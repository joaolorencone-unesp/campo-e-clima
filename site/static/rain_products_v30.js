'use strict';
/** Campo e Clima v3 — renders the derived rain products published by the collector:
 * multi-day accumulations and dry spells per member trajectory, daily model agreement
 * and the change since the previous publication. Pure formatters are exported for tests.
 */
(function(root){
 const finite=v=>typeof v==='number'&&Number.isFinite(v);
 const fmt=(v,d=1)=>finite(v)?v.toFixed(d).replace('.',','):'—';
 const pct=v=>finite(v)?(v*100).toFixed(0)+'%':'—';
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const ddmm=iso=>typeof iso==='string'&&/^\d{4}-\d\d-\d\d/.test(iso)?iso.slice(8,10)+'/'+iso.slice(5,7):'—';
 const $=id=>document.getElementById(id);
 function describeChange(day){
  if(!day)return '';
  const parts=[];
  if(finite(day.delta_p50_mm))parts.push(`mediana ${day.delta_p50_mm>0?'+':''}${fmt(day.delta_p50_mm)} mm (${fmt(day.p50_before_mm)} → ${fmt(day.p50_now_mm)})`);
  if(finite(day.delta_p_gt_1))parts.push(`freq. >1 mm ${day.delta_p_gt_1>0?'+':''}${(day.delta_p_gt_1*100).toFixed(0)} p.p. (${pct(day.p_gt_1_before)} → ${pct(day.p_gt_1_now)})`);
  return parts.join('; ')||'sem variação mensurável';
 }
 function agreementBadge(row){
  const cls=row.agreement_label==='alta'?'ok':row.agreement_label==='media'?'warn':'bad';
  const label=row.agreement_label==='alta'?'Alta':row.agreement_label==='media'?'Média':'Baixa';
  return `<span class="agree ${cls}">${label} · ${row.side==='chuva'?'chuva':row.side==='seco'?'seco':'dividido'}</span>`;
 }
 function render(state){
  if(typeof document==='undefined')return;
  const acc=$('rain-accumulated-body'),dry=$('rain-dry-spell'),agree=$('rain-agreement-daily'),change=$('run-change');
  const custom=Boolean(state?.site?.custom);
  if(acc){
   const rows=state?.rain_ensemble_accumulated||[];
   acc.innerHTML=rows.length?rows.map(r=>`<tr><td>${r.span_days} dias (${esc(ddmm(r.start))}–${esc(ddmm(r.end))})</td><td>${fmt(r.p50_mm,0)}</td><td>${fmt(r.p10_mm,0)}–${fmt(r.p90_mm,0)}</td><td>${fmt(r.mean_mm,0)}</td><td>${pct(r.p_gt_10_mm)}</td><td>${pct(r.p_gt_25_mm)}</td><td>${pct(r.p_gt_50_mm)}</td><td>${pct(r.p_gt_100_mm)}</td><td>${r.model_count} / ${r.member_count}</td></tr>`).join(''):
    `<tr><td colspan="9" class="na">${custom?'Acumulados por trajetória ficam disponíveis quando os ensembles de chuva do ponto respondem com dias completos.':'Sem trajetórias de membros completas nesta coleta.'}</td></tr>`;
  }
  if(dry){
   const d=state?.rain_dry_spell;
   dry.textContent=d?`Dias secos consecutivos (<${fmt(d.dry_day_threshold_mm,0)} mm/dia) até ${ddmm(d.end)}: mediana ${fmt(d.p50_days,0)} dia(s), P90 ${fmt(d.p90_days,0)}; ${pct(d.p_ge_3_days)} das trajetórias com ≥3 dias e ${pct(d.p_ge_5_days)} com ≥5 dias (${d.model_count} modelos, ${d.member_count} membros; janela de ${d.window_days} dias).`:'Sequência de dias secos indisponível: faltam trajetórias completas.';
  }
  if(agree){
   const rows=state?.rain_model_agreement_daily||[];
   agree.innerHTML=rows.length?'<table><thead><tr><th>Dia</th><th>Concordância</th><th>Modelos com maioria chuvosa</th><th>Médias por modelo (mín–máx)</th><th>Dispersão de volume</th></tr></thead><tbody>'+rows.map(r=>`<tr><td>${esc(ddmm(r.date))}</td><td>${agreementBadge(r)} <small>${(r.agreement_fraction*100).toFixed(0)}%</small></td><td>${r.wet_majority_models} de ${r.models}</td><td>${fmt(r.model_mean_min_mm)}–${fmt(r.model_mean_max_mm)} mm (mediana ${fmt(r.model_mean_median_mm)})</td><td>${esc(r.volume_spread_label)}</td></tr>`).join('')+'</tbody></table>':'<p class="caption">Sem comparação entre modelos nesta coleta.</p>';
  }
  if(change){
   const c=state?.previous_run_comparison;
   if(!c||c.state!=='ok'){change.innerHTML=`<p class="caption">${custom?'A comparação entre publicações existe apenas para as localidades coletadas automaticamente (Naviraí e Diamantino).':'Ainda não há publicação anterior armazenada para comparar; a próxima coleta passará a registrar as diferenças.'}</p>`;}
   else{
    const fresh=(c.models_with_new_acquisition||[]).length,same=(c.models_unchanged_acquisition||[]).length;
    change.innerHTML=`<p>${c.significant_days?`<strong>${c.significant_days} dia(s) com mudança relevante</strong> (≥${fmt(c.thresholds?.p50_mm,0)} mm na mediana ou ≥${(c.thresholds?.p_gt_1*100).toFixed(0)} p.p. na frequência >1 mm)`:'<strong>Sem mudança relevante</strong> desde a publicação anterior'} · anterior: ${esc((c.previous_issued_at_utc||'').replace('T',' ').slice(0,16))} UTC · ${fresh} modelo(s) com aquisição nova, ${same} reutilizado(s) do cache (mesma rodada).</p>
     <div class="scroll"><table><thead><tr><th>Dia</th><th>Mudança</th><th>Modelos (antes → agora)</th></tr></thead><tbody>${c.days.map(d=>`<tr class="${d.significant?'changed':''}"><td>${esc(ddmm(d.date))}</td><td>${esc(describeChange(d))}</td><td>${d.models_before??'—'} → ${d.models_now??'—'}</td></tr>`).join('')}</tbody></table></div>
     <p class="caption">${esc(c.note||'')}</p>`;
   }
  }
  const note=$('rain-hour-resolution-note');
  if(note){
   const steps=Object.entries(state?.ensemble_models||{}).filter(([,m])=>m.state==='ok').map(([n,m])=>`${n} ${m.precipitation_native_step_hours?m.precipitation_native_step_hours+' h':'?'}`);
   const first=(state?.rain_ensemble_hourly||[])[0]?.windows||{};
   note.textContent=`Passo nativo de precipitação detectado por modelo: ${steps.join(' · ')||'—'}. Janelas de 1 h usam ${first['1']?.models??'—'} modelo(s), 3 h ${first['3']?.models??'—'}, 6 h ${first['6']?.models??'—'}; modelos de 3/6 h entram apenas nas janelas que comportam seu passo, porque a API divide a acumulação em partes horárias iguais.`;
  }
 }
 function bind(){root.addEventListener?.('campo:forecast-rendered',()=>{try{render(typeof state!=='undefined'?state:null);}catch(e){console.error('rain products render',e);}});}
 if(typeof document!=='undefined')bind();
 root.CampoRainProducts={render,_test:{describeChange,agreementBadge}};
 if(typeof module==='object'&&module.exports)module.exports=root.CampoRainProducts;
})(typeof window!=='undefined'?window:globalThis);
