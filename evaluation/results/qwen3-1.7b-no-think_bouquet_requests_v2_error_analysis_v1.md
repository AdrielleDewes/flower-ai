# Error analysis v1 — Qwen3 1.7B, think:false, bouquet_requests_v2

Análise em 2026-10-18 exclusivamente do [benchmark salvo](qwen3-1.7b-no-think_bouquet_requests_v2.json). Nenhuma inferência, alteração de código, dataset, prompt, catálogo, schema ou métrica. As classificações abaixo são anotações de análise, não novas métricas do runner.

## Critérios e limites da evidência

São 21 casos sem exact match: 9 rejeições e 12 respostas aceitas divergentes. As categorias podem se sobrepor; contagens por categoria indicam casos distintos, e contagens por campo indicam pares caso/campo.

- **T — invalid output structure/type:** falha estrutural/de tipo registrada. Nenhuma observada; `InvalidLLMOutputError` sozinho não significa erro estrutural. Todas as rejeições registradas ocorreram na validação de catálogo, posterior à validação do schema. Isso não prova conformidade estrita do JSON bruto antes de coerções/normalizações.
- **O — out-of-catalog values:** campo explicitamente citado no erro de catálogo. O valor bruto e quaisquer outros erros não estão disponíveis. O validador para no primeiro campo inválido; as contagens são limites inferiores.
- **M — missing expected information:** valor esperado não nulo ausente, incluindo elemento faltante em lista.
- **I — invented information:** informação sem suporte segundo o rótulo, incluindo elementos adicionados a listas não nulas. Esta classificação é mais ampla que a hallucination rate do runner.
- **C — incorrect category assignment:** transferência observável para uma categoria de interpretação errada. Nenhuma transferência entre campos está confirmada; ver hipótese sobre Pink/Rose abaixo.
- **S — other semantic errors:** divergência restante; nesta execução, ordem de lista invertida sem diferença de conteúdo. É erro pelo contrato de exact match atual, sem perda de conteúdo semântico.

## Contagens por categoria

| Categoria | Casos confirmados | Pares caso/campo confirmados |
|---|---:|---:|
| T — Estrutura/tipo | 0 | 0 |
| O — Fora do catálogo | 9 | 9 |
| M — Informação ausente | 8 | 10 |
| I — Informação inventada | 7 | 9 |
| C — Categoria incorreta | 0 | 0 |
| S — Outros: ordem de lista | 1 | 1 |

M/I/S são calculados somente onde `actual` existe. Há 9 campos rejeitados conhecidos, mas não é possível determinar omissões, invenções, trocas de categoria ou ordem nesses outputs. Zero confirmado não significa ausência de erros ocultos.

## Contagens por campo

| Campo | M | I | S | Divergências em aceitos | O confirmado em rejeitados | Não pontuados pelo runner¹ |
|---|---:|---:|---:|---:|---:|---:|
| occasion | 0 | 2 | 0 | 2 | 2 | 11 |
| styles | 3 | 1 | 0 | 4 | 2 | 13 |
| colors | 1 | 2 | 1 | 4 | 1 | 13 |
| size | 2 | 1 | 0 | 3 | 0 | 12 |
| budget_max | 0 | 0 | 0 | 0 | 0 | 9 |
| preferred_flowers | 0 | 3 | 0 | 3 | 4 | 12 |
| excluded_flowers | 4 | 0 | 0 | 4 | 0 | 13 |

¹ O runner atribui zero acertos a todos os sete campos de cada caso rejeitado: 63 campos não pontuados nos 9 outputs rejeitados, além de 20 divergências observadas em outputs aceitos. Somente 9 desses 63 campos têm erro de catálogo confirmado; os outros 54 são indeterminados. Mesmo nos nove campos identificados não se recupera o valor rejeitado. Por exemplo, os nove `budget_max` não pontuados não são nove erros de orçamento observados: não há divergência de orçamento nos aceitos. T e C têm zero confirmado em todos os campos.

## Classificação dos 21 casos

Cada diferença disponível é apresentada como esperado → obtido. O caso pode ter mais de uma categoria.

