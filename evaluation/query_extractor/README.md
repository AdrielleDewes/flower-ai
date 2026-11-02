# Query Extractor v1 (experimental)

Extrator determinístico, com núcleo puro independente de schemas canônicos e do LLM. Não implementa
`BouquetRequestInterpreter`, não retorna `BouquetInterpretation` e não avalia
estoque, preço, composição ou readiness. Todos os módulos usam apenas a biblioteca
padrão; os testes usam pytest. A API POC usa um adaptador e merger separados; os contratos de avaliação não entram na API.

Em 2026-11-02, os 46 casos gold_v2 foram explicitamente aprovados para avaliação
do POC e marcados `reviewed: true`. A [primeira execução completa](../results/query-extractor-v1_bouquet_requests_v1-v2_gold-v2_run1_report.md)
mantém as regras originais, sem otimizações. Os relatórios de revisão anteriores
registram o estado histórico pré-aprovação; gold_v1 continua não aprovado.

## Uso e contratos

```python
from evaluation.query_extractor import FlowerVocabulary, QueryExtractor

extractor = QueryExtractor(FlowerVocabulary(("Rose", "Lily")))
result = extractor.extract("Quero rosas, sem lírios. Orçamento até R$80.")
print(result.to_dict())
```

`QueryExtraction` contém `size`, `budget_max`, `preferred_flowers` e
`excluded_flowers`, além de `rules_version`. Cada campo contém:

- `state`: `ABSENT`, `RESOLVED`, `AMBIGUOUS` ou `CONFLICT`.
- `values`: valores confirmados, preenchidos **somente** em `RESOLVED`.
- `candidates`: candidatos observados, incluindo os retidos por ambiguidade.
- `reasons`: motivos de abstenção ou conflito.

Os tamanhos são strings próprias do experimento: SMALL/MEDIUM/LARGE. Orçamentos
usam `Decimal` e são serializados como strings. Flores usam a grafia canônica
do catálogo injetado. Listas seguem a primeira menção; repetições são deduplicadas
com todas as evidências preservadas.

Cada valor/candidato tem evidências `{start, end, text, rule_id}`. Os índices são
posições de caracteres Python no texto original, fim exclusivo, não bytes ou
índices UTF-16. O invariante é `query[start:end] == text`. O trecho cobre a oração
com o contexto semântico (por exemplo, **sem lírios**), não apenas o nome da flor.
Apenas existir uma palavra no texto não basta para confirmá-la como preferência.

O catálogo é um snapshot local de nomes, sem banco ou cache global. Nomes
canônicos são reconhecidos diretamente, junto a aliases explícitos em PT/EN das
dez espécies do catálogo de avaliação. Traduções e plurais são uma tabela
versionada, sem fuzzy matching, stemming ou associação por semelhança. Aliases
não introduzem espécies ausentes do catálogo. Colisões ficam ambíguas. Nomes
compostos mais longos prevalecem e o matching usa limites de tokens Unicode.

## Regras incrementais e abstenção

- Tamanhos exigem relação com buquê/tamanho ou seleção isolada inequívoca. Não
  são inferidos de orçamento ou quantidade de hastes. Alternativas ou tamanho
  negado ficam pendentes; tamanhos afirmados distintos geram conflito.
- Orçamento exige contexto monetário ou palavra explícita de orçamento, além de
  construção reconhecida de limite (`até`, `under`, `up to`, `at most`, `no more
  than`, `budget is/of`, `orçamento de/é`). Intervalos monetários explícitos usam
  o limite superior; não se escolhe o menor de limites incompatíveis.
- Aceita numerais positivos, centavos com ponto/vírgula e agrupamentos claros
  como `1.234,50` e `1,234.50`. `1.000` isolado é ambíguo. Não converte moedas,
  não lê números por extenso e não interpreta mínimo como máximo. Moedas
  estrangeiras reconhecidas no contexto de orçamento produzem abstenção.
- Flores exigem construção de pedido, relação explícita `com/with`, exclusão ou
  lista nominal floral. `sem`, `não use/coloque`, `nada de`, `avoid`, `without`,
  `no`, `leave out` e `excluding` têm escopo local, com propagação por listas
  coordenadas e mudança de polaridade por novos cues.
- Escolhas com `ou/or`, incerteza, dupla negação ou escopo não reconhecido não
  confirmam espécies. Preferência ausente declarada não significa exclusão.
