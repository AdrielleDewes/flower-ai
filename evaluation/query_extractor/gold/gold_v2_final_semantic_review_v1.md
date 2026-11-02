# Gold_v2 — revisão semântica final v1

**Data: 2026-11-02. Conclusão: anotações prontas para aprovação humana.** Não foram identificadas inconsistências semânticas que exijam correção dentro do escopo dos quatro campos e do contrato v2. Nenhum caso foi aprovado automaticamente.

## Método e cobertura

Revisados os textos originais dos 46 casos (16 no dataset v1 e 30 no v2), usando as queries como fonte de verdade, sem consultar saídas do extrator ou do LLM. A revisão cobriu os 184 campos: 75 RESOLVED, 100 ABSENT, 3 PARTIAL e 6 AMBIGUOUS. Conferidos os 86 valores resolvidos, as 9 menções pendentes e os contextos de pedido, exclusão, limite monetário e indecisão. Não há afirmações contraditórias que justifiquem CONFLICT.

A validação direta de todos os campos passou: hashes dos datasets, catálogo dos valores suportados, ordem dos valores, estados, motivos, candidatos e posições no texto. Os 95 spans de suporte e os 9 spans de menção coincidem exatamente com as queries. A validação chamou apenas o validador de campos, sem executar extract e sem alterar reviewed nem em cópias temporárias. Essa checagem estrutural complementa, não substitui, a leitura semântica.

## Todas as menções pendentes e todos os campos PARTIAL

| Caso | Campo / estado | Resolvido | Menção pendente e motivo | Evidência original | Parecer |
|---|---|---|---|---|---|
| `pt_v2_ambiguous_impact` | size / AMBIGUOUS | — | `ainda não escolhi cores nem tamanho` / UNDECIDED | `ainda não escolhi cores nem tamanho` [50:85] | Manter. Escolha explicitamente não feita; nenhum candidato deve ser inferido. |
| `pt_v2_unsupported_flower` | preferred_flowers / PARTIAL | Rose | `orquídeas` / OUT_OF_CATALOG | `com orquídeas e rosas` [20:41] | Manter. Pedido explícito; espécie indisponível no catálogo, sem substituição. |
| `pt_v2_unsupported_flower` | excluded_flowers / AMBIGUOUS | — | `antúrios` / OUT_OF_CATALOG | `sem antúrios` [43:55] | Manter. Exclusão explícita preservada; a pendência é de catálogo, não de intenção. |
| `pt_v2_size_unsure` | size / AMBIGUOUS | — | `pequeno ou grande` / UNDECIDED | `Ainda não sei se pequeno ou grande` [53:87] | Manter. Alternativas SMALL/LARGE não decididas; não são valores confirmados nem conflito. |
| `en_v2_ambiguous_size` | size / AMBIGUOUS | — | `I have not decided on a size` / UNDECIDED | `Something reasonably sized and lovely for graduation; I have not decided on a size` [0:82] | Manter. Escolha explicitamente não feita; nenhum candidato deve ser inferido. |
| `en_v2_unsupported_mixed` | preferred_flowers / PARTIAL | Tulip | `orchids` / OUT_OF_CATALOG | `with orchids and tulips` [41:64] | Manter. Pedido explícito; espécie indisponível no catálogo, sem substituição. |
| `en_v2_unsupported_mixed` | excluded_flowers / PARTIAL | Rose | `dahlias` / OUT_OF_CATALOG | `no dahlias or roses` [66:85] | Manter. Exclusão explícita preservada; a pendência é de catálogo, não de intenção. |
| `en_v2_occasion_no_defaults` | size / AMBIGUOUS | — | `with no particular flower, color, style or size chosen` / UNDECIDED | `with no particular flower, color, style or size chosen` [29:83] | Manter. Escolha explicitamente não feita; nenhum candidato deve ser inferido. |
| `en_v2_occasion_no_defaults` | preferred_flowers / AMBIGUOUS | — | `with no particular flower, color, style or size chosen` / UNDECIDED | `with no particular flower, color, style or size chosen` [29:83] | Manter. Escolha explicitamente não feita; nenhum candidato deve ser inferido. |

Os três campos PARTIAL estão corretamente limitados aos campos de flores em `pt_v2_unsupported_flower` e `en_v2_unsupported_mixed`. Os nomes não suportados não foram inventados como valores canônicos. A exclusão isolada de antúrios está corretamente pendente: AMBIGUOUS/OUT_OF_CATALOG, não ABSENT. Em `no dahlias or roses`, o operador no tem escopo sobre ambos os nomes; or não indica escolha indecisa nesse contexto.

