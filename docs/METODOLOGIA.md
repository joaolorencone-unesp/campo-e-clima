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

## v0.4 — joint-member meteorological screening (prototype)

- A API consulta especificamente `precipitation`, `temperature_2m`, `relative_humidity_2m`, `wind_speed_10m`, `wind_direction_10m` e `wind_gusts_10m` em uma chamada de **4 dias por modelo**. Somente membros com todos os seis campos **identificados pelo mesmo sufixo** e chuva completa nas 3 horas seguintes entram na triagem probabilística. A requisição original de chuva D0-D6 permanece separada.
- VPD calculado por membro a partir de `T` e `UR` pela equação da pressão de vapor de saturação de Tetens/FAO: `VPD = 0.6108*exp(17.27*T/(T+237.3))*(1-UR/100)` [kPa]. Não usar UR média ou temperatura de outro membro.
- Filtros experimentais de triagem: vento 3–10 km/h, rajada ≤25 km/h, T<30°C, UR≥55%, chuva no horizonte 3h ≤0,1 mm, VPD <1,2 kPa (herbicida), <1,4 (inseticida), <1,5 (fungicida). **São filtros de engenharia para demonstrar o software, não limites universais ou validados cientificamente para estas classes de produtos.** Os valores deverão ser substituídos por critérios dependentes do produto, formulação, gotas, equipamento, deriva e bula.
- Classes mutuamente exclusivas: `passa` (cumpre todos os filtros com margem), `marginal` (cumpre filtros mas próximo dos limites) ou `restrito` (viola ≥1 filtro). Nenhuma classe equivale a segurança garantida. Inversão, deriva para receptor e bula **não são verificadas**; classificação operacional permanece indeterminada.
- Frequências são calculadas por membro **conjunto**, dividindo igualmente o peso por modelo e por seus membros disponíveis. Para janelas de 2 horas, o **mesmo membro** deve cumprir a condição nas duas horas. Não multiplicar probabilidades horárias ou marginais.
- Contagens por hora e por categoria mostram amostras *conjuntas completas*, não contagens apenas da variável `wind_gusts_10m`. A disponibilidade de oito ensembles com rajadas não prova oito ensembles úteis para pulverização.
- Guia DJI Agras T100: especificação de resistência de vento <6 m/s da aeronave não equivale a limite seguro de deriva. Manual ressalta operação sob <3 m/s para produtos sensíveis à deriva/fitotoxicidade. Fontes: https://ag.dji.com/t100/downloads e https://www.dji.com/support/product/t100 .
- Segurança regulatória: https://www.gov.br/agricultura/pt-br/assuntos/insumos-agropecuarios/aviacao-agricola/fiscalizacao ; Portaria MAPA 298/2021. Verificar atualizações legislativas, regiões sensíveis e regras de rótulo/bula antes da aplicação.
- Revisão sobre deposição/deriva de gotas UAV: Qin & Chen (2023), Scientific Reports 13, 14935: https://www.nature.com/articles/s41598-023-40556-0 .
