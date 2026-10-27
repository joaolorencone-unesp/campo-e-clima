'use strict';
/** Open-Meteo lightweight ECMWF SEASONAL endpoint for the selected coordinate.
 * Weekly/monthly means must not be interpreted as daily probabilities or P10/90.
 * No paid credentials. Exports only validated API fields with units.
 */
(() => {
 const $=id=>document.getElementById(id), CACHE=new Map();
 const finite=v=>typeof v==='number'&&Number.isFinite(v);
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const fmt=v=>finite(v)?v.toFixed(1).replace('.',','):'—';
 const key=p=>`${Number(p.latitude).toFixed(4)},${Number(p.longitude).toFixed(4)}`;
 let requestNo=0;
 function parse(payload){
  if(!payload || payload.error)throw Error(payload?.reason||'Falha no serviço sazonal');
  const w=payload.weekly||{},m=payload.monthly||{},wu=payload.weekly_units||{},mu=payload.monthly_units||{};
  if(!Array.isArray(w.time)||!Array.isArray(w.precipitation_mean)||w.precipitation_mean.length!==w.time.length)throw Error('ECMWF sem série semanal completa');
  const weekly=w.time.map((time,i)=>({date:String(time).slice(0,10),p:w.precipitation_mean[i],t:w.temperature_2m_mean?.[i],anom:w.precipitation_anomaly?.[i]})).filter(x=>finite(x.p)&&x.p>=0);
  const monthly=Array.isArray(m.time)&&Array.isArray(m.precipitation_mean)?m.time.map((time,i)=>({date:String(time).slice(0,10),p:m.precipitation_mean[i]})).filter(x=>finite(x.p)&&x.p>=0):[];
  if(!weekly.length)throw Error('ECMWF sem valores semanais válidos');
  return {weekly,monthly,unit:wu.precipitation_mean||'não informada',munit:mu.precipitation_mean||'não informada',grid:[payload.latitude,payload.longitude],source:'ECMWF EC46/SEAS5, ensemble mean; não são membros ou probabilidades'};
 }
 async function load(force=false){
  const point=window.CampoLocation?.getPoint?.();if(!point||!$('extended-coordinate-status'))return;
  const token=++requestNo,k=key(point),cached=CACHE.get(k);
  $('extended-coordinate-status').textContent='Consultando média semanal e mensal ECMWF no ponto '+k+' (produto de baixa resolução)...';
  let result;
  try{
   if(!force && cached && Date.now()-cached.at < 6*3600000)result=cached.value;
   else{
    const query=new URLSearchParams({latitude:String(point.latitude),longitude:String(point.longitude),timezone:'auto',forecast_days:'63',models:'ecmwf_seasonal_ensemble_mean_seamless',weekly:'precipitation_mean,precipitation_anomaly,temperature_2m_mean',monthly:'precipitation_mean'});
    const ctrl=new AbortController(),timer=setTimeout(()=>ctrl.abort(),50000);
    let response;try{response=await fetch('https://seasonal-api.open-meteo.com/v1/seasonal?'+query,{signal:ctrl.signal,cache:'no-store'});}finally{clearTimeout(timer);}
    if(!response.ok)throw Error('HTTP '+response.status);
    result=parse(await response.json());CACHE.set(k,{at:Date.now(),value:result});
   }
   if(token!==requestNo || k!==key(window.CampoLocation.getPoint()))return;
   const unit=result.unit,days=result.weekly;
   $('extended-coordinate-status').textContent=`✓ ECMWF EC46/SEAS5: ${days.length} períodos semanais consultados para ${k}; grade ${result.grid.map(v=>fmt(v)).join(', ')}. Unidade declarada para precipitação: ${unit}. Tendência modelada, NÃO chuva diária ou probabilidade calibrada.`;
   const plot=$('extended-coordinate-plot');
   if(window.Plotly && plot){
    Plotly.react(plot,[{x:days.map(d=>d.date),y:days.map(d=>d.p),type:'bar',name:'Precipitação média ECMWF',marker:{color:'#388cba'},hovertemplate:'Início: %{x}<br>Média: %{y:.2f} '+esc(unit)+'<extra></extra>'}],{height:320,margin:{l:65,r:25,t:20,b:65},xaxis:{type:'category',tickangle:-35,title:'Período semanal (início)'},yaxis:{title:'Média de precipitação ('+esc(unit)+')'},paper_bgcolor:'rgba(0,0,0,0)',plot_bgcolor:'rgba(0,0,0,0)'},{responsive:true,displaylogo:false});
   }else if(plot)plot.textContent='Tabela semanal disponível; gráfico interativo indisponível.';
   $('extended-coordinate-monthly').innerHTML=result.monthly.length?`<strong>Contexto mensal SEAS5 (não somar médias semanais e mensais):</strong> ${result.monthly.map(m=>`<span class="badgegray">${esc(m.date)}: ${fmt(m.p)} ${esc(result.munit)}</span>`).join(' ')}`:'Nenhum produto mensal numérico disponível. Não significa tempo seco.';
  }catch(e){if(token!==requestNo)return;$('extended-coordinate-status').textContent='Tendência estendida não disponível: '+String(e.name==='AbortError'?'tempo limite':e.message||e).slice(0,150)+'. O horizonte diário confiável permanece limitado à previsão validada.';$('extended-coordinate-monthly').textContent='';const plot=$('extended-coordinate-plot');if(plot){if(window.Plotly)Plotly.purge(plot);plot.textContent='Sem dados semanais validados nesta consulta.';}}
 }
 document.getElementById('tabs')?.addEventListener('click',ev=>{if(ev.target.closest('[data-tab="extended"]'))load();});
 $('extended-refresh')?.addEventListener('click',()=>load(true));
 window.addEventListener?.('campo:location-changed',()=>{requestNo++;if(document.getElementById('extended')?.classList.contains('active'))load();});
 window.CampoExtendedV12={load,_test:{parse}};
})();
