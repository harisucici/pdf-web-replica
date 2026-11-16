#!/usr/bin/env python3
"""Portable PDF inventory, extraction, OCR, draft web reconstruction and review ledger."""
import argparse,hashlib,json,math,os,re,shutil,subprocess,sys,tempfile,time,unicodedata
from pathlib import Path
import ocr_backends
import image_policy
import fidelity
import layout_analysis
import scan_reconstruction
try:import pymupdf as fitz
except ImportError:
 try:import fitz
 except ImportError:fitz=None
ROOT=Path(__file__).resolve().parents[1]
if fitz is not None and not all(hasattr(fitz,x) for x in ['open','Rect','Matrix']):fitz=None
class PDFError(Exception):pass

def write_json(path,data,js=None):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 text=json.dumps(data,ensure_ascii=False,allow_nan=False,indent=None if js else 2)
 if js:text=js+text.replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')+';\n'
 tmp=path.with_name(path.name+'.tmp');tmp.write_text(text,encoding='utf-8');tmp.replace(path)

def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()

def require_pdf():
 if fitz is None:raise PDFError('PyMuPDF is missing. Run scripts/bootstrap.py --venv work/.pdf-web-env and use its Python executable.')

def open_pdf(path,password_env=None,scratch=None):
 require_pdf();path=Path(path).expanduser().resolve();password=os.environ.get(password_env,'') if password_env else ''
 if not path.is_file():raise PDFError('input_not_found: '+str(path))
 try:doc=fitz.open(path)
 except Exception as error:
  if scratch:
   repaired=Path(scratch)/'repaired.pdf';repaired.parent.mkdir(parents=True,exist_ok=True)
   for executable,args in [('qpdf',[str(path),str(repaired)]),('mutool',['clean','-gggg',str(path),str(repaired)])]:
    if not shutil.which(executable):continue
    result=subprocess.run([executable]+args,capture_output=True,timeout=120)
    if result.returncode==0:
     try:doc=fitz.open(repaired);break
     except Exception:continue
   else:raise PDFError('cannot_open_pdf: '+str(error)+'; qpdf/mutool repair unavailable or unsuccessful') from error
  else:raise PDFError('cannot_open_pdf: '+str(error)) from error
 was_encrypted=bool(doc.needs_pass);doc._pdf_web_was_encrypted=was_encrypted
 if was_encrypted and (not password or not doc.authenticate(password)):
  doc.close();raise PDFError('password_required_or_incorrect: provide the authorized password using --password-env VARIABLE')
 if not doc.is_pdf:doc.close();raise PDFError('input_is_not_a_pdf: inspect the actual file format')
 return doc

def page_numbers(spec,count):
 if not spec or spec=='all':return list(range(1,count+1))
 result=set()
 for part in spec.split(','):
  if '-' in part:
   a,b=map(int,part.split('-',1));result.update(range(a,b+1))
  else:result.add(int(part))
 if not result or min(result)<1 or max(result)>count:raise PDFError('page_range_out_of_bounds')
 return sorted(result)

def coverage(rect,page):
 r=fitz.Rect(rect)&page.rect
 return max(0,r.width*r.height)/max(1,page.rect.width*page.rect.height)

def page_image_policy(page):
 images=[{'bbox':rect(item['bbox'],page.rotation_matrix)} for item in page.get_image_info()]
 flags,union=image_policy.scan_flags(images,page.rect.width,page.rect.height)
 return images,flags,union

def classify(page):
 text=page.get_text();chars=len(text.strip());replacement=text.count('\ufffd')+text.count('\x00');images,flags,union=page_image_policy(page);large=max([coverage(x['bbox'],page) for x in images] or [0]);draw_count=len(page.get_drawings())
 if chars==0 and not images and draw_count==0:return 'blank',text,large
 if any(flags):return 'scan' if chars<30 else 'hybrid',text,large
 if chars<10 and draw_count>100:return 'outlined-or-graphics',text,large
 if replacement/max(1,chars)>.04:return 'invalid-text-map',text,large
 if chars<10 and images:return 'image-or-scan',text,large
 return 'native',text,large

