'use strict';
/** Campo e Clima v4.1 — simple-mode agro indices from already published products:
 * frost risk (member fractions at or below 3 °C and 1 °C from the agro ensembles, plus the
 * deterministic minimum), degree-days for the week (deterministic daily extremes, selectable base)
 * and chill hours below 7,2 °C (deterministic hourly). Nothing here is a recommendation. */
(function(root){
 const $=id=>typeof document==='undefined'?null:document.getElementById(id);
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const finite=v=>typeof v==='number'&&Number.isFinite(v);
 const fmt=(v,d=1)=>finite(v)?v.toFixed(d).replace('.',','):'—';
 const pct=v=>finite(v)?(v*100).toFixed(0)+'%':'—';
 const BASES=[{t:10,label:'10 °C (milho, soja)'},{t:12.8,label:'12,8 °C (citros)'},{t:15,label:'15 °C (cana)'}];
 function offsetSeconds(state){const s=state?.site?.utc_offset_seconds,d=state?.deterministic?.utc_offset_seconds;return finite(s)?s:finite(d)?d:-14400;}
 function localDate(now,state){return new Date(now+offsetSeconds(state)*1000).toISOString().slice(0,10);}
 function frost(state,now=Date.now()){
  const today=localDate(now,state);
  const nights=new Map(); // local date → worst night (00–08 h local) statistics
  for(const row of state?.agro_ensemble_hourly||[]){
   const t=row.time||'';const hour=Number(t.slice(11,13));if(!(hour<=8))continue;
   const date=t.slice(0,10);if(date<today)continue;
   const v=row.variables?.temperature_2m;if(!v)continue;
   const slot=nights.get(date)||{date,p_le_5:0,p_le_3:0,p_le_1:0,p10:null,models:v.models||null};
   slot.p_le_5=Math.max(slot.p_le_5,v.p_le_5||0);slot.p_le_3=Math.max(slot.p_le_3,v.p_le_3||0);slot.p_le_1=Math.max(slot.p_le_1,v.p_le_1||0);
   if(finite(v.p10))slot.p10=slot.p10===null?v.p10:Math.min(slot.p10,v.p10);
   nights.set(date,slot);
  }
  const daily=state?.deterministic?.daily||{};
  const detMin=(daily.time||[]).map((d,i)=>({date:d,tmin:daily.temperature_2m_min?.[i]})).filter(x=>x.date>=today&&finite(x.tmin)).slice(0,7);
  const worst=[...nights.values()].sort((a,b)=>b.p_le_3-a.p_le_3||b.p_le_5-a.p_le_5)[0]||null;
  const coldest=detMin.sort((a,b)=>a.tmin-b.tmin)[0]||null;
  let level='sem sinal',cls='ok';
  if(worst&&worst.p_le_1>=.2||coldest&&coldest.tmin<=1){level='alto';cls='bad';}
  else if(worst&&worst.p_le_3>=.2||coldest&&coldest.tmin<=3){level='atenção';cls='warn';}
  else if(worst&&worst.p_le_5>=.3||coldest&&coldest.tmin<=5){level='baixo';cls='warn';}
  return {level,cls,worst,coldest,available:Boolean(worst||coldest)};
 }
 function degreeDays(state,base,now=Date.now()){
  const today=localDate(now,state);const d=state?.deterministic?.daily||{};
  const days=(d.time||[]).map((date,i)=>({date,tmax:d.temperature_2m_max?.[i],tmin:d.temperature_2m_min?.[i]})).filter(x=>x.date>=today&&finite(x.tmax)&&finite(x.tmin)).slice(0,7);
  const rows=days.map(x=>({...x,gdd:Math.max(0,(x.tmax+x.tmin)/2-base)}));
  return {days:rows,total:rows.reduce((s,x)=>s+x.gdd,0),n:rows.length};
 }
 function chillHours(state,now=Date.now()){
  const h=state?.deterministic?.hourly||{};const today=localDate(now,state);
  let n=0,total=0;(h.time||[]).forEach((t,i)=>{if(t.slice(0,10)<today)return;const v=h.temperature_2m?.[i];if(!finite(v))return;total++;if(v<7.2)n++;});
  return {hours:n,covered:total};
 }
 function render(state,now=Date.now()){
  const box=$('agro-indices');if(!box)return;
  const base=Number($('gdd-base')?.value||10);
  const f=frost(state,now),g=degreeDays(state,base,now),c=chillHours(state,now);
  if(!f.available&&!g.n){box.innerHTML='<p class="caption">Sem previsão publicada para calcular os índices.</p>';return;}
  box.innerHTML=`<div class="farm-cards">
   <div class="farm-card"><small>Risco de geada (7 noites)</small><strong class="${f.cls}">${esc(f.level)}</strong><span>${f.worst?`${pct(f.worst.p_le_3)} dos membros ≤ 3 °C e ${pct(f.worst.p_le_1)} ≤ 1 °C na madrugada de ${esc(f.worst.date.slice(8,10))}/${esc(f.worst.date.slice(5,7))}${finite(f.worst.p10)?` · P10 ${fmt(f.worst.p10)} °C`:''}`:'ensembles sem madrugadas futuras'}${f.coldest?` · mínima determinística ${fmt(f.coldest.tmin)} °C em ${esc(f.coldest.date.slice(8,10))}/${esc(f.coldest.date.slice(5,7))}`:''}</span></div>
   <div class="farm-card"><small>Graus-dia da semana (base ${fmt(base,1)} °C)</small><strong>${fmt(g.total,0)} °C·dia</strong><span>${g.n} dias · soma de máx(0, (Tmáx+Tmín)/2 − base) da previsão determinística</span></div>
   <div class="farm-card"><small>Horas de frio &lt; 7,2 °C</small><strong>${c.hours} h</strong><span>em ${c.covered} horas previstas (determinístico)</span></div>
  </div><p class="caption">Geada no ar a 2 m não é geada na folha: relevo, céu limpo e vento calmo mudam o risco local. Percentuais são frequências de membros, não probabilidades calibradas. Graus-dia e horas de frio são índices de planejamento, não recomendação de manejo.</p>`;
 }
 if(typeof document!=='undefined'){
  root.addEventListener('campo:forecast-rendered',()=>{try{render(typeof state!=='undefined'?state:null);}catch(e){console.error('agro indices',e);}});
  document.addEventListener('change',e=>{if(e.target?.id==='gdd-base')try{render(typeof state!=='undefined'?state:null);}catch(_){}});
 }
 root.CampoAgroIndices={frost,degreeDays,chillHours,render,BASES};
 if(typeof module==='object'&&module.exports)module.exports=root.CampoAgroIndices;
})(typeof window!=='undefined'?window:globalThis);
