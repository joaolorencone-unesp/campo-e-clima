'use strict';
/** Campo e Clima v3 — two levels of use (simple / advanced) and five navigation areas.
 * All original tabs remain in the DOM (#tabs button[data-tab]); this module only groups
 * them and hides advanced-only ones in simple mode. The choice persists per browser.
 */
(function(root){
 const GROUPS=[
  {id:'overview',label:'Visão geral',tabs:['overview']},
  {id:'rain',label:'Chuva e previsões',tabs:['rain','extended']},
  {id:'operations',label:'Operações agrícolas',tabs:['agro','spray','wind']},
  {id:'maps',label:'Mapas e monitoramento',tabs:['maps','observations']},
  {id:'science',label:'Ciência e dados',tabs:['precision','verification','history-nasa','machines']}];
 const SIMPLE_TABS=new Set(['overview','agro','maps','observations','rain']);
 const STORAGE_KEY='campo-mode';
 function groupFor(tab){return GROUPS.find(g=>g.tabs.includes(tab))?.id||'science';}
 function readMode(storage){try{const v=storage?.getItem?.(STORAGE_KEY);return v==='advanced'?'advanced':v==='simple'?'simple':null;}catch(_){return null;}}
 function writeMode(storage,mode){try{storage?.setItem?.(STORAGE_KEY,mode);}catch(_){}}
 function visibleTabs(mode){return mode==='simple'?[...SIMPLE_TABS]:GROUPS.flatMap(g=>g.tabs);}
 let mode='simple';
 function applyMode(next,{persist=true}={}){
  mode=next==='advanced'?'advanced':'simple';
  if(typeof document==='undefined')return mode;
  document.body.classList.toggle('mode-simple',mode==='simple');
  document.body.classList.toggle('mode-advanced',mode==='advanced');
  for(const button of document.querySelectorAll('#tabs button[data-tab]')){
   if(button.dataset.tab==='machines')continue; // stays hidden until validated
   const show=mode==='advanced'||SIMPLE_TABS.has(button.dataset.tab);
   button.hidden=!show;button.setAttribute('aria-hidden',show?'false':'true');
  }
  for(const chip of document.querySelectorAll('#mode-switch button'))chip.classList.toggle('active',chip.dataset.mode===mode);
  const active=document.querySelector('#tabs button.active');
  if(active&&active.hidden)document.querySelector('#tabs button[data-tab="overview"]')?.click();
  if(persist)writeMode(root.localStorage,mode);
  root.dispatchEvent?.(new CustomEvent('campo:mode-changed',{detail:{mode}}));
  return mode;
 }
 function decorate(){
  const tabs=document.getElementById('tabs');if(!tabs)return;
  for(const button of tabs.querySelectorAll('button[data-tab]'))button.dataset.group=groupFor(button.dataset.tab);
  const bar=document.getElementById('nav-groups');
  if(bar&&!bar.children.length){
   bar.innerHTML=GROUPS.map(g=>`<button type="button" data-group="${g.id}">${g.label}</button>`).join('');
   bar.addEventListener('click',e=>{const chip=e.target.closest('button[data-group]');if(!chip)return;
    const first=visibleTabs(mode).find(t=>groupFor(t)===chip.dataset.group&&t!=='machines');
    if(first)document.querySelector(`#tabs button[data-tab="${first}"]`)?.click();});
  }
  tabs.addEventListener('click',e=>{const b=e.target.closest('button[data-tab]');if(b)highlight(b.dataset.tab);});
  highlight(tabs.querySelector('button.active')?.dataset.tab||'overview');
 }
 function highlight(tab){const g=groupFor(tab);for(const chip of document.querySelectorAll('#nav-groups button'))chip.classList.toggle('active',chip.dataset.group===g);
  const tabs=document.getElementById('tabs');if(tabs)tabs.dataset.activeGroup=g;}
 function init(){
  if(typeof document==='undefined')return;
  decorate();
  const stored=readMode(root.localStorage);
  let initial=stored||'simple';
  try{const q=new URL(root.location.href).searchParams.get('modo');if(q==='avancado')initial='advanced';if(q==='simples')initial='simple';}catch(_){}
  applyMode(initial,{persist:Boolean(stored)});
  document.getElementById('mode-switch')?.addEventListener('click',e=>{const b=e.target.closest('button[data-mode]');if(b)applyMode(b.dataset.mode);});
 }
 root.CampoNav={GROUPS,SIMPLE_TABS,groupFor,visibleTabs,applyMode,init,getMode:()=>mode,_test:{readMode,writeMode}};
 if(typeof document!=='undefined'){if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();}
 if(typeof module==='object'&&module.exports)module.exports=root.CampoNav;
})(typeof window!=='undefined'?window:globalThis);
