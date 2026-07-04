# ナスケル 現状引継ぎメモ

このファイルは、後日 Codex / Claude / 人間が作業を再開するときに最初に読むための現状サマリです。

## 1. 現在の到達点

ナスケルは、看護記録テンプレートを選択し、観察項目を入力し、看護記録向けテキストをコピー出力するローカル試作用アプリです。

現在の構成:

- 通常画面: `/`
- 管理画面: `/admin`, `/admin/`
- バックエンド: Flask
- DB: SQLite
- テンプレート形式: `generic-v1` が主経路。条件付きテンプレートは `generic-v2`
- 旧形式: `stroke-v1` は履歴・後方互換用として残す
- 管理画面の新規追加は `generic-v1` / `generic-v2` を選択可能。`stroke-v1` の新規作成は画面から選ばせない
- 通常画面のroutingは `target` による明示指定。`template` と `group` をサポートする

重要方針:

- AI生成は使わない
- 患者情報や入力内容は保存しない
- 入力初期値は空欄
- 書き込みAPIでも、`stroke-v1` の初期値入りschemaは400で拒否する
- schema / copy_format の未知キーは400で拒否する
- `copy_format` の参照は `generic-v1` / `generic-v2` schema に存在するfieldだけ許可する
- 原則は警告してコピー可能。`blankPolicy=block` や `hardRange` 逸脱など明示された安全ルールだけコピーを止める
- テンプレート編集はバージョン追加で行い、既存バージョンを上書きしない
- 編集保存時は `draft` versionを作成し、履歴画面から公開すると通常画面に反映する
- rollbackは過去versionへ直接戻さず、過去versionの内容を複製した新しい `published` versionを作る
- 削除は論理削除

## 2. 現在登録済みのテンプレート

DB初期化後の標準テンプレートは脳梗塞5件と脳卒中共通1件です。

- `mca`: MCA領域梗塞
- `aca`: ACA領域梗塞
- `pca`: PCA領域梗塞
- `lacunar`: ラクナ梗塞／穿通枝梗塞
- `brainstem`: 脳幹梗塞
- `neuro_common`: 脳卒中共通（脳神経共通テンプレート）
- `cerebral_infarction`: 脳梗塞5件をまとめるtemplate group

現在版は `generic-v1` です。脳梗塞5件の旧 `stroke-v1` 版は `template_versions` に履歴として残っています。

追加検討中だが未取り込み:

- `C:\Users\kazum\Downloads\慢性硬膜下血腫_ナスケル用テンプレート_エンジニア共有.txt`

脳卒中共通テンプレートは、`multi_select` と `number` を使う平坦な `generic-v1` テンプレートとして取り込み済みです。条件分岐は `generic-v2` で実装済みです。状況グループ、派生出力は未実装です。

## 3. 重要なマイグレーション

`server/init_db.py` は冪等に実行できる前提です。

主なマイグレーション:

- `001`: 初期SQLite/API構成
- `002`: `template_versions` 追加
- `003`: 読み取り系運用API
- `004`: 脳梗塞5テンプレートを `generic-v1` に変換
- `005`: `generic-v1` の脳梗塞コピー出力を旧 `stroke-v1` 出力互換に調整
- `006`: 脳卒中共通テンプレート（`neuro_common`）を追加
- routing tables: `template_groups`, `template_group_items`

`005` の目的:

- 既存stroke項目だけを入力した場合、旧 `stroke-v1` のコピー出力と文字列一致させる
- `stroke_findings` は空欄なら出力しない
- `stroke_findings` に入力した場合のみ追加行として出力する
- `その他神経症状` は旧挙動に合わせて改行分割する

## 4. schema と copy_format

### schemaFormat

- `schemaFormat` なし: `stroke-v1` とみなす
- `stroke-v1`: 旧脳梗塞固定schema
- `generic-v1`: section / field ベースの可変schema
- `generic-v2`: `generic-v1` に条件式を追加した可変schema

### generic-v1

`generic-v1` は以下の構造です。

```json
{
  "schemaFormat": "generic-v1",
  "sections": [
    {
      "id": "vitals",
      "label": "バイタル",
      "displayOrder": 1,
      "fields": [
        {
          "id": "jcs",
          "label": "JCS",
          "type": "text",
          "allowEmpty": true,
          "requiredWarning": true
        }
      ]
    }
  ]
}
```

