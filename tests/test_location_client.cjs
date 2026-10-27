'use strict';
/* Offline mock test. Fake responses are not bundled with site or deployed as forecasts. */
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const els=new Map();function el(id){if(!els.has(id))els.set(id,{id,value:'',textContent:'',innerHTML:'',className:'',hidden:false,disabled:false,href:'',dataset:{},addEventListener(){},setAttribute(){}});return els.get(id);}
const context={
 document:{getElementById:el,querySelector(sel){if(sel==='.coord')return el('coord');if(sel==='button[data-tab="observations"]')return el('obs-button');return null;},querySelectorAll(){return [];}},
 window:{location:{href:'https://example.org/campo-e-clima/'},Plotly:null},
 sessionStorage:{getItem(){return null;},setItem(){},removeItem(){}},
 navigator:{clipboard:{writeText:async()=>{}}},history:{replaceState(){}},
 state:null,chart(){},redrawActive(){},clearPlot(){},tableFill(){},
 setRefreshFeedback(){},render(){},refresh(){},FORECAST_HOURLY:[],FORECAST_DAILY:[],FORECAST_CURRENT:[],
 fetch:async()=>{throw Error('offline test — no network request allowed')},
 setTimeout,clearTimeout,Date,Math,Number,String,Array,URL,URLSearchParams,Intl,Promise,Map,Set,Error,Object,console
};
vm.createContext(context);vm.runInContext(fs.readFileSync('site/static/location.js','utf8'),context);
const {validate,parseNASA,computeModel,summarizeEnsembles,weightedQuantile}=context.window.CampoLocation._test;
assert.strictEqual(validate(-14.408,-56.446).latitude,-14.408);
assert.throws(()=>validate(95,12),/Latitude/);
assert.throws(()=>validate(10,-181),/longitude/);
const fields={PRECTOTCORR:{},T2M:{}};
for(let i=0;i<100;i++){const day=new Date(Date.UTC(2025,0,1+i)).toISOString().slice(0,10).replaceAll('-','');fields.PRECTOTCORR[day]=i===0?-999:1.5;fields.T2M[day]=24;}
const nasa=parseNASA({properties:{parameter:fields}},{latitude:-23,longitude:-54});
assert.strictEqual(nasa.records.length,100);assert.strictEqual(nasa.records[0].PRECTOTCORR,null);assert.strictEqual(nasa.records[1].PRECTOTCORR,1.5);
const dates=Array.from({length:168},(_,i)=>new Date(Date.UTC(2026,9,27,i)).toISOString().slice(0,16));
const eA={latitude:-23,longitude:-54,hourly:{time:dates,precipitation_member00:Array(168).fill(0),precipitation_member01:Array(168).fill(2),wind_gusts_10m_member00:Array(168).fill(20),wind_gusts_10m_member01:Array(168).fill(40)}};
const eB={latitude:-23,longitude:-54,hourly:{time:dates,precipitation_member00:Array(168).fill(1),wind_gusts_10m_member00:Array(168).fill(30)}};
const cA=computeModel(eA),cB=computeModel(eB);
assert.strictEqual(cA.member_rain,2);assert.strictEqual(cB.member_rain,1);
const out=summarizeEnsembles({A:{payload:eA,computed:cA},B:{payload:eB,computed:cB}});
assert.strictEqual(out.rain_ensemble_daily[0].model_count,2);
assert.strictEqual(out.rain_ensemble_daily[0].member_count,3);
assert(Math.abs(out.rain_ensemble_daily[0].mean_mm-24)<1e-8,'Equal MODEL weighting: model A mean24, model B mean24');
assert.strictEqual(out.gust_ensemble_daily[0].model_count,2);
assert.strictEqual(out.rain_ensemble_hourly[0].windows['3'].model_count||out.rain_ensemble_hourly[0].windows['3'].models,2);
assert.strictEqual(weightedQuantile([[0,.5],[20,.5]],.5),0);
const {readJoint,mixJointEvent}=context.window.CampoLocation._test;
const shortDates=Array.from({length:7},(_,i)=>`2026-10-27T${String(i+9).padStart(2,'0')}:00`);const jh={time:shortDates};
const six=['temperature_2m','relative_humidity_2m','wind_speed_10m','wind_gusts_10m','wind_direction_10m','precipitation'];
const nums={temperature_2m:25,relative_humidity_2m:80,wind_speed_10m:6,wind_gusts_10m:15,wind_direction_10m:135,precipitation:0};
for(const key of six){jh[key+'_member00']=Array(7).fill(nums[key]);jh[key+'_member01']=Array(7).fill(nums[key]);}
jh.wind_gusts_10m_member00[1]=30;
const joint=readJoint({hourly:jh});assert.strictEqual(joint.members_available,2);
const hourly=mixJointEvent({A:joint},'hour'),win=mixJointEvent({A:joint},'window');
assert.strictEqual(hourly[0].herb.passa,1);
assert.strictEqual(hourly[1].herb.restrito,.5);
assert.strictEqual(win[0].herb.passa,.5,'Same member must meet filters for two consecutive hours');
assert.strictEqual(win[0].herb.restrito,.5);
const nightDates=Array.from({length:7},(_,i)=>new Date(Date.UTC(2026,9,27,19+i)).toISOString().slice(0,16));
const nightH={time:nightDates};for(const key of six)nightH[key+'_member00']=Array(7).fill(nums[key]);
assert.strictEqual(mixJointEvent({A:readJoint({hourly:nightH})},'hour')[0].herb.indeterminado,1);
console.log('PASS coordinate bounds, NASA missingness, ensemble weighting, joint 2h spraying windows.');
