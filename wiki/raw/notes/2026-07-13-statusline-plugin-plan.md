# Statusline Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish the author's Claude Code statusline as an installable `statusline` plugin in the `jojee-tools` marketplace.

**Architecture:** A pure `stdin→stdout` renderer (`statusline.sh`) does the drawing. Because plugins cannot declare a main `statusLine` and `${CLAUDE_PLUGIN_ROOT}` does not expand in the statusline execution context, a `/statusline-setup` command writes an **absolute-path** `statusLine` entry into `~/.claude/settings.json`, and a `SessionStart` hook (`sync.sh`) re-pins that absolute path each session — but only for an entry this plugin owns (tracked in `owned.json`), never clobbering a foreign statusline.

**Tech Stack:** POSIX `sh` / Bash, `jq`, Claude Code plugin manifest + hooks + slash commands.

## Global Constraints

- Plugin name: `statusline`; marketplace: `jojee-tools`; author: `Jo-Jee <jojee.dev@gmail.com>`.
- Renderer `statusline.sh` MUST be a pure formatter — read stdin, write stdout, no side effects, exit 0.
- Never silently overwrite a foreign `statusLine`; the SessionStart hook re-pins ONLY an entry matching our ownership record.
- All state-mutating scripts MUST honor these test-override env vars: `STATUSLINE_SETTINGS` (settings.json path), `STATUSLINE_DATA` (dir holding `owned.json`), `STATUSLINE_ROOT` (plugin root). Defaults: `$HOME/.claude/settings.json`, `$CLAUDE_PLUGIN_DATA`, `$CLAUDE_PLUGIN_ROOT`.
- The written `statusLine.command` string format is exactly: `STATUSLINE_ICONS=<nerd|ascii> "<abs-root>/scripts/statusline.sh"`.
- Icon set toggled by `STATUSLINE_ICONS` (`nerd` default, `ascii` fallback).
- Do not use `cmd && exit 0` at statement top-level in `set -e` scripts (a false test makes the list return non-zero and trips `set -e`); use `if … then exit 0; fi`.
- Working branch: `feat/statusline-plugin`. Commit after each task.

## File Structure

```
statusline/
├── .claude-plugin/plugin.json          # manifest
├── hooks/hooks.json                    # SessionStart → scripts/sync.sh
├── scripts/
│   ├── statusline.sh                   # renderer (pure stdin→stdout)
│   ├── lib-settings.sh                 # settings.json + owned.json helpers (sourced)
│   ├── sync.sh                         # SessionStart re-pin (ownership-checked)
│   ├── setup.sh                        # install / uninstall / status subcommands
│   └── test.sh                         # test harness (renderer + settings mutation)
├── commands/
│   ├── statusline-setup.md             # /statusline-setup
│   └── statusline-uninstall.md         # /statusline-uninstall
└── README.md
.claude-plugin/marketplace.json         # add "statusline" entry (repo root)
```

---

### Task 1: Scaffold plugin manifest & marketplace entry

**Files:**
- Create: `statusline/.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json` (add second plugin entry)

**Interfaces:**
- Produces: an installable plugin skeleton named `statusline` under marketplace `jojee-tools`.

- [ ] **Step 1: Write the manifest**

Create `statusline/.claude-plugin/plugin.json`:

```json
{
  "name": "statusline",
  "description": "A polished Claude Code statusline: cwd, git branch, model, reasoning effort, context-window and 5h rate-limit bars. Nerd Font icons with an ASCII fallback.",
  "version": "1.0.0",
  "author": { "name": "Jo-Jee", "email": "jojee.dev@gmail.com" }
}
```

- [ ] **Step 2: Add the marketplace entry**

In `.claude-plugin/marketplace.json`, add a second object to the `plugins` array (after `english-coach`):

```json
    {
      "name": "statusline",
      "source": "./statusline",
      "category": "productivity",
      "description": "A polished Claude Code statusline with context-window and 5h rate-limit bars, git/model/effort segments, Nerd Font icons + ASCII fallback. Installs via /statusline-setup."
    }
```

- [ ] **Step 3: Validate JSON**

