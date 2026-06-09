#!/usr/bin/env bash
# submit_analysis_dphi_sliced.slurm v7.4
# CHANGELOG
# v7.4 (bundle batch-id precedence):
#   • FIX: In bundled_hadrons mode, AnalysisBatchID now overrides legacy AN_BATCH_ID from jetscape.ini, so bundle workers write under bundle0 consistently with the manager and merge.
#   • LOG: Warns when legacy AN_BATCH_ID conflicts with AnalysisBatchID and prints the effective batch folder.
#   • KEEP: v7.3 event-header detection, synthetic separator logic, post-run event-count guard, OG single-task mode, normalization, provenance, ROOT/JSON naming, FastJet banner, and diagnostics.
#
# v7.3 (bundle header detection + hard event-count guard):
#   • FIX: Correct Python event-header detector regex so real # Event headers are counted and synthetic separators are not injected on top of real headers.
#   • FIX: After analyzer + metadata augmentation, hard-fail bundle jobs unless slice_meta events_seen equals BUNDLE_EXPECTED_EVENTS and root_status is ok.
#   • LOG: Prints explicit bundle event-count validation after the analyzer so bad bundle roots are caught before merge/self-heal.
#   • KEEP: OG single-task mode, normalization, provenance, ROOT/JSON naming, FastJet banner, and per-task diagnostics remain unchanged.
#
# v7.2 (bundle event separators for headerless one-event hadron files):
#   • FIX: Headerless one-event JETSCAPE hadron files are now accepted as one event when NUM_EVENTS=1 and a valid sigma footer exists.
#   • FIX: Bundle mode injects synthetic # Event separators before headerless source files so concatenating 100 one-event files produces 100 analyzer events, not one giant event.
#   • LOG: Bundle manifests record each source file's detected event count, header count, and whether a synthetic separator was injected.
#
# v7.1 (bundled hadron analysis mode):
#   • NEW: ANALYSIS_BUNDLE_MODE=1 / AnalysisInputMode=bundled_hadrons supports one Slurm job analyzing a temporary concatenation of many one-event hadron files.
#   • NEW: Persistent bundle manifest records the source hadron files; analyzer input stays in $TMPDIR and is not preserved.
#   • KEEP: Single-task mode, normalization policy, sim-subdir selection, provenance writing, and ROOT/JSON output contract are preserved for non-bundled launches.
#
# v6.9 (custom ini-path support for wrapper-driven multianalysis):
#   • NEW: Honor INI_PATH / JETSCAPE_INI_PATH so wrapper-generated per-variant ini files can drive the existing ANALYSIS worker.
#   • NO CHANGE: Normalization policy, hadron/meta validation, provenance writing, and ROOT/JSON output contracts remain unchanged.
# v6.8 (remove dead helper code only):
#   • CLEANUP: Removed the unused extract_sigmaGen_mb() helper.
#   • CLEANUP: Removed the unused count_present_hadron_files() helper.
#   • DOC: No runtime logic, normalization policy, or task-selection behavior changed.
#
# v6.7 (explicit Mjj back-to-back knob validation/logging):
#   • FIX: Require MJJ_REQUIRE_BACKTOBACK to be present and equal to 0 or 1 before the worker proceeds, keeping the analyzer/fitter/comparisor Mjj selection contract explicit.
#   • LOG: Worker startup now prints MJJ_REQUIRE_BACKTOBACK next to DIJET_BACKTOBACK_TOL_DEG and the imbalance controls for reproducible per-task debugging.
#
# v6.6 (rename sim subdir marker files):
#   • CHANGE: Read SIM run-directory markers from subdir_sim_<PTL>_<PTH>.txt instead of jid_sim_<PTL>_<PTH>.txt.
#     The marker stores the SIM subdirectory/batch name, not a Slurm job id.
#   • LOG: Error/help text now consistently refers to subdir_sim_* markers.
#
# v6.5 (post-run metadata patch stability + JSON write fix):
#   • FIX: Repair the embedded Python JSON augmentation writer so it writes a real newline (fh.write("\n")) instead of a broken multiline string literal.
#   • FIX: Preserve the existing atomic tmp-file replace flow while ensuring the wrapper can complete successfully after analyzer output exists.
#
# v6.4 (canonical normalization provenance + authoritative analysis metadata):
#   • FIX: The analysis wrapper now records the exact normalization actually used for each task into slice_meta JSON: norm_weight_mb_per_event_used, norm_sigmaGen_mb_used, norm_sigmaErr_mb_used, norm_denominator_events_used, norm_source, norm_policy, and related provenance fields.
#   • FIX: Post-run JSON augmentation now preserves the analyzer-parsed hadron-footer sigma values as hadron_footer_sigmaGen_mb / hadron_footer_sigmaErr_mb diagnostics and overwrites sigmaGen_mb / sigmaErr_mb with the authoritative normalization used by the wrapper.
#   • SAFETY: Hard-fail if the selected normalization path cannot provide a finite positive canonical sigmaGen/sigmaErr pair and denominator, so merge/fitter cannot later consume mismatched normalization metadata.
#
# v6.3 (retire dead weight-file switch cleanly):
#   • FIX: Removed the legacy USE_WEIGHT_FILES / UseWeightFiles fallback logic. Analysis now supports only the manifest/metadata weighting path.
#   • SAFETY: Hard-fail if a stale USE_WEIGHT_FILES environment variable or UseWeightFiles ini key is present, so old configs cannot masquerade as supported behavior.
#
# v6.2 (strict sim-run resolution + explicit config contract):
#   • FIX: Removed the dangerous newest-directory fallback for SIM run selection. Analysis now accepts only the exact subdir_sim_<PTL>_<PTH>.txt run directory and hard-fails otherwise, so it cannot silently analyze the wrong sim batch.
#   • FIX: Multiplier must now be explicitly present in jetscape.ini, non-empty, numeric, and >= 1. The analyzer-side expected-task logic no longer assumes a default.
#   • FIX: INCLUDE_XSEC_NORM_ERR must now be explicitly present in jetscape.ini and equal to 0 or 1, matching the stricter workflow contract already enforced on merge.
#
# v6.1 (record exact sim provenance into analysis JSON):
#   • NEW: After resolving the actual SIM_SUBDIR/HADRON_FILE used for a task, write exact sim provenance into slice_meta JSON: sim_run_dir, hadron_file, sim_batch_id, sim_manifest_path, and sim_selection_mode.
#   • FIX: Merge no longer has to guess which sim run directory analysis used when this metadata is present; downstream provenance/debugging can trust the analysis JSON as the source of truth.
#   • SAFETY: Provenance paths are written as canonical absolute paths and are patched into the existing analyzer JSON only after the analyzer succeeds, so failed jobs do not advertise fake provenance.
#
# v6.0 (fallback denominator fix + comment cleanup):
#   • FIX: In manifest-missing fallback mode with ENABLE_RENORM=1, the event denominator now matches the
#     exact strict-good source set used to compute fallback sigmaGen_mb (good meta tasks + good hadron-only tasks).
#     This removes the old mixed-source bug where the numerator could use more tasks than the denominator.
#   • FIX: Removed the legacy denominator fallback that counted merely non-empty hadron files.
#   • DOC: Trimmed stale header comments/changelog entries so the file describes current behavior.
#
# v5.9:
#   • Hadron ASCII fallback sources are accepted only if they look like complete tasks:
#     exactly NUM_EVENTS event headers are present, sigmaGen > 0, and sigmaErr > 0.
#
# v5.8:
#   • When sim_manifest.json is missing, compute one slice-level fallback sigmaGen_mb from all available good
#     per-task meta / hadron sources in the slice instead of wobbling task-by-task.
#
#SBATCH --account=wsu
#SBATCH --job-name=analyse_dphi
#SBATCH --qos=primary
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --time=00:20:00
#SBATCH --mem=1G
#SBATCH --export=ALL
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null

