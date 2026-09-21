# SPDX-License-Identifier: GPL-2.0-or-later
"""Tap Dance / Combos のエントリを人が読める文字列に整形する。

Qt に依存しないので、PyQt5 が無い環境でも単体テストを実行できる。
キー表示名の取得は label_fn として呼び出し側から注入する
(本番では KeycodeDisplay.get_label、テストではダミー関数)。
こうしておくと国別キーマップの上書きにも自動で追従する。
"""

# 空きスロットの表示


def tr(context, text):
    """QT_TRANSLATE_NOOP: marks a string for the translation catalog without translating it.

    This module stays Qt-free; callers that want translated output pass the real translator as ``tr_fn``
    (``util.tr``, i.e. QCoreApplication.translate) and the functions below apply it to the marked strings.
    """
    return text


CONTEXT = "EntrySummary"

EMPTY = "—"

# 空きとみなすキーコード。ファームウェアは KC_TRNS も KC_NO として書き戻すため KC_NO だけでよい
EMPTY_KEYCODES = ("KC_NO",)

# Tap Dance エントリの 4 欄の呼び名
TAP_DANCE_SLOT_LABELS = (tr("EntrySummary", "Tap"), tr("EntrySummary", "Hold"), tr("EntrySummary", "2×Tap"), tr("EntrySummary", "Tap+Hold"))

# 同じ 4 欄を HostOS として読み替えたときの呼び名。
# HostOS では 5 番目の欄が tapping term ではなくシード済みマーカーなので、
# ツールチップを作る際は show_tapping_term=False を渡すこと。
HOST_OS_SLOT_LABELS = (tr("EntrySummary", "Mac"), tr("EntrySummary", "Windows"), tr("EntrySummary", "Linux"), tr("EntrySummary", "Default"))

TAPPING_TERM_LABEL = tr("EntrySummary", "Tapping term")
COMBO_TITLE = tr("EntrySummary", "Combo {}")
COMBO_KEYS_LABEL = tr("EntrySummary", "Keys")
COMBO_OUTPUT_LABEL = tr("EntrySummary", "Output")
MACRO_TAG_LABELS = {"text": tr("EntrySummary", "Text"), "tap": tr("EntrySummary", "Tap"), "down": tr("EntrySummary", "Down"),
                    "up": tr("EntrySummary", "Up"), "delay": tr("EntrySummary", "Delay")}

SUMMARY_SEPARATOR = " / "
COMBO_INPUT_SEPARATOR = " + "
COMBO_ARROW = " → "


def _display(qmk_id, label_fn):
    """キーコード1つを表示名に変換する。空きスロットは EMPTY を返す。"""
    if qmk_id in EMPTY_KEYCODES:
        return EMPTY
    label = label_fn(qmk_id)
    if label is None:
        return EMPTY
    # ラベルは "ᴹᴵᴰᴵ\nCH₁₃" のように改行を含むことがある。1行に収める
    label = " ".join(str(label).split())
    return label if label else EMPTY


def tapping_term(entry):
    """エントリの 5 番目 (custom tapping term) を取り出す。"""
    return entry[4] if len(entry) > 4 else 0


def tap_dance_rows(entry, label_fn, slot_labels=TAP_DANCE_SLOT_LABELS, tr_fn=tr):
    """[(スロット名, キー表示), ...] を返す。スロット名は tr_fn で翻訳する。

    entry は keyboard.tap_dance_get() が返す 5 要素。
    zip で slot_labels 側の長さ (4) に揃うので tapping term は含まれない。
    """
    return [(tr_fn(CONTEXT, name), _display(qmk_id, label_fn)) for name, qmk_id in zip(slot_labels, entry)]


def tap_dance_summary(entry, label_fn, slot_labels=TAP_DANCE_SLOT_LABELS):
    """1行の要約。どの欄が空かが分かるよう、空きスロットも EMPTY で埋める。"""
    return SUMMARY_SEPARATOR.join(value for _, value in tap_dance_rows(entry, label_fn, slot_labels))


def tap_dance_tooltip(entry, label_fn, index=None, slot_labels=TAP_DANCE_SLOT_LABELS,
                      prefix="TD", show_tapping_term=True, tr_fn=tr):
    """ツールチップ用の複数行テキスト。

    index を渡すと "TD(3)" のような見出しが 1 行目に付く。カードのように
    見出しを別に持つ場所では省略できるよう、既定では付けない。
    """
    lines = []
    if index is not None:
        lines.append("{}({})".format(prefix, index))
    for name, value in tap_dance_rows(entry, label_fn, slot_labels, tr_fn):
        lines.append("{}: {}".format(name, value))
    if show_tapping_term:
        lines.append("{}: {} ms".format(tr_fn(CONTEXT, TAPPING_TERM_LABEL), tapping_term(entry)))
    return "\n".join(lines)