- Uma espécie simultaneamente pedida e excluída deixa **ambos os campos inteiros**
  em conflito, inclusive os itens não conflitantes; todos os candidatos continuam
  disponíveis. Não existe regra de última menção/correção vencedora.
- `rosa` singular sem relação floral clara é retida como ambígua; nomes de cor,
  descrições de terceiros e contextos conhecidos de entrega/embalagem não são
  automaticamente preferências. Texto entre aspas duplas/tipográficas é ignorado.

### Limitações conhecidas

Esta versão não é um analisador sintático. A segmentação por oração, os cues e
as exclusões de contexto são deliberadamente pequenos e conservadores. Uma oração
que mistura pedido e entrega, descrição de terceiro ou embalagem pode ser ignorada
por inteiro, causando falsos negativos. Isso não significa que todo contexto
irrelevante possível seja reconhecido: falsos positivos ainda são possíveis em
formulações novas, ironia, discurso indireto ou ambiguidades fora dessas regras.

Não há resolução geral de correferência, elipse entre frases, citações com aspas
simples, flexões arbitrárias, apelidos regionais, moedas diversas, notação
científica, erros de digitação ou precedência de correções. Negação de tamanho não
infere outro tamanho. `under` é projetado para o mesmo valor de teto usado pelos
datasets; o contrato não representa desigualdade estrita separadamente.

Nenhuma evidência automática prova entendimento semântico. As regras explicitam
o contexto que autoriza a extração, mas seus erros devem ser revisados no relatório.
A [API POC](../../docs/poc-interpretation.md) trata divergências explicitamente, sem sobrescrever silenciosamente o LLM.

## Anotações auxiliares v1 (compatibilidade)

O módulo `annotations` lê somente os quatro campos esperados dos JSONs existentes,
sem importar Pydantic ou o runner LLM. Ele gera shells **não revisados**, com idioma
e estados indefinidos; isso não executa extração. Exemplo de preparação futura:

```bash
PYTHONPATH=backend backend/.venv/bin/python -m evaluation.query_extractor \
  --dataset evaluation/data/bouquet_requests_v1.json --prepare-annotations \
  --output /tmp/bouquet_requests_v1_query_extractor_annotations.json
```

Formato de um campo revisado, dentro de `cases[].fields`:

```json
{
  "state": "RESOLVED",
  "evidence": [
    {"value": "Lily", "start": 12, "end": 22, "text": "sem lírios"}
  ]
}
```

Os índices do exemplo são ilustrativos: cada span real precisa ser copiado da
query correspondente e incluir o cue semântico. Todas as espécies esperadas
precisam ter evidência. Os valores esperados permanecem no dataset original, não
são substituídos pelo resultado do extrator ou pelo arquivo auxiliar.

Cada sidecar contém `annotation_version: 1`, SHA-256 dos bytes do dataset e todos
os IDs exatamente uma vez. Cada caso declara `language: pt|en`, `reviewed: true`
e os quatro campos. Campos `ABSENT` têm evidência vazia; campos pendentes exigem
evidência do motivo, podendo usar `value: null`. Casos com valor esperado não
nulo precisam de estado RESOLVED e evidência cobrindo exatamente os valores.
Orçamentos usam strings numéricas nas anotações.

O loader recusa hash divergente, IDs faltantes/repetidos, idioma indefinido,
anotação sem revisão, estados inconsistentes ou spans incorretos. A validação
estrutural não substitui revisão humana do significado. As propostas dos 46 casos
estão em [`gold/`](gold/gold_v1_semantic_review_v2.md), com `reviewed: false` até aprovação
manual. Não foram produzidas a partir das saídas do extrator. O relatório registra
as decisões semânticas aplicadas e as limitações da representação v1.

## Contrato de anotações v2

Os novos sidecars [`gold_v2`](gold/gold_v2_migration_review.md) preservam os 46 casos
e agora têm `reviewed: true`, após aprovação explícita para o POC. Os arquivos
gold_v1 não foram sobrescritos e conservam `reviewed: false`.
`annotation_version` identifica o contrato de anotação; a versão do dataset e a
versão das regras de extração são independentes.

Cada campo v2 contém exatamente `state`, `resolved_values` e `unresolved_mentions`.
Exemplo de exclusão parcialmente resolvida em `en_v2_unsupported_mixed`:

