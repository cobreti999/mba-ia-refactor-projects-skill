# Criação de Skills — Refatoração Arquitetural Automatizada

Ao longo do curso você aprendeu o que são Skills e como elas permitem que um agente de IA atue como um especialista em tarefas específicas. Agora imagine o seguinte cenário: você herdou 3 projetos legados com problemas de arquitetura, segurança e qualidade de código. Revisar e corrigir tudo manualmente levaria dias.

Neste desafio, você vai criar uma Skill que automatiza esse processo — analisando, auditando e refatorando qualquer projeto para o padrão MVC, independente da tecnologia.

## Acompanhamento da implementação

Ferramenta escolhida: **OpenAI Codex**. O repositório informado já é o fork do desafio.

| Etapa | Situação |
|---|---|
| Requisito 1 — Análise Manual | Concluído |
| Requisito 2 — Criação da Skill | Concluído: três fases implementadas e aprovadas |
| Requisito 3 — Execução nos três projetos | Concluído: três projetos refatorados e validados |

O desenvolvimento para ao final de cada requisito e de cada fase da skill, aguardando um **ok explícito**. Na criação, serão entregues separadamente as fases Análise, Auditoria e Refatoração. Na execução, também haverá pausa entre as fases de cada projeto. A confirmação de uma etapa autoriza somente a próxima.

## Análise Manual

Análise realizada em **19/10/2026**, por leitura direta do código, sem executar a skill. Base: commit `6d1ce6248c3e956801010a89d8bdaab48029bf30`. Os caminhos e intervalos de linhas abaixo correspondem a essa versão original; poderão mudar após a refatoração. Foram lidos os arquivos-fonte dos três projetos, seus manifestos de dependências, READMEs e exemplos de requisições disponíveis.

Esta etapa é uma inspeção estática: as evidências foram conferidas no código, mas boot, requisições HTTP e testes de regressão ainda não foram executados. As versões da tabela são as **declaradas**, não versões confirmadas em execução. O levantamento prioriza problemas concretos e não pretende esgotar todos os achados da futura auditoria.

### Visão dos projetos

| Projeto | Stack e armazenamento | Domínio e arquitetura atual |
|---|---|---|
| `code-smells-project` | Python, Flask 3.1.1, flask-cors 5.0.1, SQLite via `sqlite3` | E-commerce: produtos, usuários, pedidos e relatórios. Quatro arquivos Python, com separação nominal entre controllers/models, mas SQL e responsabilidades de negócio espalhados. |
| `ecommerce-api-legacy` | JavaScript/Node.js, Express `^4.18.2`, sqlite3 `^5.1.6`, SQLite em memória | LMS: cursos, usuários, matrículas e pagamentos. Três arquivos JavaScript; `AppManager` concentra banco, rotas, checkout e relatórios. |
| `task-manager-api` | Python, Flask 3.0.0, Flask-SQLAlchemy 3.1.1, SQLite | Tarefas, usuários, categorias e produtividade. Quinze arquivos Python, incluindo quatro `__init__.py` e o seed. Possui models/routes/services/utils, mas as rotas concentram os casos de uso. |

### Projeto 1 — code-smells-project

| ID | Severidade | Problema e evidência | Impacto e direção de correção |
|---|---|---|---|
| P1-01 | CRITICAL | **SQL Injection.** `models.py:105–111` concatena email e senha no SQL de login; `models.py:285–299` concatena termo e categoria na busca. Entradas chegam de `controllers.py:111–123` e `167–176`. | A entrada altera a expressão SQL e pode contornar a verificação de credenciais ou modificar a consulta. Parametrizar valores em todas as operações. A evidência não depende dos IDs de rota, que usam conversor inteiro. |
| P1-02 | CRITICAL | **Operações administrativas sem controle de acesso.** `app.py:47–78` expõe reset das quatro tabelas e execução do SQL recebido no JSON, sem autenticação/autorização no fluxo. | Qualquer cliente com acesso à API pode apagar dados ou executar SQL arbitrário. Definir autorização administrativa e substituir SQL livre por operações explícitas; revisar esse contrato antes da refatoração. |
| P1-03 | CRITICAL | **Senhas armazenadas e expostas em texto puro.** `models.py:122–130` persiste a senha recebida; `models.py:72–103` inclui `senha` nas consultas de usuários; `controllers.py:128–144` devolve esses objetos. | Uma leitura da API revela credenciais. Usar hash próprio para senhas, remover o campo das respostas e planejar o tratamento das credenciais existentes. |
| P1-04 | HIGH | **Conexão global mutável.** `database.py:4–12` mantém uma única conexão com `check_same_thread=False`; as funções de `models.py` reutilizam essa conexão e fazem commits. | Requisições compartilham estado transacional, dificultando isolamento, rollback e testes. Gerenciar conexão por contexto e delimitar transações por caso de uso. Desativar a checagem de thread não fornece isolamento. |
| P1-05 | HIGH | **Responsabilidades de negócio misturadas à persistência.** `models.py:133–169` valida estoque, calcula total, cria pedido e baixa estoque; `models.py:235–273` combina consultas e política de desconto. | Regras comerciais dependem diretamente de SQL e ficam difíceis de testar isoladamente. Separar orquestração, regras de domínio e acesso a dados no MVC alvo. |
| P1-06 | MEDIUM | **Consultas N+1 aninhadas.** `models.py:171–201` e `203–233` consultam itens para cada pedido e produto para cada item. | O custo cresce com pedidos e itens: uma consulta inicial, uma por pedido e uma por item. Carregar relações em lote ou por joins, preservando o formato das respostas. |
| P1-07 | MEDIUM | **Validação duplicada e divergente.** `controllers.py:28–54` valida nome e categoria na criação; `controllers.py:72–90` repete parte das regras na atualização e omite essas verificações. | Um produto rejeitado no POST pode ser aceito no PUT. Centralizar regras compartilhadas e validar tipos antes de comparações e chamadas a `len`. |
| P1-08 | LOW | **Números mágicos na política de desconto.** `models.py:256–262` embute limites e percentuais sem nomes de negócio. | Dificulta revisar e alterar a política comercial. Nomear as faixas e taxas, mantendo o comportamento até haver decisão explícita de mudá-lo. |
| P1-09 | LOW | **Imports sem uso.** `database.py:2` importa `os`; `models.py:2` importa `sqlite3`, embora o acesso ocorra por `get_db`. | Acrescenta ruído e sugere dependências inexistentes. Remover imports sem referências. |

### Projeto 2 — ecommerce-api-legacy

Os caminhos desta tabela são relativos a `ecommerce-api-legacy/`. Apesar do nome da pasta, o domínio observado é **LMS com checkout de cursos**, não uma loja de produtos.

