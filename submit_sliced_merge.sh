#!/usr/bin/env bash
# submit_sliced_merge.sh v4.5
# CHANGELOG
# v4.5 (custom ini-path support for wrapper-driven multimerge):
#   • NEW: Honor INI_PATH / JETSCAPE_INI_PATH so wrapper-generated per-variant ini files can drive the existing single-run MERGE submit path.
#   • FIX: Wrapper-side RUN_TAG/directory validation now comes from the resolved ini path instead of always hardwiring ./jetscape.ini.
#   • FIX: Preserve INI_PATH into the merge worker submission so one medium point cannot accidentally merge another medium point's analysis tree.
# v4.4 (dead wrapper preflight cleanup):
#   • CLEANUP: Removed stale wrapper-side JSON/preflight helper functions and status variables that were left behind after the heavy merge-input acceptance scan was moved into merge_dphi_histos.slurm.
#   • CLEANUP: No workflow or physics change. The wrapper still does only lightweight config validation on Warrior/login nodes, then submits the merge worker so heavy input scanning stays on the allocated compute node.
# v4.3 (submit-light; heavy preflight moved to compute node):
#   • FIX: Stop running the expensive task-by-task merge-input preflight in the wrapper on Warrior/login nodes. The wrapper now does only lightweight config validation locally, then submits the merge worker so the heavy acceptance scan runs on the allocated primary compute node.
#   • SAFETY: This avoids large merge preflight scans on Warrior while preserving the same strict acceptance contract, because merge_dphi_histos.slurm now performs the canonical expected-input preflight before deleting any published outputs.
# v4.2 (wrapper-side canonical xsec metadata preflight):
#   • FIX: When INCLUDE_XSEC_NORM_ERR=1, preflight now mirrors the worker's canonical normalization contract before sbatch: each expected accepted slice_meta JSON must contain valid norm_sigmaGen_mb_used, norm_sigmaErr_mb_used, norm_weight_mb_per_event_used, norm_denominator_events_used, norm_source, norm_policy, norm_sigma_source, and norm_denominator_source fields with internal weight=sigma/denominator consistency.
#   • FIX: Merge submission now validates INCLUDE_XSEC_NORM_ERR before the expensive upstream analysis scan, so wrapper-side gating can reject doomed xsec-enabled merges immediately instead of burning a queue slot.
# v4.1 (bash shebang fix):
#   • FIX: Added explicit bash shebang so the wrapper always runs under bash instead of relying on parent-shell fallback behavior.
#
# v4.0 (strict worker-matching accepted-input preflight):
#   • FIX: Before sbatch, mirror the merge worker's accepted-input contract for every expected analysis task in every slice.
#   • FIX: For each expected dphi_<tag>.root / slice_meta_<tag>.json pair in the jid-selected analysis run directory, require ROOT exists, meta exists, events_seen==NUM_EVENTS, and root_status==ok.
#   • FIX: Merge submission now hard-fails locally when any expected analysis task is missing, incomplete, or corrupt, instead of spending a Slurm slot to learn the same thing later.
#
# v3.9 (wrapper-side upstream analysis-run-dir preflight):
#   • FIX: Before sbatch, require DIR_LOG_ANALYSIS/jid_an_<PT_LO>_<PT_HI>.txt to exist for every configured slice.
#   • FIX: Before sbatch, require the jid-selected analysis run directory DIR_ANALYSIS/<slice>/<jid> to already exist for every slice, so merge does not burn a queue slot just to discover missing upstream analysis output.
#
# v3.8 (explicit wrapper-side Multiplier/xsec contract):
#   • FIX: Validate Multiplier in the wrapper before sbatch with the same explicit policy used for ENABLE_RENORM.
#     The wrapper now hard-fails unless Multiplier is present in jetscape.ini, non-empty, numeric, and an integer >= 1.
#   • FIX: Validate INCLUDE_XSEC_NORM_ERR in the wrapper before sbatch with no assumed default.
#     The wrapper now hard-fails unless INCLUDE_XSEC_NORM_ERR is present in jetscape.ini, non-empty, and exactly 0 or 1.
#
# v3.7 (wrapper-side Multiplier/xsec preflight):
#   • FIX: Initial wrapper-side validation for Multiplier and INCLUDE_XSEC_NORM_ERR before sbatch.
#
# v3.6 (wrapper-side ENABLE_RENORM preflight):
#   • FIX: Validate ENABLE_RENORM in the wrapper with the same explicit contract as the merge worker before mkdir -p or sbatch.
#     The wrapper now hard-fails unless ENABLE_RENORM exists, is numeric, and is exactly 0 or 1.
#
# v3.5 (full wrapper-side merge config validation):
#   • FIX: Copy the merge worker's validate_merge_config() contract into this wrapper and run it immediately after
#     sourcing jetscape.ini, before mkdir -p or sbatch. The wrapper now hard-fails unless RUN_TAG and required
#     directories are non-empty, NUM_EVENTS is a positive integer, PT_LO/PT_HI/JOBS exist and are non-empty, array
#     lengths match, slice bounds are integers with PT_HI>PT_LO, and JOBS entries are positive integers.
#
# v3.4 (strict pThat array-length guard):
#   • FIX: Hard-fail immediately after loading jetscape.ini if PT_LO, PT_HI, and JOBS arrays do not have identical lengths.
#     This prevents merge submission from pairing the wrong pTHat bins with the wrong job counts.
#
# v3.3 (parsable sbatch + mail-from-ini):
#   • FIX: Submit merge with sbatch --parsable and parse only the numeric job id prefix, avoiding locale/output-format fragility.
#   • FIX: Merge-job mail settings now come from jetscape.ini (ManagerMail/MailUser) instead of being hardcoded in the Slurm file.
#
# v3.2 (line-ending hygiene + changelog cleanup):
#   • Normalize this wrapper to LF line endings so Linux shebang execution stays valid on WSU/Slurm nodes.
#   • No workflow/dependency change: merge submission is still manual with no waits or job dependencies.
#
# v3.1 (minor robustness):
#   • Validate parsed merge job id (MID) so we don't silently print an empty id.
#   • No workflow change: still no dependencies/waits (you run merge after analysis manually).
#
# v3.0 (major: X-SCAPE alignment + path safety):
#   • Runs from the script’s directory (repo root expected), and sources jetscape.ini via absolute path.
#   • Submits merge job with --chdir=BASE_DIR so merge_dphi_histos.slurm sees the same repo root.
#   • No dependencies/waits added (you said you run merge after analysis manually).

