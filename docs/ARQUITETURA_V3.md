# Arquitetura proposta — Campo e Clima v3

Princípio: dois sistemas acoplados por hashes, nunca por confiança. O **sistema público** coleta, resume e publica (GitHub Actions + Pages, sem servidor). O **sistema científico** preserva respostas originais, reconstrói bancos, verifica e experimenta (branch `weather-archive` + processamento local). Nenhum dos dois inventa valores; cada número publicado é rastreável a uma resposta HTTP com SHA-256.

## 1. Fluxo (estado após esta entrega)

```
Open-Meteo / INMET ──HTTP──▶ FreeClient (cache em disco, cota, cooldown 429, fresh_after por rodada)
        │                          │
        │                          ├─▶ Capture: objetos gzip por SHA-256 + manifesto (URL pública, params, aquisição, cache_hit)
        ▼                          ▼
scripts/collect.py ─▶ produtos: diário, horário por passo nativo, acumulados 3/5/7 d, dias secos,
                       concordância, agro-ensembles (T/UR/VPD/vento/rajada), triagem conjunta,
                       comparação com a publicação anterior, determinístico + complementar
        │
        ├─▶ scripts/science_cli.py: horários de aquisição reais, freshness, ingestão SQLite opcional
        ├─▶ scripts/export_diagnostics.py: diagnostics.json (frescor, cadência, cota, arquivo, erros)
        ▼
site/data/*.json ──Pages──▶ navegador (modo simples / avançado; coordenadas personalizadas consultam
                              a Open-Meteo diretamente com os mesmos algoritmos em JavaScript)

runtime/captures ──artifact (7 d)──▶ job archive ─▶ weather-archive (manifests, objects, public/*.json)
weather-archive ─▶ rebuild SQLite (local) ─▶ evaluate / train (shadow) ─▶ public/verification.json ─▶ Pages
```

## 2. Coleta e política de atualização

- **Agendamento**: cron a cada 30 min continua, mas o GitHub entrega ≈9% das execuções (auditoria §4). A plataforma não depende da pontualidade: cada produto carrega `collected_at_utc`, `cache_hit` e, quando o provedor responde, `model_run.last_run_*`.
- **Identificar o último ciclo**: `model_run_metadata` consulta `static/meta.json` do domínio de cada modelo antes dos membros. Se a rodada disponível for mais nova que a cópia em cache, o cache é ignorado (`fresh_after`); se não houver rodada nova, o cache vale até 12 h. Sem metadados, TTL conservador de 3 h.
- **Evitar duplicidade**: determinístico 27 min de TTL; catálogo INMET 24 h; produtos lentos uma vez por dia (NASA POWER, GEFS estendido, Previous Runs) e semanais (ECMWF sazonal) via caches do Actions.
- **Falhas**: `429` aciona cooldown pelo `Retry-After`; timeouts têm fallback de 4 dias; orçamento total de 900 s por coleta; falha de uma fonte nunca remove o último produto válido de outra.
- **Disparo externo opcional** (exige autorização do usuário): um agendador gratuito externo chamando `POST /repos/.../actions/workflows/pages.yml/dispatches` com um *fine-grained PAT* restrito a `actions: write` deste repositório. Não implementado: envolve criar e guardar um token pessoal.

Registros separados por produto: `model_run.last_run_initialisation_utc` (rodada), `last_run_availability_utc` (disponibilização), `collected_at_utc` (aquisição original), `freshness.published_utc` (publicação), `hourly_forecast_start_local` (validade inicial). UTC internamente; conversão para o fuso do ponto só na interface.

## 3. Processamento dos ensembles

