# Campo e Clima v2.2 — revisão final e integração segura

Data: **29/10/2026**. Versão: **2.2.0, candidato local revisado**. Software/pipeline/esquema científico preservados; não se trata de uma publicação remota. Este documento complementa e atualiza a entrega anterior. Os relatórios `v2.2-final-validation.json` e `v2.2-status.md` registram aquela entrega; os relatórios `v22-integration-*` registram esta revisão.

## 1. Repositório e recuperação

Repositório original associado ao GitHub Desktop: `C:\Users\Usuario\OneDrive - Unesp\Documentos\___drone\campo-e-clima`. Remote: `https://github.com/joaolorencone-unesp/campo-e-clima.git`.

Antes das alterações, o checkout estava limpo em `main`, commit `e1241e208033baf3260d86c8ba4b03e56ba92300`. Existia somente `origin/main` no remoto consultado. Depois de `git fetch origin`, o SHA continuou igual. Os bundles foram localizados na entrega, verificados e importados por refspec explícito. Nenhum arquivo de código do ZIP foi aplicado sobre o original. Apenas o SQLite e snapshots públicos foram extraídos para caminhos ignorados de auditoria/preview.

| Referência | Commit identificado | Estado nesta revisão |
|---|---|---|
| `main` e `origin/main` | `e1241e208033baf3260d86c8ba4b03e56ba92300` | Preservadas |
| Feature importada | `7da5e68e869dbc4c38d70bee298234ec98b7ef7b` | Ancestral do commit de revisão local |
| `feature/v2.2-ciencia-e-rastreabilidade` | Commit que contém este documento; SHA integral no manifesto do novo backup | Ativa, sem upstream e sem publicação |
| `weather-archive` | `4bb516702e78cdf699ae00577d3a12d1417e74a6` | Importada e preservada, ainda ausente no remoto consultado |

A main original é ancestral da feature. Não havia atualização posterior de `origin/main` a conciliar. A branch científica tem história e finalidade independentes; não deve ser mesclada à feature ou à main. A troca para a feature foi confirmada na interface do GitHub Desktop. A revisão termina com commit local e árvore limpa, conferidos novamente após o commit.

## 2. Integridade da entrega recebida

Pasta preservada: `C:\Users\Usuario\OneDrive - Unesp\Documentos\___drone\PAINEL_CLIMA\ENTREGA_CAMPO_CLIMA_V22_2026-10-29`.

| Arquivo | SHA-256 conferido |
|---|---|
| `codigo-v22.bundle` | `9ca41f86b22401c15d878b7d50fd910161f8f0391ff2f7605fc82cca5994d0b3` |
| `weather-archive.bundle` | `b986631987dfcf24304b8342a51875563c8023e87cbe447c9b9faa0d729b2c63` |
| `CAMPO_E_CLIMA_v2.2_2026-10-29.zip` | `725f3450bd0d3f41009b49bd14acfb7c2f17efa0b9ea1211e066f66826b16b4a` |
| `MANIFESTO_ARQUIVOS.json` | `fa61b049aa95e7acc080c8626c61e3d808f4093f02bc3374e54928111f4dd231` |

Foram lidos `ENTREGA.json`, `LEIA-ME.md`, `SHA256SUMS.txt` e o manifesto. Passaram a verificação dos dois bundles, os quatro hashes externos, o CRC do ZIP e os **345 hashes internos**. Os refs dos bundles corresponderam aos SHAs solicitados. O novo backup de revisão fica em pasta separada `PAINEL_CLIMA\REVISAO_V22_GITHUB_2026-10-29`; seu manifesto contém os SHAs finais, os hashes dos novos bundles e o resultado da verificação. O pacote original permanece intacto.

## 3. Correções realizadas

| Área | Resultado |
|---|---|
| Actions | CI de PR offline; token por job; fila compartilhada; artifact seletivo; recuperação manual por ID de execução; arquivo ausente não modifica dados; deploy depende somente do build operacional |
| Persistência | RAW pode ser arquivado mesmo se os relatórios derivados falharem; relatórios anteriores são preservados; repetir uma captura já arquivada não cria commit redundante |
| Exportação pública | Leitura de todos os relatórios a partir do mesmo SHA da branch científica; validação de coordenadas e estado de IA; falha preserva arquivos anteriores |
| Armazenamento | Alertas progressivos, orçamento de arquivos e de histórico Git completo, volumes mensais com catálogo verificável, restauração sem sobrescrever destinos |
| Localidades | Correção da troca global que destruía a tabela da aba Precisão; exclusões por localidade; coordenadas desconhecidas limpam cidade/resultados anteriores |
| Proveniência | Timestamp da coleta determinística não é substituído por consulta a outra fonte; ordenação estável do pareamento/hash do dataset; intervalo de purga registrado conforme o maior horizonte |
| Entrega | Documentação, rascunho de PR, logs, ambiente congelado, evidência visual, comparação integral e reingestão do SQLite |

