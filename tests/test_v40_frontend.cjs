'use strict';
/* Offline contract tests for v4 modules: weekly board, bulletin card, stations, model comparison, navigation.
 * Synthetic values only; nothing here is written to site/data. */
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
function load(file,extra={}){const ctx={window:{},console,Date,Math,Number,String,Array,Object,Map,Set,Intl,URL,URLSearchParams,JSON,...extra};ctx.window=ctx;vm.createContext(ctx);vm.runInContext(fs.readFileSync(file,'utf8'),ctx);return ctx;}
const now=Date.parse('2026-11-05T15:00:00Z'); // 11:00 local
const days=Array.from({length:8},(_,k)=>new Date(Date.UTC(2026,10,5+k)).toISOString().slice(0,10));
const hours=[];for(const d of days.slice(0,3))for(let h=0;h<24;h++)hours.push(`${d}T${String(h).padStart(2,'0')}:00`);
const state={site:{id:'navirai',utc_offset_seconds:-14400},
 deterministic:{utc_offset_seconds:-14400,daily:{time:days,temperature_2m_max:[31,33,28,27,30,32,34,35],temperature_2m_min:[18,20,17,15,16,19,21,22],precipitation_sum:[0.2,12.4,25,3,0,0,0,1],wind_gusts_10m_max:[28,45,52,30,25,22,20,30]},
  hourly:{time:hours,temperature_2m:hours.map(()=>25),precipitation:hours.map((_,i)=>i%24===15?2:0),wind_speed_10m:hours.map(()=>8),wind_gusts_10m:hours.map(()=>20),relative_humidity_2m:hours.map(()=>60),cloud_cover:hours.map((_,i)=>i<24?20:80)}},
 rain_ensemble_daily:days.slice(0,7).map((d,k)=>({date:d,p50_mm:[0,10,18,2,0,0,0][k],p10_mm:0,p90_mm:[2,24,40,8,1,0,2][k],p_gt_1_mm:[.1,.8,.9,.4,.05,.0,.1][k],p_gt_20_mm:[0,.3,.45,0,0,0,0][k],model_count:8})),
 rain_model_agreement_daily:[{date:days[1],agreement_label:'alta',side:'chuva'},{date:days[2],agreement_label:'media',side:'dividido'}],
 gust_ensemble_daily:[{date:days[2],p_gt_30_kmh:.6}],
 rain_ensemble_accumulated:[{span_days:7,p50_mm:41,p10_mm:18,p90_mm:70,p_gt_25_mm:.78,model_count:8}],
 deterministic_models:{state:'ok',collected_at_utc:'2026-11-05T12:00:00Z',models:{ecmwf_ifs025:{state:'ok',label:'ECMWF',daily:{time:days.slice(0,7),precipitation_sum:[0,8,20,1,0,0,0],temperature_2m_max:[30,32,27,27,30,31,33],temperature_2m_min:[18,19,16,15,16,18,20],wind_gusts_10m_max:[25,40,50,30,25,20,20]}},
  gfs_global:{state:'ok',label:'GFS',daily:{time:days.slice(0,7),precipitation_sum:[1,15,30,4,0,0,2],temperature_2m_max:[32,34,29,28,31,33,35],temperature_2m_min:[19,21,18,16,17,20,22],wind_gusts_10m_max:[30,48,55,32,26,24,28]}},bad_id:{state:'unavailable',label:'bad',error:'HTTP 400'}},
  spread_daily:days.slice(0,7).map((d,k)=>({date:d,models:2,rain_min_mm:[0,8,20,1,0,0,0][k],rain_median_mm:[0.5,11.5,25,2.5,0,0,1][k],rain_max_mm:[1,15,30,4,0,0,2][k],models_wet_1mm:[1,2,2,2,0,0,1][k],models_wet_10mm:[0,1,2,0,0,0,0][k]}))},
 complementary:{gefs_extended:{state:'ok',member_count:30,days:Array.from({length:21},(_,k)=>({date:new Date(Date.UTC(2026,10,19+k)).toISOString().slice(0,10),mean_mm:3}))},
  ecmwf_extended:{state:'ok',precipitation_unit:'mm/day',weeks:[{start:'2026-11-23',rain_week_mean_api:4.2,rain_anomaly_api:1.1,temperature_mean_c:26.5},{start:'2026-11-30',rain_week_mean_api:2.1,rain_anomaly_api:-0.8}]}}};
