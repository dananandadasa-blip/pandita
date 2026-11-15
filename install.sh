#!/usr/bin/env bash
# Instala ou atualiza a skill pandita no diretório de skills de um agente.
# Uso: ./install.sh [destino]
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${1:-$HOME/.claude/skills/pandita}"

mkdir -p "$DEST"
for item in SKILL.md README.md LICENSE requirements.txt pandita.ps1 referencias scripts; do
  cp -R "$SRC/$item" "$DEST/"
done
# Arquivos da casa: só na primeira vez, para não apagar o que você editou.
for item in PADRAO.md glossario.csv config.json ignorar.txt; do
  if [ -e "$DEST/$item" ]; then echo "mantido: $item"; else cp "$SRC/$item" "$DEST/"; fi
done
find "$DEST" -name __pycache__ -type d -prune -exec rm -rf {} +

echo "pandita instalado em: $DEST"
echo "Para ler e gerar .docx: pip install -r \"$DEST/requirements.txt\""
echo "Para usar no DeepSeek Harness, copie para .dsh/skills/pandita."
