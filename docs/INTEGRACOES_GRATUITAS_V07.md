# Integrações v0.7 — custo zero (projeto experimental)

## Ativas no código (sem chaves)

| Produto | Endpoint | Frequência pretendida | Evidência necessária para declarar sucesso |
|---|---|---|---|
| Open-Meteo Forecast | `https://api.open-meteo.com/v1/forecast` | ~30 min | `utc_offset_seconds = -14400`, valores válidos e grade |
| Open-Meteo Ensemble | `https://ensemble-api.open-meteo.com/v1/ensemble` | ~30 min | N membros por variável, grade, ausências explícitas |
| INMET avisos | `https://apiprevmet3.inmet.gov.br/avisos/ativos` | ~30 min | código municipal IBGE `5005707` presente em geocodes |
| INMET estações | `https://apitempo.inmet.gov.br/estacoes/T` | ~30 min | código, georreferência e situação |
| INMET diário de estação próxima | `https://apitempo.inmet.gov.br/estacao/diaria/...` | ~30 min | código da estação, timestamp, unidade, resposta real |
| CPTEC/INPE | `https://servicos.cptec.inpe.br/XML/cidade/7dias/...` | ~30 min | cidade=Naviraí, UF=MS e atualização recente |
| Open-Meteo Forecast Soil | `https://api.open-meteo.com/v1/forecast` | ~30 min | umidade superficial modelada disponível, grade e profundidade |
| NASA POWER | `https://power.larc.nasa.gov/api/temporal/daily/point` | diário/cache | PRECTOTCORR válido, últimos dias com atraso de produto |
| ECMWF EC46/SEAS5 via Open-Meteo | `https://seasonal-api.open-meteo.com/v1/seasonal` | diário/cache | 6h de membros completos para janelas semanais, sem precisão diária falsa |
| **ERA5-Land 1991–2020** | `https://archive-api.open-meteo.com/v1/archive` | **mensal/cache** | 12 meses de agregação sobre anos completos, cobertura 1991–2020 |
| **Previous Runs 1/3 dias** | `https://previous-runs-api.open-meteo.com/v1/forecast` | **diário/cache** | 24h completas por dia, antecedência da série identificada |

**Status de código implementado não equivale a API testada em produção.** Conferir log no GitHub Actions da primeira coleta v0.7.

## Desabilitadas / não implementadas, sem gasto

- **OpenWeather One Call:** plano e chave com eventual cobrança; chamada **removida da coleta** e segredo antigo **não usado**. A alternativa gratuita 5 dias/3h está pronta, mas só executará após o usuário cadastrar uma **nova** chave Free em GitHub Secret `OPENWEATHER_FREE_API_KEY`.
- **Google Weather API:** chave pode envolver faturamento; **não usada**. Google WeatherNext2 via Open-Meteo Ensemble continua disponível sem chave nos limites não comerciais.
- **NASA Earthdata/IMERG:** token compartilhado anteriormente deve ser revogado. Integração geoespacial autenticada não foi montada nesta atualização; não usar token até haver tratamento seguro e teste.
- **Google Earth Engine / SoilGrids:** autenticação OAuth/Service Account e elegibilidade não comercial; chave de API comum não basta. Sem configuração nem credenciais nesta versão. A ISRIC suspendeu o REST, mas WCS/GEE são opções futuras.
- **NOAA GOES-19:** link de visualização sul da América do Sul; sem verificação automática da imagem mais recente sobre Naviraí.
- **INPE radar/raios:** requer camada/API confiável com timestamp e geolocalização; sem alegar nowcast enquanto não houver integração validada.

## Limitações e ciência

- O blend dos oito ensembles não é calibrado nem independente por centro.
- A climatologia ERA5-Land corresponde a **produto em grade**, não à série da Embrapa nem a observação real em talhão.
- **Previous Runs** é uma referência histórica de um produto **best_match**; não é avaliação retrospectiva dos oito ensembles atuais. A soma 24h de previsões com antecedência horária fixa difere de uma única rodada diária.
- A exportação Embrapa `.xls` **não informa ID da estação**. Pareamento preliminar serve somente para avaliação qualitativa, não para publicar acurácia validada.
- A coleta de arquivos de estações da Embrapa ainda exige confirmação e atualização manual ou endpoint documentado.

## Segurança

Não existe motivo para enviar qualquer chave OpenWeather, token Earthdata ou chave Google pelo chat. Uma chave nova OpenWeather Free é **opcional** e só deve ser inserida diretamente no GitHub Secret. Não devem aparecer em GitHub, ZIP, e-mails, screenshots ou logs. Revogue qualquer credencial previamente exposta; comprometer-se a não divulgá-la posteriormente não garante que não tenha sido copiada.
