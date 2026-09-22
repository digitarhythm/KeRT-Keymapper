<p align="center"><img src="misc/kert-mapper.png" alt="KeRT-mapper" width="480"></p>

# KeRT-mapper

**KeRT-mapper** is a keyboard configurator for [Vial](https://get.vial.today/)-compatible keyboards
(QMK + Vial firmware) with one extra feature: **HostOS** keys, which send a different keycode depending
on the operating system the keyboard is plugged into. It is a fork of
[vial-kb/vial-gui](https://github.com/vial-kb/vial-gui) and talks the unchanged Vial protocol, so every
keyboard that works with Vial works with KeRT-mapper.

日本語の説明は[下](#日本語)にあります。

## Highlights

- **HostOS keys** – one key, three keycodes: macOS / Windows / Linux, plus a default. See below.
- **Everything Vial does** – keymap, layers, macros, tap dance, combos, key overrides, alt repeat key,
  QMK settings, matrix tester, lighting, firmware updater.
- **Cards instead of codes** – tap dance, combo, HostOS and macro entries are shown as cards with their
  contents, both in the editors and in the keycode picker.
- **Light, flat look** – the "KeRT Light" theme, flat keys, a two-line keyboard selector, a 40/60 split
  between keyboard and keycode picker with the keyboard scaled to fit.
- **Japanese UI** – follows the system (or browser) language; English otherwise. Keycode names and tab
  labels stay English on purpose.
- **Fast start** – the keycode picker builds its tabs on first use.

## Download

| Platform | Download |
|---|---|
| **Browser** (Chrome, Edge, other Chromium browsers with WebHID) | **https://digitarhythm.github.io/KeRT-mapper/** |
| macOS, Apple Silicon (M1 and later) | [kert-mapper-mac-arm64.dmg](https://github.com/digitarhythm/KeRT-mapper/releases/latest/download/kert-mapper-mac-arm64.dmg) |
| Windows, x64 installer | [kert-mapper-win-x64-setup.exe](https://github.com/digitarhythm/KeRT-mapper/releases/latest/download/kert-mapper-win-x64-setup.exe) |
| Windows, x64 portable | [kert-mapper-win-x64.zip](https://github.com/digitarhythm/KeRT-mapper/releases/latest/download/kert-mapper-win-x64.zip) |

All releases: https://github.com/digitarhythm/KeRT-mapper/releases. Intel Macs and 32-bit / ARM
Windows are not supported. A Linux AppImage is built by CI as a workflow artifact.

The apps are not code-signed. On macOS, right-click `KeRT-mapper.app` and choose **Open** on first
launch, or run `xattr -d com.apple.quarantine /path/to/KeRT-mapper.app`.

The browser version needs WebHID, so it works in Chromium-based browsers only. Close any desktop
configurator (KeRT-mapper, Vial) that has the keyboard open before connecting from the browser: only
one program can open the keyboard at a time. The first visit downloads about 12 MB; later visits are
served from the browser cache.

## HostOS

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

A field is empty when it is `KC_NO` (`KC_TRNS` is written as `KC_NO` too). There is no timing
involved: `HOS(n)` resolves to the chosen keycode as soon as the key is pressed, so mod-taps and
layer-taps placed in a field behave exactly as if they were in the keymap directly.

### Keyboard requirements

The firmware has to be built from the companion vial-qmk fork with `HOST_OS_ENABLE = yes`
(and optionally `HOST_OS_COUNT`, default 16); see `quantum/host_os/docs/` there. The build adds
`"hostOS": {"count": N}` to the keyboard definition, which is how KeRT-mapper learns how many slots
are reserved. Keyboards without it simply show no HostOS tab and behave as in Vial.

### Using it

1. Open the **HostOS** tab (next to **Tap Dance**). Each card `HOS(0)`, `HOS(1)`, ... is one HostOS key.
2. Fill in the keycodes for **Mac**, **Win**, **Linux** and **Default**. Changes are written to the
   keyboard immediately, like tap dance keycodes.
3. In the **Keymap** tab, pick the key and choose `HOS(n)` from the **HostOS** tab of the keycode picker.
   `HOS(n)` is the same keycode as `TD(base + n)` (base = number of tap dance slots minus N); a stock
   Vial shows the same key as `TD(base + n)`.

The **Tap Dance** tab only shows the slots below the reserved range, so regular tap dances and HostOS
never overlap. HostOS settings are part of the `tap_dance` section of **File → Save current layout**
and are restored with **Load saved layout**; `.vil` files stay compatible with Vial.

## Development

Python 3.6 is what upstream's packaging (`fbs`) supports for the Windows build; any recent Python 3
works for running from source and for the tests.

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src/main/python python src/main/python/main.py
```

Tests (pytest + pytest-qt; the GUI tests run headless with the offscreen platform):

```
pip install pytest pytest-qt pytest-xdist
QT_QPA_PLATFORM=offscreen PYTHONPATH=src/main/python pytest -n 6 --dist loadfile src/main/python/test
```

- `KERT_LANG=ja` / `KERT_LANG=en` forces the UI language.
- Specs for the fork's features live in [`docs/`](docs/) (Japanese): HostOS, entry cards, theme and
  layout, i18n, picker lazy build, and the rebranding plan.
- Builds: [`util/macos/README.md`](util/macos/README.md) (macOS app), [`web/README.md`](web/README.md)
  (browser version), `.github/workflows/` (CI: release builds on version tags, web build on tags or
  on demand).

### Keeping up with upstream

The fork keeps upstream's code largely untouched: product identity lives in `branding.py`, the theme
in `branding_theme.py`, translations in `branding_i18n.py` and `translations/`, and new features in
new files, so upstream changes merge with few conflicts. Wire-protocol identifiers (the `vial:`
serial magic, HID command values, `.vil` / `vial.json`) are deliberately unchanged.

## License

GPL-2.0-or-later, like [vial-gui](https://github.com/vial-kb/vial-gui) it is based on. The browser
version bundles a subset of Noto Sans CJK JP (SIL Open Font License 1.1, see `web/src/fonts/OFL.txt`).

---

## 日本語

KeRT-mapper は、Vial 対応キーボード（QMK + Vial ファームウェア）向けの設定ツールです。
[vial-kb/vial-gui](https://github.com/vial-kb/vial-gui) をもとに、次の点を加えています。

- **HostOS キー**: 1 つのキーで、接続先が macOS / Windows / Linux のどれかに応じて別のキーコードを送ります
  （ファームウェア側は OS 検出付きの vial-qmk フォークでビルドしてください）。
- **カード表示**: Tap Dance、Combo、HostOS、マクロの設定内容をカードで表示します（エディタ、キーコード一覧とも）。
- **白基調のフラットな見た目**、キーボード名の 2 段表示、上下 4:6 のキーマップ画面。
- **日本語 UI**: OS（ブラウザ版はブラウザ）の言語設定に従います。キーコード名とタブ名は英語のままです。

**入手**: ブラウザ版は https://digitarhythm.github.io/KeRT-mapper/ （Chrome / Edge などの Chromium 系）、
デスクトップ版は上の Download 表から（macOS Apple Silicon、Windows x64）。デスクトップ版はコード署名を
していないため、macOS では初回のみ右クリック → 開く、または `xattr -d com.apple.quarantine` が必要です。
ブラウザ版で接続する前に、同じキーボードを開いているデスクトップ版の設定ツールは終了してください。

仕様書は [`docs/`](docs/) にあります。
