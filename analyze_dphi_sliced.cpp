// analyze_dphi_sliced.cpp // v9.9.0
/*
HOW TO COMPILE (compute node only; do NOT build on the login/head node)
------------------------------------------------------------
module purge
module load gnu7/7.3.0 root/6.28.10 fastjet/3.4.0
g++ -std=c++17 -O3 analyze_dphi_sliced.cpp -o analyze_dphi_sliced \
   $(fastjet-config --cxxflags --libs) $(root-config --cflags --glibs)


CHANGELOG

v9.9.0 (2026-04-29; true single-slice count-density histograms):
  • NEW: Add parallel unweighted count-density TH1 histograms under counts/ and nosubfrac/counts/ for dijet-normalized 1D observables.
  • NEW: Count histograms mirror Mjj, |#Delta#phi|, xJ, AJ, and dijet-selected lead/sublead jet-pT histograms while preserving all existing weighted d#sigma histogram names.
  • LOG/VALIDATION: Book, scale by bin width, write, inventory, and validate the new count_* ROOT objects so SINGLE_SLICE_MODE comparisors can plot true (1/N_dijet,sel)dN/dX.
  • SAFETY: No particle selection, jet finding, cuts, pThat weighting, weighted histogram names, or selected-dijet metadata changed.

v9.8.1 (2026-04-25; compile fix after raw-dphi removal):
  • FIX: Correct a misplaced brace in the no-subfrac |Δφ|/|Δη| pT-binned fill block introduced while removing obsolete raw dphi_R* histograms.
  • FIX: Remove the remaining stale rr.dphi[...] fill call from the default branch so the removed raw dphi_R* family is gone cleanly.
  • SAFETY: No event selection, weights, binning, ROOT object names, or physics formulas changed relative to v9.8.0.

v9.8.0 (2026-04-25; retire raw 0..2π Δφ histograms + publish TH2 densities):
  • CHANGE: Remove obsolete non-absolute dphi_R* ROOT histograms in [0,2π) from booking, filling, validation, writeout, selected-count metadata, and ROOT inventory logging.
  • CHANGE: Keep only the physics-facing dphi_abs_R* family for dijet azimuthal separation, using the minimal |Δφ| definition on [0,π].
  • FIX: Normalize h2_dphi_abs_vs_deta_* maps by the two-dimensional bin area so their z-axis is d²σ/(d|Δφ| d|Δη|) [mb/rad] instead of mb/bin.
  • FIX: Count h2_dphi_abs_vs_deta_* TH2 objects in the booked-histogram inventory and refresh stale full-range example text/log wording.
  • META: Replace raw-dphi selected-count metadata with dijet_base_* counts for generic selected-dijet denominators; keep dphi_abs_* counts for |Δφ| outputs.
  • SAFETY: No particle selection, jet finding, SUBFRAC, y*, xJ/AJ, Mjj, or pThat weighting formulas changed.

v9.7.3 (2026-04-08; new diagnostic |#Delta#phi| vs |#Delta#eta| histograms):
  • NEW: Add dijet-pair TH2 histograms of |#Delta#phi| vs |#Delta#eta| for every enabled R in BOTH branches (default and nosubfrac).
  • NEW: Publish the new observable both in leading-jet-p_{T}-binned form and as the existing advertised full-range lead-p_{T} contract.
  • LOG/VALIDATION: Add the new histogram family to the analyzer ROOT writeout, recursive inventory, and required-key validation.
  • SAFETY: No event selection, weighting, SUBFRAC logic, back-to-back gates, or existing histogram formulas changed in this patch.

v9.7.2 (2026-03-18; metadata/logging honesty for Mjj back-to-back config):
  • FIX (meta/log): Write MJJ_REQUIRE_BACKTOBACK into the slice_meta JSON config block so the emitted analyzer metadata matches the documented/logged configuration banner.
  • FIX (versioning): Update the internal analyzer version macro to v9.7.2 so --version output, startup logs, and the file header stay in sync.
  • SAFETY: No histogram content, event selection, weighting, or downstream ROOT object names changed in this patch.

v9.7.1 (2026-03-16; analyzer full-range honesty + explicit Mjj back-to-back knob):
  • FIX (selection bookkeeping): Keep dijet-selected full-range histograms/counts honest to their advertised PT_LEAD_BIN_EDGES range by requiring p_{T,1} to fall inside [PT_LEAD_BIN_EDGES.front(), PT_LEAD_BIN_EDGES.back()] with the last edge inclusive.
  • FIX (binning): Make the last leading-jet p_{T} bin inclusive on its upper edge so exact-edge events are not silently dropped from pt-binned Δφ/|Δφ|/x_{J}/A_{J} bookkeeping.
  • FIX (labels/logging): Remove the literal PT_LEAD_BIN_EDGES token from the TProfile ROOT titles and make the constituent-acceptance log text match the implemented strict |η|<PARTICLE_ETA_MAX cut.
  • NEW: Read required MJJ_REQUIRE_BACKTOBACK=0|1 from jetscape.ini, hard-fail if missing/invalid, and apply the extra Mjj back-to-back cut only when enabled.
  • META/LOG: Publish MJJ_REQUIRE_BACKTOBACK to the analyzer JSON/config banner so downstream tools can keep Mjj titles honest.

v9.7.0 (2026-03-16; analyzer observable p_{T,1}-bin policy cleanup + explicit full-range naming):
  • PHYSICS/ANALYSIS SCOPE: Keep leading-jet-p_{T}-binned histograms for #Delta#phi / |#Delta#phi| and ADD leading-jet-p_{T}-binned histograms for x_{J} / A_{J}, using PT_LEAD_BIN_EDGES from jetscape.ini in both default and nosubfrac branches.
  • PHYSICS/ANALYSIS SCOPE: REMOVE leading-jet-p_{T}-binned M_{jj} histograms and their selected-dijet count bookkeeping so M_{jj} is published only as the full configured leading-jet range, matching the intended more-standard presentation.
  • NAMING/LABELS: Replace vague "all" naming for dijet-selected full-range histograms with explicit leading-jet ranges [PT_LEAD_BIN_EDGES.front(), PT_LEAD_BIN_EDGES.back()] in histogram names and ROOT titles for dphi_abs/h2_dphi_abs_vs_deta, xJ/AJ, Mjj, eta_lead/sub, jetpt_lead/sub, and lead-sublead correlation histograms.
  • META/LOG: selected_dijet_counts JSON and analyzer logs now publish xj_ptlead_per_R and aj_ptlead_per_R instead of mjj_ptlead_per_R, consistent with the updated observable policy.
  • SAFETY: No simulation inputs, event weighting, dijet cuts, or inclusive jet histograms changed in this patch; only observable booking/filling/output metadata were updated.

v9.6.7 (2026-03-16; analyzer meta: observable-specific selected dijet counts for single-slice 1/N plots):
  • META: Record observable-specific selected dijet-event / analyzed-dijet-pair counts into slice_meta JSON for BOTH branches (default and nosubfrac).
  • META: New JSON blocks include per-R counts for dphi, |dphi|, xJ, AJ, and Mjj plus per-leading-pT-bin counts for dphi, |dphi|, and Mjj.
  • LOG: Print the same observable-specific selected dijet counts in the analyzer log so single-slice denominator debugging is transparent before any downstream merge/fitter updates.
  • SAFETY: Existing histogram filling, ROOT object names, old JSON fields, and current workflow behavior remain unchanged; this patch only adds bookkeeping needed for honest 1/N_dijet-style labels later.

v9.6.6 (2026-03-11; y* promoted to all dijet-pair histograms + particle-level QA title honesty):
  • FIX (physics/selection scope): When YSTAR_ENABLE=1, apply the rapidity-based dijet centrality cut |y*| = |y1-y2|/2 < YSTAR_MAX to all dijet-pair histograms, not only Mjj.
    Affected histogram families in both the default and nosubfrac branches: jetpt_lead_*, jetpt_sublead_*, h2_sublead_vs_lead_*, prof_sublead_vs_lead_*, xj_*, aj_*, dphi_*, dphi_abs_*, eta_lead_*, eta_sub_*, and mjj_*.
    Explicitly NOT affected: particle_pt_all, particle_eta_all, particle_phi_all, and jetpt_incl_*.
  • FIX (title honesty): Update the ROOT histogram titles of the dijet-pair observables above so they advertise the optional |y^{*}|<YSTAR_MAX gate when enabled. Histogram names/paths are unchanged.
  • FIX (labeling): Rename the particle-level QA histogram titles/y-axis labels to state that they are inclusive cross-section-weighted accepted-constituent yields, preventing misreading as per-event or per-jet normalized spectra.
  • LOG: Update the one-time histogram cut map so it documents the new y* scope correctly.

v9.6.5 (2026-03-11; status-filter comment hygiene):
  • DOC: Fix the stale inline PARTICLE_STATUS_FILTER comment in the config section so it matches the implemented auto-detect behavior.
    PARTICLE_STATUS_FILTER=1 means auto-detect the final-state hadron status convention and keep the appropriate final-state set; 0 keeps all statuses.
  • DOC: No analysis logic, physics cuts, histogram content, or output schema changed in this patch.

v9.6.4 (2026-03-10; lead-vs-sublead dijet p_{T} correlation observables):
  • NEW: Add all-range 2D dijet p_{T} correlation histograms h2_sublead_vs_lead_Rxxx_all for each enabled R.
  • NEW: Add TProfile observables prof_sublead_vs_lead_Rxxx_ptleadbins using PT_LEAD_BIN_EDGES as the leading-jet x bins and storing <p_{T,sublead}> in each leading-jet bin.
  • NEW: Book, fill, validate, write, and inventory both observables in the default branch and the parallel nosubfrac/ branch.
  • AXES: Use the same jet-spectrum p_{T} range/binning as jetpt_lead / jetpt_sublead for the 2D maps, and the configured PT_LEAD_BIN_EDGES for the profiled observable requested by Claude.
  • LOGIC: Fill after the same dijet cuts as jetpt_lead / jetpt_sublead; in the NO-SUBFRAC branch they are filled before SUBFRAC, and in the default branch after SUBFRAC.

v9.6.3 (2026-03-10; accepted particle-level constituent QA histograms):
  • NEW: Add particle_pt_all, particle_eta_all, and particle_phi_all histograms for accepted particle-level constituents.
  • LOGIC: Fill them after status filtering, CLUSTER_MIN, PARTICLE_ETA_MAX, and charged/full constituent-mode filtering,
    and before anti-k_{T} clustering or any jet-level, dijet-level, SUBFRAC, back-to-back, or y* cuts.
  • PLOTS: Use analysis-standard axes/titles: log-binned p_{T}, symmetric #eta over ±PARTICLE_ETA_MAX, and #phi over [-#pi,#pi].
  • SAFETY: Add the new histograms to ROOT writeout and required-key validation so missing particle-level QA objects hard-fail the task.

v9.6.2 (2026-03-09; Mjj title honesty for downstream ROOT inspection):
  • FIX (titles): Mjj histogram titles now state the actual dijet gate used to fill them: exact-2 vs leading-two-of->=2,
    the Mjj back-to-back requirement |#Delta#phi-#pi|<DIJET_BACKTOBACK_TOL_DEG, and the optional |y^{*}|<YSTAR_MAX cut.
  • FIX (titles): Preserve existing histogram names/paths so merge and Python plotting code remain unchanged; this is title-only metadata clarity.

v9.6.1 (2026-03-09; eta-axis honesty for per-R jet acceptance):
  • FIX (histogram honesty): Book eta_lead/eta_sub histograms over the actual accepted jet-axis range [-etaMaxJet, +etaMaxJet] for each R
    instead of the raw ±JET_ETA_MAX range. This keeps ETA_NBINS fixed while making the ROOT x-axis match the real selection.
  • FIX (titles): Include the effective jet acceptance |#eta_{jet}|<etaMaxJet in eta histogram titles for both default and nosubfrac branches.
  • FIX (versioning): Update the analyzer version macro/banner/meta string to v9.6.1 so logs and slice_meta match the file header.

v9.6.0 (2026-03-09; required exact-2 dijet knob + stricter config logging):
  • NEW (required config): Read DIJET_REQUIRE_EXACTLY_TWO_JETS=0|1 from jetscape.ini; missing/empty values now hard-fail at startup.
      - 0: dijet-dependent histograms keep the previous inclusive dijet selection (require >=2 accepted jets, use the leading two).
      - 1: dijet-dependent histograms require exactly 2 accepted jets after the jet pT/eta acceptance cuts.
  • LOG: Print the resolved DIJET_REQUIRE_EXACTLY_TWO_JETS mode in the startup config banner, histogram cut-map text, cutflow summary, and slice_meta JSON.
  • NOTE: Inclusive jet spectra remain inclusive in both modes; the new knob only changes the dijet event selection gate.

v9.5.3 (2026-03-09; logging honesty: status-filter text + recursive ROOT inventory):
  • FIX (logging): Replace stale PARTICLE_STATUS_FILTER=1 banner text with the current meaning:
    1 now means auto-detect the hadron status convention and keep the appropriate final-state set; 0 keeps all statuses.
  • FIX (logging): Make the post-write ROOT inventory recurse into subdirectories and print full key paths,
    so nosubfrac/ objects are counted and listed honestly instead of only scanning top-level keys.

v9.5.2 (2026-03-08; config strictness: remove hidden PARTICLE_STATUS_FILTER default):
  • BREAKING (config): PARTICLE_STATUS_FILTER is now REQUIRED in jetscape.ini / [ANALYSIS].
    The analyzer no longer silently defaults to 1 when the key is absent. Missing/empty values now hard-fail at startup.
  • FIX (versioning): Update the analyzer version macro/banner/meta string to v9.5.2 so logs and slice_meta match the file header.

v9.5.1 (2026-03-06; doc cleanup only):
  • DOC: Update PARTICLE_STATUS_FILTER comments/changelog notes to match the current auto-detect behavior
    implemented since v9.4.9. No analysis logic changed.

v9.5.0 (2026-03-06; stats + validation + cutflow consistency fixes):
  • FIX (statistics): Restore event-level variance bookkeeping for inclusive jet spectra (jetpt_incl_*).
    When multiple accepted jets from the same event land in the same pT bin, the analyzer now fills that bin once per event
    with the summed event weight for that bin, so Sumw2 stores (Σ_event w_bin)^2 instead of undercounting it as Σ_jets w^2.
    Central values are unchanged; uncertainty bars are now statistically consistent for event-weighted MC.
  • FIX (ROOT validation): Validate the full downstream-used histogram set, not just a shallow top-level subset.
    Added checks for per-pT-binned Δφ / |Δφ| / Mjj histograms and for the complete nosubfrac/ branch objects.
  • FIX (cutflow accounting): Process empty accepted events too, so cutflow events_total now matches events_seen/event headers.
    Previously events with zero kept constituents after filtering incremented events_seen but skipped the cutflow loop.

v9.4.9 (2026-03-01; bugfix: auto-detect hadron ASCII status conventions to avoid filtering everything):
  • FIX: PARTICLE_STATUS_FILTER=1 now auto-detects status conventions:
        - If status==-1 is present: keep st>=0 (reject -1 backreaction holes)
        - Else if statuses look like 0/1: keep st==0 or 1
        - Else (e.g. status 83/84 like your file): disable status filtering (keep all) with a warning.
         This prevents the analyzer from accidentally rejecting every constituent when the hadron
         writer uses status=1 for final-state hadrons.
  • ADD: Separate counters for status==1 in logs + meta JSON.

v9.4.7 (2026-03-01; physics safety: particle status filter for recoil/backreaction):
  • NEW: Read PARTICLE_STATUS_FILTER=0|1 from jetscape.ini (default 1).
         - 1: auto-detect status conventions and keep the appropriate final-state set
         - 0: keep all particle statuses (debug).
  • ADD: Log aggregated particle status counters (status0, status-1, status_other, skipped_by_status).
  • ADD: Write particle status filter config + counters into per-task meta JSON.
  • NOTE: No changes to physics cuts beyond optional status filtering; the later auto-detect logic superseded the old status==0-only wording.


v9.4.6 (2026-02-28; bugfix: correct inclusive jet spectrum Sumw2):
  • FIX: Fill jetPtIncl once per jet (Fill(j.pt(), weight)) so Sumw2 accumulates Σw² correctly.
         (Previous per-event per-bin filling inflated uncertainties when >1 jet landed in a bin.)

v9.4.5 (2026-02-27; consistency: nosubfrac hist binning/labels + clarify pass counters):
  • FIX: Make NO-SUBFRAC jet pT lead/sublead histograms use the SAME variable bin edges (jetpt_edges) as the DEFAULT branch.
  • FIX: Make NO-SUBFRAC axis labels consistent with DEFAULT for η, xJ, AJ (use dσ/dX [mb] style labels).
  • ADD: Clarify SLURM log “passed(R=...)” lines as DEFAULT-after-SUBFRAC, and print the corresponding NO-SUBFRAC pass counts separately.
  • NOTE: Physics selection unchanged; only histogram binning/labels and log counters clarified.

v9.4.4 (2026-02-27; logging: print per-cut pass counts + jet/particle breakdown; fix nosubfrac Mjj booking):
  • ADD: Print per-R event-level cutflow counters at end of job for BOTH analysis branches:
      - >=2 accepted jets, lead pT cut, sublead pT cut,
      - SUBFRAC (default branch only),
      - imbalance back-to-back (xJ/AJ) and Mjj back-to-back,
      - y* counts (only when YSTAR_ENABLE=1).
  • ADD: Print constituent cut breakdown in logs (clusterMin vs particleEta) instead of only the combined after_pt_eta.
  • ADD: Print jet acceptance breakdown per R in logs (raw jets vs pt cut vs eta cut vs combined), aggregated over all events.
  • FIX: Book + fill NO-SUBFRAC Mjj histograms for both linear and log binning (previously missing when MJJ_LOG_BINS=1).
  • NOTE: Physics selection unchanged; only logging + intended output completeness for NO-SUBFRAC Mjj.

v9.4.3 (2026-02-27; build fix: restore headerHits counter declaration):
  • FIX: Reintroduce the missing headerHits counter (used for '[INFO] Event headers matched') so GCC7 builds cleanly.
  • NOTE: Physics output unchanged; logging only.

v9.4.2 (2026-02-27; build fix: cutflow logger scope/order):
  • FIX: Define CutFlow + cutflow vectors + print_histogram_map() before first use (previous patch referenced them before declaration, causing build failure).
  • FIX: Use subFracMin (configured SUBFRAC) in log text (was a stale variable name).
  • NOTE: Physics output unchanged; logging only.

v9.4.1 (2026-02-27; build fix: logging string literals):
  • FIX: Replace accidental multiline string literals in the new histogram cut-map logger with compile-safe std::cout stream lines (GCC7-compatible).
  • NOTE: Physics output unchanged; logging only.

v9.4 (2026-02-27; logging: detailed cutflow + histogram inventory):
  • ADD: Per-R cutflow counters for BOTH analysis branches:
      - default (WITH SUBFRAC cut) and the extra NO-SUBFRAC histograms
      - lead/sublead pT cuts, optional imbalance back-to-back, Mjj back-to-back, optional y* cut
  • ADD: One-time “histogram map” printed to logs that documents which cuts apply to which histogram groups.
  • ADD: ROOT output inventory: counts by histogram family (jetpt/dphi_abs/h2_dphi_abs_vs_deta/xj/aj/eta/mjj) and nosubfrac vs default,
        plus a compact list of the first N key names for sanity.
  • NOTE: Physics output unchanged; this is logging only.

v9.3 (2026-02-26; bugfix: restore undefined histogram range vars):
  • FIX: Replace undefined legacy variables (eta_range/jetpt_min/max/xj_min/max/aj_min/max)
    with the configured ranges already in use elsewhere:
      - η nosubfrac histos use ±JET_ETA_MAX (jetEtaMaxRaw)
      - jet pT nosubfrac histos use [JET_PT_MIN, JET_PT_MAX] (jetPtMin/jetPtMax)
      - xJ/AJ nosubfrac histos use [0,1] like the default histos.

v9.2 (2026-02-26; build fix: drop <filesystem> for GCC7):
  • FIX: Removed dependency on <filesystem> (not available on GCC 7 libstdc++ on WSU Grid).
    File size is now obtained via POSIX stat(), preserving behavior while restoring build compatibility.

v9.1 (2026-02-26; new: parallel dijet observables without SUBFRAC cut):
  • NEW: Keep existing (default) dijet-selected histograms exactly as-is (they still apply SUBFRAC when SUBFRAC>0).
  • NEW: Add a second set of dijet-selected histograms that DO NOT apply the SUBFRAC cut (all other cuts unchanged).
    These are written into the ROOT subdirectory: nosubfrac/
    Histogram names carry the suffix: _nosubfrac
    Titles explicitly include: (no SUBFRAC)

v9.0 (2026-02-26; robustness: ROOT output integrity + meta status):
  • NEW: After writing the per-task ROOT output, perform strict integrity checks:
      - reopen the file in READ mode,
      - reject IsZombie() and kRecovered files,
      - verify non-empty key list,
      - verify presence of expected histogram keys for each enabled R.
  • NEW: Record ROOT validation results into slice_meta JSON (root_status/root_validation/...)
    so merge can quickly skip bad files without probing ROOT.
  • NEW: If ROOT validation fails, exit nonzero so the analysis manager auto-resubmits the task.

v8.9 (2026-02-23; hotfix: compile-safe y* note + changelog hygiene):
  • FIX: Replace accidental multiline string literal in the YSTAR note log with a proper single-line stream output ending with \\n (prevents compilation failure).
  • DOC: Add missing v8.8 changelog entry (v8.8 patch shipped without header note).

v8.8 (2026-02-23; robustness: edge clamping + config validation/meta):
  • FIX: Clamp |Δφ| fills at the upper edge (|Δφ|==π) using std::nextafter(M_PI,0) so exact-edge values land in the last bin instead of ROOT overflow (hist range remains [0,π]).
  • FIX: Clamp xJ fills at the upper edge (xJ==1) using std::nextafter(1,0) so exact-edge values land in the last bin instead of ROOT overflow (hist range remains [0,1]).
  • SAFETY: Validate JETPT_BIN_EDGES are strictly increasing and finite; hard-fail with clear diagnostics if malformed.
  • META: Record JET_PT_MAX in slice_meta JSON config for reproducibility.
  • LOGS: Store and print the first 10 unique unknown PDG IDs encountered (charged-mode debugging).
  • NOTE: If YSTAR_ENABLE=1, emit a note about η-acceptance vs rapidity-based y* (no behavior change).


v8.7 (2026-02-23; physics: optional charged-track jets via ini):
  • NEW: Add required jetscape.ini key JET_CONSTITUENTS_MODE ("charged" or "full").
    - charged: only charged final-state hadrons are clustered (ALICE-style charged-track jets).
    - full: all final-state hadrons are clustered (previous behavior; "full" truth jets).
  • SAFETY: Hard-fail if JET_CONSTITUENTS_MODE is missing or not one of {charged, full}.
  • LOGS: Print resolved JET_CONSTITUENTS_MODE, CLUSTER_MIN, PARTICLE_ETA_MAX at startup and
    report total kept/rejected (charged vs neutral) constituents at end of run.
  • META: Record JET_CONSTITUENTS_MODE and constituent selection counters in slice_meta JSON.
  • FIX: Version printed in logs/--version and stored in slice_meta now matches the file version (single source constant).

v8.6 (2026-02-22; physics: decouple jet spectrum binning from PT_LEAD_BIN_EDGES):
  • NEW: Read optional JET_PT_MAX from jetscape.ini (upper pT bound for jet spectra histograms).
  • FIX (physics/binning): For JETPT_BINS_MODE=logspace, build jet pT bin edges over [JET_PT_MIN, JET_PT_MAX]
    instead of [max(JET_PT_MIN, PT_LEAD_BIN_EDGES.front), PT_LEAD_BIN_EDGES.back].
    This restores intended low-pT coverage (e.g. 15–30 GeV) and prevents high-pT events from going to overflow
    just because the leading-jet slicing bins stop at a lower value.
  • Backward-compat: If JET_PT_MAX is missing, fall back to PT_LEAD_BIN_EDGES.back with a loud warning.

v8.5 (2026-02-22)
  - FIX (stats): fill inclusive jet pT spectrum (jetPtIncl) with per-event bin-summed weights
    so TH1::Sumw2 reflects event-level variance for multi-jet events. Central values unchanged;
    error bars become statistically honest when multiple jets occur per event.

v8.4 (2026-02-22; label clarity: dijet-selected jet spectra):
  • DOC/plots: Updated jetpt_lead_* and jetpt_sublead_* histogram titles to explicitly state they are filled
    after dijet selection (lead/sublead pT cuts + SUBFRAC). This prevents misinterpretation as inclusive spectra.

v8.3 (bugfix: correct histogram booking scope + safe Mjj fill):
  • Fixed missing closing brace in pT-binned histogram booking loop. Prevents repeated allocation,
    pointer overwrites/leaks, and ROOT object name collisions.
  • Guarded all Mjj histogram fills behind mjj_enable and pointer/vector size checks to avoid
    null dereference if MJJ is disabled in jetscape.ini.

v8.2 (2026-02-22; enforce sigma footer contract):
  • FIX (actually enforce): If sigmaGen and/or sigmaErr are missing/NaN/non-positive in the hadron ASCII comment footer,
    the analyzer now exits nonzero BEFORE writing ROOT/JSON outputs.
  • LOGS: Print the last sigma footer line seen (when present) to make bad/missing footers obvious in SLURM logs.

v8.1 (2026-02-21; bookkeeping):
  • DOC: Added missing v8.0 changelog entry (v8.0 code shipped without its header notes).
  • No behavior changes vs v8.0; this is purely version+changelog hygiene to prevent “which binary is this?” confusion.

v8.0 (2026-02-21; config correctness + multi-R compatibility):
  • BREAKING (safety): Removed silent fallback defaults for analysis configuration. Required keys MUST exist in jetscape.ini or the analyzer exits nonzero.
  • FIX (config parity): Support global KEY=VALUE jetscape.ini format directly (global keys), while still accepting legacy [ANALYSIS] section keys.
    Search order is <global> first, then [ANALYSIS].
  • NEW (debuggability): Log every configuration value read from jetscape.ini with its resolved source (global vs [ANALYSIS]).
  • FIX (compatibility): Standardize jet-radius tags in histogram names to R*100 (R020, R040, R050, R060) to match Python tools.
  • FIX (keys): Use jetscape.ini canonical names (with legacy aliases):
      - JET_RADIUS_LIST (alias JET_R_LIST)
      - SUBFRAC (alias SUBFRAC_MIN)
      - DIJET_BACKTOBACK_TOL_DEG (alias DPHI_TO_PI_TOL_DEG)
      - MJJ_ENABLE, XJ_NBINS, AJ_NBINS are now read and applied.
  • FIX (physics definition): Make jetpt_incl_* truly inclusive (filled for all jets passing base selection, not only dijet-selected events).
  • FIX (ROOT labels): Update η/xJ/AJ histogram y-axis labels to explicitly indicate differential densities after Scale("width").

v7.0 (2026-02-21; robustness: safe η for constituents):
  • FIX (numerics): Replace η = 0.5*log((p+pz)/(p-pz)) with a stable computation η = asinh(pz/pT).
    This avoids NaN/inf poisoning when p≈|pz| or pT→0, and cleanly rejects undefined cases (pT=0 & pz=0).
  • No physics intent change: this only hardens the constituent acceptance cut |η|<PARTICLE_ETA_MAX.

v6.9 (2026-02-21; compile hotfix):
  • FIX: Removed accidental literal newlines inside C++ string literals (was a hard compile failure).
  • No physics/logic changes: output content unchanged, only newline formatting.

v6.8 (2026-02-21; xsec strict + jet pT binning default fix):
  • BREAKING (cleanup): Removed legacy "Step A" xsec/xsecerr file inference based on weight-file directory.
    The analyzer now ONLY uses sigmaGen/sigmaErr parsed from hadron ASCII comments (JetScapeWriterFinalStateHadronsAscii).
  • SAFETY (hard fail): If sigmaGen and/or sigmaErr cannot be parsed (missing/NaN/non-positive), the analyzer exits nonzero.
    This prevents silent xsec_mb=-1 JSON sidecars and downstream "unknown" normalization.
  • FIX (physics/binning): Jet pT spectrum histograms now default to PT_LEAD_BIN_EDGES from jetscape.ini.
    Optional overrides:
      - JETPT_BIN_EDGES="..." to fully control edges
      - JETPT_BINS_MODE=logspace with JETPT_NBINS to restore old fine log-spaced binning.

v6.7 (2026-02-21; hotfix):
  • FIX: Repair two broken std::cerr string literals that made the file uncompilable.
    (No physics/analysis behavior change.)

v6.6 (2026-02-20; parser correctness + configurable imbalance cut + η histogram comparability + log bins tidy):
  • FIX (parser): Strip inline '#' comments only when '#' is OUTSIDE quotes (quote-aware), preserving values like EVENT_HEADER_PREFIX="#\tEvent".
  • FIX (physics/config): Read IMBALANCE_BACKTOBACK_TOL_DEG from jetscape.ini and apply it to xJ/AJ back-to-back requirement (no more hard-coded 0.5 rad).
  • FIX (plot comparability): Book η histograms with a constant range [-JET_ETA_MAX, +JET_ETA_MAX] for all R while keeping the selection cut |η_jet|<etaMaxJet (may shrink with R).
  • FIX (code consistency): Use natural-log spacing in make_mjj() to match make_log_edges() convention (bin edges unchanged in practice).

v6.5 (2026-02-20; bugfix + physics correctness sweep):
  • FIX (version): Update version constant to match changelog (was 6.3, now 6.5).
  • FIX (code quality): Remove duplicate line "rh[ir].R = R; rh[ir].etaMaxJet = etaMaxJet;" at histogram initialization.
  • FIX (parser): C++ parse_ini() now strips inline '#' comments from string values (previously only worked for numeric values due to std::stod/stoi stopping at whitespace).
  • FIX (physics): Apply LEAD_PT_MIN and SUBLEAD_PT_MIN cuts when both are defined in ini file (previously only JET_PT_MIN and SUBFRAC were enforced).
  • FIX (physics): Implement IMBALANCE_REQUIRE_BACKTOBACK=1 for xJ/AJ histograms: now requires |Δφ(j1,j2) - π| < 0.5 rad when flag is set.
  • All fixes ensure C++ analyzer behavior matches the documented physics intent in jetscape.ini.

v6.4 (2026-02-20; acceptance + units + metadata fixes):
  • FIX (physics): actually APPLY the jet-axis η acceptance per R using JET_ETA_MAX + JET_ETA_MODE:
      - mode=1: |η_jet| < (JET_ETA_MAX − R)
      - mode=0: |η_jet| < JET_ETA_MAX
    Implemented via fastjet::SelectorAbsEtaMax(etaMaxJet) so it affects lead/sublead selection, inclusive jet spectra, Mjj fills, and xJ/AJ/Δφ.
  • FIX (units): normalize Δφ_abs histograms (dphi_abs_*) with Scale(1,'width') so contents are mb/rad (not mb/bin).
  • FIX (metadata): robust slice_tag parsing for current underscore format <RUN_TAG>_<L>_<H>_<T> plus legacy forms; JSON now records correct pthat_low/high and task id.
  • FIX (robustness): PT_LEAD_BIN_EDGES read via safe fallback (no cfg.at() throw).
  • FIX (build): remove a stray duplicated line in the xsec filename derivation block that could break compilation.


v6.2 (stats: enforce stored variances via Sumw2 for all histograms):
  • NEW: TH1::SetDefaultSumw2(true) so every histogram carries proper Sumw2.
  • This makes Python loaders strict: variances are mandatory (no sqrt(y) fallback).
  • No physics changes; only uncertainty bookkeeping correctness.

v6.1 (bugfix: fix accidental escaped quotes in Δφ_abs histogram booking):
  • FIX: Replace Form(\"...\") with Form("...") in Δφ_abs histogram definitions.
  • This was a text-escaping artifact that breaks compilation (stray '\\' and missing quotes).
  • No physics logic changes; only string literals.

v6.0 (feature: add standard Δφ_abs in [0,π] alongside existing oriented Δφ in [0,2π)):
  • NEW: Compute Δφ_abs = |wrap(φ1−φ2)| (minimal absolute separation) and histogram it in [0,π].
  • NEW: Write parallel histograms:
      - dphi_abs_Rxxx_all
      - dphi_abs_Rxxx_<ptlo>_<pthi>
    (Removed in v9.8.0: obsolete dphi_Rxxx_* histograms in [0,2π).)
  • NOTE: Uses nbins_abs = max(1, DPHI_NBINS/2) to keep the same Δφ bin width as the 0..2π histograms.

v5.9 (minor: diagnostics + robustness for jet pT spectra):
  • NEW: Print analyzer version banner at start of every run.
  • NEW: Support --version to quickly verify which binary your SLURM jobs are running.
  • NEW: TH1::AddDirectory(kFALSE) to avoid directory-ownership surprises in merged ROOT.
  • No physics changes: same selections and weights; only output/diagnostics.

v5.8 (minor: add dijet imbalance observables):
  • NEW: Write dijet momentum imbalance histograms for each R:
      - xj_Rxxx_all : xJ = pT2/pT1  (dimensionless; stored as mb per unit xJ)
      - aj_Rxxx_all : AJ = (pT1-pT2)/(pT1+pT2) (dimensionless; stored as mb per unit AJ)
    These enable direct vacuum-vs-brick comparisons of imbalance distributions.
  • No changes to existing selections, weights, Δφ, η, Mjj, or jet pT logic.

v5.7 (minor, build fix):
  • FIX: Close parse_list() before defining make_log_edges().
    This restores C++ compliance and prevents the "function-definition is not allowed here" compile error.

v5.6 (minor, plotting/diagnostics upgrades):
  • NEW: Write an “all pT” Δφ histogram per R:
      - dphi_abs_Rxxx_all  (|Δφ| for all leading-jet pT, mb/rad)
    The obsolete raw dphi_Rxxx_* [0,2π) family was removed in v9.8.0.
  • NEW: Write subleading jet pT spectrum per R:
      - jetpt_sublead_Rxxx_all (subleading-jet dσ/dpT, mb/GeV)
    (Complementary to existing leading/inclusive jet spectra.)
  • NEW (binning): If JETPT_BIN_EDGES is not provided, jet pT spectra now default to log-spaced bins
    (controlled by JETPT_NBINS, default 60) instead of reusing PT_LEAD_BIN_EDGES (which was way too coarse).
  • NEW: ETA_NBINS config key (default 80) to increase η “dot count” without touching code.
  • Defaults bumped slightly for more points: DPHI_NBINS=720, MJJ_NBINS=240 (override in jetscape.ini anytime).
  • No selection/weight logic changes. Existing histogram names are preserved; only new histograms are added.

v5.5 (minor, physics-friendly additions):
  • NEW: Write jet pT spectra histograms to the ROOT output for each R:
      - jetpt_lead_Rxxx_all  (leading-jet dσ/dpT, mb/GeV)
      - jetpt_incl_Rxxx_all  (inclusive-jet dσ/dpT, mb/GeV; counts all jets passing selection)
    These are the observables Claude is asking for and are typically much more sensitive to
    medium (brick) energy loss than Mjj shape alone.
  • No changes to existing Δφ/η/Mjj histogram names or selection logic.

v5.4 (minor, correctness hardening):
  • FIX: Normalize Δφ histograms using ROOT's per-bin-width scaling (Scale(1,"width")).
    This guarantees the histogram contents truly match the axis label "mb/rad" even if
    binning ever changes (removes the uniform-bin assumption).
  • FIX: Normalize η histograms using ROOT's per-bin-width scaling as well
    (keeps "mb per unit η" correct for any η binning).
  • No changes to selections, weights, or physics logic. Histogram names unchanged.

v5.3 (minor):
  • FIX metadata robustness: JSON xsec_mb no longer becomes -1 when the analysis job
    computes a fallback weight in $TMPDIR (where xsec_*.txt does not exist).
    Now the analyzer extracts sigmaGen/sigmaErr directly from the hadron ASCII
    while streaming the file and uses it as a fallback source for xsec_mb/xsecerr_mb.
  • Histogram physics, cuts, and weights are unchanged.

v5.2 (minor):
  • FIX bookkeeping bug: events_passing was incorrectly incremented once per R (multi-R could exceed events_seen).
    Now:
      - events_passing = number of events passing jet selection for at least one R
      - new JSON field events_passing_per_R gives per-R pass counts
    Histogram physics and weighting are unchanged.

v5.1 (minor):
  • X-SCAPE migration note: this analyzer consumes the same JetScapeWriterFinalStateHadronsAscii
    output used before, so no physics logic changes. Updated metadata output:
      - JSON now records ENGINE_NAME / EXE_NAME when present in jetscape.ini.
  • No histogram definitions or cuts changed.

v5.0 (major):
  • Optional dijet centrality cut: enforce |y*| = |(y1−y2)|/2 < YSTAR_MAX **only for Mjj fills**
    when YSTAR_ENABLE=1 (Δφ and η histograms unaffected).
  • Optional logarithmic binning for Mjj when MJJ_LOG_BINS=1 and MJJ_MIN_GEV>0.
    Uses variable-width bins with proper per-bin-width normalization.
  • Correct Mjj normalization for variable bins using ROOT per-bin width scaling
    (Scale(1.0,"width")) so units remain mb/GeV for any binning.
  • JSON sidecar now records y* settings and whether log Mjj bins were used.
*/
#include <fstream>
#include <sys/stat.h>   // POSIX file size (GCC7-safe)
#include <sstream>
#include <iostream>
#include <string>
#include <map>
#include <unordered_map>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <cmath>
#include <regex>
#include <cctype>
#include <limits>
#include <stdexcept>
#include <cstdlib>

