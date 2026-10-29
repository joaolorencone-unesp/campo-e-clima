## v2.1 — Central Agro e retrospectiva meteorológica recente (28/10/2026)

- Nova aba **🌱 Central Agro**: filtro por operação (pulverização, plantio, colheita e irrigação), 24/48/72 h de previsão, chuva, vento, rajadas, UR/VPD e restrições por horário.
- Comparação **>0,1 mm vs. >1 mm** dos ensembles válidos, com fonte, contagem de modelos/membros e aviso de **frequências não calibradas**.
- Formulário experimental para operação com **DJI Agras T100** (cultura, altura pretendida, gotas, áreas sensíveis e itens de verificação), sem prescrição automática de altura, dose ou liberação de pulverização.
- **Ontem/anteontem** para Naviraí, Diamantino ou outras coordenadas, sob demanda, via Open-Meteo Forecast `past_days=4`; retrospectiva **modelada**, não observação de estação.
- Proteção contra mistura de previsões de cidades diferentes; série incompleta não é tratada como chuva zero; testes automatizados e simulação no Chromium.
- Sem nova API paga, sem credenciais embutidas. Veja `docs/CENTRAL_AGRO_V21.md` e `ATUALIZAR_GITHUB_V21.md`.


## v1.9 — Avisos INMET compactos, radar e histórico automático (28/10/2026)

- Avisos INMET de Naviraí agrupados visualmente por fenômeno e severidade; cada aviso e suas vigências originais continuam disponíveis.
- Radar **observado** RainViewer em Mapas & nuvens, com quadros passados, hora local e playback; sem garantia de cobertura e sem nowcasting futuro. Previsão Open-Meteo agora representada por nove pontos circulares, não células preenchidas. Links para animações oficiais INMET/INPE.
- Histórico NASA POWER × ERA5 atualizado diariamente pelo GitHub Actions, em `site/data/history_navirai.json`, com cache e preservação da última coleta bem-sucedida. É estimativa de grade, não estação. Histórico por outras coordenadas continua sob consulta ao abrir a seção respectiva.
- Máquinas & solo removida da navegação principal por falta de validação, preservando código experimental.
- Falhas do ECMWF estendido resumidas para leitura; diagnóstico técnico permanece em Qualidade & fontes.
- Sem novas credenciais embutidas e sem novas APIs pagas. **Leia `docs/MELHORIAS_V19.md` e `ATUALIZAR_GITHUB_V19.md`.**

## v1.4 — Mapas e imagens de satélite (atualização)

- Aba **🛰 Mapas & nuvens**: mapa por coordenadas, 48 horas de nuvens (total/baixas/médias/altas), chuva e vento em grade Open-Meteo (9 amostras, sem pretensão de alta resolução espacial).
- Camadas **NASA GIBS** MODIS Terra/VIIRS NOAA-20 por data UTC, imagens orbitais observadas (não GOES ao vivo; horário da passagem não verificado).
- **Bússola do vento** na aba de vento mostrando origem meteorológica e sentido oposto do transporte potencial.
- Links para NASA Worldview, GPM/IMERG e CPTEC/INPE GOES-19. Fontes gratuitas, sem novas chaves.
- Atualização do mapa sob demanda, cache 2h; ver `docs/MAPAS_SATELITE_V14.md` e `ATUALIZAR_GITHUB_V14.md`.

# Campo e Clima v1.3 — meteorologia multimodelo, histórico e operação agrícola

**Novo nesta edição:** formulário de latitude/longitude WGS84, link compartilhável por ponto, consulta direta de Forecast e até oito ensembles da Open-Meteo para coordenadas selecionadas, gráficos NASA POWER (chuva/temperatura histórica), reanálise ERA5-Land, altitude, qualidade do ar e umidade superficial modelada. Sem serviços pagos e sem novas chaves. A publicação permanece pelo GitHub Desktop/Actions. **O GitHub Pages não é um servidor de APIs.**

Documentação: [Coordenadas e fontes v0.9](docs/COORDENADAS_E_FONTES_V09.md) · [Como publicar](ATUALIZAR_GITHUB_v09.md).

---

