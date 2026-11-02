# Query Extractor v1 — POC gold_v2 — run1

**Data local: 2026-11-02 (America/Sao_Paulo).** Execução completa autorizada dos 46 casos, com regras originais e gold_v2 aprovado para este POC. Não houve LLM, acesso a banco, otimização ou integração de produção.

## Aprovação e validação

- Os 46 casos gold_v2 foram marcados reviewed:true por autorização explícita. Somente essa flag mudou nos sidecars; estados, valores, candidatos, evidências e hashes foram preservados. gold_v1 continua intacto e não aprovado.
- O loader validou hashes, IDs, idiomas, tipos, estados, catálogo, ordem dos valores, candidatos, menções pendentes e spans exatos. Foram executados 16 casos de v1 e 30 de v2, sem erro de execução.
- O agregado soma contagens brutas dos dois relatórios e recalcula as taxas. Não executa extração novamente nem tira média simples de percentuais.
- Os datasets foram usados e revisados durante o desenvolvimento: os resultados são experimentais, não avaliação em holdout.

## Precisão, recall e F1 canônicos

As unidades são valores por campo: nomes canônicos em listas e um valor por tamanho/orçamento. Substituição contaria FP+FN; abstenções e ausências indevidas permanecem no denominador de recall. TRUE negatives não elevam precisão/recall.

| Grupo / campo | TP | FP | FN | Precisão | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| Global / todos | 73 | 0 | 13 | 100.00% | 84.88% | 91.82% |
| Global / size | 16 | 0 | 7 | 100.00% | 69.57% | 82.05% |
| Global / budget_max | 13 | 0 | 0 | 100.00% | 100.00% | 100.00% |
| Global / preferred_flowers | 27 | 0 | 5 | 100.00% | 84.38% | 91.53% |
| Global / excluded_flowers | 17 | 0 | 1 | 100.00% | 94.44% | 97.14% |
| Português / todos | 33 | 0 | 4 | 100.00% | 89.19% | 94.29% |
| Português / size | 5 | 0 | 4 | 100.00% | 55.56% | 71.43% |
| Português / budget_max | 6 | 0 | 0 | 100.00% | 100.00% | 100.00% |
| Português / preferred_flowers | 13 | 0 | 0 | 100.00% | 100.00% | 100.00% |
| Português / excluded_flowers | 9 | 0 | 0 | 100.00% | 100.00% | 100.00% |
| Inglês / todos | 40 | 0 | 9 | 100.00% | 81.63% | 89.89% |
| Inglês / size | 11 | 0 | 3 | 100.00% | 78.57% | 88.00% |
| Inglês / budget_max | 7 | 0 | 0 | 100.00% | 100.00% | 100.00% |
| Inglês / preferred_flowers | 14 | 0 | 5 | 100.00% | 73.68% | 84.85% |
| Inglês / excluded_flowers | 8 | 0 | 1 | 100.00% | 88.89% | 94.12% |

No agregado, são **73 valores emitidos corretos em 86 esperados, 0 FP e 13 FN**. Houve zero falsos positivos nos 106 pares caso/campo sem valor canônico esperado. Isso não significa ausência de erros de estado ou de diagnóstico. O alvo experimental global de precisão >=95% e recall >=80% foi atingido neste conjunto conhecido; não é gate de aprovação, evidência de generalização ou justificativa para integrar em produção. Size ficou com recall 69,57%, e o dataset v1 isolado com recall canônico 76%.

## Exact match e resultados por idioma

Exact match canônico considera os quatro campos, incluindo valores ausentes, mantendo a ordem das listas. Exact match semântico exige também estados, menções pendentes, motivos, candidatos e spans válidos. Não é comparável diretamente ao exact match do LLM sobre sete campos de interpretação.

| Grupo | Casos | Exact match canônico | Exact match semântico completo |
|---|---:|---:|---:|
| Global | 46 | 38/46 (82.61%) | 31/46 (67.39%) |
| Português | 21 | 17/21 (80.95%) | 12/21 (57.14%) |
| Inglês | 25 | 21/25 (84.00%) | 19/25 (76.00%) |
| Dataset v1 | 16 | 13/16 (81.25%) | 12/16 (75.00%) |
| Dataset v2 | 30 | 25/30 (83.33%) | 19/30 (63.33%) |

Acurácia de estado por campo: 164/184 (89.13%). Exact match semântico por campo: 163/184 (88.59%). São 8 casos com erro de valor canônico e 15 casos sem exact match semântico.

## Cobertura e abstenção

| Grupo | Campos positivos com valores emitidos | Campos positivos retidos | Abstenções explícitas AMBIGUOUS/CONFLICT, em todos os campos |
|---|---:|---:|---:|
| Global | 66/78 (84.62%) | 12/78 (15.38%) | 10/184 (5.43%) |
| Português | 30/34 (88.24%) | 4/34 (11.76%) | 7/84 (8.33%) |
| Inglês | 36/44 (81.82%) | 8/44 (18.18%) | 3/100 (3.00%) |

