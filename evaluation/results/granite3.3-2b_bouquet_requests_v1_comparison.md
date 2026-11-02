# Comparação — bouquet_requests_v1 com Granite3.3 2B

Execução do Granite em 2026-10-18. Dataset completo de 16 casos, timeout de 60 s, temperatura 0. Sem otimização específica ou alteração no pipeline. `OLLAMA_THINK` removido do ambiente do processo, sem `--think`/`--no-think`; `configuration.think: null` significa que a opção não foi enviada ao Ollama.

Os demais números vêm dos relatórios anteriores, sem reexecutá-los ou sobrescrevê-los. São resultados de execuções individuais locais, sem controle adicional de aquecimento/carga de hardware.

| Modelo | Exact match | Outputs aceitos | Hallucination rate | Status accuracy | Latência média | Latência total |
|---|---:|---:|---:|---:|---:|---:|
| Gemma3 1B | 2/16 (12.50%) | 9/16 (56.25%) | 17/33 (51.52%) | 5/16 (31.25%) | 3.157 s | 50.510 s |
| Qwen3 1.7B padrão | 11/16 (68.75%) | 13/16 (81.25%) | 1/47 (2.13%) | 13/16 (81.25%) | 28.941 s | 463.059 s |
| Qwen3 1.7B think:false | 6/16 (37.50%) | 13/16 (81.25%) | 5/50 (10.00%) | 11/16 (68.75%) | 5.007 s | 80.114 s |
| Granite3.3 2B | 2/16 (12.50%) | 9/16 (56.25%) | 9/41 (21.95%) | 8/16 (50.00%) | 7.410 s | 118.555 s |

Outputs aceitos passam por schema e validação de catálogo; isso não garante extração semanticamente correta. Exact match e status accuracy usam os 16 casos, incluindo falhas no denominador. Hallucination rate mede campos preenchidos quando o esperado era null, apenas nos casos aceitos; não contabiliza os outputs rejeitados nem todo tipo de erro semântico. Os denominadores variam entre modelos.

## Acurácia por campo

| Campo | Gemma | Qwen padrão | Qwen think:false | Granite |
|---|---:|---:|---:|---:|
| occasion | 43.75% | 75.00% | 68.75% | 50.00% |
| styles | 25.00% | 81.25% | 75.00% | 43.75% |
| colors | 18.75% | 75.00% | 75.00% | 50.00% |
| size | 37.50% | 81.25% | 68.75% | 25.00% |
| budget_max | 56.25% | 81.25% | 81.25% | 56.25% |
| preferred_flowers | 25.00% | 81.25% | 62.50% | 43.75% |
| excluded_flowers | 50.00% | 81.25% | 62.50% | 56.25% |

## Inferência Ollama

Métricas capturadas em 16/16 respostas tanto do Granite quanto do Qwen sem thinking, inclusive respostas rejeitadas. Gemma e Qwen padrão não possuem essas métricas nos artefatos anteriores: indisponíveis, sem estimativa. Durações abaixo convertidas de nanossegundos para segundos.

| Métrica | Granite total | Granite média/resposta | Qwen think:false total | Qwen think:false média/resposta |
|---|---:|---:|---:|---:|
| total_duration | 118.337077 s | 7.396067 s | 79.938713 s | 4.996170 s |
| load_duration | 4.000318 s | 0.250020 s | 2.677806 s | 0.167363 s |
| prompt_eval_duration | 45.226224 s | 2.826639 s | 28.774284 s | 1.798393 s |
| eval_duration | 68.721918 s | 4.295120 s | 48.163853 s | 3.010241 s |
| prompt_eval_count | 18559 | 1159.9375 | 16860 | 1053.7500 |
| eval_count | 1125 | 70.3125 | 956 | 59.7500 |

Taxa agregada de geração (`sum(eval_count) / sum(eval_duration)`): Granite **16.370 tokens/s**; Qwen sem thinking **19.849 tokens/s**.

## Observações do Granite

- 4 falhas de saída estruturada e 3 valores fora do catálogo; nenhum erro de transporte registrado. O runner não preserva o conteúdo bruto rejeitado, portanto não é possível detalhar a causa das quatro falhas estruturadas.
- Os dois casos integralmente corretos foram `large_graduation` e `unspecified_request`.
- Acertou o status de 1/4 casos READY e 7/12 NEEDS_CLARIFICATION.
- Houve tamanho inventado em cinco casos aceitos sem tamanho explícito.
- Nesta execução, teve o mesmo exact match e quantidade de outputs aceitos do Gemma, com menor hallucination rate e maior status accuracy, mas maior latência. Os dois relatórios do Qwen tiveram maior exact match e menor hallucination rate.
- Nenhuma alteração no pipeline foi feita com base nestes resultados.

## Artefatos

- [gemma3-1b_bouquet_requests_v1.json](gemma3-1b_bouquet_requests_v1.json)
- [qwen3-1.7b_bouquet_requests_v1.json](qwen3-1.7b_bouquet_requests_v1.json)
- [qwen3-1.7b-no-think_bouquet_requests_v1.json](qwen3-1.7b-no-think_bouquet_requests_v1.json)
- [granite3.3-2b_bouquet_requests_v1.json](granite3.3-2b_bouquet_requests_v1.json)

## Integridade dos arquivos utilizados

Hashes SHA-256 registrados durante a execução e conferidos após o término. Resultados anteriores, dataset e arquivos do pipeline abaixo permaneceram inalterados.

```text
db3e1245ab374ac726b3591bed665a49c662395ce94e46fe9a8b1105a277df6d  evaluation/data/bouquet_requests_v1.json
4fd139b2ba12272a52b6a4fbf5c8763e2faa5863430e3fda04bb78ddf9958262  evaluation/bouquet_interpreter.py
84d97982758d5dbd732285acabbb16252f2279f7a69646332368e165722fcf30  backend/app/prompts/bouquet_interpretation.py
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  backend/app/prompts/__init__.py
f28b95010d45afbb580d2eceebae80a89d62f7224877c1e98e989f533a74ee27  backend/app/schemas/bouquet_interpretation.py
f4c06ebaf8bbed891687ae57fa9601bfbe5d518bee804c3d658456c96b7b159c  backend/app/schemas/catalog.py
4a3bcf5ffa5bcc94287bf2a4526f07f3249259f2bcf9e2e3f3c6b9ba124fa8f4  backend/app/services/llm_bouquet_request_interpreter.py
37ba64c03c6e819a073256edf08f60ca2e4287c9a134e5de0f1a2e7e3640bbce  backend/app/services/ollama_provider.py
d0e182ee9cc9655ca6cac02f2b6364585ec89c1204a9b418b10bda4dc61779c8  evaluation/results/qwen3-1.7b-no-think_bouquet_requests_v1.json
b217fd749480b3a2bc057a34316329a60af63ae53dccc36ca069fcc58f5e15b4  evaluation/results/qwen3-1.7b_bouquet_requests_v1.json
d6694fadd0810d2f557cf28b834a7e147f90f9687e955732180950a937cd41f7  evaluation/results/gemma3-1b_bouquet_requests_v1.json
```
