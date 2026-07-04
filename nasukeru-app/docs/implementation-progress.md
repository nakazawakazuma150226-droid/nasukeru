# ナスケル 段階実装進捗

## Phase 0: 開発基準線の固定

Status: PASS

Base: `887fe88a818a27f86e04a124014aec40aebdb619`

Implemented:

- baseline文書を追加
- 現在のテンプレート一覧、migration、API、copy互換範囲を記録
- Phase 1で修正する既存routing制約を明記

Tests:

- Python compile PASS
- JS syntax check PASS
- copy renderer unit test PASS
- smoke test PASS

Review:

- Critical: 0
- High: 0
- Medium: 0

Gate:

- PASS

Next:

- Phase 1A Template Group DB / API Contract

## Phase 1: Template Group / Explicit Routing

Status: PASS

Base: `be594f8`

Implemented:

- `template_groups` / `template_group_items` を追加
- `quick_templates` / `search_keywords` に `target_type` / `target_id` を追加
- `GET /api/quick-templates` と `GET /api/search-keywords` が `target` を返す
- `GET /api/template-groups/<id>` を追加
- `cerebral_infarction` groupを追加し、MCA / ACA / PCA / ラクナ / 脳幹を順序付きで紐づけ
- 通常画面に `openTarget()` を追加
- label文字列推測とstroke category fallbackを通常routingから削除
- 脳梗塞groupを既存generic rendererのタブUIとして表示
- group内タブ切替時の入力値をメモリ上で保持

Tests:

- Python compile PASS
- JS syntax check PASS
- copy renderer unit test PASS
- smoke test PASS
- Browser manual check PASS
  - 脳梗塞 quick item -> 5タブ表示
  - 脳卒中共通 quick item -> `neuro_common` 単体表示
  - groupタブ切替後にMCA入力値が復元される

Review:

- Critical: 0
- High: 0
- Medium: 0

Gate:

- PASS

Next:

- Phase 2 Optimistic Template Version Concurrency

## Phase 2: Optimistic Template Version Concurrency

Status: PASS

Base: `0c65904`

Implemented:

- `POST /api/templates/<id>/versions` に `base_version_id` 必須化を追加
- 保存時点の `current_version_id` と `base_version_id` が一致しない場合は `409` を返す
- 管理画面のschema編集保存時に、詳細取得時の `current_version_id` を送信
- スモークテストに `base_version_id` 欠落400と古い `base_version_id` 409を追加
- README / handoff に競合更新防止のAPI契約を追記

Tests:

- Python compile PASS
- JS syntax check PASS
- copy renderer unit test PASS
- smoke test PASS

Review:

- Critical: 0
- High: 0
- Medium: 0

Gate:

- PASS

Next:

- Phase 3 Option Value / Label Separation

## Phase 3: Option Value / Label Separation

Status: PASS

Base: `4ea663e`

Implemented:

- `select` / `multi_select` の `options` で `{ value, label }` 形式を受け付ける
- 旧string optionは互換として受け付け、API返却時に `{ value: 文字列, label: 文字列 }` へ正規化
- duplicate `value`、blank `value` / `label`、未知option keyを拒否
- 通常画面のselect / checkboxはDOM内部値に `value`、表示に `label` を使用
- コピー出力では内部 `value` ではなく `label` に変換して出力
- README / handoff にoption契約とCondition Engine前提を追記

Tests:

- Python compile PASS
- JS syntax check PASS
- copy renderer unit test PASS
- smoke test PASS
- Browser manual check PASS
  - selectのDOM valueが `oxygen`
  - select表示とコピー出力がlabel
  - multi_select hidden valueが `nausea`
  - multi_selectコピー出力がlabel

Review:

- Critical: 0
- High: 0
- Medium: 0

Gate:

- PASS

Next:

- Phase 4 Typed Value State

## Phase 4: Typed Value State

Status: PASS

Base: `aa6d2b9`

Implemented:

