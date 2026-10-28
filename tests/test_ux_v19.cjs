'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const w={};
vm.runInNewContext(fs.readFileSync('site/static/alerts_v19.js','utf8'),{window:w});
const notices=[{type:'Tempestade',severity:'Perigo Potencial',start_date_source:'2026-10-28',end_date_source:'2026-10-28',start_hour_source:'00:00',end_hour_source:'23:59',risks:['vento','chuva']},
{type:'Tempestade',severity:'Perigo Potencial',start_date_source:'2026-10-29',end_date_source:'2026-10-29',start_hour_source:'00:00',end_hour_source:'23:59',risks:['vento','chuva']},
{type:'Chuvas Intensas',severity:'Perigo',start_date_source:'2026-10-28',end_date_source:'2026-10-30',risks:['alagamento']}];
const groups=w.CampoAlerts.group(notices);
assert.equal(groups.length,2);
assert.equal(groups[0].items.length,2);
assert.equal(groups[0].start,'2026-10-28');
assert.equal(groups[0].end,'2026-10-29');
assert.match(w.CampoAlerts.render(notices),/aviso\(s\) oficial\(is\)/);
assert.match(w.CampoAlerts.render(notices),/<details>/);
const el={value:'off',max:'',classList:{contains:()=>false},addEventListener(){}};
const doc={readyState:'complete',hidden:false,getElementById:()=>({...el}),addEventListener(){}};
const win={CampoLocation:{getPoint:()=>({latitude:-23.065,longitude:-54.19})},addEventListener(){}};
vm.runInNewContext(fs.readFileSync('site/static/maps_v14.js','utf8'),{window:win,document:doc,setTimeout,clearTimeout,setInterval,clearInterval,Date,Intl,Math,Number,String,Map,Set,URL,URLSearchParams,AbortController});
const parse=win.CampoMaps._test.parseRadarManifest;
const radar=parse({host:'https://tilecache.rainviewer.com',radar:{past:[{time:1793210400,path:'/v2/radar/8b5b1da88d5c'}],nowcast:[]}});
assert.equal(radar.frames.length,1);
assert.equal(radar.frames[0].path,'/v2/radar/8b5b1da88d5c');
assert.throws(()=>parse({host:'https://evil.example',radar:{past:[{time:1793210400,path:'/v2/radar/8b5b1da88d5c'}]}}),/autorizado/);
assert.throws(()=>parse({host:'https://tilecache.rainviewer.com',radar:{past:[{time:1,path:'/v2/radar/../../attack'}]}}),/não forneceu imagens/);
console.log('PASS v1.9: grouped alerts, official source display, observed radar manifest validation');
