# ナスケル 全体レビュー

対象リポジトリ: `github.com/nakazawakazuma150226-droid/nasukeru`
レビュー方法: コード・設計ドキュメントの精読（動作実行はなし）
スタンス: バランス型（良い点＋改善点）
レビュー範囲: 全体構想 / アーキテクチャ / 医療安全の実装 / UI・UX / エージェント構成 / テスト / ドキュメント / セキュリティ

---

## 0. 総評

**結論から言うと、プロトタイプ（ローカル試作）としては非常に完成度が高い。** 特に「医療安全を最優先原則として掲げ、それを設計・DB・API・フロントの各層で実際にコードとして担保している」点は、社内ツールや個人開発の水準を大きく超えている。ドキュメントとプロセス規律（段階実装ゲート、baseline固定、tech-debt棚卸し）も、多くの本番システムより整っている。

一方で、**「試作として優れている」ことと「このまま多人数・臨床運用に耐える」ことの間には大きな段差**があり、その段差は主にCI/自動化・アクセシビリティ・共有運用（認証/承認/監査権限）に集中している。README自身がこの段差を正直に列挙している点は好印象。

現状で「医療安全上の致命的欠陥」は読解の範囲では見つからなかった。以下の改善提案は、いずれも「今すぐ危険」ではなく「堅牢化・運用化・磨き込み」の性質のもの。

### 評価サマリ

| 観点 | 評価 | 一言 |
| --- | --- | --- |
| 全体構想・スコープ | ◎ | ランタイムAI排除・非保存・テンプレート変換のみ、という安全posture が一貫 |
| アーキテクチャ | ◎ | strangler-fig移行、版管理、多層防御が教科書的 |
| 医療安全の実装 | ◎ | 4原則が構造的に担保されている（1箇所だけ設計判断ポイントあり） |
| UI/UX | ○ | 臨床向けに落ち着いた設計。アクセシビリティに一貫性の欠けあり |
| エージェント構成 | ○〜◎ | 役割分担・分類・エスカレーションが洗練。遵守の機械的担保が課題 |
| テスト | ○ | 中核ロジックの単体＋API統合は厚い。数分岐の明示カバレッジ要確認 |
| ドキュメント | ◎ | 過剰なほど充実。わずかに記述の重複（ドリフト源） |
| セキュリティ（試作前提） | ○ | 局所ガード・多層防御は適切。運用前TODOは正直に明記済み |

---

## 1. 全体構想（Concept / Vision）

### 良い点

- **スコープの絞り込みが明快**。「登録済みテンプレートを選び、観察項目を入力し、看護記録向けの文章をコピー出力する」だけに機能を限定している。機能を足すより先に「何をしないか」を決めているのは、安全志向のツールとして正しい判断。
- **ランタイムでの生成AIを意図的に排除**（`CLAUDE.md` 原則3）。臨床記録の文言支援でLLM生成を使わず「テンプレート変換のみ」に留めるのは、幻覚・非再現性のリスクを排する妥当な安全posture。しかも「これはアプリ出力の原則であって、開発支援のAI利用は別」と明確に線引きしている。
- **「警告してコピー可、ブロックは明示ルールのみ」という運用ポリシー**（原則4）は、安全と「臨床現場での使い勝手（過剰ブロックで邪魔しない）」のバランスが取れている。
- 進化の道筋（固定schema → 可変schema → 条件付きschema → 状況グループ/派生出力/承認フロー）が `variable-template-migration-design.md` に描かれており、product roadmap として筋が通っている。

### 検討したい点

