# Playbook de refatoração

Aplique apenas transformações relacionadas aos findings e ao escopo aprovado. Os trechos abaixo são exemplos locais antes/depois, não aplicações completas: colaboradores como `repository`, `hasher` e `unit_of_work` representam interfaces a implementar/adaptar à stack. Não copiar nomes ou APIs fictícias como se existissem no projeto. Valide a implementação real pelo [roteiro de validação](validation.md).

## T-01 — Parametrizar SQL (AP-01)

Antes — entrada altera o texto SQL:

```python
cursor.execute("SELECT id FROM users WHERE email = '" + email + "'")
```

Depois — exemplo com driver SQLite Python:

```python
cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
```

Use o mecanismo de binding do driver/ORM real. Parâmetros vinculados são valores, não nomes de tabela ou coluna: identificadores dinâmicos precisam de lista permitida. Endpoint que recebe SQL livre exige substituir a capacidade por operações aprovadas, não simplesmente parametrizar a string inteira. Verifique consultas com apóstrofos como dados e rejeição de operações não autorizadas em ambiente isolado.

## T-02 — Configuração e resposta sem segredos (AP-02)

Antes:

```python
SECRET_KEY = "segredo-fixo"

def health():
    return {"status": "ok", "secret_key": SECRET_KEY}
```

Depois:

```python
import os

def load_config():
    key = os.environ.get("APP_SECRET_KEY")
    if not key:
        raise RuntimeError("APP_SECRET_KEY é obrigatória")
    return {"SECRET_KEY": key}

def health():
    return {"status": "ok"}
```

Carregue configuração na composição e injete-a onde necessário. Omita senha, token e cartão de logs e serializadores; uma configuração externa não resolve vazamento em log. Verifique boot com configuração válida e falha clara quando ausente; confira ausência de campos sensíveis nas respostas. Planeje tratamento de credenciais antigas sem alegar que foram revogadas.

## T-03 — Hash de senha e representação pública (AP-03, AP-02)

Antes:

```python
import hashlib

def register(data, repository):
    password = hashlib.md5(data["password"].encode()).hexdigest()
    user = repository.create(data["email"], password)
    return {"id": user.id, "password": user.password}
```

Depois — `hasher` é um adaptador de biblioteca própria para senhas:

```python
def register(data, repository, hasher):
    password_hash = hasher.hash(data["password"])
    user = repository.create(data["email"], password_hash)
    return {"id": user.id, "email": user.email}

def authenticate(user, candidate, hasher):
    return hasher.verify(user.password, candidate)
```

Escolha implementação mantida e compatível com a stack, com salt e custo apropriados; não criar algoritmo próprio. Documente migração/redefinição de senhas antigas e campos públicos alterados. Verifique senha correta/incorreta e que cadastro, login e consultas nunca devolvem senha/hash.

## T-04 — Autorização na fronteira (AP-04)

Antes — exclusão direta:

```javascript
app.delete('/users/:id', (req, res) => {
  users.remove(req.params.id);
  res.sendStatus(204);
});
```

Depois — exemplo Express, com middlewares/adaptadores implementados no projeto:

```javascript
app.delete('/users/:id', authenticate, requireAdmin, async (req, res, next) => {
  try {
    await users.remove(req.params.id);
    res.sendStatus(204);
  } catch (error) {
    next(error);
  }
});
```

`authenticate` deve verificar identidade real, não apenas presença de token; `requireAdmin` deve usar identidade confiável, não o papel recebido no corpo. Para operações de usuário, aplicar autorização de propriedade quando exigida. Verifique 401 sem identidade, 403 sem permissão e sucesso autorizado; preserve o contrato de exclusão real ou documente a mudança aprovada. A ordem dos middlewares é parte da correção.

## T-05 — Extrair responsabilidades do módulo concentrador (AP-05, AP-06)

Antes:

```python
class AppManager:
    def checkout(self, request, connection):
        course_id = request.json["course_id"]
        course = connection.execute(
            "SELECT price FROM courses WHERE id = ?", (course_id,)
        ).fetchone()
        total = course[0]
        enrollment = connection.execute(
            "INSERT INTO enrollments(course_id) VALUES (?)", (course_id,)
        ).lastrowid
        connection.commit()
        return {"enrollment_id": enrollment, "total": total}
```

