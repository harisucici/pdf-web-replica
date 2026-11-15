"""Local OCR adapters. Commands are argument arrays, never shell strings."""
import csv,io,json,os,platform,re,shutil,subprocess
from pathlib import Path
ALIASES={'en':'eng','ja':'jpn','zh':'chi_sim','zh-hant':'chi_tra','ko':'kor','ar':'ara','ru':'rus','de':'deu','fr':'fra','es':'spa','he':'heb','hi':'hin','pt':'por','it':'ita'}
APPLE={'en':'en-US','ja':'ja-JP','zh':'zh-Hans','zh-hant':'zh-Hant','ko':'ko-KR','ar':'ar-SA','ru':'ru-RU','de':'de-DE','fr':'fr-FR','es':'es-ES','pt':'pt-BR','it':'it-IT'}
def capabilities():return {'tesseract':shutil.which('tesseract'),'vision':platform.system()=='Darwin' and bool(shutil.which('swiftc'))}
def _run(cmd,timeout=180):
 r=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout)
 if r.returncode:raise RuntimeError((r.stderr or r.stdout or 'OCR failed')[-1200:])
 return r.stdout

def tesseract(image,languages,width,height):
 installed=[s.strip() for s in _run(['tesseract','--list-langs']).splitlines()[1:] if s.strip()]
 requested=[ALIASES.get(x,x) for x in languages if x!='auto']
 warnings=[]
 if not requested:
  requested=[x for x in ['eng','jpn','chi_sim','chi_tra','kor','ara','rus'] if x in installed]
  if not requested:requested=[x for x in installed if x!='osd'][:1]
  warnings.append('automatic_language_selection_requires_source_review')
 missing=[x for x in requested if x not in installed]
 if missing:warnings.append('missing_ocr_languages:'+','.join(missing))
 blocks=[]
 for lang in [x for x in requested if x in installed]:
  raw=_run(['tesseract',str(image),'stdout','-l',lang,'--psm','3','tsv']);groups={}
  for row in csv.DictReader(io.StringIO(raw),delimiter='\t'):
   text=(row.get('text') or '').strip()
   try:conf=float(row['conf'])
   except (ValueError,KeyError):continue
   if not text or conf<0:continue
   key=tuple(row[k] for k in ['block_num','par_num','line_num']);groups.setdefault(key,[]).append((row,text,conf))
  for words in groups.values():
   x=min(int(r['left']) for r,t,c in words);y=min(int(r['top']) for r,t,c in words);r=max(int(r['left'])+int(r['width']) for r,t,c in words);b=max(int(r['top'])+int(r['height']) for r,t,c in words)
   blocks.append({'text':' '.join(t for r,t,c in words),'bbox':[x,y,r,b],'confidence':sum(c for r,t,c in words)/len(words)/100,'language':lang})
 return {'coordinate_space':'pixels','width':width,'height':height,'blocks':fuse(blocks),'warnings':warnings}

def vision(image,languages,width,height,cache):
 cache=Path(cache);cache.mkdir(parents=True,exist_ok=True);src=Path(__file__).with_name('vision_ocr.swift');binary=cache/'vision-ocr'
 if not binary.exists() or binary.stat().st_mtime<src.stat().st_mtime:_run(['swiftc',str(src),'-o',str(binary)],timeout=180)
 output=cache/(Path(image).stem+'.vision.json')
 _run([str(binary),str(image),str(output),','.join(APPLE.get(x,x) for x in languages)],timeout=240)
 result=json.loads(output.read_text());result['blocks']=fuse(result.get('blocks',[]));return result

def external(image,languages,width,height,command,cache):
 args=json.loads(command)
 if not isinstance(args,list) or not args or not all(isinstance(x,str) for x in args):raise ValueError('--ocr-command-json must be a JSON array of command arguments')
 output=Path(cache)/(Path(image).stem+'.external.json');output.parent.mkdir(parents=True,exist_ok=True)
 values={'image':str(image),'output':str(output),'languages':','.join(languages)}
 cmd=[]
 for arg in args:
  for key,value in values.items():arg=arg.replace('{'+key+'}',value)
  cmd.append(arg)
 stdout=_run(cmd,timeout=300);result=json.loads(output.read_text() if output.exists() else stdout)
 if isinstance(result,list):result={'coordinate_space':'pdf','blocks':result}
 return result

def score(b):
 t=b.get('text','');lang=b.get('language','');n=max(1,len(t.replace(' ','')));hangul=len(re.findall('[가-힣]',t));kana=len(re.findall('[ぁ-ヿ]',t));han=len(re.findall('[一-龯]',t));latin=len(re.findall('[A-Za-z]',t));bonus=0
 if lang.startswith(('ko','kor')):bonus=.8 if hangul/n>.35 else -.7
 elif lang.startswith(('ja','jpn')):bonus=.65 if kana else .05
 elif lang.startswith(('zh','chi')):bonus=.5 if han and not kana and not hangul else -.4
 elif lang.startswith(('en','eng')):bonus=.45 if latin/n>.65 else -.3
 return float(b.get('confidence',.5))+bonus

def fuse(blocks):
 chosen=[]
 for b in sorted(blocks,key=score,reverse=True):
  a=b.get('bbox',[0,0,0,0]);area=max(.000001,(a[2]-a[0])*(a[3]-a[1]));duplicate=False
  for c in chosen:
   z=c['bbox'];inter=max(0,min(a[2],z[2])-max(a[0],z[0]))*max(0,min(a[3],z[3])-max(a[1],z[1]));union=area+(z[2]-z[0])*(z[3]-z[1])-inter
   if inter/max(.000001,union)>.48:duplicate=True;break
  if not duplicate:chosen.append(b)
 return sorted(chosen,key=lambda b:(round(b['bbox'][1],1),b['bbox'][0]))

def run(image,languages,width,height,backend,cache,command=None):
 cap=capabilities()
 if backend=='auto':
  warnings=[];routes=(['external'] if command else [])+(['vision'] if cap['vision'] else [])+(['tesseract'] if cap['tesseract'] else [])
  for route in routes:
   try:
    result=run(image,languages,width,height,route,cache,command);warnings+=result.get('warnings',[])
    if result.get('blocks'):
     result['warnings']=warnings+['ocr_auto_backend:'+route];return result
    warnings.append('ocr_auto_empty:'+route)
   except Exception as error:warnings.append('ocr_auto_failed:'+route+':'+str(error))
  return {'coordinate_space':'pixels','width':width,'height':height,'blocks':[],'warnings':warnings+['ocr_backend_unavailable:use_host_vision_or_install_local_backend']}
 if backend=='tesseract' and cap['tesseract']:return tesseract(image,languages,width,height)
 if backend=='vision' and cap['vision']:return vision(image,languages,width,height,cache)
 if backend=='external' and command:return external(image,languages,width,height,command,cache)
 return {'coordinate_space':'pixels','width':width,'height':height,'blocks':[],'warnings':['ocr_backend_unavailable:use_host_vision_or_install_local_backend']}
