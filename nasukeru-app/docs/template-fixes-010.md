# Built-in Template Fixes 010

## Purpose

Migration 010 corrects visible defects in the current built-in nursing templates without overwriting historical versions.

## Stroke template corrections

- MCA `左口角下垂` is replaced by `口角下垂` with `なし / 右 / 左 / 両側`.
- MCA `左半身感覚鈍麻` is replaced by `半身感覚鈍麻` with side selection.
- PCA `左同名半盲` is replaced by `同名半盲` with side selection.
- PCA `左半身感覚鈍麻` is replaced by side-selectable `半身感覚鈍麻`.
- Brainstem `右方視時の水平性眼振` is replaced by `水平性眼振` with `なし / 右方視時 / 左方視時 / 両方向`.

The copy format follows the corrected labels and field references.

## Neuro common template corrections

`neuro_common` is upgraded to `generic-v2` so existing Condition Engine behavior can be used.

Conditional detail inputs:

- `心電図リズム = その他` -> `その他の心電図リズム`
- `酸素使用 = O2使用` -> `酸素流量`
- `バレー徴候 = 陽性` -> side / angle / detail
- `ミンガッチーニ徴候 = 陽性` -> side / detail / note
- `食事・飲水 contains とろみ水` -> `とろみの程度: 薄め / 中程度 / 濃いめ`
- `食事・飲水 contains 嚥下食` -> `嚥下食レベル: 1 / 2 / 3 / 4 / 5`
- `降圧薬 contains ニカルジピン` -> `ニカルジピン速度`
- `降圧薬 contains その他` -> `その他の降圧薬` free text

The corrected copy format uses `segments`, `omitIfAllBlank`, and `showIf` so optional or hidden details do not produce unnatural `__` text.

## Versioning

Migration 010 creates new published template versions and keeps previous versions as retired history. Audit logs are appended with action `migrate`. Existing version rows are not overwritten.

## Apply

From `nasukeru-app`:

```powershell
py -3.10 server\prepare_db.py
```

or:

```bash
python server/prepare_db.py
```

`prepare_db.py` runs the existing DB preparation first and then applies migration 010. The migration is idempotent.

## Test

```powershell
py -3.10 server\template_fixes_010_test.py
```

The test uses a temporary SQLite database and verifies field replacement, conditions, copy references, published-version integrity, and idempotency.
