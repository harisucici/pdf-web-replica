#!/usr/bin/env python3
"""Observable regression checks; fixtures contain no user document content."""
import argparse,json,os,subprocess,sys,tempfile
from pathlib import Path
import pymupdf as fitz
ROOT=Path(__file__).resolve().parents[1];CLI=ROOT/'scripts/pdf_web.py'
def call(*args,ok=(0,),env=None):
 r=subprocess.run([sys.executable,str(CLI),*map(str,args)],capture_output=True,text=True,env=env)
 if r.returncode not in ok:raise AssertionError(f'CLI failed: {args}: {r.stdout[-1000:]} {r.stderr[-1000:]}')
 return r

def raster_checks(w, scan):
 doc=fitz.open()
 margin=(85.6,72,526.4,720)
 for rotation in (0,90):
  p=doc.new_page(width=612,height=792);p.insert_image(margin,stream=scan,keep_proportion=False);p.set_rotation(rotation)
 p=doc.new_page(width=612,height=792)
 p.insert_image((80,60,532,396),stream=scan,keep_proportion=False)
 p.insert_image((80,396,532,732),stream=scan,keep_proportion=False)
 p=doc.new_page(width=612,height=792);p.insert_image(margin,stream=scan,keep_proportion=False);p.insert_text((30,35),'Long native header does not reconstruct the scanned body',fontsize=10)
 fixture=w/'raster-regression.pdf';doc.save(fixture);doc.close()
 call('inspect',fixture,'--out',w/'raster-inspection.json')
 inv=json.loads((w/'raster-inspection.json').read_text())
 assert [p['kind'] for p in inv['pages']]==['scan','scan','scan','hybrid']
 assert .58<inv['pages'][0]['large_image_coverage']<.60
 assert inv['pages'][2]['large_image_coverage']<.5
 out=w/'raster-regression'
 call('build',fixture,'--out',out,'--ocr','none')
 for no in range(1,5):
  d=json.loads((out/'pages'/f'{no:05}.json').read_text());assert not d['images'] and d['status']=='needs_ocr'
 assert not list((out/'site').glob('illustrations/*'))
 # Older page data: refresh must remove a margin scan, preserve text/manual notes,
 # and invalidate earlier acceptance rather than merely changing reader templates.
 target=w/'mixed/pages/00001.json';d=json.loads(target.read_text());original_blocks=d['blocks'];original_notes=d.get('review_notes')
 candidate=d['images'][0];assert candidate['role']=='illustration_candidate' and candidate['reviewed'] is False
 d['images']=[dict(candidate, bbox=[58.8,59.5,361.2,535.5],matrix=[302.4,0,0,476,58.8,59.5],role='illustration',reviewed=True)]
 d['review']={k:True for k in ['text','layout','fonts','languages']};target.write_text(json.dumps(d))
 call('refresh',w/'mixed');after=json.loads(target.read_text())
 assert not after['images'] and after['excluded_images']
 assert after['blocks']==original_blocks and after.get('review_notes')==original_notes
 assert not any(after['review'].values())
 published=json.loads((w/'mixed/site/pages/00001.js').read_text().split('=',1)[1].strip().removesuffix(';'));assert not published['images'] and published['excluded_images']
 audit=json.loads(call('audit',w/'mixed',ok=(3,)).stdout)
 assert any(i['issue']=='excluded_page_rasters_require_reconstruction' for i in audit['issues'])
 # A genuine small illustration can be explicitly approved and remains intact.
 after['images']=[dict(candidate,role='illustration',reviewed=True)];target.write_text(json.dumps(after))
 call('refresh',w/'mixed');assert json.loads(target.read_text())['images'][0]['reviewed'] is True


