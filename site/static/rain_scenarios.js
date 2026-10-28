/* Campo e Clima v1.6 — Cenários exclusivos e comparação dos ensembles.
   Cálculos puros: não cria previsões ou probabilidades, apenas exibe frequências já calculadas. */
(function(root){
 'use strict';
 function value(x){return x===null||x===undefined||x===''||!Number.isFinite(Number(x))?null:Number(x);}
 function frequencies(row){
  const p01=value(row?.p_gt_0_1_mm),p1=value(row?.p_gt_1_mm),p5=value(row?.p_gt_5_mm);
  if([p01,p1,p5].some(x=>x===null||x<0||x>1))return null;
  // They must be non-increasing for nested precipitation thresholds.
  if(p01+1e-8<p1||p1+1e-8<p5)return null;
  return {p01,p1,p5};
 }
 function bands(row){
  const p=frequencies(row);if(!p)return null;
  const result={almostDry:1-p.p01,veryLight:p.p01-p.p1,light:p.p1-p.p5,higher:p.p5};
  for(const k of Object.keys(result))result[k]=Math.max(0,Math.min(1,result[k]));
  return result;
 }
 function modelAgreement(modelRows,day){
  if(!Array.isArray(modelRows)||typeof day!=='string')return [];
  const out=[];
  for(const row of modelRows){
   if(row?.date!==day||!row?.model||!Number.isInteger(row.members)||row.members<=0)continue;
   const p=frequencies(row);if(!p)continue;
   out.push({model:row.model,members:row.members,p01:p.p01,p1:p.p1,veryLight:p.p01-p.p1});
  }
  return out;
 }
 root.CampoRain={bands,modelAgreement};
 if(typeof module==='object'&&module.exports)module.exports=root.CampoRain;
})(typeof window!=='undefined'?window:globalThis);
