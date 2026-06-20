# ナスケル 引継ぎメモ

## 1. 現状のアプリ概要

ナスケルは、看護師が患者の病状確認後に看護記録へ転記する文章を作るための、テンプレート入力支援デモアプリ。

現時点では、機能を「登録済みテンプレートを選択し、必要項目を入力し、コピー出力する」ことに絞っている。

現在の推奨作業対象:

- `C:\Users\kazum\Documents\Codex\2026-06-20\kor\outputs\nasukeru-app\index.html`
- `C:\Users\kazum\Documents\Codex\2026-06-20\kor\outputs\nasukeru-app\css\styles.css`
- `C:\Users\kazum\Documents\Codex\2026-06-20\kor\outputs\nasukeru-app\js\templates.js`
- `C:\Users\kazum\Documents\Codex\2026-06-20\kor\outputs\nasukeru-app\js\validation.js`
- `C:\Users\kazum\Documents\Codex\2026-06-20\kor\outputs\nasukeru-app\js\copy-format.js`
- `C:\Users\kazum\Documents\Codex\2026-06-20\kor\outputs\nasukeru-app\js\app.js`
- `C:\Users\kazum\Documents\Codex\2026-06-20\kor\outputs\nasukeru-app\assets\nasukeru-icon.jpg`

旧デモファイル:

- `C:\Users\kazum\Downloads\medical-template-app.html`
- `C:\Users\kazum\Downloads\nasukeru-icon.jpg`

今後は分割版の `nasukeru-app` を正とし、旧デモHTMLは参照用として扱う。

## 2. 現状の主要仕様

### 2.1 対象テンプレート

現在は脳梗塞テンプレートのみ登録済み。

タブで以下の分類を切り替える。

- MCA領域梗塞
- ACA領域梗塞
- PCA領域梗塞
- ラクナ梗塞／穿通枝梗塞
- 脳幹梗塞

### 2.2 入力項目

主な入力欄:

- バイタル
  - JCS
  - 体温
  - 血圧
  - 脈拍
  - SpO2
- 症状
  - 頭痛
  - めまい
  - 嘔気
- 神経所見
  - 瞳孔
  - 対光反射
  - 眼球位置
  - バレー徴候
  - ミンガッチー徴候
  - MMT
  - NIHSS
  - その他神経症状
- 安静度
  - ベッド上安静
  - ベッド上フリー
  - 病棟内フリー
  - 院内フリー
  - リハビリに準ずる

### 2.3 初期値

全テンプレートの入力値は空欄。

理由:

- 初期値が入っていると、実測・確認前の値をそのまま記録してしまうリスクがあるため。
- 例示は `placeholder` として表示し、記録本文には入らないようにしている。

### 2.4 コピー出力

「コピー出力」ボタンを押すと、入力内容を記録文形式に整形してモーダル表示する。

未入力項目は本文上では `__` として出力する。

コピーはブラウザのクリップボードAPIで実行する。

### 2.5 未入力警告

コピー出力時に、重要項目が未入力の場合は警告を表示する。

ただし、コピー自体は止めない。

理由:

- 現場では未確認・未実施・該当なしなど、空欄でよいケースがあるため。

現在の警告対象:

- JCS
- 体温
- 血圧
- 脈拍
- SpO2
- NIHSS
- 安静度
- 瞳孔
- 対光反射
- MMT 右上肢
- MMT 右下肢
- MMT 左上肢
- MMT 左下肢

### 2.6 削除済み/廃止済み仕様

以下は現在のHTMLから削除済み。

- AI自動生成
- 外部API通信
- ローカル保存
- 保存済みテンプレート欄
- テンプレート保存モーダル

理由:

- 医療情報や患者状態に近い情報を外部送信するリスクを避けるため。
- デモ段階では「入力とコピー」に機能を絞った方が安全で分かりやすいため。

### 2.7 UI/表示

- ヘッダー左にナスケルのアイコンを表示。
- favicon も同じ画像を参照。
- Google Fonts 依存は削除済み。
- Windows標準寄りの日本語フォントを使用。
- スマホ/タブレット向けのレスポンシブCSSを追加済み。
- 安静度のラジオボタンはキーボードフォーカスできる隠し方に修正済み。

## 3. 現状の制約

### 3.1 デモ用途

