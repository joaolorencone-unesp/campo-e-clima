# Dicionário de dados

Internamente, timestamps ISO 8601 UTC com offset explícito. Exibição usa IANA `America/Campo_Grande` e `America/Cuiaba`. Horários sem fuso em um arquivo observacional canônico são recusados. Unix time recebido da API é UTC.

| Campo | Significado |
|---|---|
| location_id | Identidade do ponto solicitado; não o nome arbitrário de uma fazenda |
| grid_latitude / grid_longitude | Coordenadas efetivamente retornadas; não substituem as solicitadas |
| initialization_utc | Inicialização informada pelo produto Single Runs; NULL nos demais quando desconhecida |
| collected_at_utc | Aquisição efetiva da resposta; cache mantém a data original |
| available_at_utc | Disponibilidade comprovada nesta coleta operacional; histórica pode ser NULL |
| valid_at_utc | Instante de validade do campo |
| interval_start/end_utc | Intervalo do acumulado; chuva horária termina no timestamp do provedor |
| lead_hours / lead_basis | Antecedência à inicialização, deslocamento fixo ou desconhecida; comparação por coleta é rotulada separadamente |
| original_value / value | Valor de origem e convertido; valores inválidos não viram zero |
| qc / missing | Motivo da exclusão e ausência no valor utilizável |
| member_id | Sufixo original do membro, vinculado ao modelo |
| raw_sha256 | Hash do corpo de origem; manifesto também guarda hash gzip |
| model_version_id / spatial_resolution_km | NULL se não informados; não deduzidos do nome comercial |

Variáveis canônicas: temperatura/dew point `degC`; UR/nuvens `%`; precipitação `mm`; vento/rajada `km/h`; direção `degree`; VPD `kPa`; pressão `hPa`. Conversão documentada de m/s para km/h: ×3,6. Unidade desconhecida impede uso numérico. Precipitação negativa, NaN, infinito e sentinela -9999 são inválidos ou ausentes; original fica no RAW.

O primeiro acumulado de chuva não tem início comprovado na própria série e é excluído da tabela utilizável. Intervalos maiores que uma hora não são reinterpretados como acumulados horários. A grade horária pode ser interpolada pela API: não há promessa de resolução nativa. O dia local usa os finais 01h…00h seguinte; sem a última hora, o dia é incompleto.


## Campos públicos acrescentados na versão 3 (`schema_version` 5)

| Campo | Significado |
|---|---|
| `ensemble_models.<nome>.precipitation_native_step_hours` | Passo nativo de precipitação detectado (1, 3, 6) ou `null` sem chuva suficiente para decidir |
| `ensemble_models.<nome>.model_run` | Metadados da última rodada do provedor (`last_run_initialisation_utc`, `last_run_availability_utc`, estado); nunca inferidos da hora da consulta |
| `rain_ensemble_hourly[].windows.<d>.models_excluded_by_resolution` | Modelos deixados de fora da janela por passo nativo maior que a janela |
| `rain_ensemble_accumulated[]` | Totais de 3/5/7 dias por trajetória de membro, com P10/P50/P90 e frequências >10/25/50/100 mm |
| `rain_dry_spell` | Maior sequência de dias <1 mm por trajetória nos 7 dias (mediana, P90, frequência ≥3 e ≥5 dias) |
| `rain_model_agreement_daily[]` | Por dia: modelos com maioria de membros >1 mm, fração de concordância, dispersão das médias por modelo |
| `agro_ensemble_hourly[]`, `agro_ensemble_coverage` | T, UR, VPD (mesmo membro), vento e rajadas por hora com peso igual por modelo; modelos válidos por variável |
| `deterministic_extended` | Radiação, ET₀ FAO-56, CAPE, CIN, lifted index, bulbo úmido, solo, nuvens por nível (estado explícito) |
| `previous_run_comparison` | Diferença por dia frente à publicação anterior e modelos com aquisição nova/reutilizada |
| `freshness` | Idades de aquisição, rodada e publicação por produto; `models_with_newer_run_pending` |
| `site.utc_offset_seconds` | Offset do fuso configurado no instante da coleta |

## Campos públicos acrescentados na versão 4

### `deterministic_models` (em `latest.json`)

| Campo | Significado |
|---|---|
| `state` | `ok` quando ao menos um modelo respondeu; `unavailable` com `error` caso contrário |
| `requested` | Identificadores Open-Meteo pedidos (padrão `DETERMINISTIC_MODELS` do coletor ou variável de ambiente) |
| `models.<id>.state`, `label`, `error` | `ok` ou `unavailable` por modelo; o motivo (por exemplo `HTTP 400`) fica em `error` |
| `models.<id>.daily` | `time`, `temperature_2m_max`, `temperature_2m_min`, `precipitation_sum`, `wind_gusts_10m_max`, `weather_code` (7 dias) |
| `models.<id>.hourly` | `time`, `precipitation`, `temperature_2m` limitados às primeiras 72 h |
| `spread_daily[]` | Por dia: `models`, `rain_min_mm`, `rain_median_mm`, `rain_max_mm`, `models_wet_1mm`, `models_wet_10mm`, `tmax_min`, `tmax_max`, `tmin_min`, `tmin_max` — dispersão entre modelos, não probabilidade calibrada |
| `models_ok`, `fallback`, `collected_at_utc` | Modelos válidos; aviso quando o pedido combinado foi rejeitado e os modelos foram consultados um a um; hora da coleta |

