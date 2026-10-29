# Reprodução e Windows

Python 3.11+ recomendado. PowerShell, dentro da pasta do repositório:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-science.txt
New-Item -ItemType Directory .test_runs -Force
.\.venv\Scripts\python.exe -X utf8 -m pytest -q --basetemp .test_runs/nova_execucao
.\.venv\Scripts\python.exe -X utf8 -m scripts.science_cli collect --location all
.\.venv\Scripts\python.exe -X utf8 -m scripts.science_cli archive --location all
.\.venv\Scripts\python.exe -X utf8 -m scripts.science_cli rebuild --output runtime/novo.sqlite
.\.venv\Scripts\python.exe -X utf8 -m scripts.science_cli evaluate --db runtime/novo.sqlite
.\.venv\Scripts\python.exe -X utf8 -m scripts.science_cli train --db runtime/novo.sqlite
.\.venv\Scripts\python.exe -X utf8 -m scripts.science_cli explain --db runtime/novo.sqlite
.\.venv\Scripts\python.exe -m http.server 8776 --bind 127.0.0.1 --directory site
```

Abrir http://127.0.0.1:8776. A v2.2 não precisa da aplicação v0.3/FastAPI nem altera as tarefas Windows já instaladas. O .bat fornecido só inicia servidor local enquanto aberto; não registra tarefas persistentes.

Testes JavaScript: executar os arquivos test_*.cjs e frontend_smoke.cjs com Node. O teste browser_v22.cjs requer Playwright e um Edge local (EDGE_EXECUTABLE configurável); testa um contexto isolado, sem perfil pessoal. Screenshots e resultado estão em docs/RELEASES. Não serve fixtures sintéticas como forecasts.

Versões: sistema 2.2.0 (candidato), pipeline 1.0.0, esquema 2, dataset 1.0.0, fórmula científica 1.0.0 e explicação facts-only-1.0.0. Mudanças futuras exigem novas versões/manifestos, sem alterar silenciosamente entradas arquivadas. requirements-lock-v22.txt registra o ambiente real da validação.

A migração 002 compacta IDs repetidos de rodada em uma tabela de chaves inteiras e usa WITHOUT ROWID nas tabelas de valores. O hash canônico permanece em forecast_runs e no Parquet de chaves. Para limitar o banco analítico local, reconstruir com `--since AAAA-MM-DD` (data UTC de coleta); todos os RAW permanecem no arquivo durável.

Para repetir exatamente o ambiente local em Windows/Python 3.13, instalar `requirements-lock-v22.txt`. O workflow Linux/Python 3.11 resolve `requirements-science.txt`; a execução no GitHub ainda não foi validada.