set -euo pipefail

ts(){ date +'%F %T'; }
log(){ echo "[$(ts)] $*"; }
die(){ log "[ERROR] $*"; exit 2; }

canon_path(){
  local p="$1"
  python3 - <<'PY' "${p}"
import os, sys
print(os.path.realpath(sys.argv[1]), end="")
PY
}

augment_analysis_meta_with_provenance(){
  local json_path="$1"
  local sim_run_dir="$2"
  local hadron_file="$3"
  local sim_batch_id="$4"
  local sim_manifest_path="$5"
  local sim_selection_mode="$6"
  local norm_weight="$7"
  local norm_sigma="$8"
  local norm_sigma_err="$9"
  local norm_denom="${10}"
  local norm_source="${11}"
  local norm_policy="${12}"
  local norm_denom_source="${13}"
  local norm_sigma_source="${14}"
  local norm_enable_renorm="${15}"

  python3 - <<'PY' "${json_path}" "${sim_run_dir}" "${hadron_file}" "${sim_batch_id}" "${sim_manifest_path}" "${sim_selection_mode}" "${norm_weight}" "${norm_sigma}" "${norm_sigma_err}" "${norm_denom}" "${norm_source}" "${norm_policy}" "${norm_denom_source}" "${norm_sigma_source}" "${norm_enable_renorm}"
import json, os, sys

(
    json_path,
    sim_run_dir,
    hadron_file,
    sim_batch_id,
    sim_manifest_path,
    sim_selection_mode,
    norm_weight,
    norm_sigma,
    norm_sigma_err,
    norm_denom,
    norm_source,
    norm_policy,
    norm_denom_source,
    norm_sigma_source,
    norm_enable_renorm,
) = sys.argv[1:16]

with open(json_path, "r", encoding="utf-8") as fh:
    data = json.load(fh)

hadron_sigma = data.get("sigmaGen_mb", None)
hadron_sigma_err = data.get("sigmaErr_mb", None)
if hadron_sigma is not None:
    data["hadron_footer_sigmaGen_mb"] = hadron_sigma
if hadron_sigma_err is not None:
    data["hadron_footer_sigmaErr_mb"] = hadron_sigma_err

auth_weight = float(norm_weight)
auth_sigma = float(norm_sigma)
auth_sigma_err = float(norm_sigma_err)
auth_denom = int(norm_denom)
auth_enable_renorm = int(norm_enable_renorm)

data["sim_run_dir"] = sim_run_dir
data["hadron_file"] = hadron_file
data["sim_batch_id"] = sim_batch_id
data["sim_manifest_path"] = sim_manifest_path
data["sim_selection_mode"] = sim_selection_mode

data["weight_mb_per_event"] = auth_weight
data["sigmaGen_mb"] = auth_sigma
data["sigmaErr_mb"] = auth_sigma_err

data["norm_contract_version"] = "xscape.analysis_norm.v1"
data["norm_weight_mb_per_event_used"] = auth_weight
data["norm_sigmaGen_mb_used"] = auth_sigma
data["norm_sigmaErr_mb_used"] = auth_sigma_err
data["norm_denominator_events_used"] = auth_denom
data["norm_source"] = norm_source
data["norm_policy"] = norm_policy
data["norm_denominator_source"] = norm_denom_source
data["norm_sigma_source"] = norm_sigma_source
data["norm_enable_renorm"] = auth_enable_renorm


bundle_mode = os.environ.get("ANALYSIS_BUNDLE_MODE", "0").strip()
if bundle_mode in ("1", "true", "TRUE", "yes", "YES"):
    data["analysis_input_mode"] = "bundled_hadrons"
    data["bundle_id"] = int(os.environ.get("BUNDLE_ID", "0") or "0")
    data["bundle_task_start"] = int(os.environ.get("TASK_START", "0") or "0")
    data["bundle_task_end"] = int(os.environ.get("TASK_END", "0") or "0")
    data["bundle_task_count"] = int(os.environ.get("BUNDLE_TASK_COUNT", "0") or "0")
    data["bundle_expected_events"] = int(os.environ.get("BUNDLE_EXPECTED_EVENTS", "0") or "0")
    data["hadron_bundle_manifest"] = os.environ.get("BUNDLE_MANIFEST_REAL", "")
    data["hadron_bundle_input_note"] = "Analyzer read a temporary concatenated hadron file in $TMPDIR; this manifest records the persistent source list."
else:
    data["analysis_input_mode"] = "single_hadron_file"

tmp_path = json_path + ".tmp"
with open(tmp_path, "w", encoding="utf-8") as fh:
    json.dump(data, fh, indent=2)
    fh.write("\n")
os.replace(tmp_path, json_path)
PY
}

# Slurm copies the script into /var/spool/...; use submit dir as the canonical base.
if [[ -n "${SLURM_SUBMIT_DIR:-}" && -d "${SLURM_SUBMIT_DIR}" ]]; then
  BASE_DIR="${SLURM_SUBMIT_DIR}"
else
  BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi

INI_PATH="${INI_PATH:-${JETSCAPE_INI_PATH:-${BASE_DIR}/jetscape.ini}}"
[[ -f "${INI_PATH}" ]] || die "jetscape.ini not found: ${INI_PATH}. Fix by submitting from xscape folder, or export INI_PATH=/abs/path/jetscape.ini."
ENV_AN_BATCH_ID="${AN_BATCH_ID:-}"
ENV_ANALYSIS_INPUT_MODE="${AnalysisInputMode:-}"

# shellcheck disable=SC1090
source "${INI_PATH}"

log "[INI] Using jetscape.ini: ${INI_PATH}"
log "[INI] PARTICLE_ETA_MAX=${PARTICLE_ETA_MAX:-unset}  JET_ETA_MAX=${JET_ETA_MAX:-unset}  JET_ETA_MODE=${JET_ETA_MODE:-unset}"
log "[INI] JET_PT_MIN=${JET_PT_MIN:-unset}  LEAD_PT_MIN=${LEAD_PT_MIN:-unset}  SUBLEAD_PT_MIN=${SUBLEAD_PT_MIN:-unset}  SUBFRAC=${SUBFRAC:-unset}"
log "[INI] DIJET_BACKTOBACK_TOL_DEG=${DIJET_BACKTOBACK_TOL_DEG:-unset}  MJJ_REQUIRE_BACKTOBACK=${MJJ_REQUIRE_BACKTOBACK:-unset}  IMBALANCE_REQUIRE_BACKTOBACK=${IMBALANCE_REQUIRE_BACKTOBACK:-unset}  IMBALANCE_BACKTOBACK_TOL_DEG=${IMBALANCE_BACKTOBACK_TOL_DEG:-unset}"
# NOTE: In bash, arrays expand as only the first element when referenced as ${VAR}.
# Print a stable full representation for debugging.
if declare -p JET_RADIUS_LIST >/dev/null 2>&1; then
  log "[INI] JET_RADIUS_LIST=${JET_RADIUS_LIST[*]}"
