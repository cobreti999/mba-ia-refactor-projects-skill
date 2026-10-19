# Catálogo de anti-patterns

## Como usar e classificar

Leia os padrões como hipóteses a verificar no fluxo real. Uma busca textual encontra candidatos; só uma evidência contextualizada sustenta um finding. Use a mesma classificação em qualquer linguagem:

| Severidade | Critério |
|---|---|
| CRITICAL | Exposição de dados sensíveis, execução insegura ou violação completa da separação de responsabilidades que compromete o sistema. |
| HIGH | Forte violação MVC/SOLID, acoplamento ou inconsistência de dados que prejudica manutenção, isolamento e testes. |
| MEDIUM | Duplicação, validação insuficiente, padronização ou custo de consultas que afetam qualidade e desempenho. |
| LOW | Legibilidade, nomenclatura e constantes sem significado explícito. |

As severidades abaixo são bases, não rótulos automáticos. Justifique mudanças conforme alcance, entrada controlável, controles existentes e impacto demonstrável. Não confunda suspeita com confirmação. Um módulo extenso não é necessariamente uma God Class; ORM não garante ausência de SQL Injection; `print` isolado não prova vazamento.

Agrupe ocorrências da mesma causa e correção em um finding com todas as localizações relevantes. Separe causas com correções independentes. Não conte duas vezes o mesmo problema como God Class e regra de negócio no controller sem distinguir o alcance. Problemas concretos fora do catálogo podem receber identificação adicional, evidência e classificação pelos mesmos critérios.

## AP-01 — SQL construído com entrada externa

- **Base:** CRITICAL.
- **Sinais:** concatenação, interpolação ou formatação de dados recebidos em consultas executadas; SQL recebido diretamente por um endpoint.
- **Confirmar:** rastrear entrada → composição → execução, citando cada ponto. Verificar parâmetros vinculados, conversores e listas permitidas antes de afirmar explorabilidade.
- **Não confundir:** SQL fixo, parâmetros separados do texto e expressões do ORM que fazem binding não são injeção por si só. Um ID convertido para inteiro limita o vetor específico, embora a parametrização ainda possa ser recomendável.
- **Impacto/correção:** acesso ou alteração indevida; parametrizar valores e restringir operações/identificadores dinâmicos. Não executar payloads contra o banco durante a auditoria.

## AP-02 — Segredos ou dados sensíveis expostos

- **Base:** CRITICAL para credenciais expostas; HIGH para configuração sensível embutida sem exposição demonstrada.
- **Sinais:** segredo literal usado na aplicação, senha/token/cartão incluído em resposta ou log, configuração privada em health check.
- **Confirmar:** mostrar onde o valor é consumido ou exposto, ocultando seu conteúdo no relatório. Diferenciar exemplo inerte de configuração efetivamente utilizada; não afirmar que uma chave é válida externamente.
- **Não confundir:** nome de variável de ambiente e identificador público não comprovam segredo exposto.
- **Impacto/correção:** divulgação de dados e configuração; retirar campos de respostas/logs, carregar configuração externamente e propor tratamento das credenciais existentes quando pertinente.

## AP-03 — Armazenamento inadequado de senhas

- **Base:** CRITICAL.
- **Sinais:** senha em texto puro, MD5/SHA simples sem derivação apropriada ou codificação própria/Base64 usada como hash.
- **Confirmar:** seguir cadastro/persistência/verificação. Distinguir senha de checksum ou identificador não secreto.
- **Não confundir:** hash rápido usado para checksum não é armazenamento inseguro de senha.
- **Impacto/correção:** recuperação ou tentativa offline facilitada; usar derivação própria para senhas, evitar exposição e planejar migração ou redefinição das credenciais existentes.

## AP-04 — Autenticação/autorização ausente ou simulada

- **Base:** HIGH; CRITICAL se liberar operação destrutiva ou dados sensíveis sem controle.
- **Sinais:** token previsível sem verificação, papel privilegiado controlado pelo cliente, exclusão/reset/consulta administrativa sem checagem de permissão.
- **Confirmar:** examinar middlewares globais, decorators, registro de rotas e verificação de propriedade. Se o controle puder existir fora do código disponível, registrar a limitação.
- **Não confundir:** endpoint público intencional ou proteção aplicada em middleware não é falha por ausência de decorator local.
- **Impacto/correção:** operações indevidas; propor identidade verificável, autorização por operação/recurso e explicitar mudanças de contrato que exigirão aprovação.

