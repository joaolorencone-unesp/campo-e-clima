'use strict';
/** Campo e Clima v2.1 — transparent decision support, NOT automated flight/spray authorisation.
 * The tool intentionally does not recommend application height, flight speed, dose or nozzle settings.
 * All forecast data are gridded model output. Validity, thresholds and missingness are explicit.
 */
(() => {
 const byId=id=>document.getElementById(id);
 const finite=n=>typeof n==='number'&&Number.isFinite(n);
 const val=(a,i)=>Array.isArray(a)&&finite(a[i])?a[i]:null;
 const escape=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const fmt=(x,d=1)=>finite(x)?x.toFixed(d).replace('.',','):'—';
 const sector=deg=>['N','NE','L','SE','S','SO','O','NO'][Math.round((((deg%360)+360)%360)/45)%8];
 const limits={herb:1.2,fung:1.5,inse:1.4};
 const HOUR_MS=3600000;
 const cache=new Map(); let recentBusy=false,recentController=null,renderCounter=0,recentToken=0;
 const stateData=()=>typeof state!=='undefined'?state:null;
 const currentPoint=()=>window.CampoLocation?.getPoint?.()||{latitude:-23.065,longitude:-54.190,name:'Naviraí–MS'};
 const pointKey=p=>`${Number(p.latitude).toFixed(4)},${Number(p.longitude).toFixed(4)}`;
 function parseLocalHour(time,offsetSeconds){
  if(typeof time!=='string'||!/^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}/.test(time)||!finite(offsetSeconds))return null;
  const utc=Date.parse(time+'Z');return Number.isFinite(utc)?utc-offsetSeconds*1000:null;
 }
 function isContiguous(t,first,last){
  if(last>=t.length)return false;
  for(let i=first+1;i<=last;i++)if(Date.parse(t[i]+'Z')-Date.parse(t[i-1]+'Z')!==HOUR_MS)return false;
  return true;
 }
 function nextRain(h,i,span=3){
  const times=h?.time;if(!Array.isArray(times)||!isContiguous(times,i,i+span))return null;
  const xs=[];for(let j=i+1;j<=i+span;j++){
   const x=val(h.precipitation,j);if(x===null||x<0)return null;xs.push(x);
  }
  return xs.reduce((a,b)=>a+b,0);
 }
 function getHours(h,offsetSeconds,max=72,now=Date.now()){
  if(!Array.isArray(h?.time)||!finite(offsetSeconds))return [];
  return h.time.map((time,i)=>({time,i,millis:parseLocalHour(time,offsetSeconds)})).filter(z=>z.millis!==null&&z.millis>now).slice(0,max);
 }
 function assess(h,index,product='herb',gustIndex=index){
  const wind=val(h.wind_speed_10m,index),gust=val(h.wind_gusts_10m,gustIndex);
  const temp=val(h.temperature_2m,index),rh=val(h.relative_humidity_2m,index),vpd=val(h.vapour_pressure_deficit,index);
  const direction=val(h.wind_direction_10m,index),rain=nextRain(h,index,3);
  const reasons=[];const missing=[];
  if(wind===null)missing.push('vento');else if(wind<3||wind>10)reasons.push('vento fora de 3–10 km/h');
  if(gust===null)missing.push('rajadas');else if(gust>25)reasons.push('rajada >25 km/h');
  if(temp===null)missing.push('temperatura');else if(temp>=30)reasons.push('temperatura ≥30 °C');
  if(rh===null)missing.push('umidade');else if(rh<55)reasons.push('UR <55%');
  if(vpd===null)missing.push('VPD');else if(vpd>=limits[product])reasons.push(`VPD ≥${fmt(limits[product])} kPa`);
  if(rain===null)missing.push('chuva +3 h');else if(rain>0.1)reasons.push('chuva >0,1 mm nas próximas 3 h');
  const attention=[];
  let cls='triagem';
  if(reasons.length)cls='restrita';
  else if(missing.length)cls='indeterminada';
  else{
   if(wind>8)attention.push('vento perto do limite de triagem');
   if(gust>20)attention.push('rajada perto do limite de triagem');
   if(rh<60)attention.push('umidade perto do limite de triagem');
   if(temp>=28)attention.push('temperatura perto do limite de triagem');
   if(vpd>limits[product]*.85)attention.push('VPD perto do limite de triagem');
   if(rain>0)attention.push('chuva residual nas próximas 3 h');
   if(attention.length)cls='marginal';
  }
  // These are *numerical filters*, not validation of stability, drift, product label or spray operation.
  return {cls,reasons,attention,missing,wind,gust,temp,rh,vpd,direction,rain};
 }
 function currentData(){
  const raw=stateData(),det=raw?.deterministic||{},hourly=det.hourly||{};
  const offset=det.utc_offset_seconds;
  return {raw,det,hourly,offset,hours:getHours(hourly,offset,72)};
 }
 function category(a,op){
  if(op==='spray')return a.cls;
  if(a.rain===null||a.wind===null||a.gust===null)return 'indeterminada';
  if(op==='harvest'&&(a.rain>0.1||a.gust>35))return 'marginal';
  if(op==='seeding'&&(a.rain>5||a.gust>40))return 'marginal';
  if(op==='irrigation'&&a.rain>5)return 'marginal';
  return 'informativa';
 }
 function catLabel(cls){return {triagem:'Passa filtros*',marginal:'Atenção',restrita:'Restrição',indeterminada:'Indeterminada',informativa:'Informativo'}[cls]||'—';}
 function opLabel(op){return {spray:'pulverização',seeding:'plantio',harvest:'colheita',irrigation:'irrigação'}[op]||'operação';}
 function ensembleInfo(raw,day){const a=(raw?.rain_ensemble_daily||[]).find(r=>r.date===day);
  if(!a||!finite(a.p_gt_0_1_mm)||!finite(a.p_gt_1_mm))return null;
  return {mean:finite(a.mean_mm)?a.mean_mm:null,trace:a.p_gt_0_1_mm,over1:a.p_gt_1_mm,over10:finite(a.p_gt_10_mm)?a.p_gt_10_mm:null,models:a.model_count||a.models||0,members:a.member_count||a.members||0};
 }
 function freshness(stamp,limit,now=Date.now()){
  const timestamp=Date.parse(stamp),age=(now-timestamp)/60000;
  if(!finite(age)||age<0)return {state:'unknown',label:'idade desconhecida'};
  const stale=age>limit;
  return {state:stale?'stale':'recent',timestamp,label:`${stale?'coleta antiga':'coleta recente'} · há ${Math.floor(age)} min`};
 }
 function ensembleFreshness(raw,now=Date.now()){
  const acquisitions=Object.values(raw?.ensemble_models||{})
   .filter(model=>model.state==='ok'&&model.precipitation_members>0)
   .map(model=>Date.parse(model.collected_at_utc));
  if(!acquisitions.length||!acquisitions.every(stamp=>finite(stamp)&&stamp<=now))return freshness(null,180,now);
  return freshness(new Date(Math.min(...acquisitions)).toISOString(),180,now);
 }
 function hourReason(a,op){
  if(op==='spray')return [...a.reasons,...a.attention,...(a.missing.length?[`faltam ${a.missing.join(', ')}`]:[])].join(' · ')||'Filtros numéricos sem restrição; verificação local pendente';
  const missing=[['chuva',a.rain],['vento',a.wind],['rajada',a.gust]].filter(([,value])=>value===null);
  if(missing.length)return 'Faltam dados de '+missing.map(([label])=>label).join(', ');
  if(op==='harvest')return a.rain>0.1?'Chuva prevista em 3 h':a.gust>35?'Rajadas elevadas':'Verificar condição real do solo/produto';
  if(op==='seeding')return a.rain>5?'Chuva nas 3 h seguintes':a.gust>40?'Rajadas fortes':'Avaliar umidade real do solo e plantabilidade';
  return a.rain>5?'Chuva nas 3 h seguintes':'Necessidade hídrica não estimada';
 }
 function windowRuns(rows,duration,op){
  const accepted=op==='spray'?'triagem':'informativa';
  const windows=[];
  let streak=[];
  const finish=reason=>{
   if(streak.length>=duration)windows.push({hours:streak.slice(0,duration),length:streak.length,reason});
   streak=[];
  };
  for(const row of rows){
   if(streak.length&&row.millis-streak.at(-1).millis!==HOUR_MS)finish('Lacuna na previsão');
   if(category(row.a,op)===accepted)streak.push(row);
   else finish(hourReason(row.a,op));
  }
  finish('Fim do período exibido');
  return windows;
 }
 function displayHour(millis,offset){
  const iso=new Date(millis+offset*1000).toISOString();
  return `${iso.slice(8,10)}/${iso.slice(5,7)} ${iso.slice(11,16)}`;
 }
 function sourceStatus(source,offset){
  return finite(source.timestamp)?`${source.label} · ${displayHour(source.timestamp,offset)} (hora local)` : source.label;
 }
 function renderWindows(rows,hourly,raw,op,product,offset,forecastFresh,ensembleAge){
  const date=byId('agro-window-date'),duration=Number(byId('agro-window-duration').value);
  const target=byId('agro-window-results'),message=byId('agro-window-status');
  const observation=byId('agro-window-observation');
  const selected=date.value;
  const days=[...new Set(rows.map(r=>r.time.slice(0,10)))];
  date.innerHTML='<option value="">Qualquer dia no horizonte</option>'+days.map(d=>`<option value="${escape(d)}">${escape(d.split('-').reverse().join('/'))}</option>`).join('');
  date.value=days.includes(selected)?selected:'';
  date.disabled=!days.length;
  target.innerHTML='';
  observation.textContent='';
  if(!rows.length){message.textContent='Aguardando previsão horária para este ponto.';return;}
  const station=raw.official?.inmet_hourly_nearby;
  const latest=station?.records?.find(r=>finite(Date.parse(r.valid_at_utc)));
  observation.textContent=station?.state==='ok'&&latest
   ?`Medição de estação: ${station.station_name} (${station.station_code}) · ${fmt(station.distance_km)} km do ponto · registro de ${displayHour(Date.parse(latest.valid_at_utc),offset)} (hora local). Consulte Observações & fontes. Verificação no talhão é separada.`
   :'Medição horária de estação indisponível para este ponto nesta edição.';
  if(forecastFresh.state!=='recent'){
   message.textContent=`Janelas indisponíveis para planejamento (${forecastFresh.label}). Atualize a previsão do ponto.`;return;
  }
  const filtered=rows.filter(r=>!date.value||r.time.startsWith(date.value+'T')).map(r=>({
   ...r,a:assess(hourly,r.i,product,r.i+1),rain:nextRain(hourly,r.i,1)
  }));
  const windows=windowRuns(filtered,duration,op).slice(0,2);
  const complete=filtered.filter(r=>op==='spray'?!r.a.missing.length:![r.a.rain,r.a.wind,r.a.gust].includes(null)).length;
  const blocked=filtered.find(r=>!['triagem','informativa'].includes(category(r.a,op)));
  const summary=windows.length?'Horários locais do ponto.':'Nenhuma janela contínua encontrada para esta duração.';
  const blocker=!windows.length&&blocked?` Primeiro limite às ${displayHour(blocked.millis,offset)}: ${hourReason(blocked.a,op)}.`:'';
  message.textContent=`${summary}${blocker} Dados suficientes para avaliar ${complete} de ${filtered.length} horários disponíveis. ${op==='spray'?'Confira bula, deriva, estabilidade e medições no talhão.':'Confira as condições reais da operação no talhão.'}`;
  target.innerHTML=windows.map(({hours,length,reason},i)=>{
   const first=hours[0],end=first.millis+duration*HOUR_MS;
   const range=`${displayHour(first.millis,offset)} a ${displayHour(end,offset)}`;
   const rain=hours.reduce((sum,r)=>sum+r.rain,0),gust=Math.max(...hours.map(r=>r.a.gust));
   const ensemble=(raw.rain_ensemble_hourly||[]).find(r=>r.time===first.time)?.windows?.[duration];
   const frequency=finite(ensemble?.p_gt_1_mm)?`${fmt(ensemble.p_gt_1_mm*100,0)}% para chuva >1 mm · ${ensemble.models} modelos / ${ensemble.members} membros · ${sourceStatus(ensembleAge,offset)} (aquisição mais antiga dos modelos de chuva)${ensembleAge.state==='recent'?'':'. Use apenas como referência da coleta'}. Frequência sem calibração local.`:'Frequência do ensemble indisponível para este intervalo.';
   return `<article class="agro-insight"><h4>${i===0?'Primeira janela':'Alternativa'} · ${escape(range)}</h4>
    <p><strong>${op==='spray'?'Passa filtros experimentais':'Triagem meteorológica preliminar'}</strong> · ${duration} h de ${length} h consecutivas.</p>
    <p>Previsão em grade · ${escape(sourceStatus(forecastFresh,offset))}. ${fmt(rain,2)} mm na janela · rajada máxima de ${fmt(gust)} km/h a 10 m.</p>
    <p>Fim da sequência às ${escape(displayHour(first.millis+length*HOUR_MS,offset))} · ${escape(reason)}.</p>
    <p>Ensembles no mesmo intervalo · ${escape(frequency)}</p>
    <details><summary>Ver condições por hora</summary><ul>${hours.map(r=>`<li>${escape(displayHour(r.millis,offset))} · chuva ${fmt(r.rain,2)} mm · vento ${fmt(r.a.wind)} km/h · rajada ${fmt(r.a.gust)} km/h</li>`).join('')}</ul></details></article>`;
  }).join('');
 }
 function kp(label,value,note){return `<div class="agro-kpi"><small>${escape(label)}</small><strong>${escape(value)}</strong><span>${escape(note)}</span></div>`;}
 function insight(title,text,kind='normal'){return `<div class="agro-insight ${kind}"><strong>${escape(title)}</strong>${escape(text)}</div>`;}
 function renderPlan(){
  const target=byId('agro-plan-result');if(!target)return;
  const op=byId('agro-operation').value;
  if(op!=='spray'){
   target.className='notice muted';target.textContent='Os campos de configuração do T100 só são utilizados como lista de verificações na operação de pulverização. Para outras operações, consulte a linha do tempo.';return;
  }
  const h=Number(byId('agro-flight-height').value),heightText=byId('agro-flight-height').value.trim();
  const crop=byId('agro-crop').value.trim(),drops=byId('agro-droplet').value,sens=byId('agro-sensitive').value;
  const done=['agro-label-checked','agro-field-wind','agro-inversion-checked'].filter(id=>byId(id).checked).length;
  const checks=[];
  if(!crop)checks.push('informar cultura');
  if(!heightText)checks.push('informar altura pretendida');
  else if(!Number.isFinite(h)||h<=0||h>30)checks.push('revisar altura informada');
  if(!drops)checks.push('informar classe de gotas');
  if(sens==='unknown')checks.push('mapear receptores sensíveis');
  if(sens==='yes')checks.push('avaliar áreas sensíveis e direção de transporte');
  if(!byId('agro-label-checked').checked)checks.push('consultar bula e exigências legais');
  if(!byId('agro-field-wind').checked)checks.push('medir vento e rajadas no talhão');
  if(!byId('agro-inversion-checked').checked)checks.push('verificar estabilidade/inversão');
  target.className='notice warning';
  target.textContent=`Plano T100 • ${done}/3 declarações de verificação marcadas pelo operador. ${checks.length?'Pendente: '+checks.join('; ')+'. ':'Ainda é necessário verificar a adequação técnica, a calibração e as condições do talhão. '}A altura ${heightText&&h>0&&h<=30?fmt(h)+' m':'não informada'} não foi validada nem recomendada pelo software. Nenhum horário constitui autorização de aplicação.`;
 }
 function chartTimeline(rows,op){
  const target=byId('agro-timeplot');if(!target)return;
  if(!rows.length){target.textContent='Sem horas futuras válidas.';return;}
  if(!window.Plotly){target.textContent='Gráfico indisponível; consulte a tabela de horários.';return;}
  if(!target.classList.contains('js-plotly-plot'))target.textContent='';
  const x=rows.map(r=>r.time.replace('T',' '));
  const traces=[{type:'bar',name:'Vento médio 10 m',x,y:rows.map(r=>r.a.wind),marker:{color:'#3f9bc7'}},
   {type:'scatter',name:'Rajadas 10 m',x,y:rows.map(r=>r.a.gust),mode:'lines+markers',line:{color:'#dd934c',width:2},marker:{size:5}}];
  window.Plotly.react(target,traces,{height:320,margin:{l:55,r:15,t:14,b:100},
   yaxis:{title:'km/h'},xaxis:{type:'category',tickangle:-55,nticks:12},
   legend:{orientation:'h',y:-.4},paper_bgcolor:'rgba(0,0,0,0)',plot_bgcolor:'rgba(0,0,0,0)'},
   {responsive:true,displaylogo:false});
 }
 function render(){
  const container=byId('agro');if(!container||!container.classList.contains('active'))return;
  const {raw,det,hourly,hours,offset}=currentData(),status=byId('agro-main-status'),kpBox=byId('agro-kpis'),insBox=byId('agro-insights');
  const op=byId('agro-operation').value,product=byId('agro-product').value,horizon=Number(byId('agro-horizon').value)||48;
  const p=currentPoint();
  const belongsToPoint=finite(raw?.site?.latitude)&&finite(raw?.site?.longitude)&&Math.abs(raw.site.latitude-p.latitude)<0.001&&Math.abs(raw.site.longitude-p.longitude)<0.001;
  byId('agro-product').closest('label').hidden=op!=='spray';
  const future=hours.slice(0,horizon),rows=future.map(z=>({...z,a:assess(hourly,z.i,product)}));
  const forecastAt=det.collected_at_utc||raw?._liveForecastAt;
  const forecastFresh=freshness(forecastAt,120),ensembleAge=ensembleFreshness(raw);
  renderWindows(belongsToPoint?rows:[],hourly,raw,op,product,offset,forecastFresh,ensembleAge);
  const name=currentPoint().name||'Ponto selecionado';
  if(!rows.length||!belongsToPoint){status.className='notice warning';status.textContent=`Sem previsão horária futura validada para ${name}. Nenhuma classificação de operação calculada.`;kpBox.innerHTML='';insBox.innerHTML='';byId('agro-hours-table').querySelector('tbody').innerHTML='<tr><td colspan="8">Sem horários válidos para este ponto.</td></tr>';chartTimeline([],op);renderPlan();return;}
  status.className='notice '+(forecastFresh.state==='recent'?'muted':'warning');
  status.textContent=`${name} • ${rows.length} horas futuras de ${horizon} solicitadas • ${det.model_used||'Previsão em grade'} • ${forecastFresh.label}. Classificações numéricas experimentais; não são observações nem autorização operacional.`;
  const rain24=rows.length>=24 && rows.slice(0,24).every((r,j)=>val(hourly.precipitation,r.i)!==null && (j===0 || r.millis-rows[j-1].millis===3600000))?
   rows.slice(0,24).reduce((sum,r)=>sum+val(hourly.precipitation,r.i),0):null;
  const gustVals=rows.map(r=>r.a.gust).filter(finite),maxGust=gustVals.length?Math.max(...gustVals):null;
  const restricted=rows.filter(r=>['restrita','marginal'].includes(category(r.a,op))).length,missing=rows.filter(r=>category(r.a,op)==='indeterminada').length;
  const day=rows[0].time.slice(0,10),ensemble=ensembleInfo(raw,day);
  kpBox.innerHTML=kp('🌧 Chuva prevista • próximas 24 h',rain24===null?'—':fmt(rain24)+' mm','Open-Meteo determinístico • horas futuras completas')+
   kp('💨 Maior rajada no período',maxGust===null?'—':fmt(maxGust)+' km/h','Modelo a 10 m • não medição na fazenda')+
   kp('🕒 Horas com restrição numérica',`${restricted}/${rows.length}`,op==='spray'?'Filtros experimentais de pulverização':'Critérios experimentais específicos de '+opLabel(op))+
   kp('🌦 Frequência dos ensembles • dia local',ensemble?fmt(ensemble.over1*100,0)+'%':'—',ensemble?`>1 mm em ${day.split('-').reverse().join('/')} • ${ensemble.models} modelos / ${ensemble.members} membros • ${sourceStatus(ensembleAge,offset)} (aquisição mais antiga)`:'Sem frequência multimodelo válida');
  let notes=[];
  if(ensemble)notes.push(insight('Chuva residual versus mensurável',`Neste dia, ${fmt(ensemble.trace*100,0)}% do peso dos membros indica chuva >0,1 mm e ${fmt(ensemble.over1*100,0)}% indica >1 mm. Diferença de ${fmt((ensemble.trace-ensemble.over1)*100,0)} pontos percentuais. Frequências NÃO calibradas.`));
  else notes.push(insight('Sem amostra probabilística validada',`Para ${day}, não há distribuição de ensemble válida neste painel. O resumo usa apenas a previsão determinística.`, 'warn'));
  if(op==='spray'){
   const first=rows[0],reasons=hourReason(first.a,op);
   notes.push(insight('Pulverização • primeira hora futura',`${first.time.replace('T',' ')}: ${catLabel(first.a.cls)}; ${reasons}. Inversão, bula, deriva e vento na altura de aplicação permanecem pendentes independentemente da cor.` ,first.a.cls==='restrita'?'danger':'warn'));
   if(missing)notes.push(insight('Completude meteorológica',`${missing} hora(s) sem todos os campos para triagem numérica. Dados faltantes não são considerados zero nem condições favoráveis.`,'warn'));
  } else {
   const rainMessage=rain24===null?'Chuva acumulada de 24 h sem série completa.':`Chuva determinística prevista nas próximas 24 h: ${fmt(rain24)} mm.`;
   const ag={seeding:'Planeje o plantio considerando umidade real do solo, textura, trafegabilidade e previsão de chuva. Não há sensor de solo validado.',harvest:'Avalie umidade do produto, acesso de máquinas e precipitação local. A previsão não comprova condição de colheita.',irrigation:'A chuva prevista não substitui balanço hídrico nem medição de umidade do solo; não automatize lâmina ou turno com este indicador.'};
   notes.push(insight(opLabel(op).replace(/^./,x=>x.toUpperCase())+' • análise preliminar',rainMessage+' '+ag[op],'warn'));
  }
  insBox.innerHTML=notes.join('');
  byId('agro-hours-table').querySelector('tbody').innerHTML=rows.map(r=>{
   const c=category(r.a,op),dir=r.a.direction===null?'':` de ${sector(r.a.direction)} → ${sector(r.a.direction+180)}`;
   const reasons=hourReason(r.a,op);
   return `<tr><td>${escape(r.time.slice(5).replace('T',' '))}</td><td><span class="agro-status ${c}">${escape(catLabel(c))}</span></td><td>${fmt(r.a.wind)} km/h${escape(dir)}</td><td>${fmt(r.a.gust)} km/h</td><td>${fmt(r.a.rh,0)}%</td><td>${fmt(r.a.vpd,2)} kPa</td><td>${fmt(r.a.rain,2)} mm</td><td>${escape(reasons)}</td></tr>`;
  }).join('');
  chartTimeline(rows,op);renderPlan();renderCounter++;
 }
 function localDateISO(timezone){const parts=new Intl.DateTimeFormat('en-US',{timeZone:timezone,year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date());
  const v=kind=>parts.find(p=>p.type===kind)?.value;return `${v('year')}-${v('month')}-${v('day')}`;
 }
 function recentRows(payload,expectedPoint,now=new Date()){
  if(!payload||!Array.isArray(payload?.daily?.time))throw Error('A API não retornou datas diárias');
  if(!finite(payload.latitude)||!finite(payload.longitude)||Math.abs(payload.latitude-expectedPoint.latitude)>1||Math.abs(payload.longitude-expectedPoint.longitude)>1)throw Error('Resposta pertence a outra grade');
  if(!payload.timezone)throw Error('Fuso da resposta ausente');
  const today=new Intl.DateTimeFormat('en-US',{timeZone:payload.timezone,year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(now);
  const v=kind=>today.find(p=>p.type===kind)?.value;
  const todayStr=`${v('year')}-${v('month')}-${v('day')}`;
  const d=payload.daily;
  return d.time.map((date,i)=>({date,rain:val(d.precipitation_sum,i),tmin:val(d.temperature_2m_min,i),tmax:val(d.temperature_2m_max,i),gust:val(d.wind_gusts_10m_max,i)}))
    .filter(r=>/^\d{4}-\d\d-\d\d$/.test(r.date)&&r.date<todayStr&&(r.rain!==null||r.tmin!==null||r.tmax!==null)).slice(-4).reverse();
 }
 async function loadRecent(force=false){
  if(recentBusy)return;
  const p=currentPoint(),key=pointKey(p),status=byId('agro-recent-status'),table=byId('agro-recent-table');if(!status||!table)return;
  const c=cache.get(key);if(!force&&c&&Date.now()-c.at<30*60000){drawRecent(c.rows,c.source,c.at,p);return;}
  recentBusy=true;const token=++recentToken;
  status.className='notice muted';status.textContent='Consultando retrospectiva do modelo nos últimos dias para '+(p.name||key)+'…';
  const ctrl=new AbortController();recentController=ctrl;const timer=setTimeout(()=>ctrl.abort(),27000);
  try{
   const params=new URLSearchParams({latitude:String(p.latitude),longitude:String(p.longitude),timezone:'auto',past_days:'4',forecast_days:'1',daily:'precipitation_sum,temperature_2m_min,temperature_2m_max,wind_gusts_10m_max'});
   const res=await fetch('https://api.open-meteo.com/v1/forecast?'+params,{signal:ctrl.signal,cache:'no-store'});
   if(!res.ok)throw Error('API HTTP '+res.status);
   const doc=await res.json();if(doc?.error)throw Error(doc.reason||'A API retornou erro');
   const rows=recentRows(doc,p);if(!rows.length)throw Error('Sem dias passados com valores válidos');
   if(token!==recentToken||pointKey(currentPoint())!==key)return;
   const data={at:Date.now(),rows,source:'Open-Meteo Forecast • past_days'};cache.set(key,data);drawRecent(rows,data.source,data.at,p);
  }catch(e){if(token!==recentToken)return;
   if(c){drawRecent(c.rows,c.source,c.at,p);status.className='notice warning';status.textContent+=' ⚠ Consulta nova falhou; valores anteriores no cache. '+String(e.message||'').slice(0,90);}
   else{status.className='notice warning';status.textContent='Retrospectiva de modelo indisponível: '+String(e.name==='AbortError'?'tempo-limite':e.message||e).slice(0,110)+'. Não significa tempo seco; consulte observações oficiais quando disponíveis.';table.querySelector('tbody').innerHTML='<tr><td colspan="6">Nenhum valor retrospectivo confirmado pela API.</td></tr>';}
  }finally{clearTimeout(timer);if(token===recentToken){recentBusy=false;recentController=null;}}
 }
 function drawRecent(rows,source,at,p){
  byId('agro-recent-status').className='notice muted';
  byId('agro-recent-status').textContent=`${p.name||pointKey(p)} • ${rows.length} datas passadas com valores de modelo • consulta ${new Date(at).toLocaleString('pt-BR')} • estimativa retrospectiva, NÃO observação de estação. Chuva ausente ≠ 0 mm.`;
  byId('agro-recent-table').querySelector('tbody').innerHTML=rows.map(r=>`<tr><td>${escape(r.date)}</td><td>${fmt(r.rain)}</td><td>${fmt(r.tmin)}</td><td>${fmt(r.tmax)}</td><td>${fmt(r.gust)}</td><td>${escape(source)} (não observado)</td></tr>`).join('');
 }
 function activate(){render();void loadRecent();}
 function bind(){
  if(!byId('agro'))return;
  byId('tabs')?.addEventListener('click',event=>{if(event.target.closest('button[data-tab="agro"]'))setTimeout(activate,60);});
  for(const id of ['agro-operation','agro-horizon','agro-product','agro-window-date','agro-window-duration'])byId(id)?.addEventListener('change',render);
  byId('agro-refresh')?.addEventListener('click',render);
  for(const id of ['agro-crop','agro-flight-height','agro-droplet','agro-sensitive','agro-label-checked','agro-field-wind','agro-inversion-checked'])byId(id)?.addEventListener('input',renderPlan);
  byId('agro-recent-refresh')?.addEventListener('click',()=>void loadRecent(true));
  window.addEventListener('campo:forecast-rendered',render);
  window.addEventListener('campo:location-changed',()=>{recentToken++;recentController?.abort();recentController=null;recentBusy=false;if(byId('agro')?.classList.contains('active')){
    const box=byId('agro-recent-status');box.textContent='Coordenada alterada: aguardando previsão do novo ponto.';
    byId('agro-kpis').innerHTML='';byId('agro-insights').innerHTML='';byId('agro-window-results').innerHTML='';
    byId('agro-window-status').textContent='Coordenada alterada. Aguardando dados do novo ponto.';byId('agro-window-observation').textContent='';
    byId('agro-recent-table').querySelector('tbody').innerHTML='<tr><td colspan="6">Carregando nova localização…</td></tr>';
    setTimeout(()=>{render();void loadRecent();},120);
  }});
  window.CampoAgro={open:activate,render,_test:{nextRain,assess,getHours,parseLocalHour,recentRows,ensembleInfo,category,windowRuns,freshness,ensembleFreshness}};
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();
