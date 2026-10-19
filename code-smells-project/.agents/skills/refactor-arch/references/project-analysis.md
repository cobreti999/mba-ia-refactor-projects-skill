# Análise de projeto

## 1. Delimitar e contar

Comece pelo diretório-alvo, seus manifestos, pontos de entrada e instruções locais. Em monorepos, identifique as aplicações independentes antes de escolher o escopo. Não inclua automaticamente projetos vizinhos. Se não houver Git, prossiga com os arquivos disponíveis e registre essa limitação.

Use `rg --files --hidden` ou uma ferramenta equivalente para obter a lista inicial. Exclua metadados Git, dependências instaladas (`node_modules`, ambientes virtuais, `vendor`), caches, builds, arquivos gerados, bancos binários e pastas de skills. Respeite as regras de ignore; inspecione separadamente apenas configurações relevantes que tenham ficado fora da lista. Não siga links para fora do alvo sem necessidade explícita.

Classifique e apresente separadamente:

- **Aplicação:** fontes da aplicação, inicializadores, seeds e migrations mantidos pelo projeto. Inclua arquivos vazios de pacote, como `__init__.py`, e explicite a convenção.
- **Testes:** arquivos de testes e fixtures; não somar ao total da aplicação.
- **Configuração e suporte:** manifestos, lockfiles, configuração de runtime, documentação e exemplos HTTP; não somar ao total da aplicação.
- **Excluídos/não lidos:** registre os motivos e limitações de cobertura.

Conte caminhos únicos, não ocorrências de imports ou resultados de busca. Para projetos pequenos, liste todos os fontes lidos. Para projetos grandes, agrupe por diretório, declare a cobertura e não anuncie análise completa se houver partes não inspecionadas. Números aproximados devem ser identificados como estimativas.

## 2. Detectar stack com evidências

Combine manifestos com imports e uso real. Uma dependência declarada pode não ser utilizada; extensão de arquivo, isoladamente, não identifica framework. Exemplos de sinais, sem limitar a análise a estas stacks:

| Ecossistema | Manifestos/configuração | Sinais no código |
|---|---|---|
| Python | `pyproject.toml`, `requirements*.txt`, lockfiles | Imports e criação de aplicação Flask, Django, FastAPI ou outro framework; decorators, registro de blueprints/routers |
| JavaScript/TypeScript | `package.json`, lockfiles, `tsconfig.json` | Imports/requires, criação do servidor, routers e middlewares Express ou de outro framework |
| Java/Kotlin | `pom.xml`, arquivos Gradle | Bootstrap, anotações e configuração do framework efetivamente utilizado |
| C# | Arquivos de projeto/solução, configuração JSON | Composition root, registro de serviços e mapeamento de endpoints |
| Go | `go.mod`, `go.sum` | `main`, imports e registro de handlers |
| Ruby/PHP | `Gemfile`, `composer.json` e locks | Inicialização, rotas e modelos do framework presente |
| Outra stack | Manifestos e configuração próprios | Pontos de entrada, dependências e fluxos reais; documentar incertezas |

Para cada framework/dependência relevante, diferencie:

- **Declarada:** restrição no manifesto, como `^4.18.2`; não a apresente como versão instalada.
- **Resolvida:** versão exata no lockfile correspondente ao pacote, se existente.
- **Em execução:** somente se houver evidência de execução já disponível e atribuível ao ambiente atual. Na inspeção estática, normalmente registrar “não verificada”.

Registre linguagens principal e secundárias quando houver. Diferencie bibliotecas usadas no código de dependências apenas declaradas. Não deduza versão de runtime a partir da versão do framework. Falta de manifesto ou lockfile é uma limitação, não motivo para inventar uma versão.

## 3. Identificar persistência e domínio

Busque drivers, criação de conexões, configurações de ORM, schemas, migrations, SQL e modelos. Registre motor, mecanismo de acesso e ciclo de vida: memória, arquivo ou serviço externo. Não confunda SQLite em memória com persistência durável. Um ORM não informa sozinho qual banco está configurado.

Liste tabelas/entidades e relações observadas. Diferencie relação declarada no ORM, chave estrangeira no schema e vínculo inferido por nomes/código. Não afirme que uma restrição está efetiva no banco sem evidência. Leia configurações de exemplo ou referências a variáveis de ambiente; omita valores sensíveis e não abra arquivos de segredos para preencher o resumo.

