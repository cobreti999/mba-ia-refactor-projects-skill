================================
ARCHITECTURE AUDIT REPORT
================================
Project: ecommerce-api-legacy
Stack: JavaScript + Node.js + Express + SQLite
Files: 3 analyzed | 180 physical source lines

## Contexto e escopo — auditoria original aprovada

- Data: 19/10/2026.
- Alvo: `ecommerce-api-legacy/`, raiz Git `/Users/lailson/Documents/ChatGPT/mba-ia-refactor-project-skills`.
- Revisão auditada: `f4df2266e4952c10ca6b10e1fd2c487befd4f9d2`.
- Estado anterior: README da raiz e arquivos da skill do projeto 1 modificados; scripts/skill não rastreados. Preservar esses trabalhos.
- Stack declarada/resolvida: Express ^4.18.2 / 4.22.1; sqlite3 ^5.1.6 / 5.1.7. Runtime não verificado nas fases 1/2.
- Domínio: LMS com usuários, cursos, matrículas, pagamentos e auditoria. Arquitetura concentrada em AppManager.
- Cobertura: 3/3 fontes integralmente lidos (`src/app.js`, 14 linhas; `src/AppManager.js`, 141; `src/utils.js`, 25), manifesto, lockfile completo por análise estrutural, README e api.http. Zero testes separados encontrados. Lockfile com 192 entradas incluindo raiz.
- Exclusões: código das dependências, gerados, Git, skills e aplicações vizinhas. README do desafio consultado como especificação. Nenhum AGENTS.md encontrado nos caminhos consultados.
- Método: inspeção estática e documentação oficial; aplicação, banco, testes e endpoints não executados nas fases 1/2. Nenhuma escrita nessas fases.
- Destino apresentado: `reports/audit-project-2.md`, relativo à raiz Git. Não existia antes da aprovação.
- Esta seção preserva findings e proposta da Fase 2; resultados posteriores são acrescentados separadamente.

## Summary

| Severidade | Findings |
|---|---:|
| CRITICAL | 4 |
| HIGH | 2 |
| MEDIUM | 5 |
| LOW | 2 |
| Total | 13 |

Critérios: mínimo de cinco findings e pelo menos um CRITICAL/HIGH atendidos. Comparação manual: 8/8 problemas do projeto 2 confirmados após inspeção.

## Findings

### F-001 — [CRITICAL] Operações administrativas e identidade de checkout sem controle

- Padrão: AP-04.
- Localização: `src/AppManager.js:80–84,131–136`; demais evidências `src/app.js:5–10`, `src/AppManager.js:40–43,66–75`.
- Fluxo/evidência: único middleware global é parser JSON. Relatório e exclusão sem autenticação; checkout usa usuário encontrado por email sem verificar senha.
- Impacto: leitura financeira/nomes, exclusão indevida e atribuição de matrículas a terceiros. CRITICAL por operações destrutivas/dados administrativos sem controle; infraestrutura externa não demonstrada.
- Recomendação: credencial administrativa verificável para GET/DELETE e senha correta no checkout existente.
- Contratos: autenticação e 401; senha deixa de ser ignorada.
- Validação futura: acesso ausente/incorreto negado sem gravações; acesso autorizado bem-sucedido.

### F-002 — [CRITICAL] Cartão e configuração sensível enviados ao log

- Padrão: AP-02.
- Localização: `src/AppManager.js:43–46`; configuração `src/utils.js:1–7`, entrada `AppManager.js:33`.
- Evidência: cartão recebido e configuração de chave interpolados em console.log; configurações literais com aparência de credenciais, algumas sem consumidores. Valores omitidos.
- Impacto/severidade: exposição integral do cartão e configuração nos logs; CRITICAL independentemente de validade externa da chave.
- Recomendação: eliminar dados sensíveis de logs, remover configuração inerte, segredos necessários via ambiente.
- Contratos: configuração operacional e logs; sucesso HTTP preservado.
- Validação futura: capturar logs com dados sintéticos e garantir ausência de senha, token e cartão. Não testar credenciais em serviços externos.

### F-003 — [CRITICAL] Senhas persistidas com transformação insegura e fallback previsível

