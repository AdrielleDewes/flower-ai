# Query Extractor v1 — revisão das anotações gold v1 (proposta)

> Histórico da proposta inicial. As decisões semânticas posteriores e a tabela
> atual dos 184 campos estão na [revisão semântica v2](gold_v1_semantic_review_v2.md).
> As contagens e propostas abaixo descrevem a versão anterior; em particular,
> `sem antúrios` agora tem estado AMBIGUOUS com evidência, e não ABSENT.

Preparado em **2026-11-02**. Status: **aguardando aprovação manual**. Esta revisão foi feita a partir dos textos originais e das expectativas dos datasets; não utiliza saídas do Query Extractor ou do LLM. Nenhuma extração ou benchmark dos 46 casos foi executado.

## Arquivos, cobertura e bloqueio de aprovação

| Dataset | Casos | PT / EN | Campos | RESOLVED | ABSENT | AMBIGUOUS | CONFLICT | Spans |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| [v1](bouquet_requests_v1_gold_v1.json) | 16 | 6 / 10 | 64 | 24 | 40 | 0 | 0 | 25 |
| [v2](bouquet_requests_v2_gold_v1.json) | 30 | 15 / 15 | 120 | 54 | 61 | 5 | 0 | 67 |

Total: **46 casos, 21 PT e 25 EN; 184 campos; 78 RESOLVED, 101 ABSENT, 5 AMBIGUOUS e 0 CONFLICT; 92 spans**. Estas são contagens das anotações, não métricas do extrator.

Todos os casos permanecem com `reviewed: false`. O loader existente recusa os sidecars salvos, impedindo seu uso acidental como gold aprovado. `reviewed` só deve ser alterado após a decisão humana; nenhum teste muda os arquivos de origem. Para verificar a estrutura, foram usadas cópias temporárias com a flag habilitada, explicitamente sem efeito de aprovação e sem chamada a `extract`.

### SHA-256 dos datasets originais

- v1: `db3e1245ab374ac726b3591bed665a49c662395ce94e46fe9a8b1105a277df6d`.
- v2: `f96fe878f3ada60a353db035d16a7d768c1d13053635a42f520159b7528bc143`.

Os sidecars usam `annotation_version: 1` e o formato existente: ID, idioma, flag de revisão e os quatro campos com estado e evidências. Os valores de campos RESOLVED vêm das expectativas originais **após verificação textual individual**. Os rótulos de estado não foram deduzidos automaticamente de null. Não foi necessário alterar nenhum valor esperado dos quatro campos.

## Critérios de anotação

- RESOLVED: há evidência explícita para um valor canônico suportado. Quantidade de hastes e preço não determinam tamanho.
- ABSENT: não há valor identificável do campo na projeção do catálogo; no caso de falta explícita de preferência, não se inventa uma exclusão. A ressalva de espécies não suportadas está em D3.
- AMBIGUOUS: o texto declara escolha pendente ou tamanho indeterminado, sem confirmar um valor único. Preservar contexto de indecisão nos spans. A distinção de escolha pendente versus indiferença requer a decisão D2 abaixo.
- CONFLICT: exigiria afirmações incompatíveis efetivamente feitas, não apenas alternativas. Nenhum dos 46 textos apresenta esse caso. Não foram inventados conflitos para aumentar cobertura.
- Spans usam índices de caracteres Python no texto original, fim exclusivo. Incluem pedido/objeto, limite monetário ou negação. Quando duas flores compartilham o mesmo cue, o span coordenado é repetido para cada valor.
- ABSENT tem evidência vazia, conforme o contrato do loader. A justificativa de ausência/escopo é documentada aqui, não por evidência positiva artificial.
- Datas, horários e endereço não são orçamento; cores, estilos ou ocasiões não implicam espécie. A incerteza sobre cores não se propaga aos quatro campos fora de sua relação textual.
- As anotações não são adaptadas às construções que o extrator atual reconhece. Uma solicitação inequívoca continua RESOLVED mesmo que as regras do experimento se abstenham.

## Pontos para decisão humana

### D1 — tamanho explicitamente não decidido

