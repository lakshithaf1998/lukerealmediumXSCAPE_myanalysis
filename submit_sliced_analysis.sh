#!/usr/bin/env bash
# submit_sliced_analysis.sh v5.3
# CHANGELOG
# v5.3 (bundle0 batch precedence + stronger diagnostics preservation):
#   • FIX: In bundled_hadrons mode, AnalysisBatchID now takes precedence over legacy AN_BATCH_ID so outputs go to bundle0 when AnalysisBatchID="bundle0" even if older AN_BATCH_ID="batch0" remains in jetscape.ini for legacy workflows.
#   • FIX: Manager log filename and jid_an_<slice>.txt now use the same effective batch id selected by the bundled-analysis contract.
#   • FIX: submitted_bundles_<batch>.csv is appended on resume instead of overwritten, preserving submission history for debugging.
#   • FIX: JSON status reads use Python JSON parsing instead of sed so events_seen/root_status checks are not fooled by formatting.
#   • KEEP: All v5.2 OG-style diagnostics, visible submit/skip/progress logs, watchdog logs, quarantine, and self-heal behavior remain enabled.
#
# v5.2 (restore OG-style visibility + safe bundle watchdog):
#   • FIX: Bundle manager logs submit/skip/progress lines directly instead of swallowing them inside command substitution.
#   • FIX: Watchdog counts only bundle worker jobs for the active RUN_TAG, not the manager job itself, so it cannot wait forever at active=1.
#   • FIX: Watchdog also respects the WSU primary QoS cap using total primary-job count while applying AnalysisMaxActiveBundleJobs to bundle workers only.
#   • FIX: Bad bundle outputs with wrong events_seen/root_status are quarantined before rerun, preserving debugging artifacts.
#   • LOG: Adds scan_start, scan_progress, count_missing_start/done, queue-slot, skip_done, submit_bundle, self-heal, and final report logs without dropping OG-style diagnostics.
#
# v5.1 (manager walltime honors SBATCH header):
#   • FIX: Auto-submit from Warrior now reads the script's own #SBATCH --time/--mem defaults instead of hardcoding 03:00:00.
#   • KEEP: MANAGER_TIME and MANAGER_MEM environment variables still override the script header when explicitly set.
#
# v5.0 (bundled hadron analysis manager):
#   • NEW: Replaces one-analyzer-job-per-hadron-file with one analyzer job per temporary hadron bundle.
#   • NEW: Keeps simulation untouched: source hadron files remain one event per XML/job.
#   • NEW: AnalysisBundleSize controls how many one-event hadron files are concatenated in $TMPDIR for each analyzer job.
#   • NEW: Bundle outputs are written as dphi_<RUN_TAG>_<PTLOW>_<PTHIGH>_bundleNNNNNN.root with matching JSON sidecars and manifests.
#   • KEEP: Auto-submit manager from Warrior/head node, compute-node analyzer rebuild, throttled Slurm submission, self-heal repair passes, skip/resume behavior, and jid_an_<slice>.txt merge handoff.
#
#SBATCH --account=wsu
#SBATCH --job-name=xan_bundle_mgr
#SBATCH --qos=primary
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --time=24:00:00
#SBATCH --mem=1G
#SBATCH --export=ALL

set -euo pipefail

ts(){ date +'%F %T'; }
log(){ echo "[$(ts)] $*"; }
die(){ log "[FATAL] $*"; exit 1; }

