# Atualização Campo e Clima v1.2 — como publicar

1. Faça uma cópia da pasta do repositório antes de alterar.
2. Baixe o ZIP de **somente atualização**, extraia e copie seus arquivos para a pasta clonada do GitHub Desktop. Preserve as subpastas `site/`, `scripts/`, `tests/`, `.github/`, `docs/`.
3. No GitHub Desktop, confirme os arquivos modificados e o **novo** `site/static/extended_v12.js`. Faça commit `fix: explicacao pulverizacao, historico ERA5 e tendencia semanal v1.2` e clique **Push origin**.
4. Acesse https://github.com/joaolorencone-unesp/campo-e-clima/actions . Aguarde o workflow «Collect and deploy Campo e Clima» terminar com ✅. Se falhar, abra os logs e confira a mensagem sem publicar segredos.
5. Abra https://joaolorencone-unesp.github.io/campo-e-clima/ e pressione **Ctrl+F5**.
6. Em **Pulverização**, selecione categoria, dia e **hora** no quadro «Por que a pulverização está restrita?»; compare as causas e o percentual total de restrição. Em **Histórico & indicadores**, escolha 30/90 dias e confira chuvas numéricas. Em **30–60 dias**, consulte média semanal/mensal ECMWF do ponto escolhido.
7. Não esqueça que o painel é de pesquisa. Sem confirmação de inversão, bula, deriva, ambiente e medições locais, nenhum indicador significa autorização de pulverização.

**Sem custos de API**: nenhuma credencial paga foi adicionada. Open-Meteo no serviço público para uso não comercial, sujeito a seus termos. A consulta sazonal pode falhar; a página informará essa situação. Testes externos precisam da execução real no GitHub Actions e no navegador.
