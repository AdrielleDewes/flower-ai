# Qwen3 1.7B — bouquet_requests_v2 — think:false

Execução completa dos 30 casos em 2026-10-18. Timeout: 60 s por caso. Temperatura: 0. Pipeline, dataset e artefatos anteriores preservados. Nenhuma otimização aplicada.

[Relatório original JSON](qwen3-1.7b-no-think_bouquet_requests_v2.json)

## Qualidade

- Exact match: 9/30 (30.00%).
- Outputs aceitos: 21/30 (70.00%); rejeitados: 9/30 (30.00%).
- Todas as 9 rejeições são valores fora do catálogo; não houve erro de transporte ou falha estrutural separada registrada.
- Hallucination rate: 8/66 (12.12%).
- Status accuracy: 19/30 (63.33%).
- Latência média: 5.262166 s; total: 157.864975 s.

Outputs aceitos passaram pelas validações de schema e catálogo, sem garantia de correção semântica. Hallucination rate conta campos preenchidos quando o esperado é null, apenas nos outputs aceitos. Não mede todas as adições indevidas dentro de listas já esperadas como não nulas. Falhas continuam no denominador de exact match e acurácia por campo/status. Listas são comparadas com ordem, conforme a métrica existente.

| Campo | Acertos | Acurácia |
|---|---:|---:|
| occasion | 19/30 | 63.33% |
| styles | 17/30 | 56.67% |
| colors | 17/30 | 56.67% |
| size | 18/30 | 60.00% |
| budget_max | 21/30 | 70.00% |
| preferred_flowers | 18/30 | 60.00% |
| excluded_flowers | 17/30 | 56.67% |

| Status esperado | Acertos/esperados | Acurácia | Predições totais |
|---|---:|---:|---:|
| READY | 7/10 | 70.00% | 7 |
| NEEDS_CLARIFICATION | 12/20 | 60.00% | 14 |

A acurácia por status acima usa os casos cujo status esperado é o indicado (recall por classe), incluindo outputs rejeitados. As predições somam 21, pois 9 casos rejeitados não produzem status.

## Inferência Ollama

Métricas capturadas para 30/30 respostas, inclusive outputs rejeitados. Durações convertidas de nanossegundos para segundos; médias calculadas sobre as 30 respostas.

| Métrica | Total | Média por resposta |
|---|---:|---:|
| total_duration | 157.494314 s | 5.249810 s |
| load_duration | 3.052400 s | 0.101747 s |
| prompt_eval_duration | 54.782792 s | 1.826093 s |
| eval_duration | 98.934104 s | 3.297803 s |
| prompt_eval_count | 31840 | 1061.333 |
| eval_count | 1905 | 63.500 |

Velocidade agregada de geração: **19.255 tokens/s** (`sum(eval_count) / sum(eval_duration)`).

## Casos divergentes

Há 21 casos sem exact match: 12 outputs aceitos divergentes e 9 rejeitados. O runner não preserva o conteúdo bruto das rejeições; nesses casos só é possível identificar o campo citado no erro, sem inventar a diferença de valor.

### pt_v2_thanks_carnations

Status esperado: `READY`; obtido: `NEEDS_CLARIFICATION`.

| Campo | Esperado | Obtido |
|---|---|---|
| colors | `["Orange", "Yellow"]` | `["Yellow", "Orange"]` |
| size | `"MEDIUM"` | `null` |
| preferred_flowers | `["Carnation"]` | `["Baby's Breath", "Carnation", "Daisy", "Gerbera", "Hydrangea", "Lily", "Sunflower", "Tulip"]` |
| excluded_flowers | `["Rose"]` | `null` |

### pt_v2_just_because_delicate

Status esperado: `READY`; obtido: `None`.

Erro: `InvalidLLMOutputError: LLM returned a value outside the catalog for preferred_flowers.`.

### pt_v2_mothers_day_rustic

Status esperado: `READY`; obtido: `READY`.

| Campo | Esperado | Obtido |
|---|---|---|
| excluded_flowers | `["Lily"]` | `null` |

### pt_v2_anniversary_dual_style

Status esperado: `READY`; obtido: `READY`.

| Campo | Esperado | Obtido |
|---|---|---|
| styles | `["Classic", "Elegant"]` | `["Classic"]` |
| excluded_flowers | `["Carnation"]` | `null` |

### pt_v2_budget_not_size

Status esperado: `NEEDS_CLARIFICATION`; obtido: `NEEDS_CLARIFICATION`.

| Campo | Esperado | Obtido |
|---|---|---|
| styles | `["Romantic"]` | `null` |
| preferred_flowers | `null` | `["Rose"]` |

### pt_v2_stem_count_not_size

Status esperado: `NEEDS_CLARIFICATION`; obtido: `NEEDS_CLARIFICATION`.