else
  log "[INI] JET_RADIUS_LIST=${JET_RADIUS_LIST:-unset}"
fi

RUN_TAG="${RUN_TAG:-run}"
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
log "[INI] ENABLE_RENORM=${ENABLE_RENORM}"

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
log "[INI] Multiplier=${MULT}"

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
log "[INI] INCLUDE_XSEC_NORM_ERR=${INCLUDE_XSEC_NORM_ERR}"

if [[ -z "${MJJ_REQUIRE_BACKTOBACK+x}" ]]; then
  die "jetscape.ini missing required key MJJ_REQUIRE_BACKTOBACK (must be 0 or 1). Refusing to assume a default."
fi
if [[ -z "${MJJ_REQUIRE_BACKTOBACK}" ]] || ! [[ "${MJJ_REQUIRE_BACKTOBACK}" =~ ^[01]$ ]]; then
  die "jetscape.ini has invalid MJJ_REQUIRE_BACKTOBACK=${MJJ_REQUIRE_BACKTOBACK:-<unset>}. Must be 0 or 1."
fi
log "[INI] MJJ_REQUIRE_BACKTOBACK=${MJJ_REQUIRE_BACKTOBACK}"

# Canonical run directory
RUN_DIR="${RUNS_BASE:-}"
if [[ -z "${RUN_DIR}" ]]; then
  if [[ -n "${DIR_BASE:-}" ]]; then
    RUN_DIR="${DIR_BASE%/}/${RUN_TAG}"
  else
    RUN_DIR="${HOME}/xscape_runs/${RUN_TAG}"
  fi
fi
RUN_DIR="${RUN_DIR%/}"

DIR_SIM="${DIR_SIM:-${RUN_DIR}/sim}"
DIR_ANALYSIS="${DIR_ANALYSIS:-${RUN_DIR}/analysis}"
DIR_LOG_SIM="${DIR_LOG_SIM:-${RUN_DIR}/logs/sim}"

if [[ -n "${USE_WEIGHT_FILES+x}" ]]; then
  die "Stale environment variable USE_WEIGHT_FILES is no longer supported. Remove it and rerun; analysis now uses only the manifest/metadata weighting path."
fi
if [[ -n "${UseWeightFiles+x}" ]]; then
  die "Stale jetscape.ini key UseWeightFiles is no longer supported. Remove it from jetscape.ini and rerun; analysis now uses only the manifest/metadata weighting path."
fi

ANALYZER_BIN_DEFAULT="${BASE_DIR}/analyze_dphi_sliced"
ANALYZER="${ANALYZER:-${ANALYZER_BIN_DEFAULT}}"
[[ -x "${ANALYZER}" ]] || die "Analyzer binary not found or not executable: ${ANALYZER} (BASE_DIR=${BASE_DIR})."

# ------------------ modules ------------------
module purge
module load gnu7/7.3.0 mpich/3.2.1
module load python/3.8 cmake/3.12.4 root/6.28.10
module load pythia/8.303 fastjet/3.4.0

# ------------------ args/env ------------------
PT_LOW="${PT_LOW:-${1:-}}"
PT_HIGH="${PT_HIGH:-${2:-}}"
TASK="${TASK_ID:-${SLURM_ARRAY_TASK_ID:-1}}"
ANALYSIS_INPUT_MODE="${AnalysisInputMode:-${ENV_ANALYSIS_INPUT_MODE:-per_task}}"
LEGACY_AN_BATCH_ID="${AN_BATCH_ID:-}"
if [[ "${ANALYSIS_INPUT_MODE}" == "bundled_hadrons" ]]; then
  AN_BATCH_ID="${AnalysisBatchID:-${ENV_AN_BATCH_ID:-${LEGACY_AN_BATCH_ID:-bundle0}}}"
else
  AN_BATCH_ID="${ENV_AN_BATCH_ID:-${LEGACY_AN_BATCH_ID:-${AnalysisBatchID:-batch0}}}"
fi

[[ -n "${PT_LOW}" && -n "${PT_HIGH}" ]] || die "Need PT_LOW and PT_HIGH (either env or first two args)."
if [[ "${ANALYSIS_INPUT_MODE}" == "bundled_hadrons" && -n "${LEGACY_AN_BATCH_ID}" && -n "${AnalysisBatchID:-}" && "${LEGACY_AN_BATCH_ID}" != "${AnalysisBatchID}" ]]; then
  log "[WARN] legacy AN_BATCH_ID=${LEGACY_AN_BATCH_ID} conflicts with AnalysisBatchID=${AnalysisBatchID}; bundled_hadrons uses effective AN_BATCH_ID=${AN_BATCH_ID}."
fi

ANALYSIS_BUNDLE_MODE="${ANALYSIS_BUNDLE_MODE:-0}"
if [[ "${ANALYSIS_INPUT_MODE}" == "bundled_hadrons" ]]; then
  ANALYSIS_BUNDLE_MODE=1
fi

if [[ "${ANALYSIS_BUNDLE_MODE}" == "1" ]]; then
  BUNDLE_ID="${BUNDLE_ID:-${TASK_ID:-}}"
  TASK_START="${TASK_START:-}"
  TASK_END="${TASK_END:-}"
  [[ -n "${BUNDLE_ID}" && "${BUNDLE_ID}" =~ ^[0-9]+$ && ${BUNDLE_ID} -gt 0 ]] || die "Bundle mode requires numeric BUNDLE_ID>0"
  [[ -n "${TASK_START}" && "${TASK_START}" =~ ^[0-9]+$ && ${TASK_START} -gt 0 ]] || die "Bundle mode requires numeric TASK_START>0"
  [[ -n "${TASK_END}" && "${TASK_END}" =~ ^[0-9]+$ && ${TASK_END} -ge ${TASK_START} ]] || die "Bundle mode requires numeric TASK_END>=TASK_START"
  TASK="${BUNDLE_ID}"
  BUNDLE_PAD="$(printf '%06d' "${BUNDLE_ID}")"
  SLICE_TAG="${RUN_TAG}_${PT_LOW}_${PT_HIGH}_bundle${BUNDLE_PAD}"
  BUNDLE_TASK_COUNT=$(( TASK_END - TASK_START + 1 ))
  BUNDLE_EXPECTED_EVENTS="${BUNDLE_EXPECTED_EVENTS:-$(( BUNDLE_TASK_COUNT * NUM_EVENTS ))}"
  export ANALYSIS_BUNDLE_MODE BUNDLE_ID TASK_START TASK_END BUNDLE_TASK_COUNT BUNDLE_EXPECTED_EVENTS
else
  [[ -n "${TASK}" && "${TASK}" =~ ^[0-9]+$ && ${TASK} -gt 0 ]] || die "Single-task mode requires numeric TASK_ID/SLURM_ARRAY_TASK_ID>0"
  SLICE_TAG="${RUN_TAG}_${PT_LOW}_${PT_HIGH}_${TASK}"
fi

# ------------------ locate sim output ------------------
SIM_SLICE_DIR="${DIR_SIM}/${PT_LOW}-${PT_HIGH}"
SUBDIR_FILE="${DIR_LOG_SIM}/subdir_sim_${PT_LOW}_${PT_HIGH}.txt"

