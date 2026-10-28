# Campo e Clima v1.9 — mapa, avisos, histórico diário e painel mais legível

**Data:** 28/10/2026. **Ponto padrão:** Naviraí–MS (−23,065; −54,190; UTC−4).

## 1. Melhorias implementadas

### Avisos oficiais do INMET

- Exibe um resumo com a quantidade de avisos retornados para o município **confirmado no coletor**.
- Avisos com mesmo fenômeno, severidade e texto de riscos são **agrupados apenas visualmente**. A lista oficial individual, suas datas e seus horários de origem permanecem acessíveis em `<details>`.
- Agrupar não transforma avisos distintos num único aviso; também não significa continuidade ininterrupta entre as vigências.
- Erros técnicos HTTP / JSON das leituras S735 não são despejados na interface principal, mas o serviço continua identificado como **não confirmado** e pode ser investigado nas fontes oficiais.
- Para localidade diferente de Naviraí, a seção de avisos municipais específicos permanece oculta. Não extrapolar alertas municipais a outras coordenadas.

### Mapa meteorológico e radar

- A grade Open-Meteo de nove pontos é exibida como **círculos amostrais**, sem quadrados preenchendo uma área contínua. Os círculos **não** são interpolação de alta resolução nem radares.
- Nova seleção de **radar observado RainViewer (últimas ~2h disponíveis)**, com quadros, data/hora local, reprodução e atualização com limitação de frequência. A API gratuita atual aceita apenas quadros **passados**; não é nowcasting e não oferece previsão futura.
- RainViewer: `https://api.rainviewer.com/public/weather-maps.json` (metadados). As imagens dependem da cobertura e do uso permitido pela fonte. O navegador usa tiles providos pelo próprio serviço. A animação é lenta, de propósito, para respeitar a modalidade gratuita e reduzir consumo. **Não presumir cobertura do radar no interior do MS.**
- Links para os produtos oficiais INMET/DECEA, INMET satélite e CPTEC/INPE. Como acesso e licenciamento variam, a v1.9 **não reproduz nem redistribui automaticamente imagens oficiais do INMET/DECEA**.
- NASA MODIS/VIIRS permanece disponível como **imagem de observação de passagem orbital**, sem confusão com quadros de radar ou nuvens previstas.

### Histórico automático (Naviraí)

- Novo script: `python -m scripts.collect_history_v19`.
- GitHub Actions coleta, no máximo uma vez ao dia local (com cache), uma **série móvel de 90 dias** de:
  - ERA5 via Open-Meteo Historical Weather API (`precipitation_sum`, `temperature_2m_mean`);
  - NASA POWER (`PRECTOTCORR`, `T2M`, `time-standard=UTC`).
- Os últimos sete dias são excluídos da consulta por possível atraso do produto reanalisado; a janela consultada termina em **D−7**.
- Publicação automática no `site/data/history_navirai.json`, **desde que a coleta seja executada no GitHub Actions**. Na primeira implantação, o arquivo pode ainda não existir ou conter uma falha; sua ausência é explicitamente informada no painel.
- Tabela e gráfico com chuva diária de **duas fontes separadas**, datas UTC alinhadas e `—` para valores ausentes. Nunca substituir ausente por 0 mm. Os resultados não são medições de estação nem avaliação de acurácia.
- Cache de coleta é restaurado entre builds usando `actions/cache`. Um último sucesso pode ser publicado como **desatualizado** quando houver falha. O histórico por coordenada personalizada já disponível no navegador foi preservado; a série pré-coletada é exclusiva de Naviraí.
- **Não** foram automatizadas observações certificadas INMET S735 nem a exportação IFMS/Embrapa por falta de um endpoint validado com dados reais e identificação inequívoca da estação. O INMET possui recursos oficiais de dados históricos, mas acesso, distribuição e formatos precisam ser confirmados caso a caso.

### UI e confiabilidade

- A aba **Máquinas & solo** foi retirada da navegação principal e mantida no código como módulo de pesquisa não calibrado. Não possui indicador validado de trafegabilidade.
- Falha ECMWF EC46/SEAS5 passa a ser mostrada resumidamente no calendário/aba estendida; o motivo técnico detalhado permanece na aba **Qualidade & fontes**.
- Nenhuma nova chamada pesada aos oito ensembles foi adicionada; lógica das frequências >0,1 mm, >1 mm e pulverização foi preservada.
- Nenhuma chave privada é embutida em HTML/JS/Python. A chave do OpenWeather enviada em conversa anterior **não deve ser reutilizada**. Rotacione e configure exclusivamente `OPENWEATHER_FREE_API_KEY` como GitHub Actions Secret, limitado ao endpoint gratuito de cinco dias/três horas.