Run: `jq empty statusline/.claude-plugin/plugin.json && jq empty .claude-plugin/marketplace.json && echo OK`
Expected: `OK`

- [ ] **Step 4: Confirm two plugins registered**

Run: `jq -r '.plugins[].name' .claude-plugin/marketplace.json`
Expected:
```
english-coach
statusline
```

- [ ] **Step 5: Commit**

```bash
git add statusline/.claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "feat(statusline): scaffold plugin manifest and marketplace entry"
```

---

### Task 2: Renderer `statusline.sh` (hardened)

**Files:**
- Create: `statusline/scripts/statusline.sh`
- Create: `statusline/scripts/test.sh` (renderer cases; extended in later tasks)

**Interfaces:**
- Consumes: session JSON on stdin (fields: `.cwd`, `.workspace.current_dir`, `.model.display_name`, `.context_window.used_percentage`, `.rate_limits.five_hour.used_percentage`, `.rate_limits.five_hour.resets_at`, `.effort.level`, `.worktree.path`).
- Produces: statusline text on stdout. Honors `STATUSLINE_ICONS=nerd|ascii`. Prints `⚠ statusline: jq not found — install jq` and exits 0 when `jq` is absent.

- [ ] **Step 1: Write the failing tests**

Create `statusline/scripts/test.sh`:

```bash
#!/usr/bin/env bash
# Test harness for the statusline plugin. Run: bash scripts/test.sh
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PASS=0; FAIL=0
ok()   { PASS=$((PASS+1)); printf '  ok   - %s\n' "$1"; }
bad()  { FAIL=$((FAIL+1)); printf '  FAIL - %s\n' "$1"; }
assert_contains() { case "$2" in *"$1"*) ok "$3" ;; *) bad "$3 (missing: $1)"; printf '      got: %s\n' "$2" ;; esac; }
assert_equals()   { if [ "$1" = "$2" ]; then ok "$3"; else bad "$3 (want '$1' got '$2')"; fi; }

REND="$ROOT/scripts/statusline.sh"

FULL='{"cwd":"'"$HOME"'/proj","model":{"display_name":"Opus 4.8"},"context_window":{"used_percentage":42},"rate_limits":{"five_hour":{"used_percentage":30,"resets_at":0}},"effort":{"level":"high"}}'

echo "== renderer =="
out=$(printf '%s' "$FULL" | STATUSLINE_ICONS=nerd sh "$REND")
assert_contains "~/proj" "$out" "full: cwd shown with ~"
assert_contains "Opus 4.8" "$out" "full: model shown"
assert_contains "42%" "$out" "full: context percent shown"
assert_contains "5h 30%" "$out" "full: rate-limit percent shown"
assert_contains "high" "$out" "full: effort shown"

NOGIT='{"cwd":"/tmp/nowhere-xyz","model":{"display_name":"Haiku"}}'
out=$(printf '%s' "$NOGIT" | STATUSLINE_ICONS=nerd sh "$REND")
assert_contains "Haiku" "$out" "no-git: model still shown"

out=$(printf '%s' "$FULL" | STATUSLINE_ICONS=ascii sh "$REND")
assert_contains "ctx" "$out" "ascii: context label"
assert_contains "git" "$out" "ascii: branch label"

out=$(PATH= sh "$REND" </dev/null)
assert_contains "jq not found" "$out" "no-jq: prints hint"

echo
echo "PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `bash statusline/scripts/test.sh`
Expected: FAIL (renderer does not exist yet; assertions fail / `sh` cannot open the script).

- [ ] **Step 3: Write the renderer**

Create `statusline/scripts/statusline.sh`:

```sh
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
```

- [ ] **Step 4: Make executable and run tests**

Run: `chmod +x statusline/scripts/statusline.sh statusline/scripts/test.sh && bash statusline/scripts/test.sh`
Expected: all renderer assertions `ok`, `FAIL=0`.

- [ ] **Step 5: Commit**

```bash
git add statusline/scripts/statusline.sh statusline/scripts/test.sh
git commit -m "feat(statusline): hardened renderer with jq guard and ASCII fallback"
```

---

### Task 3: `lib-settings.sh` (settings + ownership helpers)

**Files:**
- Create: `statusline/scripts/lib-settings.sh`
- Modify: `statusline/scripts/test.sh` (add lib section)

**Interfaces:**
- Produces (sourced functions):
  - `settings_path` → prints settings.json path (`$STATUSLINE_SETTINGS` or `$HOME/.claude/settings.json`)
  - `owned_path` → prints `$STATUSLINE_DATA/owned.json` (or `$CLAUDE_PLUGIN_DATA/owned.json`)
  - `plugin_root` → prints `$STATUSLINE_ROOT` or `$CLAUDE_PLUGIN_ROOT`
  - `build_command <root> <icons>` → prints `STATUSLINE_ICONS=<icons> "<root>/scripts/statusline.sh"`
  - `read_statusline_command` → prints `.statusLine.command` or empty
  - `write_statusline_command <cmd>` → sets `.statusLine={type:"command",command:cmd}` (creates file if absent, atomic write)
  - `remove_statusline` → deletes `.statusLine`
  - `backup_settings` / `restore_settings_backup` → copy to / restore from `<settings>.bak`
  - `owned_get_command` → prints recorded command or empty
  - `owned_get_icons` → prints recorded icons or `nerd`
  - `owned_write <cmd> <icons>` → writes `owned.json`
  - `owned_clear` → removes `owned.json`

- [ ] **Step 1: Write the failing tests**

Append to `statusline/scripts/test.sh` immediately before the final `echo` / `PASS=` summary lines:

```bash
echo "== lib-settings =="
TMP=$(mktemp -d)
export STATUSLINE_SETTINGS="$TMP/settings.json"
export STATUSLINE_DATA="$TMP/data"
export STATUSLINE_ROOT="/opt/plugins/statusline"
# shellcheck source=/dev/null
. "$ROOT/scripts/lib-settings.sh"

