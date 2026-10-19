# Arquitetura MVC alvo

## Responsabilidades e dependências

Adapte a estrutura à stack e ao tamanho do projeto. MVC descreve responsabilidades; mover um handler inteiro para uma pasta `controllers` sem separar regras e persistência não resolve o acoplamento.

| Componente | Responsabilidade | Limites |
|---|---|---|
| Models | Entidades, invariantes de domínio e abstração de persistência. Repositories podem separar consultas de entidades quando necessário. | Não importar objetos de request/response, registrar rotas ou formatar erros HTTP. |
| Views/Routes | Registrar caminhos/métodos, conectar controllers e renderizar a representação pública. Em APIs, views são serializadores JSON, não telas obrigatórias. | Não executar SQL, transações ou regras comerciais complexas. |
| Controllers | Interpretar a entrada HTTP validada, coordenar o caso de uso e selecionar resposta/status. | Não concentrar queries ou algoritmos comerciais; delegar operações aos models ou serviços de domínio. |
| Services, quando úteis | Regras que envolvem múltiplas entidades, transações e integrações. | Não depender do transporte HTTP; receber dependências explicitamente. Não criar serviço vazio só para repassar uma chamada. |
| Config | Ler ambiente, validar opções e fornecer configuração ao composition root. | Não embutir senhas ou defaults secretos; distinguir configuração obrigatória de defaults locais não sensíveis. |
| Tratamento de erros | Traduzir erros de domínio/validação para respostas consistentes, registrar falhas inesperadas com dados sensíveis omitidos. | Não converter indiscriminadamente 400/404 em 500 nem devolver traceback/SQL ao cliente. |
| Composition root | Criar aplicação, carregar config, conectar dependências e registrar rotas/middlewares. | Importar a aplicação não deve iniciar servidor, apagar dados, executar seed ou realizar integração externa. |

Direção esperada: rotas → controllers → domínio/serviços → persistência; controllers → serializadores para a saída. A infraestrutura implementa as dependências necessárias ao domínio, conectadas na composição. Evite dependências circulares e imports do entry point pelos models.

## Estrutura proporcional ao projeto

Exemplo ilustrativo, não árvore obrigatória:

```text
src/ ou pacote da aplicação/
  app                 composição e factory da aplicação
  config/             configuração
  routes/             registro HTTP
  controllers/        coordenação dos casos de uso
  models/             entidades e acesso a dados
  services/           regras multientidade, se necessárias
  views/              serializadores, se justificarem módulo próprio
  middlewares/        erros e controles de acesso
```

Use extensões, módulos e convenções naturais da linguagem. Preserve separações que já funcionam; em uma aplicação parcialmente organizada, extraia o que está acoplado sem reconstruir tudo. Bibliotecas e containers de injeção são opcionais: parâmetros de função/construtor e factories podem bastar. Não adicione ORM apenas para cumprir MVC.

## Contratos, dados e configuração

Preserve métodos, caminhos, chaves públicas, status e semântica observados na análise, exceto mudanças explicitamente aprovadas no relatório. Corrigir exposição de senha ou proteger uma rota administrativa pode alterar contrato: registre o delta, adapte os testes e não mantenha a vulnerabilidade em nome da compatibilidade. Mudanças materiais não previstas precisam de revisão antes de serem executadas.

O plano deve relacionar cada finding à mudança de camada, aos contratos afetados e à verificação. Transações de escrita pertencem a uma unidade de trabalho clara; rollback precisa deixar o estado consistente. Não compartilhe uma transação mutável entre requisições. Chaves estrangeiras, exclusões em cascata e retenção de histórico dependem das regras reais do domínio, não de uma escolha universal.

Mudar schema ou formato de senha exige estratégia de migração e reversão. Não apagar banco existente para fazer os testes passarem. Use banco temporário e dados sintéticos nos testes; preserve dados do usuário. Não realizar cobrança, envio real de email/SMS ou outras integrações externas na validação: use adaptadores controlados.

Centralize configuração; forneça exemplo de variáveis necessárias sem valores secretos e comandos reproduzíveis. Se uma chave for obrigatória, falhe com erro claro na inicialização em vez de usar segredo fixo. Mantenha debug desligado por padrão fora do ambiente local.

## Critério de arquitetura concluída

Verifique chamadas e dependências além da árvore de pastas. A revisão deve demonstrar: models abstraem dados; rotas registram HTTP; controllers coordenam fluxos; regras complexas e integrações estão isoladas quando necessário; configuração e erros têm pontos claros; entry point inicializa sem efeitos destrutivos. Use o [roteiro de validação](validation.md) para verificar funcionamento e contratos.
