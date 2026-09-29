# F0: separate neutral Feng transition endpoint

F0 is a new *transition-only* finishing pose. It does not replace the frozen
B or the formal Feng Idle cell. B remains a correct Idle frame, but the
independent compatibility audit found it unsuitable as the current morph's
direct last frame. This stage specifies F0; it does not generate art.

## Identity and pose

F0 must already be recognizably Feng: adult sharp face under the same black
hair and thin glasses, broad muscular shoulders/torso, upright posture and
the finished tailored blue suit. Gu's narrow body and tired face must not
remain. The gaze stays forward. Unlike B, both arms remain low or end a small
charge; no finger suddenly appears at the chin. The feet move only
incrementally from KB2's narrow stance. The sole is y=203 and registration
anchor x=96 on a 192×208 RGBA pixel canvas, with hard nearest-neighbor edges.

Head reference target is width 49–52, height 54–57, center x=86–91 and
y=29–34. The body-band hull should be about 99–104px wide. These are
*guides*, not substitutes for looking at the face, glasses, sleeve anatomy,
trouser legs and lapels. B's hand partly obscures its chin, so its historical
49×54 guide is approximate by about ±3px. F0 must visually match Feng in
face, suit construction and shoulder volume, not merely fit a bounding box.

## Two independent transitions

| Link | Allowed principal change | Disallowed shortcut |
| --- | --- | --- |
| KB2→F0 | Complete the Feng body, face and clothing morph while arms/feet trace a continuous path | Copy B, abruptly lift hand, snap to wide stance |
| F0→Feng Idle | Raise the arm to the chin, set the other hand and widen the stance | Further large head shrink, shoulder expansion or identity switch |

The nominal KB2 head guide is 56×68. Even to the upper target F0 guide
52×57, a direct link loses 11px of height, beyond the preceding bridge's
6px/link budget. One *additional shape bridge* is therefore allowed if needed,
but not automatically approved. It must be separately derived and visually
checked, including face, arms, legs and suit. If F0→B is still an obvious
single-frame arm/stance jump, stop adding morph frames and plan a separate
Feng entry animation. Its final handoff must still use the formal Idle frame.

No whole-character scaling, whole-image regeneration, interpolation, blur,
antialiasing, frame hiding or playback speed changes may conceal a bad link.
All A/K1/K2/K3/KB1/KB2/B source bytes stay frozen. Before F0 or a bridge is
accepted, require native/3× contact, pixel/hash provenance, head and body
landmarks, baseline/registration checks, overlays and independent visual QA.
Numeric gates alone cannot approve the art. No App integration, Tag or full
animation fill follows from this specification.