assert_equals 'STATUSLINE_ICONS=nerd "/opt/plugins/statusline/scripts/statusline.sh"' \
  "$(build_command "$(plugin_root)" nerd)" "build_command formats nerd"

write_statusline_command 'CMD_A'
assert_equals "CMD_A" "$(read_statusline_command)" "write/read roundtrip"
assert_equals "command" "$(jq -r '.statusLine.type' "$STATUSLINE_SETTINGS")" "write sets type=command"

owned_write "CMD_A" "ascii"
assert_equals "CMD_A" "$(owned_get_command)" "owned command recorded"
assert_equals "ascii" "$(owned_get_icons)" "owned icons recorded"

backup_settings
remove_statusline
assert_equals "" "$(read_statusline_command)" "remove_statusline clears entry"
restore_settings_backup
assert_equals "CMD_A" "$(read_statusline_command)" "restore brings back entry"

owned_clear
assert_equals "nerd" "$(owned_get_icons)" "owned_get_icons defaults to nerd after clear"
rm -rf "$TMP"
unset STATUSLINE_SETTINGS STATUSLINE_DATA STATUSLINE_ROOT
```

- [ ] **Step 2: Run tests to verify the new section fails**

Run: `bash statusline/scripts/test.sh`
Expected: FAIL in the `lib-settings` section (`lib-settings.sh` not found when sourced).

- [ ] **Step 3: Write the library**

Create `statusline/scripts/lib-settings.sh`:

```bash
#!/usr/bin/env bash
# Shared helpers: read/patch ~/.claude/settings.json and track whether THIS
# plugin owns the current statusLine entry. Source this file; do not execute.
# Test overrides: STATUSLINE_SETTINGS, STATUSLINE_DATA, STATUSLINE_ROOT.

settings_path() { printf '%s' "${STATUSLINE_SETTINGS:-$HOME/.claude/settings.json}"; }
owned_path()    { printf '%s' "${STATUSLINE_DATA:-$CLAUDE_PLUGIN_DATA}/owned.json"; }
plugin_root()   { printf '%s' "${STATUSLINE_ROOT:-$CLAUDE_PLUGIN_ROOT}"; }

build_command() {
  # $1 root, $2 icons(nerd|ascii)
  printf 'STATUSLINE_ICONS=%s "%s/scripts/statusline.sh"' "${2:-nerd}" "$1"
}

