# Calibração experimental

M0: climatologia estimada no treinamento. M1: determinístico original. M2: ensemble bruto, com identificação e pesos. M3: viés, regressão linear/Ridge para temperatura e velocidades; logística + isotônica para ocorrência de chuva e Ridge log1p para quantidade condicional em casos chuvosos. M4: Gradient Boosting para variáveis contínuas. Gradient Boosting de ocorrência ainda não foi incluído no experimento de chuva.

Nenhum método substitui a previsão principal. Ensaios usam apenas a previsão disponível como atributo; não usam observação futura, reanálise posterior ou previsão futura como feature. Dados de estação permanecem alvos/referências.

Divisão cronológica 60/20/20 por instantes únicos, com lacuna pelo menos 7 dias ou o maior horizonte do grupo. Uma rodada não pode atravessar blocos. Uma observação de treinamento com disponibilidade conhecida posterior à origem de teste é rejeitada. A política inicial exige 90 dias distintos e no mínimo 200/50/50 pares em treino/calibração/teste; limiar conservador experimental, não análise de poder estatístico. Ocorrência exige pelo menos 20 eventos e 20 não eventos nos blocos de ajuste. Isotônica usa somente calibração, nunca teste. Probabilidades são projetadas por PAVA para a sequência decrescente [0,1].

`python -m scripts.science_cli train --db runtime/science_rebuilt.sqlite` registra também ausência de dados. Nenhum modelo real foi treinado nesta entrega; não existe amostra observacional suficiente. O teste de software de ajuste usa fixture sintética, isolada dos dados públicos.

Ainda pendentes para promoção: walk-forward múltiplo, incerteza por blocos temporais, robustez por estação, comparação justa em amostra comum, avaliação agronômica e artefatos completos de modelos treinados reais. Nenhum intervalo de confiança foi inventado.