#include "fastjet/ClusterSequence.hh"
#include "fastjet/JetDefinition.hh"
#include "fastjet/Selector.hh"

#include "TROOT.h"
#include "TH1D.h"
#include "TH1.h"
#include "TH2D.h"
#include "TProfile.h"
#include "TArrayD.h"
#include "TDirectory.h"
#include "TFile.h"
#include "TKey.h"
#include "TList.h"
#include "TString.h"
#include "TDatabasePDG.h"

// v9.2 NOTE: GCC 7 on WSU Grid may not provide <filesystem>; use POSIX stat() instead.
static long long file_size_bytes(const std::string& path) {
  struct stat st;
  if (stat(path.c_str(), &st) == 0) return (long long)st.st_size;
  return -1LL;
}


using IniMap = std::map<std::string, std::map<std::string, std::string>>;
#define ANALYZE_DPHI_SLICED_VERSION_STR "9.9.0"
static constexpr const char* ANALYZE_DPHI_SLICED_VERSION = ANALYZE_DPHI_SLICED_VERSION_STR;


struct RootValidation {
    bool ok = false;
    bool is_zombie = false;
    bool is_recovered = false;
    bool reopen_ok = false;
    long long filesize_bytes = -1;
    int nkeys = 0;
    std::vector<std::string> missing_keys;
    std::string note;
};

static bool root_key_exists(TDirectory* dir, const std::string& key_path){
    if(!dir || key_path.empty()) return false;
    size_t pos = 0;
    TDirectory* cur = dir;
    while(true){
        size_t slash = key_path.find('/', pos);
        std::string token = key_path.substr(pos, (slash == std::string::npos) ? std::string::npos : (slash - pos));
        if(token.empty()) return false;
        if(slash == std::string::npos){
            TList* keys = cur->GetListOfKeys();
            return keys && keys->FindObject(token.c_str());
        }
        TDirectory* next = cur->GetDirectory(token.c_str());
        if(!next) return false;
        cur = next;
        pos = slash + 1;
    }
}

static void collect_root_keys_recursive(TDirectory* dir,
                                        const std::string& prefix,
                                        std::vector<std::string>& out_keys){
    if(!dir) return;
    TList* keys = dir->GetListOfKeys();
    if(!keys) return;
    TIter next(keys);
    TObject* obj = nullptr;
    while((obj = next())){
        const auto* k = dynamic_cast<TKey*>(obj);
        if(!k) continue;
        const std::string name = k->GetName();
        const std::string full = prefix.empty() ? name : (prefix + "/" + name);
        out_keys.push_back(full);
        const char* cls = k->GetClassName();
        if(cls && std::string(cls) == "TDirectoryFile"){
            TDirectory* sub = dir->GetDirectory(name.c_str());
            if(sub) collect_root_keys_recursive(sub, full, out_keys);
        }
    }
}

static void fill_histogram_event_weighted_bin(TH1D* h, int bin, double total_weight){
    if(!h || total_weight == 0.0) return;
    const int nb = h->GetNbinsX();
    if(bin >= 1 && bin <= nb){
        const double x = h->GetXaxis()->GetBinCenter(bin);
        h->Fill(x, total_weight);
        return;
    }
    if(bin < 0 || bin > nb + 1) return;
    h->AddBinContent(bin, total_weight);
    if(h->GetSumw2N() > 0){
        TArrayD* sw2 = h->GetSumw2();
        if(sw2 && bin < sw2->GetSize()){
            sw2->SetAt(sw2->At(bin) + total_weight*total_weight, bin);
        }
    }
}


static void scale_TH2_by_bin_area(TH2D* h){
    if(!h) return;
    const int nx = h->GetNbinsX();
    const int ny = h->GetNbinsY();
    for(int ix = 1; ix <= nx; ++ix){
        const double wx = h->GetXaxis()->GetBinWidth(ix);
        for(int iy = 1; iy <= ny; ++iy){
            const double wy = h->GetYaxis()->GetBinWidth(iy);
            const double area = wx * wy;
            if(area <= 0.0) continue;
            const int bin = h->GetBin(ix, iy);
            h->SetBinContent(bin, h->GetBinContent(bin) / area);
            h->SetBinError(bin, h->GetBinError(bin) / area);
        }
    }
    h->GetZaxis()->SetTitle("d^{2}#sigma_{dijet}/d|#Delta#phi|d|#Delta#eta| [mb/rad]");
}

static RootValidation validate_root_output(const std::string& path, const std::vector<std::string>& expected_keys){
    RootValidation rv;
    try{
        rv.filesize_bytes = file_size_bytes(path);
    }catch(...){
        rv.filesize_bytes = -1;
    }
    if(rv.filesize_bytes <= 0){
        rv.note = "file_missing_or_empty";
        return rv;
    }

    auto probe_once = [&](RootValidation& out)->bool{
        TFile f(path.c_str(), "READ");
        if(f.IsZombie()){
            out.is_zombie = true;
            out.note = "is_zombie";
            return false;
        }
        if(f.TestBit(TFile::kRecovered)){
            out.is_recovered = true;
            out.note = "kRecovered";
            // treat recovered as bad: it means ROOT had to salvage a broken file.
            return false;
        }
        TList* keys = f.GetListOfKeys();
        out.nkeys = keys ? keys->GetSize() : 0;
        if(out.nkeys <= 0){
            out.note = "no_keys";
            return false;
        }

        // Verify presence of expected keys (histograms/directories), including nested paths like nosubfrac/<hist>.
        for(const auto& kname : expected_keys){
            if(!root_key_exists(&f, kname)){
                out.missing_keys.push_back(kname);
            }
        }
        if(!out.missing_keys.empty()){
            out.note = "missing_expected_keys";
            return false;
        }
        f.Close();
        return true;
    };

    // First open
    RootValidation tmp = rv;
    bool ok1 = probe_once(tmp);
    rv.is_zombie = tmp.is_zombie;
    rv.is_recovered = tmp.is_recovered;
    rv.nkeys = tmp.nkeys;
    rv.missing_keys = tmp.missing_keys;
    rv.note = tmp.note;
    if(!ok1) return rv;

    // Reopen-after-close verification
    RootValidation tmp2 = rv;
    bool ok2 = probe_once(tmp2);
    rv.reopen_ok = ok2;
    if(!ok2){
        rv.is_zombie = tmp2.is_zombie;
        rv.is_recovered = tmp2.is_recovered;
        rv.nkeys = tmp2.nkeys;
        rv.missing_keys = tmp2.missing_keys;
        rv.note = tmp2.note.empty() ? "reopen_failed" : tmp2.note;
        return rv;
    }

    rv.ok = true;
    rv.note = "ok";
    return rv;
}

static std::string trim(const std::string& s){
    size_t a = s.find_first_not_of(" \t\r\n");
    if (a==std::string::npos) return "";
    size_t b = s.find_last_not_of(" \t\r\n");
    return s.substr(a, b-a+1);
}

// Strip inline '#' comments only if the '#' occurs OUTSIDE single/double quotes.
// This preserves values like EVENT_HEADER_PREFIX="#\tEvent".
static std::string strip_inline_comment_outside_quotes(const std::string& in){
    bool in_single = false;
    bool in_double = false;
    for (size_t i = 0; i < in.size(); ++i){
        const char c = in[i];
        // Skip escaped characters so \" or \' doesn't flip quote state.
        if (c == '\\' && i + 1 < in.size()){
            ++i;
            continue;
        }
        if (!in_double && c == '\''){
            in_single = !in_single;
            continue;
        }
        if (!in_single && c == '"'){
            in_double = !in_double;
            continue;
        }
        if (!in_single && !in_double && c == '#'){
            return trim(in.substr(0, i));
        }
    }
    return trim(in);
}

