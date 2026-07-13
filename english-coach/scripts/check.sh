#!/usr/bin/env bash
# UserPromptSubmit hook: review the user's English. A one-line summary goes to the user
# via systemMessage (the only channel the UI renders, single-line only); the full
# correction list goes to the model via additionalContext. Perfect English gets a
# random compliment.
# Also suggests a full native-sounding rewrite ("Native: ...") when the phrasing, even after
# the itemized fixes, still wouldn't read as written by a native speaker.
# Skips slash commands (/foo), bash-escapes (!cmd), and prompts containing fenced code blocks.

# Recursion guard: when this hook calls `claude -p` below, that child claude session
# also fires UserPromptSubmit and re-enters this script. Without this check, every user
# prompt cascades into runaway claude -p processes until the hook timeout kills them.
if [ -n "${CHECK_ENGLISH_IN_PROGRESS:-}" ]; then
  exit 0
fi
export CHECK_ENGLISH_IN_PROGRESS=1

# Training-mode pause: while a fresh session sentinel exists, stay silent so the
# interactive coach (/english-coach:train) owns all feedback. A sentinel older than
# 2h is treated as an abandoned session (forgotten goodbye) — remove it and resume.
SENTINEL="${CHECK_ENGLISH_SENTINEL:-$HOME/.claude/english-coach/.session-active}"
if [ -f "$SENTINEL" ]; then
  started=$(cat "$SENTINEL" 2>/dev/null)
  now=$(date +%s)
  if printf '%s' "$started" | grep -Eq '^[0-9]+$' && [ $((now - started)) -ge 0 ] && [ $((now - started)) -lt 7200 ]; then
    exit 0
  fi
  rm -f "$SENTINEL"
fi

input=$(cat)
prompt=$(printf '%s' "$input" | jq -r '.prompt // empty')

# Log paths are overridable so the script can be tested without touching real history.
LOG="${CHECK_ENGLISH_LOG:-$HOME/.claude/english-coach.log}"
MISTAKE_LOG="${CHECK_ENGLISH_MISTAKE_LOG:-$HOME/.claude/english-mistakes.jsonl}"
mkdir -p "$(dirname "$LOG")" "$(dirname "$MISTAKE_LOG")" 2>/dev/null

# Debug log — confirms the hook fired and shows which branch it took.
{
  printf '[%s] fired pid=%s prompt_len=%s first40=%q\n' \
    "$(date '+%Y-%m-%d %H:%M:%S')" "$$" "${#prompt}" "${prompt:0:40}"
} >>"$LOG" 2>&1

