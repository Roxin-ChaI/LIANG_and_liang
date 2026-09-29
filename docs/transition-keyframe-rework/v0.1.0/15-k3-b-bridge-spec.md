# K3→B bridge specification (no new pose in this commit)

The current user explicitly approved K1/K2/K3 and A→K1→K2→K3.
All five input PNGs A/K1/K2/K3/B are pinned by SHA256. Historical reviews are
retained unchanged. B remains canonical Feng; no App, player, Scheduler,
Hook, standard atlas, Tag or currently running version changes.

## Per-link contract

Every proposed bridge link has head width/height change ≤6px, head center
|dx|≤3px / |dy|≤4px, body70:208 alpha-hull growth 0–15px, sole y203,
registration x96. The suggested budgets are enforced conservatively, not
silently widened to make B pass. Head/face/arm/cloth continuity also requires
independent visual review. Registration is a construction anchor, not the
asymmetric alpha-hull center. Body hull is not skeletal shoulder width.

KB1: gradual reinforcement from K3, small local head change, upper body
expansion and beginning arm movement, not a complete Feng pose. KB2 is
conditional on a fresh static-pass KB1 and KB1→B failure. It uses the same
budgets and a separately gated outgoing link to frozen B.

Local nearest-neighbor head/identity-part resizing is authorized in this
bridge task; whole-person scaling, image regeneration, interpolation,
antialiasing, face replacement and effects hiding geometry are prohibited.
Every local pixel donor/transform must be recorded, and lower-foot registration
must remain unchanged. Exact part masks and anatomy still need visual QA.

## Capacity warning: one or two bridges is not presumed sufficient

K3 head guide68×80 / center(88,44); B approx49×54 / (88.5,31).
Body width69→104 (+35). B's hand-occluded chin guide has ±3px annotation
uncertainty; the K3 guide includes lower neck/collar. These are historical
reference guides, **not exact skull segmentation**.

Nominal changes are −19/−26 head pixels and −13 center-y pixels. One bridge
has two links (height capacity12, center-y8, body30). Two bridges have three
links (height18, center-y12, body45). Thus even two fail the nominal height
and center-y capacity before pose/identity are considered. Head height alone
requires five links / four bridges at the6px budget. This is a nominal lower
bound, not permission to generate KB3/KB4 or proof four will be artistically
sufficient. Even the favorable height gap23 at ±3px exceeds three-link18.

We will only derive the authorized KB1 and, if its incoming link passes and
KB1→B still fails, KB2. Failure to reach B preserves FAIL; additional artwork
requires a new scope decision. Do not modify the already approved chain to
absorb the endpoint gap. No full-animation fill is eligible while any link
fails; bbox PASS alone never authorizes art or runtime integration.

## Reproducibility

`python -m tools.transition_bridge_spec` writes only `spec/specification.json`
under `assets/rework/v0.1.0/transition-keyframes/k3-b-bridge/`. It verifies all
frozen PNGs and the original endpoint approval before calculating budgets.
Tests cover pinned provenance, exact thresholds, missing capacity, approximate
guides, native-canvas rejection and refusal to overwrite. No new PNG is emitted.
