# SPDX-License-Identifier: GPL-2.0-or-later
from functools import partial

from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import QWidget, QSizePolicy, QGridLayout, QVBoxLayout, QLabel

from protocol.constants import VIAL_PROTOCOL_DYNAMIC
from widgets.key_widget import KeyWidget
from vial_device import VialKeyboard
from editor.basic_editor import BasicEditor
from widgets.entry_card import EntryCard, EntryCardContainer
import entry_labels

# 事前生成するエントリUIの上限
MAX_HOST_OS_ENTRIES = 32

# キーの描画倍率。カード内では通常より小さく描いて行間を詰める
CARD_KEY_SCALE = 0.7

# Tap Dance エントリの 5 番目 (custom_tapping_term) に書く「シード済み」マーカー ("OS")。
# ファームウェアは、4 欄がすべて空でこのマーカーが無いスロットにだけ起動時に既定値を書き込む。
# 保存時に必ず書いておけば、ユーザーが意図的に全欄を空にしても再シードされない。
HOST_OS_MARKER = 0x4F53


class HostOSEntryUI(QObject):
    """1エントリ分のフォーム。

    実体は Tap Dance エントリ (tap, hold, double_tap, tap_hold, tapping_term) で、
    ファームウェアはそれを OS ごとのキーコード表として読む:
        on tap        -> Mac (iOS も)
        on hold       -> Win
        on double tap -> Linux (ChromeOS も)
        on tap + hold -> Default (判別不能時、および該当欄が空のときのフォールバック)
    キーマップには TD(base + idx) を置く。GUI 上ではそれを HOS(idx) と表示する。
    """

    key_changed = pyqtSignal()

    def __init__(self, idx):
        super().__init__()

        self.idx = idx          # HostOS 内での通し番号 (0..count-1)
        self.td_idx = None      # 実際に読み書きする Tap Dance スロット (base + idx)
        self.container = QGridLayout()
        self.populate_container()

        w = QWidget()
        w.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        w.setLayout(self.container)
        l = QVBoxLayout()
        l.setContentsMargins(0, 0, 0, 0)
        l.addWidget(w)
        l.setAlignment(w, QtCore.Qt.AlignHCenter)
        self.w2 = QWidget()
        self.w2.setLayout(l)

    def populate_container(self):
        self.container.setVerticalSpacing(3)
        self.kc_fields = []
        for row, label in enumerate(["Mac", "Win", "Linux", "Default"]):
            self.container.addWidget(QLabel(label), row, 0)
            kc = KeyWidget()
            kc.set_scale(CARD_KEY_SCALE)
            kc.changed.connect(self.on_key_changed)
            self.container.addWidget(kc, row, 1)
            self.kc_fields.append(kc)

    def set_td_idx(self, td_idx):
        self.td_idx = td_idx

    def widget(self):
        return self.w2

    def load(self, data):
        """data は keyboard.tap_dance_get() が返す 5 要素タプル"""
        for kc in self.kc_fields:
            kc.blockSignals(True)
        for kc, value in zip(self.kc_fields, data[:4]):
            kc.set_keycode(value)
        for kc in self.kc_fields:
            kc.blockSignals(False)

    def save(self):
        """keyboard.tap_dance_set() に渡す 5 要素タプル。空欄は KC_NO、5 番目はマーカー"""
        return tuple("KC_NO" if kc.keycode == "KC_TRNS" else kc.keycode for kc in self.kc_fields) + (HOST_OS_MARKER,)

    def on_key_changed(self):
        self.key_changed.emit()


class HostOS(BasicEditor):

    def __init__(self):
        super().__init__()
        self.keyboard = None

        self.host_os_entries = []
        self.host_os_entries_available = []
        self.cards_available = []
        self.cards = []
        self.container = EntryCardContainer()
        for x in range(MAX_HOST_OS_ENTRIES):
            entry = HostOSEntryUI(x)
            entry.key_changed.connect(partial(self.on_key_changed, x))
            self.host_os_entries_available.append(entry)
            card = EntryCard(entry.widget())
            card.set_title("HOS({})".format(x))
            self.cards_available.append(card)

        self.hint = QLabel()
        self.hint.setWordWrap(True)
        self.addWidget(self.hint)
        self.addWidget(self.container)

    # NOTE: BasicEditor is a QVBoxLayout, so method names here must not shadow QLayout's own
    # virtual methods (e.g. count()) which Qt calls from C++ while the layout is being reparented.
    def host_os_base(self):
        return self.keyboard.host_os_base

    def rebuild_ui(self):
        shown = min(self.keyboard.host_os_count, MAX_HOST_OS_ENTRIES)
        self.host_os_entries = self.host_os_entries_available[:shown]
        self.cards = self.cards_available[:shown]
        for x, e in enumerate(self.host_os_entries):
            e.set_td_idx(self.host_os_base() + x)
            self.cards[x].set_title("HOS({})".format(x))
        self.hint.setText(
            "Use <code>HOS(n)</code> (HostOS tab) to place a HostOS key in the keymap."
            " Leave a field empty to fall back to Default.")
        self.container.set_cards(self.cards)
        self.reload_ui()

    def reload_ui(self):
        for x, e in enumerate(self.host_os_entries):
            e.load(self.keyboard.tap_dance_get(self.host_os_base() + x))

    def rebuild(self, device):
        super().rebuild(device)
        if self.valid():
            self.keyboard = device.keyboard
            self.rebuild_ui()

    def valid(self):
        return isinstance(self.device, VialKeyboard) and \
               (self.device.keyboard and self.device.keyboard.vial_protocol >= VIAL_PROTOCOL_DYNAMIC
                and self.device.keyboard.host_os_count > 0)

    def on_key_changed(self, x):
        # Tap Dance / Combos と同じ挙動: 変更されたエントリだけを即座にキーボードへ書き込む
        if x >= len(self.host_os_entries):
            return
        e = self.host_os_entries[x]
        self.keyboard.tap_dance_set(self.host_os_base() + x, e.save())
        # 書き込んだ値（KC_TRNS -> KC_NO の正規化後）を表示に反映する
        e.load(self.keyboard.tap_dance_get(self.host_os_base() + x))
        entry_labels.update(self.keyboard)