- Padrão: AP-03.
- Localização: `src/utils.js:17–22`; chamadas `src/AppManager.js:18,66–71`.
- Evidência: badCrypto repete dois caracteres de Base64 e retorna dez; cadastro usa fallback literal; seed persiste senha literal.
- Impacto/severidade: colisões e ausência de derivação/salt apropriados; CRITICAL por armazenamento de credenciais, embora senha não seja verificada no original.
- Recomendação: crypto.scrypt assíncrono, salt aleatório, parâmetros registrados, comparação segura; remover fallback/seed fixo.
- Contratos/dados: senha obrigatória e novo formato pass. Não converter pseudo-hash em senha; credenciais antigas exigem redefinição.
- Validação futura: correta/incorreta, salts diferentes, omissão, formato e rejeição de legado.
- Fonte: https://nodejs.org/api/crypto.html#cryptoscryptpassword-salt-keylen-options-callback (19/10/2026).

### F-004 — [CRITICAL] AppManager concentra infraestrutura, HTTP e regras

- Padrão: AP-05; AP-06 agrupado, sem duplicar contagem.
- Localização: `src/AppManager.js:5–22,28–37,43–75,83–106,131–136`; composição `src/app.js:8–10`.
- Evidência: mesma classe instancia banco, schema/seed, rotas, regras, SQL e respostas.
- Impacto/severidade: ausência de fronteiras para manutenção/testes; CRITICAL segundo definição arquitetural do desafio.
- Recomendação: config/composição, routes, controllers, services, models/repositories e middleware de erros.
- Contratos: separação interna; demais mudanças somente conforme deltas aprovados.
- Validação futura: controllers sem SQL, models sem Express, serviços substituíveis e três endpoints reais.

### F-005 — [HIGH] Checkout produz gravações parciais

- Padrão: AP-08.
- Localização: `src/AppManager.js:48–61,66–71`.
- Evidência: usuário, matrícula, pagamento e auditoria separados; falha em pagamento deixa matrícula; erro em auditoria ignorado; usuário criado antes da recusa.
- Impacto/severidade: estado parcial/sucesso sem auditoria; HIGH por inconsistência no caso de uso.
- Recomendação: validar/autenticar/simular pagamento antes das escritas, transação para todas as gravações, resposta após commit.
- Contratos: recusas/falhas não deixam registros parciais.
- Validação futura: falhas em cada escrita, rollback e concorrência.
- Fonte: serialize agenda consultas; não é transação. https://github.com/TryGhost/node-sqlite3/wiki/Control-Flow (19/10/2026).

### F-006 — [HIGH] Exclusão permite referências órfãs

- Padrão adicional: integridade referencial.
- Localização: `src/AppManager.js:12–15,131–136`; efeito `104–115`.
- Evidência: DELETE somente de users, sem foreign keys; relatório usa Unknown para usuário ausente.
- Impacto/severidade: perda do vínculo de identidade do histórico financeiro; HIGH.
- Recomendação: foreign keys ativas e restrição à exclusão de usuário matriculado.
- Contratos: DELETE 409 quando vinculado; não apagar pagamentos em cascade.
- Validação futura: vinculado permanece, sem vínculos pode sair, sem órfãos.

### F-007 — [MEDIUM] Validação não protege consumidores dos campos

- Padrão: AP-10.
- Localização: `src/AppManager.js:29–38,45–46,68–69,131–133`.
- Evidência: presença não garante tipo; card numérico chega a startsWith, campos chegam ao driver/hash sem schema, ID sem validação.
- Impacto/severidade: exceções e respostas inconsistentes; escape do callback assíncrono é inferência estática, não teste. MEDIUM conforme catálogo.
- Recomendação: validar corpo, tipos, limites, email, senha e IDs antes do uso.
- Contratos: entradas antes aceitas por coerção passam a 400.
- Validação futura: números, objetos, arrays, null, omissões, limites e disponibilidade do processo.

### F-008 — [MEDIUM] Erros ignorados e prontidão sem confirmação

- Padrão: AP-12.
- Localização: `src/AppManager.js:92–94,104–115,133–135`; demais evidências `10–22,37–38`, `src/app.js:8–13`.
- Evidência: callbacks ignoram err; acesso a enrollments.length sem proteção; DELETE sempre anuncia sucesso; erro de consulta vira 404; listener não aguarda confirmação do schema/seed.
- Impacto/severidade: respostas falsas/diagnóstico incorreto; MEDIUM. Atomicidade já contada em F-005.
- Recomendação: prontidão verificável, propagação e tradutor HTTP central.
- Contratos: 500 genérico para falha interna; 404 para DELETE inexistente.
- Validação futura: falhas de boot/consulta/exclusão; sem stack/SQL/segredos, recursos encerrados.