Depois — controller, caso de uso e repositório com responsabilidades distintas:

```python
class CheckoutService:
    def __init__(self, repository, unit_of_work):
        self.repository = repository
        self.unit_of_work = unit_of_work

    def execute(self, course_id):
        with self.unit_of_work():
            course = self.repository.require_course(course_id)
            enrollment_id = self.repository.enroll(course_id)
            return {"enrollment_id": enrollment_id, "total": course.price}

class CheckoutController:
    def __init__(self, service):
        self.service = service

    def create(self, data):
        return self.service.execute(data["course_id"])
```

A rota extrai a entrada validada, chama o controller e serializa a resposta. O repositório contém SQL; a unidade de trabalho garante commit/rollback; o serviço contém o caso de uso. O exemplo não contém pagamento real: preservar todas as etapas existentes ao extrair. Verifique ausência de imports HTTP no domínio e o fluxo completo com falhas intermediárias.

## T-06 — Substituir estado global por dependência com ciclo de vida (AP-07)

Antes:

```python
connection = open_connection()

def find_user(user_id):
    return connection.execute(
        "SELECT id FROM users WHERE id = ?", (user_id,)
    ).fetchone()
```

Depois:

```python
class UserRepository:
    def __init__(self, connection):
        self.connection = connection

    def find(self, user_id):
        return self.connection.execute(
            "SELECT id FROM users WHERE id = ?", (user_id,)
        ).fetchone()
```

O composition root/factory fornece uma conexão ou sessão do contexto da operação e encerra-a no ciclo de vida correto. Injetar a mesma conexão global não resolve o finding. Não substituir uma sessão contextual do ORM por gerenciamento manual sem necessidade. Testar isolamento entre operações e limpeza de recursos.

## T-07 — Tornar a escrita atômica (AP-08)

Antes — cada comando fica confirmado independentemente:

```python
connection.execute("INSERT INTO enrollments(course_id) VALUES (?)", (course_id,))
connection.commit()
connection.execute("INSERT INTO payments(amount) VALUES (?)", (amount,))
connection.commit()
```

Depois — SQLite Python, conexão em modo transacional, sem autocommit:

```python
with connection:
    connection.execute("INSERT INTO enrollments(course_id) VALUES (?)", (course_id,))
    connection.execute("INSERT INTO payments(amount) VALUES (?)", (amount,))
```