- `js/generic-values.js` を追加し、generic入力値のparse / format / blank判定 / 復元を共通化
- `number` の空欄を `null`、`0` を有効値として扱う
- `multi_select` を状態上は配列として扱い、DOM hidden valueへの復元だけ `、` 区切りにする
- groupタブの一時入力状態を型付き値で保存・復元
- genericコピー出力は型付き値をlabel表示へ整形してから `copy-renderer` に渡す
- generic未入力警告は共通blank判定を使用
- README / handoff にTyped Value Stateの現行ルールを追記

Tests:

- Python compile PASS
- JS syntax check PASS
- copy renderer unit test PASS
- generic value unit test PASS
- smoke test PASS

Review:

- Critical: 0
- High: 0
- Medium: 0

Gate:

- PASS

Next:

- Phase 5 generic-v2 / Condition Engine

## Phase 5: generic-v2 / Condition Engine

Status: PASS

Base: `064fa7b`

Implemented:

- `generic-v2` schemaFormatを追加
- Backend condition validatorを追加
  - known op検証
  - required / unknown key検証
  - field ref存在検証
  - numeric operatorはnumber fieldのみ許可
  - nested conditionと最大depthを検証
- field `visibleIf` / `requiredIf` をgeneric-v2のみ許可
- copy line `showIf` をgeneric-v2のみ許可
- `js/condition-engine.js` を追加し、DOM非依存の `evaluateCondition(condition, values)` を実装
- 通常画面で `visibleIf` を評価し、非表示fieldの値をclear
- 未入力警告で `requiredIf` を評価
- コピー出力で `showIf` を評価
- 管理画面のJSON編集で `generic-v2` を選択可能にした
- README / handoff にcondition契約を追記

Tests:

- Python compile PASS
- JS syntax check PASS
- copy renderer unit test PASS
- generic value unit test PASS
- condition engine unit test PASS
- smoke test PASS
- Browser manual check PASS
  - `visibleIf` 初期非表示
  - 条件成立時にfield表示
  - `showIf` によりコピー条件行を出力
  - `requiredIf` による不要警告なし

Review:

- Critical: 0
- High: 0
- Medium: 0

Gate:

- PASS

Next:

- Phase 6 Medical Safety Rule Layer

## Phase 6: Medical Safety Rule Layer

Status: PASS

Base: `76e920b`

Implemented:

- `blankPolicy` を追加
  - `allow`: 空欄許可
  - `warn`: 確認後コピー可能
  - `block`: コピー不可
- `hardRange` / `warningRange` を追加
  - `hardRange` 範囲外はblock
  - `warningRange` 範囲外はwarn
- `js/safety-rules.js` を追加し、`{ blocks, warnings }` の安全判定結果を返す
- `requiredWarning=true` を後方互換としてwarn扱いにする
- `copy-renderer` に `renderGenericTemplateCopyResult()` を追加し、`{ text, unresolvedRefs, warnings }` を返せるようにした
- copy UIでblock時はコピー不可、warn時は確認後コピー可能にした
- テンプレート更新時の高リスク差分検出を追加
  - field削除
  - `blankPolicy` 緩和
  - condition変更
  - `requiredIf` 削除
  - `hardRange` 緩和
  - copy line削除または変更
- 高リスク差分をAPIレスポンス `high_risk_changes` と監査ログ `diff.high_risk_changes` に保存
- README / handoff にSafety Layerの現行仕様を追記

Tests:

- Python compile PASS
- JS syntax check PASS
- copy renderer unit test PASS
- generic value unit test PASS
- condition engine unit test PASS
- safety rules unit test PASS
- smoke test PASS
- Browser manual check PASS
  - `blankPolicy=block` でコピー前修正メッセージ表示
  - block状態のwarning UIが赤系表示

Review:

- Critical: 0
- High: 0
- Medium: 0

Gate:

- PASS

Next:

- Phase 7 Admin Template Builder

## Phase 7: Admin Template Builder

Status: PASS

Base: `9ef3405`

Implemented:

