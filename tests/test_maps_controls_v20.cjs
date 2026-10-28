'use strict';
// Browser-independent test: fake radar tiles load asynchronously; clocks and API data are fake.
// No synthetic forecast is written to production data files.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const s=fs.readFileSync('site/static/maps_v14.js','utf8');
const dom=new Map();
function el(id){if(!dom.has(id))dom.set(id,{id,value:'',disabled:false,textContent:'',innerHTML:'',className:'',max:'',handlers:{},addEventListener(n,f){this.handlers[n]=f},classList:{contains:n=>n==='active'}});return dom.get(id);}
el('radar-mode').value='off';el('map-variable').value='precipitation';el('map-satellite').value='none';el('radar-speed').value='1800';el('map-opacity').value='.55';
const doc={readyState:'complete',hidden:false,getElementById:el,addEventListener(){}};
let fakeMap=null,activeLayers=new Set(),lastLayer=null;
class Layer{constructor(url){this.url=url;this.events={};this.opacity=0;this.loaded=false;}on(name,fn){this.events[name]=fn;return this;}addTo(map){activeLayers.add(this);this.map=map;lastLayer=this;setTimeout(()=>{this.loaded=true;this.events.load?.();},3);return this;}setOpacity(v){this.opacity=v;return this;}bringToFront(){return this;}setLatLng(){return this;}setPopupContent(){return this;}bindPopup(){return this;}bindTooltip(){return this;}}
class Group extends Layer{constructor(){super('group')}clearLayers(){return this;}}
const mapStub=()=>({setView(){return this;},removeLayer(l){activeLayers.delete(l);},hasLayer(l){return activeLayers.has(l);},on(){return this;},invalidateSize(){return this;},closePopup(){return this;}});
const L={map(){fakeMap=mapStub();return fakeMap;},tileLayer(url){return new Layer(url);},circleMarker(){return new Layer('point')},layerGroup(){return new Group()},divIcon(){return {}},marker(){return new Layer('arrow')}};
const clock=Date.now();const frames=Array.from({length:4},(_,i)=>({time:Math.floor(clock/1000)-(4-i)*600,path:'/v2/radar/'+String(1760000000+i*600)}));
const manifest={host:'https://tilecache.rainviewer.com',radar:{past:frames}};
function fakeFetch(url){if(String(url).includes('rainviewer'))return Promise.resolve({ok:true,json:()=>Promise.resolve(manifest)});return Promise.reject(Error('unexpected forecast fetch '+url));}
const fastTimeout=(fn,delay)=>setTimeout(fn,delay>=1400&&delay<=6000?25:delay);
let selector={latitude:-23.065,longitude:-54.190,name:'Naviraí'};
const win={L,CampoLocation:{getPoint:()=>selector},addEventListener(){}};
vm.runInNewContext(s,{document:doc,window:win,L,fetch:fakeFetch,setTimeout:fastTimeout,clearTimeout,setInterval,clearInterval,AbortController,Date,Intl,URL,URLSearchParams,Math,Number,String,Set,Map,Array,console});
const test=win.CampoMaps._test;
assert.equal(test.numericLegend('precipitation').unit,'mm/h');
assert.equal(test.numericLegend('temperature_2m').unit,'°C');
assert.equal(test.numericLegend('cape').unit,'J/kg');
assert.match(test.radarLegend(),/dBZ/);assert.match(test.radarLegend(),/não mm\/h/);
assert.equal(test.parseRadarManifest(manifest).frames.length,4);
assert.equal(test.parseRadarManifest({host:'https://tilecache.rainviewer.com',radar:{past:[{time:1793220000,path:'/v2/radar/5d8dd77f900f'}]}}).frames.length,1);
assert.throws(()=>test.parseRadarManifest({host:'https://not-trusted.example',radar:{past:frames}}),/não autorizado/);
const time=test.frameLabel(frames[0],0);assert.match(time,/UTC/);assert.match(time,/local/);
(async()=>{
  // Display map without a forecast call by switching to radar first.
  el('radar-mode').value='rainviewer';win.CampoMaps.open();
  await new Promise(r=>setTimeout(r,45));
  assert.equal(el('radar-frame').max,'3');assert.equal(el('radar-frame').value,'3');
  assert.match(el('map-product-source').textContent,/RADAR OBSERVADO/);
  assert.match(el('map-product-legend').innerHTML,/dBZ/);
  el('radar-play').handlers.click();
  await new Promise(r=>setTimeout(r,30));
  assert.notEqual(el('radar-frame').value,'3','play from newest must restart at oldest');
  const first=Number(el('radar-frame').value);
  await new Promise(r=>setTimeout(r,35));
  assert.ok(Number(el('radar-frame').value)>first,'loaded frame should advance automatically');
  assert.match(el('radar-frame-time').textContent,/UTC/);
  el('radar-next').handlers.click();assert.match(el('radar-play').textContent,/Reproduzir/);
  // Switching to future must hide radar and restore forecast legend.
  el('radar-mode').value='off';el('radar-mode').handlers.change();
  assert.match(el('map-product-source').textContent,/PREVISÃO FUTURA/);
  assert.match(el('map-product-legend').innerHTML,/mm\/h/);
  assert.equal(el('map-satellite').disabled,false);
  console.log('PASS map v2.0 playback: timed steps, prefetch, independent source labels, UTC/local and dBZ legend');
})().catch(e=>{console.error(e);process.exitCode=1;});
