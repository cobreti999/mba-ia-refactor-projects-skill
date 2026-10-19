# task-manager-api

API de gestão de tarefas em Flask, Flask-SQLAlchemy e SQLite, refatorada para MVC. Os models e o schema original foram preservados; rotas, controllers, serviços, consultas e representações JSON têm responsabilidades separadas.

## Instalação e execução

Requer **Python >=3.11** devido ao SQLAlchemy 2.1 fixado. Ambiente validado: Python 3.14.7, Flask 3.0.0, Flask-SQLAlchemy 3.1.1, Flask-Cors 4.0.0, SQLAlchemy 2.1.5 e Werkzeug 3.1.9. Flask e Flask-SQLAlchemy mantêm as versões originais; as transitivas foram fixadas após resolver o manifesto original.

Na pasta `task-manager-api`:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
export TASK_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
export TASK_DATABASE="$PWD/instance/tasks.db"
python -m flask --app app:create_app init-db
python -m flask --app app:create_app create-admin
python app.py
```

`create-admin` solicita nome, email e senha com confirmação oculta. Nenhuma conta é criada automaticamente. Preserve a chave de ambiente entre execuções: trocá-la invalida os tokens. Servidor padrão: `http://127.0.0.1:5000`, sem debug/reloader. Importar `app` ou criar a factory não cria schema nem executa seed.

O `.env.example` documenta configuração; o código não carrega esse arquivo automaticamente. Exporte as variáveis:

| Variável | Regra |
|---|---|
| TASK_SECRET_KEY | Obrigatória, ao menos 32 caracteres; sem default secreto |
| TASK_DATABASE | Caminho do SQLite; default `instance/tasks.db` dentro deste projeto, compatível com o original |
| TASK_TOKEN_MAX_AGE | Inteiro positivo em segundos; default 3600 |
| TASK_HOST / TASK_PORT | Default 127.0.0.1 / 5000; porta 0 permite alocação pelo sistema |
| TASK_CORS_ORIGINS | Origens separadas por vírgula; default `*` |

`requirements.txt` lista imports/dependências diretas fixados; `requirements-lock.txt` fixa também as transitivas usadas na validação. Marshmallow, Requests e python-dotenv foram removidos por não terem consumidores.

## Banco existente e senhas MD5

Pare a aplicação antiga e faça uma cópia de segurança antes de mudar a aplicação sobre um banco existente. Aponte `TASK_DATABASE` para o arquivo correto. `init-db` cria apenas tabelas ausentes, sem apagar linhas e sem reescrever senhas. Não houve mudança de colunas que exija recriar o banco. Usuários, IDs, papéis, tarefas, categorias e datas são preservados.

As senhas MD5 **não autenticam na versão refatorada**. Não é possível recuperar a senha a partir desse hash. Redefina explicitamente cada credencial legada:

```bash
python -m flask --app app:create_app reset-password --user-id 1
```

O comando solicita uma nova senha com confirmação oculta. Ele altera somente a senha da conta indicada, aplica hash scrypt com salt aleatório e invalida seus tokens anteriores. Não use o hash MD5 como nova senha. Cadastros e trocas de senha pela API já usam derivação segura; nenhum endpoint retorna senha ou hash. Mantém-se o mínimo original de quatro caracteres, com limite de 128.

Para reversão, utilize a cópia de segurança com a aplicação correspondente: a versão antiga não autentica hashes novos. FKs SQLite são habilitadas nas novas conexões; dados históricos inválidos precisam de revisão própria, sem limpeza automática.

## Seed opcional

Em vez de criar administrador separadamente, após `init-db` você pode popular um **banco vazio**:

```bash
python -m flask --app app:create_app seed-demo
```

A senha é solicitada com confirmação e aplicada com salts independentes aos três usuários demonstrativos: `admin@example.test`, `user@example.test` e `manager@example.test`. São criadas quatro categorias e dez tarefas, em uma única transação. Não há senha padrão. Se qualquer tabela contiver dados, o seed recusa a operação preservando os registros; uma falha intermediária reverte tudo. `python seed.py` mantém uma entrada alternativa com a mesma regra e confirmação da senha.

## Autenticação e permissões

`POST /login` recebe `email` e `password`. Retorna a mensagem, `user` público, `token` assinado e `expires_in`. Nas rotas protegidas use `Authorization: Bearer <token>`. Não é JWT: o token usa a assinatura e expiração do ItsDangerous. Tokens antigos simulados são rejeitados. Estado ativo e papel são consultados em cada requisição; troca/reset de senha e exclusão invalidam os tokens da conta.

- **user:** conta e tarefas próprias; criação de tarefa sem responsável usa sua identidade. Não pode atribuir a outra pessoa nem remover seu responsável. Listagem, busca e estatísticas ficam limitadas às suas tarefas. Pode consultar categorias e seu relatório.
- **manager:** gerencia tarefas e categorias de toda a equipe e consulta usuários/relatórios. Não altera outras contas, papéis ou ativação e não exclui usuários.
- **admin:** gerencia contas, papéis e ativação, além das operações da equipe.

Cadastro público admite somente `role=user`. Para criar `manager` ou outro `admin` pelo mesmo `POST /users`, envie token de admin. Tentativas de atribuir privilégio sem autorização retornam 403.

