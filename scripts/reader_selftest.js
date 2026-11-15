'use strict';
// Run the actual reader against a minimal DOM; inspect rendered SVG image nodes.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class Element{
 constructor(tag='div'){this.tag=tag;this.children=[];this.attrs={};this.hidden=true;this.value='';this.textContent='';this.style={};this.classList={toggle(){}}}
 setAttribute(k,v){this.attrs[k]=v}
 getContext(){return {font:'',measureText:text=>({width:text.length*7})}}
 append(child){this.children.push(child)}
 replaceChildren(...children){this.children=children}
 querySelectorAll(tag){return this.children.flatMap(c=>[...(c.tag===tag?[c]:[]),...c.querySelectorAll(tag)])}
}
const elements=new Map(),get=id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id)};
const page={page:1,width:612,height:792,status:'draft',kind:'scan',blocks:[],shapes:[],images:[]};
const window={PDF_DOCUMENT:{title:'Synthetic raster regression',pages:[page]},PDF_PAGES:{1:page},scrollTo(){},addEventListener(){}};
const document={getElementById:get,createElementNS:(ns,tag)=>new Element(tag),createElement:tag=>new Element(tag),querySelector:()=>new Element(),head:new Element(),body:new Element()};
const context=vm.createContext({window,document,history:{replaceState(){}},location:{hash:''},setTimeout,console});
vm.runInContext(fs.readFileSync(require('node:path').join(__dirname,'../assets/reader.js'),'utf8'),context);
const fixture={...page,blocks:[{text:'Selectable source text',bbox:[20,20,200,40]}]};
function check(images,count){context.fixture={...fixture,images};vm.runInContext('render(fixture)',context);assert.equal(get('paper').querySelectorAll('image').length,count);assert.equal(get('paper').querySelectorAll('text')[0].textContent,'Selectable source text')}
const margin={file:'scan.png',bbox:[85.6,72,526.4,720]};
check([margin],0); // Legacy images have no trusted semantic role.
check([{...margin,role:'illustration',reviewed:true}],0); // Geometry still rejects a scan.
check([{file:'scan.png',matrix:[440.8,0,0,648,85.6,72],role:'illustration',reviewed:true}],0);
check([{file:'scan.png',bbox:[10,10,20,20],matrix:[440.8,0,0,648,85.6,72],role:'illustration',reviewed:true}],0);
check([margin,{file:'mascot.png',bbox:[20,20,50,50],role:'illustration',reviewed:true}],0);
check([{file:'tile1.png',bbox:[80,60,532,396],role:'illustration',reviewed:true},{file:'tile2.png',bbox:[80,396,532,732],role:'illustration',reviewed:true}],0);
check([{file:'mascot.png',bbox:[20,20,50,50]}],0);
check([{file:'mascot.png',bbox:[20,20,50,50],role:'illustration',reviewed:true}],1);
check([{file:'mascot.png',matrix:[0,30,-30,0,50,20],role:'illustration',reviewed:true}],1);
check([{file:'bad.png',matrix:['bad',0,0,1,0,0],role:'illustration',reviewed:true}],0);
check([{file:'reference.png',bbox:[20,20,50,50],role:'reference',reviewed:true}],0);
assert.equal(get('notice').hidden,false);
console.log('Passed reader regression: legacy/margin/matrix/tiled rasters withheld; approved artwork and selectable text retained.');

context.fixture={...fixture,reference_image:'reference-pages/001.webp',images:[{file:'mascot.png',bbox:[20,20,50,50],role:'illustration',reviewed:true}],web_layout:{elements:[{tag:'div',style:'position:absolute;left:10px;top:10px;width:100px;height:50px;background:#efefef',children:[{tag:'span',text:'Native label'}]},{tag:'img',image_file:'mascot.png'},{tag:'img',image_file:'page-scan.png'}],blocks:[{text:'Selectable web layout',x:.1,y:.2,w:.4,h:.03,size:12}]}};
vm.runInContext('render(fixture)',context);
assert.equal(get('paper').querySelectorAll('foreignObject').length,1);
assert.equal(get('paper').querySelectorAll('img').length,1);
assert.ok(get('paper').querySelectorAll('span').some(el=>el.textContent==='Selectable web layout'));
assert.equal(get('compare').attrs['aria-pressed'],'false');
assert.ok(!get('paper').querySelectorAll('img').some(el=>el.src==='reference-pages/001.webp'));
console.log('Passed native web-layout regression: HTML text and panels retained, artwork approved, source reference absent from default view.');