### F-009 — [MEDIUM] Relatório executa consultas proporcionais às relações

- Padrão: AP-09.
- Localização: `src/AppManager.js:83–106`.
- Evidência: consulta de cursos + matrículas por curso + usuário/pagamento por matrícula: 1 + C + 2E no fluxo sem erros.
- Impacto/severidade: custo crescente e coordenação por contadores; MEDIUM.
- Recomendação: consulta em lote, preservando relações vazias e semântica financeira.
- Contratos: mesmos campos, receita PAID e paid; ordem determinística.
- Validação futura: equivalência sintética e número constante de consultas.

### F-010 — [MEDIUM] Cache global cresce sem leitura ou descarte

- Padrão: AP-07.
- Localização: `src/utils.js:9,12–15,25`; escritor `src/AppManager.js:57–60`.
- Evidência: chave por usuário, sem leitores/limite/remoção.
- Impacto/severidade: memória retida e dependência sem benefício; MEDIUM, abaixo da base HIGH porque nenhuma leitura demonstra contaminação de respostas.
- Recomendação: remover cache/escrita; manter auditoria transacional.
- Contratos: nenhum consumidor HTTP depende desse cache.
- Validação futura: fluxos preservados e isolamento entre instâncias.

### F-011 — [MEDIUM] Driver sqlite3 oficialmente deprecated e sem manutenção

- Padrão: AP-13, pacote completo.
- Localização: `src/AppManager.js:1,7`; `package.json:11`; `package-lock.json:2021–2044`.
- Símbolos: sqlite3.verbose(), Database, run/get/all/serialize.
- Versão/origem: ^5.1.6 declarada; 5.1.7 resolvida no lockfile, não executada na auditoria.
- Status: repositório oficial marcado deprecated/unmaintained e arquivado em 01/07/2026. Métodos existem na tag 5.1.7; não afirmar remoção ou versão inaugural de depreciação não documentada.
- Impacto/severidade: dependência direta sem manutenção; MEDIUM, sem afirmar falha de boot ou exploração.
- Recomendação: better-sqlite3 mantendo Node/Express/SQLite; escolha desta proposta, não substituição prescrita pelo mantenedor antigo.
- Equivalência: prepare().get/all/run, transaction(), close(); API síncrona/exceções/lastInsertRowid em lugar de callbacks/this.lastID. Derivação de senha fora da transação síncrona.
- Contratos: dependência/lockfile/runtime compatível; HTTP e motor mantidos. Fixar versão exata na Fase 3.
- Validação futura: instalação, boot, IDs/tipos, rollback, consultas e encerramento.
- Fontes consultadas em 19/10/2026: https://github.com/TryGhost/node-sqlite3 ; https://github.com/TryGhost/node-sqlite3/blob/v5.1.7/lib/sqlite3.js ; https://github.com/WiseLibs/better-sqlite3/blob/master/docs/api.md .

### F-012 — [LOW] Abreviações dificultam acompanhar checkout

- Padrão: AP-15.
- Localização: `src/AppManager.js:29–33,43–74`.
- Evidência: u/e/p/cid/cc em callbacks longos.
- Impacto/severidade: leitura/manutenção; LOW.
- Recomendação: userName/email/password/courseId/card internos.
- Contratos: preservar usr/eml/pwd/c_id/card.
- Validação futura: testes com chaves originais.

### F-013 — [LOW] Símbolos e configuração sem uso

- Padrão: AP-16.
- Localização: `src/utils.js:2–3,5,10,25`; `src/AppManager.js:2`.
- Evidência: totalRevenue declarado/exportado/importado, sem uso; configuração de banco/SMTP sem consumidores.
- Impacto/severidade: ruído e dependências aparentes; LOW. Exposição agrupada em F-002.
- Recomendação: remover símbolos inertes, receita derivada dos pagamentos.
- Contratos: sem consumidores externos identificados; aplicação sem API de biblioteca documentada.
- Validação futura: imports e resultados financeiros.

## Cobertura do catálogo e pendências

