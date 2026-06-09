#!/usr/bin/env bash
# python_fit.slurm  v1.6
# CHANGELOG
# v1.6 (single-slice selected-dijet preflight):
#   • FIX: Validate the published selected_dijet_counts_summary.json contract on the compute node when SINGLE_SLICE_MODE=1 so direct slurm launches fail early with a clear message.
#   • FIX: Require exactly one configured pThat slice plus non-empty JET_RADIUS_LIST/PT_LEAD_BIN_EDGES for single-slice fitter runs, matching the fitter/comparisor assumptions.
# v1.5 (mail delegated to wrapper):
#   • FIX: Remove hardcoded SLURM mail directives so submit_python_fit.sh controls mail strictly from jetscape.ini.
# v1.4 (debug + imports):
#   • NEW: Export PYTHONPATH=${BASE_DIR} so shared helpers (xscape_ini.py) are always importable.
#   • Log any env overrides that could affect reproducibility (INCLUDE_XSEC_NORM_ERR / COVARIANCE_MODE).
#
# v1.3 (minor portability):
#   • FIX: Use whichever Python exists (python3 or python) after module load.
#   • Avoid BLAS thread oversubscription by pinning common thread env vars to 1.
#   • BASE_DIR now defaults to $PWD if SLURM_SUBMIT_DIR is unset (extra safety).
#
# v1.2 (minor robustness):
#   • Export key path variables after sourcing jetscape.ini (helps downstream tools that rely on env).
#   • Extra sanity log prints the resolved DIR_FINAL actually used.
# v1.1 (minor):
#   • X-SCAPE alignment/robustness: absolute jetscape.ini path via SLURM_SUBMIT_DIR.
#   • Python module load fallback (3.10->3.8->default) and dependency preflight check.
#   • Run dphi_fit_py.py via absolute path so it works regardless of launch directory.
#
# v1.0 (major):
#   • SLURM job to run the Python fitter on a compute node.
#   • Backs up any existing dphi_fit_summary.csv and logs steps to fit_py.log.
#   • Emits stdout/stderr to ${DIR_LOG_MERGE}/pyfit-<jobid>.{out,err}.

#SBATCH --account=wsu
#SBATCH --job-name=py_fit_dphi
#SBATCH --qos=primary
#SBATCH --mem=8G
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --time=00:30:00
#SBATCH --export=ALL

set -euo pipefail
log(){ echo "[$(date +'%F %T')] $*"; }

module purge
# Prefer a newer Python if available; fall back gracefully.
if module -q load python/3.10 2>/dev/null; then
  log "[module] loaded python/3.10"
elif module -q load python/3.8 2>/dev/null; then
  log "[module] loaded python/3.8"
elif module -q load python 2>/dev/null; then
  log "[module] loaded python (default)"
else
  log "[ERROR] Could not load a python module"
  exit 2
fi
export PYTHONUSERBASE=$HOME/.local
export PATH=$PYTHONUSERBASE/bin:$PATH

# Keep numpy/scipy from spawning extra threads on a single-core allocation.
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1

# If your environment module provides uproot/scipy/matplotlib, good.
# Otherwise, ensure your site Python has them in PYTHONPATH beforehand.

BASE_DIR="${SLURM_SUBMIT_DIR:-$(pwd)}"
source "${BASE_DIR}/jetscape.ini"

# Ensure repo-root helpers are importable by Python scripts called via absolute paths.
export PYTHONPATH="${BASE_DIR}:${PYTHONPATH:-}"

# Reproducibility overrides (env vars are allowed, but we log them loudly).
[[ -n "${INCLUDE_XSEC_NORM_ERR:-}" ]] && log "[env] INCLUDE_XSEC_NORM_ERR=${INCLUDE_XSEC_NORM_ERR}" || true
[[ -n "${COVARIANCE_MODE:-}" ]] && log "[env] COVARIANCE_MODE=${COVARIANCE_MODE}" || true
[[ -n "${PERDIJET_COV_MODE:-}" ]] && log "[env] PERDIJET_COV_MODE=${PERDIJET_COV_MODE}" || true


