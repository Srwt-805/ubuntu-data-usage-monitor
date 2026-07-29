import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import Clutter from 'gi://Clutter';
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import { Extension } from 'resource:///org/gnome/shell/extensions/extension.js';


const SETTINGS_PATH = GLib.get_home_dir() + '/.config/vstat/settings.json';


export default class VStatExtension extends Extension {

    enable() {
        this._settings = this._loadSettings();

        this._indicator = new PanelMenu.Button(0.0, 'Data Usage Monitor', false);

        this._label = new St.Label({
            text: '⇅ …',
            y_align: Clutter.ActorAlign.CENTER,
            style_class: 'vstat-label',
        });

        this._indicator.add_child(this._label);

        // clicking the indicator opens the main app
        this._indicator.connect('button-press-event', () => {
            this._openApp();
            return Clutter.EVENT_STOP;
        });

        // place it left of the clock in the center box
        Main.panel.addToStatusArea('vstat', this._indicator, 0, 'center');

        // speed tracking state
        this._prevRx = 0;
        this._prevTx = 0;
        this._speedInitialized = false;

        // first refreshes
        this._refreshUsage();
        this._refreshSpeed();

        // usage refresh every 30 seconds
        this._usageTimerId = GLib.timeout_add_seconds(
            GLib.PRIORITY_DEFAULT,
            30,
            () => {
                this._refreshUsage();
                return GLib.SOURCE_CONTINUE;
            }
        );

        // speed refresh every 1 second
        this._speedTimerId = GLib.timeout_add_seconds(
            GLib.PRIORITY_DEFAULT,
            1,
            () => {
                this._refreshSpeed();
                return GLib.SOURCE_CONTINUE;
            }
        );

        // watch settings file for changes
        this._monitorSettings();
    }


    disable() {
        if (this._usageTimerId) {
            GLib.source_remove(this._usageTimerId);
            this._usageTimerId = null;
        }

        if (this._speedTimerId) {
            GLib.source_remove(this._speedTimerId);
            this._speedTimerId = null;
        }

        if (this._settingsMonitor) {
            this._settingsMonitor.cancel();
            this._settingsMonitor = null;
        }

        this._indicator?.destroy();
        this._indicator = null;
        this._label = null;
    }


    // ── Settings ──────────────────────────────────────────

    _loadSettings() {
        let defaults = {
            interface: 'auto',
            topbar_show_usage: true,
            topbar_show_speed: true,
            topbar_format: 'detailed',
        };

        try {
            if (GLib.file_test(SETTINGS_PATH, GLib.FileTest.EXISTS)) {
                let [ok, contents] = GLib.file_get_contents(SETTINGS_PATH);
                if (ok && contents && contents.length > 0) {
                    let text = new TextDecoder().decode(contents);
                    let parsed = JSON.parse(text);
                    return Object.assign(defaults, parsed);
                }
            }
        } catch (e) {
            log(`[VStat] Failed to load settings: ${e.message}`);
        }

        return defaults;
    }


    _monitorSettings() {
        try {
            let file = Gio.File.new_for_path(SETTINGS_PATH);
            // ensure parent dir exists
            let parent = file.get_parent();
            if (parent && !parent.query_exists(null)) {
                return;  // no settings dir yet
            }

            this._settingsMonitor = file.monitor_file(
                Gio.FileMonitorFlags.NONE, null
            );
            this._settingsMonitor.connect('changed', () => {
                this._settings = this._loadSettings();
                this._refreshUsage();
                this._refreshSpeed();
                this._updateLabel();
            });
        } catch (e) {
            log(`[VStat] Settings monitor failed: ${e.message}`);
        }
    }


    // ── App launcher ─────────────────────────────────────

    _openApp() {
        try {
            const installDir = GLib.get_home_dir() + '/.local/share/vstat';
            const runScript = installDir + '/run.sh';

            if (GLib.file_test(runScript, GLib.FileTest.EXISTS)) {
                GLib.spawn_command_line_async(`bash "${runScript}"`);
            } else {
                let appInfo = Gio.DesktopAppInfo.new('vstat.desktop');
                if (appInfo) {
                    appInfo.launch([], null);
                }
            }
        } catch (e) {
            log(`[VStat] Failed to open app: ${e.message}`);
        }
    }


    // ── Interface detection ──────────────────────────────

    _getActiveInterface() {
        let iface = this._settings.interface;
        if (iface && iface !== 'auto') {
            return iface;
        }

        // auto-detect from /proc/net/route
        try {
            let [ok, contents] = GLib.file_get_contents('/proc/net/route');
            if (ok && contents) {
                let text = new TextDecoder().decode(contents);
                let lines = text.split('\n');
                for (let line of lines) {
                    let parts = line.trim().split(/\s+/);
                    if (parts.length >= 2 && parts[1] === '00000000' && parts[0] !== 'lo') {
                        return parts[0];
                    }
                }
            }
        } catch (e) {
            // fallback below
        }

        // fallback: scan /sys/class/net and pick first non-lo interface
        try {
            let dir = Gio.File.new_for_path('/sys/class/net');
            let enumerator = dir.enumerate_children('standard::name', Gio.FileQueryInfoFlags.NONE, null);
            let info;
            while ((info = enumerator.next_file(null)) !== null) {
                let name = info.get_name();
                if (name !== 'lo') {
                    return name;
                }
            }
        } catch (e) {
            // ignore
        }

        return null;
    }


    // ── Data usage refresh ───────────────────────────────

