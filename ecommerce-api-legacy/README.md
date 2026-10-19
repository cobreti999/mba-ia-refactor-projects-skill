# ecommerce-api-legacy

API demonstrativa de LMS com checkout de cursos, refatorada para MVC. Mantém JavaScript/CommonJS, Express 4 e SQLite **em memória**. Pagamento é uma simulação local: cartões sintéticos com prefixo `4` são aprovados; nenhum gateway é chamado.

## Instalação e boot

Requer **Node.js >=22**, recomendado Node 24. Ambiente validado: Node 24.22.0, npm 10.2.4, Express 4.22.1 e better-sqlite3 13.0.3 (SQLite 3.53.4). Node 20.11.1 foi usado somente para caracterizar o legado. A instalação global não foi alterada; a validação final usou Node 24 temporário.

```sh
npm ci
export ADMIN_TOKEN="$(node -e 'process.stdout.write(require("node:crypto").randomBytes(32).toString("hex"))')"
export SEED_PASSWORD="$(node -e 'process.stdout.write(require("node:crypto").randomBytes(16).toString("hex"))')"
export SEED_DEMO=true
npm start
```

Servidor em `127.0.0.1:3000`. `npm start` executa `node src/server.js`; evento JSON `ready` somente após schema/seed e listener concluídos. SIGINT/SIGTERM encerram servidor e banco. Importar `src/app.js` não abre banco, executa seed ou inicia servidor.

Variáveis não são carregadas automaticamente de `.env`; `.env.example` documenta nomes. Exporte-as no ambiente. Não imprima tokens/senhas nem use cartões reais nesta demonstração.

| Variável | Regra |
|---|---|
| ADMIN_TOKEN | Obrigatória; ao menos 32 caracteres sem espaços; sem default |
| HOST | Default 127.0.0.1 |
| PORT | 0–65535; default 3000; 0 escolhe porta livre |
| SEED_DEMO | true/false; default false |
| SEED_PASSWORD | Obrigatória com seed; 8–128 caracteres |

Seed explícito cria `demo@example.test`, dois cursos, uma matrícula e um pagamento. A senha é derivada com salt aleatório; sem senha fixa. Sem seed, o schema começa vazio. Não existem rotas de gestão de cursos. Dados se perdem ao encerrar o processo.

## Arquitetura

Antes: três fontes; AppManager concentrava banco, schema, seed, HTTP, checkout, relatório e exclusão. utils misturava configuração, pseudo-hash e cache global.

```text
src/
├── app.js                    # composição/factory sem efeitos ao importar
├── server.js                 # boot, prontidão, listener e limpeza
├── config/index.js           # ambiente validado
├── database/index.js         # schema, seed e conexão volátil
├── routes/index.js           # caminhos/adaptador async Express 4
├── controllers/
│   ├── index.js              # coordenação HTTP e resposta
│   └── validation.js         # forma/tipos/limites públicos
├── services/
│   ├── index.js              # checkout, relatório e exclusão
│   ├── errors.js             # erros conhecidos
│   └── payment.js            # adaptador de simulação
├── models/index.js           # SQL parametrizado/unidade de trabalho
├── middleware/
│   ├── auth.js               # credencial administrativa
│   └── errors.js             # tradução/diagnóstico seguro
└── security/passwords.js     # scrypt/verificação
```

Rotas → controllers → serviços → repositórios. SQL somente em models/database. Configuração, conexão e adaptadores injetados na composição. JSON é a representação pública; não há templates HTML.

Checkout deriva/verifica senha antes da transação síncrona. Dentro dela, revalida usuário/curso e grava usuário novo, matrícula, pagamento e auditoria atomicamente. Não há await dentro da transação. Cadastro simultâneo do mesmo email gera 409 em uma operação sem duplicar identidade. Matrículas repetidas continuam permitidas.

Relatório: um SELECT/CTE com joins, inclusive cursos sem alunos. Mantém primeiro pagamento por matrícula (ID), sem multiplicar alunos. Receita soma apenas PAID; paid representa valor do pagamento inclusive quando negado, conforme contrato original.

## Endpoints e deltas aprovados

