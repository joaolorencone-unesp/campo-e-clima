# Campo e Clima v1.4 — Como publicar

## Atualização da v1.3 (sem necessidade de API paga)

1. Extraia `Campo_e_Clima_v14_SOMENTE_ATUALIZACAO.zip`.
2. No GitHub Desktop, abra o repositório `joaolorencone-unesp/campo-e-clima` e escolha **Repository > Show in Explorer**.
3. Copie **o conteúdo** do ZIP para a raiz da pasta clonada, mantendo as subpastas `site/`, `docs/`, `tests/` e aceitando substituir arquivos existentes.
4. No GitHub Desktop, faça o commit `feat: mapas NASA GIBS, nuvens e bussola de vento v1.4`.
5. Clique em **Push origin** e confira em `https://github.com/joaolorencone-unesp/campo-e-clima/actions`.
6. Quando a implantação estiver verde, abra `https://joaolorencone-unesp.github.io/campo-e-clima/` e pressione **Ctrl+F5**.
7. Acesse **🛰 Mapas & nuvens**; experimente a camada `Nuvens totais` e avance hora a hora; altere para `NASA MODIS Terra` e selecione uma data de 1–3 dias atrás para visualizar imagem orbital, se disponível. Em **Vento & rajadas**, use a bússola da hora.

Nenhuma chave precisa ser criada. O botão de atualização do mapa consulta os nove pontos via Open-Meteo e respeita cache. O botão principal continua atualizando a previsão determinística; ensembles são coletados separadamente.

## Validação

- Testes Python e JavaScript automatizados + verificação de sintaxe.
- Retorno real das imagens NASA e da consulta 9 pontos: **validar no seu navegador**, porque este ambiente não alcança os serviços externos.
- Se a biblioteca Leaflet não carregar, confira conexão/CDN e use links NASA Worldview ou INPE.
- A licença do CPTEC/INPE limita a reprodução de seus produtos. Nesta versão há somente link ao visualizador.
- Não publicar secrets, tokens NASA Earthdata ou chaves antigas no repositório ou screenshots.
