# Observações e QC

O catálogo INMET identificou S735 — NAVIRAI (FAZ. SANTA HELENA DO PINDO), operadora SEMADESC-MS, latitude -22.899909, longitude -53.869219, altitude cadastrada 303 m, a 37,6 km do ponto analisado. Isso é metadata pública do catálogo, não medição. O endpoint horário/diário foi consultado e não devolveu JSON observacional utilizável.

Embrapa/IFMS estação 6: a página oficial informa 23°01'33''S, 54°11'22''W, 381 m e série desde 01/12/2024. É uma referência distinta de S735. A exportação provisória já existente no repositório não identifica inequivocamente sua origem e continua fora de calibração.

Importação: `python -m scripts.science_cli import-observations --location navirai --file caminho.csv --station metadados.json --format inmet`. O CSV oficial INMET precisa conter cabeçalho Data/Hora UTC e código correspondente. O formato canônico exige valid_at_utc, variable, unit, value; chuva exige interval_start_utc e interval_end_utc. Sentinelas, datas inválidas, duplicação de horas, unidade desconhecida e intervalo não identificado são recusados/excluídos.

Metadados obrigatórios: id (INMET:... ou EMBRAPA:...), institution, name, latitude, longitude, timezone, identity_status, evidence_url; altitude e descrição de sensores quando comprovadas. `verified_by_official_metadata` é uma declaração documental do importador, não uma certificação produzida pelo programa. Guardar a evidência. Não marcar dados estimados como estação.

O pareamento exige controle básico, identidade verificada/catalogada, unidade/intervalo exatos, estação até 50 km do ponto e grade até 75 km da estação. São limites experimentais de triagem espacial, não garantia de representatividade. Altitude, exposição, altura de sensores, calibração instrumental e mudanças na estação ainda exigem auditoria especializada. Observações provisórias e referências de grade não geram selo validado.

O comando `python -m scripts.science_cli observations --location diamantino` consulta catálogo e estação operante até 50 km para esse ponto, sem aproveitar S735. Integração real testada em ambas as localidades; nenhuma respondeu com JSON observacional utilizável. Relatório: RELEASES/v2.2-observations-integration.json. O workflow científico tenta esse conector diariamente.
