#!/usr/bin/env bash
# submit_jetscape_sliced.slurm v7.1
# CHANGELOG
# v7.1 (clean attempt labels + quiet internal retry stderr):
#   • CHANGE: Internal retry attempt records are now 1-based everywhere: attempt001.json, XML attempt001, and logs attempt=1/N.
#   • FIX: Failed internal PythiaIsrMUSIC/srun retries now write stdout+stderr to each attempt_dir/attempt.log instead of polluting Slurm .err with recoverable messages.
#   • LOG: Worker prints the per-attempt log path and the tail of failed attempt logs into Slurm stdout for debugging without false .err alarms.
# v7.0 (fix Pythia runtime env for PythiaIsrMUSIC on Wayne grid):
#   • FIX: Export PYTHIA8DIR from pythia8-config --prefix after loading the pythia module.
#   • FIX: Export PYTHIA8/P8INC/P8LIB/PYTHIA8DATA when discoverable so Pythia-dependent hadronization does not abort before physics.
#   • LOG: Record resolved pythia8-config path and PYTHIA8DIR in Slurm stdout before running attempts.
#   • NO CHANGE: XML physics, retry logic, output file names, Slurm resources, and analyzer/merge contracts are unchanged.
# v6.9 (realistic pp PythiaIsrMUSIC staged retry worker):
#   • NEW: RealisticPPWorkflow=1 runs PythiaIsrMUSIC from build/ but from a per-attempt staged working directory.
#   • NEW: Copies mcglauber.input, music_input_Luke, and iSS_parameters.dat into each attempt; symlinks tables, iSS_tables, and EOS.
#   • NEW: Supports PythiaIsrMUSIC two-argument launch: user XML plus config/jetscape_main.xml.
#   • NEW: Adds internal per-task retry loop with fresh seeds for stochastic pp zero-surface/iSS failures before relying on manager resubmits.
#   • KEEP: Canonical installed output remains job<TASK>_final_state_hadrons.dat for existing analyzer/merge compatibility.
# v6.8 (custom ini-path + absolute XML template support):
#   • NEW: Honor INI_PATH / JETSCAPE_INI_PATH so wrapper-generated per-variant ini files can drive the existing SIM worker.
#   • NEW: If XML_TEMPLATE is an absolute path, use it directly instead of forcing ${CONFIG_SUBDIR}/<template>.
#   • NO CHANGE: Canonical hadron names, seed accounting, meta contracts, and downstream file locations remain unchanged.
# v6.7 (fix false post-run failure in infer_event_index_base):
#   • FIX: Remove the `head ... | awk ... exit` pipeline from infer_event_index_base(). Under `set -o pipefail`,
#     awk exits as soon as it finds the first event header, head then receives SIGPIPE, and the worker can die with rc=141
#     after a successful runJetscape completion and hadron-file install.
#   • FIX: Read the first matching event header with a single awk pass, preserving the same 0/1 base detection without the
#     pipefail/SIGPIPE hazard.
#   • NO CHANGE: Hadron naming, event-count policy, sigma validation, seed allocation, and downstream file contracts are unchanged.
#
# v6.6 (comment/changelog consistency cleanup):
#   • DOC: Correct the historical v3.1 note so it no longer claims a log-scrape fallback that this script no longer implements.
#   • NO CHANGE: Runtime behavior is unchanged; sigmaGen/sigmaErr are still read strictly from the hadron file.
#
# v6.5 (manager-only seeds_seen writing):
#   • CHANGE: Remove all worker-side writes to any seeds_seen CSV during active runs.
#     Workers now write only the authoritative per-attempt ${SLICE_DIR}/seed_launches/job<TASK>.attempt<N>.json record,
#     and the SIM manager rebuilds the final ${DIR_FINAL}/seeds_seen.csv after the queue drains.
#   • CLEANUP: Remove the live seeds_seen_current_launch.csv append function/call and stale logging/comments tied to it.
#   • NO CHANGE: Seed allocation, retry burning, launch-record contents, and downstream final canonical seeds_seen.csv format remain the same.
#
# v6.4 (nonfatal live-seed TSV append + errtrace):
#   • FIX: Make the live current-launch seed CSV append best-effort instead of fatal. On some shared filesystems,
#     `flock`/lock-file operations can fail, and workers were dying immediately after writing the per-attempt seed JSON.
#     We now try locked append first, then fall back to an unlocked append, and if both fail we log a warning and continue.
#   • FIX: Enable `set -E` so the ERR trap also fires for failures inside functions/subshells, making future silent exits much easier to diagnose.
#   • FIX: Apply the same nonfatal lock fallback to sigma failure TSV appends so a lock issue cannot mask the real task outcome.
#
# v6.3 (fix rendered-XML sed command break):
#   • FIX: Remove the blank line inside the backslash-continued `sed` command that renders the XML template.
#     In Bash, that blank line terminated the continued command, so the next `-e` was executed as a command and the worker died with `-e: command not found`.
#   • NO CHANGE: Seed allocation, hadron naming, staging, and downstream file contracts are unchanged.
#
# v6.2 (tmpdir staging + crash-aware meta):
#   • PERF: Stage the rendered XML and runJetscape hadron output in a task-local $TMPDIR directory, then copy only the final canonical hadron file back to ${SLICE_DIR}.
#     This reduces shared-filesystem write pressure without changing downstream file names or locations.
#   • FIX: ERR/INT/TERM now rewrite the task meta with the real exit code and failing command when possible, instead of leaving a misleading generic "job started" meta behind.
#   • CLEANUP: Remove task-local staging files automatically and delete orphaned shared *.tmp.<jobid> install files after failures.
#
# v6.1 (authoritative per-attempt seed launch records):
#   • FIX: Stop deriving retry offsets from quarantine-file counts. Each task now allocates its retry/attempt index from
#     ${SLICE_DIR}/seed_launches/job<TASK>.attempt<N>.json before runJetscape starts, so a crash before quarantine still burns that seed.
#   • NEW: Write one immutable per-attempt seed launch record with run_tag, batch_id, slice/task ids, pTHat range, attempt, seed, launch time, and Slurm job id.
#   • LOG: Worker logs report the launch-record path for exact auditability before runJetscape starts.
#
# v5.9 (final-dir seeds_seen.csv export):
#   • CHANGE: After computing the actual task seed, append it to ${DIR_FINAL}/seeds_seen.csv in the format
#       pthat_low,pthat_high,task,seed
#     using a lock file for cross-task safety. This records launched SIM seeds directly at the source in the canonical final directory.
#
# v5.7 (rename sim extra-file knob):
#   • RENAME: Primary ini/env knob is now WriteSimExtraFiles / WRITE_SIM_EXTRA_FILES.
#   • CLEANUP: Remove legacy WriteSimMetaFiles / WRITE_SIM_META fallback handling after the repo-wide ini rename.
#   • NO CHANGE: The knob still controls only whether xsec_*.txt, weight_*.txt, xsecerr_*.txt sidecars are written.
# v5.6 (strict sigma positivity to match analyzer):
#   • FIX: After reading sigmaGen/sigmaErr from the hadron file, hard-fail the task unless BOTH values are finite and > 0.
#   • FIX: On nonpositive/invalid sigma, write meta status=incomplete, append a sigma failure row, quarantine only that hadron file, and exit nonzero so the manager resubmits just that task.
#   • NO CHANGE: Does not fail the whole slice/pack; existing watchdog/resubmit flow still handles one bad task at a time.
# v5.5 (disable redundant pthat_*.log generation):
#   • CHANGE: Stop writing per-task ${DIR_LOG_SIM}/pthat_<L>_<H>_<TASK>.log entirely.
#     When WriteSimLogs=1, runJetscape output now goes only to Slurm stdout (slurm-<jobid>.out), avoiding duplication.
#     When WriteSimLogs=0, behavior is unchanged: runJetscape stdout/stderr are suppressed to /dev/null.
# v5.4 (fix event counting off-by-one for tab-delimited headers):
#   • FIX: infer_event_index_base() previously used grep -E patterns with `\b` and only matched space-delimited
#     `# Event <id>` headers. JetScape writes tab-delimited headers like `#\tEvent\t1`, so BASE defaulted to 0.
#     That made events_written = last_id - base + 1 become 101 for a 100-event file (last_id=100).
#     We now parse the first event header with awk (POSIX-safe) and accept either spaces or tabs.
#     Result: a 100-event file with headers Event 1..100 yields events_written=100 and is no longer quarantined.
#
# v5.3 (robust SLURM_SUBMIT_DIR fallback):
#   • FIX: Under `set -u`, `${SLURM_SUBMIT_DIR}` may be unset in unusual/debug contexts. We now fall back to $PWD,
#     and if jetscape.ini is not found there, fall back to the script directory. Normal sbatch behavior is unchanged.
#
# v5.2 (enforce canonical hadron filename):
#   • FIX: Ignore/override any HADRON_SUFFIX from the environment. Downstream manager/analyzer assume
#     the canonical job${TASK}_final_state_hadrons.dat name, so allowing env overrides creates silent mismatches.
#
# v5.1 (robust last-event detection):
#   • FIX: events_last_id() now falls back beyond `tail -n 20000` (tries 200k tail, then a fast reverse-scan).
#     Prevents false "incomplete" quarantines when the final event header lies above the small tail window.
#
# v5.0 (meta safety + faster filesize):
#   • FIX: Prevent crash under `set -u` by defining HADRON_SUFFIX/HADRON_FILE before first write_task_meta.
#   • PERF: Replace `wc -c` (reads whole file) with `stat -c %s` (metadata only) for filesize_bytes.
#   • ROBUST: write_task_meta now tolerates missing HADRON_FILE gracefully.
#
# v4.9 (per-task meta files + worker-side completeness):
#   • NEW: Each worker writes a tiny per-task meta record to ${SLICE_DIR}/meta/job${TASK}.json.
#     Status is written as "incomplete" at job start and atomically updated to "ok" only after:
#       (1) hadron file exists, (2) events_written == NUM_EVENTS, (3) sigmaGen/sigmaErr are readable.
#   • NEW: Worker enforces event completeness (no more manager scanning hadron files). If incomplete:
#       - quarantine hadron file (reason=incomplete_events)
#       - leave meta status=incomplete (with events_written/last_event_id) and exit nonzero
#   • PERF: Enables the manager to skip DONE tasks and build manifests/reports without touching big hadron files.
#
# v4.8 (fix Slurm cpu-bind failures + safer ERR trap):
#   • FIX: Force `srun --cpu-bind=none` to avoid site/user default CPU binding masks that can be outside the
#     allocated cpuset (the classic: "Unable to satisfy cpu bind request").
#   • NEW: Log the resolved SLURM_* cpu-bind environment before launching `srun` for easier debugging.
#   • FIX: ERR trap no longer hard-crashes under `set -u` if BASH_SOURCE[0] is unexpectedly unset.
# v4.7 (bash + env robustness):
#   • FIX: Removed a stray orphan 'else ... fi' block that made this script fail 'bash -n'.
#   • NEW: Ensure python3 is available before running sigmaGen/sigmaErr extraction (tries common python modules).
#
# v4.6 (strict sigmaGen/sigmaErr extraction; no log scraping):
#   • NEW: Require sigmaGen AND sigmaErr to be present in the hadron file header.
#     If missing/unreadable: quarantine the hadron file (reason=sigma_missing),
#     append a row to ${DIR_FINAL}/sigma_read_failures.tsv, and exit nonzero.
#   • REMOVED: Any fallback that scraped "X mb" strings from logs (was incorrect/ambiguous).
#   • Even when WriteSimExtraFiles=0, we still validate sigmaGen/sigmaErr and hard-fail if absent.
#
# v4.5 (seed retry + weight safety):
#   • FIX #31: On resubmission, PYTHIA got the same seed and reproduced the same
#     incomplete run. Now: count quarantined files for this task in ${SLICE_DIR}/quarantine
#     and use that count as RETRY_OFFSET in the seed formula:
#       SEED_RAW = BASE_SEED + SLI*STRIDE + TASK + RETRY_OFFSET*7919
#     7919 is a prime to spread seeds. Each retry gets a different random sequence.
#   • FIX #23: Per-task weight file (when WRITE_SIM_EXTRA_FILES=1) used NUM_JOBS as denominator,
#     which assumes ALL jobs complete. Added WARNING log and comment that the per-slice
#     sim_manifest.json (written by submit_sliced_sim.sh after all tasks finish) is the
#     authoritative weight source. WRITE_SIM_EXTRA_FILES=0 by default, so this rarely fires.
#
# v4.3 (bugfix: env override respected):
#   • FIX: WRITE_SIM_LOGS no longer gets clobbered after reading env/ini; environment override now works as intended.
#
# v4.1 (reduce file spam + no per-task emails):
#   • Removed per-task Slurm mail directives (manager scripts send at most one email).
#   • Added WriteSimExtraFiles=0/1 support: when 0, do not write xsec/weight/xsecerr per task.
#   • If WriteSimLogs=0, we no longer require pthat_*.log for xsec extraction; meta extraction prefers hadron header.
#
# v4.0 (multiplier batches + non-array tasks):
#   • Supports job-cap aware "packs": accepts TASK_ID (global per-slice task index) and SIM_BATCH_ID (stable output folder).
#   • Deterministic unique RNG seeds: seed = BASE_SEED + SLICE_INDEX*SeedStrideSlice + TASK_ID (no repeats across packs).
#   • Works as array job OR single job (no SLURM_ARRAY_* required).
#
# v3.3 (minor):
#   • Respect jetscape.ini WriteSimLogs:
#       - WriteSimLogs=1 -> write per-task ${DIR_LOG_SIM}/pthat_<L>_<H>_<TASK>.log (current behavior)
#       - WriteSimLogs=0 -> do NOT write pthat logs; also suppress runJetscape stdout/stderr (goes to /dev/null)
#
# v3.2 (critical safety fix):
#   • FIX LD_LIBRARY_PATH hazard: do NOT prepend /usr/lib64 (can override libstdc++ and re-trigger CXXABI errors).
#     We now append SYSTEM_LD_PREPEND at the END of LD_LIBRARY_PATH.
#   • FIX set -e / pipefail hazard: xsec extraction no longer hard-exits when sigmaGen is missing.
#     All awk/grep pipelines are guarded and we explicitly return failure to trigger fallback.
#
# v3.1 (critical bugfix):
#   • FIX xsec/weight extraction: read sigmaGen/sigmaErr from job*_final_state_hadrons.dat
#     instead of grepping the last "X mb" from stdout (which was often MPI sigmaInteraction).
#   • HISTORICAL NOTE: Later versions removed any remaining log-scrape fallback; current behavior is hadron-file-only.
#
# v3.0:
#   • X-SCAPE migration: assumes this file lives in the X-SCAPE repo root (still runs ./runJetscape).
#   • Writes the per-task templated XML into the slice output directory (no more writing into config/).
#   • Adds defensive LD_LIBRARY_PATH setup (optionally prepends /usr/lib64 and ${REPO_ROOT}/lib).
#   • Much noisier logging + an ERR trap to show exactly what failed and where.
# v2.x:
#   • Original sliced-array runner + cross section/weight extraction.
#
# SUBMIT (preferred): use the wrapper
#   bash submit_sliced_sim.sh
#
# NOTE:
#   - SLURM --output/--error are set by the wrapper.
#   - When WriteSimLogs=0, wrapper routes them to /dev/null.

