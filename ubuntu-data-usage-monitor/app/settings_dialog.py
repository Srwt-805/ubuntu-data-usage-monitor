"""Settings dialog for Data Usage Monitor."""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw

from app.settings import VStatSettings
from app.speed import NetworkSpeedMonitor


class VStatSettingsDialog(Adw.PreferencesDialog):
    """Preferences dialog with all Data Usage Monitor settings."""

    def __init__(self, settings: VStatSettings, **kwargs):
        super().__init__(**kwargs)
        self.settings = settings
        self.set_title("Settings")
        self._build()

    def _build(self):
        # ── Network group ──────────────────────────────
        net_group = Adw.PreferencesGroup(
            title="Network",
            description="Interface and refresh settings",
        )

        # interface selector
        iface_row = Adw.ComboRow(title="Interface")
        all_ifaces = NetworkSpeedMonitor.get_all_interfaces()
        choices = ["Auto-detect"] + all_ifaces
        model = Gtk.StringList()
        for c in choices:
            model.append(c)
        iface_row.set_model(model)

        current = self.settings.get("interface")
        if current == "auto" or current not in all_ifaces:
            iface_row.set_selected(0)
        else:
            iface_row.set_selected(all_ifaces.index(current) + 1)

        iface_row.connect("notify::selected", self._on_iface_changed, choices)
        net_group.add(iface_row)

        # refresh interval
        interval_row = Adw.ComboRow(title="Refresh Interval")
        intervals = ["15 seconds", "30 seconds", "60 seconds"]
        interval_vals = [15, 30, 60]
        int_model = Gtk.StringList()
        for label in intervals:
            int_model.append(label)
        interval_row.set_model(int_model)

        cur_interval = self.settings.get("refresh_interval")
        if cur_interval in interval_vals:
            interval_row.set_selected(interval_vals.index(cur_interval))
        else:
            interval_row.set_selected(1)  # default 30s

        interval_row.connect(
            "notify::selected", self._on_interval_changed, interval_vals
        )
        net_group.add(interval_row)

        net_page = Adw.PreferencesPage(title="General", icon_name="preferences-system-symbolic")
        net_page.add(net_group)

        # ── Top bar group ──────────────────────────────
        topbar_group = Adw.PreferencesGroup(
            title="Top Bar (GNOME Extension)",
            description="Control what appears in the system top bar",
        )

        # show usage toggle
        usage_row = Adw.SwitchRow(title="Show Data Usage", subtitle="Display today's data usage in the top bar")
        usage_row.set_active(self.settings.get("topbar_show_usage"))
        usage_row.connect("notify::active", self._on_usage_toggled)
        topbar_group.add(usage_row)

        # show speed toggle
        speed_row = Adw.SwitchRow(title="Show Network Speed", subtitle="Display realtime network speed in the top bar")
        speed_row.set_active(self.settings.get("topbar_show_speed"))
        speed_row.connect("notify::active", self._on_speed_toggled)
        topbar_group.add(speed_row)

        # display format
        format_row = Adw.ComboRow(title="Display Format")
        formats = ["Detailed (↓ 800M ↑ 400M)", "Compact (⇅ 1.2G)"]
        format_vals = ["detailed", "compact"]
        fmt_model = Gtk.StringList()
        for label in formats:
            fmt_model.append(label)
        format_row.set_model(fmt_model)

        cur_fmt = self.settings.get("topbar_format")
        if cur_fmt in format_vals:
            format_row.set_selected(format_vals.index(cur_fmt))
        else:
            format_row.set_selected(0)

        format_row.connect(
            "notify::selected", self._on_format_changed, format_vals
        )
        topbar_group.add(format_row)

        net_page.add(topbar_group)
        self.add(net_page)

    # ── callbacks ─────────────────────────────────────────

    def _on_iface_changed(self, row, _pspec, choices):
        idx = row.get_selected()
        value = "auto" if idx == 0 else choices[idx]
        self.settings.set("interface", value)

    def _on_interval_changed(self, row, _pspec, vals):
        self.settings.set("refresh_interval", vals[row.get_selected()])

    def _on_usage_toggled(self, row, _pspec):
        self.settings.set("topbar_show_usage", row.get_active())

    def _on_speed_toggled(self, row, _pspec):
        self.settings.set("topbar_show_speed", row.get_active())

    def _on_format_changed(self, row, _pspec, vals):
        self.settings.set("topbar_format", vals[row.get_selected()])