def combo_rows(entry, label_fn):
    """([入力キー表示, ...], 出力キー表示) を返す。

    entry は keyboard.combo_get() が返す 5 要素 (入力 4 つ + 出力)。
    使われていない入力スロットは一覧に含めない。
    """
    inputs = [_display(qmk_id, label_fn) for qmk_id in entry[:4] if qmk_id not in EMPTY_KEYCODES]
    output = _display(entry[4], label_fn) if len(entry) > 4 else EMPTY
    return inputs, output


def combo_summary(entry, label_fn):
    """1行の要約。例: "A + B → Esc" """
    inputs, output = combo_rows(entry, label_fn)
    if not inputs:
        # 入力が 1 つも無いコンボは発火しないので、未設定として扱う
        return EMPTY
    return COMBO_INPUT_SEPARATOR.join(inputs) + COMBO_ARROW + output


def combo_tooltip(entry, label_fn, index=None, tr_fn=tr):
    """コンボ1件のツールチップ用テキスト。"""
    lines = []
    if index is not None:
        lines.append(tr_fn(CONTEXT, COMBO_TITLE).format(index))
    inputs, output = combo_rows(entry, label_fn)
    lines.append("{}: {}".format(tr_fn(CONTEXT, COMBO_KEYS_LABEL), COMBO_INPUT_SEPARATOR.join(inputs) if inputs else EMPTY))
    lines.append("{}: {}".format(tr_fn(CONTEXT, COMBO_OUTPUT_LABEL), output))
    return "\n".join(lines)


def build_entry_tooltips(entries, host_os_base, host_os_count, label_fn, tr_fn=tr):
    """Tap Dance スロット全体から {qmk_id: ツールチップ} を作る。

    HostOS はスロットの後半 (host_os_base 以降の host_os_count 個) を間借りしており、
    配線上の id は TD(x) のままなので、辞書のキーはどちらも "TD(x)" で揃う。
    HostOS 側は OS 名で読み替え、5 番目はシード済みマーカーなので
    Tapping term としては表示しない。

    keyboard.reload_tap_dance() の後に呼ぶこと。それ以前は entries が空で、
    その場合は空の辞書を返す。
    """
    tooltips = {}
    host_os_end = host_os_base + host_os_count
    for idx, entry in enumerate(entries):
        qmk_id = "TD({})".format(idx)
        if host_os_base <= idx < host_os_end:
            tooltips[qmk_id] = tap_dance_tooltip(
                entry, label_fn,
                index=idx - host_os_base, prefix="HOS",
                slot_labels=HOST_OS_SLOT_LABELS, show_tapping_term=False, tr_fn=tr_fn,
            )
        else:
            tooltips[qmk_id] = tap_dance_tooltip(entry, label_fn, tr_fn=tr_fn)
    return tooltips


# Macro cards: how many actions to show and how long a line may get
MACRO_LINES = 4
MACRO_LINE_MAX = 24
MACRO_ELLIPSIS = "\u2026"


def _shorten(text):
    if len(text) <= MACRO_LINE_MAX:
        return text
    return text[:MACRO_LINE_MAX - 1] + MACRO_ELLIPSIS


def macro_action_line(action, label_fn, tr_fn=tr):
    """One macro action as a short line: "Text: Hello", "Tap: A + B", "Delay: 100 ms"."""
    tag = getattr(action, "tag", "")
    if tag == "text":
        body = action.text
    elif tag in ("tap", "down", "up"):
        body = COMBO_INPUT_SEPARATOR.join(_display(kc, label_fn) for kc in action.sequence) or EMPTY
    elif tag == "delay":
        body = "{} ms".format(action.delay)
    else:
        body = EMPTY
    return _shorten("{}: {}".format(tr_fn(CONTEXT, MACRO_TAG_LABELS.get(tag, tag.capitalize())), body))


def macro_lines(actions, label_fn, limit=MACRO_LINES, tr_fn=tr):
    """The first `limit` actions of a macro as lines; an empty macro is a single EMPTY line."""
    if not actions:
        return [EMPTY]
    return [macro_action_line(a, label_fn, tr_fn) for a in list(actions)[:limit]]
