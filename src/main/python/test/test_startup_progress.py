# SPDX-License-Identifier: GPL-2.0-or-later
"""Startup progress reporting for the browser build (docs/web-startup-progress-spec.md)."""
import os
import sys
import types

sys.path.insert(0, os.path.dirname(__file__))

STEPS = ["connect", "definition", "settings", "entries", "keymap", "macros", "tapdance", "combos", "ui", "layout", "ready"]


def test_report_is_noop_without_vialglue(monkeypatch):
    import startup_progress
    monkeypatch.delitem(sys.modules, "vialglue", raising=False)
    assert startup_progress.STEPS == STEPS
    startup_progress.report("keymap")   # must not raise


def test_report_calls_vialglue(monkeypatch):
    import startup_progress
    calls = []
    fake = types.ModuleType("vialglue")
    fake.progress = lambda step, done, total: calls.append((step, done, total))
    monkeypatch.setitem(sys.modules, "vialglue", fake)
    startup_progress.report("connect")
    startup_progress.report("keymap")
    startup_progress.report("ready")
    assert calls == [("connect", 1, len(STEPS)), ("keymap", 5, len(STEPS)), ("ready", 11, len(STEPS))]


def test_reload_reports_steps_in_order(qtbot, monkeypatch):
    import startup_progress
    from test_gui import prepare, FAKE_KEYBOARD

    seen = []
    monkeypatch.setattr(startup_progress, "report", lambda step: seen.append(step))
    mw, vk = prepare(qtbot, FAKE_KEYBOARD, tap_dance=[[4, 5, 6, 7, 200]] * 2, combos=[[4, 5, 0, 0, 6]] * 2)
    qtbot.waitUntil(lambda: mw.centralWidget().isVisible())
    # the desktop flow reports the keyboard-loading and window-building steps (connect/ready are webmain's)
    loading = [s for s in seen if s not in ("connect", "layout", "ready")]
    expected = ["definition", "settings", "entries", "keymap", "macros", "tapdance", "combos", "ui"]
    assert loading[:len(expected)] == expected
