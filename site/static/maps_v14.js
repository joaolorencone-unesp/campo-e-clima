'use strict';
/** Campo e Clima 2.0 • free scientific maps; NASA GIBS is observed imagery,
 * Open-Meteo gridded forecast is a distinct forecast product.
 * No NASA/Google/OpenWeather secret is needed or embedded in this code.
 */
(function(){
 const el=id=>document.getElementById(id);
 const GRID_OFFSETS=[-0.4,0,0.4],POINT_COUNT=9,HOURS=48;
 const VARIABLES=['cloud_cover','cloud_cover_low','cloud_cover_mid','cloud_cover_high','precipitation','precipitation_probability','temperature_2m','relative_humidity_2m','wind_speed_10m','wind_gusts_10m','wind_direction_10m','cape'];
 const IMAGE_LAYERS=new Set(['MODIS_Terra_CorrectedReflectance_TrueColor','VIIRS_NOAA20_CorrectedReflectance_TrueColor']);
 let map=null,selectedMarker=null,weatherLayer=null,imageLayer=null,forecast=null,pointKey=null,lastAt=0;
 let hourIndex=0,requestId=0,playing=null,imageLoaded=0,imageErrors=0;
 let radarTile=null,radarFrames=[],radarHost="",radarIndex=0,radarTimer=null,radarFetchedAt=0,radarRequest=null;
 const radarCache=new Map();let radarRequested=0,radarPlaying=false;
 const finite=v=>typeof v==='number'&&Number.isFinite(v);
 const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
 const point=()=>window.CampoLocation?.getPoint?.()||{latitude:-23.065,longitude:-54.19,name:'Naviraí–MS'};
 const coords=p=>`${Number(p.latitude).toFixed(4)}|${Number(p.longitude).toFixed(4)}`;
 const normAngle=degrees=>((Number(degrees)%360)+360)%360;
 const cardinal=deg=>['N','NE','E','SE','S','SO','O','NO'][Math.round(normAngle(deg)/45)%8];
 const transit=deg=>normAngle(deg+180);
 const todayUTC=(daysBack=0)=>new Date(Date.now()-daysBack*86400000).toISOString().slice(0,10);
 function setStatus(message,type='muted'){const e=el('map-status');if(e){e.textContent=message;e.className='notice '+(type==='error'?'warning':type==='good'?'':'muted');}}
 const escape=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 function layerValue(v){const n=Number(v);return v==null||v===''||!Number.isFinite(n)?null:n;}
 function mapColor(variable,value){
  const x=layerValue(value);if(x===null)return '#9aaab3';
  if(variable.startsWith('cloud_cover')){if(x<20)return '#f8fcfe';if(x<45)return '#c0dfed';if(x<70)return '#79bad6';if(x<90)return '#317fae';return '#185477';}
  if(variable==='precipitation'){if(x<=0)return '#edf6fd';if(x<.5)return '#b9e0ef';if(x<2)return '#63b7dc';if(x<5)return '#297dac';if(x<10)return '#155187';return '#713a9f';}
  if(variable==='precipitation_probability'){if(x<10)return '#eaf5fa';if(x<30)return '#bbddec';if(x<50)return '#7dbbd6';if(x<70)return '#348db9';if(x<90)return '#17628e';return '#163d6b';}
  if(variable==='temperature_2m'){if(x<15)return '#406ab0';if(x<20)return '#8bbee5';if(x<25)return '#8bceba';if(x<30)return '#f4dc80';if(x<35)return '#ef9a60';return '#c84c49';}
  if(variable==='relative_humidity_2m'){if(x<35)return '#da775e';if(x<50)return '#e7bd6b';if(x<65)return '#d4dd87';if(x<80)return '#82c8bd';return '#398fae';}
  if(variable==='cape'){if(x<100)return '#e8f1f5';if(x<500)return '#a9d5bd';if(x<1000)return '#eed781';if(x<2000)return '#f19c61';return '#b84d65';}
  if(variable==='wind_gusts_10m'){if(x<10)return '#d3e8da';if(x<20)return '#79c7a0';if(x<30)return '#e6cd6b';if(x<40)return '#ee9e53';return '#d26162';}
  if(x<3)return '#d3e8da';if(x<6)return '#79c7a0';if(x<10)return '#e6cd6b';if(x<15)return '#ee9e53';return '#d26162';
 }
 function numericLegend(variable){
  let colors,values,unit,title,extra='';
  if(variable.startsWith('cloud_cover')){values=['<20','20–45','45–70','70–90','≥90'];colors=[10,30,55,80,95].map(v=>mapColor(variable,v));unit='%';title='Cobertura de nuvens prevista';}
  else if(variable==='precipitation'){values=['0','0–0,5','0,5–2','2–5','5–10','≥10'];colors=[0,.2,1,3,7,12].map(v=>mapColor(variable,v));unit='mm/h';title='Chuva horária prevista';}
  else if(variable==='precipitation_probability'){values=['<10','10–30','30–50','50–70','70–90','≥90'];colors=[0,15,35,55,75,95].map(v=>mapColor(variable,v));unit='%';title='Probabilidade de precipitação (Forecast API)';extra='Produto Forecast API: não é a frequência dos oito ensembles do painel, nem calibração local.';}
  else if(variable==='temperature_2m'){values=['<15','15–20','20–25','25–30','30–35','≥35'];colors=[10,17,22,27,32,37].map(v=>mapColor(variable,v));unit='°C';title='Temperatura prevista a 2 m';}
  else if(variable==='relative_humidity_2m'){values=['<35','35–50','50–65','65–80','≥80'];colors=[25,40,55,72,90].map(v=>mapColor(variable,v));unit='%';title='Umidade relativa prevista';}
  else if(variable==='cape'){values=['<100','100–500','500–1000','1000–2000','≥2000'];colors=[0,300,700,1500,2300].map(v=>mapColor(variable,v));unit='J/kg';title='CAPE previsto';extra='Instabilidade potencial, não previsão direta de temporais.';}
  else {const gust=variable==='wind_gusts_10m';values=gust?['<10','10–20','20–30','30–40','≥40']:['<3','3–6','6–10','10–15','≥15'];colors=(gust?[5,15,25,35,45]:[1,4,8,12,20]).map(v=>mapColor(variable,v));unit='km/h';title=gust?'Rajadas previstas a 10 m':'Vento previsto a 10 m';}
  return {title,unit,values,colors,extra};
 }
 function legend(variable){const v=numericLegend(variable);return `<strong>${escape(v.title)} (${escape(v.unit)})</strong> • valores do modelo • ${v.extra||'Não é observação em campo.'}`;}
 function swatches(colors,labels){return `<div class="map-scale-row">${colors.map((c,i)=>`<span class="map-scale-item"><i style="background:${c}" aria-hidden="true"></i><b>${escape(labels[i])}</b></span>`).join('')}</div>`;}
 function radarLegend(){const palette=[['10','#087fdb'],['20','#6e0dc6'],['30','#c06487'],['40','#fac431'],['50','#fe9a58'],['60','#fd341c']];return `<strong>Radar observado • refletividade (dBZ)</strong>${swatches(palette.map(x=>x[1]),palette.map(x=>x[0]))}<small>Escala oficial RainViewer Universal Blue. Cores representam intensidade do eco de radar (dBZ), <b>não mm/h</b>. Refletividade não equivale diretamente à chuva no solo. Transparência ou ausência de eco não comprovam tempo seco.</small>`;}
 function updateProductLegend(){const d=el('map-product-legend');if(!d)return;if(radarActive()){d.innerHTML=radarLegend();return;}const v=numericLegend(el('map-variable').value);d.innerHTML=`<strong>${escape(v.title)} (${escape(v.unit)}) • Open-Meteo Forecast</strong>${swatches(v.colors,v.values)}<small>Previsão em nove pontos de grade. ${escape(v.extra||'Não é imagem de satélite, nem leitura de estação.')}</small>`;const nasa=el('map-satellite').value;if(nasa!=='none')d.innerHTML+='<small><b>NASA MODIS/VIIRS:</b> imagem orbital em cores naturais, sem escala numérica. O horário exato da passagem sobre o ponto não é conhecido.</small>';}
 function productTitle(){const badge=el('map-product-source');if(!badge)return;if(radarActive())badge.textContent='🔵 RADAR OBSERVADO • RainViewer • quadros passados';else badge.textContent='🟢 PREVISÃO FUTURA • Open-Meteo Forecast • grade regional';}
 function radarStatus(msg,kind='muted'){const x=el('radar-status');if(x){x.textContent=msg;x.className='notice '+(kind==='bad'?'warning':kind==='ok'?'':'muted');}}
 function radarActive(){return el('radar-mode')?.value==='rainviewer';}
 function parseRadarManifest(manifest){
  const host=String(manifest?.host||'');let u;
  try{u=new URL(host);}catch(_){throw Error('Radar não forneceu host válido');}
  if(u.protocol!=='https:'||!(u.hostname==='rainviewer.com'||u.hostname.endsWith('.rainviewer.com')))throw Error('Host radar não autorizado');
  const frames=(manifest?.radar?.past||[]).filter(f=>Number.isFinite(Number(f.time))&&/^\/v2\/radar\/[0-9a-f]{8,64}$/.test(f.path||''))
    .map(f=>({time:Number(f.time),path:f.path})).sort((a,b)=>a.time-b.time);
  if(!frames.length)throw Error('Radar não forneceu imagens observadas');
  return {host:u.origin,frames:frames.slice(-16)};
 }
 function stopRadar(){radarPlaying=false;if(radarTimer){clearTimeout(radarTimer);radarTimer=null;}if(el('radar-play'))el('radar-play').textContent='▶ Reproduzir radar';}
 function clearRadarCache(){++radarRequested;stopRadar();for(const entry of radarCache.values())if(map?.hasLayer(entry.layer))map.removeLayer(entry.layer);radarCache.clear();radarTile=null;}
 function frameLabel(frame,index){const date=new Date(frame.time*1000);let local,utc;try{local=new Intl.DateTimeFormat('pt-BR',{dateStyle:'short',timeStyle:'short',timeZone:tz()}).format(date);}catch(_){local=date.toISOString().slice(0,16)+' UTC';}utc=date.toISOString().slice(0,16).replace('T',' ')+' UTC';const delta=Math.round((Date.now()-frame.time*1000)/60000);return `Quadro ${index+1}/${radarFrames.length} • ${local} (local) • ${utc} • ${delta>=0?'há '+delta+' min':'horário futuro inválido'}`;}
 function radarLayerEntry(index){
  if(radarCache.has(index))return radarCache.get(index);
  const frame=radarFrames[index];if(!frame||!map)return null;
  const layer=L.tileLayer(`${radarHost}${frame.path}/256/{z}/{x}/{y}/2/1_1.png`,{maxNativeZoom:7,maxZoom:18,opacity:0,keepBuffer:1,attribution:'Radar observado: <a href="https://www.rainviewer.com/" target="_blank" rel="noopener">RainViewer</a>'});
  const entry={layer,loaded:false,errors:0,index};radarCache.set(index,entry);
  layer.on('tileerror',()=>{entry.errors++;});
  layer.on('load',()=>{entry.loaded=true;if(radarRequestedIndex()===index)activateRadarEntry(entry);});
  layer.addTo(map);
  return entry;
 }
 let radarTargetIndex=-1;
 function radarRequestedIndex(){return radarTargetIndex;}
 function trimRadarCache(){const preserve=new Set([radarIndex,Math.max(0,radarIndex-1),Math.min(radarFrames.length-1,radarIndex+1)]);for(const [i,e] of radarCache){if(preserve.has(i))continue;if(map?.hasLayer(e.layer))map.removeLayer(e.layer);radarCache.delete(i);}}
 function activateRadarEntry(entry){
  if(!radarActive()||radarTargetIndex!==entry.index||!map)return;
  radarTile=entry.layer;
  for(const [i,e] of radarCache) e.layer.setOpacity(i===entry.index?0.86:0);
  if(selectedMarker)selectedMarker.bringToFront();
  const loading=el('radar-loading');if(loading)loading.textContent=entry.errors?'Quadro exibido com blocos indisponíveis.':'✓ Imagem carregada';
  trimRadarCache();
  // Fetch only one following frame to avoid blank transitions and excessive API tile calls.
  if(radarPlaying&&radarIndex<radarFrames.length-1)radarLayerEntry(radarIndex+1);
  if(radarPlaying){const delay=Number(el('radar-speed')?.value||2800);if(radarTimer)clearTimeout(radarTimer);radarTimer=setTimeout(()=>{
   radarTimer=null;if(!radarPlaying)return;
   if(radarIndex===radarFrames.length-1){stopRadar();radarStatus('✓ Sequência observada concluída no quadro mais recente. Clique em Reproduzir para rever do início.','ok');return;}
   requestRadarFrame(radarIndex+1);
  },clamp(delay,1400,6000));}
 }
 function requestRadarFrame(index){
  if(!map||!radarActive()||!radarFrames.length)return;
  const target=clamp(index,0,radarFrames.length-1);radarIndex=target;radarTargetIndex=target;
  const f=radarFrames[target];el('radar-frame').value=String(target);
  el('radar-frame-time').textContent=frameLabel(f,target);
  const loading=el('radar-loading');if(loading)loading.textContent='Carregando quadro no mapa…';
  updateProductLegend();productTitle();
  const entry=radarLayerEntry(target);
  if(entry?.loaded){activateRadarEntry(entry);return;}
  // Never remove the previous layer before the incoming image has loaded.
  if(radarTimer)clearTimeout(radarTimer);
  const requested=++radarRequested;
  radarTimer=setTimeout(()=>{radarTimer=null;if(requested!==radarRequested||radarTargetIndex!==target||!radarActive())return;
   if(entry?.errors>0)radarStatus('Alguns blocos do radar não carregaram neste zoom. Use os links oficiais para conferir a área.','bad');
   if(radarPlaying){if(target>=radarFrames.length-1)stopRadar();else requestRadarFrame(target+1);}
   else if(loading)loading.textContent='Quadro com carregamento demorado';
  },7000);
 }
 function showRadarFrame(){requestRadarFrame(radarIndex);}
 async function loadRadar(force=false){
  if(!radarActive()||!makeMap())return;
  stopRadar();
  if(!force&&radarFrames.length&&Date.now()-radarFetchedAt<5*60*1000){requestRadarFrame(radarIndex);return;}
  if(radarRequest)radarRequest.abort();const abort=new AbortController();radarRequest=abort;
  const timeout=setTimeout(()=>abort.abort(),13000);
  radarStatus('Consultando os quadros OBSERVADOS do radar (até cerca de 2 horas passadas)…');
  try{
   const response=await fetch('https://api.rainviewer.com/public/weather-maps.json',{signal:abort.signal,cache:'default'});
   if(!response.ok)throw Error('Serviço radar HTTP '+response.status);
   const result=parseRadarManifest(await response.json());if(!radarActive())return;
   clearRadarCache();radarHost=result.host;radarFrames=result.frames;radarFetchedAt=Date.now();radarIndex=radarFrames.length-1;
   el('radar-frame').max=String(radarFrames.length-1);el('radar-frame').disabled=false;el('radar-play').disabled=radarFrames.length<2;
   for(const id of ['radar-prev','radar-next'])if(el(id))el(id).disabled=radarFrames.length<2;
   requestRadarFrame(radarIndex);
   const newestAge=Math.round((Date.now()-radarFrames.at(-1).time*1000)/60000);
   if(newestAge>45)radarStatus(`⚠ Último quadro do radar tem ${newestAge} minutos. Produto desatualizado; não interpretar como chuva atual. Confira fontes oficiais.`, 'bad');
   else radarStatus('Radar OBSERVADO disponível. Use ◀, ▶ ou Reproduzir. O horário refere-se ao quadro composto, não a cada radar individual. Sem nowcast futuro.','ok');
  }catch(err){if(!radarActive())return;
   if(radarFrames.length){requestRadarFrame(radarIndex);radarStatus('Falha ao obter quadros mais recentes; mostrando a última sequência em cache, potencialmente DESATUALIZADA. '+String(err.message).slice(0,60),'bad');}
   else{clearRadarCache();radarFrames=[];el('radar-frame').disabled=true;el('radar-play').disabled=true;
    radarStatus('Radar indisponível nesta consulta ('+(err.name==='AbortError'?'tempo limite':String(err.message).slice(0,65))+'). Consulte os visualizadores oficiais do INMET/INPE.','bad');}
  }finally{clearTimeout(timeout);if(radarRequest===abort)radarRequest=null;}
 }
 function setRadarMode(){clearRadarCache();productTitle();updateProductLegend();
  if(radarActive()){
   pause();weatherLayer?.clearLayers();
   for(const id of ['map-hour','map-previous','map-next','map-play','map-refresh'])if(el(id))el(id).disabled=true;
   el('map-time-label').textContent='Modo radar: consulte os quadros observados acima. Previsão futura pausada.';
   if(imageLayer&&map?.hasLayer(imageLayer))map.removeLayer(imageLayer); // do not mix orbit imagery with radar colors
   el('map-satellite').disabled=true;el('map-variable').disabled=true;
   radarStatus('Modo radar observado. Imagem NASA e amostras previstas ocultadas para não misturar cores e fontes.');void loadRadar();
  }else{
   el('map-satellite').disabled=false;el('map-variable').disabled=false;
   for(const id of ['map-previous','map-next','map-play','map-refresh'])if(el(id))el(id).disabled=false;
   el('radar-frame').disabled=true;el('radar-play').disabled=true;
   for(const id of ['radar-prev','radar-next'])if(el(id))el(id).disabled=true;
   el('radar-frame-time').textContent='Radar desativado';const loading=el('radar-loading');if(loading)loading.textContent='';
   radarStatus('Radar desativado. Exibindo previsão espacial da Open-Meteo.');drawImage();if(!forecast||pointKey!==coords(point()))void loadForecast();else paint();
  }
 }
 function toggleRadarPlay(){if(!radarFrames.length)return;if(radarPlaying){stopRadar();return;}
  radarPlaying=true;el('radar-play').textContent='⏸ Pausar radar';
  // Start oldest-to-newest, making movement observable even if the latest frame was selected.
  if(radarIndex===radarFrames.length-1)requestRadarFrame(0);else requestRadarFrame(radarIndex);
 }
 function radarStep(step){stopRadar();requestRadarFrame(radarIndex+step);}
 function tz(){const t=typeof state!=='undefined'?state?.site?.timezone:null;return t&&t!=='auto'?t:'America/Campo_Grande';}
 function stamp(utc){try{return new Intl.DateTimeFormat('pt-BR',{dateStyle:'short',timeStyle:'short',timeZone:tz()}).format(new Date(utc+'Z'))}catch(_){return utc+' UTC';}}
 function makeMap(){
  if(map)return true;
  if(!window.L){setStatus('A biblioteca de mapa não carregou (rede ou bloqueio do CDN). Consulte os links oficiais de satélite abaixo.','error');return false;}
  const p=point();el('weather-map').innerHTML='';map=L.map('weather-map',{zoomControl:true,scrollWheelZoom:false,preferCanvas:true}).setView([p.latitude,p.longitude],8);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:18,attribution:'© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors',crossOrigin:true}).addTo(map);
  weatherLayer=L.layerGroup().addTo(map);
  selectedMarker=L.circleMarker([p.latitude,p.longitude],{radius:9,weight:3,color:'#0e3154',fillColor:'#4c9ed0',fillOpacity:.85}).addTo(map);
  selectedMarker.bindPopup('📍 Ponto selecionado<br>'+escape(p.name||'Fazenda')+'<br>'+Number(p.latitude).toFixed(5)+', '+Number(p.longitude).toFixed(5));
  map.on('click',function(e){const {lat,lng}=e.latlng;const popup=document.createElement('div');popup.innerHTML=`<strong>Usar este ponto?</strong><br>${lat.toFixed(5)}, ${lng.toFixed(5)}<br>`;
   const btn=document.createElement('button');btn.className='pill';btn.textContent='Consultar esta coordenada';btn.type='button';btn.addEventListener('click',()=>{window.CampoLocation?.select?.({latitude:lat,longitude:lng,name:'Ponto do mapa'});map.closePopup()});popup.appendChild(btn);L.popup().setLatLng(e.latlng).setContent(popup).openOn(map);});
  return true;
 }
 function reposition(){if(!map)return;const p=point();map.setView([p.latitude,p.longitude],8);selectedMarker.setLatLng([p.latitude,p.longitude]);selectedMarker.setPopupContent('📍 '+escape(p.name||'Ponto')+'<br>'+p.latitude.toFixed(5)+', '+p.longitude.toFixed(5));setTimeout(()=>map.invalidateSize(),80);}
 function imageURL(layer,date){return `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/${layer}/default/${date}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg`;}
 function drawImage(){
  if(!map||radarActive())return;
  if(imageLayer){map.removeLayer(imageLayer);imageLayer=null;}
  const layer=el('map-satellite').value,date=el('map-image-date').value;
  if(layer==='none'){setStatus(forecast?`Previsão Open-Meteo em grade: ${forecast.points.length} locais. Imagem NASA desativada.`:'Selecione uma camada de satélite ou carregue a previsão.');return;}
  if(!IMAGE_LAYERS.has(layer)||!/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(date)||date>todayUTC()){
   setStatus('Camada NASA ou data inválida; nenhuma imagem será exibida.','error');return;
  }
  imageLoaded=0;imageErrors=0;
  const source='NASA GIBS • '+(layer.startsWith('MODIS')?'MODIS Terra':'VIIRS NOAA-20')+' • imagem orbital do dia UTC '+date;
  imageLayer=L.tileLayer(imageURL(layer,date),{minZoom:1,maxNativeZoom:9,maxZoom:18,opacity:Number(el('map-opacity').value),attribution:'NASA GIBS (MODIS/VIIRS)'});
  imageLayer.on('tileload',()=>{imageLoaded++;if(imageLoaded===1)setStatus(`✓ ${source}. Blocos de imagem recebidos. A passagem sobre o ponto e o horário exato da imagem NÃO foram verificados; não é GOES em tempo real.`,'good');});
  imageLayer.on('tileerror',()=>{imageErrors++;if(imageErrors>=3&&!imageLoaded)setStatus(`${source}: não foi possível carregar os mosaicos nesta data/local (ou a rede bloqueou a NASA). Consulte NASA Worldview.`, 'error');});
  imageLayer.addTo(map);if(weatherLayer)weatherLayer.bringToFront();if(selectedMarker)selectedMarker.bringToFront();
  setStatus('Consultando NASA GIBS para '+date+'. Imagem histórica orbital, não projeção do futuro…');
 }
 function forecastGrid(p){const a=[],b=[];for(const dy of GRID_OFFSETS){for(const dx of GRID_OFFSETS){a.push((p.latitude+dy).toFixed(5));b.push((p.longitude+dx).toFixed(5));}}return {a,b};}
 function checkForecast(payload,p){
  if(!Array.isArray(payload)||payload.length!==POINT_COUNT)throw Error('A API não retornou todos os nove pontos de grade');
  const normal=payload.map((row,i)=>{const h=row?.hourly;if(!Array.isArray(h?.time)||h.time.length<24)throw Error('Horários ausentes no ponto '+i);
   if(Math.abs(Number(row.latitude)-(p.latitude+GRID_OFFSETS[Math.floor(i/3)]))>0.25)throw Error('Coordenada de grade muito distante');
   if(Math.abs(Number(row.longitude)-(p.longitude+GRID_OFFSETS[i%3]))>0.25)throw Error('Coordenada de grade muito distante');
   return {latitude:Number(row.latitude),longitude:Number(row.longitude),hourly:h};});
  if(!normal.every((r,i)=>r.hourly.time.slice(0,48).join('|')===normal[0].hourly.time.slice(0,48).join('|')))throw Error('Horários das grades inconsistentes');
  if(!normal.some(r=>r.hourly.cloud_cover?.some(finite)))throw Error('Previsão de nuvens vazia');
  return {points:normal,times:normal[0].hourly.time.slice(0,HOURS),coords:coords(p),issued_at:new Date().toISOString()};
 }
 let memory=new Map();
 async function loadForecast(force=false){
  if(!map)return;
  const p=point(),key=coords(p),old=memory.get(key);
  if(!force&&old&&Date.now()-old.at<2*3600000){forecast=old.data;pointKey=key;paint();setStatus('Previsão regional recuperada do cache (menos de 2h); horário válido indicado no seletor. Fonte: Open-Meteo Forecast, não satélite.');return;}
  if(force&&old&&Date.now()-old.at<3*60000){forecast=old.data;pointKey=key;paint();setStatus('Previsão consultada há menos de 3 minutos; cache mantido para respeitar os limites gratuitos.');return;}
  const task=++requestId,g=forecastGrid(p);
  setStatus('Consultando Open-Meteo para 9 pontos de grade ao redor de '+(p.name||'local')+'…');
  const q=new URLSearchParams({latitude:g.a.join(','),longitude:g.b.join(','),timezone:'UTC',forecast_hours:String(HOURS),hourly:VARIABLES.join(',')});
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),42000);
  try{
   let r=await fetch('https://api.open-meteo.com/v1/forecast?'+q,{signal:controller.signal});
   // A legacy forecast model may reject one of the optional cloud-height fields.
   // A single fallback with only core variables is allowed on HTTP 400; never retry
   // after 429/5xx (rate limits/outages), to respect the free API.
   if(r.status===400){
    q.set('hourly','cloud_cover,precipitation,wind_speed_10m,wind_direction_10m');
    r=await fetch('https://api.open-meteo.com/v1/forecast?'+q,{signal:controller.signal});
   }
   if(!r.ok)throw Error('HTTP '+r.status);
   const result=await r.json();if(result.error)throw Error(result.reason||'API retornou erro');
   const ready=checkForecast(result,p);
   if(task!==requestId||key!==coords(point()))return;
   forecast=ready;pointKey=key;memory.set(key,{at:Date.now(),data:ready});
   paint();setStatus('✓ Open-Meteo: previsão regional para 9 pontos, amostragem em grade. Fonte consultada às '+new Date().toLocaleTimeString('pt-BR')+'. Estas células NÃO são imagens de satélite.','good');
  }catch(err){if(task!==requestId)return;forecast=null;weatherLayer.clearLayers();el('map-hour').disabled=true;
   setStatus('Previsão regional indisponível: '+(err.name==='AbortError'?'tempo-limite':err.message)+'. A imagem NASA e os links oficiais continuam disponíveis.','error');}
  finally{clearTimeout(timer);}
 }
 function paint(){
  if(!map)return;
  if(!forecast||forecast.coords!==coords(point())){weatherLayer.clearLayers();el('map-hour').disabled=true;return;}
  const variable=el('map-variable').value;
  hourIndex=clamp(hourIndex,0,forecast.times.length-1);
  el('map-hour').disabled=false;el('map-hour').max=String(forecast.times.length-1);el('map-hour').value=String(hourIndex);
  const target=forecast.times[hourIndex];el('map-time-label').textContent=`${stamp(target)} (hora local do ponto) · ${target.replace('T',' ')} UTC · Open-Meteo Forecast`;
  el('map-legend').innerHTML=legend(variable);updateProductLegend();productTitle();
  weatherLayer.clearLayers();if(radarActive())return;let valid=0,center=null;
  const base=point();
  for(let i=0;i<forecast.points.length;i++){
   const sample=forecast.points[i],dy=GRID_OFFSETS[Math.floor(i/3)],dx=GRID_OFFSETS[i%3],v=layerValue(sample.hourly[variable]?.[hourIndex]);
   const from=layerValue(sample.hourly.wind_direction_10m?.[hourIndex]);
   if(v===null)continue;valid++;
   const color=mapColor(variable,v);
   const unit=variable==='precipitation'?'mm/h':['wind_speed_10m','wind_gusts_10m'].includes(variable)?'km/h':variable==='temperature_2m'?'°C':variable==='cape'?'J/kg':'%';
   const content=`<strong>${escape(variable)}</strong> ${v.toFixed(1)} ${unit}<br>Horário ${escape(stamp(target))}<br>Grade ${sample.latitude.toFixed(3)}, ${sample.longitude.toFixed(3)}${from!==null?`<br>Vento de ${cardinal(from)} (${from.toFixed(0)}°), transporte potencial ${cardinal(transit(from))}`:''}<br><small>Previsão Open-Meteo, não observação</small>`;
   L.circleMarker([sample.latitude,sample.longitude],{radius:19,weight:1.5,color:'#f8fbff',fillColor:color,fillOpacity:.55,interactive:true}).bindTooltip(content,{sticky:true}).addTo(weatherLayer);
   if(variable==='wind_speed_10m'&&from!==null){const bearing=transit(from);const icon=L.divIcon({className:'forecast-arrow',html:`<span style="transform:rotate(${bearing}deg)">↑</span>`,iconSize:[30,30],iconAnchor:[15,15]});L.marker([base.latitude+dy,base.longitude+dx],{icon,interactive:false}).addTo(weatherLayer);}
   if(i===4)center={v,from,wind:layerValue(sample.hourly.wind_speed_10m?.[hourIndex]),gust:null,rain:layerValue(sample.hourly.precipitation?.[hourIndex]),cloud:layerValue(sample.hourly.cloud_cover?.[hourIndex])};
  }
  if(selectedMarker)selectedMarker.bringToFront();
  if(center?.from!==null&&center?.from!==undefined){el('map-wind-summary').innerHTML=`<strong>Vento previsto no ponto central • ${escape(stamp(target))}:</strong> ${center.wind===null?'sem velocidade':center.wind.toFixed(1)+' km/h'}; <strong>de ${cardinal(center.from)} (${Math.round(center.from)}°)</strong> → transporte potencial para <strong>${cardinal(transit(center.from))} (${Math.round(transit(center.from))}°)</strong>. Nuvens previstas ${center.cloud===null?'—':center.cloud.toFixed(0)+'%'}; chuva prevista ${center.rain===null?'—':center.rain.toFixed(2)+' mm/h'}. Confirme no talhão.`;}
  else el('map-wind-summary').textContent='Direção prevista não disponível para esta hora. Não é possível inferir transporte.';
  if(valid===0)setStatus('Variável '+variable+' não disponível em nenhuma das nove células para a hora escolhida.','error');
 }
 function pause(){if(playing){clearInterval(playing);playing=null;el('map-play').textContent='▶ Animar';}}
 function togglePlay(){if(playing){pause();return;}if(!forecast)return;el('map-play').textContent='■ Pausar';playing=setInterval(()=>{if(!el('maps').classList.contains('active')){pause();return;}hourIndex=(hourIndex+1)%forecast.times.length;paint();},1200);}
 function display(){if(!makeMap())return;setTimeout(()=>map.invalidateSize(),130);reposition();if(radarActive()){void loadRadar();return;}if(!forecast||pointKey!==coords(point()))void loadForecast();else paint();}
 function onPointChange(){pause();stopRadar();++requestId;forecast=null;pointKey=null;hourIndex=0;if(map){reposition();weatherLayer.clearLayers();el('map-hour').disabled=true;if(el('maps').classList.contains('active')){if(radarActive())void loadRadar();else void loadForecast();}}}
 function syncWindCompass(){
  const container=el('wind-compass-content'),select=el('wind-hour-picker');if(!container||!select)return;
  const h=(typeof state!=='undefined'?state?.deterministic?.hourly:null)||{};
  if(!Array.isArray(h.time)||!h.time.length){container.textContent='Sem previsão horária válida para mostrar direção do vento.';select.innerHTML='<option>Sem dados</option>';return;}
  const localTimes=typeof hoursFrom==='function'?hoursFrom(h,72):h.time.map((t,i)=>({t,i})).slice(0,72);
  if(!localTimes.length)return;
  const before=select.value;select.innerHTML=localTimes.map(z=>`<option value="${z.i}">${escape(z.t.replace('T',' '))}</option>`).join('');
  if(localTimes.some(z=>String(z.i)===before))select.value=before;
  function update(){const i=Number(select.value),source=layerValue(h.wind_direction_10m?.[i]),speed=layerValue(h.wind_speed_10m?.[i]),gust=layerValue(h.wind_gusts_10m?.[i]);
   if(source===null){container.textContent='Sem direção de vento válida para a hora selecionada.';return;}
   const to=transit(source);
   container.innerHTML=`<svg viewBox="0 0 220 220" width="215" height="215" role="img" aria-label="Direção de origem ${Math.round(source)} graus, potencial transporte ${Math.round(to)} graus"><circle cx="110" cy="110" r="82" fill="#f5fafc" stroke="#b9d4e4" stroke-width="2"/><circle cx="110" cy="110" r="4" fill="#28506c"/><text x="110" y="20" text-anchor="middle">N</text><text x="199" y="115" text-anchor="middle">L</text><text x="110" y="208" text-anchor="middle">S</text><text x="20" y="115" text-anchor="middle">O</text><g transform="rotate(${source} 110 110)"><path d="M110 112 L110 40" stroke="#237da9" stroke-width="5" stroke-dasharray="5 5"/><path d="M102 52 L110 34 L118 52" stroke="#237da9" stroke-width="4" fill="none" stroke-linecap="round"/></g><g transform="rotate(${to} 110 110)"><path d="M110 112 L110 48" stroke="#c36839" stroke-width="7" stroke-linecap="round"/><path d="M99 59 L110 34 L121 59" fill="#c36839"/></g></svg><div class="compass-labels"><strong>${speed===null?'—':speed.toFixed(1)} km/h <small>vento médio 10 m</small></strong><span>Rajada prevista: <strong>${gust===null?'—':gust.toFixed(1)+' km/h'}</strong></span><span class="from-wind">🔵 Vem de <b>${cardinal(source)}</b> (${Math.round(source)}°)</span><span class="to-wind">🟠 Transporte potencial para <b>${cardinal(to)}</b> (${Math.round(to)}°)</span><small>Previsão determinística, não medição em campo.</small></div>`;
  }
  select.onchange=update;update();
 }
 function bind(){
  el('map-image-date').value=todayUTC(1);el('map-image-date').max=todayUTC();updateProductLegend();productTitle();
  el('map-to-selected').addEventListener('click',()=>{if(makeMap())reposition()});
  el('map-variable').addEventListener('change',paint);
  el('map-satellite').addEventListener('change',drawImage);
  el('map-image-date').addEventListener('change',drawImage);
  el('map-opacity').addEventListener('change',()=>{if(imageLayer)imageLayer.setOpacity(Number(el('map-opacity').value))});
  el('map-hour').addEventListener('input',()=>{hourIndex=Number(el('map-hour').value);pause();paint()});
  el('map-previous').addEventListener('click',()=>{if(!forecast)return;hourIndex=clamp(hourIndex-1,0,forecast.times.length-1);pause();paint()});
  el('map-next').addEventListener('click',()=>{if(!forecast)return;hourIndex=clamp(hourIndex+1,0,forecast.times.length-1);pause();paint()});
  el('map-play').addEventListener('click',togglePlay);
  el('map-refresh').addEventListener('click',()=>{pause();if(makeMap())void loadForecast(true)});
  el('radar-mode').addEventListener('change',setRadarMode);
  el('radar-play').addEventListener('click',toggleRadarPlay);
  el('radar-prev').addEventListener('click',()=>radarStep(-1));
  el('radar-next').addEventListener('click',()=>radarStep(1));
  el('radar-speed').addEventListener('change',()=>{if(radarPlaying)requestRadarFrame(radarIndex);});
  el('radar-refresh').addEventListener('click',()=>void loadRadar(true));
  el('radar-frame').addEventListener('input',()=>{stopRadar();requestRadarFrame(Number(el('radar-frame').value));});
  el('tabs').addEventListener('click',e=>{const tab=e.target.closest('button[data-tab]')?.dataset.tab;if(tab==='maps')setTimeout(display,90);else{pause();stopRadar();if(tab==='wind')setTimeout(syncWindCompass,110)}});
  window.addEventListener('campo:location-changed',onPointChange);
  window.addEventListener('visibilitychange',()=>{if(document.hidden){pause();stopRadar();}});
  // When new weather data is received, allow a fresh wind compass without reloading.
  window.CampoMaps={open:display,readCompass:syncWindCompass,_test:{coords,forecastGrid,checkForecast,transit,cardinal,mapColor,parseRadarManifest,numericLegend,radarLegend,frameLabel}};
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();
