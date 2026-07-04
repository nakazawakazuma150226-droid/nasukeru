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
  admin.html
  README.md
  requirements.txt
  .gitignore
  assets/
    nasukeru-icon.jpg
  css/
    styles.css
  docs/
    handoff.md
    variable-template-migration-design.md
  js/
    templates.js
    field-meta.js
    validation.js
    copy-renderer.js
    copy-format.js
    app.js
    admin.js
  tests/
    copy-renderer.test.js
  server/
    app.py
    init_db.py
    template_schema.py
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
- `js/field-meta.js` は入力項目キーと表示・警告・コピー出力用ラベルを対応付ける
- `server/` はAPI、DB初期化、スモークテストを置くバックエンド領域
- `server/nasukeru.db` はローカル生成物なのでGitには入れない
- Flaskは必要な静的ファイルだけをルート定義して配信するホワイトリスト方式にしている
- 配信対象は `index.html`, `assets/`, `css/`, `js/` で、`server/` や `.gitignore` へのルートは定義しない

## 各ファイルの役割

- `index.html`
  - 画面の骨組み
  - CSS/JSの読み込み

- `css/styles.css`
  - レイアウト、見た目、レスポンシブ対応

- `js/templates.js`
  - Flask API からテンプレート、クイックリスト、安静度選択肢を取得する境界
  - 管理画面のPOSTでは `X-Nasukeru-Local: 1` ヘッダ付与もここに集約する

- `js/field-meta.js`
  - `data-vkey`, `data-skey`, `data-mmt` と警告・コピー出力用ラベルを対応付ける
  - 現時点ではJS内の最小メタ定義とし、DBスキーマへの移譲は将来の整理対象

- `js/validation.js`
  - 未入力警告の判定と表示

- `js/copy-format.js`
  - 画面入力値を集めてコピー出力文を生成
  - クリップボードコピー

- `js/copy-renderer.js`
  - `copy_format_json` からテキストを生成する純粋関数
  - Nodeテストで `omitIfAllBlank` / `splitLinesFrom` / 空欄置換を検証

- `js/app.js`
  - 画面生成、検索、タブ切り替え、イベント処理

- `js/admin.js`
  - `/admin` の一覧表示、モーダル、画面バリデーション、管理API呼び出しを制御する
  - `stroke-v1` は既存の専用フォーム、`generic-v1` はJSON編集フォームで扱う
  - 編集時は現行 schema を読み込んで新バージョンとして保存する

- `server/init_db.py`
  - SQLite DBを作成し、足りないテーブルと初期テンプレートデータを補う
  - 既存テーブルは削除しない
  - 既存テンプレートに `template_versions` がない場合は version 1 として移行する
  - DB構造変更の適用状況を `schema_migrations` に記録する

- `server/template_schema.py`
  - テンプレートJSONの構造・型・必須キーを検証する
  - API保存前とDB初期化時の共通バリデーションとして使う

- `server/app.py`
  - Flaskで画面とAPIを配信する
  - 現在のAPI:
    - `GET /api/health`
    - `GET /api/admin/templates`
    - `GET /api/admin/templates/<id>`
    - `GET /api/templates`
    - `GET /api/templates/<id>`
    - `GET /api/templates/<id>/versions`
    - `GET /api/templates/<id>/versions/<version_id>`
    - `GET /api/templates/<id>/logs`
    - `GET /api/quick-templates`
    - `GET /api/template-groups/<id>`
    - `GET /api/rest-options`
    - `GET /api/search-keywords`
    - `GET /api/migrations`
    - `POST /api/templates`
    - `POST /api/templates/<id>/versions`
    - `POST /api/templates/<id>/delete`
    - `POST /api/templates/<id>/restore`

- `admin.html`
  - ローカル管理用のテンプレート管理画面
  - `/admin` と `/admin/` で配信される
  - 新規追加、schema編集、論理削除、復元、履歴・監査ログ閲覧を行う

- `server/smoke_test.py`
  - 主要APIが期待したステータスを返すか確認する
  - `server/` や `.gitignore` が公開されていないことも確認する

- `docs/handoff.md`
  - 後日作業再開時に最初に読む現状引継ぎメモ
  - 現在の到達点、主要ファイル、マイグレーション、次の作業順序を集約する

- `docs/variable-template-migration-design.md`
  - DSAなど新規項目を持つテンプレートに備えた可変schema設計
  - 既存脳梗塞テンプレートを最終的に可変テンプレートへ移行する方針

## 可変テンプレートの段階導入

現在は `stroke-v1` と `generic-v1` を併存させた上で、脳梗塞5テンプレートも `generic-v1` へ移行済みです。通常画面の表示とコピー出力も `generic-v1` を主経路にし、`stroke-v1` は旧バージョン・後方互換用として残す Phase 5 です。

