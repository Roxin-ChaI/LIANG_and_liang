"""Read-only A->pixel K1->existing K2 audit, gated by independent A/K1 static PASS."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

from tools.derive_locked_transition_k1 import resolve_static_review
from tools.locked_transition_k1 import OUTPUT, ROOT
from tools.prepare_manual_transition_endpoints import pixel_overlay
from tools.prepare_transition_animation_candidate import digest, metrics
from tools.specify_transition_keyframes import approved_inputs

K2 = ROOT / "assets/rework/v0.1.0/transition-keyframes/gu-to-feng-candidate-retry/keys/K2.png"
K2_SHA = "057eb3762789c5b388e09063180279a6043ceeed55a20db4e53f7661e9130c37"


def compare(k1: Image.Image, k2: Image.Image) -> dict:
    a,b = metrics(k1),metrics(k2)
    # K2 landmarks are historical approximate independent annotations, NOT new segmentation.
    return {"headSize":{"K1":[68,80],"K2Approx":[55,59],"deltaApprox":[-13,-21]},
            "headCenter":{"K1":[88,44],"K2Approx":[95.5,34.5],"deltaApprox":[7.5,-9.5]},
            "shoulderGuideWidth":{"K1":33,"K2Approx":62,"deltaApprox":29},
            "historicalK2AnnotationUncertaintyPx":3,
            "bodyBandBbox":{"K1":a["bodyReferenceBbox"],"K2":b["bodyReferenceBbox"],
                            "delta":[v-u for u,v in zip(a["bodyReferenceBbox"],b["bodyReferenceBbox"])]},
            "baselineDelta":b["baselineY"]-a["baselineY"],
            "warning":"guide estimates are review evidence, not an automatic visual FAIL; original K2 annotation is preserved"}


def prepare(output: Path = OUTPUT / "chain-qa", review_path: Path | None = None) -> dict:
    if output.exists():
        raise ValueError("refuse to overwrite chain audit")
    _,_,a = approved_inputs()[0]
    with Image.open(OUTPUT/"candidate/K1.png") as original:
        k1 = original.copy()
    review_file = review_path or OUTPUT/"candidate/qa/independent-review.json"
    prerequisite = resolve_static_review(k1,json.loads(review_file.read_text()))
    if not prerequisite["localChainAllowed"]:
        raise ValueError("A_K1_STATIC_PASS required; do not run conditional chain audit")
    if digest(K2) != K2_SHA:
        raise ValueError("existing K2 changed; stop instead of regenerating it")
    with Image.open(K2) as original:
        if original.mode != "RGBA" or original.size != (192,208):
            raise ValueError("existing K2 geometry changed")
        k2 = original.copy()
    output.mkdir(parents=True)
    images = (a,k1,k2)
    sheet = Image.new("RGBA",(576,240),(35,35,35,255))
    draw = ImageDraw.Draw(sheet)
    for i,(label,image) in enumerate(zip(("A FROZEN","K1 LOCKED PIXELS","K2 EXISTING / NO EDIT"),images)):
        sheet.alpha_composite(image,(i*192,28))
        draw.text((i*192+3,3),label,fill="white")
        draw.line((i*192,231,i*192+191,231),fill=(255,175,45,255))
    sheet.save(output/"contact-sheet.png")
    sheet.resize((1728,720),Image.Resampling.NEAREST).save(output/"contact-sheet-nearest3x.png")
    for name,left,right in (("A-K1",a,k1),("K1-K2",k1,k2)):
        panel = Image.new("RGBA",(576,240),(35,35,35,255))
        pd = ImageDraw.Draw(panel)
        for i,(label,image) in enumerate(zip((name+" LEFT",name+" RIGHT","RGBA diff overlay"),(left,right,pixel_overlay(left,right)))):
            panel.alpha_composite(image,(i*192,28))
            pd.text((i*192+3,3),label,fill="white")
        panel.save(output/f"{name}-overlay-contact.png")
    report = {"status":"AWAITING_INDEPENDENT_CHAIN_REVIEW","A_K1":"A_K1_STATIC_PASS",
              "K1_K2":compare(k1,k2),"K1Sha256":digest(OUTPUT/"candidate/K1.png"),
              "K2Sha256":digest(K2),"K2Source":str(K2.relative_to(ROOT)),
              "K2Modified":False,"K3Modified":False,"newPosesGenerated":0,
              "userArtApproval":"PENDING","runtimeEligible":False,
              "scope":"static only; no App integration, full animation or playback-speed changes"}
    (output/"landmark-report.json").write_text(json.dumps(report,indent=2)+"\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=OUTPUT/"chain-qa")
    args = parser.parse_args()
    print(prepare(args.output)["status"])