| Caso | Proposta | Evidência original | Justificativa |
|---|---|---|---|
| `pt_v2_ambiguous_impact` | size AMBIGUOUS | `ainda não escolhi cores nem tamanho` | Tamanho está explicitamente pendente; não é apenas ausência de menção. |
| `pt_v2_size_unsure` | size AMBIGUOUS | `Ainda não sei se pequeno ou grande` | SMALL e LARGE são alternativas, não dois pedidos afirmados. Ambos têm evidência, sem preferência vencedora. |
| `en_v2_ambiguous_size` | size AMBIGUOUS | `Something reasonably sized and lovely for graduation; I have not decided on a size` | “Reasonably sized” não corresponde inequivocamente a SMALL/MEDIUM/LARGE; há declaração de indecisão. |

**Decisão proposta:** aprovar esses três estados AMBIGUOUS. Os três tamanhos eram null no dataset, de modo que nenhum valor original muda. A distinção de estado será avaliada separadamente da extração de valores.

### D2 — ausência de escolha versus ausência de preferência

`en_v2_occasion_no_defaults`: `with no particular flower, color, style or size chosen`. Proposta: **size e preferred_flowers AMBIGUOUS**, com `value: null` nos spans. O texto diz que nada foi escolhido; não declara explicitamente indiferença ou liberdade para qualquer opção. Uma leitura alternativa igualmente plausível é tratar a formulação como ausência de restrições e anotar ambos como ABSENT.

**Pergunta pendente:** aprovar a leitura de escolha pendente ou preferir ABSENT para esses dois campos? Os arquivos contêm a primeira leitura, ainda bloqueada para benchmark. A decisão altera avaliação de estados e exact match, mas não cria valores gold.

Em contraste, `pt_v2_pink_is_color` diz `não tenho preferência por espécie de flor`: preferred_flowers ABSENT, sem razão para considerar a espécie pendente. `en_v2_no_specific_shade` só declara cores não escolhidas, portanto não torna size ou flores ambíguos.

### D3 — valores não suportados pelo catálogo

| Caso | Projeção proposta | Informação que o formato não representa |
|---|---|---|
| `pt_v2_unsupported_flower` | preferred_flowers RESOLVED [Rose]; excluded_flowers ABSENT | `com orquídeas e rosas, sem antúrios` pede também Orchid e exclui Anthurium, ambos fora do catálogo. ABSENT na exclusão significa zero exclusões **canônicas suportadas**, não ausência de intenção. |
| `en_v2_unsupported_mixed` | preferred_flowers RESOLVED [Tulip]; excluded_flowers RESOLVED [Rose] | `with orchids and tulips, no dahlias or roses` inclui Orchid e exclui Dahlia, sem representação canônica disponível. O escopo de “no … or …” nega ambas; não é uma escolha indecisa. |

Os spans mantêm as coordenações e negações completas, inclusive nomes não suportados quando necessários ao contexto. Os valores anotados permanecem exatamente os do dataset.

**Decisão proposta:** aprovar a projeção por catálogo, consistente com os rótulos existentes. Se a intenção é avaliar também reconhecimento de restrições não representáveis, esse objetivo precisa de anotação/diagnóstico adicional em uma versão futura; não se deve converter silenciosamente nomes não suportados em outras espécies nem fingir ausência de intenção. Nenhuma mudança de contrato foi feita para contornar essa limitação.

### D4 — “rosa” como cor, não espécie

`pt_anniversary_multiple`: `rosa e branco` é uma lista de cores; preferred_flowers ABSENT. `pt_v2_pink_is_color`: `tons de rosa e roxo` é explicitamente cor. `pt_v2_budget_not_size`: `um buquê romântico rosa` foi interpretado como adjetivo de cor, em acordo com o dataset original (Pink em colors, fora destes quatro campos), sem preferência por Rose.

**Decisão proposta:** manter ABSENT para espécie nesses três casos. O singular “rosa” isoladamente é polissêmico; em especial, confirmar a leitura adjetival de `pt_v2_budget_not_size` antes de aprovar o gold. Essa decisão vem do contexto, não da implementação do matcher.

### D5 — cortes e elipses do contrato existente

