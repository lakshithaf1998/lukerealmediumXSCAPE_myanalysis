#!/usr/bin/env bash
# unixer.sh — normalize line endings and fix exec bits (Warrior-safe)
#
# HOW TO RUN:
#   # From your jetscape repo root:
#   ./unixer.sh
#
#   # Dry run (show what would change, do nothing):
#   DRY_RUN=1 ./unixer.sh
#
#   # Quiet mode (only final summary):
#   QUIET=1 ./unixer.sh
#
# WHAT IT DOES:
#   • Converts CRLF → LF *only when needed* for:  *.sh  *.slurm  *.ini
#     (skips .git and build/)
#   • Uses 'dos2unix' if available; otherwise a safe Perl fallback
#   • chmod +x for *.sh files that aren’t executable yet
#   • By default, prints EVERY file it converted and chmod’d
#
# NOTE: This is a tiny maintenance task — fine to run on Warrior (head node).

set -euo pipefail

ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$ROOT"

DRY="${DRY_RUN:-0}"
QUIET="${QUIET:-0}"

say() { [[ "$QUIET" == "1" ]] || echo "$@"; }
log() { say "[$(date +'%F %T')] $*"; }
have() { command -v "$1" >/dev/null 2>&1; }

# Detect CRLF only for text files
file_has_crlf() {
  grep -Iq . "$1" 2>/dev/null && LC_ALL=C grep -q $'\r' "$1"
}

converted_list=()
chmod_list=()

convert_file() {
  local f="$1"
  if file_has_crlf "$f"; then
    if [[ "$DRY" == "1" ]]; then
      say "convert: $f"
      converted_list+=("$f")
      return
    fi
    if have dos2unix; then
      dos2unix -f -q "$f" >/dev/null 2>&1 || true
    else
      perl -pi -e 's/\r$//' "$f"
    fi
    say "convert: $f"
    converted_list+=("$f")
  fi
}

ensure_exec() {
  local f="$1"
  if [[ ! -x "$f" ]]; then
    if [[ "$DRY" == "1" ]]; then
      say "chmod +x: $f"
      chmod_list+=("$f")
      return
    fi
    chmod +x "$f"
    say "chmod +x: $f"
    chmod_list+=("$f")
  fi
}

log "Normalizing *.sh, *.slurm, *.ini under $(pwd)"

# Find helper (portable; avoids 'mapfile -d')
find_nul() {
  # $1 = pattern (e.g., '*.sh')
  find . \
    -path './.git' -prune -o \
    -path './build' -prune -o \
    -type f -name "$1" -print0
}

# Convert line endings where needed
while IFS= read -r -d '' f; do convert_file "$f"; done < <(find_nul '*.sh')
while IFS= read -r -d '' f; do convert_file "$f"; done < <(find_nul '*.slurm')
while IFS= read -r -d '' f; do convert_file "$f"; done < <(find_nul '*.ini')

# Fix exec bits on shell scripts
while IFS= read -r -d '' f; do ensure_exec "$f"; done < <(find_nul '*.sh')

# Summary
echo
echo "====== unixer summary ======"
printf "converted (CRLF→LF): %d file(s)\n" "${#converted_list[@]}"
((${#converted_list[@]})) && printf '  - %s\n' "${converted_list[@]}"
printf "chmod +x applied to: %d file(s)\n" "${#chmod_list[@]}"
((${#chmod_list[@]})) && printf '  - %s\n' "${chmod_list[@]}"
echo "============================"