Descreva o domínio a partir de recursos, operações e regras: por exemplo, cursos + matrículas + pagamentos indicam ensino com checkout. O nome da pasta e o README são pistas que devem ser conferidas com o código.

## 4. Mapear responsabilidades reais

Localize onde vivem:

- Inicialização e composição da aplicação.
- Registro de rotas/handlers e serialização das respostas.
- Orquestração de casos de uso e regras de negócio.
- Acesso a dados, modelos e transações.
- Configuração, autenticação/autorização, erros e integrações externas.

Monte uma tabela `responsabilidade → arquivo/símbolo → evidência (linhas)`. Se responsabilidades estiverem misturadas, descreva a mistura. Um arquivo chamado `models` pode conter regras e SQL; um diretório `services` pode existir sem ser chamado. Verifique usos/imports, não apenas nomes.

Trace pelo menos um fluxo representativo: entrada HTTP → handler/controller → regra/caso de uso → persistência/integração → resposta. Aponte chamadas reais entre arquivos ou métodos e os limites de transação observáveis. Para sistemas sem HTTP, use a entrada equivalente, como comando CLI, evento ou job.

Classifique a arquitetura descritivamente: concentrada em poucos módulos, separação parcial, MVC, outra arquitetura ou indeterminada. Explique a classificação com evidências. Nesta fase, não force todos os projetos a parecerem monolitos nem produza findings de auditoria.

## 5. Mapear superfície e validação futura

Liste método, caminho efetivo, handler e localização das rotas. Considere prefixos de routers/blueprints, parâmetros, registro em métodos de classes e chamadas como `add_url_rule`. Conte pares método/caminho explícitos; exclua HEAD/OPTIONS automáticos e rotas estáticas do framework, informando esse critério. Se o registro for dinâmico e não puder ser resolvido estaticamente, marque como indeterminado.

Registre entradas e respostas observáveis dos fluxos principais: campos obrigatórios, formato, status de sucesso/erro e autenticação aplicada. Preserve os nomes públicos ao descrevê-los. Não afirme que a API funciona por reconhecer suas rotas.

Extraia comandos de boot, preparação do banco e testes de documentação, scripts e configuração. Marque-os como **identificados, não executados**. Sinalize comandos com efeitos em dados, como seeds que apagam tabelas. Se não houver testes ou comando de teste, registre a ausência observada. Verificações em runtime ficam para a etapa apropriada.

## 6. Formato de saída

Preencha o seguinte resumo com resultados observados; use “não identificado” quando necessário. Evidências devem usar caminhos relativos ao alvo e linhas reais da versão analisada.

```markdown
# Fase 1 — Análise do projeto

- Projeto/alvo: ...
- Revisão Git e alterações locais: ...
- Linguagens: ...
- Frameworks: ... (declarado / resolvido / execução não verificada)
- Dependências relevantes: ... (usadas / somente declaradas)
- Domínio: ...
- Persistência: ...
- Arquitetura atual: ... (justificativa)
- Cobertura: ... fontes encontrados / ... lidos; ... testes; exclusões: ...

## Inventário e evidências
| Categoria | Arquivos ou entidades | Evidências/observações |
|---|---|---|

## Responsabilidades atuais
| Responsabilidade | Arquivo/símbolo | Evidência |
|---|---|---|

## Fluxo representativo
... sequência de chamadas, regras, persistência e resposta ...

## Superfície da aplicação
| Método | Caminho | Handler | Evidência |
|---|---|---|---|

Contratos principais: ...
Critério de contagem e rotas dinâmicas não resolvidas: ...

## Preparação para validação
- Boot: ... (identificado, não executado)
- Banco/seed: ... (efeitos observados, não executado)
- Testes existentes: ... (não executados)

## Limitações e encerramento
- Incertezas, arquivos não lidos e divergências: ...
- Boot e endpoints: não verificados em execução nesta fase.
- Estado da análise: completa no escopo informado / parcial, com motivo.
```

Após o resumo, aplique o encerramento definido no `SKILL.md`. Não crie arquivos ao produzir esta saída. Após imprimir o resumo, prossiga para a Auditoria, salvo pedido explícito para executar somente a Análise.
