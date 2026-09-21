# SPDX-License-Identifier: GPL-2.0-or-later
"""entry_summary の単体テスト。

entry_summary は Qt に依存しない純粋な整形モジュールなので、PyQt5 が無い環境でも
このテストは実行できる。キー表示名の取得は label_fn として注入する。
"""
import unittest

from macro.macro_action import ActionDelay, ActionDown, ActionTap, ActionText, ActionUp

from entry_summary import (
    EMPTY,
    macro_lines,
    HOST_OS_SLOT_LABELS,
    TAP_DANCE_SLOT_LABELS,
    build_entry_tooltips,
    combo_rows,
    combo_summary,
    combo_tooltip,
    tap_dance_rows,
    tap_dance_summary,
    tap_dance_tooltip,
)


def fake_label(qmk_id):
    """KeycodeDisplay.get_label の代役。テスト用に固定の表示名を返す。"""
    return {
        "KC_A": "A",
        "KC_B": "B",
        "KC_C": "C",
        "KC_ESC": "Esc",
        "KC_LSFT": "⇧",
        "KC_NO": "",
        "MI_CH13": "ᴹᴵᴰᴵ\nCH₁₃",
    }.get(qmk_id, qmk_id)


class TestTapDanceSummary(unittest.TestCase):

    def test_rows_all_slots_filled(self):
        """4スロットすべて設定済みなら、スロット名と表示名の対が順に返る"""
        entry = ("KC_A", "KC_LSFT", "KC_B", "KC_C", 200)
        self.assertEqual(
            tap_dance_rows(entry, fake_label),
            [("Tap", "A"), ("Hold", "⇧"), ("2×Tap", "B"), ("Tap+Hold", "C")],
        )

    def test_rows_empty_slot_becomes_placeholder(self):
        """KC_NO のスロットは EMPTY に置き換わる"""
        entry = ("KC_A", "KC_NO", "KC_NO", "KC_C", 200)
        self.assertEqual(
            tap_dance_rows(entry, fake_label),
            [("Tap", "A"), ("Hold", EMPTY), ("2×Tap", EMPTY), ("Tap+Hold", "C")],
        )

    def test_rows_use_host_os_slot_labels(self):
        """HostOS は同じ構造を OS 名で読み替える"""
        entry = ("KC_A", "KC_B", "KC_C", "KC_ESC", 0)
        self.assertEqual(
            [name for name, _ in tap_dance_rows(entry, fake_label, HOST_OS_SLOT_LABELS)],
            ["Mac", "Windows", "Linux", "Default"],
        )

    def test_default_slot_labels(self):
        """既定のスロット名は Tap Dance のもの"""
        self.assertEqual(TAP_DANCE_SLOT_LABELS, ("Tap", "Hold", "2×Tap", "Tap+Hold"))

    def test_summary_is_single_line(self):
        """要約は1行。空きスロットも位置が分かるよう EMPTY で埋める"""
        entry = ("KC_A", "KC_LSFT", "KC_B", "KC_NO", 200)
        self.assertEqual(tap_dance_summary(entry, fake_label), "A / ⇧ / B / " + EMPTY)

    def test_summary_all_empty(self):
        """未設定のエントリは空きスロットだけの要約になる"""
        entry = ("KC_NO", "KC_NO", "KC_NO", "KC_NO", 200)
        expected = " / ".join([EMPTY] * 4)
        self.assertEqual(tap_dance_summary(entry, fake_label), expected)

    def test_tooltip_contains_all_slots_and_term(self):
        """ツールチップには全スロットと Tapping term が入る"""
        entry = ("KC_A", "KC_LSFT", "KC_B", "KC_NO", 180)
        tooltip = tap_dance_tooltip(entry, fake_label)
        for fragment in ("Tap", "A", "Hold", "⇧", "2×Tap", "B", "Tap+Hold", EMPTY, "180"):
            self.assertIn(fragment, tooltip)

    def test_tooltip_header_with_index(self):
        """index を渡すと TD(n) の見出しが1行目に付く"""
        entry = ("KC_A", "KC_NO", "KC_NO", "KC_NO", 200)
        self.assertEqual(tap_dance_tooltip(entry, fake_label, index=3).splitlines()[0], "TD(3)")

    def test_tooltip_without_index_has_no_header(self):
        """index を渡さなければ見出しは付かない"""
        entry = ("KC_A", "KC_NO", "KC_NO", "KC_NO", 200)
        self.assertNotIn("TD(", tap_dance_tooltip(entry, fake_label))


