#!/usr/bin/env bash
# vacbrick_plotter.sh v1.1
# CHANGELOG
# v1.1 (deterministic Slurm error-log routing):
#   • LOGS: Print the exact queued Slurm stdout/stderr paths after sbatch returns the job id.
#   • LOGS: Export the resolved plotter log directory and submit timestamp to the compute job so it can create stable driver/traceback logs in the same folder.
#   • SAFETY: No run-tag routing, plotting arguments, resources, or upstream workflow behavior changed.
# v1.0 (multisim plotter wrapper):
#   • NEW: If MultiSimEnabled=0, delegate directly to paperreadycomparisor.sh so the legacy 2-run compare path stays unchanged.
#   • NEW: If MultiSimEnabled=1, submit a single compute-node plotting job that reads the vacuum merged ROOT plus all 9 brick merged ROOTs and renders grouped 4-curve overlays.
#   • NEW: Require explicit vacuum run-tag / brick-base run-tag knobs in jetscape.ini for the multisim plotting stage, while keeping COMPARE_* knobs untouched for legacy compare jobs.
#   • LOGS: Route stdout/stderr to multisim plotter logs under the brick-base run tree.
#   • SAFETY: No changes to sim/analysis/merge behavior, no manager fan-out, and no dependency assumptions on unfinished upstream jobs.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"
BASE_INI="${INI_PATH:-${JETSCAPE_INI_PATH:-${SCRIPT_DIR}/jetscape.ini}}"
[[ -f "${BASE_INI}" ]] || { echo "[FATAL] jetscape.ini not found: ${BASE_INI}" >&2; exit 1; }
# shellcheck disable=SC1090
source "${BASE_INI}"

ts(){ date +"%F %T"; }
log(){ echo "[$(ts)] [vacbrick_plotter] $*"; }
die(){ echo "[$(ts)] [vacbrick_plotter] [FATAL] $*" >&2; exit 1; }

[[ -n "${MultiSimEnabled+x}" ]] || die "Missing required key MultiSimEnabled in ${BASE_INI}"
[[ "${MultiSimEnabled}" =~ ^[01]$ ]] || die "MultiSimEnabled must be 0 or 1 (got ${MultiSimEnabled})"

if [[ "${MultiSimEnabled}" == "0" ]]; then
  log "MultiSimEnabled=0 -> delegating to paperreadycomparisor.sh with INI_PATH=${BASE_INI}"
  INI_PATH="${BASE_INI}" exec bash "${SCRIPT_DIR}/paperreadycomparisor.sh" "$@"
fi

command -v sbatch >/dev/null 2>&1 || die "sbatch not found in PATH"

VAC_TAG="${MULTISIM_PLOT_VAC_RUN_TAG:-${COMPARE_RUN_TAG_A:-}}"
BRICK_BASE_TAG="${MULTISIM_PLOT_BRICK_BASE_RUN_TAG:-${RUN_TAG:-}}"
[[ -n "${VAC_TAG}" ]] || die "Missing MULTISIM_PLOT_VAC_RUN_TAG (or COMPARE_RUN_TAG_A fallback) in jetscape.ini"
[[ -n "${BRICK_BASE_TAG}" ]] || die "Missing MULTISIM_PLOT_BRICK_BASE_RUN_TAG (or RUN_TAG fallback) in jetscape.ini"

default_runs_base="${HOME}/xscape_runs/${RUN_TAG:-multisim_placeholder}"
RUNS_BASE_RESOLVED="${RUNS_BASE:-${default_runs_base}}"
RUNS_ROOT="${RUNS_BASE_RESOLVED%/${RUN_TAG:-multisim_placeholder}}"
[[ -n "${RUNS_ROOT}" ]] || RUNS_ROOT="${HOME}/xscape_runs"

