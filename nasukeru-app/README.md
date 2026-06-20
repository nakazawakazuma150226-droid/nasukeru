# ナスケル

看護記録テンプレート入力支援アプリのデモです。

登録済みテンプレートを選択し、観察項目を入力して、看護記録向けの文章をコピー出力する機能に絞っています。現在はテンプレート定義を SQLite に保存し、Flask API 経由で読み込む構成です。

## 現在の方針

- AI生成は使用しない
- 患者情報や入力内容は保存しない
- テンプレートの初期値は空欄
- コピー前に重要項目の未入力を警告する
- 警告があってもコピーは止めない
- テンプレート本体は SQLite から読み込む

## ファイル構成

```text
nasukeru-app/
  index.html
  README.md
  requirements.txt
  .gitignore
  assets/
    nasukeru-icon.jpg
  css/
    styles.css
  docs/
    handoff.md
  js/
    templates.js
    validation.js
    copy-format.js
    app.js
  server/
    app.py
    init_db.py
    smoke_test.py
    nasukeru.db        # ローカル生成。Git管理対象外
```

## ディレクトリ構成の考え方

このアプリは、画面側とAPI側を分けた小さな構成です。

```text
ブラウザ
  ↓
index.html / css / js
  ↓ fetch
Flask API
  ↓ sqlite3
SQLite DB
```

- 画面表示と入力操作は `index.html`, `css/`, `js/` が担当する
- テンプレートや選択肢などのマスターデータは SQLite に置く
- `js/templates.js` はAPI呼び出しの境界として残し、画面本体の `js/app.js` がDB構造を直接知らないようにする
- `server/` はAPI、DB初期化、スモークテストを置くバックエンド領域
- `server/nasukeru.db` はローカル生成物なのでGitには入れない
- Flaskの静的配信は `index.html`, `assets/`, `css/`, `js/` のみに限定し、`server/` や `.gitignore` はブラウザから取得できないようにする

## 各ファイルの役割

- `index.html`
  - 画面の骨組み
  - CSS/JSの読み込み

- `css/styles.css`
  - レイアウト、見た目、レスポンシブ対応

- `js/templates.js`
  - Flask API からテンプレート、クイックリスト、安静度選択肢を取得する境界

- `js/validation.js`
  - 未入力警告の判定と表示

- `js/copy-format.js`
  - コピー出力文の生成
  - クリップボードコピー

- `js/app.js`
  - 画面生成、検索、タブ切り替え、イベント処理

- `server/init_db.py`
  - SQLite DBを作成し、足りないテーブルと初期テンプレートデータを補う
  - 既存テーブルは削除しない
  - 既存テンプレートに `template_versions` がない場合は version 1 として移行する
  - DB構造変更の適用状況を `schema_migrations` に記録する

- `server/app.py`
  - Flaskで画面とAPIを配信する
  - 現在のAPI:
    - `GET /api/health`
    - `GET /api/templates`
    - `GET /api/templates/<id>`
    - `GET /api/templates/<id>/versions`
    - `GET /api/templates/<id>/versions/<version_id>`
    - `GET /api/templates/<id>/logs`
    - `GET /api/quick-templates`
    - `GET /api/rest-options`
    - `GET /api/search-keywords`
    - `GET /api/migrations`

- `server/smoke_test.py`
  - 主要APIが期待したステータスを返すか確認する
  - `server/` や `.gitignore` が公開されていないことも確認する

- `docs/handoff.md`
  - 現状仕様、将来DB設計、監査ログ設計、実装フェーズの引継ぎメモ

## 現在のデータフロー

初期表示時:

```text
js/app.js
  ↓
getTemplates() / getQuickTemplates() / getRestOptions() / getSearchKeywords()
  ↓
js/templates.js
  ↓
/api/templates
/api/quick-templates
/api/rest-options
/api/search-keywords
  ↓
server/app.py
  ↓
server/nasukeru.db
```

テンプレート選択後:

```text
DB由来のテンプレートJSON
  ↓
js/app.js が入力フォームを生成
  ↓
利用者が観察項目を入力
  ↓
js/copy-format.js がコピー文を生成
  ↓
クリップボードへコピー
```

入力内容はDBへ保存しません。DBに保存するのはテンプレート定義、検索候補、選択肢などのマスターデータだけです。

