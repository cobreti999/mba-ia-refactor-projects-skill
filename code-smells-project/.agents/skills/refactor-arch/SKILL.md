---
name: refactor-arch
description: Analise, audite e refatore projetos legados para MVC em diferentes stacks. Identifique anti-patterns e APIs obsoletas com evidências, apresente o relatório para aprovação e valide a refatoração com boot e endpoints.
---

# Refactor Arch

## Escopo e fases

Execute Análise → Auditoria → Refatoração MVC, com pausa para revisão entre as fases. As três fases estão disponíveis; implementar a skill não equivale a executá-la em um projeto.

| Fase | Estado | Entrega |
|---|---|---|
| 1 — Análise | Disponível | Resumo da stack, inventário e mapa da arquitetura atual |
| 2 — Auditoria | Disponível | Catálogo de anti-patterns, relatório por severidade e confirmação |
| 3 — Refatoração | Disponível após aprovação | Transformações MVC e validação de boot, endpoints e findings |

## Definir o projeto-alvo

Use o diretório explicitamente indicado pelo usuário. Sem indicação, use o diretório de trabalho se ele contiver uma aplicação identificável. Se houver várias aplicações independentes e nenhum alvo claro, apresente as opções e peça a escolha antes de analisar. A localização desta skill não determina o projeto-alvo.

Resolva os caminhos das referências a partir da pasta desta skill; resolva os caminhos do código a partir do projeto-alvo. Consulte as instruções aplicáveis do repositório. Registre o caminho do alvo, a revisão Git quando disponível e alterações locais relevantes, sem sobrescrevê-las.

## Fase 1 — Análise

Leia [references/project-analysis.md](references/project-analysis.md) e siga suas heurísticas e seu formato de saída.

1. Delimite o inventário: arquivos de aplicação, testes, configuração, documentação e itens excluídos. Informe arquivos encontrados e efetivamente lidos; não confunda uma busca por padrões com leitura completa.
2. Identifique linguagens, frameworks, dependências, persistência e pontos de entrada por evidências no código e nos manifestos. Diferencie versão declarada, resolvida em lockfile e verificada em execução.
3. Determine o domínio pelos recursos e fluxos implementados. Mapeie responsabilidades reais, dependências entre módulos e um fluxo representativo de requisição até a persistência/resposta.
4. Liste os endpoints e os contratos observáveis, as tabelas/entidades e os comandos existentes de inicialização e teste. Cite arquivos e linhas. Indique lacunas, comportamento dinâmico não resolvido e divergências entre documentação e código.
5. Imprima o resumo no formato da referência. A conclusão desta fase exige stack, domínio, arquitetura, contagem verificável, mapa de responsabilidades e limitações explícitas. Se faltar evidência, registre a análise como parcial e identifique o que falta.

Faça uma inspeção estática: leia arquivos e use ferramentas de busca/listagem. Não instale dependências, importe módulos da aplicação, inicie servidores, execute seeds/migrations/testes ou abra bancos existentes nesta fase. Essas ações podem alterar dados mesmo quando parecem apenas inspecionar o projeto. Não crie relatórios em disco nem modifique arquivos durante a execução da Fase 1; apresente a saída na conversa. Não reproduza valores de senhas, tokens ou chaves encontrados no código.

A análise descreve a estrutura atual; classificação de severidade e recomendações detalhadas pertencem à Fase 2 — Auditoria. Não use relatórios anteriores ou listas de achados como substitutos da inspeção do código.

## Transição da Fase 1

Ao terminar a Fase 1, pare, mostre o resumo e pergunte se pode iniciar a Fase 2 — Auditoria. Aguarde um ok explícito. Se a análise for parcial, informe as lacunas; só prossiga com o escopo limitado se o usuário o aceitar. Um pedido inicial de fluxo completo não elimina a pausa.

## Fase 2 — Auditoria

Comece apenas após a Fase 1 e sua aprovação para o mesmo alvo. Em uma retomada, reutilize a análise disponível e confira se o código mudou. Atualize evidências afetadas antes de auditar. Se o alvo mudou ou não houver análise, execute a Fase 1 e pare para aprovação.

Leia [references/anti-patterns.md](references/anti-patterns.md) e [references/audit-report-template.md](references/audit-report-template.md). As referências da Fase 2 só precisam ser carregadas ao entrar nesta fase.

1. Cruze os arquivos e fluxos da análise com todos os padrões do catálogo. Registre cobertura por padrão: encontrado, não encontrado no escopo, não aplicável ou não verificado, sempre com justificativa. Investigue problemas concretos adicionais quando necessário.
2. Confirme cada candidato no código com caminhos e linhas exatos. Rastreie entradas, consumidores, proteções e efeitos; não trate correspondência textual como prova. Agrupe a mesma causa/correção e evite duplicar findings.
3. Verifique APIs obsoletas na documentação oficial da versão aplicável. Registre símbolo, pacote, versão e sua origem, status, equivalente moderno, URL e data. Sem evidência de versão/status, registre pendência fora dos totais confirmados.
4. Classifique e justifique severidade/impacto. Produza o relatório completo seguindo o template, ordenado de CRITICAL a LOW, com recomendações específicas, mudanças de contrato/dados e cenários de validação futura. Reconcilie totais com os findings detalhados.
5. Compare com a análise manual, se fornecida, somente após a inspeção. Para o desafio, confira pelo menos cinco findings, incluindo um CRITICAL/HIGH; no primeiro projeto, verifique a correspondência com pelo menos cinco problemas da análise manual. Se faltar evidência para esses mínimos, declare o critério não atendido sem inventar achados.
6. Apresente o relatório e uma proposta de escopo para a Fase 3, vinculada aos findings. Diferencie proposta de execução e confirmação de decisão pendente. Se houver lacunas relevantes, declare a auditoria parcial.

