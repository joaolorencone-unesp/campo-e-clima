# Publicação e GitHub Actions — v2.2

**Revisão vigente: 29/10/2026.** Seguir [V22_GITHUB_INTEGRATION.md](docs/RELEASES/V22_GITHUB_INTEGRATION.md). No repositório original, código e dados já são branches locais recuperadas dos bundles. Primeiro publicar `weather-archive`, conferir o SHA remoto, depois publicar a feature e abrir PR; cada etapa remota exige a autorização prevista no pedido. Merge exige aprovação separada. Não copiar o ZIP para o checkout.

Branch local pronta para revisão: feature/v2.2-ciencia-e-rastreabilidade. Não fazer push em main sem aprovação, conforme o item 19 e a seção de entrega do pedido. Nenhuma mudança de plano/faturamento é necessária nem feita pelos scripts.

Após aprovação da revisão: enviar a branch de desenvolvimento pelo fluxo Git habitual, abrir PR, revisar o diff/testes e integrar somente com consentimento para main. Os workflows preservam a publicação Pages existente. Não executar arquivos do ZIP por cima de um checkout com alterações não salvas.

## Rotinas preparadas

- pages.yml: coleta às 7/37 de cada hora UTC. Forecast por duas localidades; cache 6 h dos ensembles. Publica Pages independentemente do job secundário de arquivo.
- Job archive: uma escrita por local/janela UTC de 6 h, sem novas consultas; token limitado a contents:write/actions:read neste job. Branch fixa weather-archive, sem force-push.
- science.yml: 13:23 UTC, recuperação de sete dias Previous Runs e tentativa de observações INMET nas duas localidades, reconstrução e métricas. Segundas-feiras tenta calibração somente se houver amostra; na primeira inicialização também gera o diagnóstico de calibração ausente. Explicação por regras acompanha o relatório.
- Relatórios científicos arquivados são incorporados à próxima publicação do Pages; não há obrigação de sincronia instantânea entre jobs.

O GITHUB_TOKEN é nativo do runner e não é incorporado aos arquivos. GH_TOKEN é passado apenas ao processo Git. Nenhuma API de IA é habilitada. Caches/artifacts são otimizações/transporte, nunca o único arquivo permanente. Exclusão de credenciais e campos privados é responsabilidade também da revisão de dados importados.

Depois de integrar: executar workflow_dispatch uma vez, verificar Pages, branch weather-archive, hashes, relatório de integridade e contagens. Verificar uma execução programada posterior. Confirmar fonte/atualização e custo da conta pelas interfaces oficiais. O teste local não equivale a um workflow executado no GitHub.

Recuperação: reverter o commit da v2.2 por revisão Git, manter weather-archive intacta, não apagar banco/RAW. Os workflows anteriores e a aplicação local v0.3 foram preservados no histórico/checkouts de origem. Não é necessário mudar as tarefas Windows existentes.

## Branch de dados entregue localmente

A pasta `weather-archive` contém um repositório Git separado na branch homônima, com os oito manifests reais e os relatórios públicos. Nenhuma branch foi enviada ao GitHub nesta entrega. Antes da ativação dos workflows, revisar e publicar essa branch de dados, preservando seus hashes; publicar a branch de desenvolvimento para revisão e só integrar na main após aprovação explícita. Os bundles Git da entrega permitem restaurar ambas as branches sem depender do servidor.

O parágrafo anterior descreve a entrega original em `PAINEL_CLIMA/campo-e-clima-v2.2`. Na revisão no repositório original, `weather-archive` é uma branch independente dentro do mesmo Git; não é um diretório para copiar nem uma branch para mesclar.

`ci.yml` testa PRs offline em Python 3.11/3.13 e Node 22, com token somente leitura e sem segredos. `archive-recovery.yml` permite recuperar o transporte temporário de uma execução autorizada de main pelo ID, antes dos sete dias de retenção. Artifact ausente não modifica o arquivo. Escritores compartilham fila `weather-archive-writer`; `queue: max` evita o cancelamento rotineiro de capturas pendentes, mas a fila do GitHub continua finita.
