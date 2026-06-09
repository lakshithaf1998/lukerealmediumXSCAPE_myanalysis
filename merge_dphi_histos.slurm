#!/usr/bin/env bash
# merge_dphi_histos.slurm v9.9
# CHANGELOG
# v9.9 (custom ROOT histogram merger fallback; avoid stuck hadd on /counts):
#   • CHANGE: Default bundled merge engine is now MergeMergeEngine="root_macro" instead of direct ROOT hadd.
#   • FIX: Avoid the observed one-shot hadd stall at Target path /counts by merging TH1/TH2/TProfile objects with a controlled ROOT macro that logs file progress.
#   • KEEP: Final dphi_allSlices.root, per-slice ROOT, xsec summaries, selected-dijet counts, merge_status, run_manifest, bundle preflight, validation, and full merge logs.
#   • FALLBACK: Set MergeMergeEngine="hadd" to use the old direct hadd path for debugging/comparison.
#   • NO PHYSICS CHANGE: Histogram contents are added with ROOT TH1::Add, equivalent to hadd for analyzer histogram outputs.
#
# v9.8 (direct one-shot slice hadd in local TMPDIR; remove staged/heartbeat workflow):
#   • CHANGE: Remove staged hadd groups and heartbeat polling from the active workflow. Each complete pThat slice is merged with one direct hadd over all accepted bundle ROOT files.
#   • CHANGE: Temporary merge products are written under $TMPDIR when available, then copied back to final/per_slice and final/dphi_allSlices.root after validation. This keeps the published final directory clean and reduces output-write pressure on the shared filesystem.
#   • KEEP: Visible major-step logs, full hadd stdout/stderr saved under logs/merge/hadd_logs, input lists, bundle preflight, final ROOT validation, xsec summaries, selected-count summary, merge_status, and run_manifest.
#   • REMOVE: MergeHaddStaged, MergeHaddGroupSize, MergeHaddHeartbeatSec, MergeHaddPollSec, and MergeValidateStageParts are no longer used by merge v9.8.
#
# v9.7 (fast hadd polling + lean single-slice finalization):
#   • FIX: run_hadd_single_logged no longer sleeps for the full MergeHaddHeartbeatSec before noticing that a quick hadd already finished. This removed the artificial ~60s delay per staged hadd group.
#   • NEW: MergeHaddPollSec controls the lightweight polling interval used only to detect process completion; MergeHaddHeartbeatSec still controls visible heartbeat logging.
#   • NEW: MergeValidateStageParts controls optional validation of intermediate staged hadd parts. Default is 0 because final per-slice/final ROOT validation is still mandatory and intermediate validation was extra workflow.
#   • NEW: MergeFinalCopySingleSlice=1 copies the only complete slice to dphi_allSlices.root instead of running a redundant final one-input hadd. Multiple slices still use hadd.
#   • KEEP: Staged hadd, full hadd logs, input lists, preflight bundle checks, final ROOT validation, xsec summaries, selected-count summary, merge_status, and run_manifest.
#
# v9.6 (lean bundled merge workflow; keep diagnostics, remove redundant report scans):
#   • CHANGE: Stop producing merge_analysis_task_states.csv and merge_missing_analysis_outputs.csv because analysis manager already produces bundle/task status reports.
#   • CHANGE: Stop producing normalization_report.csv; keep xsec_slices.csv and xsec_summary.json for downstream normalization.
#   • CHANGE: Use the first accepted bundle meta per slice for normalization summary by default instead of re-reading norm fields from every bundle meta. Optional MergeStrictNormScan=1 restores full meta norm scanning.
#   • KEEP: Final merged ROOT, per-slice ROOT, xsec_summary.json, xsec_slices.csv, selected_dijet_counts_summary.json, merge_status.json, run_manifest.txt, staged hadd logs, heartbeat diagnostics, and ROOT validation.
#   • KEEP: Bundle preflight checks all bundle ROOT/JSON event counts before hadd, so incomplete bundle coverage is still rejected.
#
# v9.5 (staged hadd + heartbeat diagnostics):
#   • FIX: Avoid one giant 1000-input hadd call that can stall inside ROOT object merging; large input lists are now merged in staged groups controlled by MergeHaddGroupSize.
#   • FIX: Default MergeHaddEchoOutput=0 so full hadd stdout is saved to logs/merge/hadd_logs without spamming/slowing the main Slurm log.
#   • NEW: Heartbeat diagnostics during each hadd show elapsed time, output size, log size, and log line count while preserving detailed hadd logs separately.
#   • NEW: MergeHaddHeartbeatSec, MergeHaddGroupSize, and MergeHaddStaged control merge diagnostics and staging from jetscape.ini.
#   • KEEP: Verbose preflight, bundle acceptance/rejection logs, ROOT validation logs, final output names, normalization outputs, and bundle/merge physics unchanged.
#
# v9.4 (fix verbose merge helper functions + bundled batch safety):
#   • FIX: Define run_hadd_logged() and validate_root_logged() before first use; v9.3 called them without definitions and crashed after preflight.
#   • FIX: Keep full hadd stdout/stderr logs and visible Slurm log echo while preserving the real hadd exit code under pipefail.
#   • FIX: In bundled_hadrons mode, ignore stale jid_an_<slice>.txt values that disagree with the effective AnalysisBatchID/AN_BATCH_ID, update the file, and merge the intended bundle folder.
#   • FIX: Add explicit helper self-checks and output-size validation so missing helper/function or empty ROOT outputs fail with clear diagnostics.
#   • KEEP: No physics, histogram contents, normalization policy, analysis cuts, or simulation settings changed.
#
# v9.3 (full bundled-merge diagnostics):
#   • FIX: Restore OG-style visible merge progress logs for every major step: config, module setup, report initialization, slice preflight, bundle acceptance/rejection, per-slice hadd start/end, ROOT validation, publication, xsec summaries, selected-count aggregation, manifest/status writing, and cleanup.
#   • FIX: Stop hiding expensive hadd work behind /dev/null. Full hadd stdout/stderr is written to logs/merge/hadd_*.log and echoed through the Slurm log via tee so a merge no longer looks frozen.
#   • NEW: MergeVerboseBundleLogs, MergeScanLogEvery, and MergeHaddEchoOutput control diagnostic verbosity from jetscape.ini; defaults preserve verbose debugging.
#   • KEEP: No physics, histogram weighting, bundle acceptance, normalization, or final output naming changed.
#
# v9.2 (bundle0 batch precedence + safe final publish + JSONL writer fix):
#   • FIX: In bundled_hadrons mode, AnalysisBatchID overrides legacy AN_BATCH_ID so merge reads the same bundle0 folder selected by analysis.
#   • FIX: Repair selected-count JSONL writer newline so the embedded Python is valid at runtime.
#   • SAFETY: Do not remove the existing published final ROOT before the full merge preflight and temporary hadd output validate successfully.
#   • KEEP: Bundle completeness remains checked by expected event counts and total events_seen, not by one ROOT per original sim task.
#
# v9.1 (bundle merge JSON/event-count robustness):
#   • FIX: Replace broken sed JSON backreferences with Python JSON readers for events_seen/root_status/norm fields.
#   • FIX: Repair selected_dijet_counts JSONL writer so the embedded Python writes a real newline.
#   • KEEP: Bundle completeness is checked by expected event counts and total events_seen, not by one ROOT per original sim task.
# v9.0 (bundled hadron analysis merge mode):
#   • NEW: Supports AnalysisInputMode=bundled_hadrons outputs dphi_<RUN_TAG>_<L>_<H>_bundleNNNNNN.root.
#   • NEW: Completeness is checked by bundle expected event counts and total events_seen, not by one ROOT per original sim task.
#   • HISTORICAL: v9.0 published canonical dphi_allSlices.root, per_slice ROOTs, normalization_report.csv, xsec_slices.csv, xsec_summary.json, selected_dijet_counts_summary.json, merge_status.json, and run_manifest.txt; v9.6 removes redundant merge-side CSV reports.
#
#SBATCH --account=wsu
#SBATCH --job-name=merge_dphi
#SBATCH --qos=primary
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --time=02:00:00
#SBATCH --mem=16G
#SBATCH --export=ALL