SIM_SUBDIR=""
SIM_SELECTION_MODE=""
if [[ -s "${SUBDIR_FILE}" ]]; then
  sim_subdir_name="$(tr -d '[:space:]' < "${SUBDIR_FILE}")"
  if [[ -n "${sim_subdir_name}" && -d "${SIM_SLICE_DIR}/${sim_subdir_name}" ]]; then
    SIM_SUBDIR="${SIM_SLICE_DIR}/${sim_subdir_name}"
    SIM_SELECTION_MODE="jid_file"
  fi
fi

[[ -n "${SIM_SUBDIR}" && -d "${SIM_SUBDIR}" ]] || die "Could not locate sim subdir for slice ${PT_LOW}-${PT_HIGH} under ${SIM_SLICE_DIR}. Refusing to guess via newest-directory fallback; fix subdir_sim_${PT_LOW}_${PT_HIGH}.txt or rerun sim submission cleanly."

SIM_SUBDIR_REAL="$(canon_path "${SIM_SUBDIR}")"
SIM_BATCH_ID="${SIM_SUBDIR_REAL##*/}"

OUTDIR="${DIR_ANALYSIS}/${PT_LOW}-${PT_HIGH}/${AN_BATCH_ID}"
mkdir -p "${OUTDIR}"

if [[ "${ANALYSIS_BUNDLE_MODE}" == "1" ]]; then
  TMP_BUNDLE_DIR="${TMPDIR:-${OUTDIR}/tmp_bundles}"
  mkdir -p "${TMP_BUNDLE_DIR}"
  BUNDLE_FILE="${TMP_BUNDLE_DIR}/hadron_bundle_${SLICE_TAG}.dat"
  BUNDLE_MANIFEST="${OUTDIR}/hadron_bundle_${SLICE_TAG}.manifest"
  : > "${BUNDLE_FILE}"
  {
    echo "# hadron bundle manifest"
    echo "run_tag=${RUN_TAG}"
    echo "slice=${PT_LOW}-${PT_HIGH}"
    echo "bundle_id=${BUNDLE_ID}"
    echo "task_start=${TASK_START}"
    echo "task_end=${TASK_END}"
    echo "task_count=${BUNDLE_TASK_COUNT}"
    echo "expected_events=${BUNDLE_EXPECTED_EVENTS}"
    echo "sim_run_dir=${SIM_SUBDIR_REAL}"
    echo "created=$(date +'%F %T')"
    echo "source_hadron_files:"
  } > "${BUNDLE_MANIFEST}"

  bundle_events_found=0
  for src_task in $(seq "${TASK_START}" "${TASK_END}"); do
    src_file="${SIM_SUBDIR}/job${src_task}_final_state_hadrons.dat"
    [[ -s "${src_file}" ]] || die "Bundle ${BUNDLE_ID} missing source hadron file for task ${src_task}: ${src_file}"

    inspect_bundle_source="$(python3 - "${src_file}" "${NUM_EVENTS}" <<'PYINSPECT'
import re, sys
path = sys.argv[1]
try:
    expected = int(sys.argv[2])
except Exception:
    expected = 1
header_re = re.compile(r'^(?:\s*#\s*Event\b|\s*Event\b)', re.IGNORECASE)
num_re = re.compile(r'^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$')
header_count = 0
particle_lines = 0
has_sigma_gen = False
has_sigma_err = False
with open(path, 'r', errors='ignore') as fh:
    for raw in fh:
        line = raw.strip()
        if not line:
            continue
        if header_re.search(line):
            header_count += 1
        if 'sigmaGen' in line:
            has_sigma_gen = True
        if 'sigmaErr' in line:
            has_sigma_err = True
        if line.startswith('#'):
            continue
        parts = line.split()
        if len(parts) >= 7 and all(num_re.match(x) for x in parts[:7]):
            particle_lines += 1
inject = 0
if header_count > 0:
    event_count = header_count
elif expected == 1 and particle_lines > 0 and has_sigma_gen and has_sigma_err:
    event_count = 1
    inject = 1
else:
    event_count = 0
print(f"{event_count}	{header_count}	{particle_lines}	{int(has_sigma_gen)}	{int(has_sigma_err)}	{inject}")
PYINSPECT
)"
    IFS=$'	' read -r ev_count header_count particle_lines has_sigma_gen has_sigma_err inject_header <<< "${inspect_bundle_source}"
    if [[ ! "${ev_count}" =~ ^[0-9]+$ ]] || (( ev_count != NUM_EVENTS )); then
      die "Bundle ${BUNDLE_ID} source task ${src_task} detected events=${ev_count:-NA}, headers=${header_count:-NA}, particle_lines=${particle_lines:-NA}, expected NUM_EVENTS=${NUM_EVENTS}: ${src_file}"
    fi
    if [[ "${has_sigma_gen}" != "1" || "${has_sigma_err}" != "1" ]]; then
      die "Bundle ${BUNDLE_ID} source task ${src_task} missing sigma footer: sigmaGen=${has_sigma_gen:-NA} sigmaErr=${has_sigma_err:-NA}: ${src_file}"
    fi
    echo "${src_task} ${src_file} events=${ev_count} headers=${header_count} synthetic_event_separator=${inject_header}" >> "${BUNDLE_MANIFEST}"
    if [[ "${inject_header}" == "1" ]]; then
      printf '# Event %s synthetic_bundle_separator task=%s bundle=%s\n' "${src_task}" "${src_task}" "${BUNDLE_ID}" >> "${BUNDLE_FILE}"
    fi
    cat "${src_file}" >> "${BUNDLE_FILE}"
    printf '\n' >> "${BUNDLE_FILE}"
    bundle_events_found=$((bundle_events_found + ev_count))
  done
  if (( bundle_events_found != BUNDLE_EXPECTED_EVENTS )); then
    die "Bundle ${BUNDLE_ID} built ${bundle_events_found} events, expected ${BUNDLE_EXPECTED_EVENTS}"
  fi
  HADRON_FILE="${BUNDLE_FILE}"
  BUNDLE_MANIFEST_REAL="$(canon_path "${BUNDLE_MANIFEST}")"
  HADRON_FILE_REAL="${BUNDLE_MANIFEST_REAL}"
  export BUNDLE_MANIFEST_REAL
  log "[bundle] built ${BUNDLE_FILE} from tasks ${TASK_START}-${TASK_END}; events=${bundle_events_found}; manifest=${BUNDLE_MANIFEST_REAL}"
else
  HADRON_FILE="${SIM_SUBDIR}/job${TASK}_final_state_hadrons.dat"
  [[ -s "${HADRON_FILE}" ]] || die "Missing hadron file: ${HADRON_FILE}"
  HADRON_FILE_REAL="$(canon_path "${HADRON_FILE}")"
fi