- **プロダクトの位置づけを明文化しておくと、将来のスコープクリープを防げる**。現状は「看護記録の文言化を補助する道具」であって「電子カルテ（EMR）でも医療機器ソフトでもない」。この一文を README か docs の冒頭に置いておくと、（特に他エンジニアに共有した際に）「患者データを保存させたい」「診断ロジックを入れたい」といった要望が来たときの判断基準になる。日本の医療機器プログラム（SaMD）該当性や院内IT governance は、そこに踏み込んだ瞬間に一気に支配的要件になるため、境界の明示は安全弁になる。
- **最大の未対応領域は「単一ユーザ・ローカル」から「共有・運用」への飛躍**。認証・承認フロー・保護されたDB配置・WSGI・バックアップは README の「運用前の注意」に列挙済みだが、これは機能追加ではなく再設計に近い。特に「誰がテンプレートを編集・公開してよいか（RBAC）」「患者データ隣接の監査ログを誰が閲覧してよいか」は、構想段階で方針だけでも固めておく価値がある。

---

## 2. アーキテクチャ / 設計

### 良い点

- **レイヤリングが素直**。`ブラウザ(HTML/CSS/JS) → js/templates.js（API境界） → Flask → SQLite`。`js/app.js` がDB構造を直接知らず、必ず `templates.js` を経由する、という境界設計が守られている（README のディレクトリ方針どおり実装されている）。
- **段階移行が strangler-fig パターンの好例**。`stroke-v1`（旧・固定）/ `generic-v1`（現行・主経路）/ `generic-v2`（条件付き）を併存させ、脳梗塞5件は generic-v1 へ移行しつつ「旧 stroke-v1 出力と文字列一致」のスナップショットで後方互換を担保。新旧を同時に生かしながら段階的に置き換える、という難所を丁寧にやっている。
- **版管理モデルが本格的**（`server/app.py`）。
  - 版は不変（既存行を上書きしない）、`draft → published → retired` の状態機械。
  - 楽観ロック: `base_version_id` が保存時点の `current_version_id` と不一致なら `409`（競合更新を検出）。
  - rollback はポインタを戻さず「過去版の内容を複製した新published版」を作り、公開履歴の時系列を保つ。
  - すべての書き込みに監査ログ（`template_audit_logs`）を残す。削除は論理削除のみ。
  - これは content-versioning system として、そのまま設計例として通用する完成度。
- **current-version 不変条件の多層防御が白眉**。「`current_version_id` は同一テンプレートの published 版のみを指せる／現行公開版は retire 不可」という不変条件が、(1) アプリロジック、(2) **DBトリガ**（`server/init_db.py` の `trg_templates_current_version_*` が `RAISE(ABORT, ...)`）、(3) 統合テスト（`smoke_test.py` の `assert_current_version_integrity`）の**3層で守られている**。将来どこかのコード経路にバグが入っても、DB自身がデータ破壊を拒否する。安全critical なデータモデルとして理想的な作り。
- **スキーマ検証がホワイトリスト方式**（`server/template_schema.py`）。未知キーは全階層で `reject_unknown_keys` により拒否。加えて参照整合性（copy_format の参照先は schema に存在する field のみ）、条件式の型検査（`gt/gte/...` は number field＋number値、`in/contains` は選択肢値の実在チェック）、条件ネスト深さ上限（`CONDITION_MAX_DEPTH = 10`）、そして **visibleIf の循環検出**（`detect_visible_condition_cycles` によるDFS）まで実装。非常に堅い。
- **「安全 by construction」の自動コピー生成**（`js/simple-template-model.js`）。Template Builder は section/field/選択肢を編集させ、内部で `sec_/fld_/opt_` のIDを自動採番（作者はIDを一切扱わない）。`editorModelToCopyFormat` が field 構造から copy_format を自動コンパイルするため、**auto モードでは「存在しない field を参照する copy_format」という誤りが構造的に発生し得ない**。手動が必要なときだけ `copyMode: "custom"` で退避でき、その場合もサーバ検証が効く。良い抽象化。
- **中核ロジックが純粋・テスト可能**。`copy-renderer` / `condition-engine` / `safety-rules` / `generic-values` は UMD で切り出され、node 単体テストで検証できる形になっている。

### 改善提案

