# ナスケル 可変テンプレート移行設計書

## 1. 目的

本書は、ナスケルのテンプレート構造を、現在の脳梗塞向け固定schemaから、DSA・術後・検査後など項目構造が異なるテンプレートにも対応できる可変schemaへ移行するための設計をまとめる。

短期的には既存の脳梗塞テンプレートを壊さず、新規テンプレートで可変項目を扱えるようにする。最終的には既存テンプレートも可変テンプレートとして新バージョン化し、全テンプレートを同じ仕組みで扱える状態を目指す。

## 2. 現状設計

### 2.1 画面構成

- `/`
  - 通常入力画面
  - 現状は脳梗塞テンプレートの入力・コピー出力が中心
  - 管理画面へのリンクを持つ
- `/admin` / `/admin/`
  - ローカル管理画面
  - テンプレート追加、schema編集、論理削除、復元、履歴・監査ログ確認を行う
  - 通常画面へのリンクを持つ

### 2.2 DB構成

主なテーブル:

- `templates`
  - テンプレートの基本情報
  - `id`, `label`, `full`, `category`, `schema_json`, `is_active`, `current_version_id`, `status`
- `template_versions`
  - テンプレートschemaをバージョン管理する
  - `schema_json`, `copy_format_json`, `change_summary`, `change_reason`
- `template_audit_logs`
  - 作成、更新、削除、復元などの監査ログ
- `rest_options`, `quick_templates`, `search_keywords`
  - 通常画面の補助データ

現状は `template_versions.schema_json` を正とし、`templates.schema_json` は互換用として残している。

### 2.3 現在のschema

現在のテンプレートschemaは、実質的に脳梗塞向けの固定構造である。

```json
{
  "vitals": {},
  "symptoms": {},
  "neuro": {},
  "rest": ""
}
```

必須構造:

- `vitals`
  - `jcs`, `t`, `bp`, `hr`, `spo2`
- `symptoms`
  - `headache`, `dizzy`, `nausea`
- `neuro`
  - `pupil`, `light`, `eye`, `barre`, `mingazzini`, `mmt`, `nihss`, `other`
- `neuro.mmt`
  - `ru`, `rl`, `lu`, `ll`
- `rest`

この形式を本書では `stroke-v1` と呼ぶ。

既存DBの5テンプレートには `schemaFormat` が無いため、`schemaFormat` が無い場合は `stroke-v1` とみなす。

### 2.4 現在の制約

現在の設計では、以下のような新規項目を自然に扱えない。

- DSA後の穿刺部観察
- 末梢循環
- 造影剤後観察
- 術後の創部観察
- ドレーン
- 疼痛スケール
- 検査後の安静・解除予定

理由:

- schemaが `vitals / symptoms / neuro / rest` 固定
- 通常画面の描画が脳梗塞テンプレート前提
- 管理画面の編集UIも固定項目を前提としている
- コピー出力が `copy-format.js` 固定
- `copy_format_json` はDBにあるが、まだ実利用していない

## 3. 基本方針

一気に全テンプレートを置き換えず、段階移行する。

```text
短期:
  stroke-v1 と generic-v1 を併存する

中期:
  通常画面とコピー出力を generic-v1 に対応させる

最終:
  既存 stroke-v1 も generic-v1 へ新バージョン化し、
  全テンプレートを可変テンプレートに統一する
```

設計原則:

- 既存テンプレートを直接上書きしない
- 既存バージョンを物理削除しない
- 移行は必ず新しい `template_versions` として作る
- 問題があれば `current_version_id` を旧バージョンへ戻せるようにする
- 通常入力画面の初期値空欄原則を維持する
- 「なし」「あり」などは初期値ではなく選択肢として扱う

## 4. schemaFormat 方針

### 4.1 対応形式

```text
schemaFormat なし        -> stroke-v1
schemaFormat: stroke-v1  -> 既存脳梗塞形式
schemaFormat: generic-v1 -> 可変テンプレート形式
```

### 4.2 判定場所

`template_schema.py` の `validate_template_schema()` 入口で `schemaFormat` を判定し、内部で検証を分岐する。

呼び出し側の `app.py` には形式判定を散らさない。

```text
validate_template_schema(schema)
  ├─ stroke-v1
  │    └─ validate_stroke_v1_schema(schema)
  └─ generic-v1
       └─ validate_generic_v1_schema(schema)
```

## 5. generic-v1 schema設計

### 5.1 基本構造

