# Auditoria da exportação Guia Clima enviada em 26/10/2026

Arquivo original: `busca-dados.xls` (conteúdo real **HTML `<table id="tabela">`**, não Excel binário). Conversão reprodutível: `scripts/sources/embrapa_export.py`.

## Resultado

- **700** registros diários, datas únicas de 07/05/2024 a 25/10/2026.
- **6 registros isolados** anteriores a 01/12/2024: **07/05/2024** e **26–30/11/2024**.
- **694 registros consecutivos** dentro do intervalo oficial esperado **01/12/2024–25/10/2026**.
- **0 lacunas de datas** e **0 valores ausentes de chuva** nos 694 registros preservados.
- No CSV derivado, os horários de máximas e mínimas não são utilizados (o estudo é diário); **3 leituras de vento máximo estão ausentes** na exportação.
- Grande acumulado diário no arquivo: **102,0 mm em 04/10/2026**. Recomenda-se comparar eventos extremos com outra estação, radar e consistência dos sensores antes de usar como referência definitiva.

## Proveniência

**O arquivo não contém ID/nome da estação na própria tabela**. Embora tenha sido fornecido no contexto da estação 6 (Naviraí/IFMS), a procedência precisa ser confirmada em captura da seleção da estação ou documentação da exportação original. O painel rotula os dados como **PROVISÓRIOS — estação não confirmada**. A importação não atribui silenciosamente a série à estação 6.

## Soma de chuva por ano civil — APENAS desta exportação (não climatologia verificada)

| Ano | Registros | Soma no período informado |
|---|---:|---:|
| 2024 (dezembro) | 31 dias | 238,6 mm |
| 2025 | 365 dias | 1.515,6 mm |
| 2026 (até 25/10) | 298 dias | 1.205,5 mm |

Não use totais parciais para inferir normal climatológica. A análise de habilidade dos ensembles só começa após verificação da origem da estação e recuperação dos *forecasts* históricos com horário de emissão.

Fonte do sistema: https://www.cpao.embrapa.br/gc/busca-de-dados .
