"""Pack four new drawings between frozen keys; no optical flow or pose warping."""
from pathlib import Path
import json
import sys
import numpy as np
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.prepare_feng_walk_eight import KEYS, OUT, PAIRS, sha, verify_approved_keys
from tools.build_animation_review import save_preview, save_contact

# All generated sources have the same approximately 1205x1305 image resolution.
# One common art scale calibrated on source-02 vs its 199px approved neighbours.
# This is NOT independently adjusted to make every pose the same bbox height.
SCALE=199/1219
BELT_CENTRES={2:621,4:610,6:633,8:641}


def normalized_source(path,frame):
    im=Image.open(path).convert("RGBA")
    if im.width!=1205 or im.height not in (1305,1306):
        raise ValueError("Unexpected source resolution; review common scale explicitly")
    a=np.array(im)
    a[a[:,:,3]<128]=0
    a[a[:,:,3]>=128,3]=255
    hard=Image.fromarray(a)
    box=hard.getbbox()
    if box is None:
        raise ValueError("Empty source")
    matrix=(1/SCALE,0,BELT_CENTRES[frame]+0.5-96.5/SCALE,
            0,1/SCALE,box[3]-0.5-203.5/SCALE)
    out=hard.transform((192,208),Image.Transform.AFFINE,matrix,
                       resample=Image.Resampling.NEAREST)
    a=np.array(out);a[a[:,:,3]==0]=0;out=Image.fromarray(a)
    b=out.getbbox()
    if b is None or b[0]<2 or b[1]<2 or b[2]>190 or b[3]!=204:
        raise ValueError(f"Clipped, insufficient margin or incorrect baseline: {b}")
    return out,{"source":path.name,"sourceSha256":sha(path),"sourceSize":list(im.size),
        "sourceBbox":list(box),"beltCentreX":BELT_CENTRES[frame],"commonScale":SCALE,
        "transform":list(matrix),"baseline":b[3]-1,"bbox":list(b),"height":b[3]-b[1]}


def assemble(keys,inbetweens):
    if len(keys)!=4 or set(inbetweens)!={2,4,6,8}:
        raise ValueError("Exactly four keys and in-betweens 02/04/06/08 required")
    result=[]
    for i,key in enumerate(keys):
        result.extend([key.copy(),inbetweens[2*i+2].copy()])
    if any(f.mode!="RGBA" or f.size!=(192,208) for f in result):
        raise ValueError("192x208 RGBA cells required")
    if len({f.tobytes() for f in result})!=8:
        raise ValueError("Do not duplicate frames to fake completion")
    return result


def build(folder=OUT/"review"):
    verify_approved_keys()
    if folder.exists():
        raise FileExistsError("Review outputs are immutable; use another revision")
    keys=[Image.open(KEYS/"attempt-3-review"/f"pose-{i:02d}.png").convert("RGBA") for i in range(1,5)]
    new={};metrics=[]
    for i in [2,4,6,8]:
        new[i],metric=normalized_source(OUT/f"source-{i:02d}.png",i)
        metrics.append({"frame":i,**metric})
    frames=assemble(keys,new)
    folder.mkdir(parents=True)
    strip=Image.new("RGBA",(1536,208))
    for i,f in enumerate(frames,1):
        f.save(folder/f"right-{i:02d}.png")
        strip.paste(f,((i-1)*192,0))
    strip.save(folder/"feng-running-right.png")
    save_preview(frames,[140]*8,folder/"preview.gif")
    save_preview(frames,[450]*8,folder/"preview-slow.gif")
    save_preview(frames,[140]*8,folder/"preview-native.gif",display_size=(192,208))
    save_contact(frames,folder/"contact-native.png")
    sheet=Image.new("RGB",(1536,896),(35,38,44));draw=ImageDraw.Draw(sheet)
    for i,f in enumerate(frames):
        x,y=(i%4)*384,(i//4)*448
        big=f.resize((384,416),Image.Resampling.NEAREST)
        sheet.paste(big,(x,y+28),big)
        kind="APPROVED KEY" if i%2==0 else "NEW IN-BETWEEN"
        draw.text((x+8,y+8),f"{i+1:02d} / {kind}",fill="white")
        draw.line((x,y+435,x+383,y+435),fill=(100,180,100))
    sheet.save(folder/"contact.png")
    idle=Image.open(KEYS/"canonical-idle.png").convert("RGBA")
    comparisons=[]
    for i,f in enumerate(frames):
        pair=Image.new("RGBA",(384,208));pair.paste(idle,(0,0));pair.paste(f,(192,0))
        comparisons.append(pair)
    save_preview(comparisons,[140]*8,folder/"idle-comparison.gif",display_size=(768,416))
    edges=[]
    for index,(left,right) in enumerate(PAIRS):
        middle=2*index+2
        triple=[keys[left-1],new[middle],keys[right-1]]
        save_contact(triple,folder/f"pair-{middle:02d}.png",columns=3)
        save_preview(triple,[450]*3,folder/f"pair-{middle:02d}.gif")
        # Alpha overlay is QA only; never used as an animation frame.
        overlay=Image.new("RGB",(384,208),(35,38,44))
        for side,(a,b) in enumerate(zip(triple,triple[1:])):
            old=np.array(a)[:,:,3]>0;next_=np.array(b)[:,:,3]>0
            rgb=np.zeros((208,192,3),dtype=np.uint8);rgb[:]=(35,38,44)
            rgb[old&~next_]=(225,100,60);rgb[next_&~old]=(50,210,210);rgb[old&next_]=(210,210,210)
            overlay.paste(Image.fromarray(rgb),(side*192,0))
        overlay.resize((768,416),Image.Resampling.NEAREST).save(folder/f"pair-{middle:02d}-overlay.png")
        boxes=[f.getbbox() for f in triple]
        height=[b[3]-b[1] for b in boxes]
        edges.append({"keyFrom":left,"newFrame":middle,"keyTo":right,
                      "heights":height,"outsideNeighbourHeight":max(0,min(height[0],height[2])-height[1],height[1]-max(height[0],height[2])),
                      "visualReview":"PENDING"})
    adj=[]
    for i in range(8):
        a=np.array(frames[i]);b=np.array(frames[(i+1)%8])
        adj.append({"from":i+1,"to":(i+1)%8+1,"changedPixels":int(np.any(a!=b,axis=2).sum())})
    report={"status":"SELF_REVIEW_PENDING","userApproval":"PENDING","runtimeIntegrated":False,
        "frameCount":8,"cell":[192,208],"strip":[1536,208],"durationMs":[140]*8,
        "keyFramesPixelIdentical":all(frames[2*i].tobytes()==keys[i].tobytes() for i in range(4)),
        "newFrameMetrics":metrics,"pairs":edges,"adjacent":adj,
        "allBaselines":[f.getbbox()[3]-1 for f in frames],
        "allHeights":[f.getbbox()[3]-f.getbbox()[1] for f in frames],
        "processing":"One common isotropic NN scale for all four generated drawings; integer/native registration via belt and sole; alpha threshold128, hidden RGB zero. Approved key pixels copied unchanged. No motion tweening or anatomy warping.",
        "livePlayback":"NOT_VERIFIED","appTest":"NOT_TESTED"}
    (folder/"validation.json").write_text(json.dumps(report,indent=2)+"\n")
    return report


if __name__=="__main__":
    print(json.dumps(build(),indent=2))