`generic-v1` は、セクションとフィールドを配列で持つ。

```json
{
  "schemaFormat": "generic-v1",
  "sections": [
    {
      "id": "puncture",
      "label": "穿刺部観察",
      "displayOrder": 1,
      "fields": [
        {
          "id": "bleeding",
          "label": "出血",
          "type": "select",
          "options": ["なし", "あり"],
          "allowEmpty": true
        }
      ]
    }
  ]
}
```

### 5.2 section

必須:

- `id`
- `label`
- `fields`

任意:

- `displayOrder`
- `helpText`

制約:

- `id` は `^[a-z0-9_-]{1,32}$`
- 同一schema内で section id は重複不可
- `fields` は配列

### 5.3 field

必須:

- `id`
- `label`
- `type`

任意:

- `options`
- `allowEmpty`
- `requiredWarning`
- `placeholder`
- `helpText`
- `displayOrder`
- `unit`

制約:

- `id` は `^[a-z0-9_-]{1,32}$`
- 同一section内で field id は重複不可
- `type` は許可された型のみ
- `select` は `options` を必須とする
- `options` は文字列配列

### 5.4 初期対応するfield type

現在対応済み:

- `text`
- `textarea`
- `select`
- `number`
- `multi_select`

段階2以降の候補:

- `datetime`
- `time`
- `checkbox`
- `radio`
- `computed`
- `conditional`

## 6. DSAテンプレートの表現例

DSA後・右鼠径穿刺テンプレートは、以下のような `generic-v1` で表現できる。

```json
{
  "schemaFormat": "generic-v1",
  "sections": [
    {
      "id": "basic",
      "label": "基本情報",
      "displayOrder": 1,
      "fields": [
        { "id": "procedure", "label": "検査/治療名", "type": "text", "allowEmpty": true },
        { "id": "puncture_site", "label": "穿刺部位", "type": "select", "options": ["右鼠径", "左鼠径", "右橈骨", "左橈骨"], "allowEmpty": true },
        { "id": "hemostasis", "label": "止血方法", "type": "select", "options": ["アンギオロール", "TRバンド", "用手圧迫"], "allowEmpty": true },
        { "id": "return_time", "label": "帰室時間", "type": "text", "allowEmpty": true },
        { "id": "release_time", "label": "圧迫解除予定時間", "type": "text", "allowEmpty": true }
      ]
    },
    {
      "id": "puncture",
      "label": "穿刺部観察",
      "displayOrder": 2,
      "fields": [
        { "id": "bleeding", "label": "出血", "type": "select", "options": ["なし", "あり"], "allowEmpty": true },
        { "id": "hematoma", "label": "血腫", "type": "select", "options": ["なし", "あり"], "allowEmpty": true },
        { "id": "induration", "label": "硬結", "type": "select", "options": ["なし", "あり"], "allowEmpty": true },
        { "id": "pain", "label": "疼痛", "type": "select", "options": ["なし", "あり"], "allowEmpty": true },
        { "id": "back_pain", "label": "腰背部痛", "type": "select", "options": ["なし", "あり"], "allowEmpty": true }
      ]
    },
    {
      "id": "peripheral",
      "label": "末梢循環",
      "displayOrder": 3,
      "fields": [
        { "id": "dorsalis_pedis", "label": "両足背動脈", "type": "select", "options": ["触知可能", "触知困難", "触知不可"], "allowEmpty": true },
        { "id": "laterality", "label": "左右差", "type": "select", "options": ["なし", "あり"], "allowEmpty": true },
        { "id": "coldness", "label": "下肢冷感", "type": "select", "options": ["なし", "あり"], "allowEmpty": true },
        { "id": "color", "label": "色調不良", "type": "select", "options": ["なし", "あり"], "allowEmpty": true }
      ]
    },
    {
      "id": "contrast",
      "label": "造影剤後観察",
      "displayOrder": 4,
      "fields": [
        { "id": "hydration", "label": "飲水励行", "type": "select", "options": ["あり", "なし", "制限あり"], "allowEmpty": true },
        { "id": "urine", "label": "尿量確認", "type": "select", "options": ["継続", "不要", "医師指示による"], "allowEmpty": true },
        { "id": "rash", "label": "皮疹", "type": "select", "options": ["なし", "あり"], "allowEmpty": true },
        { "id": "dyspnea", "label": "呼吸苦", "type": "select", "options": ["なし", "あり"], "allowEmpty": true }
      ]
    }
  ]
}
```

