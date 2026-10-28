# Publicação da v1.6 — Campo e Clima (chuva >0,1 mm)

## O que mudou

- Tabela D0–D6: `≤0,1 mm`, `>0,1 mm`, `0,1–1 mm`, `>1 mm`, `>5 mm`, `>10 mm`, `>20 mm`.
- Gráfico de faixas exclusivas (as quatro classes somam 100% dos membros válidos).
- Comparação de **modelos individuais**, escolhendo o dia, entre >0,1 e >1 mm.
- Gráfico de chuva por hora e tabela 3/6 h mostram ambos os limiares.
- Resumo explicativo da diferença entre chuva residual e >1 mm.
- Testes do algoritmo e da interface, inclusive no GitHub Actions.

## Instalação pelo GitHub Desktop

1. Baixe o ZIP `Campo_e_Clima_v16_SOMENTE_ATUALIZACAO.zip` e extraia-o.
2. No GitHub Desktop abra o repositório `campo-e-clima` → **Repository > Show in Explorer**.
3. Copie **o conteúdo interno** da pasta extraída para a raiz do repositório, **preservando** `site/`, `scripts/`, `tests/`, `docs/` e `.github/`.
4. Confira as alterações, faça commit `feat: comparacao chuva residual e chuva >1 mm v1.6` e clique em **Push origin**.
5. Consulte **Actions** → `Collect and deploy Campo e Clima`. Aguarde execução verde. Abra o site e pressione `Ctrl+F5`.
6. Selecione `Chuva & ensembles`, compare a coluna `>0,1 mm` com `>1 mm` e selecione datas no gráfico de concordância. Teste também outras coordenadas com amostras válidas.

## Avisos

- Antes de a nova coleta gerar `rain_models_daily` com ambos os limiares, o gráfico de comparação **por modelo** poderá mostrar indisponibilidade, mesmo que a tabela multimodelo já apresente >0,1 mm: isso é esperado. Uma coleta válida nova resolve o preenchimento.
- Caso a API não devolva ensembles válidos para a coordenada, o painel pode apresentar previsão determinística, identificada como **outra fonte, sem frequências multimodelo**.
- `>0,1` inclui os casos `>1`; `0,1–1` é a diferença entre ambos. `≤0,1` não significa ausência absoluta de água.
- Frequências ainda não calibradas; só medições de estação confirmadas permitirão avaliar superestimativa real.
- Nenhuma credencial/API paga foi adicionada. O site não foi publicado automaticamente nesta entrega.
