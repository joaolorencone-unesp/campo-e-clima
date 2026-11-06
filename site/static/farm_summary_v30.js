'use strict';
/** Campo e Clima v3 — plain-language farm summary ("modo simples").
 * Pure builder (no DOM) + renderer. Every sentence is derived from values that already
 * exist in the published state; nothing is invented, missing data stays missing, and
 * ensemble frequencies are always labelled as uncalibrated member frequencies.
 */
(function(root){
 const finite=v=>typeof v==='number'&&Number.isFinite(v);
 const fmt=(v,d=1)=>finite(v)?v.toFixed(d).replace('.',','):'—';
 const pct=(v,d=0)=>finite(v)?(v*100).toFixed(d).replace('.',',')+'%':'—';
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const ddmm=iso=>typeof iso==='string'&&/^\d{4}-\d\d-\d\d/.test(iso)?iso.slice(8,10)+'/'+iso.slice(5,7):'—';
 function offsetSeconds(state){const site=state?.site?.utc_offset_seconds,det=state?.deterministic?.utc_offset_seconds;return finite(site)?site:finite(det)?det:-14400;}
 function offsetISO(secs){const s=secs<0?'-':'+',a=Math.abs(secs);return `${s}${String(Math.floor(a/3600)).padStart(2,'0')}:${String(Math.floor(a%3600/60)).padStart(2,'0')}`;}
 function localMillis(stamp,state){const t=Date.parse(String(stamp).slice(0,16)+':00'+offsetISO(offsetSeconds(state)));return Number.isFinite(t)?t:null;}
 function localDateISO(millis,state){const d=new Date(millis+offsetSeconds(state)*1000);return d.toISOString().slice(0,10);}
 function ageMinutes(iso,now){const t=Date.parse(iso||'');return Number.isFinite(t)?Math.round((now-t)/60000):null;}
 function humanAge(min){if(!finite(min))return 'idade desconhecida';if(min<60)return `há ${min} min`;if(min<48*60)return `há ${Math.round(min/60)} h`;return `há ${Math.round(min/1440)} dias`;}
 function futureHours(state,now,n=72){
  const h=state?.deterministic?.hourly;if(!Array.isArray(h?.time))return [];
  return h.time.map((t,i)=>({t,i,ms:localMillis(t,state)})).filter(x=>x.ms!==null&&x.ms>now).slice(0,n);
 }
 const val=(h,key,i)=>{const x=h?.[key]?.[i];return finite(x)?x:null;};
 function sumOrNull(values){return values.length&&values.every(finite)?values.reduce((a,b)=>a+b,0):null;}
 function formatRainWindow(interval){
  if(typeof interval?.start!=='string'||typeof interval?.end!=='string')return '';
  const format=stamp=>ddmm(stamp)+' '+stamp.slice(11,16);
  return `${format(interval.start)} a ${format(interval.end)} (horário local)`;
 }
 function rain24Window(state,idx){
  const hours=idx.slice(0,24), hour=3600000;
  const ends=hours.map(x=>localMillis(x.t,state));
  if(ends.length!==24||ends.some((end,i)=>end===null||(i>0&&end-ends[i-1]!==hour)))return null;
  const total=sumOrNull(hours.map(x=>val(state?.deterministic?.hourly,'precipitation',x.i)));
  if(total===null)return null;
  // Precipitation belongs to the hour ending at each timestamp.
  const start=new Date(ends[0]-hour+offsetSeconds(state)*1000).toISOString().slice(0,16);
  return {total,start,end:hours[23].t.slice(0,16)};
 }
 function agreementSentence(row,dayLabel){
  if(!row)return null;
  const occ=row.agreement_label==='alta'?'elevada concordância':row.agreement_label==='media'?'concordância parcial':'baixa concordância';
  const side=row.side==='chuva'?'quanto à ocorrência de chuva':row.side==='seco'?'quanto ao tempo seco':'e os modelos estão divididos';
  const vol=row.volume_spread_label==='alta'?'mas grande dispersão no volume previsto':row.volume_spread_label==='media'?'com dispersão moderada no volume':'e pouca dispersão no volume';
  return `Há ${occ} entre os modelos ${side} ${dayLabel} (${row.wet_majority_models} de ${row.models} modelos com maioria de membros acima de ${fmt(row.wet_threshold_mm,0)} mm), ${vol} (médias por modelo de ${fmt(row.model_mean_min_mm,0)} a ${fmt(row.model_mean_max_mm,0)} mm).`;
 }
 function build(state,now=Date.now()){
  const out={headline:'',cards:[],sentences:[],risks:[],windows:[],freshness:{},notes:[],observed:null,ready:false};
  const h=state?.deterministic?.hourly;
  if(!h&&!state?.rain_ensemble_daily?.some(row=>finite(row?.p50_mm))){out.headline='Sem previsão carregada para este ponto.';return out;}
  const idx=futureHours(state,now,72);
  const today=localDateISO(now,state),tomorrow=localDateISO(now+86400000,state);
  const daily=state.rain_ensemble_daily||[],byDay=new Map(daily.map(r=>[r.date,r]));
  const agreement=new Map((state.rain_model_agreement_daily||[]).map(r=>[r.date,r]));
  const first=idx[0];
  // --- current conditions (model) and nearest observation when recent ---
  const current=state.deterministic?.current||{};
  const obs=state.official?.inmet_hourly_nearby;
  if(obs?.state==='ok'&&Array.isArray(obs.records)&&obs.records.length){
   const last=obs.records[obs.records.length-1],age=ageMinutes(last.valid_at_utc,now);
   if(finite(age)&&age<=240)out.observed={station:obs.station_name,code:obs.station_code,distance_km:obs.distance_km,age_min:age,temperature_c:last.temperature_c,rh_pct:last.rh_pct,rain_mm:last.precipitation_previous_hour_mm,wind_kmh:last.wind_kmh,gust_kmh:last.gust_kmh};
  }
  out.cards.push({key:'now',label:'Agora (modelo)',value:finite(current.temperature_2m)?fmt(current.temperature_2m)+' °C':'—',detail:`UR ${fmt(current.relative_humidity_2m,0)}% · vento ${fmt(current.wind_speed_10m,0)} km/h`,note:'Previsão do modelo para o horário atual, não medição na fazenda.'});
  // --- rain next 6 h ---
  const win6=first?(state.rain_ensemble_hourly||[]).find(r=>r.time===first.t)?.windows?.['6']:null;
  const det6=first?sumOrNull(idx.slice(0,6).map(x=>val(h,'precipitation',x.i))):null;
  out.cards.push({key:'rain6',label:'Chuva nas próximas 6 h',value:win6?`${pct(win6.p_gt_1_mm)} dos membros`:finite(det6)?fmt(det6)+' mm':'—',
   detail:win6?`>1 mm em 6 h · média ${fmt(win6.mean_mm)} mm · ${win6.models} modelos`:'Somente previsão determinística',tone:win6&&win6.p_gt_1_mm>=.5?'wet':'neutral',note:'Frequência bruta entre membros dos ensembles; não é probabilidade calibrada.'});
  // --- rain 24 h ---
  const rainWindow=rain24Window(state,idx),det24=rainWindow?.total;
  const todayRow=byDay.get(today),tomorrowRow=byDay.get(tomorrow);
  // Before noon most of the next 24 h still belong to today; afterwards tomorrow dominates.
  const localHour=new Date(now+offsetSeconds(state)*1000).getUTCHours();
  const focus=(localHour<12?todayRow:tomorrowRow)||tomorrowRow||todayRow;
  out.cards.push({key:'rain24',label:'Chuva nas próximas 24 h',value:finite(det24)?fmt(det24)+' mm':'—',
   detail:focus?`${focus.date===tomorrow?'Amanhã':'Hoje'}: mediana ${fmt(focus.p50_mm)} mm, P10–P90 ${fmt(focus.p10_mm)}–${fmt(focus.p90_mm)} mm, ${pct(focus.p_gt_1_mm)} dos membros com >1 mm`:'Ensembles indisponíveis',tone:focus&&focus.p_gt_1_mm>=.6?'wet':finite(det24)&&det24>=10?'wet':'neutral',note:rainWindow?`Previsão determinística de ${formatRainWindow(rainWindow)}. A mediana se refere ao dia indicado.`:'Acumulado determinístico indisponível para esta janela.'});
  // --- 7 days ---
  const acc=(state.rain_ensemble_accumulated||[]);const span=acc.find(a=>a.span_days===7)||acc.find(a=>a.span_days===5)||acc[0];
  out.cards.push({key:'rain7',label:span?`Chuva em ${span.span_days} dias`:'Chuva na semana',value:span?`${fmt(span.p50_mm,0)} mm`:'—',
   detail:span?`P10–P90 ${fmt(span.p10_mm,0)}–${fmt(span.p90_mm,0)} mm · ${pct(span.p_gt_25_mm)} dos membros acima de 25 mm · ${span.model_count} modelos`:'Sem trajetórias completas',tone:span&&span.p50_mm>=30?'wet':'neutral',note:'Acumulado por trajetória de membro, não soma de medianas diárias.'});
  // --- temperatures next 24h ---
  const temps=idx.slice(0,24).map(x=>val(h,'temperature_2m',x.i)).filter(finite);
  const agro=state.agro_ensemble_hourly||[];
  const tmaxEns=agro.slice(0,24).map(r=>r.variables?.temperature_2m?.p90).filter(finite);
  out.cards.push({key:'temp',label:'Temperatura (24 h)',value:temps.length?`${fmt(Math.min(...temps),0)} a ${fmt(Math.max(...temps),0)} °C`:'—',detail:tmaxEns.length?`P90 dos ensembles até ${fmt(Math.max(...tmaxEns),0)} °C`:'Determinístico',tone:temps.length&&Math.max(...temps)>=35?'hot':'neutral'});
  // --- wind ---
  const winds=idx.slice(0,24).map(x=>val(h,'wind_speed_10m',x.i)).filter(finite),gusts=idx.slice(0,24).map(x=>val(h,'wind_gusts_10m',x.i)).filter(finite);
  const gustDay=(state.gust_ensemble_daily||[]).find(g=>g.date===today)||(state.gust_ensemble_daily||[])[0];
  out.cards.push({key:'wind',label:'Vento e rajadas (24 h)',value:winds.length?`${fmt(Math.min(...winds),0)}–${fmt(Math.max(...winds),0)} km/h`:'—',detail:`${gusts.length?'rajadas até '+fmt(Math.max(...gusts),0)+' km/h':'Rajadas determinísticas indisponíveis'}${gustDay?` · ${pct(gustDay.p_gt_30_kmh)} dos membros com rajada >30 km/h (${gustDay.model_count} modelos)`:''}`,tone:gusts.length&&Math.max(...gusts)>40?'windy':'neutral'});
  // --- risks ---
  for(const row of daily.filter(r=>r.date>=today).slice(0,5)){
   if(finite(row.p_gt_20_mm)&&row.p_gt_20_mm>=.3)out.risks.push({kind:'heavy_rain',text:`Chuva forte possível em ${ddmm(row.date)}: ${pct(row.p_gt_20_mm)} dos membros acima de 20 mm/dia.`});
  }
  for(const g of (state.gust_ensemble_daily||[]).filter(r=>r.date>=today).slice(0,5)){
   if(finite(g.p_gt_40_kmh)&&g.p_gt_40_kmh>=.3)out.risks.push({kind:'gust',text:`Rajadas >40 km/h em ${ddmm(g.date)}: ${pct(g.p_gt_40_kmh)} dos membros (${g.model_count} modelos com rajadas).`});
  }
  const hot=agro.filter(r=>finite(r.variables?.temperature_2m?.p_ge_35)&&r.variables.temperature_2m.p_ge_35>=.3);
  if(hot.length)out.risks.push({kind:'heat',text:`Calor ≥35 °C com ${pct(Math.max(...hot.map(r=>r.variables.temperature_2m.p_ge_35)))} dos membros em ${hot.length} hora(s) das próximas 72 h.`});
  const dryAir=agro.filter(r=>finite(r.variables?.vpd_kpa?.p_ge_2_5)&&r.variables.vpd_kpa.p_ge_2_5>=.3);
  if(dryAir.length)out.risks.push({kind:'vpd',text:`Ar muito seco (VPD ≥2,5 kPa) em ${dryAir.length} hora(s): atenção a estresse das plantas e deriva de aplicações.`});
  const dry=state.rain_dry_spell;
  if(dry&&finite(dry.p_ge_5_days)&&dry.p_ge_5_days>=.5)out.risks.push({kind:'dry',text:`Sequência de ≥5 dias quase sem chuva (<${fmt(dry.dry_day_threshold_mm,0)} mm) em ${pct(dry.p_ge_5_days)} das trajetórias até ${ddmm(dry.end)}.`});
  const alerts=state.official?.inmet_alerts?.municipal_alerts||[];
  if(alerts.length)out.risks.push({kind:'inmet',text:`${alerts.length} aviso(s) oficial(is) do INMET vigente(s) para o município. Confira a fonte oficial.`});
  if(!out.risks.length)out.risks.push({kind:'none',text:'Nenhum limiar de risco dos ensembles foi ultrapassado nos próximos dias. Isso não elimina riscos locais não representados pelos modelos.'});
  // --- agreement sentences ---
  const s1=agreementSentence(agreement.get(tomorrow),'amanhã'),s0=agreementSentence(agreement.get(today),'hoje');
  const preferred=localHour<12?(s0||s1):(s1||s0);
  if(preferred)out.sentences.push(preferred);
  // --- freshness ---
  const models=Object.values(state.ensemble_models||{}).filter(m=>m.state==='ok'&&(m.precipitation_members||0)>0);
  const ages=models.map(m=>ageMinutes(m.collected_at_utc,now)).filter(finite);
  const detAge=ageMinutes(state.deterministic?.collected_at_utc||state._liveForecastAt,now);
  out.freshness={models_valid:models.length,models_total:Object.keys(state.ensemble_models||{}).length,ensemble_oldest_age_min:ages.length?Math.max(...ages):null,deterministic_age_min:detAge,
   pending:state.freshness?.models_with_newer_run_pending||[],issued_at_utc:state.issued_at_utc};
  out.sentences.push(`Dados: ${h?'previsão horária obtida '+humanAge(detAge):'previsão horária determinística indisponível'}; ensembles de ${models.length}${out.freshness.models_total?'/'+out.freshness.models_total:''} modelos, o mais antigo adquirido ${humanAge(out.freshness.ensemble_oldest_age_min)}.${out.freshness.pending.length?' Há rodada mais nova anunciada para: '+out.freshness.pending.join(', ')+'.':''}`);
  if(out.observed)out.sentences.push(`Observado na estação ${out.observed.station} (${fmt(out.observed.distance_km,0)} km) ${humanAge(out.observed.age_min)}: ${fmt(out.observed.temperature_c)} °C, UR ${fmt(out.observed.rh_pct,0)}%, chuva na última hora ${fmt(out.observed.rain_mm)} mm. Não representa a fazenda.`);
  // --- lower-restriction periods (generic field work screening, next 48 h) ---
  const candidates=[];
  for(let k=0;k<Math.min(48,idx.length);k++){
   const x=idx[k],rain=val(h,'precipitation',x.i),wind=val(h,'wind_speed_10m',x.i),gust=val(h,'wind_gusts_10m',x.i);
   const next=idx.slice(k+1,k+4).map(y=>val(h,'precipitation',y.i));
   const hour=Number(x.t.slice(11,13));
   const ok=finite(rain)&&rain<=0.1&&next.length===3&&next.every(finite)&&next.every(v=>v<=0.1)&&finite(wind)&&wind>=3&&wind<=15&&finite(gust)&&gust<=25&&hour>=6&&hour<19;
   candidates.push({t:x.t,ok});
  }
  let run=[];const flush=()=>{if(run.length>=2)out.windows.push({start:run[0].t,end:run[run.length-1].t,hours:run.length});run=[];};
  for(const c of candidates){if(c.ok)run.push(c);else flush();}flush();
  out.windows=out.windows.sort((a,b)=>b.hours-a.hours||a.start.localeCompare(b.start)).slice(0,3);
  out.notes.push('Períodos de menor restrição: sem chuva prevista na hora e nas 3 seguintes, vento 3–15 km/h, rajadas ≤25 km/h, 6h–19h. Triagem genérica para planejamento; não substitui a avaliação da operação específica, a bula e a medição no talhão.');
  // headline
  const wet=focus&&finite(focus.p_gt_1_mm)?focus.p_gt_1_mm:null;
  if(wet!==null){const day=focus.date===tomorrow?'amanhã':'hoje';out.headline=wet>=.7?`Chuva provável ${day}.`:wet>=.4?`Chuva possível ${day}, com modelos divididos.`:`Pouca chuva esperada ${day}.`;}
  else if(finite(det24))out.headline=det24>=5?'Chuva prevista nas próximas 24 h (previsão determinística).':'Pouca chuva prevista nas próximas 24 h (previsão determinística).';
  else out.headline='Previsão horária incompleta para as próximas 24 h.';
  out.ready=true;
  return out;
 }
 function render(state,now=Date.now()){
  const box=typeof document!=='undefined'?document.getElementById('farm-summary'):null;if(!box)return;
  const s=build(state,now);
  const tone=t=>({wet:'tone-wet',hot:'tone-hot',windy:'tone-windy',neutral:''}[t]||'');
  const point=state?.site?.custom?'coordenadas selecionadas':(state?.site?.id==='diamantino'?'Diamantino–MT':'Naviraí–MS');
  box.innerHTML=`<div class="farm-head"><div><span class="tag">COMO ESTARÁ O TEMPO NA MINHA FAZENDA?</span><h2>${esc(s.headline)}</h2><p>${esc(point)} · resumo gerado a partir da previsão publicada; percentuais são frequências de membros, não probabilidades calibradas.</p></div></div>
  <div class="farm-cards">${s.cards.map(c=>`<article class="farm-card ${tone(c.tone)}"><span class="label">${esc(c.label)}</span><strong>${esc(c.value)}</strong><span class="detail">${esc(c.detail||'')}</span>${c.note?`<small>${esc(c.note)}</small>`:''}</article>`).join('')}</div>
  <div class="farm-grid">
   <section class="farm-block"><h3>Riscos a observar</h3><ul class="risk-list">${s.risks.map(r=>`<li class="risk-${esc(r.kind)}">${esc(r.text)}</li>`).join('')}</ul></section>
   <section class="farm-block"><h3>Concordância entre modelos e idade dos dados</h3>${s.sentences.map(t=>`<p>${esc(t)}</p>`).join('')}</section>
   <section class="farm-block"><h3>Próximos períodos com menor restrição meteorológica (48 h)</h3>${s.windows.length?`<ul class="window-list">${s.windows.map(w=>`<li><strong>${esc(w.start.slice(8,10))}/${esc(w.start.slice(5,7))} ${esc(w.start.slice(11,16))}–${esc(w.end.slice(11,16))}</strong> · ${w.hours} horas consecutivas</li>`).join('')}</ul>`:state?.deterministic?.hourly?'<p>Nenhum período de 2 h ou mais passou pela triagem genérica nas próximas 48 h.</p>':'<p>Triagem indisponível sem previsão horária determinística.</p>'}<small>${esc(s.notes[0]||'')}</small></section>
  </div>`;
 }
 root.CampoSummary={build,render,rain24Window,formatRainWindow,_test:{agreementSentence,futureHours,localMillis}};
 if(typeof module==='object'&&module.exports)module.exports=root.CampoSummary;
})(typeof window!=='undefined'?window:globalThis);