- **[中] `isBlank` の4重定義**。`js/condition-engine.js` / `js/safety-rules.js` / `js/copy-renderer.js` / `js/generic-values.js` に、ほぼ同一の `isBlank`（配列は空なら空、`0` は空でない、等）が別々に定義されている。現状は全て意味が一致しているが、**安全critical なアプリで「空欄判定」がモジュール間で将来ズレると、無言の欠落や条件誤評価に直結する**。ここは最優先で単一の source of truth（例: `js/nasukeru-blank.js` を作って各モジュールが import、あるいは全て `condition-engine` の実装を参照）に集約する価値がある。「`0` は空欄扱いしない」という一点の一貫性を守るためだけでも、集約する意義は大きい。
- **[中] `package.json` / CI / lint が未整備**。リポジトリに `package.json` がなく、JSテストは README にハードコードされた Windows の node パス（`C:\Users\kazum\...\node.exe`）で走らせる前提になっている。プロジェクト自身が掲げている「スナップショット整合性のCI強制」という設計目標が、リポジトリ上ではまだ配線されていない。
  - `package.json`（`"test": "node --test tests/*.test.js"`）を置く。
  - GitHub Actions で「`python server/init_db.py && python server/smoke_test.py`」と「node テスト」を両方回すワークフローを追加する。
  - これで `CLAUDE.md` の Definition of Done と「脳梗塞5件の出力互換スナップショット」ゲートが自動化され、構想どおりのCI enforcement になる。
- **[小] `detect_high_risk_changes` の `repr(line)` 比較**（`template_schema.py`）。正規化（`ordered_with_known_keys`）でキー順が決定的なので現状は動くが、「Python の repr 文字列で構造等価を判定」はレビュアーに前提知識を要求する脆さがある。正規化済み dict / JSON 同士の比較に置き換えると意図が明確になる。
- **[小] Python sqlite の明示 `BEGIN`**。デフォルト isolation_level のまま `conn.execute("BEGIN")` を使っており、経路によっては「トランザクション中に BEGIN」の footgun になり得る。`sqlite3.connect(..., isolation_level=None)` ＋明示BEGIN、または 3.12+ の `autocommit` でトランザクション境界を曖昧さなく制御しておくと安心（単一ユーザ・ローカルでは実害は出にくいので優先度低）。
- **[小] stroke-v1 のランタイム経路がデッドコード化**。脳梗塞5件が generic-v1 へ移行済みのため、`getTemplates` は現行版（generic-v1）を返し、`app.js` の `showStroke` / `renderStrokeBody` と `copy-format.js` の stroke 分岐は実質到達不能。`legacy-cleanup-inventory.md` の Phase 9 で追跡済みなので問題はないが、Removal Gate を満たしたら早めに落とすと保守負荷が減る。

---

## 3. 医療安全の実装（4原則の担保状況）

`CLAUDE.md` の「絶対原則」が、実際にどう強制されているかを層ごとに確認した。結論として**4原則は概ね構造的に担保されている**。

| 原則 | 担保箇所 | 評価 |
| --- | --- | --- |
| ①初期値は空欄／書込APIでも初期値入り stroke-v1 は400 | `template_schema.py: enforce_empty_initial_values`。generic系は schema に「初期値」を表現するキー自体が存在しない（`default`/`value` 不許可）ため構造的に空欄。`smoke_test.py` に400テストあり | ◎ 構造的に担保 |
| ②患者情報・入力を保存しない | 入力値はDOM/メモリのみ。DBに入るのはテンプレ定義・検索候補・選択肢等のマスタのみ。グループ内タブ切替の状態保持もメモリのみ | ◎ |
| ③ランタイムで生成AIを使わない | コピー生成は `copy-renderer` の純粋関数（プレースホルダ置換＋条件）だけ。AI呼び出し経路なし | ◎ |
| ④入力値が出力から無言で欠落しない／停止は明示ルールのみ | text-v1 では、参照済みだが空欄の field は `"__"` を出力しつつ `unresolvedRefs` に積み、`mergeCopyRenderWarnings` が「未入力のままコピー文に含まれています」と警告。ブロックは `blankPolicy=block` / `hardRange` 逸脱 / 条件計算エラー（fail-closed）のみ | ○〜◎（下記1点を要検討） |

### 特に良い点

