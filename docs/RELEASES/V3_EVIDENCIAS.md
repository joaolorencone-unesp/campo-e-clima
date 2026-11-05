# Evidências da entrega v3 (05/11/2026)

## Testes executados (ambiente Linux, Python 3.13, Node 22, sem acesso a APIs externas)

| Conjunto | Resultado |
|---|---|
| `python -m pytest -q` com `CAMPO_OFFLINE_TESTS=1` | **187 aprovados, 0 falhas** (eram 168 na base `98f48c4`; +19 novos) |
| Suítes JavaScript offline (`tests/frontend_smoke.cjs` + `tests/test_*.cjs`) | **15/15 aprovadas** (eram 13; +`test_v30_frontend.cjs`, +`test_agro_ensemble_v23.cjs` movida do payload) |
| `node --check` em todos os arquivos de `site/static/` | sem erros |
| YAML dos quatro workflows | carregam sem erro |
| `tests/browser_v30.cjs` (Chromium real, Playwright, hosts externos bloqueados) | desktop 1440×1000 e celular 390×844: 11 abas abrem no modo avançado, modo simples oculta abas científicas, 6 cartões do resumo, **0 erros de JavaScript, 0 overflow horizontal** |
| Replay de capturas reais (`scripts/replay_capture.py`, manifests de 05/11/2026 00 UTC) | Naviraí e Diamantino: 8 modelos válidos cada; detecção de passo nativo 16/16 correta nas respostas arquivadas |

Novos testes: `tests/test_rain_products_v30.py` (9), `tests/test_freshness_diagnostics_v30.py` (5), `tests/test_markup_v30.py` (5), `tests/test_agro_ensemble_v23.py` (4, relocado), extensões em `tests/test_collect_offline.py`; `tests/test_v30_frontend.cjs`.

## Capturas de tela

`docs/RELEASES/v3/`: `overview_simple_desktop.png`, `overview_simple_mobile.png`, `farm_summary_desktop.png`, `farm_summary_mobile.png`, `overview_advanced_desktop.png`, `overview_advanced_mobile.png`, `rain_advanced_desktop.png`, `rain_accumulated_desktop.png`, `rain_accumulated_mobile.png`, `freshness_desktop.png`, `freshness_mobile.png`, `agro_desktop.png`; relatório `browser_report.json`. As capturas usam os dados reais arquivados em 04–05/11/2026 (replay), não valores sintéticos.

## Arquivos alterados

- Coleta e ciência: `scripts/collect.py`, `scripts/rain_products.py` (novo), `scripts/agro_ensemble.py`, `scripts/freshness.py` (novo), `scripts/export_diagnostics.py` (novo), `scripts/replay_capture.py` (novo), `scripts/science_cli.py`, `scripts/science/{__init__,http,ingest,archive,stations}.py`, `scripts/sources/official.py`.
- Workflows: `.github/workflows/{pages,science,archive-recovery}.yml`.
- Site: `site/index.html`, `site/static/{app,location,styles}.{js,css}`, novos `farm_summary_v30.js`, `nav_v30.js`, `rain_products_v30.js`, `diagnostics_v30.js`, `agro_ensemble_v23.js`.
- Testes: listados acima; `tests/test_map_markup_v20.py` (versão do CSS).
- Documentação: `docs/AUDITORIA_V3.md`, `docs/FONTES_V3.md`, `docs/ARQUITETURA_V3.md`, `docs/DESIGN_V3.md`, `docs/PLANO_CIENTIFICO_CHUVA.md`, `docs/DATA_DICTIONARY.md`, `docs/CHANGELOG.md`, `docs/ROADMAP.md`, `README.md`.
- Removidos: `aplicar_v23.py`, `patches.json`, `INSTALAR_CORRECAO_WINDOWS.bat`, `LEIA_PRIMEIRO_CAMPO_E_CLIMA_V23.txt`, `payload/` (substituídos pela integração direta).

## Funcionalidades preservadas

Todas as abas anteriores (Central Agro, Chuva & ensembles, Observações, Mapas, Vento, Pulverização, Precisão, Qualidade, 30–60 dias, Histórico), coordenadas personalizadas, radar RainViewer, GIBS MODIS/VIIRS, arquivo científico, reconstrução SQLite/Parquet, recuperação de artifacts, caches diários/semanais, política de 429, avisos INMET. Nenhum dado do `weather-archive` foi alterado; nenhuma credencial foi adicionada ao código.

## Limitações desta validação

- Nenhuma chamada real às APIs foi possível nesta sessão: `static/meta.json` (rodada por modelo), os nomes das variáveis complementares e a rota com token do INMET serão confirmados na primeira execução do workflow; todos têm fallback explícito (estado `unavailable`/`skipped`, subconjunto mínimo, até três estações).
- A comparação entre publicações só passa a existir após duas execuções consecutivas com o cache do Actions ativo.
- A cadência do `schedule` do GitHub (≈9% das execuções) continua externa ao projeto; o diagnóstico a registra.
- Não há observações com QC básico: as métricas de precisão continuam vazias por falta de referência, não por falha de código.