| Caso | Categorias | Evidência |
|---|---|---|
| `pt_v2_thanks_carnations` | I, M, S | `colors`: `["Orange", "Yellow"]` → `["Yellow", "Orange"]`; `size`: `"MEDIUM"` → `null`; `preferred_flowers`: `["Carnation"]` → `["Baby's Breath", "Carnation", "Daisy", "Gerbera", "Hydrangea", "Lily", "Sunflower", "Tulip"]`; `excluded_flowers`: `["Rose"]` → `null` |
| `pt_v2_just_because_delicate` | O | `preferred_flowers`: valor rejeitado não preservado; demais campos indeterminados |
| `pt_v2_mothers_day_rustic` | M | `excluded_flowers`: `["Lily"]` → `null` |
| `pt_v2_anniversary_dual_style` | M | `styles`: `["Classic", "Elegant"]` → `["Classic"]`; `excluded_flowers`: `["Carnation"]` → `null` |
| `pt_v2_budget_not_size` | I, M | `styles`: `["Romantic"]` → `null`; `preferred_flowers`: `null` → `["Rose"]` |
| `pt_v2_stem_count_not_size` | M | `colors`: `["White"]` → `null` |
| `pt_v2_pink_is_color` | O | `colors`: valor rejeitado não preservado; demais campos indeterminados |
| `pt_v2_exclusions_only` | M | `excluded_flowers`: `["Hydrangea", "Tulip"]` → `null` |
| `pt_v2_unsupported_flower` | O | `preferred_flowers`: valor rejeitado não preservado; demais campos indeterminados |
| `pt_v2_unsupported_categories` | O | `styles`: valor rejeitado não preservado; demais campos indeterminados |
| `pt_v2_small_no_occasion` | O | `occasion`: valor rejeitado não preservado; demais campos indeterminados |
| `pt_v2_irrelevant_colors` | I | `colors`: `null` → `["Blue"]` |
| `pt_v2_size_unsure` | I, M | `styles`: `["Elegant"]` → `null`; `size`: `null` → `"SMALL"` |
| `en_v2_thanks_two_styles` | M | `size`: `"MEDIUM"` → `null` |
| `en_v2_low_budget_not_size` | I | `preferred_flowers`: `null` → `["Baby's Breath", "Carnation", "Daisy", "Gerbera", "Hydrangea", "Lily", "Peony", "Rose", "Sunflower", "Tulip"]` |
| `en_v2_no_specific_shade` | I | `occasion`: `null` → `"Birthday"`; `styles`: `null` → `["Colorful"]`; `colors`: `null` → `["Pink", "Orange", "Yellow"]` |
| `en_v2_preference_and_exclusion` | O | `preferred_flowers`: valor rejeitado não preservado; demais campos indeterminados |
| `en_v2_unsupported_mixed` | O | `styles`: valor rejeitado não preservado; demais campos indeterminados |
| `en_v2_unsupported_occasion` | O | `occasion`: valor rejeitado não preservado; demais campos indeterminados |
| `en_v2_missing_style` | O | `preferred_flowers`: valor rejeitado não preservado; demais campos indeterminados |
| `en_v2_irrelevant_numbers` | I | `occasion`: `null` → `"Wedding"` |

## Métricas por idioma

Mesmas definições do runner: exact match e status accuracy usam todos os 15 casos do idioma, incluindo rejeições; output válido significa interpretação aceita após schema e catálogo. Hallucination rate divide campos inventados por campos esperados como null **apenas nos outputs aceitos**. Listas inteiras contam como um campo, independentemente do número de elementos.

| Idioma | Exact match | Output válido | Status accuracy | Hallucination rate |
|---|---:|---:|---:|---:|
| Português | 2/15 (13.33%) | 10/15 (66.67%) | 9/15 (60.00%) | 3/32 (9.38%) |
| Inglês | 7/15 (46.67%) | 11/15 (73.33%) | 10/15 (66.67%) | 5/34 (14.71%) |

No agregado: 9/30 exact match, 21/30 válidos, 19/30 status corretos e 8/66 campos inventados pela definição do runner. READY: PT 3/5, EN 4/5; NEEDS_CLARIFICATION: PT 6/10, EN 6/10. As nove rejeições são cinco PT e quatro EN. Não são estratos pareados: os textos e dificuldades diferem; uma única execução com 15 casos por idioma não isola um efeito causal de idioma.

## Padrões recorrentes e exemplos

