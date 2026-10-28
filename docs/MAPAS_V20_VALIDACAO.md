# Metodologia e validação dos mapas — Campo e Clima v2.0

**Base usada:** código publicado no GitHub Pages na execução `versao 22` (28/10/2026). Arquivos alterados: `site/index.html`, `site/static/maps_v14.js`, `site/static/styles.css`, testes e workflow.

## Produtos separados

| Produto | Observado ou previsto | Janela | Legenda | Incerteza |
| --- | --- | --- | --- | --- |
| Radar RainViewer | Observado (mosaico de radares) | Até ~2h passadas, se disponível | dBZ, paleta Universal Blue | Disponibilidade/cobertura variável; intensidade da refletividade não é mm/h |
| NASA GIBS MODIS/VIIRS | Imagem orbital observada, mosaico diário | Data UTC selecionada | RGB cor natural, sem escala numérica | Horário exato da passagem sobre o talhão não conhecido |
| Open-Meteo Forecast (9 locais) | Previsão em grade | Próximas 48 horas | °C, %, mm/h, km/h e J/kg | Dados de grade, não sensores; amostragem regional não equivale a radar |
| INPE GOES / INMET | Visualizadores externos oficiais | Conforme serviço | Conforme a fonte | Não incorporados sem confirmar permissão, periodicidade e formato |

## Escala RainViewer

Somente paleta ID 2, **Universal Blue**; pontos amostrais da escala contínua, confirmados na tabela publicada pelo provedor:

- 10 dBZ: `#087fdb`
- 20 dBZ: `#6e0dc6`
- 30 dBZ: `#c06487`
- 40 dBZ: `#fac431`
- 50 dBZ: `#fe9a58`
- 60 dBZ: `#fd341c`

A escala expressa refletividade radar, não uma conversão calibrada em mm/h. Nem dBZ nem pixel transparente, isoladamente, comprovam chuva no solo ou ausência dela. O horário é o do **quadro composto**, que pode integrar imagens captadas em horários distintos.

## Controles

- **◀ Anterior / Próximo ▶**: avança ou retrocede um quadro e pausa a reprodução.
- **▶ Reproduzir**: começa do primeiro quadro quando o mais recente estava selecionado, mantém o anterior visível até o próximo carregar e encerra no mais recente.
- **Intervalo**: 1,8 / 2,8 / 4,2 segundos após carregamento; a conexão e os tiles podem reduzir a velocidade efetiva.
- **Legenda**: troca automaticamente de dBZ radar para escala de variável da Open-Meteo; opções NASA avisam ausência de escala numérica.
- **Horário**: quadro radar com hora local e UTC; previsão Open-Meteo com hora de validade, UTC e local; NASA com dia UTC, mas hora de passagem desconhecida.

## Segurança e integridade

Não apresentar imagens passadas de radar como previsão futura. Não atribuir quantificação de chuva em mm/h ao radar sem algoritmo quantitativo e validação. Não usar uma célula da Open-Meteo para afirmar posição exata de nuvem convectiva. Não usar mapa isoladamente para autorizar pulverização. RainViewer gratuita é voltada a uso pessoal/educacional e sujeita a limitação de requisições; se o painel adquirir tráfego comercial, revisar os termos e substituir a fonte, se necessário.

## Cobertura de testes

- 95 testes Python no conjunto de regressão v2.0.
- Testes JS existentes e novo teste de controles assíncronos `tests/test_maps_controls_v20.cjs`.
- A execução GitHub Actions agora testa a sequência radar antes da coleta.
- Teste real com o serviço e verificação visual no navegador ainda dependem da publicação; não há confirmação de cobertura local ou comportamento de cada navegador.

## Referências

- https://www.rainviewer.com/api/weather-maps-api.html
- https://www.rainviewer.com/api/color-schemes.html
- https://www.rainviewer.com/files/rainviewer_api_colors_table.csv
- https://www.rainviewer.com/api/transition-faq.html
- https://open-meteo.com/en/docs
- https://nasa-gibs.github.io/gibs-api-docs/access-basics/
