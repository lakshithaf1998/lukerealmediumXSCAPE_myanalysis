#!/usr/bin/env bash
# submit_python_fit.sh  v1.9
# CHANGELOG
# v1.9 (single-slice selected-dijet preflight):
#   • FIX: When SINGLE_SLICE_MODE=1, validate the published selected_dijet_counts_summary.json contract before sbatch so fitter jobs do not die later on compute nodes from missing/incompatible count metadata.
#   • FIX: Require exactly one configured pThat slice plus non-empty JET_RADIUS_LIST/PT_LEAD_BIN_EDGES for single-slice fitter submissions, matching fitter/comparisor assumptions.
# v1.8 (portable preflight python resolution):
#   • FIX: Resolve a submission-side Python interpreter as python3 or python before wrapper JSON preflight, matching python_fit.slurm fallback behavior.
#   • FIX: Use the resolved interpreter for xsec_summary.json validation instead of hard-requiring python3 in PATH on the submit side.
# v1.7 (ini-driven mail settings):
#   • FIX: Read ManagerMail/MailUser from jetscape.ini and pass mail flags at submission time, matching merge behavior.
#   • DIAG: Log the resolved mail policy before sbatch.
#   • FIX: Keep python_fit.slurm free of hardcoded mail settings so jetscape.ini is the only mail source of truth.
# v1.6 (shell preflight case fix):
#   • FIX: Correct the INCLUDE_XSEC_NORM_ERR case terminator so valid 0/1 values pass wrapper preflight instead of falling through to the fatal branch.
# v1.5 (strict xsec preflight):
#   • NEW: Add wrapper-side validation of ${DIR_FINAL}/xsec_summary.json when INCLUDE_XSEC_NORM_ERR=1.
#   • NEW: Require finite positive xsec_total_rel_err, a non-empty slices list, finite positive per-slice xsec_rel_err,
#     and existence of every referenced per-slice rootfile before sbatch.
#   • FIX: Keep wrapper preflight consistent with dphi_fit_py.py so broken xsec contracts fail before consuming a queue slot.
# v1.4 (slurm submission hardening):
#   • Submit with sbatch --parsable so the job id comes from Slurm's machine-readable interface.
#   • Parse and validate a numeric job id instead of scraping human-readable sbatch text.
# v1.3 (minor safety):
#   • Preflight check for ${DIR_FINAL}/dphi_allSlices.root before submitting the fit job.
# v1.2 (minor):
#   • Extra sanity log: print DIR_FINAL used for outputs.
# v1.1 (minor):
#   • X-SCAPE alignment: run from the script directory and source jetscape.ini via absolute path.
#   • Submit with --chdir so python_fit.slurm sees the repo root even if you launch from elsewhere.
#   • Validate parsed job id; create DIR_FINAL as well as DIR_LOG_MERGE.
#
# v1.0 (major):
#   • Submits python_fit.slurm and prints where to watch logs.

set -euo pipefail

ts(){ date +'%F %T'; }
log(){ echo "[$(ts)] $*"; }
die(){ log "[FATAL] $*"; exit 1; }

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${BASE_DIR}"

[[ -f "${BASE_DIR}/jetscape.ini" ]] || die "Missing ${BASE_DIR}/jetscape.ini"
source "${BASE_DIR}/jetscape.ini"

command -v sbatch >/dev/null 2>&1 || die "sbatch not found in PATH"

PYBIN=""
if command -v python3 >/dev/null 2>&1; then
  PYBIN="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  PYBIN="$(command -v python)"
else
  die "Neither python3 nor python was found in PATH on the submit side"
fi
log "[preflight] submit-side PYBIN=${PYBIN}"

MANAGER_MAIL="${ManagerMail:-0}"
MAIL_USER="${MailUser:-}"
MAIL_ARGS=()
if [[ "${MANAGER_MAIL}" == "1" ]]; then
  [[ -n "${MAIL_USER}" ]] || die "ManagerMail=1 but MailUser is empty in jetscape.ini"
  MAIL_ARGS=(--mail-user="${MAIL_USER}" --mail-type=BEGIN,END,FAIL)
fi

