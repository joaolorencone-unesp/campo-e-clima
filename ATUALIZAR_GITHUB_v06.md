# Atualização para Campo e Clima v0.6

1. **Faça backup** do repositório atual (GitHub Desktop já mantém histórico de commits).
2. Baixe `Campo_e_Clima_v06_SOMENTE_ATUALIZACAO.zip` e **extraia**.
3. Abra GitHub Desktop, repositório `joaolorencone-unesp/campo-e-clima`, `Repository → Show in Explorer`.
4. Copie todas as pastas e arquivos extraídos para a **raiz** do repositório, mantendo `.github`, `scripts`, `site`, `tests`, `data`, `docs`. **Substitua os arquivos existentes.**
5. No GitHub Desktop: commit `feat: integrar exportacao Embrapa, CPTEC, NASA e previsao estendida v06` e `Push origin`.
6. Abra https://github.com/joaolorencone-unesp/campo-e-clima/actions . Confira `Collect forecasts` e `Publish GitHub Pages` em verde. **Algumas integrações podem aparecer como indisponíveis sem fazer o workflow inteiro falhar.** Leia status na aba fontes.
7. Abra https://joaolorencone-unesp.github.io/campo-e-clima/ e pressione Ctrl+F5. Confira a aba **Observações & fontes**, a tabela de estado das APIs e a exportação provisória da Embrapa.
8. Para OpenWeather: crie/ative a chave One Call 3.0, acesse **GitHub → Settings → Secrets and variables → Actions → New repository secret**, nome exato `OPENWEATHER_API_KEY`, valor sua chave. **Nunca cole a chave no código, em prints, nem no chat.** Reexecute o workflow e confira o status da fonte.
9. Se NASA POWER/ECMWF extended falharem, veja os erros nas fontes e no log do GitHub; poderão falhar por cobertura/plano/quota, sem invalidar os oito ensembles.
10. **Confirme a estação selecionada na exportação**: o arquivo HTML `.xls` não contém código explícito e tem seis registros fora do período esperado. Até confirmar, o painel exibirá tudo como PROVISÓRIO. Não calcule habilidade preditiva contra uma série de estação não verificada.

Os produtos lentos usam cache diário; ao atualizar o código durante o mesmo dia, se for preciso renovar esse cache, abra Actions → Caches e limpe somente a chave `slow-sources-v06` correspondente à data, ou aguarde a coleta do próximo dia. Não é necessário remover cache para atualizar dados de meia hora.

### Limitações técnicas
- GitHub Actions é agendado, mas pode atrasar; o botão atualiza **leitura** dos dados, não força uma nova coleta.
- INMET/CPTEC podem bloquear a origem do GitHub ou retornar formato diferente. O código documenta erro sem inventar avisos.
- Satélite DSAT, GPM/IMERG e SoilGrids WCS ainda precisam de processamento geoespacial/licenças ou conta; o site fornece fonte, status e links, não falsos pixels/dados.
- Não há calibração local da precisão até validarmos a estação e preservarmos previsões emitidas.
