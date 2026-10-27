'use strict';
/** Campo e Clima v1.5 — validated, staged coordinate-specific ensemble collection.
 * Static GitHub Pages cannot run server jobs or proxy providers. ALL remote requests
 * happen in the visitor's browser, with no credentials and with provenance controls.
 */
(() => {
const DEFAULT={latitude:-23.065,longitude:-54.190,timezone:'America/Campo_Grande',name:'Naviraí–MS',custom:false};
const OM_FORECAST='https://api.open-meteo.com/v1/forecast';
const OM_ENSEMBLE='https://ensemble-api.open-meteo.com/v1/ensemble';
const NASA='https://power.larc.nasa.gov/api/temporal/daily/point';
const ARCHIVE='https://archive-api.open-meteo.com/v1/archive';
const AIR='https://air-quality-api.open-meteo.com/v1/air-quality';
const ELEV='https://api.open-meteo.com/v1/elevation';
const SOIL='https://api.open-meteo.com/v1/forecast';
const MODELS={
 'ECMWF IFS':'ecmwf_ifs025_ensemble','ECMWF AIFS':'ecmwf_aifs025_ensemble',
 'NOAA GEFS':'ncep_gefs_seamless','NOAA AI-GEFS':'ncep_aigefs025',
 'DWD ICON':'dwd_icon_seamless_eps','GEM Canada':'gem_global_ensemble',
 'UKMO':'ukmo_global_ensemble_20km','Google WeatherNext2':'google_weathernext2_ensemble'
};
let loc={...DEFAULT},generation=0, busy=false, NASA_CACHE=new Map(), ensembleCache={key:null,at:0,data:null}, ancillaryKey=null;
const $ = id => document.getElementById(id);
const format=(v,n=1)=>v==null||!Number.isFinite(Number(v))?'—':Number(v).toFixed(n).replace('.',',');
const esc=s=>String(s??'').replace(/[&<>"']/g,x=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));
const pars=(base,params)=>base+'?'+new URLSearchParams(params).toString();
const finite=x=>typeof x==='number'&&Number.isFinite(x);
const localDay=(d,timezone='UTC')=>new Intl.DateTimeFormat('en-US',{timeZone:timezone,year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(d).reduce((o,p)=>(o[p.type]=p.value,o),{});
const todayUTC=()=>new Date().toISOString().slice(0,10);
function show(message,cls='info'){$('location-status').className='loc-status '+cls;$('location-status').textContent=message;}
function setNasa(message,cls='info'){$('nasa-status').className='notice '+(cls==='error'?'warning':'muted');$('nasa-status').textContent=message;}
function validate(lat,lon){if(!Number.isFinite(lat)||lat< -90||lat>90||!Number.isFinite(lon)||lon< -180||lon>180)throw Error('Latitude deve estar entre −90 e 90; longitude entre −180 e 180.');return {latitude:lat,longitude:lon};}
function locEquals(a,b){return Math.abs(a.latitude-b.latitude)<0.0000001&&Math.abs(a.longitude-b.longitude)<0.0000001;}
function updateLocationUI(){
 const custom=loc.custom;document.querySelector('.coord').textContent=`${format(loc.latitude,5)}°, ${format(loc.longitude,5)}° · ${custom?'Coordenadas selecionadas':'Naviraí–MS'} · ${loc.timezone}`;
 $('location-label').textContent=loc.name;
 $('loc-lat').value=loc.latitude;
 $('loc-lon').value=loc.longitude;
 $('loc-name').value=custom?loc.name:'';
 $('loc-reset').hidden=!custom;
 $('official-alert-strip').hidden=custom;
 // Naviraí municipal alerts and the unverified IFMS export cannot be reused elsewhere.
 const btn=document.querySelector('button[data-tab="observations"]'); if(btn)btn.hidden=custom;
 $('custom-source-note').hidden=!custom;
 $('custom-source-note').textContent=custom?'Para estas coordenadas, o painel consulta fontes abertas por ponto. Avisos INMET e registros da Embrapa de Naviraí NÃO são extrapolados para esta localidade. Umidade do solo e pulverização exigem verificação no talhão.':'';
 $('nasa-point').textContent=`${format(loc.latitude,5)}°, ${format(loc.longitude,5)}°`;
 $('osmlink').href=`https://www.openstreetmap.org/?mlat=${loc.latitude}&mlon=${loc.longitude}#map=11/${loc.latitude}/${loc.longitude}`;
 document.querySelectorAll('.navirai-reference').forEach(x=>x.hidden=custom);
 if(typeof window.dispatchEvent==='function' && typeof CustomEvent==='function')window.dispatchEvent(new CustomEvent('campo:location-changed',{detail:{...loc}}));
 const active=document.querySelector('.tab.active');if(active?.id==='observations'&&custom)document.querySelector('#tabs button[data-tab="overview"]').click();
}
async function getJSON(url,seconds=40,cachePolicy='default'){
 const ctrl=new AbortController(),timer=setTimeout(()=>ctrl.abort(),seconds*1000);
 try{
  const r=await fetch(url,{signal:ctrl.signal,cache:cachePolicy});
  if(!r.ok){const error=Error(`HTTP ${r.status}`);error.status=r.status;error.retryAfter=r.headers?.get?.('retry-after')||null;throw error;}
  const value=await r.json();if(value?.error)throw Error(value.reason||'API retornou erro');return value;
 }finally{clearTimeout(timer);}
}
function describeError(e){const t=String(e?.message||e||'erro desconhecido');if(e?.name==='AbortError')return 'Tempo limite excedido';if(t.includes('Failed to fetch')||t.includes('NetworkError'))return 'Rede, CORS ou serviço indisponível';return t.slice(0,120);}
async function requestForecast(point){
 const params={latitude:point.latitude,longitude:point.longitude,timezone:'auto',forecast_days:'14',hourly:FORECAST_HOURLY.join(','),daily:FORECAST_DAILY.join(','),current:FORECAST_CURRENT.join(',')};
 const v=await getJSON(pars(OM_FORECAST,params),30);
 if(!Array.isArray(v.hourly?.time)||v.hourly.time.length<24||!Array.isArray(v.daily?.time))throw Error('Forecast: horários ausentes');
 if(!v.timezone||!Number.isFinite(v.utc_offset_seconds))throw Error('Forecast: metadados de fuso ausentes');
 if(Math.abs(v.latitude-point.latitude)>0.8||Math.abs(v.longitude-point.longitude)>0.8)throw Error('Grade distante demais do ponto solicitado');
 return {hourly:v.hourly,daily:v.daily,current:v.current,latitude:v.latitude,longitude:v.longitude,utc_offset_seconds:v.utc_offset_seconds,elevation:v.elevation,model_used:'Open-Meteo Forecast • grade do ponto escolhido',collected_at_utc:new Date().toISOString(),timezone:v.timezone};
}
function members(payload,key){const out=[];for(const [k,v] of Object.entries(payload.hourly||{})){if(new RegExp('^'+key+'_member\\d+$').test(k)&&Array.isArray(v))out.push(v);}return out;}
function weightedQuantile(pairs,q){const values=pairs.slice().sort((a,b)=>a[0]-b[0]);const sum=values.reduce((a,v)=>a+v[1],0);let w=0;for(const [v,p] of values){w+=p;if(w/sum>=q-1e-10)return v;}return values.at(-1)?.[0]??null;}
function mix(modelSamples,formatRow){const keys=[...new Set(Object.values(modelSamples).flatMap(m=>Object.keys(m)))].sort();const results=[];for(const key of keys){const valid=Object.entries(modelSamples).filter(([,r])=>Array.isArray(r[key])&&r[key].length>0);if(!valid.length)continue;const pairs=valid.flatMap(([,r])=>r[key].map(x=>[x,1/valid.length/r[key].length]));const row=formatRow(key,pairs);row.model_count=valid.length;row.member_count=pairs.length;results.push(row);}return results;}
function mixRain(day,pairs){const o={date:day,mean_mm:0,p10_mm:weightedQuantile(pairs,.1),p50_mm:weightedQuantile(pairs,.5),p90_mm:weightedQuantile(pairs,.9)};for(const [v,w] of pairs)o.mean_mm+=v*w;for(const l of [.1,1,3,5,10,20,30,50])o['p_gt_'+String(l).replace('.','_')+'_mm']=pairs.reduce((s,[v,w])=>s+(v>l?w:0),0);return o;}
function mixGust(day,pairs){const o={date:day,mean_kmh:0,p10_kmh:weightedQuantile(pairs,.1),p50_kmh:weightedQuantile(pairs,.5),p90_kmh:weightedQuantile(pairs,.9)};for(const [v,w] of pairs)o.mean_kmh+=v*w;for(const l of [30,40,60,80])o['p_gt_'+l+'_kmh']=pairs.reduce((s,[v,w])=>s+(v>l?w:0),0);return o;}
function computeModel(payload){
 const h=payload.hourly||{},times=h.time||[];
 const rain=members(payload,'precipitation'),gust=members(payload,'wind_gusts_10m');
 const days={};for(let i=0;i<times.length;i++){const day=times[i].slice(0,10);(days[day]??=[]).push(i);}
 const dR={},dG={},hr={},rainMeans=[];
 for(const [day,ids] of Object.entries(days).slice(0,7)){
  if(ids.length!==24)continue;
  const r=rain.flatMap(m=>{const v=ids.map(i=>m[i]);return v.every(x=>finite(x)&&x>=0)?[v.reduce((a,b)=>a+b,0)]:[];});
  const g=gust.flatMap(m=>{const v=ids.map(i=>m[i]);return v.every(x=>finite(x)&&x>=0)?[Math.max(...v)]:[];});
  if(r.length)dR[day]=r;if(g.length)dG[day]=g;
 }
 for(let i=0;i<Math.min(times.length,72);i++){
  const row={};for(const duration of [1,3,6]){if(i+duration>times.length)continue;
   const stamps=times.slice(i,i+duration).map(t=>Date.parse(t+'Z'));
   if(stamps.some((x,j)=>j&&x-stamps[j-1]!==3600000))continue;
   const valid=rain.flatMap(m=>{const v=m.slice(i,i+duration);return v.length===duration&&v.every(x=>finite(x)&&x>=0)?[v.reduce((a,b)=>a+b,0)]:[];});
   if(valid.length)row[duration]=valid;
  }if(Object.keys(row).length)hr[times[i]]=row;
 }
 return {r:dR,g:dG,h:hr,member_rain:rain.length,member_gust:gust.length};
}
const JOINT_KEYS=['temperature_2m','relative_humidity_2m','wind_speed_10m','wind_gusts_10m','wind_direction_10m','precipitation'];
const JOINT_KINDS=['herb','fung','insect'];
const JOINT_LIMITS={herb:1.2,fung:1.5,insect:1.4};
function readJoint(payload){
 const h=payload?.hourly||{},times=h.time||[];
 const byField={};for(const key of JOINT_KEYS){byField[key]=new Map();
  for(const [name,data] of Object.entries(h)){const m=name.match(new RegExp('^'+key+'_member(\\d+)$'));if(m&&Array.isArray(data))byField[key].set(m[1],data);}
 }
 let common=null;for(const f of JOINT_KEYS){const ids=new Set(byField[f].keys());common=common===null?ids:new Set([...common].filter(x=>ids.has(x)));}
 const output={members_available:common?.size||0,times:{}};
 if(!common?.size)return output;
 for(let i=0;i<Math.min(times.length-3,74);i++){
  const stamps=times.slice(i,i+4).map(t=>Date.parse(t+'Z'));
  if(stamps.length!==4||stamps.some((x,j)=>j&&x-stamps[j-1]!==3600000))continue;
  const obj={};for(const id of common){
   const v={};let good=true;
   for(const f of JOINT_KEYS){const x=byField[f].get(id)[i];if(!finite(x)){good=false;break;}v[f]=x;}
   if(!good)continue;
   const nextRain=byField.precipitation.get(id).slice(i+1,i+4);
   if(nextRain.length!==3||nextRain.some(x=>!finite(x)||x<0))continue;
   v.rain3=nextRain.reduce((a,b)=>a+b,0);
   if(v.relative_humidity_2m<0||v.relative_humidity_2m>100||v.wind_speed_10m<0||v.wind_gusts_10m<0||v.wind_direction_10m<0||v.wind_direction_10m>360)continue;
   obj[id]=Object.fromEntries(JOINT_KINDS.map(kind=>[kind,jointAssessment(v,kind,Number(times[i].slice(11,13)))]));
  }if(Object.keys(obj).length)output.times[times[i]]=obj;
 }
 return output;
}
function jointAssessment(v,kind,localHour=null){
 const t=v.temperature_2m,rh=v.relative_humidity_2m,w=v.wind_speed_10m,g=v.wind_gusts_10m;
 const vpd=.6108*Math.exp(17.27*t/(t+237.3))*(1-rh/100);
 const reasons=[];
 if(w<3||w>10)reasons.push('vento');if(g>25)reasons.push('rajadas');if(t>=30)reasons.push('temperatura');if(rh<55)reasons.push('umidade');if(vpd>=JOINT_LIMITS[kind])reasons.push('vpd');if(v.rain3>.1)reasons.push('chuva_3h');
 if(reasons.length)return {cls:'restrito',reasons};
 if(localHour!==null&&(localHour<7||localHour>=18))return {cls:'indeterminado',reasons:['inversao_nao_verificada']};
 return (w>8||g>20||rh<60||t>=28||vpd>JOINT_LIMITS[kind]*.85||v.rain3>0)?{cls:'marginal',reasons:[]}:{cls:'passa',reasons:[]};
}
function mixJointEvent(byModel, field){
 const time=[...new Set(Object.values(byModel).flatMap(m=>Object.keys(m.times||{})))].sort();const result=[];
 const summary=({modelEntries,kind})=>{
  const entries=modelEntries.filter(([,m])=>Object.keys(m).length);if(!entries.length)return null;
  const weights={passa:0,marginal:0,restrito:0,indeterminado:0},reasons={};let members=0;
  for(const [,byMember] of entries){const ids=Object.keys(byMember);members+=ids.length;
   for(const value of Object.values(byMember)){const w=1/entries.length/ids.length;const assessment=value[kind];
    if(!assessment)continue;weights[assessment.cls]+=w;
    for(const cause of assessment.reasons)reasons[cause]=(reasons[cause]||0)+w;
   }
  }
  return {models:entries.length,members,passa:weights.passa,marginal:weights.marginal,restrito:weights.restrito,indeterminado:weights.indeterminado,reasons};
 };
 for(const t of time){let entry=[];
  if(field==='hour'){entry=Object.entries(byModel).filter(([,m])=>m.times?.[t]).map(([name,m])=>[name,m.times[t]]);}
  else{const end=new Date(Date.parse(t+'Z')+3600000).toISOString().slice(0,16);
   entry=Object.entries(byModel).map(([name,m])=>{const a=m.times?.[t],b=m.times?.[end];if(!a||!b)return [name,{}];const both={};
    for(const id of Object.keys(a)){if(!b[id])continue;both[id]={};for(const kind of JOINT_KINDS){const aa=a[id][kind],bb=b[id][kind];const cls=[aa.cls,bb.cls].includes('restrito')?'restrito':[aa.cls,bb.cls].includes('indeterminado')?'indeterminado':[aa.cls,bb.cls].includes('marginal')?'marginal':'passa';both[id][kind]={cls,reasons:[...new Set([...aa.reasons,...bb.reasons])]};}}
    return [name,both];}).filter(([,m])=>Object.keys(m).length);
  }
  if(!entry.length)continue;
  const row=field==='hour'?{time:t}:{start:t,end:new Date(Date.parse(t+'Z')+3600000).toISOString().slice(0,16)};
  for(const kind of JOINT_KINDS)row[kind]=summary({modelEntries:entry,kind});
  if(row.herb)result.push(row);
 }
 return result;
}

function summarizeEnsembles(results){
 const r={},g={},hour={},models={},comparison=[],sprayModels={},sprayStatuses={};
 for(const [name,{payload,computed,error}] of Object.entries(results)){
  if(error){models[name]={state:'error',detail:error,precipitation_members:0,gust_members:0};continue;}
  const c=computed;r[name]=c.r;g[name]=c.g;hour[name]=c.h;
  if(results[name].spray?.times&&Object.keys(results[name].spray.times).length){sprayModels[name]=results[name].spray;sprayStatuses[name]={status:'ok',member_fields_complete:results[name].spray.members_available};}
  else sprayStatuses[name]={status:'indisponivel',detail:results[name].sprayError||'sem variáveis conjuntas completas'};
  models[name]={state:Object.keys(c.r).length?'ok':'no_valid_daily_rain_members',precipitation_members:c.member_rain,gust_members:Object.values(c.g).some(a=>a.length)?c.member_gust:0,grid_lat:payload.latitude,grid_lon:payload.longitude,code:MODELS[name]};
  for(const [day,values] of Object.entries(c.r))if(values.length)comparison.push({model:name,date:day,members:values.length,mean_mm:values.reduce((a,b)=>a+b,0)/values.length,p_gt_5_mm:values.filter(v=>v>5).length/values.length});
 }
 const rainD=mix(r,mixRain),gustD=mix(g,mixGust);
 const stamps=[...new Set(Object.values(hour).flatMap(x=>Object.keys(x)))].sort();const rainH=[];
 for(const time of stamps){const row={time,windows:{}};for(const duration of [1,3,6]){
  const modelsV=Object.values(hour).map(x=>x?.[time]?.[duration]).filter(x=>Array.isArray(x)&&x.length);
  if(!modelsV.length)continue;const pairs=modelsV.flatMap(xs=>xs.map(x=>[x,1/modelsV.length/xs.length]));
  const v={models:modelsV.length,members:pairs.length,mean_mm:pairs.reduce((s,[x,w])=>s+x*w,0),p10_mm:weightedQuantile(pairs,.1),p50_mm:weightedQuantile(pairs,.5),p90_mm:weightedQuantile(pairs,.9)};
  for(const threshold of [.1,1,3,5,10,20])v['p_gt_'+String(threshold).replace('.','_')+'_mm']=pairs.reduce((s,[x,w])=>s+(x>threshold?w:0),0);
  row.windows[duration]=v;
 }if(Object.keys(row.windows).length)rainH.push(row);}
 return {rain_ensemble_daily:rainD,gust_ensemble_daily:gustD,rain_ensemble_hourly:rainH,ensemble_models:models,rain_models_daily:comparison,spray_joint_hourly:mixJointEvent(sprayModels,'hour'),spray_joint_windows_2h:mixJointEvent(sprayModels,'window'),spray_joint_model_status:sprayStatuses};
}
// Consultas por coordenada: primeiro chuva, depois variáveis adicionais.
// NÃO iniciar 8 consultas complexas de pulverização antes de mostrar os cenários de chuva.
// Cada resultado válido é publicado progressivamente; falhas não se tornam cache "verde".
const ENSEMBLE_PRIORITY=['ECMWF IFS','NOAA GEFS','DWD ICON','ECMWF AIFS',
 'NOAA AI-GEFS','GEM Canada','UKMO','Google WeatherNext2'];
const SPRAY_PRIORITY=['ECMWF IFS','NOAA GEFS','UKMO'];
let sprayRunKey=null, sprayBusy=false, sprayLastAttempt={key:null,at:0}, ensembleFailureCooldown={key:null,at:0};
function validEnsembleCount(data){return Object.values(data?.ensemble_models||{})
 .filter(x=>x.state==='ok'&&x.precipitation_members>0).length;}
function setEnsembleStatus(message,kind='info'){
 const el=$('custom-ensemble-status');if(!el)return;
 el.hidden=!loc.custom;el.className='notice '+(kind==='error'?'warning':kind==='good'?'':'muted');el.textContent=message;
}
function usableModelRain(payload){
 if(!Array.isArray(payload?.hourly?.time)||payload.hourly.time.length<24)return null;
 const computed=computeModel(payload);
 return Object.keys(computed.r).length?computed:null;
}
async function requestEnsembles(point,token,onProgress=()=>{}){
 const results={},entries=ENSEMBLE_PRIORITY.map(name=>[name,MODELS[name]]);let cursor=0;
 let cancelledByLimit=false;
 const worker=async()=>{
  while(cursor<entries.length){
   if(token!==generation||cancelledByLimit)return;
   const [name,code]=entries[cursor++];
   const params={latitude:point.latitude,longitude:point.longitude,timezone:'auto',
    forecast_days:7,models:code,hourly:'precipitation'};
   try{
    let data,computed;
    try{
     data=await getJSON(pars(OM_ENSEMBLE,params),25);
     computed=usableModelRain(data);
     if(!computed)throw Error('Resposta sem 24 horas completas de chuva por membro');
    }catch(e){
     // Retry only a smaller horizon when the request times out; never hammer HTTP 429.
     if(e.name!=='AbortError')throw e;
     data=await getJSON(pars(OM_ENSEMBLE,{...params,forecast_days:4}),17);
     computed=usableModelRain(data);
     if(!computed)throw Error('Consulta reduzida sem chuva válida');
    }
    if(token!==generation)return;
    results[name]={payload:data,computed};
   }catch(e){
    if(token!==generation)return;
    if(e.status===429)cancelledByLimit=true;
    results[name]={error:describeError(e)};
   }
   if(token===generation)onProgress(name,results,entries.length,cancelledByLimit);
  }
 };
 await Promise.all([worker(),worker()]);
 if(cancelledByLimit){for(const [name] of entries)if(!results[name])results[name]={error:'Consulta interrompida após HTTP 429 (limite de acesso gratuito)'};}
 return results;
}
async function requestSprayEnsembles(point,token,key){
 if(sprayBusy && sprayRunKey===key)return;
 if(token!==generation||!state||!loc.custom)return;
 if(sprayLastAttempt.key===key && Date.now()-sprayLastAttempt.at<10*60*1000 && !(state.spray_joint_hourly||[]).length){
  return; // avoid repeatedly hitting a rate-limited provider on every tab click
 }
 sprayBusy=true;sprayRunKey=key;sprayLastAttempt={key,at:Date.now()};
 setEnsembleStatus('Ensembles de chuva disponíveis. Consultando separadamente as variáveis conjuntas de pulverização (somente modelos prioritários)…');
 const byModel={},statuses={},gusts={};
 try{
  for(const name of SPRAY_PRIORITY){
   if(token!==generation)return;
   try{
    const params={latitude:point.latitude,longitude:point.longitude,timezone:'auto',
      forecast_days:4,models:MODELS[name],hourly:JOINT_KEYS.join(',')};
    const payload=await getJSON(pars(OM_ENSEMBLE,params),27);
    if(token!==generation)return;
    const spray=readJoint(payload),computed=computeModel(payload);
    if(Object.keys(spray.times).length){byModel[name]=spray;statuses[name]={status:'ok',member_fields_complete:spray.members_available};}
    else statuses[name]={status:'indisponivel',detail:'sem membros conjuntos completos'};
    if(Object.keys(computed.g).length){gusts[name]=computed.g;
     if(state.ensemble_models?.[name])state.ensemble_models[name].gust_members=computed.member_gust;}
   }catch(e){statuses[name]={status:'indisponivel',detail:describeError(e)};
    if(e.status===429)break; // limite de taxa: evitar insistir
   }
   if(token===generation){
    state.spray_joint_hourly=mixJointEvent(byModel,'hour');
    state.spray_joint_windows_2h=mixJointEvent(byModel,'window');
    state.spray_joint_model_status={...statuses};
    if(Object.keys(gusts).length)state.gust_ensemble_daily=mix(gusts,mixGust);
    render();
   }
  }
 }finally{
  if(token===generation){
   const count=Object.keys(byModel).length;
   setEnsembleStatus(`${validEnsembleCount(state)} modelos válidos de chuva; ${count} modelos com variáveis completas para a triagem de pulverização. Frequências NÃO calibradas.`,count?'good':'info');
  }
  sprayBusy=false;
 }
}

function emptyState(point,forecast){return {
 schema_version:9,issued_at_utc:new Date().toISOString(),site:{latitude:point.latitude,longitude:point.longitude,timezone:forecast.timezone,custom:true},
 deterministic:forecast,rain_ensemble_daily:[],gust_ensemble_daily:[],rain_ensemble_hourly:[],rain_models_daily:[],ensemble_models:{},
 spray_joint_hourly:[],spray_joint_windows_2h:[],spray_joint_model_status:{},official:{},embrapa_observations:{state:'not_applicable'},
 complementary:{},sources:{'Open-Meteo Forecast':{state:'ok',source_url:'https://open-meteo.com/en/docs',collected_at_utc:forecast.collected_at_utc}},
 warnings:['Avisos oficiais e estação de Naviraí não se aplicam ao ponto selecionado.','Triagem por ensemble para pulverização não disponível neste modo; a avaliação determinística ainda exige validação local.'],
 _liveForecastAt:forecast.collected_at_utc
};}
function applyPoint(point){loc={...point};updateLocationUI();sessionStorage.setItem('campo-selected-point',JSON.stringify(loc));
 try{const url=new URL(window.location.href);url.searchParams.set('lat',String(loc.latitude));url.searchParams.set('lon',String(loc.longitude));url.searchParams.set('name',loc.name);history.replaceState(null,'',url.pathname+url.search+url.hash);}catch(_){ /* page still usable without History API */ }
}
async function refreshCustom(manual=true){
 if(busy)return;
 const token=++generation;busy=true;
 $('refresh').disabled=true;$('refresh').textContent='↻ Consultando…';
 show('Consultando a previsão Open-Meteo para as coordenadas selecionadas…');
 try{
  const forecast=await requestForecast(loc);
  if(token!==generation)return;
  const newState=emptyState(loc,forecast);
  state=newState;render();updateLocationUI();
  show('✓ Previsão horária e diária atualizadas para '+loc.name+'. Consultando ensembles em segundo plano…','good');
  setRefreshFeedback('✓ Previsão determinística nova para as coordenadas. Probabilidades: aguardando ensembles.','good');
  // Only refresh slow services on location change (or through their dedicated buttons).
  const key=`${loc.latitude.toFixed(5)},${loc.longitude.toFixed(5)}`;
  if(ancillaryKey!==key){ancillaryKey=key;void getNASA(loc,token);void getAirQuality(loc,token);void getElevation(loc,token);void getSoilForecast(loc,token);}
  // A large member request is wasteful every 30 min per visitor. The short-term
  // forecast refreshes every 30 min; ensembles are cached 3h (min 30m when manual).
  const maxAge=manual?30*60*1000:3*60*60*1000;
  const cachedCount=ensembleCache.key===key?validEnsembleCount(ensembleCache.data):0;
  if(cachedCount>0 && Date.now()-ensembleCache.at<maxAge){
   Object.assign(state,ensembleCache.data);state._ensembleFetchedAt=new Date(ensembleCache.at).toISOString();
   render();updateLocationUI();
   const mins=Math.round((Date.now()-ensembleCache.at)/60000);
   setEnsembleStatus(`✓ ${cachedCount} modelos válidos de chuva; resultados consultados há ${mins} min. Cache da MESMA coordenada. Frequências não calibradas.`,'good');
   show(`✓ ${cachedCount} ensembles válidos para ${loc.name}, atualizados há ${mins} min.`,'good');
   setRefreshFeedback(`✓ Previsão determinística atualizada. ${cachedCount} ensembles válidos em cache por ${mins} min.`,'good');
   if(document.querySelector('#tabs button[data-tab="spray"]')?.classList.contains('active') && !(state.spray_joint_hourly||[]).length){
    void requestSprayEnsembles({...loc},token,key);
   }
   return;
  }
  const recentFailure=ensembleFailureCooldown.key===key && Date.now()-ensembleFailureCooldown.at<3*60*1000;
  if(recentFailure){
   setEnsembleStatus('A Open-Meteo recusou ou não concluiu as consultas há pouco. Aguardando 3 minutos antes de uma nova tentativa, para respeitar limites gratuitos.','error');
   show('⚠ Ensembles temporariamente indisponíveis; a previsão determinística está atualizada.','error');
   return;
  }
  const onProgress=(name,partial,total,hitLimit)=>{
   if(token!==generation)return;
   const data=summarizeEnsembles(partial),valid=validEnsembleCount(data);
   Object.assign(state,data);state._ensembleFetchedAt=new Date().toISOString();
   render();updateLocationUI();
   setEnsembleStatus(`${Object.keys(partial).length}/${total} modelos consultados; ${valid} com chuva válida. ${hitLimit?'Limite HTTP 429 — interrompendo novas consultas.':'Os resultados já disponíveis aparecem nos gráficos.'} Frequências ainda não calibradas.`,valid?'good':hitLimit?'error':'info');
  };
  setEnsembleStatus('Consultando primeiro os membros de chuva (8 modelos). Os resultados serão exibidos assim que cada modelo responder; sem exigir os dados mais pesados de pulverização.');
  const ensembles=await requestEnsembles(loc,token,onProgress);
  if(token!==generation)return;
  const ensembleData=summarizeEnsembles(ensembles),n=validEnsembleCount(ensembleData);
  Object.assign(state,ensembleData);
  if(n){
   ensembleCache={key,at:Date.now(),data:ensembleData};
   state._ensembleFetchedAt=new Date(ensembleCache.at).toISOString();
   show(`✓ ${n}/8 ensembles de chuva válidos para ${loc.name}; cálculo realizado somente para essas coordenadas.`,'good');
   setEnsembleStatus(`✓ ${n}/8 ensembles válidos. ${Object.keys(ensembles).length-n} modelos indisponíveis ou sem chuva completa. Chuva e incerteza exibidas a partir da amostra disponível. Frequências NÃO calibradas.`,'good');
   setRefreshFeedback(`✓ ${n} ensembles de chuva consultados diretamente para ${loc.name}. As fontes de Naviraí não foram reutilizadas.`,'good');
  }else{
   ensembleFailureCooldown={key,at:Date.now()};
   const counts=Object.values(ensembles).map(x=>x.error||'sem dados válidos');
   const reason=counts.some(x=>x.includes('429'))?'HTTP 429: limite de requisições':counts.some(x=>x.includes('Tempo limite'))?'tempo limite da API':'nenhum ensemble retornou chuva válida';
   show('⚠ Previsão determinística disponível, mas os oito ensembles falharam: '+reason,'error');
   setEnsembleStatus(`⚠ ${reason}. Nenhum resultado vazio será guardado em cache; a previsão determinística continua disponível. Não existem percentuais multimodelo para esta coleta.`,'error');
   setRefreshFeedback('⚠ Falha nos ensembles; sem percentuais probabilísticos. Previsão determinística mantida.','error');
  }
  render();updateLocationUI();
  if(n && token===generation && document.querySelector('#tabs button[data-tab="spray"]')?.classList.contains('active'))void requestSprayEnsembles({...loc},token,key);

 }catch(e){if(token===generation){show('Falha na previsão: '+describeError(e),'error');setRefreshFeedback('⚠ '+describeError(e),'error');}}
 finally{if(token===generation){busy=false;$('refresh').disabled=false;$('refresh').textContent='↻ Atualizar previsão agora';}}
}
function parseNASA(data,point){
 const fields=data?.properties?.parameter||{};const valid=(v)=>finite(v)&&v>-900;
 const cols=['PRECTOTCORR','T2M','T2M_MAX','T2M_MIN','RH2M','WS2M','ALLSKY_SFC_SW_DWN'];
 const days=[...new Set(cols.flatMap(k=>Object.keys(fields[k]||{})))].sort();
 const records=days.map(day=>{const r={date:day.slice(0,4)+'-'+day.slice(4,6)+'-'+day.slice(6,8)};for(const key of cols){const value=fields[key]?.[day];r[key]=valid(value)?value:null;}if(r.PRECTOTCORR<0)r.PRECTOTCORR=null;return r;}).filter(x=>x.T2M!==null||x.PRECTOTCORR!==null);
 if(records.length<90)throw Error('NASA POWER não retornou 90 dias de valores válidos');
 return {source:'NASA POWER / estimativa em grade (não estação)',records,lat:point.latitude,lon:point.longitude,record_count:records.length,source_url:'https://power.larc.nasa.gov/docs/services/api/temporal/daily/'};
}
function updateNASALink(point){
 const year=new Date().getUTCFullYear(),end=new Date(Date.now()-12*86400000).toISOString().slice(0,10).replaceAll('-','');
 const start=String(year-5)+'0101';
 const params={latitude:point.latitude,longitude:point.longitude,community:'AG',start,end,'time-standard':'UTC',
  parameters:'PRECTOTCORR,T2M,T2M_MAX,T2M_MIN,RH2M,WS2M,ALLSKY_SFC_SW_DWN',format:'JSON'};
 const url=pars(NASA,params);$('nasa-raw').href=url;return url;
}
function renderNASA(data){
 const all=data.records,perMonth=new Map(),perYear=new Map();for(const row of all){const mo=row.date.slice(0,7),year=row.date.slice(0,4);const s=perMonth.get(mo)||{rain:0,days:0,temp:0,tempDays:0};const y=perYear.get(year)||{rain:0,days:0};
  if(row.PRECTOTCORR!==null){s.rain+=row.PRECTOTCORR;s.days++;y.rain+=row.PRECTOTCORR;y.days++;}
  if(row.T2M!==null){s.temp+=row.T2M;s.tempDays++;}
  perMonth.set(mo,s);perYear.set(year,y);
 }
 const recent=[...perMonth.entries()].slice(-24);
 const monthComplete=(yearMonth,days)=>{const [y,m]=yearMonth.split('-').map(Number);return days===new Date(Date.UTC(y,m,0)).getUTCDate();};
 chart('nasa-rain-plot',[{x:recent.map(([k])=>k.slice(5)+'/'+k.slice(2,4)),y:recent.map(([k,v])=>monthComplete(k,v.days)?v.rain:null),type:'bar',name:'Chuva estimada NASA POWER',marker:{color:'#258cb8'},customdata:recent.map(([,v])=>v.days),hovertemplate:'%{x}: %{y:.1f} mm (%{customdata} dias)<extra></extra>'}],'Chuva mm/mês',{height:330});
 chart('nasa-temperature-plot',[{x:recent.map(([k])=>k.slice(5)+'/'+k.slice(2,4)),y:recent.map(([k,v])=>monthComplete(k,v.tempDays)?v.temp/v.tempDays:null),type:'scatter',mode:'lines+markers',name:'Temperatura média NASA POWER',line:{color:'#dd854f',width:2.7},hovertemplate:'%{x}: %{y:.1f} °C<extra></extra>'}],'°C',{height:330});
 const annual=[...perYear.entries()];$('nasa-summary').innerHTML=`<div class="nasa-summary-grid"><div><small>Dias com valores</small><strong>${data.record_count}</strong></div><div><small>Chuva no último mês completo</small><strong>${format(recent.slice().reverse().find(([k,v])=>monthComplete(k,v.days))?.[1].rain,0)} mm</strong></div><div><small>Fonte</small><strong>NASA POWER</strong></div></div><p class="caption">Série estimada em grade de resolução grosseira, não observação da estação. Meses com menos dias válidos do que os dias do calendário são ocultados dos gráficos para não subestimar os acumulados. Dias UTC da fonte podem diferir de dias locais.</p>`;
 const tableRows=annual.map(([year,v])=>`<tr><td>${esc(year)}</td><td>${format(v.days,0)}</td><td>${v.days===((Number(year)%4===0&&(Number(year)%100!==0||Number(year)%400===0))?366:365)?format(v.rain,1):'Parcial: '+format(v.rain,1)}</td></tr>`);
 tableFill('nasa-annual-table',['Ano','Dias com chuva estimada','Acumulado de chuva (mm)'],tableRows);
 setNasa(`✓ NASA POWER: ${data.record_count} dias de dados históricos em grade disponíveis para ${format(data.lat,4)}, ${format(data.lon,4)}. Série diária UTC.`, 'good');
 if(typeof window.dispatchEvent==='function' && typeof CustomEvent==='function')window.dispatchEvent(new CustomEvent('campo:nasa-loaded',{detail:data}));
 redrawActive();
}
async function getNASA(point,token){
 const url=updateNASALink(point);
 const cached=NASA_CACHE.get(url);if(cached&&Date.now()-cached.when<24*3600*1000){if(token===generation)renderNASA(cached.data);return;}
 setNasa('Consultando NASA POWER para as coordenadas — a resposta histórica pode levar alguns segundos…');
 try{const payload=await getJSON(url,75);if(token!==generation)return;const data=parseNASA(payload,point);NASA_CACHE.set(url,{when:Date.now(),data});renderNASA(data);}
 catch(e){if(token!==generation)return;setNasa('NASA POWER não respondeu diretamente ao navegador ('+describeError(e)+'). Use “Abrir dados NASA POWER” para acessar o arquivo original; nenhuma medição foi inventada.','error');clearPlot('nasa-rain-plot','Não foi possível ler os dados NASA nesta sessão.');clearPlot('nasa-temperature-plot','Não foi possível ler os dados NASA nesta sessão.');$('nasa-summary').innerHTML='';tableFill('nasa-annual-table',['Ano','Dias','Chuva mm'],[], 'NASA indisponível para leitura automatizada.');}
}
async function getArchive(point,token){
 $('archive-status').textContent='Consultando histórico alternativo Open-Meteo Archive (reanálise em grade)…';
 const end=new Date(Date.now()-8*86400000).toISOString().slice(0,10), start=new Date(Date.now()-373*86400000).toISOString().slice(0,10);
 try{const data=await getJSON(pars(ARCHIVE,{latitude:point.latitude,longitude:point.longitude,start_date:start,end_date:end,daily:'precipitation_sum,temperature_2m_mean',models:'era5_land',timezone:'UTC'}),40);
  if(token!==generation)return;const h=data.daily||{},rain=h.precipitation_sum||[];
  if(!h.time||rain.length!==h.time.length||!rain.some(finite))throw Error('Série não disponível');
  const recent=h.time.slice(-90),ids=recent.map((_,i)=>h.time.length-recent.length+i);
  chart('archive-rain-plot',[{type:'bar',x:recent.map(x=>x.slice(8,10)+'/'+x.slice(5,7)),y:ids.map(i=>rain[i]),name:'Chuva reanalisada ERA5-Land',marker:{color:'#3e9fc8'}}], 'mm/dia',{height:310});
  $('archive-status').textContent=`✓ ERA5-Land (Open-Meteo Archive): ${h.time.length} dias consultados em grade; reanálise NÃO é pluviômetro. Dias apresentados em UTC.`;redrawActive();
 }catch(e){if(token!==generation)return;$('archive-status').textContent='Arquivo ERA5-Land indisponível: '+describeError(e);clearPlot('archive-rain-plot','Sem série de reanálise válida.');}
}
async function getAirQuality(point,token){
 $('air-status').textContent='Consultando qualidade do ar CAMS/Open-Meteo…';
 try{const v=await getJSON(pars(AIR,{latitude:point.latitude,longitude:point.longitude,timezone:'auto',current:'pm2_5,pm10,uv_index',hourly:'pm2_5,pm10,uv_index',forecast_days:3}),25);if(token!==generation)return;
  const h=v.hourly||{},keys=['pm2_5','pm10'];
  if(!h.time||!keys.some(k=>h[k]?.some(finite)))throw Error('Variáveis ausentes');
  const count=Math.min(72,h.time.length);chart('air-plot',keys.map((k,i)=>({x:h.time.slice(0,count).map(t=>t.slice(5,16)),y:(h[k]||[]).slice(0,count),type:'scatter',mode:'lines',name:k==='pm2_5'?'PM2,5':'PM10',line:{color:i?'#e9a34b':'#399fc2'}})),'µg/m³',{height:310});
  $('air-status').textContent=`✓ CAMS/Open-Meteo • grade modelada • PM2,5 atual: ${format(v.current?.pm2_5)} µg/m³; PM10 atual: ${format(v.current?.pm10)} µg/m³; UV: ${format(v.current?.uv_index)}. Não é medição local de sensor.`;
  redrawActive();
 }catch(e){if(token!==generation)return;$('air-status').textContent='Qualidade do ar indisponível: '+describeError(e);clearPlot('air-plot','Sem dados de qualidade do ar.');}
}

async function getSoilForecast(point,token){
 const options=['soil_moisture_0_to_7cm,soil_temperature_0_to_7cm,et0_fao_evapotranspiration','soil_moisture_0_to_1cm,soil_temperature_0cm,et0_fao_evapotranspiration'];
 const errors=[];
 for(const fields of options){
  try{const v=await getJSON(pars(SOIL,{latitude:point.latitude,longitude:point.longitude,timezone:'auto',forecast_days:4,hourly:fields}),30);
   if(token!==generation)return;
   const h=v.hourly||{},keys=Object.keys(h).filter(x=>x.startsWith('soil_moisture_')&&h[x]?.some(finite));
   if(!keys.length)throw Error('sem estimativa válida de umidade do solo');
   state.complementary.soil_forecast={state:'ok',source:'Open-Meteo Forecast soil grid',grid_lat:v.latitude,grid_lon:v.longitude,source_url:'https://open-meteo.com/en/docs',queried_at_utc:new Date().toISOString(),hourly:{time:h.time,...Object.fromEntries(Object.entries(h).filter(([k])=>k!=='time'))},soil_moisture_keys:keys,note:'Umidade estimada por modelo; não é sensor, nem autoriza tráfego de máquinas.'};
   renderExtras();redrawActive();return;
  }catch(e){errors.push(describeError(e));}
 }
 if(token!==generation)return;
 if(state){state.complementary.soil_forecast={state:'unavailable',source_url:'https://open-meteo.com/en/docs',error:errors.join(' / ').slice(0,180)};renderExtras();}
}
async function getElevation(point,token){
 try{const v=await getJSON(pars(ELEV,{latitude:point.latitude,longitude:point.longitude}),15);if(token!==generation)return;
  $('point-elevation').textContent=finite(v.elevation?.[0])?`${format(v.elevation[0],0)} m · Copernicus DEM GLO-90 (elevação modelada)`: 'Altitude indisponível';
 }catch(e){if(token===generation)$('point-elevation').textContent='Altitude não disponível: '+describeError(e);}
}
async function select(point){try{busy=false;sprayRunKey=null;sprayLastAttempt={key:null,at:0};const pair=validate(Number(point.latitude),Number(point.longitude));if(locEquals(pair,DEFAULT))return reset();const name=String(point.name||'Coordenadas personalizadas').trim().slice(0,62)||'Coordenadas personalizadas';applyPoint({...pair,timezone:'auto',name,custom:true});
 // Remove Naviraí forecast immediately on switching, even if API fails.
 state=null;document.querySelectorAll('.tab .plot').forEach(e=>{if(e.id)clearPlot(e.id,'Consultando dados para o novo ponto…');});
 document.querySelectorAll('.tab table').forEach(t=>{t.innerHTML='<tbody><tr><td>Aguardando dados válidos para as coordenadas selecionadas.</td></tr></tbody>';});
 $('status').textContent='Consultando o ponto selecionado. Os resultados anteriores de Naviraí foram removidos para evitar mistura de localidades.';
 $('nasa-summary').innerHTML='';setNasa('Consultando histórico NASA POWER para a coordenada…');
 $('metrics').innerHTML='';$('insights').textContent='Aguardando nova previsão específica da coordenada selecionada.';
 await refreshCustom(true);
 }catch(e){show(describeError(e),'error');}}
function reset(){++generation;busy=false;ancillaryKey=null;sprayRunKey=null;sprayLastAttempt={key:null,at:0};loc={...DEFAULT};sessionStorage.removeItem('campo-selected-point');try{const url=new URL(window.location.href);for(const x of ['lat','lon','name'])url.searchParams.delete(x);history.replaceState(null,'',url.pathname+url.search+url.hash);}catch(_){}updateLocationUI();$('location-status').textContent='Naviraí restaurada: carregando boletim automático da sede…';state=null;refresh(true);const t=++generation;void getElevation(loc,t);}
$('loc-form').addEventListener('submit',e=>{e.preventDefault();select({latitude:$('loc-lat').value.replace(',','.'),longitude:$('loc-lon').value.replace(',','.'),name:$('loc-name').value.trim()});});
$('loc-reset').addEventListener('click',reset);
$('loc-share').addEventListener('click',async()=>{try{await navigator.clipboard.writeText(window.location.href);show('Link do ponto copiado para compartilhar.','good');}catch(e){show('Copie o endereço da barra do navegador. Ele contém as coordenadas do ponto.','info');}});
$('loc-navirai').addEventListener('click',reset);
$('loc-diamantino').addEventListener('click',()=>select({latitude:-14.408,longitude:-56.446,name:'Diamantino–MT'}));
$('nasa-refresh').addEventListener('click',()=>{const t=generation;void getNASA(loc,t);});
$('tabs').addEventListener('click',event=>{
 if(event.target.closest('button[data-tab="history-nasa"]')){const t=generation;void getNASA(loc,t);void getAirQuality(loc,t);}
 if(event.target.closest('button[data-tab="spray"], button[data-tab="wind"]') && loc.custom && !busy && state && validEnsembleCount(state)>0){
  const key=`${loc.latitude.toFixed(5)},${loc.longitude.toFixed(5)}`;
  if(sprayRunKey!==key || !(state.spray_joint_hourly||[]).length)void requestSprayEnsembles({...loc},generation,key);
 }
});
// Existing 30-min polling is handled by app.js. Custom points must never pull Naviraí snapshots.
window.CampoLocation={isCustom:()=>loc.custom,refreshCustom,select,reset,getPoint:()=>({...loc}),_test:{parseNASA,computeModel,summarizeEnsembles,weightedQuantile,validate,readJoint,jointAssessment,mixJointEvent,requestEnsembles,usableModelRain,validEnsembleCount}};
updateLocationUI();
try{
 const url=new URL(window.location.href),lat=url.searchParams.get('lat'),lon=url.searchParams.get('lon');
 if(lat!==null&&lon!==null){const xy=validate(Number(lat),Number(lon));void select({...xy,name:url.searchParams.get('name')||'Local compartilhado'});return;}
 const saved=JSON.parse(sessionStorage.getItem('campo-selected-point')||'null');if(saved&&saved.custom&&validate(saved.latitude,saved.longitude)){void select(saved);return;}
}catch(e){sessionStorage.removeItem('campo-selected-point');show('Coordenadas do link inválidas; consulte a sede ou informe um novo ponto.','error');}
// NASA and air-quality reference shown even in Naviraí; forecast comes from GitHub default.
const initial=++generation;void getElevation(loc,initial);
})();