def inventory(doc):
 pages=[]
 for i,page in enumerate(doc):
  try:
   kind,text,cov=classify(page);pages.append({'page':i+1,'width':page.rect.width,'height':page.rect.height,'rotation':page.rotation,'kind':kind,'characters':len(text.strip()),'large_image_coverage':round(cov,3)})
  except Exception as e:pages.append({'page':i+1,'kind':'inspection_error','error':str(e)})
 xfa=False
 try:
  typ,value=doc.xref_get_key(doc.pdf_catalog(),'AcroForm')
  if typ=='xref':xfa=doc.xref_get_key(int(value.split()[0]),'XFA')[1]!='null'
  elif typ=='dict':xfa='/XFA' in value
 except Exception:pass
 return {'page_count':len(doc),'encrypted':bool(getattr(doc,'_pdf_web_was_encrypted',doc.is_encrypted)),'repaired_by_parser':bool(doc.is_repaired),'xfa_requires_special_review':xfa,'attachments':doc.embfile_names(),'pages':pages}

def render_reference(page,target,dpi):
 # Adaptive resolution bounds memory, not the number of pages processed.
 area=max(1,page.rect.width*page.rect.height);scale=min(dpi/72,math.sqrt(18_000_000/area));pix=page.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False,annots=True);pix.save(target);return pix.width,pix.height

def color(value):
 if value is None:return 'none'
 if isinstance(value,int):return '#%06x'%value
 if len(value)==1:return 'rgb('+','.join([str(round(value[0]*255))]*3)+')'
 if len(value)==4:
  c,m,y,k=value;value=[(1-c)*(1-k),(1-m)*(1-k),(1-y)*(1-k)]
 return 'rgb('+','.join(str(round(max(0,min(1,x))*255)) for x in value[:3])+')'

def point(p,m):
 q=fitz.Point(p)*m;return [round(q.x,4),round(q.y,4)]
def rect(r,m):return [round(v,4) for v in fitz.Rect(r)*m]
def font_key(name):return re.sub(r'^[A-Z]{6}\+','',name).lower().replace(' ','').replace('-','')

def extract_fonts(doc,page,site,cache):
 mapping={};warnings=[]
 for entry in page.get_fonts(full=True):
  xref,ext,typ,base=entry[:4]
  if xref not in cache:
   try:
    name,ext,typ,data=doc.extract_font(xref)
    if data and ext in ['ttf','otf','woff','woff2']:
     filename=f'fonts/font-{xref}.{ext}';dest=site/filename;dest.parent.mkdir(exist_ok=True);dest.write_bytes(data)
     cache[xref]={'family':f'pdf-font-{xref}','file':filename}
    else:cache[xref]=None
   except Exception:cache[xref]=None
  if cache[xref]:mapping[font_key(base)]=cache[xref]
  else:warnings.append('font_not_browser_embeddable:'+base)
 return mapping,sorted(set(warnings))

