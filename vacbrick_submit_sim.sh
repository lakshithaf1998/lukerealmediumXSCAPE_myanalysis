#!/usr/bin/env bash
# vacbrick_submit_sim.sh v1.2
# CHANGELOG
# v1.2 (stop-on-failed-variant dependency chain):
#   • CHANGE: MultiSim variant manager chaining now uses Slurm afterok instead of afterany, so later variants do not start if an earlier variant manager fails.
#   • SAFETY: Per-variant directories, ini/xml generation, Slurm resources, and task math are unchanged.
# v1.1 (quoted Slurm command-array execution + resume note):
#   • FIX: Execute the constructed sbatch array as "${submit_cmd[@]}" so the --wrap command is passed as one Slurm argument instead of being split into fake script arguments.
#   • FIX: This directly fixes the WSU Slurm error: "Script arguments not permitted with --wrap option" during multisim manager submission.
#   • DOC: Clarify resume behavior: rerunning this wrapper is safe because each variant keeps the same RUN_TAG/SIM_BATCH_ID and the underlying sim manager skips completed tasks and repairs incomplete ones.
# v1.0 (wrapper for brick multisim fan-out):
#   • NEW: If MultiSimEnabled=0, delegate directly to submit_sliced_sim.sh (legacy single-run behavior).
#   • NEW: If MultiSimEnabled=1, generate one concrete XML + one concrete ini per (brick length, qhat0) variant,
#     assign a unique RUN_TAG and BASE_SEED to each variant, and submit the existing SIM manager jobs sequentially via Slurm dependencies.
#   • SAFETY: Uses afterok dependency chaining so only one variant manager is active at a time and the workflow stays within the 1000-job qos=primary cap.
#   • LOGS: Writes a manifest with variant tags, brick lengths, qhat0 values, ini/xml paths, and submitted manager job IDs.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"
BASE_INI="${INI_PATH:-${JETSCAPE_INI_PATH:-${SCRIPT_DIR}/jetscape.ini}}"
[[ -f "${BASE_INI}" ]] || { echo "[FATAL] jetscape.ini not found: ${BASE_INI}" >&2; exit 1; }
# shellcheck disable=SC1090
source "${BASE_INI}"

ts(){ date +"%F %T"; }
log(){ echo "[$(ts)] [vacbrick_submit_sim] $*"; }
die(){ echo "[$(ts)] [vacbrick_submit_sim] [FATAL] $*" >&2; exit 1; }

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
  log "MultiSimEnabled=0 -> delegating to submit_sliced_sim.sh with INI_PATH=${BASE_INI}"
  INI_PATH="${BASE_INI}" exec bash "${SCRIPT_DIR}/submit_sliced_sim.sh" "$@"
fi