### `site/data/bulletin_<localidade>.json`

| Campo | Significado |
|---|---|
| `generated_utc`, `location_id`, `issued_at_utc` | Geração do boletim, localidade e emissão da previsão usada |
| `prompt_version`, `facts[]`, `facts_sha256` | Versão da ficha de fatos, frases factuais derivadas do JSON publicado e seu hash |
| `rule_based_text`, `text` | Texto por regras (sempre presente) e texto publicado (igual ao de regras quando não há IA válida) |
| `status` | `rules` (sem IA), `llm` (reescrita aceita) ou `rules_fallback` (IA indisponível ou rejeitada) |
| `provider`, `model`, `validation`, `error`, `usage` | Provedor e modelo usados, resultado da validação numérica, motivo da rejeição, uso de tokens quando informado |
| `disclaimer` | Aviso de que o texto é automático e os números devem ser conferidos no painel |

### `site/data/stations/index.json`

| Campo | Significado |
|---|---|
| `generated_at_utc`, `archive_commit` | Geração dos relatórios e commit da branch de arquivo de onde foram copiados |
| `stations[].id`, `slug`, `name`, `location_id`, `file` | Identidade da estação e nome do relatório individual |
| `stations[].period`, `daily_rows`, `models`, `forecast_point`, `state` | Período observado, dias agregados, estado por modelo, ponto consultado (`station_coordinates` ou `municipal_reference_point`), `ok` ou `observations_only` |
| `stations[].headline` | Por `t_max`, `t_min`, `rain_mm`: melhor modelo em D1 (`model`, `mae_raw`, `bias_raw`, `n`, `recommended`) |
| `stations[].recommendations`, `groups_evaluated` | Número de correções validadas e de grupos avaliados |
| `stations[].recent[]` | Últimos 7 dias com `date`, `t_max`, `t_min`, `rain_mm` (chuva `null` em dia incompleto) |
| `stations[].yesterday_check` | Último dia com observação e previsão D1 do modelo de referência: `date`, `model`, `obs_rain_mm`, `fc_rain_mm`, `obs_t_max`, `fc_t_max` |

### `site/data/stations/<slug>.json`

| Campo | Significado |
|---|---|
| `schema_version` (1), `generated_at_utc`, `dataset_sha256` | Versão do esquema, geração e hash do conjunto avaliado |
| `station` | Registro de `data/stations/stations.json` sem a lista de arquivos (`id`, `name`, `institution`, coordenadas, `timezone`, `utc_offset_hours`, `identity_status`, `coordinates_source`, `evidence_url`) |
| `forecast_point` | `latitude`, `longitude`, `source` (`station_coordinates` ou `municipal_reference_point`); `station_to_forecast_point_km` quando as duas coordenadas existem |
| `leads_days` | Antecedências nominais avaliadas (1, 2, 3, 7) |
| `observations` | `period`, `hourly_rows`, `daily_rows`, `qc` (contagens por variável e marca), `sources` (arquivo, formato, SHA-256 do original), `daily[]` (`date`, `t_max`, `t_min`, `t_mean`, `rain_mm`, `rh_min`, `rh_max`, `gust_max_kmh`, `wind_mean_kmh`, `radiation_mj`, `et0_mm`) |
| `models.<id>` | `state` (`ok`, `partial`, `unavailable`), `blocks`, `errors[]`, `variables`, `grid` (coordenadas/elevação devolvidas), `members` (só na média multimodelo) |
| `verification[]` | Por `model`, `lead_days`, `variable`, `kind` (`hourly`/`daily`): `status` (`evaluated`, `insufficient_pairs`, `insufficient_test_sample`), `n_pairs`, `n_test`, `raw_all_pairs` e `raw_test` (`n`, `mae`, `rmse`, `bias`), `folds[]` (mês testado, tamanhos, data de corte), `methods[]` (`name`, `n`, `mae`, `rmse`, `bias`, `skill_mae`, `delta_mae_ci95`, `significant_improvement`, `contingency` para chuva), `recommended` (`method`, `parameters`, `fitted_on`, `evidence`, `status`) ou `null` com `reason`, `raw_contingency` (chuva, limiares 1 e 10 mm), `diagnostics` (`bias_by_local_hour`, `bias_by_month`, só em D1 horário) |
| `series.<model>` | `lead_days` (1), `dates`, `obs_t_max`, `fc_t_max`, `obs_t_min`, `fc_t_min`, `obs_rain_mm`, `fc_rain_mm` |
| `headline`, `recommendations`, `groups_evaluated`, `limitations[]` | Resumo por variável, contagens e limitações textuais publicadas com o relatório |

Viés é sempre modelo − estação. Parâmetros de correção: `bias`; `ratio`; `slope`/`intercept`; `global_bias` + `by_hour` (0–23); `threshold`, `qx`, `qy` (mapeamento de quantis, com `fallback_ratio` quando a amostra úmida é pequena). Nenhum campo substitui a previsão principal.