| ID | Severidade | Problema e evidência | Impacto e direção de correção |
|---|---|---|---|
| P2-01 | CRITICAL | **God Class.** `src/AppManager.js:4–25` cria banco e schema; `28–78` implementa checkout; `80–137` implementa relatórios e exclusão, com SQL diretamente nos handlers. | A mesma classe concentra infraestrutura, HTTP e regras complexas, violando a separação MVC. Extrair acesso a dados, casos de uso e controllers, deixando rotas e composição explícitas. |
| P2-02 | CRITICAL | **Pseudo-hash de senha.** `src/utils.js:17–22` repete os dois primeiros caracteres do Base64 e retorna dez caracteres; `src/AppManager.js:66–71` usa isso ao cadastrar usuário. | O resultado descarta quase toda a informação da senha e produz muitas colisões; repetir o cálculo não o torna um hash seguro. Substituir por algoritmo próprio para senhas e tratar os registros antigos. |
| P2-03 | HIGH | **Checkout sem atomicidade.** `src/AppManager.js:50–61` grava matrícula, pagamento e auditoria em operações separadas, sem transação e sem rollback. | Uma falha no pagamento deixa matrícula persistida; a falha de auditoria é ignorada antes de responder sucesso. Delimitar uma transação para as gravações relacionadas e tratar falhas. |
| P2-04 | HIGH | **Dados sensíveis em log e configuração embutida.** `src/AppManager.js:45` imprime o cartão completo e a chave configurada em `src/utils.js:1–7`. | Logs recebem dados financeiros e a configuração de pagamento; o código também contém valores com aparência de credenciais, cuja validade externa não foi verificada. Redigir dados sensíveis e carregar configuração por ambiente. |
| P2-05 | MEDIUM | **N+1 no relatório financeiro.** `src/AppManager.js:83–106` consulta cursos, matrículas por curso e usuário/pagamento por matrícula. | O número de consultas cresce com o volume de cursos e matrículas. Agregar dados e carregar relações em lote, preservando receitas e alunos no resultado. |
| P2-06 | MEDIUM | **Validação de tipo ausente no checkout.** `src/AppManager.js:29–35` testa apenas presença; `45–46` usa `cc.startsWith` sem garantir string. | Um cartão numérico passa pelo teste de presença e provoca exceção dentro do callback assíncrono. Validar o corpo antes de consultar o banco e responder 400 para tipos inválidos. |
| P2-07 | LOW | **Nomes locais pouco expressivos.** `src/AppManager.js:29–33` usa `u`, `e`, `p`, `cid` e `cc` para dados distintos do checkout. | Aumenta o esforço de leitura dos callbacks. Usar nomes internos descritivos, preservando inicialmente as chaves públicas `usr`, `eml`, `pwd`, `c_id` e `card`. |
| P2-08 | LOW | **Estado/import sem uso.** `src/utils.js:10,25` declara e exporta `totalRevenue`; `src/AppManager.js:2` importa esse valor sem utilizá-lo. | Sugere um controle global de receita que não participa do relatório real. Remover o símbolo morto e manter a receita derivada dos pagamentos. |

### Projeto 3 — task-manager-api

Os caminhos desta tabela são relativos a `task-manager-api/`. A existência de pastas por camada não garante a separação das responsabilidades.

| ID | Severidade | Problema e evidência | Impacto e direção de correção |
|---|---|---|---|
| P3-01 | CRITICAL | **Hash de senha fraco e exposto na resposta.** `models/user.py:27–32` usa MD5 sem salt; `16–25` inclui `password` em `to_dict`, retornado por `routes/user_routes.py:33–40` e `207–211`. | Respostas expõem hashes fáceis de testar por tentativa offline. Usar hash próprio para senhas e uma representação pública sem credenciais, prevendo tratamento dos hashes existentes. |
| P3-02 | HIGH | **Autenticação e autorização não efetivadas.** `routes/user_routes.py:185–211` retorna um token formado por texto fixo e ID; `42–78` permite escolher `admin` no cadastro e `92–125` alterar papel sem verificar identidade/permissão. | O login não estabelece proteção para os endpoints e o cliente controla papéis privilegiados. Definir autenticação verificável e autorização por operação, com mudanças de contrato explícitas. |
| P3-03 | HIGH | **Rotas concentram casos de uso e persistência.** `routes/task_routes.py:85–154` valida, consulta relações, constrói entidade e faz commit; `routes/report_routes.py:12–101` calcula o relatório dentro do handler. | Regras ficam acopladas ao Flask e à sessão do banco. Extrair controllers/casos de uso e manter rotas finas, reaproveitando os models existentes. |
| P3-04 | MEDIUM | **N+1 nas categorias.** `routes/report_routes.py:157–165` busca todas as categorias e executa um `count` de tarefas por categoria. | A listagem faz uma consulta inicial mais uma por categoria. Usar agregação por categoria ou carregamento em lote, incluindo categorias sem tarefas. |
| P3-05 | MEDIUM | **Conversões sem validação na busca.** `routes/task_routes.py:240–264` converte `priority` e `user_id` com `int`, sem tratar entrada não numérica. | Uma entrada inválida gera erro interno em vez de erro de cliente. Validar parâmetros e padronizar a resposta 400. |
| P3-06 | MEDIUM | **Regra de atraso duplicada.** `models/task.py:50–60` já implementa `is_overdue`, mas a lógica se repete em `routes/task_routes.py:30–39,71–80` e `routes/user_routes.py:171–180`. | Mudanças na definição de atraso podem produzir respostas inconsistentes entre endpoints. Reutilizar uma regra de domínio, preservando os campos de cada resposta. |
| P3-07 | LOW | **Imports sem uso.** `routes/task_routes.py:7` importa `json`, `os`, `sys` e `time`; `utils/helpers.py:3–7` importa módulos sem referências no arquivo. | Oculta as dependências reais e dificulta leitura. Remover os imports não utilizados. |
| P3-08 | LOW | **Limites literais apesar de constantes existentes.** `routes/task_routes.py:96–100,166–170` embute 3 e 200; `utils/helpers.py:112–113` já define limites nomeados. | Alterar a constante não atualiza a validação das rotas. Adotar uma fonte única para os limites, sem mudar a regra comercial. |

### Conferência do Requisito 1

| Projeto | CRITICAL | HIGH | MEDIUM | LOW | Total | Mínimos atendidos |
|---|---:|---:|---:|---:|---:|---|
| code-smells-project | 3 | 2 | 2 | 2 | 9 | Sim |
| ecommerce-api-legacy | 2 | 2 | 2 | 2 | 8 | Sim |
| task-manager-api | 1 | 2 | 3 | 2 | 8 | Sim |
| **Total** | **6** | **6** | **7** | **6** | **25** | **3/3 projetos** |

