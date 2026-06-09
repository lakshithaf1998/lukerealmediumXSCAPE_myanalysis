#!/usr/bin/env bash
# dupseed_check.slurm
# Version: v1.3
#
# Change log:
#  - v1.3 (2026-03-01):
#      * Fix missing script path on compute nodes: use $SLURM_SUBMIT_DIR to locate detect_duplicate_seeds.py
#        instead of relying on the Slurm spool directory.
#      * Only chmod if the file exists.
#  - v1.2 (2026-03-01): Omit --partition (site default) to avoid invalid-partition errors on WSU; keep qos=primary.
#
# Exit codes:
#  - 0: no duplicates
#  - 1: duplicates found
#  - 2: error

#SBATCH --job-name=dupseed_check
#SBATCH --qos=primary
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=200M
#SBATCH --time=00:05:00

set -euo pipefail

echo "[dupseed] Host: $(hostname)"
echo "[dupseed] PWD(before):  $(pwd)"
echo "[dupseed] Date: $(date -Is)"
echo "[dupseed] INI_PATH=${INI_PATH:-jetscape.ini}"
echo "[dupseed] SLURM_SUBMIT_DIR=${SLURM_SUBMIT_DIR:-<unset>}"

# Ensure we're in the directory where you launched sbatch (your xscape folder)
if [[ -n "${SLURM_SUBMIT_DIR:-}" ]]; then
  cd "$SLURM_SUBMIT_DIR"
fi
echo "[dupseed] PWD(after):   $(pwd)"

PY="${SLURM_SUBMIT_DIR:-$(pwd)}/detect_duplicate_seeds.py"

if [[ ! -f "$PY" ]]; then
  echo "[dupseed] ERROR: detect_duplicate_seeds.py not found at: $PY" >&2
  exit 2
fi

if [[ ! -x "$PY" ]]; then
  chmod +x "$PY" || true
fi

python3 "$PY" --ini "${INI_PATH:-jetscape.ini}" --ignore-na
