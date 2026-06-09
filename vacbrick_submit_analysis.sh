#!/usr/bin/env bash
# vacbrick_submit_analysis.sh v1.2
# CHANGELOG
# v1.2 (stop-on-failed-variant dependency chain):
#   • CHANGE: MultiSim variant manager chaining now uses Slurm afterok instead of afterany, so later variants do not start if an earlier variant manager fails.
#   • SAFETY: Per-variant directories, ini/xml generation, Slurm resources, and task math are unchanged.
# v1.1 (quoted Slurm command-array execution + resume note):
#   • FIX: Execute the constructed sbatch array as "${submit_cmd[@]}" so the --wrap command is passed as one Slurm argument instead of being split into fake script arguments.
#   • FIX: This prevents the same WSU Slurm --wrap failure in multianalysis manager submission.
#   • DOC: Clarify resume behavior: rerunning this wrapper is safe because each variant keeps the same RUN_TAG/AN_BATCH_ID and the underlying analysis manager skips completed ROOT/JSON outputs and reruns incomplete ones.
# v1.0 (wrapper for brick multianalysis fan-out):
#   • NEW: If MultiSimEnabled=0, delegate directly to submit_sliced_analysis.sh (legacy single-analysis behavior).
#   • NEW: If MultiSimEnabled=1, generate one per-variant ini matching the multisim run-tag scheme and submit the existing ANALYSIS manager jobs sequentially via Slurm dependencies.
#   • SAFETY: Each variant keeps its own RUN_TAG/RUNS_BASE/DIR_* tree, so ROOT/JSON outputs remain separated and no medium point contaminates another.
#   • LOGS: Writes a manifest with variant tags, brick lengths, qhat0 values, ini paths, and submitted manager job IDs.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"
BASE_INI="${INI_PATH:-${JETSCAPE_INI_PATH:-${SCRIPT_DIR}/jetscape.ini}}"
[[ -f "${BASE_INI}" ]] || { echo "[FATAL] jetscape.ini not found: ${BASE_INI}" >&2; exit 1; }
# shellcheck disable=SC1090
source "${BASE_INI}"

ts(){ date +"%F %T"; }
log(){ echo "[$(ts)] [vacbrick_submit_analysis] $*"; }
die(){ echo "[$(ts)] [vacbrick_submit_analysis] [FATAL] $*" >&2; exit 1; }

sanitize_tag_value(){
  local raw="$1" s
  s="$(printf '%s' "${raw}" | tr -d '[:space:]')"
  [[ -n "${s}" ]] || die "Empty value cannot be sanitized"
  s="${s//./p}"
  s="${s//-/_m_}"
  printf '%s' "${s}"
}