# ------------------ helpers ------------------
# Count COMPLETE sim tasks via per-job meta JSONs.
# A task is considered complete if:
#   meta.status == "ok" AND meta.events_written == NUM_EVENTS
# Used only as a fallback when sim_manifest.json is missing.
count_complete_tasks_from_meta() {
  local d="$1"
  local target_events="$2"
  local meta_dir="${d%/}/meta"

  if [[ ! -d "${meta_dir}" ]]; then
    echo ""
    return 0
  fi

  # Output: ok total badjson nonok
  python3 - <<'PY' "${meta_dir}" "${target_events}"
import json, os, sys

meta_dir = sys.argv[1]
try:
    target = int(sys.argv[2])
except Exception:
    target = None

ok = 0
total = 0
badjson = 0
nonok = 0

try:
    it = os.scandir(meta_dir)
except Exception:
    print("", end="")
    sys.exit(0)

for ent in it:
    if not ent.is_file():
        continue
    name = ent.name
    if not (name.startswith("job") and name.endswith(".json")):
        continue
    total += 1
    try:
        with open(ent.path, "r") as f:
            d = json.load(f)
    except Exception:
        badjson += 1
        continue

    st = str(d.get("status","")).strip().lower()
    ew = d.get("events_written", None)
    try:
        ew = int(str(ew).strip()) if ew is not None and str(ew).strip() != "" else None
    except Exception:
        ew = None

    if st == "ok" and target is not None and ew == target:
        ok += 1
    else:
        nonok += 1

print(f"{ok} {total} {badjson} {nonok}", end="")
PY
}

# Build one fallback slice-level sigmaGen_mb from all available strict-good sources in this slice.
# Source priority is per-task meta first (strict complete-task requirement), then hadron ASCII for tasks
# that do not already have a good meta sigma. Hadron fallback is also strict: require NUM_EVENTS event
# headers and BOTH sigmaGen/sigmaErr > 0 so fallback normalization stays task-complete and analyzer-consistent.
# Output fields (tab-separated): sigmaGen_mb sigmaErr_mb mode n_meta_used n_hadron_used n_total_used skipped_meta skipped_hadron
fallback_slice_sigma_mb() {
  local d="$1"
  local target_events="$2"
  python3 - <<'PY' "${d}" "${target_events}"
import json, os, re, sys

sim_dir = sys.argv[1]
try:
    target_events = int(sys.argv[2])
except Exception:
    target_events = None

meta_dir = os.path.join(sim_dir, "meta")
job_pat = re.compile(r'^job(\d+)\.json$')
had_pat = re.compile(r'^job(\d+)_final_state_hadrons\.dat$')
pat_gen = re.compile(r'(?i)\bsigmaGen\b[^0-9+\-\.]*([+\-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+\-]?\d+)?)')
pat_err = re.compile(r'(?i)\bsigmaErr\b[^0-9+\-\.]*([+\-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+\-]?\d+)?)')
pat_evt = re.compile(r'^\s*(?:#\s*)?Event\b', re.IGNORECASE)

def norm_minus(s: str) -> str:
    return s.replace("−", "-").replace("–", "-").replace("—", "-")

def inspect_hadron_file(path: str):
    sg = None
    se = None
    n_events = 0
    try:
        with open(path, "r", errors="ignore") as fh:
            for raw in fh:
                line = norm_minus(raw)
                if pat_evt.search(line):
                    n_events += 1
                if "sigmaGen" in line or "sigmaErr" in line:
                    mg = pat_gen.search(line)
                    if mg:
                        try:
                            sg = float(mg.group(1))
                        except Exception:
                            sg = None
                    me = pat_err.search(line)
                    if me:
                        try:
                            se = float(me.group(1))
                        except Exception:
                            se = None
    except Exception:
        return None, None, None
    return sg, se, n_events

used = {}
used_err = {}
meta_used = 0
had_used = 0
skipped_meta = 0
skipped_hadron = 0

if os.path.isdir(meta_dir):
    for ent in sorted(os.scandir(meta_dir), key=lambda e: e.name):
        if not ent.is_file():
            continue
        m = job_pat.match(ent.name)
        if not m:
            continue
        task_id = int(m.group(1))
        try:
            with open(ent.path, "r") as f:
                d = json.load(f)
        except Exception:
            skipped_meta += 1
            continue
        st = str(d.get("status", "")).strip().lower()
        ew = d.get("events_written", None)
        try:
            ew = int(str(ew).strip()) if ew is not None and str(ew).strip() != "" else None
        except Exception:
            ew = None
        try:
            sg = float(d.get("sigmaGen_mb", ""))
            se = float(d.get("sigmaErr_mb", ""))
        except Exception:
            sg = None
            se = None
        if st == "ok" and target_events is not None and ew == target_events and sg is not None and se is not None and sg > 0.0 and se > 0.0:
            used[task_id] = sg
            used_err[task_id] = se
            meta_used += 1
        else:
            skipped_meta += 1

for ent in sorted(os.scandir(sim_dir), key=lambda e: e.name):
    if not ent.is_file():
        continue
    m = had_pat.match(ent.name)
    if not m:
        continue
    try:
        if ent.stat().st_size <= 0:
            skipped_hadron += 1
            continue
    except Exception:
        skipped_hadron += 1
        continue
    task_id = int(m.group(1))
    if task_id in used:
        continue
    sg, se, n_events = inspect_hadron_file(ent.path)
    if (
        target_events is not None and n_events == target_events and
        sg is not None and sg > 0.0 and
        se is not None and se > 0.0
    ):
        used[task_id] = sg
        used_err[task_id] = se
        had_used += 1
    else:
        skipped_hadron += 1

if used:
    vals = [used[k] for k in sorted(used)]
    errs = [used_err[k] for k in sorted(used_err)]
    sigma = sum(vals) / len(vals)
    sigma_err = (sum(e*e for e in errs) ** 0.5) / len(errs)
    mode = "meta+hadron" if (meta_used > 0 and had_used > 0) else ("meta" if meta_used > 0 else "hadron")
    total_used = len(vals)
    print(f"{sigma:.16g}    {sigma_err:.16g}    {mode}  {meta_used} {had_used}  {total_used}    {skipped_meta}  {skipped_hadron}", end="")
else:
    print(f"        none    0   0   0   {skipped_meta}  {skipped_hadron}", end="")
PY
}
expected_tasks_from_ini() {
  # Determine expected number of tasks for a slice from jetscape.ini arrays.
  # Returns empty if arrays are missing or the slice is not found.
  local lo="$1"
  local hi="$2"
  local mult="${MULT}"

  # Arrays are expected to exist in jetscape.ini for sliced workflows.
  if ! declare -p PT_LO >/dev/null 2>&1 || ! declare -p PT_HI >/dev/null 2>&1 || ! declare -p JOBS >/dev/null 2>&1; then
    echo ""
    return 0
  fi

  local i
  for i in "${!PT_LO[@]}"; do
    if [[ "${PT_LO[$i]}" == "${lo}" && "${PT_HI[$i]}" == "${hi}" ]]; then
      if [[ "${JOBS[$i]}" =~ ^[0-9]+$ ]] && (( JOBS[$i] > 0 )); then
        echo $(( JOBS[$i] * mult ))
        return 0
      fi
    fi
  done
  echo ""
  return 0
}

SIM_MANIFEST="${SIM_SUBDIR}/sim_manifest.json"
SIM_MANIFEST_REAL="$(canon_path "${SIM_MANIFEST}")"

