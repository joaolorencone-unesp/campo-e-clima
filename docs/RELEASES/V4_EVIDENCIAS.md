# Evidências da versão 4 (05/11/2026)

Branch `claude/campo-clima-platform-qvl7e8` sobre `main` em `c881d31`. Tudo abaixo foi executado neste ambiente sem acesso à internet (apenas GitHub), portanto as partes que dependem de rede (Previous Runs nas estações, GOES, provedores de IA, modelos determinísticos adicionais) foram validadas com testes offline e só produzem números reais nos workflows do GitHub Actions.

## Testes automatizados

| Conjunto | Resultado |
|---|---|
| `python -m pytest -q` (todos os testes, offline) | 209 aprovados |
| Suítes Node offline (16 arquivos `tests/*.cjs`, incluindo `test_v40_frontend.cjs`) | 16 aprovadas |
| `tests/browser_v40.cjs` (Chromium real, desktop 1440×1000 e celular 390×844, hosts externos bloqueados) | 0 erros de JavaScript, sem estouro horizontal, 7 linhas no quadro semanal, 2 linhas em próximas semanas (GEFS/ECMWF não reproduzidos offline), boletim e cartão de estação visíveis, 3 estações com matriz de erro, controle GOES exibido, 6 linhas na comparação de modelos |

Novos testes: `tests/test_station_calibration_v40.py` (8, incluindo prova de que a origem móvel não vê o mês de teste), `tests/test_models_compare_v40.py` (5), `tests/test_ai_bulletin_v40.py` (9, incluindo datas, separador de milhar, números por extenso e orientações operacionais rejeitados), `tests/test_v40_frontend.cjs` (quadro semanal, próximas semanas, origem do boletim, comparação de modelos, correções no navegador idênticas às do Python, quadros GOES, contrato do HTML/CSS).

## Dados das estações físicas (arquivos reais enviados pelo usuário)

| Estação | Arquivo | Linhas | Horas sem dado | Sinalizações do QC | Dias completos de chuva |
|---|---|---|---|---|---|
| INMET S735 Naviraí (Faz. Santa Helena do Pindo) | `data/stations/inmet_S735_navirai_2026-05-05_2026-11-05.csv.gz` | 4 440 horas | 65 | nenhuma (as 2 quedas bruscas de temperatura são confirmadas pelos extremos horários) | 157 de 186 dias locais |
| INMET A949 Diamantino | `data/stations/inmet_A949_diamantino_2026-05-05_2026-11-05.csv.gz` | 4 440 horas | 19 | nenhuma (3 quedas bruscas confirmadas) | 183 de 186 |
| Embrapa Guia Clima Naviraí/IFMS | `data/stations/embrapa_guiaclima_navirai_ifms_2026-05-05_2026-11-03.html.gz` | 183 dias contínuos | 0 | nenhuma (3 dias sem rajada máxima) | 183 |

Coordenadas: S735 e A949 vêm do catálogo oficial INMET (`/estacoes/T`, arquivado na branch `weather-archive`); a estação Embrapa não informa coordenadas, por isso sua previsão usa o ponto municipal e fica marcada como aproximação.

## Calibração: o que foi e o que não foi verificado aqui

- Verificado offline: leitura e QC dos três arquivos reais; agregação por dia local; pareamento; origem móvel mensal com purga; bootstrap por blocos; recomendação só com ganho significativo. O teste `test_pipeline_recovers_known_bias_out_of_sample` injeta um viés conhecido em previsões sintéticas construídas sobre as observações reais e confirma que o método o recupera (viés de +1,8 °C detectado e corrigido com IC95 % de ΔMAE abaixo de zero).
- Não verificado aqui: as previsões reais do Previous Runs API (sem rede). A primeira execução de `science.yml` (diário) ou do workflow manual `station-calibration.yml` produz os relatórios reais; até lá a aba Observações informa que os resultados ainda não foram publicados.
- As capturas de tela desta pasta que mostram estações usam previsões sintéticas apenas para validar o layout; os números não são resultados científicos.

## Capturas de tela (`docs/RELEASES/v4/`)

`overview_simple_desktop.png`, `overview_simple_mobile.png`, `weekly_board_desktop.png`, `weekly_board_mobile.png`, `weeks_ahead_*.png`, `bulletin_*.png`, `station_overview_*.png`, `stations_desktop.png`, `stations_mobile.png`, `maps_goes_desktop.png`, `models_compare_desktop.png`, `overview_advanced_desktop.png`, `browser_report.json`.

## Execuções com rede (CI do PR, 05/11/2026)

O job não bloqueante `stations-preview` consultou o Previous Runs API nas coordenadas das três estações em duas rodadas (06:40 e 06:54 UTC; a segunda já com as janelas de extremos, a janela solar da radiação e o mínimo de dias úmidos). Os sete modelos responderam nas duas estações INMET. Erro absoluto médio bruto em D1 sobre todos os pares (segunda rodada):

| Estação | Temperatura horária | T máx diária | T mín diária | Chuva diária | Radiação diária |
|---|---|---|---|---|---|
| INMET S735 Naviraí | multimodelo 1,38 °C · ICON 1,39 · ECMWF 1,42 · GFS 1,58 · JMA 2,08 | ICON 1,60 °C (viés −0,4) · UKMO 1,80 · ECMWF 2,15 (viés −1,06) | GFS 1,26 °C · ECMWF 1,27 · JMA 2,88 (viés +2,8 → 1,20 corrigido) | UKMO 3,08 mm · multimodelo 3,33 · GEM 3,49 · GFS 3,67 | ICON 2,40 MJ/m² · ECMWF 2,43 (viés +1,5) |
| INMET A949 Diamantino | ICON 1,55 °C · ECMWF 1,70 (→ 1,54 por hora do dia) · GFS 2,07 | ARPEGE 1,66 °C · ICON 1,96 (viés −1,64 → 1,02) · ECMWF 2,40 (viés −2,08 → 1,14) | ECMWF 1,08 °C · ICON 1,24 | GEM 1,95 mm (estação seca: sem dias úmidos suficientes para calibrar) | ICON 3,57 MJ/m² (viés +3,3 → 1,94) · ECMWF 4,58 (viés +4,55 → 1,97) |

Padrões recorrentes: todos os modelos subestimam o vento horário em Naviraí (viés de −1 a −5 km/h) e o superestimam em Diamantino (ECMWF +1,7; GFS +3,6 km/h); o GFS subestima a umidade relativa em ~8 pontos em Naviraí e ~21 pontos em Diamantino (corrigível para MAE 11,6); as mínimas diárias saem quentes demais em quase todos os modelos; a radiação dos modelos é alta demais em Diamantino (+3 a +4,6 MJ/m²/dia). Correções de chuva só com ganho marginal (≤ 9 %) em Naviraí e nenhuma em Diamantino. Nada substitui a previsão principal: as correções validadas aparecem na aba Observações após a publicação pelo fluxo diário.

## Produção (contexto)

A execução 66 do fluxo `Collect and deploy` em `main` (05/11/2026, 05:27 UTC), primeira após a integração da v3, publicou os dois pontos com 8 ensembles cada e diagnóstico `ok`; a v4 não altera o deploy até ser integrada.
