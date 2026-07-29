"""Data Usage Monitor GTK Application."""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio

from app.window import VStatWindow


class VStatApp(Adw.Application):
    """Main application class."""

    def __init__(self):
        super().__init__(
            application_id="com.vstat.app",
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )

    def do_activate(self):
        # if a window already exists, just present it
        win = self.get_active_window()
        if win is None:
            win = VStatWindow(application=self)
        win.present()
