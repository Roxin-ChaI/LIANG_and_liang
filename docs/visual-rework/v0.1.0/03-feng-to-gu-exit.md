# V-05 exit rework — ASSET_REWORK_REQUIRED (not fixed)

[Actual Idle exit](exit/runtime/idle-feng_to_gu-sheet.png), [actual held-Running exit](exit/runtime/running-feng_to_gu-sheet.png), [Running window recording](exit/runtime/running-feng_to_gu-window-recording.gif), [timeline/state recovery](exit/runtime/transition-timeline.json), [rigid translation diagnostics](exit/feng_to_gu-rigid-candidates.png), [anchor report](exit/feng_to_gu-feasibility.json).

Eight displayed frames were preserved; last-frame→completion dwell was at least140 ms. After completion, the actual candidate Renderer selected row7 Running and the state machine retained underlying Running. Hook code and behavior are unchanged. Correcting Gu's work baseline in Commit1 removed the former5 px foot jump on Running recovery; both the registered transition shoes and normal work foot are now y=203.

Rigid alignment was tested without changing runtime art: Idle can nearly align its horizontal proxy anchors at−8 px; Running at−2 px. Those do **not** make the endpoint's facial/torso/arm drawing match the canonical poses. The target work head top is12 px versus5 px at the final transform image; changing vertical position to match the head would break the shoe baseline. The best diagnostic Idle translation likewise leaves a different head/shoulder drawing visible. These diagnostic variants are not packaged as frame replacements.

A fixed−8 px offset across the whole reverse sequence would displace the initial Feng, whose current coordinates are already aligned. A gradual state-aware offset could reduce horizontal motion, but would still hand off an alternate endpoint pose; applying it and reporting P1 PASS would conceal an unresolved source problem. Resetting Running to Idle, dropping frame7 or accelerating the ending is not an acceptable substitute.

**V-05 remains P1, ASSET_REWORK_REQUIRED.** Needed next step: authorize a pose-matched Gu endpoint/motion bridge, with independently approved Idle and active-Running handoffs. No frozen transition pixel has been redrawn. This commit records verified baseline/state-recovery progress and the unresolved visual handoff, not a complete repair.

Relevant tests: rigid geometry is distinguished from pose approval; the retained actual renderer record proves8 frames, last-frame hold, underlying Running preservation and row7 restoration. No release candidate while this P1 remains.
