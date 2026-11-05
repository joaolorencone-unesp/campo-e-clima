# Fontes gratuitas — adendo v4

Complementa [FONTES_V3](FONTES_V3.md). Pesquisa feita em 05/11/2026 por busca na web (sete agentes, ~190 consultas), sem acesso direto às páginas a partir deste ambiente. Cada item diz se foi **verificado por busca** (citação textual encontrada) ou se **precisa confirmação** antes de depender dele. Nada pago, nada com período de teste que vira cobrança.

## 1. Adotado nesta versão

### NASA GIBS — GOES-East e IMERG (mapa, modo avançado)
- Serviço WMTS público, sem chave, EPSG:3857, dimensão TIME sub-diária `YYYY-MM-DDTHH:MM:SSZ`, janela móvel de 90 dias. Camadas usadas: `GOES-East_ABI_GeoColor` (1 km, 10 min, `GoogleMapsCompatible_Level7`), `GOES-East_ABI_Air_Mass` (2 km, 10 min, Level6), `GOES-East_ABI_Band13_Clean_Infrared` (identificador público provável, Level6) e `IMERG_Precipitation_Rate_30min` (30 min, latência ≈ 4 h).
- Verificado por busca: índice oficial `layer-metadata` para GeoColor; tabela da wiki para Air Mass (2 km, png, 10 min, 90 dias); permalinks oficiais para IMERG; latência típica do GeoColor ≈ 40 min; ordem `{z}/{y}/{x}` do caminho.
- Precisa confirmação: o identificador exato da banda 13 sem sufixo interno; o conjunto de matrizes de cada camada; cabeçalho CORS (irrelevante para tiles em `<img>`); se o feed GOES-East já é GOES-19. O código recua automaticamente até 60 min quando o instante mais recente não existe.
- Termos: dados abertos; agradecimento obrigatório (incluído no rodapé: "imagery provided by services from NASA's Global Imagery Browse Services (GIBS), part of NASA's Earth Science Data and Information System (ESDIS)"); uso em massa (> 1 000 000 tiles/24 h) exige coordenação prévia; 50 Mbps sustentados; 500 conexões simultâneas.

### Open-Meteo — Previous Runs API e parâmetro `models=`
- Previous Runs (`previous-runs-api.open-meteo.com`): variáveis `*_previous_day1…7` por modelo explícito; usado para a verificação nas coordenadas das estações. Forecast API com `models=` separado por vírgula devolve campos sufixados por modelo; usado para a comparação multimodelo determinística.
- Identificadores confirmados em páginas oficiais: `ecmwf_ifs025`, `ecmwf_aifs025_single`, `gfs_graphcast025`, `ncep_aigfs025`, `gem_global`, `jma_gsm`; `icon_global` descontinuado em 30/11/2026 (por isso o projeto usa `icon_seamless`); `bom_access_global` e `kma_gdps` descontinuados. **Precisa confirmação** (grafia não exibida nos resultados): `gfs_global`, `icon_seamless`, `meteofrance_arpege_world`, `ukmo_global_deterministic_10km`. Um id inválido devolve HTTP 400 e é isolado pelo código, sem derrubar os demais.
- Termos: CC BY 4.0 com atribuição "Weather data by Open-Meteo.com"; API gratuita só para uso não comercial; < 10 000 chamadas/dia, 5 000/h, 600/min (peso por variáveis × modelos × dias).

### Provedores gratuitos de LLM para o boletim (opcionais; padrão = regras)
| Provedor | Como ativar | Situação verificada por busca | Observação |
|---|---|---|---|
| GitHub Models | `AI_BULLETIN_PROVIDER=github`; usa o `GITHUB_TOKEN` do próprio Actions (permissão `models: read` no job de build) | sugerido pelo crítico; limites do nível gratuito não confirmados | sem segredo extra; modelo padrão `openai/gpt-4.1-mini`, substituível por `AI_BULLETIN_MODEL` |
| Cloudflare Workers AI | `cloudflare` + `CLOUDFLARE_API_TOKEN` e `CLOUDFLARE_ACCOUNT_ID` | página oficial: 10 000 neurons/dia grátis, sem cobrança excedente no plano Free (as requisições falham acima do limite) | política de uso dos prompts não encontrada |
| Google AI Studio (Gemini) | `gemini` + `GEMINI_API_KEY` | sem cartão; nível gratuito reduzido em dez/2025 (valores divergem entre fontes); termos de 23/03/2026 permitem uso dos prompts para melhoria de produtos | usar projeto sem faturamento vinculado; não enviar dados pessoais |
| Groq | `groq` + `GROQ_API_KEY` | `llama-3.1-8b` e `llama-3.3-70b` retirados em 16/08/2026; substitutos `openai/gpt-oss-20b/120b` | limites numéricos do nível gratuito não exibidos |
| OpenRouter | `openrouter` + `OPENROUTER_API_KEY` | modelos com sufixo `:free` | catálogo muda com frequência |
| Ollama local | `ollama` | sem rede externa | só para uso local |

