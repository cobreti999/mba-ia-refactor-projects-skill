# code-smells-project

API de e-commerce em Flask e SQLite, refatorada para MVC.

## Executar

Execute na pasta `code-smells-project`, com Python (validado em 3.14.7):

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export APP_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
export APP_DATABASE="$PWD/loja.db"
python -m flask --app loja:create_app init-db
python -m flask --app loja:create_app create-admin
python app.py
```

O comando `create-admin` solicita nome, email e senha com confirmação oculta. Guarde a chave de ambiente para reutilizá-la: trocar a chave invalida tokens. O servidor inicia em `http://127.0.0.1:5000`, sem debug. Não existem usuários ou senhas de exemplo criados automaticamente. Importar a aplicação não inicializa o banco; execute `init-db` explicitamente.

[.env.example](.env.example) lista as variáveis. O arquivo não é carregado automaticamente: exporte os valores no ambiente. `APP_SECRET_KEY` exige ao menos 32 caracteres; `APP_TOKEN_MAX_AGE` define a validade do token em segundos (3600 por padrão); `APP_HOST` e `APP_PORT` configuram o servidor; `APP_CORS_ORIGINS` aceita origens separadas por vírgula. `APP_ALLOW_DB_RESET` é `false` por padrão.

## Banco existente e migração de senhas

Pare o servidor antigo e faça uma cópia de segurança do banco antes da migração. Aponte `APP_DATABASE` para o arquivo existente e execute:

```bash
python -m flask --app loja:create_app init-db
python -m flask --app loja:create_app migrate-passwords
```

`init-db` preserva registros e adiciona o marcador `senha_format` quando ausente. `migrate-passwords` converte senhas legadas em hashes scrypt do Werkzeug, em uma única transação, sem modificar IDs, papéis ou datas. Executá-lo novamente não reprocessa hashes. Uma senha legada inválida reverte toda a migração. Logins legados são rejeitados até a conversão; novos cadastros já armazenam hash. Nenhuma resposta inclui senha ou hash. Um backup anterior à conversão ainda contém as credenciais legadas.

## Contrato HTTP

Envie JSON e `Content-Type: application/json`. `POST /login` recebe `email` e `senha` e retorna os dados públicos, `token` e `expires_in`. Nas rotas protegidas envie `Authorization: Bearer <token>`. O cadastro público sempre cria cliente, mesmo quando recebe `tipo`.

| Método | Caminho | Acesso |
|---|---|---|
| GET | `/` | Público |
| GET | `/health` | Público, sem configuração interna |
| GET | `/produtos` | Público |
| GET | `/produtos/busca` | Público |
| GET | `/produtos/<id>` | Público |
| POST | `/produtos` | Admin |
| PUT | `/produtos/<id>` | Admin |
| DELETE | `/produtos/<id>` | Admin |
| GET | `/usuarios` | Admin |
| GET | `/usuarios/<id>` | Próprio usuário ou admin |
| POST | `/usuarios` | Público |
| POST | `/login` | Público |
| POST | `/pedidos` | Próprio usuário ou admin |
| GET | `/pedidos` | Admin |
| GET | `/pedidos/usuario/<usuario_id>` | Próprio usuário ou admin |
| PUT | `/pedidos/<pedido_id>/status` | Admin |
| GET | `/relatorios/vendas` | Admin |
| POST | `/admin/query` | Admin; somente `{"operacao":"contagens"}` |
| POST | `/admin/reset-db` | Admin e `APP_ALLOW_DB_RESET=true` |

SQL livre é rejeitado. O reset apaga as quatro tabelas e invalida as identidades removidas, sem recriar seeds. Quantidades devem ser inteiros positivos; produtos repetidos são consolidados antes da validação do estoque. POST e PUT de produtos usam as mesmas regras. Erros de entrada retornam 400, falta de autenticação 401, falta de permissão 403, recursos ausentes 404 e email duplicado 409. Falhas inesperadas retornam erro genérico com referência.

## Arquitetura

Antes: `app.py`, `controllers.py`, `models.py`, `database.py`, com negócio e SQL misturados e conexão global.

```text
app.py                  # inicialização do servidor
loja/
  __init__.py           # factory e composição
  config.py             # configuração externa
  routes.py             # 19 rotas e política de acesso
  controllers/          # adaptação HTTP e coordenação
  services/             # validação, contas, pedidos e descontos
  models/               # repositórios e SQL parametrizado
  views/serializers.py   # representações públicas JSON
  database.py           # schema, conexão e transações
  context.py            # dependências por contexto e fechamento
  http.py               # autenticação e erros centralizados
  cli.py                # inicialização, migração e administrador
```

Repositórios e serviços não importam Flask. Pedidos verificam estoque e gravam todos os efeitos na mesma transação. Listagens carregam pedidos e itens com duas consultas, independentemente do número de pedidos. A política de desconto e a representação monetária em ponto flutuante foram preservadas; cancelar pedido continua sem reposição automática de estoque.

## Validar

```bash
python -m unittest discover -s tests -v
python tests/smoke_http.py
```

Os testes usam bancos descartáveis. O segundo comando inicia um processo real em loopback, percorre os 19 endpoints e encerra o processo, emitindo evidência JSON sem credenciais. Requer permissão para abrir porta local. Dependências diretas foram fixadas nas versões usadas na validação, sem trocar Flask/Flask-Cors.

Resultados e rastreabilidade: [auditoria](../reports/audit-project-1.md), [baseline](../reports/baseline-project-1.json) e [HTTP final](../reports/validation-project-1.json).
