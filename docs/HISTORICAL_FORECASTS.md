# Previsões históricas

`python -m scripts.science_cli historical --location navirai --product previous_runs --model gfs_global --start 2026-10-24 --end 2026-10-26`

Previous Runs solicita D1/D2/D3/D7 por variável. São deslocamentos fixos por instante de validade, não uma única emissão diária. Inicialização não é reconstruída a partir desses deslocamentos.

Single Runs usa `--product single_run --run 2026-10-24T00:00:00Z`; a API real recusou start_date/end_date, portanto o adaptador os remove e solicita 16 dias. Ambos os pontos retornaram 384 horas no teste. A inicialização é conhecida; disponibilidade exata da rodada não foi comprovada, logo o pareador conservador não a usa para alegar verificação operacional.

Historical Forecast usa `--product historical_forecast`. É série contínua costurada de modelos operacionais, mantida como tal; não recebe D1/D7 inventado. ERA5 usa `--product reanalysis --model era5`; os valores ficam em tabela distinta e nunca são promovidos a observações.

Janela máxima por requisição: 31 dias. O job diário faz somente 7 dias recentes para duas localidades, com cache e tentativas limitadas. Retrocoletas extensas exigem execução em blocos, acompanhamento de cota e armazenamento. Não foi baixado todo o histórico desde 2024.

Integração real das três APIs em ambas as localidades: `RELEASES/v2.2-historical-integration.json`. Nenhum teste sintético foi publicado como previsão. Metadados de versão do NWP indisponíveis continuam desconhecidos.