[ -z "$prompt" ] && exit 0
case "$prompt" in
  /*) exit 0 ;;
  '!'*) exit 0 ;;
  *'```'*) exit 0 ;;
esac

CLAUDE_BIN="${CHECK_ENGLISH_CLAUDE_BIN:-$(command -v claude || echo claude)}"

instruction=$(cat <<'EOF'
You review English written by a Korean software engineer. The text below is a message they are about to send to an AI assistant.

Step 1 — itemized corrections. Categories (pick exactly ONE per correction):
- articles          (a/an/the misuse or omission)
- agreement        (subject-verb or pronoun agreement)
- tense            (wrong or inconsistent tense)
- prepositions     (wrong/missing preposition)
- capitalization   (proper nouns, sentence start, "I")
- plurals          (singular/plural confusion, count vs mass)
- spelling         (typo or misspelled word)
- word-choice      (unnatural word, wrong register, Konglish — NOT spelling mistakes)
- word-order       (misplaced modifier, awkward order)
- contractions     (missing or wrong contraction)
- punctuation      (commas, apostrophes, etc.)
- structure        (run-on, fragment, awkward construction)
- other

Step 2 — native rewrite. After listing corrections, judge the message as a whole:
would it still read as written by a native English speaker even with the fixes applied?
If not, add ONE final line rewriting the ENTIRE message the way a native speaker would
naturally phrase it. Rules for the rewrite:
- Preserve the meaning and the casual register of a developer chat message.
- Do not add information, do not answer the message, do not soften requests.
- Keep it on a single line even if the original has multiple sentences.
- Include this line whenever the phrasing is unnatural — even if there are zero
  itemized corrections (e.g. grammatically fine but awkward or Konglish).
- Skip it only when the original already sounds native apart from trivial mechanical
  fixes (typos, capitalization, punctuation).

Output rules — STRICT:
- Max 5 correction lines, ONE per line, EXACT format:
  - [category] `original` → `corrected` — brief reason
- Use backticks around `original` and `corrected`. Use the arrow → and em-dash —.
- Optional final line, EXACT format: Native: <rewritten message>
- No headers, no preamble, no summary, no blank lines between lines.
- If the English is already natural and clear, respond with exactly: OK

Text:
EOF
)

feedback=$(printf '%s\n%s\n' "$instruction" "$prompt" | "$CLAUDE_BIN" -p --model sonnet 2>/dev/null) || exit 0

# Trim whitespace
feedback=$(printf '%s' "$feedback" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')

[ -z "$feedback" ] && exit 0

# Perfect English → random compliment instead of silence.
if [ "$feedback" = "OK" ]; then
  compliments=(
    "Flawless English — a native speaker couldn't have said it better. ✨"
    "Perfect sentence. Nothing to fix. 🎯"
    "Your English is on point today. 💯"
    "Clean, natural, native-sounding. Nice work. 👌"
    "Not a single correction needed — impressive. 🌟"
    "That reads like a native speaker wrote it. 🔥"
    "Grammar checker found nothing to do. Take a bow. 🎉"
    "Textbook-natural English. Keep it up. 📈"
  )
  jq -n --arg msg "${compliments[RANDOM % ${#compliments[@]}]}" '{systemMessage: $msg}'
  exit 0
fi

# Parse each correction line and append to JSONL history.
# Expected line shapes:
#   - [category] `original` → `corrected` — reason
#   Native: rewritten message                (logged with category "rewrite")
ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
prompt_snippet=$(printf '%s' "$prompt" | tr '\n' ' ' | cut -c 1-200)

native_rewrite=""
first_fix=""
n_fix=0

while IFS= read -r line; do
  # Accept optional "- " bullet prefix; the model sometimes omits it.
  if [[ "$line" =~ ^[[:space:]]*(-[[:space:]]+)?\[([a-z-]+)\][[:space:]]+\`(.+)\`[[:space:]]+→[[:space:]]+\`(.+)\`[[:space:]]+—[[:space:]]+(.+)$ ]]; then
    jq -nc \
      --arg ts "$ts" \
      --arg category "${BASH_REMATCH[2]}" \
      --arg original "${BASH_REMATCH[3]}" \
      --arg corrected "${BASH_REMATCH[4]}" \
      --arg reason "${BASH_REMATCH[5]}" \
      --arg context "$prompt_snippet" \
      '{ts:$ts, category:$category, original:$original, corrected:$corrected, reason:$reason, context:$context}' \
      >>"$MISTAKE_LOG"
    n_fix=$((n_fix + 1))
    [ -z "$first_fix" ] && first_fix="\`${BASH_REMATCH[3]}\` → \`${BASH_REMATCH[4]}\`"
  elif [[ "$line" =~ ^[[:space:]]*Native:[[:space:]]+(.+)$ ]]; then
    native_rewrite="${BASH_REMATCH[1]}"
    jq -nc \
      --arg ts "$ts" \
      --arg category "rewrite" \
      --arg original "$prompt_snippet" \
      --arg corrected "${BASH_REMATCH[1]}" \
      --arg reason "full native rewrite" \
      --arg context "$prompt_snippet" \
      '{ts:$ts, category:$category, original:$original, corrected:$corrected, reason:$reason, context:$context}' \
      >>"$MISTAKE_LOG"
  fi
done <<< "$feedback"

# Dual-channel output. systemMessage is the only channel the UI renders, and it is a
# single-line notice (anthropics/claude-code#61152) — so it carries a one-line summary:
# the native rewrite when present (the most useful single line), else the first fix.
# The full multi-line feedback goes to additionalContext so the assistant sees it and
# can relay details on request.
if [ -n "$native_rewrite" ]; then
  summary="Native: $native_rewrite"
  [ "$n_fix" -gt 0 ] && summary="$summary (+$n_fix fixes)"
elif [ "$n_fix" -gt 0 ]; then
  summary="$first_fix"
  [ "$n_fix" -gt 1 ] && summary="$summary (+$((n_fix - 1)) more)"
else
  # Model returned something unparseable; fall back to its first line.
  summary=$(printf '%s\n' "$feedback" | head -n1)
fi

jq -n --arg msg "$summary" --arg ctx "English check of the user's prompt:
$feedback" '{systemMessage: $msg, hookSpecificOutput: {hookEventName: "UserPromptSubmit", additionalContext: $ctx}}'
