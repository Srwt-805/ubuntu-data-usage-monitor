# Data Usage Monitor for Linux

A lightweight GTK4 + libadwaita application for Ubuntu and GNOME desktops that displays network data usage using **vnStat**. The application includes a desktop interface as well as a GNOME Shell top bar indicator for quickly viewing daily network usage.

> **Note:** This project uses **vnStat** as its backend and does not monitor network traffic directly.

---

## Features

* GNOME Shell top bar indicator displaying today's total, download, and upload usage
* Click the top bar indicator to open the main application
* Daily, monthly, and yearly usage statistics
* Separate download and upload totals
* Automatic refresh every 30 seconds
* Native GTK4 + libadwaita interface with dark theme support
* Standard window controls (minimize, maximize, and close)

---

## Requirements

* Ubuntu 22.04 or later
* GNOME Desktop (GNOME 45 or later recommended)
* Python 3
* GTK4
* libadwaita
* vnStat

> All required dependencies, including **vnStat**, are installed automatically during installation.

---

## Installation

Clone the repository and run:

```bash
make
```

The installer will automatically:

1. Install all required dependencies.
2. Configure **vnStat** for the active network interface.
3. Install the application to:

```text
~/.local/share/vstat/
```

4. Create desktop launchers for:

   * Data Usage Monitor
   * Uninstall Data Usage Monitor
5. Install and enable the GNOME Shell extension.

---

## Running the Application

Launch the application using any of the following methods:

* Open **Data Usage Monitor** from the application launcher.
* Click the network usage indicator in the GNOME top bar.
* Run:

```bash
make run
```

---

## Uninstallation

You can uninstall the application by:

* Launching **Uninstall Data Usage Monitor** from the application launcher.
* Running:

```bash
make uninstall
```

---

## Project Structure

```text
ubuntu-data-usage-monitor/
├── app/
│   ├── __init__.py
│   ├── application.py
│   ├── window.py
│   └── style.css
├── extension/
│   ├── extension.js
│   ├── metadata.json
│   └── stylesheet.css
├── vnstat.py
├── run.sh
├── install.sh
├── uninstall.sh
├── Makefile
├── vstat.desktop
├── vstat-uninstall.desktop
├── icon.png
└── unicon.png
```

---

## Technologies Used

* Python 3
* GTK4
* libadwaita
* JavaScript (GNOME Shell Extension)
* vnStat

---

## Future Improvements

* Application screenshots
* Additional usage graphs and charts
* Custom refresh interval
* Export usage reports

---

## License

This project is licensed under the MIT License.
