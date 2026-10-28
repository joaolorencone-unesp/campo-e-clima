'use strict';
/* Daily published historical diagnostics for Naviraí. No borrowed station observations. */
(() => {
 const $=id=>document.getElementById(id);
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const valid=v=>typeof v==='number'&&Number.isFinite(v)&&v>=0;
 const fmt=v=>valid(v)?v.toFixed(1).replace('.',','):'—';
 function validate(x){
  if(!x||!['ok','stale','unavailable'].includes(x.state))throw Error('Estado inválido');
  if(Math.abs(Number(x.latitude)+23.065)>0.005||Math.abs(Number(x.longitude)+54.190)>0.005)throw Error('Histórico pertence a outro ponto');
  if(x.reference_day!=='UTC')throw Error('Histórico não está em dias UTC');
  if(!Array.isArray(x.rows))throw Error('Histórico sem registros');
  const seen=new Set();for(const r of x.rows){if(!/^\d{4}-\d{2}-\d{2}$/.test(r.date)||seen.has(r.date))throw Error('Datas inválidas');seen.add(r.date);}
  return x;
 }
 let busy=false,loaded=false;
 async function load(){
  const box=$('history-auto-status'),table=$('history-auto-table');if(!box||!table||busy)return;
  if(window.CampoLocation?.isCustom?.()){box.textContent='Histórico automático publicado somente para Naviraí. Consulte o histórico ERA5/NASA personalizado em Histórico & indicadores.';return;}
  busy=true;box.textContent='Consultando o arquivo histórico publicado (NASA POWER e ERA5)…';
  try{
   const response=await fetch('data/history_navirai.json',{cache:'no-cache'});if(!response.ok)throw Error('HTTP '+response.status);
   const hist=validate(await response.json());loaded=true;
   const rows=hist.rows.filter(r=>valid(r.era5_mm)||valid(r.nasa_mm)).slice(-31).reverse();
   const style=hist.state==='stale'?'warning':hist.state==='ok'?'':'muted';box.className='notice '+style;
   box.textContent=`${hist.state==='ok'?'✓ Histórico atualizado automaticamente':'⚠ Histórico incompleto/desatualizado'} · Naviraí · ${hist.start_date} a ${hist.end_date} (dias UTC). ERA5: ${hist.n_era5||0} dias; NASA POWER: ${hist.n_nasa||0}; coincidentes: ${hist.n_paired||0}. Última coleta: ${hist.issued_at_utc||'—'}. Estimativas em grade, NÃO medições das estações.`;
   const failures=Object.keys(hist.source_errors||{}).length?'Fonte(s) com falha: '+Object.keys(hist.source_errors).join(', ')+'. ':' ';
   $('history-auto-caveat').textContent=failures+'Séries modeladas podem divergir dos pluviômetros; não é avaliação da acurácia das previsões. Não usar valores ausentes como 0 mm.';
   table.innerHTML='<thead><tr><th>Data UTC</th><th>NASA POWER mm</th><th>ERA5 mm</th><th>Diferença NASA − ERA5 mm</th></tr></thead><tbody>'+rows.map(r=>`<tr><td>${esc(r.date)}</td><td>${fmt(r.nasa_mm)}</td><td>${fmt(r.era5_mm)}</td><td>${valid(r.nasa_mm)&&valid(r.era5_mm)?(r.nasa_mm-r.era5_mm).toFixed(1).replace('.',','):'—'}</td></tr>`).join('')+'</tbody>';
   const plot=$('history-auto-plot');if(plot&&window.Plotly&&rows.length){const x=rows.slice().reverse();
    Plotly.react(plot,[{type:'bar',name:'ERA5',x:x.map(r=>r.date),y:x.map(r=>r.era5_mm),marker:{color:'#327fae'}},{type:'bar',name:'NASA POWER',x:x.map(r=>r.date),y:x.map(r=>r.nasa_mm),marker:{color:'#e4a04e'}}],{barmode:'group',height:320,margin:{l:46,r:15,t:12,b:70},xaxis:{tickangle:-45},yaxis:{title:'Chuva em grade (mm/dia)'},legend:{orientation:'h',y:-.36},paper_bgcolor:'white',plot_bgcolor:'white'},{responsive:true,displaylogo:false});
   }else if(plot)plot.textContent=rows.length?'Gráfico indisponível; consulte os valores na tabela.':'Sem registros numéricos históricos.';
  }catch(e){box.className='notice warning';box.textContent='Histórico diário automatizado ainda não foi publicado ou não pôde ser lido. O histórico por coordenadas continua disponível na outra aba.';table.innerHTML='';}
  finally{busy=false;}
 }
 function bind(){document.getElementById('tabs')?.addEventListener('click',e=>{if(e.target.closest('[data-tab="observations"]')&&!loaded)void load();});window.addEventListener('campo:location-changed',()=>{if($('observations')?.classList.contains('active'))void load();});}
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
 window.CampoHistoryAuto={load,_test:{validate}};
})();
