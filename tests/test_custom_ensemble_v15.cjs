'use strict';
// Offline controlled API responses. These are tests only; fake meteorology never enters published data.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const els=new Map();
const el=id=>{if(!els.has(id))els.set(id,{value:'',textContent:'',innerHTML:'',className:'',hidden:false,disabled:false,href:'',dataset:{},addEventListener(){},setAttribute(){}});return els.get(id);};
const requests=[];
let policy='mixed';
const dateTimes=Array.from({length:7*24},(_,i)=>new Date(Date.UTC(2026,9,27,i)).toISOString().slice(0,16));
const resp=(url)=>{
 const u=new URL(url);const model=u.searchParams.get('models'),days=Number(u.searchParams.get('forecast_days')||7);
 const time=dateTimes.slice(0,days*24);
 if(policy==='429')return {ok:false,status:429,headers:{get:()=>null}};
 if(policy==='mixed'&& !['ecmwf_ifs025_ensemble','ncep_gefs_seamless'].includes(model))return {ok:false,status:503,headers:{get:()=>null}};
 if(policy==='fallback'&&model==='ecmwf_ifs025_ensemble'&&days===7){const e=Error('timeout');e.name='AbortError';throw e;}
 if(model!=='ecmwf_ifs025_ensemble'&&model!=='ncep_gefs_seamless')return {ok:false,status:503,headers:{get:()=>null}};
 const xs=Array(time.length).fill(model==='ecmwf_ifs025_ensemble'?1:2);
 return {ok:true,status:200,json:async()=>({latitude:-14.4,longitude:-56.4,hourly:{time,precipitation_member00:xs}})};
};
const ctx={
 document:{getElementById:el,querySelector(sel){if(sel==='.coord')return el('coord');if(sel==='button[data-tab="observations"]')return el('obs');return null;},querySelectorAll(){return [];}},
 window:{location:{href:'https://example.org/campo-e-clima/'},Plotly:null,dispatchEvent(){}},
 sessionStorage:{getItem(){return null;},setItem(){},removeItem(){}},navigator:{clipboard:{writeText:async()=>{}}},history:{replaceState(){}},
 state:null,chart(){},redrawActive(){},clearPlot(){},tableFill(){},setRefreshFeedback(){},render(){},refresh(){},
 FORECAST_HOURLY:[],FORECAST_DAILY:[],FORECAST_CURRENT:[],CustomEvent:class{},
 fetch:async url=>{requests.push(url);return resp(url);},setTimeout,clearTimeout,AbortController,Date,Math,Number,String,Array,URL,URLSearchParams,Intl,Promise,Map,Set,Error,Object,console
};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync('site/static/location.js','utf8'),ctx);
const {requestEnsembles,summarizeEnsembles,validEnsembleCount,usableModelRain}=ctx.window.CampoLocation._test;
(async()=>{
 let seen=[];
 const result=await requestEnsembles({latitude:-14.408,longitude:-56.446},1,(name,r)=>seen.push([name,Object.keys(r).length]));
 assert.equal(seen.length,8);
 assert.equal(validEnsembleCount(summarizeEnsembles(result)),2);
 assert.equal(requests.filter(url=>url.includes('ensemble-api')).length,8,'one rain request per model, not two heavy requests');
 assert(requests.filter(url=>url.includes('ensemble-api')).every(url=>new URL(url).searchParams.get('hourly')==='precipitation'));
 assert(requests.filter(url=>url.includes('ensemble-api')).every(url=>new URL(url).searchParams.get('latitude')==='-14.408'));
 assert.equal(usableModelRain({hourly:{time:dateTimes}}),null);
 assert.equal(validEnsembleCount(summarizeEnsembles({})),0);
 requests.length=0;policy='429';
 const limited=await requestEnsembles({latitude:-14.408,longitude:-56.446},1);
 assert.equal(validEnsembleCount(summarizeEnsembles(limited)),0);
 assert(requests.length<=2,'rate limited: do not continue eight calls');
 requests.length=0;policy='fallback';
 const partial=await requestEnsembles({latitude:-14.408,longitude:-56.446},1);
 assert.equal(validEnsembleCount(summarizeEnsembles(partial)),2);
 assert(requests.some(url=>new URL(url).searchParams.get('forecast_days')==='4'),'timeout fallback to 4 days');
 console.log('PASS custom coordinate ensembles: staged 7-day rain, partial model success, HTTP 429 stop, 4-day fallback, valid-only checks');
})().catch(e=>{console.error(e);process.exit(1)});
