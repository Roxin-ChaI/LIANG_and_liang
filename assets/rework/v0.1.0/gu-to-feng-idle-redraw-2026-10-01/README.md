# Gu → Feng Idle-style redraw — 2026-10-01

Final review status: **VISUAL_QA_FAIL**. This is new artwork retained for review and further redraw, not an installed or runtime-ready animation. The packaging report's `ART_CANDIDATE_NOT_APPROVED` is an initial technical status, not a visual PASS.

The user's decision freezes the existing approved Feng → Gu eight-frame animation. Its runtime and original-source SHA256 records are in `docs/transition-redraw/v0.1.0/feng-to-gu-approved-2026-10-01.json`.

This forward draft contains **10 transition poses**, ordered across the top row, then across the bottom row. **Zero Idle cells are inserted or counted.** The normal Gu and Feng Idles remain outside the transition. Style and identity references are `assets/gu/idle.png`, `assets/feng/idle.png`, and the approved native A/B Idle copies. Previous E1/E2/E3 artwork is not an input.

The built-in `image_gen` tool produced three bounded attempts. Attempt 1 crowded the lower shoes and used generic large-headed proportions. Attempt 2 improved spacing and was selected for review. Attempt 3 attempted stronger proportion matching, but made the opening Gu face too stern; it was not selected. Exact submitted prompts are retained in `prompts/`.

Deliverables:

- `source-sheet.png`: selected attempt 2, original generated PNG, unchanged (1773×887 RGBA).
- `frames/gu_to_feng_01.png` … `gu_to_feng_10.png`: lossless grid crops with transparent padding to a common 355×444 review canvas. No scaling, recoloring, alpha hardening, pose reconstruction or Idle replacement is performed.
- `contact-sheet.png`: numbered review sheet, with the same source artwork over a dark QA background. It is not an animation texture.
- `review.json`: per-frame source crop, hash, alpha diagnostics and explicit unapproved status.
- `qa/transition-only-10-frames.gif`: exactly ten transition frames, 180 ms each, no Idle.
- `qa/idle-transition-idle-preview.gif`: the same ten transition frames with two separately labelled 900 ms canonical Idle holds outside the transition.
- `qa/idle-transition-idle-contact-sheet.png`: twelve review panels (two external Idle references plus ten transition poses).
- `qa/preview-review.json`: common-scale geometry and the failed visual gate.

Visible character bounds clear every crop edge. Source pixels remain byte-identical within each crop, but source alpha includes partial-coverage pixels. Therefore strict hard-edge alpha is **not yet satisfied**. The draft also still needs direct native-scale comparison with approved Idle identity and head/body proportions. Do not interpret the new readable limb drawings or the ten-cell count as proof of exact style consistency, animation continuity, or user approval.

The completed preview review confirms failure. All ten candidates use one nearest-neighbor QA scale of 200/371 with integer sole registration; none is individually resized to force a match. At that common scale T1 is 189 px tall versus approximately 200 px for canonical Gu, lowering its hairline by 11 px at entry. The generated face/hair and final suit/stance also differ visibly from the exact frozen Idle. No per-frame fitting, endpoint insertion, alpha hardening or playback acceleration was used to hide these defects. Morph anatomy is more coherent than the discarded E1/E2/E3 constructions, but that improvement does not satisfy the user's requirement of exact Idle-style consistency.

No runtime/player/Scheduler/Hook code, Gu/Feng atlas, previous approved frame or reverse animation is changed. No App integration or tag is created. Future acceptance must separately prove exact Idle-style identity, uncut anatomy, stable registration/baseline, hard edges and temporal continuity before replacing a runtime asset.

Reproduce the lossless review packaging into this initially empty output set with `.venv/bin/python tools/package_idle_style_redraw.py`. The tool refuses to overwrite existing review outputs.
