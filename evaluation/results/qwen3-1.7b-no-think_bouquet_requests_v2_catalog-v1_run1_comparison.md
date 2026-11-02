# Catálogo restrito v1 — benchmark controlado run1

## Condições e compatibilidade

- Data: 2026-10-18; início UTC registrado antes da chamada ao runner: 2026-10-18T19:14:16.566926+00:00. Relatório elaborado em 2026-10-18T19:18:48.666143+00:00.
- Ollama **0.35.0**, modelo **qwen3:1.7b**, quantização **Q4_K_M**.
- Digest do modelo: `8f68893c685c3ddff2aa3fffce2aa60a30bb2da65ca488b61fff134a4d1730e7`.
- Dataset v2 completo: 30 casos; think:false, temperatura 0, timeout 60 s. Flag `--catalog-constrained-output`, versão de restrição 1.
- [Smoke test](qwen3-1.7b-no-think_bouquet_requests_v2_catalog-v1_smoke1.json): uma chamada com o schema dinâmico completo do catálogo v2 foi aceita; enums escalares, arrays, null e validação posterior produziram output válido. Não é prova exaustiva de todos os recursos JSON Schema. O modelo omitiu Lily em excluded_flowers, portanto compatibilidade não implica extração correta.
- Novo [JSON do benchmark](qwen3-1.7b-no-think_bouquet_requests_v2_catalog-v1_run1.json); comparação com o [baseline irrestrito existente](qwen3-1.7b-no-think_bouquet_requests_v2.json).
- As execuções ocorreram em momentos diferentes. O baseline não registra timestamp exato nem versão/digest do servidor/modelo no próprio artefato. Não houve nova execução pareada do baseline. O smoke test aqueceu o modelo antes do benchmark atual; o baseline tem carga inicial maior. Hardware/carga/cache não foram controlados retroativamente. A comparação de latência é descritiva, sem atribuir causalidade à restrição.
- O schema permanece no prompt e em format. Nenhum prompt, schema, dataset, configuração de modelo, métrica ou lógica foi alterado nesta execução. Hashes SHA-256 de todos os arquivos protegidos foram conferidos. O smoke test não integra os 30 casos ou as métricas abaixo.

## Qualidade e latência

| Métrica | Baseline irrestrito | Catálogo restrito run1 |
|---|---:|---:|
| Exact match | 9/30 (30.00%) | 12/30 (40.00%) |
| Outputs válidos | 21/30 (70%) | 30/30 (100%) |
| Outputs inválidos | 9/30 (30%) | 0/30 (0%) |
| Rejeições por catálogo | 9 | 0 |
| Hallucination rate | 8/66 (12.12%) | 14/100 (14.00%) |
| Status accuracy | 19/30 (63,33%) | 29/30 (96,67%) |
| READY correto | 7/10 (70%) | 10/10 (100%) |
| NEEDS_CLARIFICATION correto | 12/20 (60%) | 19/20 (95%) |
| Latência média | 5.262166 s | 5.166544 s |
| Latência total | 157.864975 s | 154.996334 s |

O modo restrito foi 1,82% mais rápido nesta comparação histórica. Isso não comprova o limite de +10% sob condições equivalentes. Outputs válidos passaram por schema e catálogo; exact match e status incluem todos os 30 casos. Hallucination rate conta campos esperados null preenchidos, apenas nos outputs aceitos, não itens adicionais em listas já não nulas. Os denominadores distintos impedem interpretar diretamente 12,12% → 14% como piora causal.

| Campo | Baseline: acertos/30 | Restrito: acertos/30 |
|---|---:|---:|
| occasion | 19/30 (63.33%) | 22/30 (73.33%) |
| styles | 17/30 (56.67%) | 24/30 (80.00%) |
| colors | 17/30 (56.67%) | 23/30 (76.67%) |
| size | 18/30 (60.00%) | 27/30 (90.00%) |
| budget_max | 21/30 (70.00%) | 30/30 (100.00%) |
| preferred_flowers | 18/30 (60.00%) | 22/30 (73.33%) |
| excluded_flowers | 17/30 (56.67%) | 25/30 (83.33%) |

As melhorias por campo incluem o efeito de nove outputs antes rejeitados, cujos sete campos recebiam zero no runner. Não significam melhoria semântica em todos os campos de cada caso.

## Português versus inglês

| Modo / idioma | Exact match | Válidos | Status accuracy | Hallucination rate |
|---|---:|---:|---:|---:|
| Baseline PT | 2/15 (13.33%) | 10/15 (66.67%) | 9/15 (60.00%) | 3/32 (9.38%) |
| Baseline EN | 7/15 (46.67%) | 11/15 (73.33%) | 10/15 (66.67%) | 5/34 (14.71%) |
| Restrito PT | 2/15 (13.33%) | 15/15 (100.00%) | 15/15 (100.00%) | 8/53 (15.09%) |
| Restrito EN | 10/15 (66.67%) | 15/15 (100.00%) | 14/15 (93.33%) | 6/47 (12.77%) |

