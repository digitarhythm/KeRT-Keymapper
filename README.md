### vial-gui

# Docs and getting started

### Please visit [get.vial.today](https://get.vial.today/) to get started with Vial

Vial is an open-source cross-platform (Windows, Linux and Mac) GUI and a QMK fork for configuring your keyboard in real time.

## OS Dance (this fork)

OS Dance lets one key send a different keycode depending on the operating system the keyboard is
plugged into, detected by QMK's `OS_DETECTION_ENABLE`. A typical use is a single "copy" key that
sends `LGUI(KC_C)` on macOS and `LCTL(KC_C)` on Windows and Linux without switching layers.

### How it works

OS Dance does not add a new keycode type. The keyboard reserves a range of its tap dance entries
and the firmware reinterprets each of those entries as a per-OS table:

| Tap dance field | OS Dance meaning |
|---|---|
| On tap | macOS (and iOS) |
| On hold | Windows |
| On double tap | Linux (and ChromeOS) |
| On tap + hold | Default: used when the OS is unknown, or when the matching field above is empty |
| Tapping term | unused |

When the key is pressed, the firmware looks up the detected OS, picks the matching field and sends it.
An empty field (`KC_NO` or `KC_TRNS`) falls back to Default; if Default is empty too, nothing is sent.

### Keyboard requirements

- Firmware built with `OS_DETECTION_ENABLE = yes` and the OS Dance handling for the reserved
  tap dance entries (see the `trek/lettio` keyboard in the companion vial-qmk fork for a reference).
- An `osDance` key in the keyboard's `vial.json` telling Vial which entries are reserved:

```json
"osDance": { "base": 24, "count": 8 }
```

With `VIAL_TAP_DANCE_ENTRIES = 32` this reserves `TD(24)`–`TD(31)` as `OD(0)`–`OD(7)`.
The GUI must match the firmware: `base` and `count` are read from the definition, so keep them in sync
with the firmware's constants. Keyboards without `osDance` are unaffected and show no OS Dance tab.

### Using it in Vial

1. Open the **OS Dance** tab (next to **Tap Dance**). Each sub-tab `0`, `1`, ... is one OS Dance entry.
2. Fill in the keycodes for **Mac (iOS)**, **Windows**, **Linux (ChromeOS)** and **Default**.
   Changes are written to the keyboard immediately, like tap dance keycodes.
3. In the **Keymap** tab, pick the key and choose `OD(n)` from the **OS Dance** tab of the keycode list.
   `OD(n)` is stored on the keyboard as `TD(base + n)`; the tooltip shows which tap dance entry it is.

The **Tap Dance** tab only shows the entries below `base`, so regular tap dances and OS Dance never
overlap. Because the reserved entries are ordinary tap dance storage, OS Dance settings are included in
**File → Save current layout** and restored with **Load saved layout**.


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
