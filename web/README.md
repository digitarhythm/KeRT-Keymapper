# KeRT-mapper Web

The browser version of KeRT-mapper (WebAssembly build of this repository, WebHID), published to GitHub Pages:

**https://digitarhythm.github.io/KeRT-mapper/**

WebHID is required, so it works in Chromium-based browsers (Chrome, Edge, Brave, ...) only.

This directory is the build machinery of [vial-kb/vial-web](https://github.com/vial-kb/vial-web) moved into
the app repository (until 2026-09-22 it lived in `digitarhythm/KeRT-mapper-web`). Differences from upstream:

- `src/build.sh` takes the Python sources and resources from this repository (`../../..` from the build
  directory) and copies the KeRT-mapper resources (logo, icon, check mark, `translations/`).
- `src/index.html` loads `src/kert-serviceworker.js`: cross-origin isolation for the pthread build
  (GitHub Pages cannot send COOP/COEP headers; based on coi-serviceworker, MIT) plus cache-first delivery of
  the content-hashed wasm/data files so that repeat visits start fast. `Module.preRun` sets `KERT_LANG`
  from the browser language so the UI follows it.
- The workflow `.github/workflows/web.yml` builds and deploys on every version tag (`v*`) and on manual
  dispatch (the emscripten build of Qt and CPython takes about 45 minutes).

## Quick preview of page changes

Changes to the page shell (`src/index.html`, `src/kert-serviceworker.js`, `src/icon.png`) do not need a
build: `python3 web/dev_server.py` downloads the published build once, lays your local page over it and
serves everything on http://localhost:8765 with the COOP/COEP headers, so the app runs (keyboard included)
and a reload shows the change. Python and resource changes live inside the `.data` file and still need a
build; the CI caches the emscripten toolchain and the Qt/CPython builds, so a build after the first one
takes a few minutes instead of 45.

## Building locally

```
cd web
git clone https://github.com/vial-kb/via-keymap-precompiled.git
./fetch-emsdk.sh
./fetch-deps.sh
./build-deps.sh
cd src
./build.sh        # output in web/src/build
```