parse_sbatch_jobid(){ awk -F';' '{print $1}' <<<"${1:-}" | sed -nE 's/^([0-9]+).*$/\1/p'; }
need_jobid(){ local j; j="$(parse_sbatch_jobid "$2")"; [[ -n "$j" ]] || die "Could not parse sbatch jobid for $1: $2"; echo "$j"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"
INI_PATH="${INI_PATH:-${JETSCAPE_INI_PATH:-${SCRIPT_DIR}/jetscape.ini}}"
export INI_PATH
INSIDE_MANAGER=0
if [[ "${1:-}" == "--_inside_manager" ]]; then INSIDE_MANAGER=1; shift || true; fi

if [[ -z "${SLURM_JOB_ID:-}" && "${INSIDE_MANAGER}" -eq 0 ]]; then
  RUN_TAG_GUESS="$(grep -E '^[[:space:]]*RUN_TAG=' "${INI_PATH}" 2>/dev/null | head -n1 | sed -E 's/^[^=]+=//; s/[[:space:]]//g; s/^"//; s/"$//' || true)"
  [[ -n "${RUN_TAG_GUESS}" ]] || RUN_TAG_GUESS="NA"
  MANAGER_LOG_DIR="$HOME/xscape_runs/${RUN_TAG_GUESS}/logs/manager"
  mkdir -p "${MANAGER_LOG_DIR}"
  ts_compact="$(date +%Y%m%d_%H%M%S)"
  out="${MANAGER_LOG_DIR}/analysis_bundle_manager_${ts_compact}_%j.out"
  err="${MANAGER_LOG_DIR}/analysis_bundle_manager_${ts_compact}_%j.err"
  QDIR="$(printf %q "${SCRIPT_DIR}")"
  SELF="./$(basename "$0")"
  THIS_SCRIPT="${SCRIPT_DIR}/$(basename "$0")"
  SBATCH_MANAGER_TIME="$(awk '
    /^[[:space:]]*#SBATCH[[:space:]]+--time(=|[[:space:]]+)/ {
      line=$0; sub(/^[[:space:]]*#SBATCH[[:space:]]+--time[=[:space:]]+/, "", line); print line; exit
    }' "${THIS_SCRIPT}" 2>/dev/null || true)"
  SBATCH_MANAGER_MEM="$(awk '
    /^[[:space:]]*#SBATCH[[:space:]]+--mem(=|[[:space:]]+)/ {
      line=$0; sub(/^[[:space:]]*#SBATCH[[:space:]]+--mem[=[:space:]]+/, "", line); print line; exit
    }' "${THIS_SCRIPT}" 2>/dev/null || true)"
  MANAGER_TIME_EFFECTIVE="${MANAGER_TIME:-${SBATCH_MANAGER_TIME:-24:00:00}}"
  MANAGER_MEM_EFFECTIVE="${MANAGER_MEM:-${SBATCH_MANAGER_MEM:-1G}}"
  echo "[INFO] Manager resources: time=${MANAGER_TIME_EFFECTIVE} mem=${MANAGER_MEM_EFFECTIVE} (edit #SBATCH in $(basename "$0") or set MANAGER_TIME/MANAGER_MEM)"
  sbout=$(sbatch --parsable --account="${MANAGER_ACCOUNT:-wsu}" --qos="${MANAGER_QOS:-primary}" \
    --nodes=1 --ntasks=1 --cpus-per-task=1 --mem="${MANAGER_MEM_EFFECTIVE}" --time="${MANAGER_TIME_EFFECTIVE}" \
    --job-name="xab_mgr_${RUN_TAG_GUESS}" --output="${out}" --error="${err}" \
    --export=ALL,INI_PATH="${INI_PATH}" --wrap="cd ${QDIR} && ${SELF} --_inside_manager")
  jid="$(need_jobid "bundle analysis manager" "${sbout}")"
  echo "[INFO] Bundle analysis manager submitted: ${jid}"
  echo "[INFO] Logs: ${out/\%j/${jid}}  ${err/\%j/${jid}}"
  exit 0
fi

[[ -f "${INI_PATH}" ]] || die "jetscape.ini not found: ${INI_PATH}"
# shellcheck disable=SC1090
source "${INI_PATH}"

RUN_TAG="${RUN_TAG:-run}"
RUN_DIR="${RUNS_BASE:-${HOME}/xscape_runs/${RUN_TAG}}"; RUN_DIR="${RUN_DIR%/}"
DIR_SIM="${DIR_SIM:-${RUN_DIR}/sim}"
DIR_ANALYSIS="${DIR_ANALYSIS:-${RUN_DIR}/analysis}"
DIR_LOG_SIM="${DIR_LOG_SIM:-${RUN_DIR}/logs/sim}"
DIR_LOG_ANALYSIS="${DIR_LOG_ANALYSIS:-${RUN_DIR}/logs/analysis}"
DIR_FINAL="${DIR_FINAL:-${RUN_DIR}/final}"
ANALYSIS_INPUT_MODE="${AnalysisInputMode:-per_task}"
LEGACY_AN_BATCH_ID="${AN_BATCH_ID:-}"
if [[ "${ANALYSIS_INPUT_MODE}" == "bundled_hadrons" ]]; then
  # In bundle mode AnalysisBatchID is the authoritative folder knob. Legacy AN_BATCH_ID may remain in old ini files.
  AN_BATCH_ID="${AnalysisBatchID:-${LEGACY_AN_BATCH_ID:-bundle0}}"
else
  AN_BATCH_ID="${LEGACY_AN_BATCH_ID:-${AnalysisBatchID:-batch0}}"
fi
mkdir -p "${DIR_LOG_ANALYSIS}" "${DIR_FINAL}"
MANAGER_LOG="${DIR_LOG_ANALYSIS}/analysis_bundle_manager_${AN_BATCH_ID}.log"
log(){ echo "[$(ts)] $*" | tee -a "${MANAGER_LOG}"; }
die(){ log "[FATAL] $*"; exit 1; }
if [[ "${ANALYSIS_INPUT_MODE}" == "bundled_hadrons" && -n "${LEGACY_AN_BATCH_ID}" && -n "${AnalysisBatchID:-}" && "${LEGACY_AN_BATCH_ID}" != "${AnalysisBatchID}" ]]; then
  log "[WARN] jetscape.ini has legacy AN_BATCH_ID=${LEGACY_AN_BATCH_ID} but AnalysisBatchID=${AnalysisBatchID}; bundled_hadrons uses AnalysisBatchID -> effective batch=${AN_BATCH_ID}."
fi

[[ -n "${Multiplier+x}" || -n "${multiplier+x}" ]] || die "Missing Multiplier in jetscape.ini"
MULT="${Multiplier-${multiplier-}}"; [[ "${MULT}" =~ ^[0-9]+$ && ${MULT} -ge 1 ]] || die "Invalid Multiplier=${MULT}"
declare -p PT_LO >/dev/null 2>&1 || die "Missing PT_LO array"
declare -p PT_HI >/dev/null 2>&1 || die "Missing PT_HI array"
declare -p JOBS >/dev/null 2>&1 || die "Missing JOBS array"
[[ -n "${NUM_EVENTS+x}" && "${NUM_EVENTS}" =~ ^[0-9]+$ && ${NUM_EVENTS} -ge 1 ]] || die "Invalid/missing NUM_EVENTS=${NUM_EVENTS:-unset}"
(( ${#PT_LO[@]} == ${#PT_HI[@]} && ${#PT_LO[@]} == ${#JOBS[@]} )) || die "PT_LO/PT_HI/JOBS length mismatch"

BUNDLE_SIZE="${AnalysisBundleSize:-100}"; [[ "${BUNDLE_SIZE}" =~ ^[0-9]+$ && ${BUNDLE_SIZE} -ge 1 ]] || die "Invalid AnalysisBundleSize=${BUNDLE_SIZE}"
MAX_ACTIVE_BUNDLES="${AnalysisMaxActiveBundleJobs:-${MaxActiveJobs:-200}}"; [[ "${MAX_ACTIVE_BUNDLES}" =~ ^[0-9]+$ && ${MAX_ACTIVE_BUNDLES} -ge 1 ]] || die "Invalid AnalysisMaxActiveBundleJobs=${MAX_ACTIVE_BUNDLES}"
POLL_SEC="${SubmitPollSec:-30}"; [[ "${POLL_SEC}" =~ ^[0-9]+$ && ${POLL_SEC} -ge 1 ]] || POLL_SEC=30
BUNDLE_TIME="${AnalysisBundleTime:-04:00:00}"
BUNDLE_MEM="${AnalysisBundleMem:-2G}"
BUNDLE_CPUS="${AnalysisBundleCPUs:-1}"
SELF_HEAL_ENABLE="${AnalysisSelfHealEnable:-1}"
SELF_HEAL_MAX="${AnalysisSelfHealMaxPasses:-5}"
SELF_HEAL_GRACE="${AnalysisSelfHealGraceSec:-20}"
FAIL_ON_MISSING="${AnalysisFailOnMissing:-1}"
BUNDLE_SCAN_LOG_EVERY="${AnalysisBundleScanLogEvery:-50}"
[[ "${BUNDLE_SCAN_LOG_EVERY}" =~ ^[0-9]+$ && ${BUNDLE_SCAN_LOG_EVERY} -ge 1 ]] || BUNDLE_SCAN_LOG_EVERY=50
WSU_PRIMARY_CAP=1000
if (( MAX_ACTIVE_BUNDLES > WSU_PRIMARY_CAP )); then
  log "[WARN] AnalysisMaxActiveBundleJobs=${MAX_ACTIVE_BUNDLES} exceeds WSU primary cap ${WSU_PRIMARY_CAP}; forcing to ${WSU_PRIMARY_CAP}."
  MAX_ACTIVE_BUNDLES=${WSU_PRIMARY_CAP}
fi

log "BUNDLED ANALYSIS START run=${RUN_TAG} mode=${ANALYSIS_INPUT_MODE} bundle_size=${BUNDLE_SIZE} max_active_bundle_jobs=${MAX_ACTIVE_BUNDLES} batch=${AN_BATCH_ID}"
log "resources time=${BUNDLE_TIME} mem=${BUNDLE_MEM} cpus=${BUNDLE_CPUS}; selfheal=${SELF_HEAL_ENABLE}/${SELF_HEAL_MAX} grace=${SELF_HEAL_GRACE}s"

log "[build] rebuilding analyzer on compute node $(hostname)"
module purge
module load gnu7/7.3.0
module load root/6.28.10 fastjet/3.4.0
which g++ | sed 's/^/[build] g++=/' | tee -a "${MANAGER_LOG}" || true
which root-config | sed 's/^/[build] root-config=/' | tee -a "${MANAGER_LOG}" || true
which fastjet-config | sed 's/^/[build] fastjet-config=/' | tee -a "${MANAGER_LOG}" || true
g++ -std=c++17 -O3 $(root-config --cflags) $(fastjet-config --cxxflags) \
  analyze_dphi_sliced.cpp -o analyze_dphi_sliced \
  $(fastjet-config --libs) $(root-config --glibs) -lPhysics -lEG
chmod +x analyze_dphi_sliced
log "[build] done: ${SCRIPT_DIR}/analyze_dphi_sliced"

bundle_tag(){ printf '%s_%s_%s_bundle%06d' "$RUN_TAG" "$1" "$2" "$3"; }
bundle_expected_events(){ local start="$1" end="$2"; echo $(( (end-start+1) * NUM_EVENTS )); }
json_get(){
  local f="$1" k="$2"
  [[ -s "$f" ]] || return 0
  python3 - "$f" "$k" <<'PYJSONGET'
import json, sys
path, key = sys.argv[1], sys.argv[2]
try:
    with open(path, 'r', encoding='utf-8') as fh:
        val = json.load(fh).get(key, '')
    print(val if val is not None else '', end='')
except Exception:
    print('', end='')
PYJSONGET
}
status_bundle(){
  local rootf="$1" metaf="$2" expected="$3" ev rs
  [[ -s "$rootf" ]] || { echo MISSING_ROOT; return; }
  [[ -s "$metaf" ]] || { echo MISSING_META; return; }
  ev="$(json_get "$metaf" events_seen)"; rs="$(json_get "$metaf" root_status)"
  [[ "$rs" == "ok" ]] || { echo CORRUPT_ROOT; return; }
  [[ "$ev" =~ ^[0-9]+$ && "$ev" -eq "$expected" ]] || { echo INCOMPLETE_EVENTS; return; }
  echo DONE
}
bundle_worker_prefix(){ printf 'xab_%s_' "${RUN_TAG}"; }
active_bundle_jobs(){
  local pfx
  pfx="$(bundle_worker_prefix)"
  squeue -u "${USER}" -q primary -h -o "%j" 2>/dev/null | awk -v pfx="${pfx}" '$0 ~ "^"pfx {c++} END{print c+0}'
}
primary_job_count(){
  squeue -u "${USER}" -q primary -h 2>/dev/null | wc -l | awk '{print $1}'
}
wait_for_slot(){
  local active total_primary free_bundle free_primary
  while true; do
    active="$(active_bundle_jobs)"
    total_primary="$(primary_job_count)"
    free_bundle=$(( MAX_ACTIVE_BUNDLES - active ))
    free_primary=$(( WSU_PRIMARY_CAP - total_primary ))
    if (( free_bundle > 0 && free_primary > 0 )); then
      log "[watchdog] slot_ok bundle_workers=${active}/${MAX_ACTIVE_BUNDLES} primary_jobs=${total_primary}/${WSU_PRIMARY_CAP}"
      break
    fi
    log "[watchdog] queue_full bundle_workers=${active}/${MAX_ACTIVE_BUNDLES} primary_jobs=${total_primary}/${WSU_PRIMARY_CAP}; waiting ${POLL_SEC}s"
    sleep "${POLL_SEC}"
  done
}
wait_until_drained(){
  local active
  while true; do
    active="$(active_bundle_jobs)"
    if (( active == 0 )); then
      log "[watchdog] bundle worker queue drained for RUN_TAG=${RUN_TAG}."
      break
    fi
    log "[watchdog] waiting for bundle workers to drain: active=${active}; sleep=${POLL_SEC}s"
    sleep "${POLL_SEC}"
  done
}
quarantine_bundle_outputs(){
  local rootf="$1" metaf="$2" why="$3" qdir stamp
  stamp="$(date +%s)"
  qdir="$(dirname "${rootf}")/quarantine"
  mkdir -p "${qdir}"
  [[ -f "${rootf}" ]] && mv -f "${rootf}" "${qdir}/$(basename "${rootf}").${why}.${stamp}" || true
  [[ -f "${metaf}" ]] && mv -f "${metaf}" "${qdir}/$(basename "${metaf}").${why}.${stamp}" || true
}
submit_bundle(){
  local idx="$1" pt_l="$2" pt_h="$3" bid="$4" start="$5" end="$6" expected="$7" pass_label="$8"
  local bpad jobname out err sbout jid
  bpad="$(printf '%06d' "$bid")"
  jobname="xab_${RUN_TAG}_${pt_l}_${pt_h}_${bpad}"
  out="${DIR_LOG_ANALYSIS}/bundle_${pt_l}_${pt_h}_${pass_label}_${bpad}_%j.out"
  err="${DIR_LOG_ANALYSIS}/bundle_${pt_l}_${pt_h}_${pass_label}_${bpad}_%j.err"
  wait_for_slot
  log "submit_bundle pass=${pass_label} slice=${pt_l}-${pt_h} bundle=${bpad} tasks=${start}-${end} expected_events=${expected}"
  sbout=$(sbatch --parsable --qos=primary --job-name="${jobname}" \
    --time="${BUNDLE_TIME}" --mem="${BUNDLE_MEM}" --cpus-per-task="${BUNDLE_CPUS}" \
    --output="${out}" --error="${err}" \
    --export=ALL,INI_PATH="${INI_PATH}",AnalysisInputMode="bundled_hadrons",ANALYSIS_BUNDLE_MODE=1,PT_LOW="${pt_l}",PT_HIGH="${pt_h}",SLICE_INDEX="${idx}",TASK_ID="${bid}",BUNDLE_ID="${bid}",TASK_START="${start}",TASK_END="${end}",BUNDLE_EXPECTED_EVENTS="${expected}",AN_BATCH_ID="${AN_BATCH_ID}" \
    submit_analysis_dphi_sliced.slurm)
  jid="$(need_jobid "bundle ${pt_l}-${pt_h} ${bpad}" "${sbout}")"
  echo "${jid},${jobname},${pt_l},${pt_h},${bid},${start},${end},${expected},${pass_label}" >> "${SUBMITTED_BUNDLES_CSV}"
  log "submitted_bundle pass=${pass_label} slice=${pt_l}-${pt_h} bundle=${bpad} jobid=${jid} log=${out//%j/${jid}}"
}
scan_and_submit_missing(){
  local pass_label="$1"
  SCAN_SUBMITTED=0
  local submitted=0 skipped=0 missing=0 checked=0 idx pt_l pt_h total b start end expected tag rootf metaf st
  log "scan_start pass=${pass_label} bundle_size=${BUNDLE_SIZE} scan_log_every=${BUNDLE_SCAN_LOG_EVERY}"
  for idx in "${!PT_LO[@]}"; do
    pt_l="${PT_LO[$idx]}"; pt_h="${PT_HI[$idx]}"; total=$(( JOBS[idx] * MULT ))
    log "scan_slice_start pass=${pass_label} slice=${pt_l}-${pt_h} total_tasks=${total} batch=${AN_BATCH_ID}"
    echo "${AN_BATCH_ID}" > "${DIR_LOG_ANALYSIS}/jid_an_${pt_l}_${pt_h}.txt"
    mkdir -p "${DIR_ANALYSIS}/${pt_l}-${pt_h}/${AN_BATCH_ID}"
    b=1; start=1
    while (( start <= total )); do
      end=$(( start + BUNDLE_SIZE - 1 )); (( end > total )) && end="$total"
      expected="$(bundle_expected_events "$start" "$end")"
      tag="$(bundle_tag "$pt_l" "$pt_h" "$b")"
      rootf="${DIR_ANALYSIS}/${pt_l}-${pt_h}/${AN_BATCH_ID}/dphi_${tag}.root"
      metaf="${DIR_ANALYSIS}/${pt_l}-${pt_h}/${AN_BATCH_ID}/slice_meta_${tag}.json"
      st="$(status_bundle "$rootf" "$metaf" "$expected")"
      checked=$((checked+1))
      if [[ "$st" == DONE ]]; then
        skipped=$((skipped+1))
        log "skip_done pass=${pass_label} slice=${pt_l}-${pt_h} bundle=$(printf '%06d' "$b") tasks=${start}-${end} events=${expected}"
      else
        missing=$((missing+1))
        if [[ "$st" == "INCOMPLETE_EVENTS" || "$st" == "CORRUPT_ROOT" || ( "$st" == "MISSING_META" && -s "$rootf" ) || ( "$st" == "MISSING_ROOT" && -s "$metaf" ) ]]; then
          log "redo_bundle pass=${pass_label} slice=${pt_l}-${pt_h} bundle=$(printf '%06d' "$b") status=${st} tasks=${start}-${end} expected_events=${expected} -> quarantine"
          quarantine_bundle_outputs "$rootf" "$metaf" "${pass_label}_${st}"
        else
          log "need_bundle pass=${pass_label} slice=${pt_l}-${pt_h} bundle=$(printf '%06d' "$b") status=${st} tasks=${start}-${end} expected_events=${expected}"
        fi
        submit_bundle "$idx" "$pt_l" "$pt_h" "$b" "$start" "$end" "$expected" "$pass_label"
        submitted=$((submitted+1))
        SCAN_SUBMITTED=${submitted}
      fi
      if (( checked % BUNDLE_SCAN_LOG_EVERY == 0 )); then
        log "scan_progress pass=${pass_label} checked=${checked} submitted=${submitted} skipped_done=${skipped} missing_before_submit=${missing} active_bundle_workers=$(active_bundle_jobs)"
      fi
      b=$((b+1)); start=$((end+1))
    done
    log "scan_slice_done pass=${pass_label} slice=${pt_l}-${pt_h} checked_bundles=${b-1} submitted_so_far=${submitted} skipped_done_so_far=${skipped}"
  done
  SCAN_SUBMITTED=${submitted}
  log "scan_submit_done pass=${pass_label} submitted=${submitted} skipped_done=${skipped} missing_before_submit=${missing} checked=${checked}"
}

count_missing_bundles(){
  local missing=0 checked=0 idx pt_l pt_h total b start end expected tag rootf metaf st
  log "count_missing_start batch=${AN_BATCH_ID}"
  for idx in "${!PT_LO[@]}"; do
    pt_l="${PT_LO[$idx]}"; pt_h="${PT_HI[$idx]}"; total=$(( JOBS[idx] * MULT ))
    b=1; start=1
    while (( start <= total )); do
      end=$(( start + BUNDLE_SIZE - 1 )); (( end > total )) && end="$total"
      expected="$(bundle_expected_events "$start" "$end")"
      tag="$(bundle_tag "$pt_l" "$pt_h" "$b")"
      rootf="${DIR_ANALYSIS}/${pt_l}-${pt_h}/${AN_BATCH_ID}/dphi_${tag}.root"
      metaf="${DIR_ANALYSIS}/${pt_l}-${pt_h}/${AN_BATCH_ID}/slice_meta_${tag}.json"
      st="$(status_bundle "$rootf" "$metaf" "$expected")"
      [[ "$st" == DONE ]] || missing=$((missing+1))
      checked=$((checked+1))
      if (( checked % BUNDLE_SCAN_LOG_EVERY == 0 )); then
        log "count_missing_progress checked=${checked} missing=${missing}"
      fi
      b=$((b+1)); start=$((end+1))
    done
  done
  COUNT_MISSING_RESULT=${missing}
  log "count_missing_done checked=${checked} missing=${missing}"
}

write_reports(){
  local states="${DIR_FINAL}/analysis_bundle_states.csv" miss="${DIR_FINAL}/missing_analysis_outputs.csv"
  echo "pthat_low,pthat_high,bundle,task_start,task_end,status,root_file,meta_file,bytes,events_seen,expected_events" > "$states"
  echo "pthat_low,pthat_high,bundle,task_start,task_end,what,root_file,meta_file,events_seen,expected_events" > "$miss"
  local missing=0 total=0 idx pt_l pt_h nj b start end expected tag rootf metaf st ev sz what
  for idx in "${!PT_LO[@]}"; do
    pt_l="${PT_LO[$idx]}"; pt_h="${PT_HI[$idx]}"; nj=$(( JOBS[idx] * MULT ))
    b=1; start=1
    while (( start <= nj )); do
      end=$(( start + BUNDLE_SIZE - 1 )); (( end > nj )) && end="$nj"
      expected="$(bundle_expected_events "$start" "$end")"
      tag="$(bundle_tag "$pt_l" "$pt_h" "$b")"
      rootf="${DIR_ANALYSIS}/${pt_l}-${pt_h}/${AN_BATCH_ID}/dphi_${tag}.root"
      metaf="${DIR_ANALYSIS}/${pt_l}-${pt_h}/${AN_BATCH_ID}/slice_meta_${tag}.json"
      st="$(status_bundle "$rootf" "$metaf" "$expected")"; ev="$(json_get "$metaf" events_seen || true)"; [[ -n "$ev" ]] || ev=NA
      sz=0; [[ -s "$rootf" ]] && sz=$(wc -c < "$rootf" 2>/dev/null || echo 0)
      total=$((total+1))
      echo "${pt_l},${pt_h},${b},${start},${end},${st},${rootf},${metaf},${sz},${ev},${expected}" >> "$states"
      if [[ "$st" != DONE ]]; then
        case "$st" in MISSING_ROOT) what=missing_dphi_root;; MISSING_META) what=missing_slice_meta_json;; CORRUPT_ROOT) what=corrupt_root;; INCOMPLETE_EVENTS) what=incomplete_events;; *) what=unknown_incomplete;; esac
        echo "${pt_l},${pt_h},${b},${start},${end},${what},${rootf},${metaf},${ev},${expected}" >> "$miss"
        missing=$((missing+1))
      fi
      b=$((b+1)); start=$((end+1))
    done
  done
  log "[report] bundle_total=${total} missing=${missing}; states=${states}; missing=${miss}"
  return $(( missing == 0 ? 0 : 1 ))
}

