"""Prepare exact Idle layout and Gu motion references for Look art review."""
from pathlib import Path
import sys
import json
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.build_animation_review import cell as frame

OUT=ROOT/"assets/rework/v0.1.0/feng-look-r6-2026-10-20"


def assert_unapproved():
    status=OUT/"review-status.json"
    if status.exists() and json.loads(status.read_text()).get("generatorLocked"):
        raise RuntimeError("Approved Feng Look R6 is frozen; use a new version directory")


def gu_references():
    # Retain the exact review input without depending on unrelated uncommitted
    # repair atlases. The saved sheet was made with an exact 2x NN enlargement.
    sheet=Image.open(OUT/"gu-motion-reference.png").convert("RGBA")
    refs=[]
    for i in range(4):
        x=(i%2)*512+64;y=(i//2)*512+48
        refs.append(sheet.crop((x,y,x+384,y+416)).resize((192,208),Image.Resampling.NEAREST))
    return refs


def build():
    assert_unapproved()
    OUT.mkdir(parents=True,exist_ok=True)
    feng=Image.open(ROOT/"assets/builds/feng/spritesheet.webp").convert("RGBA")
    refs=gu_references()
    idle=frame(feng,0,0)
    idle.save(OUT/"canonical-idle.png")
    template=Image.new("RGBA",(1024,1024))
    motion=Image.new("RGBA",(1024,1024))
    for i,direction in enumerate([0,4,8,12]):
        position=((i%2)*512+64,(i//2)*512+48)
        template.paste(idle.resize((384,416),Image.Resampling.NEAREST),position)
        ref=refs[i]
        motion.paste(ref.resize((384,416),Image.Resampling.NEAREST),position)
    template.save(OUT/"edit-target-four-idles.png")
    motion.save(OUT/"gu-motion-reference.png")


if __name__=="__main__":build()
