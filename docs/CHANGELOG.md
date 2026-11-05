# Changelog

## 4.0.0 — identidade oficial, estações físicas e satélite, 05/11/2026

- Estações físicas: `scripts/science/station_files.py` lê os arquivos INMET (portal, horário UTC) e Embrapa Guia Clima (diário), aplica QC conservador (faltante ≠ zero) e agrega por dia local; `scripts/science/station_calibration.py` e `scripts/station_calibration.py` pareiam as medições com o Previous Runs API nas coordenadas da estação (D1, D2, D3, D7, sete modelos + média multimodelo), avaliam correções (viés, viés por hora, linear, fator, mapeamento de quantis) por origem móvel mensal com bootstrap por blocos e só recomendam o que vence fora da amostra. Arquivos recebidos em `data/stations/` (INMET S735 Naviraí, INMET A949 Diamantino, Embrapa Naviraí/IFMS) com registro em `stations.json`.
- Boletim: `scripts/ai_bulletin.py` gera texto por regras a partir de uma ficha de fatos e, opcionalmente, pede a um provedor gratuito (GitHub Models, Groq, Gemini, OpenRouter, Cloudflare Workers AI, Ollama) uma reescrita validada número a número; publica `site/data/bulletin_<localidade>.json` com a origem.
- Coletor: `forecast_models()` em `scripts/collect.py` consulta modelos determinísticos lado a lado (`models=`) com isolamento de identificadores inválidos (HTTP 400) e publica `deterministic_models` com a faixa diária entre modelos.
- Interface: identidade visual com o logo oficial (paleta navy/verde/azul-céu, vermelho só em alertas, favicons, manifesto); `site/static/weekly_board_v40.js` (quadro semanal estilo jornal e próximas semanas), `bulletin_v40.js`, `stations_v40.js` (observações, matriz de erro, previsão corrigida no navegador), `models_compare_v40.js`; camadas GOES-East GeoColor/IR/massas de ar e IMERG com controle de tempo em `maps_v14.js` (v=21); `nav_v30.js` retira o mapa de amostras em grade do modo simples.
- Workflows: `pages.yml` ganha a etapa do boletim e a permissão `models: read` (usada apenas com `AI_BULLETIN_PROVIDER=github`); `science.yml` executa a verificação das estações e publica `public/stations/` na branch de arquivo; `station-calibration.yml` permite prévia manual em qualquer branch sem publicar.
- Publicação: `scripts/export_science_public.py` copia `public/stations/*.json` para o site; `scripts/archive_git.py` publica os relatórios; `scripts/science/ingest.py` ignora o produto `station_previous_runs` no banco das sedes.
- Testes novos: `tests/test_station_calibration_v40.py`, `tests/test_models_compare_v40.py`, `tests/test_ai_bulletin_v40.py`, `tests/test_v40_frontend.cjs`; pinos de versão de ativos atualizados.
- Documentos: [Design v4](DESIGN_V4.md), [Estações e calibração](ESTACOES_E_CALIBRACAO_V4.md), [Fontes v4](FONTES_V4.md). Os números reais de verificação aparecem após a primeira execução dos workflows com rede.

## 3.0.0 — plataforma agrometeorológica, 05/11/2026

- Coletor: offset de fuso derivado da configuração; metadados de rodada por modelo (`static/meta.json`, best effort) e cache sensível à rodada; pedido de 8 dias para sete dias locais completos; variáveis complementares do determinístico em requisição isolada.
- Produtos novos: passo nativo por modelo e janelas horárias compatíveis; acumulados 3/5/7 dias e dias secos por membro; concordância diária; comparação com a publicação anterior; agro-ensembles (T/UR/VPD/vento/rajada) no coletor e no cliente de coordenadas.
- Observações: preferência por estações operadas pelo INMET, até três candidatas, token opcional com URL redigida nos manifests; `record_url` no cliente HTTP.
- Diagnóstico: `freshness` no JSON público, `diagnostics.json` com cadência real do Actions, cota estimada, arquivo e erros; painéis de frescor e diagnóstico no site.
- Interface: modo simples/avançado, cinco áreas, resumo da fazenda, painéis de acumulados, concordância, mudança entre publicações, radiação/ET₀/CAPE.
- Workflows: condição de repositório explícita, cache do estado de publicação e do log de coleta, exportação do diagnóstico, segredos opcionais `INMET_API_TOKEN`.
- Ferramentas: `scripts/replay_capture.py` reconstrói o JSON público a partir de uma captura arquivada.
- Removido o instalador V23 (`aplicar_v23.py`, `patches.json`, `payload/`), substituído pela integração direta.
- Testes: 187 Python e 15 suítes JavaScript offline; validação em Chromium desktop e celular (`tests/browser_v30.cjs`).

## 2.2.0 — revisão de integração GitHub, 29/10/2026

- Recuperação das duas branches por bundles no repositório original, preservando main e a entrega anterior.
- CI de PR offline, permissões por job, fila de escritores, transporte seletivo e recuperação explícita de artifacts.
- Falhas de relatórios preservam RAW e relatórios anteriores; exportação pública usa um único commit do arquivo.
- Alertas de armazenamento em 50/70/85/95%, limites conservadores e volumes mensais verificáveis, sem exclusão automática.
- Correção da troca global de localidade na aba Precisão; coordenadas desconhecidas limpam resultados anteriores e exclusões são locais.
- Pareamento e hashes de datasets determinísticos, intervalo real de purga registrado e timestamp da coleta determinística preservado.
- Reconstrução real, comparação integral do SQLite, backup/restauração e validação visual; evidências em `RELEASES/V22_GITHUB_INTEGRATION.md`.
- Nenhuma publicação remota ou promoção de calibrador; observações e pares elegíveis continuam em zero.

## 2.2.0 — candidato local, 29/10/2026

- Auditoria da v2.1 no commit e1241e2; branch de desenvolvimento sem upstream para main.
- Captura dos membros e respostas oficiais, gzip/SHA-256, manifests incrementais e escritor limitado a weather-archive.
- SQLite com migração, QC, intervalos e localidades; reconstrução, backup e exportação Parquet.
- Adaptadores Previous Runs D1/D2/D3/D7, Single Runs e Historical Forecast testados nas duas localidades.
- Importação de arquivos INMET/canônicos com identidade, unidade e intervalos; série Embrapa provisória continua excluída.
- Pareamento e métricas MAE/RMSE/viés circular/Brier/BSS/CRPS/reliability/eventos, sem ranking de precisão não validada.
- Nova aba Precisão dos modelos, filtros e comparação experimental quando houver dados elegíveis.
- Correção do dia de chuva (01h a 00h seguinte) e do contador de restrições por operação da Central Agro.
- Infraestrutura de calibração em modo experimental e IA none/Ollama opcional; provedores externos bloqueados.
- Workflows de coleta/arquivo/verificação diária e tentativa de treino semanal preparados. Ativação no GitHub pendente de aprovação para main.

Nenhuma observação, métrica ou melhoria local foi inventada. Consulte RELEASES/v2.2-status.md para limites e evidências.