# Strict manifest getter:
#  - If manifest exists but JSON is unreadable => hard fail.
#  - If key is missing => empty output, success.
manifest_get() {
  local key="$1"
  local out rc
  set +e
  out="$(python3 - <<'PY2' "${SIM_MANIFEST}" "${key}"
import json, sys
p, k = sys.argv[1], sys.argv[2]
try:
    with open(p, 'r') as f:
        d = json.load(f)
except Exception as e:
    sys.stderr.write(f"[manifest][ERROR] Failed to parse {p}: {e}\n")
    sys.exit(2)

v = d.get(k, None)
if v is None:
    sys.exit(0)

if isinstance(v, (int, float, str)):
    print(v)
    sys.exit(0)

sys.stderr.write(f"[manifest][ERROR] Key '{k}' has unsupported type: {type(v)}\n")
sys.exit(3)
PY2
)"
  rc=$?
  set -e

  if (( rc == 0 )); then
    echo "${out}"
    return 0
  fi
  die "Manifest exists but is unreadable/invalid (rc=${rc}, key=${key}): ${SIM_MANIFEST}"
}

# ------------------ weight handling ------------------
# New behavior (single straight road):
#   1) Prefer per-slice SIM MANIFEST: ${SIM_SUBDIR}/sim_manifest.json
#   2) If no manifest, fall back to ONE slice-level sigmaGen built from good meta/hadron sources plus a robust denominator.

# Deterministic weight file for this task (kept for debugging)
# NOTE: must live in OUTDIR so the job can always write it.
if [[ "${ANALYSIS_BUNDLE_MODE}" == "1" ]]; then
  WEIGHT_USE="${OUTDIR}/weight_bundle${BUNDLE_PAD}.txt"
else
  WEIGHT_USE="${OUTDIR}/weight_task${TASK}.txt"
fi
WEIGHT_SRC=""
NORM_WEIGHT_VALUE=""
NORM_SIGMA_MB_USED=""
NORM_SIGMA_ERR_MB_USED=""
NORM_DENOM_EVENTS_USED=""
NORM_POLICY=""
NORM_DENOM_SOURCE=""
NORM_SIGMA_SOURCE=""

# 1) Manifest path (policy depends on ENABLE_RENORM)
if [[ -s "${SIM_MANIFEST}" ]]; then
  # Common keys (used for logging and fallbacks)
  XS_MAN="$(manifest_get sigmaGen_mb)"
  XE_MAN="$(manifest_get sigmaErr_mb)"
  EV_MAN="$(manifest_get events_total)"
  JP_MAN="$(manifest_get jobs_present)"
  JC_MAN="$(manifest_get jobs_complete)"
  JE_MAN="$(manifest_get jobs_expected)"
  NE_T_MAN="$(manifest_get num_events_target)"
  EV_EXP_MAN="$(manifest_get events_expected)"

  if (( ENABLE_RENORM == 1 )); then
    # Present-only normalization (old behavior): prefer manifest weight_mb_per_event, else sigmaGen/events_total.
    W_MAN="$(manifest_get weight_mb_per_event)"
    log "[manifest] found: ${SIM_MANIFEST}  jobs_present=${JP_MAN:-NA} jobs_complete=${JC_MAN:-NA}  events_total=${EV_MAN:-NA}  sigmaGen_mb=${XS_MAN:-NA}  weight_mb_per_event=${W_MAN:-NA}  (ENABLE_RENORM=1)"

    if [[ -n "${W_MAN:-}" && "${W_MAN}" != "None" && "${W_MAN}" != "null" ]]; then
      awk -v w="${W_MAN}" 'BEGIN{printf "%.12e\n", w}' > "${WEIGHT_USE}"
      WEIGHT_SRC="manifest(weight_mb_per_event)"
    elif [[ -n "${XS_MAN:-}" && -n "${EV_MAN:-}" && "${EV_MAN}" =~ ^[0-9]+$ && "${EV_MAN}" -gt 0 ]]; then
      awk -v xs="${XS_MAN}" -v den="${EV_MAN}" 'BEGIN{printf "%.12e\n", xs/den}' > "${WEIGHT_USE}"
      WEIGHT_SRC="manifest(sigmaGen/events_total)"
    else
      die "sim_manifest.json present but missing usable weight_mb_per_event and sigmaGen/events_total (ENABLE_RENORM=1). File: ${SIM_MANIFEST}"
    fi

    NORM_POLICY="present_denominator"
    NORM_SIGMA_SOURCE="manifest.sigmaGen_mb"
    NORM_DENOM_SOURCE="manifest.events_total"
    NORM_DENOM_EVENTS_USED="${EV_MAN:-}"
    NORM_SIGMA_MB_USED="${XS_MAN:-}"
    NORM_SIGMA_ERR_MB_USED="${XE_MAN:-}"
  else
    # Strict expected-denominator normalization:
    # Prefer manifest weight_mb_per_event_expected, else sigmaGen/events_expected, else compute expected from manifest keys,
    # then fall back to jetscape.ini arrays (JOBS*Multiplier).
    W_EXP="$(manifest_get weight_mb_per_event_expected)"
    log "[manifest] found: ${SIM_MANIFEST}  jobs_expected=${JE_MAN:-NA} jobs_complete=${JC_MAN:-NA}  events_expected=${EV_EXP_MAN:-NA} events_total=${EV_MAN:-NA}  sigmaGen_mb=${XS_MAN:-NA}  weight_mb_per_event_expected=${W_EXP:-NA}  (ENABLE_RENORM=0)"

    denom_expected=""

    if [[ -n "${EV_EXP_MAN:-}" && "${EV_EXP_MAN}" =~ ^[0-9]+$ && "${EV_EXP_MAN}" -gt 0 ]]; then
      denom_expected="${EV_EXP_MAN}"
    elif [[ -n "${JE_MAN:-}" && "${JE_MAN}" =~ ^[0-9]+$ && "${JE_MAN}" -gt 0 && -n "${NE_T_MAN:-}" && "${NE_T_MAN}" =~ ^[0-9]+$ && "${NE_T_MAN}" -gt 0 ]]; then
      denom_expected=$(( JE_MAN * NE_T_MAN ))
    else
      NJ_EXPECTED="$(expected_tasks_from_ini "${PT_LOW}" "${PT_HIGH}")"
      if [[ -n "${NJ_EXPECTED}" && "${NJ_EXPECTED}" =~ ^[0-9]+$ && "${NJ_EXPECTED}" -gt 0 ]]; then
        denom_expected=$(( NUM_EVENTS * NJ_EXPECTED ))
        log "[weight] strict: computed events_expected from jetscape.ini arrays -> NJ_EXPECTED=${NJ_EXPECTED} denom_expected=${denom_expected}"
      fi
    fi

    if [[ -n "${W_EXP:-}" && "${W_EXP}" != "None" && "${W_EXP}" != "null" ]]; then
      awk -v w="${W_EXP}" 'BEGIN{printf "%.12e\n", w}' > "${WEIGHT_USE}"
      WEIGHT_SRC="manifest(weight_mb_per_event_expected)"
    elif [[ -n "${XS_MAN:-}" && -n "${denom_expected:-}" && "${denom_expected}" =~ ^[0-9]+$ && "${denom_expected}" -gt 0 ]]; then
      awk -v xs="${XS_MAN}" -v den="${denom_expected}" 'BEGIN{printf "%.12e\n", xs/den}' > "${WEIGHT_USE}"
      WEIGHT_SRC="manifest(sigmaGen/events_expected)"
    else
      die "sim_manifest.json present but missing usable expected-denominator weight (ENABLE_RENORM=0). Need weight_mb_per_event_expected or sigmaGen_mb with events_expected/jobs_expected*num_events_target. File: ${SIM_MANIFEST}"
    fi

    NORM_POLICY="expected_denominator"
    NORM_SIGMA_SOURCE="manifest.sigmaGen_mb"
    NORM_DENOM_EVENTS_USED="${denom_expected:-}"
    NORM_SIGMA_MB_USED="${XS_MAN:-}"
    NORM_SIGMA_ERR_MB_USED="${XE_MAN:-}"
    if [[ -n "${EV_EXP_MAN:-}" && "${EV_EXP_MAN}" =~ ^[0-9]+$ && "${EV_EXP_MAN}" -gt 0 ]]; then
      NORM_DENOM_SOURCE="manifest.events_expected"
    elif [[ -n "${JE_MAN:-}" && "${JE_MAN}" =~ ^[0-9]+$ && "${JE_MAN}" -gt 0 && -n "${NE_T_MAN:-}" && "${NE_T_MAN}" =~ ^[0-9]+$ && "${NE_T_MAN}" -gt 0 ]]; then
      NORM_DENOM_SOURCE="manifest.jobs_expected*num_events_target"
    else
      NORM_DENOM_SOURCE="jetscape.ini.NUM_EVENTS*NJ_EXPECTED"
    fi
  fi
