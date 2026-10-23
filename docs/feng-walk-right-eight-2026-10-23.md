# Feng right walk: eight-frame completion

Scope: complete the approved four-pose blocking into an eight-frame review
candidate. Do not change approved images, Gu, left walk, atlases or the App.

| Frame | Source | Temporal relationship |
|---|---|---|
| 01 | Approved key 1, exact pixels | Near-leg contact |
| 02 | New | Key 1 → key 2, weight transfer / rear heel lifts |
| 03 | Approved key 2, exact pixels | Near support, far foot moving through |
| 04 | New | Key 2 → key 3, far foot advances / near toe-off |
| 05 | Approved key 3, exact pixels | Far-leg contact |
| 06 | New | Key 3 → key 4, opposite weight transfer |
| 07 | Approved key 4, exact pixels | Far support, near foot passing |
| 08 | New | Key 4 → key 1, near foot reaches / loop closure |

Each in-between is a separate built-in image edit using only its two approved
neighbours as references. It must preserve identity, pixel scale and limb identity.
No crossfades, procedural anatomy, duplicated frames, reverse playback, endpoint
reordering, independent bbox-fit scaling or speed-up to conceal errors.

## Self-review and packaging gates

- Inspect every new pose between both neighbours before treating it as usable.
- Keep odd frames pixel-identical to approved keys. All cells 192×208 RGBA;
  eight-frame strip 1536×208. Pure transparent background and nearest-neighbour only.
- Check foot contact, support-leg continuity, low swing foot, opposite arm swing,
  hips/elbows/cuffs and jacket connections. Audit all eight adjacent edges, including
  07→08→01. Native-view and enlarged contact sheets are both required.
- Uniform 140 ms draft timing, slow 450 ms QA timing. No duplicated endpoint hold.
- Approved key poses contain approximately 6 px height variation. Keep the
  measurements honest; new poses must stay between adjacent references, without
  adding overshoot. Human acceptance of the keys is not a new numerical PASS.
- Structural tests cannot substitute for visual approval. Mark failed sources
  explicitly and retain provenance. Do not integrate a failed or pending candidate.
- Deliver numbered GIF, slow GIF, Idle comparison, full contact sheet and per-pair
  triples. Final eight-frame review remains pending until the user approves it.

Each completed stage is committed independently. No left derivation this turn.

## First assembly — REWORK_REQUIRED

Four separately generated in-betweens were interleaved at 02/04/06/08; all odd
frames are pixel-identical to approved keys. Frame 6's initial source was rejected
for wrong limb phase, then revised once before assembly. The original rejected
source and prompt are retained, never silently selected by the packager.

Native contact-sheet self-review found frame 4 overreaches its stride, while frames
4/6 undershoot neighbouring body heights by 3/4px. These are not declared fixed
by file-order tests. `attempt-1-review.json` requires targeted art corrections.
The first assembled `review/` remains immutable historical evidence.

## Targeted revision R2 — REWORK_REQUIRED

Only new drawings 04/06 were revised. `review-r2/` retains all approved odd frames
and the first assembly's 02/08 byte-for-byte. Explicit source selection and recorded
belt coordinates make packing reproducible without overwriting earlier evidence.
The common nearest-neighbour scale remains 199/1219 for every new source.

| Triple (global frame numbers) | Heights (px) | Result |
|---|---|---|
| 01 → 02 → 03 | 199 / 199 / 199 | No height overshoot; motion approval pending |
| 03 → 04 → 05 | 199 / 190 / 193 | FAIL: additional 3px undershoot, stride too advanced |
| 05 → 06 → 07 | 193 / 189 / 194 | FAIL: additional 4px undershoot, body appears smaller/lower |
| 07 → 08 → 01 | 194 / 194 / 199 | No height overshoot; loop motion approval pending |

The local labels 01/02/03 on pair contact sheets mean the three positions in
that triple, not global frame IDs. `pair-04` is global 03/04/05; `pair-06` is
global 05/06/07. All soles remain at y=203; this does not resolve head/body jumps.
Frame 6's arm trajectory improved, but that is not a whole-frame PASS.

Evidence in `assets/rework/v0.1.0/feng-walk-right-eight-2026-10-23/review-r2/`:

- `contact.png`, `contact-native.png`: ordered full eight-frame review.
- `preview.gif`, `preview-native.gif`: 140ms per frame, sequence 01…08→01.
- `preview-slow.gif`: 450ms per frame; no duplicated endpoint or speed-up.
- `idle-comparison.gif`: unchanged canonical Idle beside candidate playback.
- `pair-02/04/06/08.png`, matching GIFs and overlays: pairwise inspection.
- `validation.json`: mechanical packaging facts, not visual acceptance.
- `self-review.json`: final static self-review, failed frames and evidence hashes.

The finite directed revision did not solve frames 4/6. Stop treating further
similar generations as progress; keep these as failed review evidence, not accepted
art. No integration, left derivation or modifications to approved key poses.
Actual App playback remains NOT_TESTED; animated screen observation is NOT_VERIFIED.
The user receives GIF previews for inspection; no user approval has been inferred.

Validation: 90 related Python tests passed (eight-frame packager, approved key
poses, both Gu suspended-drag candidates, Feng Look and Failed safeguards).
`git diff --check` passed. This was a scoped art regression, not a full project
Python/Node regression. Formal Gu/Feng atlas and App override SHA256 values match
the pre-work baseline; no runtime files were changed.
