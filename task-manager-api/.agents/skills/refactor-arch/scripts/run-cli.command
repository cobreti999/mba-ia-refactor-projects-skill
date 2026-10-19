#!/bin/zsh
# Executa o Codex CLI real no projeto que contém esta cópia da skill.
set -eu
project_root="$(cd -- "$(dirname -- "$0")/../../../.." && pwd)"
cd "$project_root"
codex_binary="$(command -v codex || true)"
if [[ -z "$codex_binary" ]]; then
  for candidate in /Applications/{Codex,ChatGPT}.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex; do
    if [[ -x "$candidate" ]]; then
      codex_binary="$candidate"
      break
    fi
  done
fi
if [[ -z "$codex_binary" ]]; then
  print -u2 'Codex CLI não encontrado. Instale/configure o CLI e execute novamente.'
  exit 127
fi
exec "$codex_binary" --no-alt-screen --search '$refactor-arch Execute esta skill no projeto do diretório atual. Faça as fases 1 e 2 em sequência e mostre a saída completa neste console, com os cabeçalhos e os campos do exemplo de uso no CLI do README do desafio. Leia as referências e faça a inspeção real; não reutilize a análise manual como substituto da auditoria. Consulte documentação oficial para verificar APIs deprecated. Não exponha valores de credenciais. Antes de modificar a aplicação, apresente a proposta, seus deltas de contrato e o destino do relatório de auditoria exigido pelo desafio na raiz do repositório. Explique que y autoriza salvar esse relatório e executar a proposta, então imprima exatamente: Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]. Aguarde minha resposta nesta sessão. Não envie y em meu nome. Somente depois do meu y execute a Fase 3, valide boot real e todos os endpoints, salve as evidências e crie o commit local do projeto como exige o desafio; pare ao terminar este projeto. Não iniciar outro projeto, publicar, fazer push ou criar PR.'
