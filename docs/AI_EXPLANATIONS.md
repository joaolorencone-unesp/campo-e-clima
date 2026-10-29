# Explicações fundamentadas

LLM só pode selecionar/ordenar IDs de fatos estruturados públicos. O código renderiza o texto e todos os valores; o modelo não calcula meteorologia nem redige números novos. A saída deve conter apenas fact_ids, sem IDs desconhecidos, duplicações ou campos extras. Avisos obrigatórios não podem ser removidos pelo provedor.

Registrar provider, effective_provider, model, prompt_version, horário, input_sha256, texto final, validação, consumo quando informado, erro e limitações em ai_explanations. Provedor/modelo não são versões meteorológicas. Quando Ollama não informar digest/versionamento do modelo, essa identificação permanece limitada ao nome retornado; não inventar versão imutável.

Nesta versão, os boletins explicam quantidade de produtos/pares, ausência de calibração e limites de aplicação. Explicações livres sobre divergência entre modelos ou mudanças entre rodadas não estão implementadas. Nenhuma recomendação de altura, velocidade, gotas, dose ou autorização é produzida.

`python -m scripts.science_cli explain --db runtime/science_rebuilt.sqlite`. Apenas pontos públicos cadastrados entram nos fatos; campos privados do formulário agrícola não são enviados. O painel permanece funcional com provedor none.
