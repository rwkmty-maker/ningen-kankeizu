# 人間関係図（CustomerNexusSystem、配布 exe 名「かんたん検索.exe」）— Claude Code 用の決まり

顧客の Excel（知人管理表）を読み込み、あいまい検索（ふりがな・ローマ字・和暦・日付のゆれ・AND/OR・一文字違い）と、紹介者・グループのつながりの関係図（ブラウザで表示）を行う Windows 用 Tkinter アプリ。
仕様の読み解きは **`docs/SPEC.md`**（列の意味・検索の順番・関係図の作り方・テスト結果・既知の問題・最初に読む所）。直す前に必ず読む。

## 環境
- **Windows のローカルで Claude Code を使う**（`winreg` を無条件に import しているので、Windows 以外では起動しない）。
- 本体は `customer_app.py`（現在 v108、`VERSION` 定数）。ライブラリの案は SPEC §2（**pandas は 3 未満**。pandas 3 だと会員IDが整数だけの列で読込に失敗する）。
- 作業場所は **`C:\Users\Owner\Desktop\Claude\2025.12.28 - 人間関係図\src`**（このリポジトリの作業フォルダ。GitHub `rwkmty-maker/ningen-kankeizu` とつながっている。リポジトリの一番上＝src の中身）。
- **書いてよい場所（2026-11-10 本人の指示）**: デスクトップ以下の `src` フォルダは、ソース置き場なので直接読み書きしてよい。**ファイルの削除は毎回本人に聞いてから**。`src` 以外のデスクトップ以下（`test\`・`ico\`・exe・ルール.txt など）は**参照のみ**。ドキュメントなどの出力は `C:\Users\Owner\Downloads` に出す。
- Git の操作は Windows の Git で行う（改行は `.gitattributes` の `* text=auto` で、Git の中は LF・取り出すと CRLF。`test_results.txt` は UTF-16 なのでそのまま）。
- デスクトップの `ico\` と `ルール.txt` の控えは、このリポジトリの `docs\ico\` と `docs\windsurf\ルール.txt` にある。
- 実データ（知人管理表）は GitHub に入れない。テストには架空のデータを使う。

## 共通ルール
小松さんの共通ルール（GitHub `rwkmty-maker/kokoro-backup` の `docs/KNOWHOW_INDEX.md` の「1.」、`docs/BASE_RULES.md`、`docs/LESSONS.md`）に従う。要点：根本原因を直す／時間差処理・リトライ・エラーの握りつぶし・テストの無効化で隠さない／形だけのテストは厳禁／指示されていない変更・追加・省略をしない／不明点は推測せず質問する／直した方が良い所は最後にまとめて示す／更新ごとにバージョン番号を 1 増やす／大きいファイルは分ける／複雑なら何回かに分けて直す→テスト。

## このアプリだけのルール（2026-11-10 本人承認）
- 処理が複雑になる機能は載せなくてよい。比較的かんたんに載せられるなら載せる。

Windsurf 時代のルールの原文: `docs/windsurf/ルール.txt`。

## 注意（SPEC §11 の要点）
- `customer_app.py:50` に Claude API キーが直書きされている（本人の判断で、そのまま保存）。使うのは「フリガナ自動入力」だけ。
- 「フリガナ自動入力」は顧客の本名を Claude API に送り、元の Excel を `data_only=True` で開いて上書き保存する（数式が消える）。
- テストの多くは本体の関数ではなく「写し」や別実装を検査している（例：`OR` `AND` `&` の扱いが本体と違う）。直したら本体の関数を呼ぶテストで確かめる。

## よく使うもの
- ビルド: `pyinstaller CustomerNexusSystem.spec`（アイコン入り）。配布名「かんたん検索.exe」への名前の付け方は未確認（SPEC §8）。
- テスト: `python -m pytest test_all.py test_birth_search.py test_search_logic.py -v`、`python comprehensive_test.py`。結果の詳細は SPEC §9。
