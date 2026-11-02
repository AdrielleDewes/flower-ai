# Datasets de interpretação

`bouquet_requests_v1.json` é o baseline original de 16 pedidos e permanece
inalterado. `bouquet_requests_v2.json` é o conjunto novo para Prompt & Pipeline
Optimization v1, com 30 pedidos distintos do baseline. O número do dataset
identifica o conjunto de exemplos, não uma versão do prompt ou do provider.

## Estrutura do v2

- `version`: `2`.
- `catalog`: cópia exata das opções canônicas do v1.
- `cases`: 30 objetos com `id`, `input`, `expected` e `expected_status`.
- `expected`: todos os sete campos de `BouquetInterpretation`, com `null` explícito
  quando não há informação identificável; orçamentos decimais são strings JSON.
- `expected_status`: `READY` ou `NEEDS_CLARIFICATION`.

São 15 pedidos em português (`pt_v2_*`) e 15 em inglês (`en_v2_*`), com 10 casos
READY e 20 NEEDS_CLARIFICATION. Há 15 tamanhos explícitos e 15 tamanhos ausentes
ou ambíguos. Os exemplos incluem listas com múltiplos atributos, preferências e
exclusões simultâneas, orçamento ausente, detalhes de entrega e valores fora do
catálogo. Cada idioma tem cinco casos completos.

## Revisão dos rótulos

As respostas esperadas seguem as regras atuais de extração, sem antecipar uma
otimização do pipeline:

- READY exige ocasião, estilo, cor e tamanho conhecidos. Orçamento, preferência
  e exclusão de flores continuam opcionais. A completude não afirma viabilidade
  de estoque, preço ou composição.
- Orçamentos altos/baixos (`pt_v2_budget_not_size`, `en_v2_low_budget_not_size`)
  e quantidade de hastes (`pt_v2_stem_count_not_size`) não determinam tamanho.
- `pt_v2_size_unsure` apresenta duas opções sem escolha; `en_v2_ambiguous_size`
  usa tamanho indefinido. Ambos têm `size: null`.
- “Marcante”, “lovely”, “cheerful” e “bright colors” não identificam por si só
  um estilo canônico ou uma cor específica. Nenhuma preferência é completada.
- Em `pt_v2_pink_is_color`, “tons de rosa” significa a cor Pink, sem preferência
  pela flor Rose. Mosquitinho corresponde a Baby's Breath; os demais nomes em
  português e plurais são mapeados aos nomes canônicos em inglês.
- Orquídeas, antúrios, orchids e dahlias não têm correspondência no catálogo.
  Somente flores suportadas da mesma frase são mantidas; exclusões sem nenhuma
  correspondência ficam `null`, não uma lista vazia.
- Inauguração/retirement não são ocasiões do catálogo; gótico/bohemian não são
  estilos; preto/teal não são cores. Esses valores não são substituídos por uma
  opção aproximada. Valores suportados da mesma frase continuam presentes.
- Cores da portaria, números de apartamento e horários não são atributos do
  buquê ou orçamento. Ocasião e espécies não implicam cores nem estilos.
- Listas preservam a ordem da menção no pedido, pois o exact match atual é
  sensível à ordem. Ausência e preferência ainda não decidida são `null`.

O loader verifica presença dos sete campos, tipos, valores canônicos, IDs e
pedidos únicos e consistência do status esperado. Os testes verificam também
ausência de sobreposição com v1, paridade do catálogo, cobertura dos idiomas e
execução dos 30 casos com um interpretador falso. A revisão semântica dos textos
é documentada acima; o loader não tenta interpretar linguagem natural.

## Preservação das métricas

Exact match, acurácia por campo, readiness, erros, latência e métricas Ollama
continuam com os mesmos cálculos. A taxa de valores inventados considera apenas
campos esperados como `null` nos outputs aceitos. Falhas de validação continuam
no denominador de exact match e acurácia por campo/status, e são registradas por
caso. Relatórios v1 e v2 devem ser comparados como conjuntos diferentes.