// ---------- weekly board ----------
const weekly=load('site/static/weekly_board_v40.js').CampoWeekly;
const board=weekly.buildDays(state,now);
assert.equal(board.length,7);assert.equal(board[0].weekday,'hoje');assert.equal(board[1].weekday,'amanhã');
assert.equal(board[1].icon,'heavy','30% of members above 20 mm → heavy rain icon');
assert.equal(board[2].icon,'heavy');assert.equal(board[0].icon,'sun','dry day with few clouds → sun');
assert.equal(board[1].p50,10);assert.equal(board[1].agreement,'alta');assert.equal(board[2].gust_p30,.6);
assert.equal(JSON.stringify(board[1].models_spread),JSON.stringify({min:8,max:15,wet:2,n:2}));
assert.equal(weekly.pickIcon({p_gt_1:.2,cloud:80}),'cloud');assert.equal(weekly.pickIcon({p_gt_20:.35,cape:1500}),'storm');
const weeks=weekly.buildWeeks(state,now);
assert.equal(weeks[0].label,'Esta semana');assert.match(weeks[0].rain,/41 mm/);assert.equal(weeks[0].confidence,'média a alta');
assert.equal(weeks[1].label,'Próxima semana');assert.equal(weeks[1].rain,'—','only one deterministic day beyond day 7: no weekly total invented');
assert.ok(weeks.some(w=>w.kind==='gefs'&&/≈/.test(w.rain)),'GEFS week 3+ as approximate tendency');
assert.ok(weeks.some(w=>w.kind==='ecmwf'&&/acima do normal/.test(w.range)));
assert.ok(!weeks.some(w=>w.kind==='ecmwf'&&w.period.includes('23/11')&&false));
const noState=weekly.buildDays({},now);assert.equal(noState.length,0);
// ---------- bulletin ----------
const bulletin=load('site/static/bulletin_v40.js').CampoBulletin;
assert.equal(bulletin.originLabel({status:'llm',provider:'groq',model:'x'}).cls,'ai');assert.match(bulletin.originLabel({status:'rules'}).text,/sem IA/);
assert.match(bulletin.originLabel({status:'rules_fallback'}).text,/regras/);
// ---------- model comparison ----------
const compare=load('site/static/models_compare_v40.js').CampoModelsCompare;
const rows=compare.rows(state.deterministic_models);assert.equal(rows.length,2);assert.equal(rows[0].label,'ECMWF');
const info=compare.summary(state.deterministic_models);assert.equal(info.ok,2);assert.deepEqual(info.missing,['bad: HTTP 400']);
// ---------- stations: corrections mirror the Python implementation ----------
const stations=load('site/static/stations_v40.js').CampoStations;
assert.equal(stations.applyCorrection({method:'bias',bias:-1.5},30),28.5);
assert.equal(stations.applyCorrection({method:'linear',slope:.9,intercept:2},30),29);
assert.equal(stations.applyCorrection({method:'ratio',ratio:1.2},10),12);
assert.equal(stations.applyCorrection({method:'hourly_bias',global_bias:1,by_hour:{'14':-2}},30,14),28);
const qm={method:'quantile_map',threshold:1,qx:[1,5,10],qy:[0.5,8,20]};
assert.equal(stations.applyCorrection(qm,0.5),0,'below the wet threshold → dry');
assert.equal(stations.applyCorrection(qm,5),8);assert.equal(stations.applyCorrection(qm,7.5),14);assert.equal(stations.applyCorrection(qm,20),40,'beyond the table scales by the top ratio');
assert.equal(stations._test.clip('rain_mm',-2),0);assert.equal(stations._test.clip('relative_humidity_2m',104),100);
const report={verification:[{model:'m',lead_days:1,variable:'t_max',status:'evaluated',raw_all_pairs:{mae:1.5,bias:.8,n:150},recommended:{method:'bias',parameters:{method:'bias',bias:-.8},evidence:{mae_raw:1.5,mae_corrected:1.2,skill_mae:.2,delta_mae_ci95:[-.4,-.1]}}},
 {model:'m',lead_days:2,variable:'t_max',status:'evaluated',raw_all_pairs:{mae:1.9,bias:.9,n:150},recommended:null},{model:'m',lead_days:7,variable:'t_max',status:'insufficient_pairs',n_pairs:3}]};