現在の field type:

- `text`
- `textarea`
- `select`
- `multi_select`
- `number`

`select` / `multi_select` の `options` は以下を基本形にします。

```json
{ "value": "oxygen", "label": "O2使用" }
```

旧来の文字列optionも受け付けますが、API返却時は `{ "value": 文字列, "label": 文字列 }` に正規化されます。通常画面ではDOM内部値に `value`、表示とコピー出力に `label` を使います。将来のCondition Engineは `label` ではなく `value` を参照する前提です。

通常画面のgeneric入力値は `js/generic-values.js` を通して型付き状態に変換します。`number` の空欄は `null`、`0` は有効値、`multi_select` は配列として扱います。グループタブの一時状態、コピー出力、未入力警告はこの共通ルールを使います。

### generic-v2 condition

`generic-v2` では条件式を使えます。

- field `visibleIf`: 条件が真のときだけ表示
- field `requiredIf`: 条件が真かつ表示中のとき未入力警告対象
- copy line `showIf`: 条件が真のときだけコピー出力

対応operator:

- `eq` / `neq`
- `in` / `not_in`
- `contains`
- `gt` / `gte` / `lt` / `lte`
- `is_blank`
- `and` / `or` / `not`

条件式は `js/condition-engine.js` の `evaluateCondition(condition, values)` で評価します。条件は `label` ではなく内部 `value` を参照します。非表示になったfieldの値はclearし、hidden値がcopy、required判定、validationへ漏れない方針です。

### Safety Layer

`generic-v2` では安全レイヤーを使えます。

- `blankPolicy`: `allow` / `warn` / `block`
- `hardRange`: 範囲外ならblock
- `warningRange`: 範囲外ならwarn

通常画面では `js/safety-rules.js` が `{ blocks, warnings }` を返します。`block` がある場合はコピー不可、`warn` は確認後コピー可能です。`requiredWarning=true` は後方互換として `blankPolicy=warn` 相当に扱います。

`js/copy-renderer.js` は `renderGenericTemplateCopyResult()` で `{ text, unresolvedRefs, warnings }` を返せます。既存の `renderGenericTemplateCopyText()` は互換用に残しています。

テンプレート更新時には以下を高リスク変更として検出し、レスポンスの `high_risk_changes` と監査ログ `diff.high_risk_changes` に残します。

- field削除
- `blankPolicy` 緩和
- `visibleIf` / `requiredIf` 変更
- `requiredIf` 削除
- `hardRange` 緩和
- copy line削除または変更

### copy_format_json

`copy_format_json` は `text-v1` を使います。

```json
{
  "format": "text-v1",
  "lines": [
    "JCS{{vitals.jcs}}",
    {
      "text": "バレー徴候：{{neuro.barre}}",
      "omitIfAllBlank": ["neuro.barre"]
    },
    {
      "text": "{{neuro.other}}",
      "splitLinesFrom": "neuro.other",
      "omitIfAllBlank": ["neuro.other"]
    }
  ]
}
```

対応済みの行オブジェクト属性:

- `text`: 出力行テンプレート
- `omitIfAllBlank`: 指定fieldがすべて空欄なら行を省略
- `splitLinesFrom`: 指定fieldを改行で分割し、空行を除いて複数行出力

## 5. 主要ファイル

フロント:

- `index.html`: 通常入力画面
- `admin.html`: 管理画面
- `js/templates.js`: API呼び出し境界
- `js/app.js`: 通常画面描画。`generic-v1` 動的描画を担当
- `js/admin.js`: 管理画面。テンプレート一覧、追加、編集、削除、復元、履歴を担当
- `js/admin-builder.js`: 管理画面のTemplate Builder。セクション、項目、選択肢、条件、コピー行をフォームで編集する
- `js/copy-format.js`: DOM入力値収集とコピーUI
- `js/copy-renderer.js`: `text-v1`, `omitIfAllBlank`, `splitLinesFrom` の純粋関数renderer
- `js/validation.js`: 未入力警告
- `js/field-meta.js`: 旧 `stroke-v1` 互換用の固定ラベル

バックエンド:

