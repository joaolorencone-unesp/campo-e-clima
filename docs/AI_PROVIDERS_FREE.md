# IA opcional e política de custo

Padrão: AI_PROVIDER=none, AI_ENABLE=0, AI_ALLOW_PAID=0, limite máximo 2 chamadas/dia e timeout de até 30 s. O programa funciona por regras sem IA externa.

| Adaptador | Estado |
|---|---|
| none | Implementado e validado sem rede |
| Ollama em 127.0.0.1:11434 | Implementado; Qwen3 4B configurável. Serviço não respondeu nesta máquina; inferência real não validada |
| OpenRouter / Groq / Gemini / SiliconFlow / Qwen hospedado | Adaptador de bloqueio explícito; nenhum endpoint chamado, chave cadastrada, plano alterado ou gratuidade presumida |

Um provedor externo somente pode ser habilitado em alteração posterior após comprovação das condições oficiais de gratuidade sem cobrança automática. AI_ALLOW_PAID não contorna o bloqueio. Não há tentativa em cascata entre provedores. Nenhum segredo entra em JavaScript.

Ollama não é instalado/iniciado pelo coletor e não expõe servidor público. Ausência do PC não interrompe Actions ou Pages. Referência consultada: https://docs.ollama.com/api/generate. Contrato de saída estruturada validado localmente; falha/cota/JSON inválido → regras.

Fontes gratuitas também têm restrições. Open-Meteo gratuito é não comercial com cotas e atribuição CC BY 4.0; um uso comercial não é automaticamente autorizado. Workflows usam somente runners padrão ubuntu-latest em repositório público. Confirmado nas documentações oficiais: https://docs.github.com/en/actions/reference/runners/github-hosted-runners e https://open-meteo.com/en/terms. Não foram consultadas ou alteradas configurações de faturamento da conta.
