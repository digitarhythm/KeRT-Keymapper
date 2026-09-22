# SPDX-License-Identifier: GPL-2.0-or-later
"""Static checks on the browser start page (web/src/index.html): the loading spinner while a chosen
keyboard connects is a large one centred over the selection card (docs/web-start-page-spec.md)."""
import os
import re

PAGE = os.path.realpath(os.path.join(os.path.dirname(__file__), "../../../../web/src/index.html"))


def page():
    with open(PAGE, encoding="utf-8") as f:
        return f.read()


def css_block(html, selector):
    m = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", html)
    assert m, selector
    return re.sub(r"\s+", "", m.group(1))


def test_big_spinner_centred_in_card():
    html = page()
    # the spinner element lives directly in the card, so it is centred on the card, not on a box
    assert re.search(r'<div id="startup_inner">.*<div id="big_spinner"></div>.*</div>\s*<div id="version">',
                     html, re.S)
    assert "position:relative" in css_block(html, "#startup_inner")
    css = css_block(html, "#big_spinner")
    assert "position:absolute" in css and "left:50%" in css and "top:50%" in css
    w = re.search(r"width:([\d.]+)em", css)
    assert w and float(w.group(1)) >= 4, "a large spinner (at least 4em)"
    assert "animation:kert-spin" in css
    assert "display:none" in css and "display:block" in css_block(html, "#big_spinner.shown")


def test_big_spinner_follows_busy_state():
    html = page()
    fn = html[html.index("function set_known_status"):html.index("function select_box")]
    assert 'getElementById("big_spinner").classList.toggle("shown", !!busy)' in fn


def test_no_small_spinner_over_the_name():
    html = page()
    fn = html[html.index("function select_box"):html.index("var Module")]
    assert "spinner" not in fn, "the chosen box only turns green; the spinner is the big one on the card"
    assert ".known_name.selected .spinner" not in html


def test_other_keyboard_button_says_connect():
    """The button under the known-keyboard list reads "connect another keyboard" (ja / en)"""
    html = page()
    assert 'other: "別のキーボードを接続"' in html
    assert 'other: "Connect another keyboard"' in html
    assert "別のキーボードを選択" not in html


def test_app_script_loaded_only_when_isolated():
    """main-*.js (needs SharedArrayBuffer) is added only when the page is cross-origin isolated, so a
    hard reload that bypasses the service worker shows a message instead of an uncaught error"""
    html = page()
    assert '<script src="main-@UNIQVER@.js">' not in html
    loader = html[html.index("if (window.crossOriginIsolated) {"):html.index("</script>", html.index("if (window.crossOriginIsolated) {"))]
    assert 'app_script.src = "main-@UNIQVER@.js"' in loader
    assert "show_error(T.no_isolation)" in loader
    assert 'no_isolation: "ブラウザがこのページを隔離モード' in html and 'no_isolation: "The browser could not open' in html
