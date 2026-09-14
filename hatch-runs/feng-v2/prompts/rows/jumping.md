Create one horizontal animation strip for Codex pet `liang-no-henshin`, state `jumping`.

Use the attached canonical base for identity. Use the attached layout guide only for slot count, spacing, centering, and padding; do not draw the guide.

Approved action reference: use attached `assets/feng/hover.png` as the head, gaze, posture, and restrained hover-response basis. Keep head, face, shoulders, and body scale consistent across all frames.

Output exactly 5 full-body frames in one left-to-right row on a genuine transparent RGBA background. Treat the row as 5 invisible equal-width slots: one centered complete pose per slot, evenly spaced, with no overlap, clipping, empty slots, labels, or borders.

Identity: same pet in every frame: Approved 梁文峰: adult male, black short hair, thin-frame glasses, blue suit, white shirt, broad shoulders, strong build, upright posture, sharp cold intimidating presence; preserve the exact approved face, proportions, clothing, pixel style, and identity.. Preserve silhouette, face, proportions, markings, palette, material, style, and props.
Style: Pet-safe sprite: compact full-body mascot, readable in a 192x208 cell, clear silhouette, simple face, stable palette/materials, and crisp hard edges for direct transparent RGBA output. Style `pixel`: Pixel-art-adjacent digital mascot with a chunky silhouette, simple dark outline, limited palette, flat cel shading, and visible stepped edges. User style notes: 严格保持 approved 梁文峰 final 的黑色短发、细框眼镜、蓝色西装、白色衬衫、宽肩强壮体型、挺拔站姿与冷峻压迫感；透明背景成品必须硬边像素、无抗锯齿、无模糊；禁止重新设计、添加文字、新配饰、阴影或脱离主体的特效。.
Animation continuity: keep apparent pet scale and baseline stable within the row unless the state itself intentionally changes vertical position, such as `jumping`. Move the pose within the slot instead of redrawing the pet larger or smaller frame to frame.

State action: Hover jump loop: anticipation, lift, airborne peak, descent, and settle through body height.

State requirements:
- Show the jump through pose and vertical body position only: anticipation, lift, airborne peak, descent, settle.
- Do not draw ground shadows, contact shadows, drop shadows, oval shadows, landing marks, dust, smears, bounce pads, or motion marks under the pet.
- Keep the background outside the pet fully transparent with RGB cleared to zero.

Clean extraction: crisp opaque edges, safe padding, no scenery, text, guide marks, checkerboard, shadows, glows, motion blur, speed lines, dust, detached effects, stray pixels, or hidden background RGB in transparent pixels.
