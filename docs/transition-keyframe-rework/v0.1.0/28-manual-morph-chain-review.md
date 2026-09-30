# KF1/KF2 complete morphology-chain review

Verdict: **MANUAL_BRIDGE_QA_FAIL**. F0 is not art approved. No F0→Feng Idle audit, App integration, tag or additional bridge synthesis occurred.

## Evidence scope

`tools/review_f0_morph_chain.py` recomputes all six landmarks and binds each previous visual review to the actual source/candidate bytes. Historical K3→KB1→KB2 approval is preserved, not inferred from new numeric limits. KF1/KF2 are native-pixel manual derivatives; the retained F0 and all approved predecessors are unchanged.

Evidence is in `assets/rework/v0.1.0/transition-keyframes/feng-f0/morph-bridge/full-chain-qa/`: native and nearest-3x Contact Sheets, five adjacent alpha overlays and `chain-report.json`. QA overlays contain alpha blending solely for comparison; candidate PNGs do not.

| Adjacent pair | Head Δw, Δh | Head center Δx, Δy | Body-band Δwidth | Static visual result |
| --- | --- | --- | --- | --- |
| K3→KB1 | −6, −6 | 0, −3 | +12 | Historical PASS, current hashes match |
| KB1→KB2 | −6, −6 | 0, −3 | +12 | Historical PASS, current hashes match |
| KB2→KF1 | −2, −4 | 0, −2 | +2 | PASS |
| KF1→KF2 | −2, −5 | 0, −2.5 | +5 | PASS |
| KF2→F0 | −2, −4 | +1, −2 | −2 | FAIL |

All baselines are y=203 and canvas registrations x=96. Head guides include some neck/collar, and body bands include sleeves; they are not exact anatomical segmentation. Numeric continuity is necessary but insufficient.

## Channel review

- Arms: low hands move outward in small steps and remain attached. F0's final sleeve inclination still changes, but no large hand teleport is the blocking issue.
- Expression: KF1/KF2 preserve the preceding relaxed eyes/glasses. F0 introduces a sharp brow/eye configuration, brighter swept hair and different mouth/jaw reading at once. This is a visible identity/expression snap even though the head bounds pass.
- Clothing and stance: blue sleeve/lapel fragments develop in KF2, but narrow straight trousers and a fragmentary jacket become thick blue folded trousers and a complete tailored jacket in one frame. This remains a visible shape/structure snap.
- Feet: identical soles are retained through KF2. F0 shares y=203 but has a different footprint. Equal baseline does not establish pose continuity.

## Gate and stop

The independent KF2 review already rejects face, suit and pose continuity on the final link. The full-chain check therefore records failure, not approval. Regression tests explicitly reject numeric-only approval and stale/missing visual evidence.

Validation: 35 relevant Python tests PASS across morphology specification, KF1/KF2 derivation, full-chain review, manual F0 construction/gate and the retained endpoint/bridge contracts. `git diff --check` PASS. This is static art QA, not an App motion or new human approval result.

No weakening of Feng identity, no changes to approved KB2/F0 or standard atlases, no player/Scheduler/Hooks changes. Do not proceed to F0→Idle. A future, explicitly scoped manual rework must distribute expression, hair shading, garment structure and trouser volume before the endpoint; it must not add unlimited bridges or use geometry alone to declare a pass.