set -euo pipefail

ts(){ date +'%F %T'; }
log(){ echo "[$(ts)] $*"; }
log_section(){ log "========== $* =========="; }
die(){ log "[FATAL] $*"; exit 1; }

if [[ -n "${SLURM_SUBMIT_DIR:-}" && -d "${SLURM_SUBMIT_DIR}" ]]; then
  BASE_DIR="${SLURM_SUBMIT_DIR}"
else
  BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi
cd "${BASE_DIR}"
INI_PATH="${INI_PATH:-${JETSCAPE_INI_PATH:-${BASE_DIR}/jetscape.ini}}"
[[ -f "${INI_PATH}" ]] || die "jetscape.ini not found: ${INI_PATH}"
# shellcheck disable=SC1090
source "${INI_PATH}"

log_section "module setup"
log "[module] purge"
module purge
log "[module] load gnu7/7.3.0"
module load gnu7/7.3.0
log "[module] load python/3.8 cmake/3.12.4 root/6.28.10"
module load python/3.8 cmake/3.12.4 root/6.28.10
log "[module] loaded modules:"
module -t list 2>&1 | sed "s/^/[module] /" || true
log "[tools] python=$(command -v python3 || true) root=$(command -v root || true) hadd=$(command -v hadd || true)"

RUN_TAG="${RUN_TAG:-run}"
RUN_DIR="${RUNS_BASE:-${HOME}/xscape_runs/${RUN_TAG}}"; RUN_DIR="${RUN_DIR%/}"
DIR_ANALYSIS="${DIR_ANALYSIS:-${RUN_DIR}/analysis}"
DIR_FINAL="${DIR_FINAL:-${RUN_DIR}/final}"
DIR_LOG_ANALYSIS="${DIR_LOG_ANALYSIS:-${RUN_DIR}/logs/analysis}"
DIR_LOG_MERGE="${DIR_LOG_MERGE:-${RUN_DIR}/logs/merge}"
mkdir -p "${DIR_FINAL}" "${DIR_LOG_MERGE}" "${DIR_FINAL}/per_slice"

MULT="${Multiplier-${multiplier-}}"
[[ "${MULT}" =~ ^[0-9]+$ && "${MULT}" -ge 1 ]] || die "Invalid Multiplier=${MULT}"
declare -p PT_LO >/dev/null 2>&1 || die "Missing PT_LO"
declare -p PT_HI >/dev/null 2>&1 || die "Missing PT_HI"
declare -p JOBS >/dev/null 2>&1 || die "Missing JOBS"
[[ "${NUM_EVENTS:-}" =~ ^[0-9]+$ && "${NUM_EVENTS}" -ge 1 ]] || die "Invalid NUM_EVENTS=${NUM_EVENTS:-unset}"
AnalysisInputMode="${AnalysisInputMode:-bundled_hadrons}"
LEGACY_AN_BATCH_ID="${AN_BATCH_ID:-}"
if [[ "${AnalysisInputMode}" == "bundled_hadrons" ]]; then
  AN_BATCH_ID="${AnalysisBatchID:-${LEGACY_AN_BATCH_ID:-bundle0}}"
else
  AN_BATCH_ID="${LEGACY_AN_BATCH_ID:-${AnalysisBatchID:-batch0}}"
fi
AnalysisBundleSize="${AnalysisBundleSize:-100}"
[[ "${AnalysisInputMode}" == "bundled_hadrons" ]] || die "This merge expects AnalysisInputMode=bundled_hadrons"
[[ "${AnalysisBundleSize}" =~ ^[0-9]+$ && "${AnalysisBundleSize}" -ge 1 ]] || die "Invalid AnalysisBundleSize=${AnalysisBundleSize}"
if [[ "${AnalysisInputMode}" == "bundled_hadrons" && -n "${LEGACY_AN_BATCH_ID}" && -n "${AnalysisBatchID:-}" && "${LEGACY_AN_BATCH_ID}" != "${AnalysisBatchID}" ]]; then
  log "[WARN] legacy AN_BATCH_ID=${LEGACY_AN_BATCH_ID} conflicts with AnalysisBatchID=${AnalysisBatchID}; bundled_hadrons uses effective AN_BATCH_ID=${AN_BATCH_ID}."
