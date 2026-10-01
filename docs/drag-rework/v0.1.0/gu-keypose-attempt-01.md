# Gu right-drag keypose attempt 01 — failed; generation stopped

Date: 2026-10-01 (Asia/Shanghai).

Status: `KEYPOSE_QA_FAIL_MANUAL_REVIEW_REQUIRED`.
No Feng keyposes, additional Gu frames, leftward frames or runtime integration
were produced following the failed gate. A user request to continue was not
interpreted as visual approval.

## Inputs and method

Built-in image generation, not CLI. References were the formal canonical Gu Idle
native PNG and its exact nearest-neighbor 4x enlargement under
`assets/rework/v0.1.0/idle-appearance-contract-2026-10-01/`.

Requested four keyposes: weight shift, first short foot contact to screen right,
passing/weight transfer, opposite foot contact. Identity, pixel style and
proportions were required to match canonical Idle exactly.

Prompt: `gu-keypose-attempt-01-prompt.txt`.

## Actual output

- Generated file (outside project assets):
  `/Users/mac/.codex/generated_images/01a084f8-c8ba-78d1-9993-a73842f9d8f4/exec-8d8c9618-d36b-46e4-815a-d67b554a3831.png`
- SHA256: `72ef99a1539c0d3f32a8318108395d6c54abc0257d7285a425053ec7b2bafc08`.
- RGBA, 2172×724, not the requested native 768×208 strip.
- 256 distinct Alpha values; 487813 pixels have 0<Alpha<255.
- 1083238 fully transparent pixels. Generated Alpha was neither thresholded
  nor otherwise modified to make a hard-edge compliance claim.
- Character registration does not follow four evenly aligned native cells.
  Equal-quarter slicing is therefore not a validated extraction method.

## Visual findings

Poses 2 and 4 show similar crossed-leg configurations. Alternating foot contact
and screen-right travel are not clearly conveyed. There is no basis to approve
the requested gait. Canonical face/hair/style byte identity is not established;
the drawing must not be described as matching Idle exactly.

The image remains a failed preview, not a project source or candidate atlas.
It was not copied into the usable asset tree. No automatic retries, per-frame
rescaling, head pasting, alpha cleanup or additional-frame completion were used.

## Required next gate

Human review of the gait direction and pose language before any further art.
A possible simpler design is a restrained front-facing lateral shuffle with
the head/upper-body appearance locked and independently readable alternating
foot lifts/placements. This is a proposal, NOT an approved replacement design.

Existing atlases, frozen Feng→Gu eight frames, runtime, Scheduler and Hooks remain
unchanged. The slow-drag interaction trigger diagnosis is separate and not fixed
by this failed art attempt.
