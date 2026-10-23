"""Mechanical review packing only. Never synthesize joints or tween the walk."""
import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.prepare_feng_walk_keyposes import OUT, sha
from tools.build_animation_review import save_preview

# Manually located belt-buckle centres in source-attempt-3's local cells.
# Their differing source-sheet placements are not intended motion.
HIPS=[(356,345),(311,345),(369,337),(311,337)]
SCALE=199/623


def normalize(frame,hip):
    a=np.array(frame.convert("RGBA"))
    a[a[:,:,3]<128]=0
    a[a[:,:,3]>=128,3]=255
    hard=Image.fromarray(a)
    bbox=hard.getbbox()
    # One shared scale, anchored at belt x and foot bottom. No per-pose fit.
    # PIL maps pixel centres: account for the half-pixel offset explicitly.
    coefficients=(1/SCALE,0,hip[0]+0.5-96.5/SCALE,
                  0,1/SCALE,bbox[3]-0.5-203.5/SCALE)
    packed=hard.transform((192,208),Image.Transform.AFFINE,coefficients,
                          resample=Image.Resampling.NEAREST)
    array=np.array(packed)
    array[array[:,:,3]==0]=0
    packed=Image.fromarray(array)
    b=packed.getbbox()
    if not b or b[0]<=0 or b[1]<=0 or b[2]>=192 or b[3]>=208:
        raise ValueError("Clipping or empty candidate; do not silently crop")
    return packed,{"sourceBbox":list(bbox),"sourceHip":list(hip),
                   "sharedScale":SCALE,"outputBbox":list(b),
                   "soleY":b[3]-1,"characterHeight":b[3]-b[1],
                   "transform":list(coefficients)}


def build(folder=OUT/"attempt-3-review"):
    if folder.exists():
        record=folder/"validation.json"
        if not record.exists() or json.loads(record.read_text())["status"]!="SELF_REVIEW_PENDING":
            raise FileExistsError("Keep completed review evidence; use a new revision")
    source=Image.open(OUT/"source-attempt-3.png").convert("RGBA")
    frames=[]; metrics=[]
    for i,hip in enumerate(HIPS):
        x,y=(i%2)*602,(i//2)*653
        raw=source.crop((x,y,x+602,y+653))
        f,m=normalize(raw,hip)
        frames.append(f);metrics.append(m)
    folder.mkdir(exist_ok=True)
    for i,frame in enumerate(frames,1):
        frame.save(folder/f"pose-{i:02d}.png")
    idle=Image.open(OUT/"canonical-idle.png").convert("RGBA")
    labels=["IDLE / unchanged","01 N contact","02 N support","03 F contact","04 F support"]
    sheet=Image.new("RGB",(1920,456),(35,38,44))
    draw=ImageDraw.Draw(sheet)
    for i,f in enumerate([idle]+frames):
        big=f.resize((384,416),Image.Resampling.NEAREST)
        sheet.paste(big,(i*384,30),big)
        draw.text((i*384+8,8),labels[i],fill="white")
        draw.line((i*384,437,(i+1)*384-1,437),fill=(100,180,100))
    sheet.save(folder/"idle-contact.png")
    save_preview(frames,[280]*4,folder/"preview.gif")
    save_preview(frames,[650]*4,folder/"preview-slow.gif")
    comparisons=[]
    for f in frames:
        pair=Image.new("RGBA",(384,208));pair.paste(idle,(0,0));pair.paste(f,(192,0))
        comparisons.append(pair)
    save_preview(comparisons,[400]*4,folder/"idle-comparison.gif",display_size=(768,416))
    joints=Image.new("RGB",(1536,592),(35,38,44))
    for i,f in enumerate(frames):
        crop=f.crop((32,60,160,208)).resize((384,444),Image.Resampling.NEAREST)
        joints.paste(crop,(i*384,32),crop)
    ImageDraw.Draw(joints).text((8,8),"JOINTS / NEAREST-NEIGHBOUR DETAIL",fill="white")
    joints.save(folder/"joint-detail.png")
    height_range=max(m["characterHeight"] for m in metrics)-min(m["characterHeight"] for m in metrics)
    report={"status":"SELF_REJECTED","userApproval":"NOT_REQUESTED",
        "runtimeIntegrated":False,"frameCount":4,"cell":[192,208],
        "source":"../source-attempt-3.png","sourceSha256":sha(OUT/"source-attempt-3.png"),
        "mechanicalProcessing":"Shared isotropic NN scale; pelvis/sole registration; alpha threshold 128 and transparent RGB zero. No anatomy painting, palette remapping, tweening or per-frame size fitting.",
        "metrics":metrics,"uniquePoses":len({f.tobytes() for f in frames}),
        "heightRange":height_range,
        "geometryGate":{"maxHeightRange":2,"passed":height_range<=2},
        "visualGate":{"passed":False,"findings":[
            "Poses 3/4 shorten visibly relative to 1/2 after common scaling and sole registration; this is not acceptable stable-height walking.",
            "Pose 3 uses a longer stride and narrower-looking torso turn than pose 1; the two half-steps are not visually balanced.",
            "Pose 2 remains early rear-foot lift whereas pose 4 is a more advanced passing pose. Timing symmetry and full foot trajectories are not established.",
            "Identity/style matching cannot be approved solely from similar head dimensions; runtime-normalized candidates still require stricter Idle matching."
        ]},
        "livePlayback":"NOT_VERIFIED","appTest":"NOT_TESTED",
        "nextStageAllowed":False,
        "note":"Animated GIF is four-pose blocking, not the final eight-frame animation. Structural values do not establish visual approval."}
    (folder/"validation.json").write_text(json.dumps(report,indent=2)+"\n")
    return report


if __name__=="__main__":
    print(json.dumps(build(),indent=2))
