# Changelog

## 2.2.0 — candidato local, 29/10/2026

- Auditoria da v2.1 no commit e1241e2; branch de desenvolvimento sem upstream para main.
- Captura dos membros e respostas oficiais, gzip/SHA-256, manifests incrementais e escritor limitado a weather-archive.
- SQLite com migração, QC, intervalos e localidades; reconstrução, backup e exportação Parquet.
- Adaptadores Previous Runs D1/D2/D3/D7, Single Runs e Historical Forecast testados nas duas localidades.
- Importação de arquivos INMET/canônicos com identidade, unidade e intervalos; série Embrapa provisória continua excluída.
- Pareamento e métricas MAE/RMSE/viés circular/Brier/BSS/CRPS/reliability/eventos, sem ranking de precisão não validada.
- Nova aba Precisão dos modelos, filtros e comparação experimental quando houver dados elegíveis.
- Correção do dia de chuva (01h a 00h seguinte) e do contador de restrições por operação da Central Agro.
- Infraestrutura de calibração em modo experimental e IA none/Ollama opcional; provedores externos bloqueados.
- Workflows de coleta/arquivo/verificação diária e tentativa de treino semanal preparados. Ativação no GitHub pendente de aprovação para main.

Nenhuma observação, métrica ou melhoria local foi inventada. Consulte RELEASES/v2.2-status.md para limites e evidências.
