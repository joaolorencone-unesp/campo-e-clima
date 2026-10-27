# Campo e Clima v1.4 — Mapas, nuvens e vento

## Fontes e escopo

Esta edição adiciona uma nova seção **Mapas & nuvens** para qualquer coordenada selecionada na interface. Nenhum serviço é pago e nenhuma credencial foi incluída.

| Informação | API/fonte | Natureza | Cobertura e atualização |
|---|---|---|---|
| Nuvens totais/baixas/médias/altas | Open-Meteo Forecast API (`cloud_cover`, `cloud_cover_low`, `cloud_cover_mid`, `cloud_cover_high`) | Previsão em grade, não observação | 9 amostras a ±0,4° em torno do ponto, até 48 horas; consultada sob demanda; cache local de até 2h |
| Precipitação | Open-Meteo Forecast (`precipitation`) | Previsão horária modelada | Mesmo grade e período. Valores horários podem ser interpolados do modelo nativo |
| Vento e direção | Open-Meteo Forecast (`wind_speed_10m`, `wind_direction_10m`) | Previsão horária modelada | Setas mostram **para onde** sopra (rumo oposto à direção meteorológica de origem) |
| Imagem orbital em cor natural | NASA Earthdata GIBS WMTS, MODIS Terra ou VIIRS NOAA-20 | Imagem observada, **não previsão de nuvens** | Seleção explícita da data UTC. Mosaicos dependem de passagem orbital, processamento e cobertura; alguns dias não têm mosaicos válidos para o ponto |
| Cartografia de base | OpenStreetMap standard raster tiles | Geografia, não meteorologia | Apenas requisições do usuário, sem pré-busca nem download em massa; atribuição visível |
| GOES-19 | CPTEC/INPE DSAT | **Link externo** | Imagens geoestacionárias públicas, sem incorporação direta: a reprodução está condicionada à autorização do INPE |
| GPM/IMERG | NASA GPM | **Link externo** | Produto de precipitação por satélite: estimativa, não pluviômetro nem previsão. Dados brutos autenticados exigem processamento posterior |

## Endpoints sem API key

- NASA GIBS: `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/` (WMTS de imagem orbital, parâmetros `layer`, `date`, `tilematrix`, `x`, `y`).
- Open-Meteo: `https://api.open-meteo.com/v1/forecast` (múltiplas latitudes/longitudes, `timezone=UTC`, `forecast_hours=48`).
- Documentação NASA: https://nasa-gibs.github.io/gibs-api-docs/access-basics/
- Open-Meteo Forecast: https://open-meteo.com/en/docs
- INPE DSAT: https://www.cptec.inpe.br/dsat/
- NASA GPM: https://gpm.nasa.gov/data/visualization
- OSM: https://operations.osmfoundation.org/policies/tiles/

## Notas científicas importantes

1. O **mapa de previsão** é uma malha de nove amostras pontuais com células apenas ilustrativas. Não significa resolução meteorológica de 0,4° ou pixels reais do modelo.
2. A evolução horária não é uma previsão do deslocamento exato de cada nuvem. O modelo prevê **percentuais de cobertura de nuvens** em cada amostra e instante.
3. A imagem NASA está datada, mas seu horário de observação local **não é verificado** pela aplicação. Não serve como nowcast convectivo de alta frequência ou substituto de radar/GOES.
4. Direção meteorológica é origem; transporte simplificado: `(direcao_de_origem + 180) % 360`. Isso não mede deriva real; exige sensores locais, contexto topográfico e avaliação de estabilidade.
5. As camadas de satélite são carregadas **somente quando selecionadas**; não se pré-baixam mosaicos. O usuário pode desativá-las e usar apenas as previsões.
6. Se a Open-Meteo não retornar um ponto/variável/horário, a célula fica sem valor. Nunca preencher ausência com zero ou céu limpo.
7. Se ocorrer HTTP 429 ou bloqueio de rede, não insistir em laço. O usuário verá a falha e poderá abrir as fontes oficiais. Consultas são feitas somente ao abrir a aba (cache 2h) ou pelo botão (limitado a 3 minutos entre tentativas).
8. Os dados em grade são úteis para planejamento **regional**, mas não constituem medição de vento ou autorização de pulverização no talhão.

## Próxima etapa

- Mapa de chuva observada por NASA IMERG, com ingestão autenticada Earthdata segura, processamento raster, hora validada e controle de latência; sem colocar token Earthdata no frontend público.
- Adição de radar/GOES apenas por serviços com metadados de horário, georreferenciamento e autorização de redistribuição.
- Relatórios de acurácia para vento e chuva usando medições e previsões arquivadas.
