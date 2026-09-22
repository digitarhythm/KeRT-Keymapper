# SPDX-License-Identifier: GPL-2.0-or-later
"""Browser-version startup: preload before the keyboard is chosen, and no needless tab rebuilds
(docs/web-startup-preload-spec.md)."""
import os
import sys
import types

import pytest
from PyQt5.QtWidgets import QApplication

sys.path.insert(0, os.path.dirname(__file__))

RESOURCES = os.path.realpath(os.path.join(os.path.dirname(__file__), "../../resources/base"))


@pytest.fixture
def web(qtbot, monkeypatch):
    """webmain wired to the test resources, the virtual keyboard and a recording notify_ready hook"""
    import hidraw as hid
    import webmain
    from PyQt5 import sip
    from util import KeycodeDisplay
    from test_gui import FAKE_KEYBOARD, MockDevice, VirtualKeyboard, mock_enumerate

    KeycodeDisplay.clients = [c for c in KeycodeDisplay.clients if not sip.isdeleted(c)]
    MockDevice.vk = VirtualKeyboard(FAKE_KEYBOARD)
    hid.enumerate = mock_enumerate
    hid.device = MockDevice

    # the web build copies src/build/settings/base.json to build_settings.json next to the resources
    settings = os.path.realpath(os.path.join(os.path.dirname(__file__), "../../../build/settings/base.json"))
    monkeypatch.setattr(webmain, "web_get_resource",
                        lambda name: settings if name == "build_settings.json" else os.path.join(RESOURCES, name))
    ready_calls = []
    monkeypatch.setattr(webmain, "_schedule_notify_ready", lambda: ready_calls.append(1))
    webmain.window = None
    app = QApplication.instance()
    yield webmain, app, ready_calls
    if webmain.window is not None:
        webmain.window.close()
        webmain.window = None


def test_preload_then_main_reuses_window(web):
    webmain, app, ready_calls = web
    webmain.preload(app)
    win = webmain.window
    assert win is not None and not win.isVisible()
    assert getattr(app, "preloaded", False) is True
    assert ready_calls == []

    webmain.main(app)
    assert webmain.window is win
    assert win.isVisible()
    assert win.autorefresh.current_device is not None
    assert ready_calls == [1]


def test_main_without_preload(web):
    webmain, app, ready_calls = web
    webmain.main(app)
    assert webmain.window is not None and webmain.window.isVisible()
    assert webmain.window.autorefresh.current_device is not None
    assert ready_calls == [1]


def test_enumerate_without_device(monkeypatch):
    """The browser HID proxy reports no devices while no keyboard has been chosen yet"""
    fake = types.ModuleType("vialglue")
    fake.get_device_desc = lambda: ""
    monkeypatch.setitem(sys.modules, "vialglue", fake)
    monkeypatch.setattr(sys, "platform", "emscripten")
    import importlib
    import hidproxy
    hidproxy = importlib.reload(hidproxy)
    try:
        assert hidproxy.hid.enumerate() == []
    finally:
        monkeypatch.undo()
        importlib.reload(hidproxy)


def test_refresh_tabs_skips_when_unchanged(qtbot):
    from test_gui import prepare, FAKE_KEYBOARD

    mw, vk = prepare(qtbot, FAKE_KEYBOARD, combos=[[4, 5, 0, 0, 6]] * 2)
    qtbot.waitUntil(lambda: mw.centralWidget().isVisible())
    before = [mw.tabs.widget(i) for i in range(mw.tabs.count())]
    assert before
    mw.refresh_tabs()
    after = [mw.tabs.widget(i) for i in range(mw.tabs.count())]
    assert after == before, "unchanged editors must keep their tab widgets"

    # an editor that becomes invalid changes the set of tabs: now the tabs are rebuilt
    labels = [mw.tabs.tabText(i) for i in range(mw.tabs.count())]
    assert "Combos" in labels
    mw.combos.device = None
    mw.refresh_tabs()
    assert "Combos" not in [mw.tabs.tabText(i) for i in range(mw.tabs.count())]


def test_main_window_preloaded_flag(qtbot):
    from test_gui import prepare, FAKE_KEYBOARD, FakeAppctx

    class PreloadedCtx(FakeAppctx):
        preloaded = True

    import test_gui
    orig = test_gui.FakeAppctx
    test_gui.FakeAppctx = PreloadedCtx
    try:
        mw, vk = prepare(qtbot, FAKE_KEYBOARD)
    finally:
        test_gui.FakeAppctx = orig
    assert mw.appctx_preloaded is True
