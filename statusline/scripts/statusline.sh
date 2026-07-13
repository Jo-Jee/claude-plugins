#!/bin/sh
# Claude Code statusline renderer. Reads session JSON on stdin, prints the
# statusline to stdout. Pure formatter — no side effects.
# Icons: STATUSLINE_ICONS=nerd (default, needs a Nerd Font) | ascii (fallback).

if ! command -v jq >/dev/null 2>&1; then
  printf '%s\n' "⚠ statusline: jq not found — install jq"
  exit 0
fi

input=$(cat)

esc=$(printf '\033')
red="${esc}[31m"; green="${esc}[32m"; yellow="${esc}[33m"; magenta="${esc}[35m"; cyan="${esc}[36m"; reset="${esc}[0m"

if [ "${STATUSLINE_ICONS:-nerd}" = "ascii" ]; then
  icon_dir="▸"; icon_model="»"; icon_effort="fx"; icon_bolt=""; icon_ctx="ctx"; icon_branch="git"
else
  icon_dir="󰉋"; icon_model="󰚩"; icon_effort="󰊚"; icon_bolt="󱐋"; icon_ctx="󰭹"; icon_branch="󰘬"
fi

cwd=$(echo "$input" | jq -r '.cwd // .workspace.current_dir // ""')
model=$(echo "$input" | jq -r '.model.display_name // ""')
ctx_used=$(echo "$input" | jq -r '.context_window.used_percentage // empty')
rl_used=$(echo "$input" | jq -r '.rate_limits.five_hour.used_percentage // empty')
rl_resets=$(echo "$input" | jq -r '.rate_limits.five_hour.resets_at // empty')
effort=$(echo "$input" | jq -r '.effort.level // empty')

worktree_path=$(echo "$input" | jq -r '.worktree.path // empty')
if [ -n "$worktree_path" ]; then
  cwd="$worktree_path"
fi

case "$cwd" in
  "$HOME") cwd_display="~" ;;
  "$HOME"/*) cwd_display="~${cwd#$HOME}" ;;
  *) cwd_display="$cwd" ;;
esac

git_branch=$(git -C "$cwd" symbolic-ref --short HEAD 2>/dev/null || git -C "$cwd" rev-parse --short HEAD 2>/dev/null)
if [ -n "$git_branch" ] && [ -n "$(git -C "$cwd" status --porcelain 2>/dev/null | head -1)" ]; then
  git_branch="${git_branch}*"
fi

make_bar() {
  _pct=$1; _width=8
  _filled=$(( (_pct * _width + 50) / 100 ))
  [ "$_filled" -gt "$_width" ] && _filled=$_width
  [ "$_filled" -lt 0 ] && _filled=0
  _bar=""; _i=0
  while [ "$_i" -lt "$_width" ]; do
    if [ "$_i" -lt "$_filled" ]; then _bar="${_bar}█"; else _bar="${_bar}░"; fi
    _i=$((_i+1))
  done
  printf '%s' "$_bar"
}

context_str=""
if [ -n "$ctx_used" ]; then
  cu=$(printf "%.0f" "$ctx_used")
  if [ "$cu" -gt 80 ]; then ctx_color="$red"
  elif [ "$cu" -ge 50 ]; then ctx_color="$yellow"
  else ctx_color="$green"; fi
  context_str=" | ${ctx_color}${icon_ctx} $(make_bar "$cu") ${cu}%${reset}"
fi

rl_str=""
if [ -n "$rl_used" ]; then
  rlu=$(printf "%.0f" "$rl_used")
  if [ "$rlu" -ge 80 ]; then rl_color="$red"
  elif [ "$rlu" -ge 50 ]; then rl_color="$yellow"
  else rl_color="$green"; fi
  rl_reset_str=""
  case "$rl_resets" in
    ''|*[!0-9]*) ;;
    *) rl_time=$(date -r "$rl_resets" +%H:%M 2>/dev/null)
       if [ -n "$rl_time" ]; then
         rl_rem=$(( rl_resets - $(date +%s) ))
         [ "$rl_rem" -lt 0 ] && rl_rem=0
         rl_rem_str=$(printf '%02d:%02d' $((rl_rem / 3600)) $((rl_rem % 3600 / 60)))
         rl_reset_str=" - ${rl_time} (${rl_rem_str})"
       fi ;;
  esac
  rl_str=" | ${rl_color}${icon_bolt} $(make_bar "$rlu") 5h ${rlu}%${rl_reset_str}${reset}"
fi

effort_str=""
if [ -n "$effort" ]; then
  effort_str=" | ${magenta}${icon_effort} ${effort}${reset}"
fi

if [ -n "$git_branch" ]; then
  printf "%s %s %s%s %s%s\n%s %s%s%s%s" \
    "$icon_dir" "$cwd_display" "$cyan" "$icon_branch" "$git_branch" "$reset" \
    "$icon_model" "$model" "$effort_str" "$context_str" "$rl_str"
else
  printf "%s %s\n%s %s%s%s%s" \
    "$icon_dir" "$cwd_display" \
    "$icon_model" "$model" "$effort_str" "$context_str" "$rl_str"
fi