fi

# 2) Compute a common slice-level fallback sigma when the manifest path is unavailable.
if [[ -z "${WEIGHT_SRC}" ]]; then
  denom_events=""
  denom_desc=""

  META_COUNTS="$(count_complete_tasks_from_meta "${SIM_SUBDIR}" "${NUM_EVENTS}")"
  if [[ -n "${META_COUNTS}" ]]; then
    read -r NJ_OK NJ_TOTAL NJ_BADJSON NJ_NONOK <<< "${META_COUNTS}"
    log "[weight] manifest missing -> meta scan: ok=${NJ_OK:-0} total=${NJ_TOTAL:-0} badjson=${NJ_BADJSON:-0} nonok=${NJ_NONOK:-0}  (dir=${SIM_SUBDIR}/meta)"
  else
    log "[weight] manifest missing -> meta directory unavailable for ${SIM_SUBDIR}/meta"
  fi

  IFS=$'    ' read -r sigmaGen_mb sigmaErr_mb sigma_mode sigma_n_meta sigma_n_hadron sigma_n_total sigma_skipped_meta sigma_skipped_hadron <<< "$(fallback_slice_sigma_mb "${SIM_SUBDIR}" "${NUM_EVENTS}")"
  [[ -n "${sigmaGen_mb}" ]] || die "Could not derive fallback slice sigmaGen_mb from strict-good meta/hadron sources in ${SIM_SUBDIR}"
  [[ -n "${sigmaErr_mb}" ]] || die "Could not derive fallback slice sigmaErr_mb from strict-good meta/hadron sources in ${SIM_SUBDIR}"
  log "[weight] fallback sigma: sigmaGen_mb=${sigmaGen_mb} sigmaErr_mb=${sigmaErr_mb} mode=${sigma_mode} n_meta=${sigma_n_meta} n_hadron=${sigma_n_hadron} n_total=${sigma_n_total} skipped_meta=${sigma_skipped_meta} skipped_hadron=${sigma_skipped_hadron}"

  # If manifest exists but did not provide a direct weight, still trust its event denominator.
  if [[ -s "${SIM_MANIFEST}" ]]; then
    EV_MAN="$(manifest_get events_total)"
    if [[ -n "${EV_MAN:-}" && "${EV_MAN}" =~ ^[0-9]+$ && "${EV_MAN}" -gt 0 ]]; then
      denom_events="${EV_MAN}"
      denom_desc="events_total_from_manifest=${EV_MAN}"
    else
      die "sim_manifest.json present but invalid events_total; cannot use it as denominator: ${SIM_MANIFEST}"
    fi
  fi

  # Policy: if ENABLE_RENORM=0, use expected denominator (do NOT paper-over missing tasks).
  if [[ -z "${denom_events}" && "${ENABLE_RENORM}" -eq 0 ]]; then
    NJ_EXPECTED="$(expected_tasks_from_ini "${PT_LOW}" "${PT_HIGH}")"
    if [[ -n "${NJ_EXPECTED}" && "${NJ_EXPECTED}" =~ ^[0-9]+$ && "${NJ_EXPECTED}" -gt 0 ]]; then
      denom_events=$(( NUM_EVENTS * NJ_EXPECTED ))
      denom_desc="NUM_EVENTS*NJ_EXPECTED=${NJ_EXPECTED} (strict)"
      log "[weight] manifest missing + ENABLE_RENORM=0 -> strict expected denom uses NJ_EXPECTED=${NJ_EXPECTED}"
    else
      die "ENABLE_RENORM=0 but cannot infer expected NJ for slice ${PT_LOW}-${PT_HIGH} from jetscape.ini arrays (PT_LO/PT_HI/JOBS, Multiplier)."
    fi
  fi

  # Policy: if ENABLE_RENORM=1 and the manifest is missing, the denominator must match the exact strict-good
  # source set used in fallback sigmaGen_mb. This keeps numerator and denominator on the same task set.
  if [[ -z "${denom_events}" ]]; then
    [[ "${sigma_n_total:-0}" =~ ^[0-9]+$ ]] || die "Fallback sigma source count is invalid: n_total=${sigma_n_total:-unset}"
    (( sigma_n_total > 0 )) || die "Fallback sigma source count is zero for ${SIM_SUBDIR}"
    denom_events=$(( NUM_EVENTS * sigma_n_total ))
    denom_desc="NUM_EVENTS*NJ_STRICT_FALLBACK=${sigma_n_total}"
  fi

  log "[weight] fallback denom: ${denom_desc} -> events=${denom_events}"
  WEIGHT_SRC="fallback_slice_sigma(${sigma_mode:-unknown})/${denom_desc}"
  if [[ "${ENABLE_RENORM}" -eq 1 ]]; then
    NORM_POLICY="present_denominator"
  else
    NORM_POLICY="expected_denominator"
  fi
  NORM_SIGMA_SOURCE="fallback_slice_sigma(${sigma_mode:-unknown})"
  NORM_DENOM_SOURCE="${denom_desc}"
  NORM_DENOM_EVENTS_USED="${denom_events}"
  NORM_SIGMA_MB_USED="${sigmaGen_mb}"
  NORM_SIGMA_ERR_MB_USED="${sigmaErr_mb}"
  awk -v xs="${sigmaGen_mb}" -v den="${denom_events}" 'BEGIN{printf "%.12e\n", xs/den}' > "${WEIGHT_USE}"
