import json
import subprocess
from datetime import date, datetime
from typing import Any, Dict, List, Optional


class VnStatReader:
    """Read vnStat statistics via JSON output."""

    def __init__(self, interface: Optional[str] = None):
        self.interface = interface
        self.data: Dict[str, Any] = {}

    # --------------------------------------------------
    # vnStat availability
    # --------------------------------------------------

    @staticmethod
    def check_vnstat() -> bool:
        try:
            subprocess.run(
                ["vnstat", "--version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            return True
        except Exception:
            return False

    # --------------------------------------------------
    # Refresh data
    # --------------------------------------------------

    def refresh(self) -> bool:
        try:
            result = subprocess.run(
                ["vnstat", "--json"],
                capture_output=True,
                text=True,
                check=True,
            )
            self.data = json.loads(result.stdout)
            return True
        except subprocess.CalledProcessError as e:
            print(f"vnStat command failed: {e}")
            return False
        except json.JSONDecodeError:
            print("Invalid JSON from vnStat.")
            return False
        except Exception as e:
            print(e)
            return False

    # --------------------------------------------------
    # Internal helpers
    # --------------------------------------------------

    def _iface(self) -> Optional[Dict]:
        interfaces = self.data.get("interfaces", [])
        if not interfaces:
            return None
        if self.interface is None:
            return interfaces[0]
        for iface in interfaces:
            if iface.get("name") == self.interface:
                return iface
        return interfaces[0]

    @staticmethod
    def _date_str(d: Dict) -> str:
        """Convert vnstat date dict {year, month, day} to readable string."""
        try:
            y = d.get("year", 0)
            m = d.get("month", 0)
            day = d.get("day", 0)
            if day:
                dt = date(y, m, day)
                return dt.strftime("%d %b %Y")
            else:
                dt = date(y, m, 1)
                return dt.strftime("%b %Y")
        except Exception:
            return "—"

    @staticmethod
    def _time_str(d: Dict) -> str:
        """Convert vnstat date+time dict to readable string."""
        try:
            y = d.get("year", 0)
            m = d.get("month", 0)
            day = d.get("day", 0)
            t = d.get("time", {})
            h = t.get("hour", 0)
            mi = t.get("minute", 0)
            dt = datetime(y, m, day, h, mi)
            return dt.strftime("%d %b %Y, %I:%M %p")
        except Exception:
            return "—"

    # --------------------------------------------------
    # General info
    # --------------------------------------------------

    def get_interface_name(self) -> str:
        iface = self._iface()
        return iface.get("name", "Unknown") if iface else "Unknown"

    def get_all_interfaces(self) -> List[str]:
        return [i["name"] for i in self.data.get("interfaces", [])]

    def get_updated(self) -> str:
        iface = self._iface()
        if not iface:
            return "—"
        return self._time_str(iface.get("updated", {}).get("date", {}))

    # --------------------------------------------------
    # Totals
    # --------------------------------------------------

    def get_total_usage(self) -> Dict:
        iface = self._iface()
        if not iface:
            return {}
        traffic = iface.get("traffic", {}).get("total", {})
        rx = traffic.get("rx", 0)
        tx = traffic.get("tx", 0)
        return {"download": rx, "upload": tx, "total": rx + tx}

    # --------------------------------------------------
    # Today
    # --------------------------------------------------

    def get_today_usage(self) -> Dict:
        iface = self._iface()
        if not iface:
            return {}
        days = iface.get("traffic", {}).get("day", [])
        if not days:
            return {}
        # find today's entry
        today = date.today()
        for d in days:
            dt = d.get("date", {})
            if (
                dt.get("year") == today.year
                and dt.get("month") == today.month
                and dt.get("day") == today.day
            ):
                rx = d.get("rx", 0)
                tx = d.get("tx", 0)
                return {
                    "date": self._date_str(dt),
                    "download": rx,
                    "upload": tx,
                    "total": rx + tx,
                }
        # fallback to most recent
        d = days[-1]
        rx = d.get("rx", 0)
        tx = d.get("tx", 0)
        return {
            "date": self._date_str(d.get("date", {})),
            "download": rx,
            "upload": tx,
            "total": rx + tx,
        }

    # --------------------------------------------------
    # Daily (list, newest first)
    # --------------------------------------------------

    def get_daily_usage(self) -> List[Dict]:
        iface = self._iface()
        if not iface:
            return []
        result = []
        for d in reversed(iface.get("traffic", {}).get("day", [])):
            rx = d.get("rx", 0)
            tx = d.get("tx", 0)
            result.append({
                "label": self._date_str(d.get("date", {})),
                "download": rx,
                "upload": tx,
                "total": rx + tx,
            })
        return result

    # --------------------------------------------------
    # Monthly (list, newest first)
    # --------------------------------------------------

    def get_monthly_usage(self) -> List[Dict]:
        iface = self._iface()
        if not iface:
            return []
        result = []
        for m in reversed(iface.get("traffic", {}).get("month", [])):
            rx = m.get("rx", 0)
            tx = m.get("tx", 0)
            result.append({
                "label": self._date_str(m.get("date", {})),
                "download": rx,
                "upload": tx,
                "total": rx + tx,
            })
        return result

    # --------------------------------------------------
    # Usage for a specific date
    # --------------------------------------------------

    def get_usage_for_date(self, year: int, month: int, day: int) -> Optional[Dict]:
        """Return usage for a specific calendar date, or None."""
        iface = self._iface()
        if not iface:
            return None
        for d in iface.get("traffic", {}).get("day", []):
            dt = d.get("date", {})
            if (
                dt.get("year") == year
                and dt.get("month") == month
                and dt.get("day") == day
            ):
                rx = d.get("rx", 0)
                tx = d.get("tx", 0)
                return {
                    "date": self._date_str(dt),
                    "download": rx,
                    "upload": tx,
                    "total": rx + tx,
                }
        return None

    # --------------------------------------------------
    # Daily breakdown for a specific month
    # --------------------------------------------------

    def get_usage_for_month(self, year: int, month: int) -> List[Dict]:
        """Return list of daily usage entries for a specific month."""
        iface = self._iface()
        if not iface:
            return []
        result = []
        for d in iface.get("traffic", {}).get("day", []):
            dt = d.get("date", {})
            if dt.get("year") == year and dt.get("month") == month:
                rx = d.get("rx", 0)
                tx = d.get("tx", 0)
                result.append({
                    "day": dt.get("day", 0),
                    "label": self._date_str(dt),
                    "download": rx,
                    "upload": tx,
                    "total": rx + tx,
                })
        return sorted(result, key=lambda x: x["day"])

    # --------------------------------------------------
    # Yearly (list, newest first)
    # --------------------------------------------------

    def get_yearly_usage(self) -> List[Dict]:
        iface = self._iface()
        if not iface:
            return []
        result = []
        for y in reversed(iface.get("traffic", {}).get("year", [])):
            rx = y.get("rx", 0)
            tx = y.get("tx", 0)
            year_val = y.get("date", {}).get("year", "—")
            result.append({
                "label": str(year_val),
                "download": rx,
                "upload": tx,
                "total": rx + tx,
            })
        return result

    # --------------------------------------------------
    # Formatter — vnstat JSON traffic values
    # --------------------------------------------------

    @staticmethod
    def format_bytes(num: float) -> str:
        """Format a byte value to a human-readable string."""
        units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"]
        val = float(num)
        for unit in units:
            if abs(val) < 1024 or unit == units[-1]:
                if val == int(val):
                    return f"{int(val)} {unit}"
                return f"{val:.2f} {unit}"
            val /= 1024
        return f"{val:.2f} PiB"