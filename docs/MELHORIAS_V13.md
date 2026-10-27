# Campo e Clima 1.3 — estabilização de dados e horizonte estendido

**Local padrão:** Naviraí–MS; coordenadas −23,065, −54,190; America/Campo_Grande (UTC−4).
**Público-alvo:** pesquisa agrometeorológica e planejamento agrícola, sem autorização automática de pulverização.

## Modificações implementadas

1. **ECMWF sazonal sem consultas repetidas do navegador.** A aba estendida lê exclusivamente `data/latest.json` publicado. O backend consulta o ECMWF uma vez por semana, com cache semanal pelo GitHub Actions. A resposta HTTP 429 ou timeout fica identificada como falha; não é interpretada como tempo seco. O botão foi renomeado para **Verificar coleta publicada**.
2. **GEFS D15–D35 (experimental).** A rotina `scripts/sources/gefs_extended.py` consulta um único ensemble NOAA GEFS por dia no modelo `ncep_gefs_seamless` solicitando `daily=precipitation_sum` e horizonte de 35 dias. São calculados P10/P50/P90 e frequência de excedência >5 e >10 mm/dia **somente** com membros diários válidos. Se o modelo não retornar a amostra, o produto fica indisponível. Não extrapolar nem recalibrar a partir de um único modelo.
3. **Calendário honesto.** Mostra datas com previsão determinística e, se houver, GEFS a partir de D15. Datas sem produto não geram cartões vazios. O quadro indica quantas datas possuem dados, sem inventar previsão diária para EC46/SEAS5.
4. **Histórico com recuperação de falha.** Valida precipitação numérica ERA5, tenta o produto `best_match` documentado em caso de série nula, e permite conservar temperaturas quando a chuva segue ausente. A NASA POWER pode fornecer **uma série separada explicitamente identificada** de precipitação quando ERA5 não retornar valores. Não há mistura silenciosa de NASA com ERA5 em uma única série; dias sem valor continuam ausentes. Todas são estimativas em grade, não pluviômetros.
5. **Pulverização mais explicável.** Um destaque identifica o período e a hora com maior frequência de restrição e lista os três fatores limitantes principais. O painel informa modelos e membros completos; motivos simultâneos não devem ser somados. A análise permanece uma *pré-triagem meteorológica* por hora, sem probabilidade calibrada de aplicação segura.
6. **Fallback de ensembles com timeout.** A primeira consulta de 7 dias inclui chuva e rajadas. Se exceder o timeout, realiza apenas **uma** tentativa limitada a 4 dias de precipitação. Registra a cobertura parcial e não fabrica rajadas. Erros HTTP 429 não geram tentativa imediata.
7. **Navegação:** abas passam a quebrar linha em telas largas, eliminando rolagem horizontal desnecessária no desktop.

## Fontes gratuitas

- Open-Meteo Forecast: https://open-meteo.com/en/docs
- Open-Meteo Ensemble: https://open-meteo.com/en/docs/ensemble-api
- Open-Meteo Historical Weather: https://open-meteo.com/en/docs/historical-weather-api
- Open-Meteo Seasonal: https://open-meteo.com/en/docs/seasonal-forecast-api
- NASA POWER: https://power.larc.nasa.gov/
- INMET: https://portal.inmet.gov.br/

Sem assinatura One Call nem serviços com cobrança por excedente. Respeite os termos e limites da Open-Meteo, especialmente uso não comercial e custo computacional de consultas extensas.

## Verificações realizadas

- Testes Python: 73 aprovados no ambiente local.
- Testes Node: `frontend_smoke.cjs`, `test_v12_browser.cjs`, `test_history_v10.cjs` e `test_location_client.cjs` aprovados.
- Sintaxe JavaScript: verificada.

**Não foi possível validar os retornos reais dos novos endpoints nesta execução local.** A primeira execução GitHub Actions após o envio deve confirmar GEFS >D14, histórico por coordenada, e o cache semanal ECMWF. Um workflow verde não é prova de funcionamento de cada fonte: confirme o status detalhado em `data/latest.json` e no painel.

## Melhorias pendentes

- Acurácia calibrada por observações INMET/Embrapa verificadas e previsões arquivadas por rodada.
- Acesso operacional confiável às leituras horárias da estação INMET S735.
- Forecast D15–D35 personalizado para qualquer coordenada com infraestrutura de backend/cache por localidade; o site estático não usa a previsão de Naviraí em pontos diferentes.
- Observação local para vento na altura operacional, estabilidade/inversão e deriva de pulverização.
- Monitoramento validado de radar/raios e satélite com timestamps.