set -euo pipefail

ts(){ date +'%F %T'; }
log(){ echo "[$(ts)] $*"; }
die(){ log "[FATAL] $*"; exit 1; }

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${BASE_DIR}"

INI_PATH="${INI_PATH:-${JETSCAPE_INI_PATH:-${BASE_DIR}/jetscape.ini}}"
export INI_PATH
[[ -f "${INI_PATH}" ]] || die "Missing jetscape.ini: ${INI_PATH}"
source "${INI_PATH}"

require_nonempty_var(){
  local var_name="$1"
  local value="${!var_name-}"
  [[ -n "${value}" ]] || die "jetscape.ini missing or empty required key ${var_name}"
}

validate_merge_config(){
  local i

  declare -p PT_LO >/dev/null 2>&1 || die "jetscape.ini missing required PT_LO array"
  declare -p PT_HI >/dev/null 2>&1 || die "jetscape.ini missing required PT_HI array"
  declare -p JOBS  >/dev/null 2>&1 || die "jetscape.ini missing required JOBS array"
  [[ -n "${NUM_EVENTS+x}" ]] || die "jetscape.ini missing required key NUM_EVENTS"

  require_nonempty_var RUN_TAG
  require_nonempty_var DIR_ANALYSIS
  require_nonempty_var DIR_FINAL
  require_nonempty_var DIR_SIM
  require_nonempty_var DIR_LOG_SIM
  require_nonempty_var DIR_LOG_ANALYSIS
  require_nonempty_var DIR_LOG_MERGE

  (( ${#PT_LO[@]} > 0 )) || die "jetscape.ini PT_LO array is empty"
  (( ${#PT_HI[@]} > 0 )) || die "jetscape.ini PT_HI array is empty"
  (( ${#JOBS[@]}  > 0 )) || die "jetscape.ini JOBS array is empty"

  (( ${#PT_LO[@]} == ${#PT_HI[@]} )) || die "jetscape.ini array length mismatch: PT_LO has ${#PT_LO[@]} entries but PT_HI has ${#PT_HI[@]}"
  (( ${#PT_LO[@]} == ${#JOBS[@]}  )) || die "jetscape.ini array length mismatch: PT_LO has ${#PT_LO[@]} entries but JOBS has ${#JOBS[@]}"

  [[ "${NUM_EVENTS}" =~ ^[0-9]+$ ]] || die "NUM_EVENTS must be a positive integer (got ${NUM_EVENTS})"
  (( NUM_EVENTS > 0 )) || die "NUM_EVENTS must be > 0 (got ${NUM_EVENTS})"

  for i in "${!PT_LO[@]}"; do
    [[ "${PT_LO[$i]}" =~ ^-?[0-9]+$ ]] || die "PT_LO[$i] must be an integer (got ${PT_LO[$i]})"
    [[ "${PT_HI[$i]}" =~ ^-?[0-9]+$ ]] || die "PT_HI[$i] must be an integer (got ${PT_HI[$i]})"
    [[ "${JOBS[$i]}"  =~ ^[0-9]+$  ]] || die "JOBS[$i] must be a positive integer (got ${JOBS[$i]})"
    (( PT_HI[i] > PT_LO[i] )) || die "Invalid pThat slice index ${i}: PT_HI=${PT_HI[$i]} must be greater than PT_LO=${PT_LO[$i]}"
    (( JOBS[i] > 0 )) || die "Invalid JOBS[$i]=${JOBS[$i]}: must be > 0"
  done
}

validate_merge_config

# ENABLE_RENORM policy must be explicit. Missing key is a configuration error.
if [[ -z "${ENABLE_RENORM+x}" ]]; then
  die "jetscape.ini missing required key ENABLE_RENORM (must be 0 or 1). Refusing to assume a default."
fi
if ! [[ "${ENABLE_RENORM}" =~ ^[0-9]+$ ]]; then
  die "jetscape.ini has invalid ENABLE_RENORM=${ENABLE_RENORM} (non-numeric). Must be 0 or 1."
fi
if [[ "${ENABLE_RENORM}" != "0" && "${ENABLE_RENORM}" != "1" ]]; then
  die "jetscape.ini has invalid ENABLE_RENORM=${ENABLE_RENORM}. Must be 0 or 1."
fi

# Multiplier policy must be explicit. Missing key is a configuration error.
if [[ -z "${Multiplier+x}" && -z "${multiplier+x}" ]]; then
  die "jetscape.ini missing required key Multiplier (must be an integer >= 1). Refusing to assume a default."
fi
MULT="${Multiplier-${multiplier-}}"
if [[ -z "${MULT}" ]]; then
  die "jetscape.ini has empty Multiplier. Must be an integer >= 1."
fi
if ! [[ "${MULT}" =~ ^[0-9]+$ ]]; then
  die "jetscape.ini has invalid Multiplier=${MULT} (non-numeric). Must be an integer >= 1."
fi
if (( MULT < 1 )); then
  die "jetscape.ini has invalid Multiplier=${MULT}. Must be an integer >= 1."
fi

# INCLUDE_XSEC_NORM_ERR policy must be explicit. Missing key is a configuration error.
if [[ -z "${INCLUDE_XSEC_NORM_ERR+x}" ]]; then
  die "jetscape.ini missing required key INCLUDE_XSEC_NORM_ERR (must be 0 or 1). Refusing to assume a default."
fi
if [[ -z "${INCLUDE_XSEC_NORM_ERR}" ]]; then
  die "jetscape.ini has empty INCLUDE_XSEC_NORM_ERR. Must be 0 or 1."
fi
if ! [[ "${INCLUDE_XSEC_NORM_ERR}" =~ ^[01]$ ]]; then
  die "jetscape.ini has invalid INCLUDE_XSEC_NORM_ERR=${INCLUDE_XSEC_NORM_ERR}. Must be 0 or 1."
fi

# Heavy upstream acceptance preflight now runs inside merge_dphi_histos.slurm on the allocated compute node. Keep the wrapper light on Warrior/login nodes.
command -v sbatch >/dev/null 2>&1 || die "sbatch not found in PATH"

MANAGER_MAIL="${ManagerMail:-0}"
MAIL_USER="${MailUser:-}"
MAIL_ARGS=()
if [[ "${MANAGER_MAIL}" == "1" ]]; then
  [[ -n "${MAIL_USER}" ]] || die "ManagerMail=1 but MailUser is empty in jetscape.ini"
  MAIL_ARGS=(--mail-user="${MAIL_USER}" --mail-type=BEGIN,END,FAIL)
fi

mkdir -p "${DIR_LOG_MERGE}" "${DIR_FINAL}"

log "[submit] ENGINE=${ENGINE_NAME:-NA}  RUN_TAG=${RUN_TAG:-NA}"
log "[submit] BASE_DIR=${BASE_DIR}"
log "[submit] DIR_LOG_MERGE=${DIR_LOG_MERGE}"
log "[submit] INI_PATH=${INI_PATH}"
log "[submit] Submitting merge job..."

SBATCH_OUT="$(
  sbatch --parsable \
    --chdir="${BASE_DIR}" \
    --output="${DIR_LOG_MERGE}/merge-%j.out" \
    --error="${DIR_LOG_MERGE}/merge-%j.err" \
    --export=ALL,INI_PATH="${INI_PATH}" \
    "${MAIL_ARGS[@]}" \
    merge_dphi_histos.slurm
)" || die "sbatch failed for merge job"

MID="${SBATCH_OUT%%;*}"
[[ -n "${MID}" && "${MID}" =~ ^[0-9]+$ ]] || die "Could not parse numeric merge job id from sbatch output: ${SBATCH_OUT}"

log "[submit] Merge job id: ${MID}"
log "[submit] Track: squeue -j ${MID}"







