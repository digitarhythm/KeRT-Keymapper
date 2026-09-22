# ブラウザ版 起動の先読みと接続時の作り直し削減 仕様書

作成日: 2026-09-22

## 1. 目的

ブラウザ版で、キーボードを選んでから画面が出るまでの時間（TReK Rouge で実測 19 秒）を短くする。

実測の内訳（クリックからの経過）:

| 区間 | 時間 | 内容 |
| --- | --- | --- |
| クリック → 最初の HID 通信 | 1.8 秒 | Python モジュールの import |
| HID 通信 233 往復 | 0.6 秒 | 通信待ちはわずか |
| 最後の HID 通信 → 画面表示 | 11.5 秒 | メインウィンドウの組み立てとタブの作り直し（ネイティブでは 0.7 秒） |
| その他 | 5 秒 | |

原因は通信ではなく、wasm 上の Python がネイティブの 10〜15 倍遅いこと。したがって
**キーボードを選ぶ前にできる処理を先に済ませる**（先読み）と、**接続後の無駄な作り直しをなくす**ことで縮める。

## 2. 先読み（ブラウザ版のみ）

```mermaid
sequenceDiagram
    participant P as ページ (index.html)
    participant W as ワーカー (Python)
    participant U as ユーザー
    W-->>P: notify_alive（実行環境の初期化完了）
    P->>W: py: import webmain; webmain.preload(qtApp)
    Note over W: モジュール import、MainWindow 生成（非表示、デバイス無し）
    U->>P: キーボードをクリック
    P->>W: py: import webmain; webmain.main(qtApp)
    Note over W: 先読み済み: 機器一覧の更新 → 接続・読み込み → show
    W-->>P: notify_ready（起動画面を閉じる）
```

- `webmain.preload(app)`: `main()` のうち MainWindow の生成までを行い、`window` に保持する（表示しない）。
  このとき機器はまだ選ばれていないので、`hidproxy.hid.enumerate()` は機器情報が無ければ空リストを返す
  （現状は JSON の解析で失敗する）。C 側の `g_device_desc` は初期値を空文字列にする。
- `webmain.main(app)`: `window` があれば `window.autorefresh.update(quiet=False, hard=True)` で機器を取り込み、
  `window.show()` して `vialglue.notify_ready` を予約する。無ければ従来どおり全処理を行う（先読みが失敗した
  場合の保険）。
- `MainWindow.__init__` にある `notify_ready` の予約は、先読みで生成した場合は行わない
  （`appctx.preloaded` が真なら予約しない。先読みの時点で起動画面が閉じてしまうのを防ぐ）。
- ページ: `notify_alive` を受けたら `preload` を送る。キーボード選択後の処理は従来どおり `main`。
  `preload` が失敗しても `main` が全処理を行うので、起動はできる。

## 3. タブの作り直しの削減（両版）

`MainWindow.refresh_tabs()` は接続のたびに（起動時は 3 回）全タブの `EditorContainer` を作り直している。
有効なエディタの並びが前回と同じなら何もしない。並びが変わったとき（例: HostOS の有無、Tap Dance 0 件）だけ
作り直す。表示中のタブは維持される。

## 4. 期待する効果

クリック後の待ちは、先読みで 1.8 秒 + MainWindow 生成分（ネイティブ 0.3 秒 ≒ wasm 4 秒前後）が消え、
タブの作り直し削減で 2 回分（ネイティブ 0.3 秒 ≒ wasm 3 秒前後）が消える見込み。19 秒 → 8〜10 秒。

## 5. テスト (`src/main/python/test/test_web_startup.py`)

| テスト | 内容 |
| --- | --- |
| `test_preload_then_main_reuses_window` | `webmain.preload(app)` で MainWindow が非表示で生成され、`webmain.main(app)` が同じウィンドウを表示して機器を選択し、`notify_ready` 相当の通知を 1 回だけ行う |
| `test_main_without_preload` | 先読み無しの `webmain.main(app)` でもウィンドウが生成・表示される |
| `test_enumerate_without_device` | 機器情報が空のとき、ブラウザ版の `hid.enumerate()` が空リストを返す（`vialglue` の代替を差し込んで確認） |
| `test_refresh_tabs_skips_when_unchanged` | 接続後に `refresh_tabs()` を再度呼んでもタブのウィジェットが同じオブジェクトのまま。有効なエディタが変わると作り直される |
| `test_main_window_preloaded_flag` | `appctx.preloaded = True` で生成した MainWindow は `notify_ready` を予約しない（デスクトップでは元々予約しないので、フラグの参照だけを確認） |