> **v0.8 — atualização de interface (26/10/2026).** Veja [o que foi corrigido](docs/CHANGELOG_V08.md) e [como instalar](ATUALIZAR_GITHUB_v08.md). O botão consulta diretamente a previsão **determinística** atual da Open-Meteo; os ensembles continuam na coleta do GitHub Actions. Sem novas APIs pagas.

# Campo & Clima 🌦️🌱 — versão 0.7 (somente fontes gratuitas)

Painel agrometeorológico **experimental e aberto** para Naviraí–MS, com prioridade para **chuva, vento e rajadas, pulverização com drones e condições dos talhões**. Coordenadas de referência: **-23.065, -54.190**; fuso **America/Campo_Grande (UTC−4)**.

**Site público atual:** https://joaolorencone-unesp.github.io/campo-e-clima/  
**Código e histórico:** https://github.com/joaolorencone-unesp/campo-e-clima

> **Não utilizamos APIs pagas.** OpenWeather **One Call foi desabilitada**; somente a API **gratuita 5 dias/3h** poderá ser consultada **opcionalmente**, se o usuário criar uma **nova** chave Free e salvá-la em GitHub Secret (sem cartão/assinatura). Nenhuma credencial da NASA/Google/OpenWeather enviada por chat está incluída nos scripts ou ZIPs. **Revogue as credenciais expostas anteriormente.**

## O que a versão 0.7 integra

| Fonte | Dados | Estado metodológico |
|---|---|---|
| Open-Meteo Forecast | Previsões horárias/determinísticas de até 14 dias | Já validada nas versões anteriores |
| Open-Meteo Ensemble — 8 modelos | Chuva e rajadas por membro, cenários conjuntos de pulverização | Frequências brutas **não calibradas**; disponibilidade variável |
| INMET | Avisos com município IBGE 5005707, cadastro de estações, tentativa de observações diárias | Conector operacional: conferir estado e atualização em cada coleta |
| Embrapa Guia Clima | 694 registros históricos da exportação fornecida, dezembro/2024 a outubro/2026 | **Provisório**: arquivo não identifica inequivocamente a estação 6 |
| CPTEC/INPE | Previsão qualitativa sete dias, quando a resposta XML é válida | Referência independente, **não adicionada** aos ensembles |
| NASA POWER | Estimativa histórica em grade de precipitação | Atualização/cache diário; **não é pluviômetro** |
| ECMWF EC46/SEAS5 via Open-Meteo | Tendências semanais 15–60 dias, se disponíveis | Resolução ~36 km e incerteza elevada |
| Open-Meteo Forecast Solo | Umidade superficial e ET0 em grade, quando válidas | Não é sensor de talhão nem indicador de trafegabilidade calibrado |
| **Open-Meteo ERA5-Land (novo)** | **Climatologia mensal de chuva 1991–2020** | Reanálise em grade; **não** é clima medido na Embrapa |
| **Open-Meteo Previous Runs (novo)** | **Previsões antigas com antecedência horária fixa 1d/3d** | Verificação exploratória, **não** reproduz as 8 ensembles |
| NOAA GOES-19 (novo link) | Visualização gratuita do setor sul da América do Sul | Apenas link oficial com data do próprio produto, **não** leitura automática/radar municipal |
| OpenWeather Free 5d/3h | Comparação externa com intervalos de 3 horas | **Opcional**, nova chave Free em `OPENWEATHER_FREE_API_KEY`, sem One Call e sem pagamento |

**Ainda não operacionais:** NASA GPM/IMERG geoespacial autenticado; SoilGrids WCS/Earth Engine; processamento automático de radar/raios; armazenamento histórico permanente e calibração estatística local. São integrações gratuitas possíveis em etapas futuras, mas necessitam código, testes e/ou autorização — não devem ser simuladas como dados atuais.

## Ciência e cuidados de interpretação

