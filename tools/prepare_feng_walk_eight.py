"""Prepare pairwise in-between references without changing approved key poses."""
from pathlib import Path
import json
import hashlib
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
KEYS=ROOT/"assets/rework/v0.1.0/feng-walk-right-keyposes-2026-10-23"
OUT=ROOT/"assets/rework/v0.1.0/feng-walk-right-eight-2026-10-23"
PAIRS=[(1,2),(2,3),(3,4),(4,1)]
PHASES=[
    "Near-leg contact settles into weight bearing. The front near shoe stays on the ground and moves partway back under the pelvis as the body advances in place. The far trailing heel lifts and the far leg starts swinging forward, still behind the support leg. Near arm begins moving from its rear extreme towards neutral. This is between contact and near-leg support, NOT a second contact or an opposite-leg swap.",
    "After near-leg support, the FAR leg swings forward through the hips towards its upcoming heel contact. The NEAR support leg moves back and starts toe-off. The far shoe has passed the support ankle and reaches forward, heel just above ground; do not land it as far ahead as the ending reference yet. The near arm swings gently forwards, intermediate between reference hands. Keep each thigh connected to the same hip; no replacement of both legs by the same crossing silhouette.",
    "Far-leg contact settles into weight bearing. FAR front shoe stays grounded and moves partway under the pelvis; NEAR trailing foot begins lifting and swinging forward. Near arm retreats from its forward extreme towards neutral. This is the opposite-leg weight transfer, NOT a repeated first-half step. Keep the newly planted far foot supporting weight, do not lift it instead.",
    "Loop closure from far-leg support to the next NEAR-leg contact: the NEAR leg advances forward/right from its passing position. Its heel reaches forwards close to the ground, not yet at the full stride of the end reference. The FAR support leg extends behind on toe-off. Near arm swings backwards, far arm forwards. This must naturally lead into reference 2 (key pose 1) without reversing time, swapping leg identity or adding a new pause."
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_approved_keys():
    review=json.loads((KEYS/"review-status.json").read_text())
    if review["status"]!="FENG_RIGHT_KEYPOSE_ART_APPROVED" or not review["generatorLocked"]:
        raise ValueError("Approved frozen key poses required")
    for p,digest in review["sha256"].items():
        if sha(KEYS/p)!=digest:
            raise ValueError(f"Frozen source changed: {p}")
    return review


def prompt(index):
    left,right=PAIRS[index]
    return f"""Use case: identity-preserve. Produce ONE in-between pixel-art walking sprite, not a sheet.
Image 1 is the START pose (approved key {left}); image 2 is the END pose (approved key {right}). Edit the pose of image 1 to the exact temporal halfway point before image 2. Keep the same canvas, viewpoint, scale and character; do not copy either endpoint unchanged. Output one complete character on a genuinely transparent 768x832 RGBA canvas, representing the SAME 192x208 native sprite enlarged exactly 4x. No cropping or zooming; leave the same transparent margins. Support sole at native y203 (4x y812), belt centre x96 (4x x384).
Motion for this specific interval: {PHASES[index]}
Identity/style invariants: exact same approved Feng, adult stern face, same short black swept hair, thin rectangular glasses, broad muscular shoulders, blue suit, open white shirt, black shoes. Consistent three-quarter SCREEN-RIGHT body and gaze. No changes of face/hair/glasses design, no slender body, chibi head or exaggerated muscles. Keep head dimensions within the two reference dimensions; its location is halfway between them. Torso, shoulder and leg volumes must stay between these reference poses, not balloon or shrink.
Art invariants: match the exact coarse hard-edge pixel clusters and palette of the two native sprites. Do NOT add finer illustration detail, smooth outlines, gradients or new shading. Make actual square pixel clusters at the reference scale. No anti-aliasing, blur, white rim or matte. No floor shadow, scenery, motion lines, effects or labels.
Anatomy: intact hips, knees, elbows, cuffs and jacket lapels. Trace near and far limbs continuously from reference 1 to 2. Small natural counter-swing; hands below waist; no high kicks, sprinting, exaggerated knee lift or theatrical fists. Foot progress and arm progress must agree. Do not mirror either character, dissolve between endpoints, make two overlapping figures, or output multiple poses. Only the requested intermediate pose.
"""


def prepare(output=OUT):
    review=verify_approved_keys()
    if output.exists():
        raise FileExistsError("Use a new revision; never overwrite prepared/reviewed art")
    output.mkdir(parents=True)
    for i in range(1,5):
        im=Image.open(KEYS/"attempt-3-review"/f"pose-{i:02d}.png").convert("RGBA")
        im.resize((768,832),Image.Resampling.NEAREST).save(output/f"key-{i:02d}-4x.png")
    mapping=[]
    for i,(left,right) in enumerate(PAIRS):
        key_frame=2*i+1; new_frame=key_frame+1
        mapping.extend([
            {"frame":key_frame,"kind":"approved-key","key":left},
            {"frame":new_frame,"kind":"in-between","fromKey":left,"toKey":right}])
        (output/f"prompt-{new_frame:02d}.txt").write_text(prompt(i))
    record={"status":"SPEC_READY","userApproval":"PENDING","runtimeIntegrated":False,
            "cell":[192,208],"strip":[1536,208],"frameCount":8,"mapping":mapping,
            "durationMs":[140]*8,"slowDurationMs":[450]*8,
            "frozenSourceReview":sha(KEYS/"review-status.json"),"frozenKeys":review["sha256"],
            "sourceDir":str(KEYS.relative_to(ROOT)),
            "sourceFindings":"Approved key poses retain their original ~6px height variation. Do not modify them or claim that approval changed the measured geometry. In-betweens must not overshoot neighbouring poses."}
    (output/"sequence-spec.json").write_text(json.dumps(record,indent=2)+"\n")
    return record


if __name__=="__main__":
    print(json.dumps(prepare(),indent=2))
