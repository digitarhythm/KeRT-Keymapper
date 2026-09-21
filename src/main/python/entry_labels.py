# SPDX-License-Identifier: GPL-2.0-or-later
"""Keeps the Tap Dance / HostOS keycodes' card data (rows, header extra, summary, tooltip) in sync
with the entries stored on the keyboard, and pushes the result to every keycode picker.

recreate_keyboard_keycodes() runs before reload_tap_dance(), so the contents cannot be baked in when
the keycodes are created; update() is called right after the entries are read, and again whenever an
editor writes an entry.
"""
from PyQt5 import sip

from entry_summary import HOST_OS_SLOT_LABELS, macro_lines, tap_dance_summary, tap_dance_tooltip, tapping_term
from keycodes.keycodes import KEYCODES_HOST_OS, KEYCODES_MACRO, KEYCODES_TAP_DANCE
from util import KeycodeDisplay

TAP_DANCE_ROW_LABELS = ("On tap", "On hold", "On double tap", "On tap + hold")


def update(keyboard):
    """Refresh card data of TD(x) and HOS(n) keycodes from keyboard.tap_dance_entries."""
    entries = getattr(keyboard, "tap_dance_entries", None) or []
    base = getattr(keyboard, "host_os_base", len(entries))
    label_fn = KeycodeDisplay.get_label

    for x, kc in enumerate(KEYCODES_TAP_DANCE):
        if x < len(entries):
            e = entries[x]
            kc.rows = list(zip(TAP_DANCE_ROW_LABELS, e[:4]))
            kc.title_extra = "{}ms".format(tapping_term(e))
            kc.summary = tap_dance_summary(e, label_fn)
            kc.tooltip = tap_dance_tooltip(e, label_fn, index=x)
    for n, kc in enumerate(KEYCODES_HOST_OS):
        x = base + n
        if x < len(entries):
            e = entries[x]
            kc.rows = list(zip(HOST_OS_SLOT_LABELS[:3] + ("Default",), e[:4]))
            kc.rows[1] = ("Win", e[1])
            kc.title_extra = ""
            kc.summary = tap_dance_summary(e, label_fn, HOST_OS_SLOT_LABELS)
            kc.tooltip = tap_dance_tooltip(e, label_fn, index=n, prefix="HOS",
                                           slot_labels=HOST_OS_SLOT_LABELS, show_tapping_term=False)

    # macros: first actions of each macro on the M0.. cards (keyboard.macro is read by reload_macros_late)
    macro_bytes = getattr(keyboard, "macro", None)
    if macro_bytes:
        try:
            macros = keyboard.macros_deserialize(macro_bytes)
        except Exception:
            macros = []
        for x, kc in enumerate(KEYCODES_MACRO):
            if not (kc.qmk_id.startswith("M") and kc.qmk_id[1:].isdigit()):
                continue
            n = int(kc.qmk_id[1:])
            if n < len(macros):
                kc.summary = ""
                kc.rows = []
                kc.title_extra = ""
                kc.lines = macro_lines(macros[n], label_fn)
                kc.tooltip = "\n".join(kc.lines)

    # every TabbedKeycodes (keymap picker, tray) is registered here; relabel refreshes the cards
    for client in list(KeycodeDisplay.clients):
        if sip.isdeleted(client):
            KeycodeDisplay.clients.remove(client)
            continue
        client.on_keymap_override()
