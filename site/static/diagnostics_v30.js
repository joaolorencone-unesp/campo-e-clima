'use strict';
/** Campo e Clima v3 — freshness (per model: run, acquisition, cache, native step) and the
 * central diagnostics file written by the collector. Read-only; nothing is estimated. */
(function(root){
 const finite=v=>typeof v==='number'&&Number.isFinite(v);
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const $=id=>document.getElementById(id);
 const when=(iso,tz)=>{if(!iso)return '—';try{return new Intl.DateTimeFormat('pt-BR',{dateStyle:'short',timeStyle:'short',timeZone:tz||'America/Campo_Grande'}).format(new Date(iso));}catch(_){return String(iso).slice(0,16).replace('T',' ');}};
 const age=min=>!finite(min)?'—':min<90?`${min} min`:`${(min/60).toFixed(1).replace('.',',')} h`;
 function renderFreshness(state){
  const body=$('freshness-body'),summary=$('freshness-summary');if(!body)return;
  const f=state?.freshness||{},tz=state?.site?.timezone;
  const models=Object.entries(state?.ensemble_models||{});
  body.innerHTML=models.length?models.map(([name,m])=>{const fr=f.ensembles?.[name]||{};const run=m.model_run||{};
   return `<tr class="${m.state==='ok'?'':'bad'}"><td>${esc(name)}</td><td>${esc(m.state||'—')}</td><td>${esc(when(run.last_run_initialisation_utc,tz))}</td><td>${esc(when(run.last_run_availability_utc,tz))}</td><td>${esc(when(m.collected_at_utc,tz))} ${m.cache_hit?'<small>(cache)</small>':''}</td><td>${esc(age(fr.acquisition_age_min))}</td><td>${m.precipitation_native_step_hours?m.precipitation_native_step_hours+' h':'?'}</td><td>${m.precipitation_members??'—'} / ${m.gust_members??'—'}</td><td>${fr.newer_run_available_than_acquired===true?'<span class="warn">sim</span>':fr.newer_run_available_than_acquired===false?'não':'<span class="na">sem metadados</span>'}</td></tr>`;}).join(''):'<tr><td colspan="9" class="na">Sem inventário de modelos.</td></tr>';
  if(summary){
   const c=f.collection||{};
   summary.innerHTML=`Publicado ${esc(when(f.published_utc,tz))} (local) · ensembles válidos para chuva: <strong>${f.models_valid_rain??'—'}</strong>, rajadas: <strong>${f.models_valid_gusts??'—'}</strong> · aquisição mais antiga: ${esc(age(f.ensemble_oldest_acquisition_age_min))}, mais recente: ${esc(age(f.ensemble_newest_acquisition_age_min))} · previsão horária: ${esc(age(f.deterministic?.acquisition_age_min))}${c.run_id?` · execução ${esc(c.runner)} #${esc(c.run_id)} (${esc(c.event||'')})`:''}.<br><small>${esc(c.schedule_note||'')}</small>`;
  }
 }
 let loaded=null;
 async function loadDiagnostics(force=false){
  const box=$('diagnostics-panel');if(!box)return;
  if(loaded&&!force){paint(loaded);return;}
  box.textContent='Lendo diagnóstico publicado…';
  try{const r=await fetch('data/diagnostics.json',{cache:'no-cache'});if(!r.ok)throw Error('HTTP '+r.status);loaded=await r.json();paint(loaded);}
  catch(e){box.innerHTML=`<p class="caption">Diagnóstico central ainda não publicado nesta versão do site (${esc(e.message||e)}). Ele é gerado pelo coletor após cada execução.</p>`;}
 }
 function paint(d){
  const box=$('diagnostics-panel');if(!box)return;
  const tz='America/Campo_Grande';
  const loc=Object.entries(d.locations||{}).map(([id,l])=>`<tr><td>${esc(id)}</td><td class="${l.state==='ok'?'ok':'bad'}">${esc(l.state)}</td><td>${esc(when(l.issued_at_utc,tz))}</td><td>${l.models_valid_rain??'—'} / ${l.models_valid_gusts??'—'}</td><td>${esc(age(l.ensemble_oldest_acquisition_age_min))}</td><td>${(l.cache_hits||[]).length}</td><td>${esc(l.observations?.inmet_hourly||'—')} / ${esc(l.observations?.embrapa||'—')}</td><td>${Object.entries(l.errors||{}).map(([k,v])=>`${esc(k)}: ${esc(v)}`).join('<br>')||'—'}</td></tr>`).join('');
  const cad=d.cadence||{},q=d.http_quota_ledger||{},a=d.archive||{};
  const cooldowns=Object.entries(q.blocked_until_by_provider||{}).map(([source,until])=>`${source}: até ${when(until,tz)}`);
  if(q.blocked_until_utc)cooldowns.push(`bloqueio até ${when(q.blocked_until_utc,tz)}`);
  box.innerHTML=`<div class="diag-grid">
   <div class="diag-kpi"><small>Estado geral</small><strong class="${d.overall_state==='ok'?'ok':'warn'}">${esc(d.overall_state||'—')}</strong><span>${esc(when(d.generated_utc,tz))}</span></div>
   <div class="diag-kpi"><small>Execuções nas últimas 24 h</small><strong>${cad.runs_last_24h??'—'}<small> / ${cad.expected_runs_per_day??48} agendadas</small></strong><span>intervalo mediano ${esc(age(cad.median_gap_min))}, máximo ${esc(age(cad.max_gap_min))}</span></div>
   <div class="diag-kpi"><small>Chamadas equivalentes hoje (estimativa local)</small><strong>${q.equivalent_calls??'—'}</strong><span>${q.http_requests??'—'} requisições HTTP · dia ${esc(q.day||'—')}${cooldowns.length?' · '+esc(cooldowns.join(' · ')):''}</span></div>
   <div class="diag-kpi"><small>Arquivo científico</small><strong class="${a.severity==='ok'?'ok':'warn'}">${esc(a.severity||'—')}</strong><span>${a.manifest_count??'—'} manifestos · ${esc(when(a.updated_at_utc,tz))}</span></div>
  </div>
  <div class="scroll"><table><thead><tr><th>Local</th><th>Estado</th><th>Publicação</th><th>Modelos chuva / rajada</th><th>Aquisição mais antiga</th><th>Cache</th><th>Obs. INMET / Embrapa</th><th>Erros</th></tr></thead><tbody>${loc}</tbody></table></div>
  ${(d.risks||[]).length?`<ul class="risk-list">${d.risks.map(r=>`<li class="risk-inmet">${esc(r)}</li>`).join('')}</ul>`:''}
  <p class="caption">${esc(d.collection?.schedule_note||'')} ${esc(d.limits?.open_meteo_free||'')}</p>`;
 }
 function bind(){
  root.addEventListener?.('campo:forecast-rendered',()=>{try{renderFreshness(typeof state!=='undefined'?state:null);}catch(e){console.error('freshness render',e);}});
  document.getElementById('tabs')?.addEventListener('click',e=>{if(e.target.closest('button[data-tab="verification"]'))void loadDiagnostics();});
  document.getElementById('diagnostics-refresh')?.addEventListener('click',()=>void loadDiagnostics(true));
 }
 if(typeof document!=='undefined')bind();
 root.CampoDiagnostics={renderFreshness,loadDiagnostics,_test:{age,when}};
})(typeof window!=='undefined'?window:globalThis);
