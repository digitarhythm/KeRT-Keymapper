# SPDX-License-Identifier: GPL-2.0-or-later
"""Keycode picker button for Tap Dance / HostOS entries.

Looks like the editor's card (header with the identifier, one row per field with a read-only key)
so that the right entry can be picked without opening the editor. The whole card is one button:
the children are transparent for mouse events, so clicking anywhere assigns the keycode.
"""
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtWidgets import QGridLayout, QLabel, QVBoxLayout, QWidget

from entry_summary import MACRO_LINES, MACRO_LINE_MAX
from widgets.square_button import SquareButton

# same drawing scale as the editor cards
CARD_KEY_SCALE = 0.7


class EntryCardButton(SquareButton):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.summary = ""
        self.rows = []
        self.lines = []
        self.key_widgets = []
        self.line_labels = []

        self.header = QLabel(self)
        font = self.header.font()
        font.setBold(True)
        self.header.setFont(font)
        self.header.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.grid = QGridLayout()
        self.grid.setVerticalSpacing(3)
        self.body = QWidget(self)
        self.body.setLayout(self.grid)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(3)
        layout.addWidget(self.header)
        layout.addWidget(self.body)
        layout.addStretch()

        for w in (self.header, self.body):
            w.setAttribute(Qt.WA_TransparentForMouseEvents)

    # SquareButton.setText is used by KeycodeDisplay.relabel_buttons for the identifier
    def setText(self, text):
        self.text = text
        self._render_header()

    def setSummary(self, summary):
        self.summary = summary or ""
        self.setToolTip(self.toolTip())

    def set_entry(self, title_extra, rows, lines=()):
        """rows: [(label, qmk_id), ...] drawn as label + key; lines: plain text lines (macro actions);
        title_extra: e.g. "200ms" """
        self.title_extra = title_extra
        if [r[0] for r in rows] != [r[0] for r in self.rows]:
            self._rebuild_rows(rows)
        self.rows = list(rows)
        for kw, (_, qmk_id) in zip(self.key_widgets, rows):
            kw.set_keycode(qmk_id)
        self._set_lines(list(lines))
        self._render_header()
        self.updateGeometry()

    def _set_lines(self, lines):
        if lines != self.lines or len(self.line_labels) != len(lines):
            for lbl in self.line_labels:
                self.grid.removeWidget(lbl)
                lbl.deleteLater()
            self.line_labels = []
            base = len(self.rows)
            for i, text in enumerate(lines):
                lbl = QLabel(text)
                lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
                self.grid.addWidget(lbl, base + i, 0, 1, 2)
                self.line_labels.append(lbl)
        self.lines = lines

    def _rebuild_rows(self, rows):
        # imported here: key_widget imports tabbed_keycodes, which imports this module
        from widgets.key_widget import KeyWidget

        for kw in self.key_widgets:
            kw.deleteLater()
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        self.key_widgets = []
        for r, (label, _) in enumerate(rows):
            lbl = QLabel(label)
            lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
            kw = KeyWidget()
            kw.set_scale(CARD_KEY_SCALE)
            kw.set_enabled(False)
            kw.setAttribute(Qt.WA_TransparentForMouseEvents)
            self.grid.addWidget(lbl, r, 0)
            self.grid.addWidget(kw, r, 1)
            self.key_widgets.append(kw)

    def _render_header(self):
        extra = getattr(self, "title_extra", "")
        self.header.setText("{}  {}".format(self.text, extra) if extra else self.text)

    def sizeHint(self):
        hint = self.layout().sizeHint()
        width, height = hint.width(), hint.height()
        if self.lines:
            # text cards (macros) all get the same rectangle: MACRO_LINES lines of MACRO_LINE_MAX
            # characters under the header, however short the macro is, so the row of cards stays even
            fm = self.fontMetrics()
            m = self.layout().contentsMargins()
            width = max(width, fm.horizontalAdvance("W" * (MACRO_LINE_MAX // 2)) + m.left() + m.right())
            gm = self.grid.contentsMargins()
            line_h = (self.line_labels[0].sizeHint().height() if self.line_labels else fm.height())
            height = m.top() + m.bottom() + self.header.sizeHint().height() + self.layout().spacing() \
                + gm.top() + gm.bottom() + MACRO_LINES * line_h + (MACRO_LINES - 1) * self.grid.verticalSpacing() + 4
            return QSize(width, height)
        side = max(width, height)
        return QSize(side, side)

    def minimumSizeHint(self):
        return self.sizeHint()
