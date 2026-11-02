# POC de interpretação de pedidos

O fluxo tem duas requisições independentes: interpretar texto e solicitar uma
recomendação com as preferências confirmadas pelo usuário. Não há frontend,
persistência de drafts, sessão de conversa ou salvamento automático de buquês.

## Configuração opcional do LLM

Somente o endpoint de interpretação precisa do Ollama. O provider é criado por
requisição, sem conexão ou validação de configuração durante o startup. Da pasta
`backend/`, um exemplo de configuração para uso local futuro é:

```bash
OLLAMA_MODEL=qwen3:1.7b OLLAMA_BASE_URL=http://localhost:11434 OLLAMA_THINK=false \
  .venv/bin/uvicorn app.main:app --reload
```

O modelo deve estar instalado no servidor Ollama. O endpoint exige a tag
`qwen3:1.7b`, envia `think:false`, temperatura 0 e JSON Schema restrito ao catálogo.
`OLLAMA_THINK` vazio também é enviado explicitamente como false neste endpoint;
true ou outra tag retornam 503. Base URL e timeout vêm de `OllamaConfig`;
`OLLAMA_TIMEOUT_SECONDS` tem padrão 60. O código lê variáveis de ambiente e não
carrega `.env` automaticamente.

O schema continua em `format` e no sufixo do prompt. Não há segunda chamada para
reparar saída, retry de inferência ou fallback automático. Provider e métricas
mutáveis não são compartilhados entre requisições.

## 1. Interpretar

`POST /florists/{florist_id}/interpretations`

```json
{
  "text": "Quero um buquê pequeno, moderno e vermelho, para aniversário, com rosas, até R$100. Sem lírios."
}
```

A entrada aceita apenas `text`, não vazio. O trim nas extremidades reutiliza o
contrato de entrada existente. Model, thinking e demais parâmetros são controlados
no servidor; propriedades extras são rejeitadas.

O serviço valida a florista, lê seu catálogo ativo, executa o Query Extractor v1 e
uma única interpretação Qwen com o mesmo texto e snapshot, e chama o merger.
O catálogo de interpretação não filtra por estoque: disponibilidade e preços
continuam sendo responsabilidade da recomendação.

| Campo da resposta 200 | Significado |
|---|---|
| `text` | Texto normalizado efetivamente usado pelas duas fontes. |
| `interpretation` | `BouquetInterpretation` canônica, sem defaults inventados. |
| `readiness` | Completude existente: status e campos obrigatórios faltantes. |
| `field_sources` | Valores do LLM e do extrator, relação entre as fontes e evidência. |
| `issues` | Questões pendentes, com código, campo, mensagem e campos relacionados. |
| `requires_review` | true quando há questão pendente ou campo obrigatório faltante. |
| `options` | Nomes canônicos de ocasiões, estilos, cores e flores para um formulário. |
| `recommendation_request` | Rascunho `BouquetRequest` somente se completo e sem questões pendentes; caso contrário, null. |

`requires_review:false` significa **nenhuma questão detectada**, não comprovação
de entendimento perfeito. O frontend ainda deve pedir confirmação explícita de
preferências em todos os casos. `readiness:READY` pode coexistir com questões em
campos opcionais e `requires_review:true`; nesse caso não há recommendation_request.

Valores monetários são serializados como strings decimais. Ausência de informação
continua null em interpretation. Na conversão já existente para BouquetRequest,
listas opcionais desconhecidas recebem o default sem filtro; isso não prova que
o cliente declarou ausência de preferência. O formulário deve permitir conferir
todos os campos antes de enviar o pedido final.

## Merger determinístico

Somente campos RESOLVED do extrator fornecem valores. AMBIGUOUS e CONFLICT fornecem
contexto para esclarecimento, nunca candidatos confirmados. ABSENT significa que
o extrator não identificou informação, não que ela inexiste.

| Situação | Draft e relação | Atenção pendente |
|---|---|---|
| Valores iguais, inclusive ordem | Mantém; AGREEMENT | Não |
| Uma fonte identifica valor e a outra não identifica | Mantém valor disponível; COMPLEMENTARY | Não, salvo outro problema |
| Extrator incerto/conflitante | Campo null; UNRESOLVED/CONTRADICTION | EXTRACTOR_UNCERTAIN/EXTRACTOR_CONFLICT |
| SMALL versus LARGE resolvidos | Campo null; CONTRADICTION | SCALAR_CONTRADICTION |
| Limites monetários distintos | Campo null; DIVERGENCE; não escolhe o menor | BUDGET_DIVERGENCE |
| Lista do LLM é subconjunto da lista explícita, com ordem comum compatível | Usa lista do extrator; COMPLEMENTARY | Não: adições têm evidência resolvida |
| Lista explícita é subconjunto da lista LLM | Mantém somente os valores explícitos; COMPLEMENTARY | UNCONFIRMED_LLM_VALUES para revisar adições LLM |
| Sobreposição parcial ou listas disjuntas | Mantém só interseção em ordem explícita, ou null; DIVERGENCE | LIST_DIVERGENCE |
| Ordem relativa dos itens comuns difere | Campo null; DIVERGENCE | LIST_ORDER_DIVERGENCE |
| Mesma espécie preferida e excluída em qualquer fonte confirmada | Ambos os campos null; CONTRADICTION | PREFERENCE_EXCLUSION_CONFLICT |

