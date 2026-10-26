# Atualizar Campo e Clima para v0.4

**Não extrair a pasta de testes para a raiz errada.**

1. Baixe o arquivo `Campo_e_Clima_v04_SOMENTE_ATUALIZACAO.zip`.
2. Extraia o ZIP. A estrutura deve conter `scripts/`, `site/`, `tests/`, `docs/`, `README.md` e `.github/`.
3. Abra GitHub Desktop, repositório `joaolorencone-unesp/campo-e-clima` → Repository → Show in Explorer.
4. Copie **o conteúdo interno** da pasta extraída para dentro da pasta clonada, aceitando substituição. **Não** substitua a pasta `.git`.
5. No GitHub Desktop, Commit to main com mensagem `feat: cenários conjuntos de pulverização v0.4` e **Push origin**.
6. Abra https://github.com/joaolorencone-unesp/campo-e-clima/actions . Verifique **Unit tests**, **Collect forecasts**, **Archive collected forecast snapshot** e **Publish GitHub Pages**. A arquivação é temporária e não bloqueia a publicação caso falhe.
7. Abra https://joaolorencone-unesp.github.io/campo-e-clima/ e faça Ctrl+F5. Na aba Pulverização, confirme se aparecem modelos e membros **conjuntos**. Se aparecer `0 modelos`, não é falha da interface: a API não forneceu todas as variáveis correlacionadas. Abra os logs e investigue quais campos faltam.

**IMPORTANTE:** Não foram usados valores meteorológicos simulados na versão publicada. Os testes unitários utilizam séries artificiais em arquivos de teste, isoladamente. A execução real da coleta deve ocorrer no Actions com internet.

## O que mudou
- `scripts/spraying.py`: classificação por membro correlacionado, VPD FAO e janelas de 2h; hipóteses e limites experimentais.
- `scripts/collect.py`: coleta extra de seis campos essenciais por modelo para até quatro dias. Falhas registradas por modelo sem imputar missing como favorável.
- `site/index.html`, `site/static/app.js`, `site/static/styles.css`: 3 gráficos de cenários/causas/janelas, amostra real por hora, FAQ científico e links para histórico da Embrapa.
- `.github/workflows/pages.yml`: arquivo temporal de auditoria de cada coleta até 90 dias; não há armazenamento definitivo.
- `tests/test_spraying.py`: valida mesmas identidades e janelas conjuntas.
- `docs/VERIFICACAO_E_EMBRAPA.md`: metodologia para baixar/validar série da estação Naviraí desde dezembro de 2024.
