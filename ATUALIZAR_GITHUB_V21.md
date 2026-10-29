# Campo e Clima v2.1 — Central Agro e retrospectiva recente

## Arquivos de atualização

Extraia o ZIP `Campo_e_Clima_v21_SOMENTE_ATUALIZACAO.zip` na raiz do repositório `joaolorencone-unesp/campo-e-clima`, **preservando as subpastas**. Substitua os arquivos existentes. O pacote não contém arquivos de dados reais, tokens ou chaves privadas.

Arquivos principais:

- `site/index.html`: nova aba **🌱 Central Agro**.
- `site/static/agro_cockpit_v21.js`: regras transparentes para triagem e histórico recente via Open-Meteo Forecast API `past_days=4`.
- `site/static/app.js`: evento interno de atualização para alimentar a Central Agro, sem alterar os cálculos anteriores.
- `site/static/styles.css`: estilo moderno/responsivo.
- `.github/workflows/pages.yml`: teste de regressão da nova Central.
- `tests/test_agro_cockpit_v21.cjs` e `tests/test_agro_markup_v21.py`.
- `README.md` e `docs/CENTRAL_AGRO_V21.md`.

## Como publicar

1. No GitHub Desktop, selecione `campo-e-clima` e abra **Repository → Show in Explorer**.
2. Copie os conteúdos extraídos do ZIP para essa pasta (não crie `campo-e-clima/campo-e-clima`).
3. Faça o commit `feat: central agro, triagem horaria e historico recente v2.1`.
4. Clique em **Push origin**.
5. Verifique a execução **Collect and deploy Campo e Clima** em **Actions**.
6. Abra https://joaolorencone-unesp.github.io/campo-e-clima/ e recarregue com **Ctrl+F5**.
7. Teste a aba **🌱 Central Agro** em Naviraí e depois em Diamantino, conferindo as coordenadas, a fonte e o horário.

A atualização **não foi publicada automaticamente**. Como o projeto é estático (GitHub Pages), a retrospectiva dos dias recentes é consultada no navegador apenas ao abrir a aba. Não há alteração dos limites gratuitos das APIs nem dependências novas do Python.

## Como interpretar

- **Chuva próximas 24 h:** soma das horas futuras efetivamente disponíveis do produto determinístico, não previsão observada.
- **>0,1 mm versus >1 mm:** frequências de membros ponderadas igualmente por ensemble, não probabilidades calibradas.
- **Triagem:** filtros experimentais replicados do painel (vento 3–10 km/h, rajadas ≤25 km/h, T<30 °C, UR≥55%, VPD conforme categoria e chuva das próximas 3 horas ≤0,1 mm). **Não são limites universais** e nenhum resultado equivale a autorização de pulverização.
- **Condições operacionais:** estabilidade atmosférica, inversão, bula, deriva, equipamento, pessoas, recursos hídricos e culturas sensíveis exigem avaliação profissional e local.
- **Altura de voo informada:** apenas contexto operacional. O algoritmo NÃO calcula nem recomenda altura, dose, velocidade de voo ou tamanho de gota.
- **Ontem/anteontem:** `Open-Meteo Forecast API` com `past_days`; estimativas retrospectivas de modelo, NÃO pluviometria observada e NÃO reanálise consolidada.
- **Troca de coordenadas:** a Central não reutiliza o diagnóstico de outro ponto. Ausência de dado é apresentada como ausência, nunca como 0.

## Verificações realizadas

- 97 testes Python aprovados.
- Todos os testes JavaScript existentes mais o novo teste da Central Agro aprovados.
- Teste do navegador (Chromium/Playwright) com respostas simuladas: quadro e tabelas carregando em Naviraí e Diamantino, sem erros JavaScript, inclusive histórico recente. As respostas simuladas **não fazem parte do pacote de publicação**.
- Teste real pós-publicação ainda necessário: a disponibilidade da Open-Meteo pode variar por coordenada, navegador e limites do serviço.

Documentação completa: `docs/CENTRAL_AGRO_V21.md`.