| Padrão | Estado | Justificativa |
|---|---|---|
| AP-01 | Não encontrado | SQL externo parametrizado; schema/seed estáticos |
| AP-02 | Encontrado | F-002 |
| AP-03 | Encontrado | F-003 |
| AP-04 | Encontrado | F-001 |
| AP-05 | Encontrado | F-004 |
| AP-06 | Encontrado/agrupado | F-004, sem duplicar |
| AP-07 | Encontrado | F-010; construção concreta agrupada em F-004 |
| AP-08 | Encontrado | F-005 |
| AP-09 | Encontrado | F-009 |
| AP-10 | Encontrado | F-007 |
| AP-11 | Não encontrado independente | Contadores repetidos são implementação do relatório; sem regra duplicada confirmada |
| AP-12 | Encontrado | F-008; auditoria do checkout em F-005 |
| AP-13 | Encontrado | F-011 pacote, sem remoção de métodos confirmada |
| AP-14 | Não encontrado independente | Literais do pseudo-hash em F-003; preços são seeds; prefixo é simulação |
| AP-15 | Encontrado | F-012 |
| AP-16 | Encontrado | F-013 |

Express 4.22.1: express()/express.json(), app.use/get/post/delete/listen e res.status().send()/json() documentados nas formas usadas, sem depreciação identificada. Fontes (19/10/2026): https://expressjs.com/en/4x/api/express/ ; https://expressjs.com/en/4x/api/application/ ; https://expressjs.com/en/4x/api/response/ .

Buffer.from é alternativa documentada ao construtor Buffer() deprecated; problema local é criptográfico. Node não fixado: compatibilidade instalada pendente na Fase 2. Fonte: https://nodejs.org/api/buffer.html (19/10/2026).

Fora dos totais: nove transitivas marcadas deprecated no lockfile (@npmcli/move-file, are-we-there-yet, gauge, glob, inflight, npmlog, prebuild-install, rimraf, tar). Incluem cadeia de instalação de sqlite3/node-gyp opcional; marcação não prova chamada deprecated própria nem exploração. Conferir árvore final, sem prometer zero vulnerabilidades.

## Comparação manual, após inspeção

| Manual | Finding | Resultado |
|---|---|---|
| P2-01 | F-004 | Confirmado |
| P2-02 | F-003 | Inclui seed/fallback |
| P2-03 | F-005 | Inclui criação antes da recusa |
| P2-04 | F-002 | HIGH elevado a CRITICAL pelo cartão integral |
| P2-05 | F-009 | Crescimento explicitado |
| P2-06 | F-007 | Confirmado |
| P2-07 | F-012 | Confirmado |
| P2-08 | F-013 | Confirmado |

8/8 correspondências; adicionais F-001, F-006, F-008, F-010, F-011.

## Proposta aprovada para Fase 3

Manter JavaScript/CommonJS, Express 4, SQLite em memória; substituir driver por motivo F-011. Estrutura: src/app.js composição; server.js ciclo de vida; config/, database/, routes/, controllers/, services/, models/, middleware/, security/; tests/.

| Findings | Transformação | Verificação |
|---|---|---|
| F-001/F-003 | Admin por ambiente, senha no checkout, scrypt | acesso/hash/escritas |
| F-002/F-013 | logs seguros e remoção de símbolos/segredos | captura sintética/imports |
| F-004/F-012 | MVC e nomes | dependências/contratos |
| F-005/F-006 | transação/FKs/delete restrito | rollback/concorrência/órfãos |
| F-007/F-008 | validação/erros/boot | inválidos/falhas/prontidão |
| F-009/F-010 | lote/remoção cache | relatório/contagem de queries |
| F-011 | better-sqlite3 fixado | instalação/runtime/banco/HTTP |

### Deltas de contrato

1. GET administrativo e DELETE exigem Authorization: Bearer <ADMIN_TOKEN> via ambiente, sem default. Ausente/incorreto 401. Boot exige configuração válida.
2. Checkout mantém caminho/chaves/sucesso 200 {msg:"Sucesso",enrollment_id}. usr string não vazia, trim, até 200; eml email até 254, trim/lowercase; pwd obrigatória, novos cadastros 8–128 caracteres; c_id inteiro positivo (sem coerção); card string de 13–19 dígitos somente simulação. Existente exige senha correta (401). Inválido 400, curso ausente/inativo 404, recusa 400. Prefixo da simulação preservado, sem integração real.
3. Erros JSON {error:{code,message}}, incluindo parser; internos 500 genérico sem SQL/stack/segredos.
4. DELETE ID inválido 400; ausente 404; vinculado 409; sem vínculos 200 {msg:"Usuário deletado"}. Sem cascade financeiro.
5. Relatório preserva campos/receita PAID/paid; ordem por IDs de curso/matrícula; não adicionar email.
6. FKs ativas, obrigatoriedade, unicidade de email normalizado; múltiplas matrículas por usuário/curso continuam permitidas.
7. Seeds sem senha fixa; demo explícito com senha de configuração e derivação segura. Banco original volátil, sem arquivo identificado para migrar. Não abrir/apagar banco externo. Legado não aceito silenciosamente; redefinição necessária.
8. Ambiente, prontidão e encerramento; atualizar documentação, exemplos, manifesto e lockfile conforme execução real.