## AMBIGUOUS versus ABSENT e flor versus cor

| Caso / grupo | Leitura confirmada | Correção proposta |
|---|---|---|
| `pt_v2_ambiguous_impact`, `pt_v2_size_unsure`, `en_v2_ambiguous_size` | Há indecisão explícita de tamanho; manter AMBIGUOUS/UNDECIDED. Não inferir MEDIUM de reasonably sized. | Nenhuma. |
| `en_v2_occasion_no_defaults` | no particular … chosen expressa escolha não feita; manter tamanho e flores preferidas como AMBIGUOUS/UNDECIDED, conforme a decisão semântica aprovada. Não confundir com indiferença. | Nenhuma. |
| `pt_v2_pink_is_color` | não tenho preferência por espécie de flor é ausência explícita de preferência, não escolha pendente; preferred_flowers ABSENT. tons de rosa e roxo são cores. | Nenhuma. |
| `pt_v2_budget_not_size` | um buquê romântico rosa usa rosa como adjetivo de cor. preferred_flowers ABSENT; o orçamento alto não determina tamanho. | Nenhuma. |
| `pt_anniversary_multiple` | rosa e branco é coordenação de cores, sem preferência por Rose. | Nenhuma. |
| `wedding_peonies`, `en_v2_valentines_classic`, `en_v2_mothers_day_colorful` | pink é cor; as preferências são somente as flores explicitamente solicitadas. | Nenhuma. |
| `en_v2_no_specific_shade`, `en_v2_missing_colors` | Indecisão sobre cores não torna tamanho ou espécies automaticamente ambíguos. Preservar os campos pertinentes explicitamente presentes. | Nenhuma. |

## Demais valores resolvidos e contextos negativos

- Tamanhos: os 23 valores confirmados têm tamanho explicitamente solicitado, inclusive as listas elípticas de `multiple_preferences` e `wedding_peonies`. Pode ser um buquê pequeno é uma solicitação de SMALL, não escolha entre tamanhos. Nenhum tamanho foi derivado de preço, quantidade ou ocasião.
- Orçamentos: os 13 valores confirmados têm limites monetários explícitos. R$72,50 corresponde a 72.50, sem perda de centavos. Os demais números de horário, endereço e quantidade não foram tratados como orçamento.
- Flores: as 50 ocorrências de valores canônicos confirmados (preferência ou exclusão, contando cada valor por campo) correspondem a pedidos literais, traduções usuais ou plurais. mosquitinho → Baby's Breath é coerente com o catálogo. Não há espécie extraída por mera associação com cor, estilo ou ocasião.
- Exclusões: os contextos Não use, sem, nada de, Não coloque … nem, no, avoid, Leave out e excluding foram preservados; não foram invertidos para preferência. Listas coordenadas compartilham corretamente o cue de inclusão/exclusão.
- Detalhes de entrega, horários, endereço, cores da portaria e finalidade do presente não adicionam valores aos quatro campos. Nenhuma ausência foi convertida em preferência ou exclusão implícita.

## Anotações questionáveis e correções

**Nenhuma correção de estado, valor, motivo, candidato ou span é proposta.** Os pontos antes questionados — rosa/cor, escolha não feita versus indiferença e exclusões fora do catálogo — estão representados de acordo com as decisões semânticas e o contrato v2.

Permanecem apenas ressalvas de representação já assumidas, sem exigir alteração do gold:

- under R$120 e under R$95 indicam teto estrito; budget_max não guarda uma flag separada de inclusão da fronteira. Os números anotados são os limites expressos, não promessa de que igualdade seja permitida.
- AMBIGUOUS com OUT_OF_CATALOG significa mapeamento pendente, não hesitação do cliente. Os relatórios devem continuar separando esse motivo de UNDECIDED.
- Há contextos de evidência mais amplos que o mínimo necessário, especialmente nas frases elípticas e de indecisão. Eles são semanticamente pertinentes; não há necessidade de encurtá-los ou alinhá-los às regras do extrator.

## Estado de aprovação

Os dois sidecars [v1/gold_v2](bouquet_requests_v1_gold_v2.json) e [v2/gold_v2](bouquet_requests_v2_gold_v2.json) estão **prontos para aprovação humana**, mas todos os casos permanecem `reviewed: false`. Nenhum arquivo de anotação, regra, dataset, prompt ou resultado anterior foi alterado nesta revisão. Somente este relatório foi criado. Nenhum benchmark foi executado.
