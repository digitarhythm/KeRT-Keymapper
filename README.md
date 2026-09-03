### vial-gui

# Docs and getting started

### Please visit [get.vial.today](https://get.vial.today/) to get started with Vial

Vial is an open-source cross-platform (Windows, Linux and Mac) GUI and a QMK fork for configuring your keyboard in real time.


![](https://get.vial.today/img/vial-win-1.png)


---


#### Releases

Visit https://get.vial.today/ to download a binary release of upstream Vial.

#### Download (this fork)

This fork adds the **OS Dance** editor (tap dance entries that send a different keycode per host OS).
Latest release:

| Platform | Download |
|---|---|
| macOS, Apple Silicon (M1 and later) | [vial-mac-arm64.dmg](https://github.com/digitarhythm/vial-gui/releases/latest/download/vial-mac-arm64.dmg) |
| Windows, x64 (AMD64) installer | [vial-win-x64-setup.exe](https://github.com/digitarhythm/vial-gui/releases/latest/download/vial-win-x64-setup.exe) |
| Windows, x64 (AMD64) portable | [vial-win-x64.zip](https://github.com/digitarhythm/vial-gui/releases/latest/download/vial-win-x64.zip) |

Intel Macs and 32-bit / ARM Windows are not supported by this fork.
All releases: https://github.com/digitarhythm/vial-gui/releases

The apps are not code-signed. On macOS, right-click `Vial.app` and choose **Open** on first launch,
or run `xattr -d com.apple.quarantine /path/to/Vial.app`.
Builds are produced by GitHub Actions; see [`util/macos/README.md`](util/macos/README.md) for how to build the macOS app locally.

#### Development

Python 3.6 is recommended (3.6 is the latest version that is officially supported by `fbs`).

Install dependencies:

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

To launch the application afterwards:

```
source venv/bin/activate
fbs run
```
