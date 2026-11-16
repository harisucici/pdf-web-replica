"""Source-derived scan reconstruction helpers, not a finished-layout certificate.

All coordinates come from the current PDF. Geometry/style candidates remain
editable; no page numbers, specimen text, mascot templates or book dimensions
are shared between documents.
"""
import glob
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path


def dependencies():
    try:
        import cv2
        import numpy as np
        from PIL import Image, ImageFont, ImageDraw
    except ImportError as exc:
        raise ValueError('enhanced_runtime_missing: bootstrap.py --enhanced-ocr --venv work/.pdf-web-env') from exc
    return cv2, np, Image, ImageFont, ImageDraw


def box_overlap(a, b):
    return max(0, min(a[2], b[2])-max(a[0], b[0])) * max(0, min(a[3], b[3])-max(a[1], b[1]))


def font_faces(config=None):
    """Discover installed fonts; do not copy proprietary OS fonts into the site."""
    if config:
        faces = json.loads(Path(config).read_text(encoding='utf-8'))
        if not isinstance(faces, list):
            raise ValueError('font_config_must_be_a_list')
        for f in faces:
            if not Path(f['path']).expanduser().is_file():
                raise ValueError('font_file_not_found:' + f['path'])
        return faces
    faces = []
    def add(path, family, langs, index=0, bold=False):
        if Path(path).is_file():
            faces.append({'path': str(path), 'index': index, 'family': family,
                          'languages': langs, 'bold': bold})
    for pat, family, index, bold in [
        ('*W3.ttc', 'Hiragino Kaku Gothic ProN', 2, False),
        ('*W6.ttc', 'Hiragino Kaku Gothic ProN', 2, True),
        ('*明朝*.ttc', 'Hiragino Mincho ProN', 0, False),
        ('*明朝*.ttc', 'Hiragino Mincho ProN', 2, True)]:
        for p in glob.glob('/System/Library/Fonts/' + pat):
            add(p, family, ['ja', 'zh'], index, bold)
    for name, family, langs, index, bold in [
        ('Hiragino Sans GB.ttc', 'Hiragino Sans GB', ['zh'], 0, False),
        ('Hiragino Sans GB.ttc', 'Hiragino Sans GB', ['zh'], 2, True),
        ('AppleSDGothicNeo.ttc', 'Apple SD Gothic Neo', ['ko'], 0, False),
        ('AppleSDGothicNeo.ttc', 'Apple SD Gothic Neo', ['ko'], 6, True),
        ('Supplemental/Arial.ttf', 'Arial', ['en'], 0, False),
        ('Supplemental/Arial Bold.ttf', 'Arial', ['en'], 0, True),
        ('Supplemental/Times New Roman.ttf', 'Times New Roman', ['en'], 0, False),
        ('Supplemental/Times New Roman Bold.ttf', 'Times New Roman', ['en'], 0, True),
        ('Supplemental/Songti.ttc', 'Songti SC', ['zh'], 6, False)]:
        add('/System/Library/Fonts/' + name, family, langs, index, bold)
    win=Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'
    for filename,family,langs in [('arial.ttf','Arial',['en']),('times.ttf','Times New Roman',['en']),('YuGothR.ttc','Yu Gothic',['ja']),('meiryo.ttc','Meiryo',['ja'])]:
        add(win/filename,family,langs)
    if shutil.which('fc-match'):
        for family, langs in [('Noto Sans CJK JP', ['ja', 'zh', 'ko']),
                              ('Noto Serif CJK JP', ['ja', 'zh']), ('Liberation Sans', ['en']), ('Liberation Serif', ['en'])]:
            r = subprocess.run(['fc-match', '-f', '%{file}\n%{family}\n%{index}', family], capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                fields=r.stdout.strip().splitlines()
                if len(fields)>=2:add(fields[0],fields[1].split(',')[0],langs,int(fields[2]) & 0xffff if len(fields)>2 and fields[2].isdigit() else 0)
    return faces


@lru_cache(maxsize=64)
def load_font(path, index):
    from PIL import ImageFont
    return ImageFont.truetype(str(Path(path).expanduser()), 64, index=index)


def ink_box(gray, box, white=False, background=255):
    cv2, np, _, _, _ = dependencies()
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(gray.shape[1], x1), min(gray.shape[0], y1)
    crop = gray[y0:y1, x0:x1]
    if not crop.size:
        return None
    ink = crop > min(245,max(180,background+25)) if white else crop < min(180,background-25)
    rows = ink.sum(axis=1)
    good = rows > max(1, rows.max()*.04)
    runs, start = [], None
    for i, value in enumerate(np.r_[good, False]):
        if value and start is None:
            start = i
        if not value and start is not None:
            runs.append((int(rows[start:i].sum()), start, i))
            start = None
    if not runs:
        return None
    _, top, bottom = max(runs)
    ys, xs = np.where(ink[top:bottom])
    return [x0+int(xs.min()), y0+top, x0+int(xs.max())+1, y0+bottom]


def fit_text(block, gray, sx, sy, faces):
    cv2, np, Image, _, ImageDraw = dependencies()
    source_box=block.get('ocr_bbox',block['bbox']) if block.get('source')=='ocr' else block['bbox']
    box = [v*(sx if i % 2 == 0 else sy) for i, v in enumerate(source_box)]
    x, y, x1, y1 = [int(round(v)) for v in box]
    crop = gray[max(0,y):y1, max(0,x):x1]
    if not crop.size:
        return block
    pad=max(2,round(min(sx,sy)))
    rx,ry,rx1,ry1=max(0,x-pad),max(0,y-pad),min(gray.shape[1],x1+pad),min(gray.shape[0],y1+pad)
    ring=gray[ry:ry1,rx:rx1];rm=np.ones(ring.shape,dtype=bool)
    rm[max(0,y-ry):y1-ry,max(0,x-rx):x1-rx]=False
    background=float(np.median(ring[rm])) if np.any(rm) else float(np.percentile(crop,90))
    lighter=int(np.count_nonzero(crop.astype('float32')>background+20))
    darker=int(np.count_nonzero(crop.astype('float32')<background-20))
    white=lighter>max(3,darker*1.2)
    bb = ink_box(gray, box, white,background)
    if bb is None:
        return block
    x, y, x1, y1 = bb
    text = block['text']; lang = block.get('language', 'ja').split('-')[0]
    lang = {'jpn':'ja','eng':'en','kor':'ko','chi':'zh'}.get(lang, lang)
    candidates = [f for f in faces if lang in f.get('languages', []) or (lang=='vi' and 'en' in f.get('languages', []))]
    if not candidates:
        return {**block, 'font_fit_pending': 'no_installed_font_for:' + lang}
    actual = gray[y:y1, x:x1].astype('float32')
    bg=background
    target=np.clip((actual-bg)/max(20,255-bg) if white else (bg-actual)/max(20,bg-30),0,1)
    # Underlines are geometry, not extra height or extra-bold glyph strokes.
    target[np.mean(target > .6, axis=1) > .85] = 0
    target = cv2.GaussianBlur(target, (3,3), .55)
    choices = []
    for face in candidates:
        f = load_font(face['path'], face.get('index', 0))
        m = f.getbbox(text, anchor='ls'); ww, hh = max(1,m[2]-m[0]), max(1,m[3]-m[1])
        canvas = Image.new('L', (ww, hh))
        ImageDraw.Draw(canvas).text((-m[0],-m[1]), text, font=f, fill=255, anchor='ls')
        rendered = cv2.resize(np.array(canvas).astype('float32')/255, (x1-x,y1-y), interpolation=cv2.INTER_AREA)
        error = float(np.mean((cv2.GaussianBlur(rendered,(3,3),.55)-target)**2))
        choices.append((error, face, f, m))
    error, face, f, m = min(choices, key=lambda c:c[0])
    factor = (y1-y)/max(1,m[3]-m[1])
    return {**block, 'bbox':[x/sx,y/sy,x1/sx,y1/sy],
            'origin':[(x-m[0]*factor)/sx,(y-m[1]*factor)/sy],
            'font_size':64*factor/sy, 'font_family':face['family'],
            'bold':face.get('bold',False), 'color':'#fff' if white else '#272321',
            'advance':((x1-x)+(f.getlength(text)-(m[2]-m[0]))*factor)/sx,
            'font_match_error':round(error,5), 'font_substitution':True}


def source_regions(rgb, blocks, width, height):
    cv2, np, _, _, _ = dependencies()
    ih, iw = rgb.shape[:2]; sx, sy = iw/width, ih/height
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    textmask = np.zeros((ih,iw), 'uint8')
    for b in blocks:
        x,y,x1,y1=[int(round(v*(sx if i%2==0 else sy))) for i,v in enumerate(b['bbox'])]
        textmask[max(0,y):max(0,y1),max(0,x):max(0,x1)]=1
    # Quantized source colors separate dark-brown headers from gray body panels.
    keys=(rgb[:,:,0]//16).astype('int32')*256+(rgb[:,:,1]//16)*16+rgb[:,:,2]//16
    common=np.argsort(np.bincount(keys.ravel(),minlength=4096))[-16:]
    regions=[]
    for key in common:
        mask=(keys==key).astype('uint8')
        count,ll,stats,_=cv2.connectedComponentsWithStats(mask,8)
        for k in range(1,count):
            x,y,w,h,area=stats[k]
            if area<iw*ih*.0015 or w/sx<25 or h/sy<12:continue
            if x==0 or y==0 or x+w>=iw or y+h>=ih:continue
            pixels=(ll[y:y+h,x:x+w]==k)
            # Foreground glyphs/counters cannot become traced vector content.
            if float(np.mean(textmask[y:y+h,x:x+w][pixels]))>.90:continue
            if area/(w*h)<.08:continue # Thin connected borders are not solid fills.
            cs,_=cv2.findContours(pixels.astype('uint8'),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
            pts=cv2.approxPolyDP(max(cs,key=cv2.contourArea),max(1,min(sx,sy)*.35),True).reshape(-1,2)+[x,y]
            # Flat panels have long straight sides. Circular mascots and free-form
            # artwork stay out of this vector route and must be source-cropped.
            lengths=[];straight=[]
            for a,b in zip(pts, np.roll(pts,-1,axis=0)):
                dx,dy=abs(float(b[0]-a[0])),abs(float(b[1]-a[1]));length=math.hypot(dx,dy)
                lengths.append(length);straight.append(length if min(dx,dy)<max(1,max(dx,dy)*.06) else 0)
            if sum(straight)/max(1,sum(lengths))<.80:continue
            color=np.median(rgb[y:y+h,x:x+w][pixels],axis=0).astype('int')
            path='M '+' L '.join(f'{a/sx:.4f} {b/sy:.4f}' for a,b in pts)+' Z'
            regions.append((area,{'path':path,'fill':'#%02x%02x%02x'%tuple(color),'stroke':'none','width':0,'generated_by':'scan-refine-v1'}))
    shapes=[s for _,s in sorted(regions,key=lambda r:-r[0])]
    ink=(gray<190).astype('uint8')*255
    for horizontal in (True,False):
        kernel=(max(3,round(18*sx)),1) if horizontal else (1,max(3,round(24*sy)))
        mask=cv2.morphologyEx(ink,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_RECT,kernel))
        cnt,ll,st,_=cv2.connectedComponentsWithStats(mask,8)
        for k in range(1,cnt):
            x,y,w,h,area=st[k]
            if (h/sy>1.8 if horizontal else w/sx>1.8):continue
            bb=[x/sx,y/sy,(x+w)/sx,(y+h)/sy]
            # Large lettering contains long strokes too; never trace those strokes.
            if any(box_overlap(bb,b['bbox'])>max(.1,(bb[2]-bb[0])*(bb[3]-bb[1]))*.8
                   and (not horizontal or bb[1]<b['bbox'][3]-.12*(b['bbox'][3]-b['bbox'][1])) for b in blocks):continue
            path=f'M {x/sx:.4f} {(y+h/2)/sy:.4f} h {w/sx:.4f}' if horizontal else f'M {(x+w/2)/sx:.4f} {y/sy:.4f} v {h/sy:.4f}'
            shapes.append({'path':path,'fill':'none','stroke':'#777','width':h/sy if horizontal else w/sx,'generated_by':'scan-refine-v1'})
    return shapes


def enhance(out, selected, write_json, font_config=None, refine_ruby=False):
    cv2, np, Image, _, _ = dependencies()
    out=Path(out);faces=font_faces(font_config);report=[]
    for no in selected:
        try:
            path=out/'pages'/f'{no:05}.json';d=json.loads(path.read_text(encoding='utf-8'))
            if d['kind'] in ('native','blank'):
                report.append({'page':no,'status':'preserved_native_or_blank'});continue
            if d.get('web_layout'):
                report.append({'page':no,'status':'manual_layout_preserved','next':'update visible layout and blocks together'});continue
            ref=out/'references'/f'{no:05}.png'
            with Image.open(ref) as im:rgb=np.array(im.convert('RGB'))
            sx,sy=rgb.shape[1]/d['width'],rgb.shape[0]/d['height'];gray=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY)
            backup=out/'work'/'enhance-backups'/f'{no:05}.json'
            if not backup.exists():write_json(backup,d)
            import scan_primitives
            original=scan_primitives.split_number_prefixes(d['blocks']);d['blocks']=original;shapes=source_regions(rgb,original,d['width'],d['height'])
            d['blocks']=[fit_text(b,gray,sx,sy,faces) if b.get('source') not in ('native','form') else b for b in original]
            if refine_ruby and any(b.get('language','').startswith('ja') for b in d['blocks']):
                import ruby_refinement
                d['blocks'],d['ruby_refinement']=ruby_refinement.refine(rgb,d['blocks'],d['width'],d['height'],out/'work')
                d['blocks']=[fit_text(b,gray,sx,sy,faces) if b.get('source')=='rapidocr-ruby' else b for b in d['blocks']]
            primitives,candidates=scan_primitives.analyze(rgb,original,d['width'],d['height'],out/'site')
            existing=d.get('images',[]);known={im.get('file') for im in existing}
            d['images']=existing+[im for im in candidates if im['file'] not in known and not any(old.get('reviewed') and box_overlap(im['bbox'],old['bbox'])>.8*(im['bbox'][2]-im['bbox'][0])*(im['bbox'][3]-im['bbox'][1]) for old in existing if old.get('bbox'))]
            d['shapes']=shapes+primitives+[s for s in d.get('shapes',[]) if s.get('generated_by')!='scan-refine-v1']
            d['text']='\n'.join(b['text'] for b in sorted(d['blocks'],key=lambda b:(round(b['bbox'][1],1),b['bbox'][0])))
            d['review']={k:False for k in ('text','layout','fonts','languages')};d['review_signatures']={}
            d.setdefault('warnings',[]).append('source_geometry_and_font_candidates_require_visual_review')
            entry={'page':no,'status':'draft','text_runs':len(d['blocks']),'generated_regions':len(shapes),
                   'font_faces':sorted({b.get('font_family') for b in d['blocks'] if b.get('font_family')}),
                   'next':['source-crop isolated artwork','verify ruby and script conflicts','capture and compare current page']}
            write_json(path,d);report.append(entry)
        except Exception as exc:
            report.append({'page':no,'status':'needs_attention','error':str(exc)})
            if 'd' in locals() and d.get('page')==no:
                d.setdefault('remaining_differences',[]).append('Scan enhancement failed: '+str(exc))
                write_json(path,d)
    write_json(out/'enhancement-report.json',{'pages':report,'font_candidates':faces,
               'note':'Font fitting and region detection are candidates. Artwork approval and full source review remain required.'})
    return {'pages':len(report),'status':'draft','errors':sum(r['status']=='needs_attention' for r in report),'report':str(out/'enhancement-report.json')}


def crop_artwork(out, page, bbox, holes, note, reviewed, write_json):
    from PIL import Image, ImageDraw
    import image_policy
    out=Path(out);path=out/'pages'/f'{page:05}.json';d=json.loads(path.read_text(encoding='utf-8'))
    b=list(map(float,bbox))
    if not all(math.isfinite(v) for v in b) or not(0<=b[0]<b[2]<=d['width'] and 0<=b[1]<b[3]<=d['height']):
        raise ValueError('artwork_bbox_outside_page')
    holes=[list(map(float,h)) for h in holes]
    for h in holes:
        if not all(math.isfinite(v) for v in h) or not(b[0]<=h[0]<h[2]<=b[2] and b[1]<=h[1]<h[3]<=b[3]):
            raise ValueError('text_exclusion_outside_artwork_crop')
    for block in d['blocks']:
        bb=block['bbox'];area=box_overlap(bb,b)
        if area>1 and not any(box_overlap(bb,h)>=area-.1 for h in holes):
            raise ValueError('artwork_crop_intersects_text: '+block['text'][:80]+'; crop more tightly or explicitly exclude this text region')
    if reviewed and not note.strip():raise ValueError('reviewed_artwork_requires_source_comparison_note')
    descriptor={'bbox':b,'role':'illustration' if reviewed else 'illustration_candidate','reviewed':reviewed,
                'source_page':page,'source_bbox':b,'excluded_text_bboxes':holes,'review_note':note}
    flags,_=image_policy.scan_flags(d.get('images',[])+[descriptor],d['width'],d['height'])
    if any(flags):raise ValueError('artwork_crop_rejected_by_page_raster_geometry_guard')
    ref=out/'references'/f'{page:05}.png'
    with Image.open(ref) as im:
        im=im.convert('RGBA');sx,sy=im.width/d['width'],im.height/d['height']
        x,y,x1,y1=[round(v*(sx if i%2==0 else sy)) for i,v in enumerate(b)]
        art=im.crop((x,y,x1,y1))
        for h in holes:
            hh=[round(v*(sx if i%2==0 else sy)) for i,v in enumerate(h)]
            ImageDraw.Draw(art).rectangle((hh[0]-x,hh[1]-y,hh[2]-x-1,hh[3]-y-1),fill=(0,0,0,0))
        ident=hashlib.sha256(art.tobytes()+json.dumps(b).encode()).hexdigest()[:20]
        filename=f'illustrations/crop-{ident}.png';dest=out/'site'/filename;dest.parent.mkdir(exist_ok=True);art.save(dest)
    descriptor['file']=filename
    previous=[im for im in d.get('images',[]) if not(im.get('role')=='illustration_candidate' and im.get('bbox') and box_overlap(im['bbox'],b)>.7*(im['bbox'][2]-im['bbox'][0])*(im['bbox'][3]-im['bbox'][1]))]
    d['images']=previous+[descriptor]
    d['review']={k:False for k in ('text','layout','fonts','languages')};d['review_signatures']={}
    write_json(path,d)
    return descriptor
