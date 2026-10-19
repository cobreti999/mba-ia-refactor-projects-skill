# Auditoria e resultado — Projeto 1

## Contexto e aprovação

Alvo: `code-smells-project`. Base auditada: `6d1ce6248c3e956801010a89d8bdaab48029bf30`. Data: 19/10/2026. Análise original: quatro arquivos Python, 780 linhas, 19 pares método/caminho, Flask 3.1.1, Flask-Cors 5.0.1 e SQLite. Fontes, manifesto e README foram lidos. As evidências abaixo referem-se à base original, antes das alterações.

A auditoria foi apresentada na conversa após a Análise aprovada. A resposta **“ok, prossiga”** autorizou salvar este relatório e executar a proposta de Fase 3 do projeto 1. A implementação da skill e a análise manual já eram alterações locais anteriores. Esta entrega encerra somente a execução no projeto 1.

## Achados originais

| ID | Severidade | Padrão | Achado | Evidência original | Impacto |
|---|---|---|---|---|---|
| F001 | CRITICAL | AP01 | SQL Injection | `models.py:105–111,285–299; controllers.py:111–123,167–176` | Entrada externa altera SQL de autenticação e busca. |
| F002 | CRITICAL | AP04 | Ausência de autorização | `app.py:47–78; controllers.py:167–183` | SQL arbitrário e reset disponíveis a qualquer cliente. |
| F003 | CRITICAL | AP03/AP02 | Senhas em texto puro e respostas | `models.py:79–85,95–101,122–130; controllers.py:128–144` | Leitura da API revela credenciais reutilizáveis. |
| F004 | CRITICAL | AP02 | Segredo embutido e exposto | `app.py:7–8; controllers.py:285–289` | Configuração retornada facilita abuso de credenciais e expõe detalhes internos. |
| F005 | HIGH | AP06 | Mistura de responsabilidades | `models.py:139–168,239–272; app.py:49–55,66–76` | SQL, HTTP e negócio acoplados dificultam mudanças e testes. |
| F006 | HIGH | AP07 | Conexão global mutável | `database.py:4–12` | Requisições compartilham estado transacional. |
| F007 | HIGH | AP08 | Rollback ausente | `models.py:148–168; controllers.py:218–220` | Falha intermediária pode deixar alterações parciais e contaminar operação seguinte. |
| F008 | HIGH | AP10 | Quantidade e duplicatas inconsistentes | `models.py:139–146,154–165` | Quantidades não positivas ou repetidas corrompem estoque/total. |
| F009 | MEDIUM | AP09 | N+1 em pedidos | `models.py:174–192,206–224` | Custo cresce com pedidos e seus itens. |
| F010 | MEDIUM | AP10/AP11 | Validação divergente | `controllers.py:28–54,72–90,118–126` | PUT aceita entradas rejeitadas no POST e conversões inválidas geram 500. |
| F011 | MEDIUM | AP12 | Erros internos expostos | `controllers.py:10–12,60–62,185–186; app.py:77–78` | Mensagens de exceção revelam detalhes da implementação. |
| F012 | MEDIUM | AP11 | Serialização duplicada | `models.py:12–20,31–39,304–312` | Respostas podem divergir entre consulta, busca e listagem. |
| F013 | LOW | AP14 | Limites mágicos de desconto | `models.py:256–262` | Política difícil de revisar e alterar. |
| F014 | LOW | AP16 | Imports sem uso | `database.py:2; models.py:2` | Dependências aparentes e ruído na leitura. |

Totais: **4 CRITICAL, 4 HIGH, 4 MEDIUM, 2 LOW = 14**. Severidades refletem exposição de acesso/credenciais, risco de corrupção de dados, custo de manutenção/desempenho e ruído localizado, respectivamente.

## Cobertura e comparação

AP01–AP04 e AP06–AP12, AP14 e AP16 encontrados conforme tabela. AP05: nenhuma God Class integral confirmada; mistura de responsabilidades registrada em AP06. AP15: nenhuma ocorrência adicional relevante confirmada. AP13: nenhuma depreciação confirmada; ausência de achado não comprova compatibilidade com todas as versões.

