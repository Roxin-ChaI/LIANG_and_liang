# K1 locked-region pixel derivation

The user explicitly replaces AI character regeneration with local deterministic
pixel edits of approved A. This scope overrides hatch-pet's normal generation
rule; no ImageGen, regenerated head or new full animation is permitted.

Head/hair/face/glasses/ears and neck upper edge reuse A RGBA bytes, including
transparent pixels. A conservative lock freezes all rows0:90 and the neck/collar
rectangle x84:103,y90:101. Outside x66:126,y90:180 is also locked, including all
feet/lower legs. The binary editable mask is the complement, not an anatomical
segmentation claim. This intentionally locks more than the minimum requested.

- Native192×208 RGBA, registration96, sole203. No scaling or global translation.
- Anatomical A reference [54,4,122,84],68×80; center(88,44). Exact unchanged
  identity bytes make actual delta0, stricter than the permitted±1px.
- Shoulder guide width33 is preserved at its locked canonical y83 anchors.
  Shoulder90:110 alpha-hull width is separately checked (delta≤4); not confused
  with anatomical shoulder width.
- Body70:208 alpha band edges may each move at most3px. No early muscular Feng.
- Only small local shoulder/arm/torso/upper-leg pixel edits; effects omitted.
  Pixel copies use A's existing RGBA values; no interpolation or antialiasing.
- Byte-level lock includes RGB and alpha, even beneath transparency. Any locked
  change, invalid geometry, clipping, isolated pixel or disconnected body FAILS.

Spec/masks: `assets/rework/v0.1.0/transition-keyframes/k1-locked/spec/`.
Tool: `tools/locked_transition_k1.py`; tests: `tests/test_locked_transition_k1.py`.
This first commit emits only masks, reference QA and contract, not candidate art.
Automatic PASS is not art approval: independently review pose, seams, neck and
identity at native size. Only an A→K1 visual PASS opens the unchanged K2 audit.
If any locked-region edit becomes necessary, stop MANUAL_PIXEL_ART_REQUIRED.
Do not alter the mask to accommodate a failed candidate. No App/Tag integration.
