#!/usr/bin/env bash
# run_local_pp_realistic_pair_10x.sh v10.7
# Patch notes:
# - v10.7: Uses paper-MUSIC timing/input baseline after A/B test: Initial_time_tau_0=0.6, Delta_Tau=0.02, average_surface_over_this_many_time_steps=5; no freeze_out_tau_start_max line.
# - v10.7: Keeps v10.5 retry driver, Docker runtime detection, 13 TeV hard settings, final-state hadron output, no hydro reuse.
# - v10.5: Treats iSS "Every line should have 36 variables, got -1" after "total number of cells: 0" as the known stochastic pp zero-surface case and retries with new seeds.
# - v10.5: Produces N_EVENTS accepted vac and N_EVENTS accepted medium events when possible, while keeping every failed retry directory/log in the diagnostic tarball.
# - v10.5: Adds attempt_summary.tsv and accepted_summary.tsv; terminal_transcript.log remains included in the return tarball.
# - v10.5: No physics XML changes beyond v10.4; eCM=13000, pTHat=30-3000, final-state hadrons on, softMomentumCutoff=2, eCMforHadronization=6500, nEvents=1, no hydro reuse.
# - v10.4: Detects macOS/Linux executable format mismatch and runs PythiaIsrMUSIC through Docker container xscape_mac when the host binary is not directly executable on macOS.
# - v10.4: Uses relative EOS/tables/iSS_tables symlinks so staged event directories work both on host macOS and inside Docker at /home/jetscape-user/X-SCAPE.
# - v10.4: Captures full terminal stdout/stderr into terminal_transcript.log and includes it in the return tarball.
# - v10.3: Runs one-event vac XMLs and one-event medium XMLs with unique seeds, sequentially, and logs every event.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
N_EVENTS="${N_EVENTS:-10}"
MAX_TRIES_PER_ACCEPTED="${MAX_TRIES_PER_ACCEPTED:-20}"
VAC_BASE_SEED="${VAC_BASE_SEED:-13000000}"
MED_BASE_SEED="${MED_BASE_SEED:-23000000}"
EXE="${EXE:-$ROOT/build/PythiaIsrMUSIC}"
RUN_TAG="${RUN_TAG:-pp_realistic_pair_Luke_v10_7_13TeV_paper_music_$(date +%Y%m%d_%H%M%S)}"
RUN_DIR="$ROOT/run_logs/$RUN_TAG"
DIAG_DIR="$ROOT/diagnostic_zips"
MAIN_XML="$ROOT/myanalysis/jetscape_main_Luke.xml"
VAC_TEMPLATE="$ROOT/myanalysis/jetscape_user_pp_realistic_vac_Luke.xml"
MED_TEMPLATE="$ROOT/myanalysis/jetscape_user_pp_realistic_medium_Luke.xml"
CLUSTER_CPP="$ROOT/myanalysis/tools/cluster_check.cpp"
CLUSTER_BIN="$RUN_DIR/cluster_check"
ATTEMPT_SUMMARY="$RUN_DIR/attempt_summary.tsv"
ACCEPTED_SUMMARY="$RUN_DIR/accepted_summary.tsv"
TERMINAL_TRANSCRIPT="$RUN_DIR/terminal_transcript.log"
DOCKER_CONTAINER="${DOCKER_CONTAINER:-xscape_mac}"
CONTAINER_ROOT="${CONTAINER_ROOT:-/home/jetscape-user/X-SCAPE}"
CONTAINER_EXE="${CONTAINER_EXE:-$CONTAINER_ROOT/build/PythiaIsrMUSIC}"
FORCE_DOCKER="${FORCE_DOCKER:-0}"
RUNTIME_MODE="host"
EXE_FILE_INFO="not_checked"
HOST_UNAME="$(uname -s 2>/dev/null || echo unknown)"
HOST_ARCH="$(uname -m 2>/dev/null || echo unknown)"

mkdir -p "$RUN_DIR/config" "$DIAG_DIR"
exec > >(tee -a "$TERMINAL_TRANSCRIPT") 2>&1

log() {
  printf '[%s] %s\n' "$(date '+%F %T')" "$*" | tee -a "$RUN_DIR/run_driver.log"
}

