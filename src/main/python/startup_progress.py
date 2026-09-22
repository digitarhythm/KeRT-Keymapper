# SPDX-License-Identifier: GPL-2.0-or-later
"""Startup progress for the browser build (docs/web-startup-progress-spec.md).

report(step_id) tells the page which stage of the start-up was just completed; it is a no-op on the
desktop (no vialglue module). The page maps the step ids to localized labels.
"""
import sys

STEPS = ["connect", "definition", "settings", "entries", "keymap", "macros", "tapdance", "combos", "ui", "layout", "ready"]


def report(step_id):
    if step_id not in STEPS:
        raise ValueError("unknown startup step {!r}".format(step_id))
    vialglue = sys.modules.get("vialglue")
    if vialglue is None:
        if sys.platform != "emscripten":
            return
        import vialglue   # noqa: the browser build always has it
    progress = getattr(vialglue, "progress", None)
    if progress is not None:
        progress(step_id, STEPS.index(step_id) + 1, len(STEPS))
