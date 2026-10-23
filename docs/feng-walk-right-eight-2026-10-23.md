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