### Validação e artefatos

Caracterizar original isolado com dados sintéticos e captura protegida; testes de senha, acesso, validação, rollback, integridade, concorrência, relatório; servidor real e 3/3 endpoints com sucesso e erros; versões/efeitos/limpeza. Salvar reports/baseline-project-2.json e reports/validation-project-2.json na raiz. Acrescentar resultados sem apagar auditoria. Atualizar docs do alvo e seção pertinente da raiz preservando trabalho anterior. Commit local somente deste escopo após validação. Sem outro projeto, push, PR ou publicação.

## Checklist da auditoria

- [x] Escopo/revisão/cobertura registrados.
- [x] Evidências e linhas conferidas.
- [x] Ordem/agrupamento/totais reconciliados.
- [x] Severidades e recomendações justificadas.
- [x] Documentação oficial e pendências de versão.
- [x] Contratos/dados/verificações explicitados.
- [x] Relatório apresentado antes de escrever.

## Decisão e estado

- Auditoria estática concluída com limites declarados; boot/runtime não verificados na Fase 2.
- Incidente de apresentação: uma saída intermediária de ferramenta expôs literais sensíveis; reconhecido ao usuário. Valores não reproduzidos neste artefato. Capturas posteriores devem ser redigidas antes da exibição.
- Prompt apresentado: Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
- Resposta real do usuário nesta sessão: `y`.
- Aprovação: salvar este relatório e executar proposta/deltas, evidências e commit local do projeto 2. Não abrange outros projetos ou publicação.
- Estado ao aprovar: Fase 3 autorizada. Execução concluída e resultados registrados na seção seguinte.


## Fase 3 — resultado após aprovação

Estado: concluída no escopo aprovado. Resposta real `y` aplicada nesta sessão. Baseline original isolado: 7 cenários HTTP, 3/3 endpoints, Node 20.11.1, processo encerrado. Instrumentação da cópia temporária limitou bind a loopback/porta livre e suprimiu console antes de importar o legado; não modificou regras/SQL da aplicação.

Antes: 3 fontes/180 linhas, AppManager concentrador e utils misto. Depois: 14 fontes com app/server, config, database, routes, controllers/validation, services/payment/errors, models, middleware/auth/errors e security/passwords; quatro arquivos de testes. Dependências: Express 4.22.1 preservado; better-sqlite3 13.0.3 substitui sqlite3. Node final 24.22.0 temporário, sem alterar instalação global. SQLite final registrado na evidência JSON.

### Rastreabilidade final

Caminhos abaixo relativos a ecommerce-api-legacy/; evidências runtime em validation-project-2.json e regression-project-2.txt.

