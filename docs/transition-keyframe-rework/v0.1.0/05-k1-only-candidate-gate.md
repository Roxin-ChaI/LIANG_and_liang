# K1-only candidate gate — FAIL

Only K1 was attempted, twice. The strict specification commit preceded both
generation calls. A/B, existing K2/K3, standard atlases, player, scheduler and
Hooks remain unchanged. No App integration, intermediate animation frames or Tag.

## Actual observations

Both transparent edit outputs are1254×1254, not the requested unscaled1024×1024
edit target. The hard-alpha character hulls are82×242 and81×241, versus A's
68×200 whole foreground. Neither native figure can fit the192×208 cell without
forbidden scaling or clipping. These whole-foreground sizes are NOT head sizes.

Independent head estimates are83×96 and82×95, uncertainty ±4 source pixels,
versus frozen A's68×80. They are native source measurements, NOT resized
runtime measurements. Expected edit-target head center is(504,452); observed
approximate centers are(617.5,554) and(617,554.5). Hard-alpha sole747 differs
from unscaled reference611 by136 source pixels. No coordinate remapping was
used to conceal these failures.

The independent reviewer finds both recognizable as Gu, without premature
Feng/head shrinking. Exact face preservation, neck/shoulder measurements and
canonical body-band alignment remain NOT_VERIFIED, not PASS. Attempt2 also
introduces bright blue shoulder strokes; their origin is NOT_VERIFIED.

## Evidence and reproducibility

Package: `assets/rework/v0.1.0/transition-keyframes/k1-only/`.

- `independent-review.json`: read-only native anatomy/identity review.
- `landmark-report.json`: fixed-target versus native source measurements,
  explicit uncertainty and unverified shoulder/body anatomy.
- `provenance.json`, both prompts and exact padded A reference.
- `attempt-{1,2}/raw-native.png`: complete unchanged rejected K1 PNGs.
- `attempt-{1,2}/qa/contact-sheet.png`: whole native source versus exact A,
  no resampling.
- `attempt-{1,2}/qa/native-detail-contact-sheet.png`: compact native-scale
  inspection crops only, not playable K1 cells; complete source remains retained.
- `attempt-{1,2}/qa/rejected-native-layout-overlay.png`: cyan unchanged edit
  target A, magenta rejected native source; white exact, yellow color difference.
  Alpha threshold128 is used ONLY for this diagnostic overlay, not source repair.
- `attempt-{1,2}/qa/validation.json`: layout rejection and native alpha evidence.

No normalized `K1.png` is emitted. The failed generated PNGs are retained rather
than silently fitting them into a plausible-looking cell. This prevents a new
head/baseline/identity claim from being manufactured by scaling or clipping.
`prepare_transition_k1_candidate.py` reproduces extraction rejection and QA;
tests exercise both real rejected sources and synthetic negative fixtures.

## Conditional chain gate

**A→K1: FAIL. K1→K2: NOT_EXECUTED_A_K1_NOT_PASS. K1_APPROVED: false.**

Commit3 is intentionally skipped because its prerequisite failed. Historical
K1→K2 shoulder concerns remain unresolved; this is not a fresh K2 audit and
does not claim K2 is cleared or newly verified. No further generation is run.

The hatch-pet/imagegen workflow provided isolated single-K1 generation and
independent final visual review; deterministic processing is restricted to
reference padding, rejected-source diagnostics and QA-only overlays/crops.
No procedural pose reconstruction, warping or whole-character fit is performed.

Regression before the candidate-evidence commit: Python362 passed,1 historical
xfail,12 subtests passed; Node216 passed,0 failed. The K1-only gate/preparation
suite has27 tests. Successful code tests do not change the art FAIL verdict.
`git diff --check` and cached diff checks are required before both commits.
Protected-path comparison against89b7ade confirms no standard atlases, approved
endpoints, existing K2/K3, player, renderer, scheduler or Hook definition changed.

For another attempt, use an art/edit workflow that can preserve A's native
pixel registration and anatomy, or request manual K1 artwork against the strict
reference. This report does not grant that next step or relax the constraints.