- `server/app.py`: Flask API
- `server/init_db.py`: DB作成、シード、マイグレーション
- `server/template_schema.py`: schema / copy_format 検証・正規化
- `server/smoke_test.py`: スモークテスト

設計:

- `README.md`: 全体説明と動かし方
- `docs/handoff.md`: この現状引継ぎメモ
- `docs/variable-template-migration-design.md`: 可変テンプレート移行設計

## 6. API概要

通常画面:

- `GET /api/templates`
- `GET /api/templates/<id>`
- `GET /api/quick-templates`
- `GET /api/template-groups/<id>`
- `GET /api/rest-options`
- `GET /api/search-keywords`

管理画面:

- `GET /api/admin/templates`
- `GET /api/admin/templates/<id>`
- `POST /api/templates`
- `POST /api/templates/<id>/versions`
  - 必須: `base_version_id`
  - 管理画面で読み込んだ `current_version_id` と保存時点の最新版が違う場合は `409`
  - 新versionは `draft`
- `POST /api/templates/<id>/versions/<version_id>/publish`
  - `draft` versionを `published` にし、`templates.current_version_id` を切り替える
  - 高リスク変更がある場合は `confirm_high_risk: true` が必要
- `POST /api/templates/<id>/versions/<version_id>/rollback`
  - 指定versionの内容から新versionを作成し、その新versionを `published` にする
- `POST /api/templates/<id>/delete`
- `POST /api/templates/<id>/restore`
- `GET /api/templates/<id>/versions`
- `GET /api/templates/<id>/versions/<version_id>`
- `GET /api/templates/<id>/logs`

管理系POSTは以下を要求します。

- `X-Nasukeru-Local: 1`
- `Origin` または `Referer` が localhost / 127.0.0.1 / ::1

## 7. 管理画面の現状

Phase 7でTemplate Builderを追加済みです。

できること:

- セクション追加 / 削除
- 項目追加 / 削除
- 項目ID、ラベル、種別、単位、placeholder、補足説明を編集
- `blankPolicy`、`hardRange`、`warningRange` をフォームで編集
- 選択肢を `value` / `label` の行として追加 / 削除
- `visibleIf`、`requiredIf`、copy line `showIf` を単純条件として編集
- コピー出力行を追加 / 削除
- コピー出力行へ入力項目参照 `{{section.field}}` を挿入
- 下書きversionの公開
- 過去versionの復元公開
- JSONプレビューとDeveloper Mode / JSON編集を残す

制限:

- 条件UIは単純条件のみ。`and` / `or` / `not` のネスト条件はDeveloper Modeで編集する
- copy lineの高度な表現はDeveloper Modeで編集する
- 状況グループ、派生出力、承認フローは未実装

## 8. 次にやること

推奨順序:

1. 慢性硬膜下血腫テンプレートを `generic-v2` 前提で取り込む設計を起こす
2. 状況グループ、派生出力の設計を起こす
3. 管理画面の承認フローを追加する
4. 旧 `templates.schema_json` 互換の整理条件を詰める

## 9. 検証コマンド

```powershell
py -3.10 -m py_compile server\template_schema.py server\init_db.py server\app.py server\smoke_test.py
py -3.10 server\smoke_test.py
```

JS構文チェック:

```powershell
& 'C:\Users\kazum\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' --check js\app.js
& 'C:\Users\kazum\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' --check js\admin-builder.js
& 'C:\Users\kazum\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' --check js\admin.js
& 'C:\Users\kazum\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' --check js\copy-renderer.js
& 'C:\Users\kazum\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' --check js\copy-format.js
& 'C:\Users\kazum\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' --check js\validation.js
& 'C:\Users\kazum\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' --test tests\copy-renderer.test.js tests\generic-values.test.js tests\condition-engine.test.js tests\safety-rules.test.js
```

DB初期化:

```powershell
py -3.10 server\init_db.py
```

サーバ起動:

```powershell
py -3.10 server\app.py
```

## 10. 注意点

- `server/nasukeru.db` はローカル生成物でGit管理対象外
- マイグレーションは既存バージョンを上書きせず、新バージョンを追加する
- 医療記録文面は暗黙に変えない
- 既存テンプレートの出力互換を崩す変更は、必ずスナップショット相当のテストを追加する
- 認証は未実装。ローカル専用前提で、外部公開しない
