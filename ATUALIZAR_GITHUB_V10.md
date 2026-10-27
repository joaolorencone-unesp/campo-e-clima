# Campo e Clima v1.0 — atualização do GitHub Pages

1. Baixe **Campo_e_Clima_v10_SOMENTE_ATUALIZACAO.zip** e extraia em pasta temporária.
2. Abra GitHub Desktop no repositório `joaolorencone-unesp/campo-e-clima`, clique **Repository > Show in Explorer**.
3. Copie TODOS os arquivos e pastas extraídos para a raiz clonada, mantendo `.github/`, `site/`, `scripts/`, `tests/`, `docs/`; aceite substituir os arquivos antigos. Não apague a pasta `.git`.
4. No GitHub Desktop, faça commit `feat: histórico ERA5-Land e análise agrícola v1.0` e clique **Push origin**.
5. Na aba GitHub Actions, confira a execução `Collect and deploy Campo e Clima`. O novo passo `Export free INMET station metadata...` não exige chave.
6. Quando o deploy estiver verde, atualize o site com **Ctrl+F5**, escolha coordenadas e abra **Histórico & indicadores**.
7. Confira as séries diárias 30/90/365, comparação NASA × ERA5-Land, gráfico de restrições e estações mais próximas. Clique **Exportar CSV** para baixar dados diários do período.

**Sem pagamento ou chaves.** O botão de atualização do histórico faz consulta separada da previsão. NASA POWER e ERA5-Land só devem ser interpretados como estimativas em grade. A pré-triagem histórica não libera pulverização. Falhas de CORS, timeouts ou indisponibilidade real das APIs são exibidas em lugar de dados imaginados.