- **fail-closed の徹底**。`js/app.js: updateGenericConditions` は visibleIf の相互依存を固定点反復で解決し、`rows.length + sections.length + 1` 回で安定しなければ `conditionError = "true"` を立て、`validation.js` がコピーをブロックする（「条件表示の設定を確認してください」）。つまり循環条件は**サーバ側で作成時に400拒否**され、**万一すり抜けてもランタイムで安全側に倒れる**。二重の安全網。
- **非表示 field の値クリア**。条件で非表示になった行は値をクリアし（`applyInputValue(input, "")`）、隠れた値が copy や未入力警告に漏れないようにしている。`safety-rules.js` も `visible === false` の field は判定対象外にする。
- **臨床的な読みやすさへの配慮**。テスト `copy-renderer.test.js` の「optional conditional field stays on its own line」は、空欄 optional が直前の値に `ニカルジピン__` のようにくっついて誤読されるのを防ぐ回帰テスト。ドメインの機微を理解した設計。
- **数値入力の日本語対応**（`generic-values.js: normalizeNumberInput`）。全角数字・全角ピリオド・各種マイナス記号を正規化。臨床現場のタブレット入力で効く。
- **作成時の安全ヒント**。`collect_unreferenced_fields`（出力に含まれない入力項目を警告）、`collect_duplicate_section_conditions`（同一条件で表示されるセクションのコピペミスを警告）は、テンプレート作者向けのドメイン特化型の安全チェック。

### 検討したい1点（設計判断ポイント）

- **[検討] ランタイムでの「入力済みだが未参照」の無言欠落**。text-v1 の copy_format が参照していない field に看護師が値を入力した場合、その値はコピー出力から**黙って落ちる**（ランタイム警告なし）。これは作成時に `collect_unreferenced_fields` で作者へ警告される（作成・公開レスポンスと管理画面に表示）ことで**緩和されている**が、原則④「入力した観察値が出力から無言で欠落してはならない」の最も厳密な読みからすると、「コピーの瞬間」には強制されていない唯一の箇所。
  - 現状の設計（作成時ゲート＋監査ログ）は十分に妥当だが、防御を一段厚くするなら「入力画面でこの項目に『コピーに含まれません』を控えめに表示」あるいは「コピー前チェックで、値があるのに未参照の項目を確認警告に含める」といった選択肢がある。
  - いずれにせよ「作成時に警告するが、作者が無視して公開できる」という現状仕様を、docs に**意図的な判断として明記**しておくとよい（レビュー観点では、ここが唯一「原則の文言 vs 実装」で議論の余地がある箇所）。
- **[小] fallback コピー経路**。`copy_format_json` が無い generic テンプレートは `buildGenericCopyText` の暫定形式（`label：value`）で全可視 field を出力する。この経路では `unresolvedRefs` のマージが走らない（`buildGenericTemplateCopyText` を通らない）。暫定形式では全 field が出るので無言欠落は起きないが、text-v1 経路との警告挙動の非対称は把握しておくとよい。

---

## 4. UI / UX

### 良い点

- **落ち着いた臨床向けの見た目**。`css/styles.css` は CSS カスタムプロパティで design token を定義し、`--neu`（脳神経）/ `--sav`（記録）/ `--emg`（警告）など意味づけされた色ロールを持つ。散らからず、医療現場に馴染むトーン。
- **レスポンシブ対応**。`@media (max-width: 820px)` と `460px` のブレークポイント、モバイルでテンプレート選択時に `scrollIntoView`、数値入力の `inputMode="decimal"`＋全角正規化。タブレット/スマホでの看護師利用を意識できている。
- **コピーの安全UXが明快**。コピーモーダルはプレビュー＋警告パネルを持ち、block は赤系で「修正が必要」、warn は「確認が必要」と表示を出し分け、`doCopy` は block ならコピー不可、warn なら `confirm` で確認。安全ルールが操作フローに自然に組み込まれている。
- **検索/導線**。ハイライト付きオートコンプリート、専用テンプレート一覧、グループのタブ切替（`buildTemplateGroupCard` はタブごとの入力状態をメモリ保持して復元）。空状態・初期化エラー状態も専用メッセージで処理。
- **管理画面のアクセシビリティは良好**。`admin.html` は `role="tablist"` / `role="dialog"` / `aria-modal` / `aria-labelledby` / `aria-label` を適切に付けている。Template Builder は field type / blank policy を人間語（「1つ選ぶ」「未入力ではコピーできない」）に翻訳しており、非技術者の作者に優しい。JSON Developer Mode という退避口も用意。
- **XSS 耐性**。テンプレート由来の文字列（ラベル・選択肢等）は `textContent`／`createElement` で描画し、`innerHTML` は静的SVGとクリアのみ。テンプレは元々ローカルDB由来だが、それでも `textContent` を使うのは正しい。