static std::string strip_quotes(std::string s){
    s = trim(s);
    if (!s.empty() && (s.front()=='"' || s.front()=='\'')) s.erase(0,1);
    if (!s.empty() && (s.back()== '"' || s.back()== '\'')) s.pop_back();
    return s;
}
static std::string tolower_copy(std::string s){
    for(char& c: s) c = std::tolower(static_cast<unsigned char>(c));
    return s;
}

IniMap parse_ini(const std::string& filename) {
    IniMap res;
    std::ifstream fin(filename);
    if (!fin) { std::cerr << "[ERROR] Cannot open INI: " << filename << "\n"; return res; }
    std::string line, section;
    while (std::getline(fin, line)) {
        line = trim(line);
        if (line.empty() || line[0]=='#' || line[0]==';') continue;
        if (line.front()=='[' && line.back()==']') {
            section = line.substr(1, line.size()-2);
            } else {
            auto eq = line.find('=');
            if (eq == std::string::npos) continue;
            std::string key = trim(line.substr(0, eq));
            std::string val = trim(line.substr(eq+1));
            // Strip inline comments, but ONLY when # is outside quotes
            val = strip_inline_comment_outside_quotes(val);
            res[section][key] = val;
        }
    }
    return res;
}

static double wrapDeltaPhi(double d) {
    while (d > M_PI) d -= 2*M_PI;
    while (d <= -M_PI) d += 2*M_PI;
    return d;
}

static std::vector<double> parse_list(std::string s) {
    for (char& c : s) if (c==',' || c=='(' || c==')') c = ' ';
    std::vector<double> out; std::istringstream iss(s); double v;
    while (iss >> v) out.push_back(v);
    return out;
}

// STRICT list parser: every token must be a valid finite number.
// This prevents silent truncation when a list contains a typo.
static std::vector<double> parse_list_strict(std::string s, const std::string& label){
    for (char& c : s) if (c==',' || c=='(' || c==')') c = ' ';
    std::istringstream iss(s);
    std::vector<double> out;
    std::string tok;
    while (iss >> tok){
        size_t idx = 0;
        double v = 0.0;
        try{
            v = std::stod(tok, &idx);
        } catch(...){
            throw std::runtime_error("Bad numeric token in " + label + ": '" + tok + "'");
        }
        if (idx != tok.size()){
            throw std::runtime_error("Bad numeric token in " + label + ": '" + tok + "'");
        }
        if (!std::isfinite(v)){
            throw std::runtime_error("Non-finite numeric token in " + label + ": '" + tok + "'");
        }
        out.push_back(v);
    }
    return out;
}

static std::vector<double> make_log_edges(double lo, double hi, int nbins){
    std::vector<double> edges;
    if (!(std::isfinite(lo) && std::isfinite(hi)) || lo <= 0 || hi <= lo || nbins < 1) {
        return edges;
    }
    edges.resize((size_t)nbins + 1);
    double loglo = std::log(lo);
    double loghi = std::log(hi);
    for (int i = 0; i <= nbins; ++i){
        double t = (double)i / (double)nbins;
        edges[(size_t)i] = std::exp(loglo + t * (loghi - loglo));
    }
    // guard exact endpoints
    edges.front() = lo;
    edges.back()  = hi;
    return edges;
}

// Robust event-header detection
static bool is_event_header(const std::string& line, const std::string& cfg_prefix){
    if(!cfg_prefix.empty()){
        std::string lower_line = tolower_copy(line);
        std::string lower_pref = tolower_copy(cfg_prefix);
        if (lower_line.rfind(lower_pref, 0) == 0) return true;
    }
    static const std::regex re_hash_event(R"(^\s*#\s*Event\b)", std::regex::icase);
    static const std::regex re_bare_event(R"(^\s*Event\b)",     std::regex::icase);
    if (std::regex_search(line, re_hash_event)) return true;
    if (std::regex_search(line, re_bare_event)) return true;
    return false;
}

static bool is_finite(double x){
    return std::isfinite(x);
}

static bool compute_eta_from_pT_pz(double pT, double pz, double& eta_out){
    // Stable pseudorapidity from transverse momentum and pz:
    //   η = asinh(pz/pT) = ln((p+pz)/pT)
    // This avoids numerical issues in 0.5*ln((p+pz)/(p-pz)) when p≈|pz| or pT→0.
    if (!std::isfinite(pT) || !std::isfinite(pz)) return false;

    if (pT <= 0.0){
        // Along the beam: η is formally ±∞. If both are zero, direction is undefined -> reject.
        if (pz == 0.0) return false;
        eta_out = (pz > 0.0) ? std::numeric_limits<double>::infinity()
                             : -std::numeric_limits<double>::infinity();
        return true;
    }

    const double z = pz / pT;
    const double eta = std::asinh(z);
    if (std::isnan(eta)) return false;
    eta_out = eta;
    return true;
}

// Extract sigmaGen/sigmaErr from a comment line like:
//   # sigmaGen 0.000637074 sigmaErr 3.16595e-05
// Returns true if either value was seen; caller should validate both are finite/positive.
static bool parse_sigma_line(const std::string& line, double& xs, double& xe){
    if (line.find("sigmaGen") == std::string::npos && line.find("sigmaErr") == std::string::npos) return false;
    std::istringstream iss(line);
    std::string tok;
    bool gotGen = false, gotErr = false;
    while (iss >> tok){
        if (tok == "sigmaGen"){
            double v;
            if (iss >> v){ xs = v; gotGen = true; }
        } else if (tok == "sigmaErr"){
            double v;
            if (iss >> v){ xe = v; gotErr = true; }
        }
    }
    return (gotGen || gotErr);
}


