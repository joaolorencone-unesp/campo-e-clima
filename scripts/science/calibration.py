"""Shadow experiments only; chronological train/calibration/test with purging."""
from __future__ import annotations
import datetime as dt
import json
import math
from .common import digest, instant, now, packed, write_json
from .database import connect
from .evaluation import paired_rows, EMPTY_MESSAGE
from .metrics import deterministic, brier_score, brier_skill_score, monotone_probabilities

def chronological_split(rows, *, gap_days=None):
    if gap_days is None:
        leads=[r.get("lead_hours") or ((instant(r["valid_at_utc"])-instant(r["available_at_utc"])).total_seconds()/3600 if r.get("available_at_utc") else 0) for r in rows]
        gap_days=max(7,math.ceil(max(leads,default=0)/24))
    dates=sorted({r['valid_at_utc'] for r in rows})
    if len(dates)<30:raise ValueError('Datas insuficientes para três blocos temporais')
    a=instant(dates[int(len(dates)*.6)]);b=instant(dates[int(len(dates)*.8)])
    gap=dt.timedelta(days=gap_days)
    train=[r for r in rows if instant(r['valid_at_utc'])<a-gap]
    calibration=[r for r in rows if a<=instant(r['valid_at_utc'])<b-gap]
    test=[r for r in rows if instant(r['valid_at_utc'])>=b]
    # A run may not occur in multiple partitions, including a blended run's constituents.
    def runs(block):return {v for r in block for v in r.get('lineage_run_ids',[r['run_id']])}
    if runs(train)&runs(calibration) or runs(train)&runs(test) or runs(calibration)&runs(test):
        raise ValueError('Vazamento: rodada atravessa partições')
    # Never train a live-origin test on a reference unavailable at that origin.
    for block,following in ((train,calibration),(train+calibration,test)):
        origins=[instant(r['available_at_utc']) for r in following if r.get('available_at_utc')]
        if origins and any(r.get('observation_available_at_utc') and instant(r['observation_available_at_utc'])>=min(origins) for r in block):
            raise ValueError('Observação de treino disponível somente após origem de avaliação')
    return train,calibration,test

