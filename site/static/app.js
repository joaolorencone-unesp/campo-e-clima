'use strict';
// Campo e Clima v0.3: plots deliberately use CATEGORY axes to avoid date parsing
// bugs (e.g. 26/10 rendered as 2011). Hidden plots render when their tab opens.
const DATA_URL = 'data/latest.json';
let state = null;
const chartSpecs = new Map();
const $ = id => document.getElementById(id);
const fmt = (n, d=1) => n == null || n === '' || !Number.isFinite(Number(n)) ? '—' : Number(n).toFixed(d).replace('.', ',');
const num = n => n == null || n === '' || !Number.isFinite(Number(n)) ? null : Number(n);
const esc = x => String(x ?? '—').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const val = (obj,key,i)=>obj?.[key]?.[i] ?? null;
const ddmm = iso => typeof iso==='string' && /^\d{4}-\d\d-\d\d/.test(iso) ? iso.slice(8,10)+'/'+iso.slice(5,7):iso;
const hh = iso => iso?.slice(11,13)+'h';
const dh = iso => ddmm(iso)+' '+hh(iso);
const activeTZ = () => state?.site?.timezone || 'America/Campo_Grande';
const activeOffset = () => Number.isFinite(state?.deterministic?.utc_offset_seconds) ? state.deterministic.utc_offset_seconds : -14400;
const offsetISO = (secs) => `${secs < 0?'-':'+'}${String(Math.floor(Math.abs(secs)/3600)).padStart(2,'0')}:${String(Math.floor(Math.abs(secs)%3600/60)).padStart(2,'0')}`;
const parseGridTime = t => new Date(t + offsetISO(activeOffset()));
const dateLocal = () => localISO(new Date());
function localISO(date){ // construct from explicit date components to avoid locale-dependent parsing
 const items = new Intl.DateTimeFormat('en-US',{timeZone:activeTZ(),year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(date);
 const find = t=>items.find(x=>x.type===t)?.value;
 return `${find('year')}-${find('month')}-${find('day')}`;
}
function hoursFrom(h,n=72){
 const now=Date.now(); if(!Array.isArray(h?.time)) return [];
 return h.time.map((t,i)=>({t,i,date:parseGridTime(t)}))
   .filter(x=>Number.isFinite(x.date.getTime()) && x.date.getTime()>=now-3600000).slice(0,n);
}
const percent=(p,d=0)=>p==null?'—':fmt(Number(p)*100,d)+'%';
const rainRow=(stamp)=>state?.rain_ensemble_hourly?.find(row=>row.time===stamp)||null;
const wval=(stamp,horizon,key)=>rainRow(stamp)?.windows?.[String(horizon)]?.[key]??null;
const directionName = degrees => { const d=num(degrees);return d===null?'—':['N','NE','E','SE','S','SO','O','NO'][Math.round((d%360)/45)%8]; };
const safe = (n,d=1) => num(n)===null?'na':'';
function clearPlot(id,message='Dado indisponível nesta coleta.'){
 const el=$(id);if(!el)return;
 chartSpecs.delete(id);
 if(window.Plotly && el.classList.contains('js-plotly-plot')){try{Plotly.purge(el);}catch(_){}}
 el.classList.add('is-empty');el.textContent=message;
}
function chart(id,traces,ytitle='',extra={}){
 const el=$(id);
 const hasValues=Array.isArray(traces) && traces.some(t=>{
  const arrays=[t?.y,t?.r, ...(Array.isArray(t?.z)?t.z:[])];
  return arrays.some(a=>Array.isArray(a) && a.some(v=>num(v)!==null));
 });
 if(!hasValues){clearPlot(id,'Sem dados numéricos válidos nesta edição.');return;}
 el?.classList.remove('is-empty');
 chartSpecs.set(id,{traces,ytitle,extra});drawChart(id);
}
function drawChart(id){
 const element=$(id),spec=chartSpecs.get(id);
 if(!element||!spec) return;
 if(!spec.traces?.length){clearPlot(id,'Não há amostra válida para este gráfico.');return;}
 // Plotly cannot calculate widths when a parent tab has display:none.
 if(!element.closest('.tab')?.classList.contains('active'))return;
 if(!window.Plotly){clearPlot(id,'Biblioteca gráfica indisponível. Consulte os valores nas tabelas.');return;}
 const layout={autosize:true,height:spec.extra.height||360,
   paper_bgcolor:'#fff',plot_bgcolor:'#fff',
   font:{family:'system-ui,Arial,sans-serif',size:12,color:'#456479'},
   margin:{t:24,r:55,l:62,b:78},
   legend:{orientation:'h',y:-0.27,x:0,font:{size:11}},
   hovermode:'x unified',
   xaxis:{type:'category',tickangle:0,nticks:9,showgrid:true,gridcolor:'#edf2f6',tickfont:{size:10},automargin:true},
   yaxis:{title:spec.ytitle,zeroline:false,showgrid:true,gridcolor:'#edf2f6',rangemode:'tozero',automargin:true},
   ...spec.extra};
 const conf={responsive:true,displayModeBar:false,scrollZoom:false};
 try{Plotly.react(element,spec.traces,layout,conf);}catch(err){element.textContent='Falha ao desenhar gráfico: '+String(err);}
}
function redrawActive(){for(const id of chartSpecs.keys()){const el=$(id);if(el?.closest('.tab')?.classList.contains('active'))drawChart(id);}}
function tableHead(titles){return '<thead><tr>'+titles.map(x=>`<th>${esc(x)}</th>`).join('')+'</tr></thead>';}
function tableFill(id,titles,rows,empty='Sem dados válidos para esta seção.'){$(id).innerHTML=tableHead(titles)+'<tbody>'+(rows.length?rows.join(''):`<tr><td colspan="${titles.length}" class="na">${esc(empty)}</td></tr>` )+'</tbody>';}
const cell=(x,cls='',d=1)=>`<td class="${cls}">${fmt(x,d)}</td>`;
function statusBar(){
 const issued=state?.issued_at_utc;
 const emission=issued?new Date(issued):null;
 const age=emission && Number.isFinite(emission.getTime())?Math.round((Date.now()-emission.getTime())/60000):null;
 const stale=age===null||age<0||age>90;
 const liveDate=state?._liveForecastAt?new Date(state._liveForecastAt):null;
 const liveFresh=liveDate && Number.isFinite(liveDate.getTime()) && Date.now()-liveDate.getTime()<90*60000;
 const issuedText=emission?emission.toLocaleString('pt-BR',{timeZone:activeTZ(),dateStyle:'short',timeStyle:'short'}):'não registrada';
 $('last-updated').textContent=`${state?.site?.custom?'Consulta do ponto':'Ensembles'}: ${issuedText} (horário local do ponto)`;
 const modelOK=Object.values(state?.ensemble_models||{}).filter(x=>x.state==='ok'&&x.precipitation_members>0).length;
 const gustOK=Object.values(state?.ensemble_models||{}).filter(x=>x.gust_members>0).length;
 const forecastText=liveFresh?`Previsão determinística consultada diretamente às ${liveDate.toLocaleTimeString('pt-BR',{timeZone:activeTZ(),hour:'2-digit',minute:'2-digit'})}. `:'';
 $('status').classList.toggle('warning',stale);
 if(state?.site?.custom){
  $('status').innerHTML= modelOK
    ? `✓ <strong>${modelOK} ensembles de chuva e ${gustOK} com rajadas consultados para o ponto selecionado.</strong> ${forecastText}Dados em grade, sem calibração local; fontes de Naviraí não são reutilizadas.`
    : `ℹ <strong>Previsão determinística carregada para o ponto selecionado.</strong> Probabilidades dos ensembles ainda não estão disponíveis. ${forecastText}Não confundir esta localidade com Naviraí.`;
 }else if(stale){$('status').innerHTML=`⚠ <strong>Ensembles sem coleta recente (${age==null?'horário desconhecido':age+' min'}).</strong> ${forecastText}Frequências de chuva e rajada estão desatualizadas; não utilizá-las para decisões atuais.`;}
 else{$('status').innerHTML=`✓ <strong>Ensembles publicados há ${age} min:</strong> ${modelOK} modelos com chuva; ${gustOK} com rajadas. ${forecastText}<strong>Frequências não calibradas.</strong> Observações oficiais têm atualização separada.`;}
 return {stale,age,modelOK,gustOK,issued};
}
function metric(label,value,unit,desc){return `<article class="metric"><span class="label">${esc(label)}</span><span class="number">${fmt(value)}<span class="unit"> ${esc(unit)}</span></span><span class="hint">${esc(desc)}</span></article>`;}
function dailyData(){return state?.deterministic?.daily||{};}
function renderOverview(idx){
 const d=state?.deterministic,h=d?.hourly||{},c=d?.current||{},daily=dailyData();
 const v=idx.slice(0,24).map(x=>val(h,'precipitation',x.i));
 const rain24=v.length===24&&v.every(x=>num(x)!==null)?v.reduce((s,x)=>s+Number(x),0):null;
 const todayLocal=localISO(new Date());
 const currentDate=idx[0]?.t?.slice(0,10)||todayLocal;
 const ens=state?.rain_ensemble_daily||[];
 const biggest=ens.filter(x=>x.date>=currentDate).slice(0,7).sort((a,b)=>b.mean_mm-a.mean_mm)[0];
 const strongest=(state?.gust_ensemble_daily||[]).filter(x=>x.date>=currentDate).sort((a,b)=>b.p_gt_40_kmh-a.p_gt_40_kmh)[0];
 const currentRain=num(c.precipitation);
 $('metrics').innerHTML=[
  metric('Temperatura prevista agora',c.temperature_2m,'°C','Open-Meteo Forecast'),
  metric('Umidade relativa',c.relative_humidity_2m,'%','Previsão de modelo'),
  metric('Vento médio',c.wind_speed_10m,'km/h',directionName(c.wind_direction_10m)+' (de onde sopra)'),
  metric('Chuva nas próximas 24h',rain24,'mm','Previsão determinística'),
  metric('Maior chuva média • 7 dias',biggest?.mean_mm,'mm',biggest?ddmm(biggest.date)+' • multimodelo':'Ensemble indisponível'),
  metric('Rajada forte >40 km/h',strongest?.p_gt_40_kmh!=null?strongest.p_gt_40_kmh*100:null,'% ',strongest?'Frequência em '+ddmm(strongest.date):'Sem ensemble')
 ].join('');
 const insights=[];
 if(biggest)insights.push({cls:'warn',title:`🌧 Maior volume previsto: ${ddmm(biggest.date)}`,desc:`Chuva média multimodelo ${fmt(biggest.mean_mm)} mm; P10–P90: ${fmt(biggest.p10_mm)}–${fmt(biggest.p90_mm)} mm; frequência >10 mm/dia: ${percent(biggest.p_gt_10_mm)}.`});
 if(strongest)insights.push({cls:'risk',title:`🌬 Atenção às rajadas: ${ddmm(strongest.date)}`,desc:`Frequência >30 km/h: ${percent(strongest.p_gt_30_kmh)}; >40 km/h: ${percent(strongest.p_gt_40_kmh)}. Apenas ${strongest.model_count} modelos com rajadas válidas.`});
 const nextSpray=idx.map(x=>({...sprayAssessment(h,x.i,'herb'),t:x.t})).filter(x=>x.cls==='bad').slice(0,1);
 if(nextSpray.length)insights.push({cls:'risk',title:`🚁 Pulverização: restrição às ${dh(nextSpray[0].t)}`,desc:nextSpray[0].reasons.join('; ')+'. Confirmar condições no talhão.'});
 insights.push({cls:'',title:'🔬 Grau de certeza',desc:'Os percentuais são frequências entre membros dos ensembles. Ainda não temos histórico observacional auditado para calibrar a previsão neste local.'});
 $('insights').innerHTML=insights.map(x=>`<div class="insight ${x.cls}"><strong>${esc(x.title)}</strong><div>${esc(x.desc)}</div></div>`).join('');
 if(idx.length){
  const x=idx.map(y=>dh(y.t));
  chart('temp-plot',[{x,y:idx.map(z=>val(h,'temperature_2m',z.i)),type:'scatter',mode:'lines',name:'Temperatura °C',line:{color:'#ee9566',width:3},hovertemplate:'%{y:.1f} °C<extra></extra>'},
     {x,y:idx.map(z=>val(h,'relative_humidity_2m',z.i)),type:'scatter',mode:'lines',name:'UR %',yaxis:'y2',line:{color:'#158bae',width:2.6},hovertemplate:'%{y:.0f}%<extra></extra>'}],'Temperatura °C',{
        yaxis2:{overlaying:'y',side:'right',title:'UR (%)',range:[0,100],showgrid:false}});
  chart('hour-rain-plot',[{x,y:idx.map(z=>val(h,'precipitation',z.i)),type:'bar',name:'Chuva mm/h',marker:{color:'#4a9acc'},hovertemplate:'%{y:.1f} mm/h<extra></extra>'}],'mm/h');
  const vpd=idx.map(z=>val(h,'vapour_pressure_deficit',z.i));
  if(vpd.some(z=>num(z)!==null))chart('vpd-plot',[{x,y:vpd,type:'scatter',mode:'lines',name:'VPD',fill:'tozeroy',fillcolor:'rgba(228,146,61,.1)',line:{color:'#d98b41',width:3},hovertemplate:'%{y:.2f} kPa<extra></extra>'}],'kPa');
  else clearPlot('vpd-plot','VPD não disponível nesta rodada.');
  const pressure=idx.map(z=>val(h,'pressure_msl',z.i));
  if(pressure.some(z=>num(z)!==null))chart('pressure-plot',[{x,y:pressure,type:'scatter',mode:'lines',name:'Pressão MSL',line:{color:'#6a6cb3',width:3},hovertemplate:'%{y:.1f} hPa<extra></extra>'}],'hPa',{
     yaxis:{title:'hPa',gridcolor:'#edf2f6',autorange:true}});
  else clearPlot('pressure-plot','Pressão ao nível do mar não disponível nesta rodada.');
 }else{['temp-plot','hour-rain-plot','vpd-plot','pressure-plot'].forEach(k=>clearPlot(k,'Sem previsão horária utilizável nesta edição.'));}
 const rainMap=new Map((state?.rain_ensemble_daily||[]).map(x=>[x.date,x]));
 const gustMap=new Map((state?.gust_ensemble_daily||[]).map(x=>[x.date,x]));
 const rows=(daily.time||[]).slice(0,7).map((date,i)=>{
  const r=rainMap.get(date),g=gustMap.get(date);
  return `<tr><td>${esc(ddmm(date))}</td>${cell(val(daily,'temperature_2m_min',i))}${cell(val(daily,'temperature_2m_max',i))}${cell(val(daily,'precipitation_sum',i))}${cell(r?.p50_mm)}${cell(r?.p90_mm)}<td>${percent(r?.p_gt_5_mm)}</td><td class="${g?.p_gt_30_kmh>=.5?'bad':''}">${percent(g?.p_gt_30_kmh)}</td></tr>`;
 });
 tableFill('summary-table',['Data','T mín °C','T máx °C','Chuva det. mm','Chuva P50 mm','P90 mm','Freq. >5 mm','Freq. rajada >30'],rows);
 const currentISO=localISO(new Date());
 const tomorrowISO=new Date(Date.parse(currentISO+'T12:00:00Z')+86400000).toISOString().slice(0,10);
 const hourRows=(targetDate,isToday)=>{
  if(!Array.isArray(h.time))return [];
  return h.time.map((t,i)=>({t,i})).filter(x=>x.t.startsWith(targetDate) && (!isToday || parseGridTime(x.t).getTime()>=Date.now()-3600000))
    .map(({t,i})=>{const rh=val(h,'relative_humidity_2m',i),wind=val(h,'wind_speed_10m',i),gust=val(h,'wind_gusts_10m',i);
      return `<tr><td>${hh(t)}</td>${cell(val(h,'temperature_2m',i))}${cell(rh,rh!==null&&rh<55?'bad':'',0)}${cell(val(h,'precipitation',i))}<td>${percent(wval(t,1,'p_gt_0_1_mm'))}</td><td>${percent(wval(t,1,'p_gt_1_mm'))}</td>${cell(wind,wind!=null&&(wind>10||wind<3)?'bad':'')}${cell(gust,gust!=null&&gust>30?'bad':'')}<td>${esc(directionName(val(h,'wind_direction_10m',i)))}</td></tr>`;
   });
 };
 const titles=['Hora local','T °C','UR %','Chuva mm/h','Freq. >0,1 mm','Freq. >1 mm','Vento km/h','Rajada km/h','Vento de'];
 tableFill('today-table',titles,hourRows(currentISO,true),'Hoje não há mais horas futuras ou não foram encontrados dados.');
 tableFill('tomorrow-table',titles,hourRows(tomorrowISO,false),'Amanhã: previsão horária indisponível.');
}
function renderRain(idx){
 const rain=state?.rain_ensemble_daily||[];
 const x=rain.map(z=>ddmm(z.date));
 if(rain.length){
   chart('rain-plot',[
     {x,y:rain.map(z=>z.p10_mm),type:'scatter',mode:'lines',name:'P10 • cenário seco',line:{color:'#aecfe3',width:1},hovertemplate:'P10 %{y:.1f} mm<extra></extra>'},
     {x,y:rain.map(z=>z.p90_mm),type:'scatter',mode:'lines',name:'P90 • cenário úmido',line:{color:'#7fb8de',width:1},fill:'tonexty',fillcolor:'rgba(48,145,209,.17)',hovertemplate:'P90 %{y:.1f} mm<extra></extra>'},
     {x,y:rain.map(z=>z.p50_mm),type:'scatter',mode:'lines+markers',name:'Mediana P50',line:{color:'#176eaa',width:3},marker:{size:8},hovertemplate:'P50 %{y:.1f} mm<extra></extra>'},
     {x,y:rain.map(z=>z.mean_mm),type:'scatter',mode:'lines+markers',name:'Média',line:{color:'#e49a45',width:2,dash:'dot'},hovertemplate:'Média %{y:.1f} mm<extra></extra>'}
   ],'Chuva (mm/dia)');
   const thresholds=[[1,'#66bbcc'],[5,'#448dc6'],[10,'#e4a354'],[20,'#ba526b']];
   chart('rain-risk-plot',thresholds.map(([n,c])=>({x,y:rain.map(z=>z['p_gt_'+n+'_mm']*100),type:'scatter',mode:'lines+markers',name:'>'+n+' mm/dia',line:{color:c,width:2.5},marker:{size:7},hovertemplate:'%{y:.0f}%<extra></extra>'})),'Frequência (%)',{yaxis:{range:[0,100],title:'Frequência (%)',gridcolor:'#edf2f6'}});
 }else{['rain-plot','rain-risk-plot'].forEach(id=>$(id).textContent='Sem distribuição validada de chuva nesta coleta.');}
 const titles=['Dia','Modelos','Membros','Média mm','P10','P50','P90','>1 mm','>5 mm','>10 mm','>20 mm'];
 tableFill('rain-table',titles,rain.map(z=>`<tr><td>${esc(ddmm(z.date))}</td><td>${z.model_count}</td><td>${z.member_count}</td>${cell(z.mean_mm)}${cell(z.p10_mm)}${cell(z.p50_mm)}${cell(z.p90_mm)}<td>${percent(z.p_gt_1_mm)}</td><td>${percent(z.p_gt_5_mm)}</td><td>${percent(z.p_gt_10_mm)}</td><td>${percent(z.p_gt_20_mm)}</td></tr>`));
 const hr=state?.rain_ensemble_hourly||[];
 const forward=hr.filter(z=>parseGridTime(z.time).getTime()>=Date.now()-3600000).slice(0,72);
 if(forward.length){const rx=forward.map(z=>dh(z.time));
   chart('rain-hour-prob',[
     {x:rx,y:forward.map(z=>z.windows?.['1']?.mean_mm??null),type:'bar',name:'Média mm/h',marker:{color:'#76b7df'},hovertemplate:'%{y:.2f} mm/h<extra></extra>'},
     {x:rx,y:forward.map(z=>num(z.windows?.['1']?.p_gt_1_mm)!=null?z.windows['1'].p_gt_1_mm*100:null),type:'scatter',mode:'lines',name:'Freq. >1 mm/h',yaxis:'y2',line:{color:'#c85f51',width:2.4},hovertemplate:'%{y:.0f}%<extra></extra>'}
   ],'Chuva (mm/h)',{yaxis2:{title:'Frequência (%)',overlaying:'y',side:'right',range:[0,100],showgrid:false}});
 }else{$('rain-hour-prob').textContent='Sem membros horários válidos; os acumulados diários ainda podem estar disponíveis.';}
 const windows=[];
 // Show timestamps at 3-hour intervals to avoid double-counting overlapping windows in a table.
 for(const o of forward){if(Number(o.time.slice(11,13))%3!==0)continue;
  const a=o.windows?.['3'],b=o.windows?.['6'];if(!a&&!b)continue;
  windows.push(`<tr><td>${esc(dh(o.time))}</td>${cell(a?.mean_mm)}<td>${percent(a?.p_gt_1_mm)}</td><td>${percent(a?.p_gt_5_mm)}</td><td>${percent(a?.p_gt_10_mm)}</td>${cell(b?.mean_mm)}<td>${percent(b?.p_gt_5_mm)}</td><td>${percent(b?.p_gt_10_mm)}</td><td class="na">${a?.models??b?.models??'—'}</td></tr>`);
 }
 tableFill('rain-window-table',['Início local','Média 3h mm','Freq. 3h >1','Freq. 3h >5','Freq. 3h >10','Média 6h mm','Freq. 6h >5','Freq. 6h >10','Modelos'],windows,'Agregação horária conjunta ainda não disponível para esta coleta.');
 const mrows=state?.rain_models_daily||[];
 if(mrows.length){const names=[...new Set(mrows.map(z=>z.model))],dates=[...new Set(mrows.map(z=>z.date))].sort();const map=new Map(mrows.map(z=>[z.model+'|'+z.date,z.mean_mm]));
   chart('rain-models-plot',[{type:'heatmap',x:dates.map(ddmm),y:names,z:names.map(name=>dates.map(date=>map.get(name+'|'+date)??null)),colorscale:[[0,'#f1f8fc'],[.2,'#aed9ef'],[.5,'#4b98ca'],[1,'#115b8f']],colorbar:{title:'mm/dia',len:.84},hovertemplate:'%{y}<br>%{x}<br>Média %{z:.1f} mm<extra></extra>'}],'',{
      height:Math.max(390,names.length*34+120),margin:{l:155,r:50,t:30,b:78},hovermode:'closest',yaxis:{autorange:'reversed',showgrid:false,automargin:true}});
 }else{$('rain-models-plot').textContent='Sem dados individuais por modelo nesta versão da coleta. A atualização do coletor permitirá esta comparação.';}
 const d=dailyData();tableFill('daily-table',['Data','T mín °C','T máx °C','Chuva mm','Chance máx. %*','Rajada máx km/h'],(d.time||[]).map((date,i)=>`<tr><td>${esc(ddmm(date))}</td>${cell(val(d,'temperature_2m_min',i))}${cell(val(d,'temperature_2m_max',i))}${cell(val(d,'precipitation_sum',i))}${cell(val(d,'precipitation_probability_max',i),'',0)}${cell(val(d,'wind_gusts_10m_max',i))}</tr>`));
}
function renderWind(idx){
 const h=state?.deterministic?.hourly||{};
 if(idx.length){let x=idx.map(z=>dh(z.t));
  chart('wind-plot',[{x,y:idx.map(z=>val(h,'wind_speed_10m',z.i)),type:'scatter',mode:'lines',name:'Vento médio',line:{color:'#21937f',width:3},hovertemplate:'%{y:.1f} km/h<extra></extra>'},
    {x,y:idx.map(z=>val(h,'wind_gusts_10m',z.i)),type:'scatter',mode:'lines',name:'Rajada',line:{color:'#dc7e47',width:3},hovertemplate:'%{y:.1f} km/h<extra></extra>'},
    {x,y:idx.map(()=>30),type:'scatter',mode:'lines',name:'Referência 30 km/h',line:{color:'#b44855',dash:'dash',width:1},hoverinfo:'skip'}],'km/h');
  const labels=['N','NE','E','SE','S','SO','O','NO'];const sector=Array(8).fill(0),sum=Array(8).fill(0);
  for(const row of idx){const d=num(val(h,'wind_direction_10m',row.i)),v=num(val(h,'wind_speed_10m',row.i));if(d!==null&&v!==null){const bucket=Math.round((((d%360)+360)%360)/45)%8;sector[bucket]++;sum[bucket]+=v;}}
  if(sector.some(Boolean)){chart('wind-rose',[{type:'barpolar',r:sector,theta:labels.map((_,i)=>i*45),width:Array(8).fill(41),name:'Horas previstas',marker:{color:sum.map((s,i)=>sector[i]?s/sector[i]:0),colorscale:'Blues',showscale:true,colorbar:{title:'Vento médio<br>km/h'}},customdata:labels,hovertemplate:'Direção %{customdata}: %{r} hora(s)<extra></extra>'}],'',{
     polar:{bgcolor:'#fff',angularaxis:{direction:'clockwise',rotation:90,tickmode:'array',tickvals:labels.map((_,i)=>i*45),ticktext:labels},radialaxis:{visible:true,gridcolor:'#e5eef4'}},height:370,margin:{l:24,r:70,t:16,b:16},hovermode:'closest'});
  }else{$('wind-rose').textContent='Sem direção ou velocidade válida.';}
 }else{['wind-plot','wind-rose'].forEach(id=>$(id).textContent='Previsão de vento indisponível.');}
 const gusts=state?.gust_ensemble_daily||[];
 if(gusts.length){let x=gusts.map(x=>ddmm(x.date));chart('gust-plot',[
  {x,y:gusts.map(z=>z.p_gt_30_kmh*100),type:'bar',name:'>30 km/h',marker:{color:'#edb75e'},hovertemplate:'%{y:.0f}%<extra></extra>'},
  {x,y:gusts.map(z=>z.p_gt_40_kmh*100),type:'bar',name:'>40 km/h',marker:{color:'#df7966'},hovertemplate:'%{y:.0f}%<extra></extra>'},
  {x,y:gusts.map(z=>z.p_gt_60_kmh*100),type:'bar',name:'>60 km/h',marker:{color:'#bf4558'},hovertemplate:'%{y:.0f}%<extra></extra>'}
 ],'Frequência (%)',{barmode:'group',yaxis:{title:'Frequência (%)',range:[0,100],gridcolor:'#edf2f6'}});
 }else{$('gust-plot').textContent='Sem modelos com máximos diários de rajada válidos.';}
 tableFill('gust-table',['Data','Modelos','Membros','Mediana km/h','P90 km/h','Freq. >30','Freq. >40','Freq. >60'],gusts.map(z=>`<tr><td>${ddmm(z.date)}</td><td>${z.model_count}</td><td>${z.member_count}</td>${cell(z.p50_kmh)}${cell(z.p90_kmh)}<td>${percent(z.p_gt_30_kmh)}</td><td>${percent(z.p_gt_40_kmh)}</td><td>${percent(z.p_gt_60_kmh)}</td></tr>`));
 tableFill('wind-table',['Hora local','De onde sopra','Direção °','Médio km/h','Rajada km/h'],idx.map(z=>{let sp=val(h,'wind_speed_10m',z.i),gst=val(h,'wind_gusts_10m',z.i),dir=val(h,'wind_direction_10m',z.i);return `<tr><td>${dh(z.t)}</td><td>${esc(directionName(dir))}</td>${cell(dir,'',0)}${cell(sp,sp!==null&&(sp>10||sp<3)?'warn':'')}${cell(gst,gst>30?'bad':gst>25?'warn':'')}</tr>`;}));
}
function sprayAssessment(h,i,kind){
 const get=k=>val(h,k,i),t=get('temperature_2m'),rh=get('relative_humidity_2m'),wind=get('wind_speed_10m'),gust=get('wind_gusts_10m'),vpd=get('vapour_pressure_deficit'),pr=get('precipitation'),dir=get('wind_direction_10m');
 if([t,rh,wind,gust,vpd,pr,dir].some(x=>num(x)===null))return {cls:'na',label:'Indeterminado',reasons:['Variável essencial ausente']};
 const reasons=[];
 if(t>=30)reasons.push('T ≥30°C');if(rh<55)reasons.push('UR <55%');
 if(wind<3)reasons.push('Vento <3 km/h; investigar inversão');
 if(wind>10)reasons.push('Vento >10 km/h');
 if(gust>25)reasons.push('Rajada >25 km/h');
 if(pr>0.1)reasons.push('Chuva no horário');
 const vpdLimit=kind==='herb'?1.2:kind==='insect'?1.4:1.5;
 if(vpd>vpdLimit)reasons.push(`VPD >${vpdLimit.toFixed(1).replace('.',',')} kPa (triagem)`);
 const future=(h.precipitation||[]).slice(i+1,i+4);
 if(future.length===3&&future.every(x=>num(x)!==null)&&future.some(x=>x>0.1))reasons.push('Chuva nas próximas 3h');
 if(reasons.length)return {cls:'bad',label:'Restrição meteorológica',reasons};
 const localHour=Number((h.time||[])[i]?.slice(11,13));
 if(localHour<7||localHour>=18)return {cls:'na',label:'Indeterminado · inversão',reasons:['Período noturno: inversão e estabilidade não verificadas']};
 if(future.length!==3||future.some(x=>num(x)===null))return {cls:'na',label:'Indeterminado',reasons:['Chuva futura incompleta']};
 return {cls:'warn',label:'Candidata / validar campo',reasons:['Inversão, bula e deriva não verificadas']};
}
function renderSpray(idx){
 const h=state?.deterministic?.hourly||{},kind=$('product').value;
 const all=idx.map(z=>({...z,...sprayAssessment(h,z.i,kind)}));
 const windows=[];let run=[];
 function flush(){if(run.length>=2){const a=run[0],b=run[run.length-1];windows.push({start:a.t,end:b.t,n:run.length,gust:Math.max(...run.map(x=>val(h,'wind_gusts_10m',x.i)??Infinity)),rh:Math.min(...run.map(x=>val(h,'relative_humidity_2m',x.i)??0))});}run=[];}
 for(const z of all){if(z.cls==='warn')run.push(z);else flush();}flush();
 windows.sort((a,b)=>b.n-a.n||a.gust-b.gust||a.start.localeCompare(b.start));
 $('spray-windows').innerHTML=windows.length?windows.slice(0,3).map((w,i)=>`<div class="window"><strong>${i+1}º: ${dh(w.start)} — ${hh(w.end)}</strong><span>${w.n} horas candidatas consecutivas</span><small>UR mínima ${fmt(w.rh,0)}%; rajada máxima ${fmt(w.gust)} km/h. <b>Exige verificação local.</b></small></div>`).join(''):
 '<div class="notice muted">Nenhuma janela consecutiva ≥2 horas passou pelos filtros meteorológicos disponíveis. Isso não prova que todas as demais horas sejam impraticáveis: faltam medições no talhão.</div>';
 tableFill('spray-table',['Hora local','T °C','UR %','VPD kPa','Vento km/h','Rajada km/h','De onde sopra','Chuva mm/h','Triagem','Principal restrição'],all.map(z=>{
  const t=val(h,'temperature_2m',z.i),rh=val(h,'relative_humidity_2m',z.i),vpd=val(h,'vapour_pressure_deficit',z.i),wind=val(h,'wind_speed_10m',z.i),gust=val(h,'wind_gusts_10m',z.i),pr=val(h,'precipitation',z.i);
  const limit=kind==='herb'?1.2:kind==='insect'?1.4:1.5;
  return `<tr><td>${esc(dh(z.t))}</td>${cell(t,t>=30?'bad':'')}${cell(rh,rh!==null&&rh<55?'bad':'',0)}${cell(vpd,vpd!=null&&vpd>limit?'bad':'',2)}${cell(wind,wind!=null&&(wind>10||wind<3)?'bad':'')}${cell(gust,gust!=null&&gust>25?'bad':'')}<td>${esc(directionName(val(h,'wind_direction_10m',z.i)))}</td>${cell(pr,pr!=null&&pr>0.1?'bad':'')}<td class="${z.cls}">${esc(z.label)}</td><td title="${esc(z.reasons.join('; '))}">${esc(z.reasons.join('; '))}</td></tr>`;
 }),'Previsão de pulverização indisponível.');
}

// v0.4 — ensemble scenarios are JOINT within the SAME member, not a product
// of separate probabilities; all percentages are uncalibrated frequencies.
const SPRAY_REASONS = {'vento':'Vento fora de 3–10 km/h','rajadas':'Rajadas >25 km/h',
  'umidade':'UR <55%','temperatura':'T ≥30°C','vpd':'VPD acima da triagem',
  'chuva_3h':'Chuva nas próximas 3h','inversao_nao_verificada':'Noite: inversão não verificada'};
const SCREEN_KIND = {herb:'Herbicidas',fung:'Fungicidas',insect:'Inseticidas'};
const SPRAY_COLORS={passa:'#1e9c74',marginal:'#e8a842',restrito:'#d45b60',indeterminado:'#8998ad'};
function renderSprayWeather(activeDay){
 const h=state?.deterministic?.hourly||{},idx=hoursFrom(h,72).filter(z=>activeDay==='all'||z.t.slice(0,10)===activeDay);
 if(!idx.length){clearPlot('spray-hourly-wind','Previsão determinística indisponível para esse dia.');clearPlot('spray-hourly-atmos','Sem dados de UR/VPD.');return;}
 const x=idx.map(z=>dh(z.t));
 const options={xaxis:{type:'category',tickangle:-35,nticks:12,gridcolor:'#edf2f6'}};
 chart('spray-hourly-wind',[
 {x,y:idx.map(z=>val(h,'wind_speed_10m',z.i)),type:'scatter',mode:'lines+markers',name:'Vento médio 10m',line:{color:'#147ca1',width:2.6},hovertemplate:'%{y:.1f} km/h<extra></extra>'},
 {x,y:idx.map(z=>val(h,'wind_gusts_10m',z.i)),type:'scatter',mode:'lines+markers',name:'Rajada 10m',line:{color:'#db8651',width:2.6},hovertemplate:'%{y:.1f} km/h<extra></extra>'},
 {x,y:idx.map(()=>10),type:'scatter',mode:'lines',name:'Limite superior de triagem (10 km/h)',line:{color:'#c4445a',dash:'dot',width:1.5},hoverinfo:'skip'}
 ],'km/h',{...options});
 chart('spray-hourly-atmos',[
 {x,y:idx.map(z=>val(h,'relative_humidity_2m',z.i)),type:'scatter',mode:'lines+markers',name:'UR',line:{color:'#148dba',width:2.5},hovertemplate:'UR %{y:.0f}%<extra></extra>'},
 {x,y:idx.map(z=>val(h,'vapour_pressure_deficit',z.i)),type:'scatter',mode:'lines+markers',name:'VPD',yaxis:'y2',line:{color:'#dc8e4e',width:2.5},hovertemplate:'VPD %{y:.2f} kPa<extra></extra>'}
 ],'UR (%)',{...options,yaxis:{title:'Umidade relativa (%)',range:[0,100]},yaxis2:{title:'VPD (kPa)',overlaying:'y',side:'right',rangemode:'tozero',showgrid:false}});
}
function ensembleScreening(){
 const kind=$('product').value;
 const live=state?.spray_joint_hourly||[];
 const now=Date.now()-3600000;
 const all=live.filter(r=>Number.isFinite(parseGridTime(r.time).getTime()) && parseGridTime(r.time).getTime()>=now);
 const valid=all.filter(r=>r[kind]?.models>0).slice(0,72);
 const periodSelect=$('spray-period');
 if(periodSelect){
  const prev=periodSelect.value;const days=[...new Set(valid.map(r=>r.time.slice(0,10)))];
  const options=['<option value="all">72 horas completas (1h)</option>',...days.map(d=>`<option value="${d}">${d.slice(8,10)}/${d.slice(5,7)} — hora a hora</option>`)].join('');
  if(periodSelect.innerHTML!==options)periodSelect.innerHTML=options;
  periodSelect.value=prev&&([...days,'all'].includes(prev))?prev:(days[0]||'all');
 }
 const activeDay=periodSelect?.value||'all';
 const focused=valid.filter(r=>activeDay==='all'||r.time.startsWith(activeDay));
 renderSprayWeather(activeDay);
 const modelStatuses=Object.values(state?.spray_joint_model_status||{});
 const modelsOK=modelStatuses.filter(x=>x.status==='ok');
 const pstatus=$('spray-ensemble-status');
 if(!valid.length){
  pstatus.className='notice warning';
  pstatus.innerHTML='<b>Não há amostra conjunta completa dos ensembles para pulverização.</b> São necessárias as mesmas variáveis e o mesmo identificador de membro. A previsão determinística abaixo continua disponível apenas como referência; <b>não estima probabilidade de cenário.</b>';
  for(const id of ['spray-prob-plot','spray-causes-plot','spray-2h-plot']) {clearPlot(id,'Sem amostra conjunta verificada; não foi atribuída probabilidade.');}
  $('spray-scenario-cards').innerHTML='';$('spray-best2h').innerHTML='';
  tableFill('spray-ensemble-table',['Hora','Modelos','Membros','Passa','Marginal','Restrita','Indeterminada'],[],'Nenhum membro com todos os campos necessários nesta coleta.');
  return;
 }
 pstatus.className='notice muted';
 const allModels=[...new Set(valid.map(z=>z[kind].models))];
 const allMembers=[...new Set(valid.map(z=>z[kind].members))];
 pstatus.innerHTML=`<strong>FREQUÊNCIA DE CENÁRIOS, NÃO PROBABILIDADE CALIBRADA.</strong> <strong>${modelsOK.length} de 8 modelos</strong> forneceram pelo menos uma hora com membros completos. Amostra conjunta por hora: <strong>${allModels.join('–')} modelos</strong> e <strong>${allMembers.join('–')} membros</strong>. VPD calculado por temperatura e UR do mesmo membro (equação FAO). <strong>Amostra válida não significa aplicação liberada.</strong>`;
 const cards=focused.slice(0,1).map(r=>r[kind]);
 const first=cards[0];
 if(!first){clearPlot('spray-prob-plot','Sem horários válidos neste dia.');clearPlot('spray-causes-plot','Sem horários válidos neste dia.');clearPlot('spray-2h-plot','Sem horários válidos neste dia.');$('spray-scenario-cards').innerHTML='';$('spray-best2h').innerHTML='';return;}
 $('spray-scenario-cards').innerHTML=[['Passa filtros (NÃO é liberação)',first.passa,'#1e9c74'],['Marginal',first.marginal,'#d28b22'],['Restrita',first.restrito,'#c24f54'],['Indeterminada (noite/inversão)',first.indeterminado??0,'#8998ad']].map(([label,p,color])=>`<div class="screen-metric"><small>${esc(label)} • ${esc(dh(valid[0].time))}</small><strong style="color:${color}">${percent(p)}</strong><span>Frequência entre ${first.members} membros completos</span></div>`).join('');
 // EVERY valid hour displayed: filter by date if the user wants readable 24h.
 const sample=focused, x=sample.map(r=>dh(r.time));
 chart('spray-prob-plot',['passa','marginal','restrito','indeterminado'].map(cls=>({
  type:'bar',x,y:sample.map(r=>(r[kind]?.[cls]??0)*100),name:cls==='passa'?'Passa filtro':cls==='marginal'?'Marginal':cls==='restrito'?'Restrita':'Indeterminada',
  marker:{color:SPRAY_COLORS[cls]},hovertemplate:'%{y:.1f}% dos membros<extra></extra>'
 })),'Frequência conjunta (%)',{barmode:'stack',yaxis:{title:'Frequência (%)',range:[0,100],gridcolor:'#edf2f6'}});
 const keyColors={'vento':'#0a85ae','rajadas':'#d3872b','umidade':'#b75267','vpd':'#9a67b8','chuva_3h':'#4e8e63','temperatura':'#dd735d'};
 chart('spray-causes-plot',Object.keys(keyColors).map(reason=>({type:'scatter',mode:'lines+markers',
  x,y:sample.map(r=>(r[kind]?.reasons?.[reason]??0)*100),name:SPRAY_REASONS[reason],
  line:{color:keyColors[reason],width:2.5},marker:{size:5},hovertemplate:'%{y:.1f}% dos membros<extra></extra>'
 })),'Frequência por motivo (%)',{yaxis:{title:'Frequência (%)',range:[0,100],gridcolor:'#edf2f6'}});
 const windows=(state?.spray_joint_windows_2h||[]).filter(r=>parseGridTime(r.start).getTime()>=now && r[kind]?.models>0).slice(0,72);
 const sampledWindows=windows.filter(r=>activeDay==='all'||r.start.startsWith(activeDay));
 if(sampledWindows.length){chart('spray-2h-plot',[
  {type:'bar',x:sampledWindows.map(r=>dh(r.start)),y:sampledWindows.map(r=>r[kind].passa*100),name:'Ambas as horas passam',marker:{color:SPRAY_COLORS.passa}},
  {type:'bar',x:sampledWindows.map(r=>dh(r.start)),y:sampledWindows.map(r=>r[kind].marginal*100),name:'Pelo menos uma hora marginal',marker:{color:SPRAY_COLORS.marginal}},
  {type:'bar',x:sampledWindows.map(r=>dh(r.start)),y:sampledWindows.map(r=>r[kind].restrito*100),name:'Pelo menos uma hora restrita',marker:{color:SPRAY_COLORS.restrito}},
  {type:'bar',x:sampledWindows.map(r=>dh(r.start)),y:sampledWindows.map(r=>(r[kind].indeterminado??0)*100),name:'Indeterminada: inversão noturna',marker:{color:SPRAY_COLORS.indeterminado}}
 ],'Frequência nas 2h (%)',{barmode:'stack',yaxis:{title:'Frequência (%)',range:[0,100],gridcolor:'#edf2f6'}});
 }else {clearPlot('spray-2h-plot','Sem duas horas consecutivas com membros completos.');}
 const top=windows.filter(r=>r[kind].passa>0 && Number(r.start.slice(11,13))>=7 && Number(r.end.slice(11,13))<18).sort((a,b)=>b[kind].passa-a[kind].passa || b[kind].models-a[kind].models || a.start.localeCompare(b.start)).slice(0,3);
 $('spray-best2h').innerHTML=top.length?top.map((r,i)=>`<div class="window"><strong>${i+1}ª • ${esc(dh(r.start))}–${esc(hh(r.end))}</strong><b class="ok">${percent(r[kind].passa)} passam os filtros nas 2h</b><small>Marginal ${percent(r[kind].marginal)}, restrita ${percent(r[kind].restrito)}; ${r[kind].models} modelos, ${r[kind].members} membros. <strong>Exige verificação local.</strong></small></div>`).join(''):'<div class="notice muted">Nenhuma janela de 2 horas teve membros passando conjuntamente os filtros meteorológicos. A falta de dados não pode ser convertida em favorabilidade.</div>';
 const rows=focused.map(r=>{const o=r[kind];const major=Object.entries(o.reasons||{}).sort((a,b)=>b[1]-a[1]).slice(0,2).map(([k,p])=>SPRAY_REASONS[k]+' ('+percent(p)+')').join('; ');
  return `<tr><td>${esc(dh(r.time))}</td><td>${o.models}</td><td>${o.members}</td><td class="ok">${percent(o.passa)}</td><td class="warn">${percent(o.marginal)}</td><td class="bad">${percent(o.restrito)}</td><td class="na">${percent(o.indeterminado??0)}</td><td>${esc(major||'Sem restrições meteorológicas nos membros classificados; outras condições não verificadas')}</td></tr>`;
 });
 tableFill('spray-ensemble-table',['Hora','Modelos','Membros','Passa filtros','Marginal','Restrita','Indeterminada','Motivos mais frequentes'],rows);
}

function renderMachines(){const daily=dailyData();const items=(daily.time||[]).slice(0,14);if(!items.length){clearPlot('machine-rain','Dados diários indisponíveis para planejamento.');return;}
 chart('machine-rain',[{type:'bar',x:items.map(ddmm),y:items.map((_,i)=>val(daily,'precipitation_sum',i)),name:'Chuva prevista',marker:{color:'#76b7d7'},hovertemplate:'%{y:.1f} mm<extra></extra>'}],'mm/dia');
}
function renderVerification(){const model=state?.ensemble_models||{};const items=Object.entries(model).sort((a,b)=>a[0].localeCompare(b[0]));
 tableFill('model-inventory',['Modelo','Chuva: membros','Rajadas: membros','Latitude grade','Longitude grade','Disponibilidade'],items.map(([name,item])=>`<tr><td>${esc(name)}</td><td>${item.precipitation_members??'—'}</td><td>${item.gust_members??'—'}</td>${cell(item.grid_lat,'',3)}${cell(item.grid_lon,'',3)}<td class="${item.state==='ok'?'ok':'warn'}">${esc(item.state==='ok'?'Chuva válida':item.state==='error'?'Falha na fonte':'Sem chuva diária completa')}</td></tr>`));
}

function renderOfficial(){
 const official=state?.official||{}, alerts=official.inmet_alerts||{}, catalog=official.inmet_stations||{};
 const strip=$('official-alert-strip'), box=$('inmet-alerts');
 const checked=alerts.queried_at_utc?new Date(alerts.queried_at_utc).toLocaleString('pt-BR',{timeZone:activeTZ(),dateStyle:'short',timeStyle:'short'}):'horário indisponível';
 if(alerts.state!=='ok'){
  const msg='⚠ Avisos oficiais INMET: consulta indisponível. Não interprete como ausência de alerta.';
  strip.className='notice warning';strip.textContent=msg;
  box.innerHTML=`<div class="notice warning">${esc(msg)} <a href="https://alertas2.inmet.gov.br/" target="_blank" rel="noopener">Consultar avisos INMET ↗</a></div>`;
 } else {
  const list=alerts.municipal_alerts||[];
  if(list.length){
   strip.className='notice warning';strip.textContent=`⚠ ${list.length} aviso(s) INMET retornado(s) com Naviraí (IBGE 5005707) na abrangência municipal. Conferir validade. Consulta: ${checked} (Naviraí).`;
   box.innerHTML=list.map(a=>`<article class="official-alert-card"><strong>${esc(a.type)} • ${esc(a.severity)}</strong><p>Fonte: ${esc(a.start_date_source)} ${esc(a.start_hour_source||'hora não informada')} até ${esc(a.end_date_source)} ${esc(a.end_hour_source||'hora não informada')} • fuso não confirmado</p><small>Município confirmado pelo código IBGE 5005707. ${esc((a.risks||[]).join(' · ').slice(0,420))}</small></article>`).join('');
  }else{
   strip.className='notice';strip.textContent='INMET consultado: nenhum aviso da resposta recebida incluiu explicitamente Naviraí (IBGE 5005707). Isso não descarta outros riscos. Consulta: '+checked+' (Naviraí).';
   box.innerHTML='<div class="notice">Nenhum aviso com Naviraí identificado na consulta; verifique novamente a fonte oficial em caso de instabilidade.</div>';
  }
 }
 const stations=((catalog.state==='ok'?catalog.nearest:[])||[]).slice(0,8);
 tableFill('inmet-stations-table',['Estação','Código','Distância km','Situação','Altitude m'],
  stations.map(x=>`<tr><td>${esc(x.name)}</td><td>${esc(x.station_code)}</td><td>${fmt(x.distance_km)}</td><td>${esc(x.status)}</td><td>${esc(x.altitude_m)}</td></tr>`));
 if(!stations.length) $('inmet-stations-table').innerHTML='<tr><td>Catálogo INMET indisponível nesta consulta. Sem dados de estação não significa tempo estável.</td></tr>';
 const obsHourly=official.inmet_hourly_nearby||{};
 const hourlyStatus=$('inmet-hourly-status');
 if(hourlyStatus){
  if(obsHourly.state==='ok' && (obsHourly.records||[]).length){
   const records=obsHourly.records.slice(-24).reverse();
   hourlyStatus.className='notice';
   hourlyStatus.textContent=`OBSERVADO • INMET/rede parceira: ${obsHourly.station_name} (${obsHourly.station_code}), ${fmt(obsHourly.distance_km,0)} km da sede, entidade ${obsHourly.entity||'não informada'}. São leituras reais reportadas pela estação, não previsão e não representam o talhão. Última leitura: ${records[0].valid_at_local}.`;
   tableFill('inmet-hourly-table',['Hora local (UTC−4)','T °C','UR %','Chuva última hora mm','Vento médio km/h','Rajada km/h','Vento de onde (°)'],records.map(r=>`<tr><td>${esc(r.valid_at_local.slice(0,16).replace('T',' '))}</td>${cell(r.temperature_c)}${cell(r.rh_pct,'',0)}${cell(r.precipitation_previous_hour_mm)}${cell(r.wind_kmh)}${cell(r.gust_kmh)}${cell(r.wind_from_deg,'',0)}</tr>`));
  }else{
   hourlyStatus.className='notice warning';
   hourlyStatus.innerHTML=`<strong>Leitura horária S735/INMET ainda não confirmada.</strong> ${esc(obsHourly.error||'Endpoint sem valores válidos nesta coleta')}. Não significa chuva ou vento zero. Consulte a <a target="_blank" rel="noopener" href="https://tempo.inmet.gov.br/TabelaEstacoes">tabela oficial do INMET</a> ou os <a target="_blank" rel="noopener" href="https://portal.inmet.gov.br/dadoshistoricos/">arquivos horários históricos gratuitos</a>.`;
   if($('inmet-hourly-table'))$('inmet-hourly-table').innerHTML='';
  }
 }
 const stationObs=official.inmet_daily_nearby||{};
 const obsEl=$('inmet-daily');
 if(stationObs.state==='ok' && (stationObs.records||[]).length){
  const rainRec=stationObs.records.filter(x=>x.precipitation_mm!==null);
  const last=stationObs.records[stationObs.records.length-1];
  obsEl.textContent=`INMET ${stationObs.station_name} (${stationObs.station_code}; ${fmt(stationObs.distance_km,0)} km da sede): ${stationObs.records.length} dia(s) consultados, ${rainRec.length} com chuva observada. Último registro: ${last.date}. Não é medição de Naviraí.`;
 } else {
  obsEl.textContent=`Observações diárias INMET não confirmadas: ${stationObs.error||'sem resposta válida'}; não significa ausência de chuva.`;
 }
 const e=state?.embrapa_observations||{}, records=(['ok','provisional'].includes(e.state)?(e.records||[]):[]);
 const notice=$('embrapa-status');
 if(!records.length){
  notice.className='notice muted';notice.textContent=e.state==='invalid'?'CSV da Embrapa reprovado na validação: '+(e.errors||[]).join(' | ').slice(0,190):'Histórico Embrapa Naviraí ainda não integrado. É necessária exportação revisada da estação 6.';
  clearPlot('observed-rain-plot','Sem observações auditadas. Não corresponde a chuva de 0 mm.');clearPlot('embrapa-monthly-plot','Histórico não disponível.');clearPlot('embrapa-et0-plot','Histórico não disponível.');
  $('embrapa-history-table').innerHTML='<tr><td>Aguardando série observacional validada.</td></tr>';
 }else{
  const last=records.slice(-30);
  notice.className=e.state==='provisional'?'notice warning':'notice';
  notice.textContent=e.state==='provisional'
   ? `⚠️ Exportação da Embrapa ainda SEM ID DE ESTAÇÃO confirmado: ${e.record_count} dias (até ${e.date_last}), ${e.excluded_early_records||6} registros anteriores a 01/12/2024 excluídos. Confirmar Naviraí/IFMS antes de avaliar acurácia; são valores preliminares, não dados observados certificados para este local.`
   : `Estação 6 · ${e.record_count} registros importados, ${e.rain_nonmissing_days} dias com chuva informada. Dados históricos, não tempo real.`;
  chart('observed-rain-plot',[{type:'bar',x:last.map(r=>ddmm(r.date)),y:last.map(r=>r.precipitation_mm),name:e.state==='provisional'?'Chuva do arquivo exportado • localização não confirmada (mm)':'Chuva observada (mm)',marker:{color:'#168fc2'}}],e.state==='provisional'?'Chuva do arquivo provisório (mm/dia)':'Chuva observada (mm/dia)');
  tableFill('embrapa-history-table',['Dia','Chuva observada mm','T média °C','UR média %'],last.slice().reverse().map(r=>`<tr><td>${esc(ddmm(r.date))}</td>${cell(r.precipitation_mm)}${cell(r.temperature_mean_c)}${cell(r.relative_humidity_mean_pct)}</tr>`));
  const monthMap=new Map();
  for(const rec of records){const mo=rec.date.slice(0,7), m=monthMap.get(mo)||{total:0,days:0};
    if(num(rec.precipitation_mm)!==null){m.total+=Number(rec.precipitation_mm);m.days++;}
    monthMap.set(mo,m);}
  const months=[...monthMap.entries()].slice(-15);
  chart('embrapa-monthly-plot',[{type:'bar',x:months.map(([m])=>m.slice(5)+'/'+m.slice(2,4)),
      y:months.map(([,v])=>Number(v.total.toFixed(1))),name:'Acumulado da exportação • mm',marker:{color:'#258ec0'},
      customdata:months.map(([,v])=>v.days),hovertemplate:'%{x}: %{y:.1f} mm (%{customdata} dias)'}], 'mm/mês',{height:310});
  const et0last=records.filter(r=>num(r.et0_mm_day)!==null).slice(-45);
  chart('embrapa-et0-plot',[{type:'scatter',mode:'lines+markers',
      x:et0last.map(r=>ddmm(r.date)),y:et0last.map(r=>r.et0_mm_day),
      name:'ET₀ • mm/dia',line:{color:'#e7974b',width:3},marker:{size:4}}],'ET₀ (mm/dia)',{height:310});

 }
}

function renderExtras(){
 const c=state?.complementary||{};
 const metas=[['CPTEC/INPE — 7 dias','cptec'],['OpenWeather Free • 5 dias / 3h (opcional)','openweather'],
 ['Open-Meteo • solo em grade','soil_forecast'],['NASA POWER (histórico em grade)','nasa_power'],
 ['ECMWF EC46/SEAS5 (tendência)','ecmwf_extended'],
 ['Climatologia ERA5-Land (1991–2020)','era5_climatology'],['Previous Runs • previsões passadas','previous_runs'],['GOES-19 / INPE DSAT','goes_satellite'],
 ['GPM/IMERG','gpm_imerg'],['ISRIC SoilGrids','soilgrids']];
 tableFill('source-status-table',['Serviço','Estado real da integração','Horário da consulta (UTC)','Informação'],
  metas.map(([name,key])=>{const o=c[key]||{};const label=({ok:'✓ Dados válidos',unavailable:'Falha de consulta',requires_key:'Requer chave/plano',requires_setup:'Aguardando configuração',requires_registration:'Requer cadastro',service_paused:'Serviço REST pausado',disabled_no_cost:'Desativado: sem cobrança',disabled:'Desativado',optional_free_key:'Opcional: chave gratuita' })[o.state]||'Ainda não integrado';
   return `<tr><td>${esc(name)}</td><td class="${o.state==='ok'?'ok':'warn'}">${esc(label)}</td><td>${esc(o.queried_at_utc?.slice(0,19).replace('T',' ')||'—')}</td><td><a target="_blank" rel="noopener" href="${esc(o.source_url||'#')}">Fonte ↗</a> · ${esc((o.error||o.note||'').slice(0,140))}</td></tr>`;
  }));
 const ow=c.openweather||{};
 const owMsg=ow.state==='ok'?`OpenWeather gratuito: ${(ow.forecast||[]).length} previsões em blocos de 3h, com chuva e PoP quando fornecidas. Não é novo membro nem dado observado.`:`OpenWeather gratuito opcional: ${ow.note||ow.error||'sem retorno'} (sem custo e sem One Call).`;
 const cp=c.cptec||{};
 $('cptec-preview').innerHTML=cp.state==='ok'
  ? `<strong>CPTEC/INPE — previsão independente</strong> (emissão ${esc(cp.product_updated_date)}) · ${esc(cp.place)}/${esc(cp.uf)}<div class="scroll"><table class="compact"><thead><tr><th>Data</th><th>Condição/código</th><th>Tmin °C</th><th>Tmax °C</th></tr></thead><tbody>${(cp.days||[]).map(d=>`<tr><td>${esc(d.date)}</td><td>${esc(d.weather_code)}</td><td>${fmt(d.tmin_c)}</td><td>${fmt(d.tmax_c)}</td></tr>`).join('')}</tbody></table></div><small>Não fornece mm ou probabilidade calibrada neste produto. Não conta como membro do ensemble.</small>`
  : `CPTEC/INPE — ${esc(cp.error||cp.note||'sem resposta confirmada')}. A previsão do próprio serviço deve ser consultada em sua página.`;
 const soil=c.soil_forecast||{},sh=soil.hourly||{},key=soil.soil_moisture_keys?.[0];
 if(soil.state==='ok'&&key&&Array.isArray(sh[key])&&sh[key].some(v=>v!=null)){
   $('soil-forecast-report').textContent=`Estimativa modelada ${key} (m³/m³), grade ${fmt(soil.grid_lat,3)}, ${fmt(soil.grid_lon,3)}. Não representa sensor no talhão e não é índice calibrado de trafegabilidade.`;
   const sample=sh[key].slice(0,72),times=(sh.time||[]).slice(0,72);
   chart('soil-forecast-plot',[{type:'scatter',mode:'lines',x:times.map(dh),y:sample,name:'Umidade do solo na grade',line:{color:'#1689aa',width:3}}],'m³/m³',{height:310});
 }else{$('soil-forecast-report').textContent='Umidade do solo em grade indisponível: '+(soil.error||soil.note||'sem dados');clearPlot('soil-forecast-plot','Sem estimativa de umidade do solo.')}
 const ext=c.ecmwf_extended||{},weeks=ext.weeks||[];
 $('extended-weekly').innerHTML=weeks.length
  ? `<strong>Cenários semanais ECMWF (36 km; não calibrados):</strong><div class="scroll"><table class="compact"><thead><tr><th>Semana</th><th>P10 chuva mm</th><th>P50</th><th>P90</th><th>Membros</th></tr></thead><tbody>${weeks.map(w=>`<tr><td>${esc(w.start)} a ${esc(w.end)}</td><td>${fmt(w.rain_week_p10_mm)}</td><td>${fmt(w.rain_week_p50_mm)}</td><td>${fmt(w.rain_week_p90_mm)}</td><td>${esc(w.member_count)}</td></tr>`).join('')}</tbody></table></div><small>Não é previsão diária para pulverização. Fontes EC46/SEAS5 variam conforme prazo.</small>`
  : 'ECMWF 15–60 dias: '+esc(ext.note||ext.error||'produto ainda não configurado')+' Os primeiros 14 dias acima permanecem determinísticos.';
 $('source-extra-notes').textContent=owMsg+' Somente fontes gratuitas são consultadas; One Call paga não é utilizada. NASA POWER, ERA5-Land e Previous Runs não são medições de pluviômetros. GOES-19 possui visualização pública externa, sem interpretação automática de imagem local.';
}

function renderFreeResearch(){
 const c=state?.complementary||{}, clima=c.era5_climatology||{};
 const climateStatus=$('climate-era5-status'),climateEl=$('climate-era5-plot');
 const climateAvailable=clima.state==='ok' && (clima.months||[]).length===12;
 $('climate-era5-card').hidden=!climateAvailable;
 if(climateAvailable){
  const months=clima.months;
  climateStatus.className='notice';climateStatus.textContent=`ERA5-Land 1991–2020 · precipitação média anual estimada: ${fmt(clima.yearly_mean_sum_mm,0)} mm · grade ${fmt(clima.grid_lat,3)}, ${fmt(clima.grid_lon,3)}. Reanálise, não pluviômetro.`;
  chart('climate-era5-plot',[{type:'bar',x:months.map(x=>x.month_name),y:months.map(x=>x.mean_monthly_rain_mm),name:'Chuva mensal média em grade',marker:{color:'#218ec0'},
     customdata:months.map(x=>x.years_complete),hovertemplate:'%{x}: %{y:.1f} mm · %{customdata} anos completos<extra></extra>'}],'mm/mês',{height:330});
 }else{climateStatus.className='notice warning';climateStatus.textContent=`ERA5-Land não disponível nesta edição: ${clima.error||clima.note||'sem resposta'}. Não extrapolamos dados.`;clearPlot('climate-era5-plot','Sem série climatológica válida.');}
 const prev=c.previous_runs||{},comp=state?.historical_comparison||{};
 const previousStatus=$('previous-runs-status'),previousEl=$('previous-runs-plot');
 const previousAvailable=comp.state==='exploratory' && (comp.paired_days||[]).length>0;
 $('previous-runs-card').hidden=!previousAvailable;
 $('historical-evidence').hidden=!climateAvailable&&!previousAvailable;
 if(previousAvailable){
  const pairs=comp.paired_days;
  previousStatus.className='notice warning';previousStatus.textContent=`${comp.days_overlapping} dias com correspondência de datas. Diagnóstico SOMENTE EXPLORATÓRIO: a planilha não identifica a estação; sem índice de acerto ou calibração.`;
  const x=pairs.map(p=>ddmm(p.date));
  chart('previous-runs-plot',[
   {x,y:pairs.map(p=>p.export_mm),type:'bar',name:'Arquivo Embrapa não verificado (mm)',marker:{color:'#4ca7d0'}},
   {x,y:pairs.map(p=>p.previous_lead1_mm),type:'scatter',mode:'lines',name:'Previsão 1 dia antes (mm)',line:{color:'#e48742',width:2}},
   {x,y:pairs.map(p=>p.previous_lead3_mm),type:'scatter',mode:'lines',name:'Previsão 3 dias antes (mm)',line:{color:'#345a8c',width:2,dash:'dot'}}
  ],'mm/dia',{height:330});
 }else{previousStatus.className='notice muted';previousStatus.textContent=`Comparação ainda indisponível: ${prev.error||comp.note||'sem dias pareados'}. Sem dado não é erro zero.`;clearPlot('previous-runs-plot','Aguardando previsões históricas comparáveis.');}
}

function renderCalendar(){
 const base=state?.issued_at_utc?new Date(state.issued_at_utc):new Date();
 const start=localISO(base);
 const daily=dailyData(),byDate=new Map((daily.time||[]).map((str,i)=>[str,i]));
 const startUTC=Date.parse(start+'T12:00:00Z');
 const mondayOffset=(new Date(startUTC).getUTCDay()+6)%7;
 let cells=['Seg','Ter','Qua','Qui','Sex','Sáb','Dom'].map(x=>`<div class="calhead">${x}</div>`);
 for(let k=0;k<mondayOffset;k++)cells.push('<div class="calblank"></div>');
 for(let k=0;k<30;k++){
  const date=new Date(startUTC+k*86400000).toISOString().slice(0,10);
  const i=byDate.get(date);
  const rain=i==null?null:num(val(daily,'precipitation_sum',i)),tmax=i==null?null:num(val(daily,'temperature_2m_max',i));
  const has=rain!==null||tmax!==null;
  const cls=!has?'missing':rain>=15?'heavy':rain>=5?'wet':rain>=.1?'light':'dry';
  const symbol=!has?'—':rain>=15?'🌧':rain>=5?'🌦':rain>=.1?'🌤':'☀';
  cells.push(`<div class="calday ${cls}"><strong>${esc(ddmm(date))}</strong>${has?`<span>${symbol} ${fmt(rain)} mm</span><small>T máx ${fmt(tmax,0)} °C</small><small>Previsão determinística</small>`:'<span>Sem previsão diária</span><small>Não significa tempo seco</small>'}</div>`);
 }
 $('calendar').innerHTML=cells.join('');
}
function render(){
 const d=state?.deterministic;
 const {stale}=statusBar();
 const idx=hoursFrom(d?.hourly,72);
 const guards=[()=>renderOverview(idx),()=>renderRain(idx),()=>renderWind(idx),()=>renderSpray(idx),ensembleScreening,renderMachines,renderVerification,renderOfficial,renderExtras,renderFreeResearch,renderCalendar];
 for(const f of guards){try{f();}catch(err){console.error('Render failure',err);}}
 redrawActive();
 document.querySelectorAll('.plot').forEach(el=>{
  if(!chartSpecs.has(el.id) && !el.classList.contains('js-plotly-plot')){
   if(!el.textContent.trim())el.textContent='Sem dados válidos nesta edição.';
   el.classList.add('is-empty');
  }
 });
}
// On GitHub Pages, client-side JavaScript cannot trigger an Actions job without
// exposing a write token. Manual refresh therefore fetches the *public* Open-Meteo
// deterministic forecast and also re-reads the last published ensemble snapshot.
const FORECAST_LIVE_URL='https://api.open-meteo.com/v1/forecast';
const FORECAST_HOURLY=['temperature_2m','relative_humidity_2m','dew_point_2m','vapour_pressure_deficit','precipitation','precipitation_probability','wind_speed_10m','wind_direction_10m','wind_gusts_10m','pressure_msl','cloud_cover'];
const FORECAST_DAILY=['temperature_2m_max','temperature_2m_min','precipitation_sum','precipitation_probability_max','wind_gusts_10m_max'];
const FORECAST_CURRENT=['temperature_2m','relative_humidity_2m','precipitation','wind_speed_10m','wind_direction_10m'];
function setRefreshFeedback(message,kind='normal'){
 const node=$('refresh-feedback');node.textContent=message;node.className='refresh-feedback '+kind;
}
async function fetchWithTimeout(url,seconds=18){
 const ctrl=new AbortController(),timer=setTimeout(()=>ctrl.abort(),seconds*1000);
 try{const response=await fetch(url,{cache:'no-store',signal:ctrl.signal});if(!response.ok)throw Error('HTTP '+response.status);return await response.json();}
 finally{clearTimeout(timer);}
}
async function fetchDirectForecast(){
 const query=new URLSearchParams({latitude:'-23.065',longitude:'-54.190',timezone:'America/Campo_Grande',forecast_days:'14',hourly:FORECAST_HOURLY.join(','),daily:FORECAST_DAILY.join(','),current:FORECAST_CURRENT.join(',')});
 const payload=await fetchWithTimeout(FORECAST_LIVE_URL+'?'+query.toString(),22);
 if(payload?.error||payload?.utc_offset_seconds!==-14400)throw Error('Fuso horário ou resposta incompatível');
 if(Math.abs(payload.latitude+23.065)>.3||Math.abs(payload.longitude+54.19)>.3)throw Error('Grade muito distante da sede');
 const h=payload.hourly||{},d=payload.daily||{};
 if(!Array.isArray(h.time)||h.time.length<48||!Array.isArray(h.temperature_2m)||h.temperature_2m.length!==h.time.length||!Array.isArray(d.time)||d.time.length<7)throw Error('Previsão horária/diária incompleta');
 if(!payload.current||payload.current.time==null)throw Error('Ausência de horário da previsão atual');
 const currentDate=new Date(payload.current.time+'-04:00');
 if(!Number.isFinite(currentDate.getTime())||Math.abs(Date.now()-currentDate.getTime())>4*3600000)throw Error('Previsão atual com horário incompatível');
 return {hourly:h,daily:d,current:payload.current,latitude:payload.latitude,longitude:payload.longitude,elevation:payload.elevation,utc_offset_seconds:payload.utc_offset_seconds,model_used:'Open-Meteo Forecast auto — consulta direta do navegador',collected_at_utc:new Date().toISOString()};
}
let refreshInProgress=false;
async function refresh(manual=false){
 if(window.CampoLocation?.isCustom())return window.CampoLocation.refreshCustom(manual);
 if(refreshInProgress)return;
 refreshInProgress=true;
 const button=$('refresh'),prior=state;
 button.disabled=true;button.textContent='↻ Consultando…';
 setRefreshFeedback(manual?'Consultando publicação e previsão atual…':'Lendo último boletim publicado…');
 let publishedNew=false,liveNew=false,errorHosted=null,errorLive=null;
 try{
  try{
   const published=await fetchWithTimeout(DATA_URL+'?cache='+Date.now(),18);
   if(!published||!published.issued_at_utc||!published.deterministic)throw Error('Publicação sem os campos esperados');
   publishedNew=published.issued_at_utc!==prior?.issued_at_utc;
   if(window.CampoLocation?.isCustom())return;
   state=published;
   // Preserve the latest direct forecast when GitHub did not publish a newer run.
   if(!publishedNew && prior?._liveForecastAt && Date.now()-new Date(prior._liveForecastAt).getTime()<90*60000){
    state.deterministic=prior.deterministic;state._liveForecastAt=prior._liveForecastAt;
   }
  }catch(e){errorHosted=e;if(window.CampoLocation?.isCustom())return;if(!state)state=prior;}
  if(manual){
   try{
    const forecast=await fetchDirectForecast();
    if(window.CampoLocation?.isCustom())return;
    if(!state)throw Error('A publicação multimodelo ainda não está disponível');
    state.deterministic=forecast;state._liveForecastAt=forecast.collected_at_utc;
    liveNew=true;
   }catch(e){errorLive=e;}
  }
  if(state)render();
  else $('status').textContent='⚠️ Nenhuma coleta meteorológica válida está disponível.';
  const localTime=new Date().toLocaleTimeString('pt-BR',{timeZone:activeTZ(),hour:'2-digit',minute:'2-digit'});
  if(liveNew){setRefreshFeedback(`✓ ${localTime}: previsão horária consultada agora na Open-Meteo. Ensembles: última publicação do GitHub.`, 'good');}
  else if(publishedNew){setRefreshFeedback(`✓ ${localTime}: nova coleta do GitHub carregada. ${manual?'A consulta direta não respondeu; previsão do servidor mantida.':''}`, 'good');}
  else if(state){setRefreshFeedback(`ℹ ${localTime}: nenhuma nova coleta publicada. ${errorLive?'Consulta direta indisponível; dados anteriores mantidos.':'Previsão da última coleta mantida.'}`, 'info');}
  else{setRefreshFeedback(`⚠ ${localTime}: não foi possível obter dados. Verifique a conexão.`, 'error');}
  if(errorHosted||errorLive)console.warn('Campo e Clima refresh status', {hosted:!!errorHosted,direct:!!errorLive});
 }finally{button.disabled=false;button.textContent='↻ Atualizar previsão agora';refreshInProgress=false;}
}
$('tabs').addEventListener('click',event=>{
 const button=event.target.closest('button[data-tab]');if(!button)return;
 document.querySelectorAll('#tabs button').forEach(x=>x.classList.toggle('active',x===button));
 document.querySelectorAll('.tab').forEach(x=>x.classList.toggle('active',x.id===button.dataset.tab));
 requestAnimationFrame(()=>requestAnimationFrame(redrawActive));
});
$('refresh').addEventListener('click',()=>refresh(true));
$('product').addEventListener('change',()=>{if(state){renderSpray(hoursFrom(state.deterministic?.hourly,72));ensembleScreening();}});
$('spray-period').addEventListener('change',()=>{if(state){renderSpray(hoursFrom(state.deterministic?.hourly,72));ensembleScreening();}});
window.addEventListener('resize',()=>{if(window.Plotly)for(const el of document.querySelectorAll('.tab.active .js-plotly-plot'))Plotly.Plots.resize(el);});
refresh(false);setInterval(()=>refresh(true),30*60*1000);
