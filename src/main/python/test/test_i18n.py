# SPDX-License-Identifier: GPL-2.0-or-later
"""Japanese localization / i18n groundwork (docs/i18n-spec.md §7)."""
import ast
import os
import re
import sys
import xml.etree.ElementTree as ET

import pytest
from PyQt5.QtCore import QCoreApplication, QLibraryInfo
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QLabel

sys.path.insert(0, os.path.dirname(__file__))

SRC = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
RESOURCES = os.path.realpath(os.path.join(SRC, "../resources/base"))
CATALOG = os.path.join(RESOURCES, "translations", "kert_ja.ts")

EDITOR_TABS = ["Keymap", "Layout", "Macros", "Lighting", "Tap Dance", "HostOS", "Combos", "Key Overrides",
               "Alt Repeat Key", "QMK Settings", "Matrix tester", "Firmware updater"]
QMK_SETTINGS_TABS = ["Magic", "Grave Escape", "Tap-Hold", "Auto Shift", "Combo", "One Shot Keys", "Mouse keys"]
PICKER_TABS = ["Basic", "ISO/JIS", "Layers", "Quantum", "Backlight", "App, Media and Mouse", "MIDI",
               "Tap Dance", "HostOS", "User", "Macro"]

# tr() calls whose source text is assembled at runtime (main_window.py no_devices label)
NO_DEVICES = 'No devices detected. Connect a Vial-compatible device and press "Refresh"<br>' \
             'or select "File" → "Download VIA definitions" in order to enable support for VIA keyboards.'
NO_DEVICES_LINUX = NO_DEVICES + '<br><br>On Linux you need to set up a custom udev rule for keyboards to be detected. ' \
                                'Follow the instructions linked below:<br>' \
                                '<a href="https://get.vial.today/manual/linux-udev.html">https://get.vial.today/manual/linux-udev.html</a>'
DYNAMIC_SOURCES = {("MainWindow", NO_DEVICES), ("MainWindow", NO_DEVICES_LINUX)}


def qmk_settings_titles():
    """Field titles of qmk_settings.json: shown through tr("QmkSettings", title) in editor/qmk_settings.py."""
    import json
    with open(os.path.join(RESOURCES, "qmk_settings.json"), encoding="utf-8") as inf:
        return {("QmkSettings", f["title"]) for tab in json.load(inf)["tabs"] for f in tab["fields"]}

TR_CALL = re.compile(r'\btr\(\s*"(\w+)"\s*,\s*((?:"(?:[^"\\]|\\.)*"\s*)+)\)', re.S)


def get_resource(name):
    return os.path.join(RESOURCES, name)


def source_files():
    for root, dirs, files in os.walk(SRC):
        if os.path.basename(root) == "test":
            continue
        for f in files:
            if f.endswith(".py"):
                yield os.path.join(root, f)


def tr_strings_in_sources():
    found = set()
    for path in source_files():
        with open(path, encoding="utf-8") as inf:
            text = inf.read()
        for m in TR_CALL.finditer(text):
            found.add((m.group(1), ast.literal_eval("(" + m.group(2) + ")")))
    return found


def catalog_messages():
    tree = ET.parse(CATALOG)
    for ctx in tree.getroot().findall("context"):
        name = ctx.findtext("name")
        for msg in ctx.findall("message"):
            tr = msg.find("translation")
            yield name, msg.findtext("source"), (tr.text if tr is not None else None), \
                (tr.get("type") if tr is not None else None)


@pytest.fixture
def ja(qtbot):
    import branding_i18n
    app = QApplication.instance()
    branding_i18n.install(app, get_resource, locale="ja")
    yield app
    branding_i18n.uninstall(app)


def test_catalog_parses():
    root = ET.parse(CATALOG).getroot()
    assert root.tag == "TS"
    assert root.get("language", "").startswith("ja")
    assert sum(1 for _ in catalog_messages()) >= 100


def test_catalog_complete():
    incomplete = [(c, s) for c, s, t, ty in catalog_messages() if not t or ty == "unfinished"]
    assert incomplete == []


def test_catalog_matches_sources():
    in_code = tr_strings_in_sources()
    in_catalog = {(c, s) for c, s, t, ty in catalog_messages()}
    assert in_code - in_catalog == set(), "tr() strings without a Japanese translation"
    assert qmk_settings_titles() - in_catalog == set(), "QMK settings titles without a Japanese translation"
    assert in_catalog - in_code - DYNAMIC_SOURCES - qmk_settings_titles() == set(), "catalog entries that no tr() call uses"


