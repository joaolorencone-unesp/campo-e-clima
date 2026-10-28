# Campo e Clima v1.6 — chuva residual, limiares e concordância de modelos

## Objetivo

Distinguir situações em que muitos membros preveem precipitação residual (>0,1 mm/dia) mas poucos excedem 1 mm/dia. O painel apresenta frequências brutas ponderadas; **não são probabilidades calibradas**.

## Cálculos

Os dados diários por modelo são obtidos da mesma amostra de membros válidos, para o mesmo dia local e grade de previsão. Cada ensemble válido recebe peso total 1/M; seus membros válidos recebem 1/(M × N_m). O campo `p_gt_0_1_mm` já era produzido pelas rotinas multimodelo; passou a ser mostrado na interface e incluído no resumo individual por modelo.

- `p_gt_0_1_mm = Σpeso(member) × I(chuva_dia > 0,1)`
- `p_gt_1_mm = Σpeso(member) × I(chuva_dia > 1)`
- `p_gt_5_mm = Σpeso(member) × I(chuva_dia > 5)`
- **Praticamente seco:** `P(chuva ≤ 0,1) = 1 - P(chuva > 0,1)`.
- **Muito fraca:** `P(0,1 < chuva ≤ 1) = P(>0,1) - P(>1)`.
- **Fraca:** `P(1 < chuva ≤ 5) = P(>1) - P(>5)`.
- **Mais significativa:** `P(>5)`.

Essas quatro classes são exclusivas e somam 100% na amostra válida. Os limiares são de **acumulado no período**, não de intensidade de chuva.

`null`/ausência de campo não é 0. Se algum limiar não existe ou os limiares são inconsistentes, gráficos derivados ficam indisponíveis. O gráfico não combina probabilidades de modelos e observações nem reutiliza dados de Naviraí para outra coordenada.

## Leitura do painel

1. **Frequência de ultrapassar limites:** >0,1 e >1 exibidas lado a lado com >5, >10 e >20 mm/dia.
2. **Chuva residual ou chuva mensurável:** barras empilhadas com quatro classes exclusivas.
3. **Concordância dos modelos:** selecionar o dia e comparar, por ensemble, a frequência de >0,1 e >1 mm/dia. A diferença entre as duas é a faixa >0,1 a 1 mm/dia. Não significa precisão comprovada.
4. **Tabela diária**: P10/P50/P90, média e frequências `≤0,1`, `>0,1`, `>1`, `>5`, `>10` e `>20` mm.
5. **Janelas horárias**: >0,1 e >1 mm por 1h, 3h e 6h são derivados dos mesmos membros válidos para cada janela, sem multiplicar probabilidades marginais.

## Limitações

- Frequências dos membros não são calibradas e os ensembles podem ter erros correlacionados.
- Alguns modelos podem interpolar dados de resolução nativa 3–6h; isso não equivale à informação horária independente.
- Comparações devem manter a mesma definição temporal do dia, a coordenada de grade e a variável.
- Limiares >0,1 e >1 mm por **dia** não são diretamente comparáveis com os limiares por **hora**.
- Para avaliar se o painel superestima chuva, preservar previsões emitidas e comparar os eventos em observações verificadas de estação; usar diagramas de confiabilidade e Brier Score para cada limiar.
