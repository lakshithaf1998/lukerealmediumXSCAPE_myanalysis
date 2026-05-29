#!/usr/bin/env bash
# create_github_repo_from_myanalysis.sh v1.0
# Patch notes:
# - v1.0: Creates a standalone GitHub repository from the current myanalysis folder contents only.
# - v1.0: Does not push the full X-SCAPE source tree or run logs.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MYANALYSIS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DEFAULT_REPO_NAME="lukerealmediumXSCAPE_myanalysis"
REPO_NAME="${1:-$DEFAULT_REPO_NAME}"
VISIBILITY="${VISIBILITY:---private}"
STAMP="$(date +%Y%m%d_%H%M%S)"
TMP_REPO="${TMPDIR:-/tmp}/myanalysis_github_push_${STAMP}"

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: GitHub CLI 'gh' was not found. Install it or create the repo manually on github.com." >&2
  exit 2
fi
if ! gh auth status >/dev/null 2>&1; then
  echo "ERROR: gh is not authenticated. Run: gh auth login" >&2
  exit 2
fi
if ! command -v git >/dev/null 2>&1; then
  echo "ERROR: git was not found." >&2
  exit 2
fi

mkdir -p "$TMP_REPO"
rsync -a   --exclude '.git'   --exclude '__MACOSX'   --exclude '.DS_Store'   --exclude 'run_logs'   --exclude 'diagnostic_zips'   "$MYANALYSIS_DIR"/ "$TMP_REPO"/

cd "$TMP_REPO"
git init -q
git add .
git commit -m "Add Luke realistic pp myanalysis v10.7" >/dev/null

echo "Creating/pushing GitHub repo: $REPO_NAME"
gh repo create "$REPO_NAME" "$VISIBILITY" --source "$TMP_REPO" --remote origin --push

echo "DONE: pushed myanalysis contents to $REPO_NAME"
echo "Temporary repo copy: $TMP_REPO"