- `schemaFormat` が無い既存テンプレートは `stroke-v1` として扱う
- `generic-v1` は `sections` と `fields` を持つ可変schemaとして保存できる
- `generic-v1` の field type は `text` / `textarea` / `select` / `multi_select` / `number`
- 通常入力画面は `stroke-v1` を従来タブUI、`generic-v1` を section/field ベースの動的UIとして表示する
- `generic-v1` の入力初期値は安全側で空欄にする
- `generic-v1` のコピー出力は `copy_format_json` の `text-v1` 形式を優先する
- `copy_format_json` が無い場合は暫定の汎用形式で出力する
- `text-v1` は `lines` 配列と `{{section.field}}` 参照をサポートする
- `text-v1` の各行は文字列、または `{ "text": "...", "omitIfAllBlank": ["section.field"], "splitLinesFrom": "section.field" }` の行オブジェクトで定義できる
- `omitIfAllBlank` は指定した入力がすべて空欄のとき、その行をコピー出力から省略する
- `splitLinesFrom` は指定した入力を改行で分割し、空行を除いて複数行として出力する
- `copy_format` の参照先は `generic-v1` schema に存在する field のみ許可する
- 複雑な条件分岐や高度な整形は次フェーズで設計・実装する
- 管理画面の新規追加は `generic-v1` 固定とし、`stroke-v1` は旧バージョン・後方互換用として残す
- 通常画面のクイックリストと検索は `target` で明示的に `template` または `group` を開く
- 脳梗塞5テンプレートは `cerebral_infarction` groupとして表示し、group内タブは既存generic rendererを再利用する

脳梗塞5テンプレートは `generic-v1` へ移行済みです。共通項目に加えて、MCA/ACA/PCA/ラクナ/脳幹ごとの個別観察項目を空欄フィールドとして持ちます。既存の `stroke-v1` 版は履歴に残し、DB初期化時のマイグレーション `004` で新バージョンとして適用します。マイグレーション `005` では、既存stroke項目だけを入力した場合に旧 `stroke-v1` のコピー出力と一致する `copy_format_json` へ更新します。

脳卒中共通テンプレート（`neuro_common`）は `generic-v1` として追加済みです。`multi_select` と `number` を使い、意識レベル、バイタル、瞳孔・眼球所見、運動機能、NIHSS、高次脳機能、頭蓋内圧亢進症状、嚥下、安静度・ADL、排泄、治療を平坦な共通観察項目として扱います。条件分岐、状況グループ、派生出力は含めず、次フェーズで扱います。

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

`NASUKERU_HOST=0.0.0.0` と `NASUKERU_DEBUG=1` を同時に指定しないでください。Flaskのデバッガが外部から到達可能になると、任意コード実行につながる危険があります。

## 動作確認

主要APIと非公開ファイルの遮断をまとめて確認できます。

```powershell
py -3.10 server\smoke_test.py
```

コピー出力rendererの単体テスト:

```powershell
& 'C:\Users\kazum\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' --test tests\copy-renderer.test.js
```

ヘルスチェックだけ確認する場合:

```text
http://127.0.0.1:8000/api/health
```

## DB/API構成

現在は通常画面向けの読み取りAPIに加えて、ローカル管理用のテンプレート追加・編集・削除・復元APIと管理画面を持ちます。承認フローは未実装です。

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
- `GET /api/template-groups/<id>`
- `GET /api/rest-options`
- `GET /api/search-keywords`

確認・運用補助用:

- `GET /api/health`
- `GET /api/migrations`
- `GET /api/templates/<id>/versions`
- `GET /api/templates/<id>/versions/<version_id>`
- `GET /api/templates/<id>/logs`
- `GET /api/templates?include_inactive=1`

ローカル管理用:

- `GET /api/admin/templates`
  - 管理画面の一覧用に、削除済みを含む全テンプレートのメタ情報を返す
  - `is_active`, `status`, `current_version_id`, `current_version_number`, `created_at`, `updated_at` を含む
- `GET /api/admin/templates/<id>`
  - 管理画面の編集用に、単体テンプレートのschema、copy_format、現在版番号を返す
- `POST /api/templates`
  - テンプレートを追加し、`template_versions` に version 1 を作成する
  - 必須: `id`, `label`, `full`, `category`, `schema`, `change_reason`
  - `id` は `^[a-z0-9_-]{1,32}$`
- `POST /api/templates/<id>/versions`
  - 既存テンプレートを上書きせず、新しいバージョンとして編集内容を追加する
  - 必須: `schema`, `change_summary`, `change_reason`
- `POST /api/templates/<id>/delete`
  - 物理削除せず `is_active = 0` にする
  - 必須: `reason`
- `POST /api/templates/<id>/restore`
  - 論理削除済みテンプレートを復元する
  - 必須: `reason`

すべての `POST` は `X-Nasukeru-Local: 1` と、`localhost` / `127.0.0.1` / `::1` の `Origin` または `Referer` を必須にしています。これは認証ではなく、ローカル起動中のブラウザ経由攻撃を軽く防ぐためのものです。外部公開や多人数運用を行う場合は、別途認証・権限管理・CSRF対策が必要です。

### 管理画面

`/admin` または `/admin/` でローカル管理画面を開けます。通常画面とは分離しており、テンプレートの追加、schema編集、論理削除、復元、バージョン履歴・監査ログ確認を行います。通常画面のヘッダーから管理画面へ、管理画面のヘッダーから通常画面へ移動できます。

管理画面の最小版では `label` / `full` / `category` の既存テンプレート編集は行いません。編集対象は schema の新バージョン作成です。削除済みテンプレートは編集できませんが、履歴と監査ログは確認できます。

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
