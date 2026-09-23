# SPDX-License-Identifier: GPL-2.0-or-later
"""Selecting a keyboard that cannot be opened (another program has it) shows a plain message instead of
a traceback, and leaves no keyboard selected (docs/device-open-error-spec.md)."""
import os
import sys

from PyQt5.QtWidgets import QMessageBox

sys.path.insert(0, os.path.dirname(__file__))


def test_open_retries_briefly_then_raises(monkeypatch):
    import vial_device
    from vial_device import VialDevice, DeviceOpenError

    class Dev:
        def open_path(self, path):
            raise OSError("busy")

    sleeps = []
    monkeypatch.setattr(vial_device.hid, "device", Dev)
    monkeypatch.setattr(vial_device.time, "sleep", lambda s: sleeps.append(s))
    d = VialDevice({"path": "x"})
    try:
        d.open()
    except DeviceOpenError:
        pass
    else:
        assert False, "DeviceOpenError expected"
    assert issubclass(DeviceOpenError, RuntimeError)
    assert 1 <= sum(sleeps) <= 3, "a few seconds of retries at most"


def test_busy_keyboard_shows_message_and_deselects(qtbot, monkeypatch):
    import vial_device
    from test_gui import prepare, FAKE_KEYBOARD, MockDevice

    mw, vk = prepare(qtbot, FAKE_KEYBOARD)
    qtbot.waitUntil(lambda: mw.centralWidget().isVisible())
    assert mw.autorefresh.current_device is not None

    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: warnings.append(a[2]))
    monkeypatch.setattr(vial_device.time, "sleep", lambda s: None)

    def busy(self, path):
        raise OSError("device busy")
    monkeypatch.setattr(MockDevice, "open_path", busy)

    # re-select the keyboard: the open fails the way it does when another program holds the device
    mw.on_device_selected()

    assert len(warnings) == 1
    assert "other program" in warnings[0] and "browser" in warnings[0]
    assert mw.autorefresh.current_device is None
    assert mw.combobox_devices.currentIndex() == -1
