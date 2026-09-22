# KeRT-Keymapper 日本語化・国際化 仕様書

作成日: 2026-09-21

## 1. 目的

- 画面表示を日本語化する。まずは日本語のみを提供するが、翻訳ファイルを追加すれば他の言語にも
  対応できる仕組み (i18n) を用意する。
- upstream (vial-kb/vial-gui) からの取り込みを妨げないよう、既存の `tr("Context", "text")` の
  仕組みをそのまま使い、コード側の変更は「英語リテラルを `tr()` で包む」最小差分に留める。

## 2. 方針

| 項目 | 決定 |
| --- | --- |
| 翻訳の仕組み | Qt 標準の `QTranslator`。翻訳ファイルは Qt Linguist 形式の `.ts` (XML) |
| 翻訳ファイル | `src/main/resources/base/translations/kert_<lang>.ts` (まず `kert_ja.ts`) |
| `.qm` の生成 | **行わない**。`lrelease` が開発環境に無いため、`.ts` を実行時に直接読む `QTranslator` サブクラスを用意する |
| Qt 組み込みダイアログ | PyQt5 同梱の `qtbase_<lang>.qm` (OK / キャンセル / はい / いいえ など) があれば併せて読み込む |
| 言語の決定 | 環境変数 `KERT_LANG` → OS ロケール (`QLocale.system()`) の順。該当する `.ts` が無ければ英語 (翻訳なし) |
| キーコードのラベル | 翻訳しない (`KC_A` → `A` など。約 540 個。自作キーボード利用者は英語表記に慣れている) |
| タブの文言 | **翻訳しない**。上段のエディタタブ (Keymap / Layout / Macros / Lighting / Tap Dance / HostOS / Combos / Key Overrides / Alt Repeat Key / QMK Settings / Matrix tester / Firmware updater) と下段のピッカータブ (Basic / ISO/JIS / Layers / Quantum / Backlight / App, Media and Mouse / MIDI / Tap Dance / HostOS / User / Macro) は英語のまま |
| Firmware updater のログ | 翻訳しない (技術的なログ文字列。ボタンとチェックボックスは翻訳する) |
| About キーボード ダイアログの本文 | 翻訳しない (仕様値の一覧。メニュー項目とウィンドウタイトルは翻訳する) |

## 3. 構成

```mermaid
flowchart LR
    subgraph 開発時
        SRC["Python ソース<br/>tr(&quot;Context&quot;, &quot;text&quot;)"] -->|util/i18n/update_ts.py| TS["translations/kert_ja.ts<br/>(人が訳を記入)"]
    end
    subgraph 実行時
        MAIN["main.py / webmain.py"] --> INST["branding_i18n.install(app, get_resource)"]
        INST -->|KERT_LANG または OS ロケール| LANG{"言語"}
        LANG -->|ja| TSL["TsTranslator (.ts を XML として読む)"]
        LANG -->|ja| QTB["QTranslator (qtbase_ja.qm)"]
        LANG -->|en / 未対応| NONE["翻訳なし (英語)"]
        TSL --> APP["QApplication.installTranslator"]
        QTB --> APP
        APP --> TR["QCoreApplication.translate → 日本語"]
    end
    TS -. get_resource(&quot;translations/kert_ja.ts&quot;) .-> TSL
```

`pylupdate5` は `tr("Context", "text")` 形式 (`QCoreApplication.translate` の別名) からコンテキストを
取り出せず、全件が `@default` になるため使わない。代わりに `util/i18n/update_ts.py` がソースを走査し、
既存の訳を保ったまま `.ts` に不足エントリを追記する。

## 4. モジュール `branding_i18n.py`

