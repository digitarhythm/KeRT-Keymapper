# SPDX-License-Identifier: GPL-2.0-or-later
"""Product branding, kept in one file so that the fork's identity does not spread through upstream code
(docs/rebranding-plan.md). Wire-protocol strings (the "vial:..." serial magic, HID command values, the
.vil / vial.json names) are deliberately NOT here: they must stay as they are."""
APP_NAME = "KeRT-Keymapper"
APP_ORG = "digitarhythm"
APP_ORG_DOMAIN = "digitarhythm.github.io"
APP_URL = "https://github.com/digitarhythm/KeRT-Keymapper"
APP_DESCRIPTION = "Vial-compatible keyboard configurator with HostOS support"
# the project this is a fork of; shown in the About box (GPL-2.0 attribution) and kept in user-facing help
UPSTREAM_NAME = "Vial"
UPSTREAM_URL = "https://get.vial.today/"
