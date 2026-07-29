"""VStat settings — persist user preferences to ~/.config/vstat/settings.json."""

import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


_DEFAULTS = {
    "interface": "auto",          # "auto" or specific name like "wlan0"
    "refresh_interval": 30,       # seconds: 15, 30, or 60
    "topbar_show_usage": True,    # show data usage in GNOME top bar
    "topbar_show_speed": True,    # show realtime speed in GNOME top bar
    "topbar_format": "detailed",  # "compact" or "detailed"
}

_CONFIG_DIR = Path.home() / ".config" / "vstat"
_CONFIG_FILE = _CONFIG_DIR / "settings.json"


class VStatSettings:
    """Load, save, and observe user settings."""

    def __init__(self):
        self._data: Dict[str, Any] = dict(_DEFAULTS)
        self._listeners: List[Callable] = []
        self.load()

    # ── persistence ──────────────────────────────────────

    def load(self):
        """Load settings from disk, merging with defaults."""
        if _CONFIG_FILE.exists():
            try:
                with open(_CONFIG_FILE, "r") as f:
                    saved = json.load(f)
                for k, v in saved.items():
                    if k in _DEFAULTS:
                        self._data[k] = v
            except Exception:
                pass  # fall back to defaults

    def save(self):
        """Persist current settings to disk."""
        try:
            _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(_CONFIG_FILE, "w") as f:
                json.dump(self._data, f, indent=2)
        except Exception as e:
            print(f"[VStat] Failed to save settings: {e}")

    # ── access ───────────────────────────────────────────

    def get(self, key: str) -> Any:
        return self._data.get(key, _DEFAULTS.get(key))

    def set(self, key: str, value: Any):
        if self._data.get(key) != value:
            self._data[key] = value
            self.save()
            self._notify(key, value)

    @property
    def all(self) -> Dict[str, Any]:
        return dict(self._data)

    # ── observation ──────────────────────────────────────

    def connect(self, callback: Callable):
        """Register a callback(key, value) for setting changes."""
        self._listeners.append(callback)

    def _notify(self, key: str, value: Any):
        for cb in self._listeners:
            try:
                cb(key, value)
            except Exception:
                pass
