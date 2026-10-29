# ADR 003 — IA restrita a fatos renderizados por código

Data: 29/10/2026. Versão: 2.2.0.

Problema: texto gerado pode alterar números, inventar precisão ou ser confundido com autorização agronômica. Alternativas: geração livre, validação apenas por palavras proibidas, ou seleção de fatos estruturados. Decisão: seleção de IDs de fatos conhecidos, com texto produzido por regras e avisos obrigatórios.

Justificativa: uma lista de palavras não garante fidelidade meteorológica. Consequência: a explicação inicial é deliberadamente limitada; análise narrativa de divergências está pendente. Provedor padrão none; Ollama opcional em loopback. Provedores externos ficam bloqueados enquanto não houver comprovação específica de gratuidade sem cobrança automática. Não ativar pagamento para contornar indisponibilidade.
