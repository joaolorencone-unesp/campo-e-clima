# Verificação observacional — Embrapa Guia Clima, Naviraí

## O que foi confirmado nas páginas oficiais em 26/10/2026
- Estação 6: Naviraí/IFMS, latitude aproximada -23.025833, longitude -54.189444, **381 m**, disponibilidade de dados desde **01/12/2024**. Consultar: https://www.cpao.embrapa.br/gc/guia-clima?cod_estacao=6
- A interface de pesquisa https://www.cpao.embrapa.br/gc/busca-de-dados permite consulta e download de **dados diários** de temperatura, chuva e umidade por estação/período. Confirmar filtros e planilha gerada antes de automatizar a extração. Não foi identificada aqui uma API oficial estável com documentação pública para séries por estação.
- Leituras correntes podem retornar **Sem Dados**. Não interpretar como tempo seco ou ausência de tempestades.
- O boletim da Embrapa publicou 101 mm para **setembro de 2026 em Naviraí**; isso é um agregado mensal histórico informado pelo órgão, não um dado horário.
- O balanço hídrico Embrapa considera CTA de 58,5 mm para camada 0–1 m, um parâmetro padronizado pelo órgão que **não representa automaticamente cada talhão**.

## Pipeline de histórico a implementar
1. Exportar manualmente uma amostra da estação **Naviraí** (somente estação 6), começando 01/12/2024, com data, precipitação, temperaturas e UR.
2. Registrar o **link/arquivo original**, data de download, período de medição, identificador da estação, fuso, unidades, ausência de dados e qualidade; não modificar os valores brutos.
3. Confirmar permissão e mecanismo oficial de acesso automatizado com a Embrapa antes de automatizar coleta; respeitar licença e limites.
4. Harmonizar para CSV canônico `date_local,precip_mm,temp_mean_c,temp_min_c,temp_max_c,rh_mean_pct,station_id,quality_flag`.
5. Fazer QC: chuva <0 inválida, somas diárias inconsistentes, picos extremos e duplicatas com auditoria; faltantes são nulos, não zeros. Verificar mudança de estação/sensor e horas de fechamento pluviométrico.
6. Reconciliar previsão arquivada (data de emissão, data de validade, lead-time em horas) e observação diária **observada no mesmo dia local e no mesmo período de acumulação**.
7. Calcular MAE/Bias para temperatura, Brier/Brier skill por limiares de chuva e CRPS para distribuições. Separar por horizonte, meses chuvosos/secos e fonte (estação pontual vs grade).
8. Comparar pesos iguais, pesos institucionais, melhor modelo isolado e climatologia, com **rolling-origin holdout temporal**. Calibrar em histórico passado e verificar em períodos futuros não vistos.

## Limitações e próximos passos
- Histórico a partir de 2024 é insuficiente para normais climatológicas de 30 anos e pode ser pequeno para calibrar eventos raros >30–50 mm/dia.
- Para séries longas de referência, consultar estações vizinhas INMET/Embrapa e CHIRPS/ERA5-Land com seus vieses e diferenças espaciais; **não declarar que são observações diretas em Naviraí**.
- Upload do JSON gerado pelo Actions como artifact com retenção **máxima de 90 dias** é recurso temporário. Para décadas de verificação, exigir armazenamento permanente em Parquet/objeto e manter snapshots das distribuições emitidas (idealmente membros individuais, não apenas resumos).
- Não publicar coordenadas privadas de fazendas nem históricos privados de produtores em Pages público.