Dos 78 campos com valores canônicos esperados, **66 foram preenchidos e 12 retidos**: 7 por abstenção explícita e 5 classificados indevidamente como ABSENT. Esses 12 campos contêm os 13 valores FN.

Nos 184 campos, o extrator declarou RESOLVED em 66, ABSENT em 108 e AMBIGUOUS em 10; nenhum PARTIAL ou CONFLICT. **118/184 campos não receberam valor**, mas não se deve chamar todos de abstenção: a maior parte é ausência legítima. A abstenção explícita é 10/184 (5,43%).

Os 174/184 campos declarados completos pelo extrator não representam 174 acertos: correctly_complete_fields é 163. Entre as dez abstenções explícitas, sete retêm valores esperados, duas são ambiguidades espúrias de rosa/cor e uma reconhece a indecisão de tamanho de pt_v2_size_unsure. Esse último reconhecimento legado não contém o diagnóstico estruturado necessário ao contrato v2.

## Menções pendentes

| Motivo gold | Esperadas | TP | FP | FN | Precisão | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| OUT_OF_CATALOG | 4 | 0 | 0 | 4 | indefinido | 0.00% | 0.00% |
| UNDECIDED | 5 | 0 | 0 | 5 | indefinido | 0.00% | 0.00% |
| CONFLICTING_INFORMATION | 0 | 0 | 0 | 0 | indefinido | indefinido | indefinido |

Global: **0/9 menções pendentes detectadas no contrato estruturado v2**; precisão indefinida porque nenhuma menção estruturada foi emitida. Português: 0/4 (2 OUT_OF_CATALOG + 2 UNDECIDED); inglês: 0/5 (2 OUT_OF_CATALOG + 3 UNDECIDED). Não há casos gold de conflito, portanto esse motivo não foi avaliado em recall.

**Limitação de capacidade/contrato:** todas as 46 saídas são legadas (`pending_mentions_supported:false`). O extrator não foi alterado para retornar AnnotationPrediction, PARTIAL ou unresolved_mentions. O avaliador não inventa diagnósticos a partir do gold e conta as menções ausentes como FN. Em pt_v2_size_unsure, os candidatos e o motivo legado undecided_size reconhecem a indecisão, mas não equivalem à detecção v2 com motivo e span da menção. Portanto zero detecções estruturadas não prova que toda indecisão passou despercebida.

## Falsos negativos canônicos — todos os casos/valores

| Caso | Campo | Valores esperados não emitidos | Estado obtido | Diagnóstico legado |
|---|---|---|---|---|
| `wedding_peonies` | size | MEDIUM | ABSENT | — |
| `wedding_peonies` | preferred_flowers | Peony | ABSENT | — |
| `multiple_preferences` | size | LARGE | ABSENT | — |
| `multiple_preferences` | preferred_flowers | Rose, Tulip | ABSENT | — |
| `pt_mothers_day_exclusion` | size | SMALL | AMBIGUOUS | negated_or_unclear_size |
| `pt_v2_just_because_delicate` | size | LARGE | AMBIGUOUS | negated_or_unclear_size |
| `pt_v2_mothers_day_rustic` | size | SMALL | AMBIGUOUS | negated_or_unclear_size |
| `pt_v2_small_no_occasion` | size | SMALL | AMBIGUOUS | negated_or_unclear_size |
| `en_v2_unsupported_mixed` | size | SMALL | AMBIGUOUS | undecided_size |
| `en_v2_unsupported_mixed` | preferred_flowers | Tulip | AMBIGUOUS | undecided_flower |
| `en_v2_unsupported_mixed` | excluded_flowers | Rose | AMBIGUOUS | undecided_flower |
| `en_v2_missing_style` | preferred_flowers | Carnation | ABSENT | — |

## Análise concisa de erros

1. **Escopo de negação/alternativa amplo demais.** Sem cravos/lírios/peônias torna tamanho explícito ambíguo em pt_mothers_day_exclusion, pt_v2_mothers_day_rustic e pt_v2_small_no_occasion. Sem motivo especial também bloqueia LARGE em pt_v2_just_because_delicate. Em en_v2_unsupported_mixed, or dentro de no dahlias or roses é tratado como escolha indecisa, retendo SMALL, Tulip e Rose. São erros de escopo, não falta real de evidência.
2. **Cobertura limitada de construções elípticas e relações.** wedding_peonies e multiple_preferences perdem tamanho/espécies explicitamente listados. en_v2_missing_style perde Carnation na relação bouquet of carnations. Regras conservadoras de contexto evitam FP, mas deixam essas construções sem cobertura.
3. **Pendências não estruturadas.** Os três campos gold PARTIAL não são representados como tal. pt_v2_unsupported_flower preserva Rose corretamente, mas ignora a pendência de orquídeas e a exclusão de antúrios; o perfil parece mais completo do que realmente é. Esse problema permanece invisível no exact match exclusivamente canônico.
4. **Indecisão genérica sem valor candidato.** pt_v2_ambiguous_impact, en_v2_ambiguous_size e en_v2_occasion_no_defaults ficam ABSENT nos campos pendentes; o extrator depende de candidatos lexicais reconhecidos e não expressa a ausência de decisão como diagnóstico v2.
5. **Abstenção espúria em cor rosa.** pt_anniversary_multiple e pt_v2_pink_is_color recebem preferred_flowers AMBIGUOUS quando o contexto determina cor e o gold é ABSENT. Nenhuma Rose foi inventada, mas o estado semântico está errado.

