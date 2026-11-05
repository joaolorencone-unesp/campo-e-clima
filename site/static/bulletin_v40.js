'use strict';
/** Campo e Clima v4 — interpretive bulletin card. The text is produced by the collector
 * (rules always; a free LLM may only rephrase validated facts). The card always states its
 * origin and hides itself for custom coordinates, which have no published bulletin. */
(function(root){
 const $=id=>typeof document==='undefined'?null:document.getElementById(id);
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const cache=new Map();
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
  $('bulletin-meta').textContent=`${locationName?locationName+' · ':''}gerado ${ageText(bulletin.generated_utc)} a partir da previsão emitida ${bulletin.issued_at_utc?new Date(bulletin.issued_at_utc).toLocaleString('pt-BR'):'—'} · ${bulletin.disclaimer||''}`;
  card.hidden=false;
 }
 async function load(locationId,locationName){
  const card=$('bulletin-card');if(!card)return null;
  if(!locationId){card.hidden=true;return null;}
  try{
   if(!cache.has(locationId)){
    const r=await fetch(`data/bulletin_${encodeURIComponent(locationId)}.json`,{cache:'no-store'});
    if(!r.ok)throw Error('HTTP '+r.status);
    cache.set(locationId,await r.json());
   }
   render(cache.get(locationId),locationName);return cache.get(locationId);
  }catch(_){card.hidden=true;return null;}
 }
 function currentLocation(){
  const st=typeof state!=='undefined'?state:null;
  const custom=root.CampoLocation?.getPoint?.()?.custom;
  if(custom)return {id:null,name:null};
  return {id:st?.site?.id||'navirai',name:st?.site?.id==='diamantino'?'Diamantino–MT':'Naviraí–MS'};
 }
 function refresh(){const loc=currentLocation();void load(loc.id,loc.name);}
 if(typeof document!=='undefined'){
  root.addEventListener('campo:forecast-rendered',refresh);
  root.addEventListener('campo:location-changed',()=>setTimeout(refresh,50));
 }
 root.CampoBulletin={load,render,originLabel,_test:{ageText}};
 if(typeof module==='object'&&module.exports)module.exports=root.CampoBulletin;
})(typeof window!=='undefined'?window:globalThis);