# Export a few scalars so any subprocess that prefers env (or debugging) sees the resolved values.
export RUN_TAG RUNS_BASE DIR_SIM DIR_ANALYSIS DIR_FINAL DIR_LOG_MERGE PLOTS_SUBDIR
log "[cfg] RUN_TAG=${RUN_TAG}"
log "[cfg] DIR_FINAL=${DIR_FINAL}"

INPUT="${DIR_FINAL}/dphi_allSlices.root"
if [[ ! -f "$INPUT" ]]; then
  log "[ERROR] Missing $INPUT — run merge step first."
  exit 2
fi

log "[pyfit] Starting Python fitter"

PYBIN=""
if command -v python3 >/dev/null 2>&1; then
  PYBIN="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  PYBIN="$(command -v python)"
fi
[[ -n "${PYBIN}" ]] || { log "[ERROR] No python executable found after module load"; exit 2; }
log "[cfg] PYBIN=${PYBIN}"

"${PYBIN}" -c "import numpy, matplotlib, uproot; import scipy" 2>/dev/null || { log "[ERROR] Missing python deps (numpy/matplotlib/uproot/scipy). Install in $HOME/.local or load a module that provides them."; exit 3; }

validate_single_slice_selected_dijet_contract(){
  local final_dir="$1"
  local radii_str="$2"
  local pt_edges_str="$3"
  log "[preflight] Validating single-slice selected-dijet contract in ${final_dir}"
  "${PYBIN}" - "${final_dir}" "${radii_str}" "${pt_edges_str}" <<'PY'
import json
import os
import sys

final_dir = sys.argv[1]
radii = [float(x) for x in str(sys.argv[2]).split() if str(x).strip()]
pt_edges = [float(x) for x in str(sys.argv[3]).split() if str(x).strip()]
expected_semantics = "event_level_selected_dijet_pair_counts"


def fail(msg: str) -> None:
    print(f"[counts][FATAL] {msg}", file=sys.stderr)
    raise SystemExit(1)

if len(radii) == 0:
    fail("JET_RADIUS_LIST is empty; cannot validate selected-dijet count arrays")
if len(pt_edges) < 2:
    fail("PT_LEAD_BIN_EDGES must contain at least two edges for single-slice validation")

summary_path = ""
xsec_path = os.path.join(final_dir, "xsec_summary.json")
if os.path.isfile(xsec_path):
    try:
        with open(xsec_path, "r", encoding="utf-8") as fh:
            xsec_payload = json.load(fh)
        rel = str(xsec_payload.get("selected_dijet_counts_summary_json", "") or "").strip()
        if rel:
            cand = rel if os.path.isabs(rel) else os.path.join(final_dir, rel)
            if os.path.isfile(cand):
                summary_path = cand
    except Exception as exc:
        fail(f"Could not read {xsec_path} while resolving selected_dijet_counts_summary_json: {exc}")
if not summary_path:
    summary_path = os.path.join(final_dir, "selected_dijet_counts_summary.json")
if not os.path.isfile(summary_path):
    fail(f"Missing required selected dijet count summary: {summary_path}")

try:
    with open(summary_path, "r", encoding="utf-8") as fh:
        payload = json.load(fh)
except Exception as exc:
    fail(f"Could not read {summary_path}: {exc}")

merged_slice_count = int(payload.get("merged_slice_count", -1))
if merged_slice_count != 1:
    fail(f"Expected merged_slice_count=1 in {summary_path}, got {merged_slice_count}")

semantics = str(payload.get("count_semantics") or "").strip()
if semantics != expected_semantics:
    fail(f"Unsupported count_semantics in {summary_path}: {semantics!r}; expected {expected_semantics!r}")

total = payload.get("selected_dijet_counts_total")
if not isinstance(total, dict):
    fail(f"{summary_path} is missing selected_dijet_counts_total")

fields_per_r = ("dphi_all_per_R", "dphi_abs_all_per_R", "xj_all_per_R", "aj_all_per_R", "mjj_all_per_R")
fields_per_r_per_pt = ("dphi_ptlead_per_R", "dphi_abs_ptlead_per_R", "xj_ptlead_per_R", "aj_ptlead_per_R")
expected_r = len(radii)
expected_pt = len(pt_edges) - 1


def _is_intlike(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)

for branch_name in ("default", "nosubfrac"):
    block = total.get(branch_name)
    if not isinstance(block, dict):
        fail(f"{summary_path} is missing branch block {branch_name!r}")
    for field in fields_per_r:
        arr = block.get(field)
        if not isinstance(arr, list) or len(arr) != expected_r:
            fail(f"{summary_path} field {branch_name}.{field} must be a list of length {expected_r}")
        for idx, val in enumerate(arr):
            if not _is_intlike(val) or val < 0:
                fail(f"{summary_path} field {branch_name}.{field}[{idx}] must be a non-negative integer; got {val!r}")
    for field in fields_per_r_per_pt:
        arr = block.get(field)
        if not isinstance(arr, list) or len(arr) != expected_r:
            fail(f"{summary_path} field {branch_name}.{field} must be a list of length {expected_r}")
        for ridx, row in enumerate(arr):
            if not isinstance(row, list) or len(row) != expected_pt:
                fail(f"{summary_path} field {branch_name}.{field}[{ridx}] must be a list of length {expected_pt}")
            for pidx, val in enumerate(row):
                if not _is_intlike(val) or val < 0:
                    fail(f"{summary_path} field {branch_name}.{field}[{ridx}][{pidx}] must be a non-negative integer; got {val!r}")

print(f"[counts] validated {summary_path}: merged_slice_count=1, branches=2, R={expected_r}, ptlead_bins={expected_pt}")
PY
}

