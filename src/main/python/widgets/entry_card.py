# SPDX-License-Identifier: GPL-2.0-or-later
"""Card list used by the Tap Dance / HostOS / Combos editors.

All entries are shown at once as cards (instead of one tab per entry) so that their
contents can be read without opening them one by one. The cards are laid out with a
FlowLayout inside a scroll area.
"""
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtWidgets import QFrame, QLabel, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

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

    def sizeHint(self):
        # square cards: the longer side of the content decides both dimensions
        hint = super().sizeHint()
        side = max(hint.width(), hint.height())
        return QSize(side, side)

    def minimumSizeHint(self):
        return self.sizeHint()

    def set_title(self, text):
        self.header.setText(text)


class EntryCardContainer(QScrollArea):
    """Scrollable flow of EntryCards. Clicking the empty area closes the keycode tray, which is what
    switching tabs did when the entries were shown in a QTabWidget."""

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
        self.inner.updateGeometry()

    def mousePressEvent(self, ev):
        TabbedKeycodes.close_tray()
        super().mousePressEvent(ev)
