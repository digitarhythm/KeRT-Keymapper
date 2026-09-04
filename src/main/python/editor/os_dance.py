# SPDX-License-Identifier: GPL-2.0-or-later
from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import QWidget, QSizePolicy, QGridLayout, QVBoxLayout, QLabel

from protocol.constants import VIAL_PROTOCOL_DYNAMIC
from widgets.key_widget import KeyWidget
from vial_device import VialKeyboard
from editor.basic_editor import BasicEditor
from widgets.tab_widget_keycodes import TabWidgetWithKeycodes

# 事前生成するエントリUIの上限（OSD(n) のキーコード空間 0x7E20..0x7E3F と同じ 32）
MAX_OS_DANCE_ENTRIES = 32


class OSDanceEntryUI(QObject):
    """1エントリ分のフォーム。

    ファームウェアの os_dance_entry_t（kc_macos, kc_windows, kc_linux, kc_ios, kc_default）に対応する
    5つの KeyWidget を持つ。空欄（KC_NO / KC_TRNS）は Default にフォールバックし、iOS は先に macOS を見る。
    キーマップには専用キーコード OSD(idx) を置く。
    """

    key_changed = pyqtSignal()

    def __init__(self, idx):
        super().__init__()

        self.idx = idx
        self.container = QGridLayout()
        self.populate_container()

        w = QWidget()
        w.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        w.setLayout(self.container)
        l = QVBoxLayout()
        l.addStretch()
        l.addSpacing(10)
        l.addWidget(w)
        l.setAlignment(w, QtCore.Qt.AlignHCenter)
        l.addSpacing(10)
        self.lbl_hint = QLabel(
            "Use <code>OSD({})</code> (OS Dance tab) to place this action in the keymap."
            " Leave a field empty to fall back to Default (iOS falls back to macOS first).".format(self.idx))
        l.addWidget(self.lbl_hint)
        l.setAlignment(self.lbl_hint, QtCore.Qt.AlignHCenter)
        l.addStretch()
        self.w2 = QWidget()
        self.w2.setLayout(l)

    def populate_container(self):
        self.kc_fields = []
        for row, label in enumerate(["macOS", "Windows", "Linux (ChromeOS)", "iOS", "Default"]):
            self.container.addWidget(QLabel(label), row, 0)
            kc = KeyWidget()
            kc.changed.connect(self.on_key_changed)
            self.container.addWidget(kc, row, 1)
            self.kc_fields.append(kc)

    def widget(self):
        return self.w2

    def load(self, data):
        """data は keyboard.os_dance_get() が返す5要素タプル"""
        for kc in self.kc_fields:
            kc.blockSignals(True)
        for kc, value in zip(self.kc_fields, data):
            kc.set_keycode(value)
        for kc in self.kc_fields:
            kc.blockSignals(False)

    def save(self):
        """keyboard.os_dance_set() に渡す5要素タプル"""
        return tuple(kc.keycode for kc in self.kc_fields)

    def on_key_changed(self):
        self.key_changed.emit()


class OSDance(BasicEditor):

    def __init__(self):
        super().__init__()
        self.keyboard = None

        self.os_dance_entries = []
        self.os_dance_entries_available = []
        self.tabs = TabWidgetWithKeycodes()
        for x in range(MAX_OS_DANCE_ENTRIES):
            entry = OSDanceEntryUI(x)
            entry.key_changed.connect(self.on_key_changed)
            self.os_dance_entries_available.append(entry)

        self.addWidget(self.tabs)

    # NOTE: BasicEditor is a QVBoxLayout, so method names here must not shadow QLayout's own
    # virtual methods (e.g. count()) which Qt calls from C++ while the layout is being reparented.
    def rebuild_ui(self):
        while self.tabs.count() > 0:
            self.tabs.removeTab(0)
        shown = min(self.keyboard.os_dance_count, MAX_OS_DANCE_ENTRIES)
        self.os_dance_entries = self.os_dance_entries_available[:shown]
        for x, e in enumerate(self.os_dance_entries):
            self.tabs.addTab(e.widget(), str(x))
        self.reload_ui()

    def reload_ui(self):
        for x, e in enumerate(self.os_dance_entries):
            e.load(self.keyboard.os_dance_get(x))

    def rebuild(self, device):
        super().rebuild(device)
        if self.valid():
            self.keyboard = device.keyboard
            self.rebuild_ui()

    def valid(self):
        # os_dance_count is only non-zero when the firmware announces OS Dance (feature bit 2)
        return isinstance(self.device, VialKeyboard) and \
               (self.device.keyboard and self.device.keyboard.vial_protocol >= VIAL_PROTOCOL_DYNAMIC
                and self.device.keyboard.os_dance_count > 0)

    def on_key_changed(self):
        # Combos タブと同じ挙動: キーコード変更は即座にキーボードへ書き込む
        for x, e in enumerate(self.os_dance_entries):
            self.keyboard.os_dance_set(x, e.save())
            # os_dance_set normalizes empty fields (KC_TRNS -> KC_NO); show what was actually stored
            e.load(self.keyboard.os_dance_get(x))