1. **Catálogo/canonicalização:** 9 rejeições; `preferred_flowers` responde por 4, `occasion` e `styles` por 2 cada, `colors` por 1. Não sabemos se vieram traduções, plurais, nomes não suportados ou outra confusão. `pt_v2_pink_is_color` não permite concluir que o modelo colocou Rose em colors: o valor não foi salvo.
2. **Negação e cobertura de múltiplos atributos:** quatro omissões de `excluded_flowers`, todas PT (`thanks_carnations`, `mothers_day_rustic`, `anniversary_dual_style`, `exclusions_only`); `anniversary_dual_style` perde também Elegant. Hipótese de dificuldade com português/negação, sem evidência de causa.
3. **Preferências preenchidas com opções disponíveis:** `en_v2_low_budget_not_size` retorna todas as dez flores; `pt_v2_thanks_carnations` preserva Carnation, mas adiciona sete espécies. Esta última invenção não entra na hallucination rate porque o campo esperado não era null.
4. **Confusão entre ausência, ambiguidade e evidência:** dois MEDIUM explícitos viram null (`pt_v2_thanks_carnations`, `en_v2_thanks_two_styles`); uma escolha não decidida vira SMALL (`pt_v2_size_unsure`). São três divergências de size. Os dois tamanhos omitidos causam READY → NEEDS_CLARIFICATION.
5. **Associações e contexto irrelevante:** `pt_v2_irrelevant_colors` copia Blue da portaria para o buquê; `en_v2_irrelevant_numbers` inventa Wedding; `en_v2_no_specific_shade` preenche ocasião, estilo e cores ausentes. Esses casos continuam NEEDS_CLARIFICATION, mostrando que status correto não garante extração correta.
6. **Possível ambiguidade lexical:** `pt_v2_budget_not_size` mantém Pink e adiciona Rose. Invenção confirmada; associação cultural ou confusão cor/flor são hipóteses, não transferência de categoria demonstrada. Por isso C permanece zero confirmado. A cor da portaria é erro de escopo/referente, classificado como I, sem transferência entre categorias do schema.
7. **Ordem:** `pt_v2_thanks_carnations` retorna Yellow/Orange em vez de Orange/Yellow; o conteúdo é equivalente como conjunto, mas não no exact match vigente. Corrigir apenas a ordem não tornaria esse caso integralmente correto.

## Intervenções propostas — nenhuma implementada

Benefícios e complexidades são estimativas baseadas nesta execução; não são ganhos medidos. Validar mudanças em novos benchmarks versionados, com baseline congelado e conjunto adicional reservado para reduzir sobreajuste.

| Prioridade | Proposta para experimento futuro | Benefício esperado e evidência | Complexidade / ressalva |
|---|---|---|---|
| 1 | Exemplos bilíngues contrastivos de extração por campo: exclusões, múltiplos atributos, tamanho explícito/indeciso e ausência de preferência | Alto: 8 casos com omissões e 7 com invenções; exemplos novos, distintos do benchmark | Baixa–média; prompt maior pode aumentar latência e causar regressões |
| 2 | Restringir as opções por categoria durante a geração, com valores canônicos e null, em vez de apenas rejeitar depois | Potencial alto: 9 rejeições; preserva validação e não comprova correção semântica | Média; requer experimento de integração com structured outputs/provider, pode deslocar erros para opções válidas inventadas |
| 3 | Reforçar escopo/evidência e separação entre opções do catálogo e preferências, incluindo não copiar listas disponíveis | Alto–médio: listas infladas e atributos de contexto irrelevante; sobrepõe a prioridade 1 | Baixa no prompt; média–alta se exigir evidência por campo; não eliminar valores com heurísticas sem avaliação |
| 4 | Retry limitado após rejeição, com campo e opções permitidas; jamais aceitar correção silenciosa | Médio e incerto: pode recuperar parte das 9 rejeições | Média; aumenta latência/chamadas e pode produzir outputs válidos ainda errados |
| 5 | Solicitar preservação da ordem de menção em listas | Baixo: uma diferença de ordem, em caso que também tem outros erros | Baixa; não alterar a métrica para melhorar o número |

Antes de atribuir causa às rejeições, uma melhoria de observabilidade em experimento futuro seria preservar o output bruto rejeitado e diagnósticos completos por campo em artefatos de avaliação, com cuidado para dados pessoais. Benefício diagnóstico alto, ganho direto de qualidade zero; complexidade baixa–média. Nenhuma dessas alterações foi feita.

## Verificação da análise

As contagens foram derivadas e conferidas contra o JSON salvo: 21 casos classificados, 20 divergências de campo observadas e 9 campos rejeitados identificados. As métricas por idioma recompõem os totais do runner. Integridade dos arquivos existentes verificada por SHA-256. Nenhuma inferência executada; apenas este novo Markdown foi criado.
