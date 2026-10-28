'use strict';
/* Purely synthetic offline contract tests; weather values never enter site data. */
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const els=new Map();
const el=id=>{if(!els.has(id))els.set(id,{id,innerHTML:'',textContent:'',className:'',hidden:false,value:'',disabled:false,href:'',addEventListener(){}});return els.get(id);};
const context={
 document:{getElementById:el,querySelector(sel){if(sel==='.coord')return el('coord');if(sel==='button[data-tab="observations"]')return el('obs');return null;},querySelectorAll(){return [];}},
 window:{location:{href:'https://example.org/'},dispatchEvent(){}},sessionStorage:{getItem(){return null;},setItem(){},removeItem(){}},
 history:{replaceState(){}},navigator:{clipboard:{writeText:async()=>{}}},CustomEvent:class{},
 state:null,chart(){},clearPlot(){},tableFill(){},render(){},refresh(){},setRefreshFeedback(){},
 FORECAST_HOURLY:[],FORECAST_DAILY:[],FORECAST_CURRENT:[],fetch:async()=>({ok:false,status:503}),
 setTimeout,clearTimeout,AbortController,Date,Math,Number,String,Array,URL,URLSearchParams,Intl,Promise,Map,Set,Object,Error,console
};
vm.createContext(context);vm.runInContext(fs.readFileSync('site/static/location.js','utf8'),context);
const {computeModel,readJoint,mixJointEvent}=context.window.CampoLocation._test;
const utcMidnight=new Date();utcMidnight.setUTCHours(0,0,0,0);
const times=Array.from({length:168},(_,i)=>new Date(utcMidnight.valueOf()+i*3600000).toISOString().slice(0,16));
const precip=times.map((_,i)=>i);
const badGust=times.map(()=>null),goodGust=times.map(()=>10);
const payload={utc_offset_seconds:0,hourly:{time:times,precipitation_member01:precip,
 wind_gusts_10m_member01:badGust,wind_gusts_10m_member02:goodGust}};
const computed=computeModel(payload);
assert.equal(computed.member_rain_declared,1);
assert.equal(computed.member_gust_declared,2);
assert.equal(computed.member_gust,1,'only numerical complete day usable');
const futureTimes=Object.keys(computed.h);
assert.equal(futureTimes.length,72,'exactly 72 future start hours');
assert(futureTimes.every(t=>Date.parse(t+'Z')>Date.now()),'no past hours');
const first=futureTimes[0],index=times.indexOf(first);
assert.equal(computed.h[first][1][0],precip[index+1], 'rain starting at t is value ENDING t+1');
assert.equal(computed.h[first][3][0],precip[index+1]+precip[index+2]+precip[index+3]);
const h={time:times};for(const [key,v] of Object.entries({precipitation:0,temperature_2m:24,
 relative_humidity_2m:72,wind_speed_10m:5,wind_direction_10m:135,wind_gusts_10m:9}))h[key+'_member01']=times.map(()=>v);
const joint=readJoint({utc_offset_seconds:0,hourly:h});
assert(Object.keys(joint.times).every(t=>Date.parse(t+'Z')>Date.now()),'spray excludes past');
assert(Object.keys(joint.times).length<=72);
const mixed=mixJointEvent({MODEL:joint},'hour');
assert(mixed.length>0);
const night=mixed.find(r=>r.herb.indeterminado===1);
assert(night,'fixture includes at least one night hour');
assert.equal(night.herb.numeric_passa,1, 'inversion pending does not hide numerical screening');
assert.equal(night.herb.restrito,0);
console.log('PASS v1.8: actual future 72 hours, forward precipitation timing, valid members, independent operational uncertainty.');