fi
NORM_WEIGHT_VALUE="$(<"${WEIGHT_USE}")"
[[ -n "${NORM_POLICY}" ]] || die "Internal error: normalization policy was not recorded for ${SLICE_TAG}"
[[ -n "${NORM_DENOM_SOURCE}" ]] || die "Internal error: normalization denominator source was not recorded for ${SLICE_TAG}"
[[ -n "${NORM_SIGMA_SOURCE}" ]] || die "Internal error: normalization sigma source was not recorded for ${SLICE_TAG}"
[[ -n "${NORM_DENOM_EVENTS_USED}" ]] || die "Internal error: normalization denominator value was not recorded for ${SLICE_TAG}"
[[ -n "${NORM_SIGMA_MB_USED}" ]] || die "Internal error: normalization sigmaGen value was not recorded for ${SLICE_TAG}"
[[ -n "${NORM_SIGMA_ERR_MB_USED}" ]] || die "Internal error: normalization sigmaErr value was not recorded for ${SLICE_TAG}"
awk -v w="${NORM_WEIGHT_VALUE}" 'BEGIN{exit(!(w==w && w>0))}' || die "Invalid canonical weight_mb_per_event=${NORM_WEIGHT_VALUE} for ${SLICE_TAG}"
awk -v xs="${NORM_SIGMA_MB_USED}" 'BEGIN{exit(!(xs==xs && xs>0))}' || die "Invalid canonical sigmaGen_mb=${NORM_SIGMA_MB_USED} for ${SLICE_TAG}"
awk -v xe="${NORM_SIGMA_ERR_MB_USED}" 'BEGIN{exit(!(xe==xe && xe>0))}' || die "Invalid canonical sigmaErr_mb=${NORM_SIGMA_ERR_MB_USED} for ${SLICE_TAG}"
[[ "${NORM_DENOM_EVENTS_USED}" =~ ^[0-9]+$ ]] || die "Invalid canonical denominator events value=${NORM_DENOM_EVENTS_USED} for ${SLICE_TAG}"
(( NORM_DENOM_EVENTS_USED > 0 )) || die "Canonical denominator events must be > 0 for ${SLICE_TAG} (got ${NORM_DENOM_EVENTS_USED})"
awk -v w="${NORM_WEIGHT_VALUE}" -v xs="${NORM_SIGMA_MB_USED}" -v den="${NORM_DENOM_EVENTS_USED}" 'BEGIN{target=xs/den; diff=w-target; if(diff<0) diff=-diff; tol=1e-12*(1.0 + (target<0?-target:target)); exit(!(diff<=tol))}' || die "Canonical weight/sigma/denominator mismatch for ${SLICE_TAG}: weight=${NORM_WEIGHT_VALUE} sigmaGen_mb=${NORM_SIGMA_MB_USED} denom=${NORM_DENOM_EVENTS_USED}"
log "[weight] source=${WEIGHT_SRC}  policy=${NORM_POLICY}  sigma_source=${NORM_SIGMA_SOURCE}  denom_source=${NORM_DENOM_SOURCE}  weight_file=${WEIGHT_USE}  value=${NORM_WEIGHT_VALUE}  sigmaGen_mb=${NORM_SIGMA_MB_USED}  sigmaErr_mb=${NORM_SIGMA_ERR_MB_USED}  denom_events=${NORM_DENOM_EVENTS_USED}"

# ------------------ run analyzer ------------------
ROOT_OUT="dphi_${SLICE_TAG}.root"
JSON_OUT="slice_meta_${SLICE_TAG}.json"

log "[cfg] BASE_DIR=${BASE_DIR}"
log "[cfg] INI=${INI_PATH}"
log "[cfg] RUN_DIR=${RUN_DIR}"
log "[cfg] DIR_SIM=${DIR_SIM}"
log "[cfg] DIR_ANALYSIS=${DIR_ANALYSIS}"
log "[cfg] AN_BATCH_ID=${AN_BATCH_ID}"
log "[cfg] OUTDIR=${OUTDIR}"
log "[cfg] sim_run_dir=${SIM_SUBDIR_REAL} sim_batch_id=${SIM_BATCH_ID} sim_selection_mode=${SIM_SELECTION_MODE:-unknown}"
log "[run] analyzer_input=${HADRON_FILE} provenance_hadron=${HADRON_FILE_REAL} weight=${WEIGHT_USE} tag=${SLICE_TAG}"

cd "${OUTDIR}"

srun --cpu-bind=none "${ANALYZER}" \
     "${HADRON_FILE}" \
     "${WEIGHT_USE}" \
     "${INI_PATH}" \
     "${SLICE_TAG}"

if [[ ! -s "${OUTDIR}/${ROOT_OUT}" && -s "${ROOT_OUT}" ]]; then
  mv -f "${ROOT_OUT}" "${OUTDIR}/" || true
fi
if [[ ! -s "${OUTDIR}/${JSON_OUT}" && -s "${JSON_OUT}" ]]; then
  mv -f "${JSON_OUT}" "${OUTDIR}/" || true
fi

[[ -s "${OUTDIR}/${ROOT_OUT}" ]] || die "ROOT output missing in OUTDIR after run: ${OUTDIR}/${ROOT_OUT}"
[[ -s "${OUTDIR}/${JSON_OUT}" ]] || die "JSON sidecar missing in OUTDIR after run: ${OUTDIR}/${JSON_OUT}"

augment_analysis_meta_with_provenance \
  "${OUTDIR}/${JSON_OUT}" \
  "${SIM_SUBDIR_REAL}" \
  "${HADRON_FILE_REAL}" \
  "${SIM_BATCH_ID}" \
  "${SIM_MANIFEST_REAL}" \
  "${SIM_SELECTION_MODE:-unknown}" \
  "${NORM_WEIGHT_VALUE}" \
  "${NORM_SIGMA_MB_USED}" \
  "${NORM_SIGMA_ERR_MB_USED}" \
  "${NORM_DENOM_EVENTS_USED}" \
  "${WEIGHT_SRC}" \
  "${NORM_POLICY}" \
  "${NORM_DENOM_SOURCE}" \
  "${NORM_SIGMA_SOURCE}" \
  "${ENABLE_RENORM}"
log "[meta] Added sim + normalization provenance to ${OUTDIR}/${JSON_OUT}: sim_run_dir=${SIM_SUBDIR_REAL} hadron_file=${HADRON_FILE_REAL} sim_batch_id=${SIM_BATCH_ID} sim_selection_mode=${SIM_SELECTION_MODE:-unknown} norm_source=${WEIGHT_SRC} norm_policy=${NORM_POLICY} norm_sigma_source=${NORM_SIGMA_SOURCE} norm_denom_source=${NORM_DENOM_SOURCE}"

if [[ "${ANALYSIS_BUNDLE_MODE}" == "1" ]]; then
  bundle_meta_events="$(python3 - <<'PYBUNDLECHECK_EVENTS' "${OUTDIR}/${JSON_OUT}"
import json, sys
try:
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        print(json.load(f).get('events_seen', ''))
except Exception:
    print('')
PYBUNDLECHECK_EVENTS
)"
  bundle_meta_root_status="$(python3 - <<'PYBUNDLECHECK_ROOT' "${OUTDIR}/${JSON_OUT}"
import json, sys
try:
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        print(json.load(f).get('root_status', ''))
except Exception:
    print('')
PYBUNDLECHECK_ROOT
)"
  log "[bundle-check] events_seen=${bundle_meta_events:-NA} expected=${BUNDLE_EXPECTED_EVENTS} root_status=${bundle_meta_root_status:-NA}"
  [[ "${bundle_meta_root_status}" == "ok" ]] || die "Bundle ${BUNDLE_ID} root_status=${bundle_meta_root_status:-NA}, expected ok"
  [[ "${bundle_meta_events}" =~ ^[0-9]+$ && "${bundle_meta_events}" -eq "${BUNDLE_EXPECTED_EVENTS}" ]] || die "Bundle ${BUNDLE_ID} events_seen=${bundle_meta_events:-NA}, expected ${BUNDLE_EXPECTED_EVENTS}. Refusing to publish bad bundle output."
fi

log "[done] Finished analyze_dphi_sliced -> ${OUTDIR}"
