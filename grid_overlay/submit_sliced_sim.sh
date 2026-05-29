#!/usr/bin/env bash
# submit_sliced_sim.sh v8.3
# CHANGELOG
# v8.3 (realistic pp PythiaIsrMUSIC simulation-manager compatibility):
#   • DOC/COMPAT: Supports jetscape.ini v6.0 RealisticPPWorkflow=1 and submit_jetscape_sliced.slurm v5.8 without changing analysis/merge contracts.
#   • KEEP: Existing throttled manager, watchdog, meta recovery, seed report, and Slurm job cap behavior are preserved.
#   • SAFETY: First grid smoke-test defaults come from jetscape.ini: NUM_EVENTS=1, JOBS=(25), Multiplier=1, MultiSimEnabled=0.
# v8.2 (single-brick placeholder rendering for MultiSimEnabled=0):
#   • FIX: If MultiSimEnabled=0 and the selected XML template still contains BRICK_LENGTH/QHAT0 placeholders,
#     render one concrete single-run brick XML using SingleBrickLength and SingleQhat0 before any manager/worker submission.
#   • NEW: Write a small single-run override ini under $HOME/xscape_runs/<RUN_TAG>/single_brick_config/sim/ and switch INI_PATH to it,
#     so the existing manager/worker chain sees a resolved XML_TEMPLATE without changing the multisim path.
# v8.1 (custom ini-path support for wrapper-driven multisim):
#   • NEW: Honor INI_PATH / JETSCAPE_INI_PATH so wrapper-generated per-variant ini files can drive the existing single-run SIM manager.
#   • FIX: Manager self-submit now guesses RUN_TAG/log paths from the resolved ini path instead of always hardwiring ./jetscape.ini.
#   • FIX: Export INI_PATH through manager self-submit so downstream worker submissions inherit the same variant config cleanly.
# v8.0 (remove fake ResumeMode flag; keep real rerun behavior):
#   • FIX: Remove the dead RESUME_MODE variable and its misleading ResumeMode log line.
#     Rerun/resume behavior is still preserved exactly as before through the real per-task checks that skip completed outputs,
#     recover good hadron files with missing meta, and resubmit only unfinished/incomplete tasks.
#   • LOG: Replace the fake mode flag with an honest submit log that reports whether existing per-task meta was detected for this batch,
#     without implying a separate resume-only control-flow branch.
#
# v7.9 (manager-only seeds_seen finalization):
#   • CHANGE: Remove the temporary ${DIR_FINAL}/seeds_seen_current_launch.csv path entirely.
#     The SIM manager now writes only the final canonical ${DIR_FINAL}/seeds_seen.csv after the queue drains.
#   • CLEANUP: Stop exporting/resetting any live seed CSV for workers; workers already write authoritative per-attempt
#     ${SLICE_DIR}/seed_launches/job<TASK>.attempt<N>.json records, which this manager rebuilds into seeds_seen.csv.
#   • CLEANUP: Remove stale finalize/live-log fallback code and update logging/comments to reflect manager-only seeds_seen writing.
#
# v7.8 (watchdog drain + safer resubmit recovery):
#   • FIX: When the sim queue reaches zero, the manager now forces a final watchdog pass and keeps looping until no tracked task still needs grace handling or deferred resubmission.
#     This fixes the real last-job bug where WATCH_NEED_RESUB could be left pending and the manager would exit before auto-resubmitting the final failed task.
#   • FIX: Finished-task grace now computes the meta path from the explicit slice/task arguments instead of uninitialized watch state, so first-seen resume checks cannot read the wrong slice meta path.
#   • FIX: meta-ok-but-hadron-missing now gets the same grace window as other finished-task races instead of being resubmitted immediately.
#   • FIX: If stale/bad meta exists but the hadron file is already valid, the manager now rebuilds canonical meta from the hadron and skips the task as DONE instead of quarantining/resubmitting good output.
#   • FIX: Add a final manager-side meta recovery sweep before reports/manifests so good hadron files are not misreported as missing/incomplete just because meta lagged or was malformed.
#   • SAFETY: Runtime-only stuck-job killing is now opt-in through SimWatchdogAllowRuntimeOnlyKill=1. By default old RUNNING jobs are logged but not scancelled solely for age, eliminating false resubmits of legitimate long jobs.
#
# v7.7 (grace even when outputs are still settling):
#   • FIX: Finished-task grace now starts whenever a task leaves the queue incomplete, even if the hadron file is not yet visible on the shared filesystem.
#     This reduces false resubmits when Slurm state clears before NFS metadata and file visibility fully catch up.
#
# v7.6 (fix held-reason helper startup order):
#   • FIX: Move helper availability ahead of first use so manager startup no longer fails with `expand_held_reason_regex: command not found`.
#   • LOGIC: Held-job reason matching behavior is unchanged from v7.5; this is a Bash function-order hotfix only.
#
# v7.5 (robust held-reason matching across Slurm separators):
#   • FIX: Held-job watchdog now matches recoverable Slurm reasons case-insensitively and tolerates spaces/underscores/hyphens between words.
#     This lets a config like "launch failed requeued held" correctly catch WSU-style reasons such as launch_failed_requeued_held.
#   • LOGIC: Running-job stuck detection and finished-task meta grace are unchanged; only held-reason matching is hardened.
#
# v7.4 (launch-record seeds + real meta-grace + retire fake hadron-fallback knob):
#   • FIX: Rebuild ${DIR_FINAL}/seeds_seen.csv from worker-written ${SLICE_DIR}/seed_launches/job<TASK>.attempt<N>.json records,
#     so every launched seed survives crashes/requeues even when no quarantine file or final ok-meta exists yet.
#   • FIX: SimWatchdogMetaGraceSec now actually delays quarantine/resubmit for finished tasks when a hadron file exists but meta/output validation may still be settling on the filesystem.
#   • CLEANUP: Remove the dead SimWatchdogHadronFallback knob from parsing/logging/config comments so the manager no longer advertises fake behavior.
#
# v7.2 (authoritative manager-written seeds_seen.csv at end):
#   • CHANGE: Stop resetting the canonical ${DIR_FINAL}/seeds_seen.csv at manager start.
#     Workers now append only to ${DIR_FINAL}/seeds_seen_current_launch.csv during the active launch.
#   • NEW: After the queue drains, the manager writes the canonical ${DIR_FINAL}/seeds_seen.csv itself.
#     For deterministic runs (SEED_SALT_TIME=0), it rebuilds the full visible seed history across retries/reruns from the current slice folders and quarantine counts.
#     For salted runs (SEED_SALT_TIME=1), it appends the current-launch live log into the canonical file because exact historical salts cannot be reconstructed.
#   • LOG: Manager now reports both the live per-launch seed log and the canonical final seeds_seen.csv path/count.
#
# v7.1 (create final dir before seeds_seen reset):
#   • FIX: Create ${DIR_FINAL} before recreating ${DIR_FINAL}/seeds_seen.csv so a fresh RUN_TAG does not fail at manager start
#     just because the final directory has not been created yet.
#
# v7.0 (fresh seeds_seen reset per sim launch):
#   • CHANGE: Recreate ${DIR_FINAL}/seeds_seen.csv from scratch at every SIM-manager start with header
#       pthat_low,pthat_high,task,seed
#     so reruns do not preserve stale seed rows from older attempts in the same final directory.
#   • LOG: The SIM manager now reports seeds_seen.csv as reset instead of preserved.
# v6.9 (final-dir seeds_seen export):
#   • CHANGE: Rename misleading per-slice marker files from jid_sim_<PTL>_<PTH>.txt to subdir_sim_<PTL>_<PTH>.txt.
#     These files store the selected SIM subdirectory/batch name, not a Slurm job id.
#   • CHANGE: Initialize ${DIR_FINAL}/seeds_seen.csv at SIM-manager start with header
#       pthat_low,pthat_high,task,seed
#     so SIM workers append their actual launched seeds in the canonical final directory used by downstream checks.
#   • LOG: Resume/subdir-detection comments now consistently refer to subdir_sim_* markers.
#
# v6.7 (fix stray quote in manager read parsing):
#   • FIX: Remove accidental trailing `"` after two embedded Python command substitutions used by the final report and per-slice manifest summary parsing.
#     This stops raw_missing/raw_total and manifest summary lines from picking up a stray quote while leaving all sim logic unchanged.
#
# v6.6 (validated meta recovery for resume mode):
#   • FIX: In throttled resume mode, tasks with a hadron file but missing meta are no longer trusted blindly.
#     The manager now validates the hadron file (events + sigma), reconstructs a canonical per-task meta JSON,
#     and only then skips the task as DONE.
#   • FIX: If that hadron validation fails, the manager quarantines the stale hadron file and resubmits the task,
#     so reruns heal missing-meta outputs instead of falsely skipping them.
#   • LOG: Recovered tasks are tagged with note=manager_recovered_from_hadron for downstream traceability.
#
# v6.5 (use sbatch --parsable for all SIM submissions):
#   • FIX: Manager self-submit, legacy array submit, throttled single-task submit, and watchdog resubmits now all use `sbatch --parsable`.
#   • FIX: All SIM-side Slurm submissions now parse only the machine-readable numeric job ID and hard-fail if submission succeeds but the returned ID is not numeric.
#
# v6.4 (explicit config contract for manager submission):
#   • FIX: Multiplier must now be explicitly present in jetscape.ini, non-empty, numeric, and >= 1. The sim manager no longer assumes Multiplier=1.
#   • FIX: INCLUDE_XSEC_NORM_ERR must now be explicitly present in jetscape.ini and equal to 0 or 1, so sim/analysis/merge all enforce the same top-level config contract.
#
# v6.3 (strict pThat array-length guard):
#   • FIX: Hard-fail immediately after loading jetscape.ini if PT_LO, PT_HI, and JOBS arrays do not have identical lengths.
#     This prevents silent pTHat/job-count misalignment before any submission logic runs.
#
# v6.2 (manager self-submit logs moved under xscape_runs):
#   • CHANGE: Manager self-submit stdout/stderr now go under $HOME/xscape_runs/<RUN_TAG>/logs/manager/
#     so the sim side matches the analysis side and keeps run artifacts together.
#   • Fallback remains: if RUN_TAG cannot be parsed from jetscape.ini, keep repo-local ./logs/manager/.
# v6.1 (manifest sigma strictness aligned with worker/analyzer):
#   • FIX: Per-job meta aggregation for sim_manifest.json now requires BOTH sigmaGen_mb and sigmaErr_mb
#     to be finite and strictly > 0 before contributing to slice sigma aggregation.
#   • FIX: This removes the old manager-side allowance for sigmaErr_mb == 0 during manifest rebuild,
#     so manager, worker, and analyzer now enforce the same positive-sigma contract.
# v6.0 (strict sigma validation in manager fallback):
#   • FIX: output_is_ok() now requires BOTH sigmaGen and sigmaErr from the hadron file to be finite and > 0 before
#     accepting an output as DONE during meta-lag fallback. This aligns manager fallback with analyzer/worker strictness.
#   • NEW: sigma_pair_is_positive() helper centralizes the finite-and-positive check for manager-side hadron validation.
# v5.9 (manager fallback event-header parser hardened):
#   • FIX: Replace manager-side infer_event_index_base() with the same field-based first-header parser used by the worker.
#   • FIX: Replace manager-side events_last_id() with the worker's hardened logic: 20k tail, 200k tail, Python reverse-scan from EOF, then full scan.
#   • NO LOGIC CHANGE: output_is_ok(), watchdog, resubmission, and manifest behavior are unchanged; this only makes hadron fallback validation match worker robustness.
# v5.8 (fix spurious manager ExitCode=2 emails):
#   • FIX: Sanitize parsed totals (total/missing) from the final python report to digits only before any arithmetic/logging.
#     Prevents rare cases where a stray character (e.g. an accidental quote) causes bash arithmetic to error and Slurm reports ExitCode=2
#     even though all tasks completed.
# v5.7 (resume-safe reruns + clean meta parsing + held-pending auto-heal):
#   • FIX: require_python3() logs were contaminating meta_dump_fields() parsing when used in process substitution,
#     causing ms='[env] ...' and bogus quarantine filenames with slashes. meta_dump_fields() now uses a quiet python guard.
#   • FIX: Rerunning submit_sliced_sim.sh no longer quarantines/resubmits tasks just because meta is missing.
#     In resume mode (any meta exists for this RUN_TAG+SIM_BATCH_ID), tasks with an existing hadron file are treated as DONE
#     and the manager validates the hadron output directly before trusting that task as DONE.
#   • NEW: Optional held-pending watchdog: detects squeue reason matching SimWatchdogHeldReasonRegex (default:
#     "launch failed requeued held") for PENDING jobs; if SimWatchdogKillHeld=1 it scancels and resubmits them.
# v5.6 (quiet watchdog + suppress python BrokenPipe spam):
#   • FIX: Embedded python one-liners can receive SIGPIPE (e.g. when the manager is canceled),
#     which can spam the manager .err with repeated BrokenPipeError-at-shutdown messages.
#     We now set SIGPIPE to default inside each embedded python snippet so it exits quietly.
#   • LOG: Watchdog no longer prints per-task "done"/"resolve" lines for every OK job.
#     Instead it prints a compact per-poll summary (checked/done/redo/giveup/kill).
#     Non-OK tasks (kill/redo/giveup) still log full details.
# v5.5 (watchdog race fix: stop quarantining good outputs):
#   • FIX: In Multiplier>1 watchdog mode, a task could be marked incomplete if the meta file was not yet visible
#     when the job left squeue (filesystem latency). Manager would quarantine a *complete* hadron file as
#     jobX_final_state_hadrons.dat.watch_incomplete.<stamp> and resubmit endlessly.
#   • NEW: is_task_complete() now falls back to direct hadron validation (events + sigma) when meta is missing or non-ok.
#     If the hadron is complete, the task is accepted as DONE and is NOT quarantined/resubmitted.
#   • LOG: Emits a clear '[watch] done_output_ok' line when meta lags but output is valid.
#
# v5.4 (expected-vs-present manifest support for strict normalization):
#   • NEW: sim_manifest.json now includes expected-denominator fields:
#       events_expected = jobs_expected * num_events_target
#       weight_mb_per_event_expected = sigmaGen_mb / events_expected
#     Existing fields remain unchanged for backward compatibility:
#       events_total and weight_mb_per_event are still present-only (complete tasks) quantities.
#
# v5.3 (log retention + watch attempt numbering cleanup):
#   • LOG: Manager log file now includes timestamp to avoid overwriting logs on reruns with the same SIM_BATCH_ID.
#   • FIX: Watchlist adopt attempt counter now starts at 0 so the first resubmission logs as attempt=1 (no more attempt=0).
#
# v5.2 (watchlist healing for Multiplier>1):
#   • FIX: In Multiplier>1 mode, tasks skipped as active are now tracked in a watchlist and re-evaluated when they leave squeue.
#     If outputs/meta are incomplete, the manager can resubmit within the SAME run (no more "notice only at the end").
#   • NEW: Optional watchdog knobs from jetscape.ini: SimWatchdogEnable, SimWatchdogCheckSec, SimWatchdogStuckRunSec,
#     SimWatchdogKillStuck, SimWatchdogMaxResubmits. Stuck RUNNING jobs can be scancel'ed and resubmitted with full logging.
#   • LOG: Watchdog actions are logged with [watch] prefix for traceability.
#
# v5.1 (manager robustness fixes):
#   • FIX: Manager now attempts to load a python module if python3 is not in PATH (matches worker behavior).
#   • FIX: Manifest sigma aggregation now accepts sigmaErr_mb == 0 (still requires sigmaGen_mb > 0).
#   • FIX: Self-submit wrapper now runs the script via `bash` (no execute-bit required).
#
# v5.0 (fix per-slice SIM_BATCH_ID export; prevents batch folder mismatch):
#   • FIX: When a slice has a subdir_sim_<PTL>_<PTH>.txt batch id (BID) different from the global SIM_BATCH_ID,
#     the manager now exports SIM_BATCH_ID=${SIM_BID[i]} to the worker for that slice.
#     This guarantees the worker writes outputs under the same ${BID} folder that the manager (and analysis) expects.
#   • LOG: If a slice BID differs from the global SIM_BATCH_ID, the manager logs it explicitly.
#
# v4.9 (meta-based finalization; no big hadron scans on manager):
#   • NEW: The worker now writes per-task meta JSON files in ${SLICE_DIR}/meta/job${TASK}.json.
#   • PERF: Manager uses meta files to decide DONE vs redo and to build end-of-step reports + sim_manifest.json,
#     without scanning large hadron files after the queue drains.
#   • COMPAT: If meta is missing, tasks are treated as not started / incomplete (no legacy hadron scan by default).
#
# v4.8 (batch-manager self-submit; no long-running processes on warrior):
#   • NEW: If you run this on warrior (or anywhere outside a Slurm allocation), it auto-submits *itself* as a
#     lightweight manager batch job on qos=primary (24h, 1 CPU, 8G by default), then exits immediately.
#     This survives VPN/SSH disconnects and avoids running a long manager loop on the login node.
#   • Keeps old screen/nohup detach only as a fallback when sbatch is unavailable (e.g. laptop).

