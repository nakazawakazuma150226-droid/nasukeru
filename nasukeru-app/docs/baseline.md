# ナスケル Baseline

Baseline commit: `887fe88a818a27f86e04a124014aec40aebdb619`

この文書は、段階実装の比較対象として現在の仕様を固定するためのメモです。希望仕様ではなく、現時点の実装状態を記録します。

## 登録済みテンプレート

DB初期化後の標準テンプレートは6件です。

| id | label | category | schemaFormat | 備考 |
| --- | --- | --- | --- | --- |
| `mca` | MCA | stroke | generic-v1 | 旧stroke-v1版は履歴に残る |
| `aca` | ACA | stroke | generic-v1 | 旧stroke-v1版は履歴に残る |
| `pca` | PCA | stroke | generic-v1 | 旧stroke-v1版は履歴に残る |
| `lacunar` | ラクナ | stroke | generic-v1 | 旧stroke-v1版は履歴に残る |
| `brainstem` | 脳幹 | stroke | generic-v1 | 旧stroke-v1版は履歴に残る |
| `neuro_common` | 脳卒中共通 | neuro_common | generic-v1 | migration `006` で追加 |

## generic-v1

対応済みfield type:

- `text`
- `textarea`
- `select`
- `multi_select`
- `number`

現在の制約:

- unknown schema keyは拒否する
- section id / field idの重複は拒否する
- `select` / `multi_select` は `options` が必須
- `number` は `min` / `max` / `step` を任意指定できる
- `copy_format` の参照先はschema内fieldに存在する必要がある

## copy_format_json

形式は `text-v1` です。

対応済み:

- 文字列行
- 行オブジェクト `text`
- `omitIfAllBlank`
- `splitLinesFrom`

未対応:

- `showIf`
- Condition AST
- structured render result
- unresolvedRefsの構造返却

## コピー出力互換

脳梗塞5テンプレートは、既存stroke項目だけを入力した場合に旧 `stroke-v1` 出力と文字列一致することを `server/smoke_test.py` で確認しています。

確認対象:

- empty
- representative
- branching
- `stroke_findings` は空欄なら出力しない
- `stroke_findings` は入力時だけ追加行として出力する

## migrations

| version | name |
| --- | --- |
| `001` | initial sqlite template api |
| `002` | versioned template schema |
| `003` | read-only operational APIs |
| `004` | convert stroke templates to generic v1 |
| `005` | align stroke generic copy output with stroke v1 |
| `006` | add neuro common template |

## API

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

運用確認:

- `GET /api/migrations`
- `GET /api/health`

## 現在のrouting制約

Phase 0時点では、通常画面のroutingはまだ明示target方式ではありません。

- quick templateは `label` を検索欄に入れて `showTemplateForQuery(label)` を呼ぶ
- search keyword APIは `keyword` のみ返す
- `quick_templates.action` / `search_keywords.template_action` は通常画面で十分使われていない
- `showTemplateForQuery()` には `category === "stroke"` のfallbackが残っている

この制約はPhase 1で修正します。

## 検証コマンド

```powershell
py -3.10 -m py_compile server\template_schema.py server\init_db.py server\app.py server\smoke_test.py
py -3.10 server\smoke_test.py
& 'C:\Users\kazum\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' --check js\app.js
& 'C:\Users\kazum\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' --check js\admin.js
& 'C:\Users\kazum\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' --check js\copy-renderer.js
& 'C:\Users\kazum\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' --check js\copy-format.js
& 'C:\Users\kazum\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' --check js\validation.js
& 'C:\Users\kazum\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' --test tests\copy-renderer.test.js
```