#SBATCH --account=wsu
#SBATCH --job-name=xscape_sliced
#SBATCH --qos=primary
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:30:00
#SBATCH --export=ALL

set -Eeuo pipefail



ts(){ date +'%F %T'; }
log(){ echo "[$(ts)] $*"; }
die(){ log "[FATAL] $*"; exit 1; }

task_failure_handler(){
  local rc="$1"
  local sig="${2:-ERR}"
  local src="${BASH_SOURCE[1]-${BASH_SOURCE[0]-$0}}"
  local line="${BASH_LINENO[0]-${LINENO}}"
  local cmd="${BASH_COMMAND-unknown}"
  log "[FATAL] ${src}:${line}  signal=${sig}  rc=${rc}  cmd=${cmd}"
  if declare -F write_task_meta >/dev/null 2>&1 && [[ -n "${META_FILE:-}" ]]; then
    write_task_meta "incomplete" "${EVENTS_WRITTEN:-0}" "${LASTID:-}" "${BASE:-}" "${XS:-}" "${XERR:-}" "failed signal=${sig} rc=${rc} cmd=${cmd}" "${rc}" || true
  fi
  rm -f -- "${HADRON_TMP_INSTALL:-}" 2>/dev/null || true
  if [[ -n "${TASK_TMP_DIR:-}" && -d "${TASK_TMP_DIR}" ]]; then
    rm -rf -- "${TASK_TMP_DIR}" 2>/dev/null || true
  fi
}
trap 'rc=$?; task_failure_handler "${rc}" ERR; exit "${rc}"' ERR
trap 'task_failure_handler 130 INT; exit 130' INT
trap 'task_failure_handler 143 TERM; exit 143' TERM

