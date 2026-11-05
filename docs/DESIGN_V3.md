# Proposta visual e arquitetura de informação — v3

Implementada nesta entrega e validada em Chromium (1440×1000 e 390×844). Capturas em `docs/RELEASES/v3/`.

## Dois níveis de uso

- **Modo simples (padrão para novos visitantes)**: cabeçalho compacto, seleção da fazenda, avisos essenciais (frescor dos ensembles, avisos INMET) e o painel **"Como estará o tempo na minha fazenda?"** com manchete, seis cartões (agora, chuva 6 h, chuva 24 h, chuva na semana, temperatura, vento/rajadas), riscos a observar, frase de concordância entre modelos com idade dos dados e períodos de menor restrição meteorológica (48 h). Abas visíveis: Visão geral, Chuva & ensembles, Central Agro, Mapas, Observações.
- **Modo avançado**: todas as 11 abas em cinco áreas (Visão geral · Chuva e previsões · Operações agrícolas · Mapas e monitoramento · Ciência e dados), painéis densos (métricas, gráficos horários, ensembles agrometeorológicos, acumulados, concordância, mudança entre publicações, frescor por modelo, diagnóstico central). A escolha fica no navegador (`localStorage`) e pode ser forçada por `?modo=avancado` ou `?modo=simples`.

## Linguagem

Toda frase gerada segue regras: percentuais são "frequência dos membros", nunca probabilidade; "chuva provável/possível/pouca chuva" deriva de limiares explícitos (≥70%, ≥40%); riscos citam limiar, data e número de modelos; nenhuma frase autoriza operação. Exemplo real produzido: "Há elevada concordância entre os modelos quanto à ocorrência de chuva amanhã (7 de 8 modelos com maioria de membros acima de 1 mm), com dispersão moderada no volume (médias por modelo de 3 a 19 mm)."

## Diretrizes aplicadas

Tipografia de sistema com hierarquia clara; cores discretas (azul para chuva, terracota para calor, ocre para vento) usadas apenas para tom, não como semáforo de decisão; espaçamento consistente; cartões com rótulo, valor, detalhe e nota de método; tabelas roláveis no celular; sem overflow horizontal; foco visível; `aria-live` nos resumos.

## O que falta (Fase 4/5)

Mapas com GOES-East de 10 min e IMERG (NASA GIBS), seletor de variável/horário com legendas quantitativas unificadas (já existentes para a previsão em grade), exportação CSV dos novos produtos, diagramas de confiabilidade reais quando houver pares, e um relatório imprimível para o produtor.