条件分岐は段階1では扱わない。たとえば穿刺部位が鼠径なら下肢観察、橈骨なら手指観察を出し分ける処理は段階2以降とする。

## 7. copy_format_json 方針

### 7.1 現状

現状のコピー出力は `js/copy-format.js` に固定実装されている。

`template_versions.copy_format_json` はDBに存在するが、まだ通常画面では利用していない。

### 7.2 将来方針

`generic-v1` の通常画面対応後、テンプレートごとの出力形式を `copy_format_json` に移す。

例:

```json
{
  "format": "text-v1",
  "lines": [
    "DSA後、帰室。",
    "JCS {{neuro.jcs}}。",
    "右鼠径穿刺部、{{puncture.bleeding}}。",
    "両足背動脈 {{peripheral.dorsalis_pedis}}。"
  ]
}
```

未入力時の扱い:

- 段階1では未対応
- 段階3で `__` 表示、空欄維持、行ごと省略などのルールを設計する

## 8. 管理画面設計

### 8.1 段階1

管理画面では、`generic-v1` の作成・編集を可能にする。

新規作成時:

- `template id`
- `label`
- `full`
- `category`
- `schemaFormat`
  - `stroke-v1`
  - `generic-v1`
- `change_reason`

`generic-v1` 編集時:

- section追加
- section削除
- section名編集
- field追加
- field削除
- field名編集
- field type選択
- select options編集
- 表示順編集

段階1では、ドラッグ&ドロップによる並び替えは必須にしない。`displayOrder` 数値入力または上下ボタンで十分とする。

### 8.2 stroke-v1 の扱い

段階1では既存 `stroke-v1` 編集UIを維持する。

ただし、将来的に完全移行するため、管理画面には以下を追加する余地を残す。

- `generic-v1` 変換プレビュー
- `generic-v1` 版を新バージョンとして作成
- 移行前後のschema差分表示

## 9. 通常画面対応

### 9.1 段階1では対象外

段階1では `generic-v1` を通常画面に表示しない。

理由:

- 通常画面は医療安全の中心
- 初期値空欄原則、未入力警告、コピー出力への影響が大きい
- 可変schemaの保存形式が固まってから描画設計を行う方が安全

### 9.2 段階2

通常画面は2モード化する。

```text
stroke-v1   -> 既存固定UI
generic-v1  -> 動的UI
```

`generic-v1` 動的UIでは、sections / fields を順に描画する。

初期値:

- 原則空欄
- `placeholder` は入力例として表示
- `options` は選択肢として表示
- 「なし」「あり」を勝手に初期選択しない

未入力警告:

- `requiredWarning: true` のfieldを対象にする
- 警告してもコピーは止めない方針を維持する

## 10. 既存テンプレート完全移行設計

### 10.1 移行対象

現在の脳梗塞5テンプレート:

- `mca`
- `aca`
- `pca`
- `lacunar`
- `brainstem`

### 10.2 移行方式

既存行・既存バージョンは直接上書きしない。

各テンプレートに対して、`generic-v1` 変換後のschemaを新しい `template_versions` として追加する。

```text
template_versions v1: stroke-v1
template_versions v2: generic-v1
templates.current_version_id -> v2
```

旧バージョンは履歴として残す。

### 10.3 変換ルール

`stroke-v1` から `generic-v1` への基本変換:

```text
vitals       -> section: vitals / バイタル
symptoms     -> section: symptoms / 症状
neuro        -> section: neuro / 神経所見
neuro.mmt    -> section: mmt / MMT
rest         -> section: rest / 安静度
```

変換例:

```json
{
  "schemaFormat": "generic-v1",
  "sections": [
    {
      "id": "vitals",
      "label": "バイタル",
      "displayOrder": 1,
      "fields": [
        { "id": "jcs", "label": "JCS", "type": "text", "allowEmpty": true, "requiredWarning": true },
        { "id": "t", "label": "体温", "type": "text", "allowEmpty": true, "requiredWarning": true, "unit": "℃" },
        { "id": "bp", "label": "血圧", "type": "text", "allowEmpty": true, "requiredWarning": true, "unit": "mmHg" },
        { "id": "hr", "label": "脈拍", "type": "text", "allowEmpty": true, "requiredWarning": true },
        { "id": "spo2", "label": "SpO₂", "type": "text", "allowEmpty": true, "requiredWarning": true, "unit": "%" }
      ]
    },
    {
      "id": "symptoms",
      "label": "症状",
      "displayOrder": 2,
      "fields": [
        { "id": "headache", "label": "頭痛", "type": "text", "allowEmpty": true },
        { "id": "dizzy", "label": "めまい", "type": "text", "allowEmpty": true },
        { "id": "nausea", "label": "嘔気", "type": "text", "allowEmpty": true }
      ]
    }
  ]
}
```

