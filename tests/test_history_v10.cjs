'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const elements=new Map();
function el(id){if(!elements.has(id))elements.set(id,{id,value:'90',textContent:'',innerHTML:'',className:'',hidden:false,addEventListener(){},closest(){return null;}});return elements.get(id);}
const ctx={
 document:{getElementById:el,querySelector(){return {classList:{contains:()=>false}}}},
 window:{addEventListener(){},CampoLocation:{getPoint:()=>({latitude:-23.065,longitude:-54.19})}},
 console,Date,Math,Number,String,Array,Object,Map,Set,Intl,URL,URLSearchParams,AbortController,
 setTimeout,clearTimeout,fetch:async()=>{throw Error('offline: no data requests during tests')},
 clearPlot(){},chart(){},redrawActive(){},tableFill(){},Blob:class Blob{},Error
};
vm.createContext(ctx);vm.runInContext(fs.readFileSync('site/static/history_v10.js','utf8'),ctx);
const {parseDaily,parseHourly,screenHour,screenDays,pairedSummary,haversine}=ctx.window.CampoHistoryV10._test;
const d=parseDaily({timezone:'UTC',utc_offset_seconds:0,daily:{time:Array.from({length:12},(_,i)=>`2026-10-${String(i+1).padStart(2,'0')}`),precipitation_sum:Array(12).fill(5)}});
assert.strictEqual(d.length,12);assert.strictEqual(d[0].precipitation_sum,5);
assert.throws(()=>parseDaily({timezone:'UTC',daily:{time:['2026-10-01'],precipitation_sum:[0]}}),/histórico/);
const base={time:'2026-10-01T11:00',temperature_2m:24,relative_humidity_2m:80,vapour_pressure_deficit:.6,wind_speed_10m:6,wind_gusts_10m:13,precipitation:0};
assert.strictEqual(screenHour(base),'candidato');
assert.strictEqual(screenHour({...base,wind_gusts_10m:25}),'restritivo');
assert.strictEqual(screenHour({...base,wind_speed_10m:9}),'marginal');
assert.strictEqual(screenHour({...base,vapour_pressure_deficit:null,relative_humidity_2m:null}),'indeterminado');
assert.strictEqual(screenHour({...base,time:'2026-10-01T22:00'}),'fora_periodo_diurno');
const hourly={hourly:{time:Array.from({length:25},(_,i)=>`2026-10-01T${String(i%24).padStart(2,'0')}:00`),temperature_2m:Array(25).fill(24),relative_humidity_2m:Array(25).fill(80),vapour_pressure_deficit:Array(25).fill(.7),wind_speed_10m:Array(25).fill(5),wind_gusts_10m:Array(25).fill(12),precipitation:Array(25).fill(0)}};
assert.strictEqual(parseHourly(hourly).length,25);
const daily=screenDays(parseHourly(hourly));
assert.strictEqual(daily.length,1);
assert.strictEqual(daily[0].candidato,11);
const summary=pairedSummary([{date:'2026-10-01',PRECTOTCORR:3},{date:'2026-10-02',PRECTOTCORR:4}], [{date:'2026-10-01',precipitation_sum:2},{date:'2026-10-02',precipitation_sum:2}]);
assert.strictEqual(summary.n,2);assert.strictEqual(summary.meanDifference,1.5);
assert(haversine(-23.065,-54.19,-23.065,-54.19)<0.001);
console.log('PASS v1.0: UTC history, daily series, NASA/ERA5 pairing, daytime meteorological screening, station distance.');
