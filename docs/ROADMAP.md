# Roteiro de desenvolvimento e validação

## P0 — publicar MVP e auditar as fontes
- [x] Estrutura dos arquivos, docs, código-fonte inicial e testes
- [x] Página inicial em abas, com transparência e botão de atualização
- [x] Coletor Open-Meteo Forecast e oito ensembles de precipitação diária
- [ ] Conceder permissão de escrita à integração GitHub e publicar arquivos
- [ ] Ativar GitHub Pages, executar e conferir GitHub Actions
- [ ] Confirmar variáveis e quantidade de membros reais da API em execução

## P1 — tornar operacional chuva e vento (0–72h)
- [ ] Observações históricas/a cada hora: Embrapa e INMET, com QA/QC
- [ ] Alertas INMET vigentes com Naviraí no recorte oficial
- [ ] Radar/satélite/raios INPE com hora e cobertura confirmadas
- [ ] Precipitação por 1/3/6/12/24h e rajadas máximas por membro
- [ ] Gráficos de chuva, vento e cenários e risco de extremos

## P2 — validação empírica e aperfeiçoamento D0–D14
- [ ] Armazenamento durável das previsões emitidas e observações
- [ ] Backtesting e comparação: climatologia, melhor único modelo, blend de peso igual
- [ ] Brier, confiabilidade, CRPS, MAE; intervalos de confiança e regimes sazonais
- [ ] Calibração temporal sem vazamento; ponderação orientada por skill

## P3 — recomendações agrícolas com rastreabilidade
- [ ] Pulverização: DJI T100, bula, classes de gotas, alvo, deriva, inversão e meteorologia no talhão
- [ ] Trafegabilidade: solo SoilGrids, água do solo, estado de superfície, ensaios e tipo de máquina
- [ ] Probabilidade conjunta do mesmo membro, nunca produto de marginais

## P4 — extensão científica e escala
- [ ] Produtos subsazonais/estendidos em escala semanal para 15–60 dias
- [ ] Histórico da previsão realizada versus observada, scorecards de desempenho
- [ ] Integrações OpenWeather autorizadas, imagens com licença, alertas e e-mail

**Etapa de aprovação:** cada módulo precisa funcionar em dados recentes, declarar lacunas e ser comparado com referência observacional antes de receber selo de confiança.