### 10.4 変換プレビュー

完全移行前に、管理画面で変換結果を確認できるようにする。

プレビュー対象:

- 変換後schema
- section / field 一覧
- requiredWarning 対象
- copy_format_json 変換結果
- 通常画面での表示イメージ

段階1ではプレビューは必須ではない。完全移行段階で必須とする。

### 10.5 移行時の監査ログ

移行操作は `template_audit_logs` に記録する。

推奨値:

- `action`: `migrate`
- `actor_name`: `local` または将来の実ユーザー
- `reason`: `Migrate stroke-v1 schema to generic-v1`
- `before_json`: 旧schema
- `after_json`: 新schema

現在のaction設計に `migrate` が既に使われているため、これを継続利用できる。

### 10.6 ロールバック

移行は新バージョン方式なので、問題があれば `templates.current_version_id` を旧 `stroke-v1` バージョンへ戻せる。

```text
current_version_id: v2 generic-v1
↓
current_version_id: v1 stroke-v1
```

ロールバックも監査ログに残す。

### 10.7 互換性確認

移行前後で以下が変わらないことを確認する。

- 通常画面の表示項目
- 入力欄の初期値
- 未入力警告対象
- コピー出力文
- テンプレート一覧
- 履歴・監査ログ
- 管理画面での編集・削除・復元

特にコピー出力文は、既存の看護記録運用に影響するため、文字列単位で差分テストする。

## 11. API設計

### 11.1 段階1で追加・変更するAPI

既存APIは原則維持する。

必要な変更:

- `POST /api/templates`
  - `generic-v1` schemaを受け付ける
- `POST /api/templates/<id>/versions`
  - `generic-v1` schemaを受け付ける
- `GET /api/templates/<id>/versions/<vid>`
  - `copy_format_json` を返す現状仕様を維持する

`template_schema.py` の検証分岐により、`app.py` 側の大きな分岐は避ける。

### 11.2 完全移行段階で検討するAPI

- `POST /api/templates/<id>/migrate-to-generic`
  - 既存 `stroke-v1` を `generic-v1` として新バージョン化
- `GET /api/templates/<id>/migration-preview`
  - 変換結果プレビュー
- `POST /api/templates/<id>/rollback-version`
  - 過去バージョンを現在版へ戻す

段階1では未実装でよい。

## 12. 実装段階

### Phase 1: generic-v1 保存・管理画面編集

状態: 実装済み。

対象:

- `schemaFormat` 導入
- `generic-v1` 検証追加
- 管理画面で `generic-v1` 新規作成
- 管理画面で section / field 編集
- `select` options編集
- 履歴・監査ログは既存の仕組みを利用

対象外:

- 通常画面表示
- コピー出力
- 条件分岐
- 既存テンプレート完全移行

### Phase 2: 通常画面 generic-v1 表示

状態: 実装済み。

対象:

- `generic-v1` 動的描画
- 初期値空欄原則
- requiredWarningによる未入力警告
- `stroke-v1` 固定UIとの併存

### Phase 3: copy_format_json 出力

状態: 実装済み。

対象:

- `text-v1` 出力定義
- `{{section.field}}` 参照
- 未入力値の扱い
- 既存出力との互換テスト

### Phase 4: 既存stroke-v1完全移行

状態: 実装済み。DB初期化時のマイグレーション `004` で、脳梗塞5テンプレートを `generic-v1` の新バージョンとして追加する。

対象:

- 変換関数
- 変換プレビュー
- 新バージョン作成
- current_version_id切替
- ロールバック
- 互換性テスト

### Phase 5: stroke-v1専用処理の整理

状態: 着手中。

対象:

- `stroke-v1` 専用描画の削除検討
- `field-meta.js` 固定ラベルのschema側移行
- `copy-format.js` 固定出力の縮小

方針:

