# SPDX-License-Identifier: GPL-2.0-or-later

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtWidgets import QPushButton, QLabel, QHBoxLayout, QApplication

class SquareButton(QPushButton):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.scale = 1.2
        self.width_factor = 1
        # room for the themed outline (see branding_theme / key_style); 0 keeps upstream's size
        self.frame_extra = 0
        self.label = None
        self.word_wrap = False
        self.text = ""

    def setRelSize(self, ratio):
        self.scale = ratio
        self.updateGeometry()

    def setFontDelta(self, delta):
        """ Use a font `delta` points larger (or smaller, if negative) than the application default """
        font = self.font()
        font.setPointSize(max(1, QApplication.font().pointSize() + delta))
        self.setFont(font)
        self.updateGeometry()

    def setWidthFactor(self, factor):
        """ Make the button `factor` times wider than it is tall (1 = square) """
        self.width_factor = factor
        self.updateGeometry()

    def setWordWrap(self, state):
        self.word_wrap = state
        self.setText(self.text)

    def sizeHint(self):
        size = int(round(self.fontMetrics().height() * self.scale)) + 2 * self.frame_extra
        return QSize(int(round(size * self.width_factor)), size)

    # Override setText to facilitate automatic word wrapping
    def setText(self, text):
        self.text = text
        if self.word_wrap:
            super().setText("")
            if self.label is None:
                self.label = QLabel(text, self)
                self.label.setWordWrap(True)
                self.label.setAlignment(Qt.AlignCenter)
                layout = QHBoxLayout(self)
                layout.setContentsMargins(0, 0, 0, 0)
                layout.addWidget(self.label,0,Qt.AlignCenter)
            else:
                self.label.setText(text)
        else:
            if self.label is not None:
                self.label.hide()
                self.label.deleteLater()
            super().setText(text)