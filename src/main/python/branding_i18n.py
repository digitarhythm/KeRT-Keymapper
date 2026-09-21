# SPDX-License-Identifier: GPL-2.0-or-later
"""Locale detection and translator installation for KeRT-mapper (docs/i18n-spec.md).

Translations live in ``translations/kert_<lang>.ts`` (Qt Linguist XML) inside the resources directory and are
read directly at runtime, so no ``lrelease`` / ``.qm`` step is needed. Qt's own ``qtbase_<lang>.qm`` (standard
dialog buttons) is loaded as well when PyQt5 ships it.
"""
import os
import xml.etree.ElementTree as ET

from PyQt5.QtCore import QLibraryInfo, QLocale, QTranslator

LANG_ENV = "KERT_LANG"
CATALOG_PATTERN = "translations/kert_{}.ts"
APP_ATTR = "kert_translators"


def resolve_language(env=None, system_locale=None):
    """Language code ("ja", "en", ...) from KERT_LANG, else from the system locale ("ja_JP" -> "ja")."""
    if env is None:
        env = os.environ
    name = env.get(LANG_ENV) or system_locale or QLocale.system().name()
    return name.replace("-", "_").split("_")[0].split(".")[0].lower() or "en"


class TsTranslator(QTranslator):
    """A QTranslator backed by a .ts file parsed with xml.etree (no lrelease required)."""

    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.messages = {}
        for ctx in ET.parse(path).getroot().findall("context"):
            name = ctx.findtext("name")
            for msg in ctx.findall("message"):
                translation = msg.find("translation")
                if translation is None or translation.get("type") == "unfinished" or not translation.text:
                    continue
                self.messages[(name, msg.findtext("source"))] = translation.text

    def translate(self, context, source, disambiguation=None, n=-1):
        # None becomes a null QString, which tells Qt to try the next translator and finally return `source`
        # (an empty "" would be taken as a real, empty translation)
        return self.messages.get((context, source))

    def isEmpty(self):
        return not self.messages


def install(app, get_resource, locale=None):
    """Install the translators for `locale` (default: resolve_language()) on `app`; returns them.

    Nothing is installed (and [] returned) when no catalog exists for the language, so the UI stays English.
    """
    lang = resolve_language(system_locale=locale) if locale else resolve_language()
    installed = []
    catalog = get_resource(CATALOG_PATTERN.format(lang))
    if os.path.exists(catalog):
        try:
            translator = TsTranslator(catalog, app)
        except ET.ParseError:
            translator = None
        if translator is not None and not translator.isEmpty() and app.installTranslator(translator):
            installed.append(translator)
        qt_translator = QTranslator(app)
        if qt_translator.load("qtbase_" + lang, QLibraryInfo.location(QLibraryInfo.TranslationsPath)) \
                and app.installTranslator(qt_translator):
            installed.append(qt_translator)
    setattr(app, APP_ATTR, getattr(app, APP_ATTR, []) + installed)
    return installed


def uninstall(app):
    """Remove every translator that install() registered on `app` (used by tests)."""
    for translator in getattr(app, APP_ATTR, []):
        app.removeTranslator(translator)
    setattr(app, APP_ATTR, [])
