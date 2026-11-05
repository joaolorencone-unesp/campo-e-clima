# Estações físicas: verificação e correção de viés por estação (v4)

Objetivo: comparar as previsões determinísticas com as medições de três estações físicas, usando as coordenadas de cada estação, e publicar correções de viés **somente quando comprovadas fora da amostra**. Código: `scripts/science/station_files.py` (leitura e QC), `scripts/science/station_calibration.py` (pareamento, correções, validação), `scripts/station_calibration.py` (linha de comando). Testes: `tests/test_station_calibration_v40.py`.

## 1. Arquivos recebidos

| Estação | Arquivo (em `data/stations/`) | Conteúdo | Coordenadas usadas |
|---|---|---|---|
| INMET S735 — NAVIRAI (FAZ. SANTA HELENA DO PINDO), entidade SEMADESC-MS | `inmet_S735_navirai_2026-05-05_2026-11-05.csv.gz` | horário UTC, 05/05–05/11/2026 | −22,899909 / −53,869219, 303 m (catálogo INMET `/estacoes/T`, consultado 05/11/2026); 37,6 km do ponto municipal |
| INMET A949 — DIAMANTINO, entidade INMET | `inmet_A949_diamantino_2026-05-05_2026-11-05.csv.gz` | horário UTC, 05/05–05/11/2026 | −14,37777777 / −56,37972221, 317 m (catálogo INMET) |
| Embrapa Guia Clima — Naviraí (IFMS) | `embrapa_guiaclima_navirai_ifms_2026-05-05_2026-11-03.html.gz` | diário (dia local), 05/05–03/11/2026 | não informadas no arquivo: previsão consultada no ponto municipal (−23,065 / −54,190) e marcada como aproximada |

Os arquivos foram guardados comprimidos, com o SHA-256 do original em `data/stations/stations.json`. Nenhuma coordenada foi estimada: a estação Embrapa só passa a usar o ponto exato quando `latitude`/`longitude` forem preenchidas no registro.

Formatos. INMET (portal `tempo.inmet.gov.br/TabelaEstacoes/<código>`): `"Data";"Hora (UTC)";Temp. Ins./Max./Min.;Umi. Ins./Max./Min.;Pto Orvalho;Pressao;Vel. Vento (m/s);Dir. Vento;Raj. Vento (m/s);Radiacao (KJ/m²);Chuva (mm)`, decimal com vírgula. Para acumulados e extremos, o rótulo `HH00` cobre a hora que termina nele; instantâneos valem no rótulo. Vento e rajada são convertidos para km/h (×3,6); radiação kJ/m² para média horária em W/m² (×1000/3600). Embrapa: tabela HTML salva como `.xls` com T média/máx/mín, UR média/máx/mín, U2 (vento a 2 m), U2M, chuva, Rs e ET₀; reutiliza o leitor auditado `scripts/sources/embrapa_export.py`. O vento a 2 m é convertido para 10 m pelo perfil logarítmico FAO-56 (u2 = 0,748·u10, fator 1/0,748) apenas para comparação aproximada; a rajada a 2 m não é comparada.

## 2. Controle de qualidade (QC)

Só sinaliza; nada é corrigido ou interpolado. Valores vazios, `-9999` e ilegíveis viram ausentes (faltante ≠ zero).

| Teste | Regra | Marca |
|---|---|---|
| Faixa física | T −10…48 °C; UR 1…100 %; orvalho −20…35 °C; pressão 850…1050 hPa; vento 0…144 km/h; rajada 0…216 km/h; direção 0…360°; chuva 0…120 mm/h; radiação 0…1500 W/m² | `out_of_range` |
| Extremos horários | T mín − 0,3 ≤ T ≤ T máx + 0,3 (UR com tolerância 1) | `inconsistent_extremes` |
| Degrau | variação > 8 °C entre horas consecutivas | `step` |
| Sensor travado | ≥ 6 valores idênticos consecutivos de T; ≥ 12 de vento não nulo | `flatline` |
| Coerência | rajada < vento − 0,5 km/h; orvalho > T + 0,5 °C | `gust_below_speed`, `dew_above_temperature` |