### 改善提案

- **[中] アクセシビリティの一貫性欠如（コピーモーダル側）**。管理モーダルは ARIA を備えるのに、**通常画面のコピーモーダル `#cov` には `role="dialog"` / `aria-modal` が無く**、フォーカストラップ・フォーカス復帰も無い。さらに**警告パネル `#warn` とトースト `#toast` に `aria-live` が無い**ため、スクリーンリーダー利用者に「コピーできません」「確認が必要」が読み上げられない。臨床ツールとしては、
  - `#warn` に `role="alert"` / `aria-live="assertive"`、`#toast` に `aria-live="polite"` を付与。
  - コピーモーダルに dialog セマンティクス＋フォーカス管理を追加。
  を推奨。
- **[小] インライン `onclick` と `addEventListener` の混在**。`index.html` は `onclick="doCopy()"` 等を使い、`app.js` は `addEventListener` を使う。一貫性＋将来のCSP適用のため `addEventListener` に統一するとよい。
- **[小] ラベル関連付け**。検索入力や一部フィールドが視覚ラベルを `for`/`id` で関連付けていない。`label` を明示的に紐付けるとスクリーンリーダー体験が向上。
- **[小] オートコンプリートのキーボード操作**。`keydown` は Enter/Escape を処理するが、矢印キーでの候補移動が未配線（CSSには `.aci.on` があるのに使われていない）。仕上げの磨き込みとして。
- **[小] 「クリア」に確認がない**。入力を全消去する操作に確認・undo が無いため、誤タップで入力が飛ぶ。記録系ツールとしては軽い確認かトースト付き undo があると安心。
- **[検討] ダークモード**。design token 化されているので、`prefers-color-scheme` で token を差し替えるだけで比較的安価に追加できる（臨床ツールとして必須ではないが、夜勤帯の眩しさ対策として相性が良い）。

---

## 5. エージェント構成（`CLAUDE.md` + `.claude/agents/`）

`CLAUDE.md` の "AI Orchestration and Auto Routing" と、`deep-reasoner.md` / `verifier.md` を読んだ上での評価。

### 良い点

- **役割分担が明快で、責務が重ならない**。
  - Main（Sonnet）: 要求理解・分類・計画・通常実装・委任判断・統合・最終判断。
  - Explore: 広範囲の読み取り調査に限定し、メインコンテキストを調査ログで汚さない。**安全/データ/Critical の最終判断はしない**（Main が `CLAUDE.md` と照合）。
  - deep-reasoner（Opus）: アーキ判断・難バグ・DB/認可・セキュリティ・データ整合性など「深い推論」専用。**通常実装はしない**。
  - verifier（Sonnet）: 実装後の独立検証。「**Main の実装が正しいと仮定しない**」と明記。
  - Codex: 別モデル系統のピアとして Review / Adversarial Review / Rescue に用途分け。「単なる形式レビュアーとして使わない」。
