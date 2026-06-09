#!/usr/bin/env bash
# paperreadycomparisor.sh  v1.2
# CHANGELOG
# v1.2 (vacuum/medium comparison defaults + log-path cleanup):
#   • FIX: Default COMPARE_LABEL_B fallback is now medium, while still honoring explicit COMPARE_LABEL_B/COMP_LABEL_B from jetscape.ini/environment.
#   • FIX: Final submit log now prints the actual paperreadycompare-%j stdout/stderr paths used by sbatch.
#   • SAFETY: No SLURM resources, queue footprint, selected-count validation, xsec validation, run-folder routing, or plotting arguments changed.
# v1.1 (INI_PATH + selected-count contract fix):
#   • FIX: Honor INI_PATH/JETSCAPE_INI_PATH when sourcing the comparison configuration and pass that same path into the SLURM job.
#   • FIX: Validate current analyzer/merge selected-count fields dijet_base_* instead of retired dphi_* non-absolute count fields.
#   • SAFETY: No SLURM resources, run-tag routing, xsec preflight, or plotting script arguments changed except forwarding the selected ini path.
# v1.0 (paper-ready comparison wrapper):
#   • NEW: Submit paperreadycomparisor.slurm instead of the standard comparison SLURM script.
#   • NEW: Keep the same compare-tag, ratio-range, xsec, and single-slice preflight contract as the standard wrapper so plotting-only jobs do not waste queue slots.
#   • NEW: Route SLURM stdout/stderr to paperreadycompare-%j.{out,err}.
#   • DIAG: Log the paper-ready comparison stage explicitly.
#   • SAFETY: No changes to compare-tag resolution, required jetscape.ini keys, selected-dijet/xsec preflight, or run-folder routing.
#
# Legacy wrapper body below is derived from submit_mjj_comparisor.sh.
set -euo pipefail

ts(){ date +'%F %T'; }
log(){ echo "[$(ts)] $*"; }
die(){ log "[FATAL] $*"; exit 1; }

list_tags(){
  local root="$1"
  [[ -d "$root" ]] || return 0
  # show a few tag dirs (exclude comparisons and hidden)
  (cd "$root" && ls -1d */ 2>/dev/null | sed 's#/##' | grep -v '^comparisons$' | head -n 30) || true
}

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${BASE_DIR}"

INI_FILE="${INI_PATH:-${JETSCAPE_INI_PATH:-${BASE_DIR}/jetscape.ini}}"
[[ -f "${INI_FILE}" ]] || die "Missing ini file: ${INI_FILE}"
# shellcheck disable=SC1090
source "${INI_FILE}" || die "Failed to source ini file: ${INI_FILE}"

command -v sbatch >/dev/null 2>&1 || die "sbatch not found in PATH"

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python)"
else
  die "Neither python3 nor python found in PATH"
fi
log "[submit] Using submit-side Python interpreter: ${PYTHON_BIN}"

MANAGER_MAIL="${ManagerMail:-0}"
MAIL_USER="${MailUser:-}"
MAIL_ARGS=()
if [[ "${MANAGER_MAIL}" == "1" ]]; then
  [[ -n "${MAIL_USER}" ]] || die "ManagerMail=1 but MailUser is empty in jetscape.ini"
  MAIL_ARGS=(--mail-user="${MAIL_USER}" --mail-type=BEGIN,END,FAIL)
fi

validate_single_slice_selected_dijet_contract(){
  local final_dir="$1"
  local label="$2"
  local radii_str="$3"
  local pt_edges_str="$4"
  log "[preflight] Validating ${label} single-slice selected-dijet contract in ${final_dir}"
  "${PYTHON_BIN}" - "${final_dir}" "${label}" "${radii_str}" "${pt_edges_str}" <<'PY'
import json
import os
import sys

final_dir = sys.argv[1]
label = sys.argv[2]
radii = [float(x) for x in str(sys.argv[3]).split() if str(x).strip()]
pt_edges = [float(x) for x in str(sys.argv[4]).split() if str(x).strip()]
expected_semantics = "event_level_selected_dijet_pair_counts"


def fail(msg: str) -> None:
    print(f"[{label}][counts][FATAL] {msg}", file=sys.stderr)
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

fields_per_r = ("dijet_base_all_per_R", "dphi_abs_all_per_R", "xj_all_per_R", "aj_all_per_R", "mjj_all_per_R")
fields_per_r_per_pt = ("dijet_base_ptlead_per_R", "dphi_abs_ptlead_per_R", "xj_ptlead_per_R", "aj_ptlead_per_R")
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

print(f"[{label}][counts] validated {summary_path}: merged_slice_count=1, branches=2, R={expected_r}, ptlead_bins={expected_pt}")
PY
}

