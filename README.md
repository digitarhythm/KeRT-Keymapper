### vial-gui

# Docs and getting started

### Please visit [get.vial.today](https://get.vial.today/) to get started with Vial

Vial is an open-source cross-platform (Windows, Linux and Mac) GUI and a QMK fork for configuring your keyboard in real time.


![](https://get.vial.today/img/vial-win-1.png)


---


#### Releases

Visit https://get.vial.today/ to download a binary release of upstream Vial.

#### Download (this fork, macOS)

This fork adds the **OS Dance** editor (tap dance entries that send a different keycode per host OS).
Native macOS builds of the latest release:

| Mac | Download |
|---|---|
| Apple Silicon (M1 and later) | [vial-mac-arm64.dmg](https://github.com/digitarhythm/vial-gui/releases/latest/download/vial-mac-arm64.dmg) |
| Intel (x86_64 / AMD64) | [vial-mac-x86_64.dmg](https://github.com/digitarhythm/vial-gui/releases/latest/download/vial-mac-x86_64.dmg) |

All releases: https://github.com/digitarhythm/vial-gui/releases

The apps are not code-signed. On first launch, right-click `Vial.app` and choose **Open**,
or run `xattr -d com.apple.quarantine /path/to/Vial.app`.
Builds are produced by GitHub Actions; see [`util/macos/README.md`](util/macos/README.md) for how to build locally.

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