## Casos com valores canônicos corretos, mas sem completude semântica

| Caso | Valores canônicos corretos? | Motivo principal do não acerto semântico |
|---|---|---|
| `pt_anniversary_multiple` | Sim | Rosa/cor indevidamente sinalizada como preferência ambígua. |
| `pt_v2_ambiguous_impact` | Sim | Indecisão de tamanho tratada como ausência; diagnóstico não emitido. |
| `pt_v2_pink_is_color` | Sim | Falta de preferência explícita e cor rosa tratadas como ambiguidade de espécie. |
| `pt_v2_unsupported_flower` | Sim | Rose correta, mas estado PARTIAL e as duas menções OUT_OF_CATALOG não foram emitidos. |
| `pt_v2_size_unsure` | Sim | Estado AMBIGUOUS correto, mas falta menção estruturada UNDECIDED. |
| `en_v2_ambiguous_size` | Sim | Indecisão de tamanho tratada como ausência; diagnóstico não emitido. |
| `en_v2_occasion_no_defaults` | Sim | Escolhas não feitas tratadas como ausência, sem os dois diagnósticos UNDECIDED. |

## Latência e evidências

- Tempo total exclusivo de extração: **18.621581 ms** nos 46 casos.
- Média exclusiva de extração: **0.404817 ms por query**.
- Inicialização do vocabulário: 1.690292 ms somados em duas inicializações, **excluídos** dos tempos de extração.
- Parsing/validação dos sidecars e escrita dos artefatos também ficam fora do cronômetro por query. É uma única passagem local, sem warm-up padronizado ou repetição estatística; tempos submilissegundo são sensíveis ao ambiente e não constituem SLA.
- Os 73 spans confirmados são válidos e alinhados ao suporte gold (73/73). Isso não corrige valores omitidos, estados incorretos ou diagnósticos ausentes. Não houve inferência LLM, tokens ou métricas Ollama nesta avaliação.

## Artefatos e reprodutibilidade

- [Dataset v1 — JSON da execução](query-extractor-v1_bouquet_requests_v1_gold-v2_run1.json).
- [Dataset v2 — JSON da execução](query-extractor-v1_bouquet_requests_v2_gold-v2_run1.json).
- [Agregado dos 46 casos](query-extractor-v1_bouquet_requests_v1-v2_gold-v2_run1.json).

Os JSONs individuais registram os hashes dos datasets e sidecars aprovados. O agregado registra hashes dos JSONs de origem, de modo que as taxas podem ser recalculadas sem repetir a extração. Nenhum artefato anterior foi sobrescrito. Regras mantidas, SHA-256:

- `contracts.py`: `f3c4eb1e5ba330ab7c04bc7f972315e92bc71f9a88e2ad5afa526f64f2c28cec`.
- `extractor.py`: `73c50eb19b8abd6e8d07bc35dfcce846f49de252da71f49faa6ca50cf728cb2b`.
- `text.py`: `3f776db0b82f089323324de044f22953620b294712462f468ad160d9b11e0ae1`.
- `vocabulary.py`: `b2a856b124409d3c5e0d886f540449729a442674128532377c1fc2a5ae6f7c39`.

Comandos executados (uma vez por dataset):

```bash
backend/.venv/bin/python -m evaluation.query_extractor \
  --dataset evaluation/data/bouquet_requests_v1.json \
  --annotations evaluation/query_extractor/gold/bouquet_requests_v1_gold_v2.json \
  --annotation-version 2 \
  --output evaluation/results/query-extractor-v1_bouquet_requests_v1_gold-v2_run1.json

backend/.venv/bin/python -m evaluation.query_extractor \
  --dataset evaluation/data/bouquet_requests_v2.json \
  --annotations evaluation/query_extractor/gold/bouquet_requests_v2_gold_v2.json \
  --annotation-version 2 \
  --output evaluation/results/query-extractor-v1_bouquet_requests_v2_gold-v2_run1.json
```

## Verificação e limites da conclusão

Ruff aprovado em backend e evaluation. Pytest: **229 testes do backend e 162 da avaliação aprovados**. Os testes de aprovação foram atualizados para exigir gold_v2 aprovado e comprovar que um caso não revisado ainda bloqueia o loader; gold_v1 permanece bloqueado. git diff --check aprovado. Hashes confirmam preservação de regras, produção, datasets, prompts, configuração LLM, avaliador e benchmarks anteriores. Somente flags reviewed dos gold_v2 mudaram, além de testes/documentação e novos artefatos.

O POC mostra precisão canônica alta e recall agregado acima do alvo neste conjunto conhecido, com perda significativa de recall em tamanho e completude semântica de 31/46. Não demonstra melhoria do pipeline LLM nem prontidão de produção. Nenhuma regra foi otimizada e nenhuma integração foi feita.
