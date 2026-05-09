#!/usr/bin/env bash
# render-cli.sh — wrapper for Render API operations
#
# Usage:
#   ./scripts/render-cli.sh <command> [args...]
#
# Commands:
#   services                     List all services with id, name, type, status
#   service <name|id>            Get service detail
#   env <name|id>                Show env vars for a service
#   set-env <name|id> KEY VALUE  Set/update one env var (preserves others)
#   deploys <name|id>            List recent deploys for a service
#   deploy <name|id> <deploy_id> Get one deploy detail
#   logs <name|id> [tail_lines]  Get recent build/deploy logs (default 200 lines)
#   redeploy <name|id>           Trigger a manual redeploy
#   sync                         Trigger a blueprint manual sync
#   blueprints                   List blueprints
#   ids                          Cache and print all service IDs (saves to ~/.revelio_render_ids)
#
# Setup (one-time):
#   echo "RENDER_API_KEY=rnd_xxx..." > ~/.revelio_render_key
#   chmod 600 ~/.revelio_render_key
#
# Requires: curl, jq

set -euo pipefail

KEY_FILE="$HOME/.revelio_render_key"
ID_CACHE="$HOME/.revelio_render_ids"
BASE="https://api.render.com/v1"
BLUEPRINT_ID="exs-d7vg8br7uimc73eo0a0g"

# ─── Auth ──────────────────────────────────────────────
if [ ! -f "$KEY_FILE" ]; then
  echo "Error: ~/.revelio_render_key not found." >&2
  echo "Create it with:" >&2
  echo "  echo 'RENDER_API_KEY=rnd_yourkey' > ~/.revelio_render_key" >&2
  echo "  chmod 600 ~/.revelio_render_key" >&2
  exit 1
fi
KEY=$(grep '^RENDER_API_KEY=' "$KEY_FILE" | cut -d= -f2-)
if [ -z "$KEY" ]; then
  echo "Error: RENDER_API_KEY not set in $KEY_FILE" >&2
  exit 1
fi

AUTH=(-H "Authorization: Bearer $KEY")
JSON=(-H "Content-Type: application/json")

# ─── Helpers ───────────────────────────────────────────
need() {
  command -v "$1" >/dev/null 2>&1 || { echo "Error: $1 not installed" >&2; exit 1; }
}
need curl
need jq

# Resolve a service name or ID to an ID. Caches in ~/.revelio_render_ids.
resolve_id() {
  local input="$1"
  # If it already looks like a Render service ID, return as-is
  if [[ "$input" =~ ^srv- ]]; then
    echo "$input"
    return
  fi
  # Try cache
  if [ -f "$ID_CACHE" ]; then
    local hit
    hit=$(grep "^$input=" "$ID_CACHE" 2>/dev/null | cut -d= -f2 || true)
    if [ -n "$hit" ]; then
      echo "$hit"
      return
    fi
  fi
  # Refresh cache and retry
  cmd_ids >/dev/null
  if [ -f "$ID_CACHE" ]; then
    local hit
    hit=$(grep "^$input=" "$ID_CACHE" 2>/dev/null | cut -d= -f2 || true)
    if [ -n "$hit" ]; then
      echo "$hit"
      return
    fi
  fi
  echo "Error: could not resolve '$input' to a service ID" >&2
  exit 1
}

# ─── Commands ──────────────────────────────────────────
cmd_services() {
  curl -sS "${AUTH[@]}" "$BASE/services?limit=50" \
    | jq -r '.[] | [.service.id, .service.name, .service.type, (.service.suspended // "running")] | @tsv' \
    | column -t -s $'\t'
}

cmd_ids() {
  local raw
  raw=$(curl -sS "${AUTH[@]}" "$BASE/services?limit=50")
  echo "$raw" | jq -r '.[] | "\(.service.name)=\(.service.id)"' > "$ID_CACHE"
  echo "Cached $(wc -l < "$ID_CACHE" | tr -d ' ') service IDs to $ID_CACHE"
  cat "$ID_CACHE"
}