| Campo | Esperado | Obtido |
|---|---|---|
| colors | `["White"]` | `null` |

### pt_v2_pink_is_color

Status esperado: `NEEDS_CLARIFICATION`; obtido: `None`.

Erro: `InvalidLLMOutputError: LLM returned a value outside the catalog for colors.`.

### pt_v2_exclusions_only

Status esperado: `NEEDS_CLARIFICATION`; obtido: `NEEDS_CLARIFICATION`.

| Campo | Esperado | Obtido |
|---|---|---|
| excluded_flowers | `["Hydrangea", "Tulip"]` | `null` |

### pt_v2_unsupported_flower

Status esperado: `NEEDS_CLARIFICATION`; obtido: `None`.

Erro: `InvalidLLMOutputError: LLM returned a value outside the catalog for preferred_flowers.`.

### pt_v2_unsupported_categories

Status esperado: `NEEDS_CLARIFICATION`; obtido: `None`.

Erro: `InvalidLLMOutputError: LLM returned a value outside the catalog for styles.`.

### pt_v2_small_no_occasion

Status esperado: `NEEDS_CLARIFICATION`; obtido: `None`.

Erro: `InvalidLLMOutputError: LLM returned a value outside the catalog for occasion.`.

### pt_v2_irrelevant_colors

Status esperado: `NEEDS_CLARIFICATION`; obtido: `NEEDS_CLARIFICATION`.

| Campo | Esperado | Obtido |
|---|---|---|
| colors | `null` | `["Blue"]` |

### pt_v2_size_unsure

Status esperado: `NEEDS_CLARIFICATION`; obtido: `NEEDS_CLARIFICATION`.

| Campo | Esperado | Obtido |
|---|---|---|
| styles | `["Elegant"]` | `null` |
| size | `null` | `"SMALL"` |

### en_v2_thanks_two_styles

Status esperado: `READY`; obtido: `NEEDS_CLARIFICATION`.

| Campo | Esperado | Obtido |
|---|---|---|
| size | `"MEDIUM"` | `null` |

### en_v2_low_budget_not_size

Status esperado: `NEEDS_CLARIFICATION`; obtido: `NEEDS_CLARIFICATION`.

| Campo | Esperado | Obtido |
|---|---|---|
| preferred_flowers | `null` | `["Baby's Breath", "Carnation", "Daisy", "Gerbera", "Hydrangea", "Lily", "Peony", "Rose", "Sunflower", "Tulip"]` |

### en_v2_no_specific_shade

Status esperado: `NEEDS_CLARIFICATION`; obtido: `NEEDS_CLARIFICATION`.

| Campo | Esperado | Obtido |
|---|---|---|
| occasion | `null` | `"Birthday"` |
| styles | `null` | `["Colorful"]` |
| colors | `null` | `["Pink", "Orange", "Yellow"]` |

### en_v2_preference_and_exclusion

Status esperado: `NEEDS_CLARIFICATION`; obtido: `None`.

Erro: `InvalidLLMOutputError: LLM returned a value outside the catalog for preferred_flowers.`.

### en_v2_unsupported_mixed

Status esperado: `NEEDS_CLARIFICATION`; obtido: `None`.

Erro: `InvalidLLMOutputError: LLM returned a value outside the catalog for styles.`.

### en_v2_unsupported_occasion

Status esperado: `NEEDS_CLARIFICATION`; obtido: `None`.

Erro: `InvalidLLMOutputError: LLM returned a value outside the catalog for occasion.`.

### en_v2_missing_style

Status esperado: `NEEDS_CLARIFICATION`; obtido: `None`.

Erro: `InvalidLLMOutputError: LLM returned a value outside the catalog for preferred_flowers.`.

### en_v2_irrelevant_numbers

Status esperado: `NEEDS_CLARIFICATION`; obtido: `NEEDS_CLARIFICATION`.

| Campo | Esperado | Obtido |
|---|---|---|
| occasion | `null` | `"Wedding"` |

## Reprodução

```bash
PYTHONPATH=backend backend/.venv/bin/python -m evaluation.bouquet_interpreter \
  --dataset-version 2 --model qwen3:1.7b --no-think \
  --base-url http://localhost:11434 --timeout-seconds 60 \
  --output evaluation/results/<novo-nome>.json
```

Use um novo nome para preservar esta execução. O código de saída do runner foi 1 por causa dos nove outputs rejeitados; todos os 30 casos foram executados e registrados.

## Validação final

- Ruff: backend e evaluation aprovados.
- pytest: 212 testes do backend e 23 da avaliação aprovados.
- `git diff --check`: aprovado.
- Hashes SHA-256 conferidos: dataset, código da aplicação, runner e JSONs anteriores preservados.