No restrito: PT READY 5/5 e NEEDS_CLARIFICATION 10/10; EN READY 5/5 e NEEDS_CLARIFICATION 9/10. PT continua com somente 2 exact matches, apesar de 100% de validade e status correto. São amostras de textos distintos por idioma, não pares traduzidos.

## Inferência Ollama

Métricas disponíveis em 30/30 respostas nos dois relatórios. Médias sobre 30; durações convertidas de ns para s.

| Métrica | Baseline total | Baseline média | Restrito total | Restrito média |
|---|---:|---:|---:|---:|
| total_duration | 157.494314 s | 5.249810 s | 154.674988 s | 5.155833 s |
| load_duration | 3.052400 s | 0.101747 s | 0.175460 s | 0.005849 s |
| prompt_eval_duration | 54.782792 s | 1.826093 s | 65.178749 s | 2.172625 s |
| eval_duration | 98.934104 s | 3.297803 s | 85.640862 s | 2.854695 s |
| prompt_eval_count | 31840 | 1061.333 | 37660 | 1255.333 |
| eval_count | 1905 | 63.500 | 1842 | 61.400 |

Geração agregada: baseline 19.255 tokens/s; restrito 21.508 tokens/s. Tokens de entrada aumentaram **18,28%** (31.840 → 37.660); tokens gerados caíram de 1.905 para 1.842. O processamento de prompt aumentou, enquanto carregamento e geração diminuíram; isso reforça a necessidade de comparar latência em condições pareadas antes de concluir neutralidade de custo.

## Casos antes rejeitados: validade versus fidelidade

Os nove casos rejeitados no baseline foram aceitos. **Somente dois ficaram integralmente corretos; sete continuam errados.** A resposta antiga desses casos não está salva, portanto é possível comparar com o esperado, não recuperar diferenças entre os outputs antigos e novos.

| Caso | Resultado restrito | Diferenças esperado → obtido |
|---|---|---|
| `pt_v2_just_because_delicate` | Válido, incorreto | `preferred_flowers`: `["Baby's Breath", "Daisy"]` → `["Baby's Breath", "Lily", "Tulip"]` |
| `pt_v2_pink_is_color` | Válido, incorreto | `colors`: `["Pink", "Purple"]` → `null` |
| `pt_v2_unsupported_flower` | Válido, incorreto | `occasion`: `null` → `"Mother's Day"`; `preferred_flowers`: `["Rose"]` → `["Rose", "Hydrangea"]` |
| `pt_v2_unsupported_categories` | Válido, incorreto | `occasion`: `null` → `"Wedding"`; `size`: `null` → `"LARGE"`; `preferred_flowers`: `["Daisy"]` → `["Gerbera"]` |
| `pt_v2_small_no_occasion` | Válido, incorreto | `styles`: `["Colorful"]` → `null`; `colors`: `null` → `["Pink"]`; `preferred_flowers`: `["Sunflower", "Carnation"]` → `["Gerbera", "Carnation", "Daisy", "Tulip"]`; `excluded_flowers`: `["Peony"]` → `null` |
| `en_v2_preference_and_exclusion` | Correto | Nenhuma |
| `en_v2_unsupported_mixed` | Válido, incorreto | `occasion`: `null` → `"Just Because"`; `styles`: `null` → `["Romantic"]`; `colors`: `["Yellow"]` → `["Yellow", "Blue"]`; `preferred_flowers`: `["Tulip"]` → `["Tulip", "Hydrangea"]`; `excluded_flowers`: `["Rose"]` → `["Daisy", "Rose", "Daisy"]` |
| `en_v2_unsupported_occasion` | Válido, incorreto | `occasion`: `null` → `"Wedding"`; `styles`: `["Elegant"]` → `null` |
| `en_v2_missing_style` | Correto | Nenhuma |

Exemplos claros de substituição por opção válida indevida: `pt_v2_unsupported_categories` retorna Wedding/LARGE/Gerbera; `en_v2_unsupported_mixed` adiciona ocasião, estilo, cor, espécie e exclusões não solicitadas. Neste último também há Daisy duplicada; o schema não restringe unicidade, conforme o experimento planejado. Não são sucessos semânticos.

## População comum e regressões

Nos 21 casos aceitos em ambos os modos, com os mesmos 66 campos esperados null:

| Diagnóstico offline (não altera métricas do runner) | Baseline | Restrito |
|---|---:|---:|
| Campos inventados esperados null | 8/66 (12,12%) | 7/66 (10,61%) |
| Pares caso/campo com omissão¹ | 10 | 9 |
| Pares caso/campo com invenção¹ | 9 | 8 |
| Pares caso/campo divergentes | 20 | 19 |