- Mistura de oito ensembles com pesos totais iguais por modelo válido; **dependências institucionais** ECMWF IFS/AIFS e NOAA GEFS/AI-GEFS não desaparecem com a ponderação.
- Quantis P10/P50/P90 e frequências de chuva devem usar valores de membros válidos, sem imputar ausências como zero. Rajadas em janela = **máximo**, nunca soma.
- Triagem conjunta de pulverização usa as mesmas variáveis do mesmo membro. **Não aprova defensivos**: bula, inversão, vento na altura de voo, polinizadores, deriva, equipamentos e medições locais são obrigatórios.
- O diagnóstico de previsões antigas compara dias de validade alinhados, mas a série da Embrapa permanece **sem identificação confirmada**. Nenhum índice MAE/Brier/CRPS é anunciado como acurácia científica.
- ERA5-Land e NASA POWER são **produtos modelados em grade**, não substitutos de medição de pluviômetro e não fontes independentes para aferir acurácia.
- A API Previous Runs entrega previsões em horas com antecedência fixa de 24h/72h; o total diário é a soma de 24 horas dessas séries, **não** uma única rodada de previsão emitida às 7h.
- Horizonte 30–60 dias é **tendência semanal**, não previsão operacional diária.

## Estrutura de código

```text
.github/workflows/pages.yml       GitHub Actions: publicação a cada ~30min (sem garantia de pontualidade)
scripts/collect.py                Orquestração do dado público
scripts/spraying.py              Triagem conjunta dos membros e janelas >=2h
scripts/sources/official.py      INMET: avisos, estações e observação próxima
scripts/sources/supplementary.py CPTEC, NASA POWER, EC46/SEAS5, solo modelado
scripts/sources/free_research.py  NOVO: ERA5-Land, Previous Runs, comparação provisória e OpenWeather **Free**
scripts/sources/embrapa_export.py Auditoria da exportação HTML/.xls
data/observacoes/                Série provisória recebida do usuário
site/index.html                  Site e abas
site/static/app.js               Gráficos e filtros
site/data/                      JSONs gerados no workflow, NÃO versionados
  latest.json                   Edição corrente
  slow_sources_cache.json       Cache diário de produtos mais lentos
  climate_cache.json            Cache mensal de referência climatológica
tests/                           Testes sem chamadas externas
```

## Implantação no GitHub

Veja **[ATUALIZAR_GITHUB_v07.md](ATUALIZAR_GITHUB_v07.md)**. Com o GitHub Desktop, copiar o conteúdo do ZIP **somente atualização** na pasta clonada, substituir arquivos, fazer commit e push. Verificar **Actions** → execução verde e, no site, status real de cada fonte. A publicação pública **não é feita automaticamente por este chat**, pois a integração GitHub disponível não autorizou gravações.

## Reproduzir localmente

```bash
python -m pip install -r requirements.txt
python -m pytest -q
node --check site/static/app.js
python scripts/collect.py
python -m http.server 8000 --directory site
```

`collect.py` precisa de internet. Sem APIs respondendo, o script indica indisponibilidade e não deve publicar valores antigos como recentes.

## Custos, proteção e licenças