read_statusline_command() {
  _sp=$(settings_path)
  [ -f "$_sp" ] || return 0
  jq -r '.statusLine.command // empty' "$_sp" 2>/dev/null
}

write_statusline_command() {
  _sp=$(settings_path)
  mkdir -p "$(dirname "$_sp")"
  [ -f "$_sp" ] || printf '{}\n' > "$_sp"
  _tmp="${_sp}.tmp.$$"
  jq --arg cmd "$1" '.statusLine = {type:"command", command:$cmd}' "$_sp" > "$_tmp" && mv "$_tmp" "$_sp"
}

remove_statusline() {
  _sp=$(settings_path)
  [ -f "$_sp" ] || return 0
  _tmp="${_sp}.tmp.$$"
  jq 'del(.statusLine)' "$_sp" > "$_tmp" && mv "$_tmp" "$_sp"
}

backup_settings() {
  _sp=$(settings_path)
  [ -f "$_sp" ] && cp "$_sp" "${_sp}.bak"
  return 0
}

restore_settings_backup() {
  _sp=$(settings_path)
  [ -f "${_sp}.bak" ] && mv "${_sp}.bak" "$_sp"
  return 0
}

owned_get_command() {
  _op=$(owned_path)
  [ -f "$_op" ] || return 0
  jq -r '.command // empty' "$_op" 2>/dev/null
}

owned_get_icons() {
  _op=$(owned_path)
  if [ ! -f "$_op" ]; then printf 'nerd'; return 0; fi
  _i=$(jq -r '.icons // empty' "$_op" 2>/dev/null)
  if [ -n "$_i" ]; then printf '%s' "$_i"; else printf 'nerd'; fi
}

owned_write() {
  _op=$(owned_path)
  mkdir -p "$(dirname "$_op")"
  jq -n --arg cmd "$1" --arg icons "$2" '{command:$cmd, icons:$icons}' > "$_op"
}