```json
{
  "state": "PARTIAL",
  "resolved_values": [
    {"value": "Rose", "evidence": [
      {"start": 66, "end": 85, "text": "no dahlias or roses"}
    ]}
  ],
  "unresolved_mentions": [
    {
      "reason": "OUT_OF_CATALOG",
      "mention": {"start": 69, "end": 76, "text": "dahlias"},
      "candidates": [],
      "evidence": [{"start": 66, "end": 85, "text": "no dahlias or roses"}]
    }
  ]
}
```

`mention` localiza o item pendente; `evidence` preserva a relação semântica, como
negação ou indecisão. Cada span de suporte precisa conter o span da menção.
Spans de contexto podem ser compartilhados por itens coordenados. `candidates`
contém alternativas canônicas realmente identificadas no texto, sem inventar
nomes para espécies fora do catálogo.

| Estado da anotação | Valores resolvidos | Menções pendentes |
|---|---|---|
| ABSENT | Nenhum | Nenhuma |
| RESOLVED | Pelo menos um | Nenhuma |
| PARTIAL | Pelo menos um | Pelo menos uma; somente campos de flores |
| AMBIGUOUS | Nenhum | Pelo menos uma, sem conflito |
| CONFLICT | Nenhum | Motivo de conflito e múltiplas menções ou candidatos incompatíveis |

Motivos fechados nesta versão: `OUT_OF_CATALOG`, `UNDECIDED` e
`CONFLICTING_INFORMATION`. Uma exclusão inequívoca sem mapeamento usa AMBIGUOUS
com motivo OUT_OF_CATALOG: a pendência é de catálogo, não dúvida do cliente.
Os relatórios distinguem os motivos em vez de tratar toda pendência como indecisão.

A validação exige valores únicos, canônicos e na ordem dos rótulos originais.
Tamanho/orçamento não admitem PARTIAL nem múltiplos valores confirmados. Spans
precisam corresponder exatamente ao texto original. Itens pendentes não podem
duplicar a posição no mesmo campo; OUT_OF_CATALOG não aceita candidatos canônicos.
Um nome canônico literal não pode ser marcado fora do catálogo, mas sinônimos e
plurais ainda precisam de revisão humana: o loader não incorpora regras linguísticas
para provar esse diagnóstico. O hash, a revisão de cada caso e todos os IDs seguem
obrigatórios. Nenhum desses checks aprova automaticamente as anotações.

`annotation_template(..., annotation_version=2)` e a opção de preparação
`--annotation-version 2` geram shells v2. O padrão de preparação permanece v1.
Ao avaliar, o loader detecta a versão do sidecar; uma versão explicitamente pedida
que divergir do arquivo é recusada antes de extrair. `migrate_annotations_v1`
faz a migração estrutural em memória, sem modificar o original ou aprovar casos.
Ele exige decisões explícitas de pendência: não deduz motivos de null ou de saídas
do extrator. A migração aplicada foi revisada e está documentada no relatório gold_v2.

### Avaliação v2: valores versus completude

Somente sidecars v2 ativam `evaluation_version: 2`. O caminho v1 e seus cálculos
permanecem iguais. O avaliador v2 separa, por campo e por idioma:

- **canonical_values:** TP/FP/FN, precisão, recall, F1, falsos positivos e exact
  match ordenado dos valores suportados. Valores confirmados em PARTIAL contam;
  nomes não mapeados não entram no denominador canônico.
- **pending_mentions:** detecção por campo, motivo e posição original. Erro de
  motivo ou span conta FP+FN. As alternativas candidatas são avaliadas pelo exact
  match semântico, não pela métrica de detecção da menção. Há agregação por motivo.
- **canonical_exact_match:** compara os valores dos quatro campos, em ordem,
  independentemente do estado de completude.
- **semantic_exact_match:** exige valores, estados, menções, motivos e conjuntos
  de candidatos corretos, além de spans válidos. Não exige que os limites dos
  contextos de suporte sejam idênticos aos do gold. Como antes, validade estrutural
  e alinhamento de spans não provam fidelidade semântica sem revisão.
