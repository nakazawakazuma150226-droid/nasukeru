# ナスケル 現状引継ぎメモ

このファイルは、後日 Codex / Claude / 人間が作業を再開するときに最初に読むための現状サマリです。

## 1. 現在の到達点

ナスケルは、看護記録テンプレートを選択し、観察項目を入力し、看護記録向けテキストをコピー出力するローカル試作用アプリです。

現在の構成:

- 通常画面: `/`
- 管理画面: `/admin`, `/admin/`
- バックエンド: Flask
- DB: SQLite
- テンプレート形式: `generic-v1` が主経路
- 旧形式: `stroke-v1` は履歴・後方互換用として残す

重要方針:

- AI生成は使わない
- 患者情報や入力内容は保存しない
- 入力初期値は空欄
- 未入力警告は出すがコピーは止めない
- テンプレート編集はバージョン追加で行い、既存バージョンを上書きしない
- 削除は論理削除

## 2. 現在登録済みのテンプレート

DB初期化後の標準テンプレートは脳梗塞5件です。

- `mca`: MCA領域梗塞
- `aca`: ACA領域梗塞
- `pca`: PCA領域梗塞
- `lacunar`: ラクナ梗塞／穿通枝梗塞
- `brainstem`: 脳幹梗塞

現在版は `generic-v1` です。旧 `stroke-v1` 版は `template_versions` に履歴として残っています。

追加検討中だが未取り込み:

- `C:\Users\kazum\Downloads\ナスケル_脳卒中共通テンプレート_エンジニア向け (1).txt`
- `C:\Users\kazum\Downloads\慢性硬膜下血腫_ナスケル用テンプレート_エンジニア共有.txt`

これらを取り込む前に、まず `generic-v2` の設計を行う予定です。初期スコープは `multi_select` と `number` の追加に絞る方針です。条件分岐、状況グループ、派生出力は次フェーズです。

## 3. 重要なマイグレーション

`server/init_db.py` は冪等に実行できる前提です。

主なマイグレーション:

- `001`: 初期SQLite/API構成
- `002`: `template_versions` 追加
- `003`: 読み取り系運用API
- `004`: 脳梗塞5テンプレートを `generic-v1` に変換
- `005`: `generic-v1` の脳梗塞コピー出力を旧 `stroke-v1` 出力互換に調整

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

次に追加予定:

- `multi_select`
- `number`

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
- `js/admin.js`: 管理画面。現状、`generic-v1` schema/copy_format はJSON編集が中心
- `js/copy-format.js`: コピー出力生成。`text-v1`, `omitIfAllBlank`, `splitLinesFrom` 対応
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
- `GET /api/rest-options`
- `GET /api/search-keywords`

管理画面:

- `GET /api/admin/templates`
- `GET /api/admin/templates/<id>`
- `POST /api/templates`
- `POST /api/templates/<id>/versions`
- `POST /api/templates/<id>/delete`
- `POST /api/templates/<id>/restore`
- `GET /api/templates/<id>/versions`
- `GET /api/templates/<id>/versions/<version_id>`
- `GET /api/templates/<id>/logs`

管理系POSTは以下を要求します。

- `X-Nasukeru-Local: 1`
- `Origin` または `Referer` が localhost / 127.0.0.1 / ::1

## 7. 管理画面の現状課題

非エンジニアには、現在のテンプレート作成・編集は分かりにくいです。

理由:

- `generic-v1 schema JSON` を直接編集する必要がある
- `copy_format JSON` を直接編集する必要がある
- セクション追加、項目追加、選択肢編集がフォーム化されていない

今後の改善候補:

- JSONを隠してフォーム型テンプレートビルダーにする
- セクション追加 / 項目追加 / 選択肢追加をボタン操作にする
- コピー文も行単位エディタにする
- JSON編集は「詳細設定」扱いにする

## 8. 次にやること

推奨順序:

1. 現在の互換修正をレビューし、問題なければGitHubへpushする
2. `generic-v2` 設計を起こす
3. `generic-v2` の最初の実装は `multi_select` と `number` に絞る
4. 脳卒中共通テンプレートを `generic-v2` で追加できるか検討する
5. 慢性硬膜下血腫テンプレートは条件分岐が必要なので、次フェーズで扱う

## 9. 検証コマンド

```powershell
py -3.10 -m py_compile server\template_schema.py server\init_db.py server\app.py server\smoke_test.py
py -3.10 server\smoke_test.py
```

JS構文チェック:

```powershell
& 'C:\Users\kazum\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' --check js\app.js
& 'C:\Users\kazum\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' --check js\admin.js
& 'C:\Users\kazum\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' --check js\copy-format.js
& 'C:\Users\kazum\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' --check js\validation.js
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