owned_clear() {
  rm -f "$(owned_path)"
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `bash statusline/scripts/test.sh`
Expected: `lib-settings` assertions `ok`, `FAIL=0`.

- [ ] **Step 5: Commit**

```bash
git add statusline/scripts/lib-settings.sh statusline/scripts/test.sh
git commit -m "feat(statusline): settings.json + ownership helper library"
```

---

### Task 4: `sync.sh` SessionStart hook + `hooks.json`

**Files:**
- Create: `statusline/scripts/sync.sh`
- Create: `statusline/hooks/hooks.json`
- Modify: `statusline/scripts/test.sh` (add sync section)

**Interfaces:**
- Consumes: `lib-settings.sh` functions; env `CLAUDE_PLUGIN_ROOT` (or `STATUSLINE_ROOT`), `CLAUDE_PLUGIN_DATA` (or `STATUSLINE_DATA`).
- Produces: on SessionStart, re-pins `.statusLine.command` to `build_command(plugin_root, owned_icons)` ONLY when the current entry equals the recorded owned command; otherwise leaves settings untouched. Never adds an entry when none exists.

- [ ] **Step 1: Write the failing tests**

Append to `statusline/scripts/test.sh` before the final summary lines:

```bash
echo "== sync =="
run_sync() {
  # $1 settings-dir sentinel; uses a fresh temp env each call
  TMP=$(mktemp -d)
  SET="$TMP/settings.json"; DATA="$TMP/data"; NEWROOT="/opt/plugins/statusline-v2"
  NEWCMD='STATUSLINE_ICONS=nerd "/opt/plugins/statusline-v2/scripts/statusline.sh"'
  OLDCMD='STATUSLINE_ICONS=nerd "/opt/plugins/statusline-v1/scripts/statusline.sh"'
}

# Case A: no statusLine present -> stays empty
run_sync
printf '{}\n' > "$SET"
STATUSLINE_SETTINGS="$SET" STATUSLINE_DATA="$DATA" STATUSLINE_ROOT="$NEWROOT" bash "$ROOT/scripts/sync.sh"
assert_equals "" "$(STATUSLINE_SETTINGS="$SET" jq -r '.statusLine.command // empty' "$SET")" "sync: empty stays empty"
rm -rf "$TMP"

# Case B: ours but stale path -> re-pinned to new root
run_sync
mkdir -p "$DATA"
jq -n --arg c "$OLDCMD" '{statusLine:{type:"command",command:$c}}' > "$SET"
jq -n --arg c "$OLDCMD" '{command:$c, icons:"nerd"}' > "$DATA/owned.json"
STATUSLINE_SETTINGS="$SET" STATUSLINE_DATA="$DATA" STATUSLINE_ROOT="$NEWROOT" bash "$ROOT/scripts/sync.sh"
assert_equals "$NEWCMD" "$(jq -r '.statusLine.command' "$SET")" "sync: stale ours re-pinned"
assert_equals "$NEWCMD" "$(jq -r '.command' "$DATA/owned.json")" "sync: owned.json updated"
rm -rf "$TMP"

# Case C: foreign statusLine -> untouched
run_sync
mkdir -p "$DATA"
jq -n '{statusLine:{type:"command",command:"~/my/other.sh"}}' > "$SET"
jq -n --arg c "$OLDCMD" '{command:$c, icons:"nerd"}' > "$DATA/owned.json"
STATUSLINE_SETTINGS="$SET" STATUSLINE_DATA="$DATA" STATUSLINE_ROOT="$NEWROOT" bash "$ROOT/scripts/sync.sh"
assert_equals "~/my/other.sh" "$(jq -r '.statusLine.command' "$SET")" "sync: foreign untouched"
rm -rf "$TMP"
```

- [ ] **Step 2: Run tests to verify the sync section fails**

Run: `bash statusline/scripts/test.sh`
Expected: FAIL in the `sync` section (`sync.sh` not found).

- [ ] **Step 3: Write the hook script**

Create `statusline/scripts/sync.sh`:

```bash
#!/usr/bin/env bash
# SessionStart hook: re-pin the statusLine to the current absolute plugin path,
# but ONLY if the existing entry is one we previously wrote. Never adds a
# statusLine when none exists; never overwrites a foreign one.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
. "$DIR/lib-settings.sh"

command -v jq >/dev/null 2>&1 || exit 0

icons=$(owned_get_icons)
computed=$(build_command "$(plugin_root)" "$icons")
current=$(read_statusline_command)
owned=$(owned_get_command)

# Nothing configured -> never silently add one.
if [ -z "$current" ]; then exit 0; fi
# Already correct.
if [ "$current" = "$computed" ]; then exit 0; fi
# Ours but stale (plugin path changed after an update) -> re-pin.
if [ -n "$owned" ] && [ "$current" = "$owned" ]; then
  write_statusline_command "$computed"
  owned_write "$computed" "$icons"
fi
exit 0
```

- [ ] **Step 4: Write the hook manifest**

Create `statusline/hooks/hooks.json`:

```json
{
  "description": "Re-pins the statusline plugin's absolute path in settings.json each session.",
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/sync.sh",
            "timeout": 15
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 5: Make executable, validate JSON, run tests**

Run: `chmod +x statusline/scripts/sync.sh && jq empty statusline/hooks/hooks.json && bash statusline/scripts/test.sh`
Expected: `hooks.json` valid; all `sync` assertions `ok`; `FAIL=0`.

- [ ] **Step 6: Commit**

```bash
git add statusline/scripts/sync.sh statusline/hooks/hooks.json statusline/scripts/test.sh
git commit -m "feat(statusline): SessionStart re-pin hook (ownership-checked)"
```

---

### Task 5: `setup.sh` + slash commands

**Files:**
- Create: `statusline/scripts/setup.sh`
- Create: `statusline/commands/statusline-setup.md`
- Create: `statusline/commands/statusline-uninstall.md`
- Modify: `statusline/scripts/test.sh` (add setup section)

**Interfaces:**
- Consumes: `lib-settings.sh`.
- Produces: `setup.sh <status|install|uninstall> [--ascii|--nerd] [--force]`:
  - `status` → prints `state: none|ours|foreign` (and `current: <cmd>` when foreign).
  - `install` → installs when none/ours; over a foreign entry, exits 2 unless `--force` (which backs up first). Records ownership.
  - `uninstall` → removes our entry (restoring `.bak` if present) and clears ownership; leaves a foreign entry untouched.

- [ ] **Step 1: Write the failing tests**

Append to `statusline/scripts/test.sh` before the final summary lines:

```bash
echo "== setup =="
S="$ROOT/scripts/setup.sh"

# install onto empty
TMP=$(mktemp -d); SET="$TMP/settings.json"; DATA="$TMP/data"; RT="/opt/plugins/statusline"
printf '{}\n' > "$SET"
STATUSLINE_SETTINGS="$SET" STATUSLINE_DATA="$DATA" STATUSLINE_ROOT="$RT" bash "$S" install >/dev/null
assert_equals 'STATUSLINE_ICONS=nerd "/opt/plugins/statusline/scripts/statusline.sh"' \
  "$(jq -r '.statusLine.command' "$SET")" "setup: install onto empty"
st=$(STATUSLINE_SETTINGS="$SET" STATUSLINE_DATA="$DATA" STATUSLINE_ROOT="$RT" bash "$S" status)
assert_contains "state: ours" "$st" "setup: status reports ours"
rm -rf "$TMP"

# install refuses foreign without --force
TMP=$(mktemp -d); SET="$TMP/settings.json"; DATA="$TMP/data"; RT="/opt/plugins/statusline"
jq -n '{statusLine:{type:"command",command:"~/foreign.sh"}}' > "$SET"
set +e
STATUSLINE_SETTINGS="$SET" STATUSLINE_DATA="$DATA" STATUSLINE_ROOT="$RT" bash "$S" install >/dev/null 2>&1
rc=$?
set -e 2>/dev/null || true
assert_equals "2" "$rc" "setup: install refuses foreign (exit 2)"
assert_equals "~/foreign.sh" "$(jq -r '.statusLine.command' "$SET")" "setup: foreign untouched without force"
rm -rf "$TMP"

# install --force replaces foreign and backs up
TMP=$(mktemp -d); SET="$TMP/settings.json"; DATA="$TMP/data"; RT="/opt/plugins/statusline"
jq -n '{statusLine:{type:"command",command:"~/foreign.sh"}}' > "$SET"
STATUSLINE_SETTINGS="$SET" STATUSLINE_DATA="$DATA" STATUSLINE_ROOT="$RT" bash "$S" install --force >/dev/null
assert_contains "statusline.sh" "$(jq -r '.statusLine.command' "$SET")" "setup: --force replaced foreign"
assert_equals "~/foreign.sh" "$(jq -r '.statusLine.command' "$SET.bak")" "setup: --force backed up original"
rm -rf "$TMP"

# install --ascii records ascii
TMP=$(mktemp -d); SET="$TMP/settings.json"; DATA="$TMP/data"; RT="/opt/plugins/statusline"
printf '{}\n' > "$SET"
STATUSLINE_SETTINGS="$SET" STATUSLINE_DATA="$DATA" STATUSLINE_ROOT="$RT" bash "$S" install --ascii >/dev/null
assert_contains "STATUSLINE_ICONS=ascii" "$(jq -r '.statusLine.command' "$SET")" "setup: --ascii selected"
rm -rf "$TMP"

# uninstall removes ours
TMP=$(mktemp -d); SET="$TMP/settings.json"; DATA="$TMP/data"; RT="/opt/plugins/statusline"
printf '{}\n' > "$SET"
STATUSLINE_SETTINGS="$SET" STATUSLINE_DATA="$DATA" STATUSLINE_ROOT="$RT" bash "$S" install >/dev/null
STATUSLINE_SETTINGS="$SET" STATUSLINE_DATA="$DATA" STATUSLINE_ROOT="$RT" bash "$S" uninstall >/dev/null
assert_equals "" "$(jq -r '.statusLine.command // empty' "$SET")" "setup: uninstall removed ours"
rm -rf "$TMP"
```

- [ ] **Step 2: Run tests to verify the setup section fails**

Run: `bash statusline/scripts/test.sh`
Expected: FAIL in the `setup` section (`setup.sh` not found).

- [ ] **Step 3: Write `setup.sh`**

Create `statusline/scripts/setup.sh`:

```bash
#!/usr/bin/env bash
# /statusline-setup and /statusline-uninstall helper.
# Usage: setup.sh <status|install|uninstall> [--ascii|--nerd] [--force]
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
. "$DIR/lib-settings.sh"
command -v jq >/dev/null 2>&1 || { echo "ERROR: jq not found — install jq first."; exit 1; }

ICONS="nerd"; force=""; cmd="status"
for a in "$@"; do
  case "$a" in
    --ascii) ICONS="ascii" ;;
    --nerd)  ICONS="nerd" ;;
    --force) force="1" ;;
    status|install|uninstall) cmd="$a" ;;
    *) : ;;
  esac
