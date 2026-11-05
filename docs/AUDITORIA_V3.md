# Auditoria técnica — Campo e Clima v3 (05/11/2026)

Base auditada: `main` em `98f48c4` (merge do PR #6, 04/11/2026), branch `weather-archive` em `f5fe590`, execuções do GitHub Actions até 05/11/2026 03:48 UTC e as respostas brutas arquivadas da captura `manifests/2026-11/20261105T00-{navirai,diamantino}.json`. Onde a afirmação depende de algo que não pôde ser reproduzido nesta sessão, isso está dito.

Limitação da sessão: o ambiente de auditoria não alcança a internet aberta (apenas a API do GitHub). Nenhuma chamada à Open-Meteo, INMET, RainViewer ou NASA foi feita aqui; toda a evidência sobre as fontes vem das respostas **arquivadas** pelo próprio projeto e da documentação pública pesquisada por busca.

## 1. O que existe e funciona

| Componente | Evidência | Estado |
|---|---|---|
| Coleta operacional (`scripts/collect.py` via `scripts/science_cli.py collect --location all`) | Execução 41963408447: 8 ensembles válidos em Naviraí e Diamantino; determinístico 336 h; 21 e 17 requisições por local | Funciona |
| Arquivo científico (`weather-archive`) | 25 manifests operacionais + 14 de importações; `public/archive_status.json` sem falhas; 10,1 MB usados de 750 MB (1,3%); ~1,4 MB/dia | Funciona desde 03/11 (ver §4) |
| Verificação diária (`science.yml`) | 5 execuções desde 31/10, todas verdes; `verification.json` regenerado em 05/11 03:48 | Funciona, mas sem pares (ver §5) |
| Site estático (GitHub Pages) | deploy em cada execução verde; 11 abas; 168 testes Python e 14 suítes JS passavam antes desta entrega | Funciona |
| Coordenadas personalizadas (`location.js`) | consultas no navegador: Forecast + 8 ensembles de chuva + 3 modelos com variáveis conjuntas | Funciona |

## 2. Código e arquitetura — achados

| # | Achado | Gravidade | Situação após esta entrega |
|---|---|---|---|
| C1 | Fuso fixo `-14400`/UTC-4 em `fetch`, `validate_forecast` e `next_local_forecast_hour` (`collect.py`). Correto para Naviraí e Diamantino, mas impediria qualquer terceira localidade | média | **Corrigido**: offset derivado de `ZoneInfo(TZ)`; mensagens preservam "UTC-4" para as localidades atuais |
| C2 | Janelas horárias de chuva (1 h/3 h) misturavam 8 modelos como se todos fossem horários. As respostas arquivadas mostram passo nativo de 6 h (AIFS, AI-GEFS, WeatherNext2), 3 h (IFS, GEFS, GEM) e 1 h (ICON, UKMO): a API divide a acumulação em partes horárias iguais, o que superestima ocorrência e subestima intensidade por hora | **alta (erro metodológico)** | **Corrigido**: `rain_products.native_step_hours` detecta o passo (16/16 acertos nas respostas reais) e `mix_hourly_rain` só usa modelos cujo passo cabe na janela; o número de modelos excluídos é publicado por janela |
| C3 | `forecast_days=7` entregava apenas 6 dias locais completos de chuva (convenção 01h–00h); não existia acumulado de 7 dias | média | **Corrigido**: pedido de 8 dias; acumulados 3/5/7 dias por trajetória de membro |
| C4 | Não havia produtos de concordância entre modelos nem de mudança entre publicações | média | **Implementado**: `rain_model_agreement_daily`, `previous_run_comparison` (persistido via cache do Actions) |
| C5 | Patch V23 (T/UR/VPD/vento por ensemble) só existia como instalador Windows (`aplicar_v23.py`, `patches.json`, `payload/`); `scripts/agro_ensemble.py` era um atalho de importação para os testes | média | **Integrado** diretamente: módulo real, coletor, `location.js`, painel estático; instalador removido |
| C6 | Nenhum metadado de rodada do provedor; "coleta nova" e "rodada nova" indistinguíveis; TTL de 6 h do cache dos ensembles | alta | **Implementado** best effort: `static/meta.json` por domínio (inicialização/disponibilidade), cache sensível à rodada (12 h quando há metadado, 3 h sem), `freshness` no JSON e painel por modelo. O endpoint não pôde ser exercitado nesta sessão; falha é tratada como "sem metadados" |
| C7 | Rajadas: só ECMWF IFS, GEFS e UKMO publicam `wind_gusts_10m` nos ensembles; AIFS, AI-GEFS, ICON-EPS, GEM e WeatherNext2 retornam `null` (evidência: `gust_members` 0 nas respostas arquivadas). UR ausente em AI-GEFS e WeatherNext2 | informação | Exposto na interface (modelos válidos por variável); a triagem conjunta de pulverização continua restrita a 3 modelos por construção |
| C8 | Condição `github.event.repository.private == false` nos workflows; três execuções agendadas (58, 59, 60) terminaram com todos os jobs "skipped". A chave `concurrency.queue: max` não é reconhecida pelo actionlint 1.7.12 (`docs/RELEASES/premerge/actionlint.json`), embora o GitHub a aceite em tempo de execução | média | **Substituída** por `github.repository == 'joaolorencone-unesp/campo-e-clima'`; `queue` mantida; causa dos skips não reproduzida, cadência passa a ser registrada no diagnóstico |
| C9 | Estação INMET escolhida só por distância: S735 (SEMADESC-MS) responde HTTP 204 na rota pública; A752 Itaquiraí (INMET, 42,8 km) e A949 Diamantino (INMET, 7,9 km, operante desde 26/11/2025) nunca eram tentadas | alta para a verificação | **Corrigido**: preferência por estações operadas pelo INMET, até 3 candidatas, rota com token opcional (`INMET_API_TOKEN`) com URL redigida no arquivo |
| C10 | Variáveis agro no determinístico limitadas a T/UR/VPD/chuva/vento/pressão/nuvens | média | **Implementado** pedido complementar isolado (radiação, ET₀, CAPE, CIN, lifted index, bulbo úmido, solo, nuvens por nível); falha nunca derruba a previsão principal |
| C11 | Diagnóstico disperso (status por fonte dentro do JSON, `archive_status.json` separado, cota só no `runtime`) | média | **Implementado** `site/data/diagnostics.json` + painel central (frescor, cadência real, cota estimada, arquivo, erros) |
| C12 | Mensagem de "ensembles desatualizados" acima de 90 min, incompatível com ciclos de 6–12 h dos modelos e com a cadência real do Actions | baixa | Limiar 3 h (aviso) e 12 h (desatualizado), com encaminhamento ao painel de frescor |
| C13 | Segurança: `GH_TOKEN` só em `extraheader` de ambiente; nenhum segredo no site; `safe_parameters` bloqueia chaves em parâmetros | ok | Mantido; novo caminho de token INMET nunca grava a credencial em manifests, URLs públicas ou erros |
| C14 | Desempenho: `latest.json` de Naviraí ≈ 0,5 MB (Diamantino 0,36 MB); Plotly local 3,9 mil linhas | aceitável | Sem alteração; compressão do Pages cobre o JSON |

## 3. Matemática e tratamento de dados (verificados por leitura e teste)

- Pesos: 1/M por modelo válido e 1/n por membro válido; quantis por CDF empírica inversa ponderada (menor x com F(x) ≥ q). Coerente em Python e JS.
- Chuva: rótulo `t` cobre (t−1, t]; dia local = finais 01h…00h; janelas futuras começam em t+1. Confirmado em `model_daily_rain`, `model_hourly_rain`, `computeModel`.
- Rajadas: máximo diário por membro, nunca soma. VPD: Tetens/FAO-56 com T e UR do mesmo membro.
- Dados ausentes: membro/dia/janela incompletos são excluídos; nulos nunca viram zero; contagens de válidos/declarados publicadas.
- Correlação entre modelos: continua tratada apenas por aviso textual (IFS/AIFS, GEFS/AI-GEFS). A concordância diária conta modelos, não membros, mas não desconta a dependência institucional.

## 4. GitHub e automações

Cadência real do `pages.yml` (evento `schedule`, 26/10 23:19 → 05/11 03:43 UTC):

| Métrica | Valor |
|---|---|
| Execuções agendadas registradas | 40 em 9,2 dias (≈ 4,3 por dia) |
| Execuções esperadas pelo cron `7,37 * * * *` | 48 por dia |
| Taxa efetiva | ≈ 9% |
| Intervalo típico entre execuções | 3 a 8 horas |
| Duração | build ≈ 45 s; archive ≈ 3,5 min; deploy ≈ 12 s |
| Falhas consecutivas | 18 (30/10 18:49 → 03/11 08:31): job `archive` (autenticação do `ls-remote`, depois divergência de hash gzip legado) — corrigidas pelos PRs #2 e #4 |
| Skips | 3 (03/11 21:57, 04/11 02:14, 04/11 09:48 com 3 tentativas): todos os jobs `skipped` |

Leitura: o agendamento do GitHub é melhor esforço e, para este repositório, entrega uma fração pequena das execuções; não é defeito do código. Consequências e mitigação estão em `docs/ARQUITETURA_V3.md` (disparo externo opcional por `workflow_dispatch`, registro de cadência no diagnóstico, cache sensível à rodada).

Workflow científico: 5 execuções (31/10 a 04/11), todas verdes, ~5,5 min. Importações diárias de Previous Runs (GFS) e Historical Forecast chegam ao arquivo; a importação de observações INMET falha silenciosamente para o arquivo (captura marcada `unavailable`), porque a rota pública devolve 204/404.

Branch `weather-archive`: janelas de 6 h de 29/10 a 05/11, Diamantino com 20 janelas e Naviraí com 5 (lacuna 30/10–03/11 pela falha do job). Hashes verificados na reconstrução; limite Git de 1 GB e de arquivos de 750 MB longe de serem atingidos.

## 5. Observações e verificação

- Pares elegíveis: 0 em ambas as localidades (`verification.json` de 05/11). Causa: nenhuma observação com QC básico, porque a rota de estação do INMET sem token não responde e a série Embrapa continua provisória (sem identificação da estação no arquivo exportado).
- Catálogo INMET capturado em 05/11 (669 estações): Naviraí → S735 (37,6 km, SEMADESC-MS), A752 Itaquiraí (42,8 km, INMET, desde 2008), A749 Juti (48,4 km, em pane), A772 Amambai–Novo Horizonte (69 km, nova em 2026); Diamantino → **A949 Diamantino (7,9 km, INMET, operante desde 26/11/2025)**, A944 Rosário Oeste (46,8 km).
- Embrapa Guia Clima: 694 dias (01/12/2024–25/10/2026), sem lacunas de datas, sem identificação da estação no arquivo. Necessário: captura da seleção da estação 6 ou confirmação por escrito da Embrapa/IFMS para promover a `verified_by_official_metadata`.

## 6. Problemas históricos — classificação

| Problema | Classificação | Evidência |
|---|---|---|
| Ensembles desatualizados | Resolvido parcialmente; dependente de infraestrutura externa | Dados agora carregam aquisição real, cache sensível à rodada e painel de frescor; cadência do Actions (≈9%) segue externa |
| Atualização manual só do determinístico | Ainda existente por limitação arquitetural | Pages não dispara Actions; para coordenadas personalizadas os ensembles são consultados no navegador |
| Diferenças Naviraí × Diamantino | Resolvido e validado | Mesmos 8 modelos nas duas capturas de 05/11; fuso derivado da configuração |
| Ensembles de vento ausentes em coordenadas personalizadas | Resolvido parcialmente | Variáveis conjuntas (3 modelos com rajadas) agora disparam automaticamente; só 3 de 8 modelos publicam rajadas |
| Falhas de APIs / timeouts | Resolvido (tratamento) | Orçamento de 900 s, fallback de 4 dias, 429 com cooldown, estados explícitos |
| Falhas no arquivamento | Resolvido e validado | PR #2 e #4; `failures: []`; manifests de Naviraí desde 03/11 12 UTC |
| Divergência de hash gzip | Resolvido e validado | Tolerância a gzip legado com RAW idêntico; teste de regressão |
| Caches com horários antigos | Resolvido e validado | `collected_at_utc` vem do manifesto; `cache_hit` publicado; evidência na captura de 05/11 (aquisição 23:36 de 04/11) |
| Previsões estendidas indisponíveis | Dependente de dados externos | Estados `unavailable/disabled` visíveis; cache semanal/diário |
| Mapas com informações insuficientes | Ainda existente | Fase 4 planejada (`docs/ARQUITETURA_V3.md`, `docs/FONTES_V3.md`) |
| Limitações de observações | Ainda existente; dependente de token/arquivos | Rota com token implementada; A949 identificada para Diamantino |
| Falta de calibração local validada | Ainda existente | 0 pares; plano em `docs/PLANO_CIENTIFICO_CHUVA.md` |
| Skips de execuções agendadas | Não reproduzido | Condição do `if` endurecida; monitorar no diagnóstico |

## 7. Arquivos relevantes desta auditoria

`scripts/collect.py`, `scripts/rain_products.py`, `scripts/freshness.py`, `scripts/export_diagnostics.py`, `scripts/replay_capture.py`, `scripts/agro_ensemble.py`, `scripts/science/http.py`, `scripts/science/stations.py`, `scripts/sources/official.py`, `scripts/science_cli.py`, `.github/workflows/*.yml`, `site/index.html`, `site/static/{app,location,farm_summary_v30,nav_v30,rain_products_v30,diagnostics_v30,agro_ensemble_v23}.js`, `tests/test_rain_products_v30.py`, `tests/test_freshness_diagnostics_v30.py`, `tests/test_markup_v30.py`, `tests/test_v30_frontend.cjs`, `tests/browser_v30.cjs`.
