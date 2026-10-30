# Arquitetura e auditoria inicial — v2.2

Origem verificada: repositório público `joaolorencone-unesp/campo-e-clima`, branch `main`, commit `e1241e208033baf3260d86c8ba4b03e56ba92300`, README v2.1. Branch local de desenvolvimento: `feature/v2.2-ciencia-e-rastreabilidade`. A aplicação FastAPI v0.3 e suas tarefas Windows são outro projeto; não foram substituídas.

## Auditoria dos componentes existentes

| Componente | Evidência e decisão |
|---|---|
| scripts/collect.py | Coletor Python, oito ensembles e determinístico. Produzia resumos e descartava membros. Reutilizado; acrescida opção de excluir fontes específicas de Naviraí para Diamantino. |
| scripts/spraying.py | Trajetórias conjuntas por membro e filtros experimentais; preservado. Não libera aplicação. |
| scripts/sources/ | Fontes INMET, Embrapa, POWER, produtos estendidos; preservadas. Respostas oficiais principais agora também entram no arquivo RAW. |
| history_navirai_v19.py | NASA POWER e ERA5 em dias UTC, com cache diário. Estimativas modeladas, não estação. Preservado. |
| site/index.html / app.js | Site estático com Plotly, navegação e consultas diretas; app.js preservado. Nova aba adicionada sem servidor de aplicação. |
| location.js | Consultas independentes por coordenada. Corrigido o fechamento do dia de chuva; mantida separação de localidades. |
| agro_cockpit_v21.js | Critérios próprios por operação já existiam, mas o KPI de horas restritas contava sempre pulverização. Corrigido para usar a operação selecionada. |
| maps_v14.js / history_v10.js | Mapas Leaflet, grade de nove pontos, radar e séries históricas; preservados e testados. |
| pages.yml | Coleta 7/37 minutos UTC e Pages. Artifact de 90 dias era o único snapshot. Agora artifact de 1 dia é transporte para job que escreve a branch permanente. |
| requirements / tests | 97 testes Python originais aprovados em UTF-8; Windows exige pasta de testes existente. Dependências científicas e testes adicionais incluídos. |

`site/data/latest.json` não existia no checkout original, pois é ignorado pelo Git e produzido pela coleta. Sua estrutura efetiva foi validada pela execução real: `site`, `deterministic`, `ensemble_models`, `rain_ensemble_daily`, `rain_ensemble_hourly`, `gust_ensemble_daily`, `spray_joint_*`, `official`, `complementary`, `sources`, `warnings`. Schema público 4 preservado; v2.2 acrescenta versão do sistema, ID do local, coleta e inicialização explicitamente desconhecida. O nome legado `issued_at_utc` significa emissão do arquivo público, não inicialização de NWP.

## Fluxo novo

Coletor existente → captura RAW (mesma requisição) → objetos gzip por SHA-256 + manifesto por local/janela UTC → branch `weather-archive` → reconstrução SQLite → verificação / experimentos → JSON compacto → Pages.

`scripts/science/` contém persistência, QC, pareamento, métricas, modelos opcionais e explicações. `scripts/science_cli.py` fornece comandos reproduzíveis. A coleta de cada local tem estado separado. Cadastro estático inclui Naviraí e Diamantino. Fontes específicas de Naviraí não entram no JSON de Diamantino.

Pages continua sendo estático. Nenhuma rota SQLite ou serviço Ollama é exposta publicamente. Falhas analíticas não invalidam uma previsão operacional obtida. Os novos workflows só ficam ativos após publicação aprovada na branch padrão.
