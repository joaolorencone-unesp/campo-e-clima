# Campo e Clima v2.1 — especificação da Central Agro

**Escopo implementado:** assistência agrometeorológica transparente e retrospectiva recente por coordenada. Não há IA treinada, previsão própria nem calibração probabilística. É um motor de regras, desenhado para evoluir com registros observacionais.

## 1. Fontes e procedência

1. **Open-Meteo Forecast API (determinística):** previsão horária de temperatura, UR, VPD, vento a 10 m, rajadas a 10 m e precipitação. A origem e a idade da rodada são exibidas na interface. Não é medição da fazenda.
2. **Open-Meteo Ensemble API:** campos diários multimodelo já calculados no projeto para limiares >0,1 e >1 mm. Cada ensemble recebe peso total igual entre os modelos válidos. Não é frequência estatisticamente calibrada.
3. **Open-Meteo Forecast API `past_days=4`:** série diária recente **retrospectiva de modelo** para o ponto selecionado, sob demanda e cache de 30 min em memória. Dia atual é excluído. Não confundir com observações INMET/IFMS, NASA POWER ou ERA5. Respostas são validadas por coordenada e fuso horário.
4. **INMET, NASA POWER, ERA5, radar e outros produtos** continuam nas abas existentes, sem alteração do método da coleta.

### Fundamentação e manuais

- Open-Meteo Forecast: https://open-meteo.com/en/docs
- Open-Meteo Historical Weather: https://open-meteo.com/en/docs/historical-weather-api
- Open-Meteo Previous Runs: https://open-meteo.com/en/docs/previous-runs-api
- DJI Agras T100: https://www.dji.com/support/product/t100

## 2. Filtros numéricos experimentais (pulverização)

| Variável | Regra de triagem | Observação |
|---|---|---|
| Vento médio previsto a 10 m | 3 a 10 km/h | Não é vento medido à altura operacional |
| Rajada prevista a 10 m | ≤25 km/h | Não é limite de segurança aeronáutica |
| Temperatura | <30 °C | Condição prevista em grade |
| Umidade relativa | ≥55% | Condição prevista em grade |
| VPD | Herbicida <1,2 kPa; fungicida <1,5; inseticida <1,4 | Configurações experimentais, não valores universais |
| Chuva das 3 horas posteriores | ≤0,1 mm | Chuva horária em `t+1`, `t+2`, `t+3`, sem reutilizar `precipitation[t]` |

**Classes numéricas:** restrita (algum limite ultrapassado), indeterminada (falta ao menos uma variável crítica e nenhum filtro já é restritivo), marginal (próximo dos limites) ou passa filtros (todos os filtros numéricos atendidos). Mesmo a classe "passa filtros" tem **pendências operacionais obrigatórias**, inclusive verificações de inversão e deriva e exigências legais. A aplicação jamais é liberada automaticamente.

Para plantio, colheita e irrigação, a interface fornece observações preliminares distintas e não reaproveita os limiares de pulverização como regras operacionais universais.

## 3. Retrospectiva recente

- Consulta por localidade, não por município fixo: latitude e longitude selecionadas.
- Requisição feita **apenas ao abrir a Central Agro**; cache de 30 minutos por coordenada e botão para tentar atualização.
- Apenas datas anteriores à data local (fuso devolvido pela API) são mostradas, até quatro dias disponíveis.
- Precipitação, Tmin, Tmax e rajadas, sempre com rótulo de **modelo**.
- Null, arrays ausentes e resposta inconsistente não viram 0 mm. Erros são exibidos e uma resposta anterior em cache é explicitamente marcada como potencialmente antiga.
- Série não deve ser utilizada como referência independente para inferir habilidade preditiva. Para validação, obter observações verificadas de estações ou sensores e guardar previsões de rodadas anteriores.

## 4. Integridade por coordenada

Antes de renderizar as decisões horárias, coordenadas de `state.site` devem coincidir com o ponto atualmente selecionado. Isso impede a exibição de previsões da localidade anterior durante a troca de Naviraí → Diamantino. Requisições de retrospectiva em andamento são canceladas ao mudar coordenadas; respostas antigas não podem substituir as novas.

## 5. Próximas evoluções (ainda NÃO implementadas)

- Coleta histórica incremental de estações verificadas, com proveniência por estação e data de atualização.
- Verificação de previsões e mapas de confiabilidade por horizonte de emissão, com Brier Score, MAE, RMSE, CRPS e diagramas de confiabilidade.
- Camadas futuras de chuva em resolução nativa de GFS/ECMWF, em vez de colorir nove pontos como se houvesse resolução espacial detalhada.
- Sequências GOES-19 georreferenciadas, sujeitas a termos de acesso, processamento e licenças dos fornecedores.
- Planejamento de pulverização com bula, classes de gota, áreas sensíveis georreferenciadas, medições in situ e validação de deriva. Sem recomendações automáticas de altura de voo antes de evidência experimental.
- Revisão formal de uso gratuito/licenciamento antes de escala comercial.
