#!/bin/bash
set -eo pipefail

[ -z "$1" ] && { echo "Usage: $0 <max-iterations>"; exit 1; }

for ((i=1; i<=$1; i++)); do
  echo "=== Ralph iteration $i/$1 ==="

  commits=$(git log -n 5 --format="%H%n%ad%n%B---" --date=short 2>/dev/null || echo "No commits found")
  issues=$(cat Issues/0{03,05,06,07,08,09,10,12,13}-*.md 2>/dev/null || echo "No issues found")
  prompt=$(cat ralph/prompt.md)

  echo "Previous commits: $commits

Issues: $issues

$prompt" | pi -p

  # Count remaining AFK issues (skip HITL 004/011 and docs 001/002)
  remaining=$(ls Issues/0{03,05,06,07,08,09,10,12,13}-*.md 2>/dev/null | wc -l | tr -d ' ')

  if [ "$remaining" -eq 0 ]; then
    echo "=== All AFK tasks complete after $i iterations ==="
    exit 0
  fi
done

echo "=== Max iterations ($1) reached, $remaining AFK task(s) remaining in Issues/ ==="
