# Atualizar o Campo e Clima para v0.7 — sem serviços pagos

1. Baixe `Campo_e_Clima_v07_SOMENTE_ATUALIZACAO.zip` nesta conversa.
2. Extraia o ZIP. **Não copie o arquivo .zip para dentro do repositório; copie os arquivos e pastas extraídos.**
3. No **GitHub Desktop**, escolha o repositório `joaolorencone-unesp/campo-e-clima`; clique em **Repository → Show in Explorer**.
4. Copie o conteúdo extraído para a pasta clonada, preservando `scripts/`, `site/`, `.github/`, `tests/`, `docs/` e demais caminhos; confirme substituição dos arquivos existentes.
5. No GitHub Desktop, confira `Changes`, escreva o commit `feat: integracoes gratuitas e clima historico v0.7`, clique **Commit to main** e depois **Push origin**.
6. Abra **https://github.com/joaolorencone-unesp/campo-e-clima/actions**. A execução deve terminar verde. Se estiver vermelha, abra a etapa **Collect forecasts** e compartilhe somente a **mensagem de erro, sem tokens/chaves**.
7. Abra **https://joaolorencone-unesp.github.io/campo-e-clima/**, use `Ctrl+F5`, e entre na aba **Observações & fontes**. Procure os gráficos “Climatologia de chuva — 1991–2020” e “Previsão passada × exportação provisória”. Na aba **Qualidade & fontes**, confira os status das duas fontes e erros de coleta.

## Não precisa contratar nada

- **NÃO assine OpenWeather One Call.** O workflow não a utiliza.
- A previsão **OpenWeather 5 dias/3h Free** foi implementada **opcionalmente**. Só será consultada se, após revogar a chave exposta, você criar outra do plano gratuito e cadastrá-la como segredo `OPENWEATHER_FREE_API_KEY`. Sem isso, o painel funciona com as outras fontes e não faz a chamada.
- **NÃO coloque as chaves NASA/Google no GitHub.** As novas integrações não as utilizam.
- Revogue as credenciais que foram expostas por capturas/mensagens anteriores e gere outras apenas quando um conector gratuito e seguro efetivamente precisar delas.

## O que esperar na primeira publicação

A primeira execução no GitHub terá de consultar os novos endpoints externos; por isso ela poderá durar mais. A climatologia (30 anos, ERA5-Land) é armazenada em **cache mensal** e Previous Runs, NASA POWER e ECMWF subsazonal em **cache diário**. A coleta geral continua agendada a cada 30 minutos (sujeita ao GitHub).

- Se a API recusar uma variável, o painel informará o erro da fonte, sem preencher números fictícios.
- A série da Embrapa continuará **provisória** até identificarmos formalmente Naviraí/IFMS na exportação original.
- Gráficos do diagnóstico histórico **não são índices de precisão**.
- O GOES-19 é apenas um link público externo neste estágio: não exibimos satélite/radar “ao vivo” sem validar horário e localização.

## Verificar segurança

No GitHub, em **Settings → Secrets and variables → Actions**, você não precisa cadastrar qualquer API Key para esta versão. Mesmo que exista algum segredo antigo, o workflow v0.7 **não referencia** os segredos antigos do One Call, NASA ou Google. A única chave opcional aceita é uma chave NOVA do OpenWeather Free de cinco dias.

Confira se `site/data/latest.json` não foi versionado no repositório. Ele é gerado durante o deploy; não publique credenciais, exports privados ou históricos de navegação.