if [[ -z "${SINGLE_SLICE_MODE+x}" ]]; then
  log "[ERROR] Missing SINGLE_SLICE_MODE in jetscape.ini (no default)."
  exit 2
fi
case "${SINGLE_SLICE_MODE}" in
  0|1) ;;
  *) log "[ERROR] Invalid SINGLE_SLICE_MODE='${SINGLE_SLICE_MODE}'. Use 0 or 1."; exit 2 ;;
esac

if (( SINGLE_SLICE_MODE == 1 )); then
  [[ ${#PT_LO[@]} -eq 1 && ${#PT_HI[@]} -eq 1 ]] || { log "[ERROR] SINGLE_SLICE_MODE=1 requires exactly one configured pThat slice; got PT_LO=(${PT_LO[*]-}) PT_HI=(${PT_HI[*]-})"; exit 2; }
  [[ ${#JET_RADIUS_LIST[@]} -ge 1 ]] || { log "[ERROR] SINGLE_SLICE_MODE=1 requires non-empty JET_RADIUS_LIST in jetscape.ini"; exit 2; }
  [[ ${#PT_LEAD_BIN_EDGES[@]} -ge 2 ]] || { log "[ERROR] SINGLE_SLICE_MODE=1 requires PT_LEAD_BIN_EDGES with at least two edges in jetscape.ini"; exit 2; }
  validate_single_slice_selected_dijet_contract "${DIR_FINAL}" "${JET_RADIUS_LIST[*]}" "${PT_LEAD_BIN_EDGES[*]}"
else
  log "[preflight] SINGLE_SLICE_MODE=0; skipping selected-dijet count summary validation"
fi

"${PYBIN}" "${BASE_DIR}/dphi_fit_py.py" "${BASE_DIR}/jetscape.ini"
log "[pyfit] Done (see ${DIR_FINAL}/fit_py.log and ${DIR_FINAL}/dphi_fit_summary.csv)"












