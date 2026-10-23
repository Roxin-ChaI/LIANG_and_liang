# Feng right walk: four-key-pose review

Date: 2026-10-23. User confirmed Feng; the preceding “Gu right” was a typo.
Scope: four review poses only, not the final eight-frame strip. No App integration,
left derivation, Gu changes, runtime changes or release tag.

## Identity and rendering contract

Use formal Feng atlas row 0 / cell 0 as canonical proportions, colours and pixel
scale. Preserve adult face, short black hair, thin glasses, broad shoulders,
strong build, blue suit and white shirt. The finger-at-lips arm may lower naturally.
The four poses share a near-three-quarter screen-right orientation and gaze;
do not turn the face independently on every step or mirror the head between poses.

Runtime-sized candidates: RGBA 192×208, hard alpha, transparent RGB zero,
no white halo, interpolation, blur or per-frame independent scale fitting.
Reference Idle bbox is (44,4,148,204), head reference (64,4,113,61), sole y=203.
These are references, not a demand for identical silhouette in moving limbs.
Hip registration remains around x=96; support sole y=203. Whole-body height and
head dimensions must remain visually consistent with Idle, not just each other.

## Key-pose order

Leg N means camera-near leg; leg F means camera-far leg. These identifiers must
track the same leg through occlusion, not be renamed by screen position.

1. N contact: N heel forward/right, F trailing on toe. Opposite arm forward.
2. N support: N bears weight under pelvis; F passes with low toe clearance.
3. F contact: F heel forward/right, N trailing on toe. Arm swing reverses.
4. F support: F bears weight under pelvis; N passes, reconnecting to pose 1.

Quiet upright walk, not a sprint, march or suspended Gu drag. Do not use extreme
knee flexion, kicks, wide lunges or large arm swings. Maintain anatomical connections
at hip, knee, elbow, wrist/cuff. Jacket lapels and sleeves must remain coherent.

## Gates

1. Inspect the actual generated source before packing. Reject visible identity
   drift, repeated same-leg gait, disconnected limbs or unstable proportions.
2. Pack all poses with one shared nearest-neighbour scale, if necessary, never
   different per-pose scale. Record crop/translation/scale and raw source.
3. Report alpha, bounds, baseline, unique poses and protected-file hashes. These
   are structural checks, not proof of correct anatomy, identity or locomotion.
4. Review each adjacent pair including 4→1, contact/passing leg identity and
   small counter-swing of arms. Show Idle beside every pose and a four-pose GIF.
   Do not interpolate, duplicate or accelerate poses to hide a failed step.
5. Human approval is PENDING until explicit review. A four-pose GIF is a motion
   blocking preview, not evidence that the eventual eight-frame cycle is smooth.
6. Only after approval make eight frames; only after approved right make left.

If a candidate fails self-review, label it rejected and do not promote it.
Protected inputs: Gu/Feng formal atlas, Gu approved suspended right/left,
Feng approved Look/Failed, asset overrides. No writes to those paths.

## Attempt 1 — self-rejected

The source sheet repeats near-leg-forward contact in poses 1/3 and the same
support leg in 2/4. The near arm does not reverse its swing. This fails the central
alternating gait requirement even though four distinct images were generated.
`attempt-1-review.json` records the failure; this is not a user review candidate.
A bounded targeted correction will address only the lower row's limb phase.

## Attempts 2/3 — bounded corrections, still self-rejected

Attempt 2 changes the lower-row arm/leg phase but pose 4 becomes another extended
contact rather than passing. Attempt 3 targets that leg only. Its low passing pose
improves the silhouette, but native-scale inspection exposes remaining failures:

- After one common scale and foot registration, poses 3/4 are approximately 6 px
  shorter than 1/2. Contact pose 3 should not suddenly shrink relative to contact 1.
- Pose 3 has a larger stride and more narrowed-looking torso turn than pose 1.
- Pose 2 is early rear-foot lift, while 4 is advanced passing: corresponding gait
  phases still do not establish balanced alternating support and timing.

No extra retry, eight-frame expansion, left mirror or integration is performed.
This is `FENG_RIGHT_KEYPOSE_SELF_REJECTED`, not an approved replacement.
The supplied GIF is failed-draft evidence, not a claim of smooth walking.

`attempt-3-review/` contains four 192×208 RGBA review crops, Idle comparison,
normal/slow GIF, joint details and measured geometry. The packer uses a shared
isotropic nearest-neighbour transform anchored at each manually identified belt
centre and sole. Alpha is thresholded at 128, hidden RGB zeroed. There is no
per-pose resizing, anatomy synthesis, recolouring, tweening or source-frame drop.
The foot sample uses PIL's half-pixel convention so the rendered sole is y=203.

Artwork was produced with the built-in image tool, not CLI. Exact prompts are
`assets/rework/v0.1.0/feng-walk-right-prompt-2026-10-23.txt` and the candidate
folder's `retry-prompt.txt` / `passing-prompt.txt`. Generated sources are retained
as `source-attempt-1.png` through `source-attempt-3.png` with no source overwrites.

Static self-review inspected actual source and native/2x/3x derived frames.
GIF decoding/cadence is tested; real-time playback observation is NOT_VERIFIED.
No App was launched or replaced. User approval is NOT_REQUESTED for failed art.

## Verification

64 related Python tests passed: Feng walk references/rejection evidence (12),
Gu suspended left/right, approved Feng Look and Failed suites. This is not a full
Python/Node application regression. `git diff --check` passed before submission.
Passing tests verify preservation, packing and honest rejection, not passing art.