Mantenha a auditoria em modo de leitura: não instale dependências, execute a aplicação/testes/seeds, aplique fixes ou altere arquivos. Gere o relatório na conversa; não escreva nem sobrescreva o relatório em disco antes da confirmação específica de salvamento. Consultar documentação externa não autoriza enviar código ou segredos do projeto a serviços externos. Omita valores sensíveis das evidências.

## Confirmação e encerramento da Fase 2

Depois de mostrar o relatório, pare e pergunte: **“Autoriza executar a Fase 3 — Refatoração, conforme o escopo e as mudanças de contrato apresentados neste relatório?”** Se houver decisões em aberto que alterem o escopo, apresente-as antes de solicitar aprovação. Registre a resposta real vinculada ao projeto, revisão e proposta; não presuma autorização pelo silêncio ou pela aprovação da Fase 1.

Se foi solicitado um arquivo, peça também a confirmação do salvamento no caminho exato, separadamente da decisão de refatorar. Após o ok de salvamento, siga a referência do template e escreva somente o relatório autorizado. A exigência de revisão antes de qualquer escrita faz parte do fluxo desta auditoria.

A autorização de refatoração vale para o alvo e a proposta apresentados. Mudanças materiais no código ou no escopo exigem atualizar a parte afetada do relatório e submetê-la à revisão. Uma recusa mantém os arquivos intactos e permite revisar a proposta na conversa. Uma aprovação já registrada e ainda aplicável não precisa ser solicitada novamente.

## Fase 3 — Refatoração e validação

Só inicie com análise, auditoria e aprovação explícita da proposta para o mesmo projeto. Pedido genérico para refatorar, aprovação de salvamento ou aprovação da análise não substituem essa decisão. Se faltar uma fase, retome nela e respeite sua pausa. Confira a revisão e as alterações locais antes de editar; preserve trabalho preexistente.

Leia [references/mvc-guidelines.md](references/mvc-guidelines.md), [references/refactoring-playbook.md](references/refactoring-playbook.md) e [references/validation.md](references/validation.md). Carregue essas referências ao entrar nesta fase; selecione as transformações pertinentes aos findings aprovados.

1. Relacione findings, arquivos/camadas de destino, contratos e testes esperados. Prepare ambiente e banco isolados; caracterize o comportamento original conforme o roteiro de validação. Registre falhas preexistentes e não confunda preservação de contrato com preservação de vulnerabilidades.
2. Reestruture incrementalmente para MVC, mantendo separações úteis da aplicação. Extraia configuração e composição, separe rotas/controllers/models e centralize erros. Isole regras complexas, persistência e integrações conforme a necessidade real. Não trocar a stack nem adicionar abstrações sem benefício concreto.
3. Aplique os padrões do playbook às causas confirmadas. Preserve os contratos, salvo mudanças aprovadas; implemente migrações necessárias sem apagar dados existentes. Valide regressões relevantes a cada transformação. Descobertas que mudem materialmente a proposta devem voltar à revisão antes de execução.
4. Execute testes e confirme boot real e todos os pares método/caminho do inventário, verificando payloads, status e efeitos nos dados. Use dados sintéticos e substitutos para serviços externos. Siga as regras de prontidão, logs, limpeza e tratamento de falhas da referência.
5. Reavalie cada finding na versão final, revise dependências entre camadas e registre correções, resíduos e evidências. Atualize a documentação para os comandos efetivamente utilizados. Preserve o relatório original e acrescente resultado/rastreabilidade no artefato autorizado ou na conversa.
6. Apresente o resultado no formato da referência de validação: estrutura antes/depois, arquivos importantes, matriz de endpoints, testes reais, estado dos findings e limitações. Se houver autorização de commit aplicável, faça commit somente do escopo concluído e informe o hash real. Não publicar ou enviar alterações por inferência.

Não declarar conclusão completa se houver falha de boot, endpoint não verificado ou finding aprovado ainda pendente. Corrija falhas dentro do escopo e repita os checks necessários; se houver bloqueio ambiental, apresente evidências e o que falta, sem transformar ausência de teste em sucesso. Encerre os processos iniciados para validar.

## Encerramento da Fase 3

Pare após apresentar o resultado do projeto atual. Aguarde revisão explícita antes de iniciar outro projeto ou requisito. A aprovação desta fase não se estende automaticamente aos demais projetos.
