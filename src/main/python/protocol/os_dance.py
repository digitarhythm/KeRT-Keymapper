# SPDX-License-Identifier: GPL-2.0-or-later
import struct

from keycodes.keycodes import Keycode, RESET_KEYCODE
from protocol.base_protocol import BaseProtocol
from protocol.constants import CMD_VIA_VIAL_PREFIX, CMD_VIAL_DYNAMIC_ENTRY_OP, DYNAMIC_VIAL_OS_DANCE_GET, \
    DYNAMIC_VIAL_OS_DANCE_SET
from unlocker import Unlocker

# One OS Dance entry is 5 keycodes: (macOS, Windows, Linux, iOS, Default), 10 bytes on the wire.
OS_DANCE_ENTRY_FORMAT = "<HHHHH"
OS_DANCE_FIELDS = ("macos", "windows", "linux", "ios", "default")


def os_dance_normalize(entry):
    """ Empty fields are always written as KC_NO; the firmware treats KC_TRNS as empty as well """
    return tuple("KC_NO" if kc == "KC_TRNS" else kc for kc in entry)


class ProtocolOSDance(BaseProtocol):

    def reload_os_dance(self):
        entries = self._retrieve_dynamic_entries(DYNAMIC_VIAL_OS_DANCE_GET, self.os_dance_count,
                                                 OS_DANCE_ENTRY_FORMAT)
        self.os_dance_entries = [tuple(Keycode.serialize(kc) for kc in e) for e in entries]

    def os_dance_get(self, idx):
        return self.os_dance_entries[idx]

    def os_dance_set(self, idx, entry):
        entry = os_dance_normalize(entry)
        if self.os_dance_entries[idx] == entry:
            return
        if RESET_KEYCODE in entry:
            Unlocker.unlock(self)
        self.os_dance_entries[idx] = entry
        serialized = struct.pack(OS_DANCE_ENTRY_FORMAT, *[Keycode.deserialize(kc) for kc in entry])
        self.usb_send(self.dev, struct.pack("BBBB", CMD_VIA_VIAL_PREFIX, CMD_VIAL_DYNAMIC_ENTRY_OP,
                                            DYNAMIC_VIAL_OS_DANCE_SET, idx) + serialized, retries=20)

    def save_os_dance(self):
        return [list(e) for e in self.os_dance_entries]

    def restore_os_dance(self, data):
        for x, e in enumerate(data):
            if x < self.os_dance_count:
                self.os_dance_set(x, tuple(e))