LOG_DIR="${RUNS_ROOT}/${BRICK_BASE_TAG}/logs/plotter"
mkdir -p "${LOG_DIR}"
TS_COMPACT="$(date +%Y%m%d_%H%M%S)"
OUT="${LOG_DIR}/vacbrick_plotter_${BRICK_BASE_TAG}_${TS_COMPACT}_%j.out"
ERR="${LOG_DIR}/vacbrick_plotter_${BRICK_BASE_TAG}_${TS_COMPACT}_%j.err"

ACCOUNT="${MANAGER_ACCOUNT:-wsu}"
QOS="${MANAGER_QOS:-primary}"
TIME="${PLOTTER_TIME:-02:00:00}"
MEM="${PLOTTER_MEM:-12G}"
CPUS="${PLOTTER_CPUS:-1}"
NODES="${PLOTTER_NODES:-1}"
NTASKS="${PLOTTER_NTASKS:-1}"

log "Submitting multisim plotter for vacuum=${VAC_TAG} brick_base=${BRICK_BASE_TAG} using INI_PATH=${BASE_INI}"
SBATCH_OUT="$(sbatch --parsable \
  --account="${ACCOUNT}" \
  --qos="${QOS}" \
  --nodes="${NODES}" \
  --ntasks="${NTASKS}" \
  --cpus-per-task="${CPUS}" \
  --mem="${MEM}" \
  --time="${TIME}" \
  --job-name="xbplt_${BRICK_BASE_TAG}" \
  --output="${OUT}" \
  --error="${ERR}" \
  --export=ALL,INI_PATH="${BASE_INI}",VACBRICK_PLOTTER_LOG_DIR="${LOG_DIR}",VACBRICK_PLOTTER_TS="${TS_COMPACT}",VACBRICK_PLOTTER_BRICK_BASE_TAG="${BRICK_BASE_TAG}" \
  "${SCRIPT_DIR}/vacbrick_plotter.slurm")" || die "sbatch failed for multisim plotter"

JID="$(sed -nE 's/^([0-9]+)(;.*)?$/\1/p' <<< "${SBATCH_OUT}" | head -n 1)"
[[ "${JID}" =~ ^[0-9]+$ ]] || die "Could not parse numeric job id from sbatch output: ${SBATCH_OUT}"
OUT_RESOLVED="${OUT//%j/${JID}}"
ERR_RESOLVED="${ERR//%j/${JID}}"
DRIVER_OUT="${LOG_DIR}/vacbrick_plotter_${BRICK_BASE_TAG}_${TS_COMPACT}_${JID}.driver.out"
DRIVER_ERR="${LOG_DIR}/vacbrick_plotter_${BRICK_BASE_TAG}_${TS_COMPACT}_${JID}.driver.err"
TRACE_LOG="${LOG_DIR}/vacbrick_plotter_${BRICK_BASE_TAG}_${TS_COMPACT}_${JID}.traceback.log"
SUBMIT_MANIFEST="${LOG_DIR}/vacbrick_plotter_${BRICK_BASE_TAG}_${TS_COMPACT}_${JID}.submit_manifest.log"
{
  echo "[$(ts)] job_id=${JID}"
  echo "[$(ts)] ini=${BASE_INI}"
  echo "[$(ts)] slurm_stdout=${OUT_RESOLVED}"
  echo "[$(ts)] slurm_stderr=${ERR_RESOLVED}"
  echo "[$(ts)] driver_stdout=${DRIVER_OUT}"
  echo "[$(ts)] driver_stderr=${DRIVER_ERR}"
  echo "[$(ts)] python_traceback=${TRACE_LOG}"
} > "${SUBMIT_MANIFEST}"
log "Queued multisim plotter job ${JID}"
log "Slurm stdout: ${OUT_RESOLVED}"
log "Slurm stderr: ${ERR_RESOLVED}"
log "Driver stdout mirror: ${DRIVER_OUT}"
log "Driver stderr mirror: ${DRIVER_ERR}"
log "Python traceback/fault log: ${TRACE_LOG}"
log "Submit manifest: ${SUBMIT_MANIFEST}"
