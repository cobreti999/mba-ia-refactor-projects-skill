# Relatório de auditoria — formato e revisão

## Regras de preenchimento

Apresente o relatório na sessão ativa antes de qualquer escrita; no CLI, use o console. Preencha todos os campos aplicáveis; use “não verificado” ou “não aplicável” com motivo, sem inventar resultados. O relatório cobre a revisão e as alterações locais observadas, não apenas o commit base.

Use IDs únicos `F-001`, `F-002` etc. Ordene CRITICAL → HIGH → MEDIUM → LOW; dentro da severidade, priorize impacto e use caminho/linha como desempate. Preserve IDs ao revisar o mesmo relatório. Conte findings distintos, não linhas, ocorrências ou itens do catálogo. Os totais devem coincidir com as seções detalhadas; candidatos pendentes não entram na soma.

Cada finding exige caminho relativo ao projeto, linha inicial e final exatas, símbolo/fluxo, evidência, impacto contextualizado, justificativa da severidade, recomendação e verificação futura. Um intervalo deve conter a evidência, não um arquivo inteiro por conveniência. Achados arquiteturais podem exigir vários intervalos curtos de responsabilidades diferentes.

Para AP-13, acrescente símbolo, pacote, versão aplicável e origem dessa versão, status oficial, versão de depreciação/remoção quando documentada, equivalente recomendado, diferenças de comportamento e link oficial com data de consulta. Se a versão não estiver estabelecida, informe a condição como pendência, sem chamar o achado de confirmado.

Se houver menos de cinco findings confirmados, revise áreas não cobertas; se o resultado permanecer, informe o número real e o critério não atendido. Não fabrique ou divida achados para cumprir uma meta. Compare com uma análise manual fornecida somente depois da inspeção independente e explicite correspondências e divergências.

## Template

```markdown
# Relatório de Auditoria Arquitetural

## Contexto e escopo
- Projeto e caminho: ...
- Data da auditoria: ...
- Commit base / alterações locais relevantes: ...
- Stack e versões (declaradas/resolvidas; runtime verificado ou não): ...
- Domínio e arquitetura atual: ...
- Cobertura: ... fontes encontrados / ... fontes lidos; testes e suporte: ...
- Exclusões e limitações: ...
- Método: inspeção estática; aplicação, banco e endpoints não executados.
- Destino proposto, se solicitado: ... (ainda não salvo)

## Resumo
| Severidade | Findings confirmados |
|---|---:|
| CRITICAL | ... |
| HIGH | ... |
| MEDIUM | ... |
| LOW | ... |
| Total | ... |

Critérios do desafio: mínimo de 5 findings e ao menos 1 CRITICAL/HIGH — atendidos/não atendidos, com totais reais.

## Findings

### F-001 — [SEVERIDADE] Título concreto
- Padrão: AP-... / padrão adicional descrito.
- Localização principal: `caminho:linha-inicial–linha-final`.
- Outras evidências: ... (origem da entrada, chamada, configuração ou consumidor).
- Símbolo/fluxo: ...
- Evidência: ... (trecho mínimo ou descrição precisa; valores sensíveis omitidos).
- Problema: ...
- Impacto e condições: ...
- Justificativa da severidade: ...
- Recomendação: ...
- Contratos/dados afetados: ...
- Validação futura: ... (cenário e resultado esperado; não executada).
- Documentação de depreciação, se aplicável: símbolo/pacote, versão e origem, status, equivalente, compatibilidade, URL e data.

Repetir o bloco para cada finding confirmado; remover esta instrução da saída.

## Cobertura do catálogo e pendências
| Padrão | Estado | Evidência / justificativa / pendência |
|---|---|---|
| AP-... | encontrado / não encontrado no escopo / não aplicável / não verificado | ... |

APIs deprecated: confirmadas / não identificadas no escopo / verificação inconclusiva, com motivo. Distinguir uso confirmado da chamada e aplicabilidade da depreciação.
Candidatos sem evidência suficiente: ... (fora dos totais).

## Comparação com análise manual (se fornecida)
| ID manual | Finding correspondente | Correspondência ou divergência fundamentada |
|---|---|---|

## Proposta para a Fase 3
| Findings | Mudança proposta e responsabilidades MVC | Contratos/dados afetados | Verificação futura |
|---|---|---|---|

Prioridade e dependências: ...
Decisões necessárias: ... (especialmente autenticação, remoção de campos e migração de dados).
Esta proposta não representa execução nem aprovação.

## Checklist da auditoria
- [ ] Escopo, revisão e cobertura registrados.
- [ ] Evidências conferidas em arquivo e linhas da versão analisada.
- [ ] Findings ordenados, sem duplicidade, com totais reconciliados.
- [ ] Severidades justificadas e recomendações específicas.
- [ ] APIs obsoletas verificadas por versão ou pendências declaradas.
- [ ] Contratos, dados e verificações futuras explicitados.
- [ ] Relatório apresentado antes de qualquer escrita.

## Decisão e estado
- Auditoria: concluída no escopo informado / parcial (motivo).
- Escritas realizadas nesta execução: nenhuma.
- Relatório em disco: não salvo.
- Aprovação para salvar relatório: pendente / não solicitada.
- Aprovação para refatorar: pendente; nunca inferida da aprovação da Fase 1.
- Fase 3: disponível; aguardando aprovação explícita da proposta.
```

Marque os itens do checklist apenas após conferi-los. Remova instruções do template da saída; preserve limitações reais. No encerramento, siga a seção de confirmação do `SKILL.md`.

## Salvamento após revisão

Se o usuário solicitar um arquivo, mostre o relatório primeiro e informe o destino exato. Quando o relatório integrar a entrega da Fase 3, o prompt `[y/n]` do `SKILL.md` pode autorizar conjuntamente salvamento e refatoração, desde que isso seja explicitado antes da pergunta. Uma solicitação de somente salvamento não autoriza refatorar. No desafio, os destinos serão `reports/audit-project-1.md`, `reports/audit-project-2.md` e `reports/audit-project-3.md`, relativos à raiz do repositório, conforme o projeto — não relativos à pasta da skill. Em outros projetos, use o destino informado, sem assumir essa numeração.

A confirmação de salvamento autoriza apenas esse artefato. Verifique se já existe e apresente a substituição proposta antes de sobrescrever conteúdo. Após salvar, atualize somente o estado do relatório com a decisão real; não inferir aprovação de refatoração a partir do salvamento; registrar apenas a decisão explícita, se houver. Não criar ou alterar código, configurações ou dados por consequência do salvamento.
