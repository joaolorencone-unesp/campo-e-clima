'use strict';
/** Campo e Clima v4 — newspaper-style weekly board and "next weeks" outlook for the simple mode.
 * Everything is read from the published state: deterministic daily values, ensemble daily
 * distributions, agreement, ECMWF weekly means and GEFS extended days. No value is invented;
 * a missing product leaves its cell as "—" and the row keeps its source label.
 */
(function(root){
 const finite=v=>typeof v==='number'&&Number.isFinite(v);
 const fmt=(v,d=0)=>finite(v)?v.toFixed(d).replace('.',','):'—';
 const pct=v=>finite(v)?(v*100).toFixed(0)+'%':'—';
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const WEEKDAYS=['dom','seg','ter','qua','qui','sex','sáb'];
 const ICONS={
  sun:'<svg viewBox="0 0 48 48" aria-hidden="true"><circle cx="24" cy="24" r="10" fill="#f2b705"/><g stroke="#f2b705" stroke-width="3" stroke-linecap="round"><path d="M24 4v6M24 38v6M4 24h6M38 24h6M9.9 9.9l4.2 4.2M33.9 33.9l4.2 4.2M9.9 38.1l4.2-4.2M33.9 14.1l4.2-4.2"/></g></svg>',
  partly:'<svg viewBox="0 0 48 48" aria-hidden="true"><circle cx="18" cy="18" r="8" fill="#f2b705"/><path d="M14 36h20a7 7 0 0 0 .8-13.95A9 9 0 0 0 17.6 20a7 7 0 0 0-3.6 16z" fill="#fff" stroke="#8aa0b4" stroke-width="2"/></svg>',
  cloud:'<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M13 36h22a8 8 0 0 0 .9-15.95A10 10 0 0 0 16.6 18a8 8 0 0 0-3.6 18z" fill="#e4ebf1" stroke="#7f95a8" stroke-width="2"/></svg>',
  rain:'<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M13 30h22a8 8 0 0 0 .9-15.95A10 10 0 0 0 16.6 12a8 8 0 0 0-3.6 18z" fill="#dbe6f0" stroke="#6f879c" stroke-width="2"/><g stroke="#0b8df0" stroke-width="3" stroke-linecap="round"><path d="M17 35l-2 6M25 35l-2 6M33 35l-2 6"/></g></svg>',
  heavy:'<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M13 28h22a8 8 0 0 0 .9-15.95A10 10 0 0 0 16.6 10a8 8 0 0 0-3.6 18z" fill="#c9d8e6" stroke="#5c748a" stroke-width="2"/><g stroke="#0b6fc0" stroke-width="3.5" stroke-linecap="round"><path d="M15 33l-3 9M22 33l-3 9M29 33l-3 9M36 33l-3 9"/></g></svg>',
  storm:'<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M13 28h22a8 8 0 0 0 .9-15.95A10 10 0 0 0 16.6 10a8 8 0 0 0-3.6 18z" fill="#b9c9d9" stroke="#4f6679" stroke-width="2"/><path d="M26 29l-7 10h6l-2 7 8-11h-6z" fill="#f2b705"/></svg>',
  maybe:'<svg viewBox="0 0 48 48" aria-hidden="true"><circle cx="17" cy="16" r="7" fill="#f2b705"/><path d="M14 34h20a7 7 0 0 0 .8-13.95A9 9 0 0 0 17.6 18a7 7 0 0 0-3.6 16z" fill="#fff" stroke="#8aa0b4" stroke-width="2"/><path d="M25 37l-2 6" stroke="#0b8df0" stroke-width="3" stroke-linecap="round"/></svg>'};
 function pickIcon(day){
  const p1=day.p_gt_1,p20=day.p_gt_20,p50=day.p50,cloud=day.cloud,cape=day.cape;
  if(finite(p20)&&p20>=.3)return finite(cape)&&cape>=1000?'storm':'heavy';
  if(finite(p1)&&p1>=.5)return finite(p50)&&p50>=10?'heavy':'rain';
  if(finite(p1)&&p1>=.3)return finite(p50)&&p50>=1?'rain':'maybe';
  if(finite(cloud)&&cloud>=70)return 'cloud';
  if(finite(cloud)&&cloud>=35)return 'partly';
  return 'sun';
 }
 const LABEL={sun:'Sol',partly:'Parcialmente nublado',cloud:'Nublado',maybe:'Chuva possível',rain:'Chuva',heavy:'Chuva forte',storm:'Tempestade possível'};
 function offsetSeconds(state){const s=state?.site?.utc_offset_seconds,d=state?.deterministic?.utc_offset_seconds;return finite(s)?s:finite(d)?d:-14400;}
 function localDate(now,state){return new Date(now+offsetSeconds(state)*1000).toISOString().slice(0,10);}
 function weekday(iso){const d=new Date(iso+'T12:00:00Z');return WEEKDAYS[d.getUTCDay()];}
 function dailyMeans(hourly,key){
  const out={};if(!Array.isArray(hourly?.time)||!Array.isArray(hourly?.[key]))return out;
  const acc={};hourly.time.forEach((t,i)=>{const v=hourly[key][i];if(!finite(v))return;const d=t.slice(0,10);(acc[d]??=[]).push(v);});
  for(const [d,v] of Object.entries(acc))out[d]={mean:v.reduce((a,b)=>a+b,0)/v.length,max:Math.max(...v)};
  return out;
 }
 function buildDays(state,now=Date.now()){
  const det=state?.deterministic||{},daily=det.daily||{},hourly=det.hourly||{};
  const today=localDate(now,state);
  const ens=new Map((state?.rain_ensemble_daily||[]).map(r=>[r.date,r]));
  const agree=new Map((state?.rain_model_agreement_daily||[]).map(r=>[r.date,r]));
  const gust=new Map((state?.gust_ensemble_daily||[]).map(r=>[r.date,r]));
  const spread=new Map((state?.deterministic_models?.spread_daily||[]).map(r=>[r.date,r]));
  const cloud=dailyMeans(hourly,'cloud_cover'),cape=dailyMeans(state?.deterministic_extended?.hourly||{},'cape');
  const dates=(daily.time||[]).filter(d=>d>=today).slice(0,7);
  return dates.map((date,k)=>{const i=(daily.time||[]).indexOf(date),e=ens.get(date),a=agree.get(date),g=gust.get(date);
   const row={date,weekday:k===0?'hoje':k===1?'amanhã':weekday(date),tmin:daily.temperature_2m_min?.[i],tmax:daily.temperature_2m_max?.[i],det_rain:daily.precipitation_sum?.[i],
    det_gust:daily.wind_gusts_10m_max?.[i],p50:e?.p50_mm,p10:e?.p10_mm,p90:e?.p90_mm,p_gt_1:e?.p_gt_1_mm,p_gt_20:e?.p_gt_20_mm,models:e?.model_count,members:e?.member_count,
    agreement:a?.agreement_label,side:a?.side,gust_p30:g?.p_gt_30_kmh,cloud:cloud[date]?.mean,cape:cape[date]?.max,
    models_spread:spread.get(date)?{min:spread.get(date).rain_min_mm,max:spread.get(date).rain_max_mm,wet:spread.get(date).models_wet_1mm,n:spread.get(date).models}:null};
   row.icon=pickIcon(row);row.icon_label=LABEL[row.icon];return row;});
 }
 function hoursOf(state,date){
  const h=state?.deterministic?.hourly||{};if(!Array.isArray(h.time))return [];
  return h.time.map((t,i)=>({t,i})).filter(x=>x.t.startsWith(date)&&Number(x.t.slice(11,13))%3===0).map(({t,i})=>({hour:t.slice(11,16),temp:h.temperature_2m?.[i],rain:h.precipitation?.[i],wind:h.wind_speed_10m?.[i],gust:h.wind_gusts_10m?.[i],rh:h.relative_humidity_2m?.[i]}));
 }
 function buildWeeks(state,now=Date.now()){
  const rows=[];const today=localDate(now,state);
  const acc=(state?.rain_ensemble_accumulated||[]).find(a=>a.span_days===7);
  const det=state?.deterministic?.daily||{};
  const sumDet=(from,to)=>{const vals=(det.time||[]).map((d,i)=>[d,det.precipitation_sum?.[i]]).filter(([d])=>d>=from&&d<=to).map(([,v])=>v);return vals.length&&vals.every(finite)?{sum:vals.reduce((a,b)=>a+b,0),days:vals.length}:null;};
  const addDays=(iso,n)=>new Date(Date.parse(iso+'T12:00:00Z')+n*86400000).toISOString().slice(0,10);
  const w1=sumDet(today,addDays(today,6)),w2=sumDet(addDays(today,7),addDays(today,13));
  // Confidence of the week comes from the published agreement between models (majority label), never from a fixed text.
  const labels=(state?.rain_model_agreement_daily||[]).filter(a=>a.date>=today&&a.date<=addDays(today,6)).map(a=>a.agreement_label).filter(Boolean);
  const count=l=>labels.filter(x=>x===l).length;
  const weekConfidence=!acc?'—':labels.length<3?'sem leitura':count('alta')>labels.length/2?'alta':count('baixa')>labels.length/2?'baixa':'média';
  rows.push({label:'Esta semana',period:`${today.slice(8,10)}/${today.slice(5,7)}–${addDays(today,6).slice(8,10)}/${addDays(today,6).slice(5,7)}`,
   rain:acc?`${fmt(acc.p50_mm)} mm`:w1?`${fmt(w1.sum)} mm`:'—',range:acc?`P10–P90 ${fmt(acc.p10_mm)}–${fmt(acc.p90_mm)} mm · ${pct(acc.p_gt_25_mm)} dos membros acima de 25 mm${labels.length?` · concordância ${weekConfidence} em ${labels.length} dias`:''}`:'determinístico, sem distribuição de ensemble',
   source:acc?`${acc.model_count} ensembles`:'Open-Meteo determinístico',confidence:weekConfidence,kind:'ensemble'});
  rows.push({label:'Próxima semana',period:`${addDays(today,7).slice(8,10)}/${addDays(today,7).slice(5,7)}–${addDays(today,13).slice(8,10)}/${addDays(today,13).slice(5,7)}`,
   rain:w2&&w2.days>=5?`${fmt(w2.sum)} mm`:'—',range:w2?`${w2.days} dias com previsão determinística; sem distribuição de ensemble`:'sem previsão diária',source:'Open-Meteo determinístico (dias 8–14)',confidence:'baixa',kind:'deterministic'});
  const gefs=state?.complementary?.gefs_extended;
  if(gefs?.state==='ok'&&Array.isArray(gefs.days)){
   const byWeek={};for(const d of gefs.days){const off=Math.round((Date.parse(d.date+'T12:00:00Z')-Date.parse(today+'T12:00:00Z'))/86400000);if(off<14)continue;const w=Math.floor(off/7);(byWeek[w]??=[]).push(d);}
   for(const [w,days] of Object.entries(byWeek)){const vals=days.map(d=>d.mean_mm).filter(finite);if(vals.length<5)continue;const mean=vals.reduce((s,v)=>s+v,0);
    rows.push({label:`Semana ${Number(w)+1}`,period:`${days[0].date.slice(8,10)}/${days[0].date.slice(5,7)}–${days.at(-1).date.slice(8,10)}/${days.at(-1).date.slice(5,7)}`,rain:`≈ ${fmt(mean)} mm`,range:`soma das médias diárias do GEFS (${vals.length} dias com valor; ${gefs.member_count} membros de um só modelo)`,source:'NOAA GEFS estendido',confidence:'tendência',kind:'gefs'});}
  }
  const ext=state?.complementary?.ecmwf_extended;
  if(ext?.state==='ok'&&Array.isArray(ext.weeks)){
   for(const wk of ext.weeks.slice(0,6)){
    if(wk.start<addDays(today,13))continue;
    const anomaly=finite(wk.rain_anomaly_api)?(wk.rain_anomaly_api>0?'acima do normal':wk.rain_anomaly_api<0?'abaixo do normal':'próximo do normal'):'anomalia não informada';
    rows.push({label:'Tendência ECMWF',period:`semana de ${wk.start.slice(8,10)}/${wk.start.slice(5,7)}`,rain:finite(wk.rain_week_mean_api)?`${fmt(wk.rain_week_mean_api,1)} ${ext.precipitation_unit||''}`:'—',range:`${anomaly}${finite(wk.temperature_mean_c)?' · T média '+fmt(wk.temperature_mean_c,1)+' °C':''}`,source:'ECMWF EC46/SEAS5 média semanal (~36 km)',confidence:'tendência',kind:'ecmwf'});
   }
  }
  return rows;
 }
 function render(state,now=Date.now()){
  if(typeof document==='undefined')return;
  const board=document.getElementById('weekly-board'),weeks=document.getElementById('weeks-ahead');
  if(board){
   const days=buildDays(state,now);
   if(!days.length){board.innerHTML='<p class="caption">Sem previsão diária para montar a semana.</p>';}
   else{
    const badge=d=>d.agreement?`<span class="agree ${d.agreement==='alta'?'ok':d.agreement==='media'?'warn':'bad'}">${d.agreement==='alta'?'Alta':d.agreement==='media'?'Média':'Baixa'}</span>`:'<span class="agree">—</span>';
    board.innerHTML=`<div class="board-scroll"><table class="board"><thead><tr><th>Dia</th><th>Tempo</th><th>Mín / Máx</th><th>Chuva (mediana)</th><th>Faixa P10–P90</th><th>Membros com chuva</th><th>Rajada máx.</th><th>Concordância</th></tr></thead><tbody>${days.map((d,k)=>`<tr class="board-row" data-date="${esc(d.date)}" tabindex="0" aria-expanded="false"><td><strong>${esc(d.weekday)}</strong><small>${esc(d.date.slice(8,10))}/${esc(d.date.slice(5,7))}</small></td><td class="board-icon">${ICONS[d.icon]}<small>${esc(d.icon_label)}</small></td><td><strong class="tmax">${fmt(d.tmax)}°</strong><span class="tmin">${fmt(d.tmin)}°</span></td><td><strong class="rain-big">${finite(d.p50)?fmt(d.p50,d.p50<10?1:0)+' mm':finite(d.det_rain)?fmt(d.det_rain,1)+' mm*':'—'}</strong></td><td>${finite(d.p10)?fmt(d.p10,0)+'–'+fmt(d.p90,0)+' mm':'—'}${d.models_spread?`<span class="weekly-models">modelos: ${fmt(d.models_spread.min,0)}–${fmt(d.models_spread.max,0)} mm · ${d.models_spread.wet}/${d.models_spread.n} com chuva</span>`:''}</td><td>${pct(d.p_gt_1)}${finite(d.models)?`<small>${d.models} modelos</small>`:''}</td><td>${fmt(d.det_gust)} km/h${finite(d.gust_p30)?`<small>${pct(d.gust_p30)} >30 km/h</small>`:''}</td><td>${badge(d)}</td></tr><tr class="board-detail" data-for="${esc(d.date)}" hidden><td colspan="8"><div class="board-hours">${hoursOf(state,d.date).map(h=>`<span><b>${esc(h.hour)}</b>${fmt(h.temp)}° · ${fmt(h.rain,1)} mm · ${fmt(h.wind)} km/h</span>`).join('')||'Sem detalhe horário.'}</div></td></tr>`).join('')}</tbody></table></div><p class="caption">Mediana e faixa P10–P90 vêm dos ensembles (peso igual por modelo); "membros com chuva" é a fração de membros acima de 1 mm, não probabilidade calibrada. Temperaturas e rajadas: previsão determinística Open-Meteo. * valor determinístico quando não há ensemble. Toque em um dia para ver o detalhe de 3 em 3 horas.</p>`;
    board.querySelectorAll('tr.board-row').forEach(tr=>{const toggle=()=>{const det=board.querySelector(`tr.board-detail[data-for="${tr.dataset.date}"]`);if(!det)return;det.hidden=!det.hidden;tr.setAttribute('aria-expanded',String(!det.hidden));tr.classList.toggle('open',!det.hidden);};tr.addEventListener('click',toggle);tr.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();toggle();}});});
   }
  }
  if(weeks){
   const rows=buildWeeks(state,now);
   weeks.innerHTML=`<div class="board-scroll"><table class="board weeks"><thead><tr><th>Período</th><th>Chuva esperada</th><th>Leitura</th><th>Fonte</th><th>Concordância</th></tr></thead><tbody>${rows.map(r=>`<tr class="week-${esc(r.kind)}"><td><strong>${esc(r.label)}</strong><small>${esc(r.period)}</small></td><td><strong class="rain-big">${esc(r.rain)}</strong></td><td>${esc(r.range)}</td><td>${esc(r.source)}</td><td><span class="agree ${r.confidence==='alta'?'ok':r.confidence==='média'?'warn':r.confidence==='baixa'?'bad':''}">${esc(r.confidence)}</span></td></tr>`).join('')}</tbody></table></div><p class="caption">Além de 7 dias a previsão diária perde qualidade; semanas 3 em diante são tendências de um modelo (GEFS) ou médias semanais (ECMWF), nunca chuva em dias específicos.</p>`;
  }
 }
 function bind(){root.addEventListener?.('campo:forecast-rendered',()=>{try{render(typeof state!=='undefined'?state:null);}catch(e){console.error('weekly board render',e);}});}
 if(typeof document!=='undefined')bind();
 root.CampoWeekly={buildDays,buildWeeks,pickIcon,render,_test:{dailyMeans,hoursOf}};
 if(typeof module==='object'&&module.exports)module.exports=root.CampoWeekly;
})(typeof window!=='undefined'?window:globalThis);
