# Campo e Clima v1.0 — Histórico meteorológico, análise operacional e comparação de fontes

**Local:** qualquer coordenada WGS84 informada no painel. **Sem chave e sem API paga**, sujeito às condições não comerciais da Open-Meteo.

## Por que o histórico da Open-Meteo é tão importante

A Open-Meteo oferece **produtos científicos distintos** que não devem ser confundidos:

| Produto | Fonte/alcance | Uso correto | Estado nesta versão |
|---|---|---|---|
| [Historical Weather](https://open-meteo.com/en/docs/historical-weather-api) | ERA5 desde 1940; ERA5-Land desde 1950; IFS reanalisado desde 2017 | Retrospectiva diária/horária, climatologia, ET0, VPD, vento, chuva e solo | **Implementado para 30/90/365 dias; 31 dias horários** |
| [Historical Forecast](https://open-meteo.com/en/docs/historical-forecast-api) | Previsões contínuas emendando os primeiros horários de rodadas (aprox. 2021/22) | Reconstrução de saídas dos modelos; não são observações independentes | Documentado, coleta futura |
| [Previous Model Runs](https://open-meteo.com/en/docs/previous-runs-api) | Antecedências fixas de 1–7 dias; em geral desde 2024 | Verificação retrospectiva por lead time | Conector anterior já existente; verificar dados observados |
| [Single Runs](https://open-meteo.com/en/docs/single-runs-api) | Rodadas individuais IFS desde março/2024 e outros modelos desde abril/2026 | Backtesting de previsões realmente disponíveis a cada horário de emissão | Próxima fase |
| [Ensemble API](https://open-meteo.com/en/docs/ensemble-api) | Membros de 8 ensembles e outros, horizonte variável por modelo | Probabilidade preditiva bruta, riscos de chuva/vento; até cerca de 35 dias quando válido | Implementado no painel principal |
| [Ensemble Mean API](https://open-meteo.com/en/docs/ensemble-mean-api) | Média e dispersão de conjuntos; retenção temporal maior | Resumo leve e fallback quando houver muitos membros/timeout | Proposto, não conta como modelo novo |
| [Forecast API](https://open-meteo.com/en/docs) | Global, previsão horária e diária, modelos regionalizados | Previsão D0–D14 e triagem de pulverização | Implementado |
| [Seasonal API](https://open-meteo.com/en/docs/seasonal-forecast-api) | EC46/SEAS5, ~36km, produtos até meses | Tendência semanal/sazonal, baixa previsibilidade diária | Pausado após timeout; reavaliar em rotina separada |
| [Air Quality](https://open-meteo.com/en/docs/air-quality-api) | CAMS PM2.5/PM10/UV | Qualidade do ar e contexto de fumaça | Implementado |
| [Elevation](https://open-meteo.com/en/docs/elevation-api) | Copernicus GLO-90 DEM | Altitude modelada por coordenadas | Implementado |
| [Geocoding](https://open-meteo.com/en/docs/geocoding-api) | Nomes de cidades/CEPs | Seleção futura por nome, não só lat/lon | Futuro |
| [Flood](https://open-meteo.com/en/docs/flood-api) | GloFAS vazão de rios | Monitoramento hidrológico regional, quando houver rio de interesse | Futuro; não equivale a chuva pontual |
| [Satellite Radiation](https://open-meteo.com/en/docs/satellite-radiation-api) | Radiação observada por satélite com cobertura variada | Radiação e energia, não mapa de chuva/radar | Avaliar cobertura para MS |
| [Climate API](https://open-meteo.com/en/docs/climate-api) | Projeções climáticas, horizontes de décadas | Impacto climático estrutural, **não** previsão de 60 dias | Futuro, separado |
| [Model Updates](https://open-meteo.com/en/docs/model-updates) | Metadados de disponibilidade | Diagnóstico de frescor de rodadas e timeouts | Futuro |

## Implantação v1.0 — o que foi programado

### Histórico diário por coordenada

A interface consulta:

```
GET https://archive-api.open-meteo.com/v1/archive
    ?latitude=-23.065
    &longitude=-54.190
    &models=era5_land
    &timezone=UTC
    &start_date=2026-07-01
    &end_date=2026-10-15
    &daily=precipitation_sum,temperature_2m_mean,temperature_2m_max,temperature_2m_min,wind_speed_10m_max,wind_gusts_10m_max,et0_fao_evapotranspiration,shortwave_radiation_sum
```

**As datas acima são apenas exemplo de parâmetros de API, não medições.** Na aplicação, o intervalo é gerado automaticamente, respeitando o atraso da reanálise e o período selecionado (30, 90 ou 365 dias). Quando uma variável não estiver disponível, o script tenta um conjunto reduzido e mantém campos faltantes como `null`.

Ao selecionar uma fazenda, os resultados das coordenadas anteriores são invalidados. A resposta de cada requisição é inspecionada quanto a datas, unidades, presença das variáveis e cobertura temporal.

### Comparação NASA POWER × ERA5-Land

A NASA POWER retorna por padrão valores diários em **Local Solar Time**, enquanto o Open-Meteo pode usar UTC ou um fuso civil. A v1.0 muda a consulta NASA para **`time-standard=UTC`** e a consulta diária ERA5-Land para **`timezone=UTC`**, para alinhar as datas. Essa comparação é entre dois produtos de grade e não avalia a acurácia real de um modelo contra estação.

O painel mostra diferenças médias e absolutas e correlação descritiva, somente havendo pelo menos 10 dias coincidentes. A estatística não significa que uma fonte é a verdade e a outra é a previsão. Correlação entre bases parcialmente dependentes não garante habilidade de previsão.

### Histórico operacional de pulverização

Consulta às **últimas 31 datas completas disponíveis**, `timezone=auto` (hora civil do ponto), contendo a série por hora:

- temperatura 2m;
- umidade relativa 2m;
- VPD (ou cálculo padrão FAO com T e RH quando disponíveis);
- vento 10m;
- rajadas 10m;
- precipitação horária.

As horas diurnas locais 07–17h são classificadas segundo **limites de triagem configurados para pesquisa**, contando horas `candidato`, `marginal`, `restritivo` e `indeterminado`. Critérios por hora: T<30°C, UR>55%, VPD<1,2 kPa, vento 3–10 km/h, rajadas≤20 km/h, chuva≤0,1 mm/h; faixas marginais próximas das restrições. Inversão térmica não é avaliada, assim mesmo a classe `candidato` **NÃO** corresponde a uma aplicação segura.

O produto usa retrospectiva horária de grade, **não frequência dos membros de ensembles e nem probabilidade calibrada**. A classificação experimental não serve para decidir pulverização histórica individual sem clima de talhão, bula, tecnologia de aplicação, deriva, vizinhança e verificação operacional.

### Estações INMET por qualquer coordenada

O script `scripts/export_inmet_catalog.py` consulta publicamente `https://apitempo.inmet.gov.br/estacoes/T` durante a publicação do GitHub Actions e grava `site/data/inmet_stations.json`. O navegador mostra as seis estações mais próximas do ponto informado, com código, situação e distância em linha reta. **Esse catálogo não fornece observações**, e a ausência de cadastro/erro de acesso é informada sem estimar leituras.

## Política de custo e arquitetura

- **Zero contas com cartão**; sem One Call OpenWeather.
- Dados Open-Meteo no endpoint público para uso não comercial, com atribuição e limites de chamadas; não confundir gratuidade acadêmica com licença comercial.
- A página permanece estática (GitHub Pages). O histórico por coordenada é requisitado pelo navegador, sem servidor pago. Pode haver restrições CORS, limites da API ou indisponibilidade.
- Históricos pesados só são consultados quando necessário e recebem cache temporário durante a sessão.
- A interface não simula medições ausentes.
- O GitHub Actions coleta o catálogo INMET, mas um workflow verde não implica que o INMET tenha fornecido observações.

## Próximos passos de qualidade científica

1. Confirmar ID da estação da exportação Embrapa Naviraí; aplicar controle de qualidade.
2. Importar observações por estação INMET quando o acesso institucional for autorizado; dados INMET não devem ser substituídos por metadados.
3. Construir série histórica diária por local com armazenamento persistente e possibilidade de correção de horário para dia agrícola local.
4. Recuperar emissões históricas com Single Runs para comparar forecasts vs estação, por antecedência e ano (Brier, CRPS, MAE/RMSE).
5. Avançar com perfis específicos por produto na pulverização, sustentados por bula, equipamento e informações do talhão.

## Referências oficiais

- https://open-meteo.com/en/docs/historical-weather-api
- https://open-meteo.com/en/docs/historical-forecast-api
- https://open-meteo.com/en/docs/previous-runs-api
- https://open-meteo.com/en/docs/single-runs-api
- https://open-meteo.com/en/docs/ensemble-api
- https://open-meteo.com/en/pricing
- https://power.larc.nasa.gov/docs/services/api/temporal/daily/
