"""AI bulletin: facts only, strict validation, free-tier allow-list, rule-based fallback."""
import datetime as dt
import json
from pathlib import Path
import pytest
import requests
from scripts import ai_bulletin as ab

NOW = dt.datetime(2026, 11, 5, 12, 0, tzinfo=dt.timezone.utc)


def public():
    times = [f'2026-11-05T{h:02d}:00' for h in range(24)] + [f'2026-11-06T{h:02d}:00' for h in range(24)]
    return {'site': {'id': 'navirai', 'utc_offset_seconds': -14400}, 'issued_at_utc': '2026-11-05T11:00:00+00:00',
            'deterministic': {'utc_offset_seconds': -14400, 'hourly': {'time': times, 'precipitation': [0.5] * 48, 'temperature_2m': [20 + (i % 12) for i in range(48)], 'wind_gusts_10m': [15] * 47 + [38]}},
            'rain_ensemble_daily': [{'date': '2026-11-05', 'p50_mm': 8.7, 'p10_mm': 0.6, 'p90_mm': 26.2, 'p_gt_1_mm': .889, 'p_gt_20_mm': .19, 'model_count': 8},
                                    {'date': '2026-11-06', 'p50_mm': 1.2, 'p10_mm': 0, 'p90_mm': 6, 'p_gt_1_mm': .52, 'p_gt_20_mm': .01, 'model_count': 8}],
            'rain_model_agreement_daily': [{'date': '2026-11-06', 'agreement_label': 'media', 'wet_majority_models': 4, 'models': 8, 'model_mean_min_mm': 0.4, 'model_mean_max_mm': 5.1}],
            'rain_ensemble_accumulated': [{'span_days': 7, 'p50_mm': 41, 'p10_mm': 18, 'p90_mm': 70, 'p_gt_25_mm': .78}],
            'rain_dry_spell': {'p_ge_3_days': .18, 'end': '2026-11-11'},
            'gust_ensemble_daily': [{'date': '2026-11-05', 'p_gt_40_kmh': .35, 'model_count': 3}],
            'official': {'inmet_alerts': {'municipal_alerts': [{'id': 1}, {'id': 2}]}},
            'freshness': {'ensemble_oldest_acquisition_age_min': 322, 'models_valid_rain': 8}}


def test_facts_cover_the_published_numbers_and_rule_text_is_deterministic():
    sheet = ab.build_facts(public(), now=NOW)
    text = '\n'.join(sheet['facts'])
    assert 'Chuva determinística prevista nas próximas 24 h: 12,0 mm' in text
    assert 'mediana 8,7 mm' in text and '89% dos membros' in text and 'Acumulado em 7 dias: mediana 41 mm' in text
    assert '2 aviso(s)' in text and 'não probabilidades calibradas' in sheet['facts'][-1]
    assert ab.rule_based_text(sheet) == ab.rule_based_text(ab.build_facts(public(), now=NOW))
    assert sheet['sha256'] == ab.build_facts(public(), now=NOW)['sha256']


def test_validation_rejects_invented_numbers_and_promises():
    sheet = ab.build_facts(public(), now=NOW)
    assert ab.validate_text('Chuva provável: mediana 8,7 mm amanhã, 89% dos membros com mais de 1 mm.', sheet)[0]
    assert not ab.validate_text('Deve chover 35 mm amanhã.', sheet)[0]
    assert not ab.validate_text('Aplicação liberada, chuva 8,7 mm.', sheet)[0]
    assert not ab.validate_text(' '.join(['palavra'] * 200), sheet)[0]
    assert not ab.validate_text('', sheet)[0]


def test_generate_defaults_to_rules_and_refuses_unknown_or_paid_providers(monkeypatch, tmp_path):
    monkeypatch.delenv('AI_BULLETIN_PROVIDER', raising=False)
    out = ab.generate(public(), now=NOW, ledger=tmp_path / 'l.json')
    assert out['status'] == 'rules' and out['provider'] == 'none' and out['text'] == out['rule_based_text']
    out = ab.generate(public(), now=NOW, provider='openai-paid', ledger=tmp_path / 'l.json')
    assert out['status'] == 'rules_fallback' and 'não permitido' in out['error']
    monkeypatch.setenv('AI_ALLOW_PAID', '1')
    assert ab.generate(public(), now=NOW, provider='groq', ledger=tmp_path / 'l.json')['status'] == 'rules_fallback'


def test_generate_uses_llm_when_valid_and_falls_back_when_rejected(monkeypatch, tmp_path):
    monkeypatch.setenv('GROQ_API_KEY', 'test-key')
    monkeypatch.setenv('AI_ALLOW_PAID', '0')
    calls = []
    class Session:
        def __init__(self, text): self.text = text
        def post(self, url, headers=None, json=None, timeout=None):
            calls.append((url, headers['Authorization'], json['model']))
            r = requests.Response(); r.status_code = 200
            r._content = __import__('json').dumps({'model': json['model'], 'choices': [{'message': {'content': self.text}}], 'usage': {'total_tokens': 100}}).encode()
            return r
    good = 'Chuva provável hoje: mediana 8,7 mm (0,6 a 26,2 mm), 89% dos membros com mais de 1 mm. Percentuais são frequências de membros, não probabilidades calibradas.'
    out = ab.generate(public(), now=NOW, provider='groq', session=Session(good), ledger=tmp_path / 'l.json')
    assert out['status'] == 'llm' and out['text'] == good and out['provider'] == 'groq'
    assert calls[0][0].startswith('https://api.groq.com/openai/v1/') and calls[0][1] == 'Bearer test-key'
    bad = ab.generate(public(), now=NOW, provider='groq', session=Session('Vai chover 55 mm com certeza.'), ledger=tmp_path / 'l.json')
    assert bad['status'] == 'rules_fallback' and bad['text'] == bad['rule_based_text'] and 'rejeitada' in bad['error']
    assert 'test-key' not in json.dumps(bad)


def test_daily_ledger_caps_calls(monkeypatch, tmp_path):
    monkeypatch.setenv('GROQ_API_KEY', 'k'); monkeypatch.setenv('AI_MAX_CALLS_PER_DAY', '1')
    class Session:
        def post(self, *a, **k):
            r = requests.Response(); r.status_code = 200; r._content = b'{"choices":[{"message":{"content":"Mediana 8,7 mm. Percentuais s\xc3\xa3o frequ\xc3\xaancias de membros, n\xc3\xa3o probabilidades calibradas."}}]}'; return r
    ledger = tmp_path / 'ledger.json'
    assert ab.generate(public(), now=NOW, provider='groq', session=Session(), ledger=ledger)['status'] == 'llm'
    second = ab.generate(public(), now=NOW, provider='groq', session=Session(), ledger=ledger)
    assert second['status'] == 'rules_fallback' and 'cota' in second['error']
