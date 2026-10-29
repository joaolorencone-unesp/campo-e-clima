# Verificação de previsões

`python -m scripts.science_cli evaluate --db runtime/science_rebuilt.sqlite`

Pares: previsão emitida/coletada antes da validade → instante e intervalo previstos → observação identificada. Separar local, modelo, variável, horizonte, convenção de antecedência, estação, estação do ano e data UTC. Não unir Naviraí e Diamantino. Reanálise/Historical Forecast são excluídos da comparação como previsão emitida. Versões conflitantes da observação também são excluídas.

MAE = média |f−o|; RMSE = raiz da média (f−o)²; viés = média (f−o). Direção usa menor diferença angular e média circular; 359°/1° têm diferença 2°. Média de direção dos membros também é circular; distribuição sem direção resultante é excluída.

Brier = média (p−y)², eventos y∈{0,1}; BSS = 1−BS/BS_referência, somente com referência apropriada e denominador positivo. Relatório bruto não inventa climatologia independente. CRPS empírico ponderado = Σw|x−o| − ½Σwᵢwⱼ|xᵢ−xⱼ|. Confiabilidade em dez classes com contagem e frequência observada; classes vazias ficam ausentes. Detecção: hits, misses, falsos alarmes, acertos negativos, POD, FAR e CSI, com denominadores nulos tratados como ausentes.

Chuva: limiares estritos >0,1, >1, >3, >5, >10 e >20 mm por intervalo explicitado. Frequências brutas não são probabilidades calibradas. Multimodelo atribui peso total igual a cada modelo válido e conserva IDs das rodadas na linhagem. Métricas diárias permitem agregação exata do período selecionado; não se faz média simples de RMSEs.

Nesta entrega, há zero pares elegíveis por indisponibilidade de observações confiáveis. Portanto o painel não apresenta valores de precisão nem ordena vencedores. Mesmo quando existirem pares, o relatório bruto é descritivo; os testes temporais de calibradores ficam separados. Não há inferência automática de superioridade, intervalo de confiança ou robustez.

Referências consultadas: [ECMWF, conceitos probabilísticos](https://confluence.ecmwf.int/pages/viewpage.action?pageId=250026294), [ECMWF, uso de métricas](https://confluence.ecmwf.int/pages/viewpage.action?pageId=311146420). Fórmulas e casos-limite têm testes numéricos independentes em tests/test_science_v22.py.