O contexto confirma ou reverte a transação, mas não fecha a conexão ([documentação SQLite Python](https://docs.python.org/3/library/sqlite3.html#how-to-use-the-connection-context-manager)). Verifique o modo real do driver: em autocommit esse exemplo não cria a garantia desejada. Inclua chaves e vínculos reais da aplicação; não omita auditoria necessária. No Node.js, adapte `BEGIN/COMMIT/ROLLBACK` com tratamento assíncrono e conexão exclusiva por unidade de trabalho, sem intercalar transações concorrentes. Injetar falha na segunda gravação deve deixar ambas ausentes. Efeitos externos exigem compensação/idempotência conforme o caso aprovado.

## T-08 — Eliminar N+1 preservando relações vazias (AP-09)

Antes:

```python
categories = connection.execute("SELECT id, name FROM categories").fetchall()
result = []
for category in categories:
    count = connection.execute(
        "SELECT COUNT(*) FROM tasks WHERE category_id = ?", (category[0],)
    ).fetchone()[0]
    result.append((category[0], category[1], count))
```

Depois:

```python
result = connection.execute("""
    SELECT c.id, c.name, COUNT(t.id)
    FROM categories c
    LEFT JOIN tasks t ON t.category_id = c.id
    GROUP BY c.id, c.name
""").fetchall()
```

Adapte a representação ao contrato original. Para listas aninhadas, usar carregamento em lote/eager loading e reconstruir a estrutura em memória pode ser melhor que um join com duplicação de linhas. Verifique categoria sem tarefas, múltiplas relações, resultados equivalentes e número de consultas que não cresce por entidade. Não alegar ganho de performance apenas pela mudança de SQL.

## T-09 — Centralizar validação e regra compartilhada (AP-10, AP-11, AP-14)

Antes — criação e atualização divergem:

```python
def validate_create(data):
    return 3 <= len(data["title"]) <= 200

def validate_update(data):
    return len(data["title"]) <= 200
```

Depois:

```python
MIN_TITLE_LENGTH = 3
MAX_TITLE_LENGTH = 200

def validate_title(value):
    if not isinstance(value, str):
        raise ValueError("Título deve ser texto")
    if not MIN_TITLE_LENGTH <= len(value) <= MAX_TITLE_LENGTH:
        raise ValueError("Comprimento de título inválido")
    return value

def validate_create(data):
    return {"title": validate_title(data.get("title"))}

def validate_update(data):
    return {"title": validate_title(data["title"])} if "title" in data else {}
```

Valide também a forma do corpo antes de acessar chaves. Na integração, use erro de validação específico mapeado para 400; não converta todo `ValueError` da aplicação em erro de cliente. Preserve semântica de campos opcionais e não aplique trim/coerção silenciosa sem contrato aprovado. Verifique tipos, limites, omissões e igualdade da regra nos fluxos.

## T-10 — Propagar e traduzir erros em um ponto (AP-12)

Antes:

```javascript
app.get('/courses', (req, res) => {
  repository.list((err, rows) => res.json(rows));
});
```

Depois — repositório mantém API callback neste exemplo:

```javascript
app.get('/courses', (req, res, next) => {
  repository.list((err, rows) => {
    if (err) return next(err);
    return res.json(rows);
  });
});

app.use((err, req, res, next) => {
  if (res.headersSent) return next(err);
  logger.error({ code: 'COURSES_READ_FAILED' });
  return res.status(500).json({ error: 'Erro interno' });
});
```

Instale o middleware de erro depois das rotas e mantenha o callback de quatro argumentos exigido pelo Express ([documentação oficial](https://expressjs.com/en/guide/error-handling/)). Acrescente mapeamento explícito dos erros de domínio, inclusive 400/404/409 conforme o contrato; não responder 500 para todo erro conhecido. Use logging estruturado sem credenciais, preservando diagnóstico útil. Verifique erro inesperado, erro de domínio, rollback e ausência de dupla resposta.

## T-11 — Migrar API obsoleta com equivalência (AP-13)

Antes — consulta ORM:

```python
user = User.query.get(user_id)
```

Depois — SQLAlchemy com sessão compatível:

```python
user = db.session.get(User, user_id)
```

Confirme versão e identidade do símbolo como exige o catálogo. Preserve `None` quando não existe entidade e o tratamento HTTP que o controller fazia. Testar entidade existente/ausente e sessão correta; não atualizar dependências sem necessidade aprovada. Para outras APIs, registrar versão, equivalente e mudança semântica antes da substituição. Ver [fonte oficial](https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html#sqlalchemy.orm.Query.get).

## T-12 — Remover ruído e nomear política (AP-14, AP-15, AP-16)

Antes:

```python
import math

def calc(x):
    return x * 0.1 if x > 10000 else 0
```

Depois:

```python
DISCOUNT_THRESHOLD = 10000
DISCOUNT_RATE = 0.1

def calculate_discount(revenue):
    return revenue * DISCOUNT_RATE if revenue > DISCOUNT_THRESHOLD else 0
```

Atualize consumidores ao renomear símbolos internos. Preserve API pública ou use adaptação aprovada; não remover imports com efeitos de registro. Para políticas com várias faixas, preserve todas as faixas e a ordem. Verifique os limites (abaixo, igual e acima) e pesquise consumidores do código removido.

## Ordem de aplicação

A ordem depende do plano aprovado: caracterizar contratos e preparar isolamento; criar composição/configuração; extrair responsabilidades; corrigir persistência, regras, segurança e erros; limpar código residual; executar a validação completa. Uma extração deve manter comportamento até a correção correspondente estar pronta. Não criar uma arquitetura alternativa nem reescrever a stack para facilitar a transformação.