make_return_tarball() {
  find "$RUN_DIR" -maxdepth 6 -type f -print | sed "s#^$ROOT/##" | sort > "$RUN_DIR/file_list.txt" 2>/dev/null || true
  local tarball="$DIAG_DIR/${RUN_TAG}_RETURN.tar.gz"
  tar -czf "$tarball" -C "$ROOT" "run_logs/$RUN_TAG" 2>/dev/null || true
  printf '%s' "$tarball"
}

fail_setup() {
  log "SETUP_ERROR: $*"
  local tarball
  tarball=$(make_return_tarball)
  log "RETURN_TARBALL=$tarball"
  exit 2
}

render_xml() {
  local src="$1"
  local dst="$2"
  local seed="$3"
  local prefix="$4"
  python3 - "$src" "$dst" "$seed" "$prefix" <<'PYXML'
import sys
import xml.etree.ElementTree as ET
src, dst, seed, prefix = sys.argv[1:5]
tree = ET.parse(src)
root = tree.getroot()

def set_text(path, value):
    node = root.find(path)
    if node is None:
        raise SystemExit(f"missing XML path {path} in {src}")
    node.text = str(value)

set_text('outputFilename', prefix)
set_text('nEvents', '1')
set_text('setReuseHydro', 'false')
set_text('nReuseHydro', '1')
set_text('Random/seed', seed)
set_text('JetScapeWriterAscii', 'off')
set_text('JetScapeWriterFinalStateHadronsAscii', 'on')
set_text('Hard/PythiaGun/pTHatMin', '30.0')
set_text('Hard/PythiaGun/pTHatMax', '3000.0')
set_text('Hard/PythiaGun/eCM', '13000.0')
set_text('Hard/PythiaGun/softMomentumCutoff', '2.0')
set_text('JetHadronization/eCMforHadronization', '6500.0')
ET.indent(tree, space='  ')
tree.write(dst, encoding='unicode', xml_declaration=False)
PYXML
}

stage_case() {
  local mode="$1"
  local dir="$2"
  local template="$3"
  local seed="$4"
  local prefix="$5"
  mkdir -p "$dir"
  render_xml "$template" "$dir/input.xml" "$seed" "$prefix"
  cp "$ROOT/myanalysis/music_input_Luke" "$dir/music_input_Luke"
  cp "$ROOT/myanalysis/iSS_parameters.dat" "$dir/iSS_parameters.dat"
  cp "$ROOT/myanalysis/mcglauber.input" "$dir/mcglauber.input"
  ln -sfn "../../../../../myanalysis/EOS" "$dir/EOS"
  ln -sfn "../../../../../build/iSS_tables" "$dir/iSS_tables"
  ln -sfn "../../../../../build/tables" "$dir/tables"
}

extract_last_issue() {
  local log_file="$1"
  if [[ ! -f "$log_file" ]]; then
    printf 'missing_log'
    return
  fi
  local issue
  issue=$(grep -E "\[Error\]|\[Fatal\]|Can not|cannot|ERROR|Every line should|No freeze-out fluid cell|segmentation|Segmentation|abort|Abort|Exec format" "$log_file" | tail -1 | tr '\t' ' ' | sed 's/  */ /g' | cut -c1-220)
  [[ -n "$issue" ]] && printf '%s' "$issue" || printf 'none'
}

extract_surface_cells() {
  local log_file="$1"
  if [[ ! -f "$log_file" ]]; then
    printf 'NA'
    return
  fi
  awk '
    /Total number of MUSIC surface cells:/ {v=$NF}
    /total number of cells:/ {v=$NF}
    END {if (v=="") print "NA"; else print v}
  ' "$log_file"
}

classify_attempt() {
  local log_file="$1"
  local exit_code="$2"
  local bytes="$3"
  local cluster_exit="$4"
  if [[ "$exit_code" == "0" && "$bytes" -gt 0 && "$cluster_exit" == "0" ]]; then
    printf 'accepted'
    return
  fi
  if [[ -f "$log_file" ]] && grep -q "total number of cells: 0" "$log_file" && grep -q "Every line should have 36 variables" "$log_file"; then
    printf 'retry_zero_surface_empty_iSS'
    return
  fi
  if [[ -f "$log_file" ]] && grep -q "No freeze-out fluid cell" "$log_file"; then
    printf 'retry_no_freezeout_surface'
    return
  fi
  printf 'failed_nonretry_or_unknown'
}

cluster_file() {
  local had="$1"
  local outlog="$2"
  if [[ ! -x "$CLUSTER_BIN" ]]; then
    printf 'skipped_no_cluster_binary\n' > "$outlog"
    return 125
  fi
  "$CLUSTER_BIN" "$had" > "$outlog" 2>&1
}

