# Proveniência e rastreabilidade

Cada manifesto preserva ID de execução, versão de software/pipeline/esquema, local, horário de coleta, commit quando informado pelo GitHub, URL sem credenciais, parâmetros, produto, status HTTP, metadados de cabeçalho permitidos e hashes do corpo original/gzip. As respostas RAW são imutáveis e os arquivos públicos não substituem os membros.

As primeiras coletas locais foram executadas antes do commit de entrega, portanto seu `git_commit` é NULL: não foi inventado um commit para código ainda em desenvolvimento. A origem v2.1 e o manifesto de arquivos da entrega identificam essa construção. Em Actions, `GITHUB_SHA` é registrado automaticamente. Novas capturas também incluem SHA-256 de cada módulo Python e hash conjunto do código; localmente registram o HEAD e se há alterações não commitadas. Reproduzir com a versão liberada e registrar novo dataset, sem reescrever os RAW anteriores.

Reconstrução valida SHA-256 antes de ingerir. Normalização registra valor original, unidade, conversão, intervalo, QC e hash. Avaliações recebem hash do conjunto de pares e versão de fórmulas. Experimentos registram particionamento, método, parâmetros e métricas inclusive sem melhoria. Não há promoção automática de previsões calibradas.

Horário do arquivo público ≠ inicialização do modelo. Inicialização ≠ disponibilidade pública após processamento. Campo desconhecido permanece NULL. Modelos da mesma instituição mantêm suas identidades; pesos iguais não eliminam dependência física.

O resumo público diário foi recalculado dos RAW após a correção de fechamento do dia. Os snapshots de desenvolvimento já arquivados permanecem intactos, incluindo seus resumos antigos. Para ciência, reprocessar os membros RAW com a fórmula versionada; não tratar um resumo antigo como dado independente.
