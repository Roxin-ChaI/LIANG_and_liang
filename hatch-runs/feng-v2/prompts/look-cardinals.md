Create one coherent horizontal four-cardinal anchor strip for Codex pet `liang-no-henshin`.

Use every attached reference. The approved Liang Wenfeng idle and completed `feng-v2/idle` are authoritative for the exact face, short black hair, thin-frame glasses, blue suit, white shirt, broad shoulders, strong build, upright posture, cold intimidating expression, pixel style, scale, baseline, and body registration. Use the layout guide only for four invisible equal slots; never draw or copy it. Obey `qa/look-mechanics.md`.

Output exactly four complete full-body poses in this strict left-to-right order on a genuinely transparent RGBA background:

1. `000 Up`: face broadly frontal, chin raised only slightly, pupils and eyelids unmistakably aim toward the TOP edge while retaining the cold expression.
2. `090 Right`: head turns subtly toward SCREEN-RIGHT; pupils and nose/face axis visibly shift to the right side of head center.
3. `180 Down`: face broadly frontal, chin lowered only slightly, pupils and eyelids unmistakably aim toward the BOTTOM edge without weakening the strong presence.
4. `270 Left`: head turns subtly toward SCREEN-LEFT; pupils and nose/face axis visibly shift to the left side of head center.

Screen-left and screen-right always mean the viewer's image edges. Each cardinal must be readable without labels. Keep the eye construction physical and consistent: eye whites, pupils, eyelids, eyebrows, glasses, and head turn must work together; do not paste floating pupils or replacement eyes.

Keep both feet, legs, torso, arms, hands, suit silhouette, body center, shoulder width, baseline, and apparent height fixed across all four poses. Head dimensions must remain identical. Only gaze, eyelids/eyebrows, head orientation, and at most a tiny rigid neck/shoulder accommodation may change. Do not mirror or rotate the whole person.

One centered pose per invisible 192x208 slot with generous safe padding. Crisp hard pixel edges only; no antialiasing, blur, scaling softness, clipping, overlap, empty slots, stray pixels, or hidden RGB under transparent pixels.

Do not change identity, build, clothing, hairstyle, glasses, face proportions, hands, or stance. No gestures, text, degree labels, arrows, UI, guides, energy, glow, shadows, scenery, props, effects, checkerboard, white background, black background, or color-key background.