done

computed=$(build_command "$(plugin_root)" "$ICONS")
current=$(read_statusline_command)
owned=$(owned_get_command)

is_ours() { [ -n "$current" ] && { [ "$current" = "$owned" ] || [ "$current" = "$computed" ]; }; }

case "$cmd" in
  status)
    if [ -z "$current" ]; then echo "state: none";
    elif is_ours; then echo "state: ours";
    else echo "state: foreign"; echo "current: $current"; fi
    ;;
  install)
    if [ -z "$current" ] || is_ours; then
      write_statusline_command "$computed"; owned_write "$computed" "$ICONS"
      echo "installed: $computed"
      echo "Takes effect in new sessions."
    elif [ -n "$force" ]; then
      backup_settings
      write_statusline_command "$computed"; owned_write "$computed" "$ICONS"
      echo "replaced foreign statusline (backup: $(settings_path).bak)"
      echo "installed: $computed"
    else
      echo "A different statusline is already configured."
      echo "current: $current"
      echo "Re-run with --force to replace it (a backup will be made)."
      exit 2
    fi
    ;;
  uninstall)
    if [ -z "$current" ]; then
      owned_clear; echo "no statusline configured; nothing to remove."
    elif is_ours; then
      remove_statusline
      if [ -f "$(settings_path).bak" ]; then
        restore_settings_backup; echo "removed; restored previous statusline from backup."
      else
        echo "removed the statusline plugin's entry."
      fi
      owned_clear
    else
      echo "the current statusline is not ours; leaving it untouched."
      echo "current: $current"
    fi
    ;;
