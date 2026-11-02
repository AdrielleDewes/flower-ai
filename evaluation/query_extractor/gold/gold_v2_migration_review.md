# Migração gold para contrato de anotações v2

Implementado em 2026-11-02. **Propostas não aprovadas**: todos os 46 casos permanecem `reviewed: false`. Este documento descreve migração e validação de dados, não resultados de extração. Nenhum benchmark dos 46 casos foi executado.

## Artefatos e contagens

| Dataset | Novo sidecar | Casos | RESOLVED | ABSENT | PARTIAL | AMBIGUOUS | CONFLICT | Valores resolvidos | Menções pendentes |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| v1 | [gold_v2](bouquet_requests_v1_gold_v2.json) | 16 | 24 | 40 | 0 | 0 | 0 | 25 | 0 |
| v2 | [gold_v2](bouquet_requests_v2_gold_v2.json) | 30 | 51 | 60 | 3 | 6 | 0 | 61 | 9 |

Total: **184 campos: 75 RESOLVED, 100 ABSENT, 3 PARTIAL, 6 AMBIGUOUS, 0 CONFLICT**. São **86 valores canônicos resolvidos** e **9 menções pendentes**: 4 OUT_OF_CATALOG e 5 UNDECIDED. Há 95 spans de suporte (86 dos valores e 9 das menções), além dos 9 spans que localizam as menções; todos são substrings exatas do texto original.

## Decisões de migração

| Caso | Campo | Estado v2 | Resolvido | Menção pendente | Motivo |
|---|---|---|---|---|---|
| `pt_v2_unsupported_flower` | preferred_flowers | PARTIAL | Rose | orquídeas | OUT_OF_CATALOG |
| `pt_v2_unsupported_flower` | excluded_flowers | AMBIGUOUS | — | antúrios | OUT_OF_CATALOG |
| `en_v2_unsupported_mixed` | preferred_flowers | PARTIAL | Tulip | orchids | OUT_OF_CATALOG |
| `en_v2_unsupported_mixed` | excluded_flowers | PARTIAL | Rose | dahlias | OUT_OF_CATALOG |
| `pt_v2_ambiguous_impact` | size | AMBIGUOUS | — | ainda não escolhi cores nem tamanho | UNDECIDED |
| `pt_v2_size_unsure` | size | AMBIGUOUS | — | pequeno ou grande; candidatos SMALL/LARGE | UNDECIDED |
| `en_v2_ambiguous_size` | size | AMBIGUOUS | — | I have not decided on a size | UNDECIDED |
| `en_v2_occasion_no_defaults` | size | AMBIGUOUS | — | with no particular flower, color, style or size chosen | UNDECIDED |
| `en_v2_occasion_no_defaults` | preferred_flowers | AMBIGUOUS | — | with no particular flower, color, style or size chosen | UNDECIDED |

As demais 175 anotações não têm pendências. Todos os valores resolvidos são os valores originais, em ordem, com o contexto original preservado. Nenhum valor canônico foi criado para as espécies indisponíveis. As duas evidências de alternativas SMALL/LARGE do v1 viraram uma menção pendente com dois candidatos; não viraram valores confirmados ou conflito. A espécie em `pt_v2_budget_not_size` continua ABSENT, pois rosa é cor.

A função de migração exige os nove diagnósticos explícitos acima. Não lê saídas do extrator, não infere estados a partir de null e não resolve ambiguidades. Source sidecars e datasets não são escritos; os novos arquivos foram criados com proteção contra sobrescrita.

## Contrato, validação e compatibilidade

- `annotation_version: 2`; campos com state, resolved_values e unresolved_mentions, conforme a documentação do experimento. PARTIAL existe no contrato de anotação, sem alterar o enum/regras do extrator legado.
- O loader v2 valida grafia, catálogo e ordem dos valores, tipos, spans, contenção de menção no suporte, motivos, candidatos, duplicações e invariantes dos estados. O loader v1 continua disponível sem reinterpretar suas anotações.
- O formato anterior era insuficiente para os três campos mistos; o v2 preserva agora a parte canônica e a pendência separadamente, inclusive a intenção de exclusão fora do catálogo.
- O loader ainda exige reviewed:true para avaliação. A validação técnica usa cópias temporárias com essa flag, sem alterar ou aprovar os arquivos salvos e com extração explicitamente bloqueada nos testes.
- Avaliação com sidecar v2 produz evaluation_version:2 e métricas distintas para valores, pendências e completude. O caminho v1 não recebe as novas definições. O atual extrator não emite menções estruturadas: o avaliador não as fabrica a partir do gold; registra a limitação e conta as omissões como FN.

## Integridade dos arquivos preservados

| Dataset | SHA-256 dataset | SHA-256 gold_v1 preservado |
|---|---|---|
| v1 | `db3e1245ab374ac726b3591bed665a49c662395ce94e46fe9a8b1105a277df6d` | `c5b324569da19f8ca0ee18ac27df66296e2a03105332adce7845c03918dbd840` |
| v2 | `f96fe878f3ada60a353db035d16a7d768c1d13053635a42f520159b7528bc143` | `c749d786df948284b3211f03f72040bfb7524366829f0e9e61f9262400307c06` |

## Questões semânticas e limites restantes

As decisões de revisão fornecidas foram mantidas; não foi identificado um novo conflito semântico nos 46 casos. Os arquivos ainda exigem aprovação manual final dos spans/diagnósticos. O motivo OUT_OF_CATALOG é contextual e precisa de revisão: validação estrutural não prova que um sinônimo não corresponde a uma espécie do catálogo. Não há diagnósticos gold de CONFLICTING_INFORMATION nestes datasets, embora o contrato e os testes sintéticos suportem o motivo.

Persistem os limites de escopo já documentados: não há pontuação para ocasião/estilo/cor, nem representação separada de teto monetário estrito em under. Nenhuma melhoria de precisão, recall, completude ou desempenho foi medida nesta entrega.

## Checks finais

- Ruff aprovado em backend e evaluation.
- pytest: **229 testes do backend e 162 da avaliação aprovados**.
- Validação estrutural dos 46 casos feita em cópias temporárias, com QueryExtractor.extract bloqueado nos testes de gold.
- Compatibilidade v1, estados v2, métricas separadas, ordem de listas, Decimal, migração e proteção de revisão cobertos por testes.
- git diff --check aprovado; SHA-256 confirmou preservação de 61 arquivos protegidos (produção, datasets, artefatos, gold_v1 e regras).
- Nenhum benchmark ou aprovação automática executado.
