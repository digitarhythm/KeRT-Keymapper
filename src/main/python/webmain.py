# SPDX-License-Identifier: GPL-2.0-or-later
import os

import traceback

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import pyqtSignal

import sys
import json

from main_window import MainWindow
import branding_theme
import branding_i18n
import startup_progress


# http://timlehr.com/python-exception-hooks-with-qt-message-box/
from util import init_logger

window = None

def show_exception_box(log_msg):
    if QtWidgets.QApplication.instance() is not None:
        global errorbox

        errorbox = QtWidgets.QMessageBox()
        errorbox.setText(log_msg)
        errorbox.setModal(True)
        errorbox.show()


class UncaughtHook(QtCore.QObject):
    _exception_caught = pyqtSignal(object)

    def __init__(self, *args, **kwargs):
        super(UncaughtHook, self).__init__(*args, **kwargs)

        # this registers the exception_hook() function as hook with the Python interpreter
        sys._excepthook = sys.excepthook
        sys.excepthook = self.exception_hook

        # connect signal to execute the message box function always on main thread
        self._exception_caught.connect(show_exception_box)

    def exception_hook(self, exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            # ignore keyboard interrupt to support console applications
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
        else:
            log_msg = '\n'.join([''.join(traceback.format_tb(exc_traceback)),
                                 '{0}: {1}'.format(exc_type.__name__, exc_value)])

            # trigger message box show
            self._exception_caught.emit(log_msg)
        sys._excepthook(exc_type, exc_value, exc_traceback)


def web_get_resource(name):
    return "/usr/local/" + name


# KERT_DEBUG_STARTUP=1 (browser: open the page with ?debug=startup) prints the time of each start-up step
# and a profile of the last stretch ("Finishing": from showing the window to telling the page it is ready)
DEBUG_STARTUP = bool(os.environ.get("KERT_DEBUG_STARTUP"))
_debug_clock = None
_profile = None


def _debug(step):
    global _debug_clock
    if not DEBUG_STARTUP:
        return
    import time
    now = time.monotonic()
    if _debug_clock is None:
        _debug_clock = now
    print("[startup] %-8s %7.0f ms" % (step, (now - _debug_clock) * 1000), flush=True)


def _profile_start():
    global _profile
    if DEBUG_STARTUP:
        import cProfile
        _profile = cProfile.Profile()
        _profile.enable()


def _profile_report():
    global _profile
    if _profile is None:
        return
    _profile.disable()
    import io
    import pstats
    out = io.StringIO()
    pstats.Stats(_profile, stream=out).sort_stats("cumulative").print_stats(30)
    print("[startup] profile from window.show() to ready:\n" + out.getvalue(), flush=True)
    _profile = None


def _notify_ready():
    _debug("notified")
    _profile_report()
    import vialglue
    vialglue.notify_ready()


def _schedule_notify_ready():
    """Tell the page the app is up (closes the start screen); a no-op outside the browser."""
    if sys.platform == "emscripten":
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, _notify_ready)


def preload(app):
    """Everything that does not need the keyboard: imports, fonts, the (hidden) main window.

    The page calls this as soon as the runtime is alive, before the user has chosen a keyboard, so that
    main() afterwards only has to connect and load (docs/web-startup-preload-spec.md)."""
    global window
    font = app.font()
    font.setPointSize(10)
    app.setFont(font)

    app.get_resource = web_get_resource
    with open(app.get_resource("build_settings.json"), "r") as inf:
        app.build_settings = json.loads(inf.read())
    app.qt_exception_hook = UncaughtHook()

    branding_theme.register()
    branding_i18n.install(app, app.get_resource)
    branding_i18n.install_bundled_font(app, app.get_resource)
    app.preloaded = True          # MainWindow: do not announce readiness yet
    window = MainWindow(app)
    app.processEvents()


def main(app):
    """Start with the keyboard the user chose: connect, load, show."""
    global window
    startup_progress.report("connect")
    _debug("connect")
    if window is None:
        preload(app)
    # the device is available now (the page set its descriptor): take it in and connect
    window.autorefresh.update(quiet=False, hard=True)
    _debug("loaded")
    startup_progress.report("layout")
    _profile_start()
    window.show()
    _debug("shown")
    app.processEvents()
    _debug("ready")
    startup_progress.report("ready")
    _schedule_notify_ready()

    app.processEvents()