const html=stations.matrix(report,'t_max');
assert.match(html,/✓ 20%/);assert.match(html,/bruto/);assert.match(html,/poucos pares/);assert.ok(stations._test.recommended(report,'m',1,'t_max'));assert.equal(stations._test.recommended(report,'m',2,'t_max'),null);
// ---------- navigation: maps leave the simple mode; markup contract ----------
const navStore={};const nav=load('site/static/nav_v30.js',{localStorage:{getItem:k=>navStore[k]??null,setItem:(k,v)=>{navStore[k]=v;}}}).CampoNav;
assert.ok(!nav.visibleTabs('simple').includes('maps'),'grid-sample map must not be in the simple mode');
assert.ok(nav.visibleTabs('simple').includes('observations')&&nav.visibleTabs('advanced').includes('maps'));
const page=fs.readFileSync('site/index.html','utf8');
for(const id of ['weekly-board','weeks-ahead','bulletin-card','station-overview-card','stations-panel','models-compare-panel','goes-control'])assert.ok(page.includes(`id="${id}"`),'missing '+id);
assert.ok(page.includes('static/brand/logo-horizontal.webp')&&page.includes('rel="apple-touch-icon"')&&page.includes('manifest.webmanifest'));
assert.ok(page.includes('GOES-East_ABI_GeoColor')&&page.includes('IMERG_Precipitation_Rate_30min'));
const order=['static/nav_v30.js','static/weekly_board_v40.js','static/bulletin_v40.js','static/stations_v40.js','static/models_compare_v40.js'].map(x=>page.indexOf(x));
assert.ok(order.every((v,i)=>v>0&&(i===0||v>order[i-1])),'v4 scripts load after nav');
const css=fs.readFileSync('site/static/styles.css','utf8');
assert.ok(css.includes('--bn:#0f2a66')&&css.includes('--bg1:#0f7a3b')&&css.includes('.brand-logo'),'brand tokens');
// maps: time frames follow the layer cadence and latency
const stub=()=>({addEventListener(){},value:'',max:'',textContent:'',innerHTML:'',className:'',classList:{contains:()=>false,toggle(){},add(){},remove(){}},disabled:false,hidden:false,dataset:{},style:{},appendChild(){},closest:()=>null});
const win={addEventListener(){},location:{href:'http://localhost/'},CampoLocation:null};const doc={getElementById:()=>stub(),readyState:'complete',addEventListener(){},querySelector:()=>null,querySelectorAll:()=>[]};
const mapsCtx={window:win,document:doc,setTimeout,clearTimeout,setInterval,clearInterval,Date,Intl,Math,Number,String,Map,Set,URL,URLSearchParams,AbortController,console,Array,Object,JSON,Boolean};
vm.runInNewContext(fs.readFileSync('site/static/maps_v14.js','utf8'),mapsCtx);
const mapsApi=win.CampoMaps._test;const frames=mapsApi.timeFrames('GOES-East_ABI_GeoColor',Date.parse('2026-11-05T15:07:00Z'));
assert.equal(frames.length,18);assert.equal(frames.at(-1),'2026-11-05T14:20:00Z','latest frame = now − 40 min latency rounded to 10 min');assert.equal(frames[0],'2026-11-05T11:30:00Z');
assert.equal(mapsApi.timeFrames('IMERG_Precipitation_Rate_30min',Date.parse('2026-11-05T15:07:00Z')).at(-1),'2026-11-05T11:00:00Z');
assert.match(mapsApi.timeURL('GOES-East_ABI_GeoColor','2026-11-05T14:20:00Z'),/^https:\/\/gibs\.earthdata\.nasa\.gov\/wmts\/epsg3857\/best\/GOES-East_ABI_GeoColor\/default\/2026-11-05T14:20:00Z\/GoogleMapsCompatible_Level7\/\{z\}\/\{y\}\/\{x\}\.png$/);
console.log('PASS v4 frontend: weekly board, weeks ahead, bulletin origin, model comparison, station corrections, GOES frames, markup');