```python
def resolve_language(env=os.environ, system_locale=None) -> str
    # env["KERT_LANG"] があればそれ ("ja", "en", "ja_JP" など)。無ければ QLocale.system().name()。
    # 返り値は "ja" のような言語コード (国コードは切り捨て)。

def install(app, get_resource, locale=None) -> list
    # locale (省略時は resolve_language()) に対応する翻訳を app に登録し、
    # 登録した QTranslator のリストを返す (app.kert_translators にも保持する)。
    # 翻訳ファイルが無ければ何も登録せず [] を返す。例外は投げない。

def uninstall(app)
    # install() が登録した翻訳をすべて外す (テスト用)。

class TsTranslator(QTranslator)
    # .ts を xml.etree で読み {(context, source): translation} を持つ。
    # translate(context, source, disambiguation, n) は辞書を引き、無ければ None を返す
    #  (None は null QString になり、Qt が次の翻訳器・元の文字列にフォールバックする。
    #   "" を返すと「空文字に翻訳した」と解釈されてしまう)。
```

## 5. コード側の変更 (`tr()` で包む)

既存の 62 件に加え、以下の英語リテラルを `tr("Context", "...")` にする。コンテキスト名は既存の慣例
(クラス名相当) に合わせる。

| ファイル | コンテキスト | 文字列 |
| --- | --- | --- |
| `editor/tap_dance.py` | TapDance | On tap / On hold / On double tap / On tap + hold / Tapping term (ms) / ヒント文 |
| `editor/host_os.py` | HostOS | Mac / Win / Linux / Default / ヒント文 |
| `editor/combos.py` | Combos | Key {} / Output key / Combo {} (カードの見出し) |
| `editor/key_override.py` | KeyOverride | Enable / Enable on layers / Trigger / Trigger mods / Negative mods / Suppressed mods / Replacement / Options / 6 つのオプション (修飾キー名 LCtrl 等は英語のまま) |
| `editor/alt_repeat_key.py` | AltRepeatKey | Enable / Last key / Alt key / Allowed mods / Options / 3 つのオプション (Bidirectional 含む) |
| `editor/matrix_test.py` | MatrixTest | Unlock / Reset |
| `editor/macro_recorder.py` | MacroRecorder | Memory used by macros: {}/{} |
| `main_window.py` | MainWindow | About {}... / プロトコル非対応・サンプル UID の警告 2 件 |
| `editor/qmk_settings.py` | QmkSettings | `qmk_settings.json` の各設定の `title` (48 件)。Tap-Hold タブの設定名は QMK の機能名が英語の解説記事で使われるため「日本語の説明 (英語名)」の併記にする (例: タッピングターム (Tapping Term))。内側のタブ名 (Magic / Tap-Hold …) はタブの方針に従い英語のまま |
| `about_keyboard.py` | AboutKeyboard | About {} |
| `entry_labels.py` | TapDance / HostOS | カードの行ラベル (エディタと同じ訳を共有) |
| `entry_labels.py` → `entry_summary.py` | EntrySummary | ツールチップ・マクロ行の固定語: Tapping term / Keys / Output / Combo {} / Text / Tap / Down / Up / Delay |

`entry_summary.py` は Qt 非依存のまま保つ。モジュール内の `tr(context, text)` は文字列をカタログ用に
「印を付ける」だけの no-op (Qt の `QT_TRANSLATE_NOOP` 相当) で、固定語はすべて `tr("EntrySummary", "...")`
で定数化する。各関数は翻訳関数 `tr_fn(context, source)` (省略時はこの no-op) を引数で受け取り、
Qt を知っている `entry_labels.py` 側が `util.tr` を渡す。スロット名 (Tap / Hold / 2×Tap / Tap+Hold、
Mac / Windows / Linux / Default) も `EntrySummary` コンテキストで訳す。

ピッカータブ名 (`tabbed_keycodes.py`) と上段タブ名 (`main_window.py` の `tr("MainWindow", lbl)`) は、
翻訳しない方針のため `.ts` にエントリを持たない (`tr()` を通っても元の英語が返る)。

## 6. 翻訳ファイルの運用

- `.ts` は UTF-8 / LF。`<translation>` が空、または `type="unfinished"` のエントリは残さない
  (テストで検出する)。