validate_xsec_contract(){
  local final_dir="$1"
  local summary_path="${final_dir}/xsec_summary.json"
  log "[preflight] Validating xsec contract in ${summary_path}"
  "${PYBIN}" - "${final_dir}" <<'PY'
import json
import math
import os
import sys

final_dir = sys.argv[1]
summary_path = os.path.join(final_dir, "xsec_summary.json")

def fail(msg: str) -> None:
    print(f"[xsec][FATAL] {msg}", file=sys.stderr)
    raise SystemExit(1)

if not os.path.isfile(summary_path):
    fail(f"Missing required xsec summary: {summary_path}")

try:
    with open(summary_path, "r", encoding="utf-8") as fh:
        payload = json.load(fh)
except Exception as exc:
    fail(f"Could not read {summary_path}: {exc}")

global_rel = payload.get("xsec_total_rel_err", float("nan"))
try:
    global_rel = float(global_rel)
except Exception as exc:
    fail(f"Invalid xsec_total_rel_err in {summary_path}: {global_rel!r} ({exc})")
if not math.isfinite(global_rel) or global_rel <= 0.0:
    fail(f"Invalid xsec_total_rel_err in {summary_path}: {global_rel!r}; expected finite > 0")

slices = payload.get("slices", [])
if not isinstance(slices, list) or len(slices) == 0:
    fail(f"{summary_path} has no usable slice entries")

for idx, entry in enumerate(slices, start=1):
    rel = entry.get("xsec_rel_err", float("nan"))
    try:
        rel = float(rel)
    except Exception as exc:
        fail(f"{summary_path} slice #{idx} has invalid xsec_rel_err={rel!r} ({exc})")
    if not math.isfinite(rel) or rel <= 0.0:
        fail(f"{summary_path} slice #{idx} has invalid xsec_rel_err={rel!r}; expected finite > 0")

    root_rel = str(entry.get("rootfile", "") or "").strip()
    if root_rel == "":
        fail(f"{summary_path} slice #{idx} is missing required rootfile")

    root_path = root_rel if os.path.isabs(root_rel) else os.path.join(final_dir, root_rel)
    if not os.path.isfile(root_path):
        fail(f"{summary_path} slice #{idx} rootfile does not exist: {root_path}")

print(f"[xsec] validated {summary_path}: xsec_total_rel_err={global_rel:.6g}, slices={len(slices)}")
PY
}

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

mkdir -p "${DIR_LOG_MERGE}" "${DIR_FINAL}"

ROOT_IN="${DIR_FINAL}/dphi_allSlices.root"
[[ -f "${ROOT_IN}" ]] || die "Missing ${ROOT_IN}. Run merge (submit_sliced_merge.sh) first."

if [[ -z "${INCLUDE_XSEC_NORM_ERR+x}" ]]; then
  die "Missing INCLUDE_XSEC_NORM_ERR in jetscape.ini (no default)."
fi
case "${INCLUDE_XSEC_NORM_ERR}" in
  0|1) ;;
  *) die "Invalid INCLUDE_XSEC_NORM_ERR=${INCLUDE_XSEC_NORM_ERR@Q}; expected 0 or 1." ;;
esac

if (( INCLUDE_XSEC_NORM_ERR == 1 )); then
  validate_xsec_contract "${DIR_FINAL}"
else
  log "[preflight] INCLUDE_XSEC_NORM_ERR=0; skipping xsec summary validation"
fi

if [[ -z "${SINGLE_SLICE_MODE+x}" ]]; then
  die "Missing SINGLE_SLICE_MODE in jetscape.ini (no default)."
fi
case "${SINGLE_SLICE_MODE}" in
  0|1) ;;
  *) die "Invalid SINGLE_SLICE_MODE='${SINGLE_SLICE_MODE}'. Use 0 or 1." ;;
esac

if (( SINGLE_SLICE_MODE == 1 )); then
  [[ ${#PT_LO[@]} -eq 1 && ${#PT_HI[@]} -eq 1 ]] || die "SINGLE_SLICE_MODE=1 requires exactly one configured pThat slice; got PT_LO=(${PT_LO[*]-}) PT_HI=(${PT_HI[*]-})"
  [[ ${#JET_RADIUS_LIST[@]} -ge 1 ]] || die "SINGLE_SLICE_MODE=1 requires non-empty JET_RADIUS_LIST in jetscape.ini"
  [[ ${#PT_LEAD_BIN_EDGES[@]} -ge 2 ]] || die "SINGLE_SLICE_MODE=1 requires PT_LEAD_BIN_EDGES with at least two edges in jetscape.ini"
  validate_single_slice_selected_dijet_contract "${DIR_FINAL}" "${JET_RADIUS_LIST[*]}" "${PT_LEAD_BIN_EDGES[*]}"
else
  log "[preflight] SINGLE_SLICE_MODE=0; skipping selected-dijet count summary validation"
fi

log "[submit] ENGINE=${ENGINE_NAME:-NA}  RUN_TAG=${RUN_TAG:-NA}"
log "[submit] BASE_DIR=${BASE_DIR}"
log "[submit] DIR_FINAL=${DIR_FINAL}"
log "[submit] DIR_LOG_MERGE=${DIR_LOG_MERGE}"
log "[submit] ManagerMail=${MANAGER_MAIL}  MailUser=${MAIL_USER:-<unset>}"
log "[submit] Submitting Python fitter..."

SBATCH_OUT="$(
  sbatch --parsable \
    --chdir="${BASE_DIR}" \
    --output="${DIR_LOG_MERGE}/pyfit-%j.out" \
    --error="${DIR_LOG_MERGE}/pyfit-%j.err" \
    "${MAIL_ARGS[@]}" \
    python_fit.slurm
)" || die "sbatch failed for python fit job"

JID="${SBATCH_OUT%%;*}"
[[ -n "${JID}" && "${JID}" =~ ^[0-9]+$ ]] || die "Could not parse numeric job id from sbatch output: ${SBATCH_OUT}"

log "[submit] Job id: ${JID}"
log "[submit] Track: squeue -j ${JID}"
log "[submit] Logs:  ${DIR_LOG_MERGE}/pyfit-${JID}.out  and  ${DIR_LOG_MERGE}/pyfit-${JID}.err"












