# Existing Feng frame ranking — NO_EXISTING_FENG_ENDPOINT

The formal atlas audit scanned all **88 slots / 74 populated frames**. An
independent reviewer then compared every visible pose to frozen KB2 and to
formal Feng Idle B. The shortlist below contains the *relative nearest*
three, not three approved F0s. All are untouched atlas cells, hard-edge RGBA,
uncropped, and sole-aligned at y=203. Registration x=96 denotes the cell
anchor; body-band bbox centers also include protruding limbs and must not be
mistaken for a global shift. Head guides are manual approximations ±3px,
especially where a hand or collar meets the face.

| Rank | Source | Approx head bbox / center | Body-band bbox / center | Arm and legs | KB2→candidate | Candidate→B |
| --- | --- | --- | --- | --- | --- | --- |
| F0-A | review row 8 frame 4 | `(64,4,114,59)` / `(89,31.5)` | `(39,70,145,204)` / x=92 | Hand bent across chest at waist level; other fist low; wide planted feet | Head guide shrinks about 6×13px, center rises ~6px; finished shoulders/suit and wide stance arrive together | Mainly hand rise, but not a neutral pose; single-frame gesture still visible |
| F0-B | running-right row 1 frame 6 | `(72,5,124,61)` / `(98,33)` | `(54,70,139,204)` / x=96.5 | Both fists low; rightward lean/turn with crossing step | Hands/feet are closer to KB2, but head center shifts ~10px right, face turns, and directional gait appears | Must straighten head/torso, widen apparent body/feet and raise hand; not just pose settling |
| F0-C | waving row 3 frame 0 | `(64,5,114,60)` / `(89,32.5)` | `(38,70,150,204)` / x=94 | Hand raised by cheek/chest; wide feet | Morph, lifted arm, bright suit and wide stance jump together | Hand redirects to chin; still a gesture-to-gesture jump |

For reference, KB2 head guide is 56×68 centered `(88,38)`, body-band width
93; B head guide is approximately 49×54 centered `(88.5,31)`, body-band
width104. F0-A is visibly closest to Feng Idle B, while F0-B comes closest to
KB2's low-arm/narrow-leg side. Neither satisfies **both** links. Numeric
baseline and bbox PASS do not make the identity/pose changes continuous.

Other Atlas families were inspected in the all-slot sheet: Idle/Waiting/
Failed/Jumping/task-Running and most look cells retain B's finger at chin;
review 2–3 keep the hand higher than review 4; mirrored drag frames inherit
the active side-step; waving 1–3 raise the hand farther. No frame supplies a
front-facing finished Feng with genuinely low arms and a stance close to KB2.

Independent verdict: **NO_EXISTING_FENG_ENDPOINT**. Thus the selected-candidate
static chain, an optional morphology bridge, App integration and full-frame
fill are **not run**. F0 requires genuine `MANUAL_PIXEL_ART` (or another
native, source-preserving artwork proposal) that must be approved before
testing KB2→F0→B. Formal Feng atlas and Idle B remain unchanged. Do not
present F0-A as an approved endpoint merely because it ranks first.

Evidence: `assets/rework/v0.1.0/transition-keyframes/feng-f0/atlas-candidate-ranking/`
contains the native and nearest-3× focused Contact Sheet, source-cell hashes,
landmark guides, and hash-bound independent visual verdict; the complete
88-slot sheet is in sibling `atlas-neutral-audit/`.