Para APIs, a versão de Python não estava declarada na auditoria. A [documentação oficial do Flask 3.1](https://flask.palletsprojects.com/en/stable/api/) não indicou remoção dos símbolos usados; a [documentação do Flask-Cors](https://flask-cors.readthedocs.io/en/latest/) consultada correspondia a 3.0.10, insuficiente para concluir sobre a versão 5.0.1 declarada. Consulta em 19/10/2026. Nenhuma migração de API foi inventada a partir dessa lacuna. A validação dinâmica posterior usou Python 3.14.7 e as versões registradas no JSON final; não é certificação de outras versões.

Correspondências com análise manual: P1-01→F001, P1-02→F002, P1-03→F003, P1-04→F006, P1-05→F005, P1-06→F009, P1-07→F010, P1-08→F013, P1-09→F014. **9/9 correspondências**; a auditoria acrescentou exposição de segredo, rollback, quantidades, erros e serialização. Os mínimos do desafio foram atendidos.

## Proposta aprovada e contratos

Manter Flask/SQLite, separar rotas, controllers, serviços, repositórios e serializadores, com configuração externa e erros centralizados. Corrigir os 14 achados com as transformações e verificações da tabela de resultado.

- Login passa a emitir token assinado com expiração. Leitura de produtos, cadastro, login, raiz e health públicos; operações administrativas exigem admin; recursos individuais exigem titular ou admin.
- Senhas passam a hash e deixam as respostas. Migração explícita preserva registros; credenciais antigas precisam ser migradas antes do login.
- Health deixa de retornar configuração interna. SQL livre é substituído por `{"operacao":"contagens"}` em `/admin/query`.
- Reset exige admin e opção de ambiente habilitada, desabilitada por padrão.
- Entradas válidas preservadas; entradas inválidas passam por validação central. Quantidades positivas e produtos duplicados consolidados. Nenhum banco real é usado nos testes.

## Resultado da Fase 3

Todos os 14 achados foram corrigidos no escopo aprovado. Caminhos abaixo são relativos a `code-smells-project/loja/`; o comportamento original permanece documentado acima.

| ID | Estado | Implementação | Evidência/validação |
|---|---|---|---|
| F001 | Corrigido | `models/products.py; models/users.py` | Parametrização; regressão de login e busca com payload SQL. |
| F002 | Corrigido | `routes.py; http.py; controllers/system.py` | Tokens, papéis e propriedade; testes 401/403, SQL livre rejeitado e reset opt-in. |
| F003 | Corrigido | `services/accounts.py; views/serializers.py; cli.py` | Hash, resposta pública e migração explícita; testes de idempotência, atomicidade e preservação. |
| F004 | Corrigido | `config.py; controllers/system.py; app.py` | Chave obrigatória externa, health reduzido, debug desligado; testes de configuração/health. |
| F005 | Corrigido | `services/; models/; controllers/; routes.py` | Separação MVC; revisão de imports e testes dos fluxos completos. |
| F006 | Corrigido | `context.py; database.py` | Conexão por contexto, fechamento no teardown; regressões de isolamento/fechamento e concorrência. |
| F007 | Corrigido | `database.py; services/orders.py` | Transação explícita; falha injetada após baixa de estoque verifica rollback e próximo pedido. |
| F008 | Corrigido | `services/validation.py; services/orders.py` | Inteiros positivos, consolidação e trava transacional; teste de duas compras concorrentes. |
| F009 | Corrigido | `models/orders.py` | Carga em lote; teste confirma duas consultas com um e cinco pedidos e produto removido. |
| F010 | Corrigido | `services/validation.py; controllers/products.py` | Mesmas regras e tipos/valores finitos; testes POST/PUT e filtros inválidos. |
| F011 | Corrigido | `http.py; errors.py` | Tratamento central; testes de erros HTTP e falha inesperada sem detalhes internos. |
| F012 | Corrigido | `views/serializers.py` | Representação única; teste compara produto nos diferentes endpoints. |
| F013 | Corrigido | `services/reports.py` | Faixas nomeadas; testes nas fronteiras preservam comparações estritas. |
| F014 | Corrigido | `database.py; models/` | Remoção junto à extração; revisão estática e importação pelos testes. |

## Estrutura e validação

Antes: quatro módulos com regras, SQL e HTTP misturados. Depois: factory/composição, rotas declarativas, controllers HTTP, serviços de negócio, repositórios, serializadores e contexto SQLite por requisição. A árvore e a matriz de acesso dos 19 endpoints estão no [README da aplicação](../code-smells-project/README.md).

| Verificação | Resultado | Evidência |
|---|---|---|
| Caracterização do original isolado com test client | 19 endpoints positivos | [baseline-project-1.json](baseline-project-1.json) |
| `python -m unittest discover -s tests -v` na pasta do projeto | 12 testes aprovados | [test_app.py](../code-smells-project/tests/test_app.py) |
| `python tests/smoke_http.py` na pasta do projeto | Boot real, 19/19 pares, payloads e efeitos no banco conferidos | [validation-project-1.json](validation-project-1.json) |
| Processo HTTP | Pronto em 127.0.0.1:63794; encerrado após teste | Log sanitizado no JSON final |

O teste HTTP inclui os fluxos autorizados de CRUD, cadastro/login, pedidos/status, relatório, contagens e reset, além de rejeições 401/403/400. [smoke_http.py](../code-smells-project/tests/smoke_http.py) contém os dados sintéticos, expectativas e verificações de persistência; o JSON registra status esperado/observado por requisição e chaves retornadas, sem tokens ou senhas. A primeira tentativa de bind foi impedida pelo sandbox; a execução com permissão para loopback passou. Não houve falha funcional nessa tentativa.

- [x] Responsabilidades MVC e dependências revisadas.
- [x] Configuração externa, sem chave embutida; erros centralizados.
- [x] Boot real sem debug e todos os endpoints exercitados.
- [x] Regressões de segurança, transação, concorrência, migração e N+1 verificadas.
- [x] Contratos e comandos de migração documentados.
- [x] Banco descartável e processo encerrado; nenhum banco do usuário alterado.

Limites: validação local com SQLite e servidor de desenvolvimento Flask; não foi realizado teste de carga nem implantação. Valores monetários continuam em ponto flutuante e cancelamento não repõe estoque, preservando a regra original. As versões adicionais fixadas no manifesto eram dependências transitivas já instaladas e agora importadas diretamente. Os projetos 2 e 3 aguardam suas próprias fases e aprovações.