¹ Para listas, conta ausência ou adição de pelo menos um elemento como um par; uma substituição pode contar em ambas as categorias. Os totais agregados melhoram ligeiramente, mas não impedem regressões por caso.

Há 1 regressão de exact match de caso anteriormente correto:
- `pt_v2_graduation_classic`: `occasion`: `"Graduation"` → `"Wedding"`.

O caso `pt_v2_stem_count_not_size` agora inventa SMALL e continua omitindo White; `pt_v2_size_unsure` troca uma escolha indevida SMALL por LARGE, perde Red e adiciona Rose. Mesmo com status agregado melhor, a fidelidade não está garantida.

## Todos os casos restritos sem exact match

| Caso | Diferenças esperado → obtido |
|---|---|
| `pt_v2_graduation_classic` | `occasion`: `"Graduation"` → `"Wedding"` |
| `pt_v2_thanks_carnations` | `occasion`: `"Thank You"` → `"Just Because"`; `preferred_flowers`: `["Carnation"]` → `["Sunflower"]`; `excluded_flowers`: `["Rose"]` → `null` |
| `pt_v2_just_because_delicate` | `preferred_flowers`: `["Baby's Breath", "Daisy"]` → `["Baby's Breath", "Lily", "Tulip"]` |
| `pt_v2_mothers_day_rustic` | `excluded_flowers`: `["Lily"]` → `null` |
| `pt_v2_anniversary_dual_style` | `occasion`: `"Anniversary"` → `"Wedding"`; `styles`: `["Classic", "Elegant"]` → `["Classic"]`; `excluded_flowers`: `["Carnation"]` → `null` |
| `pt_v2_budget_not_size` | `styles`: `["Romantic"]` → `null` |
| `pt_v2_stem_count_not_size` | `colors`: `["White"]` → `null`; `size`: `null` → `"SMALL"` |
| `pt_v2_pink_is_color` | `colors`: `["Pink", "Purple"]` → `null` |
| `pt_v2_unsupported_flower` | `occasion`: `null` → `"Mother's Day"`; `preferred_flowers`: `["Rose"]` → `["Rose", "Hydrangea"]` |
| `pt_v2_unsupported_categories` | `occasion`: `null` → `"Wedding"`; `size`: `null` → `"LARGE"`; `preferred_flowers`: `["Daisy"]` → `["Gerbera"]` |
| `pt_v2_small_no_occasion` | `styles`: `["Colorful"]` → `null`; `colors`: `null` → `["Pink"]`; `preferred_flowers`: `["Sunflower", "Carnation"]` → `["Gerbera", "Carnation", "Daisy", "Tulip"]`; `excluded_flowers`: `["Peony"]` → `null` |
| `pt_v2_irrelevant_colors` | `colors`: `null` → `["Blue"]` |
| `pt_v2_size_unsure` | `styles`: `["Elegant"]` → `null`; `colors`: `["Red"]` → `null`; `size`: `null` → `"LARGE"`; `preferred_flowers`: `null` → `["Rose"]` |
| `en_v2_low_budget_not_size` | `preferred_flowers`: `null` → `["Rose"]` |
| `en_v2_no_specific_shade` | `colors`: `null` → `["Yellow"]` |
| `en_v2_unsupported_mixed` | `occasion`: `null` → `"Just Because"`; `styles`: `null` → `["Romantic"]`; `colors`: `["Yellow"]` → `["Yellow", "Blue"]`; `preferred_flowers`: `["Tulip"]` → `["Tulip", "Hydrangea"]`; `excluded_flowers`: `["Rose"]` → `["Daisy", "Rose", "Daisy"]` |
| `en_v2_unsupported_occasion` | `occasion`: `null` → `"Wedding"`; `styles`: `["Elegant"]` → `null` |
| `en_v2_irrelevant_numbers` | `occasion`: `null` → `"Wedding"` |

## Conclusão e limites

Compatibilidade básica confirmada na versão instalada; rejeições por catálogo desapareceram. Exact match e status melhoraram no agregado, mas 18/30 outputs permanecem semanticamente incorretos e existe regressão de caso antes correto. A validade maior, isoladamente, não estabelece sucesso. A execução histórica não comprova causalidade nem o critério de latência em condições pareadas. Manter o recurso experimental/opt-in; nenhuma otimização ou alteração de comportamento foi realizada.

## Validação final

- Ruff: backend e evaluation aprovados.
- pytest: 229 testes do backend e 28 da avaliação aprovados.
- git diff --check aprovado.
- Integridade do código, schemas, prompts, datasets e resultados anteriores confirmada por SHA-256.
