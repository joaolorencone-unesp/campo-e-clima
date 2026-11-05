'use strict';
/** Campo e Clima v4 — deterministic models side by side (collector product `deterministic_models`). */
(function(root){
 const $=id=>typeof document==='undefined'?null:document.getElementById(id);
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const finite=v=>typeof v==='number'&&Number.isFinite(v);
 const fmt=(v,d=1)=>finite(v)?v.toFixed(d).replace('.',','):'—';
 const COLORS=['#0f2a66','#0f7a3b','#0b8df0','#e0101f','#8a5a12','#6f8194','#22a327','#7a3b8f','#c05621'];
 function rows(product){
  const out=[];
  for(const [id,block] of Object.entries(product?.models||{})){
   if(block.state!=='ok')continue;
   const d=block.daily||{};
   out.push({id,label:block.label||id,dates:d.time||[],rain:d.precipitation_sum||[],tmax:d.temperature_2m_max||[],tmin:d.temperature_2m_min||[],gust:d.wind_gusts_10m_max||[]});
  }
  return out;
 }
 function summary(product){
  const ok=rows(product),missing=Object.entries(product?.models||{}).filter(([,b])=>b.state!=='ok');
  return {ok:ok.length,missing:missing.map(([id,b])=>`${b.label||id}: ${b.error||'indisponível'}`),fallback:product?.fallback||null};
 }
 function render(product){
  const status=$('models-compare-status'),table=$('models-compare-table'),plot=$('models-compare-plot');
  if(!status||!table)return;
  if(!product||product.state!=='ok'){status.textContent='Comparação multimodelo indisponível nesta coleta'+(product?.error?` (${product.error})`:'')+'.';status.className='notice muted';table.innerHTML='';return;}
  const list=rows(product),info=summary(product);
  status.className='notice';
  status.innerHTML=`<strong>${info.ok} modelos determinísticos</strong> no mesmo ponto, coleta ${esc(new Date(product.collected_at_utc).toLocaleString('pt-BR'))}.${info.fallback?' '+esc(info.fallback)+'.':''}${info.missing.length?` <small>Indisponíveis: ${esc(info.missing.join(' · '))}</small>`:''}`;
  const dates=list[0]?.dates||[];
  const spread=new Map((product.spread_daily||[]).map(s=>[s.date,s]));
  const head=`<thead><tr><th>Modelo</th>${dates.map(d=>`<th>${esc(d.slice(8,10))}/${esc(d.slice(5,7))}</th>`).join('')}</tr></thead>`;
  const body=list.map(r=>`<tr><td><strong>${esc(r.label)}</strong><br><small>${esc(r.id)}</small></td>${dates.map((_,i)=>`<td><strong>${fmt(r.rain[i])}</strong> mm<br><small>${fmt(r.tmin[i],0)}–${fmt(r.tmax[i],0)} °C${finite(r.gust[i])?' · '+fmt(r.gust[i],0)+' km/h':''}</small></td>`).join('')}</tr>`).join('');
  const foot=`<tr class="spread-row"><td><strong>Faixa entre modelos</strong><br><small>chuva mín–mediana–máx · modelos ≥1 mm</small></td>${dates.map(d=>{const s=spread.get(d);return s?`<td><strong>${fmt(s.rain_min_mm,0)}–${fmt(s.rain_median_mm,0)}–${fmt(s.rain_max_mm,0)}</strong> mm<br><small>${s.models_wet_1mm}/${s.models} com chuva</small></td>`:'<td>—</td>';}).join('')}</tr>`;
  table.innerHTML=head+'<tbody>'+body+foot+'</tbody>';
  if(plot&&root.Plotly&&dates.length){
   const traces=list.map((r,i)=>({type:'bar',name:r.label,x:dates,y:r.rain.map(v=>finite(v)?v:null),marker:{color:COLORS[i%COLORS.length]},hovertemplate:'%{x}<br>%{y:.1f} mm<extra>'+esc(r.label)+'</extra>'}));
   root.Plotly.react(plot,traces,{barmode:'group',margin:{l:40,r:10,t:10,b:40},yaxis:{title:'mm/dia'},legend:{orientation:'h',y:-0.25},paper_bgcolor:'rgba(0,0,0,0)',plot_bgcolor:'rgba(0,0,0,0)'},{displayModeBar:false,responsive:true});
  }
 }
 if(typeof document!=='undefined')root.addEventListener('campo:forecast-rendered',()=>{try{render(typeof state!=='undefined'?state?.deterministic_models:null);}catch(e){console.error('models compare',e);}});
 root.CampoModelsCompare={render,rows,summary};
 if(typeof module==='object'&&module.exports)module.exports=root.CampoModelsCompare;
})(typeof window!=='undefined'?window:globalThis);
