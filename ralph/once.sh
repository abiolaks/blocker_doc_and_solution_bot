#!/bin/bash

issues=$(cat Issues/0{03,05,06,07,08,09,10,12,13}-*.md 2>/dev/null || echo "No issues found")
commits=$(git log -n 5 --format="%H%n%ad%n%B---" --date=short 2>/dev/null || echo "No commits found")
prompt=$(cat ralph/prompt.md)

echo "Previous commits: $commits

Issues: $issues

$prompt" | pi -p