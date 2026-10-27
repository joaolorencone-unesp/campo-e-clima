# Campo e Clima v0.9 — coordenadas personalizáveis e histórico NASA POWER

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
