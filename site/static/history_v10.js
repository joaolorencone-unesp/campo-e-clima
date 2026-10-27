'use strict';
/** Campo e Clima v1.0 — historical agronomy, all calculations based on retrieved data.
 * Operational data: Open-Meteo ERA5-Land reanalysis (daily UTC / hourly local),
 * NASA POWER UTC daily for comparison, and INMET station METADATA only.
 * No claim of validated spraying suitability or station-observed weather.
 */
(() => {
  const ARCHIVE = 'https://archive-api.open-meteo.com/v1/archive';
  const CACHE = new Map();
  const $ = id => document.getElementById(id);
  const finite = v => typeof v === 'number' && Number.isFinite(v);
  const fmt = (v, d=1) => finite(v) ? v.toFixed(d).replace('.', ',') : '—';
  const esc = v => String(v ?? '').replace(/[&<>"']/g, x => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[x]));
  const iso = d => d.toISOString().slice(0,10);
  const before = n => iso(new Date(Date.now() - n*86400000));
  const params = (url, data) => url + '?' + new URLSearchParams(data).toString();
  const dayFor = s => String(s).slice(0,10);
  const notice = (id,msg,style='muted') => { if($(id)) {$(id).className='notice '+style;$(id).textContent=msg;} };
  const numberOrNA = n => finite(n)?n:null;
  let currentPoint=null, generation=0, nasa=null, daily=null, hourly=null, lastRows=[], loadedPoint='', currentDays=90;
  function pairKey(p){return `${Number(p.latitude).toFixed(5)},${Number(p.longitude).toFixed(5)}`;}
  function changePoint(p){
    if(!p || !finite(Number(p.latitude)) || !finite(Number(p.longitude)))return;
    const k=pairKey(p); if(k===loadedPoint)return;
    loadedPoint=k; currentPoint=p; generation++; nasa=null; daily=null; hourly=null; lastRows=[];
    ['hist-daily-plot','hist-compare-plot','hist-spray-plot'].forEach(id=>{try{clearPlot(id,'Selecione o histórico deste ponto.');}catch(_){}});
    notice('hist-status','Pronto para consultar o histórico ERA5-Land do novo ponto (não é uma estação meteorológica).');
    notice('hist-spray-status','Pré-triagem histórica só será calculada com dados horários completos, após a consulta.');
    $('hist-table').innerHTML=''; $('hist-kpis').innerHTML='';$('hist-station-table').innerHTML='';
    if(document.querySelector('#history-nasa')?.classList.contains('active')) void load();
    void loadStations(p,generation);
  }
  async function fetchJSON(url,seconds=60){
    const ctrl=new AbortController(),timer=setTimeout(()=>ctrl.abort(),seconds*1000);
    try{const r=await fetch(url,{signal:ctrl.signal,cache:'no-store'});if(!r.ok)throw Error('HTTP '+r.status);const x=await r.json();if(x?.error)throw Error(x.reason||'Resposta API com erro');return x;}finally{clearTimeout(timer);}
  }
  function parseDaily(payload){
    const d=payload?.daily||{};const dates=d.time;
    if(!Array.isArray(dates)||dates.length<10||!Array.isArray(d.precipitation_sum)||d.precipitation_sum.length!==dates.length)throw Error('Arquivo histórico sem datas e chuva consistentes');
    if(payload.timezone!=='GMT' && payload.timezone!=='UTC' && payload.utc_offset_seconds!==0)throw Error('Esperado histórico em UTC');
    const values=['precipitation_sum','temperature_2m_mean','temperature_2m_max','temperature_2m_min','wind_speed_10m_max','wind_gusts_10m_max','et0_fao_evapotranspiration','shortwave_radiation_sum'];
    const seen=new Set();return dates.map((date,i)=>{
      if(seen.has(date))throw Error('Data repetida no histórico: '+date);seen.add(date);
      const row={date};for(const k of values){const v=d[k]?.[i];row[k]=numberOrNA(v);}
      if(row.precipitation_sum!==null && (row.precipitation_sum<0||row.precipitation_sum>1000))row.precipitation_sum=null;
      return row;
    });
  }
  function parseHourly(payload){
    const h=payload?.hourly||{},dates=h.time||[];
    if(!Array.isArray(dates)||dates.length<24)throw Error('Histórico horário indisponível');
    const names=['temperature_2m','relative_humidity_2m','vapour_pressure_deficit','wind_speed_10m','wind_gusts_10m','precipitation'];
    if(names.some(k=>!Array.isArray(h[k])||h[k].length!==dates.length))throw Error('Faltam variáveis horárias essenciais: a classificação não pode ser calculada');
    return dates.map((stamp,i)=>Object.fromEntries([['time',stamp],...names.map(k=>[k,numberOrNA(h[k][i])])]));
  }
  /** Only a retrospective METEOROLOGICAL SCREEN. Never labels a pesticide operation safe. */
  function screenHour(row){
    const hour=Number(row.time.slice(11,13));
    if(!Number.isInteger(hour)||hour<7||hour>=18)return 'fora_periodo_diurno';
    const {temperature_2m:t,relative_humidity_2m:rh,wind_speed_10m:wind,wind_gusts_10m:gust,precipitation:rain}=row;
    const vpd=finite(row.vapour_pressure_deficit) ? row.vapour_pressure_deficit : (finite(t)&&finite(rh)?0.6108*Math.exp(17.27*t/(t+237.3))*(1-rh/100):null);
    const valid=[t,rh,wind,gust,rain,vpd].every(finite);
    if(!valid)return 'indeterminado';
    if(t>=30||rh<=55||wind<3||wind>10||gust>20||rain>0.1||vpd>=1.2)return 'restritivo';
    if(t>=28||rh<60||wind>8||gust>15||vpd>=1.0)return 'marginal';
    return 'candidato'; // even candidates require in-field verification of inversion/drift/label
  }
  function screenDays(rows){
    const byDate=new Map();for(const row of rows){const day=dayFor(row.time),label=screenHour(row);if(label==='fora_periodo_diurno')continue;
      const counts=byDate.get(day)||{date:day,candidato:0,marginal:0,restritivo:0,indeterminado:0,total:0};counts[label]++;counts.total++;byDate.set(day,counts);
    }
    return [...byDate.values()].filter(d=>d.total>=10);
  }
  function pairedSummary(nasaRecords,archiveRows){
    const map=new Map((nasaRecords||[]).filter(r=>finite(r.PRECTOTCORR)).map(r=>[r.date,r.PRECTOTCORR]));
    const pairs=archiveRows.filter(r=>finite(r.precipitation_sum)&&map.has(r.date)).map(r=>({date:r.date,nasa:map.get(r.date),era:r.precipitation_sum}));
    if(!pairs.length)return {pairs:[],n:0,meanDifference:null,meanAbsDifference:null,correlation:null};
    const delta=pairs.map(r=>r.nasa-r.era);const n=pairs.length;
    const diff=delta.reduce((s,x)=>s+x,0)/n, abs=delta.reduce((s,x)=>s+Math.abs(x),0)/n;
    const xa=pairs.map(p=>p.nasa),ya=pairs.map(p=>p.era),mx=xa.reduce((s,x)=>s+x,0)/n,my=ya.reduce((s,x)=>s+x,0)/n;
    const co=xa.reduce((s,x,i)=>s+(x-mx)*(ya[i]-my),0),sx=Math.sqrt(xa.reduce((s,x)=>s+(x-mx)**2,0)),sy=Math.sqrt(ya.reduce((s,x)=>s+(x-my)**2,0));
    return {pairs,n,meanDifference:diff,meanAbsDifference:abs,correlation:sx>0&&sy>0?co/sx/sy:null};
  }
  function drawHistory(){
    if(!daily)return;
    const series=daily.slice(-currentDays),dates=series.map(r=>r.date);
    chart('hist-daily-plot',[
      {type:'bar',x:dates,y:series.map(r=>r.precipitation_sum),name:'Chuva ERA5-Land',marker:{color:'#2586b5'},hovertemplate:'%{x}<br>Chuva: %{y:.1f} mm<extra></extra>'},
    ],'Chuva (mm/dia)',{height:365});
    const comparison=pairedSummary(nasa?.records||[],series);
    if(comparison.n>=10){
      chart('hist-compare-plot',[
        {type:'scatter',mode:'lines',x:comparison.pairs.map(r=>r.date),y:comparison.pairs.map(r=>r.nasa),name:'NASA POWER (UTC)',line:{color:'#d38b3a',width:2.0}},
        {type:'scatter',mode:'lines',x:comparison.pairs.map(r=>r.date),y:comparison.pairs.map(r=>r.era),name:'ERA5-Land (UTC)',line:{color:'#257cae',width:2.2}}
      ],'Chuva diária (mm)',{height:365});
    }else clearPlot('hist-compare-plot','Comparação ainda sem pelo menos dez datas comuns NASA × ERA5-Land em UTC.');
    const prev=series.filter(r=>finite(r.precipitation_sum));
    const rain=prev.reduce((s,r)=>s+r.precipitation_sum,0),wet=prev.filter(r=>r.precipitation_sum>=1).length;
    const vals=k=>series.map(r=>r[k]).filter(finite),mean=v=>v.length?v.reduce((s,x)=>s+x,0)/v.length:null;
    const t=mean(vals('temperature_2m_mean')),et0=vals('et0_fao_evapotranspiration').reduce((s,x)=>s+x,0),gust=vals('wind_gusts_10m_max');
    $('hist-kpis').innerHTML=`<div class="nasa-summary-grid"><div><small>Chuva ERA5-Land · ${prev.length} dias completos</small><strong>${fmt(rain)} mm</strong></div><div><small>Dias com chuva ≥1 mm</small><strong>${wet} dias</strong></div><div><small>Temperatura média da série</small><strong>${fmt(t)} °C</strong></div><div><small>ET₀ acumulada*</small><strong>${fmt(et0)} mm</strong></div><div><small>Maior rajada diária na grade</small><strong>${fmt(gust.length?Math.max(...gust):null)} km/h</strong></div><div><small>Comparação NASA × ERA5</small><strong>${comparison.n} dias</strong></div></div>`;
    const screen=hourly?screenDays(hourly):[];
    const byScreen=new Map(screen.map(s=>[s.date,s]));
    const tableRows=series.slice().reverse().slice(0,Math.min(currentDays,120)).map(r=>{
      const cmp=comparison.pairs.find(p=>p.date===r.date);const nvalue=(nasa?.records||[]).find(p=>p.date===r.date)?.PRECTOTCORR;const sc=byScreen.get(r.date);
      return `<tr><td>${esc(r.date)}</td><td>${fmt(r.precipitation_sum)}</td><td>${fmt(nvalue)}</td><td>${fmt(r.temperature_2m_max)}</td><td>${fmt(r.temperature_2m_min)}</td><td>${fmt(r.et0_fao_evapotranspiration)}</td><td>${fmt(r.wind_gusts_10m_max)}</td><td>${sc?`${sc.candidato}/${sc.total} h*`:'—'}</td></tr>`;
    });
    tableFill('hist-table',['Data UTC¹','ERA5 chuva mm','NASA chuva mm','T máx °C','T mín °C','ET₀ mm','Rajada máx km/h','Horas pré-triagem²'],tableRows);
    if(comparison.n>=10)notice('hist-compare-status',`${comparison.n} dias UTC comparados. Diferença média NASA − ERA5: ${fmt(comparison.meanDifference)} mm/dia; diferença absoluta média: ${fmt(comparison.meanAbsDifference)} mm/dia; correlação: ${fmt(comparison.correlation,2)}. CONCORDÂNCIA ENTRE PRODUTOS, não acurácia medida em estação.`, 'muted');
    else notice('hist-compare-status','Comparação NASA/ERA5 ainda sem dias simultâneos suficientes. São duas estimativas em grade, não observações independentes de pluviômetro.');
    notice('hist-status',`✓ Open-Meteo Historical Weather: ${daily.length} dias UTC recebidos, modelo ERA5-Land. Os ${series.length} últimos dias estão representados nos gráficos e tabela. Atraso de disponibilidade: cerca de 5 dias.`, 'muted');
    redrawActive();
  }
  function drawScreen(){
    const days=hourly?screenDays(hourly):[];
    if(!days.length){notice('hist-spray-status','Sem série horária completa: não há índice histórico confiável.');clearPlot('hist-spray-plot','Dados horários não disponíveis.');return;}
    const totals=days.reduce((a,r)=>(Object.keys(a).forEach(k=>a[k]+=r[k]),a),{candidato:0,marginal:0,restritivo:0,indeterminado:0,total:0});
    const pct=x=>totals.total?Math.round(100*totals[x]/totals.total):0;
    chart('hist-spray-plot',[{type:'bar',x:days.map(d=>d.date),y:days.map(d=>d.candidato),name:'Passam na pré-triagem*',marker:{color:'#3aab83'}},{type:'bar',x:days.map(d=>d.date),y:days.map(d=>d.marginal),name:'Marginal',marker:{color:'#e1b057'}},{type:'bar',x:days.map(d=>d.date),y:days.map(d=>d.restritivo),name:'Restritiva',marker:{color:'#d66b72'}},{type:'bar',x:days.map(d=>d.date),y:days.map(d=>d.indeterminado),name:'Indeterminada',marker:{color:'#b5bfca'}}], 'Horas diurnas/dia',{barmode:'stack',height:365});
    notice('hist-spray-status',`✓ Análise retrospectiva de ${days.length} dias com ${totals.total} horas diurnas (07–17h locais): ${pct('candidato')}% passaram nos filtros; ${pct('marginal')}% marginais; ${pct('restritivo')}% restritivas; ${pct('indeterminado')}% indeterminadas. Números são FREQUÊNCIAS HISTÓRICAS, não probabilidades futuras nem aprovação de pulverização.`, 'muted');
    drawHistory();
  }
  async function load(opts={}){
    const p=window.CampoLocation?.getPoint?.();if(!p)return;
    if(pairKey(p)!==loadedPoint)changePoint(p);
    const token=++generation;currentPoint=p;currentDays=Number($('hist-period')?.value)||90;
    const end=before(8), start=before(currentDays+8);
    const key=pairKey(p)+'|'+start+'|'+end;
    notice('hist-status','Consultando Open-Meteo Historical Weather / ERA5-Land. Dados históricos levam cerca de 5 dias para ficar disponíveis.');
    try{
      const cached=CACHE.get(key);const c=cached&&Date.now()-cached.saved<12*3600000?cached:null;
      const fields='precipitation_sum,temperature_2m_mean,temperature_2m_max,temperature_2m_min,wind_speed_10m_max,wind_gusts_10m_max,et0_fao_evapotranspiration,shortwave_radiation_sum';
      let d;
      if(c)d=c.payload;else{
        let url=params(ARCHIVE,{latitude:p.latitude,longitude:p.longitude,start_date:start,end_date:end,timezone:'UTC',models:'era5_land',daily:fields});
        try{d=await fetchJSON(url,55);}catch(e){
          url=params(ARCHIVE,{latitude:p.latitude,longitude:p.longitude,start_date:start,end_date:end,timezone:'UTC',models:'era5_land',daily:'precipitation_sum,temperature_2m_mean,temperature_2m_max,temperature_2m_min'});
          d=await fetchJSON(url,55);
        }
        CACHE.set(key,{saved:Date.now(),payload:d});
      }
      if(token!==generation)return;
      daily=parseDaily(d);drawHistory();
      // Hourly spray analysis is deliberately capped at 31 days to limit free API use.
      if(!hourly || opts.force){void loadHourly(p,token);}
    }catch(e){if(token!==generation)return;daily=null;const msg=e.name==='AbortError'?'Tempo limite excedido':String(e.message||e).slice(0,140);notice('hist-status','Histórico ERA5-Land indisponível: '+msg,'warning');clearPlot('hist-daily-plot','Não há histórico diário válido.');clearPlot('hist-compare-plot','Sem dados comparáveis.');$('hist-kpis').innerHTML='';$('hist-table').innerHTML='';}
  }
  async function loadHourly(p,token){
    notice('hist-spray-status','Consultando até 31 dias horários da reanálise ERA5-Land (hora local).');
    const end=before(8),start=before(39);let lastErr=null;
    for(const model of ['era5_land','era5']){
      try{
        const url=params(ARCHIVE,{latitude:p.latitude,longitude:p.longitude,start_date:start,end_date:end,timezone:'auto',models:model,hourly:'temperature_2m,relative_humidity_2m,vapour_pressure_deficit,wind_speed_10m,wind_gusts_10m,precipitation'});
        const d=await fetchJSON(url,50);
        if(token!==generation)return;
        hourly=parseHourly(d);drawScreen();return;
      }catch(e){lastErr=e;}
    }
    if(token===generation){hourly=null;notice('hist-spray-status','Pré-triagem histórica indisponível: '+String(lastErr?.message||lastErr).slice(0,120),'warning');clearPlot('hist-spray-plot','Faltam variáveis horárias da reanálise.');}
  }
  function receiveNASA(data){const p=window.CampoLocation?.getPoint?.();if(!p||!data||!data.records||pairKey(p)!==pairKey({latitude:data.lat,longitude:data.lon}))return;nasa=data;if(daily)drawHistory();}
  const haversine=(a,b,c,d)=>{const r=Math.PI/180,x=(c-a)*r,y=(d-b)*r,p=2*Math.asin(Math.min(1,Math.sqrt(Math.sin(x/2)**2+Math.cos(a*r)*Math.cos(c*r)*Math.sin(y/2)**2)));return 6371.009*p;};
  async function loadStations(p,token){
    try{
      const doc=await fetchJSON('data/inmet_stations.json?v=10',15);
      if(pairKey(window.CampoLocation?.getPoint?.()||p)!==pairKey(p))return;
      if(doc.state!=='ok'||!Array.isArray(doc.stations))throw Error(doc.error||'Catálogo indisponível');
      const stations=doc.stations.map(s=>({...s,distance:haversine(p.latitude,p.longitude,s.latitude,s.longitude)})).sort((a,b)=>a.distance-b.distance).slice(0,6);
      $('hist-station-table').innerHTML='<thead><tr><th>Estação</th><th>Código</th><th>Distância</th><th>Situação</th></tr></thead><tbody>'+stations.map(s=>`<tr><td>${esc(s.name)}</td><td>${esc(s.code)}</td><td>${fmt(s.distance)} km</td><td>${esc(s.status||'Não informado')}</td></tr>`).join('')+'</tbody>';
      notice('hist-station-status',`✓ Catálogo INMET: ${doc.stations.length} estações em inventário. Atualizado em ${doc.collected_at_utc||'data não informada'}. Lista com metadados; NÃO são medições meteorológicas.`);
    }catch(e){if(pairKey(window.CampoLocation?.getPoint?.()||p)!==pairKey(p))return;notice('hist-station-status','Estações INMET indisponíveis neste ponto: '+String(e.message||e).slice(0,100),'warning');$('hist-station-table').innerHTML='';}
  }
  function downloadCSV(){if(!daily){notice('hist-status','Sem dados históricos para exportar.','warning');return;}
    const header=['date','era5_precipitation_mm','nasa_precipitation_mm','temp_mean_c','temp_max_c','temp_min_c','wind_max_kmh','gust_max_kmh','et0_mm'];
    const nasaMap=new Map((nasa?.records||[]).map(r=>[r.date,r.PRECTOTCORR]));
    const rows=daily.slice(-currentDays).map(r=>[r.date,r.precipitation_sum,nasaMap.get(r.date),r.temperature_2m_mean,r.temperature_2m_max,r.temperature_2m_min,r.wind_speed_10m_max,r.wind_gusts_10m_max,r.et0_fao_evapotranspiration].map(v=>v==null?'':String(v)).join(','));
    const csv='\ufeff'+header.join(',')+'\n'+rows.join('\n');const blob=new Blob([csv],{type:'text/csv;charset=utf-8'});const href=URL.createObjectURL(blob),a=document.createElement('a');a.href=href;a.download=`Campo_e_Clima_Historico_${pairKey(currentPoint)}_${currentDays}dias.csv`;document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(href);
  }
  $('hist-period')?.addEventListener('change',()=>void load());
  $('hist-reload')?.addEventListener('click',()=>void load({force:true}));
  $('hist-export')?.addEventListener('click',downloadCSV);
  $('tabs')?.addEventListener('click',e=>{if(e.target.closest('[data-tab="history-nasa"]'))void load();});
  window.addEventListener?.('campo:location-changed',e=>changePoint(e.detail));
  window.addEventListener?.('campo:nasa-loaded',e=>receiveNASA(e.detail));
  window.CampoHistoryV10={load,_test:{parseDaily,parseHourly,screenHour,screenDays,pairedSummary,haversine}};
  changePoint(window.CampoLocation?.getPoint?.());
})();
