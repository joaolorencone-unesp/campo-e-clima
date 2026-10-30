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
