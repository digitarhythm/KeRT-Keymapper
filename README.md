### vial-gui

# Docs and getting started

### Please visit [get.vial.today](https://get.vial.today/) to get started with Vial

Vial is an open-source cross-platform (Windows, Linux and Mac) GUI and a QMK fork for configuring your keyboard in real time.

## OS Dance (this fork)

OS Dance lets one key send a different keycode depending on the operating system the keyboard is
plugged into, detected by QMK's `OS_DETECTION_ENABLE`. A typical use is a single "copy" key that
sends `LGUI(KC_C)` on macOS and `LCTL(KC_C)` on Windows and Linux without switching layers.

### How it works

Each OS Dance entry is a small per-OS table stored in its own EEPROM area on the keyboard
and referenced from the keymap with the `OSD(n)` keycode:

| Field | Sent when the host is | Empty field falls back to |
|---|---|---|
| macOS | macOS | Default |
| Windows | Windows | Default |
| Linux (ChromeOS) | Linux or ChromeOS | Default |
| iOS | iOS / iPadOS | macOS, then Default |
| Default | unknown OS | nothing is sent |

A field is empty when it is `KC_NO` (Vial writes `KC_TRNS` as `KC_NO` too).
Unlike tap dance there is no timing involved: `OSD(n)` resolves to the chosen keycode as soon as
the key is pressed, so mod-taps and layer-taps placed in a field behave exactly as if they were in
the keymap directly.

### Keyboard requirements

The firmware has to be built from the companion vial-qmk fork with OS Dance enabled
(`OS_DETECTION_ENABLE = yes` plus the OS Dance library; see `quantum/os_dance/docs/` there).
Such a firmware announces the feature and the number of entries to Vial, so nothing needs to be
added to the keyboard's `vial.json`. Keyboards without OS Dance simply show no OS Dance tab.

### Using it in Vial

1. Open the **OS Dance** tab (next to **Tap Dance**). Each sub-tab `0`, `1`, ... is one OS Dance entry.
2. Fill in the keycodes for **macOS**, **Windows**, **Linux (ChromeOS)**, **iOS** and **Default**.
   Changes are written to the keyboard immediately, like combos.
3. In the **Keymap** tab, pick the key and choose `OSD(n)` from the **OS Dance** tab of the keycode list.
   `OSD(n)` can also be used inside other features (tap dance fields, key overrides, ...).

OS Dance entries are included in **File → Save current layout** (as the `os_dance` array of the `.vil`
file) and restored with **Load saved layout**. Layout files from before this feature leave the entries unchanged.

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