    _refreshUsage() {
        try {
            let [ok, stdout] = GLib.spawn_command_line_sync('vnstat --json');

            if (!ok || !stdout || stdout.length === 0) {
                this._usageText = '⇅ —';
                this._updateLabel();
                return;
            }

            let text = new TextDecoder().decode(stdout);
            let data = JSON.parse(text);

            let ifaces = data.interfaces;
            if (!ifaces || ifaces.length === 0) {
                this._usageText = '⇅ —';
                this._updateLabel();
                return;
            }

            // find the active interface
            let activeIface = this._getActiveInterface();
            let iface = ifaces[0];
            if (activeIface) {
                for (let i of ifaces) {
                    if (i.name === activeIface) {
                        iface = i;
                        break;
                    }
                }
            }

            let days = iface.traffic?.day;
            if (!days || days.length === 0) {
                this._usageText = '⇅ 0 B';
                this._updateLabel();
                return;
            }

            // find today's entry
            let now = new Date();
            let todayEntry = null;

            for (let d of days) {
                if (d.date.year  === now.getFullYear() &&
                    d.date.month === now.getMonth() + 1 &&
                    d.date.day   === now.getDate()) {
                    todayEntry = d;
                    break;
                }
            }

            // fallback to most recent recorded day if exact date match is not found
            if (!todayEntry && days.length > 0) {
                todayEntry = days[days.length - 1];
            }

            if (todayEntry) {
                let rx = todayEntry.rx || 0;
                let tx = todayEntry.tx || 0;
                let total = rx + tx;

                if (this._settings.topbar_format === 'compact') {
                    this._usageText = `⇅ ${this._fmt(total)}`;
                } else {
                    this._usageText =
                        `⇅ ${this._fmt(total)} (↓ ${this._fmt(rx)} ↑ ${this._fmt(tx)})`;
                }
            } else {
                this._usageText = '⇅ 0 B';
            }

            this._updateLabel();

        } catch (e) {
            this._usageText = '⇅ —';
            this._updateLabel();
        }
    }


    // ── Speed refresh ────────────────────────────────────

    _refreshSpeed() {
        let iface = this._getActiveInterface();
        if (!iface) {
            this._speedText = '';
            this._updateLabel();
            return;
        }

        try {
            let rxPath = `/sys/class/net/${iface}/statistics/rx_bytes`;
            let txPath = `/sys/class/net/${iface}/statistics/tx_bytes`;

            let [okRx, rxData] = GLib.file_get_contents(rxPath);
            let [okTx, txData] = GLib.file_get_contents(txPath);

            if (!okRx || !okTx) {
                this._speedText = '';
                this._updateLabel();
                return;
            }

            let rx = parseInt(new TextDecoder().decode(rxData).trim(), 10);
            let tx = parseInt(new TextDecoder().decode(txData).trim(), 10);

            if (!this._speedInitialized) {
                this._prevRx = rx;
                this._prevTx = tx;
                this._speedInitialized = true;
                this._speedText = '↓ 0 B/s ↑ 0 B/s (⇅ 0 B/s)';
                this._updateLabel();
                return;
            }

            let rxDelta = Math.max(0, rx - this._prevRx);
            let txDelta = Math.max(0, tx - this._prevTx);
            let totalDelta = rxDelta + txDelta;

            this._prevRx = rx;
            this._prevTx = tx;

            if (this._settings.topbar_format === 'compact') {
                this._speedText = `⚡ ${this._fmtSpeed(totalDelta)}`;
            } else {
                this._speedText = `↓ ${this._fmtSpeed(rxDelta)} ↑ ${this._fmtSpeed(txDelta)} (⇅ ${this._fmtSpeed(totalDelta)})`;
            }
            this._updateLabel();

        } catch (e) {
            this._speedText = '';
            this._updateLabel();
        }
    }


    // ── Label assembly ───────────────────────────────────

    _updateLabel() {
        if (!this._label) return;

        let parts = [];

        if (this._settings.topbar_show_usage && this._usageText) {
            parts.push(this._usageText);
        }

        if (this._settings.topbar_show_speed && this._speedText) {
            parts.push(this._speedText);
        }

        if (parts.length === 0) {
            this._label.set_text('⇅ Data Usage Monitor');
        } else {
            this._label.set_text(parts.join('  │  '));
        }
    }


    // ── Formatters ───────────────────────────────────────

    _fmt(bytes) {
        const units = ['B', 'K', 'M', 'G', 'T'];
        let val = bytes;

        for (let unit of units) {
            if (Math.abs(val) < 1024 || unit === units[units.length - 1]) {
                if (val === Math.floor(val)) {
                    return `${val}${unit}`;
                }
                return `${val.toFixed(1)}${unit}`;
            }
            val /= 1024;
        }

        return `${val.toFixed(1)}P`;
    }


    _fmtSpeed(bytesPerSec) {
        const units = [
            ['B/s', 1],
            ['K/s', 1024],
            ['M/s', 1048576],
            ['G/s', 1073741824],
        ];

        for (let i = units.length - 1; i >= 0; i--) {
            let [label, threshold] = units[i];
            if (bytesPerSec >= threshold) {
                let val = bytesPerSec / threshold;
                if (val >= 100) return `${Math.floor(val)}${label}`;
                if (val >= 10) return `${val.toFixed(1)}${label}`;
                return `${val.toFixed(1)}${label}`;
            }
        }

        return '0B/s';
    }
}
