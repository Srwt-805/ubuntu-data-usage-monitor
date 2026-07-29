"""Realtime network speed monitor using /sys/class/net/."""

from pathlib import Path
from typing import Callable, Optional, Tuple


_SYS_NET = Path("/sys/class/net")
_PROC_ROUTE = Path("/proc/net/route")


class NetworkSpeedMonitor:
    """Read live network throughput from sysfs.

    Call ``sample()`` at regular intervals (e.g. every 1 s).
    It returns (rx_bytes_per_sec, tx_bytes_per_sec).
    """

    def __init__(self, interface: Optional[str] = None):
        self._forced_iface = interface
        self._prev_rx: int = 0
        self._prev_tx: int = 0
        self._initialized = False

    # ── interface discovery ───────────────────────────────

    @staticmethod
    def get_all_interfaces():
        """Return list of all network interface names (excluding lo)."""
        try:
            return sorted(
                d.name
                for d in _SYS_NET.iterdir()
                if d.is_dir() and d.name != "lo"
            )
        except Exception:
            return []

    @staticmethod
    def get_default_interface() -> Optional[str]:
        """Return the interface with the default route (destination 00000000)."""
        try:
            with open(_PROC_ROUTE, "r") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2 and parts[1] == "00000000":
                        return parts[0]
        except Exception:
            pass
        # fallback: first non-lo interface
        ifaces = NetworkSpeedMonitor.get_all_interfaces()
        return ifaces[0] if ifaces else None

    @property
    def interface(self) -> Optional[str]:
        if self._forced_iface and self._forced_iface != "auto":
            return self._forced_iface
        return self.get_default_interface()

    def set_interface(self, name: Optional[str]):
        self._forced_iface = name
        self._initialized = False

    # ── reading sysfs ─────────────────────────────────────

    def _read_bytes(self) -> Tuple[int, int]:
        """Read current rx_bytes and tx_bytes for the active interface."""
        iface = self.interface
        if not iface:
            return 0, 0
        try:
            rx_path = _SYS_NET / iface / "statistics" / "rx_bytes"
            tx_path = _SYS_NET / iface / "statistics" / "tx_bytes"
            rx = int(rx_path.read_text().strip())
            tx = int(tx_path.read_text().strip())
            return rx, tx
        except Exception:
            return 0, 0

    # ── public API ────────────────────────────────────────

    def sample(self) -> Tuple[float, float]:
        """Take a sample and return (rx_speed, tx_speed) in bytes/sec.

        The first call always returns (0, 0) since there is no prior
        sample to compare against.
        """
        rx, tx = self._read_bytes()

        if not self._initialized:
            self._prev_rx = rx
            self._prev_tx = tx
            self._initialized = True
            return 0.0, 0.0

        rx_delta = max(0, rx - self._prev_rx)
        tx_delta = max(0, tx - self._prev_tx)

        self._prev_rx = rx
        self._prev_tx = tx

        return float(rx_delta), float(tx_delta)

    def reset(self):
        """Reset the monitor (e.g. after interface change)."""
        self._initialized = False

    # ── formatting ────────────────────────────────────────

    @staticmethod
    def format_speed(bps: float) -> str:
        """Format bytes-per-second to human-readable speed string."""
        units = [("B/s", 1), ("KB/s", 1024), ("MB/s", 1024**2), ("GB/s", 1024**3)]
        for label, threshold in reversed(units):
            if bps >= threshold:
                val = bps / threshold
                if val >= 100:
                    return f"{int(val)} {label}"
                elif val >= 10:
                    return f"{val:.1f} {label}"
                else:
                    return f"{val:.2f} {label}"
        return "0 B/s"