def native_blocks(doc,page,site,font_cache):
 blocks=[];images=[];m=page.rotation_matrix;fonts,warnings=extract_fonts(doc,page,site,font_cache)
 image_info,image_flags,_=page_image_policy(page)
 blocked_boxes={tuple(im['bbox']) for im,reason in zip(image_info,image_flags) if reason}
 for block in page.get_text('dict')['blocks']:
  if block['type']==0:
   for line in block['lines']:
    d=line.get('dir',(1,0));v=fitz.Point(d)*fitz.Matrix(m.a,m.b,m.c,m.d,0,0);angle=math.degrees(math.atan2(v.y,v.x))
    for span in line['spans']:
     t=span['text']
     if not t.strip():continue
     f=fonts.get(font_key(span['font']));raw=fitz.Rect(span['bbox']);advance=raw.height if abs(d[1])>.7 else raw.width
     blocks.append({'text':t,'bbox':rect(raw,m),'origin':point(span['origin'],m),'font_size':span['size'],'font_family':f['family'] if f else None,'font_file':f['file'] if f else None,'source_font':span['font'],'color':color(span['color']),'bold':bool(span['flags']&16),'italic':bool(span['flags']&2),'angle':angle,'advance':advance,'source':'native','role':'text'})
  elif block['type']==1:
   b=rect(block['bbox'],m)
   if tuple(b) in blocked_boxes or image_policy.scan_flags([{'bbox':b}],page.rect.width,page.rect.height)[0][0]:
    warnings.append('page_raster_excluded_from_web_content');continue
   try:
    data=block['image'];image_id=hashlib.sha256(data).hexdigest()[:20];ext=block.get('ext','png')
    if ext not in ['png','jpg','jpeg','webp','gif']:
     data=fitz.Pixmap(data).tobytes('png');ext='png'
    filename=f'illustrations/{image_id}.{ext}';dest=site/filename;dest.parent.mkdir(exist_ok=True);dest.write_bytes(data)
    transform=list(fitz.Matrix(*block.get('transform',(b[2]-b[0],0,0,b[3]-b[1],b[0],b[1])))*m)
    images.append({'file':filename,'bbox':b,'matrix':transform,'role':'illustration_candidate','reviewed':False})
    warnings.append('illustration_candidates_require_source_review')
   except Exception as e:warnings.append('illustration_extract_error:'+str(e))
 try:
  for widget in page.widgets() or []:
   value=widget.field_value
   if value is None or value=='':continue
   r=rect(widget.rect,m);matched=False
   for existing in blocks:
    if existing['text']!=str(value):continue
    bb=fitz.Rect(existing['bbox']);wr=fitz.Rect(r);inter=bb&wr
    if max(0,inter.width)*max(0,inter.height)/max(.001,bb.width*bb.height)>.7:
     existing.update(role='form_field',field_name=widget.field_name,field_type=widget.field_type_string);matched=True;break
   if matched:continue
   blocks.append({'text':str(value),'bbox':r,'origin':[r[0]+2,r[3]-2],'font_size':widget.text_fontsize or 11,'font_family':None,'color':color(widget.text_color or (0,0,0)),'source':'form','role':'form_field','field_name':widget.field_name,'field_type':widget.field_type_string,'angle':page.rotation,'advance':max(1,r[2]-r[0]-4)})
 except Exception as e:warnings.append('form_extract_error:'+str(e))
 return blocks,images,warnings

def native_shapes(page):
 result=[];m=page.rotation_matrix;warnings=[]
 for drawing in page.get_drawings():
  commands=[];last=None
  def xy(p):return ' '.join(str(v) for v in point(p,m))
  def move(p):
   nonlocal last
   p=tuple(p)
   if last!=p:commands.append('M '+xy(p))
   last=p
  for item in drawing['items']:
   if item[0]=='l':move(item[1]);commands.append('L '+xy(item[2]));last=tuple(item[2])
   elif item[0]=='c':move(item[1]);commands.append('C '+' '.join(xy(x) for x in item[2:5]));last=tuple(item[4])
   elif item[0]=='re':
    r=fitz.Rect(item[1]);commands.append('M '+xy(r.tl)+' L '+xy(r.tr)+' L '+xy(r.br)+' L '+xy(r.bl)+' Z');last=None
   elif item[0]=='qu':
    q=item[1];commands.append('M '+xy(q.ul)+' L '+xy(q.ur)+' L '+xy(q.lr)+' L '+xy(q.ll)+' Z');last=None
   else:warnings.append('unsupported_vector_command:'+str(item[0]))
  if drawing.get('closePath'):commands.append('Z')
  if commands:result.append({'path':' '.join(commands),'fill':color(drawing.get('fill')),'stroke':color(drawing.get('color')),'width':drawing.get('width',.5),'fill_opacity':drawing.get('fill_opacity',1),'stroke_opacity':drawing.get('stroke_opacity',1),'even_odd':drawing.get('even_odd',False),'bbox':rect(drawing['rect'],m)})
 return result,warnings