fi
MergeVerboseBundleLogs="${MergeVerboseBundleLogs:-1}"
MergeScanLogEvery="${MergeScanLogEvery:-50}"
MergeHaddEchoOutput="${MergeHaddEchoOutput:-0}"
MergeMergeEngine="${MergeMergeEngine:-root_macro}"
MergeRootMergeProgressEvery="${MergeRootMergeProgressEvery:-50}"
MergeUseLocalTmp="${MergeUseLocalTmp:-1}"
MergeFinalCopySingleSlice="${MergeFinalCopySingleSlice:-1}"
MergeStrictNormScan="${MergeStrictNormScan:-0}"
[[ "${MergeVerboseBundleLogs}" =~ ^[01]$ ]] || die "MergeVerboseBundleLogs must be 0 or 1, got ${MergeVerboseBundleLogs}"
[[ "${MergeScanLogEvery}" =~ ^[0-9]+$ && "${MergeScanLogEvery}" -ge 1 ]] || die "MergeScanLogEvery must be integer >=1, got ${MergeScanLogEvery}"
[[ "${MergeHaddEchoOutput}" =~ ^[01]$ ]] || die "MergeHaddEchoOutput must be 0 or 1, got ${MergeHaddEchoOutput}"
[[ "${MergeMergeEngine}" == "root_macro" || "${MergeMergeEngine}" == "hadd" ]] || die "MergeMergeEngine must be root_macro or hadd, got ${MergeMergeEngine}"
[[ "${MergeRootMergeProgressEvery}" =~ ^[0-9]+$ && "${MergeRootMergeProgressEvery}" -ge 1 ]] || die "MergeRootMergeProgressEvery must be integer >=1, got ${MergeRootMergeProgressEvery}"
[[ "${MergeUseLocalTmp}" =~ ^[01]$ ]] || die "MergeUseLocalTmp must be 0 or 1, got ${MergeUseLocalTmp}"
[[ "${MergeFinalCopySingleSlice}" =~ ^[01]$ ]] || die "MergeFinalCopySingleSlice must be 0 or 1, got ${MergeFinalCopySingleSlice}"
[[ "${MergeStrictNormScan}" =~ ^[01]$ ]] || die "MergeStrictNormScan must be 0 or 1, got ${MergeStrictNormScan}"
log_section "merge configuration"
log "[cfg] BASE_DIR=${BASE_DIR}"
log "[cfg] INI_PATH=${INI_PATH}"
log "[cfg] RUN_TAG=${RUN_TAG} RUN_DIR=${RUN_DIR}"
log "[cfg] DIR_ANALYSIS=${DIR_ANALYSIS}"
log "[cfg] DIR_FINAL=${DIR_FINAL}"
log "[cfg] DIR_LOG_MERGE=${DIR_LOG_MERGE}"
log "[cfg] AnalysisInputMode=${AnalysisInputMode} AnalysisBatchID=${AnalysisBatchID:-unset} legacy_AN_BATCH_ID=${LEGACY_AN_BATCH_ID:-unset} effective_AN_BATCH_ID=${AN_BATCH_ID} AnalysisBundleSize=${AnalysisBundleSize}"
log "[cfg] NUM_EVENTS=${NUM_EVENTS} Multiplier=${MULT} MergeVerboseBundleLogs=${MergeVerboseBundleLogs} MergeScanLogEvery=${MergeScanLogEvery} MergeHaddEchoOutput=${MergeHaddEchoOutput} MergeMergeEngine=${MergeMergeEngine} MergeRootMergeProgressEvery=${MergeRootMergeProgressEvery} MergeUseLocalTmp=${MergeUseLocalTmp} MergeFinalCopySingleSlice=${MergeFinalCopySingleSlice} MergeStrictNormScan=${MergeStrictNormScan}"

FINAL_OUT="${DIR_FINAL}/dphi_allSlices.root"
if (( MergeUseLocalTmp == 1 )) && [[ -n "${TMPDIR:-}" && -d "${TMPDIR}" && -w "${TMPDIR}" ]]; then
  TMP_PARENT="${TMPDIR}"
  TMP_LOCATION="local_TMPDIR"
else
  TMP_PARENT="${DIR_FINAL}"
  TMP_LOCATION="final_dir_fallback"
fi
TMP_DIR="${TMP_PARENT%/}/xscape_merge_bundle_${SLURM_JOB_ID:-$$}_$(date +%Y%m%d_%H%M%S)"
TMP_FINAL_OUT="${TMP_DIR}/dphi_allSlices.root"
mkdir -p "${TMP_DIR}/per_slice"
log "[paths] FINAL_OUT=${FINAL_OUT}"
log "[paths] TMP_PARENT=${TMP_PARENT} TMP_LOCATION=${TMP_LOCATION} MergeUseLocalTmp=${MergeUseLocalTmp}"
log "[paths] TMP_DIR=${TMP_DIR}"
log "[paths] TMP_FINAL_OUT=${TMP_FINAL_OUT}"

json_value(){
  local f="$1" k="$2" kind="$3"
  [[ -s "${f}" ]] || return 0
  python3 - "${f}" "${k}" "${kind}" <<'PYJSON'
import json, math, sys
path, key, kind = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    with open(path, 'r', encoding='utf-8') as fh:
        data = json.load(fh)
    val = data.get(key, None)
    if kind == 'num':
        if isinstance(val, bool) or val is None:
            print('', end='')
        elif isinstance(val, (int, float)) and not (isinstance(val, float) and (math.isnan(val) or math.isinf(val))):
            print(val, end='')
        else:
            print('', end='')
    else:
        print(val if isinstance(val, str) else '', end='')
except Exception:
    print('', end='')
PYJSON
}
json_num(){ json_value "$1" "$2" num; }
json_str(){ json_value "$1" "$2" str; }

btag(){ printf '%s_%s_%s_bundle%06d' "${RUN_TAG}" "$1" "$2" "$3"; }

validate_root(){
  root -l -b -q <<< "TFile f(\"$1\"); if(f.IsZombie()||f.GetNkeys()==0) gSystem->Exit(2); gSystem->Exit(0);" >/dev/null 2>&1
}

