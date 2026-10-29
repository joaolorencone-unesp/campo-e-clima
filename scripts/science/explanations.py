"""Optional language-model adapter. Weather facts are rendered by code only."""
from __future__ import annotations
import json
import os
from typing import Protocol
import requests
from .common import digest, now, packed, write_json
from .database import connect

PROMPT_VERSION='facts-only-1.0.0'
class Provider(Protocol):
    def select(self,facts:dict)->dict: ...

class NoneProvider:
    def select(self,facts):
        return {'fact_ids':list(facts),'model':'rules','usage':None}

class BlockedExternalProvider:
    def __init__(self,name):self.name=name
    def select(self,facts):
        raise ValueError(f'{self.name}: modalidade sem cobrança automática não comprovada; adaptador desativado')

class OllamaProvider:
    def __init__(self, model='qwen3:4b', timeout=30):
        self.model=model;self.timeout=timeout
    def select(self,facts):
        # Fixed loopback: no public server, proxy, external farm data or credentials.
        session=requests.Session();session.trust_env=False
        schema={'type':'object','properties':{'fact_ids':{'type':'array','items':{'type':'string','enum':list(facts)},'uniqueItems':True}},'required':['fact_ids'],'additionalProperties':False}
        r=session.post('http://127.0.0.1:11434/api/generate',json={
            'model':self.model,'stream':False,'format':schema,'options':{'temperature':0},
            'prompt':'Ordene os IDs dos fatos públicos por relevância. Retorne somente fact_ids. Não crie fatos. '+packed(facts).decode()},timeout=self.timeout,allow_redirects=False)
        r.raise_for_status();response=r.json()
        out=json.loads(response['response']);validate_selection(out,facts)
        return {**out,'model':response.get('model',self.model),'model_version':response.get('model'),
            'usage':{'input_tokens':response.get('prompt_eval_count'),'output_tokens':response.get('eval_count')}}

def validate_selection(response,facts):
    if set(response)!={'fact_ids'} or not isinstance(response['fact_ids'],list):
        raise ValueError('Resposta da IA fora do esquema')
    ids=response['fact_ids']
    if not ids or any(not isinstance(x,str) or x not in facts for x in ids) or len(set(ids))!=len(ids):
        raise ValueError('Resposta menciona fato inexistente ou repetido')

def explain(db,verification,output,*,provider=None):
    name=provider if provider is not None else os.environ.get('AI_PROVIDER','none')
    enabled=os.environ.get('AI_ENABLE','0')=='1'
    if not enabled:name='none'
    # Only public locations and structured diagnostic counts enter provider inputs.
    facts={'uncalibrated':'Frequências dos ensembles não são probabilidades calibradas.',
        'operation':'A avaliação meteorológica não autoriza voo ou aplicação e não define altura, dose, gotas ou velocidade.',
        'availability':'Sem observação confiável e teste temporal independente não há comprovação de precisão local.'}
    for loc in verification.get('locations',[]):
        facts[loc['id']]=f"{loc['name']}: {loc['forecast_runs']} produtos de previsão preservados; {loc['paired_values']} pares elegíveis no relatório."
    key=digest(packed(facts));day=now()[:10]
    limit=min(2,max(0,int(os.environ.get('AI_MAX_CALLS_PER_DAY','2'))))
    error=None;usage=None;model='rules';selected=list(facts);status='rules'
    with connect(db) as con:
        calls=con.execute("SELECT count(*) FROM ai_explanations WHERE provider!='none' AND substr(created_at_utc,1,10)=?",(day,)).fetchone()[0]
        try:
            if name!='none' and calls>=limit:raise ValueError('Cota diária de IA atingida')
            if name=='none':adapter=NoneProvider()
            elif name=='ollama':adapter=OllamaProvider(os.environ.get('AI_MODEL_ID') or 'qwen3:4b',min(30,int(os.environ.get('AI_TIMEOUT_SECONDS','30'))))
            else:adapter=BlockedExternalProvider(name)
            answer=adapter.select(facts);validate_selection({'fact_ids':answer['fact_ids']},facts)
            # Mandatory caveats cannot be removed by provider selection.
            selected=list(dict.fromkeys(answer['fact_ids']+['uncalibrated','operation','availability']))
            model=answer['model'];usage=answer.get('usage');status='validated_selection' if name!='none' else 'rules'
        except (ValueError,KeyError,TypeError,requests.RequestException) as exc:
            error=type(exc).__name__+': '+str(exc)[:200];status='rules_fallback'
        result={'provider':name,'effective_provider':'none' if status in ('rules','rules_fallback') else name,
            'model':model,'prompt_version':PROMPT_VERSION,'input_sha256':key,'created_at_utc':now(),
            'paragraphs':[facts[x] for x in selected],'validation_status':status,'usage':usage,'error':error,
            'limitations':['Somente seleção de fatos; texto meteorológico e valores gerados por regras','Nenhuma alteração nos cálculos']}
        ident=digest(packed(result))
        con.execute('INSERT OR IGNORE INTO ai_explanations VALUES(?,?,?,?,?,?,?,?,?,?)',
            (ident,name,model,PROMPT_VERSION,key,result['created_at_utc'],packed(result).decode(),status,packed(usage).decode(),error))
    write_json(output,result)
    return result
