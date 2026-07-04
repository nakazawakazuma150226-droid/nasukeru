# ナスケル Simple Template Authoring 設計書

作成日: 2026-07-04
対象branch: `feature/simple-template-authoring`

## 1. 目的

IT知識を持たない看護職でも、内部ID、JSON、schema形式、field ref、`blankPolicy`、`segments`を理解せずにテンプレートを新規追加・編集できる管理UIを提供する。

既存の `generic-v2`、option `value/label`、Condition Engine、copy format、draft/publish基盤は維持する。新しいDB形式は追加しない。

## 2. Architecture

```text
Simple Authoring UI
        ↓
Editor View Model
        ↓ compile
schema_json / copy_format_json
        ↓
既存API / validator / version workflow
```

通常操作では技術用語を隠す。

- template ID: 自動生成、非表示
- section / field ID: 自動生成、非表示
- schema format: 新規作成は `generic-v2` 固定
- option value: 自動生成・保持、表示名だけ編集
- blank policy: 日本語の動作3択で表示
- condition ref: `section.field`ではなく項目名で表示
- copy format: 自動生成モードを主経路にする
- JSON編集: 従来Template Builderの詳細編集モードへ退避

## 3. Phase 12A: Simple Authoring Foundation

- Simple Authoring用pure model追加
- template / section / field / option IDの自動生成
- `generic-v2`へのauthoring upgrade
- legacy `requiredWarning`を含むeffective blank policy表示
- 内部IDを通常UIから非表示
- 既存Builderは「詳細編集モード」として維持

## 4. Phase 12B: Clone Existing Template

新規追加の主導線:

```text
新しいテンプレート
↓
似ているテンプレートから作る
または
白紙から作る
```

cloneはschema / copy formatを読み込み、新しい自動生成template IDで既存create APIへ保存する。

## 5. Phase 12C: Simple Input Builder / Automatic Copy Format

Field設定:

- 項目名
- 入力方法
- 未入力時の動作
- コピー文に含める
- 単位
- 入力例
- 補足説明
- 選択肢
- 数値安全範囲
- 単純表示条件
- 単純必須条件

コピー文はsection単位で「項目ごとに改行」「1行にまとめる」を選ぶ。自動copy formatは既存`segments`と`omitIfAllBlank`へcompileする。

## 6. Phase 12D: Real Preview

Simple Authoring内で実入力可能なpreviewを表示する。

```text
入力画面preview | コピー文preview
```

preview入力は保存しない。既存のGenericValues、ConditionEngine、SafetyRules、CopyRendererを再利用する。

## 7. Phase 12E: Publication UX

編集保存後は履歴画面へ誘導せず、その場で「公開せず閉じる」「この下書きを公開」を選べる。high-risk changeは既存409 responseを使い、日本語確認後に`confirm_high_risk=true`で再送する。

新規templateは現行API仕様上、作成時にpublishedとなる。今回のDB/API変更対象外とし、ボタン文言を「追加して公開」として挙動を明示する。

## 8. Phase 12F: Discovery Management

今回は未実装。quick template、search keyword alias、template group membershipのwrite APIが存在しないため、次フェーズで管理APIを追加してSimple Authoringの基本情報へ統合する。

## 9. Safety

- 患者情報・preview入力は永続保存しない
- 新規field初期値は空欄
- existing validatorを通過しないschemaは保存しない
- draft editは既存`base_version_id`競合防止を使用する
- copy previewはexisting rendererを使用する
- safety previewはexisting safety rulesを使用する
- preserved copy formatが削除済fieldを参照する場合は保存前に停止する
- 複雑なconditionは通常UIで勝手に変換せず、そのまま保持し「詳細編集で確認」と表示する

## 10. Review Gate

PASS条件:

- pure model unit tests PASS
- JS syntax check PASS
- internal ID入力なしでblank templateを作成できる
- clone sourceを選んでschema / copy formatを読み込める
- effective blank policyがlegacy `requiredWarning`と一致する
- auto copy formatがblank fieldを省略する
- preview入力がDBへ送信されない
- existing edit APIへdraft versionとして保存する
- save後に同一導線からpublishできる
- Developer Modeへの退避経路が残る

## 11. Deferred

- 新規template自体をdraft状態で作成するAPI
- template基本情報のversion管理
- search keyword write API
- quick template write API
- template group write API
- complex AND / OR conditionのSimple UI
- arbitrary fixed text + field chipの完全Visual Copy Composer
