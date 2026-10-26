# Inventário de fontes (não equivale a integrações ativas)

| Fonte | Produto | Situação | Link |
|---|---|---|---|
| Open-Meteo Forecast | hora, 14 dias, vento, chuva, T e UR | conector inicial | https://open-meteo.com/en/docs |
| Open-Meteo Ensemble | 8 modelos, membros de precipitação | conector inicial; validar nomes e horas/membros | https://open-meteo.com/en/docs/ensemble-api |
| Open-Meteo Previous Runs | previsões pretéritas emitidas antes da validade | planejar avaliação retrospectiva | https://open-meteo.com/en/docs/previous-runs-api |
| ECMWF extended/seasonal | tendências semanais e sazonais até 60 dias | planejado; não extrapolar previsão diária | https://www.ecmwf.int/en/forecasts/documentation-and-support/extended-range-forecasts |
| INMET | alertas oficiais e estações | previsto; checar abrangência e UTC | https://portal.inmet.gov.br/ |
| Embrapa Guia Clima (Naviraí, estação 6) | histórico e observações | previsto; extração ainda não validada | https://www.cpao.embrapa.br/gc/guia-clima?cod_estacao=6 |
| CPTEC/INPE | radar, GOES, raios, previsão | previsto; geolocalização e atualização obrigatórias | https://www.cptec.inpe.br/ |
| OpenWeather | comparação independente conforme licença/plano | sem chave integrada | https://openweathermap.org/api |
| SoilGrids ISRIC | textura e atributos estáticos | previsto; consultar disponibilidade WCS | https://docs.isric.org/globaldata/soilgrids/ |
| NASA SMAP | umidade superficial | previsto; validar resolução/latência | https://smap.jpl.nasa.gov/ |
| ERA5-Land | histórico/balanço hídrico em grade | previsto; reanálise ≠ observação local | https://cds.climate.copernicus.eu/ |
| DJI Agras T100 | limitações e dados de aplicação | análise documental planejada | https://ag.dji.com/t100/downloads |

**Controle de qualidade:** armazenar sempre a fonte, hora da coleta e da rodada, hora de validade, timezone, centro de grade, distância até sede, contagem de membros por variável, retorno de API e eventuais lacunas. INMET/Embrapa são observação local quando sensores e horário forem conferidos; portais de previsão externos não devem ser somados como membros independentes.


### Integração incremental v0.5

O código de coleta agora inclui **INMET avisos ativos** (filtrados por IBGE 5005707) e **catálogo de estações** (`apitempo.inmet.gov.br/estacoes/T`), com tentativa de consulta à estação diária operante mais próxima e tratamento explícito para bloqueios. Verificar execução real no Actions antes de declarar a fonte ativa. Embrapa estação 6: **CSV manual auditado**, não uma API automática. Instruções em `docs/INTEGRACAO_BASES.md`.
