# Legacy Cleanup Inventory

Phase 9では、旧設計をすぐ削除せず、依存関係を明示してから段階的に整理する。

## 方針

- `template_versions.schema_json` をdefinition source of truthにする。
- `templates.schema_json` は互換用に残すが、新規読み取りコードでは参照しない。
- `stroke-v1` は履歴表示、旧version閲覧、出力互換テストのため当面残す。
- 物理削除はPhase 9後段または別Phaseで行う。

## 棚卸し

| 対象 | 現状 | 方針 |
| --- | --- | --- |
| `templates.schema_json` | 作成・公開時に互換用として更新する | 新規読み取りでは参照しない。削除は全履歴閲覧とrollback確認後 |
| `template_versions.schema_json` | 現在の主定義 | source of truth |
| `quick_templates.action` | 旧routing互換値 | `target_type` / `target_id` が主。削除は既存DB移行確認後 |
| `search_keywords.template_action` | 旧routing互換値 | `target_type` / `target_id` が主。削除は既存DB移行確認後 |
| `stroke-v1` schema | 旧脳梗塞固定schema | 新規作成UIでは選ばせない。履歴・互換用に維持 |
| `field-meta.js` stroke固定ラベル | stroke-v1互換と一部共通ラベル | generic系ではschema labelを優先 |
| `category === "stroke"` fallback | 通常画面の保険的fallback | routing targetが揃っているため将来削除候補 |

## Removal Gate

削除前に以下を満たすこと。

- main code referenceが0であること。
- migration dependencyが残っていないこと。
- old version detailを閲覧できること。
- rollback publishが維持されること。
- legacy output testが維持されること。
- smoke testで通常画面、履歴、公開、rollbackが通ること。
