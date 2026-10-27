'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const elements=new Map();function id(name){if(!elements.has(name))elements.set(name,{id:name,value:'',max:'',textContent:'',innerHTML:'',style:{},classList:{contains:()=>false},addEventListener(){}});return elements.get(name)}
const doc={readyState:'complete',hidden:false,getElementById:id,addEventListener(){}};
const point={latitude:-23.065,longitude:-54.19,name:'Naviraí'};
const windowStub={CampoLocation:{getPoint:()=>point},addEventListener(){},L:null};
const js=fs.readFileSync('site/static/maps_v14.js','utf8');
vm.runInNewContext(js,{document:doc,window:windowStub,console,setInterval,clearInterval,setTimeout,clearTimeout,Date,Intl,URLSearchParams,Math,Number,String,Set,Map,Array});
const test=windowStub.CampoMaps?._test;
assert.ok(test,'Public map testing helpers must be initialized');
assert.equal(test.transit(180),0,'Wind from south goes north');
assert.equal(test.cardinal(test.transit(45)),'SO','Wind from NE blows to SW');
assert.equal(test.cardinal(test.transit(270)),'E','Wind from west blows east (Leste)'); // labels used by compass are Portuguese
const g=test.forecastGrid(point);
assert.equal(g.a.length,9);assert.equal(g.b.length,9);
const ts=Array.from({length:48},(_,i)=>`2026-10-${String(27+Math.floor(i/24)).padStart(2,'0')}T${String(i%24).padStart(2,'0')}:00`);
const valid=g.a.map((lat,i)=>({latitude:Number(lat),longitude:Number(g.b[i]),hourly:{time:ts,cloud_cover:ts.map(()=>40),precipitation:ts.map(()=>0)}}));
const parsed=test.checkForecast(valid,point);assert.equal(parsed.points.length,9);
assert.equal(parsed.times.length,48);
assert.throws(()=>test.checkForecast(valid.slice(0,8),point),/nove pontos/);
const empty=structuredClone(valid);empty.forEach(x=>x.hourly.cloud_cover=x.hourly.cloud_cover.map(()=>null));assert.throws(()=>test.checkForecast(empty,point),/nuvens vazia/);
assert.notEqual(test.mapColor('cloud_cover',10),test.mapColor('cloud_cover',90));
assert.notEqual(test.mapColor('precipitation',0),test.mapColor('precipitation',12));
console.log('PASS maps v1.4: 9-point forecast, labels, non-fabrication and wind transport directions.');
