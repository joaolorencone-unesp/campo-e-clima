"use strict";
/** Agro ensembles: independently valid variables, VPD calculated per paired T/RH member.
 * Probabilities are UNCALIBRATED member frequencies, never operational approval.
 */
(() => {
 const FIELDS=['temperature_2m','relative_humidity_2m','wind_speed_10m','wind_gusts_10m','vpd_kpa'];
 const BOUNDS={temperature_2m:[-70,65],relative_humidity_2m:[0,100],wind_speed_10m:[0,250],wind_gusts_10m:[0,300],vpd_kpa:[0,15]};
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
   const groups=Object.values(byModel).map(m=>m[stamp]?.[key]).filter(x=>Array.isArray(x)&&x.length);
   if(!groups.length)continue;
   const pairs=groups.flatMap(values=>values.map(v=>[v,1/groups.length/values.length]));
   const row={model_count:groups.length,member_count:pairs.length,p10:quantile(pairs,.1),p50:quantile(pairs,.5),p90:quantile(pairs,.9),mean:+pairs.reduce((s,[v,w])=>s+v*w,0).toFixed(3)};
   if(key==='temperature_2m')row.p_ge_30=pairs.reduce((s,[v,w])=>s+(v>=30?w:0),0);
   if(key==='relative_humidity_2m')row.p_lt_55=pairs.reduce((s,[v,w])=>s+(v<55?w:0),0);
   if(key==='vpd_kpa')row.p_ge_1_5=pairs.reduce((s,[v,w])=>s+(v>=1.5?w:0),0);
   if(key==='wind_speed_10m')row.p_gt_10=pairs.reduce((s,[v,w])=>s+(v>10?w:0),0);
   if(key==='wind_gusts_10m')row.p_gt_30=pairs.reduce((s,[v,w])=>s+(v>30?w:0),0);
   vars[key]=row;
  }if(Object.keys(vars).length)result.push({time:stamp,variables:vars});}
  return result;
 }
 const fmt=(v,d=1)=>typeof v==='number'&&Number.isFinite(v)?v.toFixed(d).replace('.',','):'—';
 const esc=s=>String(s??'').replace(/[&<>"']/g,x=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));
 function render(state){
  const parent=document.querySelector('#overview .hero-panel');if(!parent)return;
  let panel=document.getElementById('agro-ensemble-panel');
  if(!panel){panel=document.createElement('article');panel.className='panel';panel.id='agro-ensemble-panel';
   parent.insertAdjacentElement('afterend',panel);}
  const data=state?.agro_ensemble_hourly||[];
  if(!data.length){panel.innerHTML='<h3>🌱 Ensembles agrometeorológicos</h3><p class="caption">Temperatura, umidade relativa, VPD, vento e rajadas por membro. Sem amostras válidas nesta coleta; não preencher com zeros nem com estimativas determinísticas.</p>';return;}
  const chosen=data.filter((v,i)=>i%3===0).slice(0,12);
  const v=(row,key)=>row.variables?.[key];
  const median=(row,key,unit='')=>{const s=v(row,key);return s?`${fmt(s.p50)}${unit} <small>[${fmt(s.p10)}–${fmt(s.p90)}]</small>`:'—';};
  const risk=(row,key,prop)=>{const x=v(row,key)?.[prop];return x==null?'—':fmt(x*100,0)+'%';};
  const dates=chosen.map(row=>{const day=row.time.slice(8,10)+'/'+row.time.slice(5,7),hour=row.time.slice(11,16);
   return `<tr><td>${esc(day+' '+hour)}</td><td>${median(row,'temperature_2m',' °C')}</td><td>${median(row,'relative_humidity_2m',' %')}</td><td>${median(row,'vpd_kpa',' kPa')}</td><td>${median(row,'wind_speed_10m',' km/h')}</td><td>${median(row,'wind_gusts_10m',' km/h')}</td><td>${risk(row,'vpd_kpa','p_ge_1_5')}</td><td>${v(row,'vpd_kpa')?.model_count??'—'}</td></tr>`;}).join('');
  const row=data[0],available=Object.fromEntries(FIELDS.map(k=>[k,data.some(r=>r.variables?.[k])]));
  const missing=Object.entries(available).filter(([,ok])=>!ok).map(([key])=>key).join(', ');
  const models=Math.max(0,...data.map(r=>r.variables?.vpd_kpa?.model_count||0));
  panel.innerHTML=`<h3>🌱 Temperatura, umidade, VPD e vento • ensembles</h3><p class="caption">Mediana [P10–P90] por horário, com peso igual por modelo e depois por membro. VPD calculado a partir de temperatura e UR do <strong>mesmo membro</strong>. ${models} modelo(s) com VPD válido (até 8 disponíveis na coleta automática; até 3 na consulta direta do ponto). Frequências NÃO calibradas; não autorizam pulverização.</p><div class="scroll"><table><thead><tr><th>Hora local</th><th>T</th><th>UR</th><th>VPD</th><th>Vento 10m</th><th>Rajada 10m</th><th>Freq. VPD ≥1,5</th><th>Modelos VPD</th></tr></thead><tbody>${dates}</tbody></table></div>${missing?`<p class="caption">Sem membros válidos para: ${esc(missing)}.</p>`:''}<p class="caption">Limiares são referências exploratórias. Para aplicação agrícola, verificar vento e rajadas no talhão, inversão, bula, deriva, altura de voo e receptores sensíveis.</p>`;
 }
 window.CampoAgroWeather={samples,blend,render,_test:{vpd,valid}};
})();
