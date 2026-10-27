'use strict';
/** Campo e Clima 1.4 • free scientific maps; NASA GIBS is observed imagery,
 * Open-Meteo gridded forecast is a distinct forecast product.
 * No NASA/Google/OpenWeather secret is needed or embedded in this code.
 */
(function(){
 const el=id=>document.getElementById(id);
 const GRID_OFFSETS=[-0.4,0,0.4],POINT_COUNT=9,HOURS=48;
 const VARIABLES=['cloud_cover','cloud_cover_low','cloud_cover_mid','cloud_cover_high','precipitation','wind_speed_10m','wind_direction_10m'];
 const IMAGE_LAYERS=new Set(['MODIS_Terra_CorrectedReflectance_TrueColor','VIIRS_NOAA20_CorrectedReflectance_TrueColor']);
 let map=null,selectedMarker=null,weatherLayer=null,imageLayer=null,forecast=null,pointKey=null,lastAt=0;
 let hourIndex=0,requestId=0,playing=null,imageLoaded=0,imageErrors=0;
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
  if(x<3)return '#d3e8da';if(x<6)return '#79c7a0';if(x<10)return '#e6cd6b';if(x<15)return '#ee9e53';return '#d26162';
 }
 function legend(variable){
  if(variable.startsWith('cloud_cover'))return '☁ <strong>Nebulosidade prevista (%):</strong> 0–20 muito baixa · 20–45 baixa · 45–70 moderada · 70–90 elevada · 90–100 muito elevada';
  if(variable==='precipitation')return '🌧 <strong>Chuva prevista (mm/h):</strong> 0 · até 0,5 · 0,5–2 · 2–5 · 5–10 · >10';
  return '🌬 <strong>Vento médio previsto (km/h):</strong> 0–3 · 3–6 · 6–10 · 10–15 · >15. Setas indicam o transporte potencial, oposto à direção meteorológica.';
 }
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
  if(!map)return;
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
  const target=forecast.times[hourIndex];el('map-time-label').textContent=stamp(target)+' (hora do ponto)';
  el('map-legend').innerHTML=legend(variable);
  weatherLayer.clearLayers();let valid=0,center=null;
  const base=point();
  for(let i=0;i<forecast.points.length;i++){
   const sample=forecast.points[i],dy=GRID_OFFSETS[Math.floor(i/3)],dx=GRID_OFFSETS[i%3],v=layerValue(sample.hourly[variable]?.[hourIndex]);
   const from=layerValue(sample.hourly.wind_direction_10m?.[hourIndex]);
   if(v===null)continue;valid++;
   const bounds=[[base.latitude+dy-.195,base.longitude+dx-.195],[base.latitude+dy+.195,base.longitude+dx+.195]];
   const color=mapColor(variable,v);
   const unit=variable==='precipitation'?'mm/h':variable==='wind_speed_10m'?'km/h':'%';
   const content=`<strong>${escape(variable)}</strong> ${v.toFixed(1)} ${unit}<br>Horário ${escape(stamp(target))}<br>Grade ${sample.latitude.toFixed(3)}, ${sample.longitude.toFixed(3)}${from!==null?`<br>Vento de ${cardinal(from)} (${from.toFixed(0)}°), transporte potencial ${cardinal(transit(from))}`:''}<br><small>Previsão Open-Meteo, não observação</small>`;
   L.rectangle(bounds,{color,weight:.5,fillColor:color,fillOpacity:.49,interactive:true}).bindTooltip(content,{sticky:true}).addTo(weatherLayer);
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
 function display(){if(!makeMap())return;setTimeout(()=>map.invalidateSize(),130);reposition();if(!forecast||pointKey!==coords(point()))void loadForecast();else paint();}
 function onPointChange(){pause();++requestId;forecast=null;pointKey=null;hourIndex=0;if(map){reposition();weatherLayer.clearLayers();el('map-hour').disabled=true;if(el('maps').classList.contains('active'))void loadForecast();}}
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
  el('map-image-date').value=todayUTC(1);el('map-image-date').max=todayUTC();
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
  el('tabs').addEventListener('click',e=>{const tab=e.target.closest('button[data-tab]')?.dataset.tab;if(tab==='maps')setTimeout(display,90);else{pause();if(tab==='wind')setTimeout(syncWindCompass,110)}});
  window.addEventListener('campo:location-changed',onPointChange);
  window.addEventListener('visibilitychange',()=>{if(document.hidden)pause()});
  // When new weather data is received, allow a fresh wind compass without reloading.
  window.CampoMaps={open:display,readCompass:syncWindCompass,_test:{coords,forecastGrid,checkForecast,transit,cardinal,mapColor}};
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();