| Método/caminho | Acesso | Sucesso/comportamento |
|---|---|---|
| POST /api/checkout | Cadastro público; existente exige senha correta | 200 {msg:"Sucesso",enrollment_id} |
| GET /api/admin/financial-report | Authorization: Bearer <ADMIN_TOKEN> | 200 [{course,revenue,students:[{student,paid}]}] |
| DELETE /api/users/:id | Mesmo token administrativo | 200 {msg:"Usuário deletado"} somente sem matrículas |

`api.http` usa variáveis de ambiente e cartões sintéticos. Campos públicos preservados:

- usr: texto não vazio após trim, até 200 caracteres.
- eml: email até 254 caracteres após trim, normalizado para minúsculas e único.
- pwd: texto obrigatório até 128; novos cadastros exigem ao menos oito. Existente exige autenticação, sem aceitar hash legado.
- c_id: inteiro positivo seguro; strings numéricas não são convertidas.
- card: string de 13–19 dígitos; não armazenada nem registrada em log.

Erros JSON `{error:{code,message}}`: 400 para dados/JSON inválidos ou recusa; 401 para credencial administrativa/senha inválida; 404 para curso/usuário ausente; 409 para usuário matriculado/cadastro concorrente; 500 genérico para falha interna. Parser: limite de 16 KiB (413), codificação não suportada (415).

Deltas: acesso administrativo protegido; senha deixa de ser opcional/ignorada; erros deixam de ser texto; DELETE verifica existência/preserva vínculos; falhas não deixam dados parciais; ordem determinística do relatório. FKs ativas e campos relevantes obrigatórios. Sem cascade financeiro.

## Dados, senhas e dependências

O original usava somente `:memory:`; nenhum arquivo persistente foi identificado para migração. A refatoração não abre/apaga banco externo. Seed somente em novas conexões voláteis e mediante configuração. Eventual exportação externa do legado exige revisão de duplicidades/órfãos e redefinição de senhas antes de importação. Não reutilizar pseudo-hash como senha; formatos antigos não são autenticados.

Scrypt: N=32768, r=8, p=1, 64 bytes; salt aleatório de 16 bytes e parâmetros persistidos. Segredos via ambiente. Logs somente de eventos/categorias; sem corpo, Authorization, senha, cartão, SQL ou mensagem bruta de erro.

sqlite3 5.1.7 foi substituído devido à depreciação/ausência de manutenção oficial. better-sqlite3 é síncrono: operações curtas, sem await transacional. Não há garantia de escalabilidade para carga arbitrária; produção não foi medida. SQLite e armazenamento em memória permanecem.

## Validação reproduzível

```sh
npm test
npm run test:http
# Salvar evidência em caminho escolhido:
npm run test:http -- /tmp/validation-project-2.json
```

Testes geram segredos efêmeros, bancos em memória e listeners loopback. `test:http` inicia o entry point real em porta livre, verifica PID/prontidão, exercita três endpoints e encerra processo; segundo processo com fixture comprova DELETE 200 e efeito no banco. Não requer API previamente iniciada. Somente 401 não comprova sucesso.

Resultado: **16/16 testes**, **26 cenários HTTP**, **3/3 endpoints**, processos encerrados e logs capturados sem segredos. Casos: quatro pontos de falha/rollback, concorrência, senha/salt, validação, FKs, exclusão real, isolamento, falhas de banco/listener, configuração ausente e contagem real de queries do relatório com cardinalidade crescente.

- [Auditoria aprovada e rastreabilidade](../reports/audit-project-2.md)
- [Baseline: sete cenários, três endpoints](../reports/baseline-project-2.json)
- [Validação final: contratos, efeitos, versões](../reports/validation-project-2.json)
- [Saída real da suíte](../reports/regression-project-2.txt)
- [Regressões](tests/regression.test.js) e [HTTP real](tests/smoke-http.js)

Checklist verificado: MVC, configuração externa, models/routes/controllers, erros centrais, boot real, todos os endpoints, regressões, deltas e migração documentados. Pagamento externo, persistência durável, distribuição de tokens e carga de produção estão fora desta API demonstrativa.
