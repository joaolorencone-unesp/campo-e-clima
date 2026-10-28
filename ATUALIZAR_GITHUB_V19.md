# Publicar Campo e Clima v1.9 no GitHub

1. Faça backup ou um commit da versão atual.
2. Extraia `Campo_e_Clima_v19_SOMENTE_ATUALIZACAO.zip` e copie **o conteúdo extraído** para a raiz do repositório `campo-e-clima`. Preserve as pastas `site/static`, `scripts/sources`, `tests` e `.github/workflows` (a pasta `.github` pode estar oculta no Windows).
3. No GitHub Desktop, veja os arquivos alterados, faça o commit `feat: avisos compactos, radar e historico diario v1.9` e clique em **Push origin**.
4. Abra https://github.com/joaolorencone-unesp/campo-e-clima/actions e confira o workflow `Collect and deploy Campo e Clima`.
5. Abra https://joaolorencone-unesp.github.io/campo-e-clima/ e faça `Ctrl + F5`.
6. Confira Naviraí: avisos agrupados, aba **Mapas & nuvens** com `Radar observado`, pontos circulares, ausência da aba **Máquinas & solo**, e **Observações & fontes** com novo histórico NASA × ERA5. Depois confira Diamantino usando `?lat=-14.408&lon=-56.446&name=Diamantino-MT` e verifique que observações municipais de Naviraí não aparecem como suas.

**Importante:** não suba sua chave OpenWeather em arquivos de código, README ou `.env` público. A chave anterior apareceu em uma conversa; revogue-a no provedor. Se ativar a integração gratuita existente, use uma chave nova em **Settings → Secrets and variables → Actions → New repository secret** com nome `OPENWEATHER_FREE_API_KEY`. O serviço de cinco dias/três horas é opcional e não compõe os oito ensembles.

**Falhas previstas e seguras:** o INMET S735 pode não responder automaticamente; ERA5/NASA podem sofrer atraso ou indisponibilidade; radar RainViewer pode não cobrir Naviraí. Nunca interpretar ausência de dados como 0 mm, 0% de chuva, ausência de alerta ou liberação de aplicação. ECMWF sazonal pode continuar indisponível por timeout apesar do tratamento de mensagem.

Metodologia, limites e estudos em `docs/MELHORIAS_V19.md`.
