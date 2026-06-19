# ナスケル

看護記録テンプレート入力支援アプリのデモです。

現状は、登録済みテンプレートを選択し、観察項目を入力して、看護記録向けの文章をコピー出力する機能に絞っています。

## 現在の方針

- AI生成は使用しない
- 患者情報や入力内容は保存しない
- テンプレートの初期値は空欄
- コピー前に重要項目の未入力を警告する
- 警告があってもコピーは止めない

## ファイル構成

```text
nasukeru-app/
  index.html
  README.md
  .gitignore
  assets/
    nasukeru-icon.jpg
  css/
    styles.css
  docs/
    handoff.md
  js/
    templates.js
    validation.js
    copy-format.js
    app.js
```

## 各ファイルの役割

- `index.html`
  - 画面の骨組み
  - CSS/JSの読み込み

- `css/styles.css`
  - レイアウト、見た目、レスポンシブ対応

- `js/templates.js`
  - 現在のローカルテンプレート定義
  - 将来DB/API連携に差し替える境界

- `js/validation.js`
  - 未入力警告の判定と表示

- `js/copy-format.js`
  - コピー出力文の生成
  - クリップボードコピー

- `js/app.js`
  - 画面生成、検索、タブ切り替え、イベント処理

- `docs/handoff.md`
  - 現状仕様、将来DB設計、監査ログ設計、実装フェーズの引継ぎメモ

## 動かし方

`index.html` をブラウザで開くと動作します。

ローカルサーバーで確認する場合:

```bash
python -m http.server 8000
```

その後、ブラウザで `http://localhost:8000` を開いてください。

## 将来のDB/API連携

DB連携時は、まず `js/templates.js` の以下の関数をAPI呼び出しへ差し替える想定です。

```js
async function getTemplates() {
  return STROKE_TYPES;
}

async function getQuickTemplates() {
  return QUICK_LIST;
}

async function getRestOptions() {
  return REST_OPTS;
}
```

将来的なAPI例:

- `GET /templates`
- `GET /templates/:id`
- `POST /templates`
- `POST /templates/:id/versions`
- `POST /templates/:id/delete`
- `POST /templates/:id/restore`
- `GET /templates/:id/logs`

## GitHub登録時の推奨

GitHubに登録する場合は、この `nasukeru-app` フォルダをリポジトリの初期状態にするのが分かりやすいです。

初回コミット例:

```text
Initial split static demo
```

コマンド例:

```bash
git init
git add .
git commit -m "Initial split static demo"
git branch -M main
git remote add origin <GitHubリポジトリURL>
git push -u origin main
```

次のコミット候補:

- テンプレートJSONスキーマ整理
- 管理画面設計
- DB/API連携
- 監査ログ設計
