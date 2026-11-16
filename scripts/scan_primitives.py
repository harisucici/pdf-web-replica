"""Recover discrete badges/frames and source artwork candidates, never approval."""
import hashlib
import re
from pathlib import Path


def overlap(a,b):
    return max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))


def split_number_prefixes(blocks):
    result=[]
    for b in blocks:
        m=re.match(r'^([0-9]{1,4})(?=[A-Za-zＡ-Ｚぁ-ヿ一-龯])',b['text'])
        chars=b.get('characters',[])
        if not m or len(chars)<=len(m[1]):result.append(b);continue
        cut=len(m[1]);a=chars[:cut];z=chars[cut:]
        if z[0]['bbox'][0]-a[-1]['bbox'][2] < .2*(b['bbox'][3]-b['bbox'][1]):
            result.append(b);continue
        for text,items,lang in [(m[1],a,'en'),(b['text'][cut:],z,b.get('language','ja'))]:
            boxes=[c['bbox'] for c in items]
            bb=[min(v[0] for v in boxes),min(v[1] for v in boxes),max(v[2] for v in boxes),max(v[3] for v in boxes)]
            result.append({**b,'text':text,'bbox':bb,'characters':items,'language':lang})
    return result


def analyze(rgb,blocks,width,height,site):
    import cv2
    import numpy as np
    gray=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY);ih,iw=gray.shape;sx,sy=iw/width,ih/height
    shapes=[];candidates=[];numeric=[b for b in blocks if re.fullmatch(r'\d{1,4}',b['text'])]
    # Number disks use a geometric circle plus existing Unicode, including white
    # disks on gray answer panels and white numerals on medium-gray question disks.
    for iswhite in (False,True):
        mask=(gray>250 if iswhite else gray<190).astype('uint8')
        cnt,ll,st,_=cv2.connectedComponentsWithStats(mask,8)
        for k in range(1,cnt):
            x,y,w,h,area=st[k];ww,hh=w/sx,h/sy
            if not(8<ww<36 and 8<hh<36 and .8<ww/hh<1.2 and area/(w*h)>.35):continue
            bb=[x/sx,y/sy,(x+w)/sx,(y+h)/sy]
            numbers=[b for b in numeric if overlap(bb,b['bbox'])>1]
            if not numbers:continue
            cs,_=cv2.findContours((ll[y:y+h,x:x+w]==k).astype('uint8'),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
            c=max(cs,key=cv2.contourArea)
            if cv2.contourArea(c)/(w*h)<.65 or cv2.arcLength(c,True)==0:continue
            circularity=4*np.pi*cv2.contourArea(c)/(cv2.arcLength(c,True)**2)
            if circularity<.7:continue
            color=np.median(rgb[y:y+h,x:x+w][ll[y:y+h,x:x+w]==k],axis=0).astype('int')
            cx,cy=(x+w/2)/sx,(y+h/2)/sy;rx,ry=w/(2*sx),h/(2*sy)
            shapes.append({'path':f'M {cx-rx} {cy} a {rx} {ry} 0 1 0 {2*rx} 0 a {rx} {ry} 0 1 0 {-2*rx} 0',
                           'fill':'#%02x%02x%02x'%tuple(color),'stroke':'none','width':0,'generated_by':'scan-refine-v1'})
    # Closed rectangular vocabulary/grammar labels and empty checkbox groups.
    cs,_=cv2.findContours((gray<200).astype('uint8'),cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
    squares=[];frames=[]
    for c in cs:
        x,y,w,h=cv2.boundingRect(c);ww,hh=w/sx,h/sy
        if not(5<ww<150 and 5<hh<32):continue
        if len(cv2.approxPolyDP(c,max(.7,min(sx,sy)*.5),True))!=4 or cv2.contourArea(c)/(w*h)<.8:continue
        inner=gray[y+3:y+h-3,x+3:x+w-3]
        if .75<ww/hh<1.25 and max(ww,hh)<15 and inner.size and np.mean(inner<180)<.08:
            if not any(abs(x-a[0])<3 and abs(y-a[1])<3 for a in squares):squares.append([x,y,w,h])
        elif ww>12 and ww/hh>1.2:
            if not any(abs(x-a[0])<3 and abs(y-a[1])<3 for a in frames):frames.append([x,y,w,h])
    groups=[]
    for b in sorted(squares,key=lambda b:(b[1],b[0])):
        g=next((g for g in groups if abs(g[0][1]-b[1])<2*sy and min(abs(b[0]-(a[0]+a[2])) for a in g)<5*sx),None)
        if g is None:groups.append([b])
        else:g.append(b)
    checks=[b for group in groups if len(group)>=2 for b in group]
    for x,y,w,h in frames+checks:
        shapes.append({'path':f'M {x/sx} {y/sy} h {w/sx} v {h/sy} h {-w/sx} Z',
                       'fill':'none','stroke':'#777','width':.4,'generated_by':'scan-refine-v1'})
    # Repeated circular mascots are candidates only. Their PNGs retain the source
    # details; the agent must inspect/correct false OCR and explicitly approve.
    ink=(gray<185).astype('uint8');cnt,ll,st,_=cv2.connectedComponentsWithStats(ink,8)
    for k in range(1,cnt):
        x,y,w,h,area=st[k];ww,hh=w/sx,h/sy
        if not(18<ww<48 and 18<hh<48 and .8<ww/hh<1.2 and area/(w*h)<.5):continue
        cm=(ll[y:y+h,x:x+w]==k).astype('uint8')
        cs,_=cv2.findContours(cm,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE);c=max(cs,key=cv2.contourArea)
        perimeter=cv2.arcLength(c,True)
        if perimeter==0 or cv2.contourArea(c)/(w*h)<.65 or 4*np.pi*cv2.contourArea(c)/(perimeter**2)<.65:continue
        bb=[max(0,(x-2)/sx),max(0,(y-2)/sy),min(width,(x+w+2)/sx),min(height,(y+h+2)/sy)]
        if any(overlap(bb,b['bbox'])>.6*(bb[2]-bb[0])*(bb[3]-bb[1]) for b in blocks):continue
        px=[max(0,x-2),max(0,y-2),min(iw,x+w+2),min(ih,y+h+2)]
        crop=rgb[px[1]:px[3],px[0]:px[2]];ident=hashlib.sha256(crop.tobytes()).hexdigest()[:20]
        file=f'illustrations/candidate-{ident}.png';dest=Path(site)/file;dest.parent.mkdir(parents=True,exist_ok=True)
        from PIL import Image
        Image.fromarray(crop).save(dest)
        candidates.append({'file':file,'bbox':bb,'source_bbox':bb,'role':'illustration_candidate','reviewed':False,'generated_by':'scan-refine-v1'})
    return shapes,candidates