Principais arquivos: `.github/workflows/{pages,science,ci,archive-recovery}.yml`, `scripts/archive_git.py`, `archive_transport.py`, `archive_backup.py`, `export_science_public.py`, `science_cli.py`, `scripts/science/{archive,storage,evaluation,calibration}.py`, `site/static/{location,precision_v22}.js`, `site/index.html`, testes e documentação. A lista exata está no Git e no manifesto de revisão. `.gitignore` também exclui ZIPs e bundles. Runtime, caches, `.env`, `.venv`, bancos SQLite e RAW não entram na branch de código. O `.env.example` contém apenas configurações-modelo, sem credenciais.

A conferência encontrou **22 ZIPs legados já versionados na main original**. Foram retirados somente do índice da feature com `git rm --cached`; todos continuam no computador, na main e nos commits antigos. O snapshot revisado não contém pacotes ZIP. O histórico não foi reescrito, portanto esses objetos antigos continuam alcançáveis nos bundles Git e não há promessa de redução do tamanho de todo o repositório.

## 4. Banco, arquivo e estado científico

O SQLite entregue foi comparado a uma reconstrução nova feita **exclusivamente dos oito manifests verificados** da branch científica. Foram comparados número de linhas e SHA-256 das linhas ordenadas de todas as tabelas, além de `integrity_check` e `foreign_key_check`.

| Conteúdo | Entregue | Reconstruído |
|---|---:|---:|
| Rodadas | 40 | 40 |
| Valores determinísticos/históricos | 27.888 | 27.888 |
| Valores de ensembles | 487.968 | 487.968 |
| Membros cadastrados | 299 | 299 |
| Ativos RAW registrados | 46 | 46 |
| Observações instrumentais elegíveis | 0 | 0 |
| Pares verificados | 0 | 0 |

Todos os registros científicos coincidem. Duas diferenças explicadas: `ai_explanations` tem uma explicação por regras criada após a ingestão no banco entregue, contra zero antes da regeneração; `schema_migrations` tem os mesmos SQL/hashes, mas datas reais de aplicação diferentes. Não são perda de previsão ou mudança de observação. A explicação derivada foi regenerada com provedor `none`.

Também passaram: backup SQLite consistente, backup mensal de **62 arquivos**, restauração em novo diretório e reconstrução do banco restaurado com igualdade das tabelas científicas. SHA-256 do backup SQLite desta revisão: `126f0eb110da17e40bb64922a97a208826502b307b67e07269a7c21aef185fdf`. A reingestão integral dos mesmos oito manifests numa cópia separada preservou todas as contagens e hashes; não foram encontradas linhas exatamente duplicadas. Evidências: [banco](v22-integration-database.json) e [idempotência](v22-integration-idempotency.json).

Naviraí: **−23.065, −54.190**. Diamantino: **−14.408, −56.446**. As duas localidades têm filtros, amostras e exclusões separados. Para outras coordenadas: **“Não há histórico científico validado para esta localidade.”** Nenhum resultado conhecido é reaproveitado como se pertencesse ao ponto desconhecido.

Não há calibrador meteorológico validado nem ganho de precisão demonstrado. IA externa permanece desativada. O catálogo oficial INMET retornou 669 estações durante a revisão: são metadados, não medições elegíveis. As séries provisórias e produtos modelados não foram promovidos a observação instrumental.

## 5. Testes e limites da evidência

Ambiente `.venv` novo no repositório original, Python 3.13.4, dependências de `requirements-science.txt`, PyArrow 26.0.0. O congelamento completo desta revisão está em [requirements-lock-integration-v22.txt](requirements-lock-integration-v22.txt).