Cada projeto tem pelo menos cinco problemas, pelo menos um CRITICAL/HIGH, dois MEDIUM e dois LOW. Os IDs serão usados para comparar a auditoria da skill com este levantamento, sem orientar a skill a simplesmente reproduzir a lista.

Os principais sinais reutilizáveis são: SQL concatenado com entrada externa, exposição de credenciais, ausência de controle de acesso, mistura de camadas, estado global, falta de transação, consultas dentro de loops, validação inconsistente, duplicação e código morto. A futura auditoria também deverá investigar APIs obsoletas e confirmar sua situação conforme a versão da stack; essa verificação ainda não foi realizada nesta etapa.

**Próximo passo, após aprovação:** Requisito 3, Projeto 2 — executar somente a Fase 1 da skill em `ecommerce-api-legacy/` e parar para revisão antes da Auditoria.


## Execução da Skill — Projeto 1 concluído

A execução em `code-smells-project/` percorreu Análise, Auditoria e Refatoração com aprovação entre as fases. Foram corrigidos **14 achados** (4 CRITICAL, 4 HIGH, 4 MEDIUM e 2 LOW), correspondendo aos **9 problemas da análise manual** deste projeto.

A aplicação mantém Flask e SQLite, agora com rotas, controllers, serviços, repositórios e serializadores separados. Foram implementados autenticação/autorização, hash e migração explícita de senhas, SQL parametrizado, conexão por contexto, transações com rollback, validação compartilhada e carga de pedidos em duas consultas.

**Validação:** 12 testes de regressão aprovados e 19/19 endpoints exercitados por HTTP com servidor real, banco temporário e encerramento do processo. A caracterização anterior à mudança também cobriu 19 endpoints. Os deltas de contrato aprovados incluem token no login, permissões por usuário/papel, remoção de senhas das respostas, health sem configuração, substituição de SQL livre por contagens e reset condicionado à configuração.

- [Relatório, achados e rastreabilidade](reports/audit-project-1.md)
- [Evidência do comportamento original](reports/baseline-project-1.json)
- [Evidência HTTP final e versões executadas](reports/validation-project-1.json)
- [Arquitetura, migração, execução e matriz de acesso](code-smells-project/README.md)
- [Testes de regressão](code-smells-project/tests/test_app.py) e [teste HTTP real](code-smells-project/tests/smoke_http.py)

O projeto 2 foi concluído na execução registrada em Resultados abaixo. O projeto 3 permanece pendente de revisão explícita.

## Construção da Skill

### Fase 1 — Análise (implementada)

