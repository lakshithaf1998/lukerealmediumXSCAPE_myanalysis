#!/usr/bin/env bash
# vacbrick_plotter.slurm v1.1
# CHANGELOG
# v1.1 (stable crash diagnostics):
#   • LOGS: Mirror compute-node stdout/stderr to deterministic driver logs under the multisim plotter log directory in addition to Slurm %j files.
#   • LOGS: Enable Python faulthandler/traceback output to a deterministic traceback log, including Slurm timeout SIGTERM stack dumps when possible.
#   • LOGS: Add exit traps, heartbeat messages, Python exit-code logging, and optional sacct summary so silent kills/OOM/timeouts are visible.
#   • SAFETY: No plotting arguments, module choices, resources, run-tag routing, or upstream workflow behavior changed.
# v1.0 (multisim plotter compute job):
#   • NEW: Run vacbrick_plotter_py.py on a compute node for the 10-root vacuum+9-brick grouped plotting stage.
#   • NEW: Preserve single-core safeguards and explicit INI_PATH routing like the other workflow stages.
#   • SAFETY: No queue fan-out or dependency logic here; this job only reads completed merged outputs.
#SBATCH --account=wsu
#SBATCH --job-name=xscape_mbplt
#SBATCH --qos=primary
#SBATCH --mem=12G
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --time=02:00:00
#SBATCH --export=ALL

set -Eeuo pipefail
log(){ echo "[$(date +'%F %T')] $*"; }
die(){ log "[FATAL] $*"; exit 2; }

BASE_DIR="${SLURM_SUBMIT_DIR:-$(pwd)}"
INI_PATH="${INI_PATH:-${JETSCAPE_INI_PATH:-${BASE_DIR}/jetscape.ini}}"

# Resolve a deterministic diagnostic log directory even when the user cannot find Slurm's %j files.
if [[ -f "${INI_PATH}" ]]; then
  # shellcheck disable=SC1090
  source "${INI_PATH}" || true
fi
BRICK_BASE_TAG_FOR_LOG="${VACBRICK_PLOTTER_BRICK_BASE_TAG:-${MULTISIM_PLOT_BRICK_BASE_RUN_TAG:-${RUN_TAG:-multisim}}}"
TS_FOR_LOG="${VACBRICK_PLOTTER_TS:-$(date +%Y%m%d_%H%M%S)}"
if [[ -n "${VACBRICK_PLOTTER_LOG_DIR:-}" ]]; then
  LOG_DIR="${VACBRICK_PLOTTER_LOG_DIR}"
else
  RUNS_BASE_RESOLVED="${RUNS_BASE:-$HOME/xscape_runs/${RUN_TAG:-${BRICK_BASE_TAG_FOR_LOG}}}"
  RUNS_ROOT="${RUNS_BASE_RESOLVED%/${RUN_TAG:-${BRICK_BASE_TAG_FOR_LOG}}}"
  [[ -n "${RUNS_ROOT}" ]] || RUNS_ROOT="$HOME/xscape_runs"
  LOG_DIR="${RUNS_ROOT}/${BRICK_BASE_TAG_FOR_LOG}/logs/plotter"
fi
mkdir -p "${LOG_DIR}"
JOB_ID_FOR_LOG="${SLURM_JOB_ID:-manual}"
DRIVER_OUT="${LOG_DIR}/vacbrick_plotter_${BRICK_BASE_TAG_FOR_LOG}_${TS_FOR_LOG}_${JOB_ID_FOR_LOG}.driver.out"
DRIVER_ERR="${LOG_DIR}/vacbrick_plotter_${BRICK_BASE_TAG_FOR_LOG}_${TS_FOR_LOG}_${JOB_ID_FOR_LOG}.driver.err"
TRACE_LOG="${LOG_DIR}/vacbrick_plotter_${BRICK_BASE_TAG_FOR_LOG}_${TS_FOR_LOG}_${JOB_ID_FOR_LOG}.traceback.log"

