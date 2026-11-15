#!/usr/bin/env bash
# lt.sh — sobe, derruba ou consulta o servidor local do LanguageTool.
# Uso: ./scripts/lt.sh start|stop|status [porta]
set -euo pipefail

ACAO="${1:-start}"
PORTA="${2:-8081}"
LT_HOME="${PANDITA_LT_HOME:-$HOME/.pandita/languagetool}"
LOG_FILE="$LT_HOME/lt.log"

status() { curl -sf --max-time 3 "http://localhost:$PORTA/v2/languages" >/dev/null 2>&1; }

case "$ACAO" in
  status)
    if status; then echo "LanguageTool no ar em http://localhost:$PORTA"; else echo "LanguageTool parado."; fi
    ;;
  start)
    if status; then echo "Já está no ar em http://localhost:$PORTA"; exit 0; fi
    JAR=$(ls "$LT_HOME"/LanguageTool-*/languagetool-server.jar 2>/dev/null | head -n1 || true)
    [ -z "$JAR" ] && { echo "LanguageTool não encontrado em $LT_HOME"; exit 1; }
    JAVA_BIN="${JAVA_HOME:+$JAVA_HOME/bin/java}"
    JAVA_BIN="${JAVA_BIN:-$(command -v java || true)}"
    [ -z "$JAVA_BIN" ] && { echo "Java não encontrado. Instale um JRE 17+."; exit 1; }
    # sem --public: o servidor escuta só nesta máquina
    "$JAVA_BIN" -Xmx1g -jar "$JAR" --port "$PORTA" >"$LOG_FILE" 2>&1 &
    for _ in $(seq 1 30); do
      sleep 1
      if status; then echo "LanguageTool no ar em http://localhost:$PORTA"; exit 0; fi
    done
    echo "Não subiu. Veja $LOG_FILE"; exit 1
    ;;
  stop)
    # pelo nome do servidor, não por um PID guardado: o número pode ter virado outro programa
    pkill -f languagetool-server.jar 2>/dev/null || true
    echo "LanguageTool parado."
    ;;
  *) echo "Uso: $0 start|stop|status [porta]"; exit 2 ;;
esac