declare -p MultiSimBrickLengths >/dev/null 2>&1 || die "jetscape.ini missing MultiSimBrickLengths array."
declare -p MultiSimQhat0Values >/dev/null 2>&1 || die "jetscape.ini missing MultiSimQhat0Values array."
(( ${#MultiSimBrickLengths[@]} > 0 )) || die "MultiSimBrickLengths is empty."
(( ${#MultiSimQhat0Values[@]} > 0 )) || die "MultiSimQhat0Values is empty."
validate_numeric_list MultiSimBrickLengths "${MultiSimBrickLengths[@]}"
validate_numeric_list MultiSimQhat0Values "${MultiSimQhat0Values[@]}"
[[ -n "${RUN_TAG:-}" ]] || die "RUN_TAG missing in base ini."
[[ -n "${XML_TEMPLATE:-}" ]] || die "XML_TEMPLATE missing in base ini."

BASE_RUNS_ROOT="${HOME}/xscape_runs/${RUN_TAG}"
GEN_ROOT="${BASE_RUNS_ROOT}/multisim_configs/sim"
MANIFEST_DIR="${BASE_RUNS_ROOT}/multisim_manifests"
mkdir -p "${GEN_ROOT}" "${MANIFEST_DIR}"
MANIFEST="${MANIFEST_DIR}/sim_variants.tsv"
: > "${MANIFEST}"
echo -e "variant_index\tvariant_tag\tbrick_length\tqhat0\tbase_seed\tini_path\txml_path\tmanager_jobid" > "${MANIFEST}"

MANAGER_ACCOUNT="${MANAGER_ACCOUNT:-wsu}"
MANAGER_QOS="${MANAGER_QOS:-primary}"
MANAGER_TIME="${MANAGER_TIME:-6:00:00}"
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

    variant_seed_base=$(( ${BASE_SEED:-1} + (variant_index-1)*100000000 ))
    xml_template_source="${SCRIPT_DIR}/config/${XML_TEMPLATE}"
    [[ -f "${xml_template_source}" ]] || die "Missing XML template for multisim rendering: ${xml_template_source}"
    variant_xml="${variant_root}/${variant_tag}.xml"
    sed -e "s|\*\*BRICK_LENGTH_PLACEHOLDER\*\*|${brick_length}|g" \
        -e "s|\*\*QHAT0_PLACEHOLDER\*\*|${qhat0}|g" \
        "${xml_template_source}" > "${variant_xml}"

    variant_ini="${variant_root}/${variant_tag}.ini"
    cp -f "${BASE_INI}" "${variant_ini}"
    cat >> "${variant_ini}" <<EOF2

# --- multisim wrapper overrides for ${variant_tag} ---
MultiSimEnabled=0
RUN_TAG="${variant_tag}"
RUNS_BASE="${variant_run_root}"
DIR_FINAL="${variant_run_root}/final"
DIR_SIM="${variant_run_root}/sim"
DIR_ANALYSIS="${variant_run_root}/analysis"
DIR_LOG_SIM="${variant_run_root}/logs/sim"
DIR_LOG_ANALYSIS="${variant_run_root}/logs/analysis"
XML_TEMPLATE="${variant_xml}"
BASE_SEED=${variant_seed_base}
EOF2

    ts_compact="$(date +%Y%m%d_%H%M%S)"
    out="${variant_manager_log_dir}/sim_manager_${variant_tag}_${ts_compact}_%j.out"
    err="${variant_manager_log_dir}/sim_manager_${variant_tag}_${ts_compact}_%j.err"
    submit_cmd=(
      sbatch --parsable
      --account="${MANAGER_ACCOUNT}"
      --qos="${MANAGER_QOS}"
      --nodes="${MANAGER_NODES}"
      --ntasks="${MANAGER_NTASKS}"
      --cpus-per-task="${MANAGER_CPUS}"
      --mem="${MANAGER_MEM}"
      --time="${MANAGER_TIME}"
      --job-name="xsim_mgr_${variant_tag}"
      --output="${out}"
      --error="${err}"
    )
    if [[ -n "${prev_jid}" ]]; then
      submit_cmd+=(--dependency="afterok:${prev_jid}")
    fi
    submit_cmd+=(--export=ALL,INI_PATH="${variant_ini}")
    submit_cmd+=(--wrap="cd \"${SCRIPT_DIR}\" && bash ./submit_sliced_sim.sh --_inside_manager")

    log "Submitting variant ${variant_index}: tag=${variant_tag} brick_length=${brick_length} qhat0=${qhat0} base_seed=${variant_seed_base}"
    sbout="$("${submit_cmd[@]}")" || die "sbatch failed for ${variant_tag}"
    jid="$(sed -nE 's/^([0-9]+)(;.*)?$/\1/p' <<< "${sbout}" | head -n 1)"
    [[ "${jid}" =~ ^[0-9]+$ ]] || die "Could not parse manager job id for ${variant_tag} from sbatch output: ${sbout}"
    prev_jid="${jid}"
    echo -e "${variant_index}\t${variant_tag}\t${brick_length}\t${qhat0}\t${variant_seed_base}\t${variant_ini}\t${variant_xml}\t${jid}" >> "${MANIFEST}"
    log "Queued ${variant_tag} as manager job ${jid}"
  done
done

log "Queued ${variant_index} multisim variant managers. Manifest: ${MANIFEST}"