- **タスク分類（Small/Normal/Hard/Critical）＋エスカレーション/デエスカレーション規則**が実務的。特に「**医療安全・不変条件・データ安全に触れる変更は、ファイル数に関係なく上位分類**」という規則で、安全最優先が routing に直接エンコードされている。
- **コスト意識**。「重い/外部モデルを形式的に呼ばない」「Codex Review を全タスクで機械実行しない」「verifier/Codex の指摘を盲目的に反映せず Main が妥当性判断」。多エージェント構成にありがちな「レビューのラバースタンプ化」を明確に禁じている。
- **Critical のガバナンス**。破壊的変更はユーザ確認前に実行せず、推奨方針・理由・リスク・代替案・ロールバック・検証方法を提示。governance として真っ当。
- **独立性の担保**。反証が有益な場合、deep-reasoner と Codex Adversarial を「**一方の結論を先に他方へ与えない**」で独立に走らせ、Main が統合。anchoring を避ける洗練された設計。異なるモデル系統を対抗レビューに使うのは、モデル固有の盲点を潰す実質的な強み。
- **安全原則の single source of truth**。4原則・不変条件の全文は `CLAUDE.md` に集約し、サブエージェント定義は重複記載せず参照する、という DRY がガバナンス文書にも効いている。

### 改善提案

- **[中] 遵守の機械的担保がない**。routing/gate は「LLM オーケストレータへの散文的指示」であり、ツールで強制されていない。例えば「Critical 変更が本当に deep-reasoner＋Codex＋ユーザ確認を通ったか」を機械的に保証する仕組みはなく、Completion Report は自己申告。
  - 対策案: PRテンプレート or 軽量チェックリスト（分類・使用エージェント・ゲート結果を必須記録）を用意し、`implementation-progress.md` が手動でやっている「Phase ごとの PASS/Critical/High/Medium 記録」をテンプレ化する。これで遵守が監査可能になる。
- **[小] モデル名のハードコード**。`Sonnet`/`Opus`/`Fable` を直書きしているため、モデル世代が変わると記述がドリフトする。「主モデル/推論特化/対抗レビュー」のような役割抽象で書き、対応モデルを別表にするとメンテしやすい。
- **[小] Explore の要約ロス**。Explore は read-only かつ最終判断をしないので健全だが、「安全関連の細部が Main に届く前に要約で落ちる」リスクは構造的に残る。Main が `CLAUDE.md` と再照合する運用で許容されているが、意識しておくとよい。
- **[小] ドキュメント冒頭に1枚の決定表**。routing 文書はやや長いので、先頭に「分類→標準フロー→使うエージェント」の1ページ決定表（既に部分的にある）を置くと、遵守が速くなる。

---

## 6. テスト

### 良い点

- **中核の純粋ロジックの単体カバレッジが厚い**。
  - `copy-renderer.test.js`: プレースホルダ空欄fallback、`omitIfAllBlank`、segments、`splitLinesFrom`、`showIf`（条件値との連携）、構造化結果（`unresolvedRefs`）、そして前述の読みやすさ回帰テスト。
  - `safety-rules.test.js`: `blankPolicy=block`、`requiredWarning`→warn、`hardRange`→block/`warningRange`→warn、非数値→block、非表示 field は判定対象外。
  - `condition-engine.test.js`: scalar/number/array/nested 各op、`is_blank`（`0` は空でない）。
  - `generic-values.test.js`: number `0` は実値、空欄→null、全角正規化、multi_select 配列化、ラベル整形。
  - `admin-simple.test.js`（`simple-template-model`）: 自動コンパイル、ID隠蔽（`sec_/fld_`）、ラベル変更でも option value 保持、空欄 field を省く自動コピー。
- **API統合テストが網羅的**（`server/smoke_test.py`, 1522行）。全読み取りAPIのステータス、**DB整合トリガ**、脳梗塞の出力互換スナップショット、migration 正当性、そして書き込み系のセキュリティ/検証マトリクス（ガード無し403 / 不正id 400 / サイズ超過413 / 未知キー400 / stroke-v1初期値入り400 / 重複409）、版作成・公開（stale draft 409）・rollback・削除/復元（多重操作の409、削除中編集の409、削除中GETの404、versions/logsは200）・未参照警告（generic-v1/v2）・generic-v2 の visibleIf/showIf ラウンドトリップ。

