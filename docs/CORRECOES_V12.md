# Campo e Clima v1.2 — correção da restrição de pulverização, histórico e tendência estendida

Data: outubro de 2026. Projeto experimental. Sem APIs pagas e sem credenciais no código.

## 1. Por que o gráfico de pulverização fica vermelho?

**Vermelho = membro restrito por pelo menos um dos filtros meteorológicos configurados**, não é probabilidade calibrada de acidente, deriva ou falha de aplicação. A nova seção «Por que a pulverização está restrita? Consulte cada hora» permite selecionar 1 hora e visualizar os fatores e suas frequências conjuntas ponderadas por modelo: chuva acumulada nas 3 horas posteriores (t+1…t+3), vento, rajadas, UR, VPD e temperatura. Fatores podem ocorrer simultaneamente no mesmo membro; por isso percentuais das causas não devem ser somados. Exibir também percentual marginal, passa filtros e indeterminado. Horas noturnas com estabilidade/inversão não observadas permanecem indeterminadas, não «ótimas».

## 2. Histórico: por que a versão anterior mostrava 0,0 mm indevidamente?

O script anterior aceitava HTTP 200 com **todos os valores de chuva nulos** da consulta ERA5-Land. A API Historical Weather distingue a oferta de variáveis por modelo. Nesta versão:

- Chuva, temperatura e vento de base: `models=era5`, calendário diário `timezone=UTC`, para comparação NASA POWER em dias UTC. ERA5 ~0,25°.
- Rajadas e ET₀ complementares: `models=era5_land`, grade ~0,1°; os campos só são incorporados se houver datas e números válidos alinhados exatamente.
- Para triagem retrospectiva, os elementos horários atmosféricos vêm de ERA5 com complemento de rajadas de ERA5-Land. Sem vento/rajada/chuva do mesmo horário → indeterminado, nunca favorável.
- Se a resposta contiver chuva inteiramente nula, mostrar falha, não «0 mm» e «0 dias com chuva».
- São **reanálises em grade**, não medições no talhão. O registro Embrapa/IFMS ainda exige confirmação do identificador da estação na exportação original. NASA POWER e ERA5 são estimativas potencialmente correlacionadas.
- ERA5 e ERA5-Land têm atrasos de publicação, portanto os últimos dias podem não constar no histórico. Não preencher ausências com previsão atual.

## 3. Tendência de 15–60 dias

A consulta antiga transferia **51 membros × 60 dias × 4 valores/dia** e falhava por timeout. Mudamos para a API `seasonal-api.open-meteo.com/v1/seasonal`, `models=ecmwf_seasonal_ensemble_mean_seamless`, campos **`weekly=precipitation_mean,precipitation_anomaly,temperature_2m_mean`** e **`monthly=precipitation_mean`**, horizonte de 63 dias. Isto permite tendências semanais/mensais de dados efetivamente retornados com unidades provenientes dos metadados. EC46 até 46 dias, SEAS5 meses posteriores, ~36 km. **Média do ensemble não é P10/P90, previsão diária, nem probabilidade calibrada.** Para qualquer coordenada escolhida, o site oferece consulta leve personalizada; se não houver resposta, exibe indisponibilidade. Na sede Naviraí, o Actions também tenta o produto uma vez ao dia. O calendário de dias continua sem dados inventados além do horizonte determinístico.

### Verificação de deploy

- Atualizar todos os arquivos do ZIP no repositório, inclusive `.github/workflows/pages.yml` e novo `site/static/extended_v12.js`.
- Em **Actions**, abrir a execução e confirmar `Unit tests` e `Collect forecasts` e publicação bem-sucedidos.
- No painel, **Ctrl+F5**, selecionar horário no diagnóstico de pulverização, abrir «Histórico & indicadores» e verificar valores *numéricos* de chuva; abrir «30–60 dias» e confirmar horário/unidade do produto estendido.
- Um job verde significa que o site foi publicado; não que cada serviço respondeu. Inspecionar `latest.json` → `complementary.ecmwf_extended` e também status no navegador.
- Quando um produto continuar indisponível, não dar como resolvido: anotar mensagem de erro, endpoint, horário e fuso (sem segredos), antes de ajustar o conector.

## 4. Outras fontes: próximo trabalho

- **INMET S735**: catálogo de estação confirmável; leituras oficiais por API podem ser bloqueadas/retornar 404. Solicitar acesso institucional e/ou importar arquivo anual do INMET; dados a 37,6 km não substituem sensor de talhão.
- **CPTEC/INPE**: previsão qualitativa e avisos já complementam; integração automática de radar, GOES-19 e raios exige cobertura, carimbo temporal e licença verificáveis.
- **Embrapa Guia Clima Naviraí**: confirmar a estação no arquivo exportado e auditar os 694 dias; só então habilitar validação de acurácia.
- **SoilGrids**: WCS/Earth Engine, não a API REST interrompida.
- **NASA POWER**: já fornece histórico para coordenadas; a comparação com ERA5 é concordância entre produtos, não medida de acerto.

**Principais fontes**: https://open-meteo.com/en/docs/historical-weather-api ; https://open-meteo.com/en/docs/seasonal-forecast-api ; https://open-meteo.com/en/docs/ensemble-api ; https://portal.inmet.gov.br/ .