- `js/admin-builder.js` を追加
- 管理画面のgeneric schema / copy_format編集をTemplate Builder化
- セクション追加 / 削除をフォームで操作可能にした
- 項目追加 / 削除をフォームで操作可能にした
- 項目ID、ラベル、種別、単位、placeholder、補足説明を編集可能にした
- `blankPolicy`、`hardRange`、`warningRange` をフォームで編集可能にした
- 選択肢を `value` / `label` の行として追加 / 削除できるOption Builderを追加
- `visibleIf`、`requiredIf`、copy line `showIf` を単純条件として編集できるCondition Builderを追加
- コピー出力行を追加 / 削除できるCopy Line Builderを追加
- コピー出力行へ入力項目参照 `{{section.field}}` をボタンで挿入できるようにした
- Developer Mode / JSONを残し、高度なschema / copy_format編集に使えるようにした
- README / handoff に管理画面ビルダーの現行仕様を追記

Tests:

- Python compile PASS
- JS syntax check PASS
- copy renderer unit test PASS
- generic value unit test PASS
- condition engine unit test PASS
- safety rules unit test PASS
- smoke test PASS
- Browser manual check PASS
  - Template Builder表示
  - generic-v1新規追加
  - `copy_format`保存
  - select field + option保存

Review:

- Critical: 0
- High: 0
- Medium: 0

Gate:

- PASS

Next:

- Phase 8 Version Integrity / Publication Workflow

## Phase 8: Version Integrity / Publication Workflow

Status: PASS

Base: `0da7e8a`

Implemented:

- `template_versions.status` を追加
  - `draft`
  - `published`
  - `retired`
- 既存DB初期化時に、現在版を `published`、非現在版を `retired` へ正規化
- SQLite triggerで `templates.current_version_id` が同じtemplateの `published` versionだけを指せるようにした
- `POST /api/templates/<id>/versions` を下書き作成に変更
  - `templates.current_version_id` は変更しない
  - 通常画面には即反映しない
- `POST /api/templates/<id>/versions/<version_id>/publish` を追加
  - draftをpublished化
  - 旧publishedをretired化
  - `templates.current_version_id` を切り替え
  - 高リスク変更は `confirm_high_risk: true` がない場合409
- `POST /api/templates/<id>/versions/<version_id>/rollback` を追加
  - 過去versionへ直接pointerを戻さず、過去version内容から新しいpublished versionを作成
  - 公開履歴の時系列を維持
- 管理画面の履歴にstatus表示、公開、復元公開操作を追加
- README / handoff に公開version管理の現行仕様を追記

Tests:

- Python compile PASS
- JS syntax check PASS
- copy renderer unit test PASS
- generic value unit test PASS
- condition engine unit test PASS
- safety rules unit test PASS
- smoke test PASS
  - draft作成
  - draft作成でcurrent不変
  - publishでcurrent切替
  - publish後のstale base_version_id 409
  - rollback publish
  - current_version_id triggerが別template version参照を拒否
  - 高リスクpublishは確認なし409、確認あり200

Review:

- Critical: 0
- High: 0
- Medium: 0

Gate:

- PASS

Next:

- Phase 9 Legacy Cleanup / Deprecation

## Phase 9: Legacy Cleanup / Deprecation

Status: PASS

Base: `03b5cbd`

Implemented:

- `docs/legacy-cleanup-inventory.md` を追加
- `templates.schema_json`、legacy routing値、`stroke-v1` 互換コードの棚卸しを記録
- 通常API / 管理API / group APIの新規読み取り経路を `template_versions.schema_json` に寄せた
- `templates.schema_json` は互換用として残し、物理削除は行わない
- README / handoff にPhase 9の棚卸しとRemoval Gateを追記

Tests:

- Python compile PASS
- JS syntax check PASS
- copy renderer unit test PASS
- generic value unit test PASS
- condition engine unit test PASS
- safety rules unit test PASS
- smoke test PASS

Review:

- Critical: 0
- High: 0
- Medium: 0

