# Campo e Clima v1.8 — auditoria e correções

**Escopo:** corrigir cálculos horários, disponibilidade real por variável e comunicação do risco de pulverização; preservar a arquitetura gratuita GitHub Pages + Python no GitHub Actions.

## Correções verificáveis

1. **72 horas futuras, não 00h–23h de três dias passados/parciais.** A API retorna dados desde a meia-noite local quando consultada por `forecast_days`. O coletor define `hourly_forecast_start_local` com a próxima hora cheia e mantém até 72 horários de início estritamente futuros. O navegador calcula o instante do horário usando `utc_offset_seconds` do produto consultado. A janela 3/6h é publicada somente se os passos futuros necessários estiverem disponíveis e contíguos.
2. **Precipitação acumulada por hora.** A API identifica chuva no horário `t` como a precipitação da hora anterior. Para um intervalo futuro *iniciado em `t`*, computar `precipitation[t+1:t+duracao+1]` dentro do mesmo membro. Isso evita que a previsão da hora anterior contamine a janela que o produtor consulta. Para horários nativos 3–6h sem continuidade horária não afirmar resolução de uma hora.
3. **Separação de membros declarados e válidos.** `member_count` interno ainda representa campos recebidos, para compatibilidade com outros módulos. No JSON público, `precipitation_members` e `gust_members` representam o maior número de trajetórias completas em um dia; campos novos `*_members_declared`, `*_members_with_numeric` e `*_members_valid_by_day` permitem auditoria detalhada. A amostra final utilizada nas frequências de cada data/janela está em `member_count` da própria linha de resultado. Nunca tratar nulo como vento zero nem como chuva zero.
4. **Triagem meteorológica × segurança operacional.** A classificação de quatro cores permanece para manter os gráficos anteriores. Adicionamos `numeric_passa`, `numeric_marginal`, `numeric_restrito` (mesmas condições meteorológicas sem a decisão conservadora de noite). A lista `operational_pending` registra que estabilidade/inversão e bula/receptores continuam não verificados; essas pendências não são probabilidades nem validam segurança. Essa separação funciona em janelas de duas horas usando o mesmo membro nas duas horas.
5. **Coleta mais enxuta para pulverização.** `forecast_hours=80` na API Ensemble traz horizonte relativo à hora corrente e margem para as três horas futuras de chuva, em vez de pedir quatro dias completos desde 00h.
6. **Cobertura visível.** A interface distingue horas futuras com previsão determinística das horas futuras realmente acompanhadas por amostras dos ensembles; valor em cache ou ausência de uma variável nunca são indicados como resultado validado.

## Limites científicos

- Frequências de modelos não estão calibradas; a correlação entre ECMWF IFS/AIFS e GEFS/AI-GEFS pode reduzir a independência estatística.
- Umidade, rajadas e vento previstos a 10 m não substituem sensores no talhão e avaliação de estabilidade na altura de operação.
- A regra experimental 07h–17h é conservadora e não constitui diagnóstico de inversão nem substitui dados de amanhecer/pôr do sol.
- Os limites experimentais para herbicidas/fungicidas/inseticidas não substituem **bula**, condições do produto, tecnologia de aplicação, proteção de polinizadores, receptores sensíveis e regulamentação.
- A disponibilidade real de modelos/variáveis só será confirmada na próxima execução de coleta do GitHub Actions. O sucesso do workflow **não** prova que todos os oito modelos foram utilizáveis.

## Fontes

- Open-Meteo Ensemble: https://open-meteo.com/en/docs/ensemble-api
- Open-Meteo Forecast: https://open-meteo.com/en/docs
- INMET: https://portal.inmet.gov.br/
- DJI Agras T100 — documentação do fabricante: https://ag.dji.com/t100/downloads

## Testes de regressão

`python -m pytest -q tests` — inclui `test_temporal_v18.py`.

`node tests/test_forward_browser_v18.cjs` — fonte sintética apenas em teste, nunca publicada como previsão.

A publicação continua por GitHub Desktop, sem chaves ou API paga.
