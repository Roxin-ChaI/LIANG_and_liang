# KB2 → KF1 → KF2 → F0 manual art specification

The retained F0 direction is finished Feng with a front-facing low-arm pose.
Frozen KB2 and retained F0 bytes stay fixed. This specification divides their
head, expression, suit and limb differences over three independently reviewed
links. It does not approve F0 or produce images.

| Pose | Head guide | Head center | Hand skin centers left / right |
| --- | --- | --- | --- |
| KB2 | 56×68 | (88,38) | (80,146.5) / (111,151.5) |
| KF1 target | 54×64 | (88,36) | (75,145) / (116,148) |
| KF2 target | 52×59 | (88,33.5) | (69,143.5) / (122,145) |
| F0 | 50×55 | (89,31.5) | (64,142) / (128,142) |

Head guides are approximate art annotations; skin bounds exclude dark hand
outlines. Neither is a substitute for face or anatomy review. Each link allows
at most 6px head-size difference, 3px head-center x movement, 4px y movement,
10px body-band width difference and 8px/6px hand-center x/y movement. All poses
use a 192×208 RGBA canvas, registration x=96 and sole y=203.

KF1 still reads as KB2: its source hair, eyes, glasses and relaxed face remain;
only a small hand-selected head compression and initial posture straightening
occur. Low forearms move out slightly. Dark navy remains dominant while blue
shoulder/lapel accents begin and the banded cloth structure starts to resolve
into a tailored jacket. Feet stay byte-identical to KB2.

KF2 moves closer to F0: the local head completes another small reduction, brows
and lids start to tighten, fitted lapels and blue sleeves become established,
and the hands continue toward low clenched fists. The expression, cuffs and
clothes must each show an intermediate shape instead of all arriving at once.
The final KF2→F0 link completes these changes without a face replacement snap.

Use explicitly chosen native-pixel parts and manual pixel/seam edits. Local
head row/column removal may express the specified skull change; whole-character
scaling, interpolation, partial-alpha blending and AI generation are excluded.
Document every source, copied region, moved part, palette choice and edit.

Run KB2→KF1 independent visual QA before producing KF2. A visible face, arm,
clothing or pose snap fails even if all numeric limits pass. The full
K3→KB1→KB2→KF1→KF2→F0 contact sheet and adjacent overlays must pass before
`F0_ART_APPROVED`; only then can the F0→Idle entry audit start.