BASE_DIR="${SLURM_SUBMIT_DIR:-$PWD}"
if [[ ! -f "${BASE_DIR}/jetscape.ini" ]]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  if [[ -f "${SCRIPT_DIR}/jetscape.ini" ]]; then
    BASE_DIR="${SCRIPT_DIR}"
  else
    die "Cannot find jetscape.ini in SLURM_SUBMIT_DIR/PWD (${BASE_DIR}) or script dir (${SCRIPT_DIR})."
  fi
fi
INI_PATH="${INI_PATH:-${JETSCAPE_INI_PATH:-${BASE_DIR}/jetscape.ini}}"
[[ -f "${INI_PATH}" ]] || die "jetscape.ini not found: ${INI_PATH}"
# shellcheck disable=SC1090
source "${INI_PATH}"

log "[INI] Using jetscape.ini: ${INI_PATH}"
# ---- knobs (safe defaults under set -u) ----
WRITE_SIM_EXTRA_FILES="${WRITE_SIM_EXTRA_FILES:-${WriteSimExtraFiles:-0}}"
WRITE_SIM_LOGS="${WRITE_SIM_LOGS:-${WriteSimLogs:-1}}"
JOB="${SLURM_ARRAY_JOB_ID:-${SLURM_JOB_ID:-NA}}"
TASK="${TASK_ID:-${SLURM_ARRAY_TASK_ID:-1}}"
PT_L="${PT_LOW}"
PT_H="${PT_HIGH}"
NJ="${NUM_JOBS:-1}"
SLI="${SLICE_INDEX:-0}"
BATCH_ID="${SIM_BATCH_ID:-${JOB}}"

log "[job] host=$(hostname)  job=${JOB} task=${TASK}  slice=${PT_L}-${PT_H}  slice_index=${SLI}  njobs=${NJ}  batch=${BATCH_ID}"
log "[job] base_dir=${BASE_DIR}"
log "[job] WriteSimLogs=${WRITE_SIM_LOGS}  WriteSimExtraFiles=${WRITE_SIM_EXTRA_FILES}"

module purge
module load gnu7/7.3.0 mpich/3.2.1
module load root/6.28.10
module load pythia/8.303 fastjet/3.4.0 boost/1.67.0 gsl/2.5
module load hdf5/1.12.1 zlib/1.3.1 intel/2020
module -t list 2>&1 | sed 's/^/[module] /'

ensure_pythia8_runtime_env(){
  if [[ -z "${PYTHIA8DIR:-}" ]]; then
    if command -v pythia8-config >/dev/null 2>&1; then
      PYTHIA8DIR="$(pythia8-config --prefix 2>/dev/null || true)"
    fi
  fi
  if [[ -z "${PYTHIA8DIR:-}" && -d "/wsu/el7/gnu7/pythia/8.303" ]]; then
    PYTHIA8DIR="/wsu/el7/gnu7/pythia/8.303"
  fi
  [[ -n "${PYTHIA8DIR:-}" && -d "${PYTHIA8DIR}" ]] || die "PYTHIA8DIR could not be resolved after loading pythia/8.303. Try: export PYTHIA8DIR=\`pythia8-config --prefix\`."
  export PYTHIA8DIR
  export PYTHIA8="${PYTHIA8:-${PYTHIA8DIR}}"
  export P8INC="${P8INC:-${PYTHIA8DIR}/include}"
  export P8LIB="${P8LIB:-${PYTHIA8DIR}/lib}"
  if [[ -z "${PYTHIA8DATA:-}" ]]; then
    if [[ -d "${PYTHIA8DIR}/share/Pythia8/xmldoc" ]]; then
      export PYTHIA8DATA="${PYTHIA8DIR}/share/Pythia8/xmldoc"
    elif [[ -d "${PYTHIA8DIR}/xmldoc" ]]; then
      export PYTHIA8DATA="${PYTHIA8DIR}/xmldoc"
    fi
  fi
  log "[env] pythia8-config=$(command -v pythia8-config 2>/dev/null || echo '<not found>')"
  log "[env] PYTHIA8DIR=${PYTHIA8DIR}"
  log "[env] PYTHIA8DATA=${PYTHIA8DATA:-<unset>}"
}
ensure_pythia8_runtime_env

# Ensure python3 exists (needed for strict sigmaGen/sigmaErr extraction).
ensure_python3(){
  if command -v python3 >/dev/null 2>&1; then
    log "[env] python3=$(command -v python3)"
    return 0
  fi
  log "[env] python3 not found in PATH; attempting to load a python module..."
  local cand
  for cand in python/3.11 python/3.10 python/3.9 python/3.8 python; do
    module load "${cand}" >/dev/null 2>&1 || true
    if command -v python3 >/dev/null 2>&1; then
      log "[env] loaded ${cand}; python3=$(command -v python3)"
      return 0
    fi
  done
  # Last resort: log a short module hint for debugging (won't spam output).
  { module -t avail python 2>&1 | head -n 25 | sed 's/^/[module-avail] /'; } || true
  die "python3 not found. Install/load python3 on compute nodes or adjust modules in this script."
}
ensure_python3

# -------------------- TASK META (fast, race-free) --------------------
# Each worker writes ${SLICE_DIR}/meta/job${TASK}.json
# We write status="incomplete" at start and atomically update to "ok" only after success.
utc_now(){ date -u +'%F %T'; }

