"""Local cuff repair on the pre-rejection candidate, never on upper-join.

Keep the head, directional hand, shoulders and lower arm in place. Reuse the
same candidate's front-facing sleeve/cuff pixels to connect displaced wrists.
No image generation, color interpolation, whole-body transform or deployment.
"""
from pathlib import Path
import hashlib
import json
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.repair_feng_look_hand_join import strip_cell
from tools.repair_gu_look_neck import comparison, BG

BASE = ROOT / 'assets/rework/v0.1.0/feng-look-hand-join-2026-10-25/feng-look-16.png'
OUT = ROOT / 'assets/rework/v0.1.0/feng-look-cuff-repair-2026-10-26'
# Traced cuff-edge offsets, NOT head/hand translation. Each row returns to
# the stationary sleeve by y94. All sampling uses integer source coordinates.
OFFSETS = (0,0,1,1,0,1,1,1,0,-3,-4,-6,0,-6,-6,-4)


def blue_cloth(p):
    rgb = p[:,:,:3].astype(int)
    return ((rgb[:,:,2] > rgb[:,:,0]+12) & (rgb[:,:,2] > rgb[:,:,1]+8)
            & (rgb[:,:,2] < 150) & (p[:,:,3] == 255))


def derive(strip):
    donor = np.array(strip_cell(strip,0))
    frames, provenance = [], []
    for i, offset in enumerate(OFFSETS):
        old = np.array(strip_cell(strip,i)); result = old.copy()
        scope = np.zeros((208,192),bool); scope[68:90,60:98] = True
        restore = scope & blue_cloth(old) & blue_cloth(donor)
        if i in (0,8,12):
            restore[:] = False  # Already connected cardinal cuffs stay exact.
        result[restore] = donor[restore]
        sources = {(int(x),int(y)):(int(x),int(y)) for y,x in zip(*np.where(restore))}
        for y in range(82,94):
            delta = round(offset*(94-y)/12)
            if not delta:
                continue
            left = 70 if y < 85 else 72
            if y >= 88:
                left = 75
            for x in range(min(left,left+delta),85):
                result[y,x] = donor[y,x-delta]
                sources[x,y] = (x-delta,y)
        changed = np.any(result != old,axis=2)
        records = [{'xy':[int(x),int(y)], 'source_frame':0,
                    'source_xy':list(sources[int(x),int(y)])}
                   for y,x in zip(*np.where(changed))]
        frames.append(Image.fromarray(result)); provenance.append(records)
    return frames, provenance


def build(output=OUT):
    output.mkdir(parents=True,exist_ok=True)
    strip = Image.open(BASE).convert('RGBA')
    frames, edits = derive(strip)
    result = Image.new('RGBA',(3072,208))
    full, detail = [], []
    contact = Image.new('RGB',(1536,1776),BG)
    draw = ImageDraw.Draw(contact)
    for i, frame in enumerate(frames):
        old = strip_cell(strip,i)
        result.paste(frame,(192*i,0)); frame.save(output/f'look-{i*225:04d}.png')
        change = np.any(np.array(old) != np.array(frame),axis=2)
        Image.fromarray(change.astype('uint8')*255).save(output/f'difference-{i:02d}.png')
        label = f'{i*22.5:05.1f} deg'
        full.append(comparison(old,frame,label=label))
        detail.append(comparison(old,frame,(55,55,105,100),8,label))
        x,y = i%4*384, i//4*444
        enlarged = frame.resize((384,416),Image.Resampling.NEAREST)
        contact.paste(enlarged,(x,y+28),enlarged.getchannel('A'))
        draw.text((x+8,y+8),label,fill=(30,30,30))
    result.save(output/'feng-look-16.png'); contact.save(output/'contact-light.png')
    for name, boards in [('look-light-preview',full),('cuff-light-preview',detail)]:
        boards[0].save(output/f'{name}.gif',save_all=True,append_images=boards[1:],
                       duration=320,loop=0,disposal=2,optimize=False)
    for page in range(4):
        sheet = Image.new('RGB',(detail[0].width,detail[0].height*4),BG)
        for j in range(4):sheet.paste(detail[page*4+j],(0,j*detail[0].height))
        sheet.save(output/f'cuff-comparison-{page+1}.png')
    report = {
        'status':'PENDING_USER_REVIEW', 'installed':False,
        'base':str(BASE.relative_to(ROOT)),
        'base_sha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),
        'rejected_not_used':'feng-look-upper-join-2026-10-25 / 3696422',
        'method':'local integer pixel placement at cuff edge; existing frame-0 garment colors only',
        'protected':'all skin, head/neck, shoulders above y68, pixels outside x60..97, all y>=94',
        'qa':'16 static directions inspected; color provenance and protected regions tested; human animation approval still required',
        'frames':[{'angle':i*22.5,'cuff_offset':OFFSETS[i],'changed_pixels':len(e),'edits':e}
                  for i,e in enumerate(edits)]}
    (output/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    return frames


if __name__ == '__main__':
    build()
