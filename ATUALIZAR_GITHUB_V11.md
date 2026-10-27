# Publicar Campo e Clima v1.1 — Pulverização horária e INMET S735

1. Baixe o ZIP **Somente atualização** e extraia.
2. No GitHub Desktop, selecione `joaolorencone-unesp/campo-e-clima` e abra **Repository → Show in Explorer**.
3. Copie todo o conteúdo da atualização **dentro da pasta clonada**, preservando `site/`, `scripts/`, `tests/` e `docs/` e substituindo os arquivos antigos.
4. Faça commit `feat: triagem horaria 1h e consulta S735 v1.1` e **Push origin**.
5. Aguarde a conclusão da publicação em https://github.com/joaolorencone-unesp/campo-e-clima/actions . Uma execução verde não garante que todas as APIs externas responderam: confira os registros e o painel.
6. Abra https://joaolorencone-unesp.github.io/campo-e-clima/ e pressione Ctrl+F5.
7. Na aba **Pulverização**, escolha a categoria (herbicida, fungicida, inseticida) e o dia. Os gráficos mostram cada hora do dia; a alternativa **72h completas** também está disponível.
8. Na aba **Observações & fontes**, confira o estado de **Leituras horárias INMET (estação próxima)**. Se houver bloqueio/404/204, use os links oficiais. Não trate uma falha como zero ou como estação funcionando.

**IMPORTANTE**: esta atualização ainda não foi aplicada ao GitHub. A conexão de escrita havia retornado erro 403; por isso a entrega inclui ZIP.

**Testes locais:** 62 testes Python e teste JavaScript de amostras conjuntas executados; acesso externo a endpoints INMET e Open-Meteo não validado no ambiente local. A próxima execução no GitHub Actions testará as chamadas reais.
