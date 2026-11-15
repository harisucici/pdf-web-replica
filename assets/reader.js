'use strict';
const $=id=>document.getElementById(id),NS='http://www.w3.org/2000/svg',doc=window.PDF_DOCUMENT,fonts=new Set(),inflight=new Map();let index=0,zoom=0,token=0,compareMode=false;
const qaMode=/(?:^|[?&])qa=1(?:&|$)/.test(location.search||'');
if(qaMode)document.documentElement.classList.add('qa-mode');
if(!doc||!doc.pages.length)throw new Error('Document inventory is missing or empty');
$('title').textContent=doc.title;document.title=doc.title+' · PDF Web Replica';$('total').textContent='/ '+doc.pages.length;$('subtitle').textContent=doc.subtitle||'PDF WEB REPLICA · 校对中';$('title').title=doc.title;
function svg(tag,attrs={}){const e=document.createElementNS(NS,tag);for(const [k,v]of Object.entries(attrs))if(v!==undefined&&v!==null)e.setAttribute(k,String(v));return e}
function notice(message){$('notice').hidden=!message;$('notice').textContent=message||''}
function load(no){if(window.PDF_PAGES[no])return Promise.resolve(window.PDF_PAGES[no]);if(inflight.has(no))return inflight.get(no);const promise=new Promise((resolve,reject)=>{const s=document.createElement('script');s.src='pages/'+String(no).padStart(5,'0')+'.js?v='+encodeURIComponent(doc.version||'1');s.onload=()=>window.PDF_PAGES[no]?resolve(window.PDF_PAGES[no]):reject(new Error('Page data missing'));s.onerror=()=>reject(new Error('Page resource failed'));document.body.append(s)});inflight.set(no,promise);promise.catch(()=>inflight.delete(no));return promise}
function addFont(b){if(!b.font_file||fonts.has(b.font_file))return;fonts.add(b.font_file);const style=document.createElement('style');style.textContent='@font-face{font-family:'+JSON.stringify(b.font_family)+';src:url('+JSON.stringify(b.font_file)+');font-display:swap}';document.head.append(style)}
function imagePolicy(data){
 const images=data.images||[],width=data.width,height=data.height;
 const boxes=images.map(im=>{
  const candidates=[];
  if(Array.isArray(im.bbox)&&im.bbox.length===4)candidates.push(im.bbox);
  if(Array.isArray(im.matrix)&&im.matrix.length===6&&im.matrix.every(Number.isFinite)){
   const[a,b,c,d,e,f]=im.matrix,x=[e,a+e,c+e,a+c+e],y=[f,b+f,d+f,b+d+f];
   candidates.push([Math.min(...x),Math.min(...y),Math.max(...x),Math.max(...y)]);
  }
  if(!candidates.length||!candidates.flat().every(Number.isFinite)||!(width>0&&height>0))return null;
  const box=[Math.max(0,Math.min(...candidates.map(b=>b[0]))),Math.max(0,Math.min(...candidates.map(b=>b[1]))),Math.min(width,Math.max(...candidates.map(b=>b[2]))),Math.min(height,Math.max(...candidates.map(b=>b[3])))];
  return box[2]>box[0]&&box[3]>box[1]?box:null;
 });
 const valid=boxes.filter(Boolean),xs=[...new Set(valid.flatMap(b=>[b[0],b[2]]))].sort((a,b)=>a-b);let area=0;
 for(let i=1;i<xs.length;i++){
  const left=xs[i-1],right=xs[i],intervals=valid.filter(b=>b[0]<right&&b[2]>left).map(b=>[b[1],b[3]]).sort((a,b)=>a[0]-b[0]);let end=-Infinity,covered=0;
  for(const[low,high]of intervals){covered+=Math.max(0,high-Math.max(low,end));end=Math.max(end,high)}
  area+=(right-left)*covered;
 }
 const grouped=area/Math.max(1,width*height)>=.5;
 const allowed=images.filter((im,i)=>{
  const b=boxes[i];if(!b||grouped||im.role!=='illustration'||im.reviewed!==true)return false;
  const w=b[2]-b[0],h=b[3]-b[1];return w*h/Math.max(1,width*height)<.5&&!(w/width>=.6&&h/height>=.6);
 });
 return {allowed,withheld:images.length-allowed.length+(data.excluded_images||[]).length};
}
function webLayout(data,allowed){
 const host=document.createElement('div');host.setAttribute('xmlns','http://www.w3.org/1999/xhtml');host.style.cssText=`position:relative;width:${data.width}px;height:${data.height}px;overflow:hidden;user-select:text`;
 const approved=new Map(allowed.map(im=>[im.file,im]));
 function node(item){
  if(item.tag==='img'){
   const im=approved.get(item.image_file);if(!im)return null;
   const b=im.bbox;if(!b)return null;const el=document.createElement('img');el.src=im.file;el.alt='';el.className='isolated-illustration';el.style.cssText=`position:absolute;left:${b[0]}px;top:${b[1]}px;width:${b[2]-b[0]}px;height:${b[3]-b[1]}px;object-fit:contain`;return el;
  }
  if(!['div','span','svg','path'].includes(item.tag))return null;
  const el=['svg','path'].includes(item.tag)?svg(item.tag):document.createElement(item.tag);
  if(item.style&&!/url\s*\(|expression\s*\(|@import/i.test(item.style))el.style.cssText=item.style;
  if(item.text!==undefined)el.textContent=item.text;
  if(item.text)el.setAttribute('data-page-text','');
  for(const[k,v]of Object.entries(item.attrs||{}))if(['viewBox','d','fill','stroke','stroke-width','stroke-linejoin','aria-hidden'].includes(k))el.setAttribute(k,String(v));
  for(const child of item.children||[]){const c=node(child);if(c)el.append(c)}return el;
 }
 for(const item of data.web_layout.elements||[]){const el=node(item);if(el)host.append(el)}
 const measure=document.createElement('canvas').getContext('2d');
 for(const b of data.web_layout.blocks||[]){
  if(b.number){const c=document.createElement('span');c.className='number';c.textContent=b.number;c.style.cssText=`left:${b.x*data.width-1}px;top:${b.y*data.height+2}px;width:${b.numberSize||18}px;height:${b.numberSize||18}px;font-size:${b.numberFont||7}px`;host.append(c)}
  const el=document.createElement('span');el.className='word';el.setAttribute('data-page-text','');el.textContent=b.text;
  if(b.parts){el.replaceChildren();for(const part of b.parts){const run=document.createElement('span');run.textContent=part.text;if(part.underline)run.style.textDecoration='underline';if(part.bold)run.style.fontWeight='700';el.append(run)}}
  const f=b.font==='korean'?'"Apple SD Gothic Neo","Malgun Gothic",sans-serif':b.font==='sans'?'Arial,"Hiragino Kaku Gothic ProN",sans-serif':'"Hiragino Mincho ProN","Yu Mincho","Noto Serif JP",serif';
  el.style.cssText=`left:${(b.x+(b.shift||0))*data.width}px;top:${b.y*data.height+(b.h*data.height-b.size)/2}px;font-size:${b.size}px;font-family:${f};font-weight:${b.bold?700:400};color:${b.color||'#222'}`;
  measure.font=`${b.bold?700:400} ${b.size}px ${f}`;const natural=measure.measureText(b.text).width||1;el.style.transform=`scaleX(${b.w*data.width/natural})`;
  for(const r of b.rubies||[]){const rt=document.createElement('span');rt.textContent=r.text;rt.style.cssText='position:absolute;top:-5.5px;font:4.5px/1 "Hiragino Kaku Gothic ProN",sans-serif;color:#222;white-space:nowrap;background:#efefef;padding:0 .3px;transform:translateX(-50%)';rt.style.left=(measure.measureText(b.text.slice(0,r.offset)).width+measure.measureText(b.text.slice(r.offset,r.offset+r.length)).width/2)+'px';el.append(rt)}host.append(el);
 }
 const foreign=svg('foreignObject',{x:0,y:0,width:data.width,height:data.height});foreign.append(host);return foreign;
}
function publishCaptureRecord(record){const el=$('pdf-replica-qa');if(el)el.textContent=JSON.stringify(record)}
function markCaptureReady(data){
 const record={page:data.page,render_fingerprint:data.render_fingerprint||null,default_view:!compareMode,page_only:qaMode,search_active:!!$('find').value,ready:false,visible_text_elements:0};
 window.PDF_REPLICA_QA=record;publishCaptureRecord(record);$('paper').setAttribute('data-render-fingerprint',record.render_fingerprint||'');$('paper').setAttribute('data-qa-ready','false');
 if(typeof requestAnimationFrame!=='function')return;
 (async()=>{
  try{
   await new Promise(resolve=>requestAnimationFrame(resolve));
   if(document.fonts)await document.fonts.ready;
   await Promise.all([...$('paper').querySelectorAll('img')].map(im=>im.decode()));
   await Promise.all([...$('paper').querySelectorAll('image')].map(el=>{const im=new Image();im.src=el.getAttribute('href');return im.decode()}));
   await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
   if(window.PDF_REPLICA_QA!==record)return;
   const box=$('paper').getBoundingClientRect();record.paper_bbox={x:box.x,y:box.y,width:box.width,height:box.height};
   record.visible_text_elements=[...$('paper').querySelectorAll('text,[data-page-text]')].filter(el=>el.getBoundingClientRect().width>0&&getComputedStyle(el).visibility!=='hidden'&&getComputedStyle(el).opacity!=='0').length;
   record.ready=!data.layout_needs_sync;record.error=data.layout_needs_sync?'layout_text_not_synchronized':null;$('paper').setAttribute('data-qa-ready',String(record.ready));publishCaptureRecord(record);
  }catch(error){record.error='fonts_or_images_not_ready';record.ready=false;publishCaptureRecord(record)}
 })();
}
function render(data){
 if(qaMode)document.documentElement.style.setProperty('--qa-width',data.width+'px');
 const root=svg('svg',{viewBox:`0 0 ${data.width} ${data.height}`,width:data.width,height:data.height,'aria-label':'PDF page '+data.page});root.append(svg('rect',{x:0,y:0,width:data.width,height:data.height,fill:data.background_color||'white'}));
 for(const s of data.shapes||[])root.append(svg('path',{d:s.path,fill:s.fill||'none',stroke:s.stroke||'none','stroke-width':s.width||.5,'fill-opacity':s.fill_opacity??1,'stroke-opacity':s.stroke_opacity??1,'fill-rule':s.even_odd?'evenodd':'nonzero'}));
 const imageState=imagePolicy(data);
 for(const im of imageState.allowed){if(im.matrix)root.append(svg('image',{href:im.file,x:0,y:0,width:1,height:1,preserveAspectRatio:'none',transform:'matrix('+im.matrix.join(' ')+')'}));else{const b=im.bbox;root.append(svg('image',{href:im.file,x:b[0],y:b[1],width:b[2]-b[0],height:b[3]-b[1]}))}}
 for(const b of data.blocks||[]){addFont(b);const origin=b.origin||[b.bbox[0],b.bbox[3]],size=b.font_size||12;
  if(b.role==='form_field'&&/check|radio/i.test(b.field_type||'')){const r=b.bbox;root.append(svg('rect',{x:r[0],y:r[1],width:r[2]-r[0],height:r[3]-r[1],fill:'none',stroke:'#333','stroke-width':.7}));if(!/^(off|false|0)$/i.test(b.text))root.append(svg('path',{d:`M${r[0]+2} ${(r[1]+r[3])/2} L${(r[0]+r[2])/2} ${r[3]-2} L${r[2]-2} ${r[1]+2}`,fill:'none',stroke:'#222','stroke-width':1.2}));continue}
  const text=svg('text',{x:origin[0],y:origin[1],fill:b.color||'#222','font-size':size,'font-family':b.font_family||'Arial, Noto Sans CJK JP, Noto Sans, sans-serif','font-weight':b.bold?'700':'400','font-style':b.italic?'italic':'normal','xml:space':'preserve'});if(b.angle)text.setAttribute('transform',`rotate(${b.angle} ${origin[0]} ${origin[1]})`);if(b.advance>0&&!b.rtl){text.setAttribute('textLength',b.advance);text.setAttribute('lengthAdjust','spacingAndGlyphs')}if(b.rtl){text.setAttribute('direction','rtl');text.setAttribute('unicode-bidi','plaintext')};text.textContent=b.text;root.append(text)
 }
 if(data.web_layout)root.replaceChildren(svg('rect',{x:0,y:0,width:data.width,height:data.height,fill:data.background_color||'white'}),webLayout(data,imageState.allowed));
 let displayed=root;if(compareMode&&data.reference_image){displayed=document.createElement('img');displayed.className='reference-image';displayed.src=data.reference_image;displayed.alt='原 PDF 页面，仅用于对照'}
 $('paper').replaceChildren(displayed);$('compare').hidden=!data.reference_image;$('compare').textContent=compareMode?'返回网页文字':'对照原页';$('compare').setAttribute('aria-pressed',String(compareMode));$('textTitle').textContent=`第 ${data.page} 页 · 提取文字`;$('text').textContent=data.text||'本页未识别到文字。';$('caption').textContent=`PDF 第 ${data.page} 页 · ${compareMode?'原页对照':'网页元素排版 · 文字校对中'}`;
 if(data.kind==='blank'||data.status==='blank')notice('本页在原 PDF 中就是空白页，可点击“下一页”继续阅读。');else if(data.status==='needs_ocr')notice('本页仍需识别文字，并非已确认的空白页。请查看处理报告。');else if(data.status==='error')notice('本页处理失败，请查看诊断记录。');else notice('');if(imageState.withheld){const message='已隐藏未经确认的图片：扫描内容需要重建文字和排版，候选插图需要对照原件确认。';notice(($('notice').hidden?'':$('notice').textContent+' ')+message)}find();if(data.layout_needs_sync)notice('文字已更新，页面排版尚未同步，请继续校对。');markCaptureReady(data);
}
async function show(i){index=Math.min(doc.pages.length-1,Math.max(0,i));const serial=++token,p=doc.pages[index];window.PDF_REPLICA_QA={page:p.page,ready:false};publishCaptureRecord(window.PDF_REPLICA_QA);$('page').value=p.page;$('prev').disabled=index===0;$('next').disabled=index===doc.pages.length-1;notice('正在加载第 '+p.page+' 页…');window.scrollTo({top:0,left:0,behavior:'instant'});document.querySelector('main').scrollLeft=0;history.replaceState(null,'','#page='+p.page);try{const data=await load(p.page);if(serial!==token)return;render(data)}catch(e){if(serial===token){$('paper').replaceChildren();notice('Page '+p.page+' did not load. Reload to retry; its processing report contains any extraction errors.')}}}
function resize(){$('paper').style.width=zoom?zoom+'px':'min(100%,816px)'}function find(){const q=$('find').value.normalize('NFKC').toLowerCase();for(const t of $('paper').querySelectorAll('text,[data-page-text]'))t.classList.toggle('match',!!q&&t.textContent.normalize('NFKC').toLowerCase().includes(q))}
$('prev').onclick=()=>show(index-1);$('next').onclick=()=>show(index+1);$('page').onchange=()=>{const i=doc.pages.findIndex(p=>p.page===Number($('page').value));if(i<0){$('page').value=doc.pages[index].page;notice('该页不在已处理范围内。')}else show(i)};$('page').onkeydown=e=>{if(e.key==='Enter'){$('page').blur();$('page').onchange()}};$('minus').onclick=()=>{zoom=Math.max(280,(zoom||$('paper').clientWidth)-160);resize()};$('plus').onclick=()=>{zoom=Math.min(4000,(zoom||$('paper').clientWidth)+160);resize()};$('fit').onclick=()=>{zoom=0;resize()};$('find').oninput=find;
$('copy').onclick=async()=>{const d=window.PDF_PAGES[doc.pages[index].page];if(!d)return;try{await navigator.clipboard.writeText(d.text||'');$('copy').textContent='已复制';setTimeout(()=>$('copy').textContent='复制本页文字',1500)}catch(e){const r=document.createRange();r.selectNodeContents($('paper'));const s=getSelection();s.removeAllRanges();s.addRange(r);notice('本页文字已选中，请使用复制命令。')}};
window.addEventListener('keydown',e=>{if(/INPUT|TEXTAREA/.test(e.target.tagName)||e.ctrlKey||e.metaKey||e.altKey)return;if(e.key==='ArrowRight'){e.preventDefault();show(index+1)}else if(e.key==='ArrowLeft'){e.preventDefault();show(index-1)}});window.addEventListener('hashchange',()=>{const n=Number(location.hash.match(/page=(\d+)/)?.[1]);const i=doc.pages.findIndex(p=>p.page===n);if(i>=0)show(i)});const start=Number(location.hash.match(/page=(\d+)/)?.[1]);show(Math.max(0,doc.pages.findIndex(p=>p.page===start)));

$('compare').onclick=()=>{compareMode=!compareMode;const data=window.PDF_PAGES[doc.pages[index].page];if(data)render(data)};
$('textToggle').onclick=()=>{const panel=$('textPanel');panel.hidden=!panel.hidden;$('textToggle').setAttribute('aria-expanded',String(!panel.hidden));$('textToggle').textContent=panel.hidden?'查看文字':'隐藏文字'};
function searchAll(){const norm=s=>s.normalize('NFKC').replace(/\s+/g,'').toLowerCase(),q=norm($('find').value),out=$('searchResults');out.replaceChildren();out.hidden=!q;if(!q)return;const hits=(window.PDF_TEXT_INDEX||[]).filter(p=>norm(p.text).includes(q));const info=document.createElement('span');info.textContent=hits.length?`找到 ${hits.length} 页：`:'未找到匹配文字。OCR 可能有识别误差。';out.append(info);for(const p of hits){const b=document.createElement('button');b.textContent=`第 ${p.page} 页`;b.onclick=()=>show(doc.pages.findIndex(x=>x.page===p.page));out.append(b)}}
$('search').onclick=searchAll;$('find').onkeydown=e=>{if(e.key==='Enter')searchAll()};$('find').oninput=()=>{find();if(!$('find').value)searchAll()};
if(typeof ResizeObserver!=='undefined')new ResizeObserver(()=>document.documentElement.style.setProperty('--head-height',document.querySelector('header').offsetHeight+'px')).observe(document.querySelector('header'));
