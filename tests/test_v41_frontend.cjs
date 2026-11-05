'use strict';
/* Offline contract test for the v4.1 agro indices card and markup. Synthetic values only. */
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
function load(file,extra={}){const ctx={window:{},console,Date,Math,Number,String,Array,Object,Map,Set,Intl,URL,URLSearchParams,JSON,...extra};ctx.window=ctx;vm.createContext(ctx);vm.runInContext(fs.readFileSync(file,'utf8'),ctx);return ctx;}
const idx=load('site/static/agro_indices_v40.js').CampoAgroIndices;
const now=Date.parse('2026-07-10T15:00:00Z');
const days=Array.from({length:8},(_,k)=>new Date(Date.UTC(2026,6,10+k)).toISOString().slice(0,10));
const hours=[];for(const d of days.slice(0,3))for(let h=0;h<24;h++)hours.push(`${d}T${String(h).padStart(2,'0')}:00`);
const state={site:{utc_offset_seconds:-14400},deterministic:{daily:{time:days,temperature_2m_max:[22,18,15,20,24,26,27,28],temperature_2m_min:[8,4,2,6,10,12,13,14]},hourly:{time:hours,temperature_2m:hours.map((_,i)=>(i%24<8?5:18))}},
 agro_ensemble_hourly:[{time:days[2]+'T05:00',variables:{temperature_2m:{p10:0.5,p_le_5:.8,p_le_3:.5,p_le_1:.25,models:5}}},{time:days[1]+'T04:00',variables:{temperature_2m:{p10:3,p_le_5:.4,p_le_3:.1,p_le_1:0}}},{time:days[1]+'T14:00',variables:{temperature_2m:{p10:10,p_le_5:0,p_le_3:0,p_le_1:0}}}]};
const f=idx.frost(state,now);
assert.equal(f.level,'alto');assert.equal(f.worst.date,days[2]);assert.equal(f.coldest.tmin,2);
assert.equal(idx.frost({...state,agro_ensemble_hourly:[],deterministic:{daily:{time:days,temperature_2m_max:[25,25,25,25,25,25,25,25],temperature_2m_min:[12,12,12,12,12,12,12,12]}}},now).level,'sem sinal');
const g=idx.degreeDays(state,10,now);
assert.equal(g.n,7);assert.equal(Math.round(g.total*10)/10,Math.round(((15-10)+(11-10)+0+(13-10)+(17-10)+(19-10)+(20-10))*10)/10);
assert.equal(idx.chillHours(state,now).hours,24,'8 cold hours per day over the three forecast days');
const page=fs.readFileSync('site/index.html','utf8');
for(const id of ['agro-indices-card','gdd-base','merge-panel','merge-image'])assert.ok(page.includes(`id="${id}"`),'missing '+id);
assert.ok(page.includes('GOES-East_ABI_FireTemp')&&page.includes('GOES-East_ABI_Band2_Red_Visible_1km')&&!page.includes('GLM')&&page.includes('agro_indices_v40.js'));
const ci=fs.readFileSync('.github/workflows/pages.yml','utf8');assert.ok(/repository_dispatch:\s*\n\s*types: \[collect\]/.test(ci),'external trigger');
console.log('PASS v4.1: frost/degree-days/chill indices, markup, external trigger');