- 新規テンプレート追加は `generic-v1` 固定とする
- `stroke-v1` は旧バージョン・ロールバック・既存DB互換のため当面残す
- 通常画面の主経路は `generic-v1` とし、`stroke-v1` 専用描画は互換用として段階的に縮小する
- `field-meta.js` の固定ラベルは `generic-v1` ではschema側ラベルを優先し、旧 `stroke-v1` 互換処理に限定して使う
- `copy_format_json` は文字列行を維持しつつ、行オブジェクトで空欄時の行省略を扱う
- 既存stroke項目だけを入力した場合は、移行前の `stroke-v1` コピー出力と文字列一致させる

`text-v1` の行オブジェクト:

```json
{
  "text": "皮疹：{{contrast.rash}}",
  "omitIfAllBlank": ["contrast.rash"]
}
```

`omitIfAllBlank` に指定した `section.field` がすべて空欄の場合、その行はコピー出力から省略する。既存の文字列行は従来どおり必ず出力する。

改行分割が必要な行は `splitLinesFrom` を指定する。

```json
{
  "text": "{{neuro.other}}",
  "splitLinesFrom": "neuro.other",
  "omitIfAllBlank": ["neuro.other"]
}
```

`splitLinesFrom` は指定した値を改行で分割し、空行を除いた各行を出力する。これは旧 `stroke-v1` の「その他神経症状」出力互換に使う。

### Phase 6: 脳卒中共通テンプレート追加

状態: 実装済み。DB初期化時のマイグレーション `006` で、`neuro_common` を `generic-v1` テンプレートとして追加する。

含めた範囲:

- 意識レベル
- バイタルサイン
- 瞳孔・眼球所見
- 運動機能
- NIHSS
- 高次脳機能
- 頭蓋内圧亢進症状
- 嚥下
- 安静度・ADL
- 排泄
- 治療

`multi_select` と `number` は使用する。条件分岐、状況グループ、派生出力は含めない。

## 13. テスト方針

### 13.1 Phase 1

- `stroke-v1` 既存テンプレートが従来どおり読める
- `schemaFormat` 無しは `stroke-v1` とみなされる
- `generic-v1` の正常schemaが保存できる
- `generic-v1` の不正schemaは400になる
- `select` で `options` が無い場合は400
- section id重複は400
- field id重複は400
- 管理画面で追加・編集・削除・復元・履歴確認ができる

### 13.2 Phase 2

- `generic-v1` が通常画面に動的表示される
- 初期値が勝手に入らない
- `requiredWarning` の警告が出る
- 警告があってもコピーは止めない
- `stroke-v1` の通常画面挙動が変わらない

### 13.3 Phase 3

- `copy_format_json` から出力できる
- 未入力値が定義どおり出力される
- 既存strokeテンプレートの出力文が移行前後で一致する
- `stroke_findings` は空欄時に出力されず、既存stroke項目だけの入力では旧出力と一致する

### 13.4 Phase 4

- 5テンプレートを `generic-v1` に変換できる
- 新バージョンとして保存される
- 旧バージョンが履歴に残る
- `current_version_id` 切替後も表示・コピー出力が一致する
- ロールバックできる

## 14. リスクと対策

### 14.1 既存テンプレート破壊

対策:

- 既存バージョンを上書きしない
- 移行は新バージョンとして作る
- ロールバック可能にする

### 14.2 初期値誤設定

対策:

- 初期値は原則空欄
- 「なし」「あり」は選択肢として扱う
- 通常画面投入前に医療安全レビューを行う

### 14.3 コピー出力の変化

対策:

- 既存出力を文字列単位で比較する
- `copy_format_json` 移行は段階3で別途行う
- 移行前後の差分テストを必須にする

### 14.4 管理画面の複雑化

対策:

- Phase 1では型を `text`, `textarea`, `select` に絞る
- 条件分岐や複雑な並び替えは後回しにする
- 画面より先にschema検証を安定させる

### 14.5 認証なし管理画面

対策:

- 現状はローカル利用限定
- 外部公開しない
- POSTのローカル防御を維持する
- 将来 `/api/admin/*` を認証・権限管理へ寄せる

## 15. 結論

他テンプレートで新規項目が増える前提では、現在の `stroke-v1` 固定schemaだけでは限界がある。

短期的には `generic-v1` を追加して、DB/API/管理画面で可変テンプレートを扱えるようにする。通常画面とコピー出力は医療安全上の影響が大きいため、別フェーズで慎重に対応する。

最終的には、既存の脳梗塞5テンプレートも `generic-v1` として新バージョン化し、全テンプレートを可変テンプレートに統一する。その際も旧バージョンを残し、ロールバック可能な状態を維持する。