run_hadd_direct_logged(){
  local label="$1" out="$2"
  shift 2
  local inputs=("$@")
  local n="${#inputs[@]}"
  local hdir="${DIR_LOG_MERGE}/hadd_logs"
  local list_file="${hdir}/hadd_${label}_${SLURM_JOB_ID:-manual}.inputs.txt"
  local log_file="${hdir}/hadd_${label}_${SLURM_JOB_ID:-manual}.log"
  local start_ts end_ts sec rc bytes

  mkdir -p "${hdir}" "$(dirname "${out}")"
  if (( n < 1 )); then
    die "[hadd_start] label=${label} has zero inputs; refusing to run hadd."
  fi
  printf '%s\n' "${inputs[@]}" > "${list_file}"
  rm -f "${out}"

  log "[hadd_start] label=${label} engine=hadd mode=direct_one_shot inputs=${n} output=${out} input_list=${list_file} hadd_log=${log_file} echo=${MergeHaddEchoOutput}"
  log "[hadd_cmd] hadd -f ${out} <${n} inputs>"
  log "[hadd_note] Full hadd stdout/stderr is saved in ${log_file}."
  start_ts="$(date +%s)"

  rc=0
  {
    echo "[$(ts)] [hadd ${label}] command: hadd -f ${out} <${n} inputs>"
    echo "[$(ts)] [hadd ${label}] input_list: ${list_file}"
    hadd -f "${out}" "${inputs[@]}"
  } > "${log_file}" 2>&1 || rc="$?"
  end_ts="$(date +%s)"
  sec=$(( end_ts - start_ts ))

  if (( MergeHaddEchoOutput == 1 )); then
    sed "s/^/[hadd ${label}] /" "${log_file}" || true
  fi
  if (( rc != 0 )); then
    log "[hadd_fail] label=${label} engine=hadd rc=${rc} sec=${sec} output=${out} log=${log_file} input_list=${list_file}"
    tail -n 80 "${log_file}" 2>/dev/null | sed "s/^/[hadd_tail ${label}] /" || true
    exit "${rc}"
  fi
  if [[ ! -s "${out}" ]]; then
    log "[hadd_fail] label=${label} engine=hadd rc=0 but output is missing/empty: ${out} log=${log_file} input_list=${list_file}"
    tail -n 80 "${log_file}" 2>/dev/null | sed "s/^/[hadd_tail ${label}] /" || true
    exit 3
  fi
  bytes=$(wc -c < "${out}" 2>/dev/null || echo 0)
  log "[hadd_done] label=${label} engine=hadd rc=0 sec=${sec} bytes=${bytes} output=${out} log=${log_file} input_list=${list_file}"
}