| ID | Estado | Evidência atual | Verificação real |
|---|---|---|---|
| F-001 | corrigido | src/middleware/auth.js:6–16; src/services/index.js:6–13; src/routes/index.js:4–6 | 401 sem/com token errado; GET autorizado; senha correta/incorreta; DELETE autorizado |
| F-002 | corrigido | src/config/index.js:1–20; src/middleware/errors.js:20–24 | logs HTTP sem segredos, erro de banco sanitizado, configuração externa |
| F-003 | corrigido | src/security/passwords.js:5–22; src/database/index.js:29–43 | salts distintos, correta/incorreta, rejeição de legado, seed derivado |
| F-004 | corrigido | src/app.js:12–24; src/routes/index.js:3–7; src/controllers/index.js:3–18; src/models/index.js:1–38 | direção de imports revisada; controllers sem SQL; import app sem efeitos |
| F-005 | corrigido | src/services/index.js:15–29; src/models/index.js:25 | rollback em users/enrollments/payments/audit_logs; cadastro concorrente |
| F-006 | corrigido | src/database/index.js:13–25,37; src/services/index.js:43–49 | 409 vinculado, 200 sem vínculo, FKs ativas, zero órfãos |
| F-007 | corrigido | src/controllers/validation.js:5–20 | tipos/limites/normalização; inválidos 400; processo permanece disponível |
| F-008 | corrigido | src/server.js:5–38; src/middleware/errors.js:3–25 | boot sem configuração falha; listener ocupado fecha banco; falhas DB 500 |
| F-009 | corrigido | src/models/index.js:12–22; src/services/index.js:31–41 | 4 chamadas de relatório = 4 SELECTs reais, de 0 a 31 matrículas; resultados corretos |
| F-010 | corrigido | src/app.js:12–24; src/services/index.js:6–29 | cache removido; duas instâncias sem estado compartilhado |
| F-011 | corrigido | package.json:12–16; src/database/index.js:1,35 | driver 13.0.3 e SQLite executados; npm ci reprodutível; zero marcas deprecated no lock final |
| F-012 | corrigido | src/controllers/validation.js:8–13; src/services/index.js:6–28 | nomes internos descritivos; chaves públicas preservadas por HTTP |
| F-013 | corrigido | src/config/index.js:1–20; src/app.js:1–9 | utils/totalRevenue/config inerte removidos; relatório deriva pagamentos |

### Validação executada

| Comando/cenário | Esperado | Observado | Evidência |
|---|---|---|---|
| npm ci --offline (cache temporário) | instalação pelo lock | exit 0, 70 pacotes | validation-project-2.json |
| npm test | regressões aprovadas | 16/16, zero falhas finais | regression-project-2.txt |
| npm run test:http -- <arquivo temporário> | boot/3 endpoints/limpeza | 26 casos, 3/3 endpoints, logs sem segredos, dois processos encerrados com exit 0 | validation-project-2.json |
| git diff --check | sem erros de whitespace | aprovado | revisão final |

O HTTP runner executa `node src/server.js`, o mesmo comando do npm start, com HOST=127.0.0.1 e PORT=0; valida PID/prontidão. Um segundo processo de fixture cria usuário sem vínculos para DELETE 200 e confirma exclusão no banco. Portas/PIDs/logs exatos estão no JSON, sem credenciais.

| Endpoint | Casos principais | Efeitos confirmados |
|---|---|---|
| POST /api/checkout | 200 novo/existente, 401 senha, 400 inválido/recusa, 404 curso, parser 413/415 | duas matrículas válidas, receita +994; falhas transacionais não alteram tabelas |
| GET /api/admin/financial-report | 200 autorizado; 401 ausente/incorreto; 500 DB injetado | cursos vazios preservados, receita/alunos equivalentes, consulta em lote |
| DELETE /api/users/:id | 200 sem vínculo, 401, 400 ID, 404 inexistente, 409 vinculado | usuário sem vínculo removido; histórico preservado; foreign_key_check vazio |

Ocorrências anteriores preservadas: rede/portas bloqueadas pelo sandbox foram repetidas com autorização. Primeiro teste de FK esperava subtipo FOREIGNKEY, mas SQLite usa TRIGGER para RESTRICT; ajustada a asserção para conferir a falha referencial, sem mudar a aplicação. Primeiro ensaio 13/16, final 16/16. Não são apresentados como sucessos os ensaios iniciais que falharam.

### Checklist final

- [x] MVC e direção das dependências revisados no código.
- [x] Configuração externa; sem segredos hardcoded na aplicação.
- [x] Models, routes e controllers separados.
- [x] Erros centrais e entry point claro.
- [x] Boot real com prontidão e PID conferidos.
- [x] 3/3 endpoints e fluxos autorizados exercitados.
- [x] Regressões dos 13 findings verificadas.
- [x] Deltas, dados e migração documentados.
- [x] Processos de validação encerrados.

Limitações: aplicação demo, pagamentos simulados, banco volátil, sem teste de carga/integração externa e sem auditoria completa de vulnerabilidades transitivas. Nenhum banco persistente foi apagado/migrado. Credenciais históricas externas não foram verificadas/revogadas. Não alegamos ausência universal de anti-patterns; 13/13 findings aprovados corrigidos no escopo revisado. Não iniciar projeto 3, push, publicação ou PR.