int main(int argc, char** argv) {

    // Version / sanity check helper (useful on SLURM where old binaries linger).
    if (argc == 2 && std::string(argv[1]) == "--version") {
        std::cout << "analyze_dphi_sliced.cpp v" << ANALYZE_DPHI_SLICED_VERSION_STR
                  << " (build " << __DATE__ << " " << __TIME__ << ")\n";
        return 0;
    }

    std::cout << "[INFO] analyze_dphi_sliced version v" << ANALYZE_DPHI_SLICED_VERSION_STR
              << " (build " << __DATE__ << " " << __TIME__ << ")\n";
    if (argc != 5) {
        std::cerr << "[ERROR] Usage: " << argv[0] << " <hadron.dat> <weight.txt> <jetscape.ini> <slice_tag>\n";
        return 1;
    }
    gROOT->SetBatch(kTRUE);
    TH1::AddDirectory(kFALSE);
    TH1::SetDefaultSumw2(true);

    const std::string hadron_file = argv[1];
    const std::string weight_file = argv[2];
    const std::string ini_file    = argv[3];
    const std::string slice_tag   = argv[4];


auto ini = parse_ini(ini_file);
if (ini.empty()){
    std::cerr << "[ERROR] jetscape.ini parse produced an empty config map (file unreadable or only comments?): " << ini_file << "\n";
    return 2;
}

// ---------------- Strict INI accessors (NO hidden defaults) ----------------
// We support BOTH:
//   - global keys (recommended; your jetscape.ini uses this)
//   - legacy [ANALYSIS] section keys
// but every required key MUST be present and parseable, or we hard-fail.
struct IniHit { std::string section; std::string key; std::string value; };

auto find_ini_key = [&](const std::vector<std::string>& keys, IniHit& hit)->bool{
    // Search order: global first, then legacy [ANALYSIS]
    const std::vector<std::string> sections = {"", "ANALYSIS"};
    for(const auto& sec : sections){
        auto itS = ini.find(sec);
        if(itS == ini.end()) continue;
        for(const auto& k : keys){
            auto itK = itS->second.find(k);
            if(itK != itS->second.end()){
                hit.section = sec;
                hit.key = k;
                hit.value = strip_quotes(itK->second);
                return true;
            }
        }
    }
    return false;
};

auto die_cfg = [&](const std::string& msg){
    throw std::runtime_error(msg);
};

auto require_raw = [&](const std::string& label, const std::vector<std::string>& keys)->IniHit{
    IniHit hit;
    if(!find_ini_key(keys, hit) || hit.value.empty()){
        std::ostringstream oss;
        oss << "Missing required INI key for " << label << ". Tried keys: ";
        for(size_t i=0;i<keys.size();++i){
            oss << keys[i];
            if(i+1<keys.size()) oss << ", ";
        }
        oss << " (searched <global> and [ANALYSIS]).";
        die_cfg(oss.str());
    }
    std::cout << "[INI] " << label << " = " << hit.value
              << "   (key=" << hit.key
              << ", section=" << (hit.section.empty() ? "<global>" : hit.section) << ")\n";
    return hit;
};

auto parse_double_strict = [&](const std::string& label, const std::string& s)->double{
    size_t idx = 0;
    double v = 0.0;
    try{
        v = std::stod(s, &idx);
    } catch(...){
        die_cfg("Bad double for " + label + ": '" + s + "'");
    }
    if (!trim(s.substr(idx)).empty()){
        die_cfg("Bad double for " + label + " (trailing junk): '" + s + "'");
    }
    if (!std::isfinite(v)){
        die_cfg("Non-finite double for " + label + ": '" + s + "'");
    }
    return v;
};

auto parse_int_strict = [&](const std::string& label, const std::string& s)->int{
    size_t idx = 0;
    long long v = 0;
    try{
        v = std::stoll(s, &idx);
    } catch(...){
        die_cfg("Bad int for " + label + ": '" + s + "'");
    }
    if (!trim(s.substr(idx)).empty()){
        die_cfg("Bad int for " + label + " (trailing junk): '" + s + "'");
    }
    if (v < std::numeric_limits<int>::min() || v > std::numeric_limits<int>::max()){
        die_cfg("Out-of-range int for " + label + ": '" + s + "'");
    }
    return (int)v;
};

auto require_string = [&](const std::string& label, const std::vector<std::string>& keys)->std::string{
    IniHit hit = require_raw(label, keys);
    return hit.value;
};
auto require_double = [&](const std::string& label, const std::vector<std::string>& keys)->double{
    IniHit hit = require_raw(label, keys);
    return parse_double_strict(label, hit.value);
};
auto require_int = [&](const std::string& label, const std::vector<std::string>& keys)->int{
    IniHit hit = require_raw(label, keys);
    return parse_int_strict(label, hit.value);
};
auto require_bool01 = [&](const std::string& label, const std::vector<std::string>& keys)->int{
    int v = require_int(label, keys);
    if (!(v == 0 || v == 1)){
        die_cfg(label + " must be 0 or 1 (got " + std::to_string(v) + ").");
    }
    return v;
};
auto require_list = [&](const std::string& label, const std::vector<std::string>& keys, size_t min_count)->std::vector<double>{
    IniHit hit = require_raw(label, keys);
    std::vector<double> out = parse_list_strict(hit.value, label);
    if (out.size() < min_count){
        die_cfg(label + " must contain at least " + std::to_string(min_count) + " numbers (got " + std::to_string(out.size()) + ").");
    }
    return out;
};

// ---- Read config (STRICT; no defaults) ----
// Required core parsing
std::string evt_header;
double particleEtaMax = 0.0;
double clusterMin = 0.0;

// Optional physics safety: filter particles by JETSCAPE status code (recoil/backreaction bookkeeping)
int particleStatusFilter = 1; // 1=auto-detect final-state status convention and keep the appropriate final-state set; 0=keep all statuses

std::string jetConstituentsModeRaw;
std::string jetConstituentsMode;
bool jetConstituentsChargedOnly = false; // resolved from JET_CONSTITUENTS_MODE

// Constituent selection counters (for reproducibility / honesty)
unsigned long long n_part_lines = 0ULL;
// Particle status accounting (JETSCAPE event record "st" field)
unsigned long long n_part_status0 = 0ULL;
unsigned long long n_part_status1 = 0ULL;
unsigned long long n_part_status_neg1 = 0ULL;
unsigned long long n_part_status_other = 0ULL;
unsigned long long n_part_skipped_by_status = 0ULL;
unsigned long long n_part_after_pt_eta = 0ULL;
unsigned long long n_part_after_pt = 0ULL;           // after pT >= CLUSTER_MIN
unsigned long long n_part_fail_pt = 0ULL;            // failed pT cut (finite pT but below CLUSTER_MIN)
unsigned long long n_part_fail_pt_nonfinite = 0ULL;  // non-finite pT
unsigned long long n_part_fail_eta = 0ULL;           // failed |eta| cut (among those passing pT)
unsigned long long n_part_fail_eta_undef = 0ULL;     // eta undefined/non-finite (among those passing pT)
unsigned long long n_keep_total = 0ULL;
unsigned long long n_keep_charged = 0ULL;
unsigned long long n_keep_neutral = 0ULL;
unsigned long long n_reject_neutral = 0ULL;
unsigned long long n_unknown_pid = 0ULL;

// Store a small sample of unknown PDG IDs (for debugging charged-jet mode & completeness)
const size_t unknown_pid_log_max = 10;
std::vector<int> unknown_pid_examples;
unknown_pid_examples.reserve(unknown_pid_log_max);
std::unordered_set<int> unknown_pid_seen;
unknown_pid_seen.reserve(unknown_pid_log_max * 2);

double jetPtMin = 0.0;
double jetPtMax = 0.0; // Upper pT bound for jet spectra histogram binning (from JET_PT_MAX; optional)
double leadPtMin = 0.0;
double subPtMin  = 0.0;
double subFracMin = 0.0;

int jetEtaMode = 0;
double jetEtaMaxRaw = 0.0;

int dphi_nbins = 0;
int eta_nbins  = 0;

int xj_nbins = 0;
int aj_nbins = 0;

std::string jetpt_bins_mode;
int jetpt_nbins = 0;
std::vector<double> jetpt_edges;

std::vector<double> Rlist;
std::vector<double> ptEdges;

int mjj_enable = 0;
int mjj_nbins = 0;
double mjj_min = 0.0;
double mjj_max = 0.0;
int mjj_log_bins = 0;
int mjj_require_backtoback = 0;

int ystar_enable = 0;
double ystar_max = 0.0;

double tol_deg = 0.0;
double tol_rad = 0.0;

int imbalanceBacktoback = 0;
double imbalanceTolDeg = 0.0;
double imbalanceTolRad = 0.0;

int dijetRequireExactlyTwoJets = 0;

try{
    evt_header      = require_string("EVENT_HEADER_PREFIX", {"EVENT_HEADER_PREFIX"});

    particleEtaMax  = require_double("PARTICLE_ETA_MAX", {"PARTICLE_ETA_MAX"});
    clusterMin      = require_double("CLUSTER_MIN", {"CLUSTER_MIN"});

    // Required: filter by particle status code in the JETSCAPE event record.
    // 1 enables the auto-detecting status filter; 0 keeps all statuses (debug / keep-all mode).
    particleStatusFilter = require_bool01("PARTICLE_STATUS_FILTER", {"PARTICLE_STATUS_FILTER"});

// Required: define whether jets are clustered from charged-only or all (full) hadrons.

    jetConstituentsModeRaw = require_string("JET_CONSTITUENTS_MODE", {"JET_CONSTITUENTS_MODE"});
    jetConstituentsMode = tolower_copy(strip_quotes(jetConstituentsModeRaw));
    if (jetConstituentsMode == "charged") {
        jetConstituentsChargedOnly = true;
    } else if (jetConstituentsMode == "full") {
        jetConstituentsChargedOnly = false;
    } else {
        die_cfg("JET_CONSTITUENTS_MODE must be \"charged\" or \"full\" (got: " + jetConstituentsModeRaw + ")");
    }

    jetPtMin        = require_double("JET_PT_MIN", {"JET_PT_MIN"});
    leadPtMin       = require_double("LEAD_PT_MIN", {"LEAD_PT_MIN"});
    subPtMin        = require_double("SUBLEAD_PT_MIN", {"SUBLEAD_PT_MIN"});

    // Canonical: SUBFRAC (alias: SUBFRAC_MIN)
    subFracMin      = require_double("SUBFRAC", {"SUBFRAC", "SUBFRAC_MIN"});

    // Required: control whether dijet-dependent histograms accept >=2 jets or exactly 2 accepted jets.
    dijetRequireExactlyTwoJets = require_bool01("DIJET_REQUIRE_EXACTLY_TWO_JETS", {"DIJET_REQUIRE_EXACTLY_TWO_JETS"});

    jetEtaMode      = require_int("JET_ETA_MODE", {"JET_ETA_MODE"});
    jetEtaMaxRaw    = require_double("JET_ETA_MAX", {"JET_ETA_MAX"});

    dphi_nbins      = require_int("DPHI_NBINS", {"DPHI_NBINS"});
    eta_nbins       = require_int("ETA_NBINS", {"ETA_NBINS"});

    xj_nbins        = require_int("XJ_NBINS", {"XJ_NBINS"});
    aj_nbins        = require_int("AJ_NBINS", {"AJ_NBINS"});

    jetpt_bins_mode = tolower_copy(require_string("JETPT_BINS_MODE", {"JETPT_BINS_MODE"}));
    jetpt_nbins     = require_int("JETPT_NBINS", {"JETPT_NBINS"});

    // Optional explicit edges; if absent we derive from JETPT_BINS_MODE
    {
        IniHit hit;
        if (find_ini_key({"JETPT_BIN_EDGES"}, hit) && !strip_quotes(hit.value).empty()){
            std::cout << "[INI] JETPT_BIN_EDGES present -> using explicit jet pT edges (key=" << hit.key
                      << ", section=" << (hit.section.empty() ? "<global>" : hit.section) << ")\n";
            jetpt_edges = parse_list_strict(hit.value, "JETPT_BIN_EDGES");
            if (jetpt_edges.size() < 2) die_cfg("JETPT_BIN_EDGES must have >=2 edges.");
            // Validate monotonicity: strict increasing edges prevent ROOT variable-bin corruption.
            for (size_t i = 1; i < jetpt_edges.size(); ++i) {
                const double a = jetpt_edges[i-1];
                const double b = jetpt_edges[i];
                if (!std::isfinite(a) || !std::isfinite(b)) {
                    die_cfg("JETPT_BIN_EDGES contains non-finite values.");
                }
                if (!(b > a)) {
                    std::ostringstream oss;
                    oss << "JETPT_BIN_EDGES must be strictly increasing: edge[" << (i-1) << "]=" << a
                        << " , edge[" << i << "]=" << b;
                    die_cfg(oss.str());
                }
            }
        } else {
            std::cout << "[INI] JETPT_BIN_EDGES absent -> deriving jet pT edges from JETPT_BINS_MODE\n";
        }
    }

    // Canonical: JET_RADIUS_LIST (alias: JET_R_LIST)
    Rlist = require_list("JET_RADIUS_LIST", {"JET_RADIUS_LIST", "JET_R_LIST"}, 1);

    // Lead-jet pT bin edges for slicing dphi and mjj-by-pt
    ptEdges = require_list("PT_LEAD_BIN_EDGES", {"PT_LEAD_BIN_EDGES"}, 2);

    // Optional: Upper pT bound for jet spectra histogram binning (used when JETPT_BINS_MODE=logspace).
    // Physics note: PT_LEAD_BIN_EDGES is for dijet categorization (leading-jet bins), not the jet-spectrum axis.
    // If missing, we fall back to PT_LEAD_BIN_EDGES.back for backward compatibility (with a loud warning).
    {
        IniHit hit;
        if (find_ini_key({"JET_PT_MAX"}, hit) && !strip_quotes(hit.value).empty()){
            jetPtMax = parse_double_strict("JET_PT_MAX", strip_quotes(hit.value));
            std::cout << "[INI] JET_PT_MAX=" << jetPtMax << "   (key=" << hit.key
                      << ", section=" << (hit.section.empty() ? "<global>" : hit.section) << ")\n";
        } else {
            jetPtMax = ptEdges.back();
            std::cout << "[INI][WARN] JET_PT_MAX not set -> using PT_LEAD_BIN_EDGES.back()=" << jetPtMax
                      << " as jet pT spectra upper edge (backward-compat). Consider setting JET_PT_MAX explicitly.\n";
        }
    }

    // Dijet back-to-back tolerance for Mjj selection
    // Canonical: DIJET_BACKTOBACK_TOL_DEG (alias: DPHI_TO_PI_TOL_DEG)
    tol_deg = require_double("DIJET_BACKTOBACK_TOL_DEG", {"DIJET_BACKTOBACK_TOL_DEG", "DPHI_TO_PI_TOL_DEG"});
    tol_rad = tol_deg * M_PI / 180.0;

    // Imbalance back-to-back toggle and tolerance
    imbalanceBacktoback = require_bool01("IMBALANCE_REQUIRE_BACKTOBACK", {"IMBALANCE_REQUIRE_BACKTOBACK"});
    imbalanceTolDeg     = require_double("IMBALANCE_BACKTOBACK_TOL_DEG", {"IMBALANCE_BACKTOBACK_TOL_DEG"});
    imbalanceTolRad     = imbalanceTolDeg * M_PI / 180.0;

    // Mjj controls
    mjj_enable   = require_bool01("MJJ_ENABLE", {"MJJ_ENABLE"});
    mjj_nbins    = require_int("MJJ_NBINS", {"MJJ_NBINS"});
    mjj_min      = require_double("MJJ_MIN_GEV", {"MJJ_MIN_GEV"});
    mjj_max      = require_double("MJJ_MAX_GEV", {"MJJ_MAX_GEV"});
    mjj_log_bins = require_bool01("MJJ_LOG_BINS", {"MJJ_LOG_BINS"});
    mjj_require_backtoback = require_bool01("MJJ_REQUIRE_BACKTOBACK", {"MJJ_REQUIRE_BACKTOBACK"});

    // y* cut (applied to all dijet-pair histograms when enabled)
    ystar_enable = require_bool01("YSTAR_ENABLE", {"YSTAR_ENABLE"});
    ystar_max    = require_double("YSTAR_MAX", {"YSTAR_MAX"});
    // Loud config banner for reproducibility (avoid accidental "I thought it was charged jets").
    std::cout << "[CFG] JET_CONSTITUENTS_MODE=" << jetConstituentsMode
              << "  (charged_only=" << (jetConstituentsChargedOnly ? 1 : 0) << ")\n";
    std::cout << "[CFG] CLUSTER_MIN=" << clusterMin << "  PARTICLE_ETA_MAX=" << particleEtaMax << "\n";
    std::cout << "[CFG] PARTICLE_STATUS_FILTER=" << particleStatusFilter << "  (1=auto-detect final-state status convention; 0=keep all statuses)\n";
} catch(const std::exception& e){
    std::cerr << "[ERROR] jetscape.ini strict parse failed: " << e.what() << "\n";
    std::cerr << "[ERROR] Refusing to run with hidden defaults. Fix jetscape.ini and resubmit.\n";
    return 2;
}

// ---- Basic validation (fail loud) ----
if (particleEtaMax <= 0.0) { std::cerr << "[ERROR] PARTICLE_ETA_MAX must be > 0\n"; return 2; }
if (clusterMin < 0.0)      { std::cerr << "[ERROR] CLUSTER_MIN must be >= 0\n"; return 2; }
if (!(particleStatusFilter == 0 || particleStatusFilter == 1)) { std::cerr << "[ERROR] PARTICLE_STATUS_FILTER must be 0 or 1\n"; return 2; }
if (jetPtMin <= 0.0)       { std::cerr << "[ERROR] JET_PT_MIN must be > 0\n"; return 2; }
if (jetPtMax <= 0.0)       { std::cerr << "[ERROR] JET_PT_MAX must be > 0 (set in jetscape.ini)\n"; return 2; }
if (!(jetPtMax > jetPtMin)){ std::cerr << "[ERROR] JET_PT_MAX must be > JET_PT_MIN (got max=" << jetPtMax << ", min=" << jetPtMin << ")\n"; return 2; }
if (leadPtMin <= 0.0)      { std::cerr << "[ERROR] LEAD_PT_MIN must be > 0\n"; return 2; }
if (subPtMin < 0.0)        { std::cerr << "[ERROR] SUBLEAD_PT_MIN must be >= 0\n"; return 2; }
if (subFracMin < 0.0)      { std::cerr << "[ERROR] SUBFRAC must be >= 0\n"; return 2; }
if (jetEtaMaxRaw <= 0.0)   { std::cerr << "[ERROR] JET_ETA_MAX must be > 0\n"; return 2; }
if (!(jetEtaMode == 0 || jetEtaMode == 1)){
    std::cerr << "[ERROR] JET_ETA_MODE must be 0 or 1 (got " << jetEtaMode << ")\n"; return 2;
}
if (dphi_nbins < 1){ std::cerr << "[ERROR] DPHI_NBINS must be >= 1\n"; return 2; }
if (eta_nbins < 1) { std::cerr << "[ERROR] ETA_NBINS must be >= 1\n"; return 2; }
if (xj_nbins < 1)  { std::cerr << "[ERROR] XJ_NBINS must be >= 1\n"; return 2; }
if (aj_nbins < 1)  { std::cerr << "[ERROR] AJ_NBINS must be >= 1\n"; return 2; }

// Ensure ptEdges strictly increasing
for(size_t i=1;i<ptEdges.size();++i){
    if (!(ptEdges[i] > ptEdges[i-1])){
        std::cerr << "[ERROR] PT_LEAD_BIN_EDGES must be strictly increasing.\n";
        return 2;
    }
}
// Ensure Rlist positive and reasonable
for(double R : Rlist){
    if (!(R > 0.0 && R < 2.0)){
        std::cerr << "[ERROR] Bad jet radius R=" << R << " in JET_RADIUS_LIST (expected 0 < R < 2)\n";
        return 2;
    }
}

// Determine jet pT spectrum histogram edges if not explicitly provided
if (jetpt_edges.size() >= 2){
    // explicit edges already set
} else if (jetpt_bins_mode == "logspace" || jetpt_bins_mode == "log"){
    const double lo = jetPtMin;
    const double hi = jetPtMax;
    jetpt_edges = make_log_edges(lo, hi, jetpt_nbins);
    if (jetpt_edges.size() < 2){
        std::cerr << "[ERROR] Failed to build log jet pT bin edges (lo=" << lo << ", hi=" << hi << ", nbins=" << jetpt_nbins << ")\n";
        return 2;
    }
} else if (jetpt_bins_mode == "lead_edges" || jetpt_bins_mode == "pt_lead_bin_edges"){
    jetpt_edges = ptEdges;
} else {
    std::cerr << "[ERROR] Unknown JETPT_BINS_MODE='" << jetpt_bins_mode << "'. Allowed: logspace, lead_edges.\n";
    return 2;
}

// ---- Print config summary (so SLURM logs show exactly what ran) ----
std::cout << "[INFO] Config summary (STRICT):\n";
std::cout << "  hadron_file=" << hadron_file << "\n";
std::cout << "  weight_file=" << weight_file << "\n";
std::cout << "  ini_file=" << ini_file << "\n";
std::cout << "  slice_tag=" << slice_tag << "\n";

std::cout << "  EVENT_HEADER_PREFIX=" << evt_header << "\n";
std::cout << "  PARTICLE_ETA_MAX=" << particleEtaMax << "\n";
std::cout << "  CLUSTER_MIN=" << clusterMin << "\n";
std::cout << "  PARTICLE_STATUS_FILTER=" << particleStatusFilter << "  (1=auto-detect final-state status convention; 0=keep all statuses)\n";

std::cout << "  JET_PT_MIN=" << jetPtMin << "\n";
std::cout << "  JET_PT_MAX=" << jetPtMax << "\n";
std::cout << "  LEAD_PT_MIN=" << leadPtMin << "\n";
std::cout << "  SUBLEAD_PT_MIN=" << subPtMin << "\n";
std::cout << "  SUBFRAC=" << subFracMin << "\n";
std::cout << "  DIJET_REQUIRE_EXACTLY_TWO_JETS=" << dijetRequireExactlyTwoJets
          << "  (0=require >=2 accepted jets and use the leading two; 1=require exactly 2 accepted jets for dijet observables)\n";

std::cout << "  JET_ETA_MAX=" << jetEtaMaxRaw << "  JET_ETA_MODE=" << jetEtaMode << "\n";
std::cout << "  DPHI_NBINS=" << dphi_nbins << "\n";
std::cout << "  ETA_NBINS=" << eta_nbins << "\n";

std::cout << "  XJ_NBINS=" << xj_nbins << "  AJ_NBINS=" << aj_nbins << "\n";

std::cout << "  DIJET_BACKTOBACK_TOL_DEG=" << tol_deg << "\n";
std::cout << "  IMBALANCE_REQUIRE_BACKTOBACK=" << imbalanceBacktoback
          << "  IMBALANCE_BACKTOBACK_TOL_DEG=" << imbalanceTolDeg << "\n";

std::cout << "  MJJ_ENABLE=" << mjj_enable
          << "  MJJ_NBINS=" << mjj_nbins
          << "  MJJ_MIN_GEV=" << mjj_min
          << "  MJJ_MAX_GEV=" << mjj_max
          << "  MJJ_LOG_BINS=" << mjj_log_bins
          << "  MJJ_REQUIRE_BACKTOBACK=" << mjj_require_backtoback << "\n";

std::cout << "  YSTAR_ENABLE=" << ystar_enable << "  YSTAR_MAX=" << ystar_max << "\n";

if (ystar_enable) {
    std::cout << "[INI][NOTE] YSTAR_ENABLE=1: jet acceptance is currently applied in pseudorapidity |eta|<etaMaxJet, "
              << "while y* is computed from rapidity. This is fine for ALICE-style eta acceptance; "
              << "if you later want y-based acceptance, update the jet selector accordingly.\n";
}

std::cout << "  JET_RADIUS_LIST=[";
for(size_t i=0;i<Rlist.size();++i){ std::cout << Rlist[i] << (i+1<Rlist.size()? ", ":""); }
std::cout << "]\n";

std::cout << "  PT_LEAD_BIN_EDGES=[";
for(size_t i=0;i<ptEdges.size();++i){ std::cout << ptEdges[i] << (i+1<ptEdges.size()? ", ":""); }
std::cout << "]\n";

std::cout << "  JETPT_BINS_MODE=" << jetpt_bins_mode
          << "  JETPT_NBINS=" << jetpt_nbins
          << "  (edges=" << jetpt_edges.size() << ")\n";
    // ---- Read weight file (xsec per event weight) ----
    double weight_mb_per_event = 0.0;
    {
        std::ifstream fw(weight_file);
        if(!fw){
            std::cerr << "[ERROR] Cannot open weight file: " << weight_file << "\n";
            return 3;
        }
        fw >> weight_mb_per_event;
        if(!fw || !std::isfinite(weight_mb_per_event) || weight_mb_per_event <= 0.0){
            std::cerr << "[ERROR] Bad weight_mb_per_event in weight file.\n";
            return 3;
        }
    }
    std::cout << "[INFO] weight_mb_per_event=" << weight_mb_per_event << "\n";

    // Constituent charge helper (cached). ROOT stores charge in units of e/3; we only care if it's zero or non-zero.
    std::unordered_map<int, int> pid_charge_cache;
    pid_charge_cache.reserve(512);
    auto charge_units_e_over_3 = [&](int pid)->int{
        auto it = pid_charge_cache.find(pid);
        if(it != pid_charge_cache.end()) return it->second;

        int q = 0;
        TParticlePDG* p = TDatabasePDG::Instance()->GetParticle(pid);
        if(p){
            // Charge() is a double but should be an integer multiple of 1 (in e/3 units).
            q = (int)std::lround(p->Charge());
        } else {
            // Unknown PID: treat as neutral (conservative for charged jets).
            ++n_unknown_pid;
            if (unknown_pid_examples.size() < unknown_pid_log_max) {
                if (unknown_pid_seen.insert(pid).second) {
                    unknown_pid_examples.push_back(pid);
                }
            }
            q = 0;
        }
        pid_charge_cache.emplace(pid, q);
        return q;
    };
    auto is_charged_pid = [&](int pid)->bool{
        return charge_units_e_over_3(pid) != 0;
    };


    // ---- Stream hadron file, parse sigmaGen/sigmaErr from comments ----
    std::ifstream fin(hadron_file);
    if(!fin){
        std::cerr << "[ERROR] Cannot open hadron file: " << hadron_file << "\n";
        return 4;
    }

    double sigmaGen_stream = std::numeric_limits<double>::quiet_NaN();
    double sigmaErr_stream = std::numeric_limits<double>::quiet_NaN();
    bool sigma_seen = false;
    std::string sigma_last_line; // for debugging/logs
// ---- Particle status filter auto-detection ----
// Some JETSCAPE writers output final-state hadrons with status==0 (or ==1).
// Other writers propagate generator-like status codes (e.g. 83/84) even for hadrons.
// If we blindly require st==0/1 we can accidentally drop *all* particles (=> no jets).
enum class StatusFilterMode { KEEP_ALL, KEEP_POSITIVE_01, KEEP_NONNEG };
StatusFilterMode statusMode = StatusFilterMode::KEEP_ALL;
std::string statusModeLabel = "KEEP_ALL";
std::string statusModeNote;

if (particleStatusFilter == 1) {
    // Pre-scan a limited number of particle lines to infer the status convention.
    // This is cheap and avoids a full second pass over large files.
    fin.clear();
    fin.seekg(0, std::ios::beg);

    const unsigned long long prescan_limit = 50000ULL; // particle lines (not events)
    unsigned long long prescan_lines = 0ULL;
    unsigned long long prescan_neg1 = 0ULL, prescan_0 = 0ULL, prescan_1 = 0ULL, prescan_other = 0ULL;
    int prescan_min = std::numeric_limits<int>::max();
    int prescan_max = std::numeric_limits<int>::min();

    std::string pline;
    while (prescan_lines < prescan_limit && std::getline(fin, pline)) {
        if (is_event_header(pline, evt_header)) continue;
        if (pline.empty() || pline[0] == '#') continue;

        std::istringstream pss(pline);
        int idx=0, pid=0, st=0; double E=0, px=0, py=0, pz=0;
        pss >> idx >> pid >> st >> E >> px >> py >> pz;
        if (!pss) continue;

        prescan_lines++;
        prescan_min = std::min(prescan_min, st);
        prescan_max = std::max(prescan_max, st);

        if (st == -1) prescan_neg1++;
        else if (st == 0) prescan_0++;
        else if (st == 1) prescan_1++;
        else prescan_other++;
    }

    // Decide mode:
    if (prescan_neg1 > 0ULL) {
        statusMode = StatusFilterMode::KEEP_NONNEG;
        statusModeLabel = "KEEP_NONNEG";
        statusModeNote = "auto: saw status==-1 -> keep st>=0 (reject -1 backreaction holes)";
    } else if ((prescan_0 + prescan_1) > 0ULL && prescan_other == 0ULL) {
        statusMode = StatusFilterMode::KEEP_POSITIVE_01;
        statusModeLabel = "KEEP_POSITIVE_01";
        statusModeNote = "auto: saw only status 0/1 -> keep st==0 or 1";
    } else if ((prescan_0 + prescan_1) > 0ULL && prescan_other > 0ULL) {
        // Mixed scheme: be conservative; keep non-negative (won't drop st=1/83/84) unless -1 exists.
        statusMode = StatusFilterMode::KEEP_NONNEG;
        statusModeLabel = "KEEP_NONNEG";
        statusModeNote = "auto: mixed status values -> keep st>=0 (reject any negative)";
    } else {
        // No 0/1/-1 observed (common for generator-like codes such as 83/84).
        statusMode = StatusFilterMode::KEEP_ALL;
        statusModeLabel = "KEEP_ALL";
        statusModeNote = "auto: no status 0/1/-1 observed (min=" + std::to_string(prescan_min) +
                         ", max=" + std::to_string(prescan_max) + ") -> disable status filtering (keep all)";
    }

    // Reset stream for the real parse.
    fin.clear();
    fin.seekg(0, std::ios::beg);

    std::cout << "[INI] PARTICLE_STATUS_FILTER auto-mode=" << statusModeLabel;
    if (!statusModeNote.empty()) std::cout << "  (" << statusModeNote << ")";
    std::cout << "\n";
    if (statusMode == StatusFilterMode::KEEP_ALL) {
        std::cout << "[WARN] PARTICLE_STATUS_FILTER=1 requested, but status convention looks non-JETSCAPE(0/-1). "
                     "Keeping ALL statuses to avoid dropping all constituents.\n";
    }
}


    // ---- Prepare histograms ----
    struct RHist {
        bool enabled = true;
        double R = 0.0;
        int    Rtag = 0; // histogram tag: int(round(R*100)) => R020, R040, ...
        double etaMaxJet = 0.0;


        std::vector<TH1D*> dphiAbs;
        TH1D* dphiAbsAll = nullptr;
        std::vector<TH2D*> dphiAbsVsDeta;
        TH2D* dphiAbsVsDetaAll = nullptr;

        TH1D* etaLead = nullptr;
        TH1D* etaSub  = nullptr;

        TH1D* jetPtLead = nullptr;
        TH1D* jetPtSub  = nullptr;
        TH1D* jetPtIncl = nullptr;
        TH2D* h2SubleadVsLeadAll = nullptr;
        TProfile* profSubleadVsLeadPtLeadBins = nullptr;

        TH1D* xjAll = nullptr;
        std::vector<TH1D*> xjByPt;
        TH1D* ajAll = nullptr;
        std::vector<TH1D*> ajByPt;

        TH1D* mjjAll = nullptr;


        // ---- Parallel "no SUBFRAC" versions of dijet-selected observables ----

        std::vector<TH1D*> dphiAbs_nosubfrac;
        TH1D* dphiAbsAll_nosubfrac = nullptr;
        std::vector<TH2D*> dphiAbsVsDeta_nosubfrac;
        TH2D* dphiAbsVsDetaAll_nosubfrac = nullptr;

        TH1D* etaLead_nosubfrac = nullptr;
        TH1D* etaSub_nosubfrac  = nullptr;

        TH1D* jetPtLead_nosubfrac = nullptr;
        TH1D* jetPtSub_nosubfrac  = nullptr;
        TH2D* h2SubleadVsLeadAll_nosubfrac = nullptr;
        TProfile* profSubleadVsLeadPtLeadBins_nosubfrac = nullptr;

        TH1D* xjAll_nosubfrac = nullptr;
        std::vector<TH1D*> xjByPt_nosubfrac;
        TH1D* ajAll_nosubfrac = nullptr;
        std::vector<TH1D*> ajByPt_nosubfrac;

        TH1D* mjjAll_nosubfrac = nullptr;

        fastjet::JetDefinition jetDef = fastjet::JetDefinition(fastjet::antikt_algorithm, 0.4);
        fastjet::Selector selDijet;
        fastjet::Selector selLead;
        fastjet::Selector selIncl;
    };

    // -----------------------------
    // Cutflow accounting (logging only; no physics changes)
    // -----------------------------
    struct CutFlow {
        long long events_total = 0;          // events seen for this R (header matched)
        long long jets_ge2 = 0;              // at least 2 accepted jets
        long long veto_extra_jets = 0;       // rejected in exact-2 mode because accepted jet multiplicity was >2
        long long pass_jet_multiplicity = 0; // passed the dijet jet-count gate (>=2 or exactly 2, depending on config)
        long long pass_lead = 0;             // after lead pT cut
        long long pass_sublead = 0;          // after sublead pT cut
        long long pass_leadsub = 0;          // after lead+sublead pT cuts (same as pass_sublead)
        long long pass_subfrac = 0;          // after SUBFRAC cut (default branch only)
        long long imbalance_checked = 0;     // xJ/AJ eligibility checked
        long long imbalance_pass_bb = 0;     // xJ/AJ back-to-back pass (or all if disabled)
        long long mjj_checked = 0;           // Mjj eligibility checked
        long long mjj_pass_bb = 0;           // Mjj back-to-back pass
        long long ystar_checked = 0;         // y* evaluated (only if enabled)
        long long ystar_pass = 0;            // y* pass (only if enabled)
    };

    struct DijetObservableCounts {
        long long dijet_base_all = 0;
        long long dphi_abs_all = 0;
        long long xj_all = 0;
        long long aj_all = 0;
        long long mjj_all = 0;
        std::vector<long long> dijet_base_ptlead;
        std::vector<long long> dphi_abs_ptlead;
        std::vector<long long> xj_ptlead;
        std::vector<long long> aj_ptlead;
    };

    // Cutflow vectors are sized after rh is built.
    std::vector<CutFlow> cf_default;   // WITH SUBFRAC
    std::vector<CutFlow> cf_nosubfrac; // NO-SUBFRAC (extra histograms)

    // Jet acceptance accounting (logging only; no physics changes)
    struct JetStats {
        long long jets_raw = 0;        // raw clustered jets (before acceptance)
        long long jets_pass_pt = 0;    // jets passing pT >= JET_PT_MIN (no eta gate)
        long long jets_pass_eta = 0;   // jets passing |eta| gate (no pT gate)
        long long jets_pass_pt_eta = 0;// jets passing BOTH (the actual acceptance used)
        long long events_ge1_acc = 0;  // events with >=1 accepted jet
        long long events_ge2_pt = 0;   // events with >=2 jets passing pT cut only
        long long events_ge2_eta = 0;  // events with >=2 jets passing eta cut only
        long long events_ge2_pt_eta = 0; // events with >=2 jets passing BOTH (same gate as analysis)
    };
    std::vector<JetStats> jet_stats;

    // Accepted particle-level constituent QA histograms (filled before anti-k_{T} clustering).
    TH1D* particlePtAll = nullptr;
    TH1D* particleEtaAll = nullptr;
    TH1D* particlePhiAll = nullptr;

    // Parallel unweighted count-density histograms used by downstream SINGLE_SLICE_MODE
    // dijet-normalized plots. Existing weighted d#sigma histograms remain unchanged.
    std::unordered_map<TH1D*, TH1D*> count_hist_for_weighted_hist;
    std::vector<TH1D*> count_hist_default;
    std::vector<TH1D*> count_hist_nosubfrac;

    // One-time documentation of which cuts apply to which histogram groups
    auto print_histogram_map = [&](){
        std::cout << "[INFO] Histogram cut map (documenting logic; no physics changes):\n";
        std::cout << "  (A) Particle selection (particle-level QA + all jet-based histograms):\n";
        std::cout << "      • keep particle if (pt>=CLUSTER_MIN) and (|eta|<PARTICLE_ETA_MAX)  (mode=" << jetConstituentsMode << ")\n";
        std::cout << "      • particle_pt_all / particle_eta_all / particle_phi_all are filled here, before anti-k_{T} clustering\n";
        std::cout << "  (B) Jet finding & acceptance (ALL jet-based histograms):\n";
        std::cout << "      • anti-kT, R in JET_RADIUS_LIST; jets require (pt>=JET_PT_MIN) and jet-eta cut with JET_ETA_MODE=" << jetEtaMode << "\n";
        std::cout << "  (C) Dijet selection (dijet-dependent histograms):\n";
        std::cout << "      • jet-count gate controlled by DIJET_REQUIRE_EXACTLY_TWO_JETS=" << dijetRequireExactlyTwoJets << "\n";
        if (dijetRequireExactlyTwoJets) {
            std::cout << "      • requires exactly 2 accepted jets, then lead pt>=LEAD_PT_MIN and sublead pt>=SUBLEAD_PT_MIN\n";
        } else {
            std::cout << "      • requires >=2 accepted jets, then uses the leading two with lead pt>=LEAD_PT_MIN and sublead pt>=SUBLEAD_PT_MIN\n";
        }
        std::cout << "  (D) SUBFRAC handling:\n";
        std::cout << "      • Branch NO-SUBFRAC: optional y* gate (if enabled) is applied before filling *_nosubfrac histograms\n";
        std::cout << "      • Branch DEFAULT: apply SUBFRAC=(sublead/lead>=" << subFracMin << "), then optional y* gate, then fill existing histograms\n";
        std::cout << "  (E) Back-to-back requirements:\n";
        std::cout << "      • jetpt_lead/sub, h2/prof, eta, dphi_abs/h2_dphi_abs_vs_deta: no extra back-to-back gate beyond dijet definition\n";
        std::cout << "      • xJ/AJ: IMBALANCE_REQUIRE_BACKTOBACK=" << imbalanceBacktoback
                  << " with tol_deg=" << imbalanceTolDeg << "\n";
        std::cout << "      • Mjj: MJJ_REQUIRE_BACKTOBACK=" << mjj_require_backtoback;
        if (mjj_require_backtoback) std::cout << " with DIJET_BACKTOBACK_TOL_DEG=" << tol_deg;
        std::cout << " (mjj_enable=" << mjj_enable << ")\n";
        std::cout << "  (F) Count-density output for SINGLE_SLICE_MODE plots:\n";
        std::cout << "      • counts/count_* and nosubfrac/counts/count_* are unweighted dN/dX histograms for dijet-normalized 1D observables\n";
        std::cout << "      • Existing weighted histograms are unchanged and remain d#sigma/dX or weighted yields\n";
        std::cout << "  (G) y* cut:\n";
        std::cout << "      • YSTAR_ENABLE=" << ystar_enable << " (YSTAR_MAX=" << ystar_max << ")\n";
        std::cout << "      • When enabled, applies to all dijet-pair histograms in both branches: jetpt_lead/sub, h2/prof, xJ/AJ, dphi_abs/h2_dphi_abs_vs_deta, eta_lead/sub, Mjj\n";
        std::cout << "      • Does NOT apply to particle_* QA histograms or inclusive jet spectra jetpt_incl_*\n";
    };

    std::vector<RHist> rh;
    rh.reserve(Rlist.size());

    auto make_mjj_edges = [&](double lo, double hi, int nbins, bool logbins)->std::vector<double>{
        if(!logbins) return {};
        return make_log_edges(lo, hi, nbins);
    };

    const std::string dijetMultiplicityTitle =
        (dijetRequireExactlyTwoJets == 1)
            ? "exactly 2 accepted jets"
            : "leading 2 accepted jets from >=2 accepted jets";
    const std::string dijetYstarTitleSuffix =
        ystar_enable ? std::string(Form(", |y^{*}|<%.2f", ystar_max)) : std::string("");
    const std::string dijetPairSelectionTitle = dijetMultiplicityTitle + dijetYstarTitleSuffix;
    std::string mjjSelectionTitle = dijetMultiplicityTitle +
                                    (mjj_require_backtoback ? std::string(Form(", |#Delta#phi-#pi|<%.1f deg", tol_deg)) : std::string("")) +
                                    dijetYstarTitleSuffix;
    const int ptLeadAllLoTag = static_cast<int>(std::lround(ptEdges.front()));
    const int ptLeadAllHiTag = static_cast<int>(std::lround(ptEdges.back()));
    const std::string ptLeadAllRangeTitle = Form("%d-%d GeV", ptLeadAllLoTag, ptLeadAllHiTag);

    std::vector<double> mjj_edges;
    if(mjj_enable && mjj_log_bins){
        mjj_edges = make_mjj_edges(mjj_min, mjj_max, mjj_nbins, true);
        if(mjj_edges.size() < 2){
            std::cerr << "[ERROR] Requested log Mjj bins but could not build edges.\n";
            return 2;
        }
    }

    std::vector<double> particle_pt_edges;
    if (clusterMin > 0.0) {
        particle_pt_edges = make_log_edges(clusterMin, jetPtMax, jetpt_nbins);
        if (particle_pt_edges.size() < 2) {
            std::cerr << "[ERROR] Could not build particle-level pT histogram edges from CLUSTER_MIN to JET_PT_MAX.\n";
            return 2;
        }
        particlePtAll = new TH1D("particle_pt_all",
                                 "Accepted particle-level constituents (pre-clustering, inclusive weighted yield);p_{T}^{particle} [GeV];Weighted constituent yield [mb/GeV]",
                                 (int)particle_pt_edges.size() - 1, particle_pt_edges.data());
    } else {
        particlePtAll = new TH1D("particle_pt_all",
                                 "Accepted particle-level constituents (pre-clustering, inclusive weighted yield);p_{T}^{particle} [GeV];Weighted constituent yield [mb/GeV]",
                                 jetpt_nbins, 0.0, jetPtMax);
    }

    particleEtaAll = new TH1D("particle_eta_all",
                              Form("Accepted particle-level constituents (pre-clustering, inclusive weighted yield, |#eta|<%.2f);#eta^{particle};Weighted constituent yield [mb]", particleEtaMax),
                              eta_nbins, -particleEtaMax, +particleEtaMax);

    particlePhiAll = new TH1D("particle_phi_all",
                              "Accepted particle-level constituents (pre-clustering, inclusive weighted yield);#phi^{particle} [rad];Weighted constituent yield [mb/rad]",
                              72, -M_PI, +M_PI);

    for (double R : Rlist) {
        RHist rr;
        rr.R = R;
        rr.Rtag = (int)std::lround(R * 100.0);

        // Jet eta acceptance per R
        double etaMaxJet = jetEtaMaxRaw;
        if (jetEtaMode == 1) etaMaxJet = std::max(0.0, jetEtaMaxRaw - R);
        rr.etaMaxJet = etaMaxJet;

        rr.jetDef = fastjet::JetDefinition(fastjet::antikt_algorithm, R);

        // Selectors
        //  - constituent cut is handled pre-clustering via particleEtaMax and clusterMin
        //  - jet eta acceptance is applied to jets
        rr.selIncl = fastjet::SelectorAbsEtaMax(etaMaxJet) && fastjet::SelectorPtMin(jetPtMin);
        rr.selLead = rr.selIncl; // lead/sublead filtering uses the same selector, then we check lead/sub cuts manually
        rr.selDijet = rr.selIncl;

        // Book histograms
        const int nbins_abs  = std::max(1, dphi_nbins/2);

        // |Delta phi| in [0,pi] only. The obsolete raw dphi in [0,2pi) family is intentionally retired.
        rr.dphiAbs.reserve(ptEdges.size()-1);
        rr.dphiAbsVsDeta.reserve(ptEdges.size()-1);
        rr.xjByPt.reserve(ptEdges.size()-1);
        rr.ajByPt.reserve(ptEdges.size()-1);


        rr.dphiAbs_nosubfrac.reserve(ptEdges.size()-1);
        rr.dphiAbsVsDeta_nosubfrac.reserve(ptEdges.size()-1);
        rr.xjByPt_nosubfrac.reserve(ptEdges.size()-1);
        rr.ajByPt_nosubfrac.reserve(ptEdges.size()-1);

        for (size_t i = 0; i + 1 < ptEdges.size(); ++i) {
            int lo = (int)ptEdges[i];
            int hi = (int)ptEdges[i+1];


            rr.dphiAbs.push_back(new TH1D(Form("dphi_abs_R%03d_%d_%d", rr.Rtag, lo, hi),
                                          Form("|#Delta#phi| (R=%.2f, %d-%d GeV, %s);|#Delta#phi|;mb/rad", R, lo, hi, dijetPairSelectionTitle.c_str()),
                                          nbins_abs, 0, M_PI));

            rr.dphiAbsVsDeta.push_back(new TH2D(Form("h2_dphi_abs_vs_deta_R%03d_%d_%d", rr.Rtag, lo, hi),
                                                Form("|#Delta#phi| vs |#Delta#eta| (R=%.2f, %d-%d GeV, %s);|#Delta#phi| [rad];|#Delta#eta|;d^{2}#sigma_{dijet}/d|#Delta#phi|d|#Delta#eta| [mb/rad]", R, lo, hi, dijetPairSelectionTitle.c_str()),
                                                nbins_abs, 0, M_PI,
                                                eta_nbins, 0, 2.0*rr.etaMaxJet));

            rr.xjByPt.push_back(new TH1D(Form("xj_R%03d_%d_%d", rr.Rtag, lo, hi),
                                         Form("x_{J}=p_{T,2}/p_{T,1} (R=%.2f, %d-%d GeV, %s);x_{J};d#sigma/dx_{J} [mb]", R, lo, hi, dijetPairSelectionTitle.c_str()),
                                         xj_nbins, 0.0, 1.0));

            rr.ajByPt.push_back(new TH1D(Form("aj_R%03d_%d_%d", rr.Rtag, lo, hi),
                                         Form("A_{J}=(p_{T,1}-p_{T,2})/(p_{T,1}+p_{T,2}) (R=%.2f, %d-%d GeV, %s);A_{J};d#sigma/dA_{J} [mb]", R, lo, hi, dijetPairSelectionTitle.c_str()),
                                         aj_nbins, 0.0, 1.0));

            // No-SUBFRAC counterparts (same binning, same pT binning)

            rr.dphiAbs_nosubfrac.push_back(new TH1D(Form("dphi_abs_R%03d_%d_%d_nosubfrac", rr.Rtag, lo, hi),
                                                    Form("|#Delta#phi| (R=%.2f, %d-%d GeV, %s, no SUBFRAC);|#Delta#phi|;mb/rad", R, lo, hi, dijetPairSelectionTitle.c_str()),
                                                    nbins_abs, 0, M_PI));

            rr.dphiAbsVsDeta_nosubfrac.push_back(new TH2D(Form("h2_dphi_abs_vs_deta_R%03d_%d_%d_nosubfrac", rr.Rtag, lo, hi),
                                                          Form("|#Delta#phi| vs |#Delta#eta| (R=%.2f, %d-%d GeV, %s, no SUBFRAC);|#Delta#phi| [rad];|#Delta#eta|;d^{2}#sigma_{dijet}/d|#Delta#phi|d|#Delta#eta| [mb/rad]", R, lo, hi, dijetPairSelectionTitle.c_str()),
                                                          nbins_abs, 0, M_PI,
                                                          eta_nbins, 0, 2.0*rr.etaMaxJet));

            rr.xjByPt_nosubfrac.push_back(new TH1D(Form("xj_R%03d_%d_%d_nosubfrac", rr.Rtag, lo, hi),
                                                   Form("x_{J}=p_{T,2}/p_{T,1} (R=%.2f, %d-%d GeV, %s, no SUBFRAC);x_{J};d#sigma/dx_{J} [mb]", R, lo, hi, dijetPairSelectionTitle.c_str()),
                                                   xj_nbins, 0.0, 1.0));

            rr.ajByPt_nosubfrac.push_back(new TH1D(Form("aj_R%03d_%d_%d_nosubfrac", rr.Rtag, lo, hi),
                                                   Form("A_{J}=(p_{T,1}-p_{T,2})/(p_{T,1}+p_{T,2}) (R=%.2f, %d-%d GeV, %s, no SUBFRAC);A_{J};d#sigma/dA_{J} [mb]", R, lo, hi, dijetPairSelectionTitle.c_str()),
                                                   aj_nbins, 0.0, 1.0));
        } // end ptEdges booking loop


        rr.dphiAbsAll = new TH1D(Form("dphi_abs_R%03d_%d_%d_fullrange", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag),
                                 Form("|#Delta#phi| (R=%.2f, %s, %s);|#Delta#phi|;mb/rad", R, ptLeadAllRangeTitle.c_str(), dijetPairSelectionTitle.c_str()),
                                 nbins_abs, 0, M_PI);

        rr.dphiAbsVsDetaAll = new TH2D(Form("h2_dphi_abs_vs_deta_R%03d_%d_%d_fullrange", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag),
                                       Form("|#Delta#phi| vs |#Delta#eta| (R=%.2f, p_{T,1}=%s, %s);|#Delta#phi| [rad];|#Delta#eta|;d^{2}#sigma_{dijet}/d|#Delta#phi|d|#Delta#eta| [mb/rad]", R, ptLeadAllRangeTitle.c_str(), dijetPairSelectionTitle.c_str()),
                                       nbins_abs, 0, M_PI,
                                       eta_nbins, 0, 2.0*rr.etaMaxJet);


        rr.dphiAbsAll_nosubfrac = new TH1D(Form("dphi_abs_R%03d_%d_%d_fullrange_nosubfrac", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag),
                                           Form("|#Delta#phi| (R=%.2f, %s, %s, no SUBFRAC);|#Delta#phi|;mb/rad", R, ptLeadAllRangeTitle.c_str(), dijetPairSelectionTitle.c_str()),
                                           nbins_abs, 0, M_PI);

        rr.dphiAbsVsDetaAll_nosubfrac = new TH2D(Form("h2_dphi_abs_vs_deta_R%03d_%d_%d_fullrange_nosubfrac", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag),
                                                 Form("|#Delta#phi| vs |#Delta#eta| (R=%.2f, p_{T,1}=%s, %s, no SUBFRAC);|#Delta#phi| [rad];|#Delta#eta|;d^{2}#sigma_{dijet}/d|#Delta#phi|d|#Delta#eta| [mb/rad]", R, ptLeadAllRangeTitle.c_str(), dijetPairSelectionTitle.c_str()),
                                                 nbins_abs, 0, M_PI,
                                                 eta_nbins, 0, 2.0*rr.etaMaxJet);

        // η histograms: use the actual accepted jet-axis range for this R
        rr.etaLead = new TH1D(Form("eta_lead_R%03d_%d_%d_fullrange", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag),
                              Form("#eta_{lead} (R=%.2f, p_{T,1}=%s, |#eta_{jet}|<%.2f, %s);#eta;d#sigma/d#eta [mb]", R, ptLeadAllRangeTitle.c_str(), rr.etaMaxJet, dijetPairSelectionTitle.c_str()),
                              eta_nbins, -rr.etaMaxJet, +rr.etaMaxJet);

        rr.etaSub  = new TH1D(Form("eta_sub_R%03d_%d_%d_fullrange", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag),
                              Form("#eta_{sub} (R=%.2f, p_{T,1}=%s, |#eta_{jet}|<%.2f, %s);#eta;d#sigma/d#eta [mb]", R, ptLeadAllRangeTitle.c_str(), rr.etaMaxJet, dijetPairSelectionTitle.c_str()),
                              eta_nbins, -rr.etaMaxJet, +rr.etaMaxJet);

        rr.etaLead_nosubfrac = new TH1D(Form("eta_lead_R%03d_%d_%d_fullrange_nosubfrac", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag),
                                        Form("#eta_{lead} (R=%.2f, p_{T,1}=%s, |#eta_{jet}|<%.2f, %s, no SUBFRAC);#eta;d#sigma/d#eta [mb]", R, ptLeadAllRangeTitle.c_str(), rr.etaMaxJet, dijetPairSelectionTitle.c_str()),
                                        eta_nbins, -rr.etaMaxJet, +rr.etaMaxJet);

        rr.etaSub_nosubfrac = new TH1D(Form("eta_sub_R%03d_%d_%d_fullrange_nosubfrac", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag),
                                       Form("#eta_{sub} (R=%.2f, p_{T,1}=%s, |#eta_{jet}|<%.2f, %s, no SUBFRAC);#eta;d#sigma/d#eta [mb]", R, ptLeadAllRangeTitle.c_str(), rr.etaMaxJet, dijetPairSelectionTitle.c_str()),
                                       eta_nbins, -rr.etaMaxJet, +rr.etaMaxJet);

        // Jet pT spectra histograms
        rr.jetPtLead = new TH1D(Form("jetpt_lead_R%03d_%d_%d_fullrange", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag),
                                Form("Leading jet p_{T} (dijet-selected, R=%.2f, p_{T,1}=%s, %s);p_{T} [GeV];mb/GeV", R, ptLeadAllRangeTitle.c_str(), dijetPairSelectionTitle.c_str()),
                                (int)jetpt_edges.size()-1, jetpt_edges.data());

        rr.jetPtSub  = new TH1D(Form("jetpt_sublead_R%03d_%d_%d_fullrange", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag),
                                Form("Subleading jet p_{T} (dijet-selected, R=%.2f, p_{T,1}=%s, %s);p_{T} [GeV];mb/GeV", R, ptLeadAllRangeTitle.c_str(), dijetPairSelectionTitle.c_str()),
                                (int)jetpt_edges.size()-1, jetpt_edges.data());

        rr.jetPtLead_nosubfrac = new TH1D(Form("jetpt_lead_R%03d_%d_%d_fullrange_nosubfrac", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag),
                                          Form("Leading jet p_{T} (dijet-selected, R=%.2f, p_{T,1}=%s, %s, no SUBFRAC);p_{T} [GeV];mb/GeV", R, ptLeadAllRangeTitle.c_str(), dijetPairSelectionTitle.c_str()),
                                          (int)jetpt_edges.size()-1, jetpt_edges.data());

        rr.jetPtSub_nosubfrac = new TH1D(Form("jetpt_sublead_R%03d_%d_%d_fullrange_nosubfrac", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag),
                                         Form("Subleading jet p_{T} (dijet-selected, R=%.2f, p_{T,1}=%s, %s, no SUBFRAC);p_{T} [GeV];mb/GeV", R, ptLeadAllRangeTitle.c_str(), dijetPairSelectionTitle.c_str()),
                                         (int)jetpt_edges.size()-1, jetpt_edges.data());

        rr.h2SubleadVsLeadAll = new TH2D(Form("h2_sublead_vs_lead_R%03d_%d_%d_fullrange", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag),
                                         Form("Subleading vs leading jet p_{T} (dijet-selected, R=%.2f, p_{T,1}=%s, %s);p_{T}^{lead} [GeV];p_{T}^{sublead} [GeV];Weighted dijet yield [mb]", R, ptLeadAllRangeTitle.c_str(), dijetPairSelectionTitle.c_str()),
                                         (int)jetpt_edges.size()-1, jetpt_edges.data(),
                                         (int)jetpt_edges.size()-1, jetpt_edges.data());

        rr.h2SubleadVsLeadAll_nosubfrac = new TH2D(Form("h2_sublead_vs_lead_R%03d_%d_%d_fullrange_nosubfrac", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag),
                                                   Form("Subleading vs leading jet p_{T} (dijet-selected, R=%.2f, p_{T,1}=%s, %s, no SUBFRAC);p_{T}^{lead} [GeV];p_{T}^{sublead} [GeV];Weighted dijet yield [mb]", R, ptLeadAllRangeTitle.c_str(), dijetPairSelectionTitle.c_str()),
                                                   (int)jetpt_edges.size()-1, jetpt_edges.data(),
                                                   (int)jetpt_edges.size()-1, jetpt_edges.data());

        rr.profSubleadVsLeadPtLeadBins = new TProfile(Form("prof_sublead_vs_lead_R%03d_%d_%d_fullrange_ptleadbins", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag),
                                                      Form("#LTp_{T}^{sublead}#GT vs p_{T}^{lead} (dijet-selected, R=%.2f, p_{T,1}=%s, %s);p_{T}^{lead} [GeV];#LTp_{T}^{sublead}#GT [GeV]", R, ptLeadAllRangeTitle.c_str(), dijetPairSelectionTitle.c_str()),
                                                      (int)ptEdges.size()-1, ptEdges.data());

        rr.profSubleadVsLeadPtLeadBins_nosubfrac = new TProfile(Form("prof_sublead_vs_lead_R%03d_%d_%d_fullrange_ptleadbins_nosubfrac", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag),
                                                                Form("#LTp_{T}^{sublead}#GT vs p_{T}^{lead} (dijet-selected, R=%.2f, p_{T,1}=%s, %s, no SUBFRAC);p_{T}^{lead} [GeV];#LTp_{T}^{sublead}#GT [GeV]", R, ptLeadAllRangeTitle.c_str(), dijetPairSelectionTitle.c_str()),
                                                                (int)ptEdges.size()-1, ptEdges.data());

        rr.jetPtIncl = new TH1D(Form("jetpt_incl_R%03d_all", rr.Rtag),
                                Form("Inclusive jet p_{T} (R=%.2f);p_{T} [GeV];mb/GeV", R),
                                (int)jetpt_edges.size()-1, jetpt_edges.data());

        // Dijet imbalance observables
        rr.xjAll = new TH1D(Form("xj_R%03d_%d_%d_fullrange", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag),
                            Form("x_{J}=p_{T,2}/p_{T,1} (R=%.2f, %s, %s);x_{J};d#sigma/dx_{J} [mb]", R, ptLeadAllRangeTitle.c_str(), dijetPairSelectionTitle.c_str()),
                            xj_nbins, 0.0, 1.0);

        rr.ajAll = new TH1D(Form("aj_R%03d_%d_%d_fullrange", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag),
                            Form("A_{J}=(p_{T,1}-p_{T,2})/(p_{T,1}+p_{T,2}) (R=%.2f, %s, %s);A_{J};d#sigma/dA_{J} [mb]", R, ptLeadAllRangeTitle.c_str(), dijetPairSelectionTitle.c_str()),
                            aj_nbins, 0.0, 1.0);

        rr.xjAll_nosubfrac = new TH1D(Form("xj_R%03d_%d_%d_fullrange_nosubfrac", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag),
                                      Form("x_{J}=p_{T,2}/p_{T,1} (R=%.2f, %s, %s, no SUBFRAC);x_{J};d#sigma/dx_{J} [mb]", R, ptLeadAllRangeTitle.c_str(), dijetPairSelectionTitle.c_str()),
                                      xj_nbins, 0.0, 1.0);

        rr.ajAll_nosubfrac = new TH1D(Form("aj_R%03d_%d_%d_fullrange_nosubfrac", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag),
                                      Form("A_{J}=(p_{T,1}-p_{T,2})/(p_{T,1}+p_{T,2}) (R=%.2f, %s, %s, no SUBFRAC);A_{J};d#sigma/dA_{J} [mb]", R, ptLeadAllRangeTitle.c_str(), dijetPairSelectionTitle.c_str()),
                                      aj_nbins, 0.0, 1.0);
        // Mjj all
        
        if (mjj_enable){
            if (mjj_log_bins){
                rr.mjjAll = new TH1D(Form("mjj_R%03d_%d_%d_fullrange", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag),
                                     Form("M_{jj} (R=%.2f, %s, %s);M_{jj} [GeV];mb/GeV", R, ptLeadAllRangeTitle.c_str(), mjjSelectionTitle.c_str()),
                                     (int)mjj_edges.size()-1, mjj_edges.data());

                rr.mjjAll_nosubfrac = new TH1D(Form("mjj_R%03d_%d_%d_fullrange_nosubfrac", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag),
                                              Form("M_{jj} (R=%.2f, %s, %s, no SUBFRAC);M_{jj} [GeV];mb/GeV", R, ptLeadAllRangeTitle.c_str(), mjjSelectionTitle.c_str()),
                                              (int)mjj_edges.size()-1, mjj_edges.data());
            } else {
                rr.mjjAll = new TH1D(Form("mjj_R%03d_%d_%d_fullrange", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag),
                                     Form("M_{jj} (R=%.2f, %s, %s);M_{jj} [GeV];mb/GeV", R, ptLeadAllRangeTitle.c_str(), mjjSelectionTitle.c_str()),
                                     mjj_nbins, mjj_min, mjj_max);

                rr.mjjAll_nosubfrac = new TH1D(Form("mjj_R%03d_%d_%d_fullrange_nosubfrac", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag),
                                              Form("M_{jj} (R=%.2f, %s, %s, no SUBFRAC);M_{jj} [GeV];mb/GeV", R, ptLeadAllRangeTitle.c_str(), mjjSelectionTitle.c_str()),
                                              mjj_nbins, mjj_min, mjj_max);
            }
        }

        rh.push_back(rr);
    }

    // Finalize cutflow containers now that rh is built
    cf_default.assign(rh.size(), CutFlow{});
    cf_nosubfrac.assign(rh.size(), CutFlow{});
    jet_stats.assign(rh.size(), JetStats{});

    std::vector<DijetObservableCounts> dijet_counts_default(rh.size());
    std::vector<DijetObservableCounts> dijet_counts_nosubfrac(rh.size());
    const size_t nPtLeadBins = (ptEdges.size() > 1) ? (ptEdges.size() - 1) : 0;
    for(size_t ir=0; ir<rh.size(); ++ir){
        dijet_counts_default[ir].dijet_base_ptlead.assign(nPtLeadBins, 0);
        dijet_counts_default[ir].dphi_abs_ptlead.assign(nPtLeadBins, 0);
        dijet_counts_default[ir].xj_ptlead.assign(nPtLeadBins, 0);
        dijet_counts_default[ir].aj_ptlead.assign(nPtLeadBins, 0);
        dijet_counts_nosubfrac[ir].dijet_base_ptlead.assign(nPtLeadBins, 0);
        dijet_counts_nosubfrac[ir].dphi_abs_ptlead.assign(nPtLeadBins, 0);
        dijet_counts_nosubfrac[ir].xj_ptlead.assign(nPtLeadBins, 0);
        dijet_counts_nosubfrac[ir].aj_ptlead.assign(nPtLeadBins, 0);
    }

    auto book_count_hist_for = [&](TH1D* source, bool is_nosubfrac){
        if(!source) return;
        const std::string count_name = std::string("count_") + source->GetName();
        std::string count_title = std::string(source->GetTitle()) + " [unweighted count-density mirror]";
        TH1D* h = dynamic_cast<TH1D*>(source->Clone(count_name.c_str()));
        if(!h){
            std::cerr << "[ERROR] Failed to clone count histogram for " << source->GetName() << "\n";
            std::exit(2);
        }
        h->Reset("ICES");
        h->SetTitle(count_title.c_str());
        if(h->GetYaxis()) h->GetYaxis()->SetTitle("dN/dX (unweighted count density)");
        h->SetDirectory(nullptr);
        h->Sumw2();
        count_hist_for_weighted_hist[source] = h;
        if(is_nosubfrac) count_hist_nosubfrac.push_back(h);
        else count_hist_default.push_back(h);
    };

    for(auto& rr : rh){
        if(!rr.enabled) continue;
        for(auto* h : rr.dphiAbs) book_count_hist_for(h, false);
        book_count_hist_for(rr.dphiAbsAll, false);
        book_count_hist_for(rr.jetPtLead, false);
        book_count_hist_for(rr.jetPtSub, false);
        book_count_hist_for(rr.xjAll, false);
        for(auto* h : rr.xjByPt) book_count_hist_for(h, false);
        book_count_hist_for(rr.ajAll, false);
        for(auto* h : rr.ajByPt) book_count_hist_for(h, false);
        book_count_hist_for(rr.mjjAll, false);

        for(auto* h : rr.dphiAbs_nosubfrac) book_count_hist_for(h, true);
        book_count_hist_for(rr.dphiAbsAll_nosubfrac, true);
        book_count_hist_for(rr.jetPtLead_nosubfrac, true);
        book_count_hist_for(rr.jetPtSub_nosubfrac, true);
        book_count_hist_for(rr.xjAll_nosubfrac, true);
        for(auto* h : rr.xjByPt_nosubfrac) book_count_hist_for(h, true);
        book_count_hist_for(rr.ajAll_nosubfrac, true);
        for(auto* h : rr.ajByPt_nosubfrac) book_count_hist_for(h, true);
        book_count_hist_for(rr.mjjAll_nosubfrac, true);
    }

    std::cout << "[INFO] Booked count-density histograms: default=" << count_hist_default.size()
              << " nosubfrac=" << count_hist_nosubfrac.size() << "\n";

    auto fill_weighted_and_count = [&](TH1D* h, double x, double weight){
        if(!h) return;
        h->Fill(x, weight);
        auto it = count_hist_for_weighted_hist.find(h);
        if(it != count_hist_for_weighted_hist.end() && it->second){
            it->second->Fill(x, 1.0);
        }
    };

    auto find_ptlead_bin = [&](double ptLead)->int{
        for(size_t i=0; i+1<ptEdges.size(); ++i){
            const bool is_last = (i + 2 == ptEdges.size());
            const bool in_bin = (ptLead >= ptEdges[i]) && (is_last ? (ptLead <= ptEdges[i+1]) : (ptLead < ptEdges[i+1]));
            if(in_bin) return static_cast<int>(i);
        }
        return -1;
    };

    auto in_ptlead_fullrange = [&](double ptLead)->bool{
        if (ptEdges.size() < 2) return false;
        return (ptLead >= ptEdges.front()) && (ptLead <= ptEdges.back());
    };

    // One-time documentation of which cuts apply to which histogram groups
    print_histogram_map();

    // One-time inventory of booked histograms (helps sanity-check ROOT output size)
    auto count_hist_ptrs = [&](const RHist& rr){
        long long n = 0;
        auto bump = [&](const TH1* h){ if (h) ++n; };
        bump(rr.jetPtIncl); bump(rr.jetPtLead); bump(rr.jetPtSub);
        bump(rr.h2SubleadVsLeadAll); bump(rr.profSubleadVsLeadPtLeadBins);        bump(rr.dphiAbsAll); bump(rr.dphiAbsVsDetaAll);
        bump(rr.xjAll); bump(rr.ajAll);
        bump(rr.etaLead); bump(rr.etaSub);
        bump(rr.mjjAll);
        // binned vectors
        for (auto* h : rr.dphiAbs) bump(h);
        for (auto* h : rr.dphiAbsVsDeta) bump(h);
        for (auto* h : rr.xjByPt) bump(h);
        for (auto* h : rr.ajByPt) bump(h);

        // NO-SUBFRAC add-ons
        bump(rr.jetPtLead_nosubfrac); bump(rr.jetPtSub_nosubfrac);
        bump(rr.h2SubleadVsLeadAll_nosubfrac); bump(rr.profSubleadVsLeadPtLeadBins_nosubfrac);        bump(rr.dphiAbsAll_nosubfrac); bump(rr.dphiAbsVsDetaAll_nosubfrac);
        bump(rr.xjAll_nosubfrac); bump(rr.ajAll_nosubfrac);
        bump(rr.etaLead_nosubfrac); bump(rr.etaSub_nosubfrac);
        bump(rr.mjjAll_nosubfrac);
        for (auto* h : rr.dphiAbs_nosubfrac) bump(h);
        for (auto* h : rr.dphiAbsVsDeta_nosubfrac) bump(h);
        for (auto* h : rr.xjByPt_nosubfrac) bump(h);
        for (auto* h : rr.ajByPt_nosubfrac) bump(h);
        return n;
    };

    long long booked_total = 0;
    if (particlePtAll)  ++booked_total;
    if (particleEtaAll) ++booked_total;
    if (particlePhiAll) ++booked_total;
    std::cout << "[INFO] Booked particle-level QA histograms: "
              << ((particlePtAll ? 1 : 0) + (particleEtaAll ? 1 : 0) + (particlePhiAll ? 1 : 0))
              << " (particle_pt_all, particle_eta_all, particle_phi_all)\n";
    for (size_t ir = 0; ir < rh.size(); ++ir){
        if (!rh[ir].enabled) continue;
        const long long n = count_hist_ptrs(rh[ir]);
        booked_total += n;
        std::cout << "[INFO] Booked histograms: R=" << rh[ir].R << "  count=" << n << "\n";
    }
    std::cout << "[INFO] Booked histograms total (all enabled R): " << booked_total << "\n";

    // ---- Event loop ----
    std::string line;
    std::vector<fastjet::PseudoJet> parts;
    long long totalEv = 0;
    long long headerHits = 0;  // count of matched event header lines
    long long passEvAny = 0;
    std::vector<long long> passEvR(rh.size(), 0);
    long long passEvAny_nosubfrac = 0;
    std::vector<long long> passEvR_nosubfrac(rh.size(), 0);
    bool have_open_event = false;


    auto process_event = [&](const std::vector<fastjet::PseudoJet>& particles){
        const double weight = weight_mb_per_event;

        bool passed_any = false;
        bool passed_any_nosubfrac = false;

        for (size_t ir = 0; ir < rh.size(); ++ir) {
            // Cutflow: event entered this R loop
            cf_default[ir].events_total++;
            cf_nosubfrac[ir].events_total++;
            if(!rh[ir].enabled) continue;
            const double R = rh[ir].R;
            const double etaMaxJet = rh[ir].etaMaxJet;

            // Cluster
            fastjet::ClusterSequence cs(particles, rh[ir].jetDef);

            // Jet acceptance breakdown (logging only)
            std::vector<fastjet::PseudoJet> jets_all = cs.inclusive_jets();
            jet_stats[ir].jets_raw += (long long)jets_all.size();
            const fastjet::Selector selPt = fastjet::SelectorPtMin(jetPtMin);
            const fastjet::Selector selEta = fastjet::SelectorAbsEtaMax(etaMaxJet);
            std::vector<fastjet::PseudoJet> jets_pt  = selPt(jets_all);
            std::vector<fastjet::PseudoJet> jets_eta = selEta(jets_all);
            jet_stats[ir].jets_pass_pt  += (long long)jets_pt.size();
            jet_stats[ir].jets_pass_eta += (long long)jets_eta.size();

            // Actual jet acceptance used for analysis (pt AND eta)
            std::vector<fastjet::PseudoJet> jets = rh[ir].selIncl(jets_all);
            jet_stats[ir].jets_pass_pt_eta += (long long)jets.size();
            if (!jets.empty()) jet_stats[ir].events_ge1_acc++;
            if (jets_pt.size()  >= 2) jet_stats[ir].events_ge2_pt++;
            if (jets_eta.size() >= 2) jet_stats[ir].events_ge2_eta++;
            if (jets.size()     >= 2) jet_stats[ir].events_ge2_pt_eta++;
            // Fill inclusive jet spectrum: ALL jets passing the base selection (pt/eta).
            // Statistics convention: this observable is event-weighted, so if multiple accepted jets from the
            // same event land in the same pT bin, that bin receives one event-level contribution equal to the
            // sum of jet weights in that bin. This preserves the correct event-level variance in Sumw2.
            if (rh[ir].jetPtIncl){
                std::unordered_map<int, double> incl_bin_weights;
                incl_bin_weights.reserve(jets.size());
                for(const auto& j : jets){
                    const int bin = rh[ir].jetPtIncl->FindFixBin(j.pt());
                    incl_bin_weights[bin] += weight;
                }
                for(const auto& kv : incl_bin_weights){
                    fill_histogram_event_weighted_bin(rh[ir].jetPtIncl, kv.first, kv.second);
                }
            }

            if (jets.size() < 2) continue;
            cf_default[ir].jets_ge2++;
            cf_nosubfrac[ir].jets_ge2++;

            if (dijetRequireExactlyTwoJets && jets.size() != 2) {
                cf_default[ir].veto_extra_jets++;
                cf_nosubfrac[ir].veto_extra_jets++;
                continue;
            }
            cf_default[ir].pass_jet_multiplicity++;
            cf_nosubfrac[ir].pass_jet_multiplicity++;

            std::sort(jets.begin(), jets.end(), [](const auto& a, const auto& b){ return a.pt() > b.pt(); });

            // Apply lead/sublead pT cuts (dijet-selected observables share these cuts)
            if (jets[0].pt() < leadPtMin) continue;
            cf_default[ir].pass_lead++;
            cf_nosubfrac[ir].pass_lead++;

            if (subPtMin > 0.0 && jets[1].pt() < subPtMin) continue;
            cf_default[ir].pass_sublead++;
            cf_nosubfrac[ir].pass_sublead++;

            cf_default[ir].pass_leadsub++;   // (same as pass_sublead)
            cf_nosubfrac[ir].pass_leadsub++; // (same as pass_sublead)

            const double ystar_pair = ystar_enable
                ? (0.5 * std::fabs(jets[0].rapidity() - jets[1].rapidity()))
                : 0.0;

            bool passYstar_ns_global = true;
            if (ystar_enable) {
                cf_nosubfrac[ir].ystar_checked++;
                passYstar_ns_global = (ystar_pair <= ystar_max);
                if (passYstar_ns_global) cf_nosubfrac[ir].ystar_pass++;
            }

            // ---- Fill NO-SUBFRAC versions (all other cuts unchanged, plus optional global y* gate) ----
            if (passYstar_ns_global) {
                const double pt1_ns = jets[0].pt();
                const double pt2_ns = jets[1].pt();
                const bool inPtLeadFullRangeNs = in_ptlead_fullrange(pt1_ns);

                if (inPtLeadFullRangeNs) {
                    // This event passed the dijet selection (pre-SUBFRAC) for this R and the advertised full-range lead-pT contract.
                    passed_any_nosubfrac = true;
                    passEvR_nosubfrac[ir]++;
                    fill_weighted_and_count(rh[ir].jetPtLead_nosubfrac, pt1_ns, weight);
                    fill_weighted_and_count(rh[ir].jetPtSub_nosubfrac, pt2_ns, weight);
                    if (rh[ir].h2SubleadVsLeadAll_nosubfrac) rh[ir].h2SubleadVsLeadAll_nosubfrac->Fill(pt1_ns, pt2_ns, weight);
                    if (rh[ir].profSubleadVsLeadPtLeadBins_nosubfrac) rh[ir].profSubleadVsLeadPtLeadBins_nosubfrac->Fill(pt1_ns, pt2_ns, weight);
                }

                if (pt1_ns > 0.0) {
                    double xj_ns = pt2_ns / pt1_ns;
                    if (xj_ns >= 1.0) xj_ns = std::nextafter(1.0, 0.0);
                    if (xj_ns < 0.0) xj_ns = 0.0;
                    const double aj_ns = (pt1_ns - pt2_ns) / (pt1_ns + pt2_ns);

                    cf_nosubfrac[ir].imbalance_checked++;
                    bool fillImbalance_ns = true;
                    if (imbalanceBacktoback) {
                        double dphi_12_ns = wrapDeltaPhi(jets[0].phi() - jets[1].phi());
                        if (dphi_12_ns < 0) dphi_12_ns += 2*M_PI;
                        fillImbalance_ns = (std::abs(dphi_12_ns - M_PI) < imbalanceTolRad);
                    }
                    if (fillImbalance_ns && inPtLeadFullRangeNs) {
                        cf_nosubfrac[ir].imbalance_pass_bb++;
                        dijet_counts_nosubfrac[ir].xj_all++;
                        dijet_counts_nosubfrac[ir].aj_all++;
                        fill_weighted_and_count(rh[ir].xjAll_nosubfrac, xj_ns, weight);
                        fill_weighted_and_count(rh[ir].ajAll_nosubfrac, aj_ns, weight);
                    }
                    const int ptLeadBinImbNs = find_ptlead_bin(pt1_ns);
                    if (fillImbalance_ns && ptLeadBinImbNs >= 0) {
                        const size_t i = static_cast<size_t>(ptLeadBinImbNs);
                        dijet_counts_nosubfrac[ir].xj_ptlead[i]++;
                        dijet_counts_nosubfrac[ir].aj_ptlead[i]++;
                        if (i < rh[ir].xjByPt_nosubfrac.size()) fill_weighted_and_count(rh[ir].xjByPt_nosubfrac[i], xj_ns, weight);
                        if (i < rh[ir].ajByPt_nosubfrac.size()) fill_weighted_and_count(rh[ir].ajByPt_nosubfrac[i], aj_ns, weight);
                    }
                }

                double dphi_ns = wrapDeltaPhi(jets[0].phi() - jets[1].phi());
                if (dphi_ns < 0) dphi_ns += 2*M_PI;

                double dphi_abs_ns = std::fabs(wrapDeltaPhi(jets[0].phi() - jets[1].phi()));
                if (dphi_abs_ns >= M_PI) dphi_abs_ns = std::nextafter(M_PI, 0.0);
                double deta_abs_ns = std::fabs(jets[0].pseudorapidity() - jets[1].pseudorapidity());
                const double deta_abs_ns_max = 2.0 * rh[ir].etaMaxJet;
                if (deta_abs_ns >= deta_abs_ns_max) deta_abs_ns = std::nextafter(deta_abs_ns_max, 0.0);

                const int ptLeadBinNs = find_ptlead_bin(pt1_ns);
                if (ptLeadBinNs >= 0) {
                    const size_t i = static_cast<size_t>(ptLeadBinNs);
                    dijet_counts_nosubfrac[ir].dijet_base_ptlead[i]++;
                    dijet_counts_nosubfrac[ir].dphi_abs_ptlead[i]++;
                    if (i < rh[ir].dphiAbs_nosubfrac.size() && rh[ir].dphiAbs_nosubfrac[i]) {
                        fill_weighted_and_count(rh[ir].dphiAbs_nosubfrac[i], dphi_abs_ns, weight);
                    }
                    if (i < rh[ir].dphiAbsVsDeta_nosubfrac.size() && rh[ir].dphiAbsVsDeta_nosubfrac[i]) {
                        rh[ir].dphiAbsVsDeta_nosubfrac[i]->Fill(dphi_abs_ns, deta_abs_ns, weight);
                    }
                }

                if (inPtLeadFullRangeNs) {
                    dijet_counts_nosubfrac[ir].dijet_base_all++;

                    fill_weighted_and_count(rh[ir].dphiAbsAll_nosubfrac, dphi_abs_ns, weight);
                    dijet_counts_nosubfrac[ir].dphi_abs_all++;
                    if (rh[ir].dphiAbsVsDetaAll_nosubfrac) rh[ir].dphiAbsVsDetaAll_nosubfrac->Fill(dphi_abs_ns, deta_abs_ns, weight);

                    if (rh[ir].etaLead_nosubfrac) rh[ir].etaLead_nosubfrac->Fill(jets[0].pseudorapidity(), weight);
                    if (rh[ir].etaSub_nosubfrac)  rh[ir].etaSub_nosubfrac ->Fill(jets[1].pseudorapidity(), weight);
                    // Mjj (NO-SUBFRAC branch): apply the optional Mjj back-to-back gate after the global dijet-pair y* gate (if enabled).
                    if (mjj_enable) {
                        cf_nosubfrac[ir].mjj_checked++;
                        double dphi_to_pi_ns = std::fabs(std::atan2(std::sin(dphi_ns - M_PI), std::cos(dphi_ns - M_PI)));
                        const bool pass_mjj_bb_ns = (!mjj_require_backtoback) || (dphi_to_pi_ns <= tol_rad);
                        if (pass_mjj_bb_ns) {
                            cf_nosubfrac[ir].mjj_pass_bb++;
                            dijet_counts_nosubfrac[ir].mjj_all++;
                            double mjj_ns = (jets[0] + jets[1]).m();
                            fill_weighted_and_count(rh[ir].mjjAll_nosubfrac, mjj_ns, weight);

                        }
                    }
                }
            } // end NO-SUBFRAC block

            // Apply SUBFRAC cut only for the existing (default) dijet-selected histograms
            if (subFracMin > 0.0 && jets[1].pt() < subFracMin * jets[0].pt()) continue;
            cf_default[ir].pass_subfrac++;

            bool passYstar_default_global = true;
            if (ystar_enable) {
                cf_default[ir].ystar_checked++;
                passYstar_default_global = (ystar_pair <= ystar_max);
                if (passYstar_default_global) cf_default[ir].ystar_pass++;
            }
            if (!passYstar_default_global) continue;

            // Dijet momentum imbalance / full-range contract
            const double pt1 = jets[0].pt();
            const double pt2 = jets[1].pt();
            const bool inPtLeadFullRange = in_ptlead_fullrange(pt1);

            // Fill lead/sublead jet spectra and their correlation observables only when the full-range lead-pT contract is satisfied.
            if (inPtLeadFullRange) {
                fill_weighted_and_count(rh[ir].jetPtLead, pt1, weight);
                fill_weighted_and_count(rh[ir].jetPtSub, pt2, weight);
                if (rh[ir].h2SubleadVsLeadAll) rh[ir].h2SubleadVsLeadAll->Fill(pt1, pt2, weight);
                if (rh[ir].profSubleadVsLeadPtLeadBins) rh[ir].profSubleadVsLeadPtLeadBins->Fill(pt1, pt2, weight);
            }

            // Dijet momentum imbalance
            if(pt1 > 0.0){
                double xj = pt2 / pt1;
                // ROOT histograms use [xmin,xmax) for the last bin; x==xmax goes to overflow.
                // Clamp exact-edge values so xJ==1 lands in the last bin (hist range remains [0,1]).
                if (xj >= 1.0) xj = std::nextafter(1.0, 0.0);
                if (xj < 0.0) xj = 0.0;
                const double aj = (pt1 - pt2) / (pt1 + pt2);
                // Check back-to-back requirement for imbalance observables if requested
                cf_default[ir].imbalance_checked++;
                bool fillImbalance = true;
                if (imbalanceBacktoback) {
                    double dphi_12 = wrapDeltaPhi(jets[0].phi() - jets[1].phi());
                    if (dphi_12 < 0) dphi_12 += 2*M_PI;
                    // Back-to-back means |Δφ - π| < imbalanceTolDeg (converted to radians)
                    fillImbalance = (std::abs(dphi_12 - M_PI) < imbalanceTolRad);
                }
                if (fillImbalance && inPtLeadFullRange) {
                    cf_default[ir].imbalance_pass_bb++;
                    dijet_counts_default[ir].xj_all++;
                    dijet_counts_default[ir].aj_all++;
                    fill_weighted_and_count(rh[ir].xjAll, xj, weight);
                    fill_weighted_and_count(rh[ir].ajAll, aj, weight);
                }
                const int ptLeadBinImb = find_ptlead_bin(pt1);
                if (fillImbalance && ptLeadBinImb >= 0) {
                    const size_t i = static_cast<size_t>(ptLeadBinImb);
                    dijet_counts_default[ir].xj_ptlead[i]++;
                    dijet_counts_default[ir].aj_ptlead[i]++;
                    if (i < rh[ir].xjByPt.size()) fill_weighted_and_count(rh[ir].xjByPt[i], xj, weight);
                    if (i < rh[ir].ajByPt.size()) fill_weighted_and_count(rh[ir].ajByPt[i], aj, weight);
                }
            }

            double dphi = wrapDeltaPhi(jets[0].phi() - jets[1].phi());
            if (dphi < 0) dphi += 2*M_PI;

            double ptLead = jets[0].pt();

            // Standard (experimental/theory) definition: absolute minimal separation in [0,π]
            double dphi_abs = std::fabs(wrapDeltaPhi(jets[0].phi() - jets[1].phi()));
            // ROOT histograms use [xmin,xmax) for the last bin; |Δφ|==π would otherwise go to overflow.
            // Clamp exact-edge values so |Δφ|==π lands in the last bin (hist range remains [0,π]).
            if (dphi_abs >= M_PI) dphi_abs = std::nextafter(M_PI, 0.0);
            double deta_abs = std::fabs(jets[0].pseudorapidity() - jets[1].pseudorapidity());
            const double deta_abs_max = 2.0 * rh[ir].etaMaxJet;
            if (deta_abs >= deta_abs_max) deta_abs = std::nextafter(deta_abs_max, 0.0);

            const int ptLeadBin = find_ptlead_bin(ptLead);
            if (ptLeadBin >= 0) {
                const size_t i = static_cast<size_t>(ptLeadBin);
                dijet_counts_default[ir].dijet_base_ptlead[i]++;
                dijet_counts_default[ir].dphi_abs_ptlead[i]++;
                if (i < rh[ir].dphiAbs.size()) fill_weighted_and_count(rh[ir].dphiAbs[i], dphi_abs, weight);
                if (i < rh[ir].dphiAbsVsDeta.size() && rh[ir].dphiAbsVsDeta[i]) rh[ir].dphiAbsVsDeta[i]->Fill(dphi_abs, deta_abs, weight);
            }

            if (inPtLeadFullRange) {
                // This event passed the dijet selection for this R and the advertised full-range lead-pT contract.
                passed_any = true;
                passEvR[ir]++;

                dijet_counts_default[ir].dijet_base_all++;

                fill_weighted_and_count(rh[ir].dphiAbsAll, dphi_abs, weight);
                dijet_counts_default[ir].dphi_abs_all++;
                if (rh[ir].dphiAbsVsDetaAll) rh[ir].dphiAbsVsDetaAll->Fill(dphi_abs, deta_abs, weight);

                rh[ir].etaLead->Fill(jets[0].pseudorapidity(), weight);
                rh[ir].etaSub ->Fill(jets[1].pseudorapidity(), weight);

                if(rh[ir].mjjAll){
                    cf_default[ir].mjj_checked++;
                    double dphi_to_pi = std::fabs(std::atan2(std::sin(dphi - M_PI), std::cos(dphi - M_PI)));
                    const bool pass_mjj_bb = (!mjj_require_backtoback) || (dphi_to_pi <= tol_rad);
                    if(pass_mjj_bb){
                        cf_default[ir].mjj_pass_bb++;
                        dijet_counts_default[ir].mjj_all++;
                        double mjj = (jets[0] + jets[1]).m();
                        fill_weighted_and_count(rh[ir].mjjAll, mjj, weight);

                    }
                }
            }
        }

        if (passed_any) passEvAny++;
        if (passed_any_nosubfrac) passEvAny_nosubfrac++;
    };

    while (std::getline(fin, line)) {
        if (is_event_header(line, evt_header)) {
            headerHits++;
            if (have_open_event) {
                process_event(parts);
                parts.clear();
            }
            totalEv++;
            have_open_event = true;
        } else if (!line.empty() && line[0] == '#') {
            // Metadata lines (sigmaGen/sigmaErr live here)
            double xs = sigmaGen_stream, xe = sigmaErr_stream;
            if (parse_sigma_line(line, xs, xe)) {
                sigmaGen_stream = xs;
                sigmaErr_stream = xe;
                sigma_seen = true;
                sigma_last_line = line;
            }
        } else if (!line.empty() && line[0] != '#') {
            std::istringstream ss(line);
            int idx, pid, st; double E, px, py, pz;
            ss >> idx >> pid >> st >> E >> px >> py >> pz;
            if (!ss) continue;

            ++n_part_lines;

            // Status accounting (JETSCAPE event record "st")
            // NOTE: In many JETSCAPE ASCII examples, final-state hadrons show status==0.
            // Some writers instead use status==1 for final-state hadrons. Both are "positive".
            if (st == 0) ++n_part_status0;
            else if (st == 1) ++n_part_status1;
            else if (st == -1) ++n_part_status_neg1;
            else ++n_part_status_other;

bool keep_by_status = true;
if (particleStatusFilter == 1) {
    if (statusMode == StatusFilterMode::KEEP_POSITIVE_01) keep_by_status = (st == 0 || st == 1);
    else if (statusMode == StatusFilterMode::KEEP_NONNEG) keep_by_status = (st >= 0);
    else keep_by_status = true; // KEEP_ALL
}
if (!keep_by_status) {
                ++n_part_skipped_by_status;
                continue;
            }

            double pT  = std::hypot(px, py);
            if (!std::isfinite(pT)) { ++n_part_fail_pt_nonfinite; continue; }
            if (pT < clusterMin) { ++n_part_fail_pt; continue; }
            ++n_part_after_pt;

            double eta = 0.0;
            if (!compute_eta_from_pT_pz(pT, pz, eta)) { ++n_part_fail_eta_undef; continue; }
            if (std::fabs(eta) >= particleEtaMax) { ++n_part_fail_eta; continue; }

            ++n_part_after_pt_eta;

            // Constituent mode selection: charged-only (ALICE-style) vs full (previous behavior).
            if (jetConstituentsChargedOnly) {
                if (!is_charged_pid(pid)) {
                    ++n_reject_neutral;
                    continue;
                }
                ++n_keep_charged;
            } else {
                // Full jets: keep all hadrons (previous behavior), but track charged/neutral counts for logging.
                if (is_charged_pid(pid)) ++n_keep_charged;
                else ++n_keep_neutral;
            }

            ++n_keep_total;

            if (particlePtAll)  particlePtAll->Fill(pT, weight_mb_per_event);
            if (particleEtaAll) particleEtaAll->Fill(eta, weight_mb_per_event);
            if (particlePhiAll) particlePhiAll->Fill(std::atan2(py, px), weight_mb_per_event);

            parts.emplace_back(px, py, pz, E);
        }
    }
    if (have_open_event) {
        process_event(parts);
        parts.clear();
    }
    fin.close();

    std::cout << "[INFO] Event headers matched: " << headerHits << "\n";
    std::cout << "[INFO] Constituent selection summary: mode=" << jetConstituentsMode
              << "  parsed=" << n_part_lines
              << "  after_pt=" << n_part_after_pt
              << "  after_pt_eta=" << n_part_after_pt_eta
              << "  fail_pt=" << n_part_fail_pt
              << "  fail_pt_nonfinite=" << n_part_fail_pt_nonfinite
              << "  fail_eta=" << n_part_fail_eta
              << "  fail_eta_undef=" << n_part_fail_eta_undef
              << "  kept_total=" << n_keep_total
              << "  kept_charged=" << n_keep_charged
              << "  kept_neutral=" << n_keep_neutral
              << "  rejected_neutral=" << n_reject_neutral
              << "  unknown_pid=" << n_unknown_pid << "\n";

    std::cout << "[INFO] Particle status summary: PARTICLE_STATUS_FILTER=" << particleStatusFilter
              << "  status0=" << n_part_status0
              << "  status1=" << n_part_status1
              << "  status_neg1=" << n_part_status_neg1
              << "  status_other=" << n_part_status_other
              << "  skipped_by_status=" << n_part_skipped_by_status << "\n";
    if (n_unknown_pid > 0ULL) {
        if (!unknown_pid_examples.empty()) {
            std::cout << "[INFO] Unknown PID examples (first " << unknown_pid_examples.size() << " unique): [";
            for (size_t i = 0; i < unknown_pid_examples.size(); ++i) {
                std::cout << unknown_pid_examples[i];
                if (i + 1 < unknown_pid_examples.size()) std::cout << ", ";
            }
            std::cout << "]\n";
        } else {
            std::cout << "[INFO] Unknown PID encountered (count=" << n_unknown_pid << "), but no examples stored.\n";
        }
    }
    std::cout << "[INFO] Events processed=" << totalEv << "  passed(any R; DEFAULT after SUBFRAC)=" << passEvAny << "\n";
    for(size_t ir=0; ir<rh.size(); ++ir){
        std::cout << "[INFO]   passed(R=" << rh[ir].R << "; DEFAULT after SUBFRAC)=" << passEvR[ir] << "\n";
    }
    std::cout << "[INFO] Events processed=" << totalEv << "  passed(any R; NO-SUBFRAC pre-SUBFRAC)=" << passEvAny_nosubfrac << "\n";
    for(size_t ir=0; ir<rh.size(); ++ir){
        std::cout << "[INFO]   passed(R=" << rh[ir].R << "; NO-SUBFRAC pre-SUBFRAC)=" << passEvR_nosubfrac[ir] << "\n";
    }

    // ---- Detailed cutflow summary (event-level) for both branches ----
    auto print_cutflow = [&](const std::string& label, const std::vector<CutFlow>& cf, bool has_subfrac){
        std::cout << "[INFO] Cutflow summary per R (" << label << "; event-level counts)\n";
        for(size_t ir=0; ir<rh.size(); ++ir){
            if(!rh[ir].enabled) continue;
            const auto& c = cf[ir];
            std::cout << "[INFO]   R=" << rh[ir].R
                      << " events_total=" << c.events_total
                      << " jets_ge2=" << c.jets_ge2
                      << " veto_extra_jets=" << c.veto_extra_jets
                      << " pass_jet_multiplicity=" << c.pass_jet_multiplicity
                      << " pass_lead=" << c.pass_lead
                      << " pass_sublead=" << c.pass_sublead
                      << " pass_leadsub=" << c.pass_leadsub;
            if(has_subfrac) std::cout << " pass_subfrac=" << c.pass_subfrac;
            std::cout << " imbalance_checked=" << c.imbalance_checked
                      << " imbalance_pass_bb=" << c.imbalance_pass_bb
                      << " mjj_checked=" << c.mjj_checked
                      << " mjj_pass_bb=" << c.mjj_pass_bb;
            if(ystar_enable){
                std::cout << " ystar_checked=" << c.ystar_checked
                          << " ystar_pass=" << c.ystar_pass;
            }
            std::cout << "\n";
        }
    };

    print_cutflow("DEFAULT (WITH SUBFRAC)", cf_default, true);
    print_cutflow("NO-SUBFRAC", cf_nosubfrac, false);

    auto print_dijet_observable_counts = [&](const std::string& label, const std::vector<DijetObservableCounts>& counts){
        std::cout << "[INFO] Observable-specific selected dijet counts per R (" << label << ")\n";
        for(size_t ir=0; ir<rh.size(); ++ir){
            if(!rh[ir].enabled) continue;
            const auto& c = counts[ir];
            std::cout << "[INFO]   R=" << rh[ir].R
                      << " dijet_base_sel=" << c.dijet_base_all
                      << " dphi_abs_sel=" << c.dphi_abs_all
                      << " xj_sel=" << c.xj_all
                      << " aj_sel=" << c.aj_all
                      << " mjj_sel=" << c.mjj_all
                      << " dijet_base_ptlead=[";
            for(size_t i=0; i<c.dijet_base_ptlead.size(); ++i){
                std::cout << ptEdges[i] << "-" << ptEdges[i+1] << ":" << c.dijet_base_ptlead[i];
                if(i+1<c.dijet_base_ptlead.size()) std::cout << ", ";
            }
            std::cout << "] dphi_abs_ptlead=[";
            for(size_t i=0; i<c.dphi_abs_ptlead.size(); ++i){
                std::cout << ptEdges[i] << "-" << ptEdges[i+1] << ":" << c.dphi_abs_ptlead[i];
                if(i+1<c.dphi_abs_ptlead.size()) std::cout << ", ";
            }
            std::cout << "] xj_ptlead=[";
            for(size_t i=0; i<c.xj_ptlead.size(); ++i){
                std::cout << ptEdges[i] << "-" << ptEdges[i+1] << ":" << c.xj_ptlead[i];
                if(i+1<c.xj_ptlead.size()) std::cout << ", ";
            }
            std::cout << "] aj_ptlead=[";
            for(size_t i=0; i<c.aj_ptlead.size(); ++i){
                std::cout << ptEdges[i] << "-" << ptEdges[i+1] << ":" << c.aj_ptlead[i];
                if(i+1<c.aj_ptlead.size()) std::cout << ", ";
            }
            std::cout << "]\n";
        }
    };

    print_dijet_observable_counts("DEFAULT (WITH SUBFRAC)", dijet_counts_default);
    print_dijet_observable_counts("NO-SUBFRAC", dijet_counts_nosubfrac);

    // ---- Jet acceptance breakdown (jet-level totals over all events) ----
    std::cout << "[INFO] Jet acceptance breakdown per R (jet-level totals over all events)\n";
    for(size_t ir=0; ir<rh.size(); ++ir){
        if(!rh[ir].enabled) continue;
        const auto& js = jet_stats[ir];
        std::cout << "[INFO]   R=" << rh[ir].R
                  << " jets_raw=" << js.jets_raw
                  << " jets_pass_pt=" << js.jets_pass_pt
                  << " jets_pass_eta=" << js.jets_pass_eta
                  << " jets_pass_pt_eta=" << js.jets_pass_pt_eta
                  << " events_ge1_acc=" << js.events_ge1_acc
                  << " events_ge2_pt=" << js.events_ge2_pt
                  << " events_ge2_eta=" << js.events_ge2_eta
                  << " events_ge2_pt_eta=" << js.events_ge2_pt_eta
                  << "\n";
    }
    if (sigma_seen){
        std::cout << "[INFO] sigmaGen (stream) = " << sigmaGen_stream


                  << " mb   sigmaErr (stream) = " << sigmaErr_stream << " mb\n";
    }

    // ---- Enforce sigma footer contract (needed for downstream xsec normalization uncertainty) ----
    if (!sigma_seen || !std::isfinite(sigmaGen_stream) || !std::isfinite(sigmaErr_stream) || sigmaGen_stream <= 0.0 || sigmaErr_stream <= 0.0) {
        std::cerr << "[ERROR] Missing or invalid sigmaGen/sigmaErr in hadron ASCII comment footer." << "\n";
        std::cerr << "[ERROR]  sigma_seen=" << (sigma_seen ? 1 : 0)
                  << "  sigmaGen=" << sigmaGen_stream << "  sigmaErr=" << sigmaErr_stream << "\n";
        if (!sigma_last_line.empty()) {
            std::cerr << "[ERROR]  Last sigma footer line seen: " << sigma_last_line << "\n";
        } else {
            std::cerr << "[ERROR]  No sigma footer line was detected. Expected something like:\n"
                      << "[ERROR]    #\tsigmaGen\t<value>\tsigmaErr\t<value>\n";
        }
        std::cerr << "[ERROR] Aborting BEFORE writing ROOT/JSON outputs (to avoid xsec_mb=-1 sidecars).\n";
        return 42;
    }


    // ---- Normalize histogram contents to densities (bin-width aware) ----
    if (particlePtAll)  particlePtAll->Scale(1.0, "width");
    if (particleEtaAll) particleEtaAll->Scale(1.0, "width");
    if (particlePhiAll) particlePhiAll->Scale(1.0, "width");


    for(auto& rr : rh){
        if(!rr.enabled) continue;

        // |Delta phi| density: weighted cross section per radian [mb/rad].
        for(auto* h : rr.dphiAbs) if(h) h->Scale(1.0, "width");
        if(rr.dphiAbsAll) rr.dphiAbsAll->Scale(1.0, "width");

        // |Delta phi| vs |Delta eta| density: weighted cross section per radian per eta unit [mb/(rad*eta)].
        for(auto* h : rr.dphiAbsVsDeta) scale_TH2_by_bin_area(h);
        if(rr.dphiAbsVsDetaAll) scale_TH2_by_bin_area(rr.dphiAbsVsDetaAll);

        rr.etaLead->Scale(1.0, "width");
        rr.etaSub->Scale(1.0, "width");
        if(rr.jetPtLead) rr.jetPtLead->Scale(1.0, "width");
        if(rr.jetPtSub) rr.jetPtSub->Scale(1.0, "width");
        if(rr.jetPtIncl) rr.jetPtIncl->Scale(1.0, "width");

        if(rr.xjAll) rr.xjAll->Scale(1.0, "width");
        for(auto* h : rr.xjByPt) if(h) h->Scale(1.0, "width");
        if(rr.ajAll) rr.ajAll->Scale(1.0, "width");
        for(auto* h : rr.ajByPt) if(h) h->Scale(1.0, "width");

        // No-subfrac branch uses the same differential normalization convention.
        for(auto* h : rr.dphiAbs_nosubfrac) if(h) h->Scale(1.0, "width");
        if(rr.dphiAbsAll_nosubfrac) rr.dphiAbsAll_nosubfrac->Scale(1.0, "width");
        for(auto* h : rr.dphiAbsVsDeta_nosubfrac) scale_TH2_by_bin_area(h);
        if(rr.dphiAbsVsDetaAll_nosubfrac) scale_TH2_by_bin_area(rr.dphiAbsVsDetaAll_nosubfrac);

        if(rr.etaLead_nosubfrac) rr.etaLead_nosubfrac->Scale(1.0, "width");
        if(rr.etaSub_nosubfrac) rr.etaSub_nosubfrac->Scale(1.0, "width");
        if(rr.jetPtLead_nosubfrac) rr.jetPtLead_nosubfrac->Scale(1.0, "width");
        if(rr.jetPtSub_nosubfrac) rr.jetPtSub_nosubfrac->Scale(1.0, "width");

        if(rr.xjAll_nosubfrac) rr.xjAll_nosubfrac->Scale(1.0, "width");
        for(auto* h : rr.xjByPt_nosubfrac) if(h) h->Scale(1.0, "width");
        if(rr.ajAll_nosubfrac) rr.ajAll_nosubfrac->Scale(1.0, "width");
        for(auto* h : rr.ajByPt_nosubfrac) if(h) h->Scale(1.0, "width");

        if(rr.mjjAll) rr.mjjAll->Scale(1.0, "width");
        if(rr.mjjAll_nosubfrac) rr.mjjAll_nosubfrac->Scale(1.0, "width");
    }

    for(auto* h : count_hist_default) if(h) h->Scale(1.0, "width");
    for(auto* h : count_hist_nosubfrac) if(h) h->Scale(1.0, "width");

    std::string rootfile = "dphi_" + slice_tag + ".root";
    TFile outf(rootfile.c_str(), "RECREATE");
    if (particlePtAll)  particlePtAll->Write();
    if (particleEtaAll) particleEtaAll->Write();
    if (particlePhiAll) particlePhiAll->Write();
    TDirectory* d_counts = outf.mkdir("counts");
    if(d_counts){
        d_counts->cd();
        for(auto* h : count_hist_default) if(h) h->Write();
        outf.cd();
    }
    for(auto& rr : rh){
        if(!rr.enabled) continue;
        for(auto* h : rr.dphiAbs) h->Write();
        if(rr.dphiAbsAll) rr.dphiAbsAll->Write();
        for(auto* h : rr.dphiAbsVsDeta) if(h) h->Write();
        if(rr.dphiAbsVsDetaAll) rr.dphiAbsVsDetaAll->Write();
        rr.etaLead->Write();
        rr.etaSub ->Write();
        if(rr.jetPtLead) rr.jetPtLead->Write();
        if(rr.jetPtSub)  rr.jetPtSub->Write();
        if(rr.h2SubleadVsLeadAll) rr.h2SubleadVsLeadAll->Write();
        if(rr.profSubleadVsLeadPtLeadBins) rr.profSubleadVsLeadPtLeadBins->Write();
        if(rr.jetPtIncl) rr.jetPtIncl->Write();
        if(rr.xjAll) rr.xjAll->Write();
        for(auto* h : rr.xjByPt) if(h) h->Write();
        if(rr.ajAll) rr.ajAll->Write();
        for(auto* h : rr.ajByPt) if(h) h->Write();
        if(rr.mjjAll){
            rr.mjjAll->Write();
        }
    }
    // Write the NO-SUBFRAC set into a dedicated subdirectory (does not affect existing fitter/comparisor)
    TDirectory* d_nosub = outf.mkdir("nosubfrac");
    if(d_nosub){
        d_nosub->cd();
        TDirectory* d_counts_ns = d_nosub->mkdir("counts");
        if(d_counts_ns){
            d_counts_ns->cd();
            for(auto* h : count_hist_nosubfrac) if(h) h->Write();
            d_nosub->cd();
        }
        for(auto& rr : rh){
            if(!rr.enabled) continue;
            for(auto* h : rr.dphiAbs_nosubfrac) if(h) h->Write();
            if(rr.dphiAbsAll_nosubfrac) rr.dphiAbsAll_nosubfrac->Write();
            for(auto* h : rr.dphiAbsVsDeta_nosubfrac) if(h) h->Write();
            if(rr.dphiAbsVsDetaAll_nosubfrac) rr.dphiAbsVsDetaAll_nosubfrac->Write();
            if(rr.etaLead_nosubfrac) rr.etaLead_nosubfrac->Write();
            if(rr.etaSub_nosubfrac)  rr.etaSub_nosubfrac ->Write();
            if(rr.jetPtLead_nosubfrac) rr.jetPtLead_nosubfrac->Write();
            if(rr.jetPtSub_nosubfrac)  rr.jetPtSub_nosubfrac ->Write();
            if(rr.h2SubleadVsLeadAll_nosubfrac) rr.h2SubleadVsLeadAll_nosubfrac->Write();
            if(rr.profSubleadVsLeadPtLeadBins_nosubfrac) rr.profSubleadVsLeadPtLeadBins_nosubfrac->Write();
            if(rr.xjAll_nosubfrac) rr.xjAll_nosubfrac->Write();
            for(auto* h : rr.xjByPt_nosubfrac) if(h) h->Write();
            if(rr.ajAll_nosubfrac) rr.ajAll_nosubfrac->Write();
            for(auto* h : rr.ajByPt_nosubfrac) if(h) h->Write();
            if(rr.mjjAll_nosubfrac){
                rr.mjjAll_nosubfrac->Write();
            }
        }
        outf.cd();
    }

    outf.Close();
    std::cout << "[INFO] Wrote ROOT file: " << rootfile << "\n";
    std::cout << "[INFO] (should include particle_*, jetpt_*, dphi_abs_*, counts/count_*, h2_dphi_abs_vs_deta_*, h2_sublead_vs_lead_*, prof_sublead_vs_lead_* histos) Example: particle_pt_all, jetpt_incl_R020_all, dphi_abs_R020_<ptlo>_<pthi>, jetpt_lead_R020_<ptlo>_<pthi>_fullrange, h2_dphi_abs_vs_deta_R020_<ptlo>_<pthi>_fullrange, prof_sublead_vs_lead_R020_<ptlo>_<pthi>_fullrange_ptleadbins\n";

// ---- ROOT output integrity checks (fast; runs inside the task job) ----
std::vector<std::string> expected_keys;
expected_keys.reserve(620);
bool expect_nosubfrac_dir = false;
expected_keys.push_back("particle_pt_all");
expected_keys.push_back("particle_eta_all");
expected_keys.push_back("particle_phi_all");
for(auto* h : count_hist_default){
    if(h) expected_keys.push_back(std::string("counts/") + h->GetName());
}
for(auto* h : count_hist_nosubfrac){
    if(h) expected_keys.push_back(std::string("nosubfrac/counts/") + h->GetName());
}
for(const auto& rr : rh){
    if(!rr.enabled) continue;
    expect_nosubfrac_dir = true;

    expected_keys.push_back(Form("dphi_abs_R%03d_%d_%d_fullrange", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag));
    expected_keys.push_back(Form("h2_dphi_abs_vs_deta_R%03d_%d_%d_fullrange", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag));
    expected_keys.push_back(Form("eta_lead_R%03d_%d_%d_fullrange", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag));
    expected_keys.push_back(Form("eta_sub_R%03d_%d_%d_fullrange", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag));
    expected_keys.push_back(Form("jetpt_incl_R%03d_all", rr.Rtag));
    expected_keys.push_back(Form("jetpt_lead_R%03d_%d_%d_fullrange", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag));
    expected_keys.push_back(Form("jetpt_sublead_R%03d_%d_%d_fullrange", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag));
    expected_keys.push_back(Form("h2_sublead_vs_lead_R%03d_%d_%d_fullrange", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag));
    expected_keys.push_back(Form("prof_sublead_vs_lead_R%03d_%d_%d_fullrange_ptleadbins", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag));
    expected_keys.push_back(Form("xj_R%03d_%d_%d_fullrange", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag));
    expected_keys.push_back(Form("aj_R%03d_%d_%d_fullrange", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag));
    if(mjj_enable){
        expected_keys.push_back(Form("mjj_R%03d_%d_%d_fullrange", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag));
    }

    for(size_t i = 0; i + 1 < ptEdges.size(); ++i){
        const int lo = (int)ptEdges[i];
        const int hi = (int)ptEdges[i+1];
        expected_keys.push_back(Form("dphi_abs_R%03d_%d_%d", rr.Rtag, lo, hi));
        expected_keys.push_back(Form("h2_dphi_abs_vs_deta_R%03d_%d_%d", rr.Rtag, lo, hi));
        expected_keys.push_back(Form("xj_R%03d_%d_%d", rr.Rtag, lo, hi));
        expected_keys.push_back(Form("aj_R%03d_%d_%d", rr.Rtag, lo, hi));

        expected_keys.push_back(Form("nosubfrac/dphi_abs_R%03d_%d_%d_nosubfrac", rr.Rtag, lo, hi));
        expected_keys.push_back(Form("nosubfrac/h2_dphi_abs_vs_deta_R%03d_%d_%d_nosubfrac", rr.Rtag, lo, hi));
        expected_keys.push_back(Form("nosubfrac/xj_R%03d_%d_%d_nosubfrac", rr.Rtag, lo, hi));
        expected_keys.push_back(Form("nosubfrac/aj_R%03d_%d_%d_nosubfrac", rr.Rtag, lo, hi));
    }

    expected_keys.push_back(Form("nosubfrac/dphi_abs_R%03d_%d_%d_fullrange_nosubfrac", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag));
    expected_keys.push_back(Form("nosubfrac/h2_dphi_abs_vs_deta_R%03d_%d_%d_fullrange_nosubfrac", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag));
    expected_keys.push_back(Form("nosubfrac/eta_lead_R%03d_%d_%d_fullrange_nosubfrac", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag));
    expected_keys.push_back(Form("nosubfrac/eta_sub_R%03d_%d_%d_fullrange_nosubfrac", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag));
    expected_keys.push_back(Form("nosubfrac/jetpt_lead_R%03d_%d_%d_fullrange_nosubfrac", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag));
    expected_keys.push_back(Form("nosubfrac/jetpt_sublead_R%03d_%d_%d_fullrange_nosubfrac", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag));
    expected_keys.push_back(Form("nosubfrac/h2_sublead_vs_lead_R%03d_%d_%d_fullrange_nosubfrac", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag));
    expected_keys.push_back(Form("nosubfrac/prof_sublead_vs_lead_R%03d_%d_%d_fullrange_ptleadbins_nosubfrac", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag));
    expected_keys.push_back(Form("nosubfrac/xj_R%03d_%d_%d_fullrange_nosubfrac", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag));
    expected_keys.push_back(Form("nosubfrac/aj_R%03d_%d_%d_fullrange_nosubfrac", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag));
    if(mjj_enable){
        expected_keys.push_back(Form("nosubfrac/mjj_R%03d_%d_%d_fullrange_nosubfrac", rr.Rtag, ptLeadAllLoTag, ptLeadAllHiTag));
    }
}
if(expect_nosubfrac_dir){
    expected_keys.push_back("nosubfrac");
}

RootValidation root_val = validate_root_output(rootfile, expected_keys);
if(!root_val.ok){
    std::cerr << "[ERROR] ROOT validation FAILED for " << rootfile
              << " note=" << root_val.note
              << " is_zombie=" << root_val.is_zombie
              << " is_recovered=" << root_val.is_recovered
              << " reopen_ok=" << root_val.reopen_ok
              << " nkeys=" << root_val.nkeys
              << " bytes=" << root_val.filesize_bytes
              << " missing_keys=" << root_val.missing_keys.size()
              << "\n";
    size_t lim = std::min<size_t>(10, root_val.missing_keys.size());
    for(size_t i=0;i<lim;i++){
        std::cerr << "  [ERROR] missing_key[" << i << "]=" << root_val.missing_keys[i] << "\n";
    }
    if(root_val.missing_keys.size() > lim){
        std::cerr << "  [ERROR] (missing_key list truncated; total=" << root_val.missing_keys.size() << ")\n";
    }
} else {
    std::cout << "[INFO] ROOT validation OK for " << rootfile
              << " nkeys=" << root_val.nkeys
              << " bytes=" << root_val.filesize_bytes
              << "\n";
}

    // ---- ROOT histogram inventory (compact, recursive) ----
    {
        TFile finv(rootfile.c_str(), "READ");
        if (finv.IsZombie()){
            std::cerr << "[ERROR] ROOT inventory: cannot open " << rootfile << " (zombie)\n";
        } else {
            std::map<std::string, long long> fam;
            std::vector<std::string> all_keys;
            std::vector<std::string> first_keys;
            all_keys.reserve(320);
            first_keys.reserve(32);

            collect_root_keys_recursive(&finv, "", all_keys);
            const long long n = static_cast<long long>(all_keys.size());
            for (const auto& key_path : all_keys){
                if (first_keys.size() < 25) first_keys.push_back(key_path);

                const bool ns = (key_path.rfind("nosubfrac/", 0) == 0) ||
                                (key_path.find("_nosubfrac") != std::string::npos);
                const size_t slash = key_path.find_last_of('/');
                const std::string name = (slash == std::string::npos) ? key_path : key_path.substr(slash + 1);

                auto bump = [&](const std::string& base){
                    fam[base + (ns ? "_nosubfrac" : "")] += 1;
                };

                if (name.rfind("count_", 0) == 0) bump("countDensity");
                else if (name.rfind("jetpt_", 0) == 0) bump("jetpt");
                else if (name.rfind("h2_sublead_vs_lead_", 0) == 0) bump("subleadVsLead2D");
                else if (name.rfind("h2_dphi_abs_vs_deta_", 0) == 0) bump("dphiAbsVsDeta2D");
                else if (name.rfind("prof_sublead_vs_lead_", 0) == 0) bump("subleadVsLeadProf");
                else if (name.rfind("dphi_abs_", 0) == 0) bump("dphiAbs");
                else if (name.rfind("xj_", 0) == 0) bump("xj");
                else if (name.rfind("aj_", 0) == 0) bump("aj");
                else if (name.rfind("eta_", 0) == 0) bump("eta");
                else if (name.rfind("mjj_", 0) == 0) bump("mjj");
                else fam[std::string("other") + (ns ? "_nosubfrac" : "")] += 1;
            }

            std::cout << "[INFO] ROOT key inventory (recursive): total=" << n << "\n";
            for (const auto& kv : fam){
                std::cout << "[INFO]   keys_" << kv.first << "=" << kv.second << "\n";
            }
            std::cout << "[INFO] First keys (up to 25, full paths):\n";
            for (const auto& s : first_keys){
                std::cout << "[INFO]   " << s << "\n";
            }
        }
        finv.Close();
    }

    {
        double pthat_low=-1, pthat_high=-1; int task_id=-1;

        // Expected slice_tag forms:
        //   (current)  <RUN_TAG>_<L>_<H>_<T>   e.g. vaccum_twomil_30_45_1
        //   (legacy)   <L>_<H>_<T>            e.g. 30_45_1
        //   (legacy)   <L>-<H>_<T>            e.g. 30-45_1
        auto split_underscore = [](const std::string& s){
            std::vector<std::string> out;
            size_t pos = 0;
            while(true){
                size_t p = s.find('_', pos);
                if (p == std::string::npos) { out.push_back(s.substr(pos)); break; }
                out.push_back(s.substr(pos, p-pos));
                pos = p+1;
            }
            return out;
        };
        auto toks = split_underscore(slice_tag);

        auto is_number = [](const std::string& s)->bool{
            if(s.empty()) return false;
            for(char c: s) if(!std::isdigit((unsigned char)c) && c!='.' && c!='-') return false;
            return true;
        };

        if(toks.size() >= 4){
            // try last 3 tokens as L,H,T
            std::string tL = toks[toks.size()-3];
            std::string tH = toks[toks.size()-2];
            std::string tT = toks[toks.size()-1];
            if(is_number(tL) && is_number(tH) && is_number(tT)){
                pthat_low = std::stod(tL);
                pthat_high = std::stod(tH);
                task_id = std::stoi(tT);
            }
        }
        if(task_id < 0){
            // fallback: handle L-H_T legacy
            auto dash = slice_tag.find('-');
            auto us = slice_tag.rfind('_');
            if(dash != std::string::npos && us != std::string::npos && us > dash){
                std::string a = slice_tag.substr(0, dash);
                std::string b = slice_tag.substr(dash+1, us-(dash+1));
                std::string c = slice_tag.substr(us+1);
                if(is_number(a) && is_number(b) && is_number(c)){
                    pthat_low = std::stod(a);
                    pthat_high = std::stod(b);
                    task_id = std::stoi(c);
                }
            }
        }

        std::string jsonfile = "slice_meta_" + slice_tag + ".json";
        std::ofstream fj(jsonfile);
        fj << "{\n";
        fj << "  \"slice_tag\": \"" << slice_tag << "\",\n";
        fj << "  \"analyzer_version\": \"" << ANALYZE_DPHI_SLICED_VERSION << "\",\n";
fj << "  \"rootfile\": \"" << rootfile << "\",\n";
fj << "  \"root_status\": \"" << (root_val.ok ? "ok" : "bad") << "\",\n";
fj << "  \"root_validation\": {\n";
fj << "    \"ok\": " << (root_val.ok ? "true" : "false") << ",\n";
fj << "    \"note\": \"" << root_val.note << "\",\n";
fj << "    \"is_zombie\": " << (root_val.is_zombie ? "true" : "false") << ",\n";
fj << "    \"is_recovered\": " << (root_val.is_recovered ? "true" : "false") << ",\n";
fj << "    \"reopen_ok\": " << (root_val.reopen_ok ? "true" : "false") << ",\n";
fj << "    \"filesize_bytes\": " << root_val.filesize_bytes << ",\n";
fj << "    \"nkeys\": " << root_val.nkeys << ",\n";
fj << "    \"missing_keys\": [";
for(size_t i=0;i<root_val.missing_keys.size();++i){
    fj << "\"" << root_val.missing_keys[i] << "\"";
    if(i+1<root_val.missing_keys.size()) fj << ", ";
    if(i==49 && root_val.missing_keys.size()>50){ fj << ", \"...\""; break; }
}
fj << "]\n";
fj << "  },\n";

        fj << "  \"events_seen\": " << totalEv << ",\n";
        auto write_ll_array = [&](const std::vector<long long>& vals){
            fj << "[";
            for(size_t i=0; i<vals.size(); ++i){
                fj << vals[i];
                if(i+1<vals.size()) fj << ", ";
            }
            fj << "]";
        };
        auto write_counts_per_r = [&](const std::vector<DijetObservableCounts>& counts, long long DijetObservableCounts::*member){
            fj << "[";
            for(size_t ir=0; ir<counts.size(); ++ir){
                fj << counts[ir].*member;
                if(ir+1<counts.size()) fj << ", ";
            }
            fj << "]";
        };
        auto write_counts_per_r_per_pt = [&](const std::vector<DijetObservableCounts>& counts, const std::string& which){
            fj << "[";
            for(size_t ir=0; ir<counts.size(); ++ir){
                const std::vector<long long>* vals = nullptr;
                if(which == "dijet_base") vals = &counts[ir].dijet_base_ptlead;
                else if(which == "dphi_abs") vals = &counts[ir].dphi_abs_ptlead;
                else if(which == "xj") vals = &counts[ir].xj_ptlead;
                else if(which == "aj") vals = &counts[ir].aj_ptlead;
                else vals = &counts[ir].dijet_base_ptlead;
                write_ll_array(*vals);
                if(ir+1<counts.size()) fj << ", ";
            }
            fj << "]";
        };

        fj << "  \"events_passing\": " << passEvAny << ",\n";
        fj << "  \"events_passing_per_R\": [";
        for(size_t ir=0; ir<passEvR.size(); ++ir){
            fj << passEvR[ir];
            if(ir+1<passEvR.size()) fj << ", ";
        }
        fj << "],\n";
        fj << "  \"events_passing_nosubfrac\": " << passEvAny_nosubfrac << ",\n";
        fj << "  \"events_passing_per_R_nosubfrac\": [";
        for(size_t ir=0; ir<passEvR_nosubfrac.size(); ++ir){
            fj << passEvR_nosubfrac[ir];
            if(ir+1<passEvR_nosubfrac.size()) fj << ", ";
        }
        fj << "],\n";
        fj << "  \"selected_dijet_counts\": {\n";
        fj << "    \"count_semantics\": \"event_level_selected_dijet_pair_counts\",\n";
        fj << "    \"default\": {\n";
        fj << "      \"dijet_base_all_per_R\": "; write_counts_per_r(dijet_counts_default, &DijetObservableCounts::dijet_base_all); fj << ",\n";
        fj << "      \"dphi_abs_all_per_R\": "; write_counts_per_r(dijet_counts_default, &DijetObservableCounts::dphi_abs_all); fj << ",\n";
        fj << "      \"xj_all_per_R\": "; write_counts_per_r(dijet_counts_default, &DijetObservableCounts::xj_all); fj << ",\n";
        fj << "      \"aj_all_per_R\": "; write_counts_per_r(dijet_counts_default, &DijetObservableCounts::aj_all); fj << ",\n";
        fj << "      \"mjj_all_per_R\": "; write_counts_per_r(dijet_counts_default, &DijetObservableCounts::mjj_all); fj << ",\n";
        fj << "      \"dijet_base_ptlead_per_R\": "; write_counts_per_r_per_pt(dijet_counts_default, "dijet_base"); fj << ",\n";
        fj << "      \"dphi_abs_ptlead_per_R\": "; write_counts_per_r_per_pt(dijet_counts_default, "dphi_abs"); fj << ",\n";
        fj << "      \"xj_ptlead_per_R\": "; write_counts_per_r_per_pt(dijet_counts_default, "xj"); fj << ",\n";
        fj << "      \"aj_ptlead_per_R\": "; write_counts_per_r_per_pt(dijet_counts_default, "aj"); fj << "\n";
        fj << "    },\n";
        fj << "    \"nosubfrac\": {\n";
        fj << "      \"dijet_base_all_per_R\": "; write_counts_per_r(dijet_counts_nosubfrac, &DijetObservableCounts::dijet_base_all); fj << ",\n";
        fj << "      \"dphi_abs_all_per_R\": "; write_counts_per_r(dijet_counts_nosubfrac, &DijetObservableCounts::dphi_abs_all); fj << ",\n";
        fj << "      \"xj_all_per_R\": "; write_counts_per_r(dijet_counts_nosubfrac, &DijetObservableCounts::xj_all); fj << ",\n";
        fj << "      \"aj_all_per_R\": "; write_counts_per_r(dijet_counts_nosubfrac, &DijetObservableCounts::aj_all); fj << ",\n";
        fj << "      \"mjj_all_per_R\": "; write_counts_per_r(dijet_counts_nosubfrac, &DijetObservableCounts::mjj_all); fj << ",\n";
        fj << "      \"dijet_base_ptlead_per_R\": "; write_counts_per_r_per_pt(dijet_counts_nosubfrac, "dijet_base"); fj << ",\n";
        fj << "      \"dphi_abs_ptlead_per_R\": "; write_counts_per_r_per_pt(dijet_counts_nosubfrac, "dphi_abs"); fj << ",\n";
        fj << "      \"xj_ptlead_per_R\": "; write_counts_per_r_per_pt(dijet_counts_nosubfrac, "xj"); fj << ",\n";
        fj << "      \"aj_ptlead_per_R\": "; write_counts_per_r_per_pt(dijet_counts_nosubfrac, "aj"); fj << "\n";
        fj << "    }\n";
        fj << "  },\n";

        fj << "  \"pthat_low\": " << pthat_low << ",\n";
        fj << "  \"pthat_high\": " << pthat_high << ",\n";
        fj << "  \"task_id\": " << task_id << ",\n";

        fj << "  \"weight_mb_per_event\": " << weight_mb_per_event << ",\n";
        fj << "  \"sigmaGen_mb\": " << (sigma_seen ? sigmaGen_stream : -1.0) << ",\n";
        fj << "  \"sigmaErr_mb\": " << (sigma_seen ? sigmaErr_stream : -1.0) << ",\n";

        fj << "  \"constituents\": {\n";
        fj << "    \"mode\": \"" << jetConstituentsMode << "\",\n";
        fj << "    \"particle_status_filter\": " << particleStatusFilter << ",\n";
        fj << "    \"status0\": " << n_part_status0 << ",\n";
        fj << "    \"status1\": " << n_part_status1 << ",\n";
        fj << "    \"status_neg1\": " << n_part_status_neg1 << ",\n";
        fj << "    \"status_other\": " << n_part_status_other << ",\n";
        fj << "    \"skipped_by_status\": " << n_part_skipped_by_status << ",\n";
        fj << "    \"particles_parsed\": " << n_part_lines << ",\n";
        fj << "    \"particles_after_pt_eta\": " << n_part_after_pt_eta << ",\n";
        fj << "    \"kept_total\": " << n_keep_total << ",\n";
        fj << "    \"kept_charged\": " << n_keep_charged << ",\n";
        fj << "    \"kept_neutral\": " << n_keep_neutral << ",\n";
        fj << "    \"rejected_neutral\": " << n_reject_neutral << ",\n";
        fj << "    \"unknown_pid\": " << n_unknown_pid << "\n";
        fj << "  },\n";

        fj << "  \"config\": {\n";
        fj << "    \"JET_CONSTITUENTS_MODE\": \"" << jetConstituentsMode << "\",\n";
        fj << "    \"PARTICLE_STATUS_FILTER\": " << particleStatusFilter << ",\n";
        fj << "    \"particle_status_mode\": \"" << statusModeLabel << "\",\n";
        fj << "    \"PARTICLE_ETA_MAX\": " << particleEtaMax << ",\n";
        fj << "    \"CLUSTER_MIN\": " << clusterMin << ",\n";
        fj << "    \"JET_PT_MIN\": " << jetPtMin << ",\n";
        fj << "    \"JET_PT_MAX\": " << jetPtMax << ",\n";
        fj << "    \"LEAD_PT_MIN\": " << leadPtMin << ",\n";
        fj << "    \"SUBLEAD_PT_MIN\": " << subPtMin << ",\n";
        fj << "    \"SUBFRAC\": " << subFracMin << ",\n";
        fj << "    \"DIJET_REQUIRE_EXACTLY_TWO_JETS\": " << dijetRequireExactlyTwoJets << ",\n";
        fj << "    \"JET_ETA_MAX\": " << jetEtaMaxRaw << ",\n";
        fj << "    \"JET_ETA_MODE\": " << jetEtaMode << ",\n";
        fj << "    \"DPHI_NBINS\": " << dphi_nbins << ",\n";
        fj << "    \"MJJ_ENABLE\": " << mjj_enable << ",\n";
        fj << "    \"MJJ_REQUIRE_BACKTOBACK\": " << mjj_require_backtoback << ",\n";
        fj << "    \"MJJ_NBINS\": " << mjj_nbins << ",\n";
        fj << "    \"MJJ_MIN_GEV\": " << mjj_min << ",\n";
        fj << "    \"MJJ_MAX_GEV\": " << mjj_max << ",\n";
        fj << "    \"MJJ_LOG_BINS\": " << mjj_log_bins << ",\n";
        fj << "    \"DIJET_BACKTOBACK_TOL_DEG\": " << tol_deg << ",\n";
        fj << "    \"IMBALANCE_REQUIRE_BACKTOBACK\": " << imbalanceBacktoback << ",\n";
        fj << "    \"IMBALANCE_BACKTOBACK_TOL_DEG\": " << imbalanceTolDeg << ",\n";
        fj << "    \"ETA_NBINS\": " << eta_nbins << ",\n";
        fj << "    \"XJ_NBINS\": " << xj_nbins << ",\n";
        fj << "    \"AJ_NBINS\": " << aj_nbins << ",\n";
        fj << "    \"JETPT_BINS_MODE\": \"" << jetpt_bins_mode << "\",\n";
        fj << "    \"JETPT_NBINS\": " << jetpt_nbins << ",\n";

        fj << "    \"PT_LEAD_BIN_EDGES\": [";
        for(size_t i=0;i<ptEdges.size();++i){
            fj << ptEdges[i]; if(i+1<ptEdges.size()) fj << ", ";
        }
        fj << "],\n";

        fj << "    \"JETPT_BIN_EDGES\": [";
        for(size_t i=0;i<jetpt_edges.size();++i){
            fj << jetpt_edges[i]; if(i+1<jetpt_edges.size()) fj << ", ";
        }
        fj << "],\n";

        fj << "    \"JET_RADIUS_LIST\": [";
        for(size_t i=0;i<Rlist.size();++i){
            fj << Rlist[i]; if(i+1<Rlist.size()) fj << ", ";
        }
        fj << "]\n";

        fj << "  }\n";
        fj << "}\n";
        fj.close();
        std::cout << "[INFO] Wrote JSON meta file: " << jsonfile << "\n";
    }

    if(!root_val.ok){
        std::cerr << "[ERROR] Exiting nonzero due to ROOT validation failure (task will be resubmitted).\n";
        return 6;
    }

    return 0;
}
