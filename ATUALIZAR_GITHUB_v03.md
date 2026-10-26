# Atualização do Campo e Clima v0.3 — passo a passo (Windows)

O site atual já funciona em **https://joaolorencone-unesp.github.io/campo-e-clima/**, mas o código publicado no GitHub ainda é a versão 0.2 até que esta atualização seja enviada.

## Caminho mais fácil — GitHub Desktop
1. Baixe o ZIP da **versão 0.3 completa** e extraia em uma pasta temporária.
2. No GitHub Desktop, abra o repositório **joaolorencone-unesp/campo-e-clima**. Se necessário, use **Repository → Pull** antes.
3. Selecione **Repository → Show in Explorer** para abrir a pasta *clonada do GitHub*. Atenção: use a pasta do repositório, não a pasta temporária do ZIP.
4. Copie todo o **conteúdo** da pasta extraída para a pasta clonada, mantendo as pastas `site`, `scripts`, `tests`, `docs` e `.github`. Aceite **Substituir arquivos** quando solicitado. **Não apague a pasta oculta `.git`.**
5. Volte ao GitHub Desktop e confira as alterações em **Changes**.
6. Escreva o resumo do commit: **fix: gráficos e probabilidades horárias v0.3**.
7. Clique em **Commit to main**, depois em **Push origin**.
8. Abra https://github.com/joaolorencone-unesp/campo-e-clima/actions . O workflow **Collect and deploy Campo e Clima** deve iniciar automaticamente pelo push.
9. Aguarde o selo verde ✅; reabra https://joaolorencone-unesp.github.io/campo-e-clima/ com **Ctrl+F5** para forçar atualização do JavaScript/CSS.
10. Em **Chuva & ensembles**, confirme que as datas mostram **26/10, 27/10...**, não 2011. Verifique também os gráficos de comparação dos modelos e os quadros 3h/6h.

## Se o workflow ficar vermelho
Abra a execução em Actions, clique no job que falhou e copie a mensagem de erro. Se falhar só a coleta de um modelo, o coletor deve continuar com os modelos restantes, informando amostra reduzida. Se todos falharem, ele não deve publicar números inventados.

## O que esperar da primeira execução v0.3
- 13 testes locais passaram e o código JS passou na checagem de sintaxe. O GitHub ainda fará **a primeira execução de rede real** desta nova versão.
- O workflow de 30 minutos permanece agendado; não garante execução exatamente no minuto 07 ou 37.
- O botão **Atualizar dados publicados** relê o JSON do site, **não dispara uma consulta direta aos oito modelos**. Uma nova coleta depende da execução do workflow.
- A visualização interativa requer carregar o Plotly do CDN. Se bloqueado, as tabelas continuam disponíveis.

## Segurança
Não publique tokens, coordenadas sigilosas de propriedade, senhas ou arquivos `.env` no GitHub público.