run_root_macro_merge_logged(){
  local label="$1" out="$2"
  shift 2
  local inputs=("$@")
  local n="${#inputs[@]}"
  local hdir="${DIR_LOG_MERGE}/hadd_logs"
  local list_file="${hdir}/rootmerge_${label}_${SLURM_JOB_ID:-manual}.inputs.txt"
  local log_file="${hdir}/rootmerge_${label}_${SLURM_JOB_ID:-manual}.log"
  local macro_file="${TMP_DIR}/rootmerge_${label}_${SLURM_JOB_ID:-manual}.C"
  local start_ts end_ts sec rc bytes

  mkdir -p "${hdir}" "$(dirname "${out}")" "${TMP_DIR}"
  if (( n < 1 )); then
    die "[rootmerge_start] label=${label} has zero inputs; refusing to merge."
  fi
  printf '%s\n' "${inputs[@]}" > "${list_file}"
  rm -f "${out}"

  cat > "${macro_file}" <<'ROOTMERGE'
#include <TFile.h>
#include <TKey.h>
#include <TDirectory.h>
#include <TSystem.h>
#include <TH1.h>
#include <TClass.h>
#include <TROOT.h>
#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <map>
#include <string>
#include <cstdlib>

static std::vector<std::string> split_path(const std::string& p){
  std::vector<std::string> out;
  std::stringstream ss(p);
  std::string item;
  while(std::getline(ss, item, '/')) if(!item.empty()) out.push_back(item);
  return out;
}

static TDirectory* mkdir_p(TDirectory* base, const std::string& path){
  TDirectory* cur = base;
  for(const auto& part : split_path(path)){
    TObject* obj = cur->Get(part.c_str());
    TDirectory* nxt = obj && obj->InheritsFrom(TDirectory::Class()) ? (TDirectory*)obj : nullptr;
    if(!nxt) nxt = cur->mkdir(part.c_str());
    cur = nxt;
  }
  return cur;
}

static void collect_hists(TDirectory* dir,
                          const std::string& prefix,
                          std::map<std::string, TH1*>& merged,
                          std::map<std::string, std::string>& names,
                          std::map<std::string, std::string>& dirs,
                          long long& hist_seen,
                          long long& hist_added,
                          long long& skipped_nonhist){
  TIter next(dir->GetListOfKeys());
  TKey* key = nullptr;
  while((key = (TKey*)next())){
    TObject* obj = key->ReadObj();
    if(!obj) continue;
    std::string name = obj->GetName();
    if(obj->InheritsFrom(TDirectory::Class())){
      collect_hists((TDirectory*)obj, prefix + name + "/", merged, names, dirs, hist_seen, hist_added, skipped_nonhist);
      delete obj;
      continue;
    }
    if(obj->InheritsFrom(TH1::Class())){
      TH1* h = (TH1*)obj;
      std::string full = prefix + name;
      hist_seen++;
      auto it = merged.find(full);
      if(it == merged.end()){
        TH1* clone = (TH1*)h->Clone(name.c_str());
        clone->SetDirectory(nullptr);
        merged[full] = clone;
        names[full] = name;
        dirs[full] = prefix;
      } else {
        bool ok = it->second->Add(h);
        if(!ok) std::cerr << "[rootmerge][WARN] TH1::Add returned false for " << full << std::endl;
        hist_added++;
      }
    } else {
      skipped_nonhist++;
    }
    delete obj;
  }
}

int xscape_root_merge_driver(){
  const char* list_env = gSystem->Getenv("XSCAPE_ROOT_MERGE_INPUT_LIST");
  const char* out_env  = gSystem->Getenv("XSCAPE_ROOT_MERGE_OUTPUT");
  const char* label_env = gSystem->Getenv("XSCAPE_ROOT_MERGE_LABEL");
  const char* every_env = gSystem->Getenv("XSCAPE_ROOT_MERGE_PROGRESS_EVERY");
  if(!list_env || !out_env){ std::cerr << "[rootmerge][FATAL] missing input/output env" << std::endl; return 10; }
  std::string label = label_env ? label_env : "rootmerge";
  int every = every_env ? std::atoi(every_env) : 50;
  if(every < 1) every = 50;
  std::ifstream fin(list_env);
  if(!fin){ std::cerr << "[rootmerge][FATAL] cannot open input list: " << list_env << std::endl; return 11; }
  std::vector<std::string> files; std::string line;
  while(std::getline(fin, line)){ if(!line.empty()) files.push_back(line); }
  if(files.empty()){ std::cerr << "[rootmerge][FATAL] input list is empty" << std::endl; return 12; }

  std::map<std::string, TH1*> merged;
  std::map<std::string, std::string> names, dirs;
  long long hist_seen=0, hist_added=0, skipped_nonhist=0, files_ok=0;
  std::cerr << "[rootmerge_start] label=" << label << " inputs=" << files.size() << " output=" << out_env << std::endl;
  for(size_t i=0; i<files.size(); ++i){
    TFile* f = TFile::Open(files[i].c_str(), "READ");
    if(!f || f->IsZombie()){
      std::cerr << "[rootmerge][FATAL] cannot open input " << (i+1) << "/" << files.size() << ": " << files[i] << std::endl;
      if(f) f->Close();
      return 20;
    }
    collect_hists(f, "", merged, names, dirs, hist_seen, hist_added, skipped_nonhist);
    files_ok++;
    f->Close(); delete f;
    if(((int)(i+1) % every) == 0 || i+1 == files.size()){
      std::cerr << "[rootmerge_progress] label=" << label
                << " files=" << (i+1) << "/" << files.size()
                << " unique_hists=" << merged.size()
                << " hist_seen=" << hist_seen
                << " hist_added=" << hist_added
                << " skipped_nonhist=" << skipped_nonhist << std::endl;
    }
  }
  if(merged.empty()){ std::cerr << "[rootmerge][FATAL] no histograms collected" << std::endl; return 30; }
  TFile* fout = TFile::Open(out_env, "RECREATE");
  if(!fout || fout->IsZombie()){ std::cerr << "[rootmerge][FATAL] cannot create output: " << out_env << std::endl; if(fout) fout->Close(); return 31; }
  long long written=0;
  for(auto& kv : merged){
    const std::string& full = kv.first;
    TDirectory* odir = mkdir_p(fout, dirs[full]);
    odir->cd();
    kv.second->Write(names[full].c_str(), TObject::kOverwrite);
    written++;
  }
  fout->Write(); fout->Close(); delete fout;
  for(auto& kv : merged) delete kv.second;
  std::cerr << "[rootmerge_done] label=" << label << " files_ok=" << files_ok
            << " unique_hists=" << written << " hist_seen=" << hist_seen
            << " hist_added=" << hist_added << " skipped_nonhist=" << skipped_nonhist
            << " output=" << out_env << std::endl;
  return 0;
}
ROOTMERGE

  log "[rootmerge_start] label=${label} inputs=${n} output=${out} input_list=${list_file} rootmerge_log=${log_file} progress_every=${MergeRootMergeProgressEvery}"
  log "[rootmerge_cmd] ROOT macro histogram merge <${n} inputs>; avoids direct hadd stall at /counts."
  start_ts="$(date +%s)"
  rc=0
  if XSCAPE_ROOT_MERGE_INPUT_LIST="${list_file}" \
     XSCAPE_ROOT_MERGE_OUTPUT="${out}" \
     XSCAPE_ROOT_MERGE_LABEL="${label}" \
     XSCAPE_ROOT_MERGE_PROGRESS_EVERY="${MergeRootMergeProgressEvery}" \
     root -l -b > "${log_file}" 2>&1 <<EOF_ROOT
.L ${macro_file}
int rc = xscape_root_merge_driver();
gSystem->Exit(rc);
EOF_ROOT
  then
    rc=0
  else
    rc="$?"
  fi
  end_ts="$(date +%s)"; sec=$(( end_ts - start_ts ))
  if (( MergeHaddEchoOutput == 1 )); then sed "s/^/[rootmerge ${label}] /" "${log_file}" || true; fi
  if (( rc != 0 )); then
    log "[rootmerge_fail] label=${label} rc=${rc} sec=${sec} output=${out} log=${log_file} input_list=${list_file}"
    tail -n 120 "${log_file}" 2>/dev/null | sed "s/^/[rootmerge_tail ${label}] /" || true
    exit "${rc}"
  fi
  if [[ ! -s "${out}" ]]; then
    log "[rootmerge_fail] label=${label} rc=0 but output is missing/empty: ${out} log=${log_file} input_list=${list_file}"
    tail -n 120 "${log_file}" 2>/dev/null | sed "s/^/[rootmerge_tail ${label}] /" || true
    exit 4
  fi
  bytes=$(wc -c < "${out}" 2>/dev/null || echo 0)
  log "[rootmerge_done] label=${label} rc=0 sec=${sec} bytes=${bytes} output=${out} log=${log_file} input_list=${list_file}"
}

run_hadd_logged(){
  local label="$1" out="$2"; shift 2
  if [[ "${MergeMergeEngine}" == "hadd" ]]; then
    run_hadd_direct_logged "${label}" "${out}" "$@"
  else
    run_root_macro_merge_logged "${label}" "${out}" "$@"
  fi
}

validate_root_logged(){
  local label="$1" rootf="$2"
  local vlog="${DIR_LOG_MERGE}/hadd_logs/validate_${label}_${SLURM_JOB_ID:-manual}.log"
  local start_ts end_ts sec rc bytes
  mkdir -p "$(dirname "${vlog}")"
  log "[validate_start] label=${label} root=${rootf} log=${vlog}"
  start_ts="$(date +%s)"
  if root -l -b -q <<< "TFile f(\"${rootf}\"); if(f.IsZombie()||f.GetNkeys()==0) gSystem->Exit(2); gSystem->Exit(0);" > "${vlog}" 2>&1; then
    rc=0
  else
    rc="$?"
  fi
  end_ts="$(date +%s)"
  sec=$(( end_ts - start_ts ))
  if (( rc != 0 )); then
    log "[validate_fail] label=${label} rc=${rc} sec=${sec} root=${rootf} log=${vlog}"
    tail -n 80 "${vlog}" 2>/dev/null | sed "s/^/[validate_tail ${label}] /" || true
    exit "${rc}"
  fi
  [[ -s "${rootf}" ]] || die "[validate_fail] label=${label} ROOT validation returned rc=0 but file is missing/empty: ${rootf}"
  bytes=$(wc -c < "${rootf}" 2>/dev/null || echo 0)
  log "[validate_done] label=${label} sec=${sec} bytes=${bytes} root=${rootf}"
}

