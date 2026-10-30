# Registro de experimentos

Com dados reais: elegibilidade insuficiente, zero pares observacionais, nenhum ganho medido e nenhuma calibração promovida. Diagnóstico reproduzível em site/data/calibration.json.

Software: o teste test_calibration_v22.py cria 180 dias sintéticos exclusivamente em diretório temporário, com viés conhecido, e verifica que M3 recupera esse viés no teste temporal reservado e que M4 roda sem promover a previsão. Esse resultado testa código; não mede desempenho meteorológico em Naviraí ou Diamantino.

Futuros ensaios gravam calibration_datasets, calibration_models e model_evaluations; preservam split, hash, versão de atributo, método, parâmetros e resultados. Os relatórios de ensaios não são apagados por falta de melhoria. A UI identifica teste temporal e não mostra exemplos fictícios enquanto faltarem dados.

Dependências científicas opcionais em requirements-science.txt; versões da execução local em requirements-lock-v22.txt. Nunca carregar pickle de terceiro como artefato de calibração.
