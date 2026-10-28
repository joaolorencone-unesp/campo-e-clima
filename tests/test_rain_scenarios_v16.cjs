'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {bands, modelAgreement} = require('../site/static/rain_scenarios.js');
function close(x,y){assert(Math.abs(x-y) < 1e-10,`${x} !== ${y}`);}
const row={p_gt_0_1_mm:0.8,p_gt_1_mm:0.3,p_gt_5_mm:0.1};
const b=bands(row);
close(b.almostDry,0.2);close(b.veryLight,0.5);close(b.light,0.2);close(b.higher,0.1);
close(Object.values(b).reduce((a,x)=>a+x,0),1);
assert.deepEqual(bands({p_gt_0_1_mm:0,p_gt_1_mm:0,p_gt_5_mm:0}),{almostDry:1,veryLight:0,light:0,higher:0});
assert.deepEqual(bands({p_gt_0_1_mm:1,p_gt_1_mm:1,p_gt_5_mm:1}),{almostDry:0,veryLight:0,light:0,higher:1});
assert.equal(bands({p_gt_0_1_mm:0.5,p_gt_1_mm:0.6,p_gt_5_mm:0.3}),null,'monotonicity');
assert.equal(bands({p_gt_1_mm:0.2,p_gt_5_mm:0.1}),null,'missing threshold is not zero');
assert.equal(bands({p_gt_0_1_mm:0.2,p_gt_1_mm:null,p_gt_5_mm:0.1}),null,'null is not zero');
assert.equal(bands({p_gt_0_1_mm:NaN,p_gt_1_mm:0.1,p_gt_5_mm:0.05}),null);
const x=[
 {model:'ECMWF IFS',date:'2026-10-27',members:50,p_gt_0_1_mm:0.7,p_gt_1_mm:0.25,p_gt_5_mm:0.1},
 {model:'NOAA GEFS',date:'2026-10-27',members:30,p_gt_0_1_mm:0.8,p_gt_1_mm:0.5,p_gt_5_mm:0.2},
 {model:'OTHER',date:'2026-10-28',members:10,p_gt_0_1_mm:0.8,p_gt_1_mm:0.4,p_gt_5_mm:0.1},
 {model:'INVALID',date:'2026-10-27',members:0,p_gt_0_1_mm:0.8,p_gt_1_mm:0.4,p_gt_5_mm:0.1}
];
const agreement=modelAgreement(x,'2026-10-27');
assert.equal(agreement.length,2);
close(agreement[0].veryLight,0.45);
assert.equal(agreement[1].members,30);
const html=fs.readFileSync('site/index.html','utf8'),js=fs.readFileSync('site/static/app.js','utf8'),collect=fs.readFileSync('scripts/collect.py','utf8'),client=fs.readFileSync('site/static/location.js','utf8');
for(const id of ['rain-bands-plot','rain-model-agreement','rain-agreement-day','rain-trace-insight'])assert(html.includes('id="'+id+'"'),id);
const helper=html.match(/rain_scenarios\.js\?v=\d+/)?.[0],main=html.match(/app\.js\?v=\d+/)?.[0];
assert(helper && main && html.indexOf(helper)<html.indexOf(main),'helper loaded before UI');
assert(js.includes("'≤0,1 mm','>0,1 mm','0,1–1 mm','>1 mm'"),'daily table shows all three');
assert(js.includes("'Freq. 3h >0,1'")&&js.includes("'Freq. 6h >0,1'"),'windows show trace');
assert(js.includes("name:'Freq. >0,1 mm/h'"),'hourly graph displays trace');
assert(collect.includes("'p_gt_0_1_mm':round(sum(x>0.1"),'python backend model comparison');
assert(client.includes('p_gt_0_1_mm:values.filter(v=>v>0.1)'),'custom location comparison');
console.log('PASS: exclusive bands, missing data, model agreement, UI thresholds, both collectors');