Diferenças de listas não são automaticamente contradições: duas espécies podem
ser complementares. Adições não corroboradas do LLM não são confirmadas
silenciosamente. Todos os valores originais das fontes são preservados em
`field_sources`, mesmo quando o draft retém apenas um subconjunto ou null.

As evidências são `{start, end, text}`, com índices Python no `text` retornado e
fim exclusivo. Contextos incertos podem aparecer como evidência, mas extractor_value
fica null nesses casos. Não são expostos candidatos não resolvidos, rule IDs,
contratos de gold, PARTIAL ou métricas/artefatos de avaliação. Não há scores de
confiança ou pesos heurísticos.

## 2. Confirmar/corrigir e recomendar

`POST /florists/{florist_id}/recommendations` mantém o contrato `BouquetRequest`
e a resposta `Recommendation` existentes. O cliente pode editar o draft ou montar
o pedido manualmente; não precisa reenviar texto, model, draft ID ou flags de fonte.

Exemplo de escolhas finais (confirmadas pelo usuário):

```json
{
  "occasion": "Birthday",
  "styles": ["Modern"],
  "colors": ["Red"],
  "size": "SMALL",
  "budget_max": "100.00",
  "preferred_flowers": ["Rose"],
  "excluded_flowers": ["Lily"]
}
```

Antes de chamar o motor existente, o servidor reconsulta o catálogo ativo e
valida a categoria/grafia dos nomes, orçamento máximo finito e positivo e ausência
de inclusão/exclusão simultânea da mesma espécie. Valores inválidos que antes
poderiam ser ignorados agora retornam 422. O schema canônico não mudou; listas
vazias explícitas mantêm a semântica anterior do pedido estruturado. O POC
interpreta somente budget_max; não adiciona suporte novo a orçamento mínimo.

Preços, estoque, composição e fallback continuam no algoritmo determinístico,
sem alteração. Mudanças de catálogo ou estoque depois da interpretação podem
produzir 422 na solicitação final. Interpretar/recomendar não reserva ou consome
estoque, nem grava Bouquet. Se o usuário quiser salvar depois, segue o POST de
buquês já existente, com sua validação e transação próprias.

O pedido estruturado/manual não depende de Ollama ou configuração do LLM. Isso
mantém a arquitetura pronta para um futuro formulário manual quando interpretação
estiver indisponível. Não há fallback que envie automaticamente um pedido parcial
ao motor, nem implementação de frontend nesta entrega.

## Falhas

| Código | Situação |
|---|---|
| 404 | Florista não encontrada pela dependência compartilhada. |
| 422 | Payload inválido, preferências finais inválidas ou nenhuma composição viável. |
| 502 | Saída do provider inválida, fora do catálogo ou com valor inválido para o draft. |
| 503 | LLM/configuração indisponível, timeout ou falha na leitura do catálogo durante interpretação. |

Texto incompleto, divergência ou contradição representável retorna 200 com draft
para revisão, não uma recomendação falsa. Falhas do provider não devolvem uma
interpretação aparentemente completa baseada só no extrator. As mensagens HTTP
são sanitizadas; logs não incluem query, resposta bruta, credenciais ou raciocínio.

## Reuso, limites e verificação

O núcleo puro foi movido para `app/services/query_extractor`, com reexports na
avaliação para compartilhar as mesmas classes. A AST dos quatro módulos foi
conferida contra a versão avaliada; somente comentários de compatibilidade de
lint foram acrescentados, sem alterar as regras. O núcleo não importa schemas
canônicos, providers ou artefatos gold. Para comandos de avaliação na raiz, use
`PYTHONPATH=backend`.

Completude não implica fidelidade textual nem viabilidade. O extrator continua
com os limites de negação, elipse e cobertura conhecidos; não reconhece todas as
menções fora do catálogo. Structured output restringe nomes, mas não impede que
o LLM escolha valores válidos não solicitados. O merger não garante detectar
omissões compartilhadas pelas fontes. Isso reforça a confirmação pelo usuário.

Os testes usam providers/HTTP simulados e banco de teste. Incluem um fluxo real
até o motor determinístico, divergência, correção manual, revalidação de catálogo,
ausência de persistência e independência do LLM no pedido manual. Nenhuma
inferência real ou novo benchmark de modelo foi executado para esta integração.
