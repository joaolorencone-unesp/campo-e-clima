# Campo e Clima v0.9 — coordenadas e dados históricos gratuitos

## Operação no site estático

O GitHub Pages permanece **estático**: não existe um backend executando a cada clique. Para Naviraí, os boletins multifuente continuam sendo publicados pelo GitHub Actions aproximadamente a cada 30 minutos. Quando o visitante informa outra latitude/longitude, o navegador consulta fontes gratuitas para **aquele ponto**.

Fluxo:

1. Informe latitude e longitude em **graus decimais WGS84**, ex.: `-14.408`, `-56.446`; opcionalmente dê nome ao local.
2. Clique em **Consultar coordenadas**. Uma nova previsão Open-Meteo Forecast é solicitada com `timezone=auto`.
3. O navegador consulta até oito ensembles de chuva e rajada do Open-Meteo, incluindo fallback para chuva quando a variável rajada falhar. Cada modelo com chuva válida recebe **peso total igual** e cada membro válido peso igual dentro do modelo.
4. NASA POWER, Open-Meteo Archive, Air Quality, Elevation e umidade de solo são solicitadas ao ponto, cada uma com resposta e erro independentes.
5. A guia **Histórico NASA & ar** contém os dados de precipitação diária, temperatura e gráficos mensais, além de reanálise ERA5-Land e qualidade do ar.
6. Clique em **Copiar link do local** para compartilhar a URL com `lat`, `lon` e `name` (sem chaves). O ponto também permanece salvo durante a sessão do navegador.
7. Para retornar à coleta automática de Naviraí, clique em **Voltar à sede**.

## Endpoints implementados sem chaves

| Serviço | Endpoint | Variáveis | Natureza | Frequência sugerida |
|---|---|---|---|---|
| Open-Meteo Forecast | `https://api.open-meteo.com/v1/forecast` | T, UR, vento, rajadas, VPD, chuva, pressão | Modelo | Ao trocar ponto / 30 min |
| Open-Meteo Ensemble | `https://ensemble-api.open-meteo.com/v1/ensemble` | Membros de chuva/rajadas D0–D6 | Distribuição bruta de modelos | Ao trocar ponto / cache 3h |
| NASA POWER Daily | `https://power.larc.nasa.gov/api/temporal/daily/point` | PRECTOTCORR, T2M, T2M_MAX, T2M_MIN, RH2M, WS2M, ALLSKY_SFC_SW_DWN | Estimativa/reanálise em grade, **não estação** | Ao selecionar ponto; cache de sessão de 24h |
| Open-Meteo Historical | `https://archive-api.open-meteo.com/v1/archive` | Chuva e T média ERA5-Land | Reanálise, não observação independente | Sob demanda |
| Open-Meteo Air Quality | `https://air-quality-api.open-meteo.com/v1/air-quality` | PM2.5, PM10, UV | Previsão/modelo CAMS | Sob demanda |
| Open-Meteo Elevation | `https://api.open-meteo.com/v1/elevation` | Altitude do terreno | Copernicus GLO-90 | Ao selecionar ponto |
| Open-Meteo Soil Forecast | `https://api.open-meteo.com/v1/forecast` | Umidade superficial e temperatura do solo | Estimativa de modelo, não medição | Ao selecionar ponto |

Todos esses serviços dispensam cartão na modalidade gratuita não comercial aplicável. Obedecer aos termos de uso, frequência e atribuição.

## Limitações importantes

- **CORS:** o navegador pode bloquear a leitura direta de alguns endpoints da NASA POWER. Nesse caso, a aba oferece **Abrir dados NASA POWER**, que abre a requisição original; o sistema informa a falha e **não inventa série histórica**. Para garantir NASA POWER para qualquer coordenada sem depender de CORS, será preciso introduzir um backend/proxy autorizado ou rotinas de geração de arquivos para localidades pré-configuradas.
- **Disponibilidade:** nem todos os oito ensembles garantem chuva/rajadas válidas; cada modelo é contado somente onde há dados completos. A coleta de até oito modelos pode demorar e alguns podem falhar. Para reduzir chamadas gratuitas, na mesma coordenada as distribuições são reaproveitadas por até 3h em atualização automática e por até 30 minutos no botão manual; a previsão determinística continua consultada a cada 30 minutos. A previsão determinística é mostrada primeiro.
- **Pulverização:** para um ponto arbitrário, a triagem determinística permanece e o navegador tenta obter **seis variáveis conjuntas de cada mesmo membro por modelo** para calcular frequências horárias e janelas de 2h. Apenas modelos com todos os campos válidos participam. Se nenhum responder completamente, os gráficos de probabilidade de pulverização ficam indisponíveis, sem percentuais inventados. As classes são apenas filtros meteorológicos experimentais, não liberação de aplicação. Bula, legislação, estabilidade/inversão, deriva e medição no talhão são obrigatórias.
- **Avisos oficiais:** avisos filtrados por IBGE 5005707 e histórico provisório da Embrapa são específicos de Naviraí. **Não aparecem para outro ponto**. Não significam ausência de riscos no ponto selecionado.
- **NASA POWER** retorna produtos com resolução espacial relativamente grosseira. Datas diárias do provedor podem diferir do dia meteorológico local; não comparar diretamente sem harmonização temporal.
- **Climatologia:** série NASA consultada a partir de 2021 é histórico recente, NÃO normal climatológica de 30 anos.
- **Calendário:** forecast determinístico só até o horizonte realmente disponível. Tendências D15–D60 não são convertidas em previsão diária fictícia.
- GitHub Pages não executa código Python no clique do usuário: o botão atualiza previsão do navegador, não força um novo workflow no servidor.

## Segredos

Não guardar segredos neste repositório. Os serviços novos não exigem token. Não reutilizar credenciais compartilhadas anteriormente. Não habilitar OpenWeather One Call nem serviços com cobrança automática.

## Testes

```bash
python -m pytest -q
node --check site/static/app.js
node --check site/static/location.js
node tests/test_location_client.cjs
```

Os testes JavaScript com séries sintéticas são OFFLINE e servem apenas para checar lógica, não são previsões nem produtos publicados.
