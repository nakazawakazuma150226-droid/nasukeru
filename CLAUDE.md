# CLAUDE.md

## プロジェクト概要

ナスケルは、脳神経外科の看護記録テンプレート入力支援アプリ（ローカル試作）です。
登録済みテンプレートを選択し、観察項目を入力して、看護記録向けの文章をコピー出力する
機能に絞っています。テンプレート定義は SQLite に保存し、Flask API 経由で読み込みます。

詳細な構成・API・データフローは `nasukeru-app/README.md` および
`nasukeru-app/docs/baseline.md` を参照してください。

## 最優先で守る医療安全の絶対原則（逸脱不可）

1. 入力初期値は原則空欄。実測・確認前の値を初期表示しない。書き込みAPIでも stroke-v1 の
   初期値入りschemaは400で拒否する。
2. 患者情報・入力内容は保存しない。
3. アプリのランタイム出力に生成AIを使わない（テンプレート変換のみ）。
   ※これは「アプリの出力」の原則。開発支援としてのAI利用（Claude/Codex等）は含まない。
4. コピー出力の正確性。入力した観察値が出力から無言で欠落してはならない。
   コピーを止めてよいのは明示された安全ルール（blankPolicy=block、hardRange逸脱）のみ。

## 壊してはいけない不変条件

- テンプレートは上書き・物理削除しない（編集=新バージョン、削除=論理削除、履歴は監査ログ）。
- 保存フローは draft → publish。rollback は過去versionの複製で行う。
- current の形式は generic-v1 または generic-v2。stroke-v1 は新規 current 化不可。
- schema / copy_format の未知キーは400で拒否。copy_format の参照は schema に存在するfieldのみ。
- 既存テンプレートの出力互換を壊さない（脳梗塞5件は旧stroke-v1出力と文字列一致）。

## 完了条件（Definition of Done）

- server: `cd nasukeru-app/server && python init_db.py && python smoke_test.py` が全合格。
- front: `cd nasukeru-app && node --test tests/*.test.js` が全合格。
- 脳梗塞5件の旧 stroke-v1 出力互換スナップショットが引き続き全合格。
- 医療安全（上記4原則）に触れる変更は、該当原則が守られていることを確認してから完了とする。

## 進め方の原則

- 一度に1つずつ確実に。大きな変更は単独コミット単位に分割する。
- 懸念点・疑問点はうやむやにせず、必ずユーザに確認する。勝手に前提を補完しない。
- 既存を壊さない（新旧併存・段階移行）。過剰実装を避ける（既に守られている領域に二重対策を入れない）。
- 医療安全（上記4原則）に触れる変更は、規模が小さくても Critical として慎重に扱う。

---

# AI Orchestration and Auto Routing

## Main Agent

メインエージェントは Sonnet とする。

メインエージェントは以下を担当する。

- ユーザー要求の理解
- タスク分類
- 計画
- 通常のコード実装
- サブエージェントおよび Codex への委任判断
- 各結果の比較と統合
- 最終判断

通常の実装を不要にサブエージェントへ横流ししないこと。

## Available Specialists

### Explore

コードベース調査、依存関係調査、呼び出し元調査、影響範囲調査など、
広範囲の読み取りが必要な場合に使用する。

メインコンテキストを大量の調査ログで汚さないため、
広範囲のコード調査は可能な限り Explore に委任する。

- Explore は事実調査・コード探索に限定する。
- Explore は医療安全、データ安全性、Critical分類の最終判断を行わない。
- Explore の調査結果は Main Sonnet が CLAUDE.md のルールと照合して判断する。
- 必要な場合は deep-reasoner または verifier に判断・検証を委任する。

### deep-reasoner

Opus ベースの Staff Engineer / Architecture Reasoning Specialist。

以下の場合に使用する。

- アーキテクチャ判断
- 原因不明の複雑なバグ
- DB・スキーマ設計
- 認証・認可
- セキュリティに関わる変更
- パフォーマンス調査
- 非同期処理・並行処理
- 複雑な状態遷移
- データ整合性
- 破壊的変更
- 影響範囲の広い変更
- 複数の技術案の比較

通常の実装作業には使用しない。

上記の医療安全の絶対原則・不変条件を常に踏まえて判断する
（定義は `.claude/agents/deep-reasoner.md` に集約）。

### verifier

Sonnet ベースの独立検証担当。

実装後に以下を独立して確認する。

- 要件との不一致
- リグレッション
- edge case の見落とし
- テスト不足
- 型・interface の不整合
- 意図しない挙動変更
- 医療安全リスク
- データ整合性リスク

メインエージェントの実装が正しいと仮定しない。

上記の医療安全の絶対原則・不変条件を常に踏まえて検証する
（定義は `.claude/agents/verifier.md` に集約）。

### Codex

Claude とは異なるモデル系統のシニアエンジニア・ピアとして扱う。

用途を区別する。