next_seed_attempt_index(){
  # Return a 1-based attempt index. The first launched seed record is attempt001,
  # matching user-facing XML/log labels attempt=1/N. Seed offsets still use
  # zero-based retry math through retry_index = attempt_index - 1.
  local launch_dir="$1"
  local task="$2"
  local count=0
  shopt -s nullglob
  local records=("${launch_dir}/job${task}.attempt"*.json)
  count=${#records[@]}
  shopt -u nullglob
  printf '%s
' "$((count + 1))"
}

write_seed_launch_record(){
  local launch_dir="$1"
  local attempt="$2"
  local attempt_pad
  attempt_pad="$(printf '%03d' "${attempt}")"
  local record="${launch_dir}/job${TASK}.attempt${attempt_pad}.json"
  local tmp="${record}.tmp.$$"
  mkdir -p "${launch_dir}"
  if [[ -e "${record}" ]]; then
    die "Seed launch record already exists for task=${TASK} attempt=${attempt}: ${record}"
  fi
  python3 - <<'PY' \
    "${tmp}" "${record}" \
    "${RUN_TAG}" "${BATCH_ID}" \
    "${PT_L}" "${PT_H}" "${SLI}" "${TASK}" "${attempt}" \
    "${SEED}" "${SEED_SALT_TIME:-0}" \
    "${SLURM_JOB_ID:-}" "${SLURM_ARRAY_JOB_ID:-}" "${SLURM_ARRAY_TASK_ID:-}" \
    "${META_START_UTC}" "${HOSTNAME:-}" "${USER:-}"
import json, os, sys
(tmp_path, final_path,
 run_tag, batch_id,
 pt_l, pt_h, slice_index, task, attempt,
 seed, seed_salt_time,
 slurm_job_id, slurm_array_job_id, slurm_array_task_id,
 launch_time_utc, hostname, username) = sys.argv[1:]
obj = {
    "run_tag": run_tag,
    "batch_id": batch_id,
    "pthat_low": int(pt_l),
    "pthat_high": int(pt_h),
    "slice_index": int(slice_index),
    "task": int(task),
    "attempt": int(attempt),
    "seed": int(seed),
    "seed_salt_time": int(seed_salt_time),
    "launch_time_utc": launch_time_utc,
    "slurm_job_id": slurm_job_id,
    "slurm_array_job_id": slurm_array_job_id,
    "slurm_array_task_id": slurm_array_task_id,
    "hostname": hostname,
    "user": username,
}
with open(tmp_path, "w", encoding="utf-8") as f:
    json.dump(obj, f, indent=2, sort_keys=True)
    f.write("\n")
os.replace(tmp_path, final_path)
PY
  log "[seed_record] wrote ${record} (attempt=${attempt} seed=${SEED})"
}

write_task_meta(){
  # Args:
  #   status events_written last_event_id event_index_base sigmaGen_mb sigmaErr_mb note exit_code
  local status="$1"
  local events_written="$2"
  local last_event_id="$3"
  local event_index_base="$4"
  local sigmaGen_mb="$5"
  local sigmaErr_mb="$6"
  local note="$7"
  local exit_code="${8:-0}"

  # HADRON_FILE may not exist yet; under `set -u` we must also tolerate it being unset.
  local hadron_file="${HADRON_FILE:-}"
  local bytes=0
  if [[ -n "${hadron_file}" && -f "${hadron_file}" ]]; then
    # Use metadata-only size query (fast on shared FS).
    bytes=$(stat -c %s "${hadron_file}" 2>/dev/null || echo 0)
  fi

  local tmp="${META_FILE}.tmp.$$"
  python3 - <<'PY' \
    "${tmp}" "${META_FILE}" \
    "${RUN_TAG}" "${PT_L}" "${PT_H}" "${SLI}" "${TASK}" "${BATCH_ID}" \
    "${status}" "${events_written}" "${last_event_id}" "${event_index_base}" \
    "${NUM_EVENTS}" "${sigmaGen_mb}" "${sigmaErr_mb}" "${bytes}" \
    "${hadron_file}" \
    "$(hostname)" "${SLURM_JOB_ID:-}" "${SLURM_ARRAY_JOB_ID:-}" "${SLURM_ARRAY_TASK_ID:-}" \
    "${META_START_UTC}" "$(utc_now)" \
    "${exit_code}" "${note}"
import json, os, sys, time
(
  tmp, out,
  run_tag, ptL, ptH, slice_index, task_id, batch_id,
  status, events_written, last_event_id, event_index_base,
  num_events_target, sigmaGen_mb, sigmaErr_mb, filesize_bytes,
  hadron_file,
  host, slurm_job_id, slurm_array_job_id, slurm_array_task_id,
  start_utc, end_utc,
  exit_code, note
) = sys.argv[1:]

def to_int(x, default=None):
  try:
    return int(str(x).strip())
  except Exception:
    return default

def to_float(x, default=None):
  s = str(x).strip()
  if s == "" or s.lower() == "none":
    return default
  try:
    return float(s)
  except Exception:
    return default

obj = {
  "schema": "xscape.sim_task_meta.v1",
  "run_tag": run_tag,
  "pthat_low": to_int(ptL, 0),
  "pthat_high": to_int(ptH, 0),
  "slice_index": to_int(slice_index, 0),
  "task_id": to_int(task_id, 0),
  "batch_id": batch_id,
  "status": status,
  "num_events_target": to_int(num_events_target, None),
  "events_written": to_int(events_written, None),
  "last_event_id": to_int(last_event_id, None),
  "event_index_base": to_int(event_index_base, None),
  "sigmaGen_mb": to_float(sigmaGen_mb, None),
  "sigmaErr_mb": to_float(sigmaErr_mb, None),
  "filesize_bytes": to_int(filesize_bytes, 0),
  "hadron_file": hadron_file,
  "host": host,
  "slurm_job_id": str(slurm_job_id) if str(slurm_job_id).strip() else None,
  "slurm_array_job_id": str(slurm_array_job_id) if str(slurm_array_job_id).strip() else None,
  "slurm_array_task_id": str(slurm_array_task_id) if str(slurm_array_task_id).strip() else None,
  "start_time_utc": start_utc,
  "end_time_utc": end_utc,
  "exit_code": to_int(exit_code, 0),
  "note": note,
}

with open(tmp, "w") as f:
  json.dump(obj, f, indent=2, sort_keys=True)

# Atomic install
os.replace(tmp, out)
PY
}

infer_event_index_base(){
  # Determine whether event ids start at 0 or 1 by reading the FIRST event header.
  # JetScape may write either space-delimited (`# Event 1`) or tab-delimited (`#  Event 1`) headers.
  # Use a single awk pass so `set -o pipefail` cannot turn an early-match SIGPIPE into a false worker failure.
  local f="$1"
  [[ -s "${f}" ]] || { echo "0"; return 0; }

  local first_id=""
  first_id="$(awk '$1=="#" && $2=="Event" {print $3; exit}' "${f}" 2>/dev/null || true)"
  if [[ "${first_id}" == "0" ]]; then
    echo "0"; return 0
  fi
  if [[ "${first_id}" == "1" ]]; then
    echo "1"; return 0
  fi

  # Fallback: if header format ever changes, default to 0 (historical behavior).
  echo "0"
}

events_last_id(){
  # Last event id found in the hadron file (expects '# Event <id>' lines).
  # PERF: Prefer tail windows; FALLBACK: robust reverse-scan to avoid false "incomplete" when the last
  #       event header sits above a small tail window (rare but real for very long final events).
  local f="$1"
  [[ -s "${f}" ]] || { echo ""; return 0; }

  local n=""

  # Fast path: small tail window
  n="$(
    tail -n 20000 "${f}" 2>/dev/null       | grep -E '^#\s*Event'       | tail -n 1       | awk '{for(i=1;i<=NF;i++) if($i=="Event"){print $(i+1); exit}}'       || true
  )"
  [[ -n "${n}" ]] && { echo "${n}"; return 0; }

  # Fallback 1: larger tail window (still cheap)
  n="$(
    tail -n 200000 "${f}" 2>/dev/null       | grep -E '^#\s*Event'       | tail -n 1       | awk '{for(i=1;i<=NF;i++) if($i=="Event"){print $(i+1); exit}}'       || true
  )"
  [[ -n "${n}" ]] && { echo "${n}"; return 0; }

  # Fallback 2: fast reverse-scan from EOF (reads minimal blocks until it finds the last '# Event <id>')
  # This avoids full-file reads on shared FS in the rare case the last event header is above the tail window.
  if command -v python3 >/dev/null 2>&1; then
    n="$(
      python3 - "${f}" <<'PY' 2>/dev/null || true