ensure_docker_runtime() {
  command -v docker >/dev/null 2>&1 || fail_setup "Docker runtime requested but docker command was not found."
  if ! docker ps --format '{{.Names}}' | grep -Fxq "$DOCKER_CONTAINER"; then
    log "Docker container $DOCKER_CONTAINER is not running; attempting docker start $DOCKER_CONTAINER"
    docker start "$DOCKER_CONTAINER" >/dev/null || fail_setup "Could not start Docker container: $DOCKER_CONTAINER"
  fi
  docker exec "$DOCKER_CONTAINER" test -x "$CONTAINER_EXE" || fail_setup "Container executable not found or not executable: $DOCKER_CONTAINER:$CONTAINER_EXE"
  docker exec "$DOCKER_CONTAINER" test -f "$CONTAINER_ROOT/myanalysis/jetscape_main_Luke.xml" || fail_setup "Container does not see myanalysis at $CONTAINER_ROOT/myanalysis. Check Docker mount path or set CONTAINER_ROOT."
  docker exec "$DOCKER_CONTAINER" test -d "$CONTAINER_ROOT/myanalysis/EOS/neos_bqs" || fail_setup "Container does not see EOS under $CONTAINER_ROOT/myanalysis/EOS/neos_bqs."
  RUNTIME_MODE="docker"
}

select_runtime() {
  [[ -f "$EXE" ]] || fail_setup "Executable not found: $EXE"
  [[ -x "$EXE" ]] || fail_setup "Executable exists but is not executable: $EXE"
  EXE_FILE_INFO="$(file "$EXE" 2>/dev/null || echo unknown)"
  if [[ "$FORCE_DOCKER" == "1" ]]; then
    log "FORCE_DOCKER=1, using Docker runtime"
    ensure_docker_runtime
    return
  fi
  if [[ "$HOST_UNAME" == "Darwin" && "$EXE_FILE_INFO" == *"ELF"* ]]; then
    log "Detected macOS host with ELF PythiaIsrMUSIC; using Docker runtime instead of direct host execution."
    ensure_docker_runtime
    return
  fi
  RUNTIME_MODE="host"
}

run_xscape() {
  local rel_dir="$1"
  local host_dir="$ROOT/$rel_dir"
  if [[ "$RUNTIME_MODE" == "docker" ]]; then
    docker exec "$DOCKER_CONTAINER" bash -lc "cd \"$CONTAINER_ROOT/$rel_dir\" && \"$CONTAINER_EXE\" input.xml ../../../config/jetscape_main.xml" > "$host_dir/attempt.log" 2>&1
  else
    (
      cd "$host_dir" || exit 111
      "$EXE" input.xml ../../../config/jetscape_main.xml > attempt.log 2>&1
    )
  fi
}

run_attempt() {
  local mode="$1"
  local target_idx="$2"
  local try_idx="$3"
  local seed="$4"
  local template="$5"
  local prefix_base="$6"
  local dir="$RUN_DIR/${mode}/target_${target_idx}/try_${try_idx}_seed_${seed}"
  local rel_dir="run_logs/$RUN_TAG/${mode}/target_${target_idx}/try_${try_idx}_seed_${seed}"
  local out_prefix="${prefix_base}_${target_idx}_try_${try_idx}_seed_${seed}"
  stage_case "$mode" "$dir" "$template" "$seed" "$out_prefix"
  log "START mode=$mode target=$target_idx try=$try_idx seed=$seed prefix=$out_prefix runtime=$RUNTIME_MODE"
  run_xscape "$rel_dir"
  local exit_code=$?
  local had="$dir/${out_prefix}_final_state_hadrons.dat"
  local bytes=0
  local lines=0
  local cluster_exit=NA
  local particles=NA
  local jets=NA
  if [[ -f "$had" ]]; then
    bytes=$(wc -c < "$had" | tr -d ' ')
    lines=$(wc -l < "$had" | tr -d ' ')
  fi
  if [[ -f "$had" && "$bytes" -gt 0 ]]; then
    cluster_file "$had" "$dir/cluster_check.log"
    cluster_exit=$?
    particles=$(awk '/^particles /{print $2}' "$dir/cluster_check.log" | tail -1)
    jets=$(awk '/^jets_pt_gt_1 /{print $2}' "$dir/cluster_check.log" | tail -1)
    [[ -z "$particles" ]] && particles=NA
    [[ -z "$jets" ]] && jets=NA
  else
    printf 'missing_or_empty_hadron_file\n' > "$dir/cluster_check.log"
  fi
  local cells issue status
  cells=$(extract_surface_cells "$dir/attempt.log")
  issue=$(extract_last_issue "$dir/attempt.log")
  status=$(classify_attempt "$dir/attempt.log" "$exit_code" "$bytes" "$cluster_exit")
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$mode" "$target_idx" "$try_idx" "$seed" "$status" "$exit_code" "$had" "$bytes" "$lines" "$cells" "$cluster_exit" "$particles" "$jets" "$issue" \
    | tee -a "$ATTEMPT_SUMMARY" >/dev/null
  log "DONE mode=$mode target=$target_idx try=$try_idx status=$status exit=$exit_code hadron_bytes=$bytes hadron_lines=$lines cells=$cells cluster_exit=$cluster_exit jets=$jets issue=$issue"
  if [[ "$status" == "accepted" ]]; then
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
      "$mode" "$target_idx" "$try_idx" "$seed" "$had" "$bytes" "$lines" "$cells" "$particles" "$jets" \
      | tee -a "$ACCEPTED_SUMMARY" >/dev/null
    return 0
  fi
  return 1
}

