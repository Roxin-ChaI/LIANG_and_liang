"""Read-only frame/ROI audit of rejected R2 candidates; no art repair."""
from pathlib import Path
import sys
import json
import hashlib
import numpy as np
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.rework_action_candidates import OUT, SOURCE
from tools.repair_reviewed_actions import frame, head_mask, skin_mask
from tools.build_animation_review import save_preview


def compare(stages, labels, roi, path, lines=()):
    w,h=(roi[2]-roi[0])*4,(roi[3]-roi[1])*4
    out=Image.new("RGB",(w*len(stages),(h+28)*len(stages[0])),(60,27,61))
    draw=ImageDraw.Draw(out)
    for col,(images,label) in enumerate(zip(stages,labels)):
        for i,im in enumerate(images):
            x,y=col*w,i*(h+28)
            crop=im.crop(roi).resize((w,h),Image.Resampling.NEAREST)
            out.paste(crop,(x,y+28),crop.getchannel("A"))
            draw.text((x+4,y+4),f"{i+1:02d} {label}",fill="white")
            for line in lines:
                yy=y+28+(line-roi[1])*4
                draw.line((x,yy,x+w-1,yy),fill=(255,90,140),width=1)
    out.save(path)


def trace(target):
    formal=Image.open(ROOT/"assets/builds/feng/spritesheet.webp").convert("RGBA")
    first=Image.open(SOURCE/"feng.webp").convert("RGBA")
    original=[frame(formal,9+i//8,i%8) for i in range(16)]
    r1=[frame(first,9+i//8,i%8) for i in range(16)]
    r2=[Image.open(OUT/"feng-look-edge"/f"{i+1:02d}.png").convert("RGBA") for i in range(16)]
    compare([original,r1,r2],["FORMAL","R1 shoulder join","R2 fringe only"],(62,44,113,94),target/"look-stage-trace.png",(74,))
    with Image.open(target/"look-stage-trace.png") as grouped:
        for i in range(4):
            grouped.crop((0,i*912,grouped.width,(i+1)*912)).save(target/f"look-stage-{i*4+1:02d}-{i*4+4:02d}.png")
    records=[]
    for i,(a,b,c) in enumerate(zip(original,r1,r2)):
        arrays=[np.array(im) for im in (a,b,c)]
        roi=(slice(57,92),slice(70,108))
        change=np.any(arrays[1]!=arrays[2],axis=2)
        records.append({"frame":i+1,"degrees":i*22.5,
            "r1ToR2HandRoiChanged":int(change[roi].sum()),
            "r2DeletedSkinPixels":int((change & skin_mask(b)).sum()),
            "r1BelowY74EqualsFixedUp":b.crop((0,74,192,208)).tobytes()==r1[0].crop((0,74,192,208)).tobytes(),
            "headMaskContainsHandSkin":int(((np.array(head_mask(a,"feng"))>0)&skin_mask(a))[60:74,70:106].sum())})
    failed=[Image.open(OUT/"feng-failed-keyposes"/f"{i:02d}.png").convert("RGBA") for i in range(1,5)]
    idle=frame(first,0,0);donor=frame(first,8,2)
    compare([[idle]*4,[donor]*4,failed],["Idle base","Review donor","REJECTED composite"],(38,45,151,124),target/"failed-stage-trace.png",(71,116))
    save_preview(failed,[900]*4,target/"failed-slow-evidence.gif")
    save_preview(r2,[500]*16,target/"look-slow-evidence.gif")
    frozen={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [ROOT/"assets/builds/gu/spritesheet.webp",ROOT/"assets/builds/feng/spritesheet.webp",
                      ROOT/"standalone-app/asset-overrides.json"]}
    report={"status":"VISUAL_QA_FAIL","look":records,"failedCompositingBoundaries":[71,116],
            "failedOrdinalToPlannedRuntimeFrame":[1,4,5,8],
            "scope":"All 16 Look frames; all 4 Failed keyposes and their source layers. No new art.",
            "dynamicPlaybackObserved":"NOT_VERIFIED; slow GIF files are evidence outputs, not proof of having watched playback",
            "sourceHashes":frozen}
    (target/"trace.json").write_text(json.dumps(report,indent=2)+"\n")
    return report


def sheet(name,count,roi,destination,columns=4):
    width,height=(roi[2]-roi[0])*4,(roi[3]-roi[1])*4
    board=Image.new("RGB",(columns*width,((count+columns-1)//columns)*(height+24)),(70,30,65))
    draw=ImageDraw.Draw(board)
    for i in range(count):
        im=Image.open(OUT/name/f"{i+1:02d}.png").convert("RGBA").crop(roi)
        im=im.resize((width,height),Image.Resampling.NEAREST)
        x,y=(i%columns)*width,(i//columns)*(height+24)
        board.paste(im,(x,y+24),im.getchannel("A"))
        draw.text((x+4,y+4),f"{i+1:02d}",fill="white")
    board.save(destination)


if __name__=="__main__":
    target=OUT/"diagnosis/rejected-r2-seams"
    target.mkdir(parents=True,exist_ok=True)
    sheet("feng-look-edge",16,(62,44,113,94),target/"look-hand-all-16.png")
    sheet("feng-failed-keyposes",4,(38,45,151,124),target/"failed-torso-all-4.png",columns=2)
    result=trace(target)
    print(json.dumps({"status":result["status"],"handSkinChangedByR2":[r["r2DeletedSkinPixels"] for r in result["look"]],
                      "handRoiChangedByR2":[r["r1ToR2HandRoiChanged"] for r in result["look"]]}))
