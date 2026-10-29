# Backup e restauração

Executar no diretório do projeto, em PowerShell:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.science_cli backup --db runtime/science_v22.sqlite --output runtime/backups/novo.sqlite
.\.venv\Scripts\python.exe -X utf8 -m scripts.science_cli rebuild --archive weather-archive --output runtime/restaurado.sqlite
.\.venv\Scripts\python.exe -X utf8 -m scripts.science_cli parquet --db runtime/restaurado.sqlite --output runtime/restaurado-parquet
```

Backup SQLite usa a API de backup consistente, não copia um WAL ativo cegamente. Destinos existentes são recusados. Reconstrução verifica hashes gzip, original e manifesto, bloqueia traversal e escreve em .building; o destino final só aparece após integridade e foreign_key_check. Interrupções deixam .building para diagnóstico, sem sobrescrever banco anterior.

Guardar uma cópia local da branch de arquivo, além do Git remoto. A entrega contém arquivos reais em weather-archive e backup local em runtime/backups. `.venv`, caches, bancos e RAW não entram na branch de código/main. Os RAW públicos entram somente na branch dedicada; nenhuma informação privada de fazenda deve ser importada para esse arquivo público.

Reconstrução real desta entrega: oito manifests, 40 produtos de previsão, 487.968 valores de membros, 27.888 valores determinísticos/históricos, hashes e SQLite integrity_check aprovados. As observações permanecem vazias porque a fonte não foi confirmada. Banco de trabalho pode conter coletas extras não selecionadas para as quatro janelas diárias; a base científica reconstruída é a referência arquivada.

Banco canônico entregue: `runtime/science_v22.sqlite` (84,418,560 bytes), esquema 2. Backup consistente: `runtime/backups/science_v22_verified.sqlite`. A migração de esquema 1 para 2 preservou todas as contagens de dados, conforme `RELEASES/v2.2-migration-and-rebuild.json`. O banco SQLite ocupa muito mais espaço que os RAW comprimidos; para consultas longas, usar Parquet e reconstruções por `--since`, sem apagar o arquivo original.
