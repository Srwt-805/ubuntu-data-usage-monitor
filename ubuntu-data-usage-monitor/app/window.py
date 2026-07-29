"""Main application window."""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, GLib, Gdk
from datetime import date
from pathlib import Path

from vnstat import VnStatReader
from app.settings import VStatSettings
from app.speed import NetworkSpeedMonitor
from app.settings_dialog import VStatSettingsDialog


# ── load external CSS ──────────────────────────────────────

_CSS_PATH = Path(__file__).parent / "style.css"


def _load_css(display):
    provider = Gtk.CssProvider()
    if _CSS_PATH.exists():
        provider.load_from_path(str(_CSS_PATH))
    else:
        provider.load_from_data(b"")
    Gtk.StyleContext.add_provider_for_display(
        display,
        provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )


# ── Window ──────────────────────────────────────────────────


class VStatWindow(Adw.ApplicationWindow):
    """Main Data Usage Monitor window."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.set_title("Data Usage Monitor")
        self.set_default_size(440, 720)
        self.set_size_request(360, 480)

        self.settings = VStatSettings()
        self.reader = VnStatReader(
            interface=None if self.settings.get("interface") == "auto"
            else self.settings.get("interface")
        )
        self.speed_monitor = NetworkSpeedMonitor(
            interface=None if self.settings.get("interface") == "auto"
            else self.settings.get("interface")
        )

        # follow system theme
        style_mgr = Adw.StyleManager.get_default()
        style_mgr.set_color_scheme(Adw.ColorScheme.DEFAULT)

        _load_css(self.get_display())
        self._build_ui()
        self.refresh()

        # speed update every 1s
        GLib.timeout_add(1000, self._speed_tick)

        # data refresh on configured interval
        self._data_timer_id = GLib.timeout_add_seconds(
            self.settings.get("refresh_interval"), self._data_tick
        )

        # listen for settings changes
        self.settings.connect(self._on_setting_changed)

    # ── UI Construction ───────────────────────────────────

    def _build_ui(self):
        # root toolbar view wraps header + content
        toolbar = Adw.ToolbarView()

        # ── header bar ──
        header = Adw.HeaderBar()
        header.set_title_widget(Gtk.Label(label="Data Usage Monitor", css_classes=["header-title"]))
        header.set_decoration_layout("icon:minimize,maximize,close")
        header.add_css_class("header-bar")

        # refresh button on the left
        refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        refresh_btn.set_tooltip_text("Refresh")
        refresh_btn.add_css_class("flat")
        refresh_btn.connect("clicked", lambda _: self.refresh())
        header.pack_start(refresh_btn)

        # settings button on the right
        settings_btn = Gtk.Button(icon_name="emblem-system-symbolic")
        settings_btn.set_tooltip_text("Settings")
        settings_btn.add_css_class("flat")
        settings_btn.connect("clicked", self._on_settings_clicked)
        header.pack_end(settings_btn)

        toolbar.add_top_bar(header)

        # ── view stack: Dashboard + History ──
        self.stack = Adw.ViewStack()

        # -- Dashboard page --
        dash_scroll = Gtk.ScrolledWindow(vexpand=True)
        dash_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=14,
        )
        self.content.set_margin_top(16)
        self.content.set_margin_bottom(24)
        self.content.set_margin_start(18)
        self.content.set_margin_end(18)

        self._build_dashboard()

        dash_scroll.set_child(self.content)
        self.stack.add_titled_with_icon(
            dash_scroll, "dashboard", "Dashboard", "user-home-symbolic"
        )

        # -- History page --
        history_scroll = Gtk.ScrolledWindow(vexpand=True)
        history_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.history_content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=14,
        )
        self.history_content.set_margin_top(16)
        self.history_content.set_margin_bottom(24)
        self.history_content.set_margin_start(18)
        self.history_content.set_margin_end(18)

        self._build_history()

        history_scroll.set_child(self.history_content)
        self.stack.add_titled_with_icon(
            history_scroll, "history", "History", "x-office-calendar-symbolic"
        )

        toolbar.set_content(self.stack)

        # ── bottom view switcher ──
        switcher_bar = Adw.ViewSwitcherBar()
        switcher_bar.set_stack(self.stack)
        switcher_bar.set_reveal(True)
        toolbar.add_bottom_bar(switcher_bar)

        self.set_content(toolbar)

    # ── Dashboard ──────────────────────────────────────────

    def _build_dashboard(self):
        # ── interface info ──
        self.info_label = Gtk.Label(xalign=0, css_classes=["info-label"])
        self.content.append(self.info_label)

        # ── TODAY card ──
        self.today_card = self._card()
        today_heading = Gtk.Label(label="TODAY", xalign=0, css_classes=["section-heading"])
        self.today_card.append(today_heading)
        self.today_total = Gtk.Label(label="—", xalign=0, css_classes=["big-value"])
        self.today_card.append(self.today_total)
        self.today_detail = Gtk.Label(xalign=0, css_classes=["detail-label"])
        self.today_card.append(self.today_detail)
        self.content.append(self.today_card)

        # ── download / upload mini cards ──
        pair = Gtk.Box(spacing=10, homogeneous=True)
        self.dl_card, self.dl_val = self._mini_card("↓ Download")
        self.ul_card, self.ul_val = self._mini_card("↑ Upload")
        pair.append(self.dl_card)
        pair.append(self.ul_card)
        self.content.append(pair)

        # ── realtime speed card (replaces lifetime total) ──
        self.speed_card = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
            css_classes=["speed-card"],
        )

        speed_heading = Gtk.Label(
            label="REALTIME SPEED", xalign=0, css_classes=["speed-heading"]
        )
        self.speed_card.append(speed_heading)

        speed_row = Gtk.Box(spacing=16, homogeneous=True)

        # download speed
        dl_speed_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        dl_speed_lbl = Gtk.Label(label="↓ Download", xalign=0, css_classes=["speed-label"])
        self.dl_speed_val = Gtk.Label(label="0 B/s", xalign=0, css_classes=["speed-value"])
        dl_speed_box.append(dl_speed_lbl)
        dl_speed_box.append(self.dl_speed_val)
        speed_row.append(dl_speed_box)

        # upload speed
        ul_speed_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        ul_speed_lbl = Gtk.Label(label="↑ Upload", xalign=0, css_classes=["speed-label"])
        self.ul_speed_val = Gtk.Label(label="0 B/s", xalign=0, css_classes=["speed-value"])
        ul_speed_box.append(ul_speed_lbl)
        ul_speed_box.append(self.ul_speed_val)
        speed_row.append(ul_speed_box)

        # total speed
        total_speed_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        total_speed_lbl = Gtk.Label(label="⇅ Total", xalign=0, css_classes=["speed-label"])
        self.total_speed_val = Gtk.Label(label="0 B/s", xalign=0, css_classes=["speed-value"])
        total_speed_box.append(total_speed_lbl)
        total_speed_box.append(self.total_speed_val)
        speed_row.append(total_speed_box)

        self.speed_card.append(speed_row)
        self.content.append(self.speed_card)

        # ── DAILY section ──
        self.daily_section = self._section("DAILY")
        self.content.append(self.daily_section)

        # ── MONTHLY section ──
        self.monthly_section = self._section("MONTHLY")
        self.content.append(self.monthly_section)

        # ── YEARLY section ──
        self.yearly_section = self._section("YEARLY")
        self.content.append(self.yearly_section)

        # ── error label ──
        self.error_label = Gtk.Label(xalign=0, visible=False, css_classes=["error-label"])
        self.content.append(self.error_label)

    # ── History page ──────────────────────────────────────

    def _build_history(self):
        # heading
        heading = Gtk.Label(label="DATA HISTORY", xalign=0, css_classes=["section-heading"])
        self.history_content.append(heading)

        # calendar inside a card
        cal_card = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            css_classes=["calendar-card"],
        )

        self.calendar = Gtk.Calendar()
        self.calendar.connect("day-selected", self._on_day_selected)
        cal_card.append(self.calendar)

        self.history_content.append(cal_card)

        # usage detail card for selected date
        self.date_usage_card = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
            css_classes=["date-usage-card"],
        )

        self.date_heading = Gtk.Label(
            label="SELECT A DATE", xalign=0, css_classes=["date-heading"]
        )
        self.date_usage_card.append(self.date_heading)

        self.date_total = Gtk.Label(label="—", xalign=0, css_classes=["date-total"])
        self.date_usage_card.append(self.date_total)

        self.date_detail = Gtk.Label(label="", xalign=0, css_classes=["date-detail"])
        self.date_usage_card.append(self.date_detail)

        self.history_content.append(self.date_usage_card)

        # monthly breakdown section
        monthly_heading = Gtk.Label(
            label="MONTHLY BREAKDOWN", xalign=0, css_classes=["section-heading"]
        )
        self.history_content.append(monthly_heading)

        self.month_list_card = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=0,
            css_classes=["card"],
        )
        self.history_content.append(self.month_list_card)

        # yearly breakdown section
        yearly_heading = Gtk.Label(
            label="YEARLY BREAKDOWN", xalign=0, css_classes=["section-heading"]
        )
        self.history_content.append(yearly_heading)

        self.year_list_card = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=0,
            css_classes=["card"],
        )
        self.history_content.append(self.year_list_card)

        # trigger initial calendar date selection
        self._on_day_selected(self.calendar)

    # ── Widget helpers ─────────────────────────────────────

    def _card(self):
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=4,
            css_classes=["card"],
        )
        return box

    def _mini_card(self, label_text):
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=2,
            css_classes=["mini-card"],
        )
        lbl = Gtk.Label(label=label_text, xalign=0, css_classes=["mini-label"])
        val = Gtk.Label(label="—", xalign=0, css_classes=["mini-value"])
        box.append(lbl)
        box.append(val)
        return box, val

    def _section(self, title):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        heading = Gtk.Label(label=title, xalign=0, css_classes=["section-heading"])
        box.append(heading)

        card = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=0,
            css_classes=["card"],
        )
        box.append(card)
        box._card = card
        return box

    def _add_row(self, card, label, total, detail, is_last=False):
        row = Gtk.Box(spacing=8)
        row.set_margin_top(6)
        row.set_margin_bottom(6)

        left = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=1,
            hexpand=True,
        )
        date_lbl = Gtk.Label(label=label, xalign=0, css_classes=["row-date"])
        detail_lbl = Gtk.Label(label=detail, xalign=0, css_classes=["row-detail"])
        left.append(date_lbl)
        left.append(detail_lbl)

        total_lbl = Gtk.Label(label=total, css_classes=["row-total"])
        total_lbl.set_valign(Gtk.Align.CENTER)

        row.append(left)
        row.append(total_lbl)
        card.append(row)

        if not is_last:
            sep = Gtk.Separator()
            sep.add_css_class("sep")
            card.append(sep)

    def _clear_box(self, box):
        while True:
            child = box.get_first_child()
            if child is None:
                break
            box.remove(child)

    def _clear_card(self, section):
        self._clear_box(section._card)

    # ── Settings dialog ──────────────────────────────────

    def _on_settings_clicked(self, _btn):
        dlg = VStatSettingsDialog(settings=self.settings)
        dlg.present(self)

    def _on_setting_changed(self, key, value):
        if key == "interface":
            iface = None if value == "auto" else value
            self.reader.interface = iface
            self.speed_monitor.set_interface(iface)
            self.speed_monitor.reset()
            self.refresh()
        elif key == "refresh_interval":
            # re-register data timer
            if self._data_timer_id:
                GLib.source_remove(self._data_timer_id)
            self._data_timer_id = GLib.timeout_add_seconds(value, self._data_tick)

    # ── Calendar handler ─────────────────────────────────

    def _on_day_selected(self, calendar):
        dt = calendar.get_date()
        year = dt.get_year()
        month = dt.get_month()
        day = dt.get_day_of_month()

        fmt = self.reader.format_bytes

        # refresh data to get latest
        self.reader.refresh()

        usage = self.reader.get_usage_for_date(year, month, day)
        if usage:
            self.date_heading.set_text(usage["date"].upper())
            self.date_total.set_text(fmt(usage["total"]))
            self.date_detail.set_text(
                f"↓ {fmt(usage['download'])}   ↑ {fmt(usage['upload'])}"
            )
        else:
            selected = date(year, month, day)
            self.date_heading.set_text(selected.strftime("%d %b %Y").upper())
            self.date_total.set_text("No Data")
            self.date_detail.set_text("No recorded usage for this date")

        # update monthly breakdown for selected month
        self._update_month_list(year, month)

        # update yearly breakdown
        self._update_year_list()

    def _update_month_list(self, year, month):
        self._clear_box(self.month_list_card)
        fmt = self.reader.format_bytes
        days = self.reader.get_usage_for_month(year, month)

        if not days:
            lbl = Gtk.Label(
                label="No data for this month",
                css_classes=["no-data-label"],
            )
            lbl.set_margin_top(12)
            lbl.set_margin_bottom(12)
            self.month_list_card.append(lbl)
            return

        for i, d in enumerate(days):
            self._add_row(
                self.month_list_card,
                d["label"],
                fmt(d["total"]),
                f"↓ {fmt(d['download'])}   ↑ {fmt(d['upload'])}",
                is_last=(i == len(days) - 1),
            )

    def _update_year_list(self):
        self._clear_box(self.year_list_card)
        fmt = self.reader.format_bytes
        yearly = self.reader.get_yearly_usage()

        if not yearly:
            lbl = Gtk.Label(
                label="No yearly data available",
                css_classes=["no-data-label"],
            )
            lbl.set_margin_top(12)
            lbl.set_margin_bottom(12)
            self.year_list_card.append(lbl)
            return

        for i, y in enumerate(yearly):
            self._add_row(
                self.year_list_card,
                y["label"],
                fmt(y["total"]),
                f"↓ {fmt(y['download'])}   ↑ {fmt(y['upload'])}",
                is_last=(i == len(yearly) - 1),
            )

    # ── Data refresh ──────────────────────────────────────

    def refresh(self):
        self.error_label.set_visible(False)

        if not self.reader.check_vnstat():
            self._show_error("vnStat is not installed.")
            return

        if not self.reader.refresh():
            self._show_error("Could not read vnStat data.")
            return

        fmt = self.reader.format_bytes

        # interface info
        name = self.reader.get_interface_name()
        updated = self.reader.get_updated()
        self.info_label.set_text(f"{name}  ·  updated {updated}")

        # today
        today = self.reader.get_today_usage()
        if today:
            self.today_total.set_text(fmt(today["total"]))
            self.today_detail.set_text(
                f"↓ {fmt(today['download'])}   ↑ {fmt(today['upload'])}"
            )
        else:
            self.today_total.set_text("—")
            self.today_detail.set_text("")

        # today's download / upload
        self.dl_val.set_text(fmt(today.get("download", 0)) if today else "—")
        self.ul_val.set_text(fmt(today.get("upload", 0)) if today else "—")

        # daily
        self._clear_card(self.daily_section)
        daily = self.reader.get_daily_usage()
        for i, d in enumerate(daily[:7]):
            self._add_row(
                self.daily_section._card,
                d["label"],
                fmt(d["total"]),
                f"↓ {fmt(d['download'])}   ↑ {fmt(d['upload'])}",
                is_last=(i == min(6, len(daily) - 1)),
            )

        # monthly
        self._clear_card(self.monthly_section)
        monthly = self.reader.get_monthly_usage()
        for i, m in enumerate(monthly[:6]):
            self._add_row(
                self.monthly_section._card,
                m["label"],
                fmt(m["total"]),
                f"↓ {fmt(m['download'])}   ↑ {fmt(m['upload'])}",
                is_last=(i == min(5, len(monthly) - 1)),
            )

        # yearly
        self._clear_card(self.yearly_section)
        yearly = self.reader.get_yearly_usage()
        for i, y in enumerate(yearly):
            self._add_row(
                self.yearly_section._card,
                y["label"],
                fmt(y["total"]),
                f"↓ {fmt(y['download'])}   ↑ {fmt(y['upload'])}",
                is_last=(i == len(yearly) - 1),
            )

    def _show_error(self, msg):
        self.error_label.set_text(msg)
        self.error_label.set_visible(True)

    # ── Speed tick (every 1s) ─────────────────────────────

    def _speed_tick(self):
        rx_speed, tx_speed = self.speed_monitor.sample()
        total_speed = rx_speed + tx_speed
        fmt = self.speed_monitor.format_speed
        self.dl_speed_val.set_text(fmt(rx_speed))
        self.ul_speed_val.set_text(fmt(tx_speed))
        self.total_speed_val.set_text(fmt(total_speed))
        return True  # keep running

    # ── Data tick (configurable interval) ─────────────────

    def _data_tick(self):
        self.refresh()
        return True
