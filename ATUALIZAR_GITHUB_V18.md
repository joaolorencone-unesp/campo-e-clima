# Atualização rápida — Campo e Clima v1.8

1. Baixe e extraia `Campo_e_Clima_v18_SOMENTE_ATUALIZACAO.zip`.
2. Abra **GitHub Desktop → campo-e-clima → Repository → Show in Explorer**.
3. Copie **o conteúdo** extraído para a pasta do repositório, preservando as subpastas `.github`, `scripts`, `site`, `tests` e `docs`, aceitando substituir arquivos.
4. Volte ao GitHub Desktop, faça o commit `fix: janela futura, membros validos e pulverizacao v1.8` e clique **Push origin**.
5. Acesse https://github.com/joaolorencone-unesp/campo-e-clima/actions e confirme a execução concluída com sucesso.
6. Abra https://joaolorencone-unesp.github.io/campo-e-clima/ e pressione **Ctrl+F5**.
7. Confira o novo aviso `Horizonte horário determinístico...` perto do topo, o inventário `válidos / declarados` em **Qualidade** e `Triagem meteorológica numérica / Verificações operacionais pendentes` na aba **Pulverização**.

### Se um gráfico permanecer vazio

Confira `Qualidade & fontes` e o JSON publicado `site/data/latest.json`. Membros indisponíveis não são preenchidos com zero; falhas de API não significam ausência de risco.

**Não cole chaves nem tokens no repositório ou no chat.** Nenhuma credencial nova é requerida por esta atualização.
