#!/usr/bin/env python3
"""Behavioral checks for scan geometry, typography and source-only artwork.

Uses generated content, not a copyrighted specimen or network model download.
Run in the optional enhanced runtime.
"""
import argparse
import json
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import rapid_ocr
import scan_reconstruction as scan


def write(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')


def checks(work):
    faces=scan.font_faces()
    choices=[f for f in faces if 'en' in f['languages'] and not f.get('bold')]
    assert choices,'Install an available test font or provide a supported OS font'
    face=next((f for f in choices if 'Serif' in f['family'] or 'Times' in f['family']),choices[0])
    font=ImageFont.truetype(face['path'],40,index=face.get('index',0))
    image=Image.new('RGB',(600,800),'white');draw=ImageDraw.Draw(image)
    draw.rounded_rectangle((45,110,555,340),radius=20,fill='#d7e5ef')
    draw.text((75,150),'Original serif baseline',font=font,fill='#252525')
    # Original icon artwork, spatially separated from the text.
    draw.ellipse((460,220,520,280),fill='#d7e5ef',outline='#222222',width=4)
    draw.ellipse((476,237,481,242),fill='#222222');draw.ellipse((498,237,503,242),fill='#222222')
    draw.arc((477,243,504,264),0,180,fill='#222222',width=3)
    draw.ellipse((80,370,120,410),fill='#808080')
    numfont=ImageFont.truetype(face['path'],22,index=face.get('index',0))
    draw.text((94,374),'1',font=numfont,fill='white')
    draw.rectangle((135,355,205,425),fill='#eeeeee');draw.ellipse((150,370,190,410),fill='white')
    draw.text((161,374),'8',font=numfont,fill='#222222')
    for x in (400,424,448):draw.rectangle((x,380,x+18,398),outline='#777777',width=1)
    ref=work/'references/00001.png';ref.parent.mkdir(parents=True);image.save(ref)
    page={'page':1,'width':300,'height':400,'rotation':0,'kind':'scan','status':'draft',
          'blocks':[{'text':'Original serif baseline','bbox':[35,70,260,110],
                     'font_size':30,'source':'ocr','language':'en','confidence':.99}],
          'shapes':[],'images':[],'text':'Original serif baseline','warnings':[],
          'review':{k:False for k in ('text','layout','fonts','languages')}}
    page['blocks'].append({'text':'1','bbox':[44,187,57,205],'font_size':12,'source':'ocr','language':'en','confidence':.99})
    page['blocks'].append({'text':'8','bbox':[79,187,91,205],'font_size':12,'source':'ocr','language':'en','confidence':.99})
    write(work/'pages/00001.json',page);(work/'site').mkdir()
    result=scan.enhance(work,[1],write)
    revised=json.loads((work/'pages/00001.json').read_text())
    assert result['status']=='draft' and revised['blocks'][0]['font_size']<25
    assert revised['blocks'][0]['font_family']==face['family'],revised['blocks'][0]
    assert revised['blocks'][0]['text']==page['text']
    assert revised['blocks'][1]['color']=='#fff','white source numeral was recolored dark'
    assert revised['blocks'][2]['color']!='#fff','black source numeral was recolored white'
    assert (work/'work/enhance-backups/00001.json').exists()
    # Flat panel rebuilt; the lettering is never converted into a glyph path.
    assert any(s.get('fill')!='none' for s in revised['shapes'])
    assert not any(revised['review'].values())
    assert any(' a ' in s['path'] for s in revised['shapes']),'source number disk missing'
    assert sum(s.get('width')==.4 for s in revised['shapes'])>=3,'empty answer boxes missing'
    assert all(s.get('generated_by')=='scan-refine-v1' for s in revised['shapes'])
    # A source-reviewed icon crop must reproduce its source pixels exactly.
    crop=scan.crop_artwork(work,1,[229,109,261,141],[], 'Compared synthetic source icon',True,write)
    assert crop['reviewed'] and crop['role']=='illustration'
    with Image.open(work/'site'/crop['file']) as got:
        assert np.array_equal(np.array(got),np.array(image.convert('RGBA').crop((458,218,522,282))))
    try:scan.crop_artwork(work,1,[30,70,265,115],[], 'not enough to override real text',True,write)
    except ValueError as exc:assert 'intersects_text' in str(exc)
    else:raise AssertionError('A paragraph was allowed to masquerade as artwork')
    try:scan.crop_artwork(work,1,[0,0,300,400],[], '',False,write)
    except ValueError:pass
    else:raise AssertionError('A page facsimile was accepted')
    # Explicit transparent exclusions preserve labels as Unicode, not baked pixels.
    with_hole=scan.crop_artwork(work,1,[30,65,270,120],[[30,65,270,120]],'Test text exclusion',True,write)
    with Image.open(work/'site'/with_hole['file']) as got:assert np.array(got)[:,:,3].max()==0
    assert json.loads((work/'pages/00001.json').read_text())['blocks'][0]['text']==page['text']
    # High-confidence Japanese must not be displaced by a false Korean pass.
    c=lambda t,x:[t,.99,[[x,0],[x+9,0],[x+9,10],[x,10]]]
    chosen=rapid_ocr.choose_segments('日本語', [c('日',0),c('本',10),c('語',20)],.99,
                                  '한글', [c('한',0),c('글',10)],.8)
    assert len(chosen)==1 and chosen[0][0]=='日本語'
    assert rapid_ocr.supported(['ja','en','vi'])
    assert rapid_ocr.language('Đính kèm tiếng Việt')=='vi'
    # Mixed lines retain the genuine Japanese prefix and a separate Korean suffix.
    chosen=rapid_ocr.choose_segments('意味/早',[c('意',0),c('味',10),c('/',20),c('早',40)],.8,
                                  '의미',[c('의',40),c('미',50)],.95)
    assert [s[0] for s in chosen]==['意味/','의미']
    # Previously crashing ARM/OpenCV resize geometry must survive in the pinned runtime.
    import cv2
    resized=cv2.resize(np.zeros((2376,1836,3),dtype='uint8'),(1824,2368))
    assert resized.shape==(2368,1824,3)
    # A native child exit must remain a recoverable failure in the caller.
    import ocr_worker
    worker=ocr_worker.Worker();worker.process.kill();worker.process.wait(timeout=5)
    try:worker.call({'operation':'recognize'},timeout=2)
    except (RuntimeError,OSError):pass
    else:raise AssertionError('Terminated native worker was accepted')
    finally:worker.close()
    return {'status':'passed','checks':['source font and baseline fitting','editable original palette panel',
            'no review auto-approval','original page backup','pixel-identical isolated source crop',
            'reject paragraph crop','reject whole-page raster','transparent text exclusion keeps Unicode',
            'Japanese/Korean conflict handling','mixed-language suffix separation','native resize regression','native OCR crash isolation','number disks','grouped empty answer boxes']}


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path);a=p.parse_args()
    if a.out:a.out.mkdir(parents=True,exist_ok=True);result=checks(a.out.resolve())
    else:
        with tempfile.TemporaryDirectory(prefix='scan-reconstruction-') as tmp:result=checks(Path(tmp))
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
