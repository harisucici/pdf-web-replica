"""Re-read literal small source annotations; never obtain readings from a lexicon."""
import re
from pathlib import Path


def refine(rgb, blocks, width, height, cache):
    import cv2
    import numpy as np
    import rapid_ocr
    ih,iw=rgb.shape[:2];sx,sy=iw/width,ih/height
    gray=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY)
    mask=(gray<155).astype('uint8')*255
    for kernel in ((max(3,round(18*sx)),1),(1,max(3,round(24*sy)))):
        rule=cv2.morphologyEx(mask,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_RECT,kernel))
        mask[rule>0]=0
    bodies,requests=[],[]
    for i,b in enumerate(blocks):
        bb=[round(v*(sx if j%2==0 else sy)) for j,v in enumerate(b['bbox'])];x,y,x1,y1=bb
        mask[max(0,y):max(0,y1+1),max(0,x):max(0,x1+1)]=0
        if b.get('language','').startswith('ja') and (y1-y)/sy>6:bodies.append(bb)
        if b.get('language','').startswith('ja') and (y1-y)/sy<6 and (b.get('confidence') or 0)<.94:
            requests.append({'bbox':bb,'index':i,'before':b['text']})
    cnt,ll,st,_=cv2.connectedComponentsWithStats(mask,8);parts=[]
    for k in range(1,cnt):
        x,y,w,h,area=st[k]
        if not(1<w/sx<32 and 1.3<h/sy<7.8 and area>3):continue
        if any(0<=y-a[3]<6*sy and a[0]-3*sx<x<a[2]+3*sx for a in bodies):
            parts.append([int(x),int(y),int(x+w),int(y+h)])
    groups=[]
    for bb in sorted(parts,key=lambda b:(b[1],b[0])):
        match=None
        for g in groups:
            gap=max(0,max(bb[0],g[0])-min(bb[2],g[2]))
            ov=min(bb[3],g[3])-max(bb[1],g[1])
            if gap<4*sx and ov>min(bb[3]-bb[1],g[3]-g[1])*.25:match=g;break
        if match is None:groups.append(bb)
        else:match[:]=[min(match[0],bb[0]),min(match[1],bb[1]),max(match[2],bb[2]),max(match[3],bb[3])]
    requests += [{'bbox':bb,'index':None,'before':''} for bb in groups
                 if 2<(bb[3]-bb[1])/sy<7.8 and 2<(bb[2]-bb[0])/sx<90]
    if not requests:return blocks,[]
    crops=[]
    for r in requests:
        x,y,x1,y1=r['bbox'];a=gray[max(0,y-3):min(ih,y1+3),max(0,x-3):min(iw,x1+3)]
        lo,hi=np.percentile(a,[2,85]);a=np.clip((a.astype('float32')-lo)*255/max(30,hi-lo),0,255).astype('uint8')
        crops.append(cv2.cvtColor(cv2.resize(a,None,fx=3,fy=3,interpolation=cv2.INTER_CUBIC),cv2.COLOR_GRAY2RGB))
    readings=rapid_ocr.recognize_crops(crops,cache)
    result=list(blocks);ledger=[]
    for i,r in enumerate(requests):
        variants=[tuple(readings['main'][i]),tuple(readings['japanese'][i])]
        valid=[v for v in variants if re.fullmatch('[ぁ-ゖァ-ヺー・ \u3000]+',v[0] or '')]
        entry={**r,'readings':[{'text':t,'confidence':s} for t,s in variants],'adopted':False}
        if valid:
            text,confidence=max(valid,key=lambda v:v[1])
            old=(blocks[r['index']].get('confidence') or 0) if r['index'] is not None else 0
            if confidence>=.88 and confidence>=old+.03:
                bb=[v/(sx if j%2==0 else sy) for j,v in enumerate(r['bbox'])]
                item={'text':text,'bbox':bb,'font_size':max(1,bb[3]-bb[1]),'confidence':confidence,
                      'language':'ja','source':'rapidocr-ruby','role':'ruby','angle':0,'advance':bb[2]-bb[0]}
                if r['index'] is None:result.append(item)
                else:result[r['index']]=item
                entry['adopted']=True
        ledger.append(entry)
    return result,ledger
