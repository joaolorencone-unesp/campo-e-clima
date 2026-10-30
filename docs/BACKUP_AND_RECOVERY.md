# Backup e restauração

Revisão de integração: [evidências reais e recuperação Git](RELEASES/V22_GITHUB_INTEGRATION.md). Os números e caminhos da entrega original abaixo são históricos; a revisão atual usa `runtime/integration_review` no repositório original, sem modificar o SQLite entregue no ZIP.

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

## Volumes mensais e recuperação de falhas

Os caminhos de destino devem ser novos. Para um checkout independente que esteja na branch `weather-archive`:

```powershell
.\.venv\Scripts\python.exe -m scripts.science.storage --archive runtime/archive-git --output runtime/storage.json
.\.venv\Scripts\python.exe -m scripts.archive_backup create --archive runtime/archive-git --backup runtime/backups/mensal-novo
.\.venv\Scripts\python.exe -m scripts.archive_backup verify --backup runtime/backups/mensal-novo
.\.venv\Scripts\python.exe -m scripts.archive_backup restore --backup runtime/backups/mensal-novo --output runtime/arquivo-restaurado-novo
.\.venv\Scripts\python.exe -m scripts.science_cli rebuild --archive runtime/arquivo-restaurado-novo --output runtime/banco-restaurado-novo.sqlite
```

Volumes contêm os objetos e manifests científicos; relatórios derivados são recalculados. O bundle Git preserva também commits e relatórios públicos. Copiar volumes, catálogo e hashes juntos para outro dispositivo e verificar essa cópia. Dois diretórios no mesmo computador não protegem contra perda do equipamento.

Após publicação aprovada, uma falha de envio pode ser recuperada via Actions → Recover scientific transport → informar o ID da execução de main. Somente artifacts de workflows conhecidos desse repositório são aceitos. Se expirados/ausentes, a recuperação informa isso e não altera o arquivo existente. Não reconstruir supostos RAW antigos a partir da previsão atual. Falhas de relatório não apagam os RAW ou substituem relatórios anteriores por vazios.