validate_ratio_ylim_pair(){
  local min_key="$1"
  local max_key="$2"
  local label="$3"
  local min_val="${!min_key-}"
  local max_val="${!max_key-}"

  [[ -n "${min_val}" ]] || die "Missing ${min_key} in jetscape.ini (no default)."
  [[ -n "${max_val}" ]] || die "Missing ${max_key} in jetscape.ini (no default)."

  "${PYTHON_BIN}" - "${min_key}" "${min_val}" "${max_key}" "${max_val}" "${label}" <<'PY'
import math
import sys

min_key, min_val, max_key, max_val, label = sys.argv[1:6]

def fail(msg: str) -> None:
    print(f"[{label}][FATAL] {msg}", file=sys.stderr)
    raise SystemExit(1)

try:
    y_min = float(min_val)
    y_max = float(max_val)
except Exception:
    fail(f"Invalid ratio y-range: {min_key}={min_val!r}, {max_key}={max_val!r}; expected finite floats")

if not (math.isfinite(y_min) and math.isfinite(y_max)):
    fail(f"Invalid ratio y-range: {min_key}={min_val!r}, {max_key}={max_val!r}; expected finite floats")
if y_max <= y_min:
    fail(f"Invalid ratio y-range: require {max_key} > {min_key}; got {y_max} <= {y_min}")
if not (y_min <= 1.0 <= y_max):
    fail(f"Invalid ratio y-range: require {min_key} <= 1 <= {max_key}; got [{y_min}, {y_max}]")

print(f"[{label}] validated {min_key}={y_min} {max_key}={y_max}")
PY
}

validate_xsec_contract(){
  local final_dir="$1"
  local label="$2"
  local summary_path="${final_dir}/xsec_summary.json"
  log "[preflight] Validating ${label} xsec contract in ${summary_path}"
  "${PYTHON_BIN}" - "${final_dir}" "${label}" <<'PY'
import json
import math
import os
import sys

final_dir = sys.argv[1]
label = sys.argv[2]
summary_path = os.path.join(final_dir, "xsec_summary.json")

def fail(msg: str) -> None:
    print(f"[{label}][xsec][FATAL] {msg}", file=sys.stderr)
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

print(f"[{label}][xsec] validated {summary_path}: xsec_total_rel_err={global_rel:.6g}, slices={len(slices)}")
PY
}

# ------------------ compare config (ini is source of truth) ------------------
RUN_TAG_A="${COMP_RUN_TAG_A:-${COMPARE_RUN_TAG_A:-}}"
RUN_TAG_B="${COMP_RUN_TAG_B:-${COMPARE_RUN_TAG_B:-}}"
LABEL_A="${COMP_LABEL_A:-${COMPARE_LABEL_A:-vacuum}}"
LABEL_B="${COMP_LABEL_B:-${COMPARE_LABEL_B:-medium}}"
RATIO_MODE="${COMP_RATIO_MODE:-${COMPARE_RATIO_MODE:-med}}"

[[ -n "${RUN_TAG_A}" ]] || die "Missing compare tag A. Set COMPARE_RUN_TAG_A in jetscape.ini (or export COMP_RUN_TAG_A)."
[[ -n "${RUN_TAG_B}" ]] || die "Missing compare tag B. Set COMPARE_RUN_TAG_B in jetscape.ini (or export COMP_RUN_TAG_B)."

if [[ "${RATIO_MODE}" != "med" && "${RATIO_MODE}" != "inv" ]]; then
  die "Invalid RATIO_MODE='${RATIO_MODE}'. Use 'med' or 'inv' (jetscape.ini: COMPARE_RATIO_MODE)."
fi

# Derive runs root from current RUNS_BASE (expected: .../xscape_runs/${RUN_TAG})
RUNS_BASE_RESOLVED="${RUNS_BASE:-$HOME/xscape_runs/${RUN_TAG}}"
RUNS_ROOT="${RUNS_BASE_RESOLVED%/${RUN_TAG}}"
[[ -n "${RUNS_ROOT}" ]] || RUNS_ROOT="$HOME/xscape_runs"

RUN_DIR_A="${RUNS_ROOT}/${RUN_TAG_A}"
RUN_DIR_B="${RUNS_ROOT}/${RUN_TAG_B}"

if [[ ! -d "${RUN_DIR_A}" ]]; then
  log "[ERROR] Run tag A folder not found: ${RUN_DIR_A}"
  log "[ERROR] RUNS_ROOT=${RUNS_ROOT}"
  log "[ERROR] Available tags (first 30):"
  list_tags "${RUNS_ROOT}" | sed 's/^/  - /' || true
  die "Fix COMPARE_RUN_TAG_A (or create the run)."
