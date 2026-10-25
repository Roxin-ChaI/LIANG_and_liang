"""Restore coherent directional hand/wrist/cuff pixels across the old y=74 cut."""
from pathlib import Path
import hashlib
import json
import sys

import numpy as np
from PIL import Image, ImageFilter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.repair_feng_look_neck_cutout import ORIGINAL, skin_mask
from tools.repair_gu_look_neck import cell, comparison, BG

PREVIOUS=ROOT/'assets/rework/v0.1.0/feng-look-neck-cutout-2026-10-25/feng-look-16.png'
OUT=ROOT/'assets/rework/v0.1.0/feng-look-hand-join-2026-10-25'
UNCHANGED=(0,8,12)  # Inspected cardinal hands already continuous.


def strip_cell(strip,i):
    return strip.crop((i*192,0,(i+1)*192,208))


def hand_mask(old,source):
    # Capture both the displaced upper hand and obsolete front-facing lower
    # palm; include the contour, wrist and cuff so neither leaves an orphan.
    seed=skin_mask(old)|skin_mask(source)
    area=np.zeros((208,192),bool);area[64:85,60:95]=True
    seed &= area
    # Binary selection dilation only. No RGBA resampling or smoothing.
    mask=np.asarray(Image.fromarray(seed.astype('uint8')*255).filter(ImageFilter.MaxFilter(7)))>0
    bounds=np.zeros((208,192),bool);bounds[68:90,60:98]=True
    return mask & bounds


def derive(previous,original):
    frames,masks=[],[]
    for i in range(16):
        old=np.array(strip_cell(previous,i));source=np.array(cell(original,i))
        mask=hand_mask(old,source)
        if i in UNCHANGED:mask[:]=False
        p=old.copy();p[mask]=source[mask]
        frames.append(Image.fromarray(p));masks.append(mask)
    return frames,masks


def build(output=OUT):
    output.mkdir(parents=True,exist_ok=True)
    previous=Image.open(PREVIOUS).convert('RGBA');original=Image.open(ORIGINAL).convert('RGBA')
    frames,masks=derive(previous,original)
    strip=Image.new('RGBA',(3072,208));full=[];details=[];records=[]
    for i,(im,mask) in enumerate(zip(frames,masks)):
        old=strip_cell(previous,i);delta=np.any(np.array(old)!=np.array(im),axis=2)
        ys,xs=np.where(delta)
        records.append({'angle':i*22.5,'changed_pixels':int(delta.sum()),
                        'source':'same direction, same coordinates in original Feng atlas',
                        'changed_xy':list(map(list,zip(xs.tolist(),ys.tolist())))})
        im.save(output/f'look-{i*225:04d}.png');strip.paste(im,(i*192,0))
        Image.fromarray(delta.astype('uint8')*255).save(output/f'difference-{i:02d}.png')
        Image.fromarray(mask.astype('uint8')*255).save(output/f'hand-selection-{i:02d}.png')
        label=f'{i*22.5:05.1f} deg'
        full.append(comparison(old,im,label=label))
        details.append(comparison(old,im,(55,45,115,105),6,label))
    strip.save(output/'feng-look-16.png')
    for name,boards in [('look-light-preview',full),('hand-light-preview',details)]:
        boards[0].save(output/f'{name}.gif',save_all=True,append_images=boards[1:],
                       duration=320,loop=0,disposal=2,optimize=False)
    for page in range(4):
        sheet=Image.new('RGB',(720,1552),BG)
        for j in range(4):sheet.paste(details[page*4+j],(0,j*388))
        sheet.save(output/f'hand-comparison-{page+1}.png')
    report={'status':'PENDING_USER_REVIEW','installed':False,
            'cause':'head_mask ended at y=74 and selected raised-hand skin: directional upper hand spliced onto donor lower hand',
            'method':'copy complete local directional lower palm, wrist and cuff across y=74, not slit fill',
            'previous_sha256':hashlib.sha256(PREVIOUS.read_bytes()).hexdigest(),
            'original_sha256':hashlib.sha256(ORIGINAL.read_bytes()).hexdigest(),
            'known_remaining':'body/shoulder light edge pixels not addressed here',
            'frames':records}
    (output/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    return frames,masks


if __name__=='__main__':build()
