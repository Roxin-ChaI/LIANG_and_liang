"""Compose a review-only README gallery from the selected release artwork."""
import hashlib
import json
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'docs/readme-preview'
MEDIA = OUT/'media'
CREAM = (246,244,238)
BLUE = (235,240,247)
INK = (32,42,58)
FONT = '/System/Library/Fonts/Supplemental/Arial.ttf'


def font(size):
    return ImageFont.truetype(FONT,size)


def card(frame, form, label):
    image = Image.new('RGB',(384,464),CREAM if form=='gu' else BLUE)
    ImageDraw.Draw(image).text((20,13),label,fill=INK,font=font(18))
    enlarged = frame.resize((frame.width*2,frame.height*2),Image.Resampling.NEAREST)
    image.paste(enlarged,(0,40),enlarged.getchannel('A'))
    return image


def gif(frames,times,path):
    assert len(frames)==len(times) and all(t%10==0 for t in times)
    # Shared palette avoids palette flicker; no dithering or frame resampling.
    sample = Image.new('RGB',(frames[0].width,frames[0].height*len(frames)))
    for i,f in enumerate(frames):sample.paste(f,(0,i*f.height))
    palette=sample.quantize(colors=256,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE)
    indexed=[f.quantize(palette=palette,dither=Image.Dither.NONE) for f in frames]
    indexed[0].save(path,save_all=True,append_images=indexed[1:],duration=times,
                    loop=0,disposal=2,optimize=False)
    with Image.open(path) as result:
        duration=0
        for i in range(result.n_frames):
            result.seek(i);duration+=result.info['duration']
        assert duration==sum(times)


def build():
    MEDIA.mkdir(parents=True,exist_ok=True)
    selected=json.loads((ROOT/'standalone-app/asset-overrides.json').read_text())
    layout=json.loads((ROOT/'runtime-patch/fixtures/transition-overlay-layout.json').read_text())
    timing=json.loads(subprocess.check_output([
        'node','--input-type=module','-e',
        "import {STATES,APPROVED_FORM_DURATIONS} from './standalone-app/animation.mjs'; console.log(JSON.stringify({STATES,APPROVED_FORM_DURATIONS}));"
    ],cwd=ROOT,text=True))
    originals={}
    def load(relative):
        p=ROOT/selected.get(relative,relative)
        originals[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
        return Image.open(p).convert('RGBA')
    atlases={f:load(f'assets/builds/{f}/spritesheet.webp') for f in ('gu','feng')}
    def cell(form,row,index):return atlases[form].crop((index*192,row*208,(index+1)*192,(row+1)*208))
    hero=Image.new('RGB',(768,464))
    hero.paste(card(cell('gu',0,0),'gu','GU / OFF-PEAK'),(0,0))
    hero.paste(card(cell('feng',0,0),'feng','FENG / PEAK'),(384,0))
    hero.save(MEDIA/'characters.png')
    animations={}
    for form in ('gu','feng'):
        for state,label in [('idle','IDLE'),('jumping','HOVER'),('running-right','MOVE RIGHT')]:
            d=timing['STATES'][state]
            durations=timing['APPROVED_FORM_DURATIONS'].get(form,{}).get(state)
            durations=durations or d.get('durations') or [d['duration']]*(d['frames']-1)+[d['lastDuration']]
            frames=[card(cell(form,d['row'],i),form,f'{form.upper()} / {label}') for i in range(d['frames'])]
            name=f'{form}-{state}.gif';gif(frames,durations,MEDIA/name)
            animations[name]={'row':d['row'],'sourceFrames':d['frames'],'durationsMs':durations}
        frames=[card(cell(form,9+i//8,i%8),form,f'{form.upper()} / LOOK') for i in range(16)]
        gif(frames,[220]*16,MEDIA/f'{form}-look.gif')
        animations[f'{form}-look.gif']={'directions':16,'previewStepMs':220,'mode':'direction sweep, not automatic runtime action'}
    transition_frames=[];transition_times=[];sequence=[]
    for form,name,count in [('gu','gu_to_feng',10),('feng','feng_to_gu',8)]:
        items=[(cell(form,0,i),32,24,t,f'{form.upper()} / IDLE',f'{form}:idle:{i}')
               for i,t in enumerate(timing['STATES']['idle']['durations'])]
        l=layout[name]
        for i in range(1,count+1):
            source=f'assets/transform-overlay/{name}/{name}_{i:02d}.png'
            frame=load(source)
            assert frame.size==(l['canvasWidth'],l['canvasHeight'])
            items.append((frame,32+l['offsetLeft'],24+l['offsetTop'],140,
                          'GU  >  FENG' if form=='gu' else 'FENG  >  GU',f'{name}:{i}'))
        for frame,x,y,t,label,identifier in items:
            canvas=Image.new('RGBA',(256,256))
            assert x>=0 and y>=0 and x+frame.width<=256 and y+frame.height<=256
            canvas.paste(frame,(x,y))
            board=Image.new('RGB',(512,552),CREAM)
            ImageDraw.Draw(board).text((22,12),label,fill=INK,font=font(20))
            doubled=canvas.resize((512,512),Image.Resampling.NEAREST)
            board.paste(doubled,(0,40),doubled.getchannel('A'))
            transition_frames.append(board);transition_times.append(t);sequence.append(identifier)
    gif(transition_frames,transition_times,MEDIA/'transformation-cycle.gif')
    animations['transformation-cycle.gif']={'sequence':sequence,'durationsMs':transition_times,
                                           'layout':'same 256x256 canvas/anchors as standalone renderer'}
    for relative,digest in originals.items():assert hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()==digest
    report={'status':'README_DRAFT_FOR_USER_REVIEW','sources':originals,'animations':animations,
            'sourceArtModified':False,'gifColorLimit':256,'gifDither':False,
            'mediaType':'selected-release asset animation previews, not screen recordings'}
    (OUT/'media-manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    body=(OUT/'README.md').read_text()
    style='''body{margin:0;background:#f6f8fa;color:#1f2328;font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
    .draft{padding:14px;text-align:center;background:#fff3cd;font-size:14px;color:#654b00}
    article{max-width:820px;margin:28px auto;padding:40px;background:#fff;border:1px solid #d1d9e0;border-radius:10px}
    h1{font-size:36px;margin:0 0 8px}h2{font-size:24px;margin:40px 0 20px;padding-bottom:8px;border-bottom:1px solid #d1d9e0}
    h3{margin:20px 0 10px}a{color:#0969da;text-decoration:none}a:hover{text-decoration:underline}img{max-width:100%;height:auto;image-rendering:pixelated}
    table{border-collapse:collapse;width:100%;margin:16px 0}th,td{border:1px solid #d1d9e0;padding:12px;vertical-align:top}th{background:#f6f8fa}
    .motion td{width:50%;text-align:center}blockquote{border-left:4px solid #d1d9e0;padding:0 16px;color:#59636e;margin:20px 0}details{margin:20px 0}summary{cursor:pointer;font-weight:600}
    @media(max-width:700px){article{padding:18px;margin:0;border:0}th,td{padding:6px}h1{font-size:28px}}'''
    (OUT/'index.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>LIANG & liang · README 视觉预览</title><style>'+style+'</style><div class="draft">README 视觉预览稿 · 待审核 · 尚未替换线上 README</div><article>'+body+'</article></html>')
    print(json.dumps({'output':str(OUT),'staticImages':1,'gifs':len(animations),'sourcesUnchanged':True}))


if __name__=='__main__':build()