As chamadas programadas utilizam **somente serviços gratuitos**, sem One Call ou planos por uso. A [Open-Meteo Free API](https://open-meteo.com/en/terms) permite acesso sem chave com limites de tráfego e atribuição CC BY 4.0, mas **não concede licença para atividade comercial**. NASA POWER, CPTEC/INPE e INMET possuem seus próprios termos. GitHub Pages/Actions também estão sujeitos a políticas e cotas da conta. Não informar chaves, tokens ou senhas por chat e não adicionar credenciais ao repositório. O token NASA Earthdata/Google API compartilhados anteriormente **não são utilizados**.

## Referências principais

- [Open-Meteo Ensemble](https://open-meteo.com/en/docs/ensemble-api)
- [Previous Runs](https://open-meteo.com/en/docs/previous-runs-api)
- [Histórico Archive / ERA5-Land](https://open-meteo.com/en/docs/historical-weather-api)
- [ECMWF sazonal via Open-Meteo](https://open-meteo.com/en/docs/seasonal-forecast-api)
- [INMET](https://portal.inmet.gov.br/)
- [CPTEC/INPE XML](https://servicos.cptec.inpe.br/XML/)
- [Embrapa Guia Clima](https://www.cpao.embrapa.br/gc/guia-clima?cod_estacao=6)
- [NOAA GOES-19](https://www.star.nesdis.noaa.gov/goes/sector_band.php?band=13&length=24&sat=G19&sector=ssa)
- [NASA POWER](https://power.larc.nasa.gov/)
- [SoilGrids (REST interrompida)](https://docs.isric.org/globaldata/soilgrids/)

### OpenWeather gratuito (opcional, não obrigatório)

A API oficial [5-day / 3-hour forecast](https://openweathermap.org/api/forecast5) pertence ao plano Free. **Não use a chave antiga exposta no chat**; primeiro revogue-a e gere outra de plano Free. Salve-a SOMENTE em GitHub → Settings → Secrets and variables → Actions → New repository secret, com o nome exato **`OPENWEATHER_FREE_API_KEY`**. O código usa apenas `https://api.openweathermap.org/data/2.5/forecast`, não a One Call 3/4. Sem novo segredo a integração aparece como opcional e **não há chamada externa**. Mesmo com integração, a previsão externa é apenas comparação textual, não membro extra dos oito ensembles.

## 🌦️ v1.0 — Histórico diário + fontes gratuitas por coordenada (27/10/2026)

Foi acrescentada na aba **Histórico & indicadores** uma seção de histórico ERA5-Land com filtros de 30/90/365 dias, chuva diária, T mínima/máxima/média, ET₀, rajadas e exportação CSV, mais gráficos de comparação NASA POWER × ERA5-Land com ambas as séries no dia UTC. Na NASA POWER a API passa explicitamente `time-standard=UTC` para evitar comparar tempo solar local com UTC sem aviso.

Também há pré-triagem RETROSPECTIVA de horas diurnas usando até 31 dias de variáveis horárias completas (sem aprovação automática de pulverização) e consulta a um **catálogo INMET de estações próximas por coordenadas** gerado pelo workflow. Estações são metadados, não observações. Erros de API são explicitados e gráficos não recebem valores de exemplo na página pública.

Leia a [documentação científica dos produtos históricos e a arquitetura](docs/OPEN_METEO_HISTORICO_V10.md). Os dados externos históricos por coordenadas precisam de validação na primeira visita ao site (o ambiente local de criação não conseguiu se conectar aos servidores da Open-Meteo); teste unitário offline não equivale a sucesso da coleta externa.


## Atualização v1.1 — pulverização horária e estação S735

A aba de pulverização apresenta gráficos da previsão **determinística por hora** (vento, rajadas, umidade e VPD) e gráficos **separados** das frequências conjuntas dos ensembles por hora e por janelas de 2h. Os cenários têm quatro classes: `passa filtros`, `marginal`, `restrito` e `indeterminado` (noturno sem verificação de inversão). **Nenhuma classe constitui aprovação operacional ou probabilidade calibrada de aplicação segura.** O filtro 07–17h não substitui avaliação de estabilidade/inversão nem observações no campo.

Na aba Observações & fontes, o sistema tenta ler a estação [S735 — Naviraí (Faz. Santa Helena do Pindo)](https://apitempo.inmet.gov.br/estacoes/T), entidade SEMADESC-MS, a cerca de 37,6 km da sede. A consulta horária é **experimental** e pode não funcionar fora dos sistemas oficiais do INMET; os códigos distinguem `ok`, `no_data` e `unavailable` sem criar medições. [Documentação detalhada](docs/PULVERIZACAO_HORARIA_INMET_V11.md).

Quando o usuário seleciona outra coordenada, o sistema não reutiliza a observação S735 nem o aviso de Naviraí como se fossem medições daquele talhão. Os próprios ensembles são atualizados para o ponto conforme disponibilidade.


## v1.2 — correção histórica e explicação das restrições

[Detalhes científicos e limitações](docs/CORRECOES_V12.md). O quadro de pulverização detalha causas horárias sem converter frequências não calibradas em probabilidades de segurança. Dados históricos: ERA5 para precipitação/atmosfera, ERA5-Land para rajadas/ET₀ onde válidos. Tendências de 15–60 dias: consulta leve do ECMWF Seasonal Ensemble Mean no Actions para Naviraí e por coordenadas no navegador; médias semanais não são P10/P90 ou chuva diária.

## v1.3 — estabilização da previsão estendida, histórico e pulverização

A API sazonal deixou de ser chamada diretamente pelo navegador: os produtos do ECMWF são publicados pelo GitHub Actions com cache de **uma consulta por semana**. Uma recuperação controlada tenta quatro dias de chuva quando algum ensemble apresenta timeout (sem inventar rajadas). Um novo coletor **GEFS diário D15–D35** tenta obter quantis de um único ensemble, sem inventar datas se a API retornar dados incompletos. Calendário mostra apenas dias com previsão válida e informação de cobertura. Em histórico, há tentativa adicional à Open-Meteo `best_match` e alternativa identificada NASA POWER se a precipitação ERA5 estiver inteiramente indisponível. Na pulverização, o resumo destaca fatores limitantes da janela escolhida e o número real de modelos/membros. Não são probabilidades calibradas de segurança.

Leia [documentação científica e limitações v1.3](docs/MELHORIAS_V13.md) e [atualização do GitHub](ATUALIZAR_GITHUB_V13.md). A disponibilidade real das novas consultas será verificada após a primeira execução do GitHub Actions.

## v1.5 — ensembles sob demanda para coordenadas personalizadas

Para locais como Diamantino–MT, a coleta de chuva foi separada da consulta de pulverização. Resultados válidos são exibidos progressivamente, erros de API não se tornam cache válido, e a previsão da Forecast API é usada como **referência distinta**, sem inventar probabilidades multimodelo. Consulte [ATUALIZAR_GITHUB_V15.md](ATUALIZAR_GITHUB_V15.md) para instalação, comportamento e limites da versão.


## v1.6 — chuva residual, frequência de tempo seco e concordância dos modelos

A aba **Chuva & ensembles** mostra agora a frequência de **>0,1 mm/dia** ao lado de **>1, >5, >10 e >20 mm/dia**, além da frequência **≤0,1 mm/dia** (praticamente seco) na tabela. A coluna **0,1–1 mm/dia** equivale à diferença `P(>0,1) − P(>1)` na mesma amostra, e não à soma de probabilidades independentes.

Foram acrescentados um gráfico de cenários exclusivos (≤0,1; >0,1–1; >1–5; >5 mm) e uma comparação interativa por ensemble e dia, evidenciando modelos que preveem predominantemente chuva residual. A análise por coordenada personalizada utiliza membros do local escolhido, nunca reaproveitando os de Naviraí.

A tabela horária já tinha >0,1 e >1 mm/h, e agora os gráficos horários e as janelas de 3/6 horas também mostram ambos os limiares. A mistura multimodelo continua com peso total igual por ensemble válido. **São frequências brutas não calibradas, não previsão de chuva observada nem garantia de ocorrência.** Consulte [docs/CENARIOS_CHUVA_V16.md](docs/CENARIOS_CHUVA_V16.md).


## Campo e Clima v1.8 — correção temporal e validade dos ensembles

- **Próximas 72 horas:** os cenários de precipitação e pulverização começam na primeira hora inteira futura (Naviraí UTC−4, ou fuso da coordenada na consulta pelo navegador). A previsão diária continua abrangendo dias locais completos. O painel indica separadamente a cobertura horária determinística e a probabilística.
- **Convenção da Open-Meteo:** a precipitação rotulada `t` acumula a hora anterior `(t−1,t]`. Uma janela de 1/3/6 horas que **começa em `t`** utiliza a precipitação dos horários `t+1` até `t+duracao`. Séries espaçadas de três horas não são convertidas artificialmente em acumulados de uma hora.
- **Membros válidos:** o inventário apresenta **válidos / declarados**. O cálculo sempre usa membros completos para cada data/janela, com contagens por dia guardadas nos metadados. Campos declarados totalmente `null` não contam como previsões utilizáveis.
- **Pulverização:** os cenários tradicionais de quatro classes permanecem, mas há também as frequências separadas de **triagem numérica** (passa, marginal, restrita) e um quadro permanente de **verificações operacionais pendentes**. "Indeterminado" não representa chance de inversão ou autorização de aplicação.
- **Coordenadas:** no navegador, as consultas de chuva e de pulverização também filtram horários anteriores à consulta e preservam o fuso devolvido pela API.

Documentação técnica e limitações: [`docs/CORRECOES_V18.md`](docs/CORRECOES_V18.md). Os testes offline não confirmam disponibilidade futura de todos os modelos na API pública, nem calibração local.
