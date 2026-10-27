'use strict';
/** v1.3: Read ONLY pre-collected GitHub Pages products. Never hit seasonal-api from
 * browsers: the GitHub Actions collector has weekly back-off/cache for ECMWF.
 * For custom coordinates the Naviraí outlook is explicitly inapplicable.
 */
(() => {
  const $=id=>document.getElementById(id);
  const finite=v=>typeof v==='number'&&Number.isFinite(v);
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt=v=>finite(v)?v.toFixed(1).replace('.',','):'—';
  const key=p=>`${Number(p.latitude).toFixed(4)},${Number(p.longitude).toFixed(4)}`;
  let requestNo=0;
  // Keep the pure parser for regression testing; live forecasts are read from published JSON.
  function parse(payload){
    if(!payload||payload.error)throw Error(payload?.reason||'Falha no serviço sazonal');
    const w=payload.weekly||{},m=payload.monthly||{},wu=payload.weekly_units||{},mu=payload.monthly_units||{};
    if(!Array.isArray(w.time)||!Array.isArray(w.precipitation_mean)||w.precipitation_mean.length!==w.time.length)throw Error('ECMWF sem série semanal completa');
    const weekly=w.time.map((time,i)=>({date:String(time).slice(0,10),p:w.precipitation_mean[i],t:w.temperature_2m_mean?.[i],anom:w.precipitation_anomaly?.[i]})).filter(x=>finite(x.p)&&x.p>=0);
    const monthly=Array.isArray(m.time)&&Array.isArray(m.precipitation_mean)?m.time.map((time,i)=>({date:String(time).slice(0,10),p:m.precipitation_mean[i]})).filter(x=>finite(x.p)&&x.p>=0):[];
    if(!weekly.length)throw Error('ECMWF sem valores semanais válidos');
    return {weekly,monthly,unit:wu.precipitation_mean||'não informada',munit:mu.precipitation_mean||'não informada'};
  }
  function clear(id,msg){const x=$(id);if(!x)return;if(window.Plotly&&x.classList.contains('js-plotly-plot'))try{Plotly.purge(x);}catch(_){}x.textContent=msg;x.classList.add('is-empty');}
  function plot(id,traces,yUnit){const x=$(id);if(!x)return;
    if(!window.Plotly||!traces.length){clear(id,'Gráfico indisponível; informações no resumo.');return;}
    x.classList.remove('is-empty');Plotly.react(x,traces,{height:315,margin:{l:60,r:35,t:20,b:65},
      xaxis:{type:'category',title:'Período (início)',tickangle:-35},yaxis:{title:yUnit,rangemode:'tozero'},
      legend:{orientation:'h',y:-.28},paper_bgcolor:'rgba(0,0,0,0)',plot_bgcolor:'rgba(0,0,0,0)'},{responsive:true,displaylogo:false});
  }
  async function load(){const p=window.CampoLocation?.getPoint?.();if(!p||!$('extended-coordinate-status'))return;
    const token=++requestNo;
    if(window.CampoLocation?.isCustom?.()){
      $('extended-coordinate-status').textContent='Previsão estendida publicada é específica de Naviraí. Para '+key(p)+' não há EC46/GEFS validado neste site estático; a previsão de até 14 dias permanece personalizada. Nenhuma previsão de Naviraí será reutilizada.';
      $('extended-gefs-status').textContent='GEFS 15–35 dias não consultado para este ponto. Não representa ausência de chuva.';
      clear('extended-coordinate-plot','Sem tendência semanal validada para estas coordenadas.');clear('extended-gefs-plot','Sem cenários GEFS para este ponto.');$('extended-coordinate-monthly').textContent='';return;
    }
    $('extended-coordinate-status').textContent='Consultando apenas o arquivo público do Campo e Clima. Nenhuma chamada é feita à API sazonal.';
    try{
      const res=await fetch('data/latest.json?revision='+Date.now(),{cache:'no-store'});
      if(!res.ok)throw Error('Arquivo de coleta HTTP '+res.status);
      const data=await res.json();if(token!==requestNo)return;
      const ext=data?.complementary?.ecmwf_extended||{},gefs=data?.complementary?.gefs_extended||{};
      if(ext.state==='ok'&&ext.product==='weekly_ensemble_mean'&&Array.isArray(ext.weeks)&&ext.weeks.length){
        $('extended-coordinate-status').textContent=`✓ ECMWF EC46/SEAS5: ${ext.weeks.length} semanas publicadas. Coleta: ${ext.queried_at_utc||'não informada'} UTC; precipitação em ${ext.precipitation_unit||'unidade não informada'}. Médias do ensemble; NÃO frequência calibrada.`;
        plot('extended-coordinate-plot',[{type:'bar',x:ext.weeks.map(w=>w.start),y:ext.weeks.map(w=>w.rain_week_mean_api),name:'Precipitação média semanal',marker:{color:'#418dbe'},hovertemplate:'Semana %{x}<br>%{y:.1f} '+esc(ext.precipitation_unit||'unid.')+'<extra></extra>'}],`Média semanal (${ext.precipitation_unit||'unid.'})`);
        $('extended-coordinate-monthly').textContent=Array.isArray(ext.months)&&ext.months.length?`Contexto mensal separado: ${ext.months.map(m=>m.start+' → '+fmt(m.rain_month_mean_api)+' '+(ext.monthly_precipitation_unit||'')).join(' · ')}`:'Sem valores mensais válidos nesta publicação.';
      }else{
        $('extended-coordinate-status').textContent='ECMWF EC46/SEAS5 não disponível na coleta semanal: '+String(ext.error||ext.note||'Sem semanas completas').slice(0,160)+'. Não será requisitado novamente pelo navegador.';
        clear('extended-coordinate-plot','EC46 sem dados semanais válidos publicados.');$('extended-coordinate-monthly').textContent='';
      }
      if(gefs.state==='ok'&&Array.isArray(gefs.days)&&gefs.days.length){
        const days=gefs.days.filter(d=>finite(d.p50_mm));
        $('extended-gefs-status').textContent=`✓ NOAA GEFS estendido: ${days.length} dias entre D15–D35, ${gefs.member_count} membros de UM modelo (não multimodelo). Coleta ${gefs.queried_at_utc||'sem horário'} UTC. Frequências NÃO calibradas.`;
        plot('extended-gefs-plot',[
         {type:'scatter',mode:'lines',x:days.map(d=>d.date),y:days.map(d=>d.p10_mm),name:'P10',line:{color:'#accdde'}},
         {type:'scatter',mode:'lines',x:days.map(d=>d.date),y:days.map(d=>d.p90_mm),name:'P90',fill:'tonexty',fillcolor:'rgba(25,122,176,.17)',line:{color:'#85b9d8'}},
         {type:'scatter',mode:'lines+markers',x:days.map(d=>d.date),y:days.map(d=>d.p50_mm),name:'P50',line:{color:'#147aaa',width:3}}
        ],'Chuva GEFS (mm/dia)');
      }else{$('extended-gefs-status').textContent='GEFS 15–35 dias indisponível nesta coleta: '+String(gefs.error||gefs.note||'Sem membros válidos').slice(0,145)+'. Ausência de dados não significa tempo seco.';clear('extended-gefs-plot','Sem amostra diária GEFS validada.');}
    }catch(e){if(token!==requestNo)return;
      $('extended-coordinate-status').textContent='Não foi possível ler o arquivo publicado: '+String(e.message||e).slice(0,110);
      $('extended-gefs-status').textContent='Sem dados GEFS publicados nesta consulta.';clear('extended-coordinate-plot','Dados indisponíveis.');clear('extended-gefs-plot','Dados indisponíveis.');}
  }
  document.getElementById('tabs')?.addEventListener('click',ev=>{if(ev.target.closest('[data-tab="extended"]'))void load();});
  $('extended-refresh')?.addEventListener('click',()=>void load());
  window.addEventListener?.('campo:location-changed',()=>{requestNo++;if($('extended')?.classList.contains('active'))void load();});
  window.CampoExtendedV12={load,_test:{parse}};
})();
