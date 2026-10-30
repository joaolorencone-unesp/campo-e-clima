# Auditoria técnica pré-merge — Campo e Clima V2.2

Data: 29/10/2026. Base examinada: `bcdde96514bb4731ce3f32cbde0366a79a624cdf`, exclusivamente `feature/v2.2-ciencia-e-rastreabilidade`. As correções deste relatório pertencem somente à feature local; o commit final consta do manifesto do novo pacote de auditoria.

## Conclusão: NÃO APTO para merge imediato

A situação remota atual ainda não atende ao objetivo de executar os três workflows após a integração. O [PR #1](https://github.com/joaolorencone-unesp/campo-e-clima/pull/1) continua em `bcdde96`, sem as correções locais descritas abaixo, e **não existe `weather-archive` no remoto**. A versão corrigida bloqueia a inicialização de um arquivo vazio: os jobs de persistência e recuperação exigem que o histórico aprovado seja disponibilizado primeiro. Fazer merge agora deixaria essa dependência sem atendimento.

As correções locais passaram nos testes descritos neste relatório. Isso permite revisão do código, mas não equivale à execução dos novos SHAs das actions, dos tokens/OIDC ou do serviço de artifacts no GitHub. O CI remoto verde disponível é da base anterior. O GitHub informa que o PR não tem conflito textual; isso não comprova prontidão operacional.

Para retirar os bloqueios, em uma etapa futura expressamente autorizada: disponibilizar o histórico existente sem reescrita, publicar a feature corrigida, obter CI verde no novo commit e conferir a ativação dos jobs da `main`, o Pages e a primeira persistência. Não foram executados push, merge, deploy, dispatch de workflow, alterações da `main` ou registro de tarefas nesta auditoria.

## Escopo, isolamento e preservação

- Fonte dos testes: exportação Git exata de `bcdde96`, em pasta temporária separada; ambiente Python 3.13.4 próprio, sem banco oficial.
- Bancos novos, cache HTTP novo, capturas novas e repositório Git temporário sem remote para os ensaios de escrita. `push=False` em todos os ensaios de arquivo.
- `main` e `origin/main`: `e1241e208033baf3260d86c8ba4b03e56ba92300`.
- `weather-archive` local: `4bb516702e78cdf699ae00577d3a12d1417e74a6`.
- Antes da aplicação, 286 arquivos de dados, runtime, snapshots públicos, ZIPs e dois diretórios de entrega foram inventariados por SHA-256. Os 76 arquivos enumerados no manifesto da revisão anterior também foram confrontados com seus hashes. A aplicação exige igualdade integral desse inventário antes e depois.
- Os CSVs de observação, bancos oficiais, snapshots operacionais e backups anteriores não são atualizados com dados de teste. Os dados reais coletados nesta auditoria continuam identificados como material de ensaio.

## Matriz dos workflows corrigidos

| Item | `pages.yml` | `science.yml` | `archive-recovery.yml` |
|---|---|---|---|
| Disparo | Push na `main` filtrado por caminhos; manual; cron `7,37 * * * *` UTC | Manual; cron `23 13 * * *` UTC | Manual, com `source_run_id` |
| Condição | Build somente repositório público e ref `main`; archive exige ID de artifact | Público e ref `main` | Público e ref `main` |
| Horário local | Solicitação a cada 30 min; sem garantia de pontualidade | 09:23 em Naviraí/Diamantino, UTC−4 | Conforme despacho explícito |
| Permissões | Build `contents: read`; deploy `pages: write`, `id-token: write`; archive `contents: write`, `actions: read` | `contents: write` somente no job científico | `contents: write`, `actions: read` |
| Dependências | Build Python 3.11 + requirements; archive requirements-science; deploy artifact de Pages | Python 3.11 + requirements-science; regressão antes da coleta | Python 3.11 + requirements-science; artifact não expirado |
| Concorrência | Grupo `pages`; escritor compartilha `weather-archive-writer` | Grupo `weather-archive-writer` | Mesmo grupo de escrita |
| Política de fila | `queue: max`, sem cancelar execução ativa | Idem | Idem |
| Falha externa | Fonte opcional sinalizada; catálogo INMET não impede publicação; falha principal preserva captura parcial quando possível | Falhas por localidade/produto registradas; falha total gera erro | Artifact ausente/expirado gera aviso sem mutação do arquivo |
| Recuperação | Artifact de captura por 7 dias; job archive condicionado ao upload efetivo | Artifact de imports antes da publicação; diagnóstico separado por 7 dias | Verifica ID numérico, repositório de origem, branch `main`, workflow conhecido e nome esperado |

O deploy depende do build, não do sucesso do arquivo científico. Isso mantém o painel disponível se o arquivo falhar, mas exige observar o resultado do job de arquivo; site acessível não prova persistência. O grupo compartilhado serializa os três escritores. Não há force-push. Capturas já arquivadas no mesmo slot UTC de seis horas não são sobrescritas.

Os disparos agendados só passam a usar a nova definição quando ela estiver na branch padrão. Um `workflow_dispatch` selecionando a feature será ignorado pelos guards de `main`. Nenhum guard foi removido para facilitar testes. O workflow de CI foi atualizado junto com as três rotinas para manter a mesma versão explícita de Ubuntu e runtime das actions, com permissões somente de leitura e sem secrets em PR.

Os requisitos Python usam intervalos de versões. O lock existente registra o ambiente Windows anterior e não é imposto aos runners Linux. Isso mantém compatibilidade, mas não assegura resolução idêntica no futuro; o CI em Python 3.11/3.13 deve continuar obrigatório na revisão. Actions estão fixadas por SHA; esse pin não imobiliza todas as dependências transitivas de actions compostas.

## Falhas identificadas e correções

| Achado | Consequência na base | Correção local e evidência |
|---|---|---|
| Derivação falha após arquivar RAW | Repetir a mesma captura podia não reconstruir relatórios | Reprocessar quando `report_status=previous_preserved`; teste falha na base e passa corrigido |
| Branch de dados remota ausente | Possibilidade de iniciar histórico vazio, separado do backup existente | Preflight antes de criar checkout; ausência gera erro explícito |
| HTTP 429 por modelo | Próximos modelos podiam continuar consultando o provedor | Cooldown persistido, respeitando `Retry-After`; teste comprova uma chamada entre clientes consecutivos |
| Cache corrompido | JSON inválido bloqueava aquisição posterior | Validar hash, idade e payload; tentar coleta nova quando cache é inválido |
| HTTP 200 sem dados meteorológicos úteis | Payload vazio/incompleto podia ser aceito e ocupar slot | Validador de conteúdo; `payload_valid=false`; RAW rejeitado não consome slot nem gera linhas analíticas |
| Horário de chuva sobrescrito por consulta de pulverização | Ensemble antigo parecia recém-coletado | Associar horário a modelo + produto de chuva; usar horário de aquisição real no painel |
| Falha GEFS persistida no cache diário | Timeout transitório mantinha ausência por todo o dia | Reconsultar falhas após pelo menos 6 h; conservar sucessos; chave de cache por execução permite salvar recuperação |
| Atualização visual baseada na emissão do JSON | Reempacotar dados em cache renovava indevidamente indicador | Mostrar a coleta mais antiga dos ensembles em uso; horário ausente é desconhecido |
| GEFS diário sem captura científica padronizada | Proveniência e cota separadas do coletor principal | Passar por FreeClient, preservar RAW `extended_ensemble`; não ingerir como previsão horária ou observação |
| Execução longa frente a timeouts externos | Risco de atingir limite do runner antes de preservar transporte | Orçamento compartilhado de 900 s para FreeClient, limitado a 1–1200 s por CLI; respostas parciais preservadas |
| Actions antigas/Ubuntu móvel | Avisos de Node 20 e mudança de imagem | Atualização para releases com Node 24, SHAs verificados e `ubuntu-26.04` explícito |
| Mensagem vazia permanecia no gráfico GEFS | “Sem dados válidos” coexistia com série real | Remover texto residual antes de inicializar Plotly; teste real de navegador |
| Horário GEFS em cache | Horário de consulta podia ser exibido como nova aquisição | Preservar `collected_at_utc` no produto e cache diário; teste de proveniência |

Seis regressões foram reproduzidas como falhas reais na exportação original antes das correções; o log está em `premerge/regression-before.txt`. As demais verificações complementam esses casos. Os campos novos são compatíveis com manifestos antigos: a ausência de `payload_valid` mantém o tratamento legado, sem regravar objetos já arquivados.

O orçamento de 900 s limita o cliente científico, não é um prazo rígido para todo o processo. Conectores auxiliares legados possuem timeouts próprios; o limite final do job continua 25 min. Cancelamento forçado do runner antes do upload ainda pode impedir transporte. Artifact é recuperação temporária, não backup permanente.

## Ensaios e resultados

| Verificação | Resultado |
|---|---|
| Python, suíte completa offline | **162 passaram**, Python 3.13.4, ambiente isolado, `PYTHONUTF8=1` |
| JavaScript | **13 suítes passaram**; todos os JS em `site/static` passaram em `node --check` |
| Workflows | actionlint 1.7.12 sem outros diagnósticos; exceção de parser somente para `queue`, documentada abaixo |
| Coleta real | Duas localidades; determinístico + NOAA GEFS horários; GEFS diário de Naviraí com resposta real previamente capturada |
| Repetição de coleta | **0 novas chamadas HTTP** na repetição imediata |
| Repetição de publicação no Git temporário | **0 novos commits**, sem remote e sem push |
| Rebuild | SQLite `integrity_check=ok`, verificação de chaves estrangeiras; 3 manifestos, 10 assets RAW |
| Conteúdo reconstruído | 12.384 valores determinísticos, 48.960 valores ensemble, 30 membros, 2 localidades; **0 observações e 0 verificações pareadas** |
| Backup mensal temporário | 1 parte, 16 arquivos verificados; restauração em nova pasta; mesmas contagens após novo rebuild |
| Navegador desktop/mobile | 30 datas exibidas, sendo 16 GEFS; 30 membros; sem erros JS ou recursos locais faltantes; sem overflow horizontal |
| Estado científico sem observações | Mantido “ainda não há amostras”; nenhuma métrica/calibração fabricada |

Os testes foram executados com UTF-8 explícito no Windows. Uma repetição sem essa opção encontrou erros de leitura CP1252 em testes legados/saída do Git; repetida com `PYTHONUTF8=1`, a suíte passou integralmente. O runner Ubuntu usa ambiente UTF-8. Não se afirma portabilidade da suíte Windows com qualquer encoding padrão.

O actionlint disponível antecede `queue: max` e a imagem Ubuntu 26. A configuração local adiciona o nome da imagem à lista aceita pelo linter; isso **não transforma o workflow em self-hosted**. A supressão é restrita ao diagnóstico `unexpected key "queue" for "concurrency" section`. Shellcheck/Pyflakes não foram executados. O GitHub documenta a [fila de concorrência](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency?apiVersion=2022-11-28) e sua [ampliação](https://github.blog/changelog/2026-05-07-github-actions-concurrency-groups-now-allow-larger-queues/).

### Coleta real e limites gratuitos

Foram realizadas quatro sondagens iniciais (uma leitura do JSON público e três consultas meteorológicas) e 12 requisições no ensaio integrado: **16 HTTP no total, 15 a fontes meteorológicas**, incluindo tentativas e INMET. O ensaio integrado tinha teto de 24 requisições. Não houve serviço pago, token meteorológico, IA paga ou varredura histórica extensa. O contador HTTP não é o contador de chamadas equivalentes do provedor.

Para limitar consumo, o pipeline operacional foi executado com um ensemble (GEFS) nas duas localidades. Fontes auxiliares fora do alvo foram explicitamente omitidas no ensaio; isso não é validação ao vivo dos oito ensembles. A rotina `science_daily` foi executada com seu conjunto real de consultas para as duas localidades.

- Naviraí histórico Previous Runs: HTTP 500 em duas tentativas; falha registrada, sem substituição por zero.
- Diamantino histórico Previous Runs: HTTP 200, importação arquivada no repositório temporário.
- INMET: catálogo HTTP 200; séries S735 e A949 responderam HTTP 204, sem corpo. Registradas como indisponíveis, sem observações inventadas.
- Com sucesso parcial, a rotina diária concluiu e manteve diagnóstico por fonte. Sucesso do workflow não deve ser interpretado como completude de todas as fontes.

Os relatórios de teste e rede estão em `premerge/live-integration.json` e `premerge/live-network.json`. Os RAW completos permanecem no pacote local da auditoria, fora da branch de código e dos dados oficiais.

## Por que ensembles e GEFS pareciam sem atualização

O JSON público lido às 19:28 UTC foi emitido às 15:31:41 UTC. Apresentava seis modelos válidos; ICON e GEM tinham timeout. O run [40902392569](https://github.com/joaolorencone-unesp/campo-e-clima/actions/runs/40902392569), na `main` antiga, confirmou seis ensembles e reutilização de `slow-sources-v13-2026-10-29`.

No GEFS estendido, o erro registrado era timeout de 38 s. O coletor guardava também falhas no cache diário, impedindo recuperação naquele dia. A mesma consulta `ncep_gefs_seamless`, `forecast_days=35`, `daily=precipitation_sum` retornou HTTP 200 no ensaio: 35 datas declaradas, 30 campos de membros e 1.020 valores numéricos. O último dia estava incompleto e não foi inventado. O parser aceitou 20 dias estendidos, dos quais 16 entram no calendário de 30 dias. Portanto, a evidência aponta para **timeout e retenção da falha no cache**, não para incompatibilidade comprovada do modelo ou endpoint. A [documentação da Ensemble API](https://open-meteo.com/en/docs/ensemble-api) confirma a existência do produto diário; não foi trocado o modelo sem necessidade.

Os runs agendados examinados terminaram aproximadamente às 01:49, 08:27 e 15:34 UTC, apesar do cron de 30 min. A amostra mostra lacunas de horas, sem provar sua causa exclusiva. O agendamento do GitHub não é garantia de atualização pontual. Somam-se a isso o cache de seis horas dos ensembles e o uso incorreto do horário de emissão no indicador. A correção torna a idade visível, mas não promete execução a cada 30 min.

O preview estático local não coleta sozinho. O preview de auditoria em `http://127.0.0.1:8778/` usa o snapshot real isolado de 29/10, não substitui o painel oficial nem implica atualização contínua. GEFS continua cenário de um único ensemble, sem probabilidade calibrada e sem extensão artificial de datas ausentes.

## Node.js, Ubuntu e evidência remota

O [CI do PR em bcdde96](https://github.com/joaolorencone-unesp/campo-e-clima/actions/runs/40937482568) concluiu com sucesso em Python 3.11 e 3.13, 152 testes na base. Os logs identificaram Ubuntu 26.04. As annotations de Node 20 e migração Ubuntu eram avisos, não a causa demonstrada de falha meteorológica. Os logs também mostravam deprecações `punycode`/`url.parse()` de actions antigas.

As releases oficiais e seus `action.yml` foram consultados. Pins de checkout/setup-python/setup-node/cache/upload-artifact/download-artifact/configure-pages/deploy-pages foram substituídos por releases que declaram Node 24; upload-pages-artifact é composto e usa upload-artifact atualizado. Os nove SHAs estão registrados em `premerge/action-pins.json`.

O GitHub informa que [Node 20 foi retirado](https://github.blog/changelog/2026-09-23-node-20-is-no-longer-available-in-github-actions/) e que [Ubuntu 26 passou a integrar a migração de ubuntu-latest](https://github.blog/changelog/2026-09-17-ubuntu-26-generally-available-and-latest-migration/). Fixar `ubuntu-26.04` elimina a mudança implícita de nome de imagem, não congela atualizações internas do runner.

Docker não tinha daemon ativo e não havia distribuição Ubuntu pronta no WSL. Não foram iniciados serviços ou instalados runners. A compatibilidade Linux dos **novos** pins ainda depende do CI após publicação autorizada. A execução remota anterior bem-sucedida oferece evidência da base/ambiente, não da versão corrigida inteira.

## Evidências e reprodução

Arquivos em `premerge/`: resultados Python/JS, reprodução das falhas, inspeção GitHub, pins, sondagens HTTP, integração/restauração, screenshots e relatório de navegador, inventário resumido de preservação e metodologia do lint. O pacote local adicional inclui scripts de ensaio, RAW, bundle do código corrigido e manifesto SHA-256. Não contém tokens ou arquivos `.env` privados.

Reprodução offline da suíte, em ambiente instalado a partir de `requirements-science.txt`:

```powershell
$env:PYTHONUTF8='1'
$env:CAMPO_OFFLINE_TESTS='1'
python -m pytest -q
node tests/test_freshness_v22.cjs
```

O teste `tests/browser_premerge_v22.cjs` é um ensaio separado contra o snapshot real da auditoria, via `CAMPO_PREVIEW_URL`; não integra o glob de suítes offline e não deve apontar para produção. Os scripts de coleta real do pacote destinam-se à reprodução deliberada, com orçamento de requisições, e não devem ser executados repetidamente como testes unitários.

A mudança não altera schemas de bancos oficiais nem reescreve objetos/manifestos científicos existentes. Reversão do código, se necessária, deve ocorrer em commit na feature, com preservação dos arquivos de dados; os bundles anteriores permanecem íntegros. O novo pacote mantém uma cópia recuperável do commit auditado.
