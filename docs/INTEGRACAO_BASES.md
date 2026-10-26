# Plano de integração: observações, alertas e verificação

**Estado do código: v0.5** · Local: Naviraí/MS, IBGE 5005707; sede -23.065, -54.190; estação Embrapa nº 6 em -23.025833, -54.189444 (381 m). Fuso de apresentação UTC−4.

## O que entra agora (v0.5)

| Produto | Coleta | Tipo | O que é mostrado | Status/limitação |
|---|---|---|---|---|
| Open-Meteo Forecast e Ensemble | GitHub Actions ~30min | **Previsão** | D0–D14, membros e cenários, pulverização experimental | Não calibrados |
| INMET avisos ativos/futuros | API oficial https://apiprevmet3.inmet.gov.br/avisos/ativos | **Aviso oficial** | Apenas se o código IBGE 5005707 constar nos geocodes | Fonte pode falhar; horário específico não convertido sem fuso documentado |
| INMET catálogo de estações | API https://apitempo.inmet.gov.br/estacoes/T | **Cadastro** | Estações e distâncias da sede, status, altitude | Cadastro não é medição |
| INMET histórico diário próximo | API https://apitempo.inmet.gov.br/estacao/diaria/INICIO/FIM/CODIGO | **Observação de estação vizinha** | Status de disponibilidade e dias com dados | API pode bloquear clientes externos; estação vizinha ≠ Naviraí |
| Embrapa Guia Clima estação 6 | CSV exportado e revisado | **Observação local histórica** | Gráfico de chuva diária, dias faltantes, tabela | Integração manual inicial; não há contrato público de API confirmado |

Quando fonte falhar, registrar `unavailable`. Não converter falta de observação para zero. Nem abrir página da estação e ler Dourados por engano.

## Como importar o histórico da Embrapa, passo a passo

1. Abrir https://www.cpao.embrapa.br/gc/busca-de-dados. **Selecionar Naviraí** (estação 6; séries desde 01/12/2024), nunca deixar Dourados como estação padrão.
2. Escolher período de 01/12/2024 até a data final disponibilizada. Selecionar as variáveis *Chuva*; opcionalmente Temperatura Média e Umidade Relativa Média.
3. Clicar em **Baixar planilha**. Conferir se o arquivo traz efetivamente registros de Naviraí, suas datas e unidades. Guardar cópia original e origem; não publicar informações privadas.
4. Abrir a planilha exportada no Excel e salvar uma cópia CSV com cabeçalho **exatamente**:

   `station_id,date,precipitation_mm,temperature_mean_c,relative_humidity_mean_pct`

   - `station_id` sempre igual a **6**.
   - `date` em `AAAA-MM-DD` ou `DD/MM/AAAA`.
   - `precipitation_mm`: chuva diária em mm, `0` somente quando o registro realmente mediu 0; célula vazia para faltante.
   - `temperature_mean_c`, `relative_humidity_mean_pct` opcionais, vazios caso não disponíveis. Não inferir valores.
   - Uma linha por dia. Sem cabeçalhos extras, totais mensais ou linhas misturadas de outras estações.
5. Substituir o arquivo `data/observacoes/embrapa_navirai.csv` do repositório. O arquivo inicial contém **somente cabeçalho, sem medições fabricadas**.
6. Fazer commit e push. O GitHub Actions executará a validação e publicará o gráfico na aba **Observações & alertas**. Se houver datas duplicadas, estações diferentes, valores negativos ou erros de formato, **a importação é rejeitada inteira** até revisão.
7. Para auditoria científica, manter o arquivo exportado original em armazenamento com acesso controlado e documentar data de extração, campo selecionado e eventuais revisões, inclusive se o arquivo público for posteriormente substituído.

**Importante:** a exportação da Embrapa pode ser `.xlsx`. Esta v0.5 não lê Excel automaticamente na automação: salve-a em `.csv` após conferir os nomes e unidades das colunas. Isto evita transformar o formato bruto da planilha em uma suposta API oficial não documentada.

## Próximas bases a integrar

**Fase 2 (observações e agora):**
- INMET: alternativa BDMEP e dados horários de estação próxima com status, proveniência e QC. A API pública pode ter restrições de acesso, portanto usar fontes documentadas sem contornar bloqueios.
- CEMADEN: inventário das estações e dados recentes/históricos após confirmar termos e autenticação da PED; Swagger https://sws.cemaden.gov.br/ . Não tratar o pluviômetro mais próximo como medição exata no talhão.
- INPE: mapa de satélite GOES-19 pelo DSAT (https://www.cptec.inpe.br/dsat/), radar e raios somente quando puderem ser acessados com timestamp verificável; imagens em TMS/STAC só serão embutidas quando CORS/licença/validade forem testados.
- NASA GPM/IMERG Early/Late: estimativa espacial de precipitação, não pluviômetro; Early ~4h, Late ~14h, Final meses depois. https://gpm.nasa.gov/data/directory .

**Fase 3 (backtesting):**
- Preservar **issued_at, valid_at, modelo, membro, lead_time, versão do processamento, célula/grade e variável** por rodada. O `latest.json` atual guarda apenas resumos e frequências: **não permite reconstruir os membros originais para CRPS completo**; será necessário persistir as trajetórias brutas (por exemplo Parquet/objeto) e manter suas versões.
- Comparar exatamente a previsão emitida antes do evento com a observação do dia/hora, sem misturar dados corrigidos depois do fato.
- Métricas de chuva: frequência, viés dos acumulados, Brier (por limiar), CRPS, diagramas de confiabilidade, habilidade relativa à climatologia e persistência.
- Fazer holdout por tempo, avaliando antecipações 1, 3, 6, 24, 48, 72 h, 7 e 14 dias. Só depois testar blend com pesos aprendidos.
- Manter, quando possível, pluviômetro instalado na própria fazenda. Apenas série de 2024 em diante NÃO define climatologia de 30 anos.

**Fase 4 (bases de solo e máquinas):** SoilGrids/ISRIC para mapas estáticos de textura, carbono, densidade e retenção; chuva + ET0 e/ou NASA SMAP para condição dinâmica, com validação por amostragens e tráfego local. Risco de trafegabilidade continuará 'indeterminado' sem parâmetros da máquina, solo e umidade verificada.

## Limites de atualização

- GitHub Actions agendado a cada 30 minutos **não garante execução no minuto exato**. A fonte exibirá timestamp.
- Publicação de código e dados no GitHub Pages é **pública**. Não subir chaves de API ou informações de produtores.
- O aviso INMET com município confirmado precisa ser exibido em destaque. Falha da API ≠ 'sem aviso'.
- O painel é pesquisa/triagem e não autoriza operação aérea ou entrada de máquinas.