SUBMITTED_BUNDLES_CSV="${DIR_LOG_ANALYSIS}/submitted_bundles_${AN_BATCH_ID}.csv"
if [[ ! -s "${SUBMITTED_BUNDLES_CSV}" ]]; then
  echo "jobid,jobname,pthat_low,pthat_high,bundle,task_start,task_end,expected_events,pass" > "${SUBMITTED_BUNDLES_CSV}"
else
  log "[resume] preserving existing submission history: ${SUBMITTED_BUNDLES_CSV}"
fi
scan_and_submit_missing initial
submitted="${SCAN_SUBMITTED:-0}"
if (( submitted > 0 )); then wait_until_drained; fi

if [[ "$SELF_HEAL_ENABLE" == "1" ]]; then
  for pass in $(seq 1 "$SELF_HEAL_MAX"); do
    count_missing_bundles
    missing="${COUNT_MISSING_RESULT:-0}"
    if (( missing == 0 )); then log "[self-heal] all bundles complete after $((pass-1)) repair pass(es)."; break; fi
    log "[self-heal] missing_bundles=${missing}; repair_pass=${pass}/${SELF_HEAL_MAX} after grace=${SELF_HEAL_GRACE}s"
    (( SELF_HEAL_GRACE > 0 )) && sleep "$SELF_HEAL_GRACE"
    scan_and_submit_missing "repair_${pass}"
    submitted="${SCAN_SUBMITTED:-0}"
    if (( submitted > 0 )); then wait_until_drained; fi
  done
else
  log "[self-heal] disabled"
fi

if write_reports; then
  log "BUNDLED ANALYSIS COMPLETE: all bundle outputs present."
else
  log "BUNDLED ANALYSIS INCOMPLETE: see ${DIR_FINAL}/missing_analysis_outputs.csv"
  [[ "${FAIL_ON_MISSING}" == "1" ]] && exit 3 || true
fi
