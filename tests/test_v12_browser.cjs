'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const elements=new Map();
function el(id){if(!elements.has(id))elements.set(id,{id,value:'90',textContent:'',innerHTML:'',className:'',hidden:false,addEventListener(){},closest(){return null;}});return elements.get(id);}
const ctx={
 document:{getElementById:el,querySelector(){return {classList:{contains:()=>false}}}},
 window:{addEventListener(){},CampoLocation:{getPoint:()=>({latitude:-23.065,longitude:-54.19})}},
 console,Date,Math,Number,String,Array,Object,Map,Set,Intl,URL,URLSearchParams,AbortController,
 setTimeout,clearTimeout,fetch:async()=>{throw Error('offline')},clearPlot(){},chart(){},tableFill(){},Error
};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync('site/static/history_v10.js','utf8'),ctx);
const h=ctx.window.CampoHistoryV10._test;
const dates=Array.from({length:12},(_,i)=>`2026-10-${String(i+1).padStart(2,'0')}`);
const base={utc_offset_seconds:0,daily:{time:dates,precipitation_sum:Array(12).fill(0),temperature_2m_mean:Array(12).fill(25)}};
const bad={utc_offset_seconds:0,daily:{time:dates,precipitation_sum:Array(12).fill(null),temperature_2m_mean:Array(12).fill(25)}};
assert.throws(()=>h.parseDaily(bad),/chuva nula/);
assert.strictEqual(h.parseDaily(base)[0].precipitation_sum,0);
const land={utc_offset_seconds:0,daily:{time:dates,wind_gusts_10m_max:Array(12).fill(22),et0_fao_evapotranspiration:Array(12).fill(4)}};
const merged=h.mergeDailyBaseLand(base,land);
assert.strictEqual(h.parseDaily(merged)[0].wind_gusts_10m_max,22);
assert.strictEqual(h.parseDaily(merged)[0].et0_fao_evapotranspiration,4);
const shifted={utc_offset_seconds:0,daily:{time:[...dates].reverse(),wind_gusts_10m_max:Array(12).fill(20)}};
assert.throws(()=>h.mergeDailyBaseLand(base,shifted),/coincidem/);
const hourly={hourly:{time:dates.map(d=>d+'T12:00'),temperature_2m:Array(12).fill(24),relative_humidity_2m:Array(12).fill(68),precipitation:Array(12).fill(0),wind_speed_10m:Array(12).fill(5),vapour_pressure_deficit:Array(12).fill(.7)}};
const hourlyLand={hourly:{time:hourly.hourly.time,wind_gusts_10m:Array(12).fill(12)}};
assert.strictEqual(h.mergeHourlyBaseLand(hourly,hourlyLand).hourly.wind_gusts_10m[0],12);
assert.throws(()=>h.mergeHourlyBaseLand(hourly,{hourly:{time:[...hourly.hourly.time].reverse(),wind_gusts_10m:Array(12).fill(12)}}),/divergentes/);
vm.runInContext(fs.readFileSync('site/static/extended_v12.js','utf8'),ctx);
const seasonal=ctx.window.CampoExtendedV12._test.parse({
 weekly:{time:['2026-11-02'],precipitation_mean:[10.2],temperature_2m_mean:[27.3]},
 weekly_units:{precipitation_mean:'mm'},monthly:{time:['2026-11-01'],precipitation_mean:[90]}
});
assert.strictEqual(seasonal.weekly[0].p,10.2);
assert.throws(()=>ctx.window.CampoExtendedV12._test.parse({weekly:{time:['2026-11-02'],precipitation_mean:[null]}}),/nenhuma|válidos/i);
console.log('PASS v1.2: no fabricated rain, strict hourly/daily alignment, dynamic long-range with units.');
