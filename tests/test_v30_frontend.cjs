'use strict';
/* Offline contract tests for v3 modules: farm summary, navigation modes, rain products formatters.
 * Synthetic values only; nothing here is written to site/data. */
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
function load(file,extra={}){const ctx={window:{},console,Date,Math,Number,String,Array,Object,Map,Set,Intl,URL,URLSearchParams,JSON,...extra};ctx.window=ctx;vm.createContext(ctx);vm.runInContext(fs.readFileSync(file,'utf8'),ctx);return ctx;}
// ---------- farm summary ----------
const summary=load('site/static/farm_summary_v30.js').CampoSummary;
const now=Date.parse('2026-11-05T18:30:00Z'); // 14:30 local (UTC-4): after noon the summary focuses on tomorrow
const times=Array.from({length:96},(_,i)=>new Date(Date.UTC(2026,10,5,4)+i*3600000).toISOString().slice(0,16)); // local 00:00 Nov 5 onwards, labelled local
const localTimes=times.map(t=>new Date(Date.parse(t+'Z')-4*3600000).toISOString().slice(0,16));
const h={time:localTimes,temperature_2m:localTimes.map((_,i)=>22+10*Math.sin(i/24*Math.PI*2)),relative_humidity_2m:localTimes.map(()=>70),wind_speed_10m:localTimes.map((_,i)=>i%7===0?20:8),wind_gusts_10m:localTimes.map((_,i)=>i%7===0?45:18),precipitation:localTimes.map((_,i)=>i>=30&&i<36?2:0),vapour_pressure_deficit:localTimes.map(()=>1),wind_direction_10m:localTimes.map(()=>90)};
const state={site:{id:'navirai',timezone:'America/Campo_Grande',utc_offset_seconds:-14400},issued_at_utc:'2026-11-05T12:00:00Z',
 deterministic:{hourly:h,current:{temperature_2m:24.5,relative_humidity_2m:80,wind_speed_10m:7},collected_at_utc:'2026-11-05T12:10:00Z',utc_offset_seconds:-14400},
 ensemble_models:{A:{state:'ok',precipitation_members:50,collected_at_utc:'2026-11-05T06:00:00Z'},B:{state:'ok',precipitation_members:30,collected_at_utc:'2026-11-05T11:00:00Z'},C:{state:'error'}},
 rain_ensemble_daily:[{date:'2026-11-05',p50_mm:1,p10_mm:0,p90_mm:6,p_gt_1_mm:.45,p_gt_20_mm:.05,model_count:2},{date:'2026-11-06',p50_mm:14,p10_mm:3,p90_mm:30,p_gt_1_mm:.86,p_gt_20_mm:.35,model_count:2}],
 rain_ensemble_hourly:[{time:localTimes[15],windows:{'6':{p_gt_1_mm:.62,mean_mm:3.1,models:2}}}],
 rain_ensemble_accumulated:[{span_days:3,p50_mm:20,p10_mm:5,p90_mm:40,p_gt_25_mm:.3,model_count:2},{span_days:7,p50_mm:48,p10_mm:12,p90_mm:90,p_gt_25_mm:.8,model_count:2}],
 rain_model_agreement_daily:[{date:'2026-11-06',models:8,wet_majority_models:7,dry_majority_models:1,agreement_fraction:.875,agreement_label:'alta',side:'chuva',model_mean_min_mm:3,model_mean_max_mm:19,model_mean_median_mm:11,volume_spread_label:'alta',wet_threshold_mm:1}],
 gust_ensemble_daily:[{date:'2026-11-05',p_gt_30_kmh:.4,p_gt_40_kmh:.35,model_count:3}],
 rain_dry_spell:{p_ge_5_days:.1,p_ge_3_days:.3,dry_day_threshold_mm:1,end:'2026-11-10'},
 agro_ensemble_hourly:[{time:localTimes[12],variables:{temperature_2m:{p90:36,p_ge_35:.4},vpd_kpa:{p_ge_2_5:.1}}}],
 official:{inmet_alerts:{municipal_alerts:[{id:'1'}]},inmet_hourly_nearby:{state:'ok',station_name:'ITAQUIRAI',station_code:'A752',distance_km:42.8,records:[{valid_at_utc:'2026-11-05T17:00',temperature_c:21.3,rh_pct:90,precipitation_previous_hour_mm:0.2}]}},
 freshness:{models_with_newer_run_pending:['A']}};