def normalize_ocr(result,width,height):
 space=result.get('coordinate_space','pdf');sx=width/(result.get('width') or width) if space=='pixels' else width if space=='normalized' else 1;sy=height/(result.get('height') or height) if space=='pixels' else height if space=='normalized' else 1;blocks=[]
 for item in result.get('blocks',[]):
  if not item.get('text','').strip():continue
  x0,y0,x1,y1=item['bbox'];b=[x0*sx,y0*sy,x1*sx,y1*sy]
  if not all(math.isfinite(v) for v in b) or b[2]<=b[0] or b[3]<=b[1]:continue
  size=item.get('font_size') or max(3,(b[3]-b[1])*.82)
  rtl=sum(unicodedata.bidirectional(c) in ['R','AL'] for c in item['text'])>len(item['text'])/3
  blocks.append({'text':item['text'],'bbox':b,'ocr_bbox':list(b),'origin':item.get('origin',[b[0],b[3]-(b[3]-b[1])*.12]),'font_size':size,'font_family':item.get('font_family'),'color':item.get('color','#222'),'bold':item.get('bold',False),'italic':item.get('italic',False),'angle':item.get('angle',0),'advance':item.get('advance',b[2]-b[0]),'source':'ocr','language':item.get('language','unknown'),'confidence':item.get('confidence'),'rtl':rtl,'role':item.get('role','text'),'characters':[{'text':c['text'],'confidence':c.get('confidence'),'bbox':[v*(sx if j%2==0 else sy) for j,v in enumerate(c['bbox'])]} for c in item.get('characters',[])]})
 return blocks

def refresh(out):
 out=Path(out);manifest=json.loads((out/'manifest.json').read_text());site=out/'site';site.mkdir(exist_ok=True);summary=[];text=[];search_index=[];requests=[];stamp=time.time()
 # Fingerprints include the actual viewer templates, installed before page export.
 for name in ['index.html','reader.js','reader.css']:
  value=(ROOT/'assets'/name).read_text().replace('__BUILD__',str(stamp));(site/name).write_text(value,encoding='utf-8')
 for no in manifest['selected_pages']:
  filename=out/'pages'/f'{no:05}.json'
  if not filename.exists():summary.append({'page':no,'status':'pending','width':612,'height':792});continue
  data=json.loads(filename.read_text());image_policy.enforce_image_policy(data)
  current=fidelity.fingerprint(out,data)
  signatures=data.get('review_signatures',{})
  for check in fidelity.CHECKS:
   if data.get('review',{}).get(check) and signatures.get(check)!=current:data['review'][check]=False
  data['render_fingerprint']=current;write_json(filename,data);write_json(site/'pages'/f'{no:05}.js',data,js=f'window.PDF_PAGES[{no}]=')
  summary.append({k:data[k] for k in ['page','width','height','kind','status','warnings']});search_index.append({'page':no,'text':data.get('text','')});text.append(f'\n\n========== PDF page {no} ==========\n'+data.get('text',''))
  requests.append({'page':no,'render_fingerprint':current,'url':f'index.html?qa=1#page={no}','capture':f'{no:05}.png','metadata':f'{no:05}.json'})
 manifest['pages']=summary;manifest['updated_at']=stamp;manifest['status']='draft';write_json(out/'manifest.json',manifest)
 write_json(out/'qa'/'capture-requests.json',{'pages':requests,'instructions':'Capture the default web page after window.PDF_REPLICA_QA.ready is true. Save the page crop and that metadata, plus captured_with. Never capture the source comparison view.'})
 write_json(site/'text-index.js',search_index,js='window.PDF_TEXT_INDEX=')
 write_json(site/'document.js',{'title':manifest.get('display_title',manifest['title']),'subtitle':manifest.get('subtitle','PDF WEB REPLICA · 校对中'),'pages':summary,'draft':True,'version':str(stamp)},js='window.PDF_DOCUMENT=')
 (out/'extracted.txt').write_text(''.join(text).lstrip(),encoding='utf-8');shutil.copy(out/'extracted.txt',site/'extracted.txt')
 return manifest

