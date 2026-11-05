# Plano científico — precisão da previsão de chuva (Naviraí, Diamantino e outros pontos)

## 1. Pergunta e hipóteses

Pergunta: qual produto de chuva (modelo individual, média, mediana, consenso, ponderação por desempenho) tem melhor desempenho por horizonte (0–6 h … 7–14 dias), para ocorrência, quantidade e intensidade, nestas localidades?

Hipóteses a testar, não assumir: H1 a mistura de 8 modelos com pesos iguais supera o melhor modelo individual em CRPS/Brier; H2 a correção de viés simples reduz o MAE da quantidade; H3 a frequência bruta dos ensembles é superconfiante (diagrama de confiabilidade abaixo da diagonal); H4 modelos do mesmo centro (IFS/AIFS, GEFS/AI-GEFS) não acrescentam habilidade proporcional ao número de membros.

## 2. Dados que já existem

| Conjunto | Situação | Uso |
|---|---|---|
| Ensembles arquivados (8 modelos, 4 janelas/dia alvo) | desde 29/10/2026; Naviraí contínuo desde 03/11 | Verificação probabilística real a partir de ~90 dias |
| Previous Runs GFS (D1/D2/D3/D7) | importação diária, 7 dias por execução, desde 29/10 | Verificação determinística com antecedência fixa; estender a ECMWF IFS 0,25° e ICON (31 dias por chamada, retrocoleta em blocos) |
| Single Runs | arquivado, disponibilidade pública não comprovada | Somente exploratório |
| Historical Forecast / ERA5 | série modelada | Nunca como observação; útil como clima de referência e para preditores antecedentes |
| Embrapa Guia Clima (694 dias) | provisória (sem identidade no arquivo) | Referência diária assim que confirmada; é a estação mais próxima (~4,5 km) |
| INMET A752/A949 | rota pública sem dados; token pendente | Referência horária oficial |

## 3. O que pode ser feito agora (sem calibrar)

1. Retrocoletar Previous Runs (ECMWF IFS, ICON seamless, GFS) para 2025–2026 em blocos de 31 dias, duas localidades, D1/D2/D3/D7 — cabe na cota (≈3 chamadas por bloco).
2. Confirmar a identidade da série Embrapa (captura de tela da seleção da estação ou e-mail da Embrapa/IFMS) e importá-la como `verified_by_official_metadata`.
3. Pedir o token do INMET e importar BDMEP de A752 e A949 (horário) para o mesmo período.
4. Rodar `science_cli evaluate`: MAE/RMSE/viés por modelo e antecedência; matriz de contingência, POD/FAR/CSI/ETS em 0,1/1/5/10/20/50 mm (ETS a acrescentar em `metrics.py`), Brier e confiabilidade para Previous Runs transformados em evento; climatologia como referência para BSS.
5. Publicar apenas resultados com n ≥ 30 eventos por classe; classes raras (≥50 mm) ficam com aviso de amostra insuficiente.

## 4. Protocolo de validação (obrigatório para qualquer método)

- Divisão temporal: treino / calibração / teste em blocos cronológicos com purga ≥ maior antecedência (já implementado em `calibration.py`); depois **walk-forward** anual/safra (treinar até setembro, testar na safra seguinte).
- Referências: previsão original, climatologia (ERA5-Land 1991–2020 e observada), correção de viés simples, melhor modelo individual.
- Métricas pareadas no mesmo conjunto de casos; intervalos de confiança por bootstrap em blocos de 7 dias; nenhuma melhoria anunciada sem intervalo que exclua zero.
- Dependência entre modelos: avaliar misturas por centro (ECMWF, NOAA, DWD, ECCC, UKMO, Google) e com desduplicação (apenas um produto por centro).

## 5. Machine learning — ordem de tentativa

1. Viés aditivo/multiplicativo por mês e antecedência.
2. Regressão logística + isotônica para ocorrência (já no código); quantil mapping para quantidade.
3. GAM/regularizada com preditores disponíveis no instante da emissão: previsão de chuva do modelo, antecedência, mês, T, UR, VPD, pressão, vento, radiação, CAPE, chuva observada antecedente, membros (média, dispersão).
4. Só com ≥2 safras pareadas: Random Forest / gradient boosting (HistGradientBoosting já previsto; XGBoost/LightGBM se justificarem) para ocorrência e quantidade condicional, sempre contra as referências acima.

Critério de promoção: ganho fora da amostra em CRPS/Brier/MAE com intervalo que exclui zero em pelo menos duas safras e por horizonte; caso contrário permanece "experimento".

## 6. Dependências de dados

Sem observação confiável não há item 4 nem 5. A ação de maior retorno é administrativa: token INMET e confirmação da estação Embrapa. Com isso, a primeira verificação descritiva (Previous Runs × observação diária) pode sair em semanas; a verificação dos ensembles arquivados exige cerca de 90 dias de janelas.
