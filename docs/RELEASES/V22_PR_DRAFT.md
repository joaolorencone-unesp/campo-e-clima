# Rascunho local — ainda não publicado

**Título:** Adiciona arquivo científico reproduzível e verificação v2.2 com recuperação segura

**Base:** `main` · **Head:** `feature/v2.2-ciencia-e-rastreabilidade`

## Descrição

O painel passa a preservar respostas meteorológicas públicas e sua proveniência em `weather-archive`, permitindo reconstruir SQLite/Parquet e verificar previsões quando houver observações elegíveis. A aba Precisão separa Naviraí, Diamantino e coordenadas não cadastradas. Atualmente há zero observações instrumentais elegíveis, zero pares verificados e nenhum calibrador validado; a IA externa permanece desativada.

A coleta e o deploy do Pages ficam independentes do job científico. Os escritores usam fila compartilhada, transporte temporário seletivo, recuperação manual de artifacts e preservação de RAW/relatórios anteriores em falhas. O CI de PR roda offline com permissão de leitura. A exportação pública lê relatórios de um mesmo commit científico.

O arquivo tem compressão, deduplicação, alertas de capacidade em 50/70/85/95%, limites conservadores e backup mensal com verificação/restauração. Não apaga registros nem depende somente dos artifacts temporários.

Os 22 ZIPs legados presentes na main saem do snapshot de código; os arquivos locais e os commits anteriores foram preservados. `.env.example` continua como modelo sem credenciais, e SQLite/runtime/caches/RAW/bundles ficam fora da branch de código.

## Validação local

- 152 testes Python e 12 suítes JavaScript; sintaxe Python/JS e diff verificados.
- 11 abas em desktop/celular, mais troca global entre as duas cidades e ponto desconhecido, inclusive com API indisponível; sem erros JavaScript, erros locais de carregamento ou overflow nos cenários documentados.
- Oito manifests, hashes e reconstrução SQLite: 40 rodadas, 27.888 valores determinísticos/históricos, 487.968 valores de ensembles e 299 membros. Integridade/FKs aprovadas; reingestão sem mudança de hashes/contagens; backup mensal/restauração equivalentes.
- Actionlint 1.7.12 sem outros diagnósticos após exclusão somente da chave `queue: max`, suportada pelo GitHub atual e ainda não reconhecida pelo parser. ShellCheck/Pyflakes não executados.

Evidências completas em [V22_GITHUB_INTEGRATION.md](V22_GITHUB_INTEGRATION.md). CI Linux e workflows novos ainda dependem de execução remota; a revisão local não certifica disponibilidade contínua das APIs.

## Implantação, riscos e rollback

Publicar `weather-archive` antes da feature e confirmar seu SHA. Essa branch de dados não faz parte do merge. Depois da aprovação do PR e autorização de merge, verificar a execução manual e pelo menos uma execução programada, o Pages e a preservação dos manifests.

O limite de 750 MB de arquivos/1 GB de objetos Git exige planejamento de rotação em repositório gratuito antes de 85%; os volumes de backup não diminuem o histórico Git. Backup mensal em outro dispositivo, futura rotação e benchmark de grandes reconstruções dependem de operação explícita. Artifacts de recuperação expiram em sete dias. Main estava sem proteção obrigatória de checks na consulta.

Rollback por novo commit de reversão revisado em PR, preservando `weather-archive` e backups. Sem force-push, exclusão de dados ou reescrita de história.
