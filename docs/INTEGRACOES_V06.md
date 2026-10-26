# Plano de integração de fontes — Campo e Clima v0.6

**Sede:** Naviraí–MS, -23.065/-54.190, `America/Campo_Grande` UTC−4. **Coleta:** GitHub Actions a cada ~30min, sem SLA. **Data:** 26/10/2026.

## O que entra de verdade na v0.6

| Fonte | Produto e método | Estado no código | Precisa do usuário? | Quando atualizar |
|---|---|---|---|---|
| Open-Meteo Forecast | T, UR, chuva, vento, VPD, pressão, D0–D13 | Já operacional v0.5 | Não, respeitar os termos de uso | ~30min |
| Open-Meteo Ensemble | 8 ensembles, quantis/membros, precipitação, rajadas, cenários conjuntos de pulverização quando disponíveis | Já operacional v0.5 | Não; verificar disponibilidade por membro | ~30min |
| INMET avisos | Alertas com cobertura **IBGE 5005707** confirmada | Já implementado v0.5; conferir produção | Não | ~30min |
| INMET estações | Catálogo e amostra diária vizinha quando operante e API acessível | Já implementado v0.5; conferir produção | Não | ~30min |
| Embrapa Guia Clima | **694 linhas 01/12/2024–25/10/2026**, chuva/T/UR/vento/ET0/radiação, 6 linhas anteriores isoladas | **Importação concluída como PROVISÓRIA** | **Confirmar no portal que a exportação é da estação Naviraí/IFMS nº6** | Nova exportação periodicamente; leitura automática depende de API/permite extração |
| CPTEC/INPE XML | Previsão textual independente D0–D6 (categoria, Tmin/Tmax); não retorna probabilidade de chuva neste produto | Conector novo, parser com validação de município/atualização | Não; HTTPS pode falhar; verificar Actions | ~30min |
| OpenWeather One Call 3.0 | Previsão alternativa D0–D7/8, `pop`, rain, T; **não adicionar como membro do ensemble** | Conector novo | **Chave e acesso One Call 3.0**; secret `OPENWEATHER_API_KEY` | ~30min se contratado |
| Open-Meteo solo | Umidade volumétrica modelada e ET0 em grade; comparação, **não trafegabilidade calibrada** | Conector novo com dois fallbacks | Não; variável/modelo pode não estar disponível | ~30min |
| NASA POWER | Estimativa diária em grade (PRECTOTCORR) para comparação, não pluviômetro | Conector novo + cache por dia no Actions | Não para dados abertos, sujeitos a limites | 1x/dia |
| ECMWF EC46/SEAS5 via Open-Meteo Seasonal | 51 membros (se disponíveis), totais semanais P10/P50/P90 D14–D55; sem previsão diária fictícia | Conector novo + cache por dia no Actions | Não para uso não comercial conforme termos, conferir disponibilidade do modelo | 1x/dia |
| INPE GOES-19/DSAT | Visualizador público de satélite | Link oficial e status; **pixels não integrados automaticamente** | Definir camada/TMS documentada, atribuição, hora, geografia e atualização | Até 10–30min após validado |
| CPTEC radar/raios | Radar e raios sobre Naviraí | **Não integrados numericamente**: falta endpoint/licença atual verificável | Confirmar acesso/restrições de rede | Nowcast frequente se disponível |
| NASA GPM/IMERG | Chuva por satélite 0,1°, atraso Early/Late/Final | Documentação e status; sem dados numéricos | Conta Earthdata/PPS, autenticação e processamento espacial | 4–24h depois, conforme produto |
| ISRIC SoilGrids | Textura, argila, densidade e retenção estáticas | REST temporariamente suspensa; alternativa WCS/Earth Engine pendente | Para GEE: autenticação/projeto; WCS requer processamento GeoTIFF | Baixa frequência (p.ex. mensal) |
| CEMADEN | Pluviômetros da rede, quando disponíveis | Não integrado: API pública estável, cobertura e política a confirmar | Confirmar fonte endpoint e estação no raio | 10–60min conforme dados |

## Documentação confiável
- Embrapa: https://www.cpao.embrapa.br/gc/busca-de-dados
- INMET: https://portal.inmet.gov.br/ ; https://apiprevmet3.inmet.gov.br/avisos/ativos
- CPTEC XML: https://servicos.cptec.inpe.br/XML/
- CPTEC/INPE DSAT: https://www.cptec.inpe.br/dsat/
- Open-Meteo: https://open-meteo.com/en/docs/ensemble-api ; https://open-meteo.com/en/docs/seasonal-forecast-api
- OpenWeather: https://openweathermap.org/api/one-call-3
- NASA POWER: https://power.larc.nasa.gov/docs/services/api/temporal/daily/
- NASA IMERG: https://gpm.nasa.gov/data/imerg
- ISRIC: https://docs.isric.org/globaldata/soilgrids/

## Por que 694 dias de Embrapa não são ainda observações *verificadas de Naviraí*?
O arquivo enviado se chama `busca-dados.xls` mas é HTML tabular. Tem **700 datas únicas**, sendo seis anteriores a **01/12/2024**. O corpo exportado **não contém nome/código da estação selecionada**. Para impedir atribuição equivocada, o script `scripts/sources/embrapa_export.py` coloca esses seis dias em quarentena e salva 694 dias consecutivos em `data/observacoes/embrapa_exportacao_provisoria.csv`. O painel sinaliza a pendência sem inventar localização.

**Para certificar:** retornar à página oficial da Embrapa, selecionar explicitamente Naviraí/IFMS (código 6), conferir a tabela/estação, salvar evidência de seleção; comunicar a confirmação. Então, uma atualização posterior poderá marcar a série como verificada por origem (ainda sujeita a QA de sensores).

## Agendamento correto
O GitHub Pages é estático: o botão “Atualizar” relê a coleta publicada, não chama o servidor. O Actions continua agendado ~30min. A cada dia, um cache de `actions/cache` keyed pela data de Naviraí evita baixar repetidamente NASA POWER e EC46/SEAS5.

O acesso gratuito da Open-Meteo tem limites e condições de uso não comercial. Para uma plataforma com muitos municípios/alto tráfego ou distribuição comercial, avaliar licenciamento, orçamento e banco de dados dedicado.

## Dados de validação científica
Guardar `issued_at`, `valid_at`, membro/modelo, grade, timezone, versão da metodologia, erro de aquisição e fonte. Comparar contra observações **independentes**, não reanálises de modelos usadas como dados observados. Para chuva: Brier/BSS por limiar, CRPS, reliability, bias de frequência; para T/vento: MAE/RMSE e confiabilidade por antecedência. Preservar artefatos por 90 dias é transição, não arquivo científico permanente.

## Aviso operacional
Dados de umidade de solo gridded não autorizam trânsito de máquinas. Classificação meteorológica conjunta de pulverização não autoriza aplicação: bula, equipamento DJI, deriva, inversão, estrutura dos talhões, culturas sensíveis, polinizadores e legislação permanecem mandatórios.
