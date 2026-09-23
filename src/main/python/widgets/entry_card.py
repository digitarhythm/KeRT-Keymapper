# SPDX-License-Identifier: GPL-2.0-or-later
"""Card list used by the Tap Dance / HostOS / Combos editors.

All entries are shown at once as cards (instead of one tab per entry) so that their
contents can be read without opening them one by one. The cards are laid out with a
FlowLayout inside a scroll area.
"""
from PyQt5.QtCore import QSize, Qt, QTimer
from PyQt5.QtWidgets import QFrame, QLabel, QScrollArea, QSizePolicy, QStyle, QVBoxLayout, QWidget

from tabbed_keycodes import TabbedKeycodes
from widgets.flowlayout import FlowLayout


class EntryCard(QFrame):
    """One entry: a header line (identifier, and e.g. the tapping term) above the entry's own widget."""

    def __init__(self, body):
        super().__init__()
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)

        self.header = QLabel()
        font = self.header.font()
        font.setBold(True)
        self.header.setFont(font)
        self.header.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        layout = QVBoxLayout()
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(3)
        layout.addWidget(self.header)
        layout.addWidget(body)
        layout.addStretch()
        self.setLayout(layout)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def natural_side(self):
        """Side of the square the content asks for (before the container stretches the width)"""
        hint = super().sizeHint()
        return max(hint.width(), hint.height())

    def sizeHint(self):
        # square cards: the longer side of the content decides both dimensions; the container widens
        # them (setFixedWidth) so that a row fills the available width
        side = self.natural_side()
        return QSize(side, side)

    def minimumSizeHint(self):
        return self.sizeHint()

    def set_title(self, text):
        self.header.setText(text)


class EntryCardContainer(QScrollArea):
    """Scrollable flow of EntryCards. As many cards as fit go on a row, and they are widened equally so
    that every full row spans the whole width (no empty strip at the right). Clicking the empty area
    closes the keycode tray, which is what switching tabs did when the entries were shown in a
    QTabWidget."""

    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.flow = FlowLayout(margin=3, spacing=3)
        self.inner = QWidget()
        self.inner.setLayout(self.flow)
        self.setWidget(self.inner)
        self.cards = []

    def set_cards(self, cards):
        for c in self.cards:
            self.flow.removeWidget(c)
            c.setParent(None)
            c.hide()
        self.cards = list(cards)
        for c in self.cards:
            self.flow.addWidget(c)
            c.show()
        self.fit_cards()
        self.inner.updateGeometry()

    # FlowLayout.doLayout: cards go from rect.x() with spacing() + style layoutSpacing between them, and
    # a card stays on the row while its right edge is <= rect.right() (the margins are not applied)
    def card_gap(self):
        """Horizontal distance between cards, the way FlowLayout lays them out"""
        card = self.cards[0] if self.cards else self
        return self.flow.spacing() + card.style().layoutSpacing(QSizePolicy.PushButton, QSizePolicy.PushButton,
                                                                Qt.Horizontal)

    def row_width(self):
        return self.viewport().width() - 1

    def columns(self):
        """How many cards fit on a row at their natural width"""
        if not self.cards:
            return 0
        side = max(c.natural_side() for c in self.cards)
        return max(1, (self.row_width() + self.card_gap()) // (side + self.card_gap()))

    def fit_cards(self):
        """Widen the cards so that `columns()` of them fill the row exactly"""
        n = self.columns()
        if n == 0:
            return
        width = (self.row_width() - (n - 1) * self.card_gap()) // n
        side = max(c.natural_side() for c in self.cards)
        width = max(width, side)
        for c in self.cards:
            if c.width() != width or c.maximumWidth() != width:
                c.setFixedWidth(width)
        self.flow.invalidate()

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self.fit_cards()
        # the vertical scroll bar appearing or vanishing changes the viewport width once more
        QTimer.singleShot(0, self.fit_cards)

    def mousePressEvent(self, ev):
        TabbedKeycodes.close_tray()
        super().mousePressEvent(ev)
