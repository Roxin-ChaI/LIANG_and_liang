"""Candidate-only removal of traced donor-jaw remnants; no resampling or repaint."""
from pathlib import Path
import hashlib
import json
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.repair_reviewed_actions import head_mask

SOURCE = ROOT / 'assets/rework/v0.1.0/approved-actions-integration-2026-10-23/gu.webp'
HEAD_SOURCE = ROOT / 'assets/builds/gu/spritesheet.webp'
OUT = ROOT / 'assets/rework/v0.1.0/gu-look-neck-cleanup-2026-10-25'
BG = (245, 243, 238)
# Traced original front-facing jaw, excluding the blue collar at y>=76.
JAW_SPANS = [(70,73,114),(71,73,113),(72,73,112),(73,75,111),
             (74,75,111),(75,77,109),(76,79,106),(77,79,106),(78,80,106)]
# Short horizontal spurs in the directional source itself, visually inspected
# on a light background. Retain the innermost dark contour pixel.
SPURS = {9: [(72,106,109)], 10: [(73,105,109)],
         12: [(77,75,78)], 15: [(75,78,82)]}


def cell(atlas, i):
    x, y = i % 8 * 192, (9 + i // 8) * 208
    return atlas.crop((x, y, x + 192, y + 208))


def derive(atlas, original):
    donor = cell(atlas, 0)
    d = np.array(donor)
    jaw = np.zeros((208,192), bool)
    for y, left, right in JAW_SPANS:
        jaw[y,left:right] = True
    jaw &= ~(np.array(head_mask(donor, 'gu')) > 0)
    frames, masks = [], []
    for i in range(16):
        p = np.array(cell(atlas, i))
        own = np.array(head_mask(cell(original, i), 'gu')) > 0
        erase = jaw & ~own & np.all(p == d, axis=2) & (p[:,:,3] > 0)
        if i == 0:
            erase[:] = False
        for y, left, right in SPURS.get(i, []):
            erase[y,left:right] = True
        rgb = p[:,:,:3].astype(int)
        skin = (rgb[:,:,0]>140)&(rgb[:,:,0]>rgb[:,:,1]+10)&(rgb[:,:,1]>rgb[:,:,2]+8)
        clothing = rgb[:,:,2]>rgb[:,:,0]+8
        erase &= ~(skin | clothing)
        p[erase] = 0
        frames.append(Image.fromarray(p))
        masks.append(erase)
    return frames, masks


def comparison(before, after, crop=(0,0,192,208), scale=2, label=''):
    w, h = (crop[2]-crop[0])*scale, (crop[3]-crop[1])*scale
    board = Image.new('RGB', (w*2,h+28), BG)
    draw = ImageDraw.Draw(board)
    for col, im in enumerate((before,after)):
        detail = im.crop(crop).resize((w,h), Image.Resampling.NEAREST)
        board.paste(detail, (col*w,28), detail.getchannel('A'))
        draw.text((col*w+8,8), f'{label} / {("BEFORE","CANDIDATE")[col]}', fill=(30,30,30))
    return board


def build(output=OUT):
    output.mkdir(parents=True, exist_ok=True)
    atlas = Image.open(SOURCE).convert('RGBA')
    original = Image.open(HEAD_SOURCE).convert('RGBA')
    frames, masks = derive(atlas, original)
    full, details, reports = [], [], []
    for i, (im, mask) in enumerate(zip(frames,masks)):
        im.save(output / f'look-{i*225:04d}.png')
        Image.fromarray(mask.astype('uint8')*255).save(output / f'difference-{i:02d}.png')
        label = f'{i*22.5:05.1f} deg'
        full.append(comparison(cell(atlas,i),im,label=label))
        details.append(comparison(cell(atlas,i),im,(55,55,135,102),6,label))
        ys, xs = np.where(mask)
        reports.append({'direction':i*22.5,'removed_pixels':int(mask.sum()),
                        'removed_coordinates_xy':list(map(list,zip(xs.tolist(),ys.tolist())))})
    for name, boards in [('look-light-preview',full),('neck-light-preview',details)]:
        boards[0].save(output/f'{name}.gif',save_all=True,append_images=boards[1:],
                       duration=220,loop=0,disposal=2,optimize=False)
    for page in range(4):
        sheet = Image.new('RGB',(details[0].width,details[0].height*4),BG)
        for row in range(4):
            sheet.paste(details[page*4+row],(0,row*details[0].height))
        sheet.save(output/f'neck-comparison-{page+1}.png')
    strip = Image.new('RGBA',(192*16,208))
    for i, im in enumerate(frames):
        strip.paste(im,(i*192,0))
    strip.save(output/'gu-look-16.png')
    report = {'status':'PENDING_USER_REVIEW','scope':'Gu Look neck only; candidate not installed',
              'method':'explicit donor jaw/spur pixel removal; all retained RGBA bytes unchanged',
              'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
              'head_source_sha256':hashlib.sha256(HEAD_SOURCE.read_bytes()).hexdigest(),
              'frames':reports}
    (output/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    return frames, masks


if __name__ == '__main__':
    build()
