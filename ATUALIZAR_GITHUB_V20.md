# Campo e Clima v2.0 — Mapas meteorológicos interativos e radar

Versão construída em cima dos arquivos **publicados na versão 22 do GitHub Pages** (28/10/2026). Não reinstale ZIPs antigos por cima desta atualização.

## Como publicar

1. Extraia **Campo_e_Clima_v20_MAPAS_ATUALIZACAO.zip**.
2. No GitHub Desktop, escolha `joaolorencone-unesp/campo-e-clima` > Repository > Show in Explorer.
3. Copie **o conteúdo** da pasta extraída para a raiz do repositório, substituindo os arquivos e mantendo as pastas `site`, `tests`, `.github` e `docs`.
4. Commit: `fix(maps): radar animation, source timestamps and legends v2.0`.
5. Clique em Push origin e aguarde o GitHub Actions verde. Abra a aba Mapas & nuvens e faça Ctrl+F5.
6. Valide manualmente: selecione Radar observado, clique em Reproduzir; a barra deve avançar do quadro 1 ao mais recente. Teste Anterior, Próximo, Pausar, mudança de zoom. Alterne para Modo previsão: radar some e os pontos previstos retornam. Selecione cada variável e confira legenda e horário.

**Atenção:** GitHub Actions verde verifica testes de código, não comprova cobertura de radares em Naviraí ou que o provedor de tiles esteja disponível no navegador. O serviço externo pode bloquear conexões ou atingir limite de requisições.

## Melhorias

- Nova lógica de vídeo: mantém a imagem anterior até a seguinte carregar, pré-carrega somente um próximo quadro, mostra progresso e permite controles Anterior/Próximo/Reproduzir/Pausar/Velocidade. Uma reprodução termina no quadro mais recente; outra pode ser iniciada do começo.
- Cada quadro exibe **data/hora local, data/hora UTC, posição na sequência e idade aproximada**. Horário do quadro composto pode não corresponder exatamente a cada observação de radar individual.
- Escala RainViewer **Universal Blue (2)** com amostras de 10, 20, 30, 40, 50 e 60 dBZ e fonte. Esses valores são **refletividade**, não milímetros de chuva por hora; sem relação Z–R calibrada não converter.
- Quando Radar está ativo, **satélite NASA e pontos previstos da Open-Meteo são ocultados**, impedindo mistura de cores. Ao desativar o radar, reaparecem previsão e, se escolhido, mosaico NASA.
- A previsão futura para 48 horas mantém nove pontos em grade e agora oferece: temperatura, umidade relativa, rajadas, probabilidade de precipitação fornecida pela Forecast API, CAPE e camadas já existentes. Variáveis ausentes aparecem como **sem dados**.
- Legenda da previsão com cores, unidades e faixas; horário local e UTC de cada quadro previsto.
- Erros e atrasos do radar não devem ser interpretados como tempo seco; se falhar uma atualização, a última sequência em cache é explicitamente descrita como potencialmente **desatualizada**.
- Nova verificação offline no GitHub Actions com simulação do carregamento assíncrono dos quadros.

## Fontes, rigor e limites

- RainViewer API: https://www.rainviewer.com/api/weather-maps-api.html
- RainViewer paleta exata: https://www.rainviewer.com/api/color-schemes.html
- RainViewer atualização de condições de uso: https://www.rainviewer.com/api/transition-faq.html
- Open-Meteo Forecast: https://open-meteo.com/en/docs
- NASA GIBS: https://nasa-gibs.github.io/gibs-api-docs/access-basics/
- GOES/INPE (acesso externo): https://www.cptec.inpe.br/dsat/
- INMET (consulta externa): https://satelite.inmet.gov.br/

A RainViewer gratuita é destinada a usos pessoais/educacionais de pequena escala, tem limite de requisições e NÃO fornece radar futuro. O mapa de previsão da Open-Meteo NÃO é rastreamento de tempestades. As camadas são de grade com resolução limitada; não devem ser usadas isoladamente para liberar pulverização.
