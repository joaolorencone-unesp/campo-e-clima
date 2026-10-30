# Arquivamento permanente

Decisão e estimativa prévia em `DECISIONS/001-archive-storage.md`. Branch dedicada `weather-archive`, conteúdo de objetos gzip por SHA-256 e manifests por local e janela UTC de 6 h. Importações históricas usam identidade derivada de produto, consulta e hash; repetições do mesmo conteúdo não criam outro arquivo.

O job de coleta continua a cada ~30 minutos. Ensembles têm cache de 6 h, determinístico ~27 minutos, e cabeçalhos/horários de cache são explícitos. O arquivamento usa os corpos dessa coleta, sem nova requisição meteorológica. GitHub artifact de 1 dia serve exclusivamente ao transporte entre jobs; a branch é o arquivo permanente.

Na amostra real: Naviraí 406.910 bytes e Diamantino 212.529 bytes por lote, incluindo snapshot público e metadados oficiais. Projeção linear conservadora sem deduplicação: **74,3 MB/30 dias e 904,4 MB/ano**, mais manifests, históricos e armazenamento Git. É uma medição pequena, não limite garantido. A trava de 750 MB de arquivos pode exigir migração em cerca de dez meses nesse ritmo; Git pode atingir limites antes. Monitorar tamanho real e rever a estratégia antes disso.

Escrita incremental, sem force-push, com concorrência única `weather-archive-writer`. Uma rejeição de push falha visivelmente. Até duas respostas do mesmo cache podem aparecer em execuções diferentes, mas objetos idênticos são guardados uma vez. Falhas não transformam dados ausentes em séries vazias válidas.

`python -m scripts.archive_git --captures runtime/captures` cria/atualiza somente checkout local da branch. `--push` é explícito e usado pelo workflow preparado. Nenhum script escreve em main. Nesta entrega, novos workflows ainda não foram executados no GitHub porque main permanece sem alterações.

Não prometer pontualidade exata do cron nem armazenamento gratuito ilimitado. A máquina do usuário poderá ficar desligada após a ativação dos workflows no GitHub; as tarefas Windows antigas continuam com suas próprias condições.
