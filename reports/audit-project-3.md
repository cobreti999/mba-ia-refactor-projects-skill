# Auditoria arquitetural — Projeto 3

Projeto: `task-manager-api`. Base: `ecc6ca0b5e6bbd4c48effdba8108f0cc7b1626bc`. Data: 19/10/2026.

## Contexto e análise

15 fontes Python/1.158 linhas integralmente lidos; quatro inicializadores incluídos, zero testes, README e requirements examinados. Skills, bancos e caches excluídos. Domínio: tarefas, usuários, categorias e produtividade. Flask 3.0.0, Flask-SQLAlchemy 3.1.1 e Flask-Cors 4.0.0 declarados; SQLAlchemy transitivo sem lock. Marshmallow, Requests e python-dotenv declarados e sem uso identificado. Python não fixado. Banco SQLite em arquivo (`instance/tasks.db` pela configuração original); models com três tabelas e relações opcionais de tarefa. Arquitetura parcialmente separada: rotas implementam consultas, regras e transações. Factory ausente; importar app cria schema. Serviço SMTP não chamado; validade externa das credenciais de exemplo não verificada.

22 pares explícitos, excluindo HEAD/OPTIONS e static: GET / e /health; GET/POST /tasks; GET/PUT/DELETE /tasks/<id>; GET /tasks/search e /tasks/stats; GET/POST /users; GET/PUT/DELETE /users/<id>; GET /users/<id>/tasks; POST /login; GET /reports/summary e /reports/user/<id>; GET/POST /categories; PUT/DELETE /categories/<id>. Comandos originais: pip install -r requirements.txt, python seed.py, python app.py. Não executados na auditoria; seed apaga dados. Análise e auditoria apresentadas na conversa em sequência.

Alterações locais anteriores: documentação e skill do projeto 1 fora deste escopo; cópia autorizada da skill no projeto 3. Fontes da aplicação intactas durante a auditoria. Evidências abaixo correspondem à versão original e permanecem preservadas após a refatoração.

## Resumo

2 CRITICAL, 3 HIGH, 5 MEDIUM, 2 LOW: **12 findings**. Mínimos do desafio atendidos. Auditoria estática; impactos e verificações futuras não são testes executados.

## Findings originais

### F-001 — [CRITICAL] Hash MD5 e exposição de credenciais

- Padrão: AP-02/AP-03.
- Evidência: `models/user.py:16–32; routes/user_routes.py:33–40,85–86,129,208–211` (relativa ao alvo).
- Impacto/justificativa: MD5 facilita tentativas offline e a representação pública expõe o hash.
- Recomendação: Derivação de senha, serialização pública e redefinição explícita para credenciais antigas.
- Verificação prevista: Hash/salt, senha correta/incorreta, ausência de password em todas as respostas e preservação do usuário após redefinição.

### F-002 — [CRITICAL] Identidade e autorização ausentes

- Padrão: AP-04.
- Evidência: `routes/user_routes.py:71–78,119–125,134–148,185–211; app.py:18–20` (relativa ao alvo).
- Impacto/justificativa: Papel vem do cliente, token não é verificado e operações destrutivas não exigem identidade.
- Recomendação: Token assinado com expiração, papel atual e propriedade.
- Verificação prevista: 401/403, token adulterado/expirado, inativo, papéis e acesso cruzado.

### F-003 — [HIGH] Configuração insegura de execução

- Padrão: AP-02/configuração.
- Evidência: `app.py:13,33–34` (relativa ao alvo).
- Impacto/justificativa: Chave fixa e debug em todas as interfaces podem expor configuração e debugger.
- Recomendação: Segredo externo obrigatório, debug/reloader desligados e loopback por padrão.
- Verificação prevista: Falha clara sem chave, boot configurado e health sem configuração.

### F-004 — [HIGH] Casos de uso e persistência nos handlers

- Padrão: AP-06.
- Evidência: `routes/task_routes.py:85–154; routes/report_routes.py:15–101; app.py:30–31` (relativa ao alvo).
- Impacto/justificativa: Consultas, regras, transações e schema ao importar prejudicam isolamento e testes.
- Recomendação: Manter models; extrair controllers, serviços, repositórios, serializadores e factory sem efeitos.
- Verificação prevista: Imports/camadas, import sem banco e regressões de todos os fluxos.

