# SPDX-License-Identifier: GPL-2.0-or-later
"""Entry cards (Tap Dance / HostOS / Combos): as many per row as fit, widened so a row spans the full
width of the editor (docs/theme-flat-keys-spec.md §4.8)."""
from PyQt5.QtWidgets import QLabel

from widgets.entry_card import EntryCard, EntryCardContainer


def make_cards(n, w=150, h=100):
    cards = []
    for i in range(n):
        body = QLabel("entry %d" % i)
        body.setFixedSize(w, h)
        card = EntryCard(body)
        card.set_title("TD(%d)" % i)
        cards.append(card)
    return cards


def row_of(cards):
    """The cards on the first row (same y as the first card)"""
    y = cards[0].y()
    return [c for c in cards if c.y() == y]


def test_cards_fill_the_row(qtbot):
    box = EntryCardContainer()
    qtbot.addWidget(box)
    box.resize(1000, 500)
    box.show()
    cards = make_cards(12)
    box.set_cards(cards)
    qtbot.waitUntil(lambda: cards[-1].isVisible() and cards[0].width() > 0 and box.viewport().width() > 900)
    qtbot.waitUntil(lambda: row_of(cards)[-1].geometry().right() >= box.viewport().width() - 10)

    row = row_of(cards)
    side = cards[0].natural_side()
    assert len(row) == (box.row_width() + box.card_gap()) // (side + box.card_gap()) >= 4
    assert len(set(c.width() for c in cards)) == 1, "all cards the same width"
    assert cards[0].width() > side, "wider than the natural square"
    assert 0 <= box.row_width() - row[-1].geometry().right() <= len(row), "row spans the width"
    assert cards[0].height() == side, "the height stays the natural one"


def test_cards_refit_on_resize(qtbot):
    box = EntryCardContainer()
    qtbot.addWidget(box)
    box.resize(1000, 500)
    box.show()
    cards = make_cards(12)
    box.set_cards(cards)
    qtbot.waitUntil(lambda: cards[-1].isVisible() and box.viewport().width() > 900)
    before = len(row_of(cards))

    box.resize(620, 500)
    qtbot.waitUntil(lambda: box.viewport().width() < 650 and len(row_of(cards)) < before
                    and box.row_width() - row_of(cards)[-1].geometry().right() <= len(row_of(cards)))
    row = row_of(cards)
    assert 0 <= box.row_width() - row[-1].geometry().right() <= len(row)


def picker_cards(qtbot, n, width):
    """An AlternativeDisplay (no display keyboard) holding n Tap Dance style card buttons, inside a scroll
    area of the given width"""
    from PyQt5.QtWidgets import QScrollArea
    from tabbed_keycodes import AlternativeDisplay
    from widgets.entry_card_button import EntryCardButton

    disp = AlternativeDisplay(None, [], None)
    cards = []
    for i in range(n):
        b = EntryCardButton()
        b.setText("TD(%d)" % i)
        b.set_entry("200ms", [("On tap", "KC_A"), ("On hold", "KC_LSFT"), ("On double tap", "KC_B"), ("On tap + hold", "KC_C")])
        disp.key_layout.addWidget(b)
        disp.buttons.append(b)
        cards.append(b)
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setWidget(disp)
    qtbot.addWidget(area)
    area.resize(width, 600)
    area.show()
    qtbot.waitUntil(lambda: area.viewport().width() > width - 60)   # themed frame + scroll bar
    disp.update_block_width()
    return area, disp, cards


def test_picker_cards_fill_rows_when_wrapping(qtbot):
    area, disp, cards = picker_cards(qtbot, 12, 1000)
    natural = cards[0].sizeHint().width()
    assert disp.flow_row_width() > disp.available_width(), "12 cards do not fit on one row: they wrap"
    qtbot.waitUntil(lambda: disp.block.width() == disp.available_width() and cards[0].width() > natural)
    qtbot.waitUntil(lambda: row_of(cards)[-1].geometry().right() >= disp.block.width() - 20)
    row = row_of(cards)
    assert len(set(c.width() for c in cards)) == 1
    assert 0 <= (disp.block.width() - 1) - row[-1].geometry().right() <= len(row), "the row spans the block"
    assert cards[0].height() == cards[0].sizeHint().height()


def test_picker_cards_keep_natural_width_on_one_row(qtbot):
    area, disp, cards = picker_cards(qtbot, 3, 1400)
    natural = cards[0].sizeHint().width()
    assert disp.flow_row_width() <= disp.available_width()
    qtbot.waitUntil(lambda: cards[0].width() == natural)
    assert disp.block.width() < disp.available_width(), "the block is only as wide as the row, centred"


def test_picker_cards_stay_within_the_wrap_width(qtbot):
    """Card tabs keep the picker's wrap width (window height in landscape windows, §4.5): the cards
    fill the rows of that block, and the block stays centred"""
    area, disp, cards = picker_cards(qtbot, 12, 1000)
    disp.set_wrap_width(600)
    qtbot.waitUntil(lambda: disp.block.width() == 600)
    qtbot.waitUntil(lambda: row_of(cards)[-1].geometry().right() >= 600 - 20)
    row = row_of(cards)
    assert 0 <= 599 - row[-1].geometry().right() <= len(row)
    qtbot.waitUntil(lambda: abs(disp.block.x() - (disp.width() - 600) / 2) < 5)   # centred
