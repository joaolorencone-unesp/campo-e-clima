"""Interpretive bulletin: rule-based text always; optional free-tier LLM rewrite, strictly fact-bound.

Design
- The facts come only from the published forecast file (numbers already computed and labelled).
- A deterministic rule-based bulletin is always produced and published as the baseline.
- When an LLM provider is enabled (free tier, key in a GitHub secret), the model may only
  rephrase the facts. Any number in its answer that is not in the fact sheet, any forbidden
  promise ("garantido", "liberado"), or any schema problem rejects the answer and the
  rule-based text is kept. Nothing paid is ever called: providers are an allow-list of
  OpenAI-compatible endpoints whose free tiers do not require billing.
"""
from __future__ import annotations
import datetime as dt
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any
import requests

PROMPT_VERSION = 'bulletin-facts-1.0'
PROVIDERS = {
    # name: (base_url, env var with the key, default model, note). Only tiers that do not bill
    # without an explicit upgrade; an invalid model or exhausted quota falls back to rules.
    'github': ('https://models.github.ai/inference', 'GITHUB_MODELS_TOKEN', 'openai/gpt-4.1-mini', 'GitHub Models (gratuito com GITHUB_TOKEN em Actions; limites por minuto/dia)'),
    'groq': ('https://api.groq.com/openai/v1', 'GROQ_API_KEY', 'openai/gpt-oss-20b', 'Groq free tier (limites por minuto/dia)'),
    'gemini': ('https://generativelanguage.googleapis.com/v1beta/openai', 'GEMINI_API_KEY', 'gemini-2.5-flash', 'Google AI Studio free tier (projeto sem faturamento)'),
    'openrouter': ('https://openrouter.ai/api/v1', 'OPENROUTER_API_KEY', 'meta-llama/llama-3.3-70b-instruct:free', 'OpenRouter modelos :free'),
    'cloudflare': ('https://api.cloudflare.com/client/v4/accounts/{account}/ai/v1', 'CLOUDFLARE_API_TOKEN', '@cf/meta/llama-3.3-70b-instruct-fp8-fast', 'Cloudflare Workers AI (10 000 neurons/dia no plano Free, sem cobrança excedente)'),
    'ollama': ('http://127.0.0.1:11434/v1', '', 'qwen3:4b', 'Ollama local (sem rede externa)'),
}
FORBIDDEN = ('garant', 'liberad', 'autoriz', 'certeza absoluta', 'com certeza', '100%', 'pulveriz', 'aplic', 'recomend', 'janela', 'ideal para',
             'favorável para', 'seguro para', 'pode-se', 'deve-se')
NUMBER_WORDS = re.compile(r'\b(dois|duas|tr[eê]s|quatro|cinco|seis|sete|oito|nove|dez|onze|doze|treze|quatorze|catorze|quinze|dezesseis|dezessete|dezoito|dezenove|vinte|trinta|quarenta|cinquenta|sessenta|setenta|oitenta|noventa|cem|cento|mil|milh[aã]o|milh[oõ]es)\b', re.I)
MAX_WORDS = 170