- **152 testes Python** aprovados, com bloqueio de HTTP externo em `requests` nos testes offline. Logs e versões: [validação](v22-integration-validation.json), [pytest](v22-integration-pytest.txt).
- **12 suítes JavaScript** aprovadas, além de sintaxe de todos os JS estáticos e parsing dos Python. [Log Node](v22-integration-node.txt).
- **11 abas** em desktop e celular, sem erros JavaScript ou transbordamento horizontal. [Relatório visual](v2.2-browser.json).
- Regressão adicional do seletor global Naviraí/Diamantino/coordenada desconhecida em desktop/celular, com falha explícita de API de previsão: sem erros locais de carregamento, sem mistura de cidades, retorno correto ao local conhecido. Foram usados snapshots públicos reais; a simulação de erro HTTP 503 não contém meteorologia fictícia. [Relatório](v22-integration-browser.json), imagens em `integration-screenshots/`.
- `git diff --check`, integridade Git/bundles, varredura de caminhos proibidos e padrões de credenciais. A varredura não é garantia absoluta de detecção de todo segredo.
- `actionlint 1.7.12` não reconhece a chave nova `queue: max`; somente esse diagnóstico foi excluído e os quatro workflows passaram nas demais verificações. ShellCheck/Pyflakes não estavam instalados. A opção está documentada pelo [GitHub](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency?apiVersion=2022-11-28) e no [changelog de 07/05/2026](https://github.blog/changelog/2026-05-07-github-actions-concurrency-groups-now-allow-larger-queues/). A fila tem limite; não equivale a garantia de execução de toda coleta.

O CI Linux/Python 3.11 e 3.13 está preparado, mas ainda não foi executado no GitHub com estas mudanças. Testes locais não confirmam disponibilidade futura das APIs, execução programada ou publicação do candidato. Preview local desta revisão: `http://127.0.0.1:8777/`; previews e tarefas Windows anteriores foram preservados.

## 6. GitHub Actions e configurações consultadas

Consulta em 29/10/2026: repositório público, main como padrão, Actions permitidas, token padrão somente leitura, PR por Actions desabilitado, retenção padrão de 90 dias. Os novos artifacts de transporte definem **sete dias** explicitamente. Pages usa **GitHub Actions**, HTTPS obrigatório. Nenhuma configuração foi alterada. Não há rulesets ou proteção de main na consulta: os checks de PR estão preparados, mas não são obrigatórios pelo servidor; revisão/aprovação continuam sendo controles operacionais.

Última execução existente consultada: [40841772568](https://github.com/joaolorencone-unesp/campo-e-clima/actions/runs/40841772568), concluída com sucesso na main original, SHA `e1241e2`. Isso não valida os workflows novos.

`pages.yml`: build lê código/coleta e publica site; deploy tem `pages:write/id-token:write`; archive tem `contents:write/actions:read`, depende da existência efetiva do artifact e é independente do deploy. Falhas de transporte científico são avisadas sem bloquear o Pages. Falhas da coleta operacional ainda podem impedir uma nova edição; a edição já publicada permanece no Pages.

`science.yml`: importação diária e arquivo em fila compartilhada `weather-archive-writer`, com backup temporário da captura antes da tentativa de push. Treino é experimental nas segundas-feiras, ou diagnóstico inicial se ainda não houver relatório de calibração. `archive-recovery.yml` valida repositório, branch main, workflow de origem e artifact não expirado. Artifact ausente/expirado gera aviso sem alteração de dados.

`ci.yml`: PR para main e push de feature, token somente leitura, checkout sem credenciais persistidas, sem segredos, regressão Python/JS offline. Não envia código ou dados.

## 7. Capacidade, backup e continuidade

Arquivo: 750 MB; lote: 25 MB; objetos Git: orçamento de 1 GB. Alertas em 50/70/85/95%, com bloqueio ao atingir o limite. Arquivo inexistente gera erro, nunca estado “saudável”. Os avisos aparecem no Actions e no JSON público `archive_status`; não foi criada notificação externa. A estimativa anterior de 0,90 GB/ano é indicativa; a nova projeção usa taxa observada somente após pelo menos quatro manifests cobrindo um dia.

Gzip e deduplicação já reduzem RAW. Volumes mensais verificáveis preservam os dados fora de artifacts; não reduzem o histórico Git. Antes de 85%, manter duas cópias verificadas e preparar, com aprovação, particionamento em novo repositório público gratuito e catálogo entre períodos. O escritor tem remoto fixo, portanto essa migração precisa de alteração/validação explícita. Nenhum registro é apagado ou reescrito automaticamente. Não foi habilitado serviço pago.

O backup novo fica no mesmo computador; copiar para outro dispositivo ainda é uma ação operacional pendente. A retenção de sete dias limita o prazo de recuperação de uma captura que não chegou ao arquivo. Grandes históricos precisam de benchmark de reconstrução/memória/tempo antes de se aproximarem do limite. Ver [política](../DECISIONS/001-archive-storage.md) e [restauração](../BACKUP_AND_RECOVERY.md).

## 8. Comandos de recuperação e reprodução

Comandos usados na recuperação, a partir do repositório original; executar novamente somente após comparar refs existentes, sem forçar substituição:

```powershell
$entrega = 'C:\Users\Usuario\OneDrive - Unesp\Documentos\___drone\PAINEL_CLIMA\ENTREGA_CAMPO_CLIMA_V22_2026-10-29'
git status --short
git remote -v
git branch -avv
git fetch origin
git bundle list-heads "$entrega\codigo-v22.bundle"
git bundle verify "$entrega\codigo-v22.bundle"
git bundle verify "$entrega\weather-archive.bundle"
git fetch "$entrega\codigo-v22.bundle" 'refs/heads/feature/v2.2-ciencia-e-rastreabilidade:refs/heads/feature/v2.2-ciencia-e-rastreabilidade'
git fetch "$entrega\weather-archive.bundle" 'refs/heads/weather-archive:refs/heads/weather-archive'
git merge-base --is-ancestor e1241e208033baf3260d86c8ba4b03e56ba92300 feature/v2.2-ciencia-e-rastreabilidade
git switch feature/v2.2-ciencia-e-rastreabilidade
git diff --stat main...HEAD
```

Reprodução dos testes, sem executar coleta externa:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-science.txt
$env:CAMPO_OFFLINE_TESTS = '1'
$env:AI_PROVIDER = 'none'
$env:AI_ENABLE = '0'
$env:AI_ALLOW_PAID = '0'
.\.venv\Scripts\python.exe -X utf8 -m pytest -q --basetemp .test_runs/revisao_nova
node tests/frontend_smoke.cjs
Get-ChildItem tests/test_*.cjs | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { throw 'Falha JavaScript' } }
git diff --check
```

Os testes de navegador requerem Playwright, Edge, servidor local e os snapshots reais ignorados pelo Git. Com preview pronto: definir `CAMPO_PREVIEW_URL=http://127.0.0.1:8777` e executar `node tests/browser_v22.cjs` e `node tests/browser_v22_integration.cjs`. A ausência dos snapshots não deve ser suprida por dados fictícios no painel.

Para restauração independente a partir do novo backup, usar um diretório **novo**: `git clone -b feature/v2.2-ciencia-e-rastreabilidade <codigo-v22-revisado.bundle> <pasta-nova>`, verificar o SHA do manifesto e importar `weather-archive` do bundle de dados com refspec explícito. `git bundle verify` e SHA-256 devem passar antes de usar o backup. Não substituir o checkout existente. Restaurar os volumes mensais e reconstruir SQLite conforme `BACKUP_AND_RECOVERY.md`; destinos existentes são recusados.

## 9. Publicação pendente de autorização

**Nada foi enviado, nenhum PR foi aberto e não houve merge/deploy nesta revisão.** O [rascunho de PR](V22_PR_DRAFT.md) está pronto para revisão.

Somente depois de autorização explícita para publicar as duas branches e abrir PR:

```powershell
git fetch origin
git status --short
git ls-remote --heads origin main weather-archive feature/v2.2-ciencia-e-rastreabilidade
# Comparar qualquer referência que passou a existir; parar em caso de divergência.
git push -u origin weather-archive:refs/heads/weather-archive
git ls-remote --heads origin weather-archive
# Confirmar 4bb516702e78cdf699ae00577d3a12d1417e74a6.
git push -u origin feature/v2.2-ciencia-e-rastreabilidade:refs/heads/feature/v2.2-ciencia-e-rastreabilidade
```

Abrir PR da feature para main usando o rascunho e revisar CI/diff/permissões. **Merge depende de nova autorização.** Depois do merge autorizado, disparar os workflows necessários, conferir Pages, novo commit científico/manifests/hashes, preservação do histórico, uma execução programada posterior e o painel público. Não prometer conclusão dessas etapas antes de observá-las. Nunca usar force-push nem mesclar `weather-archive` à main.

## 10. GitHub Desktop e rollback

No GitHub Desktop, selecionar o repositório original `campo-e-clima`; a branch deve ser `feature/v2.2-ciencia-e-rastreabilidade`. Em History, revisar o commit importado e o commit de integração, depois comparar com main. A aba Changes deve ficar vazia ao fim desta entrega. **Publish branch** publica remotamente: aguardar autorização. A branch `weather-archive` aparece na lista, mas não usar “Merge into current branch” para ela.

Antes de publicação, para voltar a visualizar o software original com árvore limpa: `git switch main`. Isso não remove a feature nem o arquivo científico. Para voltar ao candidato: `git switch feature/v2.2-ciencia-e-rastreabilidade`. Não trocar de branch com alterações locais sem salvá-las e revisar.

Após eventual merge, rollback deve ser um novo commit por PR: `git revert <commit>` para um commit simples/squash, ou `git revert -m 1 <merge_commit>` após conferir os pais de um merge. Revisar o diff, executar testes e obter autorização para publicação. Manter `weather-archive`, bundles e backups intactos. Não executar `reset --hard`, `clean -fdx`, force-push, exclusão de branches ou reescrita de histórico. As tarefas Windows previamente instaladas e o aplicativo local v0.3 não fazem parte desta alteração.
