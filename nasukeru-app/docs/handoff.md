# ナスケル 現状引継ぎメモ

このファイルは、後日 Codex / Claude / 人間が作業を再開するときに最初に読むための現状サマリです。

## 1. 現在の到達点

ナスケルは、看護記録テンプレートを選択し、観察項目を入力し、看護記録向けテキストをコピー出力するローカル試作用アプリです。

現在の構成:

- 通常画面: `/`
- 管理画面: `/admin`, `/admin/`
- バックエンド: Flask
- DB: SQLite
- テンプレート形式: `generic-v1` / `generic-v2` が主経路。条件付きテンプレートは `generic-v2`
- コピー形式: 単一出力は `text-v1`、複数の名前付き出力は `multi-v1`
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
- `copy_format` の未参照フィールドは警告する。`omitIfAllBlank` や `showIf` は制御参照であり、値が出力されないため未参照判定では出力参照に含めない
- 原則は警告してコピー可能。`blankPolicy=block` や `hardRange` 逸脱など明示された安全ルールだけコピーを止める
- テンプレート編集はバージョン追加で行い、既存バージョンを上書きしない
- 編集保存時は `draft` versionを作成し、履歴画面から公開すると通常画面に反映する
- rollbackは過去versionへ直接戻さず、過去versionの内容を複製した新しい `published` versionを作る
- 削除は論理削除

## 2. 現在登録済みのテンプレート

DB初期化後の標準テンプレートは脳梗塞5件、脳卒中共通1件、慢性硬膜下血腫1件です。

- `mca`: MCA領域梗塞
- `aca`: ACA領域梗塞
- `pca`: PCA領域梗塞
- `lacunar`: ラクナ梗塞／穿通枝梗塞
- `brainstem`: 脳幹梗塞
- `neuro_common`: 脳卒中共通（脳神経共通テンプレート）
- `chronic_subdural`: 慢性硬膜下血腫
- `cerebral_infarction`: 脳梗塞5件をまとめるtemplate group

脳梗塞5件の現在版は `generic-v1` です。脳梗塞5件の旧 `stroke-v1` 版は `template_versions` に履歴として残っています。`neuro_common` と `chronic_subdural` は `generic-v2` です。

脳卒中共通テンプレートは、`multi_select` と `number` を使い、条件付き詳細項目を持つ `generic-v2` テンプレートとして収束済みです。派生出力は `multi-v1` で実装済みです。状況グループは未実装です。

## 3. 重要なマイグレーション

`server/init_db.py` は冪等に実行できる前提です。

主なマイグレーション:

- `001`: 初期SQLite/API構成
- `002`: `template_versions` 追加
- `003`: 読み取り系運用API
- `004`: 脳梗塞5テンプレートを `generic-v1` に変換
- `005`: `generic-v1` の脳梗塞コピー出力を旧 `stroke-v1` 出力互換に調整
- `006`: 脳卒中共通テンプレート（`neuro_common`）を追加
- `010`: 組み込みテンプレートの臨床入力修正を `init_db.py` に統合
- `011`: `neuro_common` を正典定義へ整合
- `012`: 慢性硬膜下血腫テンプレート（`chronic_subdural`）を追加
- `013`: 既存DB向けに組み込みテンプレート定義を再収束
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

### copy_format

- `text-v1`: 単一のコピー出力。`lines` に文字列行または行オブジェクトを持つ
- `multi-v1`: 複数の名前付きコピー出力。`variants` に `{ id, label, lines }` を持つ

`multi-v1` は通常画面のコピー出力モーダルで出力形式を切り替えます。選択中variantに含まれない入力済みfieldがある場合は、コピー前警告として表示します。

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

`number` は通常画面では `type=text` + `inputmode=decimal` として描画します。全角数字、全角ピリオド、全角マイナス、前後空白を正規化してから型付き値へ変換します。`min` / `max` / `step` はdatasetに保持します。

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

テンプレート保存・管理詳細表示時には、schemaにあるがcopy_formatの出力参照に現れないfieldを `warnings` として返します。これは導出値でDB保存しません。警告はpublishをブロックしません。

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
- `docs/legacy-cleanup-inventory.md`: 旧設計依存とRemoval Gateの棚卸し

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
  - 未参照フィールドがあれば201レスポンスに `warnings` を含める
- `POST /api/templates/<id>/versions`
  - 必須: `base_version_id`
  - 管理画面で読み込んだ `current_version_id` と保存時点の最新版が違う場合は `409`
  - 新versionは `draft`
  - 未参照フィールドがあれば201レスポンスに `warnings` を含める
- `POST /api/templates/<id>/versions/<version_id>/publish`
  - `draft` versionを `published` にし、`templates.current_version_id` を切り替える
  - `draft.base_version_id` が現在の `current_version_id` と違う場合は `409`
  - 高リスク変更がある場合は `confirm_high_risk: true` が必要
- `POST /api/templates/<id>/versions/<version_id>/rollback`
  - 指定versionの内容から新versionを作成し、その新versionを `published` にする
