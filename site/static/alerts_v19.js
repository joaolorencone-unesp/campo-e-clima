'use strict';
/* Display confirmed municipal INMET notices without visually duplicating the
 * same phenomenon on consecutive days. A visual group is NOT one official notice. */
(function(root){
  const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const slug=a=>[a.type||'',a.severity||'',...(Array.isArray(a.risks)?a.risks:[])].map(x=>String(x).trim().toLocaleLowerCase('pt-BR')).join('|');
  const date=x=>/^\d{4}-\d{2}-\d{2}$/.test(x||'')?x:null;
  const fmt=d=>d?d.slice(8,10)+'/'+d.slice(5,7):'data não informada';
  function group(list){
    const groups=new Map();
    for(const notice of (Array.isArray(list)?list:[])){
      const k=slug(notice),rec=groups.get(k)||{type:notice.type||'Aviso',severity:notice.severity||'Não informada',risks:Array.isArray(notice.risks)?notice.risks:[],items:[]};
      rec.items.push(notice);groups.set(k,rec);
    }
    return [...groups.values()].map(g=>{
      g.items.sort((a,b)=>String(a.start_date_source||'').localeCompare(String(b.start_date_source||'')));
      const starts=g.items.map(a=>date(a.start_date_source)).filter(Boolean),ends=g.items.map(a=>date(a.end_date_source)).filter(Boolean);
      g.start=starts.length?starts.sort()[0]:null;g.end=ends.length?ends.sort().at(-1):null;
      return g;
    });
  }
  function render(list){
    const items=group(list);
    if(!items.length)return '<div class="notice">Nenhum aviso confirmado nesta consulta. Consulte a fonte oficial em caso de instabilidade.</div>';
    return `<div class="inmet-summary"><strong>⚠ ${list.length} aviso(s) oficial(is) • ${items.length} tipo(s) agrupado(s) visualmente</strong><span>Os avisos continuam independentes e preservam suas vigências oficiais. Horários apresentados como informados pela fonte, sem conversão de fuso.</span></div>`+
      items.map(g=>`<article class="inmet-group"><div class="inmet-group-top"><div><strong>${esc(g.type)} · ${esc(g.severity)}</strong><p>${g.items.length} aviso(s) · ${fmt(g.start)} a ${fmt(g.end)} <small>(datas de origem, sem fuso confirmado)</small></p></div><span class="inmet-badge">${g.items.length} registro(s)</span></div>
       <p><b>Riscos citados:</b> ${esc(g.risks.join(' · ').slice(0,540)||'Consultar texto oficial')}</p>
       <details><summary>Ver cada aviso e sua vigência (${g.items.length})</summary><div class="inmet-details">${g.items.map((a,i)=>`<p><b>Aviso ${i+1}:</b> ${esc(a.start_date_source||'—')} ${esc(a.start_hour_source||'hora não informada')} → ${esc(a.end_date_source||'—')} ${esc(a.end_hour_source||'hora não informada')}</p>`).join('')}</div></details></article>`).join('')+
      '<p class="caption">Somente avisos com abrangência municipal verificada pelo coletor. Ausência de aviso não comprova ausência de risco. <a href="https://alertas2.inmet.gov.br/" target="_blank" rel="noopener">Consultar todos os avisos oficiais ↗</a></p>';
  }
  root.CampoAlerts={group,render};
})(window);
