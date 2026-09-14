Create one horizontal animation strip for Codex pet `liang-no-henshin`, state `idle`.

Use the attached canonical base for identity. Use the attached layout guide only for slot count, spacing, centering, and padding; do not draw the guide.

Approved anchor: use attached `assets/feng/idle.png` as the exact neutral identity and pose baseline. Frame 1 must preserve this approved Liang Wenfeng without redesign.

Output exactly 6 full-body frames in one left-to-right row on a genuine transparent RGBA background. Treat the row as 6 invisible equal-width slots: one centered complete pose per slot, evenly spaced, with no overlap, clipping, empty slots, labels, or borders.

Identity: same pet in every frame: Approved 梁文峰: adult male, black short hair, thin-frame glasses, blue suit, white shirt, broad shoulders, strong build, upright posture, sharp cold intimidating presence; preserve the exact approved face, proportions, clothing, pixel style, and identity.. Preserve silhouette, face, proportions, markings, palette, material, style, and props.
Style: Pet-safe sprite: compact full-body mascot, readable in a 192x208 cell, clear silhouette, simple face, stable palette/materials, and crisp hard edges for direct transparent RGBA output. Style `pixel`: Pixel-art-adjacent digital mascot with a chunky silhouette, simple dark outline, limited palette, flat cel shading, and visible stepped edges. User style notes: 严格保持 approved 梁文峰 final 的黑色短发、细框眼镜、蓝色西装、白色衬衫、宽肩强壮体型、挺拔站姿与冷峻压迫感；透明背景成品必须硬边像素、无抗锯齿、无模糊；禁止重新设计、添加文字、新配饰、阴影或脱离主体的特效。.
Animation continuity: keep apparent pet scale and baseline stable within the row unless the state itself intentionally changes vertical position, such as `jumping`. Move the pose within the slot instead of redrawing the pet larger or smaller frame to frame.

State action: Calm low-distraction resting loop: subtle breathing, tiny blink, slight head/body bob, and only quiet persona-preserving motion.

State requirements:
- CRITICAL: idle is the low-distraction baseline state and the first frame is also used as the reduced-motion static pet.
- Use only subtle idle motion: gentle breathing, a tiny blink, a slight head or body bob, a very small material sway, or another quiet motion that fits the pet persona.
- Keep the pet essentially in the same pose, facing direction, silhouette, markings, palette, and prop state across all 6 frames.
- Idle variation must stay calm but still read as animation; do not repeat effectively identical copies across the loop.
- Do not show waving, walking, running, jumping, talking, working, reviewing, emotional reactions, large gestures, item interactions, or new props.
- Feet, base, body, or object anchor should remain planted or nearly planted.
- The first and last frames should be very close visually so the loop feels calm and does not pop.

Clean extraction: crisp opaque edges, safe padding, no scenery, text, guide marks, checkerboard, shadows, glows, motion blur, speed lines, dust, detached effects, stray pixels, or hidden background RGB in transparent pixels.
