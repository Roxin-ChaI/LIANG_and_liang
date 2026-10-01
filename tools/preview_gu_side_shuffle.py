"""Four-frame motion review; originals intact, raw and alignment-disclosed GIFs."""
from pathlib import Path
import hashlib,json
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'assets/rework/v0.1.0/gu-drag-side-shuffle-keyposes-2026-10-01'
SOURCE=BASE/'source-preview.png'
SHA='4325836d4f6327964a72783de919d7aa25698d411b71bf407097511b93e3deab'

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def write_gif(panels,path,duration):
    # One shared palette for all frames avoids palette changes between frames.
    joined=Image.new('RGB',(panels[0].width*4,panels[0].height))
    for i,panel in enumerate(panels):joined.paste(panel.convert('RGB'),(i*panel.width,0))
    palette=joined.quantize(colors=256,dither=Image.Dither.NONE)
    encoded=[p.convert('RGB').quantize(palette=palette,dither=Image.Dither.NONE) for p in panels]
    encoded[0].save(path,save_all=True,append_images=encoded[1:],duration=duration,loop=0,disposal=2,optimize=False)
    with Image.open(path) as gif:
        assert gif.n_frames==4
        assert gif.info['loop']==0
        for i in range(4):gif.seek(i);assert gif.info['duration']==duration

def build(out=BASE/'qa-motion'):
    if out.exists():raise ValueError('refuse to overwrite existing preview')
    assert digest(SOURCE)==SHA
    source=Image.open(SOURCE).convert('RGBA');assert source.size==(2172,724)
    frames=[source.crop((i*543,0,(i+1)*543,724)) for i in range(4)]
    out.mkdir(parents=True)
    aligned=[];raw=[];records=[]
    for i,frame in enumerate(frames):
        # Alpha threshold locates the head only. Never threshold saved pixels.
        box=frame.getchannel('A').crop((0,0,543,280)).point(lambda v:255 if v>=128 else 0).getbbox()
        assert box
        center=(box[0]+box[2])/2
        dx=round(432-center);dy=32
        assert 0<=dx and dx+543<=864 and dy+724<=784
        native=Image.new('RGBA',(864,784),(40,42,47,255))
        native.alpha_composite(frame,(dx,dy))
        panel=native.resize((432,392),Image.Resampling.NEAREST)
        ImageDraw.Draw(panel).text((8,8),f'{i+1:02d}/04  ALIGNED PREVIEW',fill='white')
        aligned.append(panel)
        unaligned=Image.new('RGBA',(544,752),(40,42,47,255))
        unaligned.alpha_composite(frame,(0,28))
        panel_raw=unaligned.resize((272,376),Image.Resampling.NEAREST)
        ImageDraw.Draw(panel_raw).text((5,4),f'{i+1:02d}/04  RAW POSITION',fill='white')
        raw.append(panel_raw)
        frame.save(out/f'source-cell-{i+1:02d}.png')
        assert Image.open(out/f'source-cell-{i+1:02d}.png').tobytes()==frame.tobytes()
        records.append({'number':i+1,'sourceCrop':[i*543,0,(i+1)*543,724],
          'headBandAlpha128Bounds':box,'previewIntegerOffset':[dx,dy],
          'rgbaSha256':hashlib.sha256(frame.tobytes()).hexdigest()})
    write_gif(aligned,out/'keyposes-4-frames.gif',250)
    write_gif(aligned,out/'keyposes-4-frames-slow.gif',500)
    write_gif(raw,out/'keyposes-4-frames-raw-position.gif',250)
    contact=Image.new('RGBA',(864,784),(40,42,47,255))
    for i,panel in enumerate(aligned):contact.paste(panel,((i%2)*432,(i//2)*392))
    contact.save(out/'contact-sheet.png')
    assert digest(SOURCE)==SHA
    report={'status':'PENDING_USER_REVIEW_TECHNICAL_SOURCE_GATE_STILL_FAIL',
      'frameCount':4,'order':[1,2,3,4],'frameDurationMs':250,'slowFrameDurationMs':500,
      'loop':'forever','timingPurpose':'keypose review only, not final eight-frame animation timing',
      'sourceSha256':SHA,'sourceUnchanged':True,'nativeCropPixelsPreserved':True,
      'commonDisplayScale':0.5,'resampling':'NEAREST','alignment':'integer head-band centering, constant vertical offset; no per-frame scaling',
      'rawPositionPreviewIncluded':True,'sourceAlphaModified':False,
      'gifBackground':'opaque dark gray, to avoid GIF binary-alpha damage; palette conversion for previews only',
      'runtimeReady':False,'artApproved':False,'frames':records}
    (out/'preview.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return report

if __name__=='__main__':print(json.dumps(build(),ensure_ascii=False,indent=2))
