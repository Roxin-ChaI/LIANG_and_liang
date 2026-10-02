# Restore original side-shuffle and extend to eight — failed trial

2026-10-02: user rejected the low-motion native pixel derivative and selected
the earlier four-pose source shown in their screenshot. This is a candidate-line
rollback, not a Git reset or deletion. No runtime was changed.

Selected source: `../gu-drag-side-shuffle-keyposes-2026-10-01/source-preview.png`.
The native-pixel four/eight-frame line is no longer the active motion baseline.
Its history remains intact. Selection does not automatically waive source alpha,
native-size or exact-Idle appearance constraints for future production use.

The imagegen skill / built-in image tool produced four intermediate poses from
the selected source. `prompt.txt` records the full prompt. A single targeted
correction (`correction-prompt.txt`) attempted to fix the wrong support foot.
Both generated PNGs are retained without alpha or color edits. No CLI was used.

**Result: VISUAL_QA_FAIL_STOPPED_FOR_HUMAN_REVIEW.** Both attempts lift the
screen-right foot in intermediate 2 where it should support and screen-left
should lift. Attempt 2 also changed other regions despite the targeted prompt;
it is retained as rejection evidence, not silently substituted.

`qa/eight-frame-trial.gif` assembles attempt 1 with untouched original keys:
O1,N1,O2,N2,O3,N3,O4,N4. The failing intermediate is frame 4 and is labeled.
It is not a finished animation. This report does not claim improved fluidity.

- Eight frames, alternating 120/130 ms, 1 s infinite loop.
- Slow GIF: 250 ms each, 2 s loop. No omitted frames or accelerated defects.
- Original source RGBA crops in slots 1,3,5,7 are byte-identical.
- QA centers each head band with integer horizontal offsets and a constant
  vertical offset, then uses a common 0.5 nearest-neighbor display scale.
- Original-position GIF is provided separately. Alignment is not a runtime fix.
- PNG alpha preserved. GIF gray background and palette conversion are preview-only.
- `qa/contact-sheet.png` and `qa/validation.json` show frames and provenance.

No third generation attempt, final runtime strip, leftward version, app/atlas
change or deletion. Next action requires human direction on fixing the failed
leg articulation, not approval inferred from an eight-frame count.
