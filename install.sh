#!/bin/bash

set -e

APP_NAME="Data Usage Monitor"
APP_ID="vstat"

INSTALL_DIR="$HOME/.local/share/$APP_ID"
DESKTOP_DIR="$HOME/.local/share/applications"
EXT_UUID="vstat@vstat.app"
EXT_DIR="$HOME/.local/share/gnome-shell/extensions/$EXT_UUID"

echo
echo "========================================"
echo "         $APP_NAME Installer"
echo "========================================"
echo

# --------------------------------------------------
# 1. Install dependencies
# --------------------------------------------------

echo "[1/5] Checking dependencies..."

if ! command -v vnstat >/dev/null 2>&1; then
    sudo apt update -qq || true
    sudo apt install -y python3 python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 vnstat rsync || true
fi

echo "✓ Dependencies ready."

# --------------------------------------------------
# 2. Configure vnStat
# --------------------------------------------------

echo
echo "[2/5] Checking vnStat configuration..."

INTERFACE=$(ip route | awk '/default/ {print $5}' | head -n1)
if [ -z "$INTERFACE" ]; then
    INTERFACE=$(ls /sys/class/net | grep -v '^lo$' | head -n1)
fi

if [ -n "$INTERFACE" ]; then
    echo "Detected interface: $INTERFACE"
fi

echo "✓ vnStat ready."

# --------------------------------------------------
# 3. Install / Update application files
# --------------------------------------------------

echo
echo "[3/5] Installing application..."

if [ -d "$INSTALL_DIR" ]; then
    echo "Existing installation detected — updating..."
else
    echo "Fresh installation."
fi

mkdir -p "$INSTALL_DIR"

rsync -a \
    --delete \
    --exclude=".git" \
    --exclude=".gitignore" \
    --exclude="README.md" \
    --exclude="LICENSE" \
    --exclude="__pycache__" \
    --exclude="*.pyc" \
    --exclude="ui.py" \
    ./ "$INSTALL_DIR/"

chmod +x "$INSTALL_DIR/run.sh"
chmod +x "$INSTALL_DIR/uninstall.sh"

echo "✓ Application installed to $INSTALL_DIR"

# --------------------------------------------------
# 4. Desktop launchers
# --------------------------------------------------

echo
echo "[4/5] Creating desktop launchers..."

mkdir -p "$DESKTOP_DIR"

sed \
    -e "s|@DIR@|$INSTALL_DIR|g" \
    "$INSTALL_DIR/vstat.desktop" \
    > "$DESKTOP_DIR/vstat.desktop"

sed \
    -e "s|@DIR@|$INSTALL_DIR|g" \
    "$INSTALL_DIR/vstat-uninstall.desktop" \
    > "$DESKTOP_DIR/vstat-uninstall.desktop"

chmod 644 "$DESKTOP_DIR/vstat.desktop"
chmod 644 "$DESKTOP_DIR/vstat-uninstall.desktop"

update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true

echo "✓ Desktop launchers created."

# --------------------------------------------------
# 5. GNOME Shell extension (top bar indicator)
# --------------------------------------------------

echo
echo "[5/5] Installing top bar extension..."

mkdir -p "$EXT_DIR"
cp "$INSTALL_DIR/extension/metadata.json" "$EXT_DIR/"
cp "$INSTALL_DIR/extension/extension.js" "$EXT_DIR/"
cp "$INSTALL_DIR/extension/stylesheet.css" "$EXT_DIR/"

# ── Auto-enable the extension ──
# Method 1: gnome-extensions CLI
gnome-extensions enable "$EXT_UUID" >/dev/null 2>&1 || true

# Method 2: gsettings fallback (more reliable, works even if shell hasn't reloaded)
CURRENT=$(gsettings get org.gnome.shell enabled-extensions 2>/dev/null || echo "@as []")

if echo "$CURRENT" | grep -q "$EXT_UUID"; then
    echo "Extension already enabled."
else
    # add our UUID to the enabled list
    if [ "$CURRENT" = "@as []" ]; then
        gsettings set org.gnome.shell enabled-extensions "['$EXT_UUID']" 2>/dev/null || true
    else
        # strip trailing ] and append
        NEW=$(echo "$CURRENT" | sed "s/]$/, '$EXT_UUID']/")
        gsettings set org.gnome.shell enabled-extensions "$NEW" 2>/dev/null || true
    fi
    echo "Extension enabled via gsettings."
fi

# Request shell to reload extensions via D-Bus (works on X11, harmless on Wayland)
dbus-send --session --type=method_call \
    --dest=org.gnome.Shell /org/gnome/Shell \
    org.gnome.Shell.Eval string:"Meta.restart('Reloading…')" \
    >/dev/null 2>&1 || true

echo "✓ Top bar extension installed and enabled."

# --------------------------------------------------
# Done
# --------------------------------------------------

echo
echo "========================================"
echo "        Installation Complete"
echo "========================================"
echo
echo "Application : $APP_NAME"
echo "Location    : $INSTALL_DIR"
echo
echo "Launch:"
echo "  • Applications → Data Usage Monitor"
echo "  • Click the usage indicator on the top bar"
echo
echo "Uninstall:"
echo "  • Applications → Uninstall Data Usage Monitor"
echo "  • Or run: $INSTALL_DIR/uninstall.sh"
echo
echo "NOTE: If the top bar indicator doesn't appear"
echo "immediately, log out and back in once."
echo