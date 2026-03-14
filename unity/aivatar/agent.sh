#!/usr/bin/env bash
# Usage: ./agent.sh <command> [timeout_seconds]
# Examples:
#   ./agent.sh screenshot
#   ./agent.sh refresh 60
#   ./agent.sh "execute FixAppearanceV5.Run"
CMD="$1"
TIMEOUT="${2:-10}"
ITERS=$(echo "$TIMEOUT * 5" | bc)

rm -f "unity/aivatar/agent_result.txt"
echo "$CMD" > "unity/aivatar/agent_request.txt"
for i in $(seq 1 "$ITERS"); do
  [ -f "unity/aivatar/agent_result.txt" ] && cat "unity/aivatar/agent_result.txt" && exit 0
  sleep 0.2
done
echo "Timeout waiting for agent result"
exit 1
