# Campo e Clima v1.5 — correção de ensembles em outras coordenadas

## Problema corrigido

Na v1.4, o navegador iniciava até **16 consultas pesadas** para uma localidade personalizada (até oito consultas de chuva/rajadas e oito de variáveis conjuntas para pulverização). Falhas podiam resultar em um resumo vazio armazenado temporariamente e apresentado como "ensembles em cache"; os gráficos de probabilidade ficavam vazios apesar de a previsão determinística funcionar.

## Alterações

1. **Chuva primeiro:** consultar os oito ensembles independentes de chuva separadamente, com no máximo duas solicitações simultâneas. Os modelos são divulgados assim que devolvem dados diários completos, sem aguardar todos.
2. **Recuperação de timeout:** quando a consulta de sete dias termina por timeout, tentar apenas uma consulta mais leve de quatro dias. Mostrar claramente a cobertura parcial.
3. **Sem cache vazio:** somente dados com pelo menos um modelo de chuva válido podem entrar no cache de ensembles. Um erro 429 interrompe novas chamadas e ativa uma pausa de três minutos em caso de falha total.
4. **Pulverização sob demanda:** variáveis conjuntas (temperatura, UR, vento, direção, rajada, chuva) são consultadas separadamente ao abrir a aba de pulverização de um ponto personalizado. O número de modelos completos é independente do número de modelos válidos de chuva. Tentativas malsucedidas têm intervalo de dez minutos antes de outra requisição.
5. **Previsão alternativa honesta:** se não houver ensembles, os gráficos mostram chuva determinística e probabilidade horária fornecida pela **Forecast API** com legendas explícitas, nunca percentuais multimodelo fictícios.
6. **Menos cartões vazios:** tabelas e gráficos dependentes exclusivamente dos ensembles ficam ocultos até existir uma amostra válida.
7. **Diagnóstico de disponibilidade:** estado de cada modelo e motivo da falha ficam visíveis na aba Qualidade & fontes.
8. **Cache do navegador:** os arquivos `app.js` e `location.js` usam `?v=15` para não carregar código antigo após publicação.

### Instalação pelo GitHub Desktop

1. Baixe o ZIP `Campo_e_Clima_v15_SOMENTE_ATUALIZACAO.zip`.
2. Extraia e copie **o conteúdo interno** para a pasta clonada do repositório `campo-e-clima`, substituindo os arquivos existentes e preservando as pastas.
3. No GitHub Desktop, faça o commit `fix: ensembles por coordenadas e fallback transparente v1.5`.
4. Clique em **Push origin** e acompanhe a execução em `https://github.com/joaolorencone-unesp/campo-e-clima/actions`.
5. Depois de uma execução verde, acesse `https://joaolorencone-unesp.github.io/campo-e-clima/?lat=-14.408&lon=-56.446&name=Diamantino-MT` e pressione **Ctrl + F5**.

### O que você deve ver

- Após selecionar Diamantino, as primeiras estimativas de chuva determinística aparecem imediatamente.
- Na aba **Chuva & ensembles**, um aviso informa quantos modelos já foram consultados e quantos retornaram membros válidos.
- Modelos que responderam são exibidos progressivamente; quando um modelo falha, o site não apaga os que deram certo.
- Se a API rejeitar todas as chamadas, os gráficos mostram apenas as informações da Forecast API, identificadas como tal, e não afirmam que existe probabilidade multimodelo.
- Na aba **Qualidade & fontes**, modelos indisponíveis mostram a causa.
- A aba **Pulverização** utiliza as variáveis conjuntas disponíveis para o ponto. Se não existirem membros completos, a frequência probabilística é marcada como indisponível.

### Como identificar erros de rede

Abra **F12 → Network (Rede)** e filtre por `ensemble-api.open-meteo.com`. Inspecione o status:

- **200**: a requisição respondeu; o código ainda valida se há 24 horas numéricas por membro.
- **429**: limite de requisições; evite clicar repetidamente, aguarde e tente novamente.
- **503**: serviço indisponível temporariamente.
- **CORS / Failed to fetch**: o navegador não conseguiu acessar a resposta. A Forecast API pode continuar funcional.

### Testes e limitações

- Testes unitários Python e JavaScript passaram, incluindo casos simulados de resposta parcial, HTTP 429 e timeout.
- A consulta real para Diamantino precisa ser verificada **no GitHub Pages após publicação**. Não há garantia de que a API gratuita responderá a todos os modelos em todas as ocasiões.
- O acesso público gratuito da Open-Meteo está sujeito aos limites e termos de licença aplicáveis; esta correção reduz, mas não elimina, a dependência das cotas por navegador/IP.
- As frequências dos membros NÃO são probabilidades calibradas e NÃO autorizam pulverização.
- GitHub Pages é estático: **sem backend próprio, o navegador não pode garantir disponibilidade de todos os ensembles para coordenadas arbitrárias**. Se o uso crescer, considere um coletor gratuito com cache geográfico e/ou um conjunto de localidades previamente cadastradas.