def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--vision',action='store_true');a=p.parse_args();w=a.out.resolve();w.mkdir(parents=True,exist_ok=True);source=w/'fixtures';source.mkdir(exist_ok=True)
 doc=fitz.open();p1=doc.new_page(width=420,height=595);p1.draw_rect((30,40,390,170),fill=(.93,.93,.93));p1.insert_text((45,75),'Native PDF: selectable text',fontsize=15);p1.insert_text((45,110),'日本語の文字',fontname='japan',fontsize=13);p1.insert_text((45,140),'한국어 텍스트',fontname='korea',fontsize=13)
 scan=p1.get_pixmap(matrix=fitz.Matrix(2,2)).tobytes('png');pix=fitz.Pixmap(fitz.csRGB,(0,0,12,12),False);pix.clear_with(200);p1.insert_image((330,200,370,240),stream=pix.tobytes('png'))
 doc.new_page(width=420,height=595);rot=doc.new_page(width=300,height=500);rot.insert_text((35,80),'Rotated page',fontsize=16);rot.set_rotation(90);p4=doc.new_page(width=420,height=595);p4.insert_image(p4.rect,stream=scan);p5=doc.new_page(width=420,height=595);p5.insert_image(p5.rect,stream=scan);p5.insert_text((20,580),'Native header: '+('mixed page content '*7),fontsize=8)
 widget=fitz.Widget();widget.field_name='status';widget.field_type=fitz.PDF_WIDGET_TYPE_TEXT;widget.rect=fitz.Rect(45,260,210,285);widget.field_value='Ready';p1=doc[0];p1.add_widget(widget)
 doc.embfile_add('nested.pdf',fitz.open(stream=doc.tobytes(),filetype='pdf').tobytes());fixture=source/'mixed 日本語.pdf';doc.save(fixture);doc.close()
 enc=fitz.open();enc.new_page().insert_text((72,72),'Authorized encrypted PDF');enc.save(source/'encrypted.pdf',encryption=fitz.PDF_ENCRYPT_AES_256,owner_pw='owner-secret',user_pw='test-password');enc.close();(source/'broken.pdf').write_bytes(b'%PDF-1.7\ntruncated')
 call('inspect',fixture,'--out',w/'inspection.json');inv=json.loads((w/'inspection.json').read_text());assert inv['page_count']==5 and inv['pages'][1]['kind']=='blank' and inv['pages'][2]['width']==500
 call('build',fixture,'--out',w/'mixed','--ocr','none');m=json.loads((w/'mixed/manifest.json').read_text());assert len(m['pages'])==5 and m['pages'][3]['status']=='needs_ocr' and m['pages'][4]['status']=='needs_ocr'
 native=json.loads((w/'mixed/pages/00001.json').read_text());assert sum('Ready'==b['text'] for b in native['blocks'])==1;assert any('日本語' in b['text'] for b in native['blocks']);assert native['images'];assert not json.loads((w/'mixed/pages/00004.json').read_text())['images']
 f=w/'mixed/pages/00001.json';value=json.loads(f.read_text());value['review_notes']=[{'note':'manual preservation check'}];f.write_text(json.dumps(value));call('build',fixture,'--out',w/'mixed','--ocr','none','--resume');assert json.loads(f.read_text())['review_notes'][0]['note']=='manual preservation check'
 call('inspect',source/'encrypted.pdf',ok=(2,));env=dict(os.environ,PDF_WEB_TEST_PASSWORD='test-password');call('build',source/'encrypted.pdf','--out',w/'encrypted','--password-env','PDF_WEB_TEST_PASSWORD','--ocr','none',env=env);assert 'test-password' not in (w/'encrypted/manifest.json').read_text()
 call('inspect',source/'broken.pdf',ok=(2,));call('attachments',fixture,'--out',w/'attachments');assert json.loads((w/'attachments/attachments.json').read_text())[0]['is_pdf']
 imported={'coordinate_space':'normalized','blocks':[{'text':'Imported scan text 한국어','bbox':[.1,.1,.8,.15],'language':'ko'}]};j=w/'import.json';j.write_text(json.dumps(imported));call('import-ocr',w/'mixed','--page','4','--json',j);data=json.loads((w/'mixed/pages/00004.json').read_text());assert data['blocks'][0]['bbox'][0]==42 and data['status']=='draft'
 audit=call('audit',w/'mixed',ok=(3,));assert json.loads(audit.stdout)['acceptance']=='not-passed'
 call('review',w/'mixed','--pages','4','--checks','text','--note','Synthetic imported-text assertion');assert json.loads((w/'mixed/pages/00004.json').read_text())['review']['text']
 call('batch',source,'--out',w/'batch','--ocr','none',ok=(2,));batch=json.loads((w/'batch/batch-report.json').read_text());assert len(batch)==3 and sum(r['status']=='error' for r in batch)==2
 if a.vision:
  call('build',fixture,'--out',w/'mixed','--resume','--reprocess','--pages','4','--ocr','vision','--languages','en,ja,ko');d=json.loads((w/'mixed/pages/00004.json').read_text());assert d['status']=='draft' and d['blocks'];assert 'Native' in d['text'] or 'selectable' in d['text']
  adapter=w/'external adapter.py';adapter.write_text("import json,sys;from pathlib import Path;assert Path(sys.argv[1]).is_file();Path(sys.argv[2]).write_text(json.dumps({'coordinate_space':'normalized','blocks':[{'text':'External adapter 한국어','bbox':[.1,.1,.8,.2]}]}))")
  command=json.dumps([sys.executable,str(adapter),'{image}','{output}'])
  call('build',fixture,'--out',w/'mixed','--resume','--reprocess','--pages','5','--ocr','external','--ocr-command-json',command);d=json.loads((w/'mixed/pages/00005.json').read_text());assert 'External adapter' in d['text']
 raster_checks(w,scan)
 report={'status':'passed','checks':['native Unicode','independent illustrations','blank page','rotation','forms','scan pending state','hybrid scan pending state','resume preserves edits','encrypted password handling','malformed input diagnostics','embedded PDF extraction','OCR import coordinates','audit refuses unfinished work','batch continues on errors','margin scans excluded','rotated margin scans excluded','tiled scans excluded','legacy image migration preserves manual text','illustration source review']+(['macOS multilingual Vision OCR','external OCR adapter with spaced paths'] if a.vision else []),'fixture_root':str(w)};(w/'selftest-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