const s=summary.build(state,now);
assert.equal(s.ready,true);
assert.equal(s.cards.length,6);
assert.match(s.headline,/Chuva provável/);
assert.equal(s.cards.find(c=>c.key==='rain6').value,'62% dos membros');
assert.match(s.cards.find(c=>c.key==='rain6').note,/não é probabilidade calibrada/);
assert.match(s.cards.find(c=>c.key==='rain7').value,/48 mm/);
assert.match(s.cards.find(c=>c.key==='rain24').detail,/Amanhã: mediana 14,0 mm/);
assert.ok(s.risks.some(r=>r.kind==='heavy_rain'&&/06\/11/.test(r.text)),'heavy rain risk from p_gt_20>=0.3');
assert.ok(s.risks.some(r=>r.kind==='gust'));
assert.ok(s.risks.some(r=>r.kind==='heat'));
assert.ok(s.risks.some(r=>r.kind==='inmet'));
assert.ok(!s.risks.some(r=>r.kind==='dry'),'dry spell below threshold must not be listed');
assert.match(s.sentences[0],/elevada concordância entre os modelos quanto à ocorrência de chuva amanhã \(7 de 8/);
assert.match(s.sentences[0],/grande dispersão no volume/);
assert.match(s.sentences.find(t=>t.startsWith('Dados:')),/ensembles de 2\/3 modelos/);
assert.match(s.sentences.find(t=>t.startsWith('Dados:')),/Há rodada mais nova anunciada para: A/);
assert.equal(s.freshness.ensemble_oldest_age_min,750);
assert.ok(s.observed&&s.observed.code==='A752'&&s.observed.age_min===90);
assert.ok(s.windows.length>=1&&s.windows[0].hours>=2,'at least one lower-restriction window');
assert.ok(s.windows.every(w=>Number(w.start.slice(11,13))>=6),'windows start in daytime');
// Before noon the same state focuses on today (45% of members >1 mm): a divided picture, not 'provável'.
const morning=summary.build(state,Date.parse('2026-11-05T12:30:00Z'));
assert.match(morning.headline,/modelos divididos/);assert.match(morning.cards.find(c=>c.key==='rain24').detail,/Hoje: mediana 1,0 mm/);
const empty=summary.build({},now);assert.equal(empty.ready,false);assert.match(empty.headline,/Sem previsão/);
const noEnsemble=summary.build({...state,rain_ensemble_daily:[],rain_ensemble_hourly:[],rain_ensemble_accumulated:[],rain_model_agreement_daily:[],gust_ensemble_daily:[],agro_ensemble_hourly:[],ensemble_models:{},rain_dry_spell:null,official:{}},now);
assert.equal(noEnsemble.cards.find(c=>c.key==='rain7').value,'—','no accumulation is not zero');
assert.match(noEnsemble.headline,/determinística/);
// ---------- navigation ----------
const navStore={};const nav=load('site/static/nav_v30.js',{localStorage:{getItem:k=>navStore[k]??null,setItem:(k,v)=>{navStore[k]=v;}}}).CampoNav;
assert.equal(nav.groupFor('spray'),'operations');assert.equal(nav.groupFor('precision'),'science');assert.equal(nav.groupFor('extended'),'rain');
const allTabs=new Set(nav.GROUPS.flatMap(g=>g.tabs));
const html=fs.readFileSync('site/index.html','utf8');
for(const tab of [...html.matchAll(/data-tab="([a-z-]+)"/g)].map(m=>m[1]))assert.ok(allTabs.has(tab),'tab without group: '+tab);
assert.ok(nav.visibleTabs('simple').includes('overview')&&!nav.visibleTabs('simple').includes('precision'));
assert.equal(nav.visibleTabs('advanced').length,allTabs.size);
assert.equal(nav._test.readMode({getItem:()=>'advanced'}),'advanced');assert.equal(nav._test.readMode({getItem:()=>'weird'}),null);
// ---------- rain products formatters ----------
const rp=load('site/static/rain_products_v30.js').CampoRainProducts;
assert.match(rp._test.describeChange({delta_p50_mm:10,p50_before_mm:2,p50_now_mm:12,delta_p_gt_1:.4,p_gt_1_before:.5,p_gt_1_now:.9}),/mediana \+10,0 mm \(2,0 → 12,0\); freq. >1 mm \+40 p\.p\./);
assert.match(rp._test.agreementBadge({agreement_label:'alta',side:'chuva'}),/Alta · chuva/);
// ---------- markup contract ----------
assert.ok(html.includes('id="farm-summary"')&&html.includes('id="mode-switch"')&&html.includes('id="nav-groups"'));
for(const id of ['rain-accumulated-body','rain-dry-spell','rain-agreement-daily','run-change','rain-hour-resolution-note','freshness-body','freshness-summary','diagnostics-panel','agro-ensemble-panel'])assert.ok(html.includes(`id="${id}"`),'missing '+id);
const order=['static/agro_ensemble_v23.js','static/farm_summary_v30.js','static/app.js','static/location.js','static/rain_products_v30.js','static/diagnostics_v30.js','static/nav_v30.js'].map(x=>html.indexOf(x));
assert.ok(order.every((v,i)=>v>0&&(i===0||v>order[i-1])),'v3 scripts must load in order around app.js');
assert.ok(!/OPENWEATHER_FREE_API_KEY|INMET_API_TOKEN/.test(fs.readFileSync('site/static/farm_summary_v30.js','utf8')+fs.readFileSync('site/static/diagnostics_v30.js','utf8')));
console.log('PASS v3.0 frontend: farm summary sentences, risks, freshness, modes/groups, rain product formatters, markup.');
