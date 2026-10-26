"""Fill traced alpha gaps only; preserve every existing opaque RGBA pixel.

Base: the local cuff repair. No rejected upper-body composition is used.
The down-right spectacle cut crosses row 46; the down-left neck has enclosed
cutout holes. Use exact source/shadow colors without moving existing artwork.
"""
from pathlib import Path
import hashlib
import json
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.repair_feng_look_hand_join import strip_cell
from tools.repair_gu_look_neck import cell, comparison, BG

BASE = ROOT/'assets/rework/v0.1.0/feng-look-cuff-repair-2026-10-26/feng-look-16.png'
SOURCE = ROOT/'assets/builds/feng/spritesheet.webp'
OUT = ROOT/'assets/rework/v0.1.0/feng-look-face-gaps-2026-10-27'
# Missing pixels also absent from the original alpha; individually inspected.
# Values name existing neighboring pixels in the SAME frame, not a new color.
FALLBACK = {
    3:{(77,55):(77,54)}, 5:{(107,58):(106,58)},
    9:{(102,53):(102,52),(103,53):(104,53)},
    10:{(103,53):(104,53)}, 11:{(100,54):(101,54)},
}


def neck_holes(p):
    alpha = Image.fromarray(p[:,:,3]).copy()
    ImageDraw.floodfill(alpha,(0,0),128)
    holes = np.array(alpha) == 0
    scope = np.zeros((208,192),bool); scope[45:68,74:108] = True
    return holes & scope


def eye_samples(i):
    if i == 5:
        return {(x,45):(116,44) for x in range(111,117)}
    if i in (6,7):
        return {(x,46):((x,45) if x<112 else (112,47))
                for x in range(104 if i==6 else 105,113)}
    return {}


def derive(base, source):
    frames, records = [], []
    for i in range(16):
        old = np.array(strip_cell(base,i)); p = old.copy()
        src = np.array(cell(source,i)); edits = []
        def fill(x,y,color,kind,origin,sx,sy):
            if old[y,x,3] != 0 or color[3] != 255:
                raise ValueError(f'Not a missing pixel / invalid donor: {i}, {x}, {y}')
            p[y,x] = color
            edits.append({'xy':[int(x),int(y)],'kind':kind,'source':origin,
                          'source_xy':[int(sx),int(sy)]})
        for y,x in zip(*np.where(neck_holes(old))):
            if src[y,x,3] == 255:
                fill(x,y,src[y,x],'neck/collar alpha hole','original same direction',x,y)
            elif (x,y) in FALLBACK.get(i,{}):
                sx,sy = FALLBACK[i][x,y]
                fill(x,y,old[sy,sx],'neck contour continuation','base same frame',sx,sy)
            else:
                raise ValueError(f'Unreviewed neck gap {i}: {(x,y)}')
        for (x,y),(sx,sy) in eye_samples(i).items():
            fill(x,y,old[sy,sx],'spectacle/face alpha cut','base same frame',sx,sy)
        frames.append(Image.fromarray(p)); records.append(edits)
    return frames, records


def save_gif(path, frames):
    frames[0].save(path,save_all=True,append_images=frames[1:],
                   duration=360,loop=0,disposal=2,optimize=False)


def build(output=OUT):
    output.mkdir(parents=True,exist_ok=True)
    base = Image.open(BASE).convert('RGBA'); source = Image.open(SOURCE).convert('RGBA')
    frames,records = derive(base,source)
    strip = Image.new('RGBA',(3072,208)); full=[]; detail=[]
    contact = Image.new('RGB',(1536,1776),BG); draw=ImageDraw.Draw(contact)
    for i,frame in enumerate(frames):
        old = strip_cell(base,i)
        frame.save(output/f'look-{i*225:04d}.png');strip.paste(frame,(i*192,0))
        delta = np.any(np.array(old)!=np.array(frame),axis=2)
        Image.fromarray(delta.astype('uint8')*255).save(output/f'difference-{i:02d}.png')
        label=f'{i*22.5:05.1f} deg'
        full.append(comparison(old,frame,label=label))
        detail.append(comparison(old,frame,(64,28,120,74),6,label))
        x,y=i%4*384,i//4*444
        zoom=frame.resize((384,416),Image.Resampling.NEAREST)
        contact.paste(zoom,(x,y+28),zoom.getchannel('A'))
        draw.text((x+8,y+8),label,fill=(30,30,30))
    strip.save(output/'feng-look-16.png');contact.save(output/'contact-light.png')
    save_gif(output/'look-light-preview.gif',full)
    save_gif(output/'face-light-preview.gif',detail)
    save_gif(output/'down-right-eyes.gif',[detail[i] for i in (4,5,6,7,8,7,6,5)])
    save_gif(output/'down-left-neck.gif',[detail[i] for i in (8,9,10,11,12,11,10,9)])
    for page in range(4):
        sheet=Image.new('RGB',(detail[0].width,detail[0].height*4),BG)
        for j in range(4):sheet.paste(detail[page*4+j],(0,j*detail[0].height))
        sheet.save(output/f'face-comparison-{page+1}.png')
    report={'status':'PENDING_USER_REVIEW','installed':False,
            'base':str(BASE.relative_to(ROOT)),
            'source_hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (BASE,SOURCE)},
            'method':'fill explicitly scoped transparent holes only, exact existing RGBA colors',
            'protected':'ALL previously opaque pixels, hands, repaired cuff, shoulders, pose and direction order',
            'observed':'135/157.5-degree eye cut is an exterior-connected transparent row; left-down neck has enclosed alpha holes',
            'not_claimed':'No new character design or runtime QA; awaiting visual approval',
            'frames':[{'angle':i*22.5,'filled_pixels':len(e),'edits':e} for i,e in enumerate(records)]}
    (output/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    return frames


if __name__=='__main__':build()