def experiment(db, output):
    from collections import defaultdict
    grouped=defaultdict(list)
    rows,_=paired_rows(db)
    for r in rows:
        grouped[(r['location_id'],r['model_id'],r['variable'],r['horizon'],r['lead_basis'],r['station_id'],r['method'])].append(r)
    report={'created_at_utc':now(),'status':'insufficient_data','message':EMPTY_MESSAGE,'experiments':[],
        'primary_forecast_replaced':False,'minimum_policy':'90 dias distintos; 200 treino, 50 calibração, 50 teste; política conservadora experimental, não garantia de poder estatístico'}
    for key,sample in grouped.items():
        if key[2] not in ('temperature_2m','wind_speed_10m','wind_gusts_10m','precipitation'):continue
        if len({r['valid_at_utc'][:10] for r in sample})<90:continue
        try:train,cal,test=chronological_split(sample)
        except ValueError as exc:
            report['experiments'].append({'group':key,'status':'rejected','reason':str(exc)});continue
        if min(len(train)/200,len(cal)/50,len(test)/50)<1:continue
        import numpy as np
        from sklearn.linear_model import LinearRegression, Ridge, LogisticRegression
        from sklearn.ensemble import HistGradientBoostingRegressor, HistGradientBoostingClassifier
        from sklearn.isotonic import IsotonicRegression
        x=lambda block:np.array([[r['prediction']] for r in block])
        y=lambda block:np.array([r['observation'] for r in block])
        dataset=digest(packed(sample)); split={'train':len(train),'calibration':len(cal),'test':len(test),'gap_days':7,
            'start_test':min(r['valid_at_utc'] for r in test),'end_test':max(r['valid_at_utc'] for r in test),'feature_version':'prediction_only_v1','data_sha256':dataset}
        evaluations=[]
        if key[2]=='precipitation':
            thresholds=(.1,1,3,5,10,20);predictions=[];baseline=[]
            adequate=True
            for threshold in thresholds:
                labels=(y(train)>threshold).astype(int);cal_labels=(y(cal)>threshold).astype(int)
                if min(sum(labels),len(labels)-sum(labels),sum(cal_labels),len(cal_labels)-sum(cal_labels))<20:
                    adequate=False;break
                model=LogisticRegression(random_state=22).fit(x(train),labels)
                iso=IsotonicRegression(out_of_bounds='clip').fit(model.predict_proba(x(cal))[:,1],cal_labels)
                predictions.append(iso.predict(model.predict_proba(x(test))[:,1]).tolist())
                baseline.append(float(np.mean(labels)))
            if not adequate:continue
            adjusted=[monotone_probabilities([predictions[j][i] for j in range(len(thresholds))]) for i in range(len(test))]
            for j,threshold in enumerate(thresholds):
                probs=[p[j] for p in adjusted];obs=(y(test)>threshold).astype(int).tolist()
                evaluations.append({'method':'M3 logistic + isotonic','threshold':threshold,
                    'brier':brier_score(probs,obs),'brier_skill_score':brier_skill_score(probs,obs,[baseline[j]]*len(obs))})
            # Wet-amount regression is evaluated on observed wet cases, labelled conditional.
            wet=[r for r in train if r['observation']>.1];wet_test=[r for r in test if r['observation']>.1]
            if len(wet)>=100 and len(wet_test)>=30:
                amount=Ridge(alpha=1).fit(x(wet),np.log1p(y(wet)))
                forecast=np.maximum(0,np.expm1(amount.predict(x(wet_test)))).tolist()
                evaluations.append({'method':'M3 wet amount Ridge','conditional_on_observed_wet':True,'metrics':deterministic(forecast,y(wet_test).tolist())})
        else:
            actual=y(test).tolist();raw=[r['prediction'] for r in test]
            bias=float(np.mean(y(train)-x(train)[:,0]))
            evaluations=[{'method':'M0 train climatology','metrics':deterministic([float(np.mean(y(train)))]*len(test),actual)},
                {'method':key[6]+' raw','metrics':deterministic(raw,actual)},
                {'method':'M3 bias','metrics':deterministic([v+bias for v in raw],actual),'parameters':{'bias':bias}}]
            for name,model in [('M3 linear',LinearRegression()),('M3 Ridge',Ridge(alpha=1)),
                               ('M4 Gradient Boosting',HistGradientBoostingRegressor(max_iter=100,max_leaf_nodes=7,random_state=22))]:
                model.fit(x(train),y(train));prediction=model.predict(x(test))
                if key[2].startswith('wind_'):prediction=np.maximum(0,prediction)
                evaluations.append({'method':name,'metrics':deterministic(prediction.tolist(),actual),
                    'parameters':model.get_params(),'fit_manifest':'Refazer treino com dataset SHA e versões fixadas; não carregar pickle externo'})
        item={'group':key,'status':'experimental_test_only','split':split,'evaluations':evaluations,
            'superiority_claim':False,'calibrated_primary':False,'uncertainty':'Intervalos e teste de robustez ainda requeridos antes de qualquer promoção'}
        report['experiments'].append(item)
        with connect(db) as con:
            con.execute('INSERT OR IGNORE INTO calibration_datasets VALUES(?,?,?,?,?,?)',
                (dataset,key[0],dataset,packed(split).decode(),'observed_basic_qc',now()))
            for evaluation in evaluations:
                ident=digest(packed([dataset,evaluation['method']]))
                con.execute('INSERT OR IGNORE INTO calibration_models VALUES(?,?,?,?,?,?)',
                    (ident,dataset,evaluation['method'],'1.0.0',packed(evaluation.get('parameters',{})).decode(),'shadow_experiment'))
                eid=digest(packed([ident,evaluation]))
                con.execute('INSERT OR IGNORE INTO model_evaluations VALUES(?,?,?,?,?,?)',
                    (eid,ident,'independent_temporal_test',len(test),packed(evaluation).decode(),now()))
    if report['experiments']:report['status']='experiments_recorded'
    write_json(output,report)
    return report
