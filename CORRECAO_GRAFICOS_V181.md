# Campo e Clima — correção de gráficos (v1.8.1)

## Diagnóstico verificado

O `site/index.html` publicado incluía `script defer src="static/plotly.min.js"`, mas o arquivo `site/static/plotly.min.js` **não existia** no repositório. A interface corretamente mostrava "Biblioteca gráfica indisponível" quando `window.Plotly` não era carregado.

Os dados meteorológicos e as tabelas continuam carregando; o erro é da camada de visualização e não significa falha dos ensembles.

## Arquivos incluídos

- `site/static/plotly.min.js`: Plotly.js **v3.3.1**, cópia local do pacote Python Plotly instalado; software MIT, cabeçalho de copyright preservado.
- `tests/test_plotly_asset.py`: impede que futuras versões sejam publicadas sem o arquivo gráfico.

## Instalação no repositório

1. Extraia o ZIP de atualização.
2. Copie `site/static/plotly.min.js` para **site/static** da pasta do seu repositório Git.
3. Copie `tests/test_plotly_asset.py` para **tests** da pasta do repositório Git.
4. No GitHub Desktop, faça commit **fix: restaura Plotly local e teste de integridade** e **Push origin**.
5. Em Actions, confira a execução verde e o deploy. No site, use **Ctrl + F5**.
6. Abra a aba Chuva & ensembles; os gráficos devem reaparecer. Se ainda houver falha, confira o Console/Network (F12) e se `static/plotly.min.js` retorna HTTP 200.

**Atenção:** não copie o ZIP para dentro do repositório como arquivo ZIP. Extraia os arquivos e preserve as subpastas. Não é necessário atualizar dados de chuva nem adicionar APIs.

## Origem/licença

Plotly.js v3.3.1 (cabeçalho MIT preservado). Projeto: https://github.com/plotly/plotly.js
