# Approved action integration — 2026-10-23

User authorized unified integration, explicitly deferring Feng Look.

## Asset assembly

Two derived, lossless atlases in
`assets/rework/v0.1.0/approved-actions-integration-2026-10-23/` replace only:

| Form | Zero-based row | Approved source |
|---|---|---|
| Gu | 1 / 2 | Right revision-2 / left suspended sway |
| Feng | 1 / 2 | Approved eight-frame right R2 / exact left mirror |
| Feng | 3 | R2 Waving edge cleanup |
| Feng | 5 | Failed R3 nod-revision |
| Feng | 8 | R2 Review edge cleanup |

All source approvals and hashes are checked before assembly. Every replaced cell
is byte-identical RGBA after decoding the lossless WebP. Every other row remains
identical to the previously selected October 2 atlas, including both forms' Look.
Frozen source atlases and both transitions remain unchanged. Provenance and hashes
are in `manifest.json`; per-action GIFs show the exact integrated cells.

The existing Gu Waiting/Running/Review rows contain semi-transparent pixels;
both baseline atlases also contain an Idle slot 6 unused by the six-frame runtime.
These pre-existing details are preserved, not silently cleaned or newly declared
binary-alpha/empty. The scoped validator permits that specific unused Idle slot;
all new rows have binary alpha, transparent RGB zero and empty spare cells.
This is not a claim of a full clean-atlas validator certification.

Historical approval manifests retain their pre-integration `runtimeIntegrated`
fields as frozen evidence. This document and the new integration manifest track
the subsequent deployment separately.

## Runtime selection and acceptance

Pending in the next stage: select the derived atlases, retain approved motion
timing, build a separate local App and test it with an isolated test profile.
Do not overwrite or restart the currently running older App, touch Codex, change
Hooks, alter Look artwork, or create a release tag.
