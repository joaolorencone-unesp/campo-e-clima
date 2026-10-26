'use strict';
const DATA_URL='data/latest.json';let state=null;const $=id=>document.getElementById(id);const fmt=(x,d=1)=>x===null||x===undefined||!Number.isFinite(Number(x))?'—':Number(x).toFixed(d);const esc=s=>String(s??'—').replace(/[&<>"]/g,x=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[x]));
const hoursFrom=(h,n=48)=>{if(!h?.time)return [];const now=new Date();return h.time.map((t,i)=>({t,i,date:new Date(`${t}-04:00`)})).filter(x=>x.date>=new Date(now.getTime()-3600000)).slice(0,n)};
const val=(h,k,i)=>h?.[k]?.[i]??null;
function plot(id,traces,titleY){if(!window.Plotly){$(id).innerHTML='<p>Gráfico indisponível sem conexão com a biblioteca de visualização.</p>';return;}if(!traces.length){$(id).textContent='Sem valores verificados disponíveis.';return;}Plotly.react(id,traces,{paper_bgcolor:'#fff',plot_bgcolor:'#fff',font:{family:'system-ui',color:'#506476',size:12},margin:{l:54,r:15,t:18,b:70},legend:{orientation:'h',y:-.25},hovermode:'x unified',xaxis:{showgrid:true,gridcolor:'#eaf0f4'},yaxis:{title:titleY,gridcolor:'#eaf0f4'},height:320},{responsive:true,displayModeBar:false});}
function render(){const d=state?.deterministic,h=d?.hourly,idx=hoursFrom(h,48);const fresh=state?.issued_at_utc?new Date(state.issued_at_utc):null;const age=fresh?Math.round((Date.now()-fresh.getTime())/60000):null;const stale=age===null||age>90||age<0;const ensemble=state?.rain_ensemble_daily||[];
 $('last-updated').textContent=fresh?'Coletado: '+fresh.toLocaleString('pt-BR',{timeZone:'America/Campo_Grande'})+' (Naviraí)':'Nenhuma coleta disponível';$('status').innerHTML=stale?'⚠️ <b>Sem coleta recente.</b> Valores eventualmente presentes são históricos e não devem ser utilizados como previsão atual.':`✓ Coleta há ${age} min. ${esc(Object.keys(state?.ensemble_models||{}).filter(k=>state.ensemble_models[k].state==='ok').length)} modelos com dados diários de chuva; frequências ainda não calibradas.`;
 const cur=d?.current||{};const next24=idx.slice(0,24),rainValues=next24.map(x=>val(h,'precipitation',x.i));const rainNext=rainValues.length===24&&rainValues.every(x=>x!==null&&Number.isFinite(Number(x)))?rainValues.reduce((a,x)=>a+Number(x),0):null;
 $('metrics').innerHTML=[['Temperatura (modelo, horário atual)',cur.temperature_2m,'°C'],['Umidade relativa',cur.relative_humidity_2m,'%'],['Vento médio',cur.wind_speed_10m,'km/h'],['Chuva prevista 24h',rainNext,'mm']].map(([label,x,u])=>`<article class="metric"><span>${label}</span><strong>${fmt(x,1)} ${u}</strong><small>${stale?'Sem dados recentes':label==='Chuva prevista 24h'?'Forecast determinístico':'Open-Meteo Forecast'}</small></article>`).join('');
 if(!idx.length){['temp-plot','hour-rain-plot','wind-plot'].forEach(id=>$(id).textContent='Sem dados horários atuais.');['hour-table','wind-table','spray-table'].forEach(id=>$(id).innerHTML='<tr><td>Sem dados disponíveis.</td></tr>');}else{
 const x=idx.map(z=>z.t.slice(5).replace('T',' '));plot('temp-plot',[{x,y:idx.map(z=>val(h,'temperature_2m',z.i)),name:'Temperatura (°C)',mode:'lines',line:{color:'#eb8453',width:3}},{x,y:idx.map(z=>val(h,'relative_humidity_2m',z.i)),name:'UR (%)',mode:'lines',yaxis:'y2',line:{color:'#168aa3',width:2}}],'Temperatura °C');if(window.Plotly)Plotly.relayout('temp-plot',{'yaxis2':{overlaying:'y',side:'right',title:'UR %',range:[0,100]}});
 plot('hour-rain-plot',[{x,y:idx.map(z=>val(h,'precipitation',z.i)),name:'Chuva prevista (mm)',type:'bar',marker:{color:'#2c89c4'}}],'mm/h');
 plot('wind-plot',[{x,y:idx.map(z=>val(h,'wind_speed_10m',z.i)),name:'Vento médio (km/h)',mode:'lines',line:{color:'#15a085',width:3}},{x,y:idx.map(z=>val(h,'wind_gusts_10m',z.i)),name:'Rajada (km/h)',mode:'lines',line:{color:'#df7757',width:2,dash:'dot'}}],'km/h');
 const header=(titles)=>'<thead><tr>'+titles.map(s=>`<th>${s}</th>`).join('')+'</tr></thead>';
 $('hour-table').innerHTML=header(['Data/hora (UTC−4)','T °C','UR %','Chuva mm','P(chuva) %*','Vento km/h','Rajada km/h','Direção °'])+'<tbody>'+idx.map(z=>'<tr><td>'+esc(z.t.slice(5).replace('T',' '))+'</td>'+[['temperature_2m',1],['relative_humidity_2m',0],['precipitation',1],['precipitation_probability',0],['wind_speed_10m',1],['wind_gusts_10m',1],['wind_direction_10m',0]].map(([k,p])=>`<td>${fmt(val(h,k,z.i),p)}</td>`).join('')+'</tr>').join('')+'</tbody>';
 $('wind-table').innerHTML=header(['Hora','De onde sopra °','Vento médio km/h','Rajada km/h'])+'<tbody>'+idx.map(z=>`<tr><td>${esc(z.t)}</td><td>${fmt(val(h,'wind_direction_10m',z.i),0)}</td><td>${fmt(val(h,'wind_speed_10m',z.i))}</td><td class="${Number(val(h,'wind_gusts_10m',z.i))>30?'bad':'warn'}">${fmt(val(h,'wind_gusts_10m',z.i))}</td></tr>`).join('')+'</tbody>';
 renderSpray();}
 if(ensemble.length){let x=ensemble.map(z=>z.date.slice(5));plot('rain-plot',[{x,y:ensemble.map(z=>z.mean_mm),type:'bar',name:'Média multimodelo',marker:{color:'#438dc4'}},{x,y:ensemble.map(z=>z.p10_mm),mode:'lines',name:'P10',line:{color:'#acc7e0',dash:'dot'}},{x,y:ensemble.map(z=>z.p50_mm),mode:'lines',name:'Mediana P50',line:{color:'#15638e',width:3}},{x,y:ensemble.map(z=>z.p90_mm),mode:'lines',name:'P90',line:{color:'#df8a59',dash:'dash'}}],'mm/dia');$('rain-table').innerHTML='<thead><tr><th>Data</th><th>Modelos válidos</th><th>Membros</th><th>Média mm</th><th>P10</th><th>P50</th><th>P90</th><th>Frequência >5 mm</th><th>>10 mm</th></tr></thead><tbody>'+ensemble.map(z=>`<tr><td>${z.date}</td><td>${z.model_count}</td><td>${z.member_count}</td><td>${fmt(z.mean_mm)}</td><td>${fmt(z.p10_mm)}</td><td>${fmt(z.p50_mm)}</td><td>${fmt(z.p90_mm)}</td><td>${fmt(z.p_gt_5_mm*100,0)}%</td><td>${fmt(z.p_gt_10_mm*100,0)}%</td></tr>`).join('')+'</tbody>';}else{$('rain-plot').textContent='Ensemble indisponível nesta coleta; nenhuma probabilidade será estimada.';$('rain-table').innerHTML='<tr><td>Sem membros completos validados.</td></tr>';}renderDaily();renderGust();renderCalendar();}
function renderDaily(){
 const d=state?.deterministic?.daily;
 const days=d?.time||[];
 const rows=days.map((date,i)=>`<tr><td>${esc(date)}</td><td>${fmt(val(d,'temperature_2m_min',i))}</td><td>${fmt(val(d,'temperature_2m_max',i))}</td><td>${fmt(val(d,'precipitation_sum',i))}</td><td>${fmt(val(d,'precipitation_probability_max',i),0)}</td><td>${fmt(val(d,'wind_gusts_10m_max',i))}</td></tr>`).join('');
 $('daily-table').innerHTML=days.length?'<thead><tr><th>Dia</th><th>T min °C</th><th>T máx °C</th><th>Chuva mm</th><th>Chance máxima %*</th><th>Rajada máx km/h</th></tr></thead><tbody>'+rows+'</tbody>':'<tr><td>Sem previsão diária válida.</td></tr>';
}
function renderGust(){
 const a=state?.gust_ensemble_daily||[];
 if(!a.length){$('gust-plot').textContent='Nenhum modelo com amostra diária completa de rajadas disponível.';$('gust-table').innerHTML='<tr><td>Sem amostra válida; não equivale a risco zero.</td></tr>';return;}
 const x=a.map(z=>z.date.slice(5));plot('gust-plot',[
   {x,y:a.map(z=>z.p_gt_30_kmh*100),type:'bar',name:'>30 km/h',marker:{color:'#eeb75e'}},
   {x,y:a.map(z=>z.p_gt_40_kmh*100),type:'bar',name:'>40 km/h',marker:{color:'#e17c62'}},
   {x,y:a.map(z=>z.p_gt_60_kmh*100),type:'bar',name:'>60 km/h',marker:{color:'#c14959'}}],'Frequência (%)');
 $('gust-table').innerHTML='<thead><tr><th>Dia</th><th>Modelos</th><th>Membros</th><th>Mediana km/h</th><th>P90 km/h</th><th>>30 km/h</th><th>>40 km/h</th><th>>60 km/h</th></tr></thead><tbody>'+a.map(z=>`<tr><td>${esc(z.date)}</td><td>${z.model_count}</td><td>${z.member_count}</td><td>${fmt(z.p50_kmh)}</td><td>${fmt(z.p90_kmh)}</td><td>${fmt(z.p_gt_30_kmh*100,0)}%</td><td>${fmt(z.p_gt_40_kmh*100,0)}%</td><td>${fmt(z.p_gt_60_kmh*100,0)}%</td></tr>`).join('')+'</tbody>';
}
function renderSpray(){const h=state?.deterministic?.hourly,idx=hoursFrom(h,48),kind=$('product').value;
 $('spray-table').innerHTML='<thead><tr><th>Hora</th><th>T</th><th>UR</th><th>VPD kPa</th><th>Vento</th><th>Rajada</th><th>Chuva</th><th>Triagem meteorológica</th><th>Motivo</th></tr></thead><tbody>'+idx.map(z=>{const t=val(h,'temperature_2m',z.i),rh=val(h,'relative_humidity_2m',z.i),v=val(h,'wind_speed_10m',z.i),gust=val(h,'wind_gusts_10m',z.i),pr=val(h,'precipitation',z.i),vpd=val(h,'vapour_pressure_deficit',z.i);let reasons=[];if(t===null||rh===null||v===null||gust===null||pr===null||vpd===null)reasons.push('Variáveis faltantes');else{if(t>=30)reasons.push('Temperatura elevada');if(rh<55)reasons.push('UR baixa');if(v<3)reasons.push('Calmaria e possível inversão');if(v>10)reasons.push('Vento >10 km/h');if(gust>25)reasons.push('Rajadas elevadas');if(pr>0.1)reasons.push('Chuva prevista');if(kind==='herb'&&vpd!==null&&vpd>1.2)reasons.push('VPD alto para triagem conservadora');}let cls=reasons.includes('Variáveis faltantes')?'Indeterminado / sem dados':reasons.length?'Desfavorável / revisar':'Indeterminado';return `<tr><td>${esc(z.t.slice(5))}</td><td class="${t>=30?'bad':''}">${fmt(t)}</td><td class="${rh!==null&&rh<55?'bad':''}">${fmt(rh,0)}</td><td>${fmt(vpd,2)}</td><td class="${v!==null&&(v>10||v<3)?'bad':''}">${fmt(v)}</td><td class="${gust>25?'bad':''}">${fmt(gust)}</td><td class="${pr>.1?'bad':''}">${fmt(pr)}</td><td class="${reasons.length?'bad':'na'}">${cls}</td><td>${esc(reasons.join('; ')||'Inversão, bula, deriva e campo não verificados')}</td></tr>`;}).join('')+'</tbody>';
}
function renderCalendar(){
 const nowLocal=new Intl.DateTimeFormat('en-CA',{timeZone:'America/Campo_Grande',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
 const [yr,mo,da]=nowLocal.split('-').map(Number);
 const daily=state?.deterministic?.daily||{};
 const byDate=new Map((daily.time||[]).map((date,i)=>[date,i]));
 let html='';
 for(let i=0;i<30;i++){
   // UTC midday avoids daylight-saving shifts when formatting calendar dates.
   const date=new Date(Date.UTC(yr,mo-1,da+i,12));
   const iso=date.toISOString().slice(0,10);
   const d=byDate.get(iso);
   const rain=d===undefined?null:val(daily,'precipitation_sum',d);
   const mx=d===undefined?null:val(daily,'temperature_2m_max',d);
   const label=rain===null&&mx===null?'Sem tendência validada':`☔ ${fmt(rain)} mm · ${fmt(mx,0)}°C`;
   html+=`<div class="calday ${d===undefined?'missing':'available'}"><b>${esc(iso.slice(8))}/${esc(iso.slice(5,7))}</b><span>${label}</span><small>${d===undefined?'Sem dado':'Forecast determinístico'}</small></div>`;
 }
 $('calendar').innerHTML=html;
}
async function refresh(){const b=$('refresh');b.disabled=true;try{const res=await fetch(DATA_URL+'?t='+Date.now(),{cache:'no-store'});if(!res.ok)throw Error('HTTP '+res.status);state=await res.json();render();}catch(err){state=null;render();$('status').textContent='⚠️ Dados da coleta não encontrados. A execução automática no GitHub Pages pode estar pendente ou falhou: '+String(err);}finally{b.disabled=false;}}
$('tabs').addEventListener('click',e=>{let button=e.target.closest('button[data-tab]');if(!button)return;document.querySelectorAll('#tabs button').forEach(b=>b.classList.toggle('active',b===button));document.querySelectorAll('.tab').forEach(s=>s.classList.toggle('active',s.id===button.dataset.tab));});$('refresh').onclick=refresh;$('product').onchange=()=>{if(state)renderSpray()};refresh();setInterval(refresh,30*60*1000);