### 改善提案

- **[中] 安全critical な数分岐の明示カバレッジを要確認**。読解の範囲では、以下2つの「最も安全に効く分岐」の**明示的テストが `smoke_test` 内で確認しきれなかった**（見落としの可能性はあるが、無ければ追加を強く推奨）。
  - `detect_visible_condition_cycles` による**循環 visibleIf の作成拒否（→400）**。
  - **高リスク変更の確認ゲート**（`confirm_high_risk` 無しで high-risk 変更を公開/rollback → 409、`confirm_high_risk: true` で成功）。
  ここは「壊してはいけない不変条件」に直結するので、テストで固定しておく価値が高い。
- **[小] Python純粋バリデータの高速単体テスト**。`template_schema.py` の検証関数群は現状ほぼエンドツーエンド（smoke_test）でしか検証されていない。`detect_high_risk_changes` / `detect_visible_condition_cycles` / `validate_condition` の境界ケースを、pytest 等で高速・独立に回せると、フィードバックが速くなりエッジケースも押さえやすい。
- **[小] フロントのDOM/統合テストが無い**。`updateGenericConditions` の固定点反復、非表示 field の値クリア、コピーモーダルの block/confirm 配線は、現状「手動確認」でしか担保されていない。**「非表示 field の値が copy や未入力警告に漏れない」という安全不変条件**を jsdom ベースのテストで固定できると、UI改修時の回帰を防げる。

---

## 7. ドキュメント

### 良い点（ここは特筆に値する）

- **試作としては過剰なほど充実**。README（アーキ/API/データフロー/セットアップ/運用前TODO）、`CLAUDE.md`（ガバナンス＋安全＋オーケストレーション）、`handoff.md`（再開時に最初に読むサマリ）、`baseline.md`（回帰比較用に**コミットを固定**）、`implementation-progress.md`（617行、Phaseごとの PASS/FAIL ゲートと Critical/High/Medium 件数）、`legacy-cleanup-inventory.md`（tech-debt 台帳＋**Removal Gate**）、`variable-template-migration-design.md`（752行の設計書）。
- 多くの本番システムよりドキュメント・プロセス規律が整っている。特に「baseline を固定 → Phase ごとにゲート → tech-debt は依存を明示してから段階削除」という流れは、`CLAUDE.md` の分類/ゲート思想と一貫している。

### 改善提案

- **[小] 記述の重複によるドリフト源**。generic-v1/v2/text-v1 の仕様が README・handoff・baseline・migration設計 の複数箇所で再掲されている。仕様が変わったとき、更新漏れで矛盾が生じやすい。1つを正典（例: `variable-template-migration-design.md` または `baseline.md`）と定め、他はそこへリンクする方針にすると、`CLAUDE.md` が安全原則でやっている single source of truth をスキーマ仕様にも広げられる。

---

## 8. セキュリティ（ローカル試作という前提で）

### 良い点

- リクエストボディ上限 1MB（`MAX_CONTENT_LENGTH`）、局所書き込みガード（`X-Nasukeru-Local` ヘッダ＋`localhost/127.0.0.1/::1` の Origin/Referer）、外部bind拒否（`NASUKERU_ALLOW_EXTERNAL` 無しの非ローカルbindを `SystemExit`）、DEBUG のフラグゲート、静的配信のホワイトリスト（`send_from_directory` はパストラバーサル安全）、テンプレート由来文字列の `textContent` 描画、`PRAGMA foreign_keys = ON`。
- README が「これは認証ではなく、ローカル起動中のブラウザ経由攻撃を軽く防ぐためのもの」と**正直に位置づけ**、運用前TODO（認証・CSRF・保護DB配置・WSGI・バックアップ・承認方針・監査閲覧権限）を明記。この誠実さが良い。

### 改善提案