Resultado nos arquivos recebidos: Naviraí S735 — 4440 linhas, 65 horas totalmente vazias, 2 degraus de temperatura, nenhum outro aviso; Diamantino A949 — 4440 linhas, 19 horas vazias, 3 degraus; Embrapa — 183 dias contínuos, sem lacunas de calendário, 3 dias sem rajada. Os degraus ficam excluídos dos pares, mas o valor original permanece no arquivo.

## 3. Agregação por dia local

Fuso UTC−4 para as três estações. Variáveis instantâneas (T, UR, vento, pressão) usam os rótulos cuja hora local cai em 00–23 h; acumulados e extremos horários (chuva, T máx/mín da hora, rajada, radiação) usam os rótulos de hora final 01–24 h local, como já fazia a previsão de chuva do projeto. Chuva diária só é publicada com 24 horas válidas (caso contrário fica "incompleta", com a soma parcial informada separadamente). Médias e extremos exigem pelo menos 20 horas válidas. Com essa regra, Naviraí tem 157 dias completos de chuva e Diamantino 183; a primeira e a última data de cada arquivo são parciais.

## 4. Previsões nas coordenadas das estações

Fonte: Open-Meteo **Previous Runs API** (`previous-runs-api.open-meteo.com`), gratuita e não comercial, consultada por blocos de 31 dias, um modelo explícito por pedido, variáveis `temperature_2m`, `relative_humidity_2m`, `precipitation`, `wind_speed_10m`, `wind_gusts_10m` e, quando o modelo oferece, `shortwave_radiation` e `et0_fao_evapotranspiration`, com sufixos `_previous_day1/2/3/7`. A antecedência é nominal: D_N significa a previsão emitida N dias antes do dia válido (24N a 24N+23 h).

Modelos padrão (`STATION_MODELS` pode substituir): `ecmwf_ifs025`, `gfs_global`, `icon_seamless`, `gem_global`, `meteofrance_arpege_world`, `ukmo_global_deterministic_10km`, `jma_gsm`. Um identificador que o provedor rejeita (HTTP 400) é isolado e relatado; um pedido com radiação/ET₀ rejeitado é repetido uma vez só com as variáveis centrais. Uma média multimodelo de peso igual (`multimodelo_media`) é calculada hora a hora com os modelos disponíveis. As respostas brutas entram na captura (`product=station_previous_runs`) e são arquivadas em `weather-archive/imports`, mas não entram no banco de verificação das sedes municipais, porque as coordenadas são da estação.

Os valores horários do modelo são agregados pelo mesmo procedimento do item 3; como o modelo não tem extremos dentro da hora, suas máximas e mínimas diárias vêm de valores horários instantâneos (diferença sistemática esperada frente à estação).

## 5. Correções candidatas

| Método | Variáveis | Forma |
|---|---|---|
| viés aditivo | T, UR, T máx, T mín, radiação, ET₀ | y = x + b |
| viés por hora do dia | T horária | b_h encolhido para o viés global com k = 10 pseudo-observações |
| regressão linear | todas as anteriores, vento | y = a + b·x (≥ 30 pares e variância positiva; senão vira viés) |
| fator multiplicativo | vento, rajada, chuva | y = r·x, r = Σobs/Σprev |
| mapeamento de quantis | chuva diária | tabelas empíricas de 25 quantis dos dias úmidos (> 0,2 mm); se o modelo tem mais dias úmidos que a estação, o limiar sobe até igualar a frequência observada; acima do maior quantil escala pela razão do topo |

Saídas são recortadas às faixas físicas (UR 0–100, chuva e vento ≥ 0).

## 6. Validação fora da amostra

