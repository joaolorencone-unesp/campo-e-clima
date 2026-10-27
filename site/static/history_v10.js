'use strict';
/** Campo e Clima v1.2 — historical agronomy, all calculations based on retrieved data.
 * Operational data: ERA5 atmosphere + ERA5-Land surface reanalysis (daily UTC / hourly local),
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
  const numberOrNA = n => finite(n) && n !== -9999 ? n : null;
  let currentPoint=null, generation=0, nasa=null, daily=null, hourly=null, lastRows=[], loadedPoint='', currentDays=90, historySource='ERA5';
  function pairKey(p){return `${Number(p.latitude).toFixed(5)},${Number(p.longitude).toFixed(5)}`;}
  function changePoint(p){
    if(!p || !finite(Number(p.latitude)) || !finite(Number(p.longitude)))return;
    const k=pairKey(p); if(k===loadedPoint)return;
    loadedPoint=k; currentPoint=p; generation++; nasa=null; daily=null; hourly=null; lastRows=[];
    ['hist-daily-plot','hist-compare-plot','hist-spray-plot'].forEach(id=>{try{clearPlot(id,'Selecione o histórico deste ponto.');}catch(_){}});
    notice('hist-status','Pronto para consultar o histórico ERA5 + ERA5-Land do novo ponto (não é uma estação meteorológica).');
    notice('hist-spray-status','Pré-triagem histórica só será calculada com dados horários completos, após a consulta.');
    $('hist-table').innerHTML=''; $('hist-kpis').innerHTML='';$('hist-station-table').innerHTML='';
    if(document.querySelector('#history-nasa')?.classList.contains('active')) void load();
    void loadStations(p,generation);
  }
  async function fetchJSON(url,seconds=60){
    const ctrl=new AbortController(),timer=setTimeout(()=>ctrl.abort(),seconds*1000);
    try{const r=await fetch(url,{signal:ctrl.signal,cache:'no-store'});if(!r.ok)throw Error('HTTP '+r.status);const x=await r.json();if(x?.error)throw Error(x.reason||'Resposta API com erro');return x;}finally{clearTimeout(timer);}
  }
  function parseDaily(payload, allowMissingRain=false){
    const d=payload?.daily||{};const dates=d.time;
    if(!Array.isArray(dates)||dates.length<10||!Array.isArray(d.precipitation_sum)||d.precipitation_sum.length!==dates.length)throw Error('Arquivo histórico sem datas e chuva consistentes');
    if(payload.timezone!=='GMT' && payload.timezone!=='UTC' && payload.utc_offset_seconds!==0)throw Error('Esperado histórico em UTC');
    // HTTP 200 with all null precipitation is not a valid rainfall dataset.
    if(!d.precipitation_sum.some(v=>finite(v)&&v>=0)&&!allowMissingRain)throw Error('Fonte histórica retornou chuva nula em todos os dias; testar ERA5');
    if(allowMissingRain && !d.precipitation_sum.some(v=>finite(v)&&v>=0) && !['temperature_2m_mean','temperature_2m_max','temperature_2m_min'].some(k=>Array.isArray(d[k])&&d[k].some(finite)))throw Error('Nem chuva nem temperatura numérica disponível');
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
  /** Align ERA5 atmospheric and ERA5-Land surface fields by exact timestamps.
   * Never silently shift a day or use an array from a different grid/time index.
   */
  function mergeDailyBaseLand(base,land){
    const a=base?.daily||{},b=land?.daily||{};
    if(!Array.isArray(a.time)||!Array.isArray(b.time)||a.time.length!==b.time.length||a.time.some((t,i)=>t!==b.time[i]))throw Error('Grades temporais de ERA5 e ERA5-Land não coincidem');
    if(base.utc_offset_seconds!==land.utc_offset_seconds)throw Error('Fusos históricos incompatíveis');
    const o={...base,daily:{...a}};
    const n=a.time.length;
    for(const key of ['wind_gusts_10m_max','et0_fao_evapotranspiration']){
      if(Array.isArray(b[key])&&b[key].length===n && b[key].some(finite))o.daily[key]=b[key].map(numberOrNA);
    }
    return o;
  }
  function mergeHourlyBaseLand(base,land){
    const a=base?.hourly||{},b=land?.hourly||{};
    if(!Array.isArray(a.time)||!Array.isArray(b.time)||a.time.length!==b.time.length||a.time.some((t,i)=>t!==b.time[i]))throw Error('Horários ERA5/ERA5-Land divergentes');
    const o={...base,hourly:{...a}};
    const gust=b.wind_gusts_10m;
    if(Array.isArray(gust)&&gust.length===a.time.length&&gust.some(finite))o.hourly.wind_gusts_10m=gust.map(numberOrNA);
    return o;
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
    const hasArchiveRain=series.some(r=>finite(r.precipitation_sum));
    const nasaLookup=new Map((nasa?.records||[]).filter(r=>finite(r.PRECTOTCORR)).map(r=>[r.date,r.PRECTOTCORR]));
    chart('hist-daily-plot',[
      {type:'bar',x:dates,y:series.map(r=>hasArchiveRain?r.precipitation_sum:(nasaLookup.get(r.date)??null)),name:hasArchiveRain?'Chuva '+historySource:'Chuva NASA POWER (ERA5 indisponível)',marker:{color:'#2586b5'},hovertemplate:'%{x}<br>Chuva: %{y:.1f} mm<extra></extra>'},
    ],'Chuva (mm/dia)',{height:365});
    const comparison=pairedSummary(nasa?.records||[],series);
    if(comparison.n>=10){
      chart('hist-compare-plot',[
        {type:'scatter',mode:'lines',x:comparison.pairs.map(r=>r.date),y:comparison.pairs.map(r=>r.nasa),name:'NASA POWER (UTC)',line:{color:'#d38b3a',width:2.0}},
        {type:'scatter',mode:'lines',x:comparison.pairs.map(r=>r.date),y:comparison.pairs.map(r=>r.era),name:'ERA5 (UTC)',line:{color:'#257cae',width:2.2}}
      ],'Chuva diária (mm)',{height:365});
    }else clearPlot('hist-compare-plot','Comparação ainda sem pelo menos dez datas comuns NASA × ERA5 em UTC.');
    const prev=series.filter(r=>finite(r.precipitation_sum));
    const nasaAvail=series.map(r=>nasaLookup.get(r.date)).filter(finite);
    const nasaTotal=nasaAvail.length?nasaAvail.reduce((a,b)=>a+b,0):null;
    const rain=prev.reduce((s,r)=>s+r.precipitation_sum,0),wet=prev.filter(r=>r.precipitation_sum>=1).length;
    const vals=k=>series.map(r=>r[k]).filter(finite),mean=v=>v.length?v.reduce((s,x)=>s+x,0)/v.length:null;
    const etValues=vals('et0_fao_evapotranspiration');const t=mean(vals('temperature_2m_mean')),et0=etValues.length?etValues.reduce((s,x)=>s+x,0):null,gust=vals('wind_gusts_10m_max');
    $('hist-kpis').innerHTML=`<div class="nasa-summary-grid"><div><small>Chuva ${esc(historySource)} · ${prev.length} dias válidos</small><strong>${prev.length?fmt(rain)+' mm':'Sem dados'}</strong></div><div><small>Dias com chuva ≥1 mm</small><strong>${prev.length?wet+' dias':'Sem dados'}</strong></div><div><small>Temperatura média da série</small><strong>${fmt(t)} °C</strong></div><div><small>ET₀ acumulada*</small><strong>${finite(et0)?fmt(et0)+' mm':'Sem dados'}</strong></div><div><small>Maior rajada diária na grade</small><strong>${fmt(gust.length?Math.max(...gust):null)} km/h</strong></div><div><small>Chuva NASA · ${nasaAvail.length} dias</small><strong>${nasaTotal===null?'Sem dados':fmt(nasaTotal)+' mm'}</strong></div></div>`;
    const screen=hourly?screenDays(hourly):[];
    const byScreen=new Map(screen.map(s=>[s.date,s]));
    const tableRows=series.slice().reverse().slice(0,Math.min(currentDays,120)).map(r=>{
      const cmp=comparison.pairs.find(p=>p.date===r.date);const nvalue=(nasa?.records||[]).find(p=>p.date===r.date)?.PRECTOTCORR;const sc=byScreen.get(r.date);
      return `<tr><td>${esc(r.date)}</td><td>${fmt(r.precipitation_sum)}</td><td>${fmt(nvalue)}</td><td>${fmt(r.temperature_2m_max)}</td><td>${fmt(r.temperature_2m_min)}</td><td>${fmt(r.et0_fao_evapotranspiration)}</td><td>${fmt(r.wind_gusts_10m_max)}</td><td>${sc?`${sc.candidato}/${sc.total} h*`:'—'}</td></tr>`;
    });
    tableFill('hist-table',['Data UTC¹','ERA5 chuva mm','NASA chuva mm','T máx °C','T mín °C','ET₀ mm','Rajada máx km/h','Horas pré-triagem²'],tableRows);
    if(comparison.n>=10)notice('hist-compare-status',`${comparison.n} dias UTC comparados. Diferença média NASA − ERA5: ${fmt(comparison.meanDifference)} mm/dia; diferença absoluta média: ${fmt(comparison.meanAbsDifference)} mm/dia; correlação: ${fmt(comparison.correlation,2)}. CONCORDÂNCIA ENTRE PRODUTOS, não acurácia medida em estação.`, 'muted');
    else notice('hist-compare-status','Comparação NASA/ERA5 ainda sem dias simultâneos suficientes. São duas estimativas em grade, não observações independentes de pluviômetro.');
    notice('hist-status',`${prev.length?'✓':'⚠️'} Open-Meteo Historical Weather: ${daily.length} datas UTC; chuva ${historySource}: ${prev.length} dias com valor válido; temperatura ${vals('temperature_2m_mean').length} dias. ${prev.length===0?'A chuva mostrada no gráfico, quando disponível, é exclusivamente NASA POWER — não ERA5.':'Precipitação e temperaturas são reanálises, não pluviômetros.'} Atraso e cobertura dependem do produto.`, prev.length?'muted':'warning');
    redrawActive();
  }
  function drawNASAOnly(){
    if(daily||!Array.isArray(nasa?.records))return;
    const records=nasa.records.filter(r=>finite(r.PRECTOTCORR)).slice(-currentDays);
    if(!records.length)return;
    chart('hist-daily-plot',[{type:'bar',x:records.map(r=>r.date),y:records.map(r=>r.PRECTOTCORR),name:'NASA POWER • estimativa em grade',marker:{color:'#2586b5'}}],'Chuva NASA POWER (mm/dia)',{height:365});
    $('hist-kpis').innerHTML=`<div class="nasa-summary-grid"><div><small>NASA POWER · ${records.length} datas</small><strong>${fmt(records.reduce((a,r)=>a+r.PRECTOTCORR,0))} mm</strong></div><div><small>ERA5</small><strong>Indisponível</strong></div><div><small>Verificação</small><strong>Não é pluviômetro</strong></div></div>`;
    tableFill('hist-table',['Data UTC','NASA chuva mm'],records.slice().reverse().map(r=>`<tr><td>${esc(r.date)}</td><td>${fmt(r.PRECTOTCORR)}</td></tr>`));
    notice('hist-status',`Histórico ERA5 sem série numérica completa. Exibindo somente NASA POWER: ${records.length} dias, estimativa em grade. Não foi atribuído zero às variáveis ausentes.`,'warning');
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
    notice('hist-status','Consultando histórico: chuva, vento e temperatura ERA5; ET₀ e rajadas ERA5-Land. Valores nulos não são convertidos em zero.');
    try{
      const cached=CACHE.get(key);const c=cached&&Date.now()-cached.saved<12*3600000?cached:null;
      let d;
      if(c){d=c.payload;historySource=c.source||'ERA5';}
      else{
        const at={latitude:p.latitude,longitude:p.longitude,start_date:start,end_date:end,timezone:'UTC'};
        const baseFields='precipitation_sum,temperature_2m_mean,temperature_2m_max,temperature_2m_min,wind_speed_10m_max,shortwave_radiation_sum';
        let base;
        try{base=await fetchJSON(params(ARCHIVE,{...at,models:'era5',daily:baseFields}),55);}
        catch(_){base=await fetchJSON(params(ARCHIVE,{...at,models:'era5',daily:'precipitation_sum,temperature_2m_max,temperature_2m_min'}),55);}
        if(token!==generation)return;
        // Verify NUMERIC rain, not HTTP status. Some archive products may return
        // temperatures and an all-null rain array. Try another documented model.
        let source='ERA5';
        try{parseDaily(base);}catch(err){
          try{
            const backup=await fetchJSON(params(ARCHIVE,{...at,models:'best_match',daily:'precipitation_sum,temperature_2m_mean,temperature_2m_max,temperature_2m_min,wind_speed_10m_max'}),40);
            parseDaily(backup);
            base=backup;source='Open-Meteo best_match';
          }catch(_){
            // Preserve valid temperature without inventing precipitation.
            parseDaily(base,true);source='ERA5 (chuva indisponível)';
          }
        }
        historySource=source;
        d=base;
        try{
          const surface=await fetchJSON(params(ARCHIVE,{...at,models:'era5_land',daily:'wind_gusts_10m_max,et0_fao_evapotranspiration'}),45);
          if(token!==generation)return;
          d=mergeDailyBaseLand(base,surface);
        }catch(err){notice('hist-status','ERA5 atmosférico disponível; complementação ERA5-Land ET₀/rajadas indisponível: '+String(err.message||err).slice(0,95),'warning');}
        CACHE.set(key,{saved:Date.now(),payload:d,source:historySource});
      }
      if(token!==generation)return;
      daily=parseDaily(d,true);drawHistory();
      if(!hourly || opts.force)void loadHourly(p,token);
    }catch(e){if(token!==generation)return;daily=null;const msg=e.name==='AbortError'?'Tempo limite excedido':String(e.message||e).slice(0,140);notice('hist-status','Histórico atmosférico ERA5 indisponível: '+msg,'warning');clearPlot('hist-daily-plot','Não há chuva diária válida.');clearPlot('hist-compare-plot','Sem dados comparáveis.');$('hist-kpis').innerHTML='';$('hist-table').innerHTML='';drawNASAOnly();}
  }
  async function loadHourly(p,token){
    notice('hist-spray-status','Consultando 31 dias horários: ERA5 atmosférico + ERA5-Land rajadas (hora local).');
    const end=before(8),start=before(39);
    try{
      const at={latitude:p.latitude,longitude:p.longitude,start_date:start,end_date:end,timezone:'auto'};
      const base=await fetchJSON(params(ARCHIVE,{...at,models:'era5',hourly:'temperature_2m,relative_humidity_2m,vapour_pressure_deficit,wind_speed_10m,precipitation'}),50);
      if(token!==generation)return;
      let d=base;
      try{
        const surface=await fetchJSON(params(ARCHIVE,{...at,models:'era5_land',hourly:'wind_gusts_10m'}),45);
        if(token!==generation)return;
        d=mergeHourlyBaseLand(base,surface);
      }catch(_){/* Essential gust unavailable => classify affected hours as indeterminate. */}
      hourly=parseHourly(d);
      if(!hourly.some(r=>[r.wind_gusts_10m,r.wind_speed_10m,r.precipitation].every(finite)))throw Error('Sem dados conjuntos horários de rajada, vento e chuva');
      drawScreen();
    }catch(e){if(token!==generation)return;hourly=null;notice('hist-spray-status','Pré-triagem histórica indisponível: '+String(e.message||e).slice(0,130),'warning');clearPlot('hist-spray-plot','Faltam variáveis horárias conjuntas.');}
  }
  function receiveNASA(data){const p=window.CampoLocation?.getPoint?.();if(!p||!data||!data.records||pairKey(p)!==pairKey({latitude:data.lat,longitude:data.lon}))return;nasa=data;if(daily)drawHistory();else drawNASAOnly();}
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
  window.CampoHistoryV10={load,_test:{parseDaily,parseHourly,mergeDailyBaseLand,mergeHourlyBaseLand,screenHour,screenDays,pairedSummary,haversine}};
  changePoint(window.CampoLocation?.getPoint?.());
})();
