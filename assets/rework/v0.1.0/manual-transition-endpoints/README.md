# Four canonical boundaries — user approved for Idle only

The user has now approved A/B/C/D in the Transition Full Animation Rework
request. `approval.json` records that decision against the exact PNG hashes.
Status: **ENDPOINT_ART_APPROVED**, **Idle canonical only**. The original
`qa/validation.json` and independent review remain unchanged historical
pre-approval snapshots; their PENDING fields are not the current decision.

These are **boundary designs**, not a playable transition. No character was
redrawn: all four192×208 RGBA PNGs are exact, unscaled, untranslated extractions
of the corresponding formal Codex v2 atlas Idle row0/frame0. At a canonical Idle
handoff this ensures zero head/torso/shoe registration or identity change.

| Draft | Boundary | Canonical source |
| --- | --- | --- |
| A-gu-to-feng-entry.png | Gu→Feng entry | formal Gu Idle0 |
| B-gu-to-feng-exit.png | Gu→Feng exit | formal Feng Idle0 |
| C-feng-to-gu-entry.png | Feng→Gu entry | formal Feng Idle0 |
| D-feng-to-gu-exit.png | Feng→Gu exit | formal Gu Idle0 |

A/D and B/C are intentionally identical pairs: direction does not change the
same canonical character pose. No energy or guides are included in asset PNGs.
Effects can be designed only for later intermediate stages, not used to conceal
a boundary mismatch.

## Comparisons

- `qa/four-endpoints-contact-sheet.png`: clean four-pose preview at1×.
- `qa/canonical-overlay-and-landmarks.png`: each canonical, draft, exact-pixel
  overlay and guide panel. White overlay=identical RGBA foreground; cyan=only
  canonical, magenta=only candidate, yellow=changed color. All drafts have0
  differing pixels. `qa/A-overlay.png` through `D-overlay.png` also stand alone.
- Guide-only red line: logical registration x=96. Orange line: ground y=203.
  Cyan rectangle: fixed head QA band0:70; green: body band70:208. These are
  reference bands, **not anatomical segmentation**.
- `qa/validation.json`: hashes, head/body/shoe/whole-image bbox, per-box deltas,
  measured body-band bbox center, alpha, hidden RGB and8-connected components.

The existing asymmetric Gu head/hair gives a whole-alpha hull center different
from its body placement. Do not recenter it by hull center. The body-band bbox
proxy is95.5 for Gu and96 for Feng; both retain the existing x=96 registration
coordinate. Exact canonical equality is preserved instead of a half-pixel
resampling or one-pixel "correction" to an already approved sprite. Please
explicitly review this coordinate convention with the poses.

All four: baseline203, head-position/body-bbox delta0, alpha only0/255, hidden
RGB0, no clipping, one connected character component. These numerical checks
do not substitute for your visual approval.

Independent static visual QA also passed (`qa/independent-review.json`), with
the same Idle-only limitation. This is a review recommendation, not user approval.

## Approval and scope stop

Current decision: **ENDPOINT_ART_APPROVED**, limited to these four Idle poses.

- [x] A approved by user
- [x] B approved by user
- [x] C approved by user
- [x] D approved by user

This approval is not full-animation or Running approval. At preparation time
no intermediates or runtime installation existed. Future candidates must
separately pass their asset and real-window continuity gates.

**Idle-only scope:** these four poses are not pixel-identical to every Running
phase or Hover/Drag pose. Approval does not imply active-Running continuity is
fixed; the state-matched requirement from the previous endpoint specification
still applies. Do not reset Running abruptly to these Idle poses in code.
That limitation must be resolved and reviewed when planning the next art phase.

This package stays in normal192×208 coordinates. Future artwork may place the
approved boundary in existing oversized canvases using only the fixed integer
layout registration; this phase does not generate those canvas variants.
