"""Read-only formal drag/Idle comparison, with native pixels retained."""
from pathlib import Path
import hashlib,json
from PIL import Image,ImageDraw,ImageOps

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/drag-rework/v0.1.0/evidence'

def frame(a,row,index):
    return a.crop((192*index,208*row,192*(index+1),208*(row+1)))

def run():
    OUT.mkdir(parents=True,exist_ok=True);report={}
    for form in ('gu','feng'):
        source=ROOT/f'assets/builds/{form}/spritesheet.webp'; before=hashlib.sha256(source.read_bytes()).hexdigest()
        atlas=Image.open(source).convert('RGBA');idle=frame(atlas,0,0)
        right=[frame(atlas,1,i) for i in range(8)];left=[frame(atlas,2,i) for i in range(8)]
        mirror=[ImageOps.mirror(a).tobytes()==b.tobytes() for a,b in zip(right,left)]
        sheet=Image.new('RGBA',(4*384,5*446),(35,37,42,255));draw=ImageDraw.Draw(sheet)
        items=[('CANONICAL IDLE',idle)]+[(f'RIGHT {i+1:02d}',im) for i,im in enumerate(right)]+[(f'LEFT {i+1:02d}',im) for i,im in enumerate(left)]
        for i,(label,im) in enumerate(items):
            x=i%4*384;y=i//4*446
            draw.text((x+6,y+8),label,fill='white');sheet.alpha_composite(im.resize((384,416),Image.Resampling.NEAREST),(x,y+30))
        sheet.save(OUT/f'{form}-idle-drag-contact.png')
        records=[]
        for direction,frames in [('right',right),('left',left)]:
            preview=[]
            for label,im in [('IDLE',idle)]+[(f'{direction} {i+1:02d}',im) for i,im in enumerate(frames)]+[('IDLE',idle)]:
                canvas=Image.new('RGBA',(384,446),(35,37,42,255));ImageDraw.Draw(canvas).text((8,8),label,fill='white')
                canvas.alpha_composite(im.resize((384,416),Image.Resampling.NEAREST),(0,30));preview.append(canvas.convert('RGB'))
            preview[0].save(OUT/f'{form}-{direction}-with-idle.gif',save_all=True,append_images=preview[1:],duration=[500]+[120]*7+[220,500],loop=0,disposal=2)
            for i,im in enumerate(frames):
                records.append({'direction':direction,'frame':i+1,'alphaBbox':im.getchannel('A').getbbox(),
                  'baseline':im.getchannel('A').getbbox()[3]-1,
                  'rgbaSha256':hashlib.sha256(im.tobytes()).hexdigest(),
                  'nextFrameChangedPixels':sum(a!=b for a,b in zip(im.get_flattened_data(),frames[(i+1)%8].get_flattened_data()))})
        assert hashlib.sha256(source.read_bytes()).hexdigest()==before
        report[form]={'sourceSha256':before,'leftEqualsSameOrderRightMirror':mirror,'frames':records,
          'sourceModified':False,'visualVerdict':'USER_REPORTED_FAIL_REQUIRES_ART_REWORK',
          'warning':'Alpha bbox is not anatomical head/shoulder measurement; pixel differences do not prove gait continuity.'}
    (OUT/'inventory.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({f:{'mirrorMatches':sum(r['leftEqualsSameOrderRightMirror']),'baselines':sorted(set(x['baseline'] for x in r['frames']))} for f,r in report.items()}))

if __name__=='__main__':run()
