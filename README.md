# Campo e Clima 🌦️🚜

Painel agrometeorológico de pesquisa para **Naviraí–MS** (-23.065, -54.190; `America/Campo_Grande`, UTC-4).

**Site proposto:** https://joaolorencone-unesp.github.io/campo-e-clima/

> **Estado:** primeira versão experimental. Dados meteorológicos apenas quando coletados de fontes reais; as frequências de ensemble ainda não estão calibradas contra observações locais. O sistema NÃO autoriza pulverização ou entrada de máquinas.

## Recursos entregues nesta versão

- Site responsivo com abas: visão geral, chuva, vento, pulverização, máquinas, histórico e 30–60 dias.
- Coletor Python para Open-Meteo Forecast e oito ensembles de chuva, além de rajadas onde a variável estiver disponível, com falhas explicitadas.
- Mistura de ensembles por **peso total igual por modelo** e membros válidos; quantis ponderados.
- Workflow GitHub Actions programado a cada 30 minutos (execução sem pontualidade garantida) que publica no GitHub Pages.
- Botão para consultar a última coleta publicada; horário da última coleta exibido no painel. O botão não força execução do servidor, apenas recarrega o JSON publicado.
- Scripts de validação inicial (Brier, erro absoluto, viés) e testes; **sem validação real com dados externos neste ambiente**.
- Documentos científicos, inventário de fontes e roteiro de desenvolvimento.

## Instalação local

```bash
python -m pip install -r requirements.txt
python -m pytest -q
python scripts/collect.py
python -m http.server 8000 --directory site
```

Abra http://localhost:8000. O coletor depende de acesso HTTPS às APIs Open-Meteo. O site não exibirá probabilidades fictícias se a coleta falhar.

## Publicação

1. Leia [GUIA_PUBLICACAO.md](GUIA_PUBLICACAO.md) e importe todos os arquivos **e as pastas ocultas** para a raiz do repositório GitHub `joaolorencone-unesp/campo-e-clima`.
2. No GitHub, entre em **Settings → Pages → Build and deployment → GitHub Actions**.
3. Em **Actions → Collect and deploy Campo e Clima → Run workflow**, execute a primeira coleta.
4. Verifique logs e abra a URL proposta acima. Um repositório existente **não prova** que Pages está ativo.

## Estrutura

```
.github/workflows/pages.yml   # agendamento e deploy
scripts/collect.py           # Forecast + 8 ensembles de chuva
scripts/verify.py            # métricas de verificação
tests/test_ensemble.py       # testes unitários
site/index.html              # painel em abas
site/static/app.js           # gráficos, atualização e informações
site/static/styles.css       # tema claro responsivo
site/legacy-dashboard.html   # primeira versão anterior, preservada
site/data/latest.json        # criado na execução; não versionar
 docs/METODOLOGIA.md         # critérios, fórmulas, limites
 docs/FONTES.md              # fontes e situação de integração
 docs/ROADMAP.md             # próximas etapas
```

## Qualidade científica

Dados ausentes permanecem ausentes, nunca `0`. Previsões determinísticas e membros probabilísticos não são misturados. Probabilidades brutas só serão consideradas calibradas após backtesting **temporal** com observações auditadas. Consulte [Metodologia](docs/METODOLOGIA.md), [Fontes](docs/FONTES.md) e [Roadmap](docs/ROADMAP.md).

## Autorias e licenças

Atribuição: [Open-Meteo](https://open-meteo.com/), dados condicionados aos respectivos termos; verifique licença e limites de uso em produção. A licença do código ainda precisa ser escolhida. Não exponha chaves de API no repositório público.


## Particularidades da versão 0.2
- Chuva **D0–D6**: quantis e frequências diárias sem calibração; número válido por modelo e dia.
- Rajadas **D0–D6**: evento = máxima diária >30/>40/>60/>80 km/h, não soma de velocidades.
- Temperatura, UR, vento, rajadas, pressão e chuva **determinísticos** disponíveis até onde a API responder; previsão diária até 14 dias.
- O calendário de 30 dias mostra dados determinísticos **somente para datas com previsão disponível**; demais aparecem como indisponíveis. Não oferece previsão operacional a 60 dias.
- Nowcasting oficial, imagens GOES/radar/raios, histórico Embrapa, calibração local e triagem probabilística conjunta de pulverização ainda estão em **desenvolvimento**, explicitamente identificados.
- Coleta automática pelo GitHub Actions é **agendada, não garantida pontualmente**; status deve ser monitorado em Actions.
- O GitHub Pages é público. Não armazene coordenadas sensíveis de talhões, segredos ou dados privados de produtores em commits públicos.
