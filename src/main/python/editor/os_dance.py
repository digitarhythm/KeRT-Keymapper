# SPDX-License-Identifier: GPL-2.0-or-later
from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import QWidget, QSizePolicy, QGridLayout, QVBoxLayout, QLabel

from protocol.constants import VIAL_PROTOCOL_DYNAMIC
from widgets.key_widget import KeyWidget
from vial_device import VialKeyboard
from editor.basic_editor import BasicEditor
from widgets.tab_widget_keycodes import TabWidgetWithKeycodes

# 事前生成するエントリUIの上限。vial.json の osDance.count がこれを超えた分は表示しない
MAX_OS_DANCE_ENTRIES = 32


class OSDanceEntryUI(QObject):
    """1エントリ分のフォーム。

    実体は Tap Dance エントリ（tap, hold, double_tap, tap_hold, tapping_term の5要素）を
    OS 対応表として読み替えたもの（ファームウェア側 os_tapdance.c と同じ並び）:
        on tap        -> Mac (iOS)
        on hold       -> Windows
        on double tap -> Linux (ChromeOS)
        on tap + hold -> Default (判別不能時、および他の欄が未設定のときのフォールバック)
    tapping_term は画面に出さず、読み込んだ値をそのまま書き戻す（データ形状の維持のため）。
    キーマップには TD(base + idx) をそのまま置く。GUI 上ではこれを OD(idx) と表示する（keycodes.py の KEYCODES_OS_DANCE）。
    """

    key_changed = pyqtSignal()

    def __init__(self, idx):
        super().__init__()

        self.idx = idx            # OS Dance 内での通し番号 (0..count-1)
        self.td_idx = None        # 実際に読み書きする Tap Dance エントリ番号 (base + idx)
        self.tapping_term = 0     # 非表示・素通し
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
        self.lbl_hint = QLabel()
        l.addWidget(self.lbl_hint)
        l.setAlignment(self.lbl_hint, QtCore.Qt.AlignHCenter)
        l.addStretch()
        self.w2 = QWidget()
        self.w2.setLayout(l)
        self.update_hint()

    def populate_container(self):
        self.container.addWidget(QLabel("Mac (iOS)"), 0, 0)
        self.kc_mac = KeyWidget()
        self.kc_mac.changed.connect(self.on_key_changed)
        self.container.addWidget(self.kc_mac, 0, 1)

        self.container.addWidget(QLabel("Windows"), 1, 0)
        self.kc_win = KeyWidget()
        self.kc_win.changed.connect(self.on_key_changed)
        self.container.addWidget(self.kc_win, 1, 1)

        self.container.addWidget(QLabel("Linux (ChromeOS)"), 2, 0)
        self.kc_linux = KeyWidget()
        self.kc_linux.changed.connect(self.on_key_changed)
        self.container.addWidget(self.kc_linux, 2, 1)

        self.container.addWidget(QLabel("Default"), 3, 0)
        self.kc_default = KeyWidget()
        self.kc_default.changed.connect(self.on_key_changed)
        self.container.addWidget(self.kc_default, 3, 1)

    def set_td_idx(self, td_idx):
        self.td_idx = td_idx
        self.update_hint()

    def update_hint(self):
        fallback = "Leave an OS empty to fall back to Default."
        stored = "?" if self.td_idx is None else self.td_idx
        self.lbl_hint.setText(
            "Use <code>OD({})</code> (OS Dance tab) to place this action in the keymap."
            " Stored as <code>TD({})</code>. {}".format(self.idx, stored, fallback))

    def widget(self):
        return self.w2

    def load(self, data):
        """data は keyboard.tap_dance_get() が返す5要素タプル"""
        objs = [self.kc_mac, self.kc_win, self.kc_linux, self.kc_default]
        for o in objs:
            o.blockSignals(True)

        self.kc_mac.set_keycode(data[0])
        self.kc_win.set_keycode(data[1])
        self.kc_linux.set_keycode(data[2])
        self.kc_default.set_keycode(data[3])
        self.tapping_term = data[4]

        for o in objs:
            o.blockSignals(False)

    def save(self):
        """keyboard.tap_dance_set() に渡す5要素タプル（tapping_term は素通し）"""
        return (
            self.kc_mac.keycode,
            self.kc_win.keycode,
            self.kc_linux.keycode,
            self.kc_default.keycode,
            self.tapping_term
        )

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

    # NOTE: BasicEditor is a QVBoxLayout, so these must not shadow QLayout's own virtual
    # methods (e.g. count()) which Qt calls from C++ while the layout is being reparented.
    def os_dance_base(self):
        return self.keyboard.os_dance["base"]

    def os_dance_count(self):
        """表示するエントリ数。vial.json の count を、UI の上限と Tap Dance の残り枠に丸める"""
        return min(self.keyboard.os_dance["count"],
                   MAX_OS_DANCE_ENTRIES,
                   self.keyboard.tap_dance_count - self.os_dance_base())

    def rebuild_ui(self):
        while self.tabs.count() > 0:
            self.tabs.removeTab(0)
        self.os_dance_entries = self.os_dance_entries_available[:self.os_dance_count()]
        for x, e in enumerate(self.os_dance_entries):
            e.set_td_idx(self.os_dance_base() + x)
            self.tabs.addTab(e.widget(), str(x))
        self.reload_ui()

    def reload_ui(self):
        for x, e in enumerate(self.os_dance_entries):
            e.load(self.keyboard.tap_dance_get(self.os_dance_base() + x))

    def rebuild(self, device):
        super().rebuild(device)
        if self.valid():
            self.keyboard = device.keyboard
            self.rebuild_ui()

    def valid(self):
        if not isinstance(self.device, VialKeyboard):
            return False
        keyboard = self.device.keyboard
        if not keyboard or keyboard.vial_protocol < VIAL_PROTOCOL_DYNAMIC:
            return False
        cfg = getattr(keyboard, "os_dance", None)
        if not isinstance(cfg, dict):
            return False
        base = cfg.get("base")
        count = cfg.get("count")
        if not isinstance(base, int) or not isinstance(count, int):
            return False
        # count が大きすぎる分は count() で丸めるので、ここでは base が枠内にあることだけを見る
        return 0 <= base < keyboard.tap_dance_count and count > 0

    def on_key_changed(self):
        # Combos タブと同じ挙動: キーコード変更は即座にキーボードへ書き込む
        for x, e in enumerate(self.os_dance_entries):
            self.keyboard.tap_dance_set(self.os_dance_base() + x, e.save())
