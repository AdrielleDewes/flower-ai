# Gold Query Extractor v1 — revisão semântica v2

Decisões aplicadas em **2026-11-02**, após inspeção textual de todos os **46 casos / 184 campos**. Os sidecars continuam sendo propostas, com **reviewed: false em todos os casos**. Esta revisão não aprova automaticamente anotações e não executa extração. Substitui as propostas D1–D4 do relatório de revisão inicial.

## Decisões aplicadas

1. Escolha explicitamente não feita → AMBIGUOUS; falta explícita de preferência → ABSENT. Mantidos os cinco campos já ambíguos por indecisão. Não se propaga indecisão de cores aos quatro campos do extrator.
2. `pt_v2_unsupported_flower.excluded_flowers` mudou de ABSENT para **AMBIGUOUS**, com `value: null` e span `sem antúrios`. A intenção de excluir é inequívoca; o que está pendente é o mapeamento no catálogo. AMBIGUOUS é o estado pendente disponível, não uma afirmação de dúvida do cliente. O motivo é documentado nesta revisão, pois o formato de anotação só tipifica estado/evidência, sem campo próprio de diagnóstico.
3. `pt_v2_budget_not_size.preferred_flowers` permanece **ABSENT**: `um buquê romântico rosa` é uma construção adjetival de cor, compatível também com Pink em colors no dataset original. Não há pedido de Rose.
4. Nenhum caso apresenta afirmações efetivamente contraditórias sobre estes quatro campos; portanto não foi fabricado CONFLICT. Alternativas pequeno/grande continuam AMBIGUOUS.

Os valores originais dos datasets são mostrados abaixo sem alteração. Um valor esperado null não significa automaticamente ABSENT: pode coexistir com AMBIGUOUS e evidência de pendência. Valores em spans pendentes são candidatos ou null, não valores canônicos confirmados.

## Limitações confirmadas do formato existente

| Caso | Campo | O que foi preservado | O que não pode ser representado fielmente |
|---|---|---|---|
| `pt_v2_unsupported_flower` | preferred_flowers | RESOLVED [Rose], span `com orquídeas e rosas` | Rose resolvida **e** orquídeas não mapeadas simultaneamente. |
| `en_v2_unsupported_mixed` | preferred_flowers | RESOLVED [Tulip], span `with orchids and tulips` | Tulip resolvida **e** orchids não mapeadas simultaneamente. |
| `en_v2_unsupported_mixed` | excluded_flowers | RESOLVED [Rose], span `no dahlias or roses`; diagnóstico de Dahlia pendente nesta tabela | Rose excluída **e** exclusão de dahlias não mapeada simultaneamente. Não significa que só Rose foi negada. |

O loader exige RESOLVED quando o dataset contém um valor suportado. Mudar o campo misto inteiro para AMBIGUOUS contradiz esse requisito; inserir um item de evidência com value:null em RESOLVED falha na validação, e inserir Dahlia/Orchid como valor adicional contradiz o gold original e o catálogo. Não foram adicionadas chaves extras sem contrato nem inventado um estado PARTIAL. A evidência bruta e este diagnóstico preservam a informação para revisão, mas o avaliador atual **não pontua** a pendência por item. Essa é uma limitação de representação, não incerteza sobre o texto.

A exclusão isolada de antúrios pode ser preservada como pendente porque o dataset não contém valor canônico nesse campo. Seu estado/evidência é representável; o motivo específico out-of-catalog continua somente no relatório. ABSENT, por contrato, não aceita evidência: justificativas como falta de preferência e cor rosa aparecem nesta tabela, sem serem forçadas em spans positivos no JSON.

Outras limitações preexistentes: `under` não distingue teto exclusivo de inclusivo; escolha ainda não feita não informa todas as alternativas possíveis. Nenhuma regra ou contrato foi alterado para contornar essas limitações.

## Tabela compacta de revisão — todos os campos