A skill está em [`code-smells-project/.agents/skills/refactor-arch/`](code-smells-project/.agents/skills/refactor-arch/). O caminho `.agents/skills/` segue a [documentação oficial do Codex](https://learn.chatgpt.com/docs/build-skills), consultada em 19/10/2026, adaptando o exemplo `.claude/skills/` do enunciado à ferramenta escolhida.

| Arquivo | Responsabilidade |
|---|---|
| [`SKILL.md`](code-smells-project/.agents/skills/refactor-arch/SKILL.md) | Define o alvo, conduz as três fases, carrega as referências pertinentes e estabelece as pausas e a aprovação antes da Refatoração. |
| [`references/project-analysis.md`](code-smells-project/.agents/skills/refactor-arch/references/project-analysis.md) | Contém heurísticas para inventário, linguagem/framework, versões, persistência, domínio, responsabilidades, endpoints e formato do resumo. |

**Decisões de design:**

- Instruções em Markdown, sem script de detecção específico para Flask ou Express: o agente cruza manifestos, imports e fluxos reais. A referência inclui sinais de vários ecossistemas e orienta como lidar com stacks desconhecidas.
- O projeto-alvo vem do pedido ou do diretório de trabalho, não da pasta onde a skill reside. Se houver múltiplas aplicações e nenhum alvo definido, a skill pede a escolha.
- O ponto de entrada permanece curto; as heurísticas e o formato de saída são carregados pela referência somente quando necessários.
- A análise é estática e produz a saída na conversa. Não instala dependências, importa a aplicação, executa seeds, inicia servidores nem altera arquivos do alvo.
- A contagem separa fontes, testes e suporte; inclui inicializadores e seeds, mas exclui skills, dependências e arquivos gerados. Informa a cobertura efetiva de leitura.
- A arquitetura é inferida das responsabilidades e chamadas reais, sem assumir que nomes como `models` ou `services` garantem a separação de camadas.
- Cada conclusão deve ter evidência em arquivo/linha. Versões declaradas, resolvidas e verificadas em execução são tratadas separadamente; valores de credenciais não entram na saída.
- As pausas estão no próprio `SKILL.md`. Um pedido inicial de fluxo completo não elimina a revisão entre fases; a aprovação vale para o projeto e escopo apresentados.

**Conferência desta entrega:** `quick_validate.py` da skill-creator aprovado (`Skill is valid!`), `git diff --check` sem erros e referências locais verificadas e critérios de inventário confrontados com os três projetos: 4, 3 e 15 fontes, respectivamente. A distinção de versões foi conferida no Node.js: Express declarado `^4.18.2` e resolvido `4.22.1`; sqlite3 declarado `^5.1.6` e resolvido `5.1.7`. Isso não comprova as versões instaladas. A execução integral da skill nos três projetos continua reservada ao Requisito 3; boot e endpoints ainda não foram testados.

### Fase 2 — Auditoria (implementada)

| Arquivo | Responsabilidade |
|---|---|
| [`references/anti-patterns.md`](code-smells-project/.agents/skills/refactor-arch/references/anti-patterns.md) | Catálogo com 16 padrões, severidades, sinais, confirmação contextual, cuidados contra falsos positivos e direção de correção. |
| [`references/audit-report-template.md`](code-smells-project/.agents/skills/refactor-arch/references/audit-report-template.md) | Relatório padronizado, evidências em arquivo/linhas, totais, cobertura, proposta de refatoração e registro de aprovação. |
| [`SKILL.md`](code-smells-project/.agents/skills/refactor-arch/SKILL.md) | Sequência de auditoria, retomada após análise aprovada e confirmação antes de qualquer escrita. |

**Catálogo:** SQL Injection, exposição de segredos/dados, armazenamento inadequado de senhas, autenticação/autorização, God Class, regras acopladas a handlers, estado global, atomicidade, N+1, validação, duplicação, tratamento de erros, APIs obsoletas, números mágicos, nomenclatura e código sem uso. A seleção cobre segurança e separação MVC/SOLID, além de problemas de desempenho e manutenção observados na análise manual. Os sinais são independentes dos nomes de arquivos e das linguagens dos projetos; exemplos de bibliotecas complementam os critérios gerais.

**Relatório:** cada finding tem ID, severidade justificada, evidência, impacto, recomendação, contratos/dados afetados e validação futura. Há cobertura de todos os padrões, seção separada para candidatos não confirmados e comparação com a análise manual. Os totais contam problemas distintos, sem inflar o número por ocorrência. O mínimo de cinco findings não permite inventar achados; a correspondência com cinco problemas manuais do primeiro projeto também é conferida.

**APIs obsoletas:** a regra exige versão aplicável e documentação oficial, distinguindo deprecated, legacy suportada e removida. O catálogo traz fontes de SQLAlchemy e Python e exige pesquisa equivalente para outras stacks. Uma chamada a `datetime.utcnow()` sem versão de Python estabelecida fica como candidato condicionado, não como depreciação confirmada no ambiente. A troca de APIs também deve considerar diferenças semânticas, como datas com e sem fuso horário.

**Pausas e arquivos:** a Fase 1 pede aprovação para a Auditoria; a Fase 2 apresenta o relatório e pede autorização para a proposta de refatoração. O relatório é exibido primeiro na conversa. Se for solicitado salvamento, a confirmação especifica o destino e autoriza somente esse arquivo; não autoriza alterar a aplicação. A Fase 3 começa somente com aprovação explícita da proposta e verificação de que o alvo e o escopo continuam correspondentes. Os relatórios `reports/audit-project-{1,2,3}.md` serão produzidos na execução do Requisito 3.

**Conferência desta entrega:** `quick_validate.py` aprovado, `git diff --check` sem erros, 16 IDs únicos e referências locais verificadas. Revisão estática das transições de fase e dos casos de falso positivo: SQL parametrizado, import por efeito colateral, controle de acesso em middleware e API com versão desconhecida. A orientação exige verificar esses casos antes de confirmar findings. Esta revisão documental não é uma execução independente do agente nem comprova a detecção nos três projetos; essa validação permanece no Requisito 3.

### Fase 3 — Refatoração (implementada)

| Arquivo | Responsabilidade |
|---|---|
| [`references/mvc-guidelines.md`](code-smells-project/.agents/skills/refactor-arch/references/mvc-guidelines.md) | Responsabilidades e dependências MVC, composição, configuração, contratos e tratamento dos dados. |
| [`references/refactoring-playbook.md`](code-smells-project/.agents/skills/refactor-arch/references/refactoring-playbook.md) | 12 transformações com 24 exemplos antes/depois em Python e JavaScript, vinculadas aos 16 padrões do catálogo. |
| [`references/validation.md`](code-smells-project/.agents/skills/refactor-arch/references/validation.md) | Baseline isolado, regressões, boot real, matriz completa de endpoints, revisão dos findings e formato do resultado final. |
| [`SKILL.md`](code-smells-project/.agents/skills/refactor-arch/SKILL.md) | Retomada da proposta aprovada, sequência de execução e encerramento antes do próximo projeto. |

**Transformações:** parametrizar SQL; extrair configuração e campos sensíveis; tratar senhas; aplicar autorização; separar responsabilidades; isolar estado e dependências; tornar gravações atômicas; eliminar N+1; centralizar validação e regras; tratar erros; migrar APIs obsoletas; remover ruído e nomear políticas. Os exemplos são trechos ilustrativos e deixam explícitos os colaboradores a implementar na stack real.

**Decisões arquiteturais:** as rotas registram HTTP, controllers coordenam os fluxos e models abstraem dados e invariantes. Serviços são usados quando há regras multientidade ou integrações que justifiquem a separação. A skill orienta preservar camadas já adequadas e adaptar convenções por linguagem, sem impor ORM, framework ou árvore rígida de arquivos. Para APIs, a representação JSON ocupa o papel de view.

**Contratos e aprovação:** a correção segue o relatório aprovado, preservando interfaces salvo deltas explicitados. Alterações materiais de escopo retornam à revisão. A aprovação já registrada não é solicitada de novo se continuar aplicável. Dados existentes não são apagados para viabilizar testes; migrações e credenciais antigas exigem estratégia compatível com a proposta.

**Validação exigida na execução:** testes pertinentes aos findings, inicialização do processo real e verificação de todos os pares método/caminho inventariados, com status, payloads e efeitos nos dados. Health check isolado ou respostas 401 em todas as rotas não comprovam funcionamento. Os testes usam dados sintéticos, banco isolado e substitutos para integrações externas. O resultado registra pendências e nunca declara conclusão completa com boot/endpoint não verificado.

**Verificações desta entrega:**

| Verificação | Resultado |
|---|---|
| `quick_validate.py` da skill-creator | Aprovado: `Skill is valid!` |
| Sintaxe dos exemplos | 20 trechos Python via AST e 4 JavaScript via `node --check`, todos aprovados |
| T-01 — SQL parametrizado | Apóstrofo preservado como dado; expressão de injeção não alterou a consulta |
| T-07 — Transação | Falha na segunda gravação reverteu ambas; caminho de sucesso confirmou as duas |
| T-08 — N+1 | Mesmo resultado, inclusive categoria vazia; exemplo passou de 3 consultas para 1 |
| T-09 — Validação | Tipos e limites inválidos rejeitados; limites válidos e atualização parcial preservados |
| T-12 — Política de desconto | Mesmo resultado abaixo, no limite e acima do valor de corte |

As verificações comportamentais foram executadas diretamente sobre os exemplos extraídos do Markdown, com SQLite em memória e script temporário. Os demais exemplos tiveram verificação de sintaxe e revisão documental; não foram tratados como aplicações completas. Isso não substitui a execução da skill nos três projetos, nem constitui teste independente do comportamento do agente.

**Requisito 2 concluído:** as cinco áreas obrigatórias estão cobertas (análise, catálogo, template de auditoria, guidelines MVC e playbook), com pausas entre fases. As cópias para os outros projetos, os relatórios de auditoria, a refatoração das aplicações e seus commits permanecem no Requisito 3.

## Como Executar

### Versão atual — três fases com aprovação entre etapas

Pré-requisito: Codex instalado e configurado, com acesso aos arquivos locais. A análise não exige instalar as dependências das aplicações.

Na raiz deste repositório, entre no projeto e abra o Codex CLI:

```bash
cd code-smells-project
codex
```

No prompt do Codex, invoque:

```text
$refactor-arch Analise este projeto e execute somente a Fase 1.
```

Para usar esta mesma conversa, aberta na raiz do repositório, indique o arquivo e o alvo explicitamente, pois a descoberta local não busca skills em subpastas arbitrárias:

```text
Use a skill em code-smells-project/.agents/skills/refactor-arch/SKILL.md
para executar somente a Fase 1 no projeto code-smells-project.
```

A saída esperada contém stack, domínio, persistência, contagem de fontes, mapa de responsabilidades, fluxo representativo, endpoints, comandos identificados e limitações. Ao final, a skill para e pede aprovação para iniciar a Auditoria. Para continuar na mesma sessão após revisar a análise:

```text
Ok, prossiga para a Fase 2 — Auditoria deste mesmo projeto.
```

A Fase 2 apresenta o relatório na conversa e pede confirmação antes de qualquer escrita. Uma análise ausente ou de outro alvo exige passar pela Fase 1; alterações no código exigem atualizar as evidências afetadas. Após revisar o relatório e suas mudanças de contrato, autorize a proposta para iniciar a Fase 3:

```text
Aprovo a proposta de refatoração apresentada para este projeto.
Execute a Fase 3 e pare ao concluir a validação.
```

A Fase 3 prepara as dependências necessárias em ambiente local/isolado e usa os comandos de boot/teste identificados no projeto. Ao final, apresenta evidências e aguarda revisão antes de seguir para outro projeto. Estes comandos são instruções de uso; a invocação completa via CLI e o funcionamento das aplicações ainda não foram validados nesta entrega.

---

## Objetivo

Você deve entregar uma Skill capaz de:

- Analisar uma codebase detectando linguagem, framework e arquitetura atual
- Identificar anti-patterns e code smells, classificando por severidade com arquivo e linha exatos
- Gerar um relatório de auditoria estruturado com todos os achados
- Refatorar o projeto para o padrão MVC (Model-View-Controller), eliminando os problemas encontrados
- Validar o resultado garantindo que a aplicação continua funcionando após as mudanças

A skill deve ser agnóstica de tecnologia, funcionando com diferentes linguagens e frameworks.

## Contexto

### Definição de Severidades

Para padronizar a sua auditoria e os relatórios gerados pela IA, utilize a seguinte escala de classificação baseada em problemas de MVC e SOLID:

- **CRITICAL:** Falhas graves de arquitetura ou segurança que impedem o funcionamento correto, expõem dados sensíveis (ex: credenciais hardcoded, SQL Injection) ou violam completamente a separação de responsabilidades (ex: "God Class" contendo banco de dados, lógicas complexas e roteamento no mesmo arquivo).
- **HIGH:** Fortes violações do padrão MVC ou princípios SOLID que dificultam muito a manutenção e testes (ex: lógicas de negócio pesadas presas dentro de Controllers, forte acoplamento sem Injeção de Dependência, ou uso de estado global mutável em toda a aplicação).
- **MEDIUM:** Problemas de padronização, duplicação de código ou gargalos de performance moderada (ex: Queries N+1 no banco de dados, uso inadequado de middlewares, validações ausentes nas rotas).
- **LOW:** Melhorias de legibilidade, nomenclatura de variáveis ruins, ou "magic numbers" soltos pelo código.

### Exemplo de Uso no CLI

```bash
# Executar a skill no projeto com problemas
cd code-smells-project
claude "/refactor-arch"
```

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python
Framework:      Flask 3.1.1
Dependencies:  flask-cors
Domain:        E-commerce API (produtos, pedidos, usuários)
Architecture:  Monolítica — tudo em 4 arquivos, sem separação de camadas
Source files:  4 files analyzed
DB tables:     produtos, usuarios, pedidos, itens_pedido
================================
```

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python + Flask
Files:   4 analyzed | ~800 lines of code

## Summary
CRITICAL: 4 | HIGH: 5 | MEDIUM: 2 | LOW: 3

## Findings

### [CRITICAL] God Class / God Method
File: models.py:1-350
Description: Arquivo único contém toda lógica de negócio, queries SQL, validação e formatação para 4 domínios diferentes.
Impact: Impossível testar em isolamento, qualquer mudança afeta tudo.
Recommendation: Separar em models e controllers por domínio.

### [CRITICAL] Hardcoded Credentials
File: app.py:8
Description: SECRET_KEY hardcoded como 'minha-chave-super-secreta-123'
...

================================
Total: 14 findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
> y
```

```
[... refatoração executada ...]

================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
src/
├── config/settings.py
├── models/
│   ├── produto_model.py
│   └── usuario_model.py
├── views/
│   └── routes.py
├── controllers/
│   ├── produto_controller.py
│   └── pedido_controller.py
├── middlewares/error_handler.py
└── app.py (composition root)

## Validation
  ✓ Application boots without errors
  ✓ All endpoints respond correctly
  ✓ Zero anti-patterns remaining
================================
```

## Tecnologias obrigatórias

- **Ferramenta:** uma das três opções abaixo (não são aceitas outras ferramentas):
  - Claude Code
  - Gemini CLI
  - OpenAI Codex
- **Recurso:** Custom Skills (ou o equivalente na ferramenta escolhida)
- **Formato dos arquivos de referência:** Markdown
- **Projetos-alvo:** Python/Flask (2 projetos) e Node.js/Express (1 projeto) (fornecidos no repositório base)

> **Nota sobre a ferramenta:** Os exemplos deste documento usam o Claude Code (`.claude/skills/`) como referência, pois é a ferramenta utilizada no curso. Se você optar por Gemini CLI ou Codex, adapte o nome da pasta e o comando de invocação conforme a convenção dela — o conceito de skill e a estrutura interna (SKILL.md + arquivos de referência) permanecem os mesmos.

## Requisitos

### 1. Análise Manual dos Projetos

Antes de criar a skill, você deve entender os problemas que ela vai resolver.

**Tarefas:**

- Analisar o projeto `code-smells-project/` (Python/Flask — API de E-commerce)
- Analisar o projeto `ecommerce-api-legacy/` (Node.js/Express — LMS API com fluxo de checkout)
- Analisar o projeto `task-manager-api/` (Python/Flask — API de Task Manager)

Para cada projeto, identificar e documentar no mínimo 5 problemas, incluindo pelo menos:

- 1 de severidade CRITICAL ou HIGH
- 2 de severidade MEDIUM
- 2 de severidade LOW

Documentar os achados na seção "Análise Manual" do seu `README.md`

> **Dica:** Não precisa encontrar todos os problemas — foque nos que têm maior impacto arquitetural. Use os projetos como insumo para entender quais padrões sua skill precisa detectar.

> **Por que 3 projetos?** Dois são Python/Flask (com níveis de organização diferentes) e um é Node.js/Express. Sua skill precisa funcionar nos 3 para provar que é verdadeiramente agnóstica de tecnologia — lidando tanto com código completamente desestruturado quanto com projetos que já possuem alguma separação de camadas.

### 2. Criação da Skill

Agora que você conhece os problemas, crie uma skill que os detecte, gere um relatório de auditoria e corrija automaticamente.

**Tarefas:**

Criar a skill dentro do projeto `code-smells-project/` e implementar o SKILL.md com 3 fases sequenciais:

- **Fase 1 — Análise:** Detectar stack, mapear arquitetura atual, imprimir resumo
- **Fase 2 — Auditoria:** Cruzar código contra catálogo de anti-patterns, gerar relatório, pedir confirmação
- **Fase 3 — Refatoração:** Reestruturar para o padrão MVC, validar que funciona

Criar arquivos de referência em Markdown que forneçam à skill o conhecimento necessário para executar as 3 fases. Os arquivos devem cobrir **obrigatoriamente** as seguintes áreas de conhecimento:

| Área de conhecimento | O que deve conter |
|---|---|
| Análise de projeto | Heurísticas para detecção de linguagem, framework, banco de dados e mapeamento de arquitetura |
| Catálogo de anti-patterns | Anti-patterns com sinais de detecção e classificação de severidade |
| Template de relatório | Formato padronizado do relatório de auditoria (Fase 2) |
| Guidelines de arquitetura | Regras do padrão MVC alvo (camadas Models, Views/Routes e Controllers, responsabilidades de cada uma) |
| Playbook de refatoração | Padrões concretos de transformação para cada anti-pattern (com exemplos de código) |

> **Nota:** Você tem liberdade para organizar os arquivos de referência como preferir — pode usar os nomes e a quantidade de arquivos que fizer sentido para sua skill. O importante é que todas as 5 áreas de conhecimento estejam cobertas. O nome da skill (`refactor-arch`) e o arquivo `SKILL.md` são obrigatórios e não devem ser alterados. O path da skill segue a convenção da ferramenta escolhida (no Claude Code, por exemplo, é `.claude/skills/refactor-arch/`).

**Requisitos da skill:**

- Deve ser agnóstica de tecnologia — deve funcionar corretamente nos 3 projetos fornecidos, independente da stack ou nível de organização
- O catálogo de anti-patterns deve conter no mínimo 8 anti-patterns com severidade distribuída (CRITICAL, HIGH, MEDIUM, LOW)
- O catálogo deve incluir detecção de APIs deprecated — identificar uso de APIs obsoletas e recomendar o equivalente moderno
- O playbook deve ter no mínimo 8 padrões de transformação com exemplos de código antes/depois
- A Fase 2 deve pausar e pedir confirmação antes de modificar qualquer arquivo
- A Fase 3 deve validar o resultado (boot da aplicação + endpoints funcionando)

### 3. Execução da Skill

Execute sua skill nos 3 projetos e valide que ela funciona em todas as stacks.

#### Projeto 1 — code-smells-project (Python/Flask)

Invocar a skill no Claude Code:

```bash
claude "/refactor-arch"
```

> **Nota:** O comando acima é o exemplo com Claude Code. Se você estiver usando Gemini CLI ou Codex, utilize o comando equivalente para invocar uma skill na sua ferramenta.

- Verificar que a Fase 1 detecta corretamente a stack e imprime o resumo
- Verificar que a Fase 2 encontra no mínimo 5 dos problemas documentados na sua análise manual
- Confirmar a execução da Fase 3
- Verificar que a Fase 3:
  - Cria a estrutura de diretórios baseada em MVC
  - A aplicação inicia sem erros
  - Os endpoints originais continuam respondendo
- Salvar o relatório de auditoria (output da Fase 2) em `reports/audit-project-1.md`
- Commitar o código refatorado do projeto no repositório

#### Projeto 2 — ecommerce-api-legacy (Node.js/Express)

Prove que sua skill é reutilizável em outro projeto de backend, mas com stack diferente.

- Copiar a pasta `.claude/skills/refactor-arch/` para dentro de `ecommerce-api-legacy/`
- Invocar a skill:

```bash
cd ../ecommerce-api-legacy
claude "/refactor-arch"
```

- Verificar que as 3 fases executam corretamente neste projeto
- Salvar o relatório em `reports/audit-project-2.md`
- Commitar o código refatorado do projeto no repositório

#### Projeto 3 — task-manager-api (Python/Flask)

Agora o teste com um projeto Python/Flask que já possui alguma organização de camadas (models, routes, services, utils).

- Copiar a pasta `.claude/skills/refactor-arch/` para dentro de `task-manager-api/`
- Invocar a skill:

```bash
cd ../task-manager-api
claude "/refactor-arch"
```

- Verificar que:
  - A Fase 1 detecta corretamente Python/Flask como stack e identifica o domínio de Task Manager
  - A Fase 2 identifica problemas mesmo em um projeto parcialmente organizado
  - A Fase 3 melhora a estrutura sem quebrar a aplicação (todos os endpoints devem continuar respondendo)
- Salvar o relatório em `reports/audit-project-3.md`
- Commitar o código refatorado do projeto no repositório

> **Nota:** Este projeto já possui alguma separação de camadas, mas isso não significa que a arquitetura está adequada. A skill deve identificar tanto problemas de código (segurança, performance, qualidade) quanto oportunidades de melhoria arquitetural. Se houver mudanças estruturais necessárias, a skill deve propô-las e executá-las.

#### Validação

Para cada projeto refatorado, valide o seguinte checklist:

```markdown
## Checklist de Validação

### Fase 1 — Análise
- [ ] Linguagem detectada corretamente
- [ ] Framework detectado corretamente
- [ ] Domínio da aplicação descrito corretamente
- [ ] Número de arquivos analisados condiz com a realidade

### Fase 2 — Auditoria
- [ ] Relatório segue o template definido nos arquivos de referência
- [ ] Cada finding tem arquivo e linhas exatos
- [ ] Findings ordenados por severidade (CRITICAL → LOW)
- [ ] Mínimo de 5 findings identificados
- [ ] Detecção de APIs deprecated incluída (se aplicável)
- [ ] Skill pausa e pede confirmação antes da Fase 3

### Fase 3 — Refatoração
- [ ] Estrutura de diretórios segue padrão MVC
- [ ] Configuração extraída para módulo de config (sem hardcoded)
- [ ] Models criados para abstrair dados
- [ ] Views/Routes separadas para visualização ou roteamento
- [ ] Controllers concentram o fluxo da aplicação
- [ ] Error handling centralizado
- [ ] Entry point claro
- [ ] Aplicação inicia sem erros
- [ ] Endpoints originais respondem corretamente
```

> **Dica:** Se a skill não detectou problemas suficientes ou a refatoração falhou, ajuste os arquivos de referência e execute novamente. É normal precisar de 2-4 iterações.

## Entregável

Repositório público no GitHub (fork do repositório base) contendo:

- Skill completa em `.claude/skills/refactor-arch/` (dentro dos 3 projetos)
- Código refatorado dos 3 projetos (resultado da execução da Fase 3, commitado no repositório)
- Relatórios de auditoria em `reports/` (3 arquivos)
- `README.md` atualizado

### Estrutura do repositório

Faça um fork do repositório base contendo os três projetos com code smells.

> **Nota:** A estrutura abaixo usa Claude Code como exemplo (`.claude/skills/`). Se estiver usando outra ferramenta, adapte os caminhos conforme a convenção dela.

```
desafio-skills/
├── README.md                              # Sua documentação
│
├── code-smells-project/                   # Projeto 1 — Python/Flask (API de E-commerce)
│   ├── .claude/
│   │   └── skills/
│   │       └── refactor-arch/             # ← SUA SKILL AQUI
│   │           ├── SKILL.md
│   │           └── (arquivos de referência)
│   ├── app.py
│   ├── controllers.py
│   ├── models.py
│   ├── database.py
│   └── requirements.txt
│
├── ecommerce-api-legacy/                  # Projeto 2 — Node.js/Express (LMS API com checkout)
│   ├── .claude/
│   │   └── skills/
│   │       └── refactor-arch/             # ← CÓPIA DA SKILL
│   │           └── ...
│   ├── src/
│   │   ├── app.js
│   │   ├── AppManager.js
│   │   └── utils.js
│   ├── api.http
│   └── package.json
│
├── task-manager-api/                      # Projeto 3 — Python/Flask (API de Task Manager)
│   ├── .claude/
│   │   └── skills/
│   │       └── refactor-arch/             # ← CÓPIA DA SKILL
│   │           └── ...
│   ├── app.py
│   ├── database.py
│   ├── seed.py
│   ├── requirements.txt
│   ├── models/
│   ├── routes/
│   ├── services/
│   └── utils/
│
└── reports/                               # Relatórios gerados
    ├── audit-project-1.md                 # Saída da Fase 2 no projeto 1
    ├── audit-project-2.md                 # Saída da Fase 2 no projeto 2
    └── audit-project-3.md                 # Saída da Fase 2 no projeto 3
```

**O que você vai criar:**

- `.claude/skills/refactor-arch/` — A skill completa (SKILL.md + arquivos de referência)
- Código refatorado dos 3 projetos — resultado da execução da Fase 3, commitado no repositório
- `reports/audit-project-{1,2,3}.md` — Relatório de auditoria de cada projeto
- `README.md` — Documentação do seu processo

**O que já vem pronto:**

- `code-smells-project/` — API de E-commerce Python/Flask com code smells intencionais
- `ecommerce-api-legacy/` — LMS API Node.js/Express (com fluxo de checkout) e problemas de implementação
- `task-manager-api/` — API de Task Manager Python/Flask com organização parcial e problemas de segurança/qualidade

> **Dica:** Cada projeto contém problemas intencionais de diferentes severidades (CRITICAL, HIGH, MEDIUM, LOW), incluindo falhas de segurança, violações arquiteturais e problemas de qualidade de código. Parte do desafio é identificá-los por conta própria através da análise manual do código.

### README.md deve conter

**A) Seção "Análise Manual":**