class TestComboSummary(unittest.TestCase):

    def test_rows_returns_inputs_and_output(self):
        """入力キーの一覧と出力キーを返す。空きの入力は含めない"""
        entry = ("KC_A", "KC_B", "KC_NO", "KC_NO", "KC_ESC")
        self.assertEqual(combo_rows(entry, fake_label), (["A", "B"], "Esc"))

    def test_summary_two_inputs(self):
        """入力2個。未使用スロットは連結から除外される"""
        entry = ("KC_A", "KC_B", "KC_NO", "KC_NO", "KC_ESC")
        self.assertEqual(combo_summary(entry, fake_label), "A + B → Esc")

    def test_summary_four_inputs(self):
        """入力4個はすべて連結される"""
        entry = ("KC_A", "KC_B", "KC_C", "KC_ESC", "KC_LSFT")
        self.assertEqual(combo_summary(entry, fake_label), "A + B + C + Esc → ⇧")

    def test_summary_no_inputs_is_empty(self):
        """入力が全て空のコンボは発火しないので、要約は空き表示のみ"""
        entry = ("KC_NO", "KC_NO", "KC_NO", "KC_NO", "KC_ESC")
        self.assertEqual(combo_summary(entry, fake_label), EMPTY)

    def test_summary_empty_output(self):
        """出力が空なら → の後ろが空き表示になる"""
        entry = ("KC_A", "KC_B", "KC_NO", "KC_NO", "KC_NO")
        self.assertEqual(combo_summary(entry, fake_label), "A + B → " + EMPTY)


class TestLabelHandling(unittest.TestCase):

    def test_label_fn_is_used(self):
        """表示名の決定は label_fn に委ねる（国別キーマップの上書きに追従するため）"""
        calls = []

        def spy(qmk_id):
            calls.append(qmk_id)
            return "<{}>".format(qmk_id)

        entry = ("KC_A", "KC_NO", "KC_NO", "KC_NO", 200)
        rows = tap_dance_rows(entry, spy)

        self.assertEqual(rows[0], ("Tap", "<KC_A>"))
        self.assertIn("KC_A", calls)

    def test_newline_in_label_becomes_space(self):
        """ラベル内の改行は空白に置換する（1行表示が崩れるのを防ぐ）"""
        entry = ("MI_CH13", "KC_NO", "KC_NO", "KC_NO", 200)
        self.assertEqual(tap_dance_rows(entry, fake_label)[0], ("Tap", "ᴹᴵᴰᴵ CH₁₃"))
        self.assertNotIn("\n", tap_dance_summary(entry, fake_label))


class TestComboTooltip(unittest.TestCase):

    def test_tooltip_lists_keys_and_output(self):
        """ツールチップには入力キーと出力キーが入る"""
        entry = ("KC_A", "KC_B", "KC_NO", "KC_NO", "KC_ESC")
        tooltip = combo_tooltip(entry, fake_label)
        self.assertIn("A + B", tooltip)
        self.assertIn("Esc", tooltip)

    def test_tooltip_header_with_index(self):
        """index を渡すと見出しが1行目に付く"""
        entry = ("KC_A", "KC_B", "KC_NO", "KC_NO", "KC_ESC")
        self.assertEqual(combo_tooltip(entry, fake_label, index=1).splitlines()[0], "Combo 1")

    def test_tooltip_no_inputs(self):
        """入力が無くてもツールチップは壊れない"""
        entry = ("KC_NO", "KC_NO", "KC_NO", "KC_NO", "KC_NO")
        self.assertIn(EMPTY, combo_tooltip(entry, fake_label))