def build(args):
 source=Path(args.input).expanduser().resolve();out=Path(args.out).expanduser().resolve();out.mkdir(parents=True,exist_ok=True);source_hash=digest(source);mf=out/'manifest.json'
 if mf.exists():
  old=json.loads(mf.read_text())
  if old['source_sha256']!=source_hash:raise PDFError('output_contains_a_different_document: choose a new --out directory')
  if not args.resume:raise PDFError('output_already_exists: use --resume; existing manual edits are preserved')
 doc=open_pdf(source,args.password_env,out/'work')
 if len(doc)==0:
  doc.close();raise PDFError('pdf_has_no_pages: inspect portfolio attachments or obtain a complete PDF')
 requested=page_numbers(args.pages,len(doc));selected=list(requested);site=out/'site';site.mkdir(exist_ok=True);(out/'references').mkdir(exist_ok=True);(out/'pages').mkdir(exist_ok=True)
 if mf.exists():
  old=json.loads(mf.read_text());selected=sorted(set(old['selected_pages'])|set(selected))
 else:old={'schema_version':1,'source_sha256':source_hash,'source_name':source.name,'page_count':len(doc),'selected_pages':selected,'title':source.stem,'status':'draft'}
 old['selected_pages']=selected;old['conversion_profile']={'dpi':args.dpi,'ocr':args.ocr,'languages':args.languages.split(','),'artwork':'source-cropped','text':'visible_unicode','quality_reference':'references/scan-quality.md'};write_json(mf,old);write_json(out/'inspection.json',inventory(doc));fonts={};languages=args.languages.split(',');enhance_pages=[]
 for no in requested:
  target=out/'pages'/f'{no:05}.json'
  if target.exists() and args.resume and not args.reprocess:
   saved=json.loads(target.read_text())
   if not (args.retry_pending and saved['status'] in ['needs_ocr','error']):continue
  try:
   page=doc[no-1];kind,native_text,large=classify(page);width,height=page.rect.width,page.rect.height;ref=out/'references'/f'{no:05}.png';pixel_width,pixel_height=render_reference(page,ref,args.dpi);blocks,images,warnings=native_blocks(doc,page,site,fonts);shapes,more=native_shapes(page);warnings+=more
   needs_ocr=kind in ['scan','hybrid','outlined-or-graphics','invalid-text-map','image-or-scan']
   ocr_success=not needs_ocr
   if not ocr_success:
    try:
     result=ocr_backends.run(ref,languages,pixel_width,pixel_height,args.ocr,out/'work',args.ocr_command_json);ocr=normalize_ocr(result,width,height);warnings+=result.get('warnings',[])
     if ocr:
      if kind in ['hybrid','scan','image-or-scan'] and blocks:
       native=list(blocks)
       for ob in ocr:
        a=fitz.Rect(ob['bbox']);duplicate=False
        for nb in native:
         z=fitz.Rect(nb['bbox']);inter=a&z;intersection=max(0,inter.width)*max(0,inter.height);union=a.width*a.height+z.width*z.height-intersection
         if intersection/max(.001,union)>.5:duplicate=True;break
        if not duplicate:blocks.append(ob)
      else:blocks=ocr+[b for b in blocks if b['role']=='form_field']
      ocr_success=True
      if any(b.get('characters') or b.get('role')=='vertical_text' for b in ocr):enhance_pages.append(no)
    except Exception as e:warnings.append('ocr_failed:'+str(e))
   if kind!='blank':warnings.append('source_text_layout_fonts_and_languages_not_yet_verified')
   if needs_ocr:warnings.append('scan_regions_and_nontext_artwork_require_native_reconstruction')
   if kind=='outlined-or-graphics':shapes=[];warnings.append('outlined_text_not_used_as_a_fake_text_layer')
   if any(True for _ in page.annots() or []):warnings.append('annotations_require_visual_review')
   status='blank' if kind=='blank' else 'needs_ocr' if needs_ocr and not ocr_success else 'draft'
   data={'page':no,'width':width,'height':height,'rotation':page.rotation,'kind':kind,'status':status,'blocks':blocks,'shapes':shapes,'images':images,'warnings':sorted(set(warnings)),'text':'\n'.join(b['text'] for b in sorted(blocks,key=lambda x:(round(x['bbox'][1],1),x['bbox'][0]))),'review':{k:False for k in ['text','layout','fonts','languages']}}
  except Exception as e:data={'page':no,'width':612,'height':792,'rotation':0,'kind':'error','status':'error','blocks':[],'shapes':[],'images':[],'warnings':[str(e)],'text':'','review':{k:False for k in ['text','layout','fonts','languages']}}
  write_json(target,data);print(json.dumps({'page':no,'total_selected':len(selected),'status':data['status']},ensure_ascii=False),flush=True)
 doc.close()
 if enhance_pages:scan_reconstruction.enhance(out,enhance_pages,write_json)
 manifest=refresh(out);print(json.dumps({'output':str(out),'site':str(site/'index.html'),'pages':len(selected),'pending':sum(p['status'] in ['needs_ocr','error','pending'] for p in manifest['pages']),'pending_review_pages':len(selected),'next_steps':['analyze source pages','reconstruct from source','capture default web pages','compare and correct','record source review','audit'],'status':'draft'},ensure_ascii=False));return 0

