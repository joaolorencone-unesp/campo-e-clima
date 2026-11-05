'use strict';
/** Campo e Clima v4 — physical stations: observed values, forecast verification at the station
 * coordinates and corrections validated out of sample. Reads data/stations/index.json and one
 * JSON per station (published by the scientific workflow). The corrected forecast is computed in
 * the browser from the published parameters and is always shown next to the raw value. */
(function(root){
 const $=id=>typeof document==='undefined'?null:document.getElementById(id);
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const finite=v=>typeof v==='number'&&Number.isFinite(v);
 const fmt=(v,d=1)=>finite(v)?v.toFixed(d).replace('.',','):'—';
 const LEADS=[1,2,3,7];
 const VARS=[['t_max','T máx diária (°C)'],['t_min','T mín diária (°C)'],['rain_mm','Chuva diária (mm)'],['temperature_2m','Temperatura horária (°C)'],['relative_humidity_2m','Umidade horária (%)'],['wind_speed_10m','Vento horário (km/h)'],['wind_gusts_10m','Rajada horária (km/h)'],['radiation_mj','Radiação diária (MJ/m²)'],['et0_mm','ET₀ diária (mm)'],['wind_mean_kmh','Vento médio diário (km/h)']];
 const METHOD={bias:'viés aditivo',hourly_bias:'viés por hora do dia',linear:'regressão linear',ratio:'fator multiplicativo',quantile_map:'mapeamento de quantis'};
 let index=null,active=null,variable='t_max';const cache=new Map();
 async function getJSON(url){const r=await fetch(url,{cache:'no-store'});if(!r.ok)throw Error('HTTP '+r.status);return r.json();}
 function dateBR(iso){return iso?`${iso.slice(8,10)}/${iso.slice(5,7)}`:'—';}
 function currentLocationId(){const st=typeof state!=='undefined'?state:null;return st?.site?.id||'navirai';}
 function applyCorrection(params,x,hour){
  if(!params||!finite(x))return null;
  switch(params.method){
   case 'bias':return x+params.bias;
   case 'ratio':return x*params.ratio;
   case 'linear':return params.intercept+params.slope*x;
   case 'hourly_bias':return x+(params.by_hour?.[String(hour??0)]??params.global_bias??0);
   case 'quantile_map':{
    const qx=params.qx||[],qy=params.qy||[];
    if(qx.length<2)return x*(params.fallback_ratio??1);
    if(!(x>params.threshold))return 0;
    if(x>qx[qx.length-1])return x*(qx[qx.length-1]>0?qy[qy.length-1]/qx[qx.length-1]:1);
    let i=0;while(i<qx.length-1&&qx[i+1]<x)i++;
    const span=qx[i+1]-qx[i];return span>0?qy[i]+(qy[i+1]-qy[i])*(x-qx[i])/span:qy[i];}
   default:return null;
  }
 }
 function clip(variable,v){if(!finite(v))return v;if(['rain_mm','wind_speed_10m','wind_gusts_10m','wind_mean_kmh','gust_max_kmh','radiation_mj','et0_mm'].includes(variable))return Math.max(0,v);if(variable==='relative_humidity_2m')return Math.min(100,Math.max(0,v));return v;}
 function recommended(report,model,lead,variable){return (report.verification||[]).find(v=>v.model===model&&v.lead_days===lead&&v.variable===variable&&v.recommended)?.recommended||null;}
 function matrix(report,variable){
  const items=(report.verification||[]).filter(v=>v.variable===variable);
  const models=[...new Set(items.map(v=>v.model))];
  if(!models.length)return '<p class="caption">Sem pares avaliados para esta variável.</p>';
  const cell=v=>{if(!v)return '<td>—</td>';const raw=v.raw_all_pairs;if(!raw)return `<td><small>${esc(v.status==='insufficient_pairs'?'poucos pares':v.status)}</small></td>`;
   const rec=v.recommended;const skill=rec?` <span class="agree ok" title="${esc(METHOD[rec.method]||rec.method)} · MAE fora da amostra ${fmt(rec.evidence.mae_raw,2)} → ${fmt(rec.evidence.mae_corrected,2)}">✓ ${fmt(rec.evidence.skill_mae*100,0)}%</span>`:(v.status==='evaluated'?' <span class="agree" title="sem correção validada">bruto</span>':'');
   return `<td><strong>${fmt(raw.mae,variable==='rain_mm'?1:2)}</strong><small>viés ${raw.bias>0?'+':''}${fmt(raw.bias,variable==='rain_mm'?1:2)} · n ${raw.n}</small>${skill}</td>`;};
  return `<div class="board-scroll"><table class="board station-matrix"><thead><tr><th>Modelo</th>${LEADS.map(l=>`<th>D${l}</th>`).join('')}</tr></thead><tbody>${models.map(m=>`<tr><td><strong>${esc(m==='multimodelo_media'?'Média multimodelo':m)}</strong></td>${LEADS.map(l=>cell(items.find(v=>v.model===m&&v.lead_days===l))).join('')}</tr>`).join('')}</tbody></table></div><p class="caption">Erro absoluto médio (MAE) da previsão bruta por antecedência; viés positivo = modelo acima do medido. ✓ indica correção validada fora da amostra com o ganho de MAE; "bruto" indica que nenhuma correção simples melhorou de forma significativa.</p>`;
 }
 function recentTable(report,n=14){
  const days=(report.observations?.daily||[]).filter(d=>finite(d.t_max)||finite(d.rain_mm)).slice(-n).reverse();
  if(!days.length)return '<p class="caption">Sem dias completos recentes.</p>';
  return `<div class="board-scroll"><table class="board recent"><thead><tr><th>Dia</th><th>T máx</th><th>T mín</th><th>Chuva</th><th>UR mín</th><th>Rajada máx</th></tr></thead><tbody>${days.map(d=>`<tr><td><strong>${dateBR(d.date)}</strong></td><td><strong class="tmax">${fmt(d.t_max,1)}°</strong></td><td><strong class="tmin">${fmt(d.t_min,1)}°</strong></td><td><strong class="rain-big">${finite(d.rain_mm)?fmt(d.rain_mm,1)+' mm':`<small title="dia com horas faltantes: a soma das horas medidas é um limite inferior, não o total">${finite(d.rain_partial_mm)?'≥ '+fmt(d.rain_partial_mm,1)+' mm':'—'} (${d.rain_hours??0}/24 h)</small>`}</strong></td><td>${fmt(d.rh_min,0)}%</td><td>${fmt(d.gust_max_kmh,0)} km/h</td></tr>`).join('')}</tbody></table></div>`;
 }
 function qcSummary(report){
  const qc=report.observations?.qc||{};const h=qc.hourly,d=qc.daily;
  if(h){const flagged=Object.entries(h).filter(([k,v])=>typeof v==='object').map(([k,v])=>{const bad=Object.entries(v).filter(([f])=>!['valid','missing'].includes(f)).reduce((a,[,n])=>a+n,0);return bad?`${k}: ${bad}`:null;}).filter(Boolean);
   return `${h.rows} horas no arquivo · ${h.fully_missing_rows} horas sem nenhum dado · valores suspeitos sinalizados (não corrigidos): ${flagged.length?flagged.join(', '):'nenhum'}`;}
  if(d)return `${d.rows} dias no arquivo · ${d.missing_calendar_days??0} dias ausentes no calendário`;
  return 'sem resumo de qualidade';
 }
 function diagnosticsPlot(report,container){
  const plot=$(container);if(!plot||!root.Plotly)return;
  const items=(report.verification||[]).filter(v=>v.variable==='temperature_2m'&&v.lead_days===1&&v.diagnostics?.bias_by_local_hour?.length);
  if(!items.length){plot.innerHTML='<p class="caption">Sem diagnóstico horário (estação com dados diários).</p>';return;}
  const traces=items.map(v=>({type:'scatter',mode:'lines+markers',name:v.model==='multimodelo_media'?'Média multimodelo':v.model,x:v.diagnostics.bias_by_local_hour.map(b=>b.hour),y:v.diagnostics.bias_by_local_hour.map(b=>b.bias),hovertemplate:'%{x}h: viés %{y:.2f} °C<extra>%{fullData.name}</extra>'}));
  root.Plotly.react(plot,traces,{margin:{l:45,r:10,t:10,b:40},xaxis:{title:'hora local',dtick:3},yaxis:{title:'viés (modelo − estação) °C',zeroline:true},legend:{orientation:'h',y:-0.3},paper_bgcolor:'rgba(0,0,0,0)',plot_bgcolor:'rgba(0,0,0,0)'},{displayModeBar:false,responsive:true});
 }
 function seriesPlot(report,container){
  const plot=$(container);if(!plot||!root.Plotly)return;
  const entries=Object.entries(report.series||{});if(!entries.length){plot.innerHTML='<p class="caption">Sem série comparada.</p>';return;}
  const best=report.headline?.rain_mm?.model;const [model,s]=entries.find(([m])=>m===best)||entries[0];
  const traces=[{type:'bar',name:'Medido na estação',x:s.dates,y:s.obs_rain_mm,marker:{color:'#0b8df0'}},{type:'bar',name:`Previsto D1 (${model==='multimodelo_media'?'média multimodelo':model})`,x:s.dates,y:s.fc_rain_mm,marker:{color:'#9fb3c8'}}];
  root.Plotly.react(plot,traces,{barmode:'group',margin:{l:40,r:10,t:10,b:40},yaxis:{title:'mm/dia'},legend:{orientation:'h',y:-0.25},paper_bgcolor:'rgba(0,0,0,0)',plot_bgcolor:'rgba(0,0,0,0)'},{displayModeBar:false,responsive:true});
 }
 function headline(report){
  const h=report.headline||{};const label={t_max:'T máx',t_min:'T mín',rain_mm:'Chuva diária'};
  const rows=Object.entries(h).map(([k,v])=>`<div class="farm-card"><small>${esc(label[k]||k)} · melhor modelo em D1</small><strong>${esc(v.model==='multimodelo_media'?'Média multimodelo':v.model)}</strong><span>MAE ${fmt(v.mae_raw,k==='rain_mm'?1:2)} · viés ${v.bias_raw>0?'+':''}${fmt(v.bias_raw,k==='rain_mm'?1:2)} · ${v.n} dias${v.recommended?' · correção validada':''}</span></div>`);
  return rows.length?`<div class="farm-cards">${rows.join('')}</div>`:'';
 }
 async function correctedForecast(report,container){
  const box=$(container);if(!box)return;
  const point=report.forecast_point;const st=report.station;
  const models=Object.entries(report.models||{}).filter(([m,s])=>s.state==='ok'||s.state==='partial').map(([m])=>m);
  const preferred=report.headline?.t_max?.model||models[0];if(!preferred){box.textContent='Sem modelo avaliado para esta estação.';return;}
  const members=preferred==='multimodelo_media'?(report.models[preferred]?.members||[]):[preferred];
  box.innerHTML='<p class="caption">Consultando a previsão atual nas coordenadas da estação…</p>';
  try{
   const q=new URLSearchParams({latitude:point.latitude,longitude:point.longitude,models:members.join(','),daily:'temperature_2m_max,temperature_2m_min,precipitation_sum',timezone:st.timezone||'America/Campo_Grande',forecast_days:'7'});
   const r=await fetch('https://api.open-meteo.com/v1/forecast?'+q);if(!r.ok)throw Error('HTTP '+r.status);
   const p=await r.json();const d=p.daily||{};const suffix=members.length>1;
   const pick=(key,i)=>{const vals=members.map(m=>d[suffix?`${key}_${m}`:key]?.[i]).filter(finite);return vals.length===members.length?vals.reduce((a,b)=>a+b,0)/vals.length:null;};
   const rows=(d.time||[]).map((date,i)=>{const lead=i<=1?1:i<=3?i:7;const approx=i===0||i>3;
    const cells=[['t_max',pick('temperature_2m_max',i)],['t_min',pick('temperature_2m_min',i)],['rain_mm',pick('precipitation_sum',i)]].map(([v,raw])=>{const rec=recommended(report,preferred,lead,v);const corr=rec?clip(v,applyCorrection(rec.parameters,raw)):null;
     return `<td><strong>${fmt(raw,v==='rain_mm'?1:0)}</strong>${rec?`<br><span class="corr" title="${esc(METHOD[rec.method]||rec.method)}; validado em D${lead}${approx?' (aproximação para este dia)':''}">corrigido ${fmt(corr,v==='rain_mm'?1:0)}</span>`:'<br><small>sem correção validada</small>'}</td>`;});
    return `<tr><td><strong>${dateBR(date)}</strong><small>${i===0?'hoje':i===1?'amanhã':'D'+i}${approx?'*':''}</small></td>${cells.join('')}</tr>`;});
   box.innerHTML=`<div class="board-scroll"><table class="board corrected"><thead><tr><th>Dia</th><th>T máx (°C)</th><th>T mín (°C)</th><th>Chuva (mm)</th></tr></thead><tbody>${rows.join('')}</tbody></table></div><p class="caption">Modelo ${esc(preferred==='multimodelo_media'?'média multimodelo ('+members.join(', ')+')':preferred)} no ponto ${Number(point.latitude).toFixed(4)}, ${Number(point.longitude).toFixed(4)}. Valor bruto em destaque; "corrigido" aplica apenas correções validadas fora da amostra para a antecedência correspondente. * hoje e D4–D6 usam os parâmetros da antecedência validada mais próxima (aproximação).</p>`;
  }catch(err){box.innerHTML=`<p class="notice warning">Não foi possível consultar a previsão atual (${esc(err.message)}).</p>`;}
 }
 function renderStation(report){
  const body=$('stations-body');if(!body)return;
  const st=report.station;const point=report.forecast_point||{};
  const coords=finite(st.latitude)?`${st.latitude.toFixed(4)}, ${st.longitude.toFixed(4)} · ${st.altitude_m??'—'} m`:'coordenadas não informadas no arquivo (comparação no ponto municipal)';
  body.innerHTML=`<div class="station-head"><div><h4>${esc(st.name)}</h4><p class="caption">${esc(st.institution)} · ${esc(coords)}${finite(report.station_to_forecast_point_km)&&report.station_to_forecast_point_km>0.5?` · previsão a ${fmt(report.station_to_forecast_point_km,1)} km`:''} · período ${esc(dateBR(report.observations.period?.[0]))}–${esc(dateBR(report.observations.period?.[1]))}</p><p class="caption">${esc(qcSummary(report))}</p></div></div>
  ${headline(report)}
  <div class="grid2"><article class="subpanel"><h5>Últimos dias medidos na estação</h5>${recentTable(report)}</article><article class="subpanel"><h5>Chuva diária: medido × previsto D1</h5><div id="station-series-plot" class="plot"></div></article></div>
  <article class="subpanel"><div class="panel-head"><h5>Erro dos modelos por antecedência</h5><label>Variável <select id="station-variable">${VARS.map(([k,l])=>`<option value="${k}"${k===variable?' selected':''}>${esc(l)}</option>`).join('')}</select></label></div><div id="station-matrix">${matrix(report,variable)}</div></article>
  <div class="grid2"><article class="subpanel"><h5>Viés da temperatura por hora do dia (D1)</h5><div id="station-bias-plot" class="plot"></div></article><article class="subpanel"><h5>Previsão atual nesta estação: bruta e corrigida</h5><button type="button" class="pill" id="station-corrected-btn">Consultar previsão corrigida</button><div id="station-corrected"></div></article></div>
  <p class="caption">Limitações: ${esc((report.limitations||[]).join(' '))}</p>`;
  $('station-variable').addEventListener('change',e=>{variable=e.target.value;$('station-matrix').innerHTML=matrix(report,variable);});
  $('station-corrected-btn').addEventListener('click',()=>void correctedForecast(report,'station-corrected'));
  seriesPlot(report,'station-series-plot');diagnosticsPlot(report,'station-bias-plot');
 }
 async function select(slug){
  active=slug;for(const b of document.querySelectorAll('#stations-tabs button'))b.classList.toggle('active',b.dataset.slug===slug);
  const entry=index.stations.find(s=>s.slug===slug);if(!entry)return;
  try{if(!cache.has(slug))cache.set(slug,await getJSON('data/stations/'+entry.file));renderStation(cache.get(slug));}
  catch(err){$('stations-body').innerHTML=`<p class="notice warning">Relatório da estação indisponível (${esc(err.message)}).</p>`;}
 }
 function renderTabs(){
  const tabs=$('stations-tabs');if(!tabs)return;
  tabs.innerHTML=index.stations.map(s=>`<button type="button" data-slug="${esc(s.slug)}" role="tab">${esc(s.name)}<small>${esc(s.location_id==='navirai'?'Naviraí':'Diamantino')} · ${s.daily_rows} dias</small></button>`).join('');
  tabs.addEventListener('click',e=>{const b=e.target.closest('button[data-slug]');if(b)void select(b.dataset.slug);});
 }
 async function load(){
  const status=$('stations-status');if(!status)return;
  try{
   if(!index)index=await getJSON('data/stations/index.json');
   status.className='notice';status.innerHTML=`<strong>${index.stations.length} estações</strong> com observações importadas · resultados gerados ${esc(new Date(index.generated_at_utc).toLocaleString('pt-BR'))}.`;
   if(!$('stations-tabs').children.length)renderTabs();
   const loc=currentLocationId();const first=index.stations.find(s=>s.location_id===loc)||index.stations[0];
   if(first&&active!==first.slug)await select(first.slug);
  }catch(err){status.className='notice muted';status.textContent='Resultados das estações ainda não publicados pelo fluxo científico (gerados diariamente após a importação dos arquivos). '+(err.message||'');}
 }
 async function overviewCard(){
  const card=$('station-overview-card'),box=$('station-overview');if(!card||!box)return;
  if(root.CampoLocation?.getPoint?.()?.custom){card.hidden=true;return;}
  try{
   if(!index)index=await getJSON('data/stations/index.json');
   const loc=currentLocationId();const entries=index.stations.filter(s=>s.location_id===loc&&s.recent?.length);
   if(!entries.length){card.hidden=true;return;}
   box.innerHTML=entries.map(s=>{const last=s.recent[s.recent.length-1];const chk=s.yesterday_check;
    return `<div class="station-mini"><div class="station-mini-head"><strong>${esc(s.name)}</strong><small>último dia completo: ${dateBR(last.date)}</small></div><div class="farm-cards"><div class="farm-card"><small>T máx medida</small><strong class="tmax">${fmt(last.t_max,1)}°</strong></div><div class="farm-card"><small>T mín medida</small><strong class="tmin">${fmt(last.t_min,1)}°</strong></div><div class="farm-card tone-wet"><small>Chuva medida</small><strong>${finite(last.rain_mm)?fmt(last.rain_mm,1)+' mm':'—'}</strong></div>${chk?`<div class="farm-card"><small>Conferência D1 em ${dateBR(chk.date)}</small><strong>${finite(chk.obs_rain_mm)?fmt(chk.obs_rain_mm,1):'—'} mm</strong><span>previsto ${fmt(chk.fc_rain_mm,1)} mm · T máx ${fmt(chk.obs_t_max,0)}° (prev. ${fmt(chk.fc_t_max,0)}°)</span></div>`:''}</div><p class="caption">Últimos 7 dias: ${s.recent.map(d=>`${dateBR(d.date)} ${finite(d.rain_mm)?fmt(d.rain_mm,0)+' mm':'—'}`).join(' · ')}. Detalhes e erro dos modelos na aba Observações.</p></div>`;}).join('');
   card.hidden=false;
  }catch(_){card.hidden=true;}
 }
 if(typeof document!=='undefined'){
  document.getElementById('tabs')?.addEventListener('click',e=>{if(e.target.closest('button[data-tab]')?.dataset.tab==='observations')setTimeout(load,60);});
  root.addEventListener('campo:forecast-rendered',()=>void overviewCard());
  root.addEventListener('campo:location-changed',()=>setTimeout(()=>{void overviewCard();if(document.getElementById('observations')?.classList.contains('active'))void load();},80));
 }
 root.CampoStations={load,select,render:renderStation,overviewCard,applyCorrection,matrix,_test:{clip,recommended}};
 if(typeof module==='object'&&module.exports)module.exports=root.CampoStations;
})(typeof window!=='undefined'?window:globalThis);