## AP-05 — God Class ou módulo de responsabilidades concentradas

- **Base:** CRITICAL quando banco, roteamento e lógica complexa estão concentrados sem separação efetiva.
- **Sinais:** mesma classe/módulo cria schema, registra HTTP, executa SQL, calcula regras e coordena integrações.
- **Confirmar:** citar trechos de cada responsabilidade e explicar o acoplamento entre elas, não apenas contar linhas.
- **Não confundir:** composition root que somente conecta componentes não é God Class.
- **Impacto/correção:** mudanças e testes afetam domínios distintos; separar responsabilidades MVC e orquestração conforme os fluxos observados.

## AP-06 — Regras e persistência acopladas ao handler

- **Base:** HIGH.
- **Sinais:** rota/controller faz cálculos comerciais, controla transações e executa consultas diretamente; modelo persiste e também monta resposta HTTP.
- **Confirmar:** localizar a regra e suas dependências de framework/banco; distinguir orquestração de implementação detalhada.
- **Não confundir:** controller chamar um caso de uso, validar a forma da requisição e escolher status HTTP é esperado.
- **Impacto/correção:** isolamento difícil; concentrar fluxo no controller e separar regras, acesso a dados e representação. Usar AP-05 para a mesma concentração total, sem duplicar a contagem.

## AP-07 — Estado global mutável e dependências ocultas

- **Base:** HIGH.
- **Sinais:** conexão/sessão compartilhada entre requisições, cache global sem ciclo de vida, acumulador global ou construção de dependência concreta dentro de regra.
- **Confirmar:** identificar escritores, leitores, escopo e isolamento. Evidenciar por que impede teste ou mistura estado entre operações.
- **Não confundir:** configuração imutável e objeto de extensão que fornece sessão por contexto não equivalem a uma conexão global compartilhada.
- **Impacto/correção:** interferência e acoplamento; explicitar dependências e ciclo de vida por contexto/unidade de trabalho.

## AP-08 — Operação composta sem atomicidade

- **Base:** HIGH.
- **Sinais:** várias gravações do mesmo caso de uso com commits independentes, falha intermediária sem rollback, retorno de sucesso antes de confirmar persistência.
- **Confirmar:** mapear ordem das gravações, transação implícita/explícita e caminhos de erro. Ausência da palavra `BEGIN` isoladamente não prova falta de transação.
- **Não confundir:** operações independentes ou transação gerenciada pelo framework, desde que a delimitação seja demonstrada.
- **Impacto/correção:** estado parcial; delimitar unidade de trabalho e tratamento de falhas. Integrações externas exigem estratégia própria, não promessa de rollback de um pagamento remoto.

## AP-09 — Consultas N+1

- **Base:** MEDIUM.
- **Sinais:** consulta inicial seguida de consulta por item ou acesso lazy a relações em loops/serialização.
- **Confirmar:** indicar consulta inicial e consulta repetida; estimar crescimento pela cardinalidade. Considerar eager loading, cache de identidade e consultas realmente emitidas antes de afirmar número exato.
- **Não confundir:** loop sobre dados já carregados não comprova N+1.
- **Impacto/correção:** latência/custo crescentes; usar agregação, join ou carregamento em lote, preservando itens sem relações.

## AP-10 — Validação ausente ou inconsistente

- **Base:** MEDIUM; elevar somente se houver consequência grave demonstrada.
- **Sinais:** conversões sem tratamento, uso de métodos sem validar tipo, criação e atualização com regras divergentes, limites de domínio ausentes.
- **Confirmar:** seguir campo até consumo e verificar schemas/middlewares anteriores. Descrever entrada inválida e consequência inferida, sem apresentá-la como teste executado.
- **Não confundir:** validação centralizada fora do handler não está ausente.
- **Impacto/correção:** erro 500 ou dados inconsistentes; validar tipos e invariantes na camada apropriada, com respostas coerentes.

## AP-11 — Regra ou representação duplicada

- **Base:** MEDIUM.
- **Sinais:** mesma regra de atraso, validação ou serialização reimplementada em vários fluxos.
- **Confirmar:** citar pelo menos dois trechos e distinguir o que deve ser compartilhado das diferenças legítimas de contrato.
- **Não confundir:** formato público distinto por endpoint pode ser intencional.
- **Impacto/correção:** divergência futura; extrair a regra comum sem eliminar variações necessárias.

