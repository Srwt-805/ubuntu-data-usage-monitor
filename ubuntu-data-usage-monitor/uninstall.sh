#!/bin/bash

set -e

APP_NAME="Data Usage Monitor"
APP_ID="vstat"

INSTALL_DIR="$HOME/.local/share/$APP_ID"
DESKTOP_DIR="$HOME/.local/share/applications"
EXT_UUID="vstat@vstat.app"
EXT_DIR="$HOME/.local/share/gnome-shell/extensions/$EXT_UUID"

APP_DESKTOP="$DESKTOP_DIR/vstat.desktop"
UNINSTALL_DESKTOP="$DESKTOP_DIR/vstat-uninstall.desktop"

echo
echo "========================================"
echo "        $APP_NAME Uninstaller"
echo "========================================"
echo

if [ ! -d "$INSTALL_DIR" ]; then
    echo "$APP_NAME is not installed."
    exit 0
fi

echo "The following will be removed:"
echo
echo "  • Application files"
echo "  • Desktop launcher"
echo "  • Uninstall launcher"
echo "  • Top bar extension"
echo
echo "The following will NOT be removed:"
echo
echo "  • vnStat (and collected data)"
echo "  • Python / GTK4 / libadwaita"
echo

read -rp "Continue? [y/N]: " ANSWER

case "$ANSWER" in
    y|Y|yes|YES)
        ;;
    *)
        echo
        echo "Uninstall cancelled."
        exit 0
        ;;
esac

echo
echo "[1/3] Closing $APP_NAME..."

pkill -f "app/application.py" >/dev/null 2>&1 || true
pkill -f "app.application" >/dev/null 2>&1 || true
pkill -f "run.sh" >/dev/null 2>&1 || true

echo "Done."

echo
echo "[2/3] Removing application..."

rm -rf "$INSTALL_DIR"
rm -f "$APP_DESKTOP"
rm -f "$UNINSTALL_DESKTOP"

# also clean up old "test_monitor" leftovers if present
rm -f "$DESKTOP_DIR/test_monitor.desktop" 2>/dev/null || true
rm -f "$DESKTOP_DIR/test_monitor-uninstall.desktop" 2>/dev/null || true
rm -rf "$HOME/.local/share/test_monitor" 2>/dev/null || true

update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true

echo "Done."

echo
echo "[3/3] Removing top bar extension..."

gnome-extensions disable "$EXT_UUID" >/dev/null 2>&1 || true

# also remove from gsettings
CURRENT=$(gsettings get org.gnome.shell enabled-extensions 2>/dev/null || echo "@as []")
if echo "$CURRENT" | grep -q "$EXT_UUID"; then
    NEW=$(echo "$CURRENT" | sed "s/, '$EXT_UUID'//; s/'$EXT_UUID', //; s/'$EXT_UUID'//")
    gsettings set org.gnome.shell enabled-extensions "$NEW" 2>/dev/null || true
fi

rm -rf "$EXT_DIR"

echo "Done."

echo
echo "========================================"
echo "  $APP_NAME has been removed."
echo "========================================"
echo
echo "The following remain installed:"
echo
echo "  • vnStat"
echo "  • Python"
echo "  • GTK libraries"
echo
echo "To remove vnStat: sudo apt remove vnstat"
echo
echo "Thank you for using $APP_NAME!"
echo