esac
```

- [ ] **Step 4: Write the setup command**

Create `statusline/commands/statusline-setup.md`:

```md
---
description: Install (or re-pin) the statusline plugin into your Claude Code settings
allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh:*)
---
Set up the `statusline` plugin. Optional `$ARGUMENTS`: `--ascii` (ASCII icons instead of Nerd Font) or `--force` (replace an existing foreign statusline).

Interpret the output below:
- If it reports a different statusline is already configured (exit note about `--force`) and the user did NOT pass `--force`, STOP: show them the `current:` line and ask whether to replace it (their original is backed up to `settings.json.bak`). Only after they confirm, run `"${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh" install --force` (add `--ascii` if they wanted it) via the Bash tool.
- Otherwise, confirm what was installed and remind them it takes effect in new sessions.

!`"${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh" install $ARGUMENTS`
```

- [ ] **Step 5: Write the uninstall command**

Create `statusline/commands/statusline-uninstall.md`:

```md
---
description: Remove the statusline plugin's entry from your Claude Code settings
allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh:*)
---
Remove the `statusline` plugin's statusLine entry from settings.json. It is removed only if this plugin owns it (a previously backed-up statusline is restored). Run this BEFORE `/plugin uninstall` to avoid leaving a dangling statusLine command. Relay the result below to the user.

!`"${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh" uninstall`
```

- [ ] **Step 6: Make executable and run tests**

Run: `chmod +x statusline/scripts/setup.sh && bash statusline/scripts/test.sh`
Expected: all sections `ok`; final line `PASS=<n> FAIL=0`.

- [ ] **Step 7: Commit**

```bash
git add statusline/scripts/setup.sh statusline/commands/statusline-setup.md statusline/commands/statusline-uninstall.md statusline/scripts/test.sh
git commit -m "feat(statusline): setup/uninstall helper and slash commands"
```

---

### Task 6: README & final validation

**Files:**
- Create: `statusline/README.md`

**Interfaces:**
- Produces: user-facing install/usage/uninstall docs; final green test run.

- [ ] **Step 1: Write the README**

Create `statusline/README.md`:

```md
# statusline