def test_tab_labels_not_in_catalog():
    sources = {s for c, s, t, ty in catalog_messages()}
    assert sources.isdisjoint(EDITOR_TABS)
    assert sources.isdisjoint(PICKER_TABS)
    assert sources.isdisjoint(QMK_SETTINGS_TABS)


def test_resolve_language():
    import branding_i18n
    assert branding_i18n.resolve_language(env={"KERT_LANG": "ja"}, system_locale="en_US") == "ja"
    assert branding_i18n.resolve_language(env={"KERT_LANG": "en"}, system_locale="ja_JP") == "en"
    assert branding_i18n.resolve_language(env={}, system_locale="ja_JP") == "ja"
    assert branding_i18n.resolve_language(env={}, system_locale="en_US") == "en"


def test_install_ja_translates(ja):
    tr = QCoreApplication.translate
    assert tr("MainWindow", "Refresh") == "更新"
    assert tr("TapDance", "On tap") == "タップ"
    assert tr("KeymapEditor", "Layer") == "レイヤー"
    # tab labels are intentionally left in English
    assert tr("MainWindow", "Keymap") == "Keymap"
    assert tr("MainWindow", "Tap Dance") == "Tap Dance"


def test_install_en_keeps_english(qtbot):
    import branding_i18n
    app = QApplication.instance()
    for locale in ("en", "en_US", "fr"):
        assert branding_i18n.install(app, get_resource, locale=locale) == []
        assert QCoreApplication.translate("MainWindow", "Refresh") == "Refresh"
        branding_i18n.uninstall(app)


def test_qtbase_translation_loaded(ja):
    qm = os.path.join(QLibraryInfo.location(QLibraryInfo.TranslationsPath), "qtbase_ja.qm")
    if not os.path.exists(qm):
        pytest.skip("qtbase_ja.qm not shipped with this PyQt5")
    assert QCoreApplication.translate("QPlatformTheme", "Cancel") == "キャンセル"


def test_missing_catalog_is_harmless(qtbot, tmp_path):
    import branding_i18n
    app = QApplication.instance()
    assert branding_i18n.install(app, lambda name: str(tmp_path / name), locale="ja") == []
    assert QCoreApplication.translate("MainWindow", "Refresh") == "Refresh"
    branding_i18n.uninstall(app)


def labels_of(layout):
    """Texts of every QLabel that lives directly in the given grid/box layout."""
    return [layout.itemAt(i).widget().text() for i in range(layout.count())
            if isinstance(layout.itemAt(i).widget(), QLabel)]


def test_editor_labels_translated(ja, qtbot):
    from test_gui import prepare, find_tab, tray_tab_names, FAKE_KEYBOARD_HOST_OS

    mw, vk = prepare(qtbot, FAKE_KEYBOARD_HOST_OS, tap_dance=[[4, 5, 6, 7, 200]] * 4,
                     combos=[[4, 5, 0, 0, 6]] * 2)
    qtbot.waitUntil(lambda: mw.centralWidget().isVisible())

    assert mw.btn_refresh_devices.text() == "更新"
    assert mw.keymap_editor.layer_label.text() == "レイヤー"

    # tabs stay English
    assert [mw.tabs.tabText(x) for x in range(mw.tabs.count())] == \
           [lbl for lbl in EDITOR_TABS if find_tab(mw, lbl) is not None]
    assert tray_tab_names(mw)[:2] == ["Basic", "ISO/JIS"]

    td = mw.tap_dance
    assert labels_of(td.tap_dance_entries[0].container) == \
           ["タップ", "ホールド", "ダブルタップ", "タップ・ホールド", "Tapping term (ms)"]
    assert "TD(n)" in td.hint.text() and "キーマップ" in td.hint.text()
    assert td.btn_save.text() == "保存" and td.btn_revert.text() == "元に戻す"

    assert labels_of(mw.combos.combo_entries[0].container) == ["キー 1", "キー 2", "キー 3", "キー 4", "出力キー"]
    assert labels_of(mw.host_os.host_os_entries[0].container) == ["Mac", "Win", "Linux", "Default"]
    assert "HOS(n)" in mw.host_os.hint.text() and "Default" in mw.host_os.hint.text()

    assert mw.matrix_tester.unlock_btn.text() == "アンロック"
    assert mw.matrix_tester.reset_btn.text() == "リセット"
    assert mw.macro_recorder.lbl_memory.text().startswith("マクロ使用メモリ:")

    ko = mw.key_override.key_override_entries_available[0]
    assert ko.options.opt_no_reregister_trigger.text() == "他のキーが押されても解除しない"
    assert labels_of(ko.container)[:2] == ["有効", "有効にするレイヤー"]

    ark = mw.alt_repeat_key.alt_repeat_key_entries_available[0]
    assert ark.options.opt_bidirectional.text() == "双方向"

    # the virtual keyboard reports no QMK settings, so check the option widget on its own
    from PyQt5.QtWidgets import QGridLayout
    from editor.qmk_settings import BooleanOption, IntegerOption
    swap = BooleanOption({"type": "boolean", "title": "Swap Caps Lock and Left Control", "qsid": 21, "bit": 0}, QGridLayout())
    assert swap.lbl.text() == "Caps Lock と左 Control を入れ替える"
    term = IntegerOption({"type": "integer", "title": "Tapping Term", "qsid": 1, "width": 2, "min": 0, "max": 1000}, QGridLayout())
    assert term.lbl.text() == "タッピングターム (Tapping Term)"


