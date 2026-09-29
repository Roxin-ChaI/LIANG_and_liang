# B endpoint compatibility audit — B_ENDPOINT_REWORK_REQUIRED

This gate precedes KB3. The previously approved B remains a valid static Feng
Idle endpoint, but that approval does not establish that it works as the last
frame of the current Gu-to-Feng transformation. This audit generates no new
transition art and does not alter A/K1/K2/K3/KB1/KB2/B.

## Source integrity and coordinates — confirmed

- B is 192×208 RGBA and byte-identical in raw RGBA to formal Feng v2 atlas
  Idle row 0, frame 0 and to the approved Feng idle strip frame 0. B and the
  approved reverse C endpoint are the same PNG. Formal atlas SHA256 is
  `d697e573268b66cb0f6a062480ec87c8c11712ca34b57f8c2fc0a97ed6e2164a`.
- B's alpha bbox is `(44,4,148,204)`, leaving at least four transparent
  pixels on every edge. Baseline is y=203; body-band center is x=96. Alpha is
  binary, hidden transparent RGB is absent, and no crop/cell-edge clipping was
  found. KB2 shares the y=203 baseline. Consequently B's smaller head is part
  of the approved Feng design, **not** an extraction, scaling, or registration
  mistake in this endpoint file.
- Guide estimates: A head 68×80, center `(88,44)` and body-band width 53;
  KB2 head 56×68, center `(88,38)` and width 93; B head about 49×54,
  center `(88.5,31)` and width 104. The B skull guide has ±3 px uncertainty:
  the chin is partially obscured by a hand. These guides are not anatomical
  segmentations. The large design difference is also visible at native size.

## Artistic compatibility — independent static review

The native and nearest-neighbor contact sheets show that A through KB2 are
still fundamentally Gu-like: large rounded head, narrow parallel stance and
hands near the sides. B is a complete Feng Idle pose: finger to chin on the
screen-left, fist at the other side, legs spread, upright torso and brighter,
fitted blue suit with different lapel/waist structure. These changes occur
together at the current outgoing KB2→B pair. B would hand off *exactly* to
Feng Idle; nevertheless this chain's final move looks like switching to a
different posed character rather than the same person progressively gaining
strength. At most two additional bridge frames cannot be presumed to resolve
the simultaneous head, arm, stance, and clothing discontinuity.

This is a **visual judgment**, not a mathematical assertion that every
possible future hand-drawn animation is impossible. In particular, static
evidence cannot prove that arbitrarily many redesigned poses would still
look wrong. It does show that the currently frozen B and bounded KB3/KB4 plan
are not a sound endpoint path. A new endpoint/animation proposal would also
need to address how its last frame transitions into the existing formal Feng
Idle without a second jump. Previously approving B as an Idle canonical pose
does not approve it as this transition's final frame.

## Gate and next action

Independent verdict: **B_ENDPOINT_REWORK_REQUIRED**. The technical gate and
fresh pixel-hash-bound independent review both agree. `KB3Allowed=false`; no
KB3, KB4, replacement B, full 10-frame animation, App integration or Tag was
produced. The user should review a revised endpoint/idle handoff concept
before further art work. Do not try to cure this by endlessly adding bridge
frames, scaling the whole person, hiding a discontinuity frame, or changing
the playback speed.

Evidence is in
`assets/rework/v0.1.0/transition-keyframes/k3-b-bridge/b-endpoint-compatibility/`:
technical report, independent review, final verdict, native and nearest-3×
contact. The earlier seven-pose contact remains in the sibling `full-chain-qa`
directory. The automated test verifies source identity, no crop, no automatic
art approval, independent review freshness, and refusal to overwrite audit
evidence; it does not claim automated artistic approval.