## 2. Limitações e verificações de primeira publicação

1. Conferir no GitHub Actions se as etapas **Unit tests**, **INMET groups and radar controls regression** e **Refresh Naviraí gridded history** concluíram. Etapa de histórico é `continue-on-error`, logo um workflow verde sozinho não comprova que os dados históricos estão presentes.
2. Confirmar que `site/data/history_navirai.json` tenha `state=ok`, fonte, datas UTC e números de dias válidos, ou o erro devidamente identificado.
3. Abrir **Mapas & nuvens**, escolher `Radar observado`, clicar em **Atualizar quadros** e confirmar se houve resposta. A cobertura brasileira pode ser parcial, ausente ou atrasada.
4. Ao trocar de localidade, verificar que observações e avisos de Naviraí não apareçam como dados da nova coordenada.
5. Depois de publicar, usar Ctrl+F5 se houver cache do navegador.
6. Validar em telas desktop/mobile reais; o ambiente de produção de artefatos não conseguiu abrir Chromium local por bloqueio administrativo. Scripts e marcação estão testados, mas a experiência visual interativa e os endpoints reais precisam ser verificados após publicação.

## 3. Próximas etapas de ciência dos modelos

**Sem promover frequências brutas a probabilidades calibradas.** Antes de incluir novos modelos, armazenar previsões por emissão e antecedência e observações verificadas, pareadas por timestamp, resolução, fuso e localização. Gerar uma base de pares `forecast_issued_at`, `valid_at`, `lead_hours`, `model`, `member`, `latitude`, `longitude`, `threshold_mm`, `observed_mm`, `source_quality`. Preservar arquivos de forma durável além da retenção de 90 dias de GitHub Actions.

**Comparar baselines e pós-processamento por horizonte:** mistura com pesos iguais (referência), modelo individual, climatologia local, persistência, regressão logística e EMOS/BMA para chuva intermitente (massa de probabilidade em zero + intensidade assimétrica). Usar validação temporal retroativa de origem móvel (*rolling-origin*) e impedir vazamento de safras/estações e rodadas futuras. Métricas sugeridas: Brier Score e diagramas de confiabilidade para >0,1, >1, >5, >10, >20 mm em 1/3/6/24 h; CRPS para a distribuição; MAE/viés de acumulados; CSI/POD/FAR para eventos; Brier Skill Score contra climatologia, com intervalos de confiança por bloco temporal. Amostra mínima e dependência entre ensembles devem orientar qualquer peso diferente de 1/N.

**Previsão estendida:** manter as previsões de 15–35 dias do GEFS claramente como um único ensemble e EC46/SEAS5 como **anomalias e tendências semanais/mensais** quando disponíveis, não como chuva exata por dia. O valor de acrescentar outro modelo deve ser demonstrado por ganho de habilidade em validação independente, não pela contagem total de membros.

### Fontes técnicas e estudos

- Open-Meteo Historical Weather API: https://open-meteo.com/en/docs/historical-weather-api
- Open-Meteo Ensemble API: https://open-meteo.com/en/docs/ensemble-api
- Open-Meteo Seasonal EC46/SEAS5: https://open-meteo.com/en/docs/seasonal-forecast-api
- NASA POWER REST: https://power.larc.nasa.gov/docs/services/api/
- RainViewer Maps e restrições 2026: https://www.rainviewer.com/api/weather-maps-api.html ; https://www.rainviewer.com/api/transition-faq.html
- INMET: https://portal.inmet.gov.br/servicos/esta%C3%A7%C3%B5es-autom%C3%A1ticas ; https://portal.inmet.gov.br/servicos/produtos-de-imagens-de-sat%C3%A9lite
- Gneiting, Sloughter & Raftery (2006), *Probabilistic Quantitative Precipitation Forecasting Using Bayesian Model Averaging*: https://stat.uw.edu/research/tech-reports/probabilistic-quantitative-precipitation-forecasting-using-bayesian-model-averaging
- Raftery et al. (2005), *Using Bayesian Model Averaging to Calibrate Forecast Ensembles*: https://doi.org/10.1175/MWR2906.1
- Catão et al. (2026), *Precipitation nowcasting of satellite data using physically aligned neural networks*: https://www.cambridge.org/core/journals/environmental-data-science/article/precipitation-nowcasting-of-satellite-data-using-physically-aligned-neural-networks/612E7BB69D05775215399DB33BB70103

As publicações demonstram métodos e potenciais aplicações. Não comprovam, por si só, ganho de acurácia do Campo e Clima em Naviraí.
