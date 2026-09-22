#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Preview changes to the browser version's page (index.html, kert-serviceworker.js, icon.png) in seconds.

The heavy files (main-<hash>.js / .wasm / .data / .worker.js, the emscripten build of Qt + CPython + the
app) are taken from an existing build: web/src/build if you built locally, otherwise they are downloaded
once from the published site into web/.preview/. Your local web/src/index.html is laid over them with the
build's hash substituted, and everything is served on http://localhost:8765 with the COOP/COEP headers the
pthread build needs (so no service worker is involved). Chrome treats localhost as a secure context, so
WebHID works and the keyboard can be connected.

    python3 web/dev_server.py            # serve, using web/src/build or a download of the live site
    python3 web/dev_server.py --refresh  # download the live build again (after a new CI deployment)

Only the page shell is previewed this way: Python or resource changes (they live inside the .data file)
still need a real build (web/README.md).
"""
import argparse
import http.server
import os
import re
import shutil
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src")
SITE = "https://digitarhythm.github.io/KeRT-Keymapper/"
PREVIEW = os.path.join(HERE, ".preview")
PORT = 8765
MAIN_JS = re.compile(r'(main-([0-9a-f]{64})\.js)')   # in src="…" or in the isolation-guarded loader
SHELL_FILES = ("kert-serviceworker.js", "coi-serviceworker.LICENSE", "icon.png")


def download(url, dest):
    if os.path.exists(dest):
        return
    print("downloading", url)
    with urllib.request.urlopen(url) as resp, open(dest, "wb") as outf:
        shutil.copyfileobj(resp, outf)


def prepare(refresh):
    """Returns the directory to serve and the build hash."""
    local_build = os.path.join(SRC, "build")
    if os.path.isdir(local_build) and any(f.endswith(".wasm") for f in os.listdir(local_build)):
        build_dir = local_build
        with open(os.path.join(build_dir, "index.html"), encoding="utf-8") as inf:
            uniqver = MAIN_JS.search(inf.read()).group(2)
        print("using the local build in", build_dir)
    else:
        build_dir = PREVIEW
        if refresh and os.path.isdir(PREVIEW):
            shutil.rmtree(PREVIEW)
        os.makedirs(PREVIEW, exist_ok=True)
        with urllib.request.urlopen(SITE) as resp:
            live_index = resp.read().decode("utf-8")
        uniqver = MAIN_JS.search(live_index).group(2)
        for suffix in (".js", ".wasm", ".data", ".worker.js"):
            name = "main-" + uniqver + suffix
            download(SITE + name, os.path.join(PREVIEW, name))
        print("using the published build", uniqver[:12], "cached in", PREVIEW)

    # overlay the local page shell
    with open(os.path.join(SRC, "index.html"), encoding="utf-8") as inf:
        html = inf.read()
    html = html.replace("@UNIQVER@", uniqver).replace("@VIAL_VER@", "local preview") \
               .replace("@WEB_VER@", "local preview").replace("@VIA_STACK_VER@", "(from build)")
    with open(os.path.join(build_dir, "index.html"), "w", encoding="utf-8") as outf:
        outf.write(html)
    for name in SHELL_FILES:
        shutil.copy(os.path.join(SRC, name), os.path.join(build_dir, name))
    return build_dir


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      ".wasm": "application/wasm", ".js": "text/javascript; charset=utf-8", ".data": "application/octet-stream",
                      ".html": "text/html; charset=utf-8"}

    def end_headers(self):
        # what the service worker adds on GitHub Pages: cross-origin isolation for SharedArrayBuffer
        # (KERT_NO_ISOLATION=1 leaves them out, to try the page the way a hard reload on Pages sees it)
        if not os.environ.get("KERT_NO_ISOLATION"):
            self.send_header("Cross-Origin-Opener-Policy", "same-origin")
            self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
            self.send_header("Cross-Origin-Resource-Policy", "cross-origin")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        if not str(args[0]).startswith("GET /main-"):
            super().log_message(fmt, *args)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--refresh", action="store_true", help="download the published build again")
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()
    directory = prepare(args.refresh)
    handler = lambda *a, **kw: Handler(*a, directory=directory, **kw)
    with http.server.ThreadingHTTPServer(("127.0.0.1", args.port), handler) as httpd:
        print("serving http://localhost:{}/  (edit web/src/index.html, re-run to re-apply, reload the page)".format(args.port))
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    sys.exit(main())