Em todos os casos o texto do modelo é validado número a número contra a ficha de fatos; falha ou cota esgotada devolve o texto por regras. `AI_ALLOW_PAID` permanece `0`.

## 2. Pesquisado e não adotado

| Item | Motivo |
|---|---|
| Windy embed (`embed.windy.com/embed2.html`) | termos (cláusula 9.6.3, citada em fórum) reservam os widgets a "uso de mídia" e vedam "weather apps"; um site meteorológico não comercial é zona cinzenta; parâmetros não documentados; bloqueio por referer possível. Só com resposta escrita do suporte. |
| meteoblue Weather Maps Widget | gratuito segundo a página comercial, mas exibe dados próprios (modelo diferente da tabela do painel) e os limites de tráfego/condições precisam ser lidos na página de uso comercial/não comercial. |
| Ventusky embed | "free to use" aparece só em blog corporativo; sem termos formais de embed. |
| OpenWeatherMap Weather Maps 1.0 | exigiria expor a chave pessoal em site estático; licença ODbL (share-alike) relatada por terceiros; resolução baixa. |
| ECMWF Open Charts API | licença CC BY 4.0 confirmada, mas os ids de produto de meteograma, a projeção América do Sul e os "termos adicionais" não foram confirmados; candidato a próxima fase (imagens oficiais geradas no Actions). |
| CPTEC/INPE MERGE e SAMeT (quicklooks PNG em `data.inpe.br/bdc/...`) | padrão de URL inferido de um único exemplo por produto; precisa de teste com `HEAD` no Actions antes de ir à interface; licença não comercial com citação "CPTEC/INPE". |
| Tiles próprios a partir do ECMWF Open Data | viável (CC BY 4.0, 0,25°, índice `.index` com `_offset/_length`), mas exige processamento no Actions e validação de tamanho por passo; proposta. |
| Leaflet.TimeDimension, Meteocons | MIT, úteis, dispensados para evitar dependências externas; o controle de tempo do GOES foi implementado localmente e os ícones são SVG inline. |

## 3. Lacunas apontadas pelo crítico (próximas pesquisas)

Radar meteorológico brasileiro (DECEA/REDEMET com chave gratuita, SIMEPAR, CEMADEN, radar INMET) e a cobertura real sobre Naviraí e Diamantino; pluviômetros automáticos do CEMADEN e telemetria da ANA (Hidro-WebService); relâmpagos (GOES-19 GLM via GIBS, Blitzortung, ELAT/INPE); alertas oficiais em CAP (INMET alertas2/alerts.json, Defesa Civil); ZARC (dados abertos do MAPA) e Agritempo; queimadas (INPE Programa Queimadas, NASA FIRMS); umidade do solo e NDVI (SMAP, Sentinel-2/HLS, Planetary Computer); previsão sazonal (C3S, prognósticos INMET/CPTEC, ENSO); nowcasting de 1–3 h (RainViewer já traz 30 min; pySTEPS seria pesado no Actions); normais climatológicas 1991–2020 do INMET. Nenhum desses itens foi verificado nesta versão.


## Adendo 4.1 (05/11/2026)

| Fonte | Uso | Licença/limites | Estado |
|---|---|---|---|
| CEMADEN — pluviômetros automáticos (`sws.cemaden.gov.br/PED/rest`) | chuva observada 24 h até 80 km | dados públicos federais; **exige token** (gratuito, solicitado ao CEMADEN; confirmado em 05/11/2026: HTTP 400 sem token) | integrado; estado `requires_registration` até existir o segredo `CEMADEN_TOKEN` |
| INMET avisos RSS (`apiprevmet3.inmet.gov.br/avisos/rss`) | redundância dos avisos oficiais | público | integrado como caminho secundário |
| INMET WIS 2.0 (`wis2bra.inmet.gov.br/oapi`) | observações SYNOP padronizadas (candidato a substituir o token do apitempo) | OGC API pública | sondado pelo `sources-probe`; integração depende da cobertura de S735/A949 |
| NASA GIBS GOES-East (`GOES-East_ABI_FireTemp`, `GOES-East_ABI_Band2_Red_Visible_1km`) | focos de queimada e visível 1 km | NASA, agradecimento obrigatório | identificadores confirmados no GetCapabilities (05/11/2026); **não há camada GLM de relâmpagos** no serviço EPSG:3857 |
| CPTEC/INPE MERGE (`data.inpe.br/bdc/data/prec_merge_daily/FIG/DAILY`) | figura diária de chuva observada | não comercial, citar CPTEC/INPE | URL confirmada (HTTP 200, PNG de 735 kB para 04/11/2026) |
| radarmeteorologico.com.br | — | site de terceiros sem termos claros | não adotado |

Sondagem de 05/11/2026 (`sources-probe`): INMET avisos JSON e RSS respondendo (77 itens no RSS); INMET WIS 2.0 lista Diamantino como estação convencional 83309 (WIGOS 0-20000-0-83309) com SYNOP horário, candidata a observação ao vivo sem token numa próxima versão; Naviraí não apareceu no catálogo WIS 2.0.
