"use strict";
/** Agro ensembles: independently valid variables, VPD calculated per paired T/RH member.
 * Mirrors scripts/agro_ensemble.py. Frequencies are UNCALIBRATED member frequencies,
 * never operational approval. No HTTP request is made here.
 */
(() => {
 const FIELDS=['temperature_2m','relative_humidity_2m','wind_speed_10m','wind_gusts_10m','vpd_kpa'];
 const BOUNDS={temperature_2m:[-70,65],relative_humidity_2m:[0,100],wind_speed_10m:[0,250],wind_gusts_10m:[0,300],vpd_kpa:[0,15]};
 const THRESHOLDS={
  temperature_2m:[['p_ge_30',v=>v>=30],['p_ge_35',v=>v>=35],['p_le_5',v=>v<=5]],
  relative_humidity_2m:[['p_lt_55',v=>v<55],['p_lt_40',v=>v<40],['p_ge_90',v=>v>=90]],
  vpd_kpa:[['p_ge_1_5',v=>v>=1.5],['p_ge_2_5',v=>v>=2.5],['p_lt_0_5',v=>v<.5]],
  wind_speed_10m:[['p_gt_10',v=>v>10],['p_gt_15',v=>v>15],['p_lt_3',v=>v<3]],
  wind_gusts_10m:[['p_gt_25',v=>v>25],['p_gt_30',v=>v>30],['p_gt_40',v=>v>40]]};
 const LABELS={temperature_2m:'Temperatura',relative_humidity_2m:'Umidade relativa',wind_speed_10m:'Vento 10 m',wind_gusts_10m:'Rajadas 10 m',vpd_kpa:'VPD'};
 const UNITS={temperature_2m:'°C',relative_humidity_2m:'%',wind_speed_10m:'km/h',wind_gusts_10m:'km/h',vpd_kpa:'kPa'};
 const valid=(key,v)=>typeof v==='number'&&Number.isFinite(v)&&v>=BOUNDS[key][0]&&v<=BOUNDS[key][1];
 const vpd=(t,rh)=>.6108*Math.exp(17.27*t/(t+237.3))*(1-rh/100);
 function samples(payload, nowMillis=Date.now(), maxHours=72){
  const h=payload?.hourly||{},times=h.time||[],out={};
  const byKey={};for(const key of FIELDS.filter(k=>k!=='vpd_kpa')){
   byKey[key]=new Map();
   for(const [name,series] of Object.entries(h)){
    const match=name.match(new RegExp('^'+key+'_member(\\d+)$'));
    if(match&&Array.isArray(series))byKey[key].set(match[1],series);
   }
  }
  const off=payload?.utc_offset_seconds;
  const sign=off<0?'-':'+';
  const pad=x=>String(x).padStart(2,'0');
  const offset=Number.isFinite(off)?sign+pad(Math.floor(Math.abs(off)/3600))+':'+pad(Math.floor(Math.abs(off)%3600/60)):null;
  for(let i=0;i<times.length&&Object.keys(out).length<maxHours;i++){
   const stamp=times[i];
   if(offset){const utc=Date.parse(stamp+offset);if(!Number.isFinite(utc)||utc<=nowMillis)continue;}
   const row={};
   for(const key of FIELDS){let nums=[];
    if(key==='vpd_kpa'){
     for(const [id,ts] of byKey.temperature_2m){const rhs=byKey.relative_humidity_2m.get(id);
      if(!rhs||i>=ts.length||i>=rhs.length)continue;
      if(valid('temperature_2m',ts[i])&&valid('relative_humidity_2m',rhs[i])){
       const value=vpd(ts[i],rhs[i]);if(valid(key,value))nums.push(value);
      }
     }
    }else{for(const series of byKey[key].values())if(i<series.length&&valid(key,series[i]))nums.push(series[i]);}
    if(nums.length)row[key]=nums;
   }
   if(Object.keys(row).length)out[stamp]=row;
  }
  return out;
 }
 function quantile(pairs,q){const ordered=[...pairs].sort((a,b)=>a[0]-b[0]);let w=0;for(const [v,p] of ordered){w+=p;if(w>=q-1e-10)return +v.toFixed(3);}return ordered.at(-1)?.[0]??null;}
 function blend(byModel,limit=72){
  const stamps=[...new Set(Object.values(byModel).flatMap(m=>Object.keys(m)))].sort().slice(0,limit),result=[];
  for(const stamp of stamps){const vars={};for(const key of FIELDS){
   const groups=Object.entries(byModel).map(([name,m])=>[name,m[stamp]?.[key]]).filter(([,x])=>Array.isArray(x)&&x.length);
   if(!groups.length)continue;
   const pairs=groups.flatMap(([,values])=>values.map(v=>[v,1/groups.length/values.length]));
   const row={model_count:groups.length,member_count:pairs.length,models:groups.map(([name])=>name).sort(),p10:quantile(pairs,.1),p50:quantile(pairs,.5),p90:quantile(pairs,.9),mean:+pairs.reduce((s,[v,w])=>s+v*w,0).toFixed(3)};
   for(const [label,test] of THRESHOLDS[key]||[])row[label]=+pairs.reduce((s,[v,w])=>s+(test(v)?w:0),0).toFixed(4);
   vars[key]=row;
  }if(Object.keys(vars).length)result.push({time:stamp,variables:vars});}
  return result;
 }
 function coverage(byModel){
  const out={};
  for(const key of FIELDS){const models=Object.entries(byModel).filter(([,rows])=>Object.values(rows||{}).some(r=>r[key])).map(([name])=>name).sort();out[key]={models,model_count:models.length};}
  return out;
 }
 const fmt=(v,d=1)=>typeof v==='number'&&Number.isFinite(v)?v.toFixed(d).replace('.',','):'—';
 const esc=s=>String(s??'').replace(/[&<>"']/g,x=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));
 function render(state){
  let panel=document.getElementById('agro-ensemble-panel');
  if(!panel){const parent=document.querySelector('#overview .hero-panel');if(!parent)return;
   panel=document.createElement('article');panel.className='panel';panel.id='agro-ensemble-panel';parent.insertAdjacentElement('afterend',panel);}
  const data=state?.agro_ensemble_hourly||[];
  const cov=state?.agro_ensemble_coverage||{};
  if(!data.length){panel.innerHTML='<h3>🌡 Temperatura, umidade, VPD e vento por ensemble</h3><p class="caption">Sem membros válidos nesta coleta para estas variáveis. Nada é preenchido com zeros nem com a previsão determinística.</p>';return;}
  const chosen=data.filter((v,i)=>i%3===0).slice(0,16);
  const v=(row,key)=>row.variables?.[key];
  const median=(row,key,d=1)=>{const s=v(row,key);return s?`${fmt(s.p50,d)} <small>[${fmt(s.p10,d)}–${fmt(s.p90,d)}]</small>`:'—';};
  const risk=(row,key,prop)=>{const x=v(row,key)?.[prop];return x==null?'—':fmt(x*100,0)+'%';};
  const rows=chosen.map(row=>{const day=row.time.slice(8,10)+'/'+row.time.slice(5,7),hour=row.time.slice(11,16);
   return `<tr><td>${esc(day+' '+hour)}</td><td>${median(row,'temperature_2m')}</td><td>${median(row,'relative_humidity_2m',0)}</td><td>${median(row,'vpd_kpa',2)}</td><td>${median(row,'wind_speed_10m')}</td><td>${median(row,'wind_gusts_10m')}</td><td>${risk(row,'vpd_kpa','p_ge_1_5')}</td><td>${risk(row,'temperature_2m','p_ge_30')}</td><td>${risk(row,'wind_gusts_10m','p_gt_30')}</td></tr>`;}).join('');
  const covText=FIELDS.map(k=>`${LABELS[k]}: <strong>${cov[k]?.model_count??Math.max(0,...data.map(r=>r.variables?.[k]?.model_count||0))}</strong> modelo(s)`).join(' · ');
  panel.innerHTML=`<div class="panel-head"><h3>🌡 Temperatura, umidade, VPD e vento por ensemble</h3><span>Mediana [P10–P90] · peso igual por modelo</span></div>
   <p class="caption">Modelos válidos por variável — ${covText}. VPD calculado com temperatura e UR do <strong>mesmo membro</strong> (FAO-56). Rajadas só existem nos modelos que as publicam; a ausência não é rajada zero. Frequências <strong>não calibradas</strong>; nenhum valor autoriza operação.</p>
   <div class="scroll"><table><thead><tr><th>Hora local</th><th>T °C</th><th>UR %</th><th>VPD kPa</th><th>Vento km/h</th><th>Rajada km/h</th><th>Freq. VPD ≥1,5</th><th>Freq. T ≥30</th><th>Freq. rajada &gt;30</th></tr></thead><tbody>${rows}</tbody></table></div>
   <p class="caption">Amostra a cada 3 h das ${data.length} horas futuras disponíveis. Para o detalhe por hora, use a Central Agro e a aba Vento.</p>`;
 }
 window.CampoAgroWeather={samples,blend,coverage,render,FIELDS,LABELS,UNITS,_test:{vpd,valid}};
})();