fi
if [[ ! -d "${RUN_DIR_B}" ]]; then
  log "[ERROR] Run tag B folder not found: ${RUN_DIR_B}"
  log "[ERROR] RUNS_ROOT=${RUNS_ROOT}"
  log "[ERROR] Available tags (first 30):"
  list_tags "${RUNS_ROOT}" | sed 's/^/  - /' || true
  die "Fix COMPARE_RUN_TAG_B (or create the run)."
fi

COMPARE_DIR="${RUNS_ROOT}/comparisons/${RUN_TAG_A}_vs_${RUN_TAG_B}"
LOG_DIR="${COMPARE_DIR}/logs"
mkdir -p "${LOG_DIR}"

if [[ -z "${INCLUDE_XSEC_NORM_ERR+x}" ]]; then
  die "Missing INCLUDE_XSEC_NORM_ERR in jetscape.ini (no default)."
fi
case "${INCLUDE_XSEC_NORM_ERR}" in
  0|1) ;;
  *) die "Invalid INCLUDE_XSEC_NORM_ERR=${INCLUDE_XSEC_NORM_ERR@Q}; expected 0 or 1." ;;
esac

if [[ -z "${SINGLE_SLICE_MODE+x}" ]]; then
  die "Missing SINGLE_SLICE_MODE in jetscape.ini (no default)."
fi
case "${SINGLE_SLICE_MODE}" in
  0|1) ;;
  *) die "Invalid SINGLE_SLICE_MODE=${SINGLE_SLICE_MODE@Q}; expected 0 or 1." ;;
esac

