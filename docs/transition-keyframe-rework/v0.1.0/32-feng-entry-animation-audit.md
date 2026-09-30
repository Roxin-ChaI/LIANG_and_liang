# Neutral F0-v2 → Feng Idle Entry audit

Verdict: **FENG_ENTRY_ANIMATION_REQUIRED**. The direct connection fails. The requested independent four-pose Entry is planned here; no Entry frames were generated.

Prerequisite: the current hash-bound project static Morph gate is `F0_MORPH_ENDPOINT_APPROVED`. That is not a new human artwork approval or a dynamic runtime result.

## What changes at the direct cut

Head guide changes 50×55→49×54, center (88,31.5)→(88.5,31). Body-band width changes 101→104. This avoids the earlier large head shrink, but numeric bounds alone do not make the images continuous.

The viewer-left hand moves from the low charge-finishing pose to the lips. Both elbow/sleeve configurations change. The feet's sole-band centers move left 17px and right 18.5px into the wide stance. Relaxed brows/eyes become sharp, and hair/shirt/lapels/hem/trouser folds resolve into B's final detailing. These changes need a performed action rather than a direct cut.

The exact pose-normalized thigh/calf volume is **NOT_PROVEN**. Both images read broad/strong, but the bent/open limbs and spread stance prevent a scalar bbox comparison from establishing identical anatomy. The Entry art gate must verify this explicitly; it may not conceal an additional form change behind the pose change.

## Four planned Entry poses

| Pose | Face and arm | Support/stance | Clothing |
| --- | --- | --- | --- |
| E1 | Slight brow focus; low forearm starts rising | Prepare weight transfer, retain grounded feet | Small folds respond to elbow movement |
| E2 | Forearm reaches mid chest; eyes focus gradually | One outward step begins | Lapel and waist folds track the pose |
| E3 | Fingertips approach the chin; expression nears B | Other foot reaches the wider stance | Trouser contours follow leg rotation, not inflation |
| E4 | Exact frozen B; fingers make final contact and fist settles | Complete B stance and baseline | Finish B detailing without a last-frame form replacement |

F0-v2 precedes these four planned poses; E4 terminates at the exact approved B. They are separate from the Gu→Feng Morph frame budget. No original 10-frame constraint is used to compress this action. Timing will be evaluated against actual future art; this report does not claim a tested playback cadence.

Every future link must preserve approximately the existing Feng skull/shoulder proportions and inspect face identity, arm trajectory, planted feet, garment contours and limb volume visually. If the posture-normalized proportions cannot connect, reopen the relevant art gate rather than approving more morphing as Entry.

## Evidence and validation

`assets/rework/v0.1.0/transition-keyframes/feng-f0/v2/entry-audit/` contains native/nearest-3x three-pose Contact Sheets, F0-v2/B overlay, hash-bound visual review and measured Entry report.

The phase uses 18 relevant Python tests for specification, construction, Morph gate and Entry audit. Tests reject altered locked regions, visual failures, stale evidence and Entry execution without a fresh Morph pass. No player, Scheduler, Hook, standard atlas, current App or tag was changed.
