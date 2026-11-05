# Design v4 — identidade oficial, modo simples em formato de jornal e satélite

Versão 4.0.0 (05/11/2026). Complementa o [Design v3](DESIGN_V3.md): a estrutura de cinco áreas e os dois níveis de uso (simples/avançado) permanecem; muda o que o produtor vê primeiro, a identidade visual e os mapas.

## 1. Identidade visual com o logo oficial

Fonte: três arquivos do logo "Projeto Campo e Clima — Boletim Meteorológico" enviados pelo pesquisador (horizontal, vertical e ícone). Foram convertidos para `site/static/brand/` com fundo transparente: `logo-horizontal.{png,webp}` (1820×573), `logo-vertical.{png,webp}` (1007×1244), `icone.{png,webp}` (1155×1184) e `icone-{16,32,64,180,192,512}.png`.

Paleta extraída do próprio logo (poucas cores, uso fixo):

| Token CSS | Cor | Uso |
|---|---|---|
| `--bn` | navy `#0f2a66` | texto de títulos, números grandes, navegação ativa |
| `--bg1` | verde `#0f7a3b` | ação primária, bordas de destaque, linha do cabeçalho e rodapé |
| `--bg1-leaf` | verde-folha `#22a327` | acento pontual (o "e" do logo) |
| `--bsky` | azul-céu `#0b8df0` | chuva, temperaturas mínimas, chips de satélite |
| `--bred` | vermelho `#e0101f` | somente alertas e temperaturas máximas |
| `--bbg` | fundo `#f4f7f5` | fundo da página; cartões em branco |

Regras: o vermelho não aparece em elementos decorativos; verde e navy carregam a hierarquia; o azul só marca água/frio. Os tokens antigos (`--blue`, `--green`, `--red`, `--bg`, `--ink`) passam a apontar para os novos valores, de modo que as telas anteriores herdam a paleta sem reescrita.

Cabeçalho: logo horizontal em telas largas, ícone em telas estreitas (≤760 px); o `<h1>` continua no DOM (acessibilidade e busca) mas fica visualmente oculto porque o logo já traz o nome. Favicons 16/32, `apple-touch-icon` 180, `manifest.webmanifest` (ícones 192/512, `display: standalone`) para "adicionar à tela inicial" no celular, `theme-color` verde. Rodapé com o ícone, a natureza não comercial do projeto e os créditos obrigatórios (Open-Meteo CC BY 4.0; NASA GIBS/ESDIS; INMET; Embrapa Guia Clima).

## 2. Modo simples em formato de jornal

Objetivo: números grandes e informação direta, sem gráficos densos. Tudo é derivado do JSON já publicado; nenhum valor é inventado e uma célula sem produto mostra "—".

### 2.1 Quadro "A semana na fazenda" (`site/static/weekly_board_v40.js`)

Uma linha por dia (hoje até 7 dias) com: dia da semana; ícone (sol, parcialmente nublado, nublado, chuva, chuva forte, tempestade possível) escolhido por regras explícitas sobre fração de membros >1 mm e >20 mm, mediana, nebulosidade determinística e CAPE; mínima (azul) e máxima (vermelho) determinísticas; **mediana da chuva do ensemble** em destaque; faixa P10–P90; fração de membros com chuva (rotulada como fração de membros, não probabilidade calibrada) e número de modelos; rajada máxima determinística com a fração de membros >30 km/h; concordância entre modelos (alta/média/baixa). Quando a coleta multimodelo determinística existe, a célula da faixa mostra também "modelos: mín–máx mm · n/N com chuva". Tocar em um dia abre o detalhe de 3 em 3 horas (temperatura, chuva, vento). Se não há ensemble para um dia, o valor determinístico aparece com asterisco.

### 2.2 Tabela "Próximas semanas"

| Linha | Fonte | O que mostra | Confiança exibida |
|---|---|---|---|
| Esta semana | acumulado de 7 dias por trajetória de membro | P50, faixa P10–P90, fração de membros acima de 25 mm | média a alta |
| Próxima semana | determinístico dias 8–14 | soma apenas se houver ≥5 dias com previsão; caso contrário "—" | baixa |
| Semanas 3+ | GEFS estendido (um só modelo, 15–35 dias) | soma das médias diárias por semana ("≈"), só com ≥5 dias | baixa |
| Tendência | ECMWF EC46/SEAS5 (médias semanais, ~36 km) | média semanal na unidade da API e sinal da anomalia | tendência |

