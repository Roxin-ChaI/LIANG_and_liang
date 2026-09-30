# Feng Entry E3 / frozen Idle static gate

Verdict: **ENTRY_QA_FAIL**. E2→E3 is a readable pose progression, but E3→the exact frozen Feng Idle B still has a clear visual jump. `FENG_ENTRY_ART_APPROVED` is not granted.

E3 is a manually controlled local pose based on the reviewed E2: the left forearm/hand rises again, the brow tightens, the second foot moves outward, and existing dark-blue suit/leg pixels remain the body base. No source endpoint, earlier keyframe or formal atlas was modified. Its technical gate confirms 192×208 RGBA, binary alpha, zero hidden RGB, intact silhouette, y=203 baseline, a stable 50×55 head guide and no new isolated fragments or internal holes.

The final visual link still fails. E3's hand is raised toward the face, but the approved B fingertip is much higher and touches the lip; the final forearm angle and right fist differ. The hair/eyes and suit tailoring also change together. The new stance almost reaches B's foot positions, yet the trousers suddenly gain volume: opaque left/right pixel counts at y=150 are E3 **13/13** versus B **21/25**, at y=160 **14/19** versus B **19/22**. That is a real local volume/suit-structure gap, not solved by matching the sole baseline or head bbox.

Two E3 revisions were inspected: an earlier close-to-E2 garment retained the full last-frame jump, while transferring many B garment pixels at once created noisy jacket and pants fragments in E3. The retained candidate uses the cleaner local construction and keeps the failure visible. More edits solely to E3 cannot credibly make both E2→E3 and E3→B continuous with the present proportions; do not shift the mismatch into another single frame.

Evidence: `assets/rework/v0.1.0/transition-keyframes/feng-f0/v2/feng-entry/e3-gate/` contains E3.png, native/nearest-3x Contact Sheets, both overlays, source-bound provenance, landmark report, visual review and gate result. The visual review is recorded as a project static assessment, with human approval pending.

Stop at this gate. No full-chain approval, App integration, tag, player/Scheduler/Hook edits or alteration of approved E1/E2/F0/B occurred. The remaining issue requires a separate art decision about limb/clothing construction or the number of Entry poses; the current four-frame request cannot be declared complete by geometry alone.