### F-005 — [HIGH] Seed destrutivo e parcial

- Padrão: AP-08.
- Evidência: `seed.py:11–14,37,63,92` (relativa ao alvo).
- Impacto/justificativa: Exclusão é confirmada antes da carga: falha posterior deixa banco vazio/parcial.
- Recomendação: Seed explícito somente em banco vazio e em uma única transação.
- Verificação prevista: Recusa sobre banco preenchido e rollback de falha intermediária.

### F-006 — [MEDIUM] Consultas por registro

- Padrão: AP-09.
- Evidência: `routes/report_routes.py:53–67,157–164; routes/user_routes.py:12–22; routes/task_routes.py:14–57` (relativa ao alvo).
- Impacto/justificativa: Contagens/lazy loading nos loops crescem com usuários, categorias ou relações distintas.
- Recomendação: Agregação e carregamento em lote.
- Verificação prevista: Contar consultas com cardinalidades diferentes; incluir categorias/usuários vazios e tarefas sem relações.

### F-007 — [MEDIUM] Validação inconsistente

- Padrão: AP-10.
- Evidência: `routes/task_routes.py:92–114,166–184,260–264; routes/user_routes.py:49–65,102–125; routes/report_routes.py:169–202` (relativa ao alvo).
- Impacto/justificativa: Tipos inválidos chegam a len, int, comparações, join e ao banco, podendo causar 500 ou dados inválidos.
- Recomendação: Validadores compartilhados antes de mutar entidades.
- Verificação prevista: POST/PUT, tipos/bool/null/listas, limites, filtros, datas e erros 400.

### F-008 — [MEDIUM] Regra de atraso e representação duplicadas

- Padrão: AP-11.
- Evidência: `models/task.py:23–60; routes/task_routes.py:17–39,69–80; routes/user_routes.py:162–180` (relativa ao alvo).
- Impacto/justificativa: Mesma regra pode divergir entre listagem, detalhe, usuário e relatórios.
- Recomendação: Uma regra com relógio UTC e serializadores com projeções explícitas.
- Verificação prevista: Datas antes/iguais/depois do instante, status finais, payloads e relatórios.

### F-009 — [MEDIUM] Erros dispersos e diagnóstico inseguro

- Padrão: AP-12.
- Evidência: `routes/task_routes.py:62–63,151–154; routes/user_routes.py:87–90,130–132` (relativa ao alvo).
- Impacto/justificativa: Capturas genéricas sem referência consistente e mensagens brutas de drivers em logs.
- Recomendação: Tradução HTTP central, rollback e log seguro por referência.
- Verificação prevista: Falhas injetadas, erros HTTP e ausência de entrada/SQL/credenciais nos logs.

### F-010 — [MEDIUM] Uso de Query.get legacy/deprecated

- Padrão: AP-13.
- Evidência: `routes/task_routes.py:42,51,67,117,122,158,188,195,227; routes/user_routes.py:29,94,136,155; routes/report_routes.py:105,192,213` (relativa ao alvo).
- Impacto/justificativa: 16 chamadas dependem da interface deprecated do SQLAlchemy >=2.0.
- Recomendação: session.get(Model,id), select e execute/scalars.
- Verificação prevista: Objeto existente/ausente, 404 preservado e deprecations da aplicação como erro.

### F-011 — [LOW] Imports e dependências sem uso

- Padrão: AP-16.
- Evidência: `routes/task_routes.py:7; utils/helpers.py:3–7; requirements.txt:4–6; services/notification_service.py:4–48` (relativa ao alvo).
- Impacto/justificativa: Dependências aparentes e serviço SMTP sem consumidor identificado acrescentam ruído.
- Recomendação: Remover imports/dependências e serviço inativo, sem ativar integração externa.
- Verificação prevista: Busca de consumidores, importação, testes e manifesto mínimo reproduzível.

### F-012 — [LOW] Limites desconectados das constantes

