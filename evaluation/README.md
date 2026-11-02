# Avaliação de modelos

Esta pasta reúne os experimentos de interpretação de pedidos, separados da
aplicação em `backend/`.

- `bouquet_interpreter.py`: executor e cálculo de métricas.
- `data/`: datasets versionados com catálogo fixo e respostas esperadas.
- `results/`: relatórios das execuções dos modelos.
- `tests/`: testes determinísticos das métricas, sem chamadas ao Ollama ou banco.

A avaliação reutiliza os schemas, o interpretador e o provider do backend para
medir o comportamento da implementação real. O backend não depende desta pasta.
O script `backend/scripts/interpret_bouquet.py` continua sendo uma ferramenta
para interpretar um pedido com o catálogo real de uma florista.

## Executar uma avaliação

Use o ambiente Python e as dependências de `backend/requirements-dev.txt`.
Com o Ollama em execução e o modelo instalado, execute da raiz do repositório:

```bash
PYTHONPATH=backend backend/.venv/bin/python -m evaluation.bouquet_interpreter \
  --model gemma3:1b \
  --output evaluation/results/gemma3-1b_bouquet_requests_v1.json
```

Para comparar sem thinking, acrescente `--no-think` quando o modelo suportar
essa opção. Use `--think` para ativá-la explicitamente. A execução usa o catálogo
do dataset e não acessa o banco. O código de saída é `1` quando algum caso falha;
o relatório ainda é gravado para inspeção.

Os JSONs existentes são registros de execuções anteriores, preservados sem
alteração. Caminhos de dataset registrados neles podem refletir a estrutura antiga.

## Prompt & Pipeline Optimization v1

O dataset `data/bouquet_requests_v2.json` contém 30 pedidos novos (15 em português
e 15 em inglês), com o mesmo catálogo do v1. Estrutura, cobertura e critérios de
anotação estão em [`data/README.md`](data/README.md).

O runner mantém v1 como padrão. Para uma execução futura, selecione v2 com
`--dataset-version 2`, ou informe `--dataset evaluation/data/bouquet_requests_v2.json`.
Essas opções são mutuamente exclusivas. A seleção não altera o modelo, provider,
prompt, grounding ou métricas. Use um novo nome de saída para cada benchmark.

No v2, cada caso declara `expected_status`, validado contra a interpretação
esperada. O v1 continua compatível sem esse campo: seu status é calculado como
antes. A preparação do v2 foi validada com interpretadores falsos nos testes;
nenhum benchmark de modelo foi executado nesta etapa.

## Catálogo restrito na geração (experimental, opt-in)

O runner aceita `--catalog-constrained-output`, desativado por padrão. A opção
constrói um JSON Schema de inferência com enums para ocasião, estilos, cores,
flores preferidas e excluídas. Cada array restringe seus itens à categoria correta;
todos os campos continuam opcionais e aceitam `null`. Categorias vazias permitem
somente `null` quando presentes. Arrays vazios nas categorias não vazias continuam
sendo normalizados para `None` pelo contrato atual. Não há alteração em tamanho,
orçamento, campos obrigatórios ou comparação da ordem das listas.

O schema usa o mesmo snapshot de catálogo do prompt e da validação posterior,
construído uma vez por interpretador, sem cache compartilhado entre floristas.
Ele não modifica o schema Pydantic canônico. O provider recebe a restrição pelo
argumento opcional `json_schema`; o argumento `schema` continua sendo o modelo
Pydantic usado para validar a resposta. Providers alternativos precisam suportar
esse argumento para participar do experimento. Restrições não são descartadas
silenciosamente: falhas não acionam retry ou fallback irrestrito.

O mesmo schema dinâmico é enviado em `format` e no sufixo de schema já incluído
no prompt. O template textual permanece igual. Isso pode aumentar os tokens de
entrada, especialmente com catálogos maiores. O runner mantém `prompt_eval_count`
por caso e agrega contagens e durações de inferência, inclusive em respostas
rejeitadas quando o Ollama fornece as métricas. Dados ausentes continuam `null`;
os tokens não são estimados pelo tamanho do texto.

Os novos relatórios registram `configuration.catalog_constrained_output` e
`configuration.catalog_constraint_version` (`1` quando ativado, `null` no baseline).
Sem a flag, o payload e a chamada ao provider permanecem no modo anterior; somente
esses metadados adicionais aparecem nos relatórios novos. A aplicação continua
com o modo desativado por padrão.

Exemplo **para execução futura após revisão**, não executado nesta implementação:

```bash
PYTHONPATH=backend backend/.venv/bin/python -m evaluation.bouquet_interpreter \
  --dataset-version 2 --model qwen3:1.7b --no-think \
  --catalog-constrained-output \
  --output evaluation/results/qwen3-1.7b-no-think_bouquet_requests_v2_catalog-v1_run1.json
```

Structured output restringe valores, não comprova evidência no pedido: o modelo
ainda pode inventar preferências válidas, omitir informações ou selecionar tamanho
indevido. A validação de catálogo posterior é mantida. A compatibilidade dos enums,
arrays e null com a versão local do Ollama ainda precisa de verificação real;
os testes atuais usam HTTP simulado, sem inferência.

Na avaliação futura, registrar versão do Ollama e comparar baseline e modo restrito
em v1/v2 congelados, com `think:false`, mesmo modelo, timeout e temperatura. Fazer
duas execuções por modo/dataset, alternando a ordem e padronizando o aquecimento,
com novos nomes de artefato. Analisar exact match, rejeições, métricas por idioma,
status, tokens e latência. Revisar os casos recuperados e comparar omissões/invenções
também nos casos aceitos por ambos os modos, pois o denominador da hallucination
rate muda com o número de respostas aceitas. Recomendar ativação apenas com menos
rejeições, maior exact match, sem regressão de status ou omissões/invenções na
população comum e aumento de latência média de no máximo 10%. Nenhum ganho de
qualidade ou latência foi medido nesta implementação.

## Verificar as ferramentas de avaliação

Da raiz do repositório:

```bash
backend/.venv/bin/ruff check evaluation
backend/.venv/bin/pytest -c evaluation/pytest.ini evaluation/tests
```

Esses testes são executados separadamente dos testes da aplicação no CI.