- `small_wedding` e `en_v2_missing_style`: “under R$120/95” é estritamente menor, mas o contrato só oferece budget_max numérico. Preservados 120 e 95 como limites, sem adicionar inclusão/exclusão de fronteira. Isto é limitação de representação, não erro numérico corrigido no dataset.
- `multiple_preferences`: LARGE e Rose/Tulip são pedidos explícitos numa lista nominal, mesmo sem o substantivo bouquet. O span de tamanho preserva a lista de atributos para evitar uma palavra isolada sem referente.
- `wedding_peonies`: MEDIUM é explicitamente um atributo do pedido floral, apesar da elipse. O span preserva o enunciado com peonies para situar o tamanho.
- `pt_v2_small_no_occasion`: “Pode ser um buquê pequeno” é uma solicitação aceitável de tamanho, não uma alternativa aberta entre tamanhos. Mantido SMALL RESOLVED; uma regra conservadora pode abster-se, mas o gold não deve ser alterado por isso.
- `pt_v2_stem_count_not_size`: doze rosas confirma a espécie, não SMALL/MEDIUM/LARGE. `pt_v2_budget_not_size` e `en_v2_low_budget_not_size`: orçamento não confirma tamanho.
- `birthday_delivery_detail`, `graduation_delivery_detail`, `pt_mothers_day_exclusion`, `pt_v2_irrelevant_colors`, `pt_v2_exclusions_only`, `en_v2_irrelevant_numbers` e `en_v2_mothers_day_colorful`: horários/endereço/entrega não adicionam valores a estes quatro campos.

Não foi encontrada inconsistência direta entre valores suportados dos quatro campos e os textos. As diferenças propostas em relação ao uso ingênuo das expectativas são **cinco estados AMBIGUOUS em vez de ABSENT para valores null**. As questões D2–D4 são decisões semânticas/ontológicas a confirmar, não incompatibilidades escondidas pelo loader.

## Inventário de todos os casos

Legenda: `A` = ABSENT; `R` = RESOLVED; `M` = AMBIGUOUS. Os números são valores gold, não resultados de extração. Todas as evidências e offsets estão nos dois sidecars.