class TestBuildEntryTooltips(unittest.TestCase):
    """Tap Dance スロットの後半を HostOS が間借りする構成を扱えること"""

    ENTRIES = [
        ("KC_A", "KC_LSFT", "KC_NO", "KC_NO", 200),      # 0: Tap Dance
        ("KC_ESC", "KC_NO", "KC_NO", "KC_NO", 180),      # 1: Tap Dance
        ("KC_A", "KC_B", "KC_C", "KC_ESC", 0x4F53),      # 2: HostOS 0
        ("KC_NO", "KC_NO", "KC_NO", "KC_NO", 0x4F53),    # 3: HostOS 1
    ]

    def build(self, host_os_base=2, host_os_count=2, entries=None):
        entries = self.ENTRIES if entries is None else entries
        return build_entry_tooltips(entries, host_os_base, host_os_count, fake_label)

    def test_keys_are_tap_dance_qmk_ids(self):
        """HostOS のスロットも配線上は TD(x) なので、キーは TD(x) で揃う"""
        self.assertEqual(sorted(self.build()), ["TD(0)", "TD(1)", "TD(2)", "TD(3)"])

    def test_tap_dance_slot_has_tapping_term(self):
        """前半の Tap Dance スロットは Tapping term を含む"""
        tooltip = self.build()["TD(0)"]
        self.assertIn("Tap: A", tooltip)
        self.assertIn("Hold: ⇧", tooltip)
        self.assertIn("200", tooltip)

    def test_host_os_slot_uses_os_labels(self):
        """後半の HostOS スロットは OS 名で表示される"""
        tooltip = self.build()["TD(2)"]
        self.assertIn("Mac: A", tooltip)
        self.assertIn("Windows: B", tooltip)
        self.assertIn("Linux: C", tooltip)
        self.assertIn("Default: Esc", tooltip)

    def test_host_os_slot_hides_tapping_term(self):
        """HostOS の5番目はシード済みマーカーなので Tapping term として出さない"""
        tooltip = self.build()["TD(2)"]
        self.assertNotIn("Tapping term", tooltip)
        self.assertNotIn(str(0x4F53), tooltip)

    def test_host_os_slot_header_is_alias(self):
        """HostOS スロットの見出しは HOS(n)。n は base からの相対番号"""
        self.assertEqual(self.build()["TD(2)"].splitlines()[0], "HOS(0)")
        self.assertEqual(self.build()["TD(3)"].splitlines()[0], "HOS(1)")

    def test_without_host_os_every_slot_is_tap_dance(self):
        """HostOS が無効なら全スロットが Tap Dance として扱われる"""
        tooltips = self.build(host_os_base=4, host_os_count=0)
        self.assertNotIn("Mac", tooltips["TD(2)"])
        self.assertIn("Tapping term", tooltips["TD(2)"])

    def test_empty_entries(self):
        """未読み込みの状態では空の辞書を返す"""
        self.assertEqual(self.build(entries=[]), {})

    def test_fewer_entries_than_declared(self):
        """宣言より実エントリが少なくても、ある分だけ返す"""
        tooltips = self.build(entries=self.ENTRIES[:3])
        self.assertEqual(sorted(tooltips), ["TD(0)", "TD(1)", "TD(2)"])


if __name__ == "__main__":
    unittest.main()


class TestMacroLines(unittest.TestCase):

    def test_first_four_actions(self):
        actions = [ActionText("Hello"), ActionTap(["KC_A", "KC_B"]), ActionDelay(100),
                   ActionDown(["KC_LSFT"]), ActionUp(["KC_LSFT"])]
        self.assertEqual(macro_lines(actions, fake_label),
                         ["Text: Hello", "Tap: A + B", "Delay: 100 ms", "Down: \u21e7"])

    def test_empty_macro(self):
        self.assertEqual(macro_lines([], fake_label), [EMPTY])

    def test_long_text_is_truncated(self):
        lines = macro_lines([ActionText("x" * 40)], fake_label)
        self.assertEqual(len(lines), 1)
        self.assertLessEqual(len(lines[0]), 24)
        self.assertTrue(lines[0].endswith("\u2026"))
