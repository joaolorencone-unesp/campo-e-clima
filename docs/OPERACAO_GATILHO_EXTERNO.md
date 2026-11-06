# Coleta de contingência para o Campo e Clima

O cron do GitHub Actions pode atrasar ou perder disparos. A verificação externa consulta a idade da publicação de Naviraí e Diamantino. A partir de 35 minutos em qualquer um dos locais, confere a fila do workflow `pages.yml`. Só solicita uma coleta se nenhum run consultado estiver ativo ou tiver sido criado nos últimos 25 minutos. A idade de publicação é diferente da idade de aquisição ou da rodada de cada modelo. Os caches e os limites de consulta dos provedores continuam sob controle do workflow.

## Simular

Em uma máquina com Python e `requests`, a partir da raiz do repositório, rode o comando abaixo. O script lê o diagnóstico público e, quando necessário, consulta o histórico do Actions. A resposta `would_dispatch` indica que a coleta seria solicitada.

```text
python -m scripts.dispatch_pages
```

## Ativar após autorização

1. Em **Settings → Developer settings → Personal access tokens → Fine-grained tokens**, selecione somente `joaolorencone-unesp/campo-e-clima` e conceda **Actions: Read and write**. Escolha uma validade definida e anote a data de renovação. Esse é o escopo exigido pela [API de disparo de workflows](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event).
2. Configure `CAMPO_PAGES_DISPATCH_TOKEN` como segredo no ambiente do processo agendado. Mantenha o token fora de arquivos do repositório, argumentos de comando e logs. A credencial permite operar os workflows do repositório e deve ficar em uma máquina de confiança.
3. Configure um único agendador para executar `python -m scripts.dispatch_pages --dispatch` a cada 10 minutos, a partir da raiz do repositório. Em Windows, selecione **Não iniciar uma nova instância** se a anterior ainda estiver em execução. A máquina deve estar ligada para cobrir o período desejado.
4. Em **Actions → Collect and deploy Campo e Clima**, verifique o evento `workflow_dispatch`. Compare os intervalos entre deploys bem-sucedidos e os horários de aquisição em **Qualidade, fontes & diagnóstico**. Pause a tarefa externa para suspender o piloto.

Se a leitura do painel ou do GitHub falhar, a verificação termina sem POST e pode ser executada novamente no próximo horário. O resultado `dispatch_accepted` confirma a aceitação da solicitação. A publicação é confirmada pelo job `deploy` e pelo JSON público. Disparos do próprio GitHub ainda podem coincidir com a verificação externa. A fila do workflow protege a execução concorrente.

O evento `repository_dispatch` com tipo `collect` permanece disponível para integrações existentes. O script de contingência usa `workflow_dispatch` para trabalhar com uma credencial de Actions.
