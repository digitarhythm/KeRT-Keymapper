#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""実機のキーボードなしで GUI を起動する開発用ランチャ。

test_gui.py の VirtualKeyboard (HID プロトコルを模擬する) をそのまま使い、
hidraw のデバイス列挙を差し替えて仮想キーボードを1台繋いだ状態で MainWindow を出す。
Tap Dance / HostOS / Combos の各タブを実際に触って確認できる。

    PYTHONPATH=src/main/python python util/dev/run_virtual_keyboard.py

テスト専用のため配布物には含めない。
"""
import os
import sys

_HERE = os.path.dirname(os.path.realpath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, os.path.join(_ROOT, "src", "main", "python"))

from PyQt5 import QtWidgets  # noqa: E402

from test.test_gui import (  # noqa: E402
    FAKE_KEYBOARD_HOST_OS,
    HOST_OS_MARKER,
    FakeAppctx,
    MockDevice,
    VirtualKeyboard,
    mock_enumerate,
)

# QMK の基本キーコード
KC_A, KC_B, KC_E, KC_Q, KC_R, KC_W, KC_X = 0x04, 0x05, 0x08, 0x14, 0x15, 0x1A, 0x1B
KC_ESC, KC_LSFT = 0x29, 0xE1
KC_NO = 0x00

# FAKE_KEYBOARD_HOST_OS は hostOS.count = 2 なので、
# 後ろ2スロット (2, 3) が HostOS、前の2スロット (0, 1) が通常の Tap Dance になる
TAP_DANCE = [
    [KC_A, KC_LSFT, KC_B, KC_NO, 200],              # 0: Tap Dance
    [KC_ESC, KC_NO, KC_NO, KC_NO, 180],             # 1: Tap Dance (Tap のみ)
    [KC_Q, KC_W, KC_E, KC_R, HOST_OS_MARKER],       # 2: HostOS 0 (Mac/Win/Linux/Default)
    [KC_NO, KC_NO, KC_NO, KC_X, HOST_OS_MARKER],    # 3: HostOS 1 (Default のみ)
]

COMBOS = [
    [KC_A, KC_B, KC_NO, KC_NO, KC_ESC],             # A + B -> Esc
    [KC_Q, KC_W, KC_E, KC_NO, KC_LSFT],             # Q + W + E -> LShift
    [KC_NO, KC_NO, KC_NO, KC_NO, KC_NO],            # 未設定
]


def main():
    import hidraw as hid
    from main_window import MainWindow

    vk = VirtualKeyboard(FAKE_KEYBOARD_HOST_OS, combos=COMBOS, tap_dance=TAP_DANCE)
    MockDevice.vk = vk
    hid.enumerate = mock_enumerate
    hid.device = MockDevice

    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow(FakeAppctx())
    window.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
