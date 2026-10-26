# Metodologia científica (plano experimental)

## Tese operacional
Mais modelos NÃO significam automaticamente maior exatidão. Acurácia deve ser medida por variável, horizonte, época do ano e evento, confrontando previsões que estavam realmente disponíveis antes da observação.

## Forecast versus ensemble
- 0–72 horas: integrar observações, previsões horárias determinísticas e incerteza ensemble. Separar **observação** de **previsão**.
- 4–14 dias: quantis e frequências conjuntas de extremos meteorológicos.
- 15–60 dias: somente produtos subsazonais/sazonais em escalas semanais e quinzenais, com baixa previsibilidade diária.

## Ensemble multimodelo
A primeira versão usa peso total igual por cada **modelo válido**. Para um limiar `z`: `P(X>z) = (1/M) Σ_m (1/n_m) Σ_k I(x_mk>z)`. Quantis são calculados sobre a distribuição **dos membros ponderados**, não pela média dos quantis dos modelos. A versão atual calcula chuva diária; produtos 1h/3h/6h/12h e rajadas por membro, com controle de resolução nativa, são próximos passos. Modelos institucionalmente correlacionados (ECMWF IFS/AIFS, GEFS/AI-GEFS) requerem sensibilidade por centro, sem contar aliases como modelos novos.

**Frequência bruta não é probabilidade calibrada.** Calibração depende de estações auditadas e avaliação prospectiva/hindcast temporal; usar Brier Score e diagramas de confiabilidade para eventos, CRPS para distribuição, MAE/RMSE/bias para variáveis contínuas, com baseline climatológico e melhor modelo isolado. Testar EMOS/isotônica apenas depois de observações suficientes. O código de verificação atual só fornece componentes básicos e não demonstra skill.

## Observações
Embrapa Guia Clima Naviraí `cod_estacao=6`, estação reportada próxima a -23.025833,-54.189444. Fazer auditoria de período, sensores, escala de chuva, dias faltantes, mudanças e anemômetro; comparar também INMET e estação em propriedade. Uma observação diária não valida diretamente uma previsão horária. Guarda de arquivo bruto, origem, hora de emissão e coordenada da grade é essencial.

## Pulverização com drones
Limites de triagem como vento 3–10 km/h, UR>55%, T<30°C são **orientativos**, não autorizam aplicação. Considerar manual e configuração do **DJI Agras T100**, produto/bula, estabilidade/inversão, classe de gotas, altura, deriva/volatilização, direção e proximidade de alvos sensíveis, proteção dos polinizadores e restrição de chuva posterior. Cálculo de adequação probabilística exige avaliar condições conjuntas **do mesmo membro** e não multiplicar probabilidades marginais; não avaliar inversão se não houver dados. Sem observação no talhão, classificar como **indeterminado** em vez de seguro.

## Trafegabilidade agrícola
SoilGrids oferece atributos quase estáticos como argila, silte, areia e densidade. A condição operacional depende de **água atual do solo**, chuva recente e prevista, drenagem, compactação, resistência do solo, declividade e tipo/carga de máquina. SMAP, ERA5-Land e modelos de umidade oferecem estimativas de grade; calibrar com sensores e ensaios de resistência à penetração antes de liberar tráfego.

## Publicação e auditoria
O site informa coleta, modelo, unidade e valores disponíveis; não fabricará radar, alertas ou dados de 30–60 dias. APIs podem mudar variáveis, nomes e limites; testes de contrato são necessários.