for required_fn in run_hadd_direct_logged run_root_macro_merge_logged run_hadd_logged validate_root_logged validate_root json_num json_str; do
  declare -F "${required_fn}" >/dev/null || die "internal merge helper missing: ${required_fn}"
done

XSEC_SLICES="${DIR_FINAL}/xsec_slices.csv"
XSEC_SUMMARY="${DIR_FINAL}/xsec_summary.json"
SEL_COUNTS_JSON="${DIR_FINAL}/selected_dijet_counts_summary.json"

echo "pthat_low,pthat_high,njobs_present,xsec_mb,xsecerr_mb,xsec_rel_err" > "${XSEC_SLICES}"
sel_jsonl="${TMP_DIR}/selected_counts.jsonl"; : > "${sel_jsonl}"
log_section "lean report initialization"
log "[report_init] xsec_slices=${XSEC_SLICES}"
log "[report_init] xsec_summary=${XSEC_SUMMARY}"
log "[report_init] selected_counts_json=${SEL_COUNTS_JSON}"
log "[report_init] selected_counts_jsonl_tmp=${sel_jsonl}"
log "[report_init] skipped_redundant=normalization_report.csv,merge_analysis_task_states.csv,merge_missing_analysis_outputs.csv"
slice_roots=(); TOT_XSEC=0; TOT_XSEC_ERR2=0

for idx in "${!PT_LO[@]}"; do
  L="${PT_LO[$idx]}"; H="${PT_HI[$idx]}"; NJ=$(( JOBS[idx] * MULT )); intended=$(( NJ * NUM_EVENTS ))
  jid_file="${DIR_LOG_ANALYSIS}/jid_an_${L}_${H}.txt"
  if [[ "${AnalysisInputMode}" == "bundled_hadrons" ]]; then
    BID="${AN_BATCH_ID}"
    if [[ -s "${jid_file}" ]]; then
      old_bid="$(tr -d '[:space:]' < "${jid_file}" || true)"
      if [[ -n "${old_bid}" && "${old_bid}" != "${BID}" ]]; then
        log "[WARN] bundled merge ignoring stale ${jid_file}=${old_bid}; using effective_AN_BATCH_ID=${BID} and updating jid file."
      fi
    fi
    printf '%s
