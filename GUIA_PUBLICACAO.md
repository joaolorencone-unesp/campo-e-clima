# PUBLICAÇÃO PASSO A PASSO — Windows e GitHub Desktop

Este guia foi preparado para a conta **joaolorencone-unesp** e o repositório **campo-e-clima**.

## 1. Baixar e descompactar o ZIP
1. Salve o ZIP enviado pelo ChatGPT.
2. Clique com o botão direito → **Extrair tudo**.
3. Dentro do conteúdo extraído, devem aparecer diretamente: `README.md`, `site`, `scripts`, `tests`, `docs` e `.github`. **Não extraia de forma a deixar uma pasta extra dentro do repositório.**
4. No Windows Explorer: menu **Exibir → Mostrar → Itens ocultos**, para enxergar `.github` e `.gitignore`.

## 2. Clonar seu repositório pelo GitHub Desktop
1. Instale [GitHub Desktop](https://desktop.github.com/) e faça login em `joaolorencone-unesp`.
2. **File → Clone repository → GitHub.com → joaolorencone-unesp/campo-e-clima → Clone**.
3. Clique em **Show in Explorer**. A pasta clonada terá o nome `campo-e-clima` e uma pasta oculta `.git`.
4. Copie **o conteúdo** do ZIP extraído para **dentro** da pasta clonada, incluindo a pasta `.github`. **Não apague a pasta `.git` existente**.

## 3. Commit e envio
1. Volte ao GitHub Desktop. Na aba **Changes**, confira arquivos de `site/`, `scripts/`, `tests/`, `docs/` e `.github/workflows/pages.yml`.
2. No campo *Summary*, digite: `feat: painel Campo e Clima e coleta agendada`.
3. Clique em **Commit to main**, depois em **Publish branch** (para repositório vazio) ou **Push origin**.
4. Visite https://github.com/joaolorencone-unesp/campo-e-clima e confira se aparecem `README.md` e `.github/workflows/pages.yml`.

## 4. GitHub Pages
1. Acesse https://github.com/joaolorencone-unesp/campo-e-clima/settings/pages
2. Em **Build and deployment → Source**, selecione **GitHub Actions**.
3. Vá para https://github.com/joaolorencone-unesp/campo-e-clima/actions.
4. Se aparecer uma solicitação de permissão para workflows, habilite-os.
5. Abra **Collect and deploy Campo e Clima → Run workflow → Branch: main → Run workflow**.
6. Abra a execução. A sequência esperada é: checkout, dependências, **9 testes**, coleta, artifact, deploy. Confirme o visto verde e verifique as mensagens do coletor.
7. Acesse o site: https://joaolorencone-unesp.github.io/campo-e-clima/

## 5. Atualização a cada 30 minutos
O GitHub Actions possui agendamento em UTC (`7,37 * * * *`). A execução é aproximada e pode atrasar ou ser suspensa. Cada execução faz uma **nova consulta** à Open-Meteo e publica um JSON atualizado. O painel verifica esse JSON automaticamente a cada 30 min **enquanto estiver aberto** e mostra o carimbo da última coleta. O botão **Consultar última coleta** não dispara coleta no servidor.

## 6. Se algo der errado
| Sintoma | Verificação e ação |
|---|---|
| Erro 404 no site | Checar Settings → Pages e execução de deploy com visto verde; conferir URL com nome de usuário correto |
| Não aparece workflow | Confirmar que `.github/workflows/pages.yml` foi copiado e enviado para `main`; checar se Actions estão habilitadas |
| Falha em testes | Abrir etapa Unit tests; enviar o erro integral ao ChatGPT |
| Erro HTTP Open-Meteo | Abrir etapa Collect forecasts; conferir disponibilidade de modelos, limites da API ou conectividade; reexecutar depois |
| Atualização aparece antiga | Conferir timestamp no painel e a última execução em Actions; erro não vira dado novo |
| Gráficos não aparecem | Verificar conectividade com CDN do Plotly; as tabelas continuam legíveis sem os gráficos |
| GitHub bloqueou Pages | Verificar permissões administrativas e políticas da conta/repositório público |

## 7. Próximas etapas técnicas
Após a primeira publicação confirmada, conectar Guia Clima/INMET, construir arquivo de observações, calibrar ensembles, integrar alertas oficiais e melhorar as abas de pulverização e máquinas. **Não trate o MVP como previsão validada localmente.**