現在の画面は静的HTML/CSS/JSをFlaskから配信するデモ。

テンプレート定義はSQLiteに保存し、`js/templates.js` のAPI境界から読み込む。

DBファイルは既定では `server/nasukeru.db`。運用配置を変える場合は `NASUKERU_DB_PATH` で指定する。

### 3.2 永続化なし

入力内容とログは保存しない。

テンプレート本体、安静度選択肢、クイックリスト、検索候補はSQLiteに保存する。

リロードすると入力内容は消える。

### 3.3 監査ログなし

現状では、誰がいつテンプレートを変更したかは記録されない。

ただし、現在はテンプレート編集機能自体を持っていないため、運用リスクは限定的。

### 3.4 配布時の注意

HTMLは `nasukeru-icon.jpg` を相対参照している。

配布時は以下を同じフォルダに置く必要がある。

- `medical-template-app.html`
- `nasukeru-icon.jpg`

## 4. 将来拡張: DB連携によるテンプレート管理

今後、テンプレートの追加・修正・削除を行う場合は、単純な保存機能ではなく、承認済みテンプレート管理機能として設計する。

推奨方針:

- テンプレート本体
- バージョン履歴
- 監査ログ
- 復元
- 権限管理
- 承認フロー

を分けて考える。

## 5. 推奨データモデル

### 5.1 templates

現在有効なテンプレートの基本情報を保持する。

主なカラム案:

- `id`
- `title`
- `category`
- `disease_name`
- `description`
- `current_version_id`
- `status`
  - `draft`
  - `review`
  - `approved`
  - `published`
  - `archived`
- `is_active`
- `display_order`
- `created_by`
- `created_at`
- `updated_by`
- `updated_at`
- `deleted_at`

削除は物理削除ではなく、`deleted_at` や `is_active=false` による論理削除にする。

### 5.2 template_versions

テンプレートの各バージョンを保持する。

主なカラム案:

- `id`
- `template_id`
- `version_number`
- `schema_json`
- `copy_format_json`
- `change_summary`
- `change_reason`
- `created_by`
- `created_at`
- `approved_by`
- `approved_at`

`schema_json` には入力項目定義を保存する。

例:

```json
{
  "sections": [
    {
      "title": "バイタル",
      "fields": [
        {"key": "jcs", "label": "JCS", "type": "text", "requiredWarning": true},
        {"key": "temperature", "label": "体温", "type": "text", "requiredWarning": true}
      ]
    }
  ]
}
```

### 5.3 template_audit_logs

テンプレートに対する操作履歴を保存する。

主なカラム案:

- `id`
- `template_id`
- `version_id`
- `action`
  - `create`
  - `update`
  - `delete`
  - `restore`
  - `approve`
  - `publish`
  - `archive`
- `actor_id`
- `actor_name`
- `acted_at`
- `before_json`
- `after_json`
- `diff_json`
- `reason`
- `client_info`

ログは後から改ざんしづらい設計にする。

最低限、通常画面からログ削除できないようにする。

### 5.4 users

操作した人を記録するために必要。

主なカラム案:

- `id`
- `name`
- `role`
  - `viewer`
  - `editor`
  - `reviewer`
  - `admin`
- `department`
- `is_active`
- `created_at`

## 6. 操作仕様案

### 6.1 テンプレート追加

流れ:

1. 編集者がテンプレートを作成
2. `templates` に基本情報を作成
3. `template_versions` に version 1 を作成
4. `template_audit_logs` に `create` を記録
5. ステータスは `draft` または `review`

### 6.2 テンプレート修正

既存バージョンを直接上書きしない。

流れ:

1. 現行テンプレートを編集画面で開く
2. 修正内容を保存
3. 新しい `template_versions` を作る
4. `templates.current_version_id` を必要に応じて更新
5. `template_audit_logs` に `update` を記録

公開中テンプレートの場合は、即時反映せず `review` を挟む設計が望ましい。

### 6.3 テンプレート削除

物理削除しない。

流れ:

1. 削除理由を入力
2. `templates.is_active=false`
3. `templates.deleted_at` を設定
4. `template_audit_logs` に `delete` を記録

通常の入力画面には表示しない。

### 6.4 復元

過去バージョンまたは削除済みテンプレートを復元できるようにする。

流れ:

