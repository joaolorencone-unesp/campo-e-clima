# v0.8 (26/10/2026) — qualidade visual e atualização sem custos

**Objetivo:** melhorar a experiência sem acrescentar serviços pagos.

- Corrigida estrutura HTML: referências históricas estavam fora das abas; movidas para Qualidade & fontes.
- Painéis históricos opcionais aparecem somente com série válida. As demais indisponibilidades são apresentadas de modo compacto.
- Botão consulta a previsão determinística diretamente na API pública Open-Meteo e relê o JSON GitHub Pages. Valida fuso UTC−4, proximidade da grade e completude da resposta.
- Feedback visível no botão: resultado e horário da última verificação. Diferencia emissão dos ensembles e atualização determinística.
- O botão e o auto-refresh do navegador usam a mesma função, com trava contra consultas simultâneas.
- Gráficos heatmap e rosa dos ventos preservados: suporte a traços Plotly `z` e `r`, além de `y`.
- ECMWF EC46 e climatologia ERA5-Land temporariamente desativados por timeout ou série incompleta; o painel não mostra projeção ausente como dado.
- Testes de regressão HTML e teste Node offline da consulta da Open-Meteo.

**Limitações:** a atualização direta não recalcula ensembles, pulverização probabilística ou alertas. Os dados conjuntos continuam vinculados à última coleta automatizada. Fontes oficialmente observadas não devem ser confundidas com previsões. Acurácia ainda depende de validação da procedência Embrapa e de hindcast.
