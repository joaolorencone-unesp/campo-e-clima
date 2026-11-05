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
