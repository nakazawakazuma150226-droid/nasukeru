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
