# Gatilho externo gratuito para a coleta (cadência real de 30 min)

O agendamento `cron` do GitHub Actions é "melhor esforço": na auditoria da v3 só cerca de 9 % das 48 rodadas diárias executaram. Desde a v4.1 o fluxo `Collect and deploy Campo e Clima` também aceita o evento `repository_dispatch` com tipo `collect`, que pode ser disparado por qualquer agendador externo gratuito. Cada disparo roda a coleta completa e publica o site; o cache de ensembles (máximo 4 h) e os caches diários continuam valendo, então o custo em consultas aos provedores não muda.

## 1. Criar um token de acesso com escopo mínimo

1. GitHub → sua foto → **Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token**.
2. Nome: `campo-e-clima-dispatch`; validade de até 1 ano (anote a data para renovar).
3. **Repository access**: *Only select repositories* → `joaolorencone-unesp/campo-e-clima`.
4. **Permissions → Repository permissions → Contents: Read and write** (é a permissão exigida pelo `repository_dispatch`). Nada mais.
5. Copie o token uma única vez. Ele nunca entra no repositório nem nesta conversa.

## 2. Configurar o agendador (exemplo: cron-job.org, plano gratuito)

1. Crie uma conta em https://cron-job.org e um novo cron job.
2. URL: `https://api.github.com/repos/joaolorencone-unesp/campo-e-clima/dispatches`
3. Método: **POST**. Corpo (request body): `{"event_type":"collect"}`
4. Cabeçalhos (headers):
   - `Accept: application/vnd.github+json`
   - `Authorization: Bearer <SEU_TOKEN>`
   - `X-GitHub-Api-Version: 2022-11-28`
   - `Content-Type: application/json`
5. Agendamento: a cada 30 minutos nos minutos **15 e 45** (o cron do GitHub já tenta nos minutos 7 e 37; os dois se complementam).
6. Salve e execute uma vez manualmente: a resposta esperada é **HTTP 204** e, em até um minuto, um novo run com evento `repository_dispatch` aparece em Actions.

## 3. Verificar e manter

- Em **Actions → Collect and deploy Campo e Clima**, os runs disparados externamente mostram "repository_dispatch". O painel exibe o evento em Qualidade, fontes & diagnóstico.
- Se o token expirar, o agendador passa a receber HTTP 401: gere um novo token e atualize o cabeçalho.
- Para suspender, basta pausar o job no agendador; nada precisa mudar no repositório.

## Limites e cuidados

- O token concede escrita de conteúdo no repositório: guarde-o só no agendador, com conta protegida por senha forte e autenticação em dois fatores.
- O GitHub pode enfileirar runs simultâneos; o fluxo já usa `concurrency: pages` com fila, então disparos sobrepostos não quebram a publicação.
- Minutos gratuitos do Actions: contas pessoais em repositório público não são cobradas por minutos de runners hospedados.