import os, re, sys
path = sys.argv[1]
pat = re.compile(rb'(?m)^#\s*Event\s+(\d+)\b')
try:
    with open(path, 'rb') as f:
        f.seek(0, os.SEEK_END)
        end = f.tell()
        chunk = 1024 * 1024  # 1 MiB
        max_bytes = 64 * 1024 * 1024  # cap worst-case work
        pos = end
        buf = b""
        while pos > 0 and len(buf) < max_bytes:
            rd = chunk if pos >= chunk else pos
            pos -= rd
            f.seek(pos)
            data = f.read(rd)
            buf = data + buf
            m = None
            for m in pat.finditer(buf):
                pass
            if m:
                sys.stdout.write(m.group(1).decode('ascii', 'ignore'))
                sys.exit(0)
except Exception:
    pass
PY
    )"
    [[ -n "${n}" ]] && { echo "${n}"; return 0; }
  fi

  # Last resort: full scan (rare, but better than lying)
  n="$(
    grep -E '^#\s*Event' "${f}" 2>/dev/null       | tail -n 1       | awk '{for(i=1;i<=NF;i++) if($i=="Event"){print $(i+1); exit}}'       || true
  )"
  [[ -n "${n}" ]] && { echo "${n}"; return 0; }

  echo ""
}




quarantine_hadron(){
  local why="$1"
  local stamp; stamp="$(date +%s)"
  local qdir="${SLICE_DIR}/quarantine"
  mkdir -p "${qdir}"
  if [[ -f "${HADRON_FILE}" ]]; then
    mv -f "${HADRON_FILE}" "${qdir}/$(basename "${HADRON_FILE}").${why}.${stamp}" || true
    log "[quarantine] moved hadron file -> ${qdir}/$(basename "${HADRON_FILE}").${why}.${stamp}"
  fi
}
# --------------------------------------------------------------------


# LD_LIBRARY_PATH hygiene
# IMPORTANT:
#   - Putting /usr/lib64 FIRST can override libstdc++.so.6 from the gcc module and re-trigger CXXABI errors.
#   - Therefore we ALWAYS append SYSTEM_LD_PREPEND at the END, never at the front.
LD_LIBRARY_PATH="${LD_LIBRARY_PATH:-}"

# Ensure repo libs are available early (if enabled)
if [[ "${ADD_REPO_LIB_TO_LD_LIBRARY_PATH:-0}" -eq 1 ]]; then
  REPO_LIB="${BASE_DIR}/${REPO_LIB_SUBDIR}"
  if [[ -n "${LD_LIBRARY_PATH}" ]]; then
    LD_LIBRARY_PATH="${REPO_LIB}:${LD_LIBRARY_PATH}"
  else
    LD_LIBRARY_PATH="${REPO_LIB}"
  fi
fi

# Append system library dirs LAST (safe)
if [[ -n "${SYSTEM_LD_PREPEND:-}" ]]; then
  if [[ -n "${LD_LIBRARY_PATH}" ]]; then
    LD_LIBRARY_PATH="${LD_LIBRARY_PATH}:${SYSTEM_LD_PREPEND}"
  else
    LD_LIBRARY_PATH="${SYSTEM_LD_PREPEND}"
  fi
fi

export LD_LIBRARY_PATH
log "[env] LD_LIBRARY_PATH=${LD_LIBRARY_PATH:-<empty>}"

CONFIG_DIR="${BASE_DIR}/${CONFIG_SUBDIR}"
BUILD_DIR="${BASE_DIR}/${BUILD_SUBDIR}"
EXE_PATH="${BUILD_DIR}/${EXE_NAME}"

SLICE_DIR="${DIR_SIM}/${PT_L}-${PT_H}/${BATCH_ID}"
mkdir -p "${SLICE_DIR}" "${DIR_LOG_SIM}"

META_DIR="${SLICE_DIR}/meta"
META_FILE="${META_DIR}/job${TASK}.json"
mkdir -p "${META_DIR}"


# Resolve hadron output path before any meta writes (required under set -u).
# Enforce canonical hadron filename: downstream scripts assume this exact suffix.
# Do NOT allow env overrides (even accidental) because it causes silent "missing output" mismatches.
if [[ -n "${HADRON_SUFFIX:-}" && "${HADRON_SUFFIX}" != "_final_state_hadrons.dat" ]]; then
  log "[env] Ignoring HADRON_SUFFIX=${HADRON_SUFFIX} (using canonical _final_state_hadrons.dat)."
fi
HADRON_SUFFIX="_final_state_hadrons.dat"
HADRON_FILE="${SLICE_DIR}/job${TASK}${HADRON_SUFFIX}"
TASK_TMP_ROOT="${TMPDIR:-/tmp}"
TASK_TMP_DIR="$(mktemp -d "${TASK_TMP_ROOT%/}/xscape_sim_${RUN_TAG}_${PT_L}_${PT_H}_${TASK}_${SLURM_JOB_ID:-$$}_XXXXXX")"
[[ -n "${TASK_TMP_DIR}" && -d "${TASK_TMP_DIR}" ]] || die "Failed to create task tmp dir under ${TASK_TMP_ROOT}"
LOCAL_OUTPUT_PREFIX="${TASK_TMP_DIR}/job${TASK}"
HADRON_FILE_LOCAL="${LOCAL_OUTPUT_PREFIX}${HADRON_SUFFIX}"
HADRON_TMP_INSTALL="${HADRON_FILE}.tmp.${SLURM_JOB_ID:-$$}"
XML_OUT_SHARED="${SLICE_DIR}/jetscape_user_sliced_${PT_L}_${PT_H}_${TASK}.xml"
log "[stage] TASK_TMP_DIR=${TASK_TMP_DIR}"

META_START_UTC="$(utc_now)"
# Status starts as "incomplete" and will be updated to "ok" only after a fully successful task.
write_task_meta "incomplete" "0" "" "" "" "" "job started" 0

