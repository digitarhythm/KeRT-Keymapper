# テーマメニューの復活と「KeRT Color」 仕様書（2026-10-04）

## 1. 目的

非表示にしていた「テーマ」メニューを復活させ、これまでの唯一のテーマ「KeRT Light」を「KeRT Color」と改名して
デフォルトにする。上流（Vial）のテーマもすべて選べるようにし、Web 版にもメニューを出す。

## 2. メニュー

| 順 | 項目 | 内容 |
|---|---|---|
| 1 | System | OS 標準の配色（上流と同じ） |
| 2 | KeRT Color | 旧 KeRT Light。デフォルト。角丸・線・黒いキーなど独自の見た目一式 |
| 3〜 | Light, Dark, Arc, Nord, Olivia, Dracula, Bliss, Catppuccin Latte / Frappé / Macchiato / Mocha | 上流のテーマ（`themes.py` は無変更） |

- 各項目の `data()` にテーマ名を入れる（表示名は翻訳されうるため）。
- 選ぶと、その場で配色とスタイルシートを切り替え、完全な適用には再起動（Web 版はページの再読み込み）が必要と
  知らせる。Web 版は入れ子のイベントループ（`exec_()`）が使えないので、メッセージを `open()` で出す（待たない）。

## 3. 上流テーマでの見た目

上流テーマと System には KeRT Color の角丸・線のスタイルシートを付けない。ただし、キーは常に黒く描くので、
黒いキーの見た目（`key_button_style`: ピッカーのキー、タブ、キーボード名、透明なレイヤーボタン）だけは付ける。
選択色はそのテーマのパレットの Highlight / HighlightedText を使う。

タブの中央寄せ（`QTabWidget::tab-bar { alignment: center; }`）は、全テーマ共通の `COMMON_STYLE` に置き、どのテーマでも
タブを中央に寄せる（2026-10-04。それまでは KeRT Color だけで、上流テーマ・System では左寄せだった）。

## 4. 選んだテーマの保存

```mermaid
flowchart TD
    M["テーマメニューで選ぶ"] --> S{"Web 版？"}
    S -- いいえ --> Q["QSettings の kert_theme に保存"]
    S -- はい --> G["vialglue.save_theme(name)"] --> P["ページが localStorage の kert_theme に保存"]
    Start["次の起動"] --> R{"Web 版？"}
    R -- いいえ --> QR["QSettings の kert_theme を読む"]
    R -- はい --> E["ページが localStorage から ENV.KERT_THEME を渡す"] --> ER["環境変数 KERT_THEME を読む"]
    QR --> V["resolve_theme(): メニューにある名前ならそのまま、なければ KeRT Color"]
    ER --> V
```

- 保存先のキーは `kert_theme`。メニューを隠していた間の古い `theme` の値（上流のテーマ名がありうる）は読まない。
- 旧名「KeRT Light」や未知の名前、未保存は KeRT Color になる。
- Web 版の Qt（Qt 5.14 for WebAssembly）は QSettings をメモリにしか持たないので、ページの `localStorage` に保存する。
  `localStorage` が使えないとき（プライベートウィンドウなど）は保存されず、毎回 KeRT Color で始まる。

| 場所 | 内容 |
|---|---|
| `branding_theme.py` | `DEFAULT_THEME = "KeRT Color"`、`SETTINGS_KEY = "kert_theme"`、`resolve_theme` / `saved_theme` / `save_theme`、`register()` は上流テーマを残して KeRT Color を先頭に置く、`stylesheet()` は上流テーマにも黒いキーの規則を付ける |
| `main_window.py` | メニューを常に表示（Web 版も）、項目に `setData(name)`、Web 版は `open()` で再読み込みを案内 |
| `web/src/main.c` | `vialglue.save_theme(name)` → `{cmd: "theme", name}` |
| `web/src/index.html` | `cmd == "theme"` で `localStorage` に保存、起動時に `ENV.KERT_THEME` へ渡す |
| `kert_ja.ts` | 「テーマを完全に適用するにはページを再読み込みしてください。」 |