validate_numeric_list(){
  local name="$1"; shift
  local v
  (( $# > 0 )) || die "${name} is empty"
  for v in "$@"; do
    [[ "${v}" =~ ^[+-]?[0-9]+([.][0-9]+)?$ ]] || die "${name} contains non-numeric value: ${v}"
  done
}

if [[ -z "${MultiSimEnabled+x}" ]]; then
  die "jetscape.ini missing required key MultiSimEnabled (must be 0 or 1)."
fi
[[ "${MultiSimEnabled}" =~ ^[01]$ ]] || die "MultiSimEnabled must be 0 or 1 (got ${MultiSimEnabled})."

if [[ "${MultiSimEnabled}" == "0" ]]; then
  log "MultiSimEnabled=0 -> delegating to submit_sliced_analysis.sh with INI_PATH=${BASE_INI}"
  INI_PATH="${BASE_INI}" exec bash "${SCRIPT_DIR}/submit_sliced_analysis.sh" "$@"
fi

declare -p MultiSimBrickLengths >/dev/null 2>&1 || die "jetscape.ini missing MultiSimBrickLengths array."
declare -p MultiSimQhat0Values >/dev/null 2>&1 || die "jetscape.ini missing MultiSimQhat0Values array."
(( ${#MultiSimBrickLengths[@]} > 0 )) || die "MultiSimBrickLengths is empty."
(( ${#MultiSimQhat0Values[@]} > 0 )) || die "MultiSimQhat0Values is empty."
validate_numeric_list MultiSimBrickLengths "${MultiSimBrickLengths[@]}"
validate_numeric_list MultiSimQhat0Values "${MultiSimQhat0Values[@]}"
[[ -n "${RUN_TAG:-}" ]] || die "RUN_TAG missing in base ini."

BASE_RUNS_ROOT="${HOME}/xscape_runs/${RUN_TAG}"
GEN_ROOT="${BASE_RUNS_ROOT}/multisim_configs/analysis"
MANIFEST_DIR="${BASE_RUNS_ROOT}/multisim_manifests"
mkdir -p "${GEN_ROOT}" "${MANIFEST_DIR}"
MANIFEST="${MANIFEST_DIR}/analysis_variants.tsv"
: > "${MANIFEST}"
echo -e "variant_index\tvariant_tag\tbrick_length\tqhat0\tini_path\tmanager_jobid" > "${MANIFEST}"

MANAGER_ACCOUNT="${MANAGER_ACCOUNT:-wsu}"
MANAGER_QOS="${MANAGER_QOS:-primary}"
MANAGER_TIME="${MANAGER_TIME:-3:00:00}"
MANAGER_MEM="${MANAGER_MEM:-1G}"
MANAGER_CPUS="${MANAGER_CPUS:-1}"
MANAGER_NODES="${MANAGER_NODES:-1}"
MANAGER_NTASKS="${MANAGER_NTASKS:-1}"

prev_jid=""
variant_index=0
for brick_length in "${MultiSimBrickLengths[@]}"; do
  for qhat0 in "${MultiSimQhat0Values[@]}"; do
    variant_index=$((variant_index + 1))
    ltag="$(sanitize_tag_value "${brick_length}")"
    qtag="$(sanitize_tag_value "${qhat0}")"
    variant_tag="${RUN_TAG}_L${ltag}_q${qtag}"
    variant_root="${GEN_ROOT}/${variant_tag}"
    variant_run_root="${HOME}/xscape_runs/${variant_tag}"
    variant_manager_log_dir="${variant_run_root}/logs/manager"
    mkdir -p "${variant_root}" "${variant_manager_log_dir}"

    [[ -d "${variant_run_root}/sim" ]] || die "Expected sim directory for ${variant_tag} not found: ${variant_run_root}/sim"

    variant_ini="${variant_root}/${variant_tag}.ini"
    cp -f "${BASE_INI}" "${variant_ini}"
    cat >> "${variant_ini}" <<EOF2

# --- multianalysis wrapper overrides for ${variant_tag} ---
MultiSimEnabled=0
RUN_TAG="${variant_tag}"
RUNS_BASE="${variant_run_root}"
DIR_FINAL="${variant_run_root}/final"
DIR_SIM="${variant_run_root}/sim"
DIR_ANALYSIS="${variant_run_root}/analysis"
DIR_LOG_SIM="${variant_run_root}/logs/sim"
DIR_LOG_ANALYSIS="${variant_run_root}/logs/analysis"
EOF2

    ts_compact="$(date +%Y%m%d_%H%M%S)"
    out="${variant_manager_log_dir}/analysis_manager_${variant_tag}_${ts_compact}_%j.out"
    err="${variant_manager_log_dir}/analysis_manager_${variant_tag}_${ts_compact}_%j.err"
    submit_cmd=(
      sbatch --parsable
      --account="${MANAGER_ACCOUNT}"
      --qos="${MANAGER_QOS}"
      --nodes="${MANAGER_NODES}"
      --ntasks="${MANAGER_NTASKS}"
      --cpus-per-task="${MANAGER_CPUS}"
      --mem="${MANAGER_MEM}"
      --time="${MANAGER_TIME}"
      --job-name="xan_mgr_${variant_tag}"
      --output="${out}"
      --error="${err}"
    )
    if [[ -n "${prev_jid}" ]]; then
      submit_cmd+=(--dependency="afterok:${prev_jid}")
    fi
    submit_cmd+=(--export=ALL,INI_PATH="${variant_ini}")
    submit_cmd+=(--wrap="cd \"${SCRIPT_DIR}\" && bash ./submit_sliced_analysis.sh --_inside_manager")

    log "Submitting variant ${variant_index}: tag=${variant_tag} brick_length=${brick_length} qhat0=${qhat0}"
    sbout="$("${submit_cmd[@]}")" || die "sbatch failed for ${variant_tag}"
    jid="$(sed -nE 's/^([0-9]+)(;.*)?$/\1/p' <<< "${sbout}" | head -n 1)"
    [[ "${jid}" =~ ^[0-9]+$ ]] || die "Could not parse manager job id for ${variant_tag} from sbatch output: ${sbout}"
    prev_jid="${jid}"
    echo -e "${variant_index}\t${variant_tag}\t${brick_length}\t${qhat0}\t${variant_ini}\t${jid}" >> "${MANIFEST}"
    log "Queued ${variant_tag} as manager job ${jid}"
  done
done

log "Queued ${variant_index} multianalysis variant managers. Manifest: ${MANIFEST}"
