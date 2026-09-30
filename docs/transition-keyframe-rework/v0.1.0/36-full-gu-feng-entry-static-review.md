# Full Gu→Feng Morph and Entry static review

Verdict: **VISUAL_QA_FAIL**. The approved A→F0-v2 Morph remains statically continuous; the four-frame Feng Entry is **not** approved. F0-v2→E1, E1→E2 and E2→E3 pass the current static art gate. E3→the frozen formal Feng Idle B fails visual review. `FENG_ENTRY_ART_APPROVED` and `GU_TO_FENG_STATIC_CHAIN_APPROVED` are withheld. No App integration or runtime playback was attempted.

The 13 source-bound poses are `A → K1 → K2 → K3 → KB1 → KB2 → KF1 → KF2 → F0-v2 → E1 → E2 → E3 → Idle B`. The Contact Sheet and all 12 adjacent-frame overlays are in `assets/rework/v0.1.0/transition-keyframes/feng-f0/v2/feng-entry/full-chain-qa/`. `chain-report.json` records source SHA256, geometry, prior gate provenance and the blocking pair. All 13 are native 192×208 RGBA, have y=203 sole baseline, and do not touch a cell edge. Head guides are approximate (±3 px); their apparent stability is **not** a substitute for visual identity review.

| Adjacent poses | Head size Δ (w,h) | Head center Δ (x,y) | Body-band width Δ | Baseline Δ | Static visual gate |
| --- | ---: | ---: | ---: | ---: | --- |
| A→K1 | 0, 0 | 0, 0 | −1 | 0 | PASS — approved frozen keyframes |
| K1→K2 | 0, 0 | 0, 0 | +7 | 0 | PASS — approved frozen keyframes |
| K2→K3 | 0, 0 | 0, 0 | +10 | 0 | PASS — approved frozen keyframes |
| K3→KB1 | −6, −6 | 0, −3 | +12 | 0 | PASS — prior hash-bound review |
| KB1→KB2 | −6, −6 | 0, −3 | +12 | 0 | PASS — prior hash-bound review |
| KB2→KF1 | −2, −4 | 0, −2 | +2 | 0 | PASS — prior hash-bound review |
| KF1→KF2 | −2, −5 | 0, −2.5 | +5 | 0 | PASS — prior hash-bound review |
| KF2→F0-v2 | −2, −4 | 0, −2 | +1 | 0 | PASS — F0-v2 Morph gate |
| F0-v2→E1 | 0, 0 | 0, 0 | +5 | 0 | PASS — Entry local gate |
| E1→E2 | 0, 0 | 0, 0 | −5 | 0 | PASS — Entry local gate |
| E2→E3 | 0, 0 | 0, 0 | 0 | 0 | PASS — Entry local gate |
| E3→Idle B | −1, −1 | +0.5, −0.5 | +3 | 0 | **FAIL** — semantic/pose jump |

The Entry hand trajectory is readable through E3: left hand starts low at F0-v2, rises to its early crossing in E1, shifts inward/up in E2, and approaches the face in E3; the right hand tightens into a fist. The left sole moves from center 82.5 through 74.5 to 69 while the right sole moves from 109 to 122.5. The frozen Idle B is at left/right sole centers 65.5/127.5, so the baseline and gross foot position nearly match. Nevertheless, E3→B simultaneously changes the eyes/hair identity cues, fingertip-to-lip hand position and forearm angle, jacket/sleeve construction, and trouser volume. At y=150 opaque left/right trouser widths jump from **13/13 to 21/25** pixels; at y=160 from **14/19 to 19/22**. This is not a geometry registration failure and should not be waived because head bounding boxes match.

This review incorporates the earlier approved or hash-bound static gates; it does **not** claim independent human approval of E1/E2/E3 or real-window playback. The source files, frozen atlas, player, Scheduler and Hooks were not modified. The failed last cut remains explicit in the Contact Sheet. The next art decision must address the combined pose/clothing/identity gap within the prescribed Entry duration; no further frames were fabricated or hidden in this stage.