## 5. テスト

| テスト | 確認内容 |
|---|---|
| `test_theme.py::test_kert_color_registered` | KeRT Color が登録され、KeRT Light は無い。二重登録しない。配色の値 |
| `test_theme.py::test_upstream_themes_are_back` | テーマの並びが KeRT Color、上流 11 種の順 |
| `test_theme.py::test_theme_menu_visible` | メニューが見え、System・KeRT Color・上流の順。保存されたテーマ（既定 KeRT Color）にチェック |
| `test_theme.py::test_default_theme_resolution` | 未保存・空・未知・KeRT Light → KeRT Color、メニューにある名前はそのまま |
| `test_theme.py::test_theme_saved_under_its_own_key` | `kert_theme` に保存・読み込み、古い `theme` は無視 |
| `test_theme.py::test_theme_saved_by_the_web_page` | Web 版は `KERT_THEME` から読み、`vialglue.save_theme` で送る（QSettings は使わない） |
| `test_theme.py::test_upstream_theme_keeps_the_key_look` | Dark と System に KeRT の線は付かず、黒いキー・透明なレイヤーボタンの規則は付く |
| `test_theme.py::test_tabs_centred_in_every_theme` | KeRT Color・Dark・Nord・System のどれでもタブの中央寄せがある |
| `test_web_start_page.py::test_page_keeps_the_theme` | `main.c` の `save_theme`、ページの保存と `ENV.KERT_THEME` |

## 6. 適用中の覆い（2026-10-05）

テーマメニューでテーマを選んでから、適用が終わって再読み込み（デスクトップは再起動）を促すメッセージが出るまで、
画面全体を半透明の黒で覆い、中央にローディングスピナーを出す。覆いの間はクリックも受け付けない。

- `MainWindow.set_theme()`: 覆いを出し（`widgets/busy_overlay.py` の `set_busy(window, True)`）、
  `THEME_COVER_MS = 50` ms 後に `apply_theme()` でテーマを適用・保存し、覆いを外してから `show_theme_message()`。
  間を置くのは、重い適用処理の前に覆いを画面に出すため。
- デスクトップ版: メインウィンドウ全体に重ねる `BusyOverlay`（黒 アルファ 140、白い円弧のスピナー）。
  適用は同じスレッドで動くので、その間スピナーは止まって見える。
- ブラウザ版: `vialglue.busy(1/0)` → `{cmd: "busy"}` → ページの `#busy_cover`（`rgba(0, 0, 0, 0.55)`、中央に CSS の
  スピナー）。ページはワーカーと別のスレッドなので、適用中もスピナーは回り続ける。

```mermaid
sequenceDiagram
    participant U as ユーザー
    participant M as MainWindow
    participant B as 覆い（BusyOverlay / ページの #busy_cover）
    U->>M: テーマを選ぶ
    M->>B: set_busy(True)（半透明の黒とスピナー）
    Note over M: 50 ms 待つ（覆いが画面に出る）
    M->>M: apply_theme()（テーマの適用・保存）
    M->>B: set_busy(False)
    M->>U: 再読み込み / 再起動を促すメッセージ
```

| テスト | 確認内容 |
|---|---|
| `test_theme_busy.py::test_cover_while_the_theme_is_applied` | 選んだ直後に覆いが出て、テーマはまだ適用されない。適用は覆いの下で行われ、メッセージの時には覆いが消えている |
| `test_theme_busy.py::test_cover_is_translucent_black_with_a_spinner` | 覆いがウィンドウ全体で、暗くなるが真っ黒ではなく、中央の輪の上に明るいスピナーの円弧がある |
| `test_theme_busy.py::test_web_cover_is_drawn_by_the_page` | ブラウザ版は `vialglue.busy(1)` / `busy(0)` を送り、Qt の覆いは出さない |
| `test_web_start_page.py::test_page_draws_the_busy_cover` | `main.c` の `busy`、ページの `#busy_cover`（固定・半透明の黒・中央のスピナー）と `cmd == "busy"` の処理 |