if [[ "${XML_TEMPLATE}" = /* ]]; then
  XML_IN="${XML_TEMPLATE}"
else
  XML_IN="${CONFIG_DIR}/${XML_TEMPLATE}"
fi
XML_OUT="${TASK_TMP_DIR}/jetscape_user_sliced_${PT_L}_${PT_H}_${TASK}.xml"

[[ -f "${XML_IN}" ]] || die "Missing XML template: ${XML_IN}"
[[ -x "${EXE_PATH}" ]] || die "Missing executable: ${EXE_PATH}"

if [[ "${RUN_LDD_ON_START:-0}" -eq 1 ]]; then
  log "[debug] ldd ${EXE_PATH}"
  ldd "${EXE_PATH}" 2>&1 | sed 's/^/[ldd] /' || true
fi

# -------------------- SEED/RUN/STAGE --------------------
# v6.9 keeps the legacy runJetscape path, but adds a RealisticPPWorkflow=1 branch for
# staged PythiaIsrMUSIC runs. The staged branch is needed because MCGlauber/MUSIC/iSS
# look for mcglauber.input, music_input_Luke, iSS tables, MUSIC tables, and EOS files
# relative to the process working directory.

render_user_xml(){
  local xml_in="$1"
  local xml_out="$2"
  local seed="$3"
  local output_prefix="$4"
  sed -e "s|\*\*NEVENTS_PLACEHOLDER\*\*|${NUM_EVENTS}|" \
      -e "s|\*\*SEED_PLACEHOLDER\*\*|${seed}|" \
      -e "s|\*\*OUTFILE_PLACEHOLDER\*\*|${output_prefix}|" \
      -e "s|\*\*PTHATMIN_PLACEHOLDER\*\*|${PT_L}|" \
      -e "s|\*\*PTHATMAX_PLACEHOLDER\*\*|${PT_H}|" \
      "${xml_in}" > "${xml_out}"
}

compute_next_seed(){
  ATTEMPT_INDEX="$(next_seed_attempt_index "${SEED_LAUNCH_DIR}" "${TASK}")"
  if ! [[ "${ATTEMPT_INDEX}" =~ ^[0-9]+$ ]] || (( ATTEMPT_INDEX < 1 )); then
    die "Non-numeric retry/attempt index for task=${TASK}: ${ATTEMPT_INDEX}"
  fi
  RETRY_OFFSET=$((ATTEMPT_INDEX - 1))
  local retry_stride="${PythiaIsrRetrySeedStride:-7919}"
  local seed_raw=$(( SEED_BASE + SLI*SEED_STRIDE + TASK + RETRY_OFFSET*retry_stride ))
  if [[ "${SEED_SALT_TIME:-0}" -eq 1 ]]; then
    local salt=$(( $(date +%s) % SEED_STRIDE ))
    seed_raw=$(( seed_raw + salt ))
  fi
  SEED=$(( (seed_raw % 2000000000) + 1 ))
  log "[seed] base=${SEED_BASE} stride=${SEED_STRIDE} slice_index=${SLI} task=${TASK} attempt=${ATTEMPT_INDEX} retry_offset=${RETRY_OFFSET} retry_stride=${retry_stride} -> seed=${SEED}"
}

stage_realistic_runtime_assets(){
  local attempt_dir="$1"
  local input_dir="${PythiaIsrInputDir:-${BASE_DIR}/myanalysis}"
  local stage_files="${PythiaIsrStageFiles:-mcglauber.input music_input_Luke iSS_parameters.dat}"
  local tables_dir="${PythiaIsrTablesDir:-${BASE_DIR}/build/tables}"
  local iss_tables_dir="${PythiaIsrISSTablesDir:-${BASE_DIR}/build/iSS_tables}"
  local eos_dir="${PythiaIsrEOSDir:-${input_dir}/EOS}"

  [[ "${input_dir}" = /* ]] || input_dir="${BASE_DIR}/${input_dir}"
  [[ "${tables_dir}" = /* ]] || tables_dir="${BASE_DIR}/${tables_dir}"
  [[ "${iss_tables_dir}" = /* ]] || iss_tables_dir="${BASE_DIR}/${iss_tables_dir}"
  [[ "${eos_dir}" = /* ]] || eos_dir="${BASE_DIR}/${eos_dir}"

  [[ -d "${input_dir}" ]] || die "PythiaIsrInputDir missing: ${input_dir}"
  [[ -d "${tables_dir}" ]] || die "PythiaIsr tables dir missing: ${tables_dir}"
  [[ -d "${iss_tables_dir}" ]] || die "PythiaIsr iSS tables dir missing: ${iss_tables_dir}"
  if [[ ! -d "${eos_dir}" ]]; then
    if [[ -d "${BASE_DIR}/build/EOS" ]]; then
      log "[stage] PythiaIsrEOSDir missing (${eos_dir}); falling back to ${BASE_DIR}/build/EOS"
      eos_dir="${BASE_DIR}/build/EOS"
    else
      die "PythiaIsr EOS dir missing: ${eos_dir} and ${BASE_DIR}/build/EOS not found"
    fi
  fi

  local f
  for f in ${stage_files}; do
    [[ -f "${input_dir}/${f}" ]] || die "Required staged input missing: ${input_dir}/${f}"
    cp -f "${input_dir}/${f}" "${attempt_dir}/${f}"
  done
  ln -sfn "${tables_dir}" "${attempt_dir}/tables"
  ln -sfn "${iss_tables_dir}" "${attempt_dir}/iSS_tables"
  ln -sfn "${eos_dir}" "${attempt_dir}/EOS"
  log "[stage] input_dir=${input_dir} tables=${tables_dir} iSS_tables=${iss_tables_dir} EOS=${eos_dir}"
}

run_legacy_jetscape_once(){
  compute_next_seed
  write_seed_launch_record "${SEED_LAUNCH_DIR}" "${ATTEMPT_INDEX}"
  render_user_xml "${XML_IN}" "${XML_OUT}" "${SEED}" "${LOCAL_OUTPUT_PREFIX}"
  log "[xml] wrote ${XML_OUT}"

  log "[run] cd ${BUILD_DIR}"
  cd "${BUILD_DIR}"
  log "[run] ${EXE_NAME} ${XML_OUT}"
  log "[slurm] cpu_bind env: SLURM_CPU_BIND=${SLURM_CPU_BIND:-unset} SLURM_CPU_BIND_TYPE=${SLURM_CPU_BIND_TYPE:-unset} SLURM_CPU_BIND_LIST=${SLURM_CPU_BIND_LIST:-unset}"

  if [[ "${WRITE_SIM_LOGS}" -eq 1 ]]; then
    srun --cpu-bind=none "${EXE_PATH}" "${XML_OUT}"
  else
    srun --cpu-bind=none "${EXE_PATH}" "${XML_OUT}" >/dev/null 2>&1
  fi

  log "[run] finished OK"
  if compgen -G "${LOCAL_OUTPUT_PREFIX}*" >/dev/null 2>&1; then
    NOUT="$(ls -1 ${LOCAL_OUTPUT_PREFIX}* 2>/dev/null | wc -l)"
    log "[out] produced ${NOUT} staged file(s) with prefix ${LOCAL_OUTPUT_PREFIX}"
  else
    log "[out] WARNING: no staged output files found with prefix ${LOCAL_OUTPUT_PREFIX}"
  fi

  if [[ -s "${HADRON_FILE_LOCAL}" ]]; then
    rm -f -- "${HADRON_TMP_INSTALL}"
    cp -f "${HADRON_FILE_LOCAL}" "${HADRON_TMP_INSTALL}"
    mv -f "${HADRON_TMP_INSTALL}" "${HADRON_FILE}"
    log "[stage] installed hadron ${HADRON_FILE_LOCAL} -> ${HADRON_FILE}"
  else
    log "[stage] WARNING: staged hadron file missing before shared install: ${HADRON_FILE_LOCAL}"
  fi
}

run_realistic_pythiaisrmusic_with_retries(){
  local main_xml_name="${PythiaIsrMainXml:-jetscape_main.xml}"
  local main_xml_path
  if [[ "${main_xml_name}" = /* ]]; then
    main_xml_path="${main_xml_name}"
  else
    main_xml_path="${CONFIG_DIR}/${main_xml_name}"
  fi
  [[ -f "${main_xml_path}" ]] || die "PythiaIsr main XML not found: ${main_xml_path}"

  local max_attempts="${PythiaIsrMaxAttemptsPerTask:-1}"
  if ! [[ "${max_attempts}" =~ ^[0-9]+$ ]] || (( max_attempts < 1 )); then
    die "PythiaIsrMaxAttemptsPerTask must be a positive integer; got ${max_attempts}"
  fi

  local accepted=0
  local internal_attempt
  for (( internal_attempt=1; internal_attempt<=max_attempts; internal_attempt++ )); do
    compute_next_seed
    write_seed_launch_record "${SEED_LAUNCH_DIR}" "${ATTEMPT_INDEX}"

    local attempt_pad
    attempt_pad="$(printf '%03d' "${ATTEMPT_INDEX}")"
    local attempt_dir="${TASK_TMP_DIR}/attempt_${attempt_pad}"
    mkdir -p "${attempt_dir}"
    stage_realistic_runtime_assets "${attempt_dir}"

    local xml_base="jetscape_user_sliced_${PT_L}_${PT_H}_${TASK}_attempt${attempt_pad}.xml"
    XML_OUT="${attempt_dir}/${xml_base}"
    LOCAL_OUTPUT_PREFIX="job${TASK}"
    HADRON_FILE_LOCAL="${attempt_dir}/${LOCAL_OUTPUT_PREFIX}${HADRON_SUFFIX}"
    local attempt_run_log="${attempt_dir}/attempt.log"
    render_user_xml "${XML_IN}" "${XML_OUT}" "${SEED}" "${LOCAL_OUTPUT_PREFIX}"
    log "[xml] attempt=${ATTEMPT_INDEX}/${max_attempts} wrote ${XML_OUT}"

    log "[run] attempt=${ATTEMPT_INDEX}/${max_attempts} cd ${attempt_dir}"
    log "[run] ${EXE_NAME} ${xml_base} ${main_xml_path}"
    log "[runlog] attempt=${ATTEMPT_INDEX}/${max_attempts} stdout+stderr -> ${attempt_run_log}"
    log "[slurm] cpu_bind env: SLURM_CPU_BIND=${SLURM_CPU_BIND:-unset} SLURM_CPU_BIND_TYPE=${SLURM_CPU_BIND_TYPE:-unset} SLURM_CPU_BIND_LIST=${SLURM_CPU_BIND_LIST:-unset}"

    local rc=0
    ( cd "${attempt_dir}" && srun --cpu-bind=none "${EXE_PATH}" "${xml_base}" "${main_xml_path}" ) >"${attempt_run_log}" 2>&1 || rc=$?

    local bytes=0
    if [[ -f "${HADRON_FILE_LOCAL}" ]]; then
      bytes=$(stat -c %s "${HADRON_FILE_LOCAL}" 2>/dev/null || echo 0)
    fi
    log "[run] attempt=${ATTEMPT_INDEX}/${max_attempts} exit=${rc} hadron=${HADRON_FILE_LOCAL} bytes=${bytes}"

    if [[ "${rc}" -eq 0 && -s "${HADRON_FILE_LOCAL}" ]]; then
      rm -f -- "${HADRON_TMP_INSTALL}"
      cp -f "${HADRON_FILE_LOCAL}" "${HADRON_TMP_INSTALL}"
      mv -f "${HADRON_TMP_INSTALL}" "${HADRON_FILE}"
      log "[stage] accepted attempt=${ATTEMPT_INDEX}; installed ${HADRON_FILE_LOCAL} -> ${HADRON_FILE}"
      cp -f "${XML_OUT}" "${XML_OUT_SHARED}.accepted_attempt${attempt_pad}" || true
      accepted=1
      break
    fi

    log "[retry] attempt=${ATTEMPT_INDEX}/${max_attempts} did not produce an accepted hadron file; trying a new seed if attempts remain"
    if [[ -s "${attempt_run_log}" ]]; then
      log "[retry] tail of ${attempt_run_log}:"
      tail -40 "${attempt_run_log}" | sed 's/^/[attempt-log] /' || true
    fi
  done

  if [[ "${accepted}" -ne 1 ]]; then
    log "[out] FATAL: no accepted PythiaIsrMUSIC attempt after ${max_attempts} internal attempts"
    write_task_meta "incomplete" "0" "" "" "" "" "no accepted PythiaIsrMUSIC attempt after ${max_attempts} tries" 2
    exit 2
  fi
}

# -------------------- XML + executable setup --------------------
SEED_BASE="${BASE_SEED:-1}"
SEED_STRIDE="${SeedStrideSlice:-1000000}"
SEED_LAUNCH_DIR="${SLICE_DIR}/seed_launches"

if [[ "${RealisticPPWorkflow:-0}" -eq 1 ]]; then
  run_realistic_pythiaisrmusic_with_retries
else
  run_legacy_jetscape_once
fi

# -------------------- XSEC/WEIGHT META (optional) --------------------
# STRICT POLICY (v4.6):
#   - sigmaGen/sigmaErr MUST be readable from the hadron file.
#   - NO log scraping fallbacks.
#   - If missing: quarantine hadron file + record failure + exit nonzero (so manager can resubmit).
#
# NOTE: This does NOT "stop all jobs" — only this task fails. The manager will see the task as missing/incomplete
# and can resubmit. The failure is made explicit in ${DIR_FINAL}/sigma_read_failures.tsv.
# HADRON_SUFFIX/HADRON_FILE already set above (needed before first meta write).


append_sigma_failure(){
  # Concurrency-safe-ish append (best effort). Also drops a per-task marker file.
  mkdir -p "${DIR_FINAL}"
  local tsv="${DIR_FINAL}/sigma_read_failures.tsv"
  local lock="${DIR_FINAL}/.sigma_read_failures.lock"
  local marker="${DIR_FINAL}/sigma_read_fail_job_${PT_L}_${PT_H}_${BATCH_ID}_${TASK}.txt"
  local msg="$1"
  local line
  line="$(printf "%s  %s  %s  %s  %s  %s  %s  %s
"             "$(ts)" "${RUN_TAG}" "${PT_L}" "${PT_H}" "${BATCH_ID}" "${TASK}" "${HADRON_FILE}" "${msg}")"

  # Marker file (unique -> no races)
  {
    echo "# sigma read failure marker"
    echo "ts=$(ts)"
    echo "run_tag=${RUN_TAG}"
    echo "pthat_low=${PT_L}"
    echo "pthat_high=${PT_H}"
    echo "batch_id=${BATCH_ID}"
    echo "task=${TASK}"
    echo "hadron_file=${HADRON_FILE}"
    echo "reason=${msg}"
  } > "${marker}" || true

  # TSV append (shared; guard with flock if available). Best effort only: marker file above remains the primary per-task breadcrumb.
  if command -v flock >/dev/null 2>&1; then
    if (
      flock -w 10 200 || exit 1
      if [[ ! -s "${tsv}" ]]; then
        printf "ts  run_tag pthat_low pthat_high  batch_id  task  hadron_file reason
" >> "${tsv}"
      fi
      printf "%s" "${line}" >> "${tsv}"
    ) 200>"${lock}"; then
      return 0
    else
      log "[sigma_fail] WARNING: locked append failed for ${tsv}; retrying without lock"
    fi
  fi

  if {
    if [[ ! -s "${tsv}" ]]; then
      printf "ts  run_tag pthat_low pthat_high  batch_id  task  hadron_file reason
" >> "${tsv}"
    fi
    printf "%s" "${line}" >> "${tsv}"
  }; then
    return 0
  fi

  log "[sigma_fail] WARNING: append failed for ${tsv}; marker file still written at ${marker}"
  return 0
}

quarantine_sigma_bad_hadron(){
  local why="$1"
  local stamp; stamp="$(date +%s)"
  local qdir="${SLICE_DIR}/quarantine"
  mkdir -p "${qdir}"
  if [[ -f "${HADRON_FILE}" ]]; then
    mv -f "${HADRON_FILE}" "${qdir}/$(basename "${HADRON_FILE}").${why}.${stamp}" || true
    log "[quarantine] moved bad hadron file -> ${qdir}/$(basename "${HADRON_FILE}").${why}.${stamp}"
  fi
}

read_sigma_from_hadron_strict(){
  # Echo: "sigmaGen sigmaErr" and return 0 on success; return 1 on failure.
  [[ -s "${HADRON_FILE}" ]] || return 1
  python3 - <<'PY' "${HADRON_FILE}"
import sys, re
p = sys.argv[1]

def scan_text(txt):
    sig = None
    err = None
    for line in txt.splitlines():
        if 'sigmaGen' not in line:
            continue
        m = re.search(r'\bsigmaGen\b\s*=?\s*([-+0-9.eE]+)', line)
        m2 = re.search(r'\bsigmaErr\b\s*=?\s*([-+0-9.eE]+)', line)
        if m and m2:
            sig = m.group(1)
            err = m2.group(1)
    return sig, err

try:
    with open(p, 'rb') as fh:
        head = fh.read(1024*1024).decode('utf-8', errors='ignore')
        fh.seek(0, 2)
        sz = fh.tell()
        back = min(sz, 2*1024*1024)
        fh.seek(sz - back)
        tail = fh.read(back).decode('utf-8', errors='ignore')
except Exception:
    sys.exit(1)

sig, err = scan_text(head)
if sig is None or err is None:
    sig2, err2 = scan_text(tail)
    sig = sig or sig2
    err = err or err2

if sig is None or err is None:
    sys.exit(1)

print(f"{sig} {err}")
PY
}


sigma_pair_is_positive(){
  # Return 0 only if sigmaGen and sigmaErr are both finite numeric values > 0.
  local xs="$1" xe="$2"
  [[ -n "${xs}" && -n "${xe}" ]] || return 1
  python3 - <<'PY' "${xs}" "${xe}"
import math, sys
try:
    xs = float(sys.argv[1])
    xe = float(sys.argv[2])
except Exception:
    raise SystemExit(1)
raise SystemExit(0 if math.isfinite(xs) and math.isfinite(xe) and xs > 0.0 and xe > 0.0 else 1)
PY
}

# -------------------- EVENT COMPLETENESS (worker-side; enables fast manager) --------------------
# Policy:
#   - We only mark a task OK in the meta file if events_written == NUM_EVENTS.
#   - If incomplete: quarantine hadron file and exit nonzero so the manager can resubmit quickly using meta only.
BASE=""
LASTID=""
EVENTS_WRITTEN=0

if [[ ! -s "${HADRON_FILE}" ]]; then
  log "[out] FATAL: hadron file missing: ${HADRON_FILE}"
  write_task_meta "incomplete" "0" "" "" "" "" "hadron file missing" 2
  exit 2
fi

BASE="$(infer_event_index_base "${HADRON_FILE}")"
LASTID="$(events_last_id "${HADRON_FILE}")"

if [[ -z "${LASTID}" ]]; then
  log "[out] FATAL: could not find last_event_id in ${HADRON_FILE}"
  write_task_meta "incomplete" "0" "" "${BASE}" "" "" "missing last_event_id" 3
  quarantine_hadron "missing_last_event_id"
  exit 3
fi

EVENTS_WRITTEN=$(( LASTID - BASE + 1 ))
(( EVENTS_WRITTEN < 0 )) && EVENTS_WRITTEN=0
log "[out] event_index_base=${BASE} last_event_id=${LASTID} -> events_written=${EVENTS_WRITTEN} (target=${NUM_EVENTS})"

if (( EVENTS_WRITTEN != NUM_EVENTS )); then
  log "[out] FATAL: incomplete events (events_written=${EVENTS_WRITTEN} != target ${NUM_EVENTS})"
  write_task_meta "incomplete" "${EVENTS_WRITTEN}" "${LASTID}" "${BASE}" "" "" "incomplete events" 3
  quarantine_hadron "incomplete_events_${EVENTS_WRITTEN}_of_${NUM_EVENTS}"
  exit 3
fi
# --------------------------------------------------------------------

SIG_LINE=""
if SIG_LINE="$(read_sigma_from_hadron_strict)"; then
  XS="$(awk '{print $1}' <<< "${SIG_LINE}")"
  XERR="$(awk '{print $2}' <<< "${SIG_LINE}")"
  log "[xsec] source=hadron  file=${HADRON_FILE}"
  log "[xsec] sigmaGen=${XS} mb  sigmaErr=${XERR} mb"
  if sigma_pair_is_positive "${XS}" "${XERR}"; then
    write_task_meta "ok" "${EVENTS_WRITTEN}" "${LASTID}" "${BASE}" "${XS}" "${XERR}" "ok" 0
  else
    log "[xsec] FATAL: invalid sigmaGen/sigmaErr (must both be finite and > 0): sigmaGen=${XS} sigmaErr=${XERR}"
    write_task_meta "incomplete" "${EVENTS_WRITTEN}" "${LASTID}" "${BASE}" "${XS}" "${XERR}" "sigmaGen/sigmaErr invalid or nonpositive" 2
    append_sigma_failure "sigmaGen/sigmaErr invalid or nonpositive in hadron file"
    quarantine_hadron "sigma_nonpositive"
    exit 2
  fi
else
  log "[xsec] FATAL: could not read sigmaGen/sigmaErr from hadron file: ${HADRON_FILE}"
  write_task_meta "incomplete" "${EVENTS_WRITTEN}" "${LASTID}" "${BASE}" "" "" "sigmaGen/sigmaErr missing or unreadable" 2
  append_sigma_failure "sigmaGen/sigmaErr missing or unreadable in hadron file"
  quarantine_hadron "sigma_missing"
  exit 2
fi

if [[ "${WRITE_SIM_EXTRA_FILES}" -eq 1 ]]; then
  XSFILE="${DIR_LOG_SIM}/xsec_${PT_L}_${PT_H}_${TASK}.txt"
  WTFILE="${DIR_LOG_SIM}/weight_${PT_L}_${PT_H}_${TASK}.txt"
  XERRFILE="${DIR_LOG_SIM}/xsecerr_${PT_L}_${PT_H}_${TASK}.txt"

  printf "%s\n" "${XS}" > "${XSFILE}"
  printf "%s\n" "${XERR}" > "${XERRFILE}"

  # [v4.5 FIX #23] WARNING: This per-task weight uses NJ (= NUM_JOBS = total expected tasks for this slice)
  # as the denominator. If some tasks failed, the per-event weight will be too small.
  # The AUTHORITATIVE weight source is the per-slice sim_manifest.json written by submit_sliced_sim.sh.
  log "[xsec] WARNING(#23): per-task weight uses NJ=${NJ} (expected total). See sim_manifest.json for correct weight."
  awk -v xs="${XS}" -v ne="${NUM_EVENTS}" -v nj="${NJ}" 'BEGIN{printf "%.12e\n", xs/(ne*nj)}' > "${WTFILE}"
  log "[xsec] nominal_weight=$(cat "${WTFILE}")  (denominator=NUM_EVENTS*NUM_JOBS=${NUM_EVENTS}*${NJ})"
else
  # Meta-file writing disabled (recommended). We already validated sigmaGen/sigmaErr above; just keep a debug log.
  log "[xsec] (no files) validated sigmaGen/sigmaErr in hadron header"
fi
# --------------------------------------------------------------------
# --------------------------------------------------------------------

if [[ "${KEEP_TEMP_XML:-0}" -eq 0 ]]; then
  log "[cleanup] KEEP_TEMP_XML=0, not copying staged XML to shared storage"
else
  cp -f "${XML_OUT}" "${XML_OUT_SHARED}"
  log "[cleanup] copied staged XML -> ${XML_OUT_SHARED}"
fi
rm -f -- "${HADRON_TMP_INSTALL}" 2>/dev/null || true
if [[ -n "${TASK_TMP_DIR:-}" && -d "${TASK_TMP_DIR}" ]]; then
  rm -rf -- "${TASK_TMP_DIR}"
  log "[cleanup] removed task tmp dir ${TASK_TMP_DIR}"
fi