Codex Review:
- 実装後のコードレビュー
- バグ
- リグレッション
- 変更漏れ
- 保守性
- 実装上のリスク

Codex Adversarial Review:
- 設計判断の反証
- 前提条件への疑義
- トレードオフの再評価
- Claude側の判断に対する独立した別視点

Codex Rescue:
- Claude側で原因調査が行き詰まった場合
- 別モデルによる独立調査が有効な場合

Codexは単なる形式的レビュアーとして使わない。

## Task Classification

すべてのタスクを開始時に以下の4段階へ分類する。

### Small

条件の例:

- typo
- 文言修正
- lint
- format
- import整理
- 軽微な型修正
- 既存パターンに完全に沿った小規模変更
- 影響範囲が限定された1〜2ファイル程度の変更

標準フロー:

Main Sonnet
→ 必要なテスト
→ 完了

原則として deep-reasoner、verifier、Codex は使用しない。

ただし医療安全、不変条件、データ安全性に触れる場合はファイル数に関係なく上位分類とする。

### Normal

条件の例:

- 既存設計に沿った機能追加
- API追加
- UI追加
- 通常のテスト追加
- 中程度のリファクタ
- 複数ファイルへまたがるが設計判断が単純な変更

標準フロー:

Main Sonnet
→ 実装
→ verifier
→ 必要な修正
→ 完了

以下の場合は Codex Review を追加する。

- 変更範囲が比較的大きい
- 重要な business logic
- 外部APIとの連携
- 既存仕様への影響が懸念される
- verifier が重要な懸念を報告した
- Main Sonnet が独立レビューを有益と判断した

### Hard

条件の例:

- 仕様が曖昧
- 原因不明バグ
- 複数の技術案が存在する
- DB・スキーマ変更
- 認証・認可
- 複雑な状態管理
- 非同期処理・並行処理
- パフォーマンス問題
- データ整合性
- 影響範囲が広い変更

標準フロー:

必要に応じて Explore
→ deep-reasoner
→ Main Sonnet が方針を判断
→ Main Sonnet が実装
→ verifier
→ Codex Review
→ 指摘を比較・精査
→ 妥当な修正のみ反映
→ 完了

複数の設計案があり反証が有益な場合は、
deep-reasoner と Codex Adversarial Review を独立した観点で使用する。

可能な限り一方の結論を先に他方へ与えない。
両者の結果を Main Sonnet が比較・統合する。

### Critical

以下は変更規模に関係なく Critical 候補とする。

- 医療安全
- 患者情報
- 医療判定ロジック
- 認証・認可の重要変更
- セキュリティ
- データ削除
- migration
- データ破壊リスク
- 本番障害
- 大規模アーキテクチャ変更
- 判断ミスのコストが極めて高い変更

標準フロー:

Explore
→ 問題定義
→ deep-reasoner と Codex に独立して検討させる
→ Main Sonnet が結果を比較・統合
→ 以下をユーザーへ提示する

1. 推奨方針
2. 判断理由
3. 主なリスク
4. 代替案
5. ロールバック方法
6. 検証方法

→ ユーザー確認
→ 実装
→ verifier
→ Codex Review
→ 必要な修正
→ 最終検証

Critical ではユーザー確認前に破壊的変更を実行しない。

必要な場合のみ、Fable に手動相談するためのプロンプトをユーザーへ提示する。
Fable を自動利用しようとしない。

## Routing Principles

- タスク開始時に Small / Normal / Hard / Critical を判断する。
- 分類理由は簡潔に示す。
- 分類はファイル数だけで決めない。
- 影響度、可逆性、安全性、不確実性、設計判断の重さを優先する。
- 重いモデルや外部モデルを形式的に呼ばない。
- 使用量節約を優先する。
- deep-reasoner は必要な場合のみ使用する。
- Codex Review を全タスクで機械的に実行しない。
- Review Gate の有効化を前提としない。
- verifier と Codex の指摘は盲目的に反映しない。
- Main Sonnet がコードと要件を確認して妥当性を判断する。
- サブエージェントへは必要なコンテキストと明確な問いを渡す。
- 各専門エージェントの詳細な調査ログをメインコンテキストへ大量に持ち込まず、結論・根拠・リスクを統合する。

## Escalation Rules

以下の場合は現在の分類を1段階以上引き上げる。

- 調査中に影響範囲が想定より広いと判明した
- 既存仕様が不明確
- テストが不足しており挙動を保証できない
- データ移行が必要
- セキュリティまたは医療安全への影響が判明した
- verifier が重大な問題を発見した
- Codex が高確度の重大リスクを指摘した
- deep-reasoner と Main Sonnet の判断が大きく異なる

逆に、調査の結果明らかに単純と判明した場合は分類を下げてもよい。
ただし Critical 条件に該当するものは安易に降格しない。

## Completion Report

作業終了時は簡潔に以下を報告する。

- Task classification
- Classification reason
- Agents/models used
- Codex usage, if any
- Changed files
- Test and verification results
- Remaining risks
