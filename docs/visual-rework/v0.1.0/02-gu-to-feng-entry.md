# V-04 entry rework — ASSET_REWORK_REQUIRED (not fixed)

The separate Rework1 candidate was run from actual Idle, held Running and Hover. All10 Gu→Feng frames were captured in order with full last-frame dwell. [Idle real-window sheet](entry/runtime/idle-gu_to_feng-sheet.png), [Running sheet](entry/runtime/running-gu_to_feng-sheet.png), [recording](entry/runtime/running-gu_to_feng-window-recording.gif), [timeline](entry/runtime/transition-timeline.json).

`tools/diagnose_transition_handoff.py` evaluates rigid integer translation only. It measures three dark-character horizontal bands (head, shoulders, shoes), excluding cyan aura. [Rigid candidate comparison](entry/gu_to_feng-rigid-candidates.png) and [measurements](entry/gu_to_feng-feasibility.json) are **diagnostic media**, not replacement runtime frames. The normal-area diagnostic crop does not authorize cropping the actual oversized effect.

| Entry | Best integer dx | Residual head / shoulders / shoes | Geometry result |
| --- | ---: | --- | --- |
| Idle frame0 | −8 px | −1.5 / +1.5 / +0.5 px | Near-aligned; pose/facial drawing still differs |
| corrected Running frame0 | −3 px | −4.5 / +0.5 / 0 px | Cannot register all parts within2 px |

Running's current pose has head top y=12, whereas the entry frame has y=4. Both have grounded shoes; a vertical translation that repairs the head would move the shoes off the canonical baseline. Running is itself animated, so a hard-coded offset for its frame0 would not establish continuity for every possible entry frame.

Visual inspection of the existing frame0 and diagnostic translation confirms a different face/torso posture. Selecting frame1 instead retains that alternate drawing plus added energy; later frames already progress toward Feng. Hiding or skipping the beginning would neither satisfy the10-frame contract nor solve the source mismatch. A shared sequence-wide horizontal offset would also displace the already aligned Feng end. Per-state translation cannot invent the missing pose transition.

Therefore no runtime offset/endpoint substitution is applied or falsely labeled PASS. **V-04 remains P1, ASSET_REWORK_REQUIRED.** Needed authorization is a pose-matched entrance asset/approved motion bridge that starts from the actual Idle/Running pose while preserving all10 transformation stages. Frozen images and Hook behavior remain unchanged. This is a verified feasibility/blocker commit, not a successful animation repair.

Relevant tests verify that geometry cannot automatically approve pose continuity and that incompatible body-part offsets remain a failure; existing transition-audit tests verify both direction counts and pixel-difference detection. No release candidate is allowed while this P1 remains.
