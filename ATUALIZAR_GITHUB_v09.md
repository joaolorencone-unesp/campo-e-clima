# Publicar Campo e Clima v0.9 no GitHub Pages

1. Baixe `Campo_e_Clima_v09_SOMENTE_ATUALIZACAO.zip` e extraia.
2. Abra **GitHub Desktop → campo-e-clima → Repository → Show in Explorer**.
3. Copie todo o conteúdo do ZIP para a raiz clonada e aceite substituir os arquivos. As pastas `site/static/`, `tests/` e `docs/` devem permanecer na mesma estrutura.
4. Confira se foi criado `site/static/location.js`. **Não adicione nenhuma chave de API.**
5. No GitHub Desktop, faça commit com a mensagem `feat: coordenadas, NASA POWER e APIs gratuitas v0.9` e clique **Push origin**.
6. Em GitHub → **Actions**, verifique a conclusão verde da execução `Collect and deploy Campo e Clima`.
7. Abra `https://joaolorencone-unesp.github.io/campo-e-clima/` e pressione `Ctrl + Shift + R`.
8. Teste o formulário com latitude `-14.408`, longitude `-56.446` e nome `Diamantino–MT`. Consulte o histórico na nova aba **Histórico NASA & ar** e verifique o status independente de cada API.
9. Depois clique em **Voltar à sede** e confira se a coleta de Naviraí foi restaurada.

**Limitação:** a NASA POWER pode bloquear consultas diretas a partir do navegador (CORS). Nesse caso, use o link **Abrir dados NASA POWER** da aba e confira o relatório. A interface não mostrará dados históricos fictícios. A solução permanente para todos os pontos nesse cenário exigirá backend, já que o Pages é apenas estático.

Somente dados gratuitos, sem One Call paga, sem novas credenciais.
