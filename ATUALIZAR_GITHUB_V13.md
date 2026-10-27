# Atualizar Campo e Clima para v1.3

**Site:** https://joaolorencone-unesp.github.io/campo-e-clima/

1. Extraia `Campo_e_Clima_v13_SOMENTE_ATUALIZACAO.zip` no computador.
2. No GitHub Desktop, selecione o repositório `campo-e-clima` e abra **Repository → Show in Explorer**.
3. Copie os arquivos e diretórios do ZIP para **dentro da pasta do repositório**, preservando o caminho de `.github/workflows/pages.yml`, `scripts/`, `site/`, `tests/` e `docs/`. Os arquivos antigos com o mesmo caminho serão substituídos.
4. Confira que a pasta `.github` (oculta em alguns sistemas) também foi copiada: o novo cache semanal depende do workflow atualizado.
5. No GitHub Desktop, crie o commit `feat: Campo e Clima v1.3 - GEFS, historico e pulverizacao` e clique em **Push origin**.
6. Abra https://github.com/joaolorencone-unesp/campo-e-clima/actions e confira a última execução.
7. Abra https://joaolorencone-unesp.github.io/campo-e-clima/ e pressione **Ctrl+F5**. Teste as abas Pulverização, Histórico & indicadores e 30–60 dias.

## Diagnóstico

- `data/latest.json`: `complementary.gefs_extended.state` e `complementary.ecmwf_extended.state` mostram separadamente a disponibilidade.
- `state: unavailable` não é tempo seco; mensagens `HTTP 429` indicam limitação de acesso.
- Um produto sazonal em erro pode continuar indisponível durante a semana para evitar requisições repetitivas.
- Nova série NASA/ERA5 no histórico depende de acesso real às APIs no navegador; nunca substitui medições do talhão.
- **Não cadastre tokens no código**, nem compartilhe chaves ou credenciais no chat. Esta versão não exige novos segredos.

Arquivos gerados no GitHub Actions podem demorar para ser publicados após o commit. O site não será atualizado até o workflow concluir.
