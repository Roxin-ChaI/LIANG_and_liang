"""Scoped Feng Look neck cutout candidate; preserve all hand/body pixels."""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.repair_reviewed_actions import head_mask
from tools.repair_gu_look_neck import cell, comparison, BG

SOURCE=ROOT/'assets/rework/v0.1.0/approved-actions-integration-2026-10-23/feng.webp'
ORIGINAL=ROOT/'assets/builds/feng/spritesheet.webp'
OUT=ROOT/'assets/rework/v0.1.0/feng-look-neck-cutout-2026-10-25'
JAW_SPANS=[(45,66,111),(46,67,110),(47,68,109),(48,69,108),
           (49,70,107),(50,72,104),(51,74,104),(52,74,104),
           (53,75,104),(54,75,103)]


def skin_mask(p):
    rgb=p[:,:,:3].astype(int)
    return ((rgb[:,:,0]>110)&(rgb[:,:,0]>rgb[:,:,1]+10)
            &(rgb[:,:,1]>rgb[:,:,2]+8)&(p[:,:,3]>0))


def derive(atlas,original):
    donor=np.array(cell(atlas,0)); jaw=np.zeros((208,192),bool)
    for y,l,r in JAW_SPANS:jaw[y,l:r]=True
    jaw &= ~(np.array(head_mask(cell(atlas,0),'feng'))>0)
    frames,records=[],[]
    for i in range(16):
        old=np.array(cell(atlas,i));p=old.copy();src=np.array(cell(original,i))
        own=np.array(head_mask(cell(original,i),'feng'))>0
        cut=jaw & ~own & np.all(p==donor,axis=2)&(p[:,:,3]>0)
        rgb=p[:,:,:3].astype(int)
        cut &= ~((rgb[:,:,2]>rgb[:,:,0]+8)|skin_mask(p))
        if i==0:cut[:]=False
        p[cut]=0
        # The old skin-only compositor also cut away genuine dark hair and
        # neck shadow behind the ears. Restore only transparent pixels from
        # the matching original direction, without shifting or repainting.
        join=np.zeros((208,192),bool)
        if 1<=i<=7:join[45:58,65:85]=True
        if 9<=i<=15:join[45:58,99:116]=True
        join &= (p[:,:,3]==0)&(src[:,:,3]>0)&(src[:,:,:3].max(axis=2)<90)
        p[join]=src[join]
        changed=np.any(p!=old,axis=2)
        edits=[]
        for y,x in zip(*np.where(changed)):
            edits.append({'xy':[int(x),int(y)],
                          'operation':'restore directional hair/neck shadow' if p[y,x,3] else 'remove donor jaw remnant',
                          'source_xy':[int(x),int(y)] if p[y,x,3] else None})
        frames.append(Image.fromarray(p));records.append(edits)
    return frames,records


def build(output=OUT):
    output.mkdir(parents=True,exist_ok=True)
    atlas=Image.open(SOURCE).convert('RGBA');original=Image.open(ORIGINAL).convert('RGBA')
    frames,records=derive(atlas,original)
    strip=Image.new('RGBA',(3072,208));full=[];details=[]
    for i,im in enumerate(frames):
        im.save(output/f'look-{i*225:04d}.png');strip.paste(im,(i*192,0))
        old=cell(atlas,i);changed=np.any(np.array(im)!=np.array(old),axis=2)
        Image.fromarray(changed.astype('uint8')*255).save(output/f'difference-{i:02d}.png')
        label=f'{i*22.5:05.1f} deg'
        full.append(comparison(old,im,label=label))
        details.append(comparison(old,im,(60,35,125,85),6,label))
    strip.save(output/'feng-look-16.png')
    for name,boards in [('look-light-preview',full),('neck-light-preview',details)]:
        boards[0].save(output/f'{name}.gif',save_all=True,append_images=boards[1:],
                       duration=280,loop=0,disposal=2,optimize=False)
    for page in range(4):
        sheet=Image.new('RGB',(780,1312),BG)
        for j in range(4):sheet.paste(details[page*4+j],(0,j*328))
        sheet.save(output/f'neck-comparison-{page+1}.png')
    report={'status':'PENDING_USER_REVIEW','installed':False,
            'scope':'Feng Look external neck remnants and missing back-hair/neck shadow only',
            'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            'original_sha256':hashlib.sha256(ORIGINAL.read_bytes()).hexdigest(),
            'known_unresolved':'Existing horizontal hand seams in side-looking directions; body-edge light pixels. Not whole-Look approval.',
            'frames':[{'angle':i*22.5,'changed_pixels':len(r),'edits':r} for i,r in enumerate(records)]}
    (output/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    return frames,records


if __name__=='__main__':build()