- **[小] 書き込みガードの適用範囲**。`before_request` は `path.startswith("/api/templates")` かつ POST のみをガードする。現状の全書き込みは `/api/templates` 配下なので問題ないが、将来 `/api/` 配下に別の書き込みエンドポイントを足すと**素通り**する。`/api/` 全体の書き込みメソッドをガードする、あるいはデコレータ化して付け忘れを防ぐと堅い。
- 局所ガードが Origin/Referer に依存する点は、非ブラウザクライアントから偽装可能だが、「認証ではなくローカルブラウザ向けの軽いCSRF対策」というスコープどおりなので妥当。

---

## 9. 優先度つき推奨アクション

「読解ベースで見えた範囲」での優先順位。上ほど効果対コストが高い。

| # | 提案 | 分類 | 効果 | コスト感 |
| --- | --- | --- | --- | --- |
| 1 | `isBlank` を単一 source of truth に集約（4モジュールの重複解消） | 保守性/安全 | 空欄判定のズレによる無言欠落・条件誤評価の芽を摘む | 小 |
| 2 | `package.json` ＋ GitHub Actions で「init_db+smoke_test」「node test」を自動化 | 運用/CI | 掲げているスナップショット整合性CIを実体化、DoD自動化 | 小〜中 |
| 3 | 循環visibleIf拒否 & 高リスク変更confirmゲートの明示テスト追加 | テスト/安全 | 不変条件の最重要分岐を固定 | 小 |
| 4 | コピーモーダルの a11y（dialog/focus/aria-live）を管理画面水準に揃える | UX/a11y | スクリーンリーダー利用者に安全警告が届く | 小〜中 |
| 5 | 「入力済みだが未参照 field」のランタイム扱いを設計判断として明記（必要なら入力画面に控えめ表示） | 安全/設計 | 原則④の最も厳密な読みへの整合、意図の可視化 | 小（明記のみ）〜中（UI追加） |
| 6 | スキーマ仕様の正典を1つに定め、他ドキュメントはリンク化 | ドキュメント | 仕様ドリフト防止 | 小 |
| 7 | エージェント運用の遵守を PR チェックリスト等で監査可能にする | プロセス | routing/gate の実効性担保 | 小 |
| 8 | Phase 9 の Removal Gate 到達後、stroke-v1 ランタイム経路を削除 | 保守性 | デッドコード削減 | 中 |

---

## 10. 補足: 細かな指摘（Nits）

- `js/validation.js` と `index.html`・`copy-format.js` の末尾に Windows 改行（`\r`）が混在。`.gitattributes` / エディタ設定で改行コードを統一しておくと差分ノイズが減る。
- `simple-template-model.js: editorModelToSchema` の blankPolicy 分岐に無操作行（`next.blankPolicy = next.blankPolicy;`）があり、「allow を明示保存 vs 削除」も意味的には等価（サーバは未指定を allow 扱い）。整理してよい。
- `randomId` は `Math.random()` 由来の32bit。テンプレ内の少数 field では衝突確率は無視できるうえ、衝突時はスキーマ検証が重複IDを400で弾く（＝破壊ではなく保存エラー）ので実害は小さいが、気になるなら衝突時リトライか連番ベースIDに。
- `get_admin_templates` は `current_version_number` を二重に付与している（`template_summary_from_row` 内でも付く）。軽微な冗長。
- README の JSテスト実行例が特定PCの node 絶対パス依存。`package.json` 導入で `npm test` に置き換えると共有しやすい（提案2と一体）。

---

### 総括

医療安全という難しいテーマに対して、「原則を掲げるだけ」で終わらせず、**DBトリガ・スキーマ検証・fail-closed・スナップショット互換・自動コピー生成**という具体的な機構に落とし込めているのが、このプロジェクトの一番の価値。加えて、開発プロセスとドキュメント、そしてAIエージェントのオーケストレーション設計まで含めて、「安全critical な小さなソフトを、規律を持って育てる」という姿勢が全体に一貫している。

次の一歩としては、その規律を **CI/自動テストとして機械化**し（提案1〜3）、**アクセシビリティを臨床水準に底上げ**し（提案4）、**原則④の最後の1点を設計判断として明示**する（提案5）——このあたりが、試作から「安心して人に渡せる」段階への橋渡しになる。