Gate:

- PASS

Next:

- 慢性硬膜下血腫テンプレートなど、`generic-v2` 前提の新規テンプレート取り込み設計

## Phase 11: Corrective Hardening

Status: PASS

Base: `a8e8b76`

Implemented:

- Template Builder lossless field round-trip:
  - preserves original field properties such as `requiredWarning`, `allowEmpty`, `min`, `max`, `step`, and field `displayOrder`
  - strips incompatible properties when field type changes
  - condition value editor now uses number input for number fields and option picker for select / contains conditions
- Draft publish concurrency:
  - `template_versions.base_version_id` records the published version a draft was created from
  - publish rejects stale drafts with 409 when the current version has moved
- Runtime copy safety:
  - invalid number input creates `invalid_number` block issue
  - unresolved copy renderer refs are merged into copy safety warnings so `__` does not silently copy
- Group UI state:
  - group tab input state moved from global storage to each group card closure
  - group clear keeps the group UI and only clears the active tab
- Condition hardening:
  - frontend visibility evaluation now converges with fixed-point passes
  - convergence failure blocks copy
  - backend rejects `visibleIf` dependency cycles
  - backend validates condition value types for number/select/multi_select cases
- DB invariant:
  - current version cannot be retired directly
  - publish/rollback order now keeps `templates.current_version_id` pointing at a published version
- Test robustness:
  - smoke test covers two-draft stale publish, condition cycles/type errors, non-select options rejection, current-version retire trigger, and Windows temp DB cleanup

Tests:

- Python compile PASS
- JS syntax check PASS
- copy renderer unit test PASS
- generic value unit test PASS
- condition engine unit test PASS
- safety rules unit test PASS
- smoke test PASS

Review:

- Critical: 0
- High: 0
- Medium: 0

Gate:

- PASS

## Phase 10: Residual Safety / Admin Warning Refinement

Status: PASS

Base: `615e7af`

Implemented:

- copy_format参照収集を出力参照と制御参照へ分離
  - 出力参照: placeholder / `splitLinesFrom`
  - 制御参照: `omitIfAllBlank` / `showIf` condition field
  - 既存のunknown ref検証は両方の和集合を使い、400挙動は維持
- `generic-v1` / `generic-v2` の未参照フィールド警告を追加
  - `POST /api/templates` と `POST /api/templates/<id>/versions` の201レスポンスに `warnings` を付与
  - `GET /api/admin/templates/<id>` と version詳細に導出 `warnings` を付与
  - publishはブロックしない
  - `omitIfAllBlank` だけに現れるfieldは、値が出力されないため未参照として警告
- 管理画面に未参照警告を表示
  - 詳細/編集画面
  - 下書き作成・新規作成後のトースト
  - Template Builderのライブプレビュー
- number fieldの通常画面入力を `type=text` + `inputmode=decimal` に変更
  - 全角数字、全角ピリオド、全角マイナス、前後空白を正規化
  - `min` / `max` / `step` はdatasetに保持し、既存の安全判定へ渡す
- 小規模サーバ改善
  - `MAX_CONTENT_LENGTH = 1MB` と413ハンドラを追加
  - `sqlite3.Error` とDB未準備/health失敗の生detailをレスポンスから除去しログ出力へ変更
  - `NASUKERU_HOST` がlocalhost系以外の場合、`NASUKERU_ALLOW_EXTERNAL=1` が無ければ起動拒否

Tests:

- Python compile PASS
- JS syntax check PASS
- copy renderer unit test PASS
- generic value unit test PASS
- condition engine unit test PASS
- safety rules unit test PASS
- smoke test PASS
  - unreferenced warning
  - omit-only control ref warning
  - generic-v2 conditional unreferenced warning
  - copy_format null no warning
  - payload too large 413

Review:

- Critical: 0
- High: 0
- Medium: 0

Gate:

- PASS

Next:

- 慢性硬膜下血腫テンプレートなど、`generic-v2` 前提の新規テンプレート取り込み設計