## セットアップ

Python 3.10 以降を使用します。

```bash
pip install -r requirements.txt
python server/init_db.py
```

Windowsで `py` ランチャーを使う場合:

```powershell
py -3.10 -m pip install -r requirements.txt
py -3.10 server\init_db.py
```

DBファイルの配置先を変える場合は `NASUKERU_DB_PATH` を指定します。

```powershell
$env:NASUKERU_DB_PATH = "C:\nasukeru-data\nasukeru.db"
py -3.10 server\init_db.py
```

## 動かし方

Flask サーバーを起動します。

```bash
python server/app.py
```

Windowsで `py` ランチャーを使う場合:

```powershell
py -3.10 server\app.py
```

その後、ブラウザで以下を開いてください。

```text
http://127.0.0.1:8000/
```

`index.html` を直接開く方法や `python -m http.server` では、`/api/...` が使えないため現在の構成では動作しません。

開発時だけデバッグモードを有効にする場合:

```powershell
$env:NASUKERU_DEBUG = "1"
py -3.10 server\app.py
```

## 動作確認

主要APIと非公開ファイルの遮断をまとめて確認できます。

```powershell
py -3.10 server\smoke_test.py
```

ヘルスチェックだけ確認する場合:

```text
http://127.0.0.1:8000/api/health
```

## DB/API構成

現在は読み取り専用の最小APIです。テンプレート編集、承認、監査ログは未実装です。

### SQLite テーブル

- `schema_migrations`
  - 適用済みDB構造変更の記録を保存
  - `version`, `name`, `applied_at` を持つ

- `templates`
  - テンプレートの基本情報、公開状態、現在バージョンへの参照を保存
  - 通常画面の一覧表示対象は `is_active = 1`
  - `current_version_id` が現在利用する `template_versions` を指す

- `template_versions`
  - テンプレートの入力項目JSONと変更理由をバージョンとして保存
  - 今後テンプレート編集を追加する場合は、既存行を直接上書きせず新しいバージョンを作る想定

- `template_audit_logs`
  - テンプレートに対する移行・更新・削除などの操作履歴を保存
  - 現時点では初期移行ログを保存している
  - 今後の編集・削除・復元でもここに履歴を残す想定

- `quick_templates`
  - 左側の専用テンプレート一覧を保存

- `rest_options`
  - 安静度の選択肢を保存

- `search_keywords`
  - 検索候補を保存

### テンプレート読み込みの考え方

通常画面の `GET /api/templates` は、`templates.current_version_id` が指す `template_versions.schema_json` を優先して返します。

互換用に `templates.schema_json` も残していますが、今後は `template_versions` を正とする想定です。

```text
templates
  id = mca
  current_version_id = 1
    ↓
template_versions
  id = 1
  template_id = mca
  version_number = 1
  schema_json = 入力項目定義
```

APIの返却形は既存画面に合わせて維持しています。

```json
{
  "id": "mca",
  "label": "MCA",
  "full": "MCA領域梗塞（中大脳動脈）",
  "vitals": {},
  "symptoms": {},
  "neuro": {},
  "rest": ""
}
```

### API一覧

画面用:

- `GET /api/templates`
- `GET /api/templates/<id>`
- `GET /api/quick-templates`
- `GET /api/rest-options`
- `GET /api/search-keywords`

確認・運用補助用:

- `GET /api/health`
- `GET /api/migrations`
- `GET /api/templates/<id>/versions`
- `GET /api/templates/<id>/versions/<version_id>`
- `GET /api/templates/<id>/logs`

現在は読み取り専用です。テンプレート追加・編集・削除APIはまだありません。

## 運用前の注意

現状はローカル試作用です。実運用前には少なくとも以下を対応してください。

- 本格的なマイグレーション管理を導入する
- DBファイルをリポジトリ配下やOneDrive同期配下ではなく、運用用の保護された場所に置く
- 本番用WSGIサーバーで起動する
- DBバックアップと復旧手順を決める
- テンプレート編集を追加する前に、権限・監査ログ・承認方針を決める

## 次のコミット候補

- テンプレートJSONスキーマ整理
- 管理画面設計
- 監査ログ設計
- 承認フロー設計