' "${BID}" > "${jid_file}"
  else
    if [[ -s "${jid_file}" ]]; then BID="$(tr -d '[:space:]' < "${jid_file}")"; else BID="${AN_BATCH_ID}"; fi
  fi
  AN_DIR="${DIR_ANALYSIS}/${L}-${H}/${BID}"
  expected_bundles=$(( (NJ + AnalysisBundleSize - 1) / AnalysisBundleSize ))
  log_section "slice ${L}-${H} preflight"
  log "[slice ${L}-${H}] idx=${idx} NJ=${NJ} intended_events=${intended} BID=${BID} jid_file=${jid_file} AN_DIR=${AN_DIR} expected_bundles=${expected_bundles}"
  inputs=(); metas=(); sum_ev=0; accepted=0; rejected=0; b=1; start=1
  while (( start <= NJ )); do
    end=$(( start + AnalysisBundleSize - 1 )); (( end > NJ )) && end=${NJ}
    exp=$(( (end - start + 1) * NUM_EVENTS ))
    tag="$(btag "${L}" "${H}" "${b}")"
    rf="${AN_DIR}/dphi_${tag}.root"
    jf="${AN_DIR}/slice_meta_${tag}.json"
    ev="$(json_num "${jf}" events_seen || true)"
    rs="$(json_str "${jf}" root_status || true)"
    sz=0; [[ -s "${rf}" ]] && sz=$(wc -c < "${rf}" 2>/dev/null || echo 0)
    st=DONE; what=ok
    if [[ ! -s "${rf}" ]]; then st=MISSING_ROOT; what=missing_dphi_root
    elif [[ ! -s "${jf}" ]]; then st=MISSING_META; what=missing_slice_meta_json
    elif [[ "${rs}" != ok ]]; then st=CORRUPT_ROOT; what=corrupt_root
    elif [[ ! "${ev}" =~ ^[0-9]+$ || "${ev}" -ne "${exp}" ]]; then st=INCOMPLETE_EVENTS; what=incomplete_events
    fi
    if (( MergeVerboseBundleLogs == 1 )); then
      log "[bundle_status] slice=${L}-${H} bundle=$(printf '%06d' ${b}) tasks=${start}-${end} status=${st} events_seen=${ev:-NA}/${exp} bytes=${sz} root_status=${rs:-NA} root=${rf} meta=${jf}"
    elif (( b % MergeScanLogEvery == 0 || b == 1 || end == NJ )); then
      log "[scan_progress] slice=${L}-${H} bundle=${b}/${expected_bundles} accepted_tasks=${accepted} rejected_bundles=${rejected} events_seen_sum=${sum_ev}"
    fi
    if [[ "${st}" == DONE ]]; then
      inputs+=("${rf}"); metas+=("${jf}"); sum_ev=$(( sum_ev + ev )); accepted=$(( accepted + end - start + 1 ))
    else
      rejected=$(( rejected + 1 ))
      log "[bundle_reject] slice=${L}-${H} bundle=$(printf '%06d' ${b}) tasks=${start}-${end} what=${what} events_seen=${ev:-NA}/${exp} root=${rf} meta=${jf}"
    fi
    if (( b % MergeScanLogEvery == 0 || end == NJ )); then
      log "[scan_progress] slice=${L}-${H} scanned_bundle=${b}/${expected_bundles} accepted_tasks=${accepted}/${NJ} accepted_events=${sum_ev}/${intended} accepted_bundles=${#inputs[@]} rejected_bundles=${rejected}"
    fi
    b=$(( b + 1 )); start=$(( end + 1 ))
  done
  log "[slice ${L}-${H}] preflight_done accepted_tasks=${accepted}/${NJ} events=${sum_ev}/${intended} bundles=${#inputs[@]}/${expected_bundles} rejected=${rejected}"
  if (( rejected > 0 || sum_ev != intended )); then
    log "[slice ${L}-${H}] incomplete coverage: rejected=${rejected} events=${sum_ev}/${intended}; writing diagnostic report row and skipping hadd for this slice."
    continue
  fi
  out="${TMP_DIR}/per_slice/dphi_${L}-${H}.root"
  log "[slice ${L}-${H}] per_slice_hadd_prepare inputs=${#inputs[@]} output=${out}"
  run_hadd_logged "slice_${L}_${H}" "${out}" "${inputs[@]}"
  validate_root_logged "per_slice_${L}_${H}" "${out}"
  log "[slice ${L}-${H}] publish_per_slice_start src=${out} dest=${DIR_FINAL}/per_slice/dphi_${L}-${H}.root"
  cp -f "${out}" "${DIR_FINAL}/per_slice/dphi_${L}-${H}.root"
  validate_root_logged "published_per_slice_${L}_${H}" "${DIR_FINAL}/per_slice/dphi_${L}-${H}.root"
  log "[slice ${L}-${H}] publish_per_slice_done dest=${DIR_FINAL}/per_slice/dphi_${L}-${H}.root"
  slice_roots+=("${out}")
  log "[slice ${L}-${H}] norm_reference_start metas=${#metas[@]} strict=${MergeStrictNormScan}"
  ref_meta="${metas[0]}"
  ref_xs="$(json_num "${ref_meta}" norm_sigmaGen_mb_used)"; ref_xe="$(json_num "${ref_meta}" norm_sigmaErr_mb_used)"
  ref_w="$(json_num "${ref_meta}" norm_weight_mb_per_event_used)"; ref_den="$(json_num "${ref_meta}" norm_denominator_events_used)"
  [[ -n "${ref_xs}" && -n "${ref_xe}" && -n "${ref_w}" && -n "${ref_den}" ]] || die "missing norm meta in reference bundle ${ref_meta}"
  log "[slice ${L}-${H}] norm_reference xs=${ref_xs} xe=${ref_xe} weight=${ref_w} denominator=${ref_den} source_meta=${ref_meta}"
  if (( MergeStrictNormScan == 1 )); then
    log "[slice ${L}-${H}] strict_norm_scan_start metas=${#metas[@]}"
    meta_idx=0
    for jf in "${metas[@]}"; do
      meta_idx=$((meta_idx + 1))
      xs="$(json_num "${jf}" norm_sigmaGen_mb_used)"; xe="$(json_num "${jf}" norm_sigmaErr_mb_used)"
      nw="$(json_num "${jf}" norm_weight_mb_per_event_used)"; nd="$(json_num "${jf}" norm_denominator_events_used)"
      [[ -n "${xs}" && -n "${xe}" && -n "${nw}" && -n "${nd}" ]] || die "missing norm meta ${jf}"
      [[ "${xs}" == "${ref_xs}" && "${xe}" == "${ref_xe}" && "${nw}" == "${ref_w}" && "${nd}" == "${ref_den}" ]] || die "inconsistent norm meta ${jf}"
      if (( meta_idx % MergeScanLogEvery == 0 || meta_idx == ${#metas[@]} )); then
        log "[slice ${L}-${H}] strict_norm_scan_progress ${meta_idx}/${#metas[@]}"
      fi
    done
    log "[slice ${L}-${H}] strict_norm_scan_done metas=${#metas[@]}"
  else
    log "[slice ${L}-${H}] strict_norm_scan_skipped MergeStrictNormScan=0; using reference bundle meta only"
  fi
  rel="$(awk -v e="${ref_xe}" -v s="${ref_xs}" 'BEGIN{if(s>0) printf "%.12g", e/s; else print "0"}')"
  echo "${L},${H},${accepted},${ref_xs},${ref_xe},${rel}" >> "${XSEC_SLICES}"
  TOT_XSEC="$(awk -v a="${TOT_XSEC}" -v b="${ref_xs}" 'BEGIN{printf "%.12g", a+b}')"
  TOT_XSEC_ERR2="$(awk -v a="${TOT_XSEC_ERR2}" -v b="${ref_xe}" 'BEGIN{printf "%.12g", a+b*b}')"
  log "[slice ${L}-${H}] selected_counts_aggregate_start metas=${#metas[@]} tmp_jsonl=${sel_jsonl}"
  python3 - "${L}" "${H}" "${NJ}" "${accepted}" "${sel_jsonl}" "${metas[@]}" <<'PYSEL'
import json, sys
L, H, NJ, ACC, out = sys.argv[1:6]
paths = sys.argv[6:]
branches = ("default", "nosubfrac")
fields = ("dijet_base_all_per_R", "dphi_abs_all_per_R", "xj_all_per_R", "aj_all_per_R", "mjj_all_per_R", "dijet_base_ptlead_per_R", "dphi_abs_ptlead_per_R", "xj_ptlead_per_R", "aj_ptlead_per_R")
def z(x):
    return [z(v) for v in x] if isinstance(x, list) else 0
def add(a, b):
    for i in range(len(a)):
        if isinstance(a[i], list):
            add(a[i], b[i])
        else:
            a[i] = int(a[i]) + int(b[i])
sums = {}
sem = None
for p in paths:
    with open(p, 'r', encoding='utf-8') as fh:
        d = json.load(fh)
    block = d['selected_dijet_counts']
    sem = sem or block.get('count_semantics')
    if not sums:
        sums = {br: {f: z(block[br][f]) for f in fields} for br in branches}
    for br in branches:
        for f in fields:
            add(sums[br][f], block[br][f])
record = {'pt_lo': int(L), 'pt_hi': int(H), 'njobs_expected': int(NJ), 'njobs_accepted': int(ACC), 'selected_dijet_counts': {'count_semantics': sem, 'default': sums['default'], 'nosubfrac': sums['nosubfrac']}}
with open(out, 'a', encoding='utf-8') as fh:
    fh.write(json.dumps(record, sort_keys=True) + "\n")
PYSEL
  log "[slice ${L}-${H}] selected_counts_aggregate_done tmp_jsonl=${sel_jsonl}"
done

log_section "final ROOT merge"
log "[final] complete_slices=${#slice_roots[@]}"
(( ${#slice_roots[@]} > 0 )) || die "no complete slices"
if (( ${#slice_roots[@]} == 1 && MergeFinalCopySingleSlice == 1 )); then
  log "[final] single_slice_copy_start src=${slice_roots[0]} dest=${TMP_FINAL_OUT} reason=MergeFinalCopySingleSlice=1"
  cp -f "${slice_roots[0]}" "${TMP_FINAL_OUT}"
  log "[final] single_slice_copy_done dest=${TMP_FINAL_OUT} bytes=$(wc -c < "${TMP_FINAL_OUT}" 2>/dev/null || echo 0)"
else
  run_hadd_logged "final_allSlices" "${TMP_FINAL_OUT}" "${slice_roots[@]}"
fi
validate_root_logged "temporary_final" "${TMP_FINAL_OUT}"
log "[final] publish_final_start src=${TMP_FINAL_OUT} dest=${FINAL_OUT}"
cp -f "${TMP_FINAL_OUT}" "${FINAL_OUT}"
validate_root_logged "published_final" "${FINAL_OUT}"
log "[final] publish_final_done dest=${FINAL_OUT}"
TOT_ERR="$(awk -v e2="${TOT_XSEC_ERR2}" 'BEGIN{printf "%.12g", sqrt(e2)}')"
TOT_REL="$(awk -v e="${TOT_ERR}" -v s="${TOT_XSEC}" 'BEGIN{if(s>0) printf "%.12g", e/s; else print "0"}')"
log_section "xsec summary publication"
log "[xsec] total=${TOT_XSEC} err=${TOT_ERR} rel=${TOT_REL} slices_csv=${XSEC_SLICES} summary_json=${XSEC_SUMMARY}"
python3 - "${XSEC_SLICES}" "${XSEC_SUMMARY}" "${RUN_TAG}" "${TOT_XSEC}" "${TOT_ERR}" "${TOT_REL}" <<'PYXSEC'
import csv, json, sys
csvp, out, run, total, err, rel = sys.argv[1:]
rows = []
with open(csvp, 'r', encoding='utf-8') as fh:
    for r in csv.DictReader(fh):
        rows.append({'pt_lo': int(r['pthat_low']), 'pt_hi': int(r['pthat_high']), 'njobs_present': int(r['njobs_present']), 'rootfile': f"per_slice/dphi_{r['pthat_low']}-{r['pthat_high']}.root", 'xsec_mb': float(r['xsec_mb']), 'xsecerr_mb': float(r['xsecerr_mb']), 'xsec_rel_err': float(r['xsec_rel_err']), 'sigmaGen_mb': float(r['xsec_mb']), 'sigmaErr_mb': float(r['xsecerr_mb'])})
json.dump({'run_tag': run, 'include_xsec_norm_err': 1, 'xsec_err_any_unknown': False, 'xsec_total_mb': float(total), 'sigma_total_mb': float(total), 'xsec_total_err_mb': float(err), 'sigma_total_err_mb': float(err), 'xsec_total_rel_err': float(rel), 'sigma_total_rel_err': float(rel), 'selected_dijet_counts_summary_json': 'selected_dijet_counts_summary.json', 'slices': rows}, open(out, 'w', encoding='utf-8'), indent=2)
PYXSEC
log "[xsec] summary_done ${XSEC_SUMMARY}"
log_section "selected dijet count summary publication"
log "[counts] input_jsonl=${sel_jsonl} output_json=${SEL_COUNTS_JSON}"
python3 - "${sel_jsonl}" "${SEL_COUNTS_JSON}" "${RUN_TAG}" <<'PYCOUNT'
import json, sys
inp, out, run = sys.argv[1:]
slices = [json.loads(l) for l in open(inp, encoding='utf-8') if l.strip()]
branches = ("default", "nosubfrac")
fields = ("dijet_base_all_per_R", "dphi_abs_all_per_R", "xj_all_per_R", "aj_all_per_R", "mjj_all_per_R", "dijet_base_ptlead_per_R", "dphi_abs_ptlead_per_R", "xj_ptlead_per_R", "aj_ptlead_per_R")
def z(x):
    return [z(v) for v in x] if isinstance(x, list) else 0
def add(a, b):
    for i in range(len(a)):
        if isinstance(a[i], list):
            add(a[i], b[i])
        else:
            a[i] = int(a[i]) + int(b[i])
sem = slices[0]['selected_dijet_counts']['count_semantics']
tot = {br: {f: z(slices[0]['selected_dijet_counts'][br][f]) for f in fields} for br in branches}
for sl in slices:
    for br in branches:
        for f in fields:
            add(tot[br][f], sl['selected_dijet_counts'][br][f])
json.dump({'run_tag': run, 'merged_slice_count': len(slices), 'count_semantics': sem, 'publication_scope': 'accepted_merged_slices_only', 'slices': slices, 'selected_dijet_counts_total': {'count_semantics': sem, 'default': tot['default'], 'nosubfrac': tot['nosubfrac']}}, open(out, 'w', encoding='utf-8'), indent=2, sort_keys=True)
PYCOUNT
log "[counts] summary_done ${SEL_COUNTS_JSON}"
log_section "manifest and status publication"
log "[manifest] writing ${DIR_FINAL}/run_manifest.txt"
cat > "${DIR_FINAL}/run_manifest.txt" <<EOF
=== xscape dphi RUN MANIFEST ===
Generated: $(date) user=$(whoami) host=$(hostname) slurm_job=${SLURM_JOB_ID:-NA}
RUN_TAG=${RUN_TAG}
AnalysisInputMode=${AnalysisInputMode}
AnalysisBundleSize=${AnalysisBundleSize}
final_root=${FINAL_OUT}
xsec_summary=${XSEC_SUMMARY}
selected_dijet_counts_summary=${SEL_COUNTS_JSON}
lean_merge_reports=1
MergeMergeEngine=${MergeMergeEngine}
skipped_redundant_reports=normalization_report.csv,merge_analysis_task_states.csv,merge_missing_analysis_outputs.csv
EOF
log "[status] writing ${DIR_FINAL}/merge_status.json"
python3 - "${DIR_FINAL}/merge_status.json" "${RUN_TAG}" "${FINAL_OUT}" <<'PYSTAT'
import json, os, sys
p, run, root = sys.argv[1:]
json.dump({'status': 'Final root ok', 'reason': 'ok', 'run_tag': run, 'final_root': root, 'final_root_exists': os.path.exists(root)}, open(p, 'w', encoding='utf-8'), indent=2)
PYSTAT
log "[status] merge_status_done ${DIR_FINAL}/merge_status.json"
log "[cleanup] removing TMP_DIR=${TMP_DIR} TMP_LOCATION=${TMP_LOCATION}"
rm -rf "${TMP_DIR}"
log "[done] final=${FINAL_OUT} xsec_rel_err=${TOT_REL} xsec_summary=${XSEC_SUMMARY} counts_summary=${SEL_COUNTS_JSON}"