Origem móvel por mês: cada mês é previsto com parâmetros ajustados só nos meses anteriores, descartando os últimos (antecedência + 1) dias antes do mês de teste (purga). Mínimos: 500 pares horários ou 25 diários de treino; 300 horários ou 45 diários de teste acumulado. O erro de cada método é comparado ao da previsão bruta no mesmo conjunto de teste; o intervalo de confiança de 95 % de ΔMAE vem de bootstrap por blocos (dias para séries horárias, semanas ISO para séries diárias; 1000 reamostragens, semente fixa). Uma correção só é **recomendada** quando o limite superior do intervalo é negativo e o ganho relativo de MAE é ≥ 5 %; o método vencedor é então reajustado em todos os pares para uso operacional, e a evidência (n de teste, MAE bruto e corrigido, intervalo, meses testados) é publicada junto. Quando nada passa, o relatório diz o motivo e o valor bruto permanece.

Métricas publicadas por estação × modelo × antecedência × variável: n, MAE, RMSE, viés (modelo − estação) de todos os pares e do conjunto de teste; para chuva, tabelas de contingência em 1 e 10 mm (POD, FAR, CSI, viés de frequência) brutas e corrigidas; para variáveis horárias em D1, viés e MAE por hora local e por mês.

## 7. Onde os resultados aparecem

- Aba **Observações** → painel "Estações físicas": últimos dias medidos, melhor modelo por variável em D1, matriz de MAE por antecedência com selo ✓ e ganho quando há correção validada, viés da temperatura por hora do dia, série de chuva medido × previsto D1 e o botão "Consultar previsão corrigida", que pede ao Open-Meteo a previsão atual no ponto da estação e aplica no navegador apenas as correções validadas, sempre ao lado do valor bruto (hoje e D4–D6 usam a antecedência validada mais próxima e são marcados como aproximação).
- **Visão geral** (modo simples): cartão com o último dia completo medido e a conferência do dia anterior (previsto D1 × medido).
- Arquivos: `site/data/stations/index.json` e `site/data/stations/<slug>.json` (ver [Dicionário de dados](DATA_DICTIONARY.md)).

## 8. Limitações

Seis meses de uma única estação por localidade; estações a 37,6 km (S735) ou com coordenadas não informadas (Embrapa) representam o ponto municipal apenas aproximadamente; extremos horários da estação versus valores instantâneos do modelo; rajada de 3 s no ponto versus máxima horária na grade; grade do provedor interpolada (9–25 km); o Previous Runs não informa a hora exata da inicialização; as recomendações valem para a estação e a época avaliadas e precisam ser reavaliadas conforme a série cresce; nenhuma correção é aplicada à previsão principal do painel.

## 9. Fluxo operacional

1. `science.yml` (diário) executa `python -m scripts.station_calibration --fetch --output-dir runtime/stations_public` com cache do Previous Runs (TTL 30 dias) e publica os relatórios em `public/stations/` da branch `weather-archive` via `scripts/archive_git.py`.
2. `pages.yml` (a cada 30 min) copia `public/stations/*.json` para `site/data/stations/` em `scripts/export_science_public.py`, validando o esquema; na falta do arquivo, as cópias anteriores permanecem.
3. `station-calibration.yml` (manual, qualquer branch) roda a mesma verificação com rede, imprime o resumo no log e guarda um artifact por 14 dias; não publica nada.

Este ambiente de desenvolvimento não alcança a API do Open-Meteo; o código foi validado offline com previsões sintéticas derivadas das próprias observações (a tendência conhecida é recuperada fora da amostra). Os números reais aparecem após a primeira execução no GitHub Actions.

## 10. Como adicionar estações ou atualizar arquivos

Acrescentar uma entrada em `data/stations/stations.json` com `id`, `slug`, `name`, `institution`, `location_id` (`navirai` ou `diamantino`), coordenadas de fonte oficial (ou `null` com `forecast_point_fallback`), `timezone`, `utc_offset_hours`, `identity_status`, `evidence_url` e a lista `files` (`path`, `format` = `inmet_portal_hourly` ou `embrapa_guiaclima_daily`, `original_sha256`, `period`, `provided_by`). Arquivos novos do mesmo portal podem ser concatenados como entradas adicionais em `files`; datas duplicadas são rejeitadas na leitura. Períodos maiores melhoram a validação: a origem móvel ganha meses de teste e os mínimos de amostra passam a ser atingidos em D7 e na chuva.
