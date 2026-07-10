# 外部レビュー依頼ブリーフ

この文書は、外部レビュー担当者がナスケルの設計意図、現在の実装範囲、直近までの修正内容、重点レビュー観点を短時間で把握するための入口です。

対象リポジトリ: `github.com/nakazawakazuma150226-droid/nasukeru`  
本ブリーフ作成時点の基準コミット: `3b6281f Update design docs for completed phases`

## 1. プロダクト境界

ナスケルは、看護記録テンプレートを選択し、観察項目を入力し、看護記録向けテキストをコピー出力するローカル試作用アプリです。

意図的にやらないこと:

- ランタイムでAI生成しない
- 患者情報や入力内容をDBへ保存しない
- 診断、予測、治療提案をしない
- 外部公開や多人数運用を前提にしない

DBに保存するのはテンプレート定義、検索候補、選択肢、テンプレート履歴、監査ログなどのマスターデータです。

## 2. 最初に読むファイル

レビュー時は以下の順で読むと全体像を追いやすいです。

| ファイル | 目的 |
| --- | --- |
| `README.md` | セットアップ、構成、API、運用前TODO |
| `docs/external-review-brief.md` | 外部レビュー用の短い入口 |
| `docs/handoff.md` | 現在の到達点と再開時サマリ |
| `docs/implementation-progress.md` | フェーズごとの実装・検証履歴 |
| `docs/variable-template-migration-design.md` | schema / copy_format / migration設計 |
| `docs/legacy-cleanup-inventory.md` | 旧形式と削除条件の棚卸し |
| `docs/baseline.md` | 初期baseline固定メモ。過去比較用で、現状仕様の正典ではありません |
| `docs/nasukeru-review.md` | 過去時点のレビュー文書。最新状態の入口は本ブリーフです |

## 3. 現在の技術構成

```text
Browser
  -> index.html / admin.html / css / js
  -> js/templates.js
  -> Flask API
  -> SQLite
```

主な領域:

- 通常画面: `/`
- 管理画面: `/admin`, `/admin/`
- バックエンド: `server/app.py`
- DB初期化・migration: `server/init_db.py`
- schema / copy_format 検証: `server/template_schema.py`
- API統合スモーク: `server/smoke_test.py`
- 通常画面ロジック: `js/app.js`
- copy rendering: `js/copy-renderer.js`, `js/copy-format.js`
- 条件・空欄・安全判定: `js/condition-engine.js`, `js/blank.js`, `js/safety-rules.js`, `js/validation.js`
- 管理画面: `js/admin.js`, `js/admin-builder.js`, `js/admin-simple.js`, `js/simple-template-model.js`

## 4. 安全原則

現状の中心原則です。

1. 入力初期値は空欄にする
2. 患者情報や入力内容は保存しない
3. ランタイムでAI生成を使わず、決定的なテンプレート変換だけを行う
4. 入力値が出力から無言で欠落しないよう、未参照・未入力・未解決参照を警告する

`showIf` によって入力済みfieldを含むコピー行が除外された場合も、コピー前警告の対象です。

コピー時は原則として警告してコピー可能です。ただし `blankPolicy=block`、`hardRange` 逸脱、条件評価エラーなど、明示された安全ルールだけコピーを止めます。

## 5. データモデルと版管理

テンプレート定義はバージョン管理されています。

- `templates`: テンプレート本体の現行ポインタと互換用定義
- `template_versions`: schema / copy_format の不変バージョン
- `template_audit_logs`: 作成、公開、rollback、削除、復元、migrationの監査ログ
- `schema_migrations`: `init_db.py` 内の冪等migration記録
- `quick_templates`, `search_keywords`, `template_groups`: 通常画面の導線定義

版管理方針:

- 編集保存は既存versionを上書きせず、新しいdraft versionを作る
- 公開はdraftをpublishedにし、現行published以外をretiredへ寄せる
- rollbackは過去versionへポインタを戻さず、過去内容を複製した新しいpublished versionを作る
- 削除は論理削除
- DB triggerで `current_version_id` の整合性を守る

## 6. schema / copy_format

### schemaFormat

- `stroke-v1`: 旧脳梗塞固定schema。履歴・後方互換用にサーバ側で維持
- `generic-v1`: section / field ベースの可変schema
- `generic-v2`: `generic-v1` に `visibleIf` / `requiredIf` などの条件式を追加

通常画面の主経路は `generic-v1` / `generic-v2` です。`stroke-v1` 固定描画と固定コピー分岐は通常画面から撤去済みです。