| Dataset / caso | Idioma | size | budget_max | preferred_flowers | excluded_flowers |
|---|---|---|---|---|---|
| v1 / `romantic_red_birthday` | en | A | R 150 | R Rose | A |
| v1 / `small_wedding` | en | R SMALL | R 120 | R Lily | A |
| v1 / `large_graduation` | en | R LARGE | A | R Sunflower | A |
| v1 / `pt_anniversary_multiple` | pt | R MEDIUM | R 200 | A | A |
| v1 / `pt_valentines_exclusion` | pt | A | A | R Rose | R Lily |
| v1 / `birthday_delivery_detail` | en | A | A | A | A |
| v1 / `blue_white_no_hydrangeas` | en | R SMALL | A | A | R Hydrangea |
| v1 / `pt_colorful_gerberas` | pt | R LARGE | R 90 | R Gerbera | A |
| v1 / `anniversary_budget_only` | en | A | R 80 | A | A |
| v1 / `pt_thank_you_exclusion` | pt | A | A | A | R Daisy |
| v1 / `wedding_peonies` | en | R MEDIUM | A | R Peony | A |
| v1 / `pt_minimalist_birthday` | pt | A | A | A | A |
| v1 / `graduation_delivery_detail` | en | A | A | A | A |
| v1 / `multiple_preferences` | en | R LARGE | A | R Rose, Tulip | A |
| v1 / `pt_mothers_day_exclusion` | pt | R SMALL | A | A | R Carnation |
| v1 / `unspecified_request` | en | A | A | A | A |
| v2 / `pt_v2_graduation_classic` | pt | R SMALL | R 135 | R Tulip | A |
| v2 / `pt_v2_thanks_carnations` | pt | R MEDIUM | R 160 | R Carnation | R Rose |
| v2 / `pt_v2_just_because_delicate` | pt | R LARGE | A | R Baby's Breath, Daisy | A |
| v2 / `pt_v2_mothers_day_rustic` | pt | R SMALL | A | R Gerbera | R Lily |
| v2 / `pt_v2_anniversary_dual_style` | pt | R LARGE | A | R Peony | R Carnation |
| v2 / `pt_v2_budget_not_size` | pt | A | R 450 | A | A |
| v2 / `pt_v2_stem_count_not_size` | pt | A | A | R Rose | A |
| v2 / `pt_v2_ambiguous_impact` | pt | M | A | A | A |
| v2 / `pt_v2_pink_is_color` | pt | A | A | A | A |
| v2 / `pt_v2_exclusions_only` | pt | A | A | A | R Hydrangea, Tulip |
| v2 / `pt_v2_unsupported_flower` | pt | A | A | R Rose | A |
| v2 / `pt_v2_unsupported_categories` | pt | A | A | R Daisy | A |
| v2 / `pt_v2_small_no_occasion` | pt | R SMALL | R 72.50 | R Sunflower, Carnation | R Peony |
| v2 / `pt_v2_irrelevant_colors` | pt | A | A | A | A |
| v2 / `pt_v2_size_unsure` | pt | M | A | A | A |
| v2 / `en_v2_birthday_modern` | en | R MEDIUM | R 175 | R Gerbera | R Daisy |
| v2 / `en_v2_wedding_minimalist` | en | R LARGE | A | R Hydrangea | R Carnation |
| v2 / `en_v2_valentines_classic` | en | R SMALL | R 110 | R Tulip, Baby's Breath | A |
| v2 / `en_v2_thanks_two_styles` | en | R MEDIUM | A | R Lily | R Rose, Peony |
| v2 / `en_v2_mothers_day_colorful` | en | R LARGE | A | R Hydrangea | A |
| v2 / `en_v2_low_budget_not_size` | en | A | R 35 | A | A |
| v2 / `en_v2_ambiguous_size` | en | M | A | A | A |
| v2 / `en_v2_no_specific_shade` | en | A | A | A | A |
| v2 / `en_v2_preference_and_exclusion` | en | A | A | R Sunflower, Daisy | R Lily, Carnation |
| v2 / `en_v2_unsupported_mixed` | en | R SMALL | A | R Tulip | R Rose |
| v2 / `en_v2_unsupported_occasion` | en | R MEDIUM | A | R Peony | A |
| v2 / `en_v2_missing_style` | en | R SMALL | R 95 | R Carnation | A |
| v2 / `en_v2_irrelevant_numbers` | en | A | A | R Rose | A |
| v2 / `en_v2_occasion_no_defaults` | en | M | A | M | A |
| v2 / `en_v2_missing_colors` | en | R MEDIUM | A | R Sunflower | R Hydrangea |

## Evidência de exclusão: exemplos para revisão

- `pt_valentines_exclusion`: **Não use lírios**, não somente “lírios”.
- `pt_v2_exclusions_only`: **Não coloque hortênsias nem tulipas no buquê**, compartilhado pelos dois nomes canônicos.
- `en_v2_thanks_two_styles`: **Leave out roses and peonies**, compartilhado por Rose e Peony.
- `en_v2_preference_and_exclusion`: **Please use sunflowers and daisies** para inclusão; **avoid lilies and carnations** para exclusão, mantendo as polaridades separadas.
- `en_v2_unsupported_mixed`: **no dahlias or roses**, não “roses” isolado.

## Validação e próximos passos

Validação técnica: os dois hashes, todos os IDs, os idiomas, os estados e a cobertura de valores esperados passaram no loader existente usando cópias temporárias de validação. Todos os 92 spans foram conferidos por igualdade exata com a query de origem. Os artefatos originais continuam recusados pelo loader por falta de aprovação. Testes dedicados impedem chamada ao extrator durante essas verificações.

**Antes da avaliação:** revisar D1–D5, aprovar ou corrigir os estados/spans nos sidecars e somente então marcar os casos aprovados como `reviewed: true`. Não aprovar em massa sem resolver D2/D3/D4. Nada foi modificado nos datasets, prompts, produção, runner ou benchmarks anteriores. Nenhuma métrica de precisão, recall ou qualidade do Query Extractor foi calculada.

Checks desta entrega: `ruff check evaluation` aprovado; **20 testes de anotações/avaliador aprovados**, incluindo as verificações dos sidecars reais sem extração e os testes do avaliador em fixtures sintéticas. `git diff --check` aprovado. Integridade dos arquivos protegidos confirmada por SHA-256.
