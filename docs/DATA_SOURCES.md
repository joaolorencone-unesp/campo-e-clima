# Fontes e estado verificado

| Fonte | Produto / uso | Estado desta entrega |
|---|---|---|
| Open-Meteo Forecast | Previsão operacional determinística; modelo automático não identificado como IFS | Duas localidades consultadas com sucesso |
| Open-Meteo Ensemble | IFS, AIFS, GEFS, AI-GEFS, ICON EPS, GEM, UKMO, WeatherNext2 | Os oito responderam nas duas localidades; disponibilidade futura não presumida |
| Previous Runs | Valores por antecedência fixa D1/D2/D3/D7 | Integração real aprovada; não representa uma rodada única |
| Single Runs | Rodada inicializada explicitamente em UTC | Integração real aprovada, 384 horas por local; disponibilidade pública da rodada não foi comprovada e bloqueia validação operacional |
| Historical Forecast | Série contínua montada de modelos operacionais | Integração real aprovada; não é observação nem reconstrução de D7 |
| INMET catálogo | Metadados públicos de estações | S735 identificada no catálogo; operadora SEMADESC-MS, 37,6 km do ponto Naviraí |
| INMET observações | Leitura horária / diária | Endpoint devolveu conteúdo não utilizável como JSON; nenhuma observação criada |
| Embrapa/IFMS | Guia Clima estação 6 | Metadados oficiais disponíveis. Exportação do projeto permanece provisória e excluída da validação |
| ERA5 / NASA POWER | Reanálise / estimativa modelada de grade | Módulos existentes preservados. Novo adaptador ERA5 separado; não usado como estação |

Referências técnicas efetivamente consultadas em 28–29/10/2026:
- https://open-meteo.com/en/docs/ensemble-api
- https://open-meteo.com/en/docs/previous-runs-api
- https://open-meteo.com/en/docs/single-runs-api
- https://open-meteo.com/en/docs/historical-forecast-api
- https://open-meteo.com/en/terms
- https://portal.inmet.gov.br/dadoshistoricos
- https://www.cpao.embrapa.br/gc/guia-clima?cod_estacao=6

Respostas e datas reais estão em `runtime/captures`, `weather-archive` e nos relatórios `docs/RELEASES`. A validade de uma fonte não é inferida de um HTTP 200: o corpo e a estrutura também são validados. O teste inicial de Single Runs retornou 400 ao receber start_date; o adaptador passou a usar apenas run/horizonte, conforme o contrato observado. A tentativa inicial foi preservada no relatório.