### copy_format

- `text-v1`: 単一コピー出力。`lines` に文字列行または行オブジェクトを持つ
- `multi-v1`: 複数の名前付きコピー出力。`variants` に `{ id, label, lines }` を持つ

`multi-v1` は通常画面のコピー出力モーダルでvariantを切り替えます。選択中variantに含まれない入力済みfieldはコピー前警告になります。

## 7. 標準テンプレート

DB初期化後の標準テンプレート:

| id | schemaFormat | 内容 |
| --- | --- | --- |
| `mca` | `generic-v1` | MCA領域梗塞 |
| `aca` | `generic-v1` | ACA領域梗塞 |
| `pca` | `generic-v1` | PCA領域梗塞 |
| `lacunar` | `generic-v1` | ラクナ梗塞 / 穿通枝梗塞 |
| `brainstem` | `generic-v1` | 脳幹梗塞 |
| `neuro_common` | `generic-v2` | 脳卒中共通 |
| `chronic_subdural` | `generic-v2` | 慢性硬膜下血腫 |

`cerebral_infarction` は脳梗塞5件をまとめるtemplate groupです。

## 8. 直近までの主なコミット履歴

`887fe88..HEAD` の履歴を確認した要約です。

| commit | 内容 |
| --- | --- |
| `be594f8` | baseline文書追加 |
| `0c65904` | 明示的template group routing |
| `4ea663e` | 楽観的テンプレート版競合制御 |
| `aa6d2b9` | option value / label分離 |
| `064fa7b` | generic値状態の型付け |
| `76e920b` | generic-v2 condition engine |
| `9ef3405` | medical safety rule layer |
| `0da7e8a` | admin template builder |
| `03b5cbd` | version publication workflow |
| `615e7af` | legacy cleanup inventory |
| `b6348ee` | residual safety refinements |
| `d20f8aa` | narrow layout usability |
| `54c499f` | corrective hardening |
| `6fffae9` | stroke templatesのJCS select化 |
| `3a8db79` | blank stroke copy field omission |
| `bf358ba` | simple template authoring foundation |
| `cb13728` | built-in template clinical input defects修正 |
| `afd4569` | left/right-fixed stroke findings修正 |
| `457cce0` | section-level visibleIf foundationとneuro_common条件項目 |
| `ea4e2fd` | blank判定集約と安全チェック強化 |
| `547f868` | 新規テンプレートをdraft-only化 |
| `ad37597` | generic preview renderer共有化 |
| `13437a8` | discovery management API/UI |
| `c075832` | authoring / content / cleanup phases前進 |
| `501105b` | multi-v1 derived copy output |
| `3b6281f` | 完了フェーズに合わせた設計書更新 |

## 9. レビューしてほしい観点

優先度の高いレビュー観点です。

1. 医療安全原則が設計・DB・API・フロントで一貫しているか
2. 入力値がコピー出力から無言で欠落する経路が残っていないか
3. `generic-v2` 条件式、`multi-v1` variant、未参照警告の仕様が矛盾していないか
4. テンプレート版管理、rollback、DB triggerの不変条件が破れないか
5. migration `010` / `011` / `012` / `013` が既存DBと新規DBの両方で冪等に動くか
6. local-only前提のセキュリティ境界がREADMEの運用前TODOと整合しているか
7. 通常画面・管理画面のアクセシビリティ、特にコピー前警告が利用者に伝わるか
8. 外部運用へ進める場合に必要な認証、承認、RBAC、バックアップ、CIが明確か

## 10. 既知の未実装 / 次候補

- 状況グループ: `generic-v2` の制御fieldと `multi-v1` variantを連動させる想定
- バージョン差分ビュー
- import / export
- 承認フロー
- 認証 / RBAC
- CI / GitHub Actions
- `multi-v1` 専用フォームUI。現状はDeveloper Mode / JSONで編集する

## 11. 検証コマンド

```powershell
cd nasukeru-app
python -m py_compile server\template_schema.py server\init_db.py server\app.py server\smoke_test.py
node --check js\app.js
node --check js\admin.js
node --check js\admin-builder.js
node --check js\admin-simple.js
node --check js\copy-renderer.js
node --check js\copy-format.js
node --check js\validation.js
node --test tests\*.test.js
python server\init_db.py
python server\smoke_test.py
```

ローカル起動:

```powershell
cd nasukeru-app
python server\init_db.py
python server\app.py
```

標準URL:

- 通常画面: `http://127.0.0.1:8000/`
- 管理画面: `http://127.0.0.1:8000/admin`