cmd_service() {
  local id; id=$(resolve_id "$1")
  curl -sS "${AUTH[@]}" "$BASE/services/$id" | jq
}

cmd_env() {
  local id; id=$(resolve_id "$1")
  curl -sS "${AUTH[@]}" "$BASE/services/$id/env-vars" \
    | jq -r '.[] | "\(.envVar.key)=\(.envVar.value // "(empty)")"'
}

cmd_set_env() {
  local id; id=$(resolve_id "$1"); shift
  local key="$1"; shift
  local value="$1"
  # Render's PUT replaces the entire env-vars list, so we read existing first then merge
  local existing
  existing=$(curl -sS "${AUTH[@]}" "$BASE/services/$id/env-vars" \
    | jq '[.[].envVar | {key, value}]')
  local updated
  updated=$(echo "$existing" | jq --arg k "$key" --arg v "$value" '
    map(if .key == $k then .value = $v else . end)
    | if (map(.key) | index($k)) then . else . + [{key: $k, value: $v}] end
  ')
  echo "Updating $key on $id..."
  curl -sS -X PUT "${AUTH[@]}" "${JSON[@]}" "$BASE/services/$id/env-vars" \
    -d "$updated" | jq
}

cmd_deploys() {
  local id; id=$(resolve_id "$1")
  curl -sS "${AUTH[@]}" "$BASE/services/$id/deploys?limit=10" \
    | jq -r '.[] | [.deploy.id, .deploy.status, (.deploy.commit.id // "?" | .[0:7]), .deploy.createdAt] | @tsv' \
    | column -t -s $'\t'
}

cmd_deploy() {
  local id; id=$(resolve_id "$1")
  local dep_id="$2"
  curl -sS "${AUTH[@]}" "$BASE/services/$id/deploys/$dep_id" | jq
}

cmd_logs() {
  local id; id=$(resolve_id "$1")
  local tail_n="${2:-200}"
  # Render's logs API
  local now; now=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  local since; since=$(date -u -v-2H +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '2 hours ago' +%Y-%m-%dT%H:%M:%SZ)
  curl -sS "${AUTH[@]}" "$BASE/logs?ownerId=$(get_owner_id)&resource=$id&startTime=$since&endTime=$now&limit=$tail_n" \
    | jq -r '.logs[] | "\(.timestamp)  \(.message)"' \
    | tail -n "$tail_n"
}

get_owner_id() {
  # Owner ID = workspace ID, returned with services
  curl -sS "${AUTH[@]}" "$BASE/services?limit=1" | jq -r '.[0].service.ownerId'
}

cmd_redeploy() {
  local id; id=$(resolve_id "$1")
  echo "Triggering redeploy on $id..."
  curl -sS -X POST "${AUTH[@]}" "${JSON[@]}" "$BASE/services/$id/deploys" \
    -d '{"clearCache": "do_not_clear"}' | jq
}

cmd_sync() {
  echo "Triggering blueprint sync on $BLUEPRINT_ID..."
  curl -sS -X POST "${AUTH[@]}" "$BASE/blueprints/$BLUEPRINT_ID/syncs" | jq
}

cmd_blueprints() {
  curl -sS "${AUTH[@]}" "$BASE/blueprints" | jq
}

# ─── Dispatcher ────────────────────────────────────────
cmd="${1:-help}"
shift || true

case "$cmd" in
  services)   cmd_services ;;
  service)    cmd_service "$@" ;;
  env)        cmd_env "$@" ;;
  set-env)    cmd_set_env "$@" ;;
  deploys)    cmd_deploys "$@" ;;
  deploy)     cmd_deploy "$@" ;;
  logs)       cmd_logs "$@" ;;
  redeploy)   cmd_redeploy "$@" ;;
  sync)       cmd_sync ;;
  blueprints) cmd_blueprints ;;
  ids)        cmd_ids ;;
  help|*)
    grep '^# ' "$0" | sed 's/^# //' | head -30
    ;;
esac
