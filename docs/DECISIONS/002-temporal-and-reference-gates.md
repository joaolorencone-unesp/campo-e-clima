# ADR 002 — admissibilidade temporal e da referência

Data: 29/10/2026. Versão: 2.2.0.

Problema: arquivos históricos, reanálises e exportações provisórias podem produzir métricas aparentemente válidas sem uma previsão realmente disponível nem uma estação identificada.

Alternativas: inferir emissão pela consulta, usar ERA5 como observação, ou manter categorias explícitas com exclusões conservadoras. Decisão: terceira alternativa. Previous Runs tem deslocamento fixo, Single Runs tem inicialização mas disponibilidade não comprovada, Historical Forecast é série modelada. Somente observação identificada com QC básico entra em pares descritivos. Não há selo de calibração validada.

Justificativa: evitar vazamento e falsa precisão. Consequência: o painel permanecerá sem métricas enquanto faltarem pares. Distância e QC básico não resolvem altitude/sensores/exposição. Promoção exige avaliação independente e robustez.

Correção adicional: chuva horária é intervalo terminado no timestamp. O dia local deve usar finais 01h…00h seguinte. Três fixtures antigas de testes foram ajustadas para esse contrato e um teste com chuva forte na meia-noite anterior detecta a regressão. Nenhum dado foi deslocado silenciosamente no RAW.
