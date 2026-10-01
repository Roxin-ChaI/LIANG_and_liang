# User-confirmed retirement of malformed source art

Date: 2026-10-01 (Asia/Shanghai).
Authority: user confirmed deletion of all twelve D01–D04 source images in the deletion review.

These sources are REJECTED / RETIRED. This decision supersedes any historical
ART_APPROVED or numerical PASS for these candidates. They must not be regenerated,
reused as art references, or restored merely to satisfy historical asset tests.

## Exact deleted sources

Paths below are relative to `assets/rework/v0.1.0/transition-keyframes/`:

| Review ID | Source |
| --- | --- |
| D01-01 | feng-f0/v2/feng-entry/e1-e2/E1.png |
| D01-02 | feng-f0/v2/feng-entry/e1-e2/E2.png |
| D01-03 | feng-f0/v2/feng-entry/e3-gate/E3.png |
| D02-01 | feng-f0/morph-bridge/kf2/KF2.png |
| D02-02 | feng-f0/v2/candidate/F0-v2.png |
| D03-01 | k2-controlled/candidate/K2.png |
| D03-02 | k2-controlled/candidate-locked-hands/K2.png |
| D03-03 | k3-controlled/candidate/K3.png |
| D03-04 | k3-b-bridge/kb1/KB1.png |
| D03-05 | k3-b-bridge/kb2/KB2.png |
| D03-06 | feng-f0/morph-bridge/kf1/KF1.png |
| D04-01 | feng-f0/manual-pixel-art/F0.png |

## Recovery and scope

All twelve files matched the reviewed SHA256 values and committed bytes before
removal. Recovery point: `d7b530b28322aca44ebe87d566f2f68ac7eb851c`.
No identical file-byte copies were listed by the review inventory.

Historical contact sheets, overlays, reports and Git objects remain only as
failure evidence, not usable source art. Other failed image-generation drafts
were outside this twelve-file deletion approval and remain untouched.

Formal Gu/Feng atlases, Idle endpoints, approved reverse transformation frames,
runtime, Scheduler, Hooks and the running App are unchanged.

## Dependency impact

Historical art construction/audit tools and associated tests reference the
retired PNGs (including `review_gu_feng_entry_chain.py` and the controlled
K2/K3, bridge, F0 and entry workflows). They no longer have a complete input set.
Do not claim their regression suite passes after retirement. No runtime code or
test assertions were changed to hide this missing-source condition.

Next work starts with Gu failed 02/08 and waiting 02/03/05/06 eye-region review.
New visual deformation requires stopping for human review, irrespective of
bounding-box or other numerical gates.
