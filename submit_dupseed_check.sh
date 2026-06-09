#!/usr/bin/env bash
# submit_dupseed_check.sh
# Version: v1.3
#
# Change log:
#  - v1.3 (2026-03-01):
#      * Force tools logs under $HOME/xscape_runs/<RUN_TAG>/logs/tools (matches your workflow convention),
#        ignoring RUNS_BASE (which may point elsewhere or include literal tokens).
#      * Print the resolved log directory to make "where are my logs" obvious.
#  - v1.2 (2026-03-01): Fix broken quote-stripping in ini_get (prevents EOF parse error).
#  - v1.1 (2026-03-01): Expand $HOME/${RUN_TAG} tokens from jetscape.ini RUNS_BASE; avoid double-appending RUN_TAG.
#  - v1.0 (2026-03-01): Submit duplicate-seed check to a compute node (primary QoS).
#
# Purpose:
#  - Run from HEAD node. Submits a tiny Slurm job to run detect_duplicate_seeds.py on a compute node.
#
# Usage:
#  ./submit_dupseed_check.sh [path/to/jetscape.ini]
#
# Outputs:
#  - Logs: $HOME/xscape_runs/<RUN_TAG>/logs/tools/dupseed_check_<jobid>.out/.err

set -euo pipefail

INI_PATH="${1:-jetscape.ini}"
if [[ ! -f "$INI_PATH" ]]; then
  echo "[dupseed-submit] ERROR: INI not found: $INI_PATH" >&2
  exit 2
fi

ini_get() {
  local key="$1"
  local file="$2"
  local line val
  line="$(grep -E "^[[:space:]]*${key}[[:space:]]*=" "$file" | head -n 1 || true)"
  [[ -z "$line" ]] && return 1
  val="${line#*=}"
  val="${val%%#*}"
  val="$(echo "$val" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')"
  val="${val%\"}"; val="${val#\"}"
  val="${val%\'}"; val="${val#\'}"
  echo "$val"
}

RUN_TAG="$(ini_get RUN_TAG "$INI_PATH" 2>/dev/null || true)"
[[ -z "${RUN_TAG:-}" ]] && RUN_TAG="UNKNOWN_RUN_TAG"

# ✅ Stable tool log root (your preferred convention)
TOOLS_LOG_DIR="$HOME/xscape_runs/$RUN_TAG/logs/tools"
mkdir -p "$TOOLS_LOG_DIR"

OUT_LOG="${TOOLS_LOG_DIR}/dupseed_check_%j.out"
ERR_LOG="${TOOLS_LOG_DIR}/dupseed_check_%j.err"

echo "[dupseed-submit] INI_PATH=$INI_PATH"
echo "[dupseed-submit] RUN_TAG=$RUN_TAG"
echo "[dupseed-submit] Tools log dir: $TOOLS_LOG_DIR"
echo "[dupseed-submit] Logs: $OUT_LOG / $ERR_LOG"
echo "[dupseed-submit] NOTE: dupseed_check.slurm omits --partition (site default)."

sbatch   --export=ALL,INI_PATH="$INI_PATH"   --output="$OUT_LOG"   --error="$ERR_LOG"   dupseed_check.slurm

echo "[dupseed-submit] Submitted."
