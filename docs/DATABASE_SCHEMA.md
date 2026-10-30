# Banco e migrações

SQLite local com WAL, foreign keys e transações. Migração imutável `scripts/science/migrations/001_initial.sql`, registrada por número e SHA-256. Alterar uma migração já aplicada faz a abertura falhar; futuras mudanças exigem outro arquivo numerado.

Entidades: locations, weather_sources, weather_models, model_versions, forecast_runs, forecast_values, ensemble_members, ensemble_forecasts, observing_stations, observations, reanalysis_values, data_quality_flags, forecast_verifications, calibration_datasets, calibration_models, calibration_predictions, model_evaluations, ai_explanations, system_versions e pipeline_executions; auxiliares raw_assets e schema_migrations.

Valores determinísticos e de ensemble têm chaves compostas com rodada, validade, variável, membro quando aplicável e convenção de antecedência. Uma ingestão repetida não duplica registros. Rodada aqui é o produto preservado; a inicialização pode permanecer desconhecida. `best_match_unspecified` não é um NWP individual identificado.

Observações são versionadas pelo hash de origem. Importações repetidas do mesmo valor são deduplicadas no pareamento; versões discordantes são excluídas até revisão. Identidades INMET:S735 e EMBRAPA:6 não são intercambiáveis. Nenhum registro provisório é promovido automaticamente.

O banco científico reconstruído entregue é `runtime/science_v22.sqlite`; `runtime/science.sqlite` é o banco de trabalho das coletas desta sessão. Somente os manifests selecionados para arquivo durável constituem a base reconstruível. `runtime/parquet` exporta tabelas com esquema Arrow estável e manifesto. Tabelas de calibração ficam vazias quando falta amostra: não é erro nem resultado zero.

A migração 002 compacta IDs repetidos de rodada em uma tabela de chaves inteiras e usa WITHOUT ROWID nas tabelas de valores. O hash canônico permanece em forecast_runs e no Parquet de chaves. Para limitar o banco analítico local, reconstruir com `--since AAAA-MM-DD` (data UTC de coleta); todos os RAW permanecem no arquivo durável.
