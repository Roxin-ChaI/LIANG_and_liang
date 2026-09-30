# Feng Entry keyframe specification

The entrance is a separate four-frame action after F0-v2. Its frames are E1, E2, E3, and the exact frozen Feng Idle B. F0-v2 is the input pose and is not counted as a frame. `tools/feng_entry_spec.py` binds both endpoint hashes and the approved static Morph gate.

E1 begins a small gaze change and lifts the left hand while the feet stay near F0. E2 raises that arm to chest level, begins the other hand's fist and starts one outward step. E3 brings the fingertips close to the lips, approaches the sharp gaze and almost reaches the wide stance. The final approved Idle frame completes only small details.

All poses use 192×208 RGBA, registration x=96 and baseline y=203. The head reference stays near the Feng 50×55 size, with at most 2px size or center change per link; these guides include some collar and, at B, a hand-occluded chin. They do not certify identity alone. Face/glasses, connected shoulders and sleeves, hand trajectory, alternating planted/supporting feet, trouser volume and garment folds each need a visual gate.

The sole-center guide is left 82.5→82.5→74→68→65.5 and right 109→109→116→125→127.5. Hand coordinates in the JSON are planning guides, not substituted art. The support-leg contact and body volume must be checked against real pixels in each candidate.

E1/E2 are the first art gate. A clear failure stops E3. E3 cannot be produced until both incoming links pass. The full A→Idle static review is a separate final gate. No source frame, F0, standard atlas, player, Scheduler or Hook is altered by this specification.