# v4.7 (sigma aggregation + python3 guard + traceability):
#   • NEW: sim_manifest.json now aggregates sigmaGen/sigmaErr across ALL present hadron files in the slice.
#     sigmaGen_mb = mean(sigmaGen_i); sigmaErr_mb = sqrt(sum(sigmaErr_i^2))/N_used (matches merge policy).
#   • NEW: writes sigma_sources.csv in each slice sim directory for traceability:
#       job_id,file,sigmaGen_mb,sigmaErr_mb,status
#     where status is ok|missing|parse_fail|nonpositive.
#   • NEW: PYTHON3 env override (default: python3) + hard fail early if python is unavailable.
#   • PERF: extract_sigma_from_hadron now tries cheap tail/head parsing first; falls back to small-byte python scan only if needed.
#
# v4.6 (manifest strict typing; no silent 0/null):
#   • FIX: sim_manifest.json writer no longer converts bad/empty numeric fields to 0/None silently.
#     Required integer fields must parse cleanly or manifest creation fails with a clear error.
#   • FIX: sigmaGen/sigmaErr extraction used a tail-only scan; now scans BOTH head and tail of the hadron file
#     (still from the hadron file only) to avoid spurious missing sigma in manifests.
#
# v4.5 (manifest refresh on reruns):
#   • FIX: Regenerate each slice sim_manifest.json at the end of the manager run.
#     If an existing manifest differs from the newly computed one, it is backed up and replaced.
#     This prevents stale weighting metadata after partial failures/reruns.
#
# v4.4 (manifested normalization + event-index bugfix):
#   • FIX: the old "events_last" returned the last *event id* (often NUM_EVENTS-1) but compared to NUM_EVENTS.
#     That falsely flagged COMPLETE jobs as incomplete and caused endless reruns producing the same "missing events".
#     Completeness now accepts last_event_id == NUM_EVENTS-1 OR == NUM_EVENTS.
#   • NEW: After the sim queue drains, write a per-slice sim_manifest.json inside each slice run folder.
#     This locks a single NJOBS_PRESENT + EVENTS_TOTAL + WEIGHT_MB_PER_EVENT for downstream analysis weighting.
#     That prevents the classic bias when you merge fewer task outputs than you *think* you generated.
#   • Mode unification: even when Multiplier=1 (legacy arrays), the manager now waits for those arrays to finish
#     and writes the same end-of-step reports + manifests (so analysis can be reproducible).
#
# v4.3 (sim completeness = events, not just bytes):
#   • DONE now requires the hadron file to contain NUM_EVENTS event headers (not just exist).
#   • Files with fewer events are marked INCOMPLETE_EVENTS and listed in missing_sim_outputs.csv.
#   • On rerun, incomplete hadron files are quarantined (not deleted) so the manager re-submits them.
#
# v4.2 (disconnect-safe manager):
#   • Auto-launches itself inside a detached screen session when run interactively (unless already in screen/tmux).
#   • Forces working directory to the script directory so jetscape.ini is found consistently.
#   • Falls back to nohup if screen is unavailable.
#
# v4.1 (resume-friendly + end-of-step reports + single email):
#   • SIM_BATCH_ID now defaults to stable value from jetscape.ini (SIM_BATCH_ID="batch0") and prefers existing subdir_sim_* if present.
#   • After queue drains, writes ${DIR_FINAL}/missing_sim_outputs.csv and ${DIR_FINAL}/sim_task_states.csv for early failure visibility.
#   • Removes per-task email spam (task Slurm file has no mail); optional ONE manager email via ManagerMail/MailUser.
#
# v4.0 (multiplier batches + 1000-job cap enforcement):
#   • Reads Multiplier/MaxActiveJobs/SubmitPollSec from jetscape.ini.
#   • If Multiplier>1: keeps at most MaxActiveJobs total jobs in qos=primary by submitting new sim jobs
#     only when earlier ones leave the queue (finished/failed/cancelled).
#   • Uses a stable SIM_BATCH_ID (timestamp by default) so all packs land in the same output folder per slice.
#   • Writes a manager log to ${DIR_LOG_SIM}/sim_manager_<SIM_BATCH_ID>.log for debugging.
# v3.3 (minor):
#   • Added banner logging + strict failure on missing config keys.
# v3.2 (minor):
#   • Writes subdir_sim_<L>_<H>.txt and submit logs in ${DIR_LOG_SIM}.
# v3.1:
#   • PTHat-sliced sbatch submission.
# v2.x:
#   • Original submission wrapper.

set -euo pipefail

# Python is used only for lightweight parsing / manifest writing on the manager node.
# Allow override if your environment uses a nonstandard name/path.
PYTHON3="${PYTHON3:-python3}"

parse_sbatch_jobid(){
  # Extract the numeric job id from `sbatch --parsable` output (e.g. "12345" or "12345;cluster").
  local raw="$1" jid=""
  raw="${raw//$'\r'/}"
  raw="${raw//$'\n'/}"
  jid="$(sed -nE 's/^([0-9]+)(;.*)?$/\1/p' <<< "${raw}" | head -n 1)"
  echo "${jid}"
}

require_numeric_sbatch_jobid(){
  local context="$1" raw="$2" jid
  jid="$(parse_sbatch_jobid "${raw}")"
  if ! [[ "${jid}" =~ ^[0-9]+$ ]]; then
    echo "[FATAL] Failed to parse numeric Slurm job ID from sbatch --parsable output for ${context}: ${raw}" >&2
    exit 1
  fi
  echo "${jid}"
}

require_python3(){
  # Ensure python3 exists (manager uses python only for lightweight manifest/report tasks).
  # Match the worker behavior: try PATH first, then attempt to load a python module.
  if command -v "${PYTHON3}" >/dev/null 2>&1; then
    log "[env] PYTHON3=${PYTHON3} ($(command -v "${PYTHON3}"))"
    return 0
  fi

  if command -v python3 >/dev/null 2>&1; then
    PYTHON3="python3"
    log "[env] python3=$(command -v python3)"
    return 0
  fi

  if command -v module >/dev/null 2>&1; then
    log "[env] python3 not found in PATH; attempting to load a python module..."
    local cand
    for cand in python/3.11 python/3.10 python/3.9 python/3.8 python; do
      module load "${cand}" >/dev/null 2>&1 || true
      if command -v python3 >/dev/null 2>&1; then
        PYTHON3="python3"
        log "[env] loaded ${cand}; python3=$(command -v python3)"
        return 0
      fi
      if command -v "${PYTHON3}" >/dev/null 2>&1; then
        log "[env] loaded ${cand}; PYTHON3=${PYTHON3} ($(command -v "${PYTHON3}"))"
        return 0
      fi
    done
    { module -t avail python 2>&1 | head -n 25 | sed 's/^/[module-avail] /'; } || true
  fi

  die "python3 not found (PYTHON3=${PYTHON3}). Load a python module or set PYTHON3=/path/to/python3."
}

require_python3_quiet(){
  # Like require_python3, but never prints log lines to stdout (important when called inside $(...) or < <(...)).
  # Suppresses stdout so meta_dump_fields and other parsers don't ingest '[env] ...' into their data fields.
  require_python3 >/dev/null
}



# --- manager launcher (compute-node batch job) ---
# Running this manager inside an interactive salloc allocation is fragile: if your SSH/VPN drops,
# Slurm cancels the allocation and kills the manager, so no more jobs get submitted.
#
# Fix: if we're NOT already inside a Slurm job allocation, auto-submit THIS script as a lightweight
# "manager" batch job on qos=primary, then exit immediately (so nothing long-lived runs on warrior).
#
# Hidden flag (prevents recursion):
#   --_inside_manager

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"
INI_PATH="${INI_PATH:-${JETSCAPE_INI_PATH:-${SCRIPT_DIR}/jetscape.ini}}"
export INI_PATH

INSIDE_MANAGER=0
if [[ "${1:-}" == "--_inside_manager" ]]; then
  INSIDE_MANAGER=1
  shift || true
fi

if [[ -z "${SLURM_JOB_ID:-}" && "${INSIDE_MANAGER}" -eq 0 ]]; then
  if command -v sbatch >/dev/null 2>&1; then
    ts_compact="$(date +%Y%m%d_%H%M%S)"

    # Best-effort RUN_TAG for nicer job names and xscape_runs log placement (do not hard-fail if missing).
    RUN_TAG_GUESS="$(grep -E '^[[:space:]]*RUN_TAG=' "${INI_PATH}" 2>/dev/null       | head -n 1       | sed -E 's/^[^=]+=[[:space:]]*//; s/^"//; s/"$//'       || true)"
    if [[ -n "${RUN_TAG_GUESS}" ]]; then
      RUNS_BASE_GUESS="${HOME}/xscape_runs/${RUN_TAG_GUESS}"
      MANAGER_LOG_DIR="${RUNS_BASE_GUESS}/logs/manager"
    else
      RUN_TAG_GUESS="NA"
      MANAGER_LOG_DIR="${SCRIPT_DIR}/logs/manager"
    fi
    mkdir -p "${MANAGER_LOG_DIR}"

    jobname="xsim_mgr_${RUN_TAG_GUESS}"

    # Defaults match what you were manually doing with salloc/srun. Override via env if needed.
    MANAGER_ACCOUNT="${MANAGER_ACCOUNT:-wsu}"
    MANAGER_QOS="${MANAGER_QOS:-primary}"
    MANAGER_TIME="${MANAGER_TIME:-6:00:00}"
    MANAGER_MEM="${MANAGER_MEM:-1G}"
    MANAGER_CPUS="${MANAGER_CPUS:-1}"
    MANAGER_NODES="${MANAGER_NODES:-1}"
    MANAGER_NTASKS="${MANAGER_NTASKS:-1}"

    out="${MANAGER_LOG_DIR}/sim_manager_${ts_compact}_%j.out"
    err="${MANAGER_LOG_DIR}/sim_manager_${ts_compact}_%j.err"

    echo "[INFO] Not in a Slurm allocation. Submitting SIM manager as a batch job (survives disconnects)."
    echo "       account=${MANAGER_ACCOUNT} qos=${MANAGER_QOS} time=${MANAGER_TIME} mem=${MANAGER_MEM} cpus=${MANAGER_CPUS}"

    sbout="$(
      sbatch         --parsable         --account="${MANAGER_ACCOUNT}"         --qos="${MANAGER_QOS}"         --nodes="${MANAGER_NODES}"         --ntasks="${MANAGER_NTASKS}"         --cpus-per-task="${MANAGER_CPUS}"         --mem="${MANAGER_MEM}"         --time="${MANAGER_TIME}"         --job-name="${jobname}"         --output="${out}"         --error="${err}"         --export=ALL,INI_PATH="${INI_PATH}"         --wrap="cd \"${SCRIPT_DIR}\" && bash ./$(basename "$0") --_inside_manager"
    )" || { echo "[FATAL] sbatch failed while trying to launch the SIM manager."; exit 1; }

    jid="$(require_numeric_sbatch_jobid "SIM manager self-submit" "${sbout}")"

    echo "[INFO] SIM manager job submitted: ${jid}"
    echo "[INFO] Track: squeue -j ${jid}"
    echo "[INFO] Logs:  ${MANAGER_LOG_DIR}/sim_manager_${ts_compact}_${jid}.out  and  ${MANAGER_LOG_DIR}/sim_manager_${ts_compact}_${jid}.err"
    exit 0
  fi

  # Non-Slurm fallback (e.g. laptop): keep the old detach behavior.
  if [[ -z "${XSCAPE_NO_SCREEN:-}" && -z "${STY:-}" && -z "${TMUX:-}" && -t 1 ]]; then
    if command -v screen >/dev/null 2>&1; then
      sess="simmgr_${USER}_$(date +%Y%m%d_%H%M%S)"
      echo "[INFO] Launching sim manager in detached screen session: ${sess}"
      echo "       Attach later with: screen -r ${sess}"
      export XSCAPE_NO_SCREEN=1
      SELF="./$(basename "$0")"
      QDIR="$(printf %q "${SCRIPT_DIR}")"
      QCMD="$(printf " %q" "${SELF}" "$@")"
      screen -dmS "${sess}" bash -lc "cd ${QDIR} && export XSCAPE_NO_SCREEN=1; ${QCMD}"
      exit 0
    elif command -v nohup >/dev/null 2>&1; then
      echo "[INFO] 'screen' not found. Launching sim manager under nohup (survives disconnect)."
      echo "       Log: ${SCRIPT_DIR}/nohup_sim_manager.out"
      export XSCAPE_NO_SCREEN=1
      SELF="./$(basename "$0")"
      QDIR="$(printf %q "${SCRIPT_DIR}")"
      QCMD="$(printf " %q" "${SELF}" "$@")"
      nohup bash -lc "cd ${QDIR} && export XSCAPE_NO_SCREEN=1; ${QCMD}" > "${SCRIPT_DIR}/nohup_sim_manager.out" 2>&1 &
      disown || true
      exit 0
    fi
  fi
