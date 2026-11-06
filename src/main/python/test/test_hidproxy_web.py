# SPDX-License-Identifier: GPL-2.0-or-later
"""The browser build's HID device (hidproxy.hiddevice) must offer everything VialDevice calls on it.

Autorefresh.select_device closes the current device before taking the next one. In the browser this
happens when the keyboard is chosen while the window is still being preloaded: the preload's refresh
already selects it, and webmain.main's refresh closes it and selects it again."""
import importlib
import sys
import types


def load_web_hidproxy(monkeypatch):
    """hidproxy as the browser build sees it (sys.platform "emscripten", the vialglue C module)"""
    vialglue = types.ModuleType("vialglue")
    vialglue.write_device = lambda data: len(data)
    vialglue.read_device = lambda: b"\x00" * 32
    vialglue.get_device_desc = lambda: ""
    monkeypatch.setitem(sys.modules, "vialglue", vialglue)
    monkeypatch.setattr(sys, "platform", "emscripten")
    monkeypatch.delitem(sys.modules, "hidproxy", raising=False)
    module = importlib.import_module("hidproxy")
    monkeypatch.delitem(sys.modules, "hidproxy")      # later imports get the host platform's one again
    return module


def test_web_device_has_the_methods_vial_device_uses(monkeypatch):
    hidproxy = load_web_hidproxy(monkeypatch)
    dev = hidproxy.hid.device()
    for name in ("open_path", "write", "read", "close"):
        assert callable(getattr(dev, name, None)), name


def test_web_device_close_is_harmless(monkeypatch):
    # the page owns the WebHID connection; closing the Python side neither fails nor stops later use
    hidproxy = load_web_hidproxy(monkeypatch)
    dev = hidproxy.hid.device()
    dev.open_path("/webhid")
    dev.close()
    dev.close()
    assert dev.write(b"\x00" * 33) == 33
