# SPDX-License-Identifier: GPL-2.0-or-later
"""Editors create their entry widgets on demand, as many as the keyboard has
(docs/editor-lazy-entries-spec.md)."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

TAP_DANCE = [[4, 5, 6, 7, 200]] * 4
COMBOS = [[4, 5, 0, 0, 6]] * 3


def prepared(qtbot):
    from test_gui import prepare, FAKE_KEYBOARD

    mw, vk = prepare(qtbot, FAKE_KEYBOARD, tap_dance=TAP_DANCE, combos=COMBOS)
    qtbot.waitUntil(lambda: mw.centralWidget().isVisible())
    return mw, vk


def test_entries_match_keyboard_counts(qtbot):
    mw, vk = prepared(qtbot)
    assert len(mw.tap_dance.tap_dance_entries_available) == len(TAP_DANCE)
    assert len(mw.tap_dance.cards_available) == len(TAP_DANCE)
    assert len(mw.combos.combo_entries_available) == len(COMBOS)
    assert len(mw.combos.cards_available) == len(COMBOS)
    assert len(mw.key_override.key_override_entries_available) == 0
    assert len(mw.alt_repeat_key.alt_repeat_key_entries_available) == 0
    assert len(mw.host_os.host_os_entries_available) == 0
    # and the visible entries are the same objects
    assert mw.tap_dance.tap_dance_entries == mw.tap_dance.tap_dance_entries_available[:len(TAP_DANCE)]


def test_entries_grow_on_demand(qtbot):
    mw, vk = prepared(qtbot)
    td = mw.tap_dance
    first = td.tap_dance_entries_available[0]
    td.ensure_entries(12)
    assert len(td.tap_dance_entries_available) == 12 and len(td.cards_available) == 12
    assert td.tap_dance_entries_available[0] is first
    td.ensure_entries(12)
    assert len(td.tap_dance_entries_available) == 12
    td.ensure_entries(129)
    assert len(td.tap_dance_entries_available) == 128

    ko = mw.key_override
    ko.ensure_entries(2)
    assert len(ko.key_override_entries_available) == 2
    assert ko.key_override_entries_available[0].options is not None   # entries are fully built
    ark = mw.alt_repeat_key
    ark.ensure_entries(1)
    assert len(ark.alt_repeat_key_entries_available) == 1


def test_startup_widget_budget(qtbot):
    from widgets.key_widget import KeyWidget

    mw, vk = prepared(qtbot)
    assert len(mw.findChildren(KeyWidget)) < 100