def test_cards_translated(ja, qtbot):
    from types import SimpleNamespace
    from test_gui import prepare, FAKE_KEYBOARD_HOST_OS
    from keycodes.keycodes import KEYCODES_TAP_DANCE, KEYCODES_HOST_OS, KEYCODES_MACRO
    from macro.macro_action import ActionText
    from protocol.macro import ProtocolMacro

    buf = ProtocolMacro.macro_serialize(SimpleNamespace(vial_protocol=6), [ActionText("Hello")]) + b"\x00"
    mw, vk = prepare(qtbot, FAKE_KEYBOARD_HOST_OS, tap_dance=[[4, 5, 6, 7, 200]] * 4,
                     macro_buffer=buf + b"\x00" * (512 - len(buf)))
    qtbot.waitUntil(lambda: mw.centralWidget().isVisible())

    assert [r[0] for r in KEYCODES_TAP_DANCE[0].rows] == ["タップ", "ホールド", "ダブルタップ", "タップ・ホールド"]
    assert [r[0] for r in KEYCODES_HOST_OS[0].rows] == ["Mac", "Win", "Linux", "Default"]
    assert "Tapping term" in KEYCODES_TAP_DANCE[0].tooltip
    assert KEYCODES_MACRO[0].lines[0].startswith("テキスト: ")


def test_entry_points_install_translator():
    for name in ("main.py", "webmain.py"):
        with open(os.path.join(SRC, name), encoding="utf-8") as inf:
            assert "branding_i18n.install(" in inf.read(), name


WEB_FONT = os.path.realpath(os.path.join(SRC, "../../../web/src/fonts/kert-ja.otf"))


def test_bundled_font_covers_catalog():
    fontTools = pytest.importorskip("fontTools.ttLib")
    sys.path.insert(0, os.path.realpath(os.path.join(SRC, "../../../web")))
    import make_font_subset

    needed = make_font_subset.needed_chars()
    assert "タップ" and all(c in needed for c in "タップ・ホールド更新")
    cmap = fontTools.TTFont(WEB_FONT).getBestCmap()
    missing = sorted(c for c in needed if ord(c) not in cmap)
    assert missing == [], "re-run web/make_font_subset.py: missing {}".format("".join(missing)[:40])


def test_install_bundled_font(qtbot, tmp_path):
    import branding_i18n
    app = QApplication.instance()
    before = QFont(app.font())
    assert branding_i18n.install_bundled_font(app, lambda name: str(tmp_path / name)) is None
    assert app.font().family() == before.family()

    family = branding_i18n.install_bundled_font(app, lambda name: WEB_FONT if name == branding_i18n.BUNDLED_FONT else "")
    try:
        assert family == "Noto Sans CJK JP"
        assert app.font().family() == family and app.font().pointSize() == before.pointSize()
        with open(os.path.join(SRC, "webmain.py"), encoding="utf-8") as inf:
            assert "install_bundled_font(" in inf.read()
    finally:
        app.setFont(before)