Uma linha por caso/campo; os spans são `texto [start:end]`, com fim exclusivo, índices de caracteres Python. Evidência em linhas ABSENT é **contexto de revisão**, quando relevante, e não evidência positiva armazenada no sidecar. `—` significa nenhuma menção pertinente. Repetições idênticas de span em listas são exibidas uma única vez. A coluna de incerteza registra pendências de representação e ressalvas; `—` significa nenhuma pendência identificada nesta leitura, não aprovação.

| Caso | Campo | Estado proposto | Valor esperado original | Evidência / contexto original | Incerteza / ressalva |
|---|---|---|---|---|
| `romantic_red_birthday` | size | ABSENT | `null` | — | — |
| `romantic_red_birthday` | budget_max | RESOLVED | `"150"` | `up to R$150` [57:68] | — |
| `romantic_red_birthday` | preferred_flowers | RESOLVED | `["Rose"]` | `with roses` [30:40] | — |
| `romantic_red_birthday` | excluded_flowers | ABSENT | `null` | — | — |
| `small_wedding` | size | RESOLVED | `"SMALL"` | `A small elegant white bouquet` [0:29] | — |
| `small_wedding` | budget_max | RESOLVED | `"120"` | `under R$120` [57:68] | under é limite estrito; contrato só armazena o teto numérico. |
| `small_wedding` | preferred_flowers | RESOLVED | `["Lily"]` | `with lilies` [44:55] | — |
| `small_wedding` | excluded_flowers | ABSENT | `null` | — | — |
| `large_graduation` | size | RESOLVED | `"LARGE"` | `Please make a large rustic yellow bouquet` [0:41] | — |
| `large_graduation` | budget_max | ABSENT | `null` | — | — |
| `large_graduation` | preferred_flowers | RESOLVED | `["Sunflower"]` | `with sunflowers` [42:57] | — |
| `large_graduation` | excluded_flowers | ABSENT | `null` | — | — |
| `pt_anniversary_multiple` | size | RESOLVED | `"MEDIUM"` | `Quero um buquê médio` [0:20] | — |
| `pt_anniversary_multiple` | budget_max | RESOLVED | `"200"` | `até R$200` [90:99] | — |
| `pt_anniversary_multiple` | preferred_flowers | ABSENT | `null` | `rosa e branco` [44:57] | Coordenação de cores, não espécie. |
| `pt_anniversary_multiple` | excluded_flowers | ABSENT | `null` | — | — |
| `pt_valentines_exclusion` | size | ABSENT | `null` | — | — |
| `pt_valentines_exclusion` | budget_max | ABSENT | `null` | — | — |
| `pt_valentines_exclusion` | preferred_flowers | RESOLVED | `["Rose"]` | `Quero rosas vermelhas` [0:21] | — |
| `pt_valentines_exclusion` | excluded_flowers | RESOLVED | `["Lily"]` | `Não use lírios` [48:62] | — |
| `birthday_delivery_detail` | size | ABSENT | `null` | — | — |
| `birthday_delivery_detail` | budget_max | ABSENT | `null` | — | — |
| `birthday_delivery_detail` | preferred_flowers | ABSENT | `null` | — | — |
| `birthday_delivery_detail` | excluded_flowers | ABSENT | `null` | — | — |
| `blue_white_no_hydrangeas` | size | RESOLVED | `"SMALL"` | `Small blue and white modern bouquet` [0:35] | — |
| `blue_white_no_hydrangeas` | budget_max | ABSENT | `null` | — | — |
| `blue_white_no_hydrangeas` | preferred_flowers | ABSENT | `null` | — | — |
| `blue_white_no_hydrangeas` | excluded_flowers | RESOLVED | `["Hydrangea"]` | `no hydrangeas` [37:50] | — |
| `pt_colorful_gerberas` | size | RESOLVED | `"LARGE"` | `Buquê grande` [0:12] | — |
| `pt_colorful_gerberas` | budget_max | RESOLVED | `"90"` | `até R$90` [38:46] | — |
| `pt_colorful_gerberas` | preferred_flowers | RESOLVED | `["Gerbera"]` | `com gérberas` [24:36] | — |
| `pt_colorful_gerberas` | excluded_flowers | ABSENT | `null` | — | — |
| `anniversary_budget_only` | size | ABSENT | `null` | — | — |
| `anniversary_budget_only` | budget_max | RESOLVED | `"80"` | `budget no more than R$80` [39:63] | — |
| `anniversary_budget_only` | preferred_flowers | ABSENT | `null` | — | — |
| `anniversary_budget_only` | excluded_flowers | ABSENT | `null` | — | — |
| `pt_thank_you_exclusion` | size | ABSENT | `null` | — | — |
| `pt_thank_you_exclusion` | budget_max | ABSENT | `null` | — | — |
| `pt_thank_you_exclusion` | preferred_flowers | ABSENT | `null` | — | — |
| `pt_thank_you_exclusion` | excluded_flowers | RESOLVED | `["Daisy"]` | `sem margaridas` [48:62] | — |
| `wedding_peonies` | size | RESOLVED | `"MEDIUM"` | `For a wedding: medium, elegant, white and pink, with peonies` [0:60] | — |
| `wedding_peonies` | budget_max | ABSENT | `null` | — | — |
| `wedding_peonies` | preferred_flowers | RESOLVED | `["Peony"]` | `with peonies` [48:60] | — |
| `wedding_peonies` | excluded_flowers | ABSENT | `null` | — | — |
| `pt_minimalist_birthday` | size | ABSENT | `null` | — | — |
| `pt_minimalist_birthday` | budget_max | ABSENT | `null` | — | — |
| `pt_minimalist_birthday` | preferred_flowers | ABSENT | `null` | — | — |
| `pt_minimalist_birthday` | excluded_flowers | ABSENT | `null` | — | — |
| `graduation_delivery_detail` | size | ABSENT | `null` | — | — |
| `graduation_delivery_detail` | budget_max | ABSENT | `null` | — | — |
| `graduation_delivery_detail` | preferred_flowers | ABSENT | `null` | — | — |
| `graduation_delivery_detail` | excluded_flowers | ABSENT | `null` | — | — |
| `multiple_preferences` | size | RESOLVED | `"LARGE"` | `Roses and tulips, red and purple, classic and modern, large` [0:59] | — |
| `multiple_preferences` | budget_max | ABSENT | `null` | — | — |
| `multiple_preferences` | preferred_flowers | RESOLVED | `["Rose", "Tulip"]` | `Roses and tulips` [0:16] | — |
| `multiple_preferences` | excluded_flowers | ABSENT | `null` | — | — |
| `pt_mothers_day_exclusion` | size | RESOLVED | `"SMALL"` | `Buquê pequeno` [0:13] | — |
| `pt_mothers_day_exclusion` | budget_max | ABSENT | `null` | — | — |
| `pt_mothers_day_exclusion` | preferred_flowers | ABSENT | `null` | — | — |
| `pt_mothers_day_exclusion` | excluded_flowers | RESOLVED | `["Carnation"]` | `sem cravos` [35:45] | — |
| `unspecified_request` | size | ABSENT | `null` | — | — |
| `unspecified_request` | budget_max | ABSENT | `null` | — | — |
| `unspecified_request` | preferred_flowers | ABSENT | `null` | — | — |
| `unspecified_request` | excluded_flowers | ABSENT | `null` | — | — |
| `pt_v2_graduation_classic` | size | RESOLVED | `"SMALL"` | `quero um buquê pequeno` [33:55] | — |
| `pt_v2_graduation_classic` | budget_max | RESOLVED | `"135"` | `até R$135` [89:98] | — |
| `pt_v2_graduation_classic` | preferred_flowers | RESOLVED | `["Tulip"]` | `com tulipas` [76:87] | — |
| `pt_v2_graduation_classic` | excluded_flowers | ABSENT | `null` | — | — |
| `pt_v2_thanks_carnations` | size | RESOLVED | `"MEDIUM"` | `Um buquê médio` [0:14] | — |
| `pt_v2_thanks_carnations` | budget_max | RESOLVED | `"160"` | `Posso gastar até R$160` [83:105] | — |
| `pt_v2_thanks_carnations` | preferred_flowers | RESOLVED | `["Carnation"]` | `com cravos` [45:55] | — |
| `pt_v2_thanks_carnations` | excluded_flowers | RESOLVED | `["Rose"]` | `sem rosas` [72:81] | — |
| `pt_v2_just_because_delicate` | size | RESOLVED | `"LARGE"` | `buquê grande` [38:50] | — |
| `pt_v2_just_because_delicate` | budget_max | ABSENT | `null` | — | — |
| `pt_v2_just_because_delicate` | preferred_flowers | RESOLVED | `["Baby's Breath", "Daisy"]` | `com mosquitinho e margaridas` [70:98] | — |
| `pt_v2_just_because_delicate` | excluded_flowers | ABSENT | `null` | — | — |
| `pt_v2_mothers_day_rustic` | size | RESOLVED | `"SMALL"` | `quero um buquê pequeno` [17:39] | — |
| `pt_v2_mothers_day_rustic` | budget_max | ABSENT | `null` | — | — |
| `pt_v2_mothers_day_rustic` | preferred_flowers | RESOLVED | `["Gerbera"]` | `com gérberas` [59:71] | — |
| `pt_v2_mothers_day_rustic` | excluded_flowers | RESOLVED | `["Lily"]` | `sem lírios` [74:84] | — |
| `pt_v2_anniversary_dual_style` | size | RESOLVED | `"LARGE"` | `um buquê grande` [37:52] | — |
| `pt_v2_anniversary_dual_style` | budget_max | ABSENT | `null` | — | — |
| `pt_v2_anniversary_dual_style` | preferred_flowers | RESOLVED | `["Peony"]` | `com peônias` [94:105] | — |
| `pt_v2_anniversary_dual_style` | excluded_flowers | RESOLVED | `["Carnation"]` | `nada de cravos` [107:121] | — |
| `pt_v2_budget_not_size` | size | ABSENT | `null` | `Tenho até R$450` [0:15] | Orçamento não determina tamanho. |
| `pt_v2_budget_not_size` | budget_max | RESOLVED | `"450"` | `Tenho até R$450 para um buquê` [0:29] | — |
| `pt_v2_budget_not_size` | preferred_flowers | ABSENT | `null` | `um buquê romântico rosa` [21:44] | rosa modifica buquê como cor; nenhuma preferência por Rose. |
| `pt_v2_budget_not_size` | excluded_flowers | ABSENT | `null` | — | — |
| `pt_v2_stem_count_not_size` | size | ABSENT | `null` | `Quero doze rosas brancas` [0:24] | Quantidade não determina tamanho. |
| `pt_v2_stem_count_not_size` | budget_max | ABSENT | `null` | — | — |
| `pt_v2_stem_count_not_size` | preferred_flowers | RESOLVED | `["Rose"]` | `Quero doze rosas brancas` [0:24] | — |
| `pt_v2_stem_count_not_size` | excluded_flowers | ABSENT | `null` | — | — |
| `pt_v2_ambiguous_impact` | size | AMBIGUOUS | `null` | `ainda não escolhi cores nem tamanho` [50:85] | Escolha explicitamente pendente; AMBIGUOUS, não omissão. |
| `pt_v2_ambiguous_impact` | budget_max | ABSENT | `null` | — | — |
| `pt_v2_ambiguous_impact` | preferred_flowers | ABSENT | `null` | — | — |
| `pt_v2_ambiguous_impact` | excluded_flowers | ABSENT | `null` | — | — |
| `pt_v2_pink_is_color` | size | ABSENT | `null` | — | — |
| `pt_v2_pink_is_color` | budget_max | ABSENT | `null` | — | — |
| `pt_v2_pink_is_color` | preferred_flowers | ABSENT | `null` | `não tenho preferência por espécie de flor` [29:70] | Falta explícita de preferência: ABSENT; tons de rosa é cor. |
| `pt_v2_pink_is_color` | excluded_flowers | ABSENT | `null` | — | — |
| `pt_v2_exclusions_only` | size | ABSENT | `null` | — | — |
| `pt_v2_exclusions_only` | budget_max | ABSENT | `null` | — | — |
| `pt_v2_exclusions_only` | preferred_flowers | ABSENT | `null` | — | — |
| `pt_v2_exclusions_only` | excluded_flowers | RESOLVED | `["Hydrangea", "Tulip"]` | `Não coloque hortênsias nem tulipas no buquê` [0:43] | — |
| `pt_v2_unsupported_flower` | size | ABSENT | `null` | — | — |
| `pt_v2_unsupported_flower` | budget_max | ABSENT | `null` | — | — |
| `pt_v2_unsupported_flower` | preferred_flowers | RESOLVED | `["Rose"]` | `com orquídeas e rosas` [20:41] | LIMITE: Rose suportada; orquídeas não mapeadas; campo não representa resolução parcial. |
| `pt_v2_unsupported_flower` | excluded_flowers | AMBIGUOUS | `null` | `sem antúrios` [43:55] | Exclusão explícita; mapeamento pendente. AMBIGUOUS + null preserva evidência sem inventar espécie. Motivo estruturado não existe no formato; diagnóstico documentado aqui. |
| `pt_v2_unsupported_categories` | size | ABSENT | `null` | — | — |
| `pt_v2_unsupported_categories` | budget_max | ABSENT | `null` | — | — |
| `pt_v2_unsupported_categories` | preferred_flowers | RESOLVED | `["Daisy"]` | `com margaridas` [50:64] | — |
| `pt_v2_unsupported_categories` | excluded_flowers | ABSENT | `null` | — | — |
| `pt_v2_small_no_occasion` | size | RESOLVED | `"SMALL"` | `Pode ser um buquê pequeno` [0:25] | Pode ser é solicitação de pequeno; não há tamanhos alternativos. |
| `pt_v2_small_no_occasion` | budget_max | RESOLVED | `"72.50"` | `até R$72,50` [75:86] | — |
| `pt_v2_small_no_occasion` | preferred_flowers | RESOLVED | `["Sunflower", "Carnation"]` | `com girassóis e cravos` [38:60] | — |
| `pt_v2_small_no_occasion` | excluded_flowers | RESOLVED | `["Peony"]` | `sem peônias` [62:73] | — |
| `pt_v2_irrelevant_colors` | size | ABSENT | `null` | — | — |
| `pt_v2_irrelevant_colors` | budget_max | ABSENT | `null` | — | — |
| `pt_v2_irrelevant_colors` | preferred_flowers | ABSENT | `null` | — | — |
| `pt_v2_irrelevant_colors` | excluded_flowers | ABSENT | `null` | — | — |
| `pt_v2_size_unsure` | size | AMBIGUOUS | `null` | `Ainda não sei se pequeno ou grande` [53:87] | SMALL/LARGE são alternativas não decididas, não CONFLICT. |
| `pt_v2_size_unsure` | budget_max | ABSENT | `null` | — | — |
| `pt_v2_size_unsure` | preferred_flowers | ABSENT | `null` | — | — |
| `pt_v2_size_unsure` | excluded_flowers | ABSENT | `null` | — | — |
| `en_v2_birthday_modern` | size | RESOLVED | `"MEDIUM"` | `a medium modern orange bouquet` [18:48] | — |
| `en_v2_birthday_modern` | budget_max | RESOLVED | `"175"` | `maximum R$175` [76:89] | — |
| `en_v2_birthday_modern` | preferred_flowers | RESOLVED | `["Gerbera"]` | `with gerberas` [49:62] | — |
| `en_v2_birthday_modern` | excluded_flowers | RESOLVED | `["Daisy"]` | `no daisies` [64:74] | — |
| `en_v2_wedding_minimalist` | size | RESOLVED | `"LARGE"` | `A large minimalist purple and white bouquet` [0:43] | — |
| `en_v2_wedding_minimalist` | budget_max | ABSENT | `null` | — | — |
| `en_v2_wedding_minimalist` | preferred_flowers | RESOLVED | `["Hydrangea"]` | `with hydrangeas` [59:74] | — |
| `en_v2_wedding_minimalist` | excluded_flowers | RESOLVED | `["Carnation"]` | `no carnations` [79:92] | — |
| `en_v2_valentines_classic` | size | RESOLVED | `"SMALL"` | `Please make a small classic pink bouquet` [0:40] | — |
| `en_v2_valentines_classic` | budget_max | RESOLVED | `"110"` | `up to R$110` [92:103] | — |
| `en_v2_valentines_classic` | preferred_flowers | RESOLVED | `["Tulip", "Baby's Breath"]` | `with tulips and baby's breath` [61:90] | — |
| `en_v2_valentines_classic` | excluded_flowers | ABSENT | `null` | — | — |
| `en_v2_thanks_two_styles` | size | RESOLVED | `"MEDIUM"` | `a medium delicate and elegant yellow bouquet` [18:62] | — |
| `en_v2_thanks_two_styles` | budget_max | ABSENT | `null` | — | — |
| `en_v2_thanks_two_styles` | preferred_flowers | RESOLVED | `["Lily"]` | `with lilies` [63:74] | — |
| `en_v2_thanks_two_styles` | excluded_flowers | RESOLVED | `["Rose", "Peony"]` | `Leave out roses and peonies` [76:103] | — |
| `en_v2_mothers_day_colorful` | size | RESOLVED | `"LARGE"` | `A large colorful blue and pink bouquet` [0:38] | — |
| `en_v2_mothers_day_colorful` | budget_max | ABSENT | `null` | — | — |
| `en_v2_mothers_day_colorful` | preferred_flowers | RESOLVED | `["Hydrangea"]` | `with hydrangeas` [57:72] | — |
| `en_v2_mothers_day_colorful` | excluded_flowers | ABSENT | `null` | — | — |
| `en_v2_low_budget_not_size` | size | ABSENT | `null` | `with a budget of at most R$35` [44:73] | Orçamento não determina tamanho. |
| `en_v2_low_budget_not_size` | budget_max | RESOLVED | `"35"` | `with a budget of at most R$35` [44:73] | — |
| `en_v2_low_budget_not_size` | preferred_flowers | ABSENT | `null` | — | — |
| `en_v2_low_budget_not_size` | excluded_flowers | ABSENT | `null` | — | — |
| `en_v2_ambiguous_size` | size | AMBIGUOUS | `null` | `Something reasonably sized and lovely for graduation; I have not decided on a size` [0:82] | Tamanho indeterminado e explicitamente não decidido. |
| `en_v2_ambiguous_size` | budget_max | ABSENT | `null` | — | — |
| `en_v2_ambiguous_size` | preferred_flowers | ABSENT | `null` | — | — |
| `en_v2_ambiguous_size` | excluded_flowers | ABSENT | `null` | — | — |
| `en_v2_no_specific_shade` | size | ABSENT | `null` | `I have not chosen any specific colors yet` [50:91] | Indecisão só sobre cores; não se propaga a tamanho. |
| `en_v2_no_specific_shade` | budget_max | ABSENT | `null` | — | — |
| `en_v2_no_specific_shade` | preferred_flowers | ABSENT | `null` | `I have not chosen any specific colors yet` [50:91] | Indecisão só sobre cores; nenhuma menção de espécie. |
| `en_v2_no_specific_shade` | excluded_flowers | ABSENT | `null` | — | — |
| `en_v2_preference_and_exclusion` | size | ABSENT | `null` | — | — |
| `en_v2_preference_and_exclusion` | budget_max | ABSENT | `null` | — | — |
| `en_v2_preference_and_exclusion` | preferred_flowers | RESOLVED | `["Sunflower", "Daisy"]` | `Please use sunflowers and daisies` [0:33] | — |
| `en_v2_preference_and_exclusion` | excluded_flowers | RESOLVED | `["Lily", "Carnation"]` | `avoid lilies and carnations` [39:66] | — |
| `en_v2_unsupported_mixed` | size | RESOLVED | `"SMALL"` | `A small bohemian teal and yellow bouquet` [0:40] | — |
| `en_v2_unsupported_mixed` | budget_max | ABSENT | `null` | — | — |
| `en_v2_unsupported_mixed` | preferred_flowers | RESOLVED | `["Tulip"]` | `with orchids and tulips` [41:64] | LIMITE: Tulip suportada; orchids não mapeadas; sem estado parcial por item. |
| `en_v2_unsupported_mixed` | excluded_flowers | RESOLVED | `["Rose"]` | `no dahlias or roses` [66:85] | LIMITE: Rose excluída; dahlias também negadas, mas não mapeadas. Negação completa preservada; pendência só nesta revisão, não na estrutura de estado. |
| `en_v2_unsupported_occasion` | size | RESOLVED | `"MEDIUM"` | `An elegant white medium bouquet` [0:31] | — |
| `en_v2_unsupported_occasion` | budget_max | ABSENT | `null` | — | — |
| `en_v2_unsupported_occasion` | preferred_flowers | RESOLVED | `["Peony"]` | `with peonies` [56:68] | — |
| `en_v2_unsupported_occasion` | excluded_flowers | ABSENT | `null` | — | — |
| `en_v2_missing_style` | size | RESOLVED | `"SMALL"` | `a small red bouquet` [16:35] | — |
| `en_v2_missing_style` | budget_max | RESOLVED | `"95"` | `under R$95` [51:61] | under é limite estrito; contrato só armazena o teto numérico. |
| `en_v2_missing_style` | preferred_flowers | RESOLVED | `["Carnation"]` | `of carnations` [36:49] | — |
| `en_v2_missing_style` | excluded_flowers | ABSENT | `null` | — | — |
| `en_v2_irrelevant_numbers` | size | ABSENT | `null` | — | — |
| `en_v2_irrelevant_numbers` | budget_max | ABSENT | `null` | `Deliver to apartment 250 at 10; that is not my budget` [38:91] | Endereço/horário explicitamente não são orçamento. |
| `en_v2_irrelevant_numbers` | preferred_flowers | RESOLVED | `["Rose"]` | `A classic bouquet with roses` [0:28] | — |
| `en_v2_irrelevant_numbers` | excluded_flowers | ABSENT | `null` | — | — |
| `en_v2_occasion_no_defaults` | size | AMBIGUOUS | `null` | `with no particular flower, color, style or size chosen` [29:83] | chosen declara escolha ainda não feita; decisão 1 aplicada. |
| `en_v2_occasion_no_defaults` | budget_max | ABSENT | `null` | — | — |
| `en_v2_occasion_no_defaults` | preferred_flowers | AMBIGUOUS | `null` | `with no particular flower, color, style or size chosen` [29:83] | chosen declara escolha ainda não feita; não é lack of preference. |
| `en_v2_occasion_no_defaults` | excluded_flowers | ABSENT | `null` | — | — |
| `en_v2_missing_colors` | size | RESOLVED | `"MEDIUM"` | `a medium rustic bouquet` [16:39] | — |
| `en_v2_missing_colors` | budget_max | ABSENT | `null` | — | — |
| `en_v2_missing_colors` | preferred_flowers | RESOLVED | `["Sunflower"]` | `with sunflowers` [40:55] | — |
| `en_v2_missing_colors` | excluded_flowers | RESOLVED | `["Hydrangea"]` | `excluding hydrangeas` [57:77] | — |

## Resultado da revisão

- 46 casos preservados: 21 PT / 25 EN.
- Estados: ABSENT=100, AMBIGUOUS=6, RESOLVED=78.
- 93 spans de anotação; todos conferidos contra o texto original. Os contextos adicionais da tabela também foram conferidos por igualdade exata.
- Uma mudança de estado: excluded_flowers de `pt_v2_unsupported_flower`. Nenhum valor esperado do dataset, outra decisão de estado ou flag reviewed foi alterado.
- Não há questão semântica nova sobre indecisão, falta de preferência ou rosa/cor; as decisões fornecidas foram aplicadas. Permanecem as limitações de resolução parcial acima, que precisam ser reconhecidas antes de qualquer avaliação de pendências por item.
- Os sidecars continuam bloqueados para benchmark. Validação técnica utiliza somente cópias temporárias com a flag de revisão habilitada; isso não modifica nem aprova os arquivos de origem.