- Lista dos problemas identificados manualmente em cada projeto
- Classificação por severidade
- Justificativa de por que cada problema é relevante

**B) Seção "Construção da Skill":**

- Decisões de design: como estruturou o SKILL.md e os arquivos de referência
- Quais anti-patterns incluiu no catálogo e por quê
- Como garantiu que a skill é agnóstica de tecnologia
- Desafios encontrados e como resolveu

**C) Seção "Resultados":**

- Resumo dos relatórios de auditoria dos 3 projetos (quantos findings por severidade em cada)
- Comparação antes/depois da estrutura de cada projeto
- Checklist de validação preenchido para cada projeto
- Screenshots ou logs mostrando as aplicações rodando após refatoração
- Observações sobre como a skill se comportou em stacks diferentes

**D) Seção "Como Executar":**

- Pré-requisitos (a ferramenta escolhida — Claude Code, Gemini CLI ou Codex — instalada e configurada)
- Comandos para executar a skill em cada projeto
- Como validar que a refatoração funcionou

### Ordem de execução sugerida

**1. Analisar os projetos manualmente**

Leia o código dos três projetos e documente os problemas encontrados.

**2. Criar a skill**

Escreva o SKILL.md e os arquivos de referência.

**3. Executar nos 3 projetos**

```bash
# Projeto 1
cd code-smells-project
claude "/refactor-arch"

# Projeto 2
cd ../ecommerce-api-legacy
claude "/refactor-arch"

# Projeto 3
cd ../task-manager-api
claude "/refactor-arch"
```

