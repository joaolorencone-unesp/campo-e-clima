# Atualizar o Campo e Clima para v0.5 — integração inicial das fontes

1. Baixe **Campo_e_Clima_v05_SOMENTE_ATUALIZACAO.zip** e extraia-o.
2. No **GitHub Desktop**, abra o repositório `joaolorencone-unesp/campo-e-clima` e selecione **Repository → Show in Explorer**.
3. Copie **todos os arquivos e pastas extraídos**, substituindo os existentes. Inclua as pastas **.github**, **scripts/sources**, **tests**, **docs**, **data/observacoes** e **site**. Não substitua nem exclua a pasta `.git`.
4. No GitHub Desktop: `Commit to main` (mensagem sugerida: `feat: INMET municipal, estacoes e importacao Embrapa v0.5`) → **Push origin**.
5. Abra https://github.com/joaolorencone-unesp/campo-e-clima/actions e confira execução verde. Os testes são offline; a coleta de INMET será validada pela primeira execução no GitHub.
6. Abra https://joaolorencone-unesp.github.io/campo-e-clima/ e pressione **Ctrl+F5**. A aba **📍 Observações & alertas** mostrará avisos municipais, status das fontes e estações próximas.
7. Para o histórico Embrapa, siga `docs/INTEGRACAO_BASES.md`. **Até importar o CSV real, o gráfico ficará sem dados. Isso é correto.**

Se a consulta ao INMET falhar ou for bloqueada, a tela mostrará explicitamente `consulta indisponível`; não haverá previsão ou aviso fictício. A API de observações diárias do INMET pode restringir acesso fora de seu site; isso não impede as previsões Open-Meteo de funcionar.

Não é necessário mexer em Settings → Pages novamente.