# Mirror everything to deterministic files. Slurm --output/--error still receive the same stream too.
exec > >(tee -a "${DRIVER_OUT}") 2> >(tee -a "${DRIVER_ERR}" >&2)

HEARTBEAT_PID=""
on_err(){
  local rc=$?
  log "[ERR] command failed with rc=${rc} at line ${BASH_LINENO[0]}: ${BASH_COMMAND}"
}
on_exit(){
  local rc=$?
  set +e
  if [[ -n "${HEARTBEAT_PID}" ]]; then
    kill "${HEARTBEAT_PID}" >/dev/null 2>&1 || true
    wait "${HEARTBEAT_PID}" 2>/dev/null || true
  fi
  log "[EXIT] vacbrick_plotter.slurm exit_code=${rc}"
  log "[diagnostics] driver_stdout=${DRIVER_OUT}"
  log "[diagnostics] driver_stderr=${DRIVER_ERR}"
  log "[diagnostics] python_traceback=${TRACE_LOG}"
  if command -v sacct >/dev/null 2>&1 && [[ -n "${SLURM_JOB_ID:-}" ]]; then
    log "[sacct] job accounting summary:"
    sacct -j "${SLURM_JOB_ID}" --format=JobID,JobName%30,State,ExitCode,Elapsed,MaxRSS,ReqMem -P || true
  fi
  exit "${rc}"
}
trap on_err ERR
trap on_exit EXIT

heartbeat(){
  while true; do
    sleep 300
    log "[heartbeat] plotter still running; job_id=${SLURM_JOB_ID:-manual}; trace_log=${TRACE_LOG}"
  done
}
heartbeat & HEARTBEAT_PID=$!

log "[diagnostics] driver_stdout=${DRIVER_OUT}"
log "[diagnostics] driver_stderr=${DRIVER_ERR}"
log "[diagnostics] python_traceback=${TRACE_LOG}"

module purge
if module -q load python/3.10 2>/dev/null; then
  log "[module] loaded python/3.10"
elif module -q load python/3.8 2>/dev/null; then
  log "[module] loaded python/3.8"
elif module -q load python 2>/dev/null; then
  log "[module] loaded python (default)"
else
  die "Could not load a python module"
fi
export PYTHONUSERBASE=$HOME/.local
export PATH=$PYTHONUSERBASE/bin:$PATH
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1

export PYTHONPATH="${BASE_DIR}:${PYTHONPATH:-}"
INI_PATH="${INI_PATH:-${JETSCAPE_INI_PATH:-${BASE_DIR}/jetscape.ini}}"
[[ -f "${INI_PATH}" ]] || die "Missing ini file: ${INI_PATH}"

PYBIN=""
if command -v python3 >/dev/null 2>&1; then
  PYBIN="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  PYBIN="$(command -v python)"
fi
[[ -n "${PYBIN}" ]] || die "No python executable found after module load"
"${PYBIN}" -c "import numpy, matplotlib, uproot" 2>/dev/null || die "Missing python deps (numpy/matplotlib/uproot)."

cd "${BASE_DIR}"
log "[cfg] BASE_DIR=${BASE_DIR}"
log "[cfg] INI_PATH=${INI_PATH}"
log "[cfg] LOG_DIR=${LOG_DIR}"
export VACBRICK_PLOTTER_TRACE_LOG="${TRACE_LOG}"
export PYTHONFAULTHANDLER=1
log "[run] launching ${PYBIN} -X faulthandler ${BASE_DIR}/vacbrick_plotter_py.py --ini ${INI_PATH}"
set +e
"${PYBIN}" -X faulthandler "${BASE_DIR}/vacbrick_plotter_py.py" --ini "${INI_PATH}"
PY_RC=$?
set -e
log "[run] python exit code=${PY_RC}"
exit "${PY_RC}"