if (( SINGLE_SLICE_MODE == 1 )); then
  [[ ${#PT_LO[@]} -eq 1 && ${#PT_HI[@]} -eq 1 ]] || die "SINGLE_SLICE_MODE=1 requires exactly one configured pThat slice; got PT_LO=(${PT_LO[*]-}) PT_HI=(${PT_HI[*]-})"
  [[ ${#JET_RADIUS_LIST[@]} -ge 1 ]] || die "SINGLE_SLICE_MODE=1 requires non-empty JET_RADIUS_LIST in jetscape.ini"
  [[ ${#PT_LEAD_BIN_EDGES[@]} -ge 2 ]] || die "SINGLE_SLICE_MODE=1 requires PT_LEAD_BIN_EDGES with at least two edges in jetscape.ini"
fi

FINAL_DIR_A="${RUN_DIR_A}/final"
FINAL_DIR_B="${RUN_DIR_B}/final"
ROOT_A="${FINAL_DIR_A}/dphi_allSlices.root"
ROOT_B="${FINAL_DIR_B}/dphi_allSlices.root"

[[ -f "${ROOT_A}" ]] || die "Missing ${ROOT_A}. Run merge for ${RUN_TAG_A} first."
[[ -f "${ROOT_B}" ]] || die "Missing ${ROOT_B}. Run merge for ${RUN_TAG_B} first."

if (( INCLUDE_XSEC_NORM_ERR == 1 )); then
  validate_xsec_contract "${FINAL_DIR_A}" "runA:${RUN_TAG_A}"
  validate_xsec_contract "${FINAL_DIR_B}" "runB:${RUN_TAG_B}"
else
  log "[preflight] INCLUDE_XSEC_NORM_ERR=0; skipping xsec summary validation for both runs"
fi

if (( SINGLE_SLICE_MODE == 1 )); then
  validate_single_slice_selected_dijet_contract "${FINAL_DIR_A}" "runA:${RUN_TAG_A}" "${JET_RADIUS_LIST[*]}" "${PT_LEAD_BIN_EDGES[*]}"
  validate_single_slice_selected_dijet_contract "${FINAL_DIR_B}" "runB:${RUN_TAG_B}" "${JET_RADIUS_LIST[*]}" "${PT_LEAD_BIN_EDGES[*]}"
else
  log "[preflight] SINGLE_SLICE_MODE=0; skipping selected-dijet count summary validation for both runs"
fi

validate_ratio_ylim_pair MJJ_COMPARE_RATIO_YMIN MJJ_COMPARE_RATIO_YMAX "Mjj compare ratio range"
validate_ratio_ylim_pair JETPT_COMPARE_RATIO_YMIN JETPT_COMPARE_RATIO_YMAX "Jet-pT compare ratio range"
validate_ratio_ylim_pair DPHI_COMPARE_RATIO_YMIN DPHI_COMPARE_RATIO_YMAX "Δφ compare ratio range"
validate_ratio_ylim_pair DPHI_ABS_COMPARE_RATIO_YMIN DPHI_ABS_COMPARE_RATIO_YMAX "|Δφ| compare ratio range"
validate_ratio_ylim_pair XJ_COMPARE_RATIO_YMIN XJ_COMPARE_RATIO_YMAX "xJ compare ratio range"
validate_ratio_ylim_pair AJ_COMPARE_RATIO_YMIN AJ_COMPARE_RATIO_YMAX "AJ compare ratio range"
validate_ratio_ylim_pair JETR_COMPARE_RATIO_YMIN JETR_COMPARE_RATIO_YMAX "Jet-R compare ratio range"
validate_ratio_ylim_pair LEAD_SUBLEAD_PROFILE_COMPARE_RATIO_YMIN LEAD_SUBLEAD_PROFILE_COMPARE_RATIO_YMAX "Lead-vs-sublead profile compare ratio range"

log "[submit] ENGINE=${ENGINE_NAME:-NA}"
log "[submit] COMBINE_R_LIST=${COMBINE_R_LIST:-<unset>}  INCLUDE_XSEC_NORM_ERR=${INCLUDE_XSEC_NORM_ERR:-<unset>}  COVARIANCE_MODE=${COVARIANCE_MODE:-<unset>}"
log "[submit] ratio y-ranges: MJJ=[${MJJ_COMPARE_RATIO_YMIN:-<unset>},${MJJ_COMPARE_RATIO_YMAX:-<unset>}] JETPT=[${JETPT_COMPARE_RATIO_YMIN:-<unset>},${JETPT_COMPARE_RATIO_YMAX:-<unset>}] DPHI=[${DPHI_COMPARE_RATIO_YMIN:-<unset>},${DPHI_COMPARE_RATIO_YMAX:-<unset>}] DPHI_ABS=[${DPHI_ABS_COMPARE_RATIO_YMIN:-<unset>},${DPHI_ABS_COMPARE_RATIO_YMAX:-<unset>}] XJ=[${XJ_COMPARE_RATIO_YMIN:-<unset>},${XJ_COMPARE_RATIO_YMAX:-<unset>}] AJ=[${AJ_COMPARE_RATIO_YMIN:-<unset>},${AJ_COMPARE_RATIO_YMAX:-<unset>}] JETR=[${JETR_COMPARE_RATIO_YMIN:-<unset>},${JETR_COMPARE_RATIO_YMAX:-<unset>}] LEAD_SUBLEAD_PROFILE=[${LEAD_SUBLEAD_PROFILE_COMPARE_RATIO_YMIN:-<unset>},${LEAD_SUBLEAD_PROFILE_COMPARE_RATIO_YMAX:-<unset>}]"

log "[submit] RUNS_ROOT=${RUNS_ROOT}"
log "[submit] TAG_A=${RUN_TAG_A}  (dir: ${RUN_DIR_A})"
log "[submit] TAG_B=${RUN_TAG_B}  (dir: ${RUN_DIR_B})"
log "[submit] LABEL_A=${LABEL_A}"
log "[submit] LABEL_B=${LABEL_B}"
log "[submit] RATIO_MODE=${RATIO_MODE}"
log "[submit] BASE_DIR=${BASE_DIR}"
log "[submit] INI_FILE=${INI_FILE}"
log "[submit] COMPARE_DIR=${COMPARE_DIR}"
log "[submit] LOG_DIR=${LOG_DIR}"
log "[submit] ManagerMail=${MANAGER_MAIL}  MailUser=${MAIL_USER:-<unset>}"

log "[submit] Submitting merged-observable paper-ready comparison job..."
SBATCH_OUT="$(
  sbatch --parsable \
    --chdir="${BASE_DIR}" \
    --export=ALL,INI_PATH="${INI_FILE}",COMP_RUN_TAG_A="${RUN_TAG_A}",COMP_RUN_TAG_B="${RUN_TAG_B}",COMP_LABEL_A="${LABEL_A}",COMP_LABEL_B="${LABEL_B}",COMP_RATIO_MODE="${RATIO_MODE}" \
    --output="${LOG_DIR}/paperreadycompare-%j.out" \
    --error="${LOG_DIR}/paperreadycompare-%j.err" \
    "${MAIL_ARGS[@]}" \
    paperreadycomparisor.slurm
)" || die "sbatch failed for paper-ready comparison job"

JID="${SBATCH_OUT%%;*}"
[[ -n "${JID}" && "${JID}" =~ ^[0-9]+$ ]] || die "Could not parse numeric job id from sbatch output: ${SBATCH_OUT}"

log "[submit] Job id: ${JID}"
log "[submit] Track: squeue -j ${JID}"
log "[submit] Logs:  ${LOG_DIR}/paperreadycompare-${JID}.out  and  ${LOG_DIR}/paperreadycompare-${JID}.err"
