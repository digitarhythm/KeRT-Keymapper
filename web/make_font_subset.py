#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Build web/src/fonts/kert-ja.otf: the glyphs the browser version needs for Japanese.

The WebAssembly build of Qt has no access to system fonts and ships only Latin ones, so every Japanese
character is a box unless a font is bundled. A full Japanese font is 16 MB; this subset of Noto Sans CJK
JP (OFL 1.1, see src/fonts/OFL.txt) keeps the characters used by the UI translations plus ASCII, kana,
full-width punctuation and a few symbols, and is about 250 KB.

Re-run after changing a translation catalog:

    pip install fonttools
    curl -L -o /tmp/NotoSansCJKjp-Regular.otf \\
        https://github.com/notofonts/noto-cjk/raw/main/Sans/OTF/Japanese/NotoSansCJKjp-Regular.otf
    python3 web/make_font_subset.py /tmp/NotoSansCJKjp-Regular.otf

test_i18n.py checks that the committed subset covers the current catalogs.
"""
import glob
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
TRANSLATIONS = os.path.join(HERE, "..", "src", "main", "resources", "base", "translations")
OUTPUT = os.path.join(HERE, "src", "fonts", "kert-ja.otf")

# always included, whatever the catalogs contain
FIXED_RANGES = [
    (0x0020, 0x007E),   # ASCII
    (0x00A0, 0x00FF),   # Latin-1 punctuation and symbols
    (0x3000, 0x303F),   # CJK punctuation
    (0x3041, 0x30FF),   # hiragana, katakana
    (0xFF01, 0xFF5E),   # full-width ASCII
]
FIXED_CHARS = "—–…‥・×÷°±→←↑↓✓■□●○◎△▽"


def catalog_chars(translations_dir=TRANSLATIONS):
    chars = set()
    for path in glob.glob(os.path.join(translations_dir, "*.ts")):
        for ctx in ET.parse(path).getroot().findall("context"):
            for msg in ctx.findall("message"):
                for tag in ("source", "translation"):
                    chars |= set(msg.findtext(tag) or "")
    return chars


def needed_chars(translations_dir=TRANSLATIONS):
    chars = catalog_chars(translations_dir) | set(FIXED_CHARS)
    for lo, hi in FIXED_RANGES:
        chars |= {chr(c) for c in range(lo, hi + 1)}
    return {c for c in chars if not c.isspace() or c == " "}


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    chars = needed_chars()
    text_file = OUTPUT + ".chars.txt"
    with open(text_file, "w", encoding="utf-8") as outf:
        outf.write("".join(sorted(chars)))
    subprocess.check_call([sys.executable, "-m", "fontTools.subset", argv[1], "--text-file=" + text_file,
                           "--output-file=" + OUTPUT, "--layout-features=*", "--no-hinting", "--desubroutinize"])
    os.remove(text_file)
    print("{}: {} characters, {} bytes".format(OUTPUT, len(chars), os.path.getsize(OUTPUT)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
