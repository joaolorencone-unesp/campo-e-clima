# Campo e Clima v1.1 — Pulverização por hora e observações INMET

## Situação de verificação

- **Dados de estação S735:** o catálogo público `https://apitempo.inmet.gov.br/estacoes/T` indica **Naviraí (Faz. Santa Helena do Pindo)**, código **S735**, entidade **SEMADESC-MS**, status **Operante**, latitude -22.899909, longitude -53.869219, altitude 303 m. Aproximadamente 37,6 km da sede de referência (-23.065,-54.190). **Operante no cadastro não prova que há leituras horárias disponíveis no endpoint.**
- **Observação horária da S735:** coletor experimental tenta o endpoint público `https://apitempo.inmet.gov.br/estacao/<inicio>/<fim>/S735` com três dias de intervalo, valida `CD_ESTACAO`, `DT_MEDICAO`, `HR_MEDICAO` (UTC), `TEM_INS`, `UMD_INS`, `CHUVA`, `VEN_VEL`, `VEN_RAJ`, `VEN_DIR`, converte vento m/s para km/h e timestamps para UTC-4. A rota pode bloquear cliente externo ou não estar habilitada para esta estação: quando isso ocorrer, apresenta `unavailable` e links oficiais para consulta, sem inventar medições. **Não foi possível verificar resposta real desse endpoint no ambiente de desenvolvimento.**
- Fontes alternativas gratuitas e oficiais: [Tabela de Estações](https://tempo.inmet.gov.br/TabelaEstacoes), [dados históricos automáticos INMET](https://portal.inmet.gov.br/dadoshistoricos/) e [BDMEP](https://bdmep.inmet.gov.br/). Se necessário, desenvolver importador dos CSVs oficiais anuais.

## Previsão por hora × frequência dos cenários

**Previsão determinística:** temperatura, UR, vento 10m, rajada, VPD e chuva `t`/`t+1...t+3` a partir da Open-Meteo Forecast. São estimativas pontuais de modelo em grade (não observações nem probabilidade de segurança).

**Frequência multimodelo:** classificar o conjunto T, UR, vento, direção, rajadas e chuva de **cada membro** da Open-Meteo Ensemble no mesmo horário; ponderar cada modelo válido igualmente, e seus membros válidos igualmente. Evitar multiplicar probabilidades marginais. Produzir quatro classes:

- `passa`: membro passa filtros meteorológicos experimentais no período diurno de triagem (07–17h); nunca significa operação liberada ou categoria científica de “excelente”.
- `marginal`: próximo aos filtros experimentais; exige conferência do produto e do campo.
- `restrito`: falha em um ou mais filtros meteorológicos, durante dia ou noite.
- `indeterminado`: período 18h–06h que não falha nos filtros numéricos, mas não tem evidência de estabilidade/inversão; nunca mostrar como hora verde/candidata.

**Atenção:** o critério 07–17h é uma precaução de triagem, não detecção de inversão, nem substitui horários reais de amanhecer/pôr do sol. A inversão também pode ocorrer em outras horas, inclusive no início da manhã. Nenhuma classificação valida deriva para receptores ou liberação legal.

**Resolução:** interface apresenta hora a hora, mas cada modelo pode fornecer dados com resolução **nativa de 3–6h interpolada para 1h**. A interpolação não adiciona informação física. A frequência do ensemble não está calibrada e não deve ser chamada de chance real de aplicação excelente/segura. Para maior confiabilidade, usar sensores locais a altura relevante, anemômetro e registrador de rajadas, observar nuvens/estabilidade e seguir bula.

**Chuva nas próximas 3h:** para previsão horária indexada em `t`, a precipitação em `t` se refere ao período anterior a `t`. Portanto, a janela de 3h **futuras** para avaliação a partir de `t` usa índices `t+1`, `t+2`, `t+3`. Horários incompletos são excluídos, não zerados.

**Janela de 2h:** o mesmo membro precisa satisfazer ambas as horas consecutivas. Se uma hora for restrita, janela restrita. Se nenhuma restrita, porém uma indeterminada, janela indeterminada. Ranking elimina janelas noturnas e precisa de pelo menos dois horários contíguos válidos.

## Fontes e evidências

- [INMET Estações Automáticas](https://portal.inmet.gov.br/servicos/esta%C3%A7%C3%B5es-autom%C3%A1ticas), dados horários disponibilizados via portal e arquivos históricos.
- [INMET catálogo público](https://apitempo.inmet.gov.br/estacoes/T).
- [Open-Meteo Ensemble](https://open-meteo.com/en/docs/ensemble-api), variáveis e resolução temporal.
- [DJI Agras T100 Manual](https://www.dji.com/downloads/products/t100), a resistência da aeronave ao vento não equivale a condição segura de pulverização. O fabricante informa operação com ventos abaixo de 6 m/s e recomendação abaixo de 3 m/s para aplicações com maior suscetibilidade à deriva/fitotoxicidade, sujeitas a instruções adicionais da bula e legislação.

## Limites e evolução

Próximos passos para maior precisão real: importar observações de estação com timestamps validados, verificar cobertura do talhão e desempenho local com séries pareadas; calibrar frequências de chuva e vento por Brier Score e CRPS quando existirem amostras suficientes; configurar perfis por produto/bula em vez de usar um critério único de VPD ou rajada. O módulo atual **não substitui medições no campo nem validação dos parâmetros operacionais DJI T100**.