def _finite(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v == v


def _num(v: Any, d: int = 1) -> str:
    return (f'{v:.{d}f}').replace('.', ',') if _finite(v) else '—'


def _local_date(now: dt.datetime, offset_seconds: int) -> str:
    return (now + dt.timedelta(seconds=offset_seconds)).date().isoformat()


def build_facts(public: dict, *, now: dt.datetime | None = None) -> dict:
    """Fact sheet: short labelled statements plus the set of numbers the LLM may use."""
    now = now or dt.datetime.now(dt.timezone.utc)
    offset = (public.get('site') or {}).get('utc_offset_seconds')
    if not _finite(offset):
        offset = ((public.get('deterministic') or {}).get('utc_offset_seconds')) if _finite((public.get('deterministic') or {}).get('utc_offset_seconds')) else -14400
    today = _local_date(now, int(offset))
    tomorrow = (dt.date.fromisoformat(today) + dt.timedelta(days=1)).isoformat()
    facts: list[str] = []
    numbers: set[str] = set()

    def add(text: str, *values: Any):
        facts.append(text)
        for v in values:
            if _finite(v):
                numbers.add(_num(v, 0)); numbers.add(_num(v, 1)); numbers.add(_num(v, 2))
                numbers.add(f'{v:.0f}'); numbers.add(f'{v:.1f}')

    det = public.get('deterministic') or {}
    hourly = det.get('hourly') or {}
    times = hourly.get('time') or []
    local_now = now + dt.timedelta(seconds=int(offset))
    future = [i for i, t in enumerate(times) if t[:16] > local_now.strftime('%Y-%m-%dT%H:%M')]
    rain_window = None
    if future:
        rain24 = [hourly.get('precipitation', [None] * len(times))[i] for i in future[:24]]
        if len(rain24) == 24 and all(_finite(x) for x in rain24):
            ends = [dt.datetime.fromisoformat(times[i][:16]) for i in future[:24]]
            hour = dt.timedelta(hours=1)
            if all(b - a == hour for a, b in zip(ends, ends[1:])):
                rain_window = {'start': (ends[0] - hour).isoformat(timespec='minutes'), 'end': ends[-1].isoformat(timespec='minutes')}
                add(f'Chuva determinística prevista nas próximas 24 h: {_num(sum(rain24))} mm.', sum(rain24))
        temps = [hourly.get('temperature_2m', [None] * len(times))[i] for i in future[:24]]
        temps = [x for x in temps if _finite(x)]
        if temps:
            add(f'Temperatura nas próximas 24 h entre {_num(min(temps), 0)} e {_num(max(temps), 0)} °C.', min(temps), max(temps))
        gusts = [hourly.get('wind_gusts_10m', [None] * len(times))[i] for i in future[:24]]
        gusts = [x for x in gusts if _finite(x)]
        if gusts:
            add(f'Rajada máxima prevista nas próximas 24 h: {_num(max(gusts), 0)} km/h.', max(gusts))
    daily = {r['date']: r for r in public.get('rain_ensemble_daily') or [] if isinstance(r, dict)}
    for label, day in (('hoje', today), ('amanhã', tomorrow)):
        r = daily.get(day)
        if r and _finite(r.get('p50_mm')):
            clauses, values = [f'Ensembles para {label} ({day}): mediana {_num(r.get("p50_mm"))} mm'], [r.get('p50_mm')]
            if _finite(r.get('p10_mm')) and _finite(r.get('p90_mm')):
                clauses.append(f'faixa P10–P90 {_num(r.get("p10_mm"))}–{_num(r.get("p90_mm"))} mm'); values += [r.get('p10_mm'), r.get('p90_mm')]
            if _finite(r.get('p_gt_1_mm')):
                clauses.append(f'{_num(r["p_gt_1_mm"] * 100, 0)}% dos membros com mais de 1 mm'); values.append(r['p_gt_1_mm'] * 100)
            if _finite(r.get('p_gt_20_mm')):
                clauses.append(f'{_num(r["p_gt_20_mm"] * 100, 0)}% acima de 20 mm'); values.append(r['p_gt_20_mm'] * 100)
            if _finite(r.get('model_count')):
                clauses.append(f'{r.get("model_count")} modelos'); values.append(r.get('model_count'))
            add(', '.join(clauses) + '.', *values)
    for a in public.get('rain_model_agreement_daily') or []:
        if a.get('date') in (today, tomorrow):
            add(f'Concordância {a.get("agreement_label")} entre modelos em {a["date"]}: {a.get("wet_majority_models")} de {a.get("models")} modelos apontam chuva; médias por modelo de {_num(a.get("model_mean_min_mm"))} a {_num(a.get("model_mean_max_mm"))} mm.',
                a.get('wet_majority_models'), a.get('models'), a.get('model_mean_min_mm'), a.get('model_mean_max_mm'))
    acc = [x for x in public.get('rain_ensemble_accumulated') or [] if x.get('span_days') in (7, 5) and _finite(x.get('p50_mm'))]
    if acc:
        x = sorted(acc, key=lambda a: -a['span_days'])[0]
        text = f'Acumulado em {x["span_days"]} dias: mediana {_num(x.get("p50_mm"), 0)} mm (P10–P90 {_num(x.get("p10_mm"), 0)}–{_num(x.get("p90_mm"), 0)} mm)'
        values = [x['span_days'], x.get('p50_mm'), x.get('p10_mm'), x.get('p90_mm')]
        if _finite(x.get('p_gt_25_mm')):
            text += f', {_num(x["p_gt_25_mm"] * 100, 0)}% dos membros acima de 25 mm'; values.append(x['p_gt_25_mm'] * 100)
        add(text + '.', *values)
    dry = public.get('rain_dry_spell') or {}
    if _finite(dry.get('p_ge_3_days')):
        add(f'Sequência de dias quase secos: {_num(dry["p_ge_3_days"] * 100, 0)}% das trajetórias com 3 dias ou mais até {dry.get("end")}.', dry['p_ge_3_days'] * 100)
    gust_days = [g for g in public.get('gust_ensemble_daily') or [] if g.get('date', '') >= today and _finite(g.get('p_gt_40_kmh')) and g['p_gt_40_kmh'] >= .3]
    for g in gust_days[:2]:
        add(f'Rajadas acima de 40 km/h em {g["date"]}: {_num(g["p_gt_40_kmh"] * 100, 0)}% dos membros ({g.get("model_count")} modelos com rajadas).', g['p_gt_40_kmh'] * 100, g.get('model_count'))
    alerts = ((public.get('official') or {}).get('inmet_alerts') or {}).get('municipal_alerts') or []
    if alerts:
        add(f'{len(alerts)} aviso(s) oficial(is) do INMET vigente(s) para o município.', len(alerts))
    fresh = public.get('freshness') or {}
    if _finite(fresh.get('ensemble_oldest_acquisition_age_min')):
        add(f'Ensembles adquiridos há até {_num(fresh["ensemble_oldest_acquisition_age_min"] / 60, 1)} h; {fresh.get("models_valid_rain")} modelos válidos para chuva.', fresh['ensemble_oldest_acquisition_age_min'] / 60, fresh.get('models_valid_rain'))
    facts.append('Percentuais são frequências de membros dos ensembles, não probabilidades calibradas; este texto não é orientação operacional.')
    sheet = {'location_id': (public.get('site') or {}).get('id'), 'date_local': today, 'facts': facts, 'numbers': sorted(numbers),
             'issued_at_utc': public.get('issued_at_utc'), 'rain_24h_window_local': rain_window}
    sheet['sha256'] = hashlib.sha256(json.dumps(sheet, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return sheet


def rule_based_text(sheet: dict) -> str:
    """Deterministic Portuguese bulletin assembled from the fact sheet (always available)."""
    facts = [f for f in sheet['facts'] if not f.startswith('Percentuais são')]
    if not facts:
        return 'Não há previsão publicada suficiente para redigir o boletim.'
    return ' '.join(facts) + ' ' + sheet['facts'][-1]


UNIT_RE = r'(?:mm|%|°C|km/h|h\b|modelos|dias|aviso)'
NUMBER_RE = r'(?<![\w.,])[-−]?\d+(?:[.,]\d{1,2})?(?![\d.,]?\d)'
DATE_RE = re.compile(r'\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b')
UNIT_WORDS = (('por cento', '%'), ('porcento', '%'), ('graus celsius', '°C'), ('graus', '°C'), ('milímetros', 'mm'), ('milimetros', 'mm'),
              ('quilômetros por hora', 'km/h'), ('quilometros por hora', 'km/h'), ('horas', 'h'), ('hora', 'h'))


def _value_key(raw: str) -> str | None:
    if not re.fullmatch(r'[-−]?\d+(?:[.,]\d{1,2})?', raw):
        return None
    return f'{float(raw.replace("−", "-").replace(",", ".")):.1f}'


def _normalize(text: str) -> str:
    low = text.lower()
    for word, unit in UNIT_WORDS:
        low = re.sub(rf'(?<=\d)\s*{word}\b', ' ' + unit, low)
    return low


def _numbers_with_units(text: str) -> list[tuple[str, str | None]]:
    """Numbers with the unit that follows them; a range (0,6–26,2 mm, 20 e 31 °C) gives both ends the unit."""
    pattern = re.compile(rf'({NUMBER_RE})(?:\s*(?:–|-|a|e)\s*({NUMBER_RE}))?\s*({UNIT_RE})?', re.I)
    out = []
    for m in pattern.finditer(text):
        unit = m.group(3)
        unit = unit.lower() if unit and unit.lower() != '°c' else unit
        unit = '°C' if unit and unit.lower() == '°c' else unit
        out.append((m.group(1), unit))
        if m.group(2):
            out.append((m.group(2), unit))
    return out


def fact_dates(sheet: dict) -> set[str]:
    dates = set()
    for text in sheet['facts']:
        for d in re.findall(r'\b(\d{4})-(\d{2})-(\d{2})\b', text):
            y, mo, da = d
            dates |= {f'{y}-{mo}-{da}', f'{int(da)}/{int(mo)}', f'{da}/{mo}', f'{da}/{mo}/{y}', f'{int(da)}/{int(mo)}/{y}'}
    return dates


def fact_pairs(sheet: dict) -> set[tuple[str, str | None]]:
    pairs: set[tuple[str, str | None]] = set()
    for text in sheet['facts']:
        for number, unit in _numbers_with_units(DATE_RE.sub(' ', _normalize(text))):
            key = _value_key(number)
            if key is not None:
                pairs.add((key, unit))
                pairs.add((key, None))
    return pairs


def validate_text(text: str, sheet: dict) -> tuple[bool, str]:
    """Accept only text whose dates and numbers, with their units, all come from the fact sheet."""
    if not isinstance(text, str) or not text.strip():
        return False, 'vazio'
    if len(text.split()) > MAX_WORDS:
        return False, 'longo'
    low = _normalize(text)
    if any(word in low for word in FORBIDDEN):
        return False, 'promessa ou orientação indevida'
    if NUMBER_WORDS.search(low):
        return False, 'número por extenso'
    if re.search(r'\d[.,]\d{3}', low):
        return False, 'formato numérico ambíguo (separador de milhar ou três decimais)'
    allowed_dates = fact_dates(sheet)
    for token in DATE_RE.findall(low):
        if token not in allowed_dates:
            return False, f'data fora dos fatos: {token}'
    low = DATE_RE.sub(' ', low)
    allowed = fact_pairs(sheet)
    for number, unit in _numbers_with_units(low):
        key = _value_key(number)
        if key is None:
            return False, f'número ilegível: {number}'
        if (key, unit) in allowed:
            continue
        return False, f'número fora dos fatos: {number}{" " + unit if unit else ""}'
    return True, 'ok'


def llm_text(sheet: dict, *, provider: str, model: str | None, session=None, timeout: int = 40) -> dict:
    base, key_env, default_model, note = PROVIDERS[provider]
    key = os.environ.get(key_env, '').strip() if key_env else 'local'
    if provider == 'github' and not key:
        key = os.environ.get('GITHUB_TOKEN', '').strip()
    if not key:
        raise ValueError(f'chave ausente para {provider} ({key_env})')
    if '{account}' in base:
        account = os.environ.get('CLOUDFLARE_ACCOUNT_ID', '').strip()
        if not account:
            raise ValueError('CLOUDFLARE_ACCOUNT_ID ausente')
        base = base.format(account=account)
    model = model or default_model
    system = ('Você redige boletins agrometeorológicos em português do Brasil para produtores rurais. '
              'Use SOMENTE os fatos fornecidos; não acrescente números, datas ou locais; não dê ordens operacionais nem prometa certeza. '
              'Escreva de 3 a 5 frases curtas e claras, citando faixa de incerteza e concordância entre modelos quando existirem. '
              'Termine com uma frase dizendo que os percentuais são frequências de membros dos ensembles, não probabilidades calibradas, e que o texto não é orientação operacional. '
              'Não mencione pulverização, aplicação, janelas de operação ou recomendações.')
    user = 'FATOS:\n- ' + '\n- '.join(sheet['facts']) + '\n\nRedija o boletim.'
    session = session or requests.Session()
    response = session.post(f'{base}/chat/completions', headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
                            json={'model': model, 'temperature': 0.2, 'max_tokens': 450,
                                  'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}]}, timeout=timeout)
    response.raise_for_status()
    body = response.json()
    if not isinstance(body, dict):
        raise ValueError('resposta do provedor não é um objeto JSON')
    choices = body.get('choices')
    message = (choices[0].get('message') if isinstance(choices, list) and choices and isinstance(choices[0], dict) else None) or {}
    content = message.get('content') if isinstance(message, dict) else None
    if isinstance(content, list):  # some providers return a list of parts
        content = ' '.join(str(part.get('text', '')) for part in content if isinstance(part, dict))
    text = content if isinstance(content, str) else ''
    usage = body.get('usage') if isinstance(body.get('usage'), dict) else None
    return {'text': text.strip(), 'model': body.get('model') or model, 'usage': usage, 'provider_note': note}


def ledger_allows(path: Path, limit: int, now: dt.datetime) -> bool:
    day = now.date().isoformat()
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        data = {}
    if data.get('day') != day:
        data = {'day': day, 'calls': 0}
    if data['calls'] >= limit:
        return False
    data['calls'] += 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding='utf-8')
    return True


def generate(public: dict, *, now: dt.datetime | None = None, provider: str | None = None, model: str | None = None,
             session=None, ledger: Path | None = None) -> dict:
    now = now or dt.datetime.now(dt.timezone.utc)
    sheet = build_facts(public, now=now)
    baseline = rule_based_text(sheet)
    provider = (provider if provider is not None else os.environ.get('AI_BULLETIN_PROVIDER', 'none')).strip().lower()
    result = {'generated_utc': now.isoformat(timespec='seconds'), 'location_id': sheet['location_id'], 'prompt_version': PROMPT_VERSION,
              'facts': sheet['facts'], 'facts_sha256': sheet['sha256'], 'issued_at_utc': sheet['issued_at_utc'],
              'rain_24h_window_local': sheet['rain_24h_window_local'],
              'rule_based_text': baseline, 'text': baseline, 'status': 'rules', 'provider': 'none', 'model': 'rules', 'validation': 'n/a', 'error': None,
              'disclaimer': 'Texto gerado automaticamente a partir dos números publicados; confira os valores no painel antes de qualquer decisão.'}
    if provider in ('', 'none'):
        return result
    if provider not in PROVIDERS or os.environ.get('AI_ALLOW_PAID', '0') == '1':
        result.update(status='rules_fallback', error=f'provedor não permitido: {provider}')
        return result
    limit = max(0, int(os.environ.get('AI_MAX_CALLS_PER_DAY', '24')))
    # The ledger lives with the previous publication, which the pages workflow persists between runs.
    ledger = ledger or Path(os.environ.get('PREVIOUS_PUBLICATION_DIR', 'runtime/previous_publication')) / 'ai_bulletin_ledger.json'
    if not ledger_allows(ledger, limit, now):
        result.update(status='rules_fallback', error='cota diária local de chamadas de IA atingida')
        return result
    try:
        answer = llm_text(sheet, provider=provider, model=model or os.environ.get('AI_BULLETIN_MODEL') or None, session=session)
        ok, why = validate_text(answer['text'], sheet)
        result.update(provider=provider, model=answer['model'], usage=answer.get('usage'), validation=why)
        if ok:
            result.update(text=answer['text'], status='llm')
        else:
            result.update(status='rules_fallback', error=f'resposta rejeitada: {why}', rejected_text=answer['text'][:600])
    except (requests.RequestException, ValueError, KeyError, TypeError, AttributeError) as exc:
        # Never publish provider URLs (they can embed account identifiers): type and HTTP status only.
        status = getattr(getattr(exc, 'response', None), 'status_code', None)
        detail = str(exc)[:120] if isinstance(exc, (ValueError, KeyError, TypeError, AttributeError)) else ''
        result.update(status='rules_fallback', error=f'{type(exc).__name__}' + (f' HTTP {status}' if status else '') + (f': {detail}' if detail else ''))
    return result


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', action='append', default=None, help='arquivo latest.json (repetível)')
    parser.add_argument('--output-dir', default='site/data')
    args = parser.parse_args(argv)
    inputs = args.input or ['site/data/latest.json', 'site/data/locations/diamantino/latest.json']
    written = []
    for path in inputs:
        p = Path(path)
        if not p.is_file():
            continue
        public = json.loads(p.read_text(encoding='utf-8'))
        if public.get('publication_state') == 'previous_preserved':
            continue
        loc = (public.get('site') or {}).get('id') or p.parent.name
        out = Path(args.output_dir) / f'bulletin_{loc}.json'
        result = generate(public)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
        written.append({'location': loc, 'status': result['status'], 'provider': result['provider'], 'error': result['error']})
    print(json.dumps(written, ensure_ascii=False))
    return written


if __name__ == '__main__':
    main()
