"""Reconnect the Gu neck using directional source pixels, without resampling."""
from pathlib import Path
import hashlib
import json
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.repair_gu_look_neck import HEAD_SOURCE, cell, comparison, BG

PREVIOUS = ROOT / 'assets/rework/v0.1.0/gu-look-neck-cleanup-2026-10-25/gu-look-16.png'
OUT = ROOT / 'assets/rework/v0.1.0/gu-look-neck-connection-2026-10-25'
# Manually bounded neck interior, below the jaw and inside the stationary
# collar. Not a silhouette dilation: external neck/jaw gaps stay transparent.
NECK_SPANS = [(79,87,103),(80,87,103),(81,87,103),(82,88,103),
              (83,89,102),(84,90,101),(85,91,100),(86,92,99),
              (87,93,99),(88,94,98),(89,95,98)]


def previous_cell(strip, i):
    return strip.crop((i*192,0,(i+1)*192,208))


def skin_mask(p):
    rgb=p[:,:,:3].astype(int)
    return ((rgb[:,:,0]>110)&(rgb[:,:,0]>rgb[:,:,1]+10)
            &(rgb[:,:,1]>rgb[:,:,2]+8)&(p[:,:,3]>0))


def derive(previous, original):
    frames, records = [], []
    for i in range(16):
        old=np.array(previous_cell(previous,i)); p=old.copy()
        source=np.array(cell(original,i)); skin=skin_mask(source)
        edits={}

        def copy_pixel(x,y,sx,sy,reason):
            p[y,x]=source[sy,sx]
            if np.array_equal(p[y,x],old[y,x]):
                edits.pop((x,y),None)
            else:
                edits[x,y]={'xy':[x,y],'source_xy':[sx,sy],'reason':reason}

        if i:
            # Restore the original same-direction neck skin, including the
            # small skin shadow lost at the previous head/body mask boundary.
            for y in range(75,90):
                for x in range(85,105):
                    if skin[y,x]:
                        copy_pixel(x,y,x,y,'directional neck skin')
            # Restore enclosed vertical shadow pixels between skin samples.
            for x in range(87,103):
                ys=np.flatnonzero(skin[74:90,x])+74
                if len(ys)>1:
                    for y in range(int(ys.min()),int(ys.max())+1):
                        if p[y,x,3]==0 and source[y,x,3]>0:
                            copy_pixel(x,y,x,y,'enclosed neck shadow')
            # Close interior cutout slits with the nearest existing skin
            # pixel on this exact row. No blending/new colors or scale warp.
            for y,left,right in NECK_SPANS:
                xs=np.flatnonzero(skin[y,85:105])+85
                if not len(xs):
                    continue
                for x in range(left,right):
                    if p[y,x,3]==0:
                        sx=int(xs[np.abs(xs-x).argmin()])
                        copy_pixel(x,y,sx,y,'neck interior slit')
        frames.append(Image.fromarray(p))
        records.append(list(edits.values()))
    return frames, records


def build(output=OUT):
    output.mkdir(parents=True,exist_ok=True)
    previous=Image.open(PREVIOUS).convert('RGBA')
    original=Image.open(HEAD_SOURCE).convert('RGBA')
    frames,records=derive(previous,original)
    full,detail=[],[]
    strip=Image.new('RGBA',(3072,208))
    for i,im in enumerate(frames):
        im.save(output/f'look-{i*225:04d}.png'); strip.paste(im,(i*192,0))
        old=previous_cell(previous,i)
        mask=np.any(np.array(old)!=np.array(im),axis=2)
        Image.fromarray(mask.astype('uint8')*255).save(output/f'difference-{i:02d}.png')
        label=f'{i*22.5:05.1f} deg'
        full.append(comparison(old,im,label=label))
        detail.append(comparison(old,im,(55,55,135,102),6,label))
    strip.save(output/'gu-look-16.png')
    for name,boards in [('look-light-preview',full),('neck-light-preview',detail)]:
        boards[0].save(output/f'{name}.gif',save_all=True,append_images=boards[1:],
                       duration=280,loop=0,disposal=2,optimize=False)
    for page in range(4):
        board=Image.new('RGB',(960,detail[0].height*4),BG)
        for j in range(4):board.paste(detail[page*4+j],(0,j*detail[0].height))
        board.save(output/f'neck-comparison-{page+1}.png')
    report={'status':'PENDING_USER_REVIEW','not_installed':True,
            'previous_sha256':hashlib.sha256(PREVIOUS.read_bytes()).hexdigest(),
            'directional_source_sha256':hashlib.sha256(HEAD_SOURCE.read_bytes()).hexdigest(),
            'frames':[{'angle':i*22.5,'changed_pixels':len(r),'edits':r} for i,r in enumerate(records)]}
    (output/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    return frames,records


if __name__=='__main__':
    build()