- **completeness:** acurácia de estado, campos com valores, cobertura de tentativa
  dos campos com valores esperados, estados esperados/obtidos e campos declarados
  completos. PARTIAL não é completo. `claimed_complete_fields` é uma afirmação da
  saída, não sucesso; `correctly_complete_fields` exige acerto semântico completo.

O núcleo `QueryExtractor` **não foi alterado** para produzir PARTIAL ou reconhecer
menções fora do catálogo. O avaliador aceita opcionalmente `AnnotationPrediction`
como interface de saída v2, mas o extrator atual mantém seu contrato legado.
Para saídas legadas, conserva valores/estados e os candidatos originais para
inspeção, sem inventar diagnósticos nem preencher dados a partir do gold. Menções
pendentes não emitidas contam FN; `pending_mentions_supported: false` e
`legacy_prediction_cases` explicitam essa limitação. Não se deve interpretar
essa pontuação como uma alteração ou melhoria das regras.

Os alvos continuam experimentais, sem gate de implementação. Nenhum benchmark
foi executado durante a implementação do contrato v2; a execução posterior à
aprovação está registrada no relatório do POC acima.

## Avaliação standalone v1 (preparada, não executada nos 46 casos)

Com sidecar revisado e autorização para avaliar, executar separadamente cada
dataset, usando novos nomes de saída:

```bash
PYTHONPATH=backend backend/.venv/bin/python -m evaluation.query_extractor \
  --dataset evaluation/data/bouquet_requests_v2.json \
  --annotations /tmp/bouquet_requests_v2_query_extractor_annotations.json \
  --output /tmp/query_extractor_v1_dataset_v2_run1.json
```

O CLI recusa sobrescrever qualquer arquivo. Sem anotações revisadas não inicia
extração. A preparação e a avaliação são modos mutuamente exclusivos.

O relatório identifica dataset, hashes das anotações/dataset e versão das regras,
e separa os resultados globais, PT e EN, com métricas por campo:

- TP/FP/FN por valor; uma substituição conta como FP e FN. Flores são conjuntos
  por campo para precisão/recall/F1; tamanho e orçamento são valores escalares.
- Abstenção não é descartada: valor esperado não extraído conta como FN. Quando
  não há predições, precisão é `null`; quando não há positivos, recall é `null`.
- Falsos positivos em campos esperados vazios, com denominador explícito de
  casos negativos por campo. O agregado usa pares caso/campo, não queries.
- Exact match de cada campo compara valores **em ordem** e estado anotado; exact
  match do caso exige os quatro campos. AMBIGUOUS correto pode corresponder a um
  rótulo AMBIGUOUS, mas não é convertido em ABSENT para ganhar acerto.
- Contagens de RESOLVED/ABSENT/AMBIGUOUS/CONFLICT e acurácia de estado permitem
  calcular cobertura e identificar abstenções. O agregado `micro_values.cases`
  usa pares caso/campo (4 por query); `groups.*.cases` usa queries.
- Integridade dos spans confirmados e alinhamento com evidência gold do mesmo
  campo/valor. Alinhamento significa conter o span revisado, **não** uma prova
  automática de fidelidade semântica; inspeção continua necessária.
- Tempo de construção do vocabulário separado do tempo médio/total de extração.

Os alvos de 95% de precisão e 80% de recall são registrados como **metas
experimentais, não gates de implementação nem critérios de saída do CLI**. Os
resultados atuais estão no relatório gold_v2 citado acima. Os datasets já conhecidos
não são holdout; avaliações futuras de generalização precisam de textos novos.

Para inspecionar os 46 casos, avaliar v1/v2 separadamente e somar TP/FP/FN por
campo/idioma antes de calcular médias micro; não tirar média simples de percentuais
com denominadores diferentes. Nenhum relatório deste extrator afirma melhora no
LLM, readiness ou recomendação: a integração POC está documentada separadamente e não recebeu novos benchmarks de modelo.

## Testes

```bash
backend/.venv/bin/ruff check evaluation
backend/.venv/bin/pytest -c evaluation/pytest.ini evaluation/tests
```

O núcleo está em `backend/app/services/query_extractor`; os antigos módulos nesta
pasta são reexports, sem duplicação das regras. Use `PYTHONPATH=backend` para os
comandos da raiz.

Os testes do extrator usam queries sintéticas focadas; os do avaliador usam um
dataset temporário de três casos. Não executam o benchmark dos datasets reais,
não chamam modelos e não acessam banco.