A polished Claude Code statusline: current directory, git branch (with dirty marker),
model, reasoning effort, an 8-segment context-window bar, and a 5-hour rate-limit bar
with reset time. Nerd Font icons by default, with an ASCII fallback.

## Requirements

- `jq` (required). Without it the statusline prints a one-line hint instead of rendering.
- A Nerd Font in your terminal for the default icons — or use `--ascii`.

## Install

```
/plugin marketplace add Jo-Jee/claude-plugins
/plugin install statusline@jojee-tools
/statusline-setup           # or: /statusline-setup --ascii
```

`/statusline-setup` writes a `statusLine` entry into `~/.claude/settings.json`. It never
overwrites an existing statusline without asking (your original is backed up to
`settings.json.bak`). A SessionStart hook re-pins the path automatically after plugin
updates. The statusline appears in new sessions.

## Uninstall

```
/statusline-uninstall       # run this FIRST — removes our settings.json entry
/plugin uninstall statusline@jojee-tools
```

`/statusline-uninstall` removes the entry only if this plugin owns it, restoring any
statusline it previously replaced.

## Notes

Claude Code plugins cannot declare a main `statusLine` directly, and
`${CLAUDE_PLUGIN_ROOT}` does not expand in the statusline execution context — so this
plugin writes an absolute path into your settings and re-pins it each session.
```

- [ ] **Step 2: Run the full test suite**

Run: `bash statusline/scripts/test.sh`
Expected: `PASS=<n> FAIL=0` (exit 0).

- [ ] **Step 3: Validate all JSON and manifests**

Run:
```bash
for f in statusline/.claude-plugin/plugin.json statusline/hooks/hooks.json .claude-plugin/marketplace.json; do jq empty "$f" && echo "ok $f"; done
```
Expected: `ok` for all three.

- [ ] **Step 4: Smoke-test the renderer end-to-end**

Run:
```bash
printf '{"cwd":"%s","model":{"display_name":"Opus 4.8"},"context_window":{"used_percentage":42},"rate_limits":{"five_hour":{"used_percentage":30,"resets_at":0}},"effort":{"level":"high"}}' "$HOME" | STATUSLINE_ICONS=ascii sh statusline/scripts/statusline.sh; echo
```
Expected: a two-line statusline containing `~`, `Opus 4.8`, `ctx … 42%`, `5h 30%`, `high`.

- [ ] **Step 5: Commit**

```bash
git add statusline/README.md
git commit -m "docs(statusline): add README with install/uninstall guide"
```

---

## Self-Review

**Spec coverage:**
- Architecture & file layout → Tasks 1–6 create every file in the spec's layout. ✓
- Install + collision (ownership marker, foreign prompt, backup) → Task 5 (`setup.sh` install / `--force` / status) + Task 4 (`sync.sh` re-pin only when owned). ✓
- Script hardening (jq hint, ASCII fallback) → Task 2 renderer + tests. ✓
- Uninstall / cleanup → Task 5 (`uninstall` subcommand + command md) + README guidance. ✓
- Testing (renderer golden cases + settings mutation) → `test.sh` grown across Tasks 2–5. ✓
- Marketplace entry → Task 1. ✓

**Placeholder scan:** No TBD/TODO; every step contains full file contents or exact commands with expected output. ✓

**Type/name consistency:** Helper names (`build_command`, `read_statusline_command`, `write_statusline_command`, `owned_write`, `owned_get_command`, `owned_get_icons`, `remove_statusline`, `backup_settings`, `restore_settings_backup`, `owned_clear`) are defined in Task 3 and used identically in Tasks 4–5. Command-string format identical across `build_command`, sync tests, and setup tests. Env overrides (`STATUSLINE_SETTINGS`/`DATA`/`ROOT`) consistent throughout. ✓
