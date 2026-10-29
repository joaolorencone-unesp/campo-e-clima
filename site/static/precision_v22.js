'use strict';
/* Only published scientific reports, never fabricated demonstration values. */
(() => {
 const $=id=>document.getElementById(id), esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const fmt=x=>typeof x==='number'&&Number.isFinite(x)?x.toLocaleString('pt-BR',{maximumFractionDigits:3}):'—';
 const empty='Histórico de previsões em construção. Ainda não há amostras suficientes para validar uma calibração local.';
 let report=null,pending=null,experiments=null;
 function aggregate(rows){
  const map=new Map();
  for(const r of rows){
   const key=[r.model,r.horizon,r.lead_basis,r.station_id,r.method].join('|');
   if(!map.has(key))map.set(key,{...r,n:0,maeSum:0,mseSum:0,biasSum:0,sine:0,cosine:0,biasN:0,rain:new Map()});
   const out=map.get(key),m=r.metrics;out.n+=r.n;out.maeSum+=m.mae*r.n;out.mseSum+=m.rmse**2*r.n;
   if(m.circular){out.sine+=m.sine_error_sum||0;out.cosine+=m.cosine_error_sum||0;}
   else if(m.bias!==null){out.biasSum+=m.bias*r.n;out.biasN+=r.n;}
   for(const rain of m.rain_thresholds||[]){
    const item=out.rain.get(rain.threshold_mm)||{n:0,brierSum:0,bins:Array.from({length:10},()=>({n:0,p:0,y:0}))};
    item.n+=r.n;item.brierSum+=rain.brier*r.n;
    rain.reliability.forEach((b,i)=>{item.bins[i].n+=b.n;item.bins[i].p+=(b.forecast_mean||0)*b.n;item.bins[i].y+=(b.observed_frequency||0)*b.n;});out.rain.set(rain.threshold_mm,item);
   }
  }
  return [...map.values()].map(r=>({...r,mae:r.maeSum/r.n,rmse:Math.sqrt(r.mseSum/r.n),
   bias:r.metrics.circular?(Math.hypot(r.sine,r.cosine)>1e-12?Math.atan2(r.sine,r.cosine)*180/Math.PI:null):(r.biasN?r.biasSum/r.biasN:null)}));
 }
 function filtered(){
  const loc=$('precision-location').value,varid=$('precision-variable').value,start=$('precision-start').value,end=$('precision-end').value;
  if(start&&end&&start>end)return [];
  return (report?.results||[]).filter(r=>r.location_id===loc&&r.variable===varid&&(!start||r.start_utc.slice(0,10)>=start)&&(!end||r.end_utc.slice(0,10)<=end));
 }
 function messagePlot(id,text){if(window.Plotly)try{Plotly.purge($(id));}catch(_){}$(id).textContent=text;}
 function render(){
  if(!report)return;
  const loc=report.locations.find(l=>l.id===$('precision-location').value);if(!loc)return;
  const rows=aggregate(filtered()),n=rows.reduce((s,r)=>s+r.n,0);
  $('precision-status').textContent=n?'Há pares para comparação descritiva. Nenhum calibrador foi promovido à previsão principal.':empty;
  $('precision-provenance').textContent=`${loc.name} • ${loc.latitude}, ${loc.longitude} • ${loc.timezone}. Relatório de ${new Date(report.generated_at_utc).toLocaleString('pt-BR',{timeZone:loc.timezone})}. Período dos filtros: dias UTC. Critério de referência: estação identificada com controle básico de qualidade. A contagem abaixo informa se há registros elegíveis; representatividade local requer revisão.`;
  const cards=[['Produtos arquivados',loc.forecast_runs],['Valores observados com QC básico',loc.observation_values_basic_qc],['Pares no filtro',n],['Calibração local validada','Não']];
  $('precision-kpis').innerHTML=cards.map(([label,value])=>`<div class="agro-kpi"><small>${esc(label)}</small><strong>${esc(value)}</strong></div>`).join('');
  const options=[...new Set(rows.map(r=>r.model))];
  const chosen=$('precision-model').value;
  $('precision-model').innerHTML='<option value="all">Todos os modelos</option>'+options.map(m=>`<option value="${esc(m)}">${esc(m)}</option>`).join('');
  if(options.includes(chosen))$('precision-model').value=chosen;
  const visible=rows.filter(r=>$('precision-model').value==='all'||r.model===$('precision-model').value);
  $('precision-table-body').innerHTML=visible.length?visible.map(r=>`<tr><td>${esc(r.model)}<br><small>${esc(r.method)} • bruto</small></td><td>${esc(r.horizon)}<br><small>${esc(r.lead_basis)}</small></td><td>${esc(r.station_id)}</td><td>${r.n}</td><td>${fmt(r.mae)}</td><td>${fmt(r.rmse)}</td><td>${fmt(r.bias)}</td><td>${esc(r.unit)}</td></tr>`).join(''):'<tr><td colspan="8">Sem pares elegíveis no período e variável selecionados.</td></tr>';
  $('precision-exclusions').textContent=Object.entries(report.excluded||{}).map(([why,count])=>`${({modelled_history_not_issued_forecast:'Histórico modelado sem emissão individual',single_run_availability_unverified:'Rodada sem horário de disponibilidade comprovado',unknown_or_nonpositive_lead:'Antecedência desconhecida ou não futura',reference_unverified_or_invalid:'Referência provisória ou inválida',station_too_distant:'Estação fora da distância aceita',grid_station_too_distant:'Grade distante da estação',interval_or_unit_mismatch:'Intervalos ou unidades incompatíveis',conflicting_reference_versions:'Versões conflitantes da observação'})[why]||'Outras exclusões'}: ${count}`).join(' · ')||'Ainda não há pares para examinar. As ausências não são transformadas em zero.';
  const experimental=(experiments?.experiments||[]).filter(x=>x.status==='experimental_test_only'&&x.group[0]===loc.id&&x.group[2]===$('precision-variable').value&&(!$('precision-start').value||x.split.start_test.slice(0,10)>=$('precision-start').value)&&(!$('precision-end').value||x.split.end_test.slice(0,10)<=$('precision-end').value));
  $('precision-calibration').innerHTML=experimental.length?'<div class="scroll"><table><thead><tr><th>Modelo / horizonte</th><th>Método</th><th>Teste temporal (n)</th><th>MAE / RMSE</th><th>Brier / limiar</th></tr></thead><tbody>'+experimental.flatMap(x=>x.evaluations.map(e=>`<tr><td>${esc(x.group[1])} • ${esc(x.group[3])}</td><td>${esc(e.method)}</td><td>${x.split.test}</td><td>${fmt(e.metrics?.mae)} / ${fmt(e.metrics?.rmse)}</td><td>${fmt(e.brier)} / ${fmt(e.threshold)}</td></tr>`)).join('')+'</tbody></table></div>':'<p class="caption">Nenhum calibrador foi avaliado com amostra suficiente para esta seleção. Não há ganho de precisão demonstrado.</p>';
  if(!visible.length||!window.Plotly){messagePlot('precision-bias','Viés disponível após a formação de pares válidos.');messagePlot('precision-reliability','Confiabilidade disponível após observar os eventos de chuva.');return;}
  Plotly.react($('precision-bias'),[{type:'bar',x:visible.map(r=>`${r.model} ${r.horizon}`),y:visible.map(r=>r.bias),marker:{color:'#176d83'},hovertemplate:'%{x}<br>Viés: %{y:.3f}<extra></extra>'}],{margin:{l:55,r:20,b:100,t:20},yaxis:{title:visible[0].unit},paper_bgcolor:'transparent',plot_bgcolor:'transparent'},{responsive:true,displaylogo:false});
  const threshold=Number($('precision-threshold').value),series=visible.filter(r=>r.rain.has(threshold));
  if(!series.length){messagePlot('precision-reliability','Selecione precipitação para consultar frequências brutas versus eventos observados.');return;}
  const traces=series.map(r=>{const item=r.rain.get(threshold),bins=item.bins.filter(b=>b.n);return {type:'scatter',mode:'lines+markers',name:`${r.model} ${r.horizon} (n=${item.n})`,x:bins.map(b=>b.p/b.n),y:bins.map(b=>b.y/b.n),text:bins.map(b=>`n=${b.n}`),hovertemplate:'Frequência prevista: %{x:.2f}<br>Observada: %{y:.2f}<br>%{text}<extra>%{fullData.name}</extra>'};});
  traces.push({x:[0,1],y:[0,1],type:'scatter',mode:'lines',line:{dash:'dot',color:'#889'},name:'Referência 1:1'});
  Plotly.react($('precision-reliability'),traces,{margin:{l:55,r:20,b:60,t:20},xaxis:{title:'Frequência prevista',range:[0,1]},yaxis:{title:'Frequência observada',range:[0,1]},paper_bgcolor:'transparent',plot_bgcolor:'transparent'},{responsive:true,displaylogo:false});
 }
 async function load(){
  if(report){render();return;}if(pending)return pending;
  pending=(async()=>{try{const response=await fetch('data/verification.json',{cache:'no-cache'});if(!response.ok)throw Error('HTTP '+response.status);const value=await response.json();if(value.schema_version!==1||!Array.isArray(value.locations)||!Array.isArray(value.results))throw Error('Relatório incompatível');report=value;
   try{const r=await fetch('data/calibration.json',{cache:'no-cache'});if(r.ok)experiments=await r.json();}catch(_){}
   render();}
   catch(e){$('precision-status').textContent='Relatório científico indisponível. '+empty;$('precision-provenance').textContent='A indisponibilidade do arquivo não informa a precisão dos modelos.';}finally{pending=null;}})();return pending;
 }
 function init(){
  if(!$('precision-status'))return;
  ['location','variable','start','end','model','threshold'].forEach(k=>$('precision-'+k).addEventListener('change',render));
  $('tabs').addEventListener('click',e=>{if(e.target.closest('button[data-tab="precision"]'))void load();});
  window.addEventListener('campo:location-changed',e=>{const p=e.detail;const known=[['navirai',-23.065,-54.190],['diamantino',-14.408,-56.446]].find(([,lat,lon])=>Math.abs(p.latitude-lat)<1e-5&&Math.abs(p.longitude-lon)<1e-5);if(known){$('precision-location').value=known[0];render();}});
 }
 window.CampoPrecision={load,render,_test:{aggregate}};
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