def audit(out,allow_range=False):
 out=Path(out);m=json.loads((out/'manifest.json').read_text());issues=[];verified=0
 if m['page_count']==0:issues.append({'issue':'pdf_has_no_pages'})
 if not allow_range and len(m['selected_pages'])!=m['page_count']:issues.append({'issue':'full_document_range_not_processed'})
 for no in m['selected_pages']:
  start=len(issues);path=out/'pages'/f'{no:05}.json'
  if not path.exists():issues.append({'page':no,'issue':'missing_page'});continue
  p=json.loads(path.read_text());review=p.get('review',{});current=fidelity.fingerprint(out,p)
  image_flags,_=image_policy.scan_flags(p.get('images',[]),p['width'],p['height'])
  for im,reason in zip(p.get('images',[]),image_flags):
   if not image_policy.image_approved(im,reason):issues.append({'page':no,'issue':reason or 'unreviewed_illustration','file':im.get('file')})
  if p.get('excluded_images') and not review.get('layout'):issues.append({'page':no,'issue':'excluded_page_rasters_require_reconstruction'})
  if p['status'] in ['error','needs_ocr']:issues.append({'page':no,'issue':p['status']})
  if p.get('layout_needs_sync'):issues.append({'page':no,'issue':'layout_text_not_synchronized'})
  for difference in p.get('remaining_differences',[]):issues.append({'page':no,'issue':'unresolved_source_difference','description':difference})
  if not all(review.get(k) for k in fidelity.CHECKS):issues.append({'page':no,'issue':'not_fully_verified'})
  elif any(p.get('review_signatures',{}).get(k)!=current for k in fidelity.CHECKS):issues.append({'page':no,'issue':'review_record_stale'})
  evidence=fidelity.evidence_issue(out,p)
  if evidence:issues.append({'page':no,'issue':evidence})
  if p['kind']!='blank' and not p['blocks']:issues.append({'page':no,'issue':'no_selectable_text_review_required'})
  for block in p['blocks']:
   r=block['bbox']
   if r[2]<0 or r[3]<0 or r[0]>p['width']+2 or r[1]>p['height']+2:issues.append({'page':no,'issue':'text_outside_page'})
  if len(issues)==start:verified+=1
 result={'acceptance':'passed-recorded-review' if not issues else 'not-passed','selected_pages':len(m['selected_pages']),'verified_pages':verified,'issues':issues,'note':'Recorded source review and current browser evidence are required. Pixel metrics are not a reconstruction percentage.'};write_json(out/'audit.json',result);print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if not issues else 3

