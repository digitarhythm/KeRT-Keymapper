### KeRT-mapper

KeRT-mapper is a Vial-compatible keyboard configurator with **HostOS** support, forked from
[vial-kb/vial-gui](https://github.com/vial-kb/vial-gui). Browser version: https://digitarhythm.github.io/KeRT-mapper/

# Docs and getting started

### Please visit [get.vial.today](https://get.vial.today/) to get started with Vial

Vial is an open-source cross-platform (Windows, Linux and Mac) GUI and a QMK fork for configuring your keyboard in real time.

## HostOS (this fork)

HostOS lets one key send a different keycode depending on the operating system the keyboard is
plugged into, detected by QMK's `OS_DETECTION_ENABLE`. A typical use is a single "copy" key that
sends `LGUI(KC_C)` on macOS and `LCTL(KC_C)` on Windows and Linux without switching layers.

### How it works

HostOS keys are stored in ordinary Vial tap dance slots: the firmware reserves the **last N tap
dance slots** and reads their four fields as a per-OS table. Nothing in the Vial protocol, the
EEPROM layout or the `.vil` file format changes.

| Tap dance field | HostOS field | Sent when the host is | Empty field falls back to |
|---|---|---|---|
| On tap | Mac | macOS, iOS | Default |
| On hold | Win | Windows | Default |
| On double tap | Linux | Linux, ChromeOS | Default |
| On tap + hold | Default | unknown OS | nothing is sent |
| Tapping term | (hidden) | used by the firmware as a "seeded" marker | |

A field is empty when it is `KC_NO` (Vial writes `KC_TRNS` as `KC_NO` too). There is no timing
involved: `HOS(n)` resolves to the chosen keycode as soon as the key is pressed, so mod-taps and
layer-taps placed in a field behave exactly as if they were in the keymap directly.

### Keyboard requirements

The firmware has to be built from the companion vial-qmk fork with `HOST_OS_ENABLE = yes`
(and optionally `HOST_OS_COUNT`, default 16); see `quantum/host_os/docs/` there. The build adds
`"hostOS": {"count": N}` to the keyboard definition, which is how Vial learns how many slots are
reserved. Keyboards without it simply show no HostOS tab.

### Using it in Vial

1. Open the **HostOS** tab (next to **Tap Dance**). Each sub-tab `0`, `1`, ... is one HostOS key.
2. Fill in the keycodes for **Mac**, **Win**, **Linux** and **Default**. Changes are written to the
   keyboard immediately, like tap dance keycodes.
3. In the **Keymap** tab, pick the key and choose `HOS(n)` from the **HostOS** tab of the keycode list.
   `HOS(n)` is the same keycode as `TD(base + n)` (base = number of tap dance slots minus N); a stock
   Vial shows the same key as `TD(base + n)` and the reserved slots in its Tap Dance tab.

The **Tap Dance** tab only shows the slots below the reserved range, so regular tap dances and HostOS
never overlap. HostOS settings are part of the `tap_dance` section of **File → Save current layout**
and are restored with **Load saved layout**.

![](https://get.vial.today/img/vial-win-1.png)


---


#### Releases

Visit https://get.vial.today/ to download a binary release of upstream Vial.

#### Download

Latest release (v1.0.0 and later):

| Platform | Download |
|---|---|
| macOS, Apple Silicon (M1 and later) | [kert-mapper-mac-arm64.dmg](https://github.com/digitarhythm/KeRT-mapper/releases/latest/download/kert-mapper-mac-arm64.dmg) |
| Windows, x64 (AMD64) installer | [kert-mapper-win-x64-setup.exe](https://github.com/digitarhythm/KeRT-mapper/releases/latest/download/kert-mapper-win-x64-setup.exe) |
| Windows, x64 (AMD64) portable | [kert-mapper-win-x64.zip](https://github.com/digitarhythm/KeRT-mapper/releases/latest/download/kert-mapper-win-x64.zip) |

Intel Macs and 32-bit / ARM Windows are not supported by this fork.
All releases: https://github.com/digitarhythm/KeRT-mapper/releases

The apps are not code-signed. On macOS, right-click `KeRT-mapper.app` and choose **Open** on first launch,
or run `xattr -d com.apple.quarantine /path/to/KeRT-mapper.app`.
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