run_mode_until_accepted() {
  local mode="$1"
  local template="$2"
  local prefix="$3"
  local base_seed="$4"
  local accepted=0
  local attempts=0
  local max_total=$((N_EVENTS * MAX_TRIES_PER_ACCEPTED))
  while [[ "$accepted" -lt "$N_EVENTS" && "$attempts" -lt "$max_total" ]]; do
    local target_idx try_idx seed
    target_idx=$(printf '%03d' $((accepted + 1)))
    try_idx=$(printf '%03d' $((attempts + 1)))
    seed=$((base_seed + attempts + 1))
    if run_attempt "$mode" "$target_idx" "$try_idx" "$seed" "$template" "$prefix"; then
      accepted=$((accepted + 1))
      log "ACCEPTED mode=$mode accepted=$accepted/$N_EVENTS seed=$seed"
    else
      log "RETRY mode=$mode target=$target_idx next_attempt=$((attempts + 2)) accepted=$accepted/$N_EVENTS"
    fi
    attempts=$((attempts + 1))
  done
  if [[ "$accepted" -lt "$N_EVENTS" ]]; then
    log "MODE_INCOMPLETE mode=$mode accepted=$accepted requested=$N_EVENTS attempts=$attempts max_total=$max_total"
    return 1
  fi
  log "MODE_COMPLETE mode=$mode accepted=$accepted requested=$N_EVENTS attempts=$attempts"
  return 0
}

log "ROOT=$ROOT"
log "RUN_DIR=$RUN_DIR"
log "N_EVENTS=$N_EVENTS"
log "MAX_TRIES_PER_ACCEPTED=$MAX_TRIES_PER_ACCEPTED"
log "HOST=$HOST_UNAME $HOST_ARCH"

[[ -f "$MAIN_XML" ]] || fail_setup "Missing main XML: $MAIN_XML"
[[ -f "$VAC_TEMPLATE" ]] || fail_setup "Missing vac XML template: $VAC_TEMPLATE"
[[ -f "$MED_TEMPLATE" ]] || fail_setup "Missing medium XML template: $MED_TEMPLATE"
[[ -f "$ROOT/myanalysis/mcglauber.input" ]] || fail_setup "Missing mcglauber.input"
[[ -d "$ROOT/myanalysis/EOS/neos_bqs" ]] || fail_setup "Missing myanalysis/EOS/neos_bqs"
[[ -d "$ROOT/build/tables" ]] || fail_setup "Missing build/tables"
[[ -d "$ROOT/build/iSS_tables" ]] || fail_setup "Missing build/iSS_tables"

select_runtime
log "EXE_FILE_INFO=$EXE_FILE_INFO"
log "RUNTIME_MODE=$RUNTIME_MODE"
if [[ "$RUNTIME_MODE" == "docker" ]]; then
  log "DOCKER_CONTAINER=$DOCKER_CONTAINER"
  log "CONTAINER_ROOT=$CONTAINER_ROOT"
  log "CONTAINER_EXE=$CONTAINER_EXE"
fi

cp "$MAIN_XML" "$RUN_DIR/config/jetscape_main.xml"

