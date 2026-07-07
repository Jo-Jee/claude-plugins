#!/usr/bin/env bash
# Summarize English mistake history captured by the UserPromptSubmit hook.
#
# Usage:
#   check-english-stats.sh                    # full summary
#   check-english-stats.sh recent [N]         # last N corrections (default 20)
#   check-english-stats.sh category <name>    # all corrections in one category
#   check-english-stats.sh since <date>       # corrections at or after ISO date (e.g. 2026-05-01)

LOG="${CHECK_ENGLISH_MISTAKE_LOG:-$HOME/.claude/english-mistakes.jsonl}"

if [ ! -s "$LOG" ]; then
  echo "No mistakes logged yet at $LOG"
  exit 0
fi

cmd="${1:-summary}"

case "$cmd" in
  summary|"")
    total=$(wc -l <"$LOG" | tr -d ' ')
    first_ts=$(head -n1 "$LOG" | jq -r '.ts')
    last_ts=$(tail -n1 "$LOG" | jq -r '.ts')
    echo "English mistake history — $LOG"
    echo "  Total corrections: $total"
    echo "  First logged:      $first_ts"
    echo "  Most recent:       $last_ts"
    echo ""
    echo "By category (most frequent first):"
    jq -r '.category' "$LOG" | sort | uniq -c | sort -rn \
      | awk '{printf "  %4d  %s\n", $1, $2}'
    echo ""
    echo "Last 5 corrections:"
    tail -n 5 "$LOG" \
      | jq -r '"  [\(.category)] \(.original) → \(.corrected) — \(.reason)"'
    ;;
  recent)
    n="${2:-20}"
    tail -n "$n" "$LOG" \
      | jq -r '"\(.ts)  [\(.category)] \(.original) → \(.corrected) — \(.reason)"'
    ;;
  category)
    cat_name="$2"
    if [ -z "$cat_name" ]; then
      echo "Usage: $0 category <name>"
      echo "Available categories in your log:"
      jq -r '.category' "$LOG" | sort -u | sed 's/^/  /'
      exit 1
    fi
    jq -r --arg c "$cat_name" \
      'select(.category == $c) | "\(.ts)  \(.original) → \(.corrected) — \(.reason)"' \
      "$LOG"
    ;;
  since)
    since_ts="$2"
    if [ -z "$since_ts" ]; then
      echo "Usage: $0 since <YYYY-MM-DD or full ISO timestamp>"
      exit 1
    fi
    jq -r --arg s "$since_ts" \
      'select(.ts >= $s) | "\(.ts)  [\(.category)] \(.original) → \(.corrected)"' \
      "$LOG"
    ;;
  *)
    echo "Unknown command: $cmd"
    echo "Usage: $0 [summary | recent [N] | category <name> | since <date>]"
    exit 1
    ;;
esac