## AP-12 — Tratamento de erro disperso ou silencioso

- **Base:** MEDIUM; elevar se houver perda/inconsistência demonstrada.
- **Sinais:** exceção ampla sem diagnóstico, callback ignora `err`, exceção interna enviada ao cliente, sucesso retornado após falha.
- **Confirmar:** seguir propagação até a resposta e verificar middleware global; identificar se houve gravação parcial.
- **Não confundir:** captura ampla na fronteira com registro seguro, rollback e resposta consistente pode ser adequada.
- **Impacto/correção:** falhas ocultas e respostas inconsistentes; centralizar tradução HTTP e preservar diagnóstico sem dados sensíveis. Se a causa já for AP-08, referenciar em vez de duplicar.

## AP-13 — API obsoleta ou removida

- **Base:** MEDIUM para uso deprecated confirmado; HIGH se removida na versão aplicável e bloquear funcionamento.
- **Sinais:** chamadas marcadas deprecated/legacy pela biblioteca/runtime, wrappers antigos ou símbolo removido.
- **Confirmar:** identificar símbolo e pacote reais, versão aplicável, situação oficial e substituição. Consultar documentação oficial da versão; registrar URL e data da consulta. Distinguir deprecated, legacy suportada e removida. Não classificar por idade ou estilo do código.
- **Não confundir:** nome parecido de método próprio não prova uso da biblioteca; API legacy ainda suportada não é automaticamente removida. Versão desconhecida ou documentação inacessível implica candidato pendente, fora dos totais confirmados.
- **Impacto/correção:** incompatibilidade futura ou atual; propor equivalente disponível na stack e explicitar diferenças de comportamento, retorno e tratamento de erros.

Exemplos de referência, conferidos em 19/10/2026 (não constituem findings do projeto-alvo):

| Símbolo e condição | Situação e equivalente | Cuidados / fonte oficial |
|---|---|---|
| `Query.get(id)` com SQLAlchemy 2.x | Método deprecated/legacy; usar `session.get(Model, id)` | Preservar semântica de ausência e sessão; não substituir mecanicamente todo `.get`. [SQLAlchemy Query.get](https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html#sqlalchemy.orm.Query.get). |
| `datetime.utcnow()` com Python 3.12+ | Deprecated desde 3.12; usar `datetime.now(timezone.utc)` | O resultado passa de naive para aware: revisar armazenamento, comparações e serialização. Versão de Python não especificada não confirma a aplicabilidade ao ambiente. [Python datetime](https://docs.python.org/3.12/library/datetime.html#datetime.datetime.utcnow). |

Amplie a pesquisa conforme as chamadas e a stack encontradas, inclusive JavaScript e outros ecossistemas; estes exemplos não são uma lista fechada nem autorização para atualizar dependências.

## AP-14 — Números mágicos

- **Base:** LOW.
- **Sinais:** taxas, limites e faixas de negócio literais sem nomes, repetidos ou desconectados de constantes já existentes.
- **Confirmar:** explicar o significado comercial ocultado e localizar usos relacionados.
- **Não confundir:** zero de inicialização e status HTTP convencional não exigem constante por si só.
- **Impacto/correção:** manutenção e leitura; nomear a política sem alterar seus valores.

## AP-15 — Nomes pouco expressivos

- **Base:** LOW.
- **Sinais:** abreviações indistinguíveis em fluxos longos, nome que contradiz a responsabilidade.
- **Confirmar:** demonstrar a ambiguidade no contexto e propor nome informativo.
- **Não confundir:** índice curto em loop simples e chave pública legada não exigem renomear contrato.
- **Impacto/correção:** leitura difícil; melhorar nomes internos, preservando interface pública salvo mudança aprovada.

## AP-16 — Código, imports ou dependências sem uso

- **Base:** LOW.
- **Sinais:** import nunca referenciado, acumulador exportado sem consumidores, helper abandonado.
- **Confirmar:** pesquisar consumidores, exports, registro dinâmico e efeitos de importação no escopo disponível.
- **Não confundir:** import de registro, reexportação pública ou uso por reflexão pode ser necessário. Ausência de ocorrência textual não prova ausência de uso.
- **Impacto/correção:** ruído e dependências aparentes; remover somente quando a ausência de uso estiver sustentada.