- `POST /api/templates/<id>/delete`
- `POST /api/templates/<id>/restore`
- `GET /api/templates/<id>/versions`
- `GET /api/templates/<id>/versions/<version_id>`
  - schemaを含む詳細レスポンスでは導出 `warnings` を含める
- `GET /api/templates/<id>/logs`

管理系POSTは以下を要求します。

- `X-Nasukeru-Local: 1`
- `Origin` または `Referer` が localhost / 127.0.0.1 / ::1

## 7. 管理画面の現状

Phase 7でTemplate Builderを追加済みです。

できること:

- セクション追加 / 削除
- 項目追加 / 削除
- 項目ID、ラベル、種別、表示順、単位、placeholder、補足説明、`min`、`max`、`step` を編集
- 既存schemaの `requiredWarning` / `allowEmpty` など、UIに出ていないfield propertyも保存時に保持する
- `blankPolicy`、`hardRange`、`warningRange` をフォームで編集
- 選択肢を `value` / `label` の行として追加 / 削除
- `visibleIf`、`requiredIf`、copy line `showIf` を単純条件として編集
- 条件値はnumberなら数値入力、selectならoption pickerで編集する
- コピー出力行を追加 / 削除
- コピー出力行へ入力項目参照 `{{section.field}}` を挿入
- 下書きversionの公開
- 過去versionの復元公開
- JSONプレビューとDeveloper Mode / JSON編集を残す
- 未参照フィールド警告をライブプレビュー、詳細表示、保存後トーストで表示する

制限:

- 条件UIは単純条件のみ。`and` / `or` / `not` のネスト条件はDeveloper Modeで編集する
- copy lineの高度な表現や `multi-v1` はDeveloper Modeで編集する
- 状況グループ、承認フローは未実装

Phase 11で追加された安全仕様:

- number fieldの不正文字列は `invalid_number` としてコピー不可
- copy rendererの `unresolvedRefs` はcopy安全警告へ統合し、`__` が残る出力は確認なしに通さない
- group tabの入力状態はカード単位で保持し、groupを離れると破棄する
- `visibleIf` は固定点に収束するまで評価し、収束しない場合はコピー不可
- backendは `visibleIf` cycle、number/select/multi_select条件値の型不一致、non-select fieldの `options` を拒否する
- DB triggerはcurrent versionを直接 `retired` にする更新を拒否する

## 8. Phase 12 Simple Authoringの現状

通常のテンプレート作成・編集導線はSimple Editorへ寄せています。

実装済み:

- 新規作成入口:
  - 似ているテンプレートから作る
  - 白紙から作る
- 白紙作成は内部的に `generic-v2` 固定
- Simple Editor通常UIでは、内部ID、schema形式、JSONを入力させない
- 項目編集は日本語表示:
  - 文字を入力
  - 長い文章を入力
  - 1つ選ぶ
  - 複数選ぶ
  - 数字を入力
- 未入力時動作は日本語表示:
  - 未入力でも問題なし
  - コピー前に確認する
  - 未入力ではコピーできない
- optionの内部valueは保持し、通常UIではlabelだけを編集
- 自動コピー文は `omitIfAllBlank` / `segments` を使い、空欄fieldを出力しない
- 既存custom copy_formatは通常編集で勝手に上書きしない
- 一覧に「下書きを確認」を追加し、通常publish導線は履歴から外した
- Simple condition builderで単純な `visibleIf` / `requiredIf` を編集できる
- Discovery Management UIでquick template、search keyword、template groupを編集できる
- Developer ModeはJSON直接編集に対応済み。高度なschema / copy_format編集はこの導線で扱う

制限:

- 条件UIは単純条件中心。`and` / `or` / `not` のネスト条件はDeveloper Modeで編集する
- `multi-v1` はDeveloper Mode / JSONで編集する。専用フォームUIは未実装
- Previewは通常画面rendererを使うが、コピー前safety warningの完全なUI再現は通常画面側で確認する

## 9. 次にやること

推奨順序:

1. 状況グループを `generic-v2` の制御field + `multi-v1` variant 連動として設計・実装する
2. バージョン差分ビューとimport/exportを追加する
3. 承認フロー、認証、RBACを病棟展開前提で設計する
4. `docs/legacy-cleanup-inventory.md` のRemoval Gateを満たした項目から段階的に削除する

## 10. 検証コマンド

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

## 11. 注意点

- `server/nasukeru.db` はローカル生成物でGit管理対象外
- マイグレーションは既存バージョンを上書きせず、新バージョンを追加する
- 医療記録文面は暗黙に変えない
- 既存テンプレートの出力互換を崩す変更は、必ずスナップショット相当のテストを追加する
- 認証は未実装。ローカル専用前提で、外部公開しない
- `NASUKERU_HOST` はlocalhost系を前提にする。localhost系以外へbindする場合は `NASUKERU_ALLOW_EXTERNAL=1` が必要
- 書き込みAPIのリクエストサイズ上限は1MB
- SQLiteやDB未準備の生エラー詳細はレスポンスに出さず、ログに残す
