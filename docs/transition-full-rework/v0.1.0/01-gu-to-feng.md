# Full transition rework — Gu→Feng stage

The user approved exact A/B/C/D Idle canonical endpoints. `approval.json` binds
that decision to the four PNG hashes; historical PENDING draft QA is retained
unchanged. This approval does not cover Running or intermediate artwork.

## Actual output and checks

Two independently preserved10-frame candidates were extracted from genuine
built-in image generation. First/last PNG files exactly match A/B, not just a
similar drawing. No standard atlas, player, Scheduler or Hook was modified.

1. First candidate: `assets/rework/v0.1.0/transition-full/gu-to-feng/`.
   It fails00→01 head-height continuity,08→09 identity/pose convergence, and an
   isolated pixel in02. Numerical body registration is not visual continuity.
2. Targeted redraw: `assets/rework/v0.1.0/transition-full/gu-to-feng-retry/`.
   It passes structure but fails independent final visual review:08→09 narrows
   abruptly from an overshooting stance and changes face relationships;00→01
   still lowers the hair7px and02→03 raises both hands abruptly.

Each has10 PNGs, a normal-size Contact Sheet, nine adjacent pixel overlays and
head/body-reference bbox/baseline comparisons. Those bands are not anatomical
masks. All transformation frames are candidates marked runtimeEligible=false.

The redraw initially returned a connection failure and no file. An identical
transport retry succeeded but did not resolve the visual root problems. Exact
prompts and three-call provenance are retained. No CLI or procedural character
synthesis was used. No further random prompt variations were attempted.

## Gate

**VISUAL_QA_FAIL.** The observed P1 endpoint snap remains. Do not package/install
these assets, mark the stage complete, or enter Running audit. Idle real-App
integration is **NOT_TESTED / BLOCKED_BY_ASSET_QA**, not an observed App failure.
Endpoint approval remains valid and is not revoked by rejected middle frames.

Targeted extraction/approval tests passed before this commit. Full regression is
recorded in the final stage summary; automated PASS cannot override visual FAIL.