A legenda diz explicitamente que, além de 7 dias, não existe chuva em dias específicos: são tendências.

### 2.3 Boletim do dia (`scripts/ai_bulletin.py`, `site/static/bulletin_v40.js`)

Texto curto gerado a cada coleta a partir de uma ficha de fatos (chuva nas próximas 24 h, mediana e faixa de hoje/amanhã, concordância, acumulado, dias secos, rajadas, avisos INMET, frescor). O texto por regras existe sempre. Se um provedor gratuito de LLM estiver configurado (variável de repositório `AI_BULLETIN_PROVIDER`; padrão `none`), o modelo só pode reescrever os fatos: todo número do texto é conferido com a unidade correspondente contra a ficha, palavras de promessa ("garantido", "liberado", "autorizado", "com certeza") são rejeitadas, textos longos são rejeitados e qualquer falha devolve o texto por regras. O cartão mostra a origem ("texto por regras" ou "IA validada", com provedor e modelo), a hora de geração e um aviso para conferir os números no painel. Coordenadas personalizadas não têm boletim e o cartão some.

### 2.4 Cartão "Estação física mais próxima"

Para Naviraí e Diamantino, mostra o último dia completo medido na estação (máxima, mínima, chuva) e a conferência do dia anterior: chuva e máxima medidas contra o que o melhor modelo previa com um dia de antecedência. Os dados vêm de `site/data/stations/index.json` (ver [Estações e calibração](ESTACOES_E_CALIBRACAO_V4.md)); sem o arquivo, o cartão fica oculto.

### 2.5 O que saiu do modo simples

O mapa de nove amostras em grade ("bolinhas") foi retirado do modo simples (`nav_v30.js`: abas visíveis `overview`, `rain`, `agro`, `observations`). A tabela "Sete dias" antiga virou avançada, pois o quadro semanal a substitui.

## 3. Modo avançado: satélite e comparação de modelos

- **Satélite GOES-East e IMERG (NASA GIBS)** no mapa: GeoColor (nuvens dia/noite, 1 km, 10 min), infravermelho banda 13 e massas de ar (2 km, 10 min) e taxa de chuva IMERG (30 min). Controle de tempo com 18 instantes, botão "Animar nuvens", recuo automático quando a imagem mais recente ainda não foi publicada (latência típica 30–60 min; IMERG ~4 h). A legenda diz "nuvens observadas, não previsão".
- **Modelos determinísticos lado a lado** (aba Precisão): ECMWF IFS, ECMWF AIFS, GFS, GraphCast, ICON, GEM, ARPEGE, UKMO e JMA no mesmo ponto, com tabela por dia (chuva, mín–máx, rajada) e faixa entre modelos; modelos rejeitados pelo provedor aparecem com o motivo.
- **Estações físicas** (aba Observações): últimos dias medidos, melhor modelo por variável, matriz de erro por antecedência, viés por hora do dia, série medido × previsto e previsão atual bruta × corrigida.

## 4. Princípios mantidos

- Dado faltante nunca vira zero: dia de chuva incompleto aparece como "incompleto".
- Fração de membros não é probabilidade calibrada; a legenda repete isso onde a fração aparece.
- Observação e previsão nunca se misturam na mesma cor ou título; satélite é passado, modelo é futuro.
- Nenhuma frase do painel ou do boletim autoriza pulverização ou operação agrícola.
- Correções por estação aparecem ao lado do valor bruto, nunca no lugar dele.

## 5. Fora desta versão

Ícones animados (Meteocons) e biblioteca de dimensão temporal (Leaflet.TimeDimension) foram avaliados e não adotados para evitar dependências; mapa previsto de alta resolução por tiles próprios (ECMWF Open Data) continua como proposta; CPTEC MERGE/SAMeT, radar DECEA, CEMADEN e relâmpagos estão listados em [Fontes v4](FONTES_V4.md) como próximos passos. Capturas de tela ficam em `docs/RELEASES/v4/` quando a validação em navegador é executada.
