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
