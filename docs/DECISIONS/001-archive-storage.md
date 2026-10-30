# ADR 001 — arquivo público incremental

Data: 28/10/2026. Versão: 2.2.0. Origem: v2.1, commit e1241e208033baf3260d86c8ba4b03e56ba92300.

Problema: `latest.json` contém resumos, não os membros originais; artifacts e cache expiram.
Alternativas: artifacts (temporários), banco no Pages (incompatível), serviço pago (vedado), branch de arquivos imutáveis (adotada).

Estimativa **antes da implementação do arquivo**, não medição: 8 modelos × cerca de 51 membros × (168 h × 2 variáveis + 80 h × 6 variáveis) ≈ 333 mil valores/local/coleta. Modelos têm contagens e coberturas diferentes. Admitindo 0,7–2 MB comprimidos por local/coleta, duas localidades e quatro arquivos/dia: **168–480 MB/30 dias; 2,0–5,8 GB/ano**, sem contar histórico Git. Essa faixa será substituída por projeção medida; não representa promessa de espaço gratuito indefinido.

Decisão: preservar respostas já obtidas na coleta, comprimidas por SHA-256, e um manifesto por local/janela UTC de 6 h em `weather-archive`. O banco e Parquet são reconstruíveis localmente; não colocar o banco no Pages. Não fazer nova consulta para arquivar. Manter somente JSON público compacto no Pages. Usar limitador conservador de 750 MB de arquivos no checkout do arquivo e 25 MB por lote; ao exceder, registrar falha e manter previsão principal. Git pode consumir mais espaço que a soma dos arquivos: acompanhar `git count-objects -vH`, tamanho remoto e projeção; a trava não é garantia de cota remota.

Consequências: será necessária uma decisão explícita de migração/particionamento gratuito antes de atingir o limite. Não apagar histórico, contratar armazenamento ou fingir durabilidade ilimitada. Quatro arquivos/dia são o alvo enquanto houver espaço e execução; GitHub schedule pode atrasar/pular execuções. Concorrência única, sem force-push. Falha de arquivo é visível no relatório.

Fontes consultadas: [limites Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits), [limites Actions](https://docs.github.com/en/actions/reference/limits), [termos Open-Meteo](https://open-meteo.com/en/terms). O uso gratuito Open-Meteo verificado é não comercial; instituição pública/pesquisa aberta não autoriza transformar a API em serviço comercial.

## Revisão de capacidade — 29/10/2026

`scripts/science/storage.py` mede arquivos, objetos comprimidos e objetos Git (loose + pack) no checkout dedicado. Exibe avisos no Actions e persiste o estado em `public/archive_status.json`, exportado para `site/data/archive_status.json`. Não há nova promessa de capacidade ilimitada nem alerta por e-mail. Limiares do arquivo: 50% aviso inicial, 70% atenção, 85% rotação necessária, 95% crítico, 100% bloqueio de novas capturas. Orçamento Git: 1 GB, com rotação a partir de 85% e bloqueio quando atingido; a checagem é anterior ao lote e pode haver pequeno excedente pelo próprio commit/relatório. O orçamento de arquivos permanece 750 MB e o lote máximo 25 MB.

Capturas usam gzip nível 9 e objetos deduplicados pelo SHA-256. A projeção depende da taxa observada; com menos de quatro manifests cobrindo um dia, retorna desconhecido. A estimativa de 0,90 GB/ano mencionada na auditoria não é garantia: imports, cobertura, deduplicação e histórico Git mudam o ritmo. O escritor recupera todo o histórico da branch científica, para o orçamento Git não medir apenas o último snapshot. O tamanho remoto deve ser acompanhado também: outras branches, objetos não alcançáveis e particularidades de compactação do servidor não entram nessa medição local.

`scripts/archive_backup.py` cria volumes mensais imutáveis e catálogo SHA-256, verifica CRC/hash e restaura em diretório novo. Manter duas cópias, idealmente em dispositivos distintos, além da branch remota. Antes de 85%, preparar com aprovação um novo repositório público gratuito para o período seguinte e um catálogo que ligue períodos/SHAs. Os volumes mensais não reduzem o histórico Git; não apagar objetos antigos, reescrever commits ou mover dados automaticamente. A migração para outro repositório ainda exige implantação explícita e validação do leitor, porque o escritor atual usa um remoto fixo. Limite ou falha preserva registros anteriores e deixa a captura recente no transporte temporário para recuperação dentro de sete dias.

A política é monitorada automaticamente, mas backup mensal e rotação dependem de operação humana; nenhuma nova tarefa persistente do Windows foi instalada. A reconstrução integral precisa de benchmark adicional antes de grande crescimento, pois pode atingir os 25 minutos do runner antes do limite de bytes.