- Pesos iguais por modelo válido, depois por membro; quantis por CDF ponderada.
- Precipitação horária: só modelos com passo nativo ≤ janela (detecção pelo padrão de repetição das acumulações desagregadas).
- Acumulados e dias secos por trajetória de membro (dias locais completos 01h–00h).
- Concordância diária por modelo (maioria de membros > 1 mm) e dispersão das médias.
- Mudança entre publicações: diferença de mediana e de frequência > 1 mm por dia, com a lista dos modelos cuja aquisição mudou (rodada nova) ou não (cache).
- Próximos passos: ponderação por desempenho só após verificação (ver plano científico); dependência institucional tratada por sensibilidade (ECMWF, NOAA) antes de qualquer ponderação.

## 4. Observações

- Estações oficiais: preferência por estações operadas pelo INMET (rota de dados funcional), até 3 candidatas em 50 km, token opcional e redigido. Alvos: A752 Itaquiraí e S735 (Naviraí), A949 Diamantino.
- Embrapa Guia Clima: importação manual auditada; promoção a referência verificada apenas com identidade confirmada.
- Camada tratada: `observations` no SQLite com `qc`, `reference_quality`, intervalo explícito; RAW preservado nos objetos.
- Quando não há observação confiável, o painel diz exatamente isso (`insufficient_verified_pairs`).

## 5. Banco de dados e histórico

Decisão mantida: objetos gzip imutáveis + manifests na branch pública; SQLite reconstruível localmente (`science_cli rebuild`), Parquet para análise (`science_cli parquet`). Medições: 10,1 MB após 8 dias (~1,4 MB/dia) → ~0,5 GB/ano; limites conservadores de 750 MB (arquivos) e 1 GB (Git) com alertas em 50/70/85/95%. Antes de 85%: novo repositório de arquivo e catálogo de ligação (ADR 001).

Recomendações: manter o SQLite fora do Git; usar o computador local para reconstruções e Parquet (DuckDB/pandas) quando as séries crescerem; backups mensais verificados (`archive_backup.py`). O painel público nunca depende do computador local.

## 6. Verificação e publicação científica

`weather-archive/public/{verification,calibration,explanation,archive_status}.json` são exportados para o site a cada coleta. Toda métrica carrega `dataset_sha256`, `formula_version`, `validation_status`. Nenhum calibrador substitui a previsão principal sem teste temporal independente (ADR 002).

## 7. Frontend

Arquivos estáticos, Plotly local, Leaflet via CDN. Dois níveis: **simples** (resumo da fazenda, Central Agro, mapas, chuva) e **avançado** (todas as abas em cinco áreas). O resumo é gerado por `farm_summary_v30.js` a partir do JSON publicado, com linguagem controlada (nunca "chuva garantida" ou "aplicação liberada"). Coordenadas personalizadas executam os mesmos algoritmos em JavaScript (`location.js`) sem reutilizar dados de Naviraí.

## 8. Fases restantes e critérios de conclusão

| Fase | Entregas pendentes | Critério objetivo |
|---|---|---|
| 1 Confiabilidade | Confirmar em produção o `meta.json` e as variáveis complementares; observar cadência no diagnóstico por 7 dias | 7 dias sem execução falha; `models_with_newer_run_pending` coerente |
| 2 Agrometeorologia | Balanço hídrico simplificado (ET₀×Kc, chuva, parâmetros de solo informados pelo usuário); estresse por cultura/fase | Módulo com entradas explícitas e testes; sem umidade "estimada" sem parâmetros |
| 3 Chuva e precisão | Retrocoleta Previous Runs (IFS, ICON, GFS) por blocos de 31 dias; observações INMET/Embrapa; primeiras métricas descritivas | ≥90 dias pareados por local antes de qualquer calibração |
| 4 Mapas | GOES-East via GIBS (10 min), IMERG por GIBS, legendas/metadados, radar mantido; sem nowcasting (fonte descontinuada) | Camadas com horário UTC/local, fonte e idade do quadro |
| 5 Experiência | Exportação CSV dos produtos, relatório imprimível, refinamento mobile | Teste de navegador em 390 px e 1440 px sem overflow |
| 6 Validação | Relatórios de desempenho por horizonte/estação; walk-forward | Documento com intervalos de incerteza e amostras por classe |
