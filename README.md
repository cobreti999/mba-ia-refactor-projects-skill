# Refatoração arquitetural automatizada com a skill refactor-arch

Entrega do desafio de análise, auditoria e refatoração de três projetos legados para MVC, usando **OpenAI Codex**. O repositório já é o fork do desafio. Os três projetos foram refatorados, validados e publicados em `origin/main`.

- [A) Análise Manual](#a-análise-manual)
- [B) Construção da Skill](#b-construção-da-skill)
- [C) Resultados](#c-resultados)
- [D) Como Executar](#d-como-executar)

O [enunciado original do desafio](DESAFIO.md) foi preservado separadamente para consulta. O [relatório final](reports/final-verification.md) reúne a conferência de aceite e as evidências.

## A) Análise Manual

Análise realizada em **19/10/2026**, por leitura direta do código, sem executar a skill. Base: commit `6d1ce6248c3e956801010a89d8bdaab48029bf30`. Os caminhos e intervalos de linhas abaixo correspondem a essa versão original; poderão mudar após a refatoração. Foram lidos os arquivos-fonte dos três projetos, seus manifestos de dependências, READMEs e exemplos de requisições disponíveis.

Esta etapa registra a inspeção estática original: as evidências foram conferidas no código, mas, naquele momento, boot, requisições HTTP e testes de regressão ainda não haviam sido executados. As versões da tabela são as **declaradas**, não versões confirmadas em execução. O levantamento prioriza problemas concretos e não pretende esgotar todos os achados da futura auditoria.

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

## B) Construção da Skill

A skill usa um `SKILL.md` como ponto de entrada e seis referências carregadas conforme a fase. As três cópias são idênticas, uma em cada projeto. O fluxo atual executa Análise e Auditoria em sequência e exige confirmação explícita antes da Refatoração. As verificações abaixo registram também a construção incremental, anterior à execução nos três projetos.

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
- O controle do fluxo está no `SKILL.md`: fases 1 e 2 em sequência, com aprovação antes da Fase 3. A aprovação vale para o projeto e escopo apresentados.

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

**Pausas e arquivos:** no fluxo atual, as fases 1 e 2 seguem em sequência. A Fase 2 apresenta o relatório completo e pede autorização antes da refatoração. A aprovação pode incluir o salvamento no destino informado; pedir somente salvamento não autoriza alterar a aplicação. A Fase 3 começa somente com aprovação explícita da proposta e verificação de que o alvo e o escopo continuam correspondentes. Os três relatórios foram produzidos na execução do Requisito 3 e estão em `reports/`.

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

**Requisito 2 concluído:** as cinco áreas obrigatórias estão cobertas (análise, catálogo, template de auditoria, guidelines MVC e playbook), com confirmação antes da Fase 3. As cópias, relatórios, refatorações e commits foram concluídos na execução do Requisito 3.

### Independência de tecnologia

A mesma skill e os mesmos seis arquivos de referência foram usados nos três alvos, sem nomes de tabelas/rotas embutidos nas regras. O catálogo tem **16 padrões** e o playbook **12 transformações**, com **24 exemplos antes/depois** em Python e JavaScript. Os alvos foram determinados pelo diretório/pedido; as instruções guiam a inspeção, não um detector dependente de uma stack.

### Desafios encontrados e soluções

Os principais desafios foram definir contratos seguros sem preservar vulnerabilidades, tratar senhas antigas sem perder registros, medir N+1 em vez de presumir ganho, distinguir APIs legacy de removidas e comprovar boot real. As decisões foram apresentadas antes da Fase 3; senhas legadas receberam migração ou redefinição explícita; os testes verificam rollback, permissões e efeitos. Bloqueios de loopback pelo sandbox foram repetidos com permissão; a demora de DNS reverso foi registrada e acomodada no prazo do teste, sem alterar o sistema. Não há alegação de ausência universal de anti-patterns nem validação de carga/produção.

## C) Resultados

**Publicação concluída:** as entregas foram enviadas para `origin/main` após a correção da autenticação. O push publicou os cinco commits até `9acc296`, preservando o histórico remoto. Detalhes estão no [relatório final](reports/final-verification.md).

| Projeto | CRITICAL | HIGH | MEDIUM | LOW | Total corrigido | Correspondência manual | Regressões | Endpoints reais |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| code-smells-project | 4 | 4 | 4 | 2 | 14/14 | 9/9 | 12/12 | 19/19 |
| ecommerce-api-legacy | 4 | 2 | 5 | 2 | 13/13 | 8/8 | 16/16 | 3/3 |
| task-manager-api | 2 | 3 | 5 | 2 | 12/12 | 8/8 | 16/16 | 22/22 |
| **Total** | **10** | **9** | **14** | **6** | **39/39** | **25/25** | **44/44** | **44/44** |

A conferência final repetiu as suítes e o HTTP real: **94 cenários HTTP** (24 + 26 + 44), todos com resultados esperados. Os processos foram encerrados. [Relatório final de aceite](reports/final-verification.md) e [evidência estruturada](reports/final-verification.json) registram comandos, versões, hashes e links para logs sanitizados. Os relatórios históricos das fases foram preservados.

### Comparação da estrutura antes/depois

| Projeto | Antes | Depois |
|---|---|---|
| `code-smells-project` | `app.py`, `controllers.py`, `models.py` e `database.py`; SQL e negócio misturados, conexão global | `app.py` como entrada; pacote `loja/` com factory/configuração, rotas, controllers, services, models/repositórios, views/serializadores e conexão por contexto |
| `ecommerce-api-legacy` | Três fontes; `AppManager` concentra banco, rotas, checkout e relatórios | 14 fontes; composição/configuração e camadas de routes, controllers, services e models/repositório, com autenticação e erros separados |
| `task-manager-api` | 15 fontes; models já existentes, mas regras e persistência concentradas em routes | Models e schema preservados; factory/configuração, controllers, services, repositório e views/serializadores; rotas finas |

As árvores completas e as responsabilidades estão nos READMEs da [loja](code-smells-project/README.md#arquitetura), do [LMS](ecommerce-api-legacy/README.md) e do [gerenciador de tarefas](task-manager-api/README.md).

### Checklist preenchido por projeto

As marcações abaixo correspondem a evidências nos relatórios [P1](reports/audit-project-1.md), [P2](reports/audit-project-2.md) e [P3](reports/audit-project-3.md). As linhas originais referem-se à base auditada, que continua acessível no histórico Git.

| Critério | Projeto 1 | Projeto 2 | Projeto 3 |
|---|---|---|---|
| Fase 1: linguagem e framework corretos | [x] Python/Flask | [x] JavaScript/Express | [x] Python/Flask |
| Fase 1: domínio correto | [x] E-commerce | [x] LMS/checkout | [x] Tarefas/produtividade |
| Fase 1: inventário conferido na base | [x] 4 fontes/780 linhas | [x] 3 fontes/180 linhas | [x] 15 fontes/1.158 linhas |
| Fase 2: relatório com evidência, impacto, recomendação e validação | [x] | [x] | [x] |
| Fase 2: arquivo/linhas originais e severidades ordenadas | [x] | [x] | [x] |
| Fase 2: pelo menos cinco achados e um CRITICAL/HIGH | [x] 14 | [x] 13 | [x] 12 |
| Fase 2: APIs deprecated verificadas por versão | [x] Nenhuma confirmada | [x] Driver sqlite3 | [x] Query.get; datas após confirmar runtime |
| Fase 2: confirmação antes da refatoração | [x] Conversa | [x] y no CLI | [x] Conversa |
| Fase 3: MVC, models, rotas/views e controllers separados | [x] | [x] | [x] |
| Fase 3: configuração externa e erros centrais | [x] | [x] | [x] |
| Fase 3: entry point claro e boot real | [x] | [x] | [x] |
| Fase 3: todos os endpoints com sucesso autorizado e efeitos verificados | [x] 19 | [x] 3 | [x] 22 |
| Fase 3: regressões, contratos e estratégia de dados documentados | [x] | [x] | [x] |
| Relatórios, logs de aplicação e código refatorado versionados | [x] | [x] | [x] |

### Logs das aplicações após a refatoração

As evidências abaixo foram produzidas por testes que iniciam o servidor real, fazem requisições HTTP e encerram o processo. Registram o comando de boot, a prontidão, os status observados e os efeitos nos dados; não são apenas testes de health check.

| Projeto | Log de boot e requisições HTTP | Saída da suíte | Resultado final |
|---|---|---|---|
| Loja Flask | [Log HTTP](reports/final-http-project-1.json) | [Log dos testes](reports/final-tests-project-1.txt) | 24 cenários, 19 endpoints; 12 testes aprovados |
| LMS Express | [Log HTTP](reports/final-http-project-2.json) | [Log dos testes](reports/final-tests-project-2.txt) | 26 cenários, 3 endpoints; 16 testes aprovados |
| Tarefas Flask/SQLAlchemy | [Log HTTP](reports/final-http-project-3.json) | [Log dos testes](reports/final-tests-project-3.txt) | 44 cenários, 22 endpoints; 16 testes aprovados |

### Comportamento da skill em stacks diferentes

Na loja, a extração criou um pacote MVC em torno de sqlite3 e transações explícitas. No LMS, callbacks e classe concentradora deram lugar a serviços/repositório; a troca de driver deprecated exigiu validar a semântica transacional síncrona e o runtime. No gerenciador de tarefas, models/ORM existentes foram preservados e o trabalho concentrou-se em retirar responsabilidades das rotas. Isso comprova a adaptação entre linguagens e níveis de organização.

### Projeto 1 — code-smells-project

A execução em `code-smells-project/` percorreu Análise, Auditoria e Refatoração com aprovação entre as fases. Foram corrigidos **14 achados** (4 CRITICAL, 4 HIGH, 4 MEDIUM e 2 LOW), correspondendo aos **9 problemas da análise manual** deste projeto.

A aplicação mantém Flask e SQLite, agora com rotas, controllers, serviços, repositórios e serializadores separados. Foram implementados autenticação/autorização, hash e migração explícita de senhas, SQL parametrizado, conexão por contexto, transações com rollback, validação compartilhada e carga de pedidos em duas consultas.

**Validação:** 12 testes de regressão aprovados e 19/19 endpoints exercitados por HTTP com servidor real, banco temporário e encerramento do processo. A caracterização anterior à mudança também cobriu 19 endpoints. Os deltas de contrato aprovados incluem token no login, permissões por usuário/papel, remoção de senhas das respostas, health sem configuração, substituição de SQL livre por contagens e reset condicionado à configuração.

- [Relatório, achados e rastreabilidade](reports/audit-project-1.md)
- [Evidência do comportamento original](reports/baseline-project-1.json)
- [Evidência HTTP final e versões executadas](reports/validation-project-1.json)
- [Arquitetura, migração, execução e matriz de acesso](code-smells-project/README.md)
- [Testes de regressão](code-smells-project/tests/test_app.py) e [teste HTTP real](code-smells-project/tests/smoke_http.py)

### Projeto 2 — ecommerce-api-legacy

A skill refactor-arch foi executada em ecommerce-api-legacy: Análise e Auditoria em sequência no console e Refatoração somente após resposta real `y`. A auditoria encontrou **13 findings (4 CRITICAL, 2 HIGH, 5 MEDIUM, 2 LOW)**, com correspondência aos **8/8 problemas manuais**; os 13 foram corrigidos.

Antes: três fontes com AppManager concentrando banco, HTTP e regras. Depois: 14 fontes com composição/configuração, models, routes, controllers, serviços, autenticação, erros e scrypt. Node/Express/SQLite preservados; driver sqlite3 deprecated substituído por better-sqlite3 13.0.3. Deltas aprovados: credencial administrativa no relatório/DELETE, senha obrigatória/verificada no checkout, erros JSON, DELETE restrito por vínculos, validação e transações.

**Validação:** baseline original com sete cenários/3 endpoints; resultado final **16/16 testes e 26 cenários HTTP, 3/3 endpoints**, processos encerrados e logs sem segredos. Instalação reprodutível pelo lockfile; Node 24.22.0 temporário, Express 4.22.1. Checklist do projeto: stack/domínio/inventário, auditoria com linhas e APIs oficiais, aprovação, MVC/configuração/erros, boot e endpoints verificados.

- [Auditoria original aprovada e rastreabilidade final](reports/audit-project-2.md)
- [Baseline HTTP](reports/baseline-project-2.json)
- [Matriz HTTP, versões, efeitos e logs](reports/validation-project-2.json)
- [Saída real dos testes](reports/regression-project-2.txt)
- [Estrutura antes/depois, contratos e comandos](ecommerce-api-legacy/README.md)

Para reproduzir: Node >=22, recomendado 24; `cd ecommerce-api-legacy`, `npm ci`, configurar ambiente conforme README, `npm start`. Validar com `npm test` e `npm run test:http`. Banco em memória e pagamento simulado; sem validação de carga/serviços externos.

### Projeto 3 — task-manager-api

A skill foi copiada integralmente para `task-manager-api/.agents/skills/refactor-arch/` e executada nesta conversa: Análise e Auditoria em sequência, Refatoração após a resposta explícita **“prossiga”**. A inspeção leu 15 fontes/1.158 linhas e inventariou 22 endpoints. A auditoria confirmou **12 findings (2 CRITICAL, 3 HIGH, 5 MEDIUM, 2 LOW)**, com correspondência aos **8/8 problemas manuais**; os 12 foram corrigidos.

O projeto já tinha models úteis, preservados com o schema. As responsabilidades restantes foram separadas em factory/configuração, rotas/controllers, serviços, repositório, serializadores e autenticação/erros. Implementados tokens assinados/expiráveis, papéis e propriedade; scrypt e redefinição explícita das senhas MD5; transações, validação compartilhada, seed somente em banco vazio, agregações/joins e regra única de atraso. Importar não cria tabelas ou inicia servidor. SQLAlchemy legacy Query.get e datetime.utcnow foram substituídos sem mudar a representação UTC do banco.

Deltas aprovados: autenticação e escopo por papel, cadastro público somente user, retirada de password das respostas, invalidação de tokens após reset/troca de senha, inicialização explícita e seed não destrutivo. Preservados os 22 caminhos/métodos, exclusão de usuário com suas tarefas e exclusão de categoria que desvincula/preserva tarefas. Migração de credenciais não apaga registros: contas MD5 exigem redefinição pelo CLI.

**Validação:** original isolado com 22/22 endpoints; versão final com **16/16 testes e 44 cenários HTTP, 22/22 endpoints**, efeitos SQLite verificados e processo encerrado. Medição de queries com 25 relações adicionais: duas consultas em tasks/users/categories e cinco no resumo, incluindo autenticação. Instalação limpa pelo lockfile; Python 3.14.7, Flask 3.0.0, Flask-SQLAlchemy 3.1.1, SQLAlchemy 2.1.5. O projeto requer Python >=3.11. A prontidão HTTP precisou de prazo de 60 segundos devido à resolução reversa do ambiente, registrada nos artefatos; nenhuma alteração no DNS ou monkeypatch da aplicação foi usada. Sem teste de carga/implantação nem envio externo de notificações.

- [Auditoria original, aprovação e rastreabilidade dos 12 achados](reports/audit-project-3.md)
- [Caracterização dos 22 endpoints originais](reports/baseline-project-3.json)
- [Matriz HTTP, efeitos, versões e hashes das fontes validadas](reports/validation-project-3.json)
- [Saída real dos testes](reports/regression-project-3.txt)
- [Arquitetura, permissões, inicialização, reset de credenciais e execução](task-manager-api/README.md)

**Requisito 3 concluído:** skill executada nos três projetos, com auditorias, aprovação antes da refatoração, MVC, boot real e cobertura dos endpoints (19/19, 3/3 e 22/22). Cada projeto possui seu relatório e evidências. As entregas foram publicadas em `origin/main`; o histórico de publicação está no relatório final.

## D) Como Executar

### Skill nos três projetos

Pré-requisito: **Codex CLI instalado e autenticado**. A análise não exige instalar dependências da aplicação. As três cópias idênticas usam a convenção do Codex: `.agents/skills/refactor-arch/`.

Execute um destes blocos a partir da raiz do repositório:

```bash
# Projeto 1 — loja Flask
cd code-smells-project
codex --no-alt-screen --search '$refactor-arch Execute as fases 1 e 2 e apresente a proposta antes da Fase 3.'
```

```bash
# Projeto 2 — LMS Express
cd ecommerce-api-legacy
codex --no-alt-screen --search '$refactor-arch Execute as fases 1 e 2 e apresente a proposta antes da Fase 3.'
```

```bash
# Projeto 3 — tarefas Flask/SQLAlchemy
cd task-manager-api
codex --no-alt-screen --search '$refactor-arch Execute as fases 1 e 2 e apresente a proposta antes da Fase 3.'
```

Também é possível abrir `codex` na pasta de cada projeto e digitar `$refactor-arch`, ou executar `.agents/skills/refactor-arch/scripts/run-cli.command`. O launcher usa o Codex CLI real, localiza o projeto pela posição da cópia da skill e preserva o histórico do console. Não contém relatório pré-fabricado nem resposta automática à confirmação.

A saída contém `PHASE 1: PROJECT ANALYSIS` e depois `ARCHITECTURE AUDIT REPORT`, com evidências, contagens reais e proposta. As fases 1 e 2 não têm pausa intermediária. Antes de alterar a aplicação, a skill apresenta os deltas e o destino `reports/audit-project-N.md` na raiz e pergunta:

```text
Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

Digite `y` no CLI para salvar o relatório e executar a proposta apresentada; `n` encerra sem refatorar. Ausência de resposta mantém a Fase 3 pendente. É possível solicitar somente uma fase. No aplicativo, indique a skill e o alvo explicitamente, por exemplo:

```text
Use task-manager-api/.agents/skills/refactor-arch/SKILL.md no projeto
 task-manager-api. Execute Análise e Auditoria em sequência nesta conversa
 e peça confirmação antes da Refatoração.
```

### Executar e validar as aplicações refatoradas

| Projeto | Runtime validado / pré-requisito | Instalação e configuração | Testes |
|---|---|---|---|
| Loja Flask | Python 3.14.7 validado | [README e migração de senhas](code-smells-project/README.md): venv, requirements, chave/SQLite, init-db e create-admin | `python -m unittest discover -s tests -v`; `python tests/smoke_http.py` |
| LMS Express | Node 24.22.0 validado; Node >=22 | [README e seed explícito](ecommerce-api-legacy/README.md): npm ci, ADMIN_TOKEN e seed opcional | `npm test`; `npm run test:http` |
| Tarefas Flask | Python 3.14.7 validado; Python >=3.11 | [README e reset das contas MD5](task-manager-api/README.md): venv, requirements-lock, chave/SQLite, init-db e create-admin | `python -W error::DeprecationWarning -m unittest discover -s tests -v`; `python tests/smoke_http.py` |

Execute cada comando na pasta indicada e no seu runtime/venv. Os READMEs contêm os blocos completos de instalação e boot. Nos projetos Python, finalize a preparação e inicie com `python app.py`; no Node, `npm start`. Os testes HTTP iniciam seus próprios processos e bancos descartáveis, exercitam caminhos autorizados e erros e encerram os processos. Eles precisam de permissão para abrir portas em loopback; o processo de tarefas admite até 60 segundos de prontidão devido ao DNS reverso observado no ambiente. Nenhum servidor previamente iniciado é necessário para os testes.
