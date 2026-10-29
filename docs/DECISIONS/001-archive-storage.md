# ADR 001 — arquivo público incremental

Data: 28/10/2026. Versão: 2.2.0. Origem: v2.1, commit e1241e208033baf3260d86c8ba4b03e56ba92300.

Problema: `latest.json` contém resumos, não os membros originais; artifacts e cache expiram.
Alternativas: artifacts (temporários), banco no Pages (incompatível), serviço pago (vedado), branch de arquivos imutáveis (adotada).

Estimativa **antes da implementação do arquivo**, não medição: 8 modelos × cerca de 51 membros × (168 h × 2 variáveis + 80 h × 6 variáveis) ≈ 333 mil valores/local/coleta. Modelos têm contagens e coberturas diferentes. Admitindo 0,7–2 MB comprimidos por local/coleta, duas localidades e quatro arquivos/dia: **168–480 MB/30 dias; 2,0–5,8 GB/ano**, sem contar histórico Git. Essa faixa será substituída por projeção medida; não representa promessa de espaço gratuito indefinido.

Decisão: preservar respostas já obtidas na coleta, comprimidas por SHA-256, e um manifesto por local/janela UTC de 6 h em `weather-archive`. O banco e Parquet são reconstruíveis localmente; não colocar o banco no Pages. Não fazer nova consulta para arquivar. Manter somente JSON público compacto no Pages. Usar limitador conservador de 750 MB de arquivos no checkout do arquivo e 25 MB por lote; ao exceder, registrar falha e manter previsão principal. Git pode consumir mais espaço que a soma dos arquivos: acompanhar `git count-objects -vH`, tamanho remoto e projeção; a trava não é garantia de cota remota.

Consequências: será necessária uma decisão explícita de migração/particionamento gratuito antes de atingir o limite. Não apagar histórico, contratar armazenamento ou fingir durabilidade ilimitada. Quatro arquivos/dia são o alvo enquanto houver espaço e execução; GitHub schedule pode atrasar/pular execuções. Concorrência única, sem force-push. Falha de arquivo é visível no relatório.

Fontes consultadas: [limites Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits), [limites Actions](https://docs.github.com/en/actions/reference/limits), [termos Open-Meteo](https://open-meteo.com/en/terms). O uso gratuito Open-Meteo verificado é não comercial; instituição pública/pesquisa aberta não autoriza transformar a API em serviço comercial.