1. 履歴一覧から復元対象を選択
2. 復元理由を入力
3. 選択した過去バージョンを新しい最新版として作成
4. `template_audit_logs` に `restore` を記録

過去バージョン自体を直接現在版に戻すのではなく、「復元操作によって新バージョンを作る」方が監査上分かりやすい。

## 7. 画面構成案

### 7.1 通常入力画面

対象:

- 一般ユーザー
- 新人看護師
- 記録作成者

機能:

- 承認済み/公開中テンプレートのみ表示
- 入力
- 未入力警告
- コピー出力

表示するテンプレート条件:

- `status = published`
- `is_active = true`
- `deleted_at IS NULL`

### 7.2 テンプレート管理画面

対象:

- 編集権限を持つユーザー
- 管理者
- 承認者

機能:

- 一覧
- 新規作成
- 編集
- 論理削除
- 履歴確認
- 復元
- 承認
- 公開/非公開切り替え

一覧で表示したい項目:

- テンプレート名
- カテゴリ
- ステータス
- 現在バージョン
- 最終更新者
- 最終更新日時
- 承認者
- 承認日時

### 7.3 履歴画面

機能:

- バージョン一覧
- 変更者
- 変更日時
- 変更理由
- 差分表示
- このバージョンを復元

差分はJSONそのままではなく、ラベル単位で見せるのが望ましい。

例:

- 「警告対象: SpO2 を追加」
- 「安静度: 院内フリー を追加」
- 「コピー出力: NIHSSの表記を変更」

## 8. 権限設計案

### viewer

- テンプレート使用
- コピー出力

### editor

- 下書き作成
- 修正案作成

### reviewer

- 内容確認
- 承認
- 差し戻し

### admin

- 公開/非公開
- 復元
- 権限管理

本番運用では、誰でも公開テンプレートを直接編集できる状態は避ける。

## 9. 実装ステップ案

### Phase 1: 現状デモの安定化

完了済み:

- AI削除
- 保存削除
- 初期値空欄化
- コピー出力
- 未入力警告
- アイコン追加
- レスポンシブ対応
- 外部フォント依存削除

### Phase 2: テンプレート定義の分離

完了済み。

単一HTMLから以下の構成へ分割した。

```text
nasukeru-app/
  index.html
  README.md
  assets/
    nasukeru-icon.jpg
  css/
    styles.css
  js/
    templates.js
    validation.js
    copy-format.js
    app.js
```

`templates.js` に `getTemplates()` / `getQuickTemplates()` / `getRestOptions()` を用意し、将来API呼び出しへ差し替える境界とした。

目的:

- 後でDB化しやすくする
- テンプレート追加に備える

### Phase 3: バックエンド/API追加

API例:

実装済み:

- `GET /api/health`
- `GET /api/templates`
- `GET /api/templates/:id`
- `GET /api/quick-templates`
- `GET /api/rest-options`
- `GET /api/search-keywords`

検証用:

- `py -3.10 server\smoke_test.py`

今後の候補:

- `POST /api/templates`
- `POST /api/templates/:id/versions`
- `POST /api/templates/:id/delete`
- `POST /api/templates/:id/restore`
- `GET /api/templates/:id/logs`

### Phase 4: DB保存

SQLite、PostgreSQL、Supabase などを検討。

デモ継続なら SQLite。

複数端末・認証・監査ログまで考えるなら Supabase または PostgreSQL + 独自API。

### Phase 5: 承認フロー

公開テンプレートは承認済みのみ通常画面に出す。

下書き・レビュー中は管理画面にだけ表示する。

## 10. 今後の注意点

### 医療安全

- 初期値を入れない方針は維持する。
- 記録支援であり、判断支援や診断支援に見えすぎない文言にする。
- 承認者、版数、最終更新日を表示できると信頼性が上がる。

### 個人情報

- 患者氏名やIDをテンプレート管理側に保存しない。
- 入力内容を保存する場合は、医療情報として扱う必要がある。
- 現状のコピー専用設計では患者情報を保存しないため、リスクは比較的低い。

### 監査性

- 変更ログは削除不可を原則にする。
- 削除・復元・承認には理由入力を必須にする。
- 過去バージョンは直接改変しない。

### UI

- 通常入力画面と管理画面は分ける。
- 新人向け画面には管理機能を出しすぎない。
- 未入力警告は現状どおり、コピーを止めない運用がよい。