{
  echo "run_tag=$RUN_TAG"
  echo "root=$ROOT"
  echo "exe=$EXE"
  echo "exe_file_info=$EXE_FILE_INFO"
  echo "host=$HOST_UNAME $HOST_ARCH"
  echo "runtime_mode=$RUNTIME_MODE"
  echo "docker_container=$DOCKER_CONTAINER"
  echo "container_root=$CONTAINER_ROOT"
  echo "container_exe=$CONTAINER_EXE"
  echo "main_xml=$MAIN_XML"
  echo "vac_template=$VAC_TEMPLATE"
  echo "medium_template=$MED_TEMPLATE"
  echo "n_events=$N_EVENTS"
  echo "max_tries_per_accepted=$MAX_TRIES_PER_ACCEPTED"
  echo "vac_base_seed=$VAC_BASE_SEED"
  echo "medium_base_seed=$MED_BASE_SEED"
  echo "date=$(date)"
  echo
  echo "source_check:"
  if [[ -f "$ROOT/src/hydro/MusicWrapper.cc" && -f "$ROOT/myanalysis/active_source_files/src/hydro/MusicWrapper.cc" ]]; then
    cmp -s "$ROOT/src/hydro/MusicWrapper.cc" "$ROOT/myanalysis/active_source_files/src/hydro/MusicWrapper.cc" && echo "MusicWrapper.cc=matches_active_copy" || echo "MusicWrapper.cc=DIFFERS_FROM_ACTIVE_COPY"
  else
    echo "MusicWrapper.cc=not_checked"
  fi
  if [[ -f "$ROOT/external_packages/music/src/evolve.cpp" && -f "$ROOT/myanalysis/active_source_files/external_packages/music/src/evolve.cpp" ]]; then
    cmp -s "$ROOT/external_packages/music/src/evolve.cpp" "$ROOT/myanalysis/active_source_files/external_packages/music/src/evolve.cpp" && echo "evolve.cpp=matches_active_copy" || echo "evolve.cpp=DIFFERS_FROM_ACTIVE_COPY"
  else
    echo "evolve.cpp=not_checked"
  fi
} > "$RUN_DIR/run_manifest.txt"

if command -v fastjet-config >/dev/null 2>&1 && [[ -f "$CLUSTER_CPP" ]]; then
  log "Compiling FastJet cluster checker on host"
  c++ "$CLUSTER_CPP" -o "$CLUSTER_BIN" $(fastjet-config --cxxflags --libs) > "$RUN_DIR/cluster_compile.log" 2>&1
  compile_exit=$?
  if [[ $compile_exit -ne 0 ]]; then
    log "FastJet cluster checker compile failed; clustering will be skipped. See $RUN_DIR/cluster_compile.log"
    rm -f "$CLUSTER_BIN"
  fi
else
  log "fastjet-config or cluster_check.cpp not found on host; clustering will be skipped"
  printf 'fastjet-config_or_cluster_cpp_missing\n' > "$RUN_DIR/cluster_compile.log"
fi

printf 'mode\ttarget_index\ttry_index\tseed\tstatus\texit_code\thadron_file\thadron_bytes\thadron_lines\tsurface_cells\tcluster_exit\tparticles\tjets_pt_gt_1\tlast_issue\n' > "$ATTEMPT_SUMMARY"
printf 'mode\taccepted_index\ttry_index\tseed\thadron_file\thadron_bytes\thadron_lines\tsurface_cells\tparticles\tjets_pt_gt_1\n' > "$ACCEPTED_SUMMARY"

overall_status=0
run_mode_until_accepted "vac" "$VAC_TEMPLATE" "pp_realistic_vac" "$VAC_BASE_SEED" || overall_status=1
run_mode_until_accepted "medium" "$MED_TEMPLATE" "pp_realistic_medium" "$MED_BASE_SEED" || overall_status=1

log "Creating diagnostic tarball"
TARBALL=$(make_return_tarball)
log "RETURN_TARBALL=$TARBALL"
log "ATTEMPT_SUMMARY=$ATTEMPT_SUMMARY"
log "ACCEPTED_SUMMARY=$ACCEPTED_SUMMARY"
printf '\nDONE\nReturn tarball: %s\nAttempt summary: %s\nAccepted summary: %s\nTerminal transcript: %s\n' "$TARBALL" "$ATTEMPT_SUMMARY" "$ACCEPTED_SUMMARY" "$TERMINAL_TRANSCRIPT"
exit "$overall_status"
