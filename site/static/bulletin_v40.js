'use strict';
/** Campo e Clima v4 — interpretive bulletin card. The text is produced by the collector
 * (rules always; a free LLM may only rephrase validated facts). The card always states its
 * origin and hides itself for custom coordinates, which have no published bulletin. */
(function(root){
 const $=id=>typeof document==='undefined'?null:document.getElementById(id);
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const cache=new Map();let requestId=0;
 const REFERENCE_POINTS={navirai:{latitude:-23.065,longitude:-54.19},diamantino:{latitude:-14.408,longitude:-56.446}};
 function locationIdFor(point){if(!point)return null;for(const [id,ref] of Object.entries(REFERENCE_POINTS)){if(Math.abs(point.latitude-ref.latitude)<0.01&&Math.abs(point.longitude-ref.longitude)<0.01)return id;}return null;}
 function siteTimeZone(){const st=typeof state!=='undefined'?state:null;const tz=st?.site?.timezone;return tz&&tz!=='auto'?tz:'America/Campo_Grande';}
 function originLabel(b){
  if(b.status==='llm')return {text:`IA (${b.provider}: ${b.model}) · números validados contra os fatos`,cls:'ai'};
  if(b.status==='rules_fallback')return {text:'texto por regras (IA indisponível ou rejeitada)',cls:'rules'};
  return {text:'texto por regras, sem IA',cls:'rules'};
 }
 function ageText(iso){const m=Math.round((Date.now()-Date.parse(iso))/60000);if(!Number.isFinite(m))return '';return m<60?`há ${m} min`:`há ${(m/60).toFixed(1).replace('.',',')} h`;}
 function render(bulletin,locationName){
  const card=$('bulletin-card');if(!card)return;
  if(!bulletin||!bulletin.text){card.hidden=true;return;}
  const origin=originLabel(bulletin);
  $('bulletin-text').textContent=bulletin.text;
  const badge=$('bulletin-origin');badge.textContent=origin.text;badge.className='source-badge origin-'+origin.cls;
  let issued='—';try{issued=bulletin.issued_at_utc?new Date(bulletin.issued_at_utc).toLocaleString('pt-BR',{timeZone:siteTimeZone()})+' (horário local do ponto)':'—';}catch(_){issued=bulletin.issued_at_utc||'—';}
  $('bulletin-meta').textContent=`${locationName?locationName+' · ':''}gerado ${ageText(bulletin.generated_utc)} a partir da previsão emitida ${issued} · ${bulletin.disclaimer||''}`;
  card.hidden=false;
 }
 async function load(locationId,locationName){
  const card=$('bulletin-card');if(!card)return null;
  const token=++requestId;
  if(!locationId){card.hidden=true;return null;}
  try{
   if(!cache.has(locationId)){
    const r=await fetch(`data/bulletin_${encodeURIComponent(locationId)}.json`,{cache:'no-store'});
    if(!r.ok)throw Error('HTTP '+r.status);
    cache.set(locationId,await r.json());
   }
   if(token!==requestId)return null; // the location changed while the bulletin was loading
   render(cache.get(locationId),locationName);return cache.get(locationId);
  }catch(_){if(token===requestId)card.hidden=true;return null;}
 }
 function currentLocation(){
  const st=typeof state!=='undefined'?state:null;
  const point=root.CampoLocation?.getPoint?.();
  const id=locationIdFor(point)||(point?.custom?null:(st?.site?.id||'navirai'));
  return {id,name:id==='diamantino'?'Diamantino–MT':id==='navirai'?'Naviraí–MS':null};
 }
 function refresh(){
  const loc=currentLocation(),st=typeof state!=='undefined'?state:null;
  const preserved=st?.publication_state==='previous_preserved'&&st?.site?.id===loc.id;
  void load(preserved?null:loc.id,loc.name);
 }
 if(typeof document!=='undefined'){
  root.addEventListener('campo:forecast-rendered',refresh);
  root.addEventListener('campo:location-changed',()=>setTimeout(refresh,50));
 }
 root.CampoBulletin={load,render,originLabel,locationIdFor,_test:{ageText,currentLocation}};
 if(typeof module==='object'&&module.exports)module.exports=root.CampoBulletin;
})(typeof window!=='undefined'?window:globalThis);