fi


[[ -f "${INI_PATH}" ]] || { echo "[FATAL] jetscape.ini not found: ${INI_PATH}" >&2; exit 1; }
# shellcheck disable=SC1090
source "${INI_PATH}"

render_single_brick_ini_if_needed(){
  local current_ini="$1" current_script_dir="$2"
  local xml_source="" render_root="" rendered_xml="" rendered_ini=""
  local single_len="${SingleBrickLength:-}" single_qhat="${SingleQhat0:-}"

  [[ "${MultiSimEnabled:-0}" == "0" ]] || return 0
  [[ -n "${XML_TEMPLATE:-}" ]] || return 0

  if [[ "${XML_TEMPLATE}" = /* ]]; then
    xml_source="${XML_TEMPLATE}"
  else
    xml_source="${current_script_dir}/config/${XML_TEMPLATE}"
  fi
  [[ -f "${xml_source}" ]] || return 0

  if ! grep -q '\*\*BRICK_LENGTH_PLACEHOLDER\*\*' "${xml_source}" && \
     ! grep -q '\*\*QHAT0_PLACEHOLDER\*\*' "${xml_source}"; then
    return 0
  fi

  [[ -n "${single_len}" ]] || { echo "[FATAL] SingleBrickLength is required when MultiSimEnabled=0 and XML_TEMPLATE contains BRICK_LENGTH placeholders." >&2; exit 1; }
  [[ -n "${single_qhat}" ]] || { echo "[FATAL] SingleQhat0 is required when MultiSimEnabled=0 and XML_TEMPLATE contains QHAT0 placeholders." >&2; exit 1; }
  [[ "${single_len}" =~ ^[+-]?[0-9]+([.][0-9]+)?$ ]] || { echo "[FATAL] SingleBrickLength must be numeric (got ${single_len})." >&2; exit 1; }
  [[ "${single_qhat}" =~ ^[+-]?[0-9]+([.][0-9]+)?$ ]] || { echo "[FATAL] SingleQhat0 must be numeric (got ${single_qhat})." >&2; exit 1; }
  [[ -n "${RUN_TAG:-}" ]] || { echo "[FATAL] RUN_TAG is required before rendering single-brick XML." >&2; exit 1; }

  render_root="${HOME}/xscape_runs/${RUN_TAG}/single_brick_config/sim"
  mkdir -p "${render_root}"
  rendered_xml="${render_root}/${RUN_TAG}_single_brick.xml"
  rendered_ini="${render_root}/${RUN_TAG}_single_brick.ini"

  sed -e "s|\*\*BRICK_LENGTH_PLACEHOLDER\*\*|${single_len}|g" \
      -e "s|\*\*QHAT0_PLACEHOLDER\*\*|${single_qhat}|g" \
      "${xml_source}" > "${rendered_xml}"

  cp -f "${current_ini}" "${rendered_ini}"
  cat >> "${rendered_ini}" <<EOF

# --- single-brick override generated by submit_sliced_sim.sh ---
MultiSimEnabled=0
XML_TEMPLATE="${rendered_xml}"
SingleBrickLength=${single_len}
SingleQhat0=${single_qhat}
EOF

  INI_PATH="${rendered_ini}"
  export INI_PATH
  export JETSCAPE_INI_PATH="${rendered_ini}"
  echo "[single-brick] Rendered ${rendered_xml} with SingleBrickLength=${single_len} SingleQhat0=${single_qhat}"
  echo "[single-brick] Switched INI_PATH to ${rendered_ini}"
}

render_single_brick_ini_if_needed "${INI_PATH}" "${SCRIPT_DIR}"

if [[ -z "${PT_LO+set}" || -z "${PT_HI+set}" || -z "${JOBS+set}" ]]; then
  echo "[FATAL] jetscape.ini must define PT_LO, PT_HI, and JOBS arrays before submission." >&2
  exit 1
fi
if (( ${#PT_LO[@]} != ${#PT_HI[@]} || ${#PT_LO[@]} != ${#JOBS[@]} )); then
  echo "[FATAL] jetscape.ini array length mismatch: PT_LO=${#PT_LO[@]} PT_HI=${#PT_HI[@]} JOBS=${#JOBS[@]}. These arrays must have identical lengths." >&2
  exit 1
fi

ts(){ date +"%F %T"; }
# MANAGER_LOG is defined later; keep a safe fallback early.
log(){ echo "[$(ts)] [submit] $*" | tee -a "${MANAGER_LOG:-/dev/null}"; }

die(){ echo "[$(ts)] [FATAL] $*" | tee -a "${MANAGER_LOG:-/dev/null}"; exit 1; }
events_last_id(){
  # Last event id found in the hadron file (expects '# Event <id>' lines).
  # PERF: Prefer tail windows; FALLBACK: robust reverse-scan to avoid false "incomplete" when the last
  #       event header sits above a small tail window (rare but real for very long final events).
  local f="$1"
  [[ -s "${f}" ]] || { echo ""; return 0; }

  local n=""

  # Fast path: small tail window
  n="$({ tail -n 20000 "${f}" 2>/dev/null | grep -E '^#\s*Event' | tail -n 1 | awk '{for(i=1;i<=NF;i++) if($i=="Event"){print $(i+1); exit}}' || true; })"
  [[ -n "${n}" ]] && { echo "${n}"; return 0; }

  # Fallback 1: larger tail window (still cheap)
  n="$({ tail -n 200000 "${f}" 2>/dev/null | grep -E '^#\s*Event' | tail -n 1 | awk '{for(i=1;i<=NF;i++) if($i=="Event"){print $(i+1); exit}}' || true; })"
  [[ -n "${n}" ]] && { echo "${n}"; return 0; }

  # Fallback 2: fast reverse-scan from EOF (reads minimal blocks until it finds the last '# Event <id>')
  # This avoids full-file reads on shared FS in the rare case the last event header is above the tail window.
  if command -v python3 >/dev/null 2>&1; then
    n="$(python3 - "${f}" <<'PY' 2>/dev/null || true
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
  n="$({ grep -E '^#\s*Event' "${f}" 2>/dev/null | tail -n 1 | awk '{for(i=1;i<=NF;i++) if($i=="Event"){print $(i+1); exit}}' || true; })"
  [[ -n "${n}" ]] && { echo "${n}"; return 0; }

  echo ""
}

is_complete_events(){
  # Complete if last_event_id is NUM_EVENTS-1 (0-indexed) OR NUM_EVENTS (1-indexed).
  local f="$1"
  [[ -s "${f}" ]] || { echo "0"; return 0; }
  local last
  last="$(events_last_id "${f}")"
  [[ -n "${last}" ]] || { echo "0"; return 0; }
  if [[ "${last}" -eq "$((NUM_EVENTS-1))" || "${last}" -eq "${NUM_EVENTS}" ]]; then
    echo "1"
  else
    echo "0"
  fi
}

infer_event_index_base(){
  # Determine whether event ids start at 0 or 1 by reading the FIRST event header.
  # JetScape may write either space-delimited (`# Event 1`) or tab-delimited (`#  Event 1`) headers.
  # We parse fields rather than relying on grep regex features that are not portable in ERE.
  local f="$1"
  [[ -s "${f}" ]] || { echo "0"; return 0; }

  local first_id=""
  first_id="$(head -n 5000 "${f}" 2>/dev/null | awk '$1=="#" && $2=="Event" {print $3; exit}')"
  if [[ "${first_id}" == "0" ]]; then
    echo "0"; return 0
  fi
  if [[ "${first_id}" == "1" ]]; then
    echo "1"; return 0
  fi

  # Fallback: if header format ever changes, default to 0 (historical behavior).
  echo "0"
}
event_count_est(){
  # Estimate number of events in file from last_event_id and inferred base.
  local f="$1"
  local base="$2"
  local last
  last="$(events_last_id "${f}")"
  [[ -n "${last}" ]] || { echo "0"; return 0; }
  local cnt=$(( last - base + 1 ))
  (( cnt < 0 )) && cnt=0
  echo "${cnt}"
}

quarantine_incomplete_hadron(){
  local f="$1" why="$2"
  local stamp; stamp="$(date +%s)"
  local qdir; qdir="$(dirname "${f}")/quarantine"
  mkdir -p "${qdir}"
  [[ -f "${f}" ]] && mv -f "${f}" "${qdir}/$(basename "${f}").${why}.${stamp}" || true
}

# -------------------- TASK META helpers --------------------
meta_dump_fields(){
  # Echo tab-separated:
  #   status events_written last_event_id event_index_base sigmaGen_mb sigmaErr_mb filesize_bytes hadron_file
  local meta="$1"
  [[ -s "${meta}" ]] || { echo ""; return 0; }
  require_python3_quiet
  "${PYTHON3}" - <<'PY' "${meta}"
import signal
signal.signal(signal.SIGPIPE, signal.SIG_DFL)
import json, sys
p = sys.argv[1]
try:
    with open(p, "r") as f:
        d = json.load(f)
except Exception:
    print("")
    raise SystemExit

def g(k):
    v = d.get(k, "")
    if v is None:
        return ""
    return str(v)

fields = [
    g("status"),
    g("events_written"),
    g("last_event_id"),
    g("event_index_base"),
    g("sigmaGen_mb"),
    g("sigmaErr_mb"),
    g("filesize_bytes"),
    g("hadron_file"),
]
print("\t".join(fields))
PY
}

meta_is_ok(){
  local meta="$1"
  [[ -s "${meta}" ]] || { echo "0"; return 0; }
  local s ew lid base sg se bytes hf
  IFS=$'\t' read -r s ew lid base sg se bytes hf < <(meta_dump_fields "${meta}" || true)
  [[ "${s}" == "ok" && "${ew}" == "${NUM_EVENTS}" ]] && echo "1" || echo "0"
}

recover_meta_from_hadron(){
  # Rebuild a canonical task meta JSON from a validated hadron file.
  # Args: meta_path hadron_path pthat_low pthat_high slice_index task_id batch_id
  local meta="$1" out="$2" ptl="$3" pth="$4" slice_idx="$5" task_id="$6" batch_id="$7"
  [[ -s "${out}" ]] || return 1

  local base last events_written sigline sig err bytes host now_utc tmp
  base="$(infer_event_index_base "${out}")"
  last="$(events_last_id "${out}")"
  [[ -n "${last}" ]] || return 1
  events_written="$(event_count_est "${out}" "${base}")"
  [[ -n "${events_written}" && "${events_written}" == "${NUM_EVENTS}" ]] || return 1

  sigline="$(extract_sigma_from_hadron "${out}" || true)"
  sig="$(awk '{print $1}' <<<"${sigline}" | xargs)"
  err="$(awk '{print $2}' <<<"${sigline}" | xargs)"
  sigma_pair_is_positive "${sig}" "${err}" || return 1

  bytes=$(stat -c %s "${out}" 2>/dev/null || echo 0)
  host="$(hostname)"
  now_utc="$(date -u +'%F %T')"
  tmp="${meta}.tmp.$$"

  mkdir -p "$(dirname "${meta}")"
  require_python3_quiet
  "${PYTHON3}" - <<'PY' \
    "${tmp}" "${meta}" \
    "${RUN_TAG}" "${ptl}" "${pth}" "${slice_idx}" "${task_id}" "${batch_id}" \
    "ok" "${events_written}" "${last}" "${base}" \
    "${NUM_EVENTS}" "${sig}" "${err}" "${bytes}" \
    "${out}" \
    "${host}" "${SLURM_JOB_ID:-}" "${SLURM_ARRAY_JOB_ID:-}" "${SLURM_ARRAY_TASK_ID:-}" \
    "${now_utc}" "${now_utc}" \
    "0" "manager_recovered_from_hadron"
import signal
signal.signal(signal.SIGPIPE, signal.SIG_DFL)
import json, os, sys
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
os.replace(tmp, out)
PY
}
# -----------------------------------------------------------


extract_sigma_from_hadron(){
  # Echo: "sigmaGen_mb sigmaErr_mb" (either can be blank).
  # Fast path: parse from the tail (JETSCAPE usually appends "# sigmaGen ... sigmaErr ..." at EOF).
  # Fallback: small-byte python scan of head+tail if tail/head parsing fails.
  local f="$1"
  [[ -s "${f}" ]] || { echo ""; return 0; }

  local line=""
  # Tail first (footer is typically at EOF)
  line="$(tail -n 200 "${f}" 2>/dev/null | grep -m1 -E 'sigmaGen' || true)"
  # If the footer isn't in the tail (rare), try the head
  if [[ -z "${line}" ]]; then
    line="$(head -n 200 "${f}" 2>/dev/null | grep -m1 -E 'sigmaGen' || true)"
  fi

  if [[ -n "${line}" ]]; then
    # Parse tokens robustly: allow either "sigmaGen 1.23" or "sigmaGen=1.23"
    local out
    out="$(awk '{
      sig=""; err="";
      for(i=1;i<=NF;i++){
        t=$i; gsub(/=/,"",t);
        if(t=="sigmaGen"){ sig=$(i+1); gsub(/=/,"",sig); }
        if(t=="sigmaErr"){ err=$(i+1); gsub(/=/,"",err); }
      }
      if(sig!="" || err!=""){ print sig, err; }
    }' <<<"${line}" | xargs)"
    if [[ -n "${out}" ]]; then
      echo "${out}"
      return 0
    fi
  fi

  # Slow fallback (still bounded I/O): scan small head+tail byte ranges for sigmaGen/sigmaErr.
require_python3_quiet
  "${PYTHON3}" - <<'PY' "${f}"
import signal
signal.signal(signal.SIGPIPE, signal.SIG_DFL)
import sys, re
p = sys.argv[1]

def scan(txt):
    sig = None
    err = None
    for line in txt.splitlines():
        if 'sigmaGen' not in line:
            continue
        m = re.search(r"\bsigmaGen\b\s*=?\s*([-+0-9.eE]+)", line)
        m2 = re.search(r"\bsigmaErr\b\s*=?\s*([-+0-9.eE]+)", line)
        if m and m2:
            sig = m.group(1)
            err = m2.group(1)
    return sig, err

try:
    with open(p, 'rb') as fh:
        head = fh.read(128*1024).decode('utf-8', errors='ignore')
        fh.seek(0, 2)
        sz = fh.tell()
        back = min(sz, 256*1024)
        fh.seek(max(0, sz - back))
        tail = fh.read(back).decode('utf-8', errors='ignore')
except Exception:
    print("")
    raise SystemExit

sig, err = scan(tail)
if sig is None or err is None:
    sig2, err2 = scan(head)
    sig = sig or sig2
    err = err or err2

if sig is None and err is None:
    print("")
else:
    print(f"{sig or ''} {err or ''}".strip())
PY
}


sigma_pair_is_positive(){
  # Return 0 only if sigmaGen and sigmaErr are both finite numeric values > 0.
  local xs="$1" xe="$2"
  [[ -n "${xs}" && -n "${xe}" ]] || return 1
  require_python3_quiet
  "${PYTHON3}" - <<'PY' "${xs}" "${xe}"
import math, signal, sys
signal.signal(signal.SIGPIPE, signal.SIG_DFL)
try:
    xs = float(sys.argv[1])
    xe = float(sys.argv[2])
except Exception:
    raise SystemExit(1)
raise SystemExit(0 if math.isfinite(xs) and math.isfinite(xe) and xs > 0.0 and xe > 0.0 else 1)
PY
}

write_slice_manifest(){
  local PT_L="$1" PT_H="$2" TMAX="$3" SLICE_DIR="$4"
  local META_DIR="${SLICE_DIR}/meta"
  local manifest="${SLICE_DIR}/sim_manifest.json"

  local SIG_SRC_CSV="${SLICE_DIR}/sigma_sources.csv"
  local manifest_tmp="${manifest}.tmp.$$"
  local sig_tmp="${SIG_SRC_CSV}.tmp.$$"

  log "[manifest ${PT_L}-${PT_H}] building from meta... slice_dir=${SLICE_DIR} expected_tasks=${TMAX}"

  if [[ ! -d "${META_DIR}" ]]; then
    log "[manifest ${PT_L}-${PT_H}] WARNING: meta dir missing (${META_DIR}) -> manifest not written"
    return 0
  fi

  require_python3_quiet
  # Python writes BOTH sigma_sources.csv and sim_manifest.json (tmp paths) and prints a small summary line.
  read -r base sigmaGen sigmaErr sigma_mode sig_used sig_skipped jobs_present jobs_complete jobs_missing jobs_incomplete events_total weight events_expected weight_expected <<EOF
$("${PYTHON3}" - <<'PY' \
  "${META_DIR}" "${TMAX}" "${NUM_EVENTS}" \
  "${manifest_tmp}" "${sig_tmp}" \
  "${RUN_TAG}" "${PT_L}" "${PT_H}" "$(ts)"
import signal
signal.signal(signal.SIGPIPE, signal.SIG_DFL)
import csv, json, math, os, sys

meta_dir, tmax_s, num_events_s, manifest_out, sig_out, run_tag, ptL_s, ptH_s, created_ts = sys.argv[1:]
tmax = int(tmax_s)
num_events = int(num_events_s)
ptL = int(ptL_s); ptH = int(ptH_s)

rows = []
jobs_present = 0
jobs_complete = 0
jobs_incomplete = 0
jobs_missing = 0
events_total = 0
bases = []

missing_ex = []
incomplete_ex = []

sigs = []
errs = []
sig_used = 0
sig_skipped = 0

def load_json(p):
    with open(p, "r") as f:
        return json.load(f)

for t in range(1, tmax+1):
    mp = os.path.join(meta_dir, f"job{t}.json")
    if not os.path.exists(mp) or os.path.getsize(mp) == 0:
        jobs_missing += 1
        if len(missing_ex) < 10:
            missing_ex.append(str(t))
        rows.append((t, f"job{t}.json", "", "", "", "missing_meta"))
        continue

    jobs_present += 1
    try:
        d = load_json(mp)
    except Exception:
        jobs_incomplete += 1
        if len(incomplete_ex) < 10:
            incomplete_ex.append(f"{t}:parse_fail")
        rows.append((t, f"job{t}.json", "", "", "", "parse_fail"))
        continue

    status = str(d.get("status", "")).strip()
    ew = d.get("events_written", "")
    lid = d.get("last_event_id", "")
    base = d.get("event_index_base", "")
    sg = d.get("sigmaGen_mb", "")
    se = d.get("sigmaErr_mb", "")

    # Determine completeness (strict: ok + ew==num_events)
    ok = (status == "ok" and str(ew) == str(num_events))
    if ok:
        jobs_complete += 1
        try:
            events_total += int(ew)
        except Exception:
            pass
        try:
            bases.append(int(base))
        except Exception:
            pass
        # sigma aggregation inputs
        try:
            sgf = float(sg); sef = float(se)
            if sgf > 0 and sef > 0:
                sigs.append(sgf); errs.append(sef)
                sig_used += 1
            else:
                sig_skipped += 1
        except Exception:
            sig_skipped += 1
    else:
        jobs_incomplete += 1
        if len(incomplete_ex) < 10:
            tag = status if status else "incomplete"
            incomplete_ex.append(f"{t}:{tag}")

    rows.append((t, f"job{t}.json", sg, se, ew, status if status else "incomplete"))

# sigma_sources.csv
with open(sig_out, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["job_id","meta_file","sigmaGen_mb","sigmaErr_mb","events_written","status"])
    for t, meta_file, sg, se, ew, st in rows:
        w.writerow([t, meta_file, sg, se, ew, st])

sigma_mode = "none"
sigmaGen = ""
sigmaErr = ""
if sigs:
    n = len(sigs)
    sigmaGen = sum(sigs)/n
    sigmaErr = math.sqrt(sum(e*e for e in errs))/n
    sigma_mode = "mean_quadrature_over_n"

# base consistency
base_val = 0
if bases:
    base_val = bases[0]
    if any(b != base_val for b in bases):
        # Hard fail: mixed base means inconsistent outputs
        raise SystemExit(f"ERROR: inconsistent event_index_base across ok tasks: {sorted(set(bases))}")

events_expected = tmax * num_events

weight = ""
weight_expected = ""
if sigmaGen != "" and events_total > 0:
    weight = sigmaGen / events_total
if sigmaGen != "" and events_expected > 0:
    weight_expected = sigmaGen / events_expected

obj = {
  "schema": "xscape.sim_manifest.v2",
  "created_at": created_ts,
  "run_tag": run_tag,
  "pthat_low": ptL,
  "pthat_high": ptH,
  "num_events_target": num_events,
  "jobs_expected": tmax,
  "jobs_present": jobs_present,
  "jobs_complete": jobs_complete,
  "jobs_missing": jobs_missing,
  "jobs_incomplete": jobs_incomplete,
  "events_total": events_total,
  "events_expected": events_expected,
  "event_index_base": base_val,
  "sigma_source_mode": sigma_mode,
  "sigma_sources_csv": os.path.basename(sig_out),
  "sigma_n_used": sig_used,
  "sigma_n_skipped": sig_skipped,
  "sigmaGen_mb": sigmaGen if sigmaGen != "" else None,
  "sigmaErr_mb": sigmaErr if sigmaErr != "" else None,
  "weight_mb_per_event": weight if weight != "" else None,
  "weight_mb_per_event_expected": weight_expected if weight_expected != "" else None,
  "missing_task_examples": missing_ex,
  "incomplete_task_examples": incomplete_ex,
}

with open(manifest_out, "w") as f:
    json.dump(obj, f, indent=2, sort_keys=True)

def fmt(x):
    if x == "":
        return ""
    if isinstance(x, float):
        return f"{x:.16g}"
    return str(x)

print(" ".join(map(fmt, [base_val, sigmaGen, sigmaErr, sigma_mode, sig_used, sig_skipped,
                        jobs_present, jobs_complete, jobs_missing, jobs_incomplete, events_total, weight, events_expected, weight_expected])))
PY
)
EOF

  log "[manifest ${PT_L}-${PT_H}] base=${base:-NA} sigmaGen_mb=${sigmaGen:-NA} sigmaErr_mb=${sigmaErr:-NA} sigma_mode=${sigma_mode:-NA} sigma_used=${sig_used:-0} sigma_skipped=${sig_skipped:-0} jobs_present=${jobs_present:-0} jobs_complete=${jobs_complete:-0} missing=${jobs_missing:-0} incomplete=${jobs_incomplete:-0} events_total=${events_total:-0} weight_mb_per_event=${weight:-NA} events_expected=${events_expected:-0} weight_mb_per_event_expected=${weight_expected:-NA}"

  # Install sigma_sources.csv (backup if changed)
  if [[ -s "${SIG_SRC_CSV}" ]]; then
    if cmp -s "${SIG_SRC_CSV}" "${sig_tmp}"; then
      rm -f "${sig_tmp}"
    else
      local sbak="${SIG_SRC_CSV}.bak_$(date +%Y%m%d_%H%M%S)"
      mv -f "${SIG_SRC_CSV}" "${sbak}"
      mv -f "${sig_tmp}" "${SIG_SRC_CSV}"
      log "[manifest ${PT_L}-${PT_H}] UPDATED -> ${SIG_SRC_CSV} (backup: ${sbak})"
    fi
  else
    mv -f "${sig_tmp}" "${SIG_SRC_CSV}"
    log "[manifest ${PT_L}-${PT_H}] wrote ${SIG_SRC_CSV}"
  fi

  # Install manifest (backup if changed)
  if [[ -s "${manifest}" ]]; then
    if cmp -s "${manifest}" "${manifest_tmp}"; then
      rm -f "${manifest_tmp}"
      log "[manifest ${PT_L}-${PT_H}] unchanged -> keeping existing ${manifest}"
    else
      local bak="${manifest}.bak_$(date +%Y%m%d_%H%M%S)"
      mv -f "${manifest}" "${bak}"
      mv -f "${manifest_tmp}" "${manifest}"
      log "[manifest ${PT_L}-${PT_H}] UPDATED -> ${manifest} (backup: ${bak})"
    fi
  else
    mv -f "${manifest_tmp}" "${manifest}"
    log "[manifest ${PT_L}-${PT_H}] wrote ${manifest}"
  fi
}


finalize_seeds_csv(){
  local slice_list="$1"
  local canonical_csv="$2"
  require_python3_quiet
  local summary
  summary="$(${PYTHON3} - <<'PY' "${slice_list}" "${canonical_csv}" "${BASE_SEED:-1}" "${SeedStrideSlice:-1000000}" "${SEED_SALT_TIME:-0}"
import csv
import glob
import json
import os
import sys
import tempfile

slice_list, canonical_csv, base_seed_s, stride_s, seed_salt_time_s = sys.argv[1:]
base_seed = int(base_seed_s)
stride = int(stride_s)
seed_salt_time = int(seed_salt_time_s)
retry_prime = 7919
seed_mod = 2000000000
header = ["pthat_low", "pthat_high", "task", "seed"]


def safe_rows_from_csv(path):
    rows = []
    if not os.path.exists(path) or os.path.getsize(path) <= 0:
        return rows
    with open(path, "r", newline="") as f:
        reader = csv.reader(f)
        first = True
        for row in reader:
            if not row:
                continue
            if first:
                first = False
                if [c.strip() for c in row] == header:
                    continue
            if len(row) < 4:
                continue
            ptl = row[0].strip()
            pth = row[1].strip()
            task = row[2].strip()
            seed = row[3].strip()
            if not (ptl and pth and task and seed):
                continue
            rows.append([ptl, pth, task, seed])
    return rows


def write_rows(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=os.path.basename(path) + ".", dir=os.path.dirname(path))
    os.close(fd)
    try:
        with open(tmp, "w", newline="") as f:
            writer = csv.writer(f, lineterminator="\n")
            writer.writerow(header)
            writer.writerows(rows)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def load_launch_record(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            rec = json.load(f)
        return {
            "task": int(rec["task"]),
            "attempt": int(rec["attempt"]),
            "seed": str(rec["seed"]),
        }
    except Exception:
        return None


launch_rows = []
launch_records_seen = 0
with open(slice_list, "r") as fl:
    for line in fl:
        line = line.strip()
        if not line:
            continue
        ptL, ptH, tmax_s, slice_dir = line.split("\t", 3)
        launch_dir = os.path.join(slice_dir, "seed_launches")
        if not os.path.isdir(launch_dir):
            continue
        for path in sorted(glob.glob(os.path.join(launch_dir, "job*.attempt*.json"))):
            rec = load_launch_record(path)
            if rec is None:
                continue
            launch_records_seen += 1
            launch_rows.append((int(ptL), int(ptH), rec["task"], rec["attempt"], [str(ptL), str(ptH), str(rec["task"]), rec["seed"]]))

if launch_rows:
    launch_rows.sort(key=lambda item: (item[0], item[1], item[2], item[3]))
    rows = [item[4] for item in launch_rows]
    write_rows(canonical_csv, rows)
    unique_tasks = len({(row[0], row[1], row[2]) for row in rows})
    print(f"mode=launch_records rows={len(rows)} tasks={unique_tasks} launch_records={launch_records_seen} salted={seed_salt_time}")
    sys.exit(0)

# Legacy fallback for older runs that do not yet have per-attempt launch records.
# Keep any existing canonical rows when SEED_SALT_TIME=1 because deterministic reconstruction is impossible.
if seed_salt_time == 1:
    rows = safe_rows_from_csv(canonical_csv)
    write_rows(canonical_csv, rows)
    print(f"mode=legacy_preserve rows={len(rows)} tasks=NA final_tasks=NA quarantined_attempts=NA launch_records=0 salted={seed_salt_time}")
    sys.exit(0)

rows = []
quarantined_attempts = 0
final_tasks = 0
with open(slice_list, "r") as fl:
    for slice_index, line in enumerate(fl):
        line = line.strip()
        if not line:
            continue
        ptL, ptH, tmax_s, slice_dir = line.split("\t", 3)
        tmax = int(tmax_s)
        meta_dir = os.path.join(slice_dir, "meta")
        qdir = os.path.join(slice_dir, "quarantine")
        for task in range(1, tmax + 1):
            qcount = len(glob.glob(os.path.join(qdir, f"job{task}_*"))) if os.path.isdir(qdir) else 0
            quarantined_attempts += qcount
            meta_path = os.path.join(meta_dir, f"job{task}.json")
            final_ok = False
            if os.path.exists(meta_path) and os.path.getsize(meta_path) > 0:
                try:
                    with open(meta_path, "r") as mf:
                        meta = json.load(mf)
                    final_ok = (str(meta.get("status", "")).strip() == "ok")
                except Exception:
                    final_ok = False
            attempts = qcount + (1 if final_ok else 0)
            if final_ok:
                final_tasks += 1
            for retry_offset in range(attempts):
                seed_raw = base_seed + slice_index * stride + task + retry_offset * retry_prime
                seed = (seed_raw % seed_mod) + 1
                rows.append([ptL, ptH, str(task), str(seed)])

write_rows(canonical_csv, rows)
print(f"mode=legacy_rebuild rows={len(rows)} tasks={len({(r[0], r[1], r[2]) for r in rows})} final_tasks={final_tasks} quarantined_attempts={quarantined_attempts} launch_records=0")
PY
)"
  log "[seed_csv] ${summary} -> ${canonical_csv}"
}


# ---- knobs (from jetscape.ini) ----
if [[ -z "${Multiplier+x}" && -z "${multiplier+x}" ]]; then
  die "jetscape.ini missing required key Multiplier (must be an integer >= 1). Refusing to assume a default."
fi
MULT="${Multiplier-${multiplier-}}"
if [[ -z "${MULT}" ]]; then
  die "jetscape.ini has empty Multiplier. Must be an integer >= 1."
fi
if [[ -z "${INCLUDE_XSEC_NORM_ERR+x}" ]]; then
  die "jetscape.ini missing required key INCLUDE_XSEC_NORM_ERR (must be 0 or 1). Refusing to assume a default."
fi
if [[ -z "${INCLUDE_XSEC_NORM_ERR}" ]]; then
  die "jetscape.ini has empty INCLUDE_XSEC_NORM_ERR. Must be 0 or 1."
fi
if ! [[ "${INCLUDE_XSEC_NORM_ERR}" =~ ^[01]$ ]]; then
  die "jetscape.ini has invalid INCLUDE_XSEC_NORM_ERR=${INCLUDE_XSEC_NORM_ERR}. Must be 0 or 1."
fi
MAX_ACTIVE="${MaxActiveJobs:-1000}"
POLL_SEC="${SubmitPollSec:-30}"
WRITE_SIM_LOGS="${WRITE_SIM_LOGS:-${WriteSimLogs:-1}}"
MANAGER_MAIL="${ManagerMail:-0}"
MAIL_USER="${MailUser:-}"

# Watchdog (Multiplier>1 manager watchlist)
WATCHDOG_ENABLE="${SimWatchdogEnable:-1}"
WATCHDOG_CHECK_SEC="${SimWatchdogCheckSec:-300}"
WATCHDOG_STUCK_RUN_SEC="${SimWatchdogStuckRunSec:-7200}"
WATCHDOG_KILL_STUCK="${SimWatchdogKillStuck:-1}"
WATCHDOG_ALLOW_RUNTIME_ONLY_KILL="${SimWatchdogAllowRuntimeOnlyKill:-0}"
WATCHDOG_MAX_RESUBMITS="${SimWatchdogMaxResubmits:-20}"

# Held-pending watchdog (optional): detects jobs stuck in PENDING with a known Slurm reason and heals them.
WATCHDOG_KILL_HELD="${SimWatchdogKillHeld:-0}"
WATCHDOG_HELD_REASON_REGEX="${SimWatchdogHeldReasonRegex:-launch failed requeued held}"
WATCHDOG_HELD_REASON_REGEX_EXPANDED="$(printf '%s' "${WATCHDOG_HELD_REASON_REGEX}" | sed -E 's/[[:space:]]+/[ _-]+/g')"

# Meta visibility grace (seconds): when outputs exist but meta may lag on filesystem, wait before declaring missing.
META_GRACE_SEC="${SimWatchdogMetaGraceSec:-120}"


# ---- watchlist state (Multiplier>1 manager watchlist; safe no-op when MULT==1) ----
declare -A WATCH_JOBID=()
declare -A WATCH_JOBNAME=()
declare -A WATCH_SLICEIDX=()
declare -A WATCH_PTL=()
declare -A WATCH_PTH=()
declare -A WATCH_TASK=()
declare -A WATCH_ATTEMPT=()
declare -A WATCH_KILLREQ=()
declare -A WATCH_NEED_RESUB=()
declare -A WATCH_LAST_REASON=()
declare -A WATCH_AWAIT_FINISH=()
declare -A WATCH_FINISH_FIRST_EPOCH=()
WATCH_LAST_POLL_EPOCH=0

# Basic sanity
[[ -n "${RUN_TAG:-}" ]] || die "RUN_TAG missing in jetscape.ini"
[[ -n "${DIR_SIM:-}" && -n "${DIR_LOG_SIM:-}" ]] || die "DIR_SIM/DIR_LOG_SIM missing in jetscape.ini"
[[ -n "${SLURM_SIM_SCRIPT:-}" ]] || die "SLURM_SIM_SCRIPT missing in jetscape.ini"

if ! [[ "${MULT}" =~ ^[0-9]+$ ]] || (( MULT < 1 )); then
  die "Multiplier must be an integer >= 1 (got '${MULT}')"
fi
if ! [[ "${MAX_ACTIVE}" =~ ^[0-9]+$ ]] || (( MAX_ACTIVE < 1 )); then
  die "MaxActiveJobs must be an integer >= 1 (got '${MAX_ACTIVE}')"
fi
if (( MAX_ACTIVE > 1000 )); then
  log "[WARN] MaxActiveJobs=${MAX_ACTIVE} > 1000. WSU primary QoS cap is 1000. Forcing to 1000."
  MAX_ACTIVE=1000
fi
if ! [[ "${POLL_SEC}" =~ ^[0-9]+$ ]] || (( POLL_SEC < 5 )); then
  log "[WARN] SubmitPollSec too small (${POLL_SEC}). Forcing to 10s."
  POLL_SEC=10
fi

# Watchdog sanity (optional knobs; defaults are safe)
if ! [[ "${WATCHDOG_ENABLE}" =~ ^[0-9]+$ ]]; then WATCHDOG_ENABLE=1; fi
if ! [[ "${WATCHDOG_CHECK_SEC}" =~ ^[0-9]+$ ]] || (( WATCHDOG_CHECK_SEC < 30 )); then WATCHDOG_CHECK_SEC=300; fi
if ! [[ "${WATCHDOG_STUCK_RUN_SEC}" =~ ^[0-9]+$ ]] || (( WATCHDOG_STUCK_RUN_SEC < 60 )); then WATCHDOG_STUCK_RUN_SEC=7200; fi
if ! [[ "${WATCHDOG_KILL_STUCK}" =~ ^[0-9]+$ ]]; then WATCHDOG_KILL_STUCK=1; fi
if ! [[ "${WATCHDOG_ALLOW_RUNTIME_ONLY_KILL}" =~ ^[0-9]+$ ]]; then WATCHDOG_ALLOW_RUNTIME_ONLY_KILL=0; fi
if ! [[ "${WATCHDOG_MAX_RESUBMITS}" =~ ^[0-9]+$ ]] || (( WATCHDOG_MAX_RESUBMITS < 1 )); then WATCHDOG_MAX_RESUBMITS=20; fi
if ! [[ "${META_GRACE_SEC}" =~ ^[0-9]+$ ]] || (( META_GRACE_SEC < 0 )); then META_GRACE_SEC=120; fi

mkdir -p "${DIR_LOG_SIM}"

# Prefer an existing batch id (subdir_sim_*) so rerunning the script resumes instead of starting a new folder.
SIM_BATCH_ID="${SIM_BATCH_ID:-}"
if [[ -z "${SIM_BATCH_ID}" ]]; then
  jf="$(ls -1 "${DIR_LOG_SIM}"/subdir_sim_*_*.txt 2>/dev/null | head -n1 || true)"
  if [[ -n "${jf}" && -f "${jf}" ]]; then
    SIM_BATCH_ID="$(cat "${jf}" 2>/dev/null || true)"
  fi
fi
SIM_BATCH_ID="${SIM_BATCH_ID:-batch0}"
MANAGER_LOG_TS="$(date +%Y%m%d_%H%M%S)"
MANAGER_LOG="${DIR_LOG_SIM}/sim_manager_${SIM_BATCH_ID}_${MANAGER_LOG_TS}.log"
: > "${MANAGER_LOG}"
# Convenience pointer to the most recent manager log for this SIM_BATCH_ID (does not overwrite the real logs).
ln -sf "${MANAGER_LOG}" "${DIR_LOG_SIM}/sim_manager_${SIM_BATCH_ID}_latest.log"

log "ENGINE=${ENGINE_NAME:-NA}  RUN_TAG=${RUN_TAG}"
log "Multiplier=${MULT}  MaxActiveJobs=${MAX_ACTIVE}  SubmitPollSec=${POLL_SEC}  INCLUDE_XSEC_NORM_ERR=${INCLUDE_XSEC_NORM_ERR}"
log "SimWatchdogEnable=${WATCHDOG_ENABLE}  SimWatchdogCheckSec=${WATCHDOG_CHECK_SEC}  SimWatchdogStuckRunSec=${WATCHDOG_STUCK_RUN_SEC}  SimWatchdogKillStuck=${WATCHDOG_KILL_STUCK}  SimWatchdogAllowRuntimeOnlyKill=${WATCHDOG_ALLOW_RUNTIME_ONLY_KILL}  SimWatchdogMaxResubmits=${WATCHDOG_MAX_RESUBMITS}"
log "SimWatchdogKillHeld=${WATCHDOG_KILL_HELD}  SimWatchdogHeldReasonRegex=${WATCHDOG_HELD_REASON_REGEX}  SimWatchdogHeldReasonRegexExpanded=${WATCHDOG_HELD_REASON_REGEX_EXPANDED}  SimWatchdogMetaGraceSec=${META_GRACE_SEC}"
log "NUM_EVENTS=${NUM_EVENTS}"
log "SIM_BATCH_ID=${SIM_BATCH_ID}"
log "SLURM_SIM_SCRIPT=${SLURM_SIM_SCRIPT}"

mkdir -p "${DIR_FINAL}"
SEEDS_CSV="${DIR_FINAL}/seeds_seen.csv"
export SEEDS_CSV
log "SEEDS_CSV=${SEEDS_CSV} (canonical manager-written file rebuilt from per-attempt seed launch records after queue drain)"

TOTAL_PER_PACK=0
for nj in "${JOBS[@]}"; do
  TOTAL_PER_PACK=$((TOTAL_PER_PACK + nj))
done
if (( TOTAL_PER_PACK > MAX_ACTIVE )); then
  die "sum(JOBS)=${TOTAL_PER_PACK} exceeds MaxActiveJobs=${MAX_ACTIVE}. Fix JOBS or MaxActiveJobs."
fi

# Prepare per-slice output folders and subdir markers
declare -a SIM_BID
for i in "${!PT_LO[@]}"; do
  PT_L="${PT_LO[$i]}"
  PT_H="${PT_HI[$i]}"
  SUBDIR_FILE="${DIR_LOG_SIM}/subdir_sim_${PT_L}_${PT_H}.txt"
  BID="${SIM_BATCH_ID}"
  if [[ -s "${SUBDIR_FILE}" ]]; then
    BID="$(cat "${SUBDIR_FILE}" 2>/dev/null || echo "${SIM_BATCH_ID}")"
  else
    echo "${BID}" > "${SUBDIR_FILE}"
  fi
  if [[ "${BID}" != "${SIM_BATCH_ID}" ]]; then
    log "NOTE: slice ${PT_L}-${PT_H} uses existing BID=${BID} (differs from global SIM_BATCH_ID=${SIM_BATCH_ID}); will export per-slice BID to workers."
  fi
  SIM_BID[$i]="${BID}"
  mkdir -p "${DIR_SIM}/${PT_L}-${PT_H}/${BID}"
done

# sbatch output/err routing
SBATCH_OUT_ARRAY=()
SBATCH_ERR_ARRAY=()
SBATCH_OUT_ONE=()
SBATCH_ERR_ONE=()
if [[ "${WRITE_SIM_LOGS}" -eq 1 ]]; then
  SBATCH_OUT_ARRAY=(--output="${DIR_LOG_SIM}/slurm-%A_%a.out")
  SBATCH_ERR_ARRAY=(--error="${DIR_LOG_SIM}/slurm-%A_%a.err")
  SBATCH_OUT_ONE=(--output="${DIR_LOG_SIM}/slurm-%A.out")
  SBATCH_ERR_ONE=(--error="${DIR_LOG_SIM}/slurm-%A.err")
else
  SBATCH_OUT_ARRAY=(--output=/dev/null)
  SBATCH_ERR_ARRAY=(--error=/dev/null)
  SBATCH_OUT_ONE=(--output=/dev/null)
  SBATCH_ERR_ONE=(--error=/dev/null)
fi

primary_job_count(){
  squeue -u "${USER}" -q primary -h 2>/dev/null | wc -l | awk '{print $1}'
}

refresh_active_names(){
  squeue -u "${USER}" -q primary -h -o "%j" 2>/dev/null || true
}

# Snapshot active jobs in qos=primary (jobid|jobname|state|runtime).
refresh_active_snapshot(){
  squeue -u "${USER}" -q primary -h -o "%A|%j|%T|%M|%r" 2>/dev/null || true
}

expand_held_reason_regex(){
  # Expand literal whitespace in the configured held-reason regex so one config can match
  # Slurm reason strings that use spaces, underscores, or hyphens between the same words.
  # Example: "launch failed requeued held" -> "launch[ _-]+failed[ _-]+requeued[ _-]+held"
  local rx="${1:-}"
  printf '%s' "${rx}" | sed -E 's/[[:space:]]+/[ _-]+/g'
}

held_reason_matches(){
  # Args: raw_reason configured_regex
  local rsn="${1:-}" rx="${2:-}" rx_expanded
  [[ -n "${rsn}" && -n "${rx}" ]] || return 1

  # First honor the regex exactly as configured.
  if printf '%s
' "${rsn}" | grep -Eiq -- "${rx}"; then
    return 0
  fi

  # Then try a separator-tolerant form so a simple word-based regex keeps working when
  # Slurm reports the same reason with spaces vs underscores vs hyphens.
  rx_expanded="$(expand_held_reason_regex "${rx}")"
  if [[ -n "${rx_expanded}" && "${rx_expanded}" != "${rx}" ]]; then
    if printf '%s
' "${rsn}" | grep -Eiq -- "${rx_expanded}"; then
      return 0
    fi
  fi

  return 1
}

# Convert squeue runtime strings to seconds. Accepts:
#   MM:SS, HH:MM:SS, or DD-HH:MM:SS
runtime_to_seconds(){
  local s="${1:-0:00}"
  local days=0 hh=0 mm=0 ss=0
  if [[ "${s}" == *-* ]]; then
    days="${s%%-*}"
    s="${s#*-}"
  fi
  IFS=: read -r a b c <<< "${s}"
  if [[ -n "${c:-}" ]]; then
    hh="${a}"; mm="${b}"; ss="${c}"
  else
    hh=0; mm="${a:-0}"; ss="${b:-0}"
  fi
  # shellcheck disable=SC2004
  echo $(( (days*24*3600) + (10#${hh}*3600) + (10#${mm}*60) + (10#${ss}) ))
}

watch_key(){
  local ptl="$1" pth="$2" tid="$3"
  echo "${ptl}_${pth}_${tid}"
}

watch_add(){
  # Args: slice_idx ptl pth tid jobname jobid reason
  local i="$1" ptl="$2" pth="$3" tid="$4" jname="$5" jid="$6" reason="${7:-submit}"
  local key; key="$(watch_key "${ptl}" "${pth}" "${tid}")"
  local a="${WATCH_ATTEMPT[${key}]:-0}"
  a=$((a+1))
  WATCH_ATTEMPT["${key}"]="${a}"
  WATCH_SLICEIDX["${key}"]="${i}"
  WATCH_PTL["${key}"]="${ptl}"
  WATCH_PTH["${key}"]="${pth}"
  WATCH_TASK["${key}"]="${tid}"
  WATCH_JOBNAME["${key}"]="${jname}"
  WATCH_JOBID["${key}"]="${jid}"
  WATCH_KILLREQ["${key}"]=0
  WATCH_NEED_RESUB["${key}"]=0
  WATCH_LAST_REASON["${key}"]="${reason}"
  watch_clear_finish_wait "${key}"
  log "[watch] track  ${ptl}-${pth} task=${tid}  attempt=${a}  jobid=${jid}  jobname=${jname}  reason=${reason}"
}

watch_ensure_active(){
  # Ensure an active task is tracked even if it was submitted earlier (e.g. from a previous manager loop).
  # Args: slice_idx ptl pth tid jobname jobid_from_squeue
  local i="$1" ptl="$2" pth="$3" tid="$4" jname="$5" jid_now="${6:-}"
  local key; key="$(watch_key "${ptl}" "${pth}" "${tid}")"
  if [[ -z "${WATCH_JOBID[${key}]:-}" && -z "${WATCH_NEED_RESUB[${key}]:-}" ]]; then
    # First time we see it.
    WATCH_ATTEMPT["${key}"]="${WATCH_ATTEMPT[${key}]:-0}"
    WATCH_SLICEIDX["${key}"]="${i}"
    WATCH_PTL["${key}"]="${ptl}"
    WATCH_PTH["${key}"]="${pth}"
    WATCH_TASK["${key}"]="${tid}"
    WATCH_JOBNAME["${key}"]="${jname}"
    WATCH_JOBID["${key}"]="${jid_now}"
    WATCH_KILLREQ["${key}"]=0
    WATCH_NEED_RESUB["${key}"]=0
    WATCH_LAST_REASON["${key}"]="active_detected"
    watch_clear_finish_wait "${key}"
    log "[watch] adopt  ${ptl}-${pth} task=${tid}  jobid=${jid_now:-NA}  jobname=${jname}"
  elif [[ -n "${jid_now}" && "${WATCH_JOBID[${key}]:-}" != "${jid_now}" ]]; then
    # Refresh jobid if we learned a more specific one.
    WATCH_JOBID["${key}"]="${jid_now}"
    watch_clear_finish_wait "${key}"
    log "[watch] refresh ${ptl}-${pth} task=${tid}  jobid=${jid_now}  jobname=${jname}"
  fi
}

watch_clear_finish_wait(){
  local key="$1"
  unset WATCH_AWAIT_FINISH["${key}"] WATCH_FINISH_FIRST_EPOCH["${key}"]
}

watch_mark_finished_wait(){
  # Args: slice_idx ptl pth tid jobname reason
  local i="$1" ptl="$2" pth="$3" tid="$4" jname="$5" reason="$6"
  local key; key="$(watch_key "${ptl}" "${pth}" "${tid}")"
  WATCH_SLICEIDX["${key}"]="${i}"
  WATCH_PTL["${key}"]="${ptl}"
  WATCH_PTH["${key}"]="${pth}"
  WATCH_TASK["${key}"]="${tid}"
  WATCH_JOBNAME["${key}"]="${jname}"
  WATCH_JOBID["${key}"]=""
  WATCH_KILLREQ["${key}"]=0
  WATCH_NEED_RESUB["${key}"]=0
  WATCH_LAST_REASON["${key}"]="${reason}"
  WATCH_ATTEMPT["${key}"]="${WATCH_ATTEMPT[${key}]:-0}"
  WATCH_AWAIT_FINISH["${key}"]=1
}

watch_should_defer_finished_task(){
  # Args: key slice_idx ptl pth tid reason out_path
  local key="$1" i="$2" ptl="$3" pth="$4" tid="$5" reason="$6" out="$7"
  if (( META_GRACE_SEC <= 0 )); then
    watch_clear_finish_wait "${key}"
    return 1
  fi
  local out_state="missing"
  [[ -s "${out}" ]] && out_state="present"
  local meta_path="${DIR_SIM}/${ptl}-${pth}/${SIM_BID[$i]}/meta/job${tid}.json"
  if [[ -s "${meta_path}" ]]; then
    out_state="${out_state},meta_present"
  else
    out_state="${out_state},meta_missing"
  fi
  local now first elapsed
  now="$(date +%s)"
  first="${WATCH_FINISH_FIRST_EPOCH[${key}]:-}"
  if [[ -z "${first}" ]]; then
    WATCH_FINISH_FIRST_EPOCH["${key}"]="${now}"
    WATCH_AWAIT_FINISH["${key}"]=1
    log "[watch] grace_start ${ptl}-${pth} task=${tid}  reason=${reason}  grace=${META_GRACE_SEC}s  out=${out_state}"
    return 0
  fi
  elapsed=$((now - first))
  if (( elapsed < META_GRACE_SEC )); then
    WATCH_AWAIT_FINISH["${key}"]=1
    return 0
  fi
  log "[watch] grace_expired ${ptl}-${pth} task=${tid}  reason=${reason}  waited=${elapsed}s"
  watch_clear_finish_wait "${key}"
  return 1
}

watch_has_tracked_tasks(){
  local key
  for key in "${!WATCH_PTL[@]}"; do
    return 0
  done
  return 1
}

watch_drop_key(){
  local key="$1"
  watch_clear_finish_wait "${key}"
  unset WATCH_JOBID["${key}"] WATCH_JOBNAME["${key}"] WATCH_SLICEIDX["${key}"] WATCH_PTL["${key}"] WATCH_PTH["${key}"] WATCH_TASK["${key}"] WATCH_KILLREQ["${key}"] WATCH_NEED_RESUB["${key}"] WATCH_LAST_REASON["${key}"] WATCH_ATTEMPT["${key}"]
}

output_is_ok(){
  # Return 0 if the hadron file itself proves completeness (independent of meta).
  # Conditions:
  #   • file exists and non-empty
  #   • events headers indicate completion (accepts 0- or 1-based ids)
  #   • sigmaGen AND sigmaErr are present, finite, and > 0
  local out="$1"
  [[ -s "${out}" ]] || return 1
  local ok
  ok="$(is_complete_events "${out}")"
  [[ "${ok}" == "1" ]] || return 1
  local sigline sig err
  sigline="$(extract_sigma_from_hadron "${out}" || true)"
  sig="$(awk '{print $1}' <<<"${sigline}" | xargs)"
  err="$(awk '{print $2}' <<<"${sigline}" | xargs)"
  sigma_pair_is_positive "${sig}" "${err}" || return 1
  return 0
}

is_task_complete(){
  # Args: meta_path out_path
  local meta="$1" out="$2"

  # Primary (preferred): meta says ok AND output exists.
  if [[ -s "${meta}" ]]; then
    local ms mew mlid mbase msg mse mbytes mhf
    IFS=$'\t' read -r ms mew mlid mbase msg mse mbytes mhf < <(meta_dump_fields "${meta}" || true)
    if [[ "${ms:-}" == "ok" && "${mew:-0}" == "${NUM_EVENTS}" && -s "${out}" ]]; then
      return 0
    fi
  fi

  # Fallback (race-safe): if the hadron file itself proves completeness, accept it as done.
  # This prevents watchdog from quarantining/resubmitting good outputs when meta lags on the filesystem.
  if output_is_ok "${out}"; then
    log "[watch] done_output_ok meta=${meta} out=${out}"
    return 0
  fi

  return 1
}


watch_submit_if_possible(){
  # Args: slice_idx ptl pth tid reason
  local i="$1" ptl="$2" pth="$3" tid="$4" reason="$5"
  local total_primary slots jid jobname key
  total_primary="$(primary_job_count)"
  slots=$((MAX_ACTIVE - total_primary))
  if (( slots <= 0 )); then
    key="$(watch_key "${ptl}" "${pth}" "${tid}")"
    WATCH_NEED_RESUB["${key}"]=1
    log "[watch] defer  ${ptl}-${pth} task=${tid}  reason=${reason} (queue full ${total_primary}/${MAX_ACTIVE})"
    return 1
  fi

  local SLICE_DIR="${DIR_SIM}/${ptl}-${pth}/${SIM_BID[$i]}"
  local TMAX="${TOTAL_TASK[$i]}"
  jobname="xsim_${RUN_TAG}_${ptl}_${pth}_${tid}"

  log "[watch] resub  ${ptl}-${pth} task=${tid}/${TMAX}  reason=${reason}"
  sbout=$(sbatch --parsable --qos=primary \
    --job-name="${jobname}" \
    --export=ALL,PT_LOW="${ptl}",PT_HIGH="${pth}",NUM_JOBS="${TMAX}",SLICE_INDEX="${i}",TASK_ID="${tid}",SIM_BATCH_ID="${SIM_BID[$i]}" \
    "${SBATCH_OUT_ONE[@]}" "${SBATCH_ERR_ONE[@]}" \
    "${SLURM_SIM_SCRIPT}")

  jid="$(require_numeric_sbatch_jobid "SIM watchdog resubmit ${ptl}-${pth} task=${tid}" "${sbout}")"
  echo "${jid},${jobname},${ptl},${pth},${tid}" >> "${DIR_LOG_SIM}/submitted_jobs_${SIM_BATCH_ID}.csv"
  watch_add "${i}" "${ptl}" "${pth}" "${tid}" "${jobname}" "${jid}" "${reason}"
  return 0
}

watch_poll_maybe(){
  local force_poll="${1:-0}"
  if (( MULT == 1 )); then
    return 0
  fi
  if ! [[ "${WATCHDOG_ENABLE}" =~ ^[0-9]+$ ]] || (( WATCHDOG_ENABLE == 0 )); then
    return 0
  fi

  local now; now="$(date +%s)"
  if (( force_poll == 0 )) && (( WATCH_LAST_POLL_EPOCH > 0 )) && (( now - WATCH_LAST_POLL_EPOCH < WATCHDOG_CHECK_SEC )); then
    return 0
  fi
  WATCH_LAST_POLL_EPOCH="${now}"

  # Build a snapshot map of active jobs (jobid -> state/runtime, and jobname -> max jobid).
  declare -A SQ_STATE=()
  declare -A SQ_RUNSEC=()
  declare -A SQ_REASON=()
  declare -A SQ_NAME2JID=()
  while IFS='|' read -r jid jname jstate jtime jreason; do
    [[ -z "${jid}" || -z "${jname}" ]] && continue
    SQ_STATE["${jid}"]="${jstate}"
    SQ_RUNSEC["${jid}"]="$(runtime_to_seconds "${jtime:-0:00}")"
    SQ_REASON["${jid}"]="${jreason:-}"
    # If multiple jobids share a name, keep the largest (most recent).
    if [[ -z "${SQ_NAME2JID[${jname}]:-}" ]] || (( jid > SQ_NAME2JID["${jname}"] )); then
      SQ_NAME2JID["${jname}"]="${jid}"
    fi
  done < <(refresh_active_snapshot)

  # Avoid log spam: summarize each watchdog poll and only print per-task lines for problems.
  local checked=0 done=0 redo=0 giveup=0 killed=0

  local key
  for key in "${!WATCH_PTL[@]}"; do
    local ptl="${WATCH_PTL[${key}]}"
    local pth="${WATCH_PTH[${key}]}"
    local tid="${WATCH_TASK[${key}]}"
    local i="${WATCH_SLICEIDX[${key}]}"
    local jname="${WATCH_JOBNAME[${key}]}"
    local jid="${WATCH_JOBID[${key}]:-}"
    local attempt="${WATCH_ATTEMPT[${key}]:-0}"
    local need="${WATCH_NEED_RESUB[${key}]:-0}"
    local await_finish="${WATCH_AWAIT_FINISH[${key}]:-0}"

    # If jobid unknown but we can resolve by name, refresh it.
    if [[ -z "${jid}" && -n "${jname}" && -n "${SQ_NAME2JID[${jname}]:-}" ]]; then
      jid="${SQ_NAME2JID[${jname}]}"
      WATCH_JOBID["${key}"]="${jid}"
    fi

    # If this task already finished but we are holding it inside the meta/output grace window, re-check it here.
    if (( await_finish == 1 )) && [[ -z "${jid}" ]]; then
      local SLICE_DIR="${DIR_SIM}/${ptl}-${pth}/${SIM_BID[$i]}"
      local meta="${SLICE_DIR}/meta/job${tid}.json"
      local out="${SLICE_DIR}/job${tid}_final_state_hadrons.dat"
      checked=$((checked+1))
      if is_task_complete "${meta}" "${out}"; then
        done=$((done+1))
        watch_drop_key "${key}"
        continue
      fi
      if watch_should_defer_finished_task "${key}" "${i}" "${ptl}" "${pth}" "${tid}" "${WATCH_LAST_REASON[${key}]:-await_finish}" "${out}"; then
        continue
      fi
      if (( attempt >= WATCHDOG_MAX_RESUBMITS )); then
        giveup=$((giveup+1))
        log "[watch] giveup ${ptl}-${pth} task=${tid}  attempt=${attempt}/${WATCHDOG_MAX_RESUBMITS}  reason=${WATCH_LAST_REASON[${key}]:-await_finish}"
        watch_drop_key "${key}"
        continue
      fi
      [[ -s "${out}" ]] && quarantine_incomplete_hadron "${out}" "watch_meta_grace_expired"
      WATCH_NEED_RESUB["${key}"]=1
      redo=$((redo+1))
      log "[watch] redo   ${ptl}-${pth} task=${tid}  reason=${WATCH_LAST_REASON[${key}]:-await_finish}  -> meta grace expired; marked need_resub"
      continue
    fi

    # If explicitly marked for resubmission and not currently active, try now.
    if (( need == 1 )) && [[ -z "${jid}" ]]; then
      if (( attempt >= WATCHDOG_MAX_RESUBMITS )); then
        log "[watch] giveup ${ptl}-${pth} task=${tid}  attempt=${attempt}/${WATCHDOG_MAX_RESUBMITS}  reason=need_resub"
        watch_drop_key "${key}"
        continue
      fi
      watch_submit_if_possible "${i}" "${ptl}" "${pth}" "${tid}" "need_resub" || true
      continue
    fi

    # If jobid is empty and not marked need_resub, nothing to do.
    [[ -n "${jid}" ]] || continue

    # Still in queue?
    if [[ -n "${SQ_STATE[${jid}]:-}" ]]; then
      local st="${SQ_STATE[${jid}]}"
      local runsec="${SQ_RUNSEC[${jid}]:-0}"


      # Held-pending watchdog: cancel jobs stuck in PENDING due to launch failures and mark for resubmission.
      if (( WATCHDOG_KILL_HELD == 1 )) && ([[ "${st}" == "PENDING" || "${st}" == "PD" ]]); then
        local rsn="${SQ_REASON[${jid}]:-}"
        if held_reason_matches "${rsn}" "${WATCHDOG_HELD_REASON_REGEX}"; then
          log "[watch] kill_held ${ptl}-${pth} task=${tid}  jobid=${jid}  reason=${rsn}  (scancel, will resubmit)"
          scancel "${jid}" 2>/dev/null || true
          WATCH_JOBID["${key}"]=""
          WATCH_NEED_RESUB["${key}"]=1
          killed=$((killed+1))
          continue
        fi
      fi

      # Stuck RUNNING watchdog.
      if [[ "${st}" == "RUNNING" || "${st}" == "R" ]]; then
        if (( WATCHDOG_KILL_STUCK == 1 )) && (( runsec >= WATCHDOG_STUCK_RUN_SEC )); then
          if (( WATCHDOG_ALLOW_RUNTIME_ONLY_KILL == 1 )); then
            if (( ${WATCH_KILLREQ[${key}]:-0} == 0 )); then
              WATCH_KILLREQ["${key}"]=1
              killed=$((killed+1))
              log "[watch] kill   ${ptl}-${pth} task=${tid}  jobid=${jid}  runsec=${runsec} >= ${WATCHDOG_STUCK_RUN_SEC}  mode=runtime_only  (scancel)"
              scancel "${jid}" 2>/dev/null || true
              # Wait for it to disappear; resub will happen on a later poll.
            fi
          elif (( ${WATCH_KILLREQ[${key}]:-0} == 0 )); then
            WATCH_KILLREQ["${key}"]=2
            log "[watch] old_running ${ptl}-${pth} task=${tid}  jobid=${jid}  runsec=${runsec} >= ${WATCHDOG_STUCK_RUN_SEC}  action=observe_only  note=SimWatchdogAllowRuntimeOnlyKill=0"
          fi
        fi
      fi
      continue
    fi

    # Not in squeue anymore => finished/failed/canceled. Evaluate outputs.
    local SLICE_DIR="${DIR_SIM}/${ptl}-${pth}/${SIM_BID[$i]}"
    local meta="${SLICE_DIR}/meta/job${tid}.json"
    local out="${SLICE_DIR}/job${tid}_final_state_hadrons.dat"

    checked=$((checked+1))
    if is_task_complete "${meta}" "${out}"; then
      done=$((done+1))
      watch_drop_key "${key}"
      continue
    fi

    # Incomplete. Give hadron/meta visibility a grace window before quarantining/resubmitting.
    if watch_should_defer_finished_task "${key}" "${i}" "${ptl}" "${pth}" "${tid}" "watch_finished_incomplete" "${out}"; then
      WATCH_JOBID["${key}"]=""
      WATCH_AWAIT_FINISH["${key}"]=1
      continue
    fi

    # Incomplete. Prepare resubmission.
    if (( attempt >= WATCHDOG_MAX_RESUBMITS )); then
      giveup=$((giveup+1))
      log "[watch] giveup ${ptl}-${pth} task=${tid}  attempt=${attempt}/${WATCHDOG_MAX_RESUBMITS}  meta=${meta}  out=${out}"
      watch_drop_key "${key}"
      continue
    fi

    # Quarantine any partial hadron to avoid analysis reading junk.
    [[ -s "${out}" ]] && quarantine_incomplete_hadron "${out}" "watch_incomplete"
    WATCH_JOBID["${key}"]=""  # clear old
    watch_clear_finish_wait "${key}"
    WATCH_NEED_RESUB["${key}"]=1
    redo=$((redo+1))
    log "[watch] redo   ${ptl}-${pth} task=${tid}  jobid=${jid}  -> marked need_resub"
  done

  if (( checked > 0 || killed > 0 )); then
    log "[watch] poll_summary checked=${checked} done=${done} redo=${redo} giveup=${giveup} kill=${killed}"
  fi
}


wait_for_sim_queue(){
  if (( MULT == 1 )); then
    local jidfile="${DIR_LOG_SIM}/submitted_arrays_${SIM_BATCH_ID}.txt"
    while true; do
      local left=0
      if [[ -s "${jidfile}" ]]; then
        left="$(squeue -u "${USER}" -q primary -h -o "%A" 2>/dev/null | grep -F -f "${jidfile}" | wc -l | awk '{print $1}')"
      else
        left="$(squeue -u "${USER}" -q primary -h -o "%j" 2>/dev/null | awk -v pfx="xsim_${RUN_TAG}_" '$0 ~ "^"pfx {c++} END{print c+0}')"
      fi
      if (( left == 0 )); then
        log "[wait] Simulation queue empty (Multiplier=1 arrays)."
        break
      fi
      log "[wait] Remaining sim arrays/jobs for this run: ${left}. Waiting ${POLL_SEC}s..."
      sleep "${POLL_SEC}"
    done
    return 0
  fi

  while true; do
    local nleft
    nleft="$(squeue -u "${USER}" -q primary -h -o "%j" 2>/dev/null | awk -v pfx="xsim_${RUN_TAG}_" '$0 ~ "^"pfx {c++} END{print c+0}')"
    if (( nleft == 0 )); then
      watch_poll_maybe 1
      if watch_has_tracked_tasks; then
        log "[wait] Queue count is zero but watchdog still has tracked tasks for RUN_TAG=${RUN_TAG}. Waiting ${POLL_SEC}s for final grace/resubmit handling..."
        sleep "${POLL_SEC}"
        continue
      fi
      log "[wait] Simulation queue empty for RUN_TAG=${RUN_TAG}."
      break
    fi
    log "[wait] Remaining sim jobs for this RUN_TAG: ${nleft}. Waiting ${POLL_SEC}s..."
    watch_poll_maybe
    sleep "${POLL_SEC}"
  done
}

# ---------------- submission ----------------
if (( MULT == 1 )); then
  log "Mode: legacy arrays (Multiplier=1). Submitting one array per pTHat slice (sum(JOBS)=${TOTAL_PER_PACK})."

  for i in "${!PT_LO[@]}"; do
    PT_L="${PT_LO[$i]}"; PT_H="${PT_HI[$i]}"; NJ="${JOBS[$i]}"
    log "Submitting slice ${PT_L}-${PT_H}  NJOBS=${NJ}"

    sbout=$(sbatch --parsable --qos=primary --array=1-"${NJ}" \
      --export=ALL,PT_LOW="${PT_L}",PT_HIGH="${PT_H}",NUM_JOBS="${NJ}",SLICE_INDEX="${i}",SIM_BATCH_ID="${SIM_BID[$i]}" \
      "${SBATCH_OUT_ARRAY[@]}" "${SBATCH_ERR_ARRAY[@]}" \
      "${SLURM_SIM_SCRIPT}")

    jid="$(require_numeric_sbatch_jobid "SIM legacy array submit ${PT_L}-${PT_H}" "${sbout}")"
    log "  -> submitted array jobid=${jid}"
    echo "${jid}" >> "${DIR_LOG_SIM}/submitted_arrays_${SIM_BATCH_ID}.txt"
  done

else
  log "Mode: throttled manager (Multiplier>1). Keeping <=${MAX_ACTIVE} jobs in qos=primary."

  declare -a NEXT_TASK TOTAL_TASK
  for i in "${!PT_LO[@]}"; do
    TOTAL_TASK[$i]=$(( JOBS[i] * MULT ))
    NEXT_TASK[$i]=1
  done

  have_remaining() {
    for i in "${!PT_LO[@]}"; do
      if (( NEXT_TASK[$i] <= TOTAL_TASK[$i] )); then
        return 0
      fi
    done
    return 1
  }


# Honest rerun context logging: rerun/resume is handled by the normal per-task skip/recover/resubmit checks below,
# not by a separate ResumeMode control-flow branch. We only report whether existing per-task meta was detected for this batch.
EXISTING_BATCH_META=0
if find "${DIR_SIM}" -maxdepth 4 -type f -path "*/${SIM_BATCH_ID}/meta/job*.json" -print -quit 2>/dev/null | grep -q .; then
  EXISTING_BATCH_META=1
fi
log "[submit] ExistingBatchMeta=${EXISTING_BATCH_META}  RerunBehavior=per_task_skip_recover_resubmit  MetaGraceSec=${META_GRACE_SEC}  KillHeld=${WATCHDOG_KILL_HELD}"

  submitted_total=0
  skipped_done=0
  skipped_active=0

  while have_remaining; do
    total_primary="$(primary_job_count)"
    slots=$((MAX_ACTIVE - total_primary))
    if (( slots <= 0 )); then
      log "Queue full: primary_jobs=${total_primary}/${MAX_ACTIVE}. Waiting ${POLL_SEC}s..."
      watch_poll_maybe
      sleep "${POLL_SEC}"
      continue
    fi

    declare -A ACTIVE=()
    declare -A NAME2JID=()
    while IFS='|' read -r jid name st tm reason; do
      [[ -z "${name}" ]] && continue
      ACTIVE["${name}"]=1
      # Keep largest jobid per jobname (handles rare duplicates safely).
      if [[ -n "${jid}" ]]; then
        if [[ -z "${NAME2JID[${name}]:-}" ]] || (( jid > NAME2JID["${name}"] )); then
          NAME2JID["${name}"]="${jid}"
        fi
      fi
    done < <(refresh_active_snapshot)

    did_any=0

    # Periodic watchdog check (resubmits incomplete finished tasks; kills stuck RUNNING jobs if enabled).
    watch_poll_maybe

    while (( slots > 0 )) && have_remaining; do
      round_submit=0

      for i in "${!PT_LO[@]}"; do
        (( slots <= 0 )) && break

        PT_L="${PT_LO[$i]}"; PT_H="${PT_HI[$i]}"
        T="${NEXT_TASK[$i]}"; TMAX="${TOTAL_TASK[$i]}"
        SLICE_DIR="${DIR_SIM}/${PT_L}-${PT_H}/${SIM_BID[$i]}"

        while (( T <= TMAX )); do
          out="${SLICE_DIR}/job${T}_final_state_hadrons.dat"
          meta="${SLICE_DIR}/meta/job${T}.json"
          jobname="xsim_${RUN_TAG}_${PT_L}_${PT_H}_${T}"
          if [[ -s "${meta}" ]]; then
            IFS=$'\t' read -r ms mew mlid mbase msg mse mbytes mhf < <(meta_dump_fields "${meta}" || true)
            if [[ "${ms}" == "ok" && "${mew}" == "${NUM_EVENTS}" && -s "${out}" ]]; then
              skipped_done=$((skipped_done + 1))
              watch_clear_finish_wait "$(watch_key "${PT_L}" "${PT_H}" "${T}")"
              log "skip(done-meta)  ${PT_L}-${PT_H}  task=${T}/${TMAX}  events_written=${mew:-NA}  last_event_id=${mlid:-NA}  bytes=${mbytes:-NA}"
              T=$((T + 1))
              NEXT_TASK[$i]="${T}"
              continue
            elif [[ "${ms}" == "ok" && "${mew}" == "${NUM_EVENTS}" && ! -s "${out}" ]]; then
              key="$(watch_key "${PT_L}" "${PT_H}" "${T}")"
              if watch_should_defer_finished_task "${key}" "${i}" "${PT_L}" "${PT_H}" "${T}" "meta_ok_missing_hadron" "${out}"; then
                watch_mark_finished_wait "${i}" "${PT_L}" "${PT_H}" "${T}" "${jobname}" "meta_ok_missing_hadron"
                T=$((T + 1))
                NEXT_TASK[$i]="${T}"
                continue
              fi
              log "redo(meta-ok-but-hadron-missing) ${PT_L}-${PT_H}  task=${T}/${TMAX} -> grace expired; will resubmit"
            fi
          fi

          # If the job is currently running/pending, DO NOT quarantine its outputs (it may be writing right now).
          if [[ -n "${ACTIVE[${jobname}]:-}" ]]; then
            skipped_active=$((skipped_active + 1))
            log "skip(active) ${PT_L}-${PT_H}  task=${T}/${TMAX}  jobname=${jobname}"
            # Watchlist: track this active task so we re-evaluate it when it leaves squeue.
            jid_active="${NAME2JID[${jobname}]:-}"
            watch_ensure_active "${i}" "${PT_L}" "${PT_H}" "${T}" "${jobname}" "${jid_active}"
            T=$((T + 1))
            NEXT_TASK[$i]="${T}"
            continue
          fi

          # Not active. If meta exists but isn't OK, give the hadron/meta pair a grace window before quarantine/resubmit.
          if [[ -s "${meta}" ]]; then
            IFS=$'	' read -r ms mew mlid mbase msg mse mbytes mhf < <(meta_dump_fields "${meta}" || true)
            if [[ -s "${out}" ]] && recover_meta_from_hadron "${meta}" "${out}" "${PT_L}" "${PT_H}" "${i}" "${T}" "${SIM_BID[$i]}"; then
              skipped_done=$((skipped_done + 1))
              watch_clear_finish_wait "$(watch_key "${PT_L}" "${PT_H}" "${T}")"
              log "skip(done-meta-recovered-from-hadron) ${PT_L}-${PT_H}  task=${T}/${TMAX}  note=manager_recovered_from_hadron"
              T=$((T + 1))
              NEXT_TASK[$i]="${T}"
              continue
            fi
            key="$(watch_key "${PT_L}" "${PT_H}" "${T}")"
            if watch_should_defer_finished_task "${key}" "${i}" "${PT_L}" "${PT_H}" "${T}" "meta_${ms:-bad}" "${out}"; then
              watch_mark_finished_wait "${i}" "${PT_L}" "${PT_H}" "${T}" "${jobname}" "meta_${ms:-bad}"
              T=$((T + 1))
              NEXT_TASK[$i]="${T}"
              continue
            fi
            log "redo(meta-${ms:-bad}) ${PT_L}-${PT_H}  task=${T}/${TMAX}  events_written=${mew:-NA}  last_event_id=${mlid:-NA} -> quarantine"
            [[ -s "${out}" ]] && quarantine_incomplete_hadron "${out}" "meta_${ms:-bad}"
          elif [[ -s "${out}" ]]; then
            # Output exists but meta is missing.
            # Best-effort recovery path: if the hadron file itself validates, rebuild canonical meta and skip as DONE.
            if recover_meta_from_hadron "${meta}" "${out}" "${PT_L}" "${PT_H}" "${i}" "${T}" "${SIM_BID[$i]}"; then
              skipped_done=$((skipped_done + 1))
              watch_clear_finish_wait "$(watch_key "${PT_L}" "${PT_H}" "${T}")"
              log "skip(done-hadron-recovered-meta) ${PT_L}-${PT_H}  task=${T}/${TMAX}  note=manager_recovered_from_hadron"
              T=$((T + 1))
              NEXT_TASK[$i]="${T}"
              continue
            fi

            # Validation failed. Give the output/meta pair a grace window before quarantining and rerunning.
            key="$(watch_key "${PT_L}" "${PT_H}" "${T}")"
            if watch_should_defer_finished_task "${key}" "${i}" "${PT_L}" "${PT_H}" "${T}" "missing_meta_invalid_hadron" "${out}"; then
              watch_mark_finished_wait "${i}" "${PT_L}" "${PT_H}" "${T}" "${jobname}" "missing_meta_invalid_hadron"
              T=$((T + 1))
              NEXT_TASK[$i]="${T}"
              continue
            fi

            quarantine_incomplete_hadron "${out}" "missing_meta_invalid_hadron"
            log "redo(no-meta-invalid-hadron) ${PT_L}-${PT_H}  task=${T}/${TMAX} -> quarantined invalid hadron and will resubmit"
          fi

          log "submit      ${PT_L}-${PT_H}  task=${T}/${TMAX}  slots_left=${slots}"
          sbout=$(sbatch --parsable --qos=primary \
            --job-name="${jobname}" \
            --export=ALL,PT_LOW="${PT_L}",PT_HIGH="${PT_H}",NUM_JOBS="${TMAX}",SLICE_INDEX="${i}",TASK_ID="${T}",SIM_BATCH_ID="${SIM_BID[$i]}" \
            "${SBATCH_OUT_ONE[@]}" "${SBATCH_ERR_ONE[@]}" \
            "${SLURM_SIM_SCRIPT}")

          jid="$(require_numeric_sbatch_jobid "SIM throttled submit ${PT_L}-${PT_H} task=${T}" "${sbout}")"
          echo "${jid},${jobname},${PT_L},${PT_H},${T}" >> "${DIR_LOG_SIM}/submitted_jobs_${SIM_BATCH_ID}.csv"
          watch_add "${i}" "${PT_L}" "${PT_H}" "${T}" "${jobname}" "${jid}" "submit"
          submitted_total=$((submitted_total + 1))

          T=$((T + 1))
          NEXT_TASK[$i]="${T}"
          slots=$((slots - 1))
          round_submit=1
          did_any=1
          break
        done
      done

      (( round_submit == 0 )) && break
    done

    if (( did_any == 0 )); then
      log "No new submissions possible right now (remaining tasks appear active). Waiting ${POLL_SEC}s..."
      watch_poll_maybe
      sleep "${POLL_SEC}"
    fi
  done

  log "All tasks submitted for Multiplier=${MULT}. submitted=${submitted_total}  skipped_done=${skipped_done}  skipped_active=${skipped_active}"
fi

log "Waiting for remaining sim jobs to leave the queue..."
wait_for_sim_queue

recover_all_sim_meta_before_reports(){
  local recovered=0 checked=0
  local i PT_L PT_H TMAX SLICE_DIR T meta out okflag
  for i in "${!PT_LO[@]}"; do
    PT_L="${PT_LO[$i]}"
    PT_H="${PT_HI[$i]}"
    TMAX=$(( JOBS[$i] * MULT ))
    SLICE_DIR="${DIR_SIM}/${PT_L}-${PT_H}/${SIM_BID[$i]}"
    for ((T=1; T<=TMAX; T++)); do
      meta="${SLICE_DIR}/meta/job${T}.json"
      out="${SLICE_DIR}/job${T}_final_state_hadrons.dat"
      [[ -s "${out}" ]] || continue
      checked=$((checked + 1))
      okflag="$(meta_is_ok "${meta}")"
      if [[ "${okflag}" == "1" ]]; then
        continue
      fi
      if recover_meta_from_hadron "${meta}" "${out}" "${PT_L}" "${PT_H}" "${i}" "${T}" "${SIM_BID[$i]}"; then
        recovered=$((recovered + 1))
        log "[final-meta] recovered ${PT_L}-${PT_H} task=${T}/${TMAX} from hadron before reports/manifests"
      fi
    done
  done
  log "[final-meta] checked_hadron_tasks=${checked} recovered=${recovered}"
}

recover_all_sim_meta_before_reports

# ---- end-of-step reports (meta-based; no hadron scans) ----
mkdir -p "${DIR_FINAL}"
MISS_SIM_CSV="${DIR_FINAL}/missing_sim_outputs.csv"
SIM_STATES_CSV="${DIR_FINAL}/sim_task_states.csv"

SLICE_LIST="${DIR_LOG_SIM}/slice_list_${SIM_BATCH_ID}.tsv"
: > "${SLICE_LIST}"
for i in "${!PT_LO[@]}"; do
  PT_L="${PT_LO[$i]}"; PT_H="${PT_HI[$i]}"
  TMAX=$(( JOBS[$i] * MULT ))
  SLICE_DIR="${DIR_SIM}/${PT_L}-${PT_H}/${SIM_BID[$i]}"
  printf "%s\t%s\t%s\t%s\n" "${PT_L}" "${PT_H}" "${TMAX}" "${SLICE_DIR}" >> "${SLICE_LIST}"
done

require_python3_quiet
read -r total missing <<EOF
$("${PYTHON3}" - <<'PY' "${SLICE_LIST}" "${MISS_SIM_CSV}" "${SIM_STATES_CSV}" "${NUM_EVENTS}"
import signal
signal.signal(signal.SIGPIPE, signal.SIG_DFL)
import json, os, sys

slice_list, miss_csv, states_csv, num_events_s = sys.argv[1:]
num_events = int(num_events_s)

def load_meta(p):
    with open(p, "r") as f:
        return json.load(f)

total = 0
missing = 0

with open(miss_csv, "w") as fmiss, open(states_csv, "w") as fstate:
    fmiss.write("pthat_low,pthat_high,task,what,file,last_event_id,bytes\n")
    fstate.write("pthat_low,pthat_high,task,status,file,last_event_id,bytes\n")

    with open(slice_list, "r") as fl:
        for line in fl:
            line = line.strip()
            if not line:
                continue
            ptL, ptH, tmax_s, slice_dir = line.split("\t", 3)
            tmax = int(tmax_s)
            for t in range(1, tmax+1):
                total += 1
                meta = os.path.join(slice_dir, "meta", f"job{t}.json")
                hadron_default = os.path.join(slice_dir, f"job{t}_final_state_hadrons.dat")

                if os.path.exists(meta) and os.path.getsize(meta) > 0:
                    try:
                        d = load_meta(meta)
                    except Exception:
                        status = "INCOMPLETE_META"
                        what = "meta_parse_fail"
                        filep = hadron_default
                        lid = "NA"
                        byt = "0"
                        fstate.write(f"{ptL},{ptH},{t},{status},{filep},{lid},{byt}\n")
                        fmiss.write(f"{ptL},{ptH},{t},{what},{filep},{lid},{byt}\n")
                        missing += 1
                        continue

                    st = str(d.get("status","")).strip()
                    ew = d.get("events_written","")
                    lid = d.get("last_event_id","NA")
                    byt = d.get("filesize_bytes", 0)
                    filep = d.get("hadron_file", hadron_default) or hadron_default

                    ok = (st == "ok" and str(ew) == str(num_events))
                    if ok:
                        status = "DONE"
                        fstate.write(f"{ptL},{ptH},{t},{status},{filep},{lid},{byt}\n")
                    else:
                        status = "INCOMPLETE_META"
                        what = f"meta_{st if st else 'incomplete'}"
                        fstate.write(f"{ptL},{ptH},{t},{status},{filep},{lid},{byt}\n")
                        fmiss.write(f"{ptL},{ptH},{t},{what},{filep},{lid},{byt}\n")
                        missing += 1
                else:
                    filep = hadron_default
                    status = "MISSING_META"
                    what = "missing_meta"
                    lid = "NA"
                    byt = "0"
                    fstate.write(f"{ptL},{ptH},{t},{status},{filep},{lid},{byt}\n")
                    fmiss.write(f"{ptL},{ptH},{t},{what},{filep},{lid},{byt}\n")
                    missing += 1

print(total, missing)
PY
)
EOF

# Sanitize: ensure total/missing are pure integers (avoid bash arithmetic errors if the parser output is polluted).
raw_total="${total:-}"
raw_missing="${missing:-}"
total="$(tr -cd '0-9' <<< "${raw_total}" || true)"
missing="$(tr -cd '0-9' <<< "${raw_missing}" || true)"
[[ -n "${total}" ]] || total="0"
[[ -n "${missing}" ]] || missing="0"
if [[ "${raw_total}" != "${total}" || "${raw_missing}" != "${missing}" ]]; then
  log "[warn] Sanitized report totals: raw_total='${raw_total}' raw_missing='${raw_missing}' -> total=${total} missing=${missing}"
fi

log "[report] sim expected=${total} missing=${missing} -> ${MISS_SIM_CSV} ; states=${SIM_STATES_CSV}"


# ---- per-slice sim manifest ----
for i in "${!PT_LO[@]}"; do
  PT_L="${PT_LO[$i]}"; PT_H="${PT_HI[$i]}"
  TMAX=$(( JOBS[$i] * MULT ))
  SLICE_DIR="${DIR_SIM}/${PT_L}-${PT_H}/${SIM_BID[$i]}"
  write_slice_manifest "${PT_L}" "${PT_H}" "${TMAX}" "${SLICE_DIR}"
done

finalize_seeds_csv "${SLICE_LIST}" "${SEEDS_CSV}"

# ---- optional ONE email (manager only) ----
if [[ "${MANAGER_MAIL}" -eq 1 && -n "${MAIL_USER}" ]]; then
  NOTIFY=$(mktemp)
  cat > "${NOTIFY}" <<'__MAILJOB__'
#!/bin/bash
#SBATCH --account=wsu
#SBATCH --qos=primary
#SBATCH --job-name=xsim_done
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=256M
#SBATCH --time=00:02:00
#SBATCH --mail-user=__MAIL__
#SBATCH --mail-type=END

echo "SIM DONE: RUN_TAG=__RUN__  SIM_BATCH_ID=__BID__"
echo "Expected tasks: __TOTAL__  Missing: __MISS__"
echo "missing_sim_outputs.csv: __MISSCSV__"
echo "sim_task_states.csv: __STATECSV__"
__MAILJOB__
  sed -i "s|__MAIL__|${MAIL_USER}|g; s|__RUN__|${RUN_TAG}|g; s|__BID__|${SIM_BATCH_ID}|g; s|__TOTAL__|${total}|g; s|__MISS__|${missing}|g; s|__MISSCSV__|${MISS_SIM_CSV}|g; s|__STATECSV__|${SIM_STATES_CSV}|g" "${NOTIFY}"
  sbatch --output=/dev/null --error=/dev/null "${NOTIFY}" >/dev/null 2>&1 || true
  rm -f "${NOTIFY}"
fi

log "Done."
exit 0