- 文字列を追加・変更したら `venv/bin/python util/i18n/update_ts.py` を実行して `.ts` に反映し、訳を記入する。
- 他言語を追加する場合は `kert_<lang>.ts` を置くだけでよい (`install()` が言語コードから探す)。
- ブラウザ版 (vial-web) は `build.sh` で `translations/` ディレクトリを `usr/local/` にコピーする必要がある
  (別リポジトリ、未対応)。

## 8. ブラウザ版のフォント (2026-09-22 追加)

WebAssembly 版の Qt は OS のフォントを使えず、同梱の欧文フォントしか持たないため、日本語がすべて豆腐
(□) になる。対策として Noto Sans CJK JP (OFL 1.1) の**サブセット** `web/src/fonts/kert-ja.otf`
(約 250 KB) を同梱する。

- `web/make_font_subset.py` が、翻訳カタログ (`translations/*.ts`) に現れる文字 + ASCII + Latin-1 記号 +
  かな + CJK 句読点 + 全角英数 + 矢印などの記号を集め、`fontTools.subset` で切り出す。カタログを変えたら
  再実行してコミットする (手順はスクリプト冒頭)。
- `web/src/build.sh` がフォントとライセンスを `usr/local/fonts/` にコピーし、`webmain.py` が
  `branding_i18n.install_bundled_font(app, get_resource)` で読み込んでアプリ既定フォントにする
  (ポイントサイズは維持)。デスクトップ版にはこのファイルが無いので何もしない (OS のフォントを使う)。
- キーボード名など、カタログ外の日本語 (製品名に日本語が含まれる場合等) は対象外で、豆腐になり得る。

## 7. テスト (`src/main/python/test/test_i18n.py`)

| テスト | 内容 |
| --- | --- |
| `test_catalog_parses` | `kert_ja.ts` が XML として読め、言語が `ja` であり、メッセージが 100 件以上ある |
| `test_catalog_complete` | すべてのメッセージに空でない訳があり、`unfinished` が無い |
| `test_catalog_matches_sources` | ソース中の全 `tr()` 文字列と `qmk_settings.json` の全 title が `.ts` にあり、`.ts` の全エントリがソースか JSON に存在する (動的に組み立てる 2 件は許容リスト) |
| `test_tab_labels_not_in_catalog` | 上段タブ・ピッカータブの文言が `.ts` に含まれない |
| `test_resolve_language` | `KERT_LANG` が優先され、無ければ OS ロケール、`ja_JP` → `ja` |
| `test_install_ja_translates` | `install(app, get_resource, "ja")` 後、`tr("MainWindow","Refresh")` が「更新」、`tr("TapDance","On tap")` が「タップ」、`tr("MainWindow","Keymap")` は "Keymap" のまま |
| `test_install_en_keeps_english` | `"en"` および未対応の `"fr"` では翻訳器を登録せず英語のまま |
| `test_qtbase_translation_loaded` | `ja` で `tr("QPlatformTheme","Cancel")` が「キャンセル」(同梱 `.qm` が無ければ skip) |
| `test_missing_catalog_is_harmless` | 翻訳ファイルが無いディレクトリでも例外にならず英語のまま |
| `test_editor_labels_translated` | GUI: `ja` で起動した MainWindow の Tap Dance / Combos / HostOS / Key Override のラベルとオプション、QMK Settings の設定名、Layer ラベル、Refresh ボタン、Matrix tester のボタン、マクロのメモリ表示が日本語。タブ名 (QMK Settings 内側のタブも) は英語のまま |
| `test_cards_translated` | GUI: `ja` でピッカーの TD / HOS カードの行ラベルとマクロカードの行頭 (テキスト: など) が日本語 |
| `test_entry_points_install_translator` | `main.py` と `webmain.py` が `branding_i18n.install(` を呼んでいる |
| `test_bundled_font_covers_catalog` | `web/src/fonts/kert-ja.otf` が現在のカタログの全文字 + かな等を持つ (fontTools が無ければ skip) |
| `test_install_bundled_font` | フォントが無ければ None で何もしない。あれば読み込んでアプリ既定フォントの family になり、ポイントサイズは変わらない。`webmain.py` が呼んでいる |