Salve a saída da Fase 2 de cada projeto em `reports/audit-project-{1,2,3}.md`.

**4. Iterar**

Se a skill não detectou problemas suficientes ou a refatoração falhou, ajuste os arquivos de referência e execute novamente. É normal precisar de 2-4 iterações.

## Critérios de Aceite

A skill deve atingir os seguintes mínimos em **todos os 3 projetos**:

| Critério | Requisito |
|---|---|
| Fase 1 detecta stack corretamente | OBRIGATÓRIO (3/3 projetos) |
| Fase 2 encontra >= 5 findings | OBRIGATÓRIO (3/3 projetos) |
| Fase 2 inclui pelo menos 1 CRITICAL ou HIGH | OBRIGATÓRIO (3/3 projetos) |
| Fase 3 aplicação funciona após refatoração | OBRIGATÓRIO (3/3 projetos) |

**IMPORTANTE:** Todos os critérios devem ser atingidos nos 3 projetos, não apenas em um!

> **Sobre o projeto 3 (task-manager-api):** Este projeto já possui alguma organização. "aplicação funciona" significa que a API inicia sem erros e todos os endpoints continuam respondendo corretamente.

## Referências

- [Claude Code: Skills](https://docs.anthropic.com/en/docs/claude-code/skills) — Documentação oficial sobre como criar e estruturar Skills
- [Claude Code: Overview](https://docs.anthropic.com/en/docs/claude-code/overview) — Visão geral do Claude Code e suas capacidades
- [The Complete Guide to Building Skills for Claude (PDF)](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf) — Guia completo da Anthropic sobre construção de Skills
- [Equipping Agents for the Real World with Agent Skills](https://claude.com/blog/equipping-agents-for-the-real-world-with-agent-skills) — Blog oficial da Anthropic sobre Agent Skills

---

## Dicas Finais

- **Comece pela análise manual** — entender os problemas profundamente é essencial para criar uma skill que os detecte.
- **O SKILL.md é um prompt** — ele instrui o agente sobre o que fazer, enquanto os arquivos de referência fornecem o conhecimento de domínio.
- **Seja específico nos sinais de detecção** — "código ruim" não ajuda; "query SQL dentro de loop for" é acionável.
- **Teste incrementalmente** — não tente criar a skill perfeita de primeira.
- **A skill deve ser copiável** — se ela só funciona em um projeto específico, está acoplada demais. Teste nos 3 projetos para validar.
- **Projetos diferentes exigem adaptação** — a Fase 3 de um projeto já parcialmente organizado não vai ter as mesmas transformações de um monolito. Sua skill deve se adaptar ao contexto.
- **Pedir confirmação na Fase 2 é obrigatório** — o humano deve revisar o relatório antes de qualquer modificação.
- **Consulte as referências do curso** — revise a documentação oficial da ferramenta escolhida e os materiais das aulas para relembrar a estrutura e anatomia de uma skill.

## Resultados — Projeto 2 concluído

A skill refactor-arch foi executada em ecommerce-api-legacy: Análise e Auditoria em sequência no console e Refatoração somente após resposta real `y`. A auditoria encontrou **13 findings (4 CRITICAL, 2 HIGH, 5 MEDIUM, 2 LOW)**, com correspondência aos **8/8 problemas manuais**; os 13 foram corrigidos.

Antes: três fontes com AppManager concentrando banco, HTTP e regras. Depois: 14 fontes com composição/configuração, models, routes, controllers, serviços, autenticação, erros e scrypt. Node/Express/SQLite preservados; driver sqlite3 deprecated substituído por better-sqlite3 13.0.3. Deltas aprovados: credencial administrativa no relatório/DELETE, senha obrigatória/verificada no checkout, erros JSON, DELETE restrito por vínculos, validação e transações.

**Validação:** baseline original com sete cenários/3 endpoints; resultado final **16/16 testes e 26 cenários HTTP, 3/3 endpoints**, processos encerrados e logs sem segredos. Instalação reprodutível pelo lockfile; Node 24.22.0 temporário, Express 4.22.1. Checklist do projeto: stack/domínio/inventário, auditoria com linhas e APIs oficiais, aprovação, MVC/configuração/erros, boot e endpoints verificados.

- [Auditoria original aprovada e rastreabilidade final](reports/audit-project-2.md)
- [Baseline HTTP](reports/baseline-project-2.json)
- [Matriz HTTP, versões, efeitos e logs](reports/validation-project-2.json)
- [Saída real dos testes](reports/regression-project-2.txt)
- [Estrutura antes/depois, contratos e comandos](ecommerce-api-legacy/README.md)

Para reproduzir: Node >=22, recomendado 24; `cd ecommerce-api-legacy`, `npm ci`, configurar ambiente conforme README, `npm start`. Validar com `npm test` e `npm run test:http`. Banco em memória e pagamento simulado; sem validação de carga/serviços externos. O projeto 3 continua pendente e não foi iniciado nesta execução. Nenhum push, publicação ou PR realizado.

## Resultados — Projeto 3 concluído

A skill foi copiada integralmente para `task-manager-api/.agents/skills/refactor-arch/` e executada nesta conversa: Análise e Auditoria em sequência, Refatoração após a resposta explícita **“prossiga”**. A inspeção leu 15 fontes/1.158 linhas e inventariou 22 endpoints. A auditoria confirmou **12 findings (2 CRITICAL, 3 HIGH, 5 MEDIUM, 2 LOW)**, com correspondência aos **8/8 problemas manuais**; os 12 foram corrigidos.

O projeto já tinha models úteis, preservados com o schema. As responsabilidades restantes foram separadas em factory/configuração, rotas/controllers, serviços, repositório, serializadores e autenticação/erros. Implementados tokens assinados/expiráveis, papéis e propriedade; scrypt e redefinição explícita das senhas MD5; transações, validação compartilhada, seed somente em banco vazio, agregações/joins e regra única de atraso. Importar não cria tabelas ou inicia servidor. SQLAlchemy legacy Query.get e datetime.utcnow foram substituídos sem mudar a representação UTC do banco.

Deltas aprovados: autenticação e escopo por papel, cadastro público somente user, retirada de password das respostas, invalidação de tokens após reset/troca de senha, inicialização explícita e seed não destrutivo. Preservados os 22 caminhos/métodos, exclusão de usuário com suas tarefas e exclusão de categoria que desvincula/preserva tarefas. Migração de credenciais não apaga registros: contas MD5 exigem redefinição pelo CLI.

**Validação:** original isolado com 22/22 endpoints; versão final com **16/16 testes e 44 cenários HTTP, 22/22 endpoints**, efeitos SQLite verificados e processo encerrado. Medição de queries com 25 relações adicionais: duas consultas em tasks/users/categories e cinco no resumo, incluindo autenticação. Instalação limpa pelo lockfile; Python 3.14.7, Flask 3.0.0, Flask-SQLAlchemy 3.1.1, SQLAlchemy 2.1.5. O projeto requer Python >=3.11. A prontidão HTTP precisou de prazo de 60 segundos devido à resolução reversa do ambiente, registrada nos artefatos; nenhuma alteração no DNS ou monkeypatch da aplicação foi usada. Sem teste de carga/implantação nem envio externo de notificações.

- [Auditoria original, aprovação e rastreabilidade dos 12 achados](reports/audit-project-3.md)
- [Caracterização dos 22 endpoints originais](reports/baseline-project-3.json)
- [Matriz HTTP, efeitos, versões e hashes das fontes validadas](reports/validation-project-3.json)
- [Saída real dos testes](reports/regression-project-3.txt)
- [Arquitetura, permissões, inicialização, reset de credenciais e execução](task-manager-api/README.md)

**Requisito 3 concluído:** skill executada nos três projetos, com auditorias, aprovação antes da refatoração, MVC, boot real e cobertura dos endpoints (19/19, 3/3 e 22/22). Cada projeto possui seu relatório e evidências. Os commits são locais; nenhum push, PR ou publicação foi realizado. A entrega para neste ponto para revisão.
