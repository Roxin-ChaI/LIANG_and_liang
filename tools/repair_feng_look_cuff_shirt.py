"""Separate moving cuff from stationary shirt with existing garment pixels.

This is a review candidate only. No atlas installation or image synthesis.
"""
from pathlib import Path
import hashlib
import json
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.repair_feng_look_cuff import OFFSETS
from tools.repair_feng_look_hand_join import strip_cell
from tools.repair_gu_look_neck import comparison, BG

BASE = ROOT/'assets/rework/v0.1.0/feng-look-face-gaps-2026-10-27/feng-look-16.png'
OUT = ROOT/'assets/rework/v0.1.0/feng-look-cuff-shirt-separation-2026-10-27'
# Screen-left forearm's right contour, traced on front-facing canonical pixels.
EDGES = (80,80,79,79,79,79,79,79,80,80,80,80)


def derive(strip):
    donor = np.array(strip_cell(strip,0))
    frames, records = [], []
    for i, offset in enumerate(OFFSETS):
        old = np.array(strip_cell(strip,i)); new = old.copy(); sources = {}
        if offset:
            for y, edge in zip(range(82,94), EDGES):
                delta = round(offset*(94-y)/12)
                if not delta:
                    continue
                if delta < 0:
                    # A narrow navy/shadow separation follows the cuff instead
                    # of extending the white shirt into the moving forearm.
                    end = min(edge, edge+delta+(1 if y == 82 else 2))
                    for x in range(edge+delta+1,end+1):
                        source = (edge,y) if x == end else (72,84)
                        new[y,x] = donor[source[1],source[0]]
                        sources[x,y] = source
                # The shirt is behind the forearm: its folds do not translate
                # with the cuff. These columns never contain skin or cuff.
                for x in range(82,85):
                    new[y,x] = donor[y,x]
                    sources[x,y] = (x,y)
        changed = np.any(old != new,axis=2)
        records.append([{'xy':[int(x),int(y)],
                         'source_frame':0,'source_xy':list(sources[x,y])}
                        for y,x in zip(*np.where(changed))])
        frames.append(Image.fromarray(new))
    return frames, records


def build(output=OUT):
    output.mkdir(parents=True,exist_ok=True)
    base = Image.open(BASE).convert('RGBA')
    frames, records = derive(base)
    strip = Image.new('RGBA',base.size)
    detail, full = [], []
    contact = Image.new('RGB',(1536,1776),BG)
    draw = ImageDraw.Draw(contact)
    for i, frame in enumerate(frames):
        old = strip_cell(base,i); label = f'{i*22.5:05.1f} deg'
        strip.paste(frame,(i*192,0)); frame.save(output/f'look-{i*225:04d}.png')
        mask = np.any(np.array(old)!=np.array(frame),axis=2)
        Image.fromarray(mask.astype('uint8')*255).save(output/f'difference-{i:02d}.png')
        detail.append(comparison(old,frame,(55,65,100,103),8,label))
        full.append(comparison(old,frame,label=label))
        large = frame.resize((384,416),Image.Resampling.NEAREST)
        x,y = i%4*384,i//4*444
        contact.paste(large,(x,y+28),large.getchannel('A'))
        draw.text((x+8,y+8),label,fill=(30,30,30))
    strip.save(output/'feng-look-16.png'); contact.save(output/'contact-light.png')
    for name, boards in [('cuff-light-preview',detail),('look-light-preview',full)]:
        boards[0].save(output/f'{name}.gif',save_all=True,append_images=boards[1:],
                       duration=400,loop=0,disposal=2,optimize=False)
    for page in range(4):
        sheet = Image.new('RGB',(detail[0].width,detail[0].height*4),BG)
        for j in range(4):sheet.paste(detail[page*4+j],(0,j*detail[0].height))
        sheet.save(output/f'cuff-comparison-{page+1}.png')
    report = {'status':'PENDING_USER_REVIEW','installed':False,
              'base':str(BASE.relative_to(ROOT)),
              'base_sha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),
              'method':'local existing-pixel cuff/shirt layer separation',
              'protected':'all skin, alpha, head, neck, shoulders, cuff white pixels and all pixels outside x74..84/y82..93',
              'frames':[{'angle':i*22.5,'changed_pixels':len(r),'edits':r}
                        for i,r in enumerate(records)]}
    (output/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    return frames


if __name__ == '__main__':
    build()