- Padrão: AP-14.
- Evidência: `routes/task_routes.py:96–100,166–170; utils/helpers.py:112–113` (relativa ao alvo).
- Impacto/justificativa: Os literais ignoram os limites já nomeados e exigem múltiplas mudanças.
- Recomendação: Fonte única para limites, status e valores padrão, sem mudar seus valores.
- Verificação prevista: Fronteiras de título, prioridade e senha nos fluxos de criação/atualização.

## APIs e fontes oficiais

Consultadas em 19/10/2026. Flask-SQLAlchemy 3.1.1 exige SQLAlchemy >=2.0.16 (https://raw.githubusercontent.com/pallets-eco/flask-sqlalchemy/3.1.1/pyproject.toml). Query.get é deprecated/legacy desde SQLAlchemy 2.0, ainda suportado, não removido; usar Session.get preservando retorno None e 404 (https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html#sqlalchemy.orm.Query.get). Interface de queries: https://flask-sqlalchemy.palletsprojects.com/en/3.1.x/legacy-query/ . A versão resolvida/em execução seria confirmada na Fase 3; nenhuma versão exata foi inventada na auditoria.

datetime.utcnow aparece em models/rotas/helpers/seed. Deprecated desde Python 3.12 (https://docs.python.org/3.12/library/datetime.html#datetime.datetime.utcnow); como o runtime não estava estabelecido, candidato condicionado fora dos totais. O equivalente now(timezone.utc) exige normalização compatível com datas naive UTC já armazenadas; não converter datas antigas para horário local. Risco de debugger: https://flask.palletsprojects.com/en/stable/debugging/ .

## Cobertura do catálogo e comparação

Encontrados: AP-02/03→F-001/F-003, AP-04→F-002, AP-06→F-004, AP-08→F-005, AP-09→F-006, AP-10→F-007, AP-11→F-008, AP-12→F-009, AP-13→F-010, AP-14→F-012, AP-16→F-011. Sem evidência adicional: AP-01 (expressões ORM vinculam valores), AP-05 (separação parcial, não God Class integral), AP-07 (db é extensão com sessão contextual, não conexão global), AP-15 (nenhuma ambiguidade adicional relevante confirmada). N+1 em query.get depende também do mapa de identidade; não afirmar uma consulta por chamada sem medir. SMTP está inativo, não comprova envio/vazamento externo.

Comparação posterior à inspeção: P3-01→F-001, P3-02→F-002, P3-03→F-004, P3-04→F-006, P3-05→F-007, P3-06→F-008, P3-07→F-011, P3-08→F-012. **8/8 correspondências**. Achados adicionais: configuração, seed parcial, erros e API legacy.

## Proposta e deltas aprovados

Manter Flask, Flask-SQLAlchemy, SQLite e os models úteis. Separar rotas/controller, serviços, repositórios e views JSON; configuração externa e erros centrais. Todos os findings da tabela fazem parte do escopo e serão ligados a testes/arquivos finais.

- Raiz, health, login e cadastro públicos. Demais recursos autenticados por token assinado com expiração; usuário ativo e papel atual verificados.
- user: conta, tarefas e relatório próprios; manager: tarefas/categorias e leituras/relatórios da equipe; admin: permissões adicionais para papéis, ativação e exclusão de usuários.
- Cadastro público apenas user; criação privilegiada pelo admin autenticado ou CLI. Usuário comum não reassocia tarefa a outra pessoa nem remove seu responsável.
- Hashes MD5 deixam de autenticar; redefinição explícita por CLI preserva IDs, usuários e tarefas. Não converter hash em senha. Remover password das respostas; novo hash próprio para senhas.
- Exclusão de usuário pelo admin remove suas tarefas atomicamente, como antes. Excluir categoria desvincula tarefas e as preserva.
- Import sem criação de schema; inicialização explícita e não destrutiva. Seed somente em banco vazio e transação única. Nenhum banco do usuário será usado nos testes.
- Erros JSON consistentes, valores/tipos inválidos rejeitados; limites de domínio existentes mantidos. Representações válidas e diferenças legítimas entre endpoints preservadas. Datas persistidas como naive UTC compatíveis com o banco original.
- Remover imports/dependências/serviço SMTP sem consumidores; não implementar notificações ou enviar mensagens externas.

Validar original isolado; suíte de regressão, permissões/propriedade, senhas/reset, falhas/rollback, contagem de consultas e datas. Boot real e todos os 22 endpoints com efeitos no banco temporário, processos encerrados e logs sanitizados. Salvar baseline/validação, atualizar documentação e realizar commit local apenas do escopo aprovado. Sem push/PR/publicação.

## Aprovação e estado

A resposta real **“prossiga”** do usuário, após a proposta completa na conversa, autoriza salvar `reports/audit-project-3.md`, executar a Fase 3 conforme os deltas, validar e criar commit local. Não autoriza alterações em outros projetos. Relatório salvo após essa aprovação; refatoração concluída e resultados acrescentados abaixo sem apagar achados originais.

## Resultado da Fase 3

Concluída no escopo aprovado. A aprovação aplicada foi a resposta real “prossiga” nesta conversa. Relatório original mantido acima; códigos de achados e severidades não foram reescritos para esconder a evolução.

### Estrutura antes/depois

Antes: 15 fontes/1.158 linhas, models úteis e rotas com regras, SQL e transações. Depois: models/schema preservados; rotas finas; controllers, serviços, repositório, views JSON, contexto, configuração, autenticação/erros, CLI e relógio/constantes separados. Não foi trocado o ORM/motor. O serviço SMTP sem consumidores foi removido; nenhuma integração foi ativada.

### Rastreabilidade final

| Finding | Estado | Implementação (relativa ao projeto) | Verificação |
|---|---|---|---|
| F-001 | Corrigido | `models/user.py:16; views/serializers.py:4; cli.py:32` | Scrypt com salts distintos, ausência de password nas respostas, MD5 rejeitado; reset preserva conta/tarefas e invalida tokens. |
| F-002 | Corrigido | `http_support.py:37; routes/; services/tasks.py:9` | Token adulterado/expirado, usuário inativo, papéis atuais, cadastro privilegiado, acesso cruzado e reassociação indevida. |
| F-003 | Corrigido | `config.py:5; app.py:41` | Falha sem chave ou TTL válido; loopback e debug off confirmados no boot real; health sem configuração. |
| F-004 | Corrigido | `app.py:19; controllers/; services/; repositories/; views/` | Import sem criação de banco/listener; factory sem schema automático; fontes revisadas e 22 endpoints exercitados. |
| F-005 | Corrigido | `services/seeding.py:9; cli.py:43` | Seed recusa banco preenchido; falhas após gravação de usuário, categoria e tarefa revertem as três tabelas. |
| F-006 | Corrigido | `repositories/store.py:37; repositories/store.py:49; services/reports.py:30` | Contagem real antes/depois de 25 relações adicionais: tasks/users/categories 2 SELECTs e summary 5, incluindo autenticação. Entidades vazias preservadas. |
| F-007 | Corrigido | `services/validation.py:8; services/validation.py:59` | POST/PUT, datas, tags, booleans, filtros e IDs extremos; rejeição antes de mutações; defaults de descrição preservados. |
| F-008 | Corrigido | `models/task.py:22; views/serializers.py:9; utils/clock.py:4` | Antes/igual/depois do instante, status finais, payloads distintos e estatísticas consistentes; UTC naive mantido. |
| F-009 | Corrigido | `http_support.py:73; repositories/store.py:8` | Falhas injetadas com referência, logs sem entrada sensível, HTTP JSON/Allow e rollback; operação seguinte funciona. |
| F-010 | Corrigido | `repositories/store.py:23; repositories/store.py` | 16 chamadas originais Query.get eliminadas; session.get/select em SQLAlchemy 2.1.5, 404 e testes com DeprecationWarning como erro. |
| F-011 | Corrigido | `requirements.txt; requirements-lock.txt; controllers/; services/` | Manifesto mínimo reproduzido em venv limpo; imports/consumidores revisados; helpers mortos e SMTP inativo removidos. |
| F-012 | Corrigido | `utils/constants.py; services/validation.py:59; models/task.py` | Constantes usadas nas regras e no limite do model; testes de limites preservam título 3–200, prioridade 1–5 e mínimo de senha 4. |

### Validação efetivamente executada

| Comando/cenário | Esperado | Observado | Artefato |
|---|---|---|---|
| Cópia isolada do original com Flask test client | Caracterizar os 22 pares | 22/22, incluindo exclusão de categoria que desvincula tarefas | baseline-project-3.json |
| Instalação em novo venv por requirements-lock.txt | Reproduzir dependências finais | Passou; pip check sem requisitos quebrados | versões em validation-project-3.json |
| python -W error::DeprecationWarning -m unittest discover -s tests -v | Regressões aprovadas | 16/16, zero falhas finais | regression-project-3.txt |
| python tests/smoke_http.py <evidence-path> | Boot real e 22 endpoints | 44 cenários, 22/22 pares, status e payloads verificados | validation-project-3.json |

A suíte foi repetida após os ajustes finais de defaults, em ambiente limpo. Os primeiros comandos de descoberta apontaram para a pasta de teste em nível incorreto; o caminho foi corrigido antes da execução real de 16 testes. Não eram falhas da aplicação. Os testes não apenas conferem estrutura: validam respostas, persistência, concorrência, falhas intermediárias, autorização e número de consultas.

O HTTP runner inicia **python app.py**, sem monkeypatch do servidor, em porta livre conhecida e banco temporário. Confere prontidão por HTTP e se o processo está vivo; o mesmo segredo sintético/banco configurado valida o login e os efeitos. PID/porta/log do processo estão no JSON. O sandbox impediu o primeiro bind; a execução autorizada passou. Houve espera na resolução reversa do sistema (`socket.getfqdn`, chamada por HTTPServer.server_bind); a janela de 15 segundos era insuficiente. Com 60 segundos, o processo original da aplicação iniciou e passou a matriz completa, sem alterar DNS/configuração do sistema ou a aplicação para contornar o problema. Processo encerrado ao terminar.

A matriz registra cada nome de cenário, método/caminho, status esperado/observado e chaves. O código tests/smoke_http.py contém as entradas e asserções de conteúdo/SQLite: criação e CRUD, relatórios, filtros, papéis, 401/403, inativo, campos inválidos, exclusão efetiva, cascata de tarefas ao excluir usuário e desvinculação ao excluir categoria. O baseline tem os formatos originais, inclusive o nome do campo password; nenhum valor de senha/hash/token foi incluído nele.

O runtime resolvido é Python 3.14.7, Flask 3.0.0, Flask-SQLAlchemy 3.1.1, Flask-Cors 4.0.0, SQLAlchemy 2.1.5, Werkzeug 3.1.9 e ItsDangerous 2.2.0. SQLAlchemy exige Python >=3.11, documentado. Não houve upgrade arbitrário: SQLAlchemy 2.1.5 foi a versão resolvida pelo manifesto original e então fixada. A pendência datetime.utcnow agora se aplica ao runtime verificado e foi resolvida com relógio moderno/normalização UTC compatível; não foi somada artificialmente como 13º finding.

### Checklist final

- [x] MVC e direção de imports revisados; models, serviços e repositórios sem imports de Flask/request/response.
- [x] Configuração externa, chave obrigatória e debug desligado.
- [x] Sem schema, seed ou listener ao importar; CLI explícito e seed não destrutivo.
- [x] Boot real e 22/22 endpoints com sucesso autorizado e efeitos nos dados.
- [x] Regressões dos 12 findings, queries constantes, rollback e concorrência.
- [x] Contratos, papéis, limites, reset de MD5 e comandos documentados no README do projeto.
- [x] Processo encerrado, dados descartáveis e logs sem segredos capturados.

Limitações: teste funcional local, sem carga/implantação. Não foi aberto ou alterado banco do usuário, nem redefinida senha real. Bancos existentes devem receber backup e reset explícito das credenciais MD5 antes do uso; init-db não limpa dados. Nenhuma chave histórica foi revogada contra serviços externos. O atraso de DNS do ambiente é registrado, não ocultado como sucesso da primeira tentativa. As evidências incluem hashes SHA-256 das fontes/testes/manifetos validados. Não há alegação de ausência universal de anti-patterns.
