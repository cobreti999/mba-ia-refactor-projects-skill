# Validação da refatoração

## 1. Estabelecer a base e o ambiente

Antes de editar, confirme aprovação, alvo e versão do relatório. Preserve as alterações locais existentes. Prepare uma cópia isolada ou mecanismo equivalente para caracterizar o comportamento original com dados sintéticos. Não executar seed/reset contra banco do usuário. Se o original não iniciar, registre comando/erro e use código, contratos documentados e testes disponíveis como base; não invente um baseline bem-sucedido.

Use ambiente virtual/dependências locais ao projeto, com versões e lockfiles existentes. Registre comandos e versões realmente utilizados. Evite upgrades amplos; se uma mudança necessária altera o escopo aprovado, apresente a decisão antes de realizá-la. Prepare configuração de teste sem credenciais reais e substitutos para integrações externas. Diretórios temporários, portas locais e processos pertencem à execução; registre-os para limpeza precisa.

Transforme o inventário da Fase 1 em uma matriz de validação. Se o inventário era parcial ou dinâmico, resolva as lacunas antes de afirmar cobertura de todos os endpoints. Use um caso por par método/caminho explícito, além dos erros relevantes; excluir HEAD/OPTIONS automáticos conforme o critério da análise.

| Método/caminho | Preparação/identidade | Entrada | Resultado esperado | Efeito esperado nos dados | Resultado observado/evidência |
|---|---|---|---|---|---|

Preserve payload/status/semântica originais, exceto deltas aprovados. Não registrar dados sensíveis nos exemplos de saída. Login e recursos administrativos devem usar identidades sintéticas adequadas. Resposta 401 em todos os endpoints protegidos não comprova que os fluxos autorizados funcionam.

## 2. Testes que comprovam as mudanças

Execute os testes existentes e acrescente testes de regressão para os findings corrigidos e contratos relevantes. Use o mecanismo nativo da stack; não impor framework de teste novo quando o existente basta.

- **Rotas/contratos:** método, caminho, chaves, tipos, status, erros e conteúdo significativo; não conferir apenas ausência de 500.
- **CRUD e fluxos:** criação, leitura, atualização e exclusão; relações, checkout/pedido e relatórios quando presentes. Confira persistência e efeitos esperados, não apenas o JSON.
- **Validação:** tipos inválidos, limites e campos ausentes. Diferencie corpo malformado, recurso inexistente e conflito.
- **Segurança corrigida:** senhas não expostas, dados de consulta tratados como valores, autenticação/autorização nos fluxos afetados e logs sem dados sensíveis. Use exclusivamente dados e ambiente de teste.
- **Transações:** falha intermediária, rollback e ausência de registros parciais. Isolamento entre operações quando esse foi um finding.
- **N+1:** contagem de consultas com conjuntos de tamanhos diferentes, dados equivalentes e relações vazias. Não usar tempo de execução como única evidência.
- **APIs e datas:** equivalência de retorno/erro e semântica de timezone quando houver migração. Verificar warnings relevantes à versão alvo.

Testes unitários de domínio, integração com banco temporário e testes HTTP têm propósitos distintos. Rode a combinação necessária para comprovar as mudanças; não criar testes que apenas verifiquem nomes de arquivos, textos do próprio código ou quantidade de classes.

## 3. Boot real e endpoints

Inicie o processo da aplicação com o comando documentado, em loopback e porta livre, sem debug/reloader quando possível. Use configuração e banco descartáveis. Confirme que o processo que iniciou está vivo e é o que responde na porta; um serviço pré-existente não serve como evidência.

Espere prontidão com prazo limitado e execute uma chamada HTTP real. Capture comando, configuração não sensível, porta, código de saída/erro e trecho sanitizado do log. Depois percorra a matriz de endpoints com clientes HTTP ou testes de integração, verificando resposta e efeitos. Um test client interno complementa, mas não substitui, a confirmação do boot do processo.

Exemplos de abordagem, adaptados aos comandos detectados:

| Stack | Testes e boot |
|---|---|
| Python/Flask | Test runner presente (`pytest`/`unittest`, conforme o projeto), cliente Flask para integração e processo via entry point/CLI documentado; banco em caminho temporário. |
| Node.js/Express | Script de teste existente ou runner apropriado; app exportável separado do listener; inicialização pelo script do manifesto e chamadas HTTP reais. |
| Outras | Equivalentes nativos que iniciem o processo, exercitem entrada real e verifiquem persistência/contratos. |

Não declarar sucesso se instalação, boot ou endpoint falhar. Corrija problemas dentro do escopo e repita as verificações afetadas; após a última alteração funcional, execute a matriz completa apropriada. Se a limitação for ambiental, registre o comando, erro e validações que ficaram pendentes. Uma falha já existente não vira aprovação silenciosa da versão refatorada.

Ao terminar, encerre somente os processos iniciados nesta execução e feche recursos temporários. Não usar encerramento amplo de processos por nome. Preserve logs úteis e artefatos de teste autorizados; não remover arquivos do usuário.

## 4. Revisão arquitetural e dos findings

Releia os pontos do relatório contra a versão final. Para cada ID, registre `corrigido`, `parcial`, `pendente` ou `não confirmado`, com evidência atual e justificativa. Não apague o achado original para esconder a evolução. Se um finding for descartado, explique a nova evidência.

Confira dependências reais das camadas, configuração externa, tratamento central de erros, ausência de imports circulares e efeitos de inicialização. Use o catálogo para procurar regressões introduzidas pela extração. Não afirmar “zero anti-patterns” com base apenas em testes que passaram; relatar o escopo revisado e resíduos concretos.

Revise o diff, elimine arquivos temporários acidentais e atualize instruções de instalação/execução conforme os comandos realmente usados. Não incluir bancos de teste, ambientes virtuais, dependências instaladas ou segredos no commit. Respeite autorização existente para commits; no desafio, o Requisito 3 pede commit do projeto refatorado. Adicione apenas os arquivos pertinentes e não use `git add .` indiscriminadamente. Push, PR e publicação não decorrem automaticamente do commit local.

## 5. Saída final da Fase 3

Apresente um resumo que possa ser revisado sem consultar o histórico:

```markdown
# Fase 3 — Resultado da refatoração

- Projeto/revisão auditada: ...
- Aprovação aplicada e deltas de contrato: ...
- Estado: concluída / parcial (motivo).

## Estrutura antes/depois
... árvore relevante e responsabilidades ...

## Findings e resultado
| ID | Estado | Arquivo/linhas atuais | Evidência de validação / pendência |
|---|---|---|---|

## Validação executada
| Comando/cenário | Esperado | Observado | Evidência |
|---|---|---|---|

Boot real: ... (comando, porta, prontidão e log).
Endpoints: ... pares método/caminho verificados de ... inventariados.
Matriz completa de contratos/efeitos: ...
Testes: ... (resultado real, incluindo falhas).
Processos/recursos de teste: ... (encerrados ou pendência explícita).

## Checklist
- [ ] Responsabilidades MVC verificadas no código.
- [ ] Configuração externa e sem segredos embutidos.
- [ ] Models abstraem dados; rotas e controllers separados.
- [ ] Erros centralizados e entry point claro.
- [ ] Aplicação inicia sem erros no ambiente validado.
- [ ] Todos os endpoints inventariados exercitados com contratos esperados.
- [ ] Regressões dos findings corrigidos verificadas.
- [ ] Alterações de contrato e migração documentadas.

## Limitações e arquivos importantes
... arquivos, resultados não verificados, findings residuais e próximos passos ...
Commit: ... (hash real, se criado; caso contrário, não realizado).
```

Só marque itens verificados. “Concluída” exige boot, cobertura dos endpoints e fechamento do escopo aprovado; pendências precisam ser declaradas e impedem alegação de sucesso completo. Ao terminar, pare para revisão do usuário; não iniciar outro projeto automaticamente.