def main():
 p=argparse.ArgumentParser();sp=p.add_subparsers(dest='command',required=True)
 sp.add_parser('doctor')
 ins=sp.add_parser('inspect');ins.add_argument('input');ins.add_argument('--out');ins.add_argument('--password-env')
 for name in ['build','batch']:
  b=sp.add_parser(name);b.add_argument('input');b.add_argument('--out',required=True);b.add_argument('--pages',default='all');b.add_argument('--languages',default='auto');b.add_argument('--ocr',choices=['auto','none','tesseract','vision','rapidocr','external'],default='auto');b.add_argument('--ocr-command-json');b.add_argument('--dpi',type=int,default=216);b.add_argument('--password-env');b.add_argument('--resume',action='store_true');b.add_argument('--retry-pending',action='store_true');b.add_argument('--reprocess',action='store_true')
 a=sp.add_parser('attachments');a.add_argument('input');a.add_argument('--out',required=True);a.add_argument('--password-env')
 a=sp.add_parser('audit');a.add_argument('out');a.add_argument('--allow-range',action='store_true')
 a=sp.add_parser('refresh');a.add_argument('out')
 a=sp.add_parser('import-ocr');a.add_argument('out');a.add_argument('--page',type=int,required=True);a.add_argument('--json',required=True)
 a=sp.add_parser('analyze');a.add_argument('out');a.add_argument('--pages',default='all')
 a=sp.add_parser('enhance');a.add_argument('out');a.add_argument('--pages',default='all');a.add_argument('--font-config');a.add_argument('--refine-ruby',action='store_true')
 a=sp.add_parser('crop-artwork');a.add_argument('out');a.add_argument('--page',type=int,required=True);a.add_argument('--bbox',type=float,nargs=4,required=True);a.add_argument('--exclude-text-bbox',type=float,nargs=4,action='append',default=[]);a.add_argument('--reviewed',action='store_true');a.add_argument('--note',default='')
 a=sp.add_parser('compare');a.add_argument('out');a.add_argument('--captures',required=True);a.add_argument('--pages',default='all')
 a=sp.add_parser('apply-layout');a.add_argument('out');a.add_argument('--page',type=int,required=True);a.add_argument('--json',required=True)
 a=sp.add_parser('review');a.add_argument('out');a.add_argument('--pages',required=True);a.add_argument('--checks',required=True);a.add_argument('--note',required=True)
 args=p.parse_args()
 try:
  if args.command=='doctor':print(json.dumps({'python':sys.executable,'pymupdf':getattr(fitz,'VersionBind',None),'ocr':ocr_backends.capabilities(),'fidelity_analysis':bool(__import__('importlib.util',fromlist=['find_spec']).find_spec('PIL')),'repair':{x:shutil.which(x) for x in ['qpdf','mutool','gs','pdftoppm']}},ensure_ascii=False,indent=2));return 0 if fitz else 2
  if args.command=='inspect':
   doc=open_pdf(args.input,args.password_env);data=inventory(doc);doc.close()
   if args.out:write_json(args.out,data)
   print(json.dumps(data,ensure_ascii=False,indent=2));return 0
  if args.command=='attachments':
   doc=open_pdf(args.input,args.password_env);dest=Path(args.out).expanduser().resolve();dest.mkdir(parents=True,exist_ok=True);files=[]
   for i,name in enumerate(doc.embfile_names(),1):
    safe=re.sub(r'[^\w. -]','_',Path(name.replace('\\','/')).name).strip(' .') or 'attachment';data=doc.embfile_get(name);target=dest/(f'{i:04}-'+safe)
    if target.exists() and target.read_bytes()!=data:raise PDFError('attachment_output_exists:'+str(target))
    target.write_bytes(data);files.append({'name':name,'path':str(target),'is_pdf':data.lstrip().startswith(b'%PDF-')})
   doc.close();write_json(dest/'attachments.json',files);print(json.dumps(files,ensure_ascii=False));return 0
  if args.command=='build':return build(args)
  if args.command=='batch':
   batch_root=Path(args.input).expanduser().resolve();files=sorted(p for p in batch_root.rglob('*') if p.is_file() and p.suffix.lower()=='.pdf');base=Path(args.out).resolve();records=[]
   for f in files:
    run=argparse.Namespace(**vars(args));run.input=str(f);run.out=str(base/f.relative_to(batch_root).with_suffix(''))
    try:build(run);records.append({'input':str(f),'out':run.out,'status':'draft'})
    except Exception as e:records.append({'input':str(f),'status':'error','reason':str(e)})
   write_json(base/'batch-report.json',records);print(json.dumps({'files':len(files),'errors':sum(r['status']=='error' for r in records)},ensure_ascii=False));return 0 if all(r['status']!='error' for r in records) else 2
  if args.command=='audit':return audit(args.out,args.allow_range)
  if args.command=='refresh':refresh(args.out);return 0
  if args.command=='analyze':
   out=Path(args.out);manifest=json.loads((out/'manifest.json').read_text());selected=page_numbers(args.pages,manifest['page_count']);selected=[n for n in selected if n in manifest['selected_pages']];print(json.dumps(layout_analysis.analyze(out,selected,write_json),ensure_ascii=False));return 0
  if args.command=='enhance':
   out=Path(args.out);manifest=json.loads((out/'manifest.json').read_text());selected=[n for n in page_numbers(args.pages,manifest['page_count']) if n in manifest['selected_pages']];result=scan_reconstruction.enhance(out,selected,write_json,args.font_config,args.refine_ruby);refresh(out);print(json.dumps(result,ensure_ascii=False));return 2 if result.get('errors') else 0
  if args.command=='crop-artwork':
   result=scan_reconstruction.crop_artwork(args.out,args.page,args.bbox,args.exclude_text_bbox,args.note,args.reviewed,write_json);refresh(args.out);print(json.dumps(result,ensure_ascii=False));return 0
  if args.command=='compare':
   out=Path(args.out);manifest=json.loads((out/'manifest.json').read_text());records=[]
   for no in page_numbers(args.pages,manifest['page_count']):
    try:records.append(fidelity.compare_page(out,json.loads((out/'pages'/f'{no:05}.json').read_text()),args.captures))
    except (ValueError,OSError,KeyError) as error:records.append({'page':no,'status':'needs_attention','error':str(error)})
   write_json(out/'qa'/'comparison-report.json',{'pages':records});print(json.dumps({'pages':[{'page':r['page'],'status':r['status'],'error':r.get('error')} for r in records]},ensure_ascii=False));return 0 if records and all(r['status']=='within_threshold' for r in records) else 3
  if args.command=='apply-layout':
   out=Path(args.out);target=out/'pages'/f'{args.page:05}.json';data=json.loads(target.read_text());patch=json.loads(Path(args.json).read_text());allowed={'blocks','text','shapes','images','web_layout','background_color','reference_image','remaining_differences'}
   if not isinstance(patch,dict) or set(patch)-allowed:raise PDFError('layout_patch_contains_unsupported_fields')
   if 'remaining_differences' in patch and (not isinstance(patch['remaining_differences'],list) or not all(isinstance(v,str) and v.strip() for v in patch['remaining_differences'])):raise PDFError('remaining_differences_must_be_a_list_of_nonempty_descriptions')
   if 'blocks' in patch and 'text' not in patch:patch['text']='\n'.join(b['text'] for b in patch['blocks'])
   if data.get('web_layout') and ('blocks' in patch or 'text' in patch) and 'web_layout' not in patch:data['layout_needs_sync']=True
   if 'web_layout' in patch:data['layout_needs_sync']=False
   data.update(patch);data['review']={k:False for k in fidelity.CHECKS};data['review_signatures']={};data['status']='draft' if data.get('blocks') or data.get('kind')=='blank' else 'needs_ocr';write_json(target,data);refresh(out);return 0
  if args.command=='import-ocr':
   out=Path(args.out);target=out/'pages'/f'{args.page:05}.json';data=json.loads(target.read_text());result=json.loads(Path(args.json).read_text());data['blocks']=normalize_ocr(result,data['width'],data['height']);data['text']='\n'.join(b['text'] for b in data['blocks']);data['status']='draft' if data['blocks'] else 'needs_ocr';data['review']={k:False for k in ['text','layout','fonts','languages']};data['warnings'].append('imported_ocr_requires_source_verification');data['layout_needs_sync']=bool(data.get('web_layout'));write_json(target,data);refresh(out);return 0
  if args.command=='review':
   out=Path(args.out);m=json.loads((out/'manifest.json').read_text());checks=args.checks.split(',');prepared=[]
   if any(k not in fidelity.CHECKS for k in checks):raise PDFError('unknown_review_dimension')
   for no in page_numbers(args.pages,m['page_count']):
    target=out/'pages'/f'{no:05}.json'
    if not target.exists():raise PDFError('cannot_review_unprocessed_page:'+str(no))
    d=json.loads(target.read_text())
    if d['status'] in ['needs_ocr','error'] or d.get('layout_needs_sync') or d.get('remaining_differences'):raise PDFError('cannot_review_unresolved_page:'+str(no))
    if any(k in checks for k in ['layout','fonts']):
     reason=fidelity.evidence_issue(out,d)
     if reason:raise PDFError(reason+': page '+str(no)+'; capture the default web page, compare, and resolve differences first')
    current=fidelity.fingerprint(out,d)
    for k in checks:d['review'][k]=True;d.setdefault('review_signatures',{})[k]=current
    d.setdefault('review_notes',[]).append({'checks':checks,'note':args.note,'time':time.time(),'render_fingerprint':current});prepared.append((target,d))
   for target,d in prepared:write_json(target,d)
   refresh(out);return 0

 except (PDFError,ValueError,FileNotFoundError,PermissionError) as e:print(json.dumps({'error':str(e),'status':'needs-attention'},ensure_ascii=False),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
