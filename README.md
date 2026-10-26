# Campo & Clima 🌦️🌱

**Painel agrometeorológico experimental para Naviraí–MS**, com prioridade para previsão de **chuva**, **vento/rajadas**, **pulverização com drones** e planejamento da entrada de máquinas. Projeto de código aberto em desenvolvimento; **as frequências de membros dos ensembles não são probabilidades calibradas**.

- 🌐 **Site publicado:** https://joaolorencone-unesp.github.io/campo-e-clima/
- 🧭 Coordenadas: **-23.065, -54.190**; horário: **America/Campo_Grande (UTC−4)**.
- 🔗 [GitHub](https://github.com/joaolorencone-unesp/campo-e-clima) · [Documentação das integrações](docs/INTEGRACOES_V06.md) · [Guia de atualização](ATUALIZAR_GITHUB_v06.md) · [Auditoria Embrapa](docs/AUDITORIA_EMBRAPA_20261026.md)

> **Versão: 0.6 (26/10/2026)** — os 35 testes de unidade/integridade passaram offline. A execução real dos conectores novos deve ser verificada após publicar no GitHub Actions. Ter código implementado ≠ serviço confirmado funcionando na produção.

## O que funciona / o que está sendo testado

| Recurso | Estado |
|---|---|
| Open-Meteo Forecast e 8 ensembles com chuva e vento D0–D6 | ✅ Já validado em GitHub Actions na versão anterior |
| Comparação de modelos, quantis, excedências, janelas de chuva 1/3/6h | ✅ Já implementado, não calibrado |
| Triagem conjunta de pulverização meteorológica por membro e janelas de 2h | ✅ Implementado como **triagem**, nunca autorização |
| INMET: avisos filtrados por IBGE 5005707 e catálogo de estações | ✅ Conector da v0.5, validar resposta real após execução |
| Embrapa: exportação HTML `.xls` com 700 registros | ✅ 694 dias convertidos **provisoriamente**, 6 em quarentena; falta confirmar a estação selecionada |
| CPTEC/INPE: previsão independente D0–D6 em XML | 🧪 Novo conector; verificar rede/HTTPS, município e atualização |
| OpenWeather One Call 3.0 | 🔑 Novo conector; necessita chave e plano compatível |
| Open-Meteo: umidade do solo em grade | 🧪 Novo conector; pode não haver cobertura da variável selecionada |
| NASA POWER: chuva histórica estimada em grade | 🧪 Novo conector; cache diário |
| ECMWF EC46/SEAS5: cenários semanais D14–D55 | 🧪 Novo conector; cache diário, baixa resolução e incerteza |
| GOES-19 DSAT, GPM/IMERG, radar/raios, SoilGrids | 📖 Links oficiais e estado documentados; processamento geográfico/credenciais pendentes |
| Métricas reais de acurácia versus observação local | ⏳ **Ainda não disponíveis**; requer identificar estação e armazenar emissões anteriores |

## Estrutura do projeto

```text
.github/workflows/pages.yml         Atualização e publicação com cache diário para produtos lentos
scripts/collect.py                 Meteorologia Open-Meteo e orquestração de fontes
scripts/spraying.py                Triagem por membro e cenários de pulverização
scripts/verify.py                  Funções de validação de previsão
scripts/sources/official.py        INMET e catálogo de estações
scripts/sources/embrapa.py         Importação normalizada estrita para estação confirmada
scripts/sources/embrapa_export.py  Leitura/auditoria do .xls HTML recebido
scripts/sources/supplementary.py   CPTEC, OpenWeather, NASA POWER, EC46, solo
site/index.html                    Site e abas
site/static/app.js                 Gráficos e navegação
site/static/styles.css             Tema claro e layout responsivo
data/observacoes/embrapa_exportacao_provisoria.csv  694 dias SEM estação confirmada
site/data/latest.json              Saída GERADA pelo GitHub Actions (não versionada)
site/data/slow_sources_cache.json  Cache temporário por dia (não versionado)
tests/                             Testes offline; dados fictícios só nos testes
```

## Instalação local

Python >=3.11:

```bash
python -m pip install -r requirements.txt
python -m pytest -q
python scripts/collect.py
python -m http.server 8000 --directory site
```

Abra `http://localhost:8000`. A aquisição depende de internet e da disponibilidade das APIs. Falhas não são substituídas por valores antigos rotulados como atuais.

## Implantar via GitHub Desktop

Leia [ATUALIZAR_GITHUB_v06.md](ATUALIZAR_GITHUB_v06.md). Para atualizar basta copiar o ZIP para a pasta clonada e fazer `Commit to main` + `Push origin`. O workflow já publica o GitHub Pages e tenta coleta a cada ~30min (sem garantia de horário exato).

### Configurar OpenWeather

No GitHub: `Settings → Secrets and variables → Actions → New repository secret`; nome **`OPENWEATHER_API_KEY`**. A chave deve oferecer acesso à API **One Call 3.0**. **Nunca publique tokens no repositório, em logs nem no chat.** A ausência desse secret não impede Open-Meteo, CPTEC ou INMET.

### Embrapa: confirmação da estação (pendente)

O arquivo `.xls` enviado é HTML sem ID da estação. Não é possível provar apenas pelos números que pertence à estação **Naviraí/IFMS (6)**. Foram isolados 6 registros anteriores a 01/12/2024 e incorporados 694 registros diários de 01/12/2024–25/10/2026 como **PROVISÓRIOS**. Confirmar seleção no portal da Embrapa antes de usar esses dados como referência definitiva de verificação. A extração automatizada da Embrapa **não foi implementada como API pública**, pois não identificamos endpoint estável autorizado.

## Metodologia e segurança

- **Chuva:** pesos totais iguais por ensemble como baseline, membros válidos, P10/P50/P90 ponderados; chuva acumulada calculada dentro de cada membro antes da mistura.
- **Vento/rajadas:** direção meteorológica = **de onde sopra**; rajada de janela é o **máximo**, nunca soma; grade ≠ medição em talhão.
- **Pulverização:** classe “meteorologicamente candidata” **não significa operação autorizada**. Bula, estabilidade, inversão, gotas, altura, deriva, culturas sensíveis, polinizadores e regras MAPA/ANAC prevalecem.
- **Máquinas:** umidade do solo do modelo em grade não é índice calibrado de trafegabilidade.
- **Longo prazo:** tendências EC46/SEAS5 são semanais, não previsão diária de pulverização.
- **Histórico de acertos:** sem arquivar emissão/membro/validade e sem observação independentemente identificada, NÃO informar porcentagem de acerto.

## Fontes, autoria e termos

[Open-Meteo](https://open-meteo.com/en/docs) · [INMET](https://portal.inmet.gov.br/) · [Embrapa](https://www.cpao.embrapa.br/gc/busca-de-dados) · [CPTEC/INPE](https://servicos.cptec.inpe.br/XML/) · [NASA POWER](https://power.larc.nasa.gov/) · [NASA GPM](https://gpm.nasa.gov/) · [ISRIC](https://docs.isric.org/globaldata/soilgrids/).

Verificar direitos sobre redistribuição das séries exportadas da Embrapa e os termos das APIs, em especial para serviços comerciais e aumento de volume. Não há licença de código explicitamente escolhida nesta versão.
