# Campo e Clima v0.8 — atualização de interface e do botão

## Problemas corrigidos

1. Gráficos de ERA5-Land e Previous Runs estavam fora das abas no HTML; agora pertencem à **Qualidade & fontes**.
2. Quando uma fonte opcional falha, seu gráfico é ocultado (ou substituído por uma mensagem compacta); não haverá cartão alto e vazio.
3. O botão **Atualizar previsão agora** tem duas ações: relê a última coleta do GitHub Pages (`site/data/latest.json`) **e consulta diretamente** a previsão determinística atual da Open-Meteo, usando HTTPS público sem chave.
4. O usuário vê o resultado da consulta: horário, sucesso, ausência de nova publicação ou falha da fonte.
5. A cada 30 minutos, enquanto a página estiver aberta, o navegador também tenta atualizar a previsão determinística. O GitHub Actions continua produzindo o ensemble em sua programação própria (não garantida no minuto exato).
6. A emissão dos ensembles e a atualização horária direta são apresentadas **separadamente**; clicar no botão não recalcula membros ou probabilidades do ensemble.
7. Consultas repetidamente falhas de ERA5-Land 1991–2020 e ECMWF estendido estão **pausadas** para acelerar as publicações. Isso não afirma que esses serviços são pagos, e sim que essas rotinas precisam de correção/validação antes de reativar.

## Como publicar

1. Descompacte `Campo_e_Clima_v08_SOMENTE_ATUALIZACAO.zip`.
2. No GitHub Desktop, escolha `joaolorencone-unesp/campo-e-clima` e abra **Repository → Show in Explorer**.
3. Copie **o conteúdo** da pasta extraída para dentro do repositório clonado, preservando `.github`, `site`, `scripts`, `tests` e `docs`.
4. Aceite substituir os arquivos existentes; **não remova o diretório oculto `.git`**.
5. Faça commit `fix: interface e atualizacao Open-Meteo v0.8` e clique **Push origin**.
6. Abra `https://github.com/joaolorencone-unesp/campo-e-clima/actions`; a execução inclui os testes Python e o teste offline do botão.
7. Após execução ✅, abra `https://joaolorencone-unesp.github.io/campo-e-clima/` e pressione Ctrl+F5.
8. Clique em **Atualizar previsão agora**. A mensagem abaixo do botão deverá indicar se obteve dados determinísticos recentes. Confira a legenda: os *ensembles* têm carimbo separado.

## Status de validação

- `python -m pytest -q`: **47 testes aprovados**.
- `node tests/frontend_smoke.cjs`: simulação offline da consulta direta, parâmetros, fuso e validação de dados: **aprovada**.
- `node --check site/static/app.js`: **aprovada**.
- Inspeção estrutural HTML: gráficos históricos dentro de `verification`, sem divisão externa entre abas.
- **Não** foi possível executar Chromium/Playwright no sandbox devido ao bloqueio administrativo de navegação local; a confirmação visual e a consulta externa serão realizadas **no próprio GitHub Pages**, após publicação.

## O que o botão NÃO faz

O navegador não consegue disparar um workflow GitHub Actions com segurança sem expor um token de escrita. Consequentemente, o botão consulta o *Forecast determinístico diretamente da Open-Meteo* e baixa o ensemble mais recente **já publicado**; não cria automaticamente uma nova rodada dos oito ensembles nem gera um novo aviso INMET.

Nenhuma chave/API paga é necessária para o funcionamento principal. Não adicione credenciais no código, ZIP ou conversa. Caso algum serviço não responda, a interface apresenta status de falha, não valores fabricados.