| Método | Caminho | Acesso e resultado |
|---|---|---|
| GET | `/` | Público; identificação da API |
| GET | `/health` | Público; status/timestamp sem configuração interna |
| GET | `/tasks` | Autenticado; user limitado às próprias tarefas |
| POST | `/tasks` | Autenticado; 201; atribuição conforme papel |
| GET | `/tasks/<task_id>` | Responsável ou equipe privilegiada |
| PUT | `/tasks/<task_id>` | Responsável ou equipe privilegiada |
| DELETE | `/tasks/<task_id>` | Responsável ou equipe privilegiada; 200 |
| GET | `/tasks/search` | Mesmo escopo da listagem; filtros `q`, `status`, `priority`, `user_id` |
| GET | `/tasks/stats` | Estatísticas próprias ou de toda a equipe conforme papel |
| GET | `/users` | Admin/manager; inclui contagem de tarefas |
| POST | `/users` | Público para user; admin pode criar contas privilegiadas; 201 |
| GET | `/users/<user_id>` | Próprio usuário ou admin/manager; inclui tarefas |
| PUT | `/users/<user_id>` | Próprio usuário ou admin; role/active somente admin |
| DELETE | `/users/<user_id>` | Somente admin; remove também suas tarefas, atomicamente |
| GET | `/users/<user_id>/tasks` | Próprio usuário ou admin/manager |
| POST | `/login` | Público; credenciais válidas e usuário ativo |
| GET | `/reports/summary` | Admin/manager |
| GET | `/reports/user/<user_id>` | Próprio usuário ou admin/manager |
| GET | `/categories` | Autenticado; inclui contagem de tarefas, inclusive zero |
| POST | `/categories` | Admin/manager; 201 |
| PUT | `/categories/<cat_id>` | Admin/manager |
| DELETE | `/categories/<cat_id>` | Admin/manager; preserva tarefas e limpa category_id |

22 pares explícitos; HEAD/OPTIONS automáticos excluídos. Métodos e caminhos originais foram preservados. A regra de autorização, o token, a retirada do campo password e a inicialização/seed explícitos são deltas aprovados. Também foram padronizados os erros JSON: 400 entrada inválida, 401 ausência/token inválido, 403 permissão/usuário inativo no login, 404 recurso ausente, 409 email duplicado e 500 genérico com referência. Headers HTTP como Allow são preservados.

## Validação de dados e datas

POST/PUT compartilham regras: título 3–200, prioridade inteira 1–5, quatro status existentes, IDs positivos ou null quando a relação pode ser removida, datas `YYYY-MM-DD`, tags como texto separado por vírgulas ou lista de textos (até 500 caracteres armazenados). Nome de usuário/categoria até 100, email até 150, descrição de categoria até 300 e cor `#RRGGBB`. Booleanos não são aceitos como inteiros. Campos de texto não são convertidos silenciosamente. Nome/email não sofrem normalização nova.

O schema original guarda datas como UTC sem offset. O relógio usa `datetime.now(timezone.utc)` e normaliza para esse formato na fronteira, sem alterar datas existentes. Atraso tem uma definição: vencimento anterior ao instante atual e status diferente de done/cancelled. Os formatos distintos de tarefa em listagem, detalhe, busca e usuário foram mantidos; descrição omitida continua vazia, tags vazias continuam lista vazia na resposta.

## Estrutura

```text
app.py                    # factory e entrada do servidor
config.py                 # ambiente validado
cli.py / seed.py           # inicialização, contas e seed explícitos
database.py               # extensão SQLAlchemy contextual
models/                   # entidades e regra de atraso
routes/                   # caminhos, métodos e política de acesso
controllers/              # adaptação HTTP e composição da resposta
services/                 # contas, tarefas, categorias, relatórios, validação e seed
repositories/store.py     # consultas, relações e unidade de trabalho
views/serializers.py      # representações públicas e projeções
context.py                # composição de dependências por contexto
http_support.py           # autenticação e tradução central de erros
utils/clock.py            # relógio UTC compatível com o schema
utils/constants.py        # limites, status e defaults compartilhados
tests/                    # regressão e boot/HTTP real
```

Models, serviços e repositórios não importam Flask/request/response. A sessão continua gerenciada pelo contexto da extensão, sem introduzir conexão global compartilhada. Escritas confirmam ou revertem a unidade de trabalho inteira. Listagens usam joins/agregações e o relatório usa consultas em quantidade constante. O serviço SMTP inativo foi removido; nenhuma notificação externa é enviada.

## Testes

```bash
python -W error::DeprecationWarning -m unittest discover -s tests -v
python tests/smoke_http.py
# Para salvar a evidência HTTP:
python tests/smoke_http.py /tmp/validation-project-3.json
```

**Resultado verificado: 16 testes aprovados, 44 cenários HTTP e 22/22 endpoints.** A contagem de consultas permaneceu constante com 25 relações adicionais: duas por listagem e cinco no resumo, incluindo autenticação. O processo HTTP foi encerrado e os logs capturados não contêm os segredos de teste. O prazo de prontidão é de 60 segundos porque a resolução reversa de nome do servidor padrão do Python demorou neste ambiente.

Os testes usam bancos e credenciais descartáveis. O teste HTTP inicia `python app.py` em loopback/porta livre e encerra somente esse processo. Requer permissão para abrir porta local. Verifica respostas, papéis, negações, estado ativo e efeitos de criação/exclusão no SQLite; 401 sozinho não conta como endpoint validado.

- [Auditoria e rastreabilidade](../reports/audit-project-3.md)
- [Caracterização do original](../reports/baseline-project-3.json)
- [Validação HTTP e versões](../reports/validation-project-3.json)
- [Transcrição da suíte](../reports/regression-project-3.txt)

A validação é funcional e local. Não houve teste de carga, implantação ou envio de email, nem acesso a banco real do usuário.
