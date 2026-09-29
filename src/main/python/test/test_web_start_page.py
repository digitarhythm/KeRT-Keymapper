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


SW = os.path.realpath(os.path.join(os.path.dirname(__file__), "../../../../web/src/kert-serviceworker.js"))


def test_service_worker_does_not_cache_on_localhost():
    """The local preview relinks under the same hash, so the service worker must not serve cached
    build files there (and drops any it has); on GitHub Pages the hashed files stay cache-first"""
    with open(SW, encoding="utf-8") as f:
        sw = f.read()
    assert "const DEV = " in sw and "localhost" in sw
    assert '!DEV && request.method === "GET" && HASHED_ASSET.test' in sw
    assert "DEV || k !== CACHE_NAME" in sw
    assert 'CACHE_NAME = "kert-keymapper-assets-v3"' in sw, "new cache name: mixed old entries are dropped"


def test_error_alert_shows_worker_error_text():
    html = page()
    handler = html[html.index("window.onerror = function"):html.index("};", html.index("window.onerror = function"))]
    assert "message.message" in handler


def test_undefined_keyboard_name_on_the_web_page():
    """The start page names a keyboard without a product name "Undefined Keyboard" (list and app)"""
    html = page()
    assert 'var UNDEFINED_KEYBOARD_NAME = "Undefined Keyboard";' in html
    fn = html[html.index("function device_name"):html.index("}", html.index("function device_name"))]
    assert "UNDEFINED_KEYBOARD_NAME" in fn and "toString(16)" not in fn
    assert "product_string: device_name(g_device)," in html


def test_start_page_uses_the_app_highlight():
    """The start page's buttons, chosen keyboard box and progress bar use the app's light grey highlight
    and dark text (2026-09-27, were KeRT green with white text); no green is left on the page"""
    import re
    from PyQt5.QtGui import QPalette
    import branding_theme

    html = page()
    theme = dict(branding_theme.BRAND_THEMES)["KeRT Light"]
    root = re.search(r":root\s*\{([^}]*)\}", html)
    assert root, "colours are defined once in :root"
    assert "--kert-highlight: %s;" % theme[QPalette.Highlight] in root.group(1)
    assert "--kert-highlight-text: %s;" % theme[QPalette.HighlightedText] in root.group(1)
    for green in ("#00a3a3", "#00b8b8", "#e6f7f7"):
        assert green not in html.lower(), green
    assert "background-color: var(--kert-highlight)" in css_block(html, ".startup_btn").replace("background-color:", "background-color: ") \
        or "background-color:var(--kert-highlight)" in css_block(html, ".startup_btn")
    # the small spinner inside the start button uses the highlight text colour (white on the grey)
    assert "var(--kert-highlight-text)" in css_block(html, "#startup_spinner")


def test_page_draws_the_tab_fade():
    """The browser build's tab fade is a CSS-animated box over the page area (widgets/tab_fade.py asks
    for it through vialglue.fade): it never takes clicks and sits above the Qt canvas"""
    html = page()
    assert '<div id="page_fade"></div>' in html
    css = css_block(html, "#page_fade")
    assert "position:fixed" in css and "pointer-events:none" in css and "display:none" in css
    assert "background-color:var(--kert-window)" in css
    handler = html[html.index("function my_onmessage"):html.index("const FILE_OPTIONS")]
    assert 'e.data.cmd == "fade"' in handler and "page_fade(e.data)" in handler
    fn = html[html.index("function page_fade"):html.index("function my_onmessage")]
    assert "transition" in fn and "opacity" in fn and "d.ms" in fn
    # never relies on requestAnimationFrame (paused in background tabs, which left the box up), and a
    # fail-safe takes the box away if the "in" message never comes
    assert "requestAnimationFrame" not in fn
    assert "PAGE_FADE_FAILSAFE_MS" in fn and "var PAGE_FADE_FAILSAFE_MS = 5000;" in html


def test_glue_has_fade():
    c = open(os.path.join(os.path.dirname(PAGE), "main.c"), encoding="utf-8").read()
    assert '{"fade",  vialglue_fade, METH_VARARGS, ""}' in c
    assert 'cmd: "fade"' in c



def test_keyboard_list_white_chosen_black():
    """The keyboard list on the start page: white boxes with black names; the one clicked turns black
    with a white name, like the app's keys (2026-09-30)"""
    import re
    html = page()
    box = css_block(html, ".known_name")
    assert "background-color:#ffffff" in box and "color:#000000" in box
    sel = re.search(r"\.known_name\.selected[^{]*\{([^}]*)\}", html).group(1).replace(" ", "")
    assert "background-color:#000000" in sel and "color:#ffffff" in sel and "opacity:1" in sel



def test_progress_bar_black():
    """The start-up progress bar fills in black (2026-09-30): the light highlight grey barely showed on
    the white track"""
    html = page()
    assert "background-color:#000000" in css_block(html, "#progress_fill")
