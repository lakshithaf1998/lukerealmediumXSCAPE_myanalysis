#!/usr/bin/env python3
# dphi_fit_py.py v4.9.75
# CHANGELOG:
#   - 4.9.75 (2026-03-18): FIX: restore fitter jet-R uncertainty annotation helper and auto-zoom jet-spectra x-ranges to populated bins.
#     • FIX: Define the missing _annotate_approx_uncertainty(fig) helper used by the fitter jet-R ratio block so that imbalance/jetR plotting no longer aborts with a NameError.
#     • FIX: Auto-zoom all fitter jet-spectra displays to the populated p_T support instead of stretching to the histogram booking ceiling, covering absolute lead/sublead/inclusive spectra plus the corresponding dijet-normalized and inclusive-unit-normalized outputs.
#     • LOG: Emit per-plot jet-spectra x-range diagnostics in fit_py.log so the rendered zoom window is explicit and reproducible.
#   - 4.9.73 (2026-03-17): FIX: Sync runtime fitter version with the file header and correct stale PT_LEAD_BIN_EDGES fallback docs.
#     • FIX: Update __version__ to 4.9.73 so fit_py.log and provenance banners report the actual file version being run.
#     • DOCS: Remove the stale comment claiming PT_LEAD_BIN_EDGES parsing falls back to "all"; current behavior is a hard fail on missing/invalid edges.
#   - 4.9.72 (2026-03-17): FIX: Extend fitter single-slice validation/labeling to dijet-selected jet-pT spectra and submission preflight.
#     • FIX: Treat single-slice dijet-selected lead/subleading jet-p_T normalized spectra as (1/N_dijet,sel) dN/dp_T, using the published base selected-dijet counts (dphi_all_per_R) for legends/notes/labels instead of stale σ_sel wording.
#     • FIX: Align the fitter-side selected-dijet resolver helpers with the comparisor by supporting the generic selected-dijet denominator alias used by dijet-selected jet-p_T overlays.
#     • DIAG: Wrapper/SLURM preflight now validates the published selected_dijet_counts_summary.json contract before consuming queue time when SINGLE_SLICE_MODE=1.
#   - 4.9.71 (2026-03-17): FIX: Mirror comparisor robustness fixes in fitter jet-R ratios and single-slice count validation.
#     • FIX: Validate SINGLE_SLICE_MODE selected-dijet count semantics against the analyzer/merge contract (event_level_selected_dijet_pair_counts) before relabeling normalized plots.
#     • FIX: Jet-R ratio plots now keep finite central-value points even when propagated ratio uncertainties are unavailable, instead of silently dropping those bins from the plot.
#     • CLEANUP: Remove the stale unused xsec_rel_err argument from read_root_histograms() and sync the runtime __version__ with the header version.
#   - 4.9.70 (2026-03-17): FIX: Generalize fitter jet-R ratio plots from JET_RADIUS_LIST, mark their uncertainties as approximate, and remove folded-|Δφ| boundary guides.
#     • FIX: Build fitter jet-R ratio plots using the configured JET_RADIUS_LIST order as first-radius/other-radius pairs (e.g. 0.2/0.4, 0.2/0.5, 0.2/0.6) instead of the old hard-coded R=0.2 over R=0.4 assumption.
#     • FIX: Add an on-plot disclaimer that the jet-R ratio uncertainties are approximate because shared-event cross-R correlations are not available downstream.
#     • FIX: Remove the redundant π guide line from folded dphi_abs_* absolute and normalized fit panels while keeping the unfolded Δφ guide and fit-window shading unchanged.
#   - 4.9.69 (2026-03-16): FIX: Make fitter Mjj title/label honesty obey explicit MJJ_REQUIRE_BACKTOBACK.
#     • FIX: Read required MJJ_REQUIRE_BACKTOBACK from jetscape.ini, hard-fail on missing/invalid values, and include the Mjj back-to-back text in Mjj titles only when that extra gate is enabled.
#     • LOG: Startup config banner now records the resolved MJJ_REQUIRE_BACKTOBACK state alongside DIJET_BACKTOBACK_TOL_DEG.
#   - 4.9.67 (2026-03-16): ADD: Single-slice-aware 1/N_dijet labeling and legend counts for normalized dijet plots.
#     • NEW: Read optional SINGLE_SLICE_MODE from jetscape.ini. When enabled, fitter requires a merged single-slice selected_dijet_counts summary and relabels only the normalized dijet plots (Δφ/|Δφ|, x_J, A_J, M_{jj}) from (1/σ_sel)dσ/dX to the correct observable-specific 1/N_dijet·dN/dX notation.
#     • NEW: Load merged selected dijet counts from ${DIR_FINAL}/selected_dijet_counts_summary.json (or the path pointed to by xsec_summary.json when available), validate single-slice consistency, and show the corresponding N_dijet count in normalized-plot legends without changing any histogram math.
#     • SAFETY: When SINGLE_SLICE_MODE=0 the fitter behavior is unchanged; absolute folders/labels remain untouched.
#   - 4.9.68 (2026-03-16): FIX: Align fitter histogram parsing/plotting with analyzer v9.7.0 leading-jet pT bin policy and explicit full-range histogram names.
#     • FIX: Accept analyzer full-range dijet histogram names using explicit <ptmin>_<ptmax>_fullrange tags for Δφ/|Δφ|, xJ, AJ, Mjj, η_lead/sub, jetpt_lead/sublead, h2_sublead_vs_lead, and prof_sublead_vs_lead while preserving legacy _all compatibility where applicable.
#     • FIX: Add leading-jet-pT-binned xJ/AJ plotting and selected-dijet legend counts, remove fitter support for deprecated pT-binned Mjj histograms, and keep Mjj full-range only.
#     • FIX: Use histogram-native names for xJ/AJ output files and replace vague “all pT” text with the explicit configured PT_LEAD_BIN_EDGES range in relevant titles/labels.
#   - 4.9.66 (2026-03-16): FIX: Clarify fitter normalized plot taxonomy and remove the literal PT_LEAD_BIN_EDGES token from lead-vs-subleading profile titles.
#     • FIX: Rename the branch-neutral inclusive unit-shape plot root from plots/unit_normalized/jet_spectra/ to plots/inclusive_unit_normalized/jet_spectra/ so it cannot be confused with true per-dijet normalized outputs under plots/dijet_normalized/.
#     • FIX: Keep only the analyzer's inclusive jet unit-shape spectra in that branch-neutral inclusive_unit_normalized tree; true dijet-selected normalized observables remain under plots/dijet_normalized/{subfrac,nosubfrac}/.
#     • FIX: Lead-vs-subleading TProfile plot titles now state that they span all configured leading-jet p_T bins and show the numeric range/bin count instead of the raw config token PT_LEAD_BIN_EDGES.
#   - 4.9.65 (2026-03-15): FIX: Make fitter exact xsec-band histogram lookup use the same normalized recursive ROOT reader as the main fitter path.
#     • FIX: SliceNormBandBuilder now indexes per-slice TH1 histograms via _iter_root_objects(), so nosubfrac/ leaf names are normalized exactly like the final merged ROOT reader before xsec-band lookup.
#     • DIAG: Log how many TH1 histograms each per-slice ROOT contributed to the exact xsec-band helper, making any future per-slice inventory mismatch visible in pyfit logs.
#   - 4.9.64 (2026-03-15): FIX: Correct fitter-side absolute folded |Δφ| y-axis labeling for dphi_abs_* panels.
#     • FIX: Absolute folded Δφ panels now label the plotted differential as dσ_dijet/d|Δφ| instead of dσ_dijet/dΔφ, matching the analyzer-defined folded observable without changing any histogram content, fit window, or normalization.
#   - 4.9.63 (2026-03-15): FIX: Make fitter-side normalized Δφ notation honest and internally consistent.
#     • FIX: Folded abs-Δφ normalized panels now label the observable as dσ/d|Δφ| instead of dσ/dΔφ, so the plotted differential matches the analyzer-defined folded quantity.
#     • FIX: Replace dijet-specific σ_dijet notation in normalized Δφ y-axis/title text with the fitter-standard per-selection σ_sel notation, matching the rest of the fitter outputs without changing any normalization or fit numerics.
#   - 4.9.62 (2026-03-15): FIX: Remove misleading weighted-histogram entry counts from the combined all-R Mjj fitter summary stats box.
#     • FIX: Combined Mjj summary annotations now report only mean and standard deviation per R, matching the earlier individual-Mjj cleanup and avoiding dishonest raw-entry text for weighted pThat-sliced histograms.
#   - 4.9.61 (2026-03-15): FIX: Make fitter xJ/AJ titles honest about optional analyzer imbalance back-to-back cuts and remove misleading weighted-histogram entry counts from Mjj stats boxes.
#     • FIX: Read required IMBALANCE_REQUIRE_BACKTOBACK and IMBALANCE_BACKTOBACK_TOL_DEG from jetscape.ini, hard-fail on invalid values, and log the resolved imbalance-selection mode at startup.
#     • FIX: xJ/AJ plot titles now append the active analyzer imbalance back-to-back requirement only when enabled, keeping fitter labeling aligned with analyze_dphi_sliced.cpp without renaming histograms or changing normalization.
#     • FIX: Remove ROOT fEntries-based “Entries” text from Mjj stats boxes; weighted pThat-sliced histograms now report only mean and standard deviation, which are materially interpretable downstream.
#   - 4.9.60 (2026-03-14): FIX: Improve fitter-side Δφ physics honesty and normalized-shape fit statistics without any upstream covariance products.
#     • FIX: Normalized Δφ shape fits now use a full bin-to-bin covariance matrix built from the existing histogram errors under the independent raw-bin approximation when COVARIANCE_MODE=diagonal. This replaces the previous diagonal-only χ² treatment for the normalized-shape fit panel.
#     • FIX: If COVARIANCE_MODE=conservative, normalized Δφ shape fits now fall back honestly to diagonal-only fitting and log that the conservative mode does not provide a usable off-diagonal covariance matrix.
#     • FIX: Δφ plot titles/y-axis labels now identify the observable as dijet azimuthal decorrelation, avoiding accidental confusion with semi-inclusive trigger-recoil observables such as Δ_recoil.
#     • DIAG: Normalized-shape panels now annotate whether the fit used full normalized covariance or a diagonal fallback, and fit logs record any covariance regularization applied for numerical stability.
#   - 4.9.59 (2026-03-14): FIX: Stop naming inclusive unit-shape jet spectra as if they were dijet-normalized outputs.
#     • FIX: Inclusive jet p_T unit-shape plots now write to plots/unit_normalized/jet_spectra/ instead of the misleading plots/dijet_normalized/jet_spectra/ neutral tree.
#     • FIX: Inclusive jet p_T unit-shape filenames now end with _unitshape.png instead of _perdijet.png, matching the actual (1/σ_incl)dσ/dp_T quantity.
#     • DOCS: Update fitter layout/logging comments so branch-neutral inclusive unit-shape outputs are clearly separated from true per-selection dijet-normalized observables.
#   - 4.9.58 (2026-03-12): FIX: Make fitter titles/logging honest for the exact-two-jets dijet selection.
#     • FIX: Read required DIJET_REQUIRE_EXACTLY_TWO_JETS from jetscape.ini, hard-fail on invalid values, and log the resolved mode at startup.
#     • FIX: Add the active exact-two-jets selection text to dijet-pair plot titles only: Δφ/|Δφ|, Mjj, η_lead/sub, jetpt_lead/sublead, h2/prof lead-vs-sublead, xJ, AJ, and lead-only jet-R ratios.
#     • FIX: Leave inclusive jet spectra and particle-level QA titles free of exact-two wording, matching analyzer scope.
#   - 4.9.57 (2026-03-11): FIX: Make fitter titles/labels honest for analyzer v9.6.6 y* routing and particle-level QA semantics.
#     • FIX: When YSTAR_ENABLE=1, add the active |y*|<YSTAR_MAX selection text to relevant dijet-pair plot titles only: jetpt_lead_*, jetpt_sublead_*, h2_sublead_vs_lead_*, prof_sublead_vs_lead_*, xj_*, aj_*, eta_lead_*, and eta_sub_*.
#     • FIX: Leave inclusive jet spectra and branch-neutral particle-level QA free of y* text, matching analyzer scope.
#     • FIX: Update particle-level QA titles to say they are pre-clustering inclusive weighted constituent yields, avoiding per-event/per-jet ambiguity.
#   - 4.9.56 (2026-03-10): ADD: Plot lead-vs-subleading jet correlation observables from analyze_dphi_sliced.cpp v9.6.4+ for both subfrac and nosubfrac branches.
#     • NEW: Plot TH2D objects h2_sublead_vs_lead_Rxxx_all(_nosubfrac) as full-range dijet p_T correlation maps under ${DIR_FINAL}/plots/absolute/{subfrac,nosubfrac}/lead_sublead_correlation/.
#     • NEW: Plot TProfile objects prof_sublead_vs_lead_Rxxx_ptleadbins(_nosubfrac) as <p_{T}^{sublead}> vs p_{T}^{lead} curves using PT_LEAD_BIN_EDGES on the x axis, written to the same branch-resolved folder.
#     • STYLE: Use standard leading/subleading jet axis labels, log p_T axes matching the jet-spectrum range conventions, and branch/R-aware titles.
#   - 4.9.55 (2026-03-10): ADD: Plot accepted particle-level constituent QA histograms particle_pt_all, particle_eta_all, and particle_phi_all under ${DIR_FINAL}/plots/particle_level/.
#     • STYLE: Use standard particle-level axis labels/titles; particle p_T uses log-x/log-y spectrum presentation while η and φ use linear axes.
#     • ROUTING: Treat these histograms as branch-neutral pre-clustering observables (not subfrac/nosubfrac and not dijet-normalized).
#   - 4.9.54 (2026-03-08): FIX: Reconstruct absolute-spectrum xsec normalization bands from published per-slice merged ROOT contributions instead of applying one run-level xsec_total_rel_err to every bin.
#     • FIX: When INCLUDE_XSEC_NORM_ERR=1, load per-slice rootfile/xsec_rel_err entries from ${DIR_FINAL}/xsec_summary.json and compute sigma_norm(bin)=sqrt(sum_s (r_s*y_{bin,s})^2).
#     • SAFETY: Hard-fail if any requested absolute histogram is missing from a published per-slice ROOT or if slice/final binning disagrees, so downstream plots cannot quietly use a fake blanket normalization band.
#   - 4.9.53 (2026-03-08): FIX: When INCLUDE_XSEC_NORM_ERR=1, require ${DIR_FINAL}/xsec_summary.json to contain a finite, strictly positive xsec_total_rel_err; otherwise hard-fail instead of silently dropping the requested global normalization band from plot errors.
#   - 4.9.52 (2026-03-06): FIX: Make explicit fitter overlay/annotation text consistently obey PLOT_NOTE_FONTSIZE and ensure combined-Mjj legends obey PLOT_LEGEND_FONTSIZE (instead of accidentally using tick size).
#     SAFETY: Plot-style parsing now warns and falls back on invalid/non-positive font-size values, but does not touch histogram parsing, branch routing, or output folder structure.
#   - 4.9.51 (2026-03-05): FIX: Stop pre-creating the unused legacy top-level plots/summary directory.
#     Canonical summary outputs still write only to plots/absolute/{subfrac,nosubfrac}/summary and
#     plots/dijet_normalized/{subfrac,nosubfrac}/summary, and the fitter now removes a stale top-level
#     plots/summary folder if it exists and is empty. This avoids the confusing stray empty summary path.
#   - 4.9.50 (2026-03-05): FIX: Treat analyzer inclusive jet spectra/radius-ratio outputs as branch-neutral.
#     Inclusive jet plots (jetpt_incl_* and jetR_ratio_incl_*) now write outside subfrac/nosubfrac folders because analyze_dphi_sliced.cpp does not apply SUBFRAC or book *_nosubfrac counterparts for them.
#     FIX: Default branch legacy jet-R plots now write into plots/jet_R_dependence/subfrac/ (instead of mixing top-level vs nosubfrac).
#     FIX: width_vs_R summaries no longer mix default + no-SUBFRAC fits; fitter now writes separate summary plots per branch.
#     DOCS: Inclusive normalized jet-spectrum labels now use σ_incl instead of σ_sel.
#   - 4.9.49 (2026-03-05): FIX: Normalize recursively-read ROOT object names to leaf histogram names before parser matching; uproot can report subdirectory objects with path prefixes (e.g. 'nosubfrac/dphi_...'), which made the fitter count no-SUBFRAC histograms in inventory but fail to parse/save them.
#     FIX: Accept analyzer η histogram names using both 'eta_sub' and legacy 'eta_sublead' spellings; previous regex silently dropped subleading-η plots.
#     ADD: Log ROOT key path-normalization samples and parser-match counts for no-SUBFRAC histograms so any future routing/parser failure is visible in pyfit logs.
#   - 4.9.48 (2026-03-05): FIX: Stop relying on prefix-swapping path routing for canonical fitter outputs.
#     All plots under plots/absolute/* and plots/dijet_normalized/* now use explicit
#     branch+category roots, so NO-SUBFRAC files cannot silently drift into the wrong tree.
#     ADD: Final save-count summary by branch/category to make empty-folder bugs obvious in logs.
#   - 4.9.47 (2026-03-05): FIX: Correct branch routing bug that created
#     plots/*/subfrac/subfrac/... (duplicate 'subfrac' level) and could hide
#     NO-SUBFRAC outputs. Routing now treats paths already rooted in
#     {absolute,dijet_normalized}/{subfrac,nosubfrac}/ as canonical and only
#     swaps the branch token when needed.
#   - 4.9.46 (2026-03-05): FIX: Canonical plot layout now writes ONLY to:
#       plots/absolute/{subfrac,nosubfrac}/<category>/ and plots/dijet_normalized/{subfrac,nosubfrac}/<category>/
#     (no more empty dead-end folders like plots/absolute/eta).
#     FIX: Δφ + frac_vs_theta outputs now also obey branch routing (subfrac vs nosubfrac).
#   - 4.9.44 (2026-03-04): ADD: Plot ALL analyzer jet-pT spectra (incl/lead/sublead) for both default and nosubfrac branches; FIX: Detect nosubfrac via ROOT subdirectory path in addition to *_nosubfrac name suffix, so nosubfrac plots always land under */nosubfrac/ folders.
#   - 4.9.43 (2026-03-03): FIX: Save frac_vs_theta diagnostic plot to the new absolute/ Δφ fit folder (avoid missing legacy dphi_fit/ directory after legacy-plot cleanup).
#   - 4.9.42 (2026-03-03): Cleanup: Stop writing duplicate 'legacy' plot copies for categories already emitted under absolute/ and dijet_normalized/; keep legacy-only plots (e.g. width_vs_R, jet_R_dependence) unchanged.
#   - 4.9.41 (2026-03-03): FIX: Dijet imbalance xJ section no longer crashes (avoid f-string braces in LaTeX $x_{J}$ title), so xJ/imbalance plots actually get written.
#   - 4.9.40 (2026-03-03): Fix matplotlib mathtext crash by using \leq instead of unsupported \le in unfolded title.
# - 2026-03-03: v4.9.39 FIX: Escape backslashes in mathtext title strings ("\\Delta\\varphi") to prevent matplotlib mathtext parse crash ("\v" -> vertical tab).
# - 2026-03-03: v4.9.38 FIX: Define xsec_rel_err in main() via load_xsec_rel_err(DIR_FINAL) before passing into read_root_histograms(); prevents NameError crash.
# - 2026-03-03: v4.9.37 FIX: xscape_ini.expand_vars signature is (p, ini); fitter wrapper now passes cfg positionally to avoid unexpected keyword crash.
# - 2026-03-03: v4.9.35 FIX: width-vs-R summary plot writes to summary output dir (no undefined hn); __version__ synchronized with header.
# - 2026-03-03: v4.9.36 FIX: Correct expand_vars(...) calls to pass cfg as keyword (cfg=cfg); prevents TypeError crash at startup when RUNS_BASE/DIR_FINAL/INPUT_ROOT are expanded.
# - 2026-03-03: v4.9.34 FIX: RMS (background-subtracted) now uses a signed estimator (no negative-bin clipping bias) while fractions/CDF remain clipped; bootstrap RMS uncertainty now matches the chosen RMS estimator (signed or clipped fallback) for internal consistency.
# - 2026-03-03: v4.9.33 FIX: Label honesty: per-normalized plots now use σ_sel (integral over the plotted selection) instead of σ_sel in y-axis/title text; avoids implying identical dijet cross section across observables with different selections (e.g., Mjj, optional xJ/AJ back-to-back).
# - 2026-03-03: v4.9.32 FIX: Fit eligibility test now counts yc==0 bins (with ye>0) inside fit window; prevents skipping fits in low-stat windows.
# - 2026-03-03: v4.9.31 FIX: Fit window now includes yc==0 bins when ye>0 (prevents bias from dropping zero-content bins in low-stat Δφ tails).
# - 2026-03-03: v4.9.30 FIX: Corrected indentation bug in negative-bin diagnostics block (prevents IndentationError crash at startup).
# - 2026-03-03: v4.9.29 FIX: parse_bool now supports default=... (prevents crash); require ≥3 fit points; clip negative background-subtracted bins to 0 for RMS/CDF metrics (diagnostics preserved).
# - 2026-03-03: v4.9.28 FIX: Δφ title η acceptance now respects JET_ETA_MODE=1 cone containment: uses |η_jet|<JET_ETA_MAX−R (per-R), matching comparisor/analyzer.
# - 2026-03-03: v4.9.27 DOCS: Ensure Δφ plot titles remain selection-free (no back-to-back cut text); analyzer applies no Δφ back-to-back cut.
# - 2026-03-02: v4.9.25 FIX: Make missing xscape_ini import fail cleanly (no NameError).
# - 2026-03-02: v4.9.25 FIX: Use PT_ALL_LABEL numeric inclusive range instead of literal 'all' in pT1 titles (match comparisor).
# - 2026-03-02: v4.9.26 FIX: Use PT_ALL_LABEL for inclusive (isAll) labels everywhere (including summary tables) for comparisor consistency.
# - 2026-03-02: Standardized 'nosubfrac' tag in plot titles/labels for consistency.
# v4.9.23 (2026-03-02, title honesty for per-dijet xJ/AJ):
#   • FIX (2026-03-02): Abs-Δφ observable labeling updated to match analyzer definition: |Δφ| ≡ |wrap(φ1−φ2)| folded to [0,π].
#     - Titles now say 'folded to [0,π]' (paper-friendly) and x-axis uses |Δφ| for abs panels.
#     - No physics/fit/normalization changes; presentation-only.
#
#   • FIX: Per-dijet normalized xJ/AJ plot titles now reflect actual y-axis scale (log vs linear) after safe-log logic.
#         (Previously hardcoded “log y” even when log scale was not applied.)
#
# v4.9.21 (2026-03-02, plot-title truth + version sync):
#   • FIX: Non-normalized xJ/AJ titles now reflect actual y-axis scale (log vs linear) after applying safe-log logic.
#   • FIX: Synced __version__ with the header version.
#
# v4.9.20 (2026-03-02, changelog correction only):
#   • DOCS: Cleaned the changelog to remove/clarify notes about outputs that no longer exist in this script.
#           No functional/physics/plot changes in this version.
#
# v4.9.19 (2026-03-02, terminology cleanup):
#   • DOCS: Comment/docstring terminology cleanup only (no changes to produced outputs).
#
# v4.9.16 (2026-03-02, retire legacy per-count / “effective stats” plot sets):
#   • CHANGE: Removed the legacy per-count / effective-stats normalized plot categories and their output routing.
#             The fitter produces ONLY paper-defensible per-dijet shapes as (1/σ_sel) dσ/dX (plus absolute dσ/dX).
#
# v4.8 (2026-03-02, align fitter input with merge output):
#   • FIX: Default input ROOT aligned with merger output: ${DIR_FINAL}/dphi_allSlices.root.
#   • ADD: Optional jetscape.ini override INPUT_ROOT (expanded with ini+env vars) and hard-fail if missing.
#   • LOG: Record INPUT_ROOT path in fit_py.log for reproducibility.
#
# v4.5 (support analyzer no-SUBFRAC histograms in-place):
#   • NEW: Recursively read TH1 histograms from ROOT subdirectories (supports TDirectory 'nosubfrac').
#   • NEW: Accept histogram names ending with '_nosubfrac' for Δφ/η/Mjj/xJ/AJ/jet pT.
#   • NEW: Write plots for *_nosubfrac into parallel plot subfolders (same layout conventions).
#
# v4.4 (strict config: remove fitter hidden defaults):
#   • CHANGE: The fitter now REQUIRES key analysis knobs in jetscape.ini (hard-fail if missing/blank).
#   • SAFETY: Invalid values for covariance/weighting/tolerance knobs hard-fail (no silent fallback).
#
# v4.3 (bugfix: restore missing covariance-mode helper):
#   • FIX: Define _canon_cov_mode() used by main() (consistent with mjj_comparisor_py.py). Prevents NameError crash.
#
# v4.2 (config consistency: covariance mode precedence + strict mismatch fail):
#   • CHANGE: COVARIANCE_MODE is canonical; PERDIJET_COV_MODE is legacy fallback only.
#   • SAFETY: Hard-fail if BOTH keys are set and disagree, preventing silent fitter/comparisor mismatches.
#
# v4.0 (robustness + compatibility cleanup):
#   • FIX: Robust jet-R tag decoding supports both legacy and standard tag conventions.
#   • FIX: Version banner/log reports the actual file version.

_FONTS = {
    'base': 12.0, 'title': 14.0, 'suptitle': 16.0, 'label': 12.0,
    'tick': 11.0, 'legend': 11.0, 'note': 10.0,
}

__version__ = "4.9.75"
import os, sys, re, math, time, errno
import json
import numpy as np

# jetscape.ini helpers (shared with mjj_comparisor_py.py). Hard-fail if missing.
try:
    from xscape_ini import read_ini as _read_ini_obj, parse_list as _ini_parse_list, parse_bool as _ini_parse_bool, expand_vars as _ini_expand_vars
except Exception as _e_ini:
    _read_ini_obj = None
    _ini_parse_list = None
    _ini_parse_bool = None
    _ini_expand_vars = None
    _INI_IMPORT_ERROR = _e_ini
else:
    _INI_IMPORT_ERROR = None

def _ini_fatal(msg: str) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(2)

def read_ini(path: str):
    if _read_ini_obj is None:
        _ini_fatal(f"Missing required module xscape_ini (needed for read_ini/expand_vars). Import error: {_INI_IMPORT_ERROR}")
    return _read_ini_obj(path)

def expand_vars(s: str, *, cfg=None):
    if _ini_expand_vars is None:
        _ini_fatal(f"Missing required module xscape_ini (needed for read_ini/expand_vars). Import error: {_INI_IMPORT_ERROR}")
    return _ini_expand_vars(s, cfg)  # xscape_ini.expand_vars(p, ini) positional

def parse_list(s: str):
    if _ini_parse_list is None:
        _ini_fatal(f"Missing required module xscape_ini (needed for parse_list). Import error: {_INI_IMPORT_ERROR}")
    return _ini_parse_list(s)

from typing import Optional, Dict, List, Tuple, Iterable

SELECTED_DIJET_COUNT_SEMANTICS_EXPECTED = "event_level_selected_dijet_pair_counts"

def parse_bool(s: Optional[str], default: Optional[bool] = None) -> bool:
    """
    Parse a boolean from ini/env text using xscape_ini.parse_bool.

    - If s is None or empty/whitespace, returns `default` when provided.
    - If default is None and s is missing/empty, raises ValueError.
    """
    if _ini_parse_bool is None:
        _ini_fatal(f"Missing required module xscape_ini (needed for parse_bool). Import error: {_INI_IMPORT_ERROR}")
    if s is None:
        if default is None:
            raise ValueError("Missing boolean value and no default provided")
        return bool(default)
    ss = str(s).strip()
    if ss == "":
        if default is None:
            raise ValueError("Empty boolean value and no default provided")
        return bool(default)
    return _ini_parse_bool(ss)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

# Plot cosmetics (override with env vars when needed)
DEFAULT_MARKER_SIZE = float(os.environ.get("DPHI_MS", "2.0"))
DEFAULT_LINE_WIDTH  = float(os.environ.get("DPHI_LW", "0.8"))
PERDIJET_COV_MODE = "diag"  # configured in main() from jetscape.ini; env may override
INCLUDE_XSEC_NORM_ERR = 1   # configured in main() from jetscape.ini; env may override

# Leading-jet pT bin edges (from jetscape.ini) for presentation-friendly titles.
# PT_LEAD_BIN_EDGES is required and validated in main(); missing/invalid values hard-fail.
PT_LEAD_BIN_EDGES = []  # type: list
PT_ALL_LABEL = "all"
SINGLE_SLICE_MODE = False
JET_RADIUS_LIST_CFG = []  # type: list
JET_RADIUS_COMPARE_PAIRS = []  # type: list[tuple[float, float]]
SELECTED_DIJET_COUNTS = None

def _ptlead_profile_title_tag() -> str:
    """Human-readable description of the configured leading-jet binning used by prof_sublead_vs_lead_* plots."""
    try:
        edges = [float(x) for x in PT_LEAD_BIN_EDGES]
    except Exception:
        edges = []
    if len(edges) >= 2 and all(np.isfinite(edges)):
        return f"all configured leading-jet bins: {edges[0]:g}–{edges[-1]:g} GeV ({len(edges)-1} bins)"
    return "all configured leading-jet bins"

from matplotlib import patches as mpatches

import uproot
from scipy.optimize import curve_fit
from scipy.special import erfinv, erf
from math import pi
from collections import defaultdict

# ------------------ per-dijet normalization w/ covariance ------------------

def normalize_per_dijet_with_cov(
    y: np.ndarray,
    ye: np.ndarray,
    bw: np.ndarray,
    *,
    denom_positive_only: bool=False,
    cov_mode: str="diag",
):
    """
    Per-dijet normalization for differential spectra:

        y_n = y / σ   with   σ = ∑_j (y_j * bw_j)

    If σ is computed from the SAME histogram bins, y and σ are correlated.
    Two (approximate) covariance models are supported:

      • cov_mode="diag" (default): independent-bin approximation (diagonal covariance only),
        but includes the shared-denominator correlation via Cov(y_i,σ)=bw_i Var(y_i).

      • cov_mode="conservative" (alias: "upperbound"): inflates Var(σ) using an upper-bound style model.
        To guarantee it never *shrinks* uncertainties, it does NOT apply a Cov(y_i,σ) term (cov=0).
        This is intentionally conservative for error bars; use "diag" for the correlated-denominator model.

    Parameters
    ----------
    y, ye, bw : arrays
        y  = bin content (e.g., dσ/dx)
        ye = 1σ uncertainty on y
        bw = bin width Δx

    denom_positive_only : bool
        If True, σ integrates only bins with y>0 (matching earlier "positive-only" practice).
        Then Cov(y_i,σ)=0 for bins with y<=0.

    cov_mode : {"diag","conservative","upperbound"}
        Choice of covariance model for σ.

    Returns
    -------
    sigma : float
    y_n   : ndarray
    ye_n  : ndarray
    """
    y  = np.asarray(y,  dtype=float)
    ye = np.asarray(ye, dtype=float)
    bw = np.asarray(bw, dtype=float)

    cov_mode = (cov_mode or "diag").strip().lower()
    var_y = np.where(np.isfinite(ye), ye*ye, 0.0)

    if denom_positive_only:
        m_denom = np.isfinite(y) & np.isfinite(bw) & (bw > 0) & (y > 0)
    else:
        m_denom = np.isfinite(y) & np.isfinite(bw) & (bw > 0)

    y_d  = np.where(m_denom, y, 0.0)
    bw_d = np.where(m_denom, bw, 0.0)

    sigma = float(np.sum(y_d * bw_d))
    if not (np.isfinite(sigma) and sigma > 0):
        return float("nan"), None, None

    if cov_mode in ("conservative", "upperbound", "upperbound_nocov"):
        # Upper-bound on Var(σ) assuming strong positive correlations between bins.
        # IMPORTANT: We intentionally apply NO Cov(y_i,σ) term here.
        # An oversized positive covariance can make the -2*y*Cov term artificially shrink
        # the propagated variance (or even drive it negative before clipping).
        S = float(np.sum(bw_d * np.where(m_denom, np.abs(ye), 0.0)))
        var_sigma = S*S
        cov = np.zeros_like(y, dtype=float)
    else:
        # Diagonal approximation (independent bins)
        var_sigma = float(np.sum((bw_d*bw_d) * np.where(m_denom, var_y, 0.0)))
        cov = np.where(m_denom, bw * var_y, 0.0)

    y_n = y / sigma

    var_n = (var_y / (sigma*sigma)) + ((y*y) * var_sigma / (sigma**4)) - (2.0 * y * cov / (sigma**3))
    bad = (~np.isfinite(var_n)) | (var_n < 0)
    if np.any(bad):
        # Do NOT clip to 0: that fakes “perfect” error bars in unstable / undefined regimes.
        # Instead, mark invalid propagated bins with NaN so plots and downstream summaries cannot silently trust them.
        try:
            _log(f"[WARN] per-dijet variance invalid in {int(np.sum(bad))}/{var_n.size} bins; setting those errors to NaN (not 0).")
        except Exception:
            pass
        var_n = var_n.astype(float, copy=True)
        var_n[bad] = np.nan
    ye_n = np.sqrt(var_n)

    return sigma, y_n, ye_n


def normalize_per_dijet_with_matrix(
    y: np.ndarray,
    ye: np.ndarray,
    bw: np.ndarray,
    *,
    denom_positive_only: bool=False,
    cov_mode: str="diag",
):
    """Return per-dijet normalized bins together with an approximate covariance matrix.

    This is a fitter-only downstream approximation built from the already-merged
    histogram bin errors. It does NOT require upstream replica/covariance products.

    For cov_mode="diag", it assumes the raw differential bins are independent before
    the shared normalization by sigma = sum_j y_j * bw_j, then propagates the full
    Jacobian to obtain a bin-to-bin covariance matrix for the normalized shape.

    For cov_mode="conservative", the current workflow only defines a diagonal
    uncertainty inflation for the normalized bins, not a physically grounded
    off-diagonal covariance matrix. In that case we return a diagonal matrix made
    from the propagated 1σ errors and mark the matrix mode as a fallback.

    Returns
    -------
    sigma : float
    y_n   : ndarray | None
    ye_n  : ndarray | None
    cov_n : ndarray | None
    matrix_mode : str
        "full" for the Jacobian-propagated covariance, "diag_fallback" when only
        a diagonal matrix is available.
    """
    y  = np.asarray(y,  dtype=float)
    ye = np.asarray(ye, dtype=float)
    bw = np.asarray(bw, dtype=float)

    sigma, y_n, ye_n = normalize_per_dijet_with_cov(
        y, ye, bw, denom_positive_only=denom_positive_only, cov_mode=cov_mode
    )
    if not (np.isfinite(sigma) and sigma > 0.0) or y_n is None or ye_n is None:
        return float("nan"), None, None, None, "invalid"

    cov_mode = (cov_mode or "diag").strip().lower()
    if cov_mode in ("conservative", "upperbound", "upperbound_nocov"):
        cov_n = np.diag(np.where(np.isfinite(ye_n), np.square(ye_n), np.nan))
        return sigma, y_n, ye_n, cov_n, "diag_fallback"

    var_y = np.where(np.isfinite(ye), np.square(ye), 0.0)
    if denom_positive_only:
        m_denom = np.isfinite(y) & np.isfinite(bw) & (bw > 0) & (y > 0)
    else:
        m_denom = np.isfinite(y) & np.isfinite(bw) & (bw > 0)

    bw_eff = np.where(m_denom, bw, 0.0)
    n = y.size
    if n == 0:
        return sigma, y_n, ye_n, np.zeros((0, 0), dtype=float), "full"

    # Jacobian for n_i = y_i / sigma with sigma = sum_k y_k * bw_eff[k].
    # d n_i / d y_k = δ_ik / sigma - y_i * bw_eff[k] / sigma^2
    J = -np.outer(y, bw_eff) / (sigma * sigma)
    idx = np.arange(n)
    J[idx, idx] += 1.0 / sigma

    cov_n = (J * var_y[np.newaxis, :]) @ J.T
    cov_n = 0.5 * (cov_n + cov_n.T)

    diag = np.diag(cov_n).astype(float, copy=True)
    bad = (~np.isfinite(diag)) | (diag < -1e-15)
    if np.any(bad):
        try:
            _log(f"[WARN] normalized covariance produced invalid diagonal entries in {int(np.sum(bad))}/{diag.size} bins; affected diagonal variances set to NaN.")
        except Exception:
            pass
        diag[bad] = np.nan
    diag[(diag < 0.0) & np.isfinite(diag)] = 0.0
    ye_n = np.sqrt(diag)
    return sigma, y_n, ye_n, cov_n, "full"


def _regularize_covariance_matrix(cov: np.ndarray, *, label: str="cov"):
    """Symmetrize and add the smallest practical diagonal nugget if needed."""
    cov = np.asarray(cov, dtype=float)
    if cov.ndim != 2 or cov.shape[0] != cov.shape[1]:
        raise ValueError(f"{label}: covariance matrix must be square; got shape {cov.shape}")
    cov = 0.5 * (cov + cov.T)
    if cov.size == 0:
        return cov, 0.0
    if not np.all(np.isfinite(cov)):
        raise ValueError(f"{label}: covariance matrix contains non-finite entries")

    diag = np.diag(cov)
    pos = diag[np.isfinite(diag) & (diag > 0)]
    scale = float(np.nanmedian(pos)) if pos.size else 1.0
    nugget_floor = max(1e-18, scale * 1e-12)

    try:
        eigmin = float(np.nanmin(np.linalg.eigvalsh(cov)))
    except Exception as exc:
        raise ValueError(f"{label}: could not diagonalize covariance matrix: {exc}")

    nugget = 0.0
    if (not np.isfinite(eigmin)) or eigmin <= 0.0:
        nugget = (abs(eigmin) if np.isfinite(eigmin) else scale) + nugget_floor
        cov = cov + np.eye(cov.shape[0]) * nugget
    return cov, float(nugget)


def _chi2_with_covariance(resid: np.ndarray, cov: np.ndarray) -> float:
    resid = np.asarray(resid, dtype=float)
    cov = np.asarray(cov, dtype=float)
    try:
        sol = np.linalg.solve(cov, resid)
    except np.linalg.LinAlgError:
        sol = np.linalg.pinv(cov, rcond=1e-12) @ resid
    return float(resid @ sol)

def ensure_dir(path: str):
    try:
        os.makedirs(path, exist_ok=True)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


def wrap_distance_to_pi(x):
    return abs(math.atan2(math.sin(x - pi), math.cos(x - pi)))

def to_deg(x): return x * 180.0 / pi
def to_rad(x): return x * pi / 180.0


def isotonic_regression_increasing(y: np.ndarray) -> np.ndarray:
    """
    Simple pool-adjacent-violators (PAVA) isotonic regression for a 1D sequence.
    Returns a non-decreasing sequence minimizing squared deviation from input.
    """
    y = np.asarray(y, dtype=float)
    n = int(y.size)
    if n == 0:
        return y

    # Work with Python lists for easy block merging.
    vals = y.tolist()
    w = [1.0]*n
    start = list(range(n))
    end = [i+1 for i in range(n)]

    i = 0
    while i < len(vals) - 1:
        if vals[i] <= vals[i+1]:
            i += 1
            continue
        # merge blocks i and i+1
        totw = w[i] + w[i+1]
        avg = (vals[i]*w[i] + vals[i+1]*w[i+1]) / totw
        vals[i] = avg
        w[i] = totw
        end[i] = end[i+1]
        del vals[i+1]
        del w[i+1]
        del start[i+1]
        del end[i+1]
        if i > 0:
            i -= 1

    out = np.empty(n, dtype=float)
    for s, e, v in zip(start, end, vals):
        out[s:e] = v

    # numerical safety
    out = np.clip(out, 0.0, 1.0)
    return out


def _strip_nosubfrac_suffix(hn: str) -> Tuple[str, bool]:
    if isinstance(hn, str) and hn.endswith("_nosubfrac"):
        return (hn[:-10], True)
    return (hn, False)


def _canonical_hist_key(hn: str, *, in_ns_dir: bool = False) -> str:
    if not isinstance(hn, str):
        return hn
    if in_ns_dir and not hn.endswith("_nosubfrac"):
        return f"{hn}_nosubfrac"
    return hn


def _iter_root_items_recursive(f, prefix: str = "") -> Iterable[Tuple[str, object, str, bool]]:
    try:
        items = list(f.items())
    except Exception:
        items = []
    for name, obj in items:
        leaf = name.split(";")[0]
        full = f"{prefix}/{leaf}" if prefix else leaf
        comps = [c for c in full.split("/") if c]
        in_ns_dir = any(c == "nosubfrac" for c in comps[:-1])
        try:
            cls = getattr(obj, "classname", "")
            cls = str(cls) if not isinstance(cls, str) else cls
        except Exception:
            cls = ""
        if cls.startswith("TDirectory") or cls.startswith("TDirectoryFile"):
            try:
                yield from _iter_root_items_recursive(obj, prefix=full)
            except Exception:
                continue
        else:
            yield (leaf, obj, full, in_ns_dir)


class SliceNormBandBuilder:
    """Build exact bin-by-bin xsec normalization bands from published per-slice merged ROOTs."""

    def __init__(self, final_dir: str):
        self.final_dir = final_dir
        self.summary_path = os.path.join(final_dir, "xsec_summary.json")
        self.global_rel_err = float("nan")
        self.slices: List[Dict[str, object]] = []
        self._norm_map: Dict[str, Dict[str, object]] = {}
        self._load_summary()
        self._build_norm_map()

    def _load_summary(self) -> None:
        with open(self.summary_path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        self.global_rel_err = float(payload.get("xsec_total_rel_err", float("nan")))
        if not np.isfinite(self.global_rel_err) or self.global_rel_err <= 0:
            raise RuntimeError(
                f"{self.summary_path} has invalid xsec_total_rel_err={self.global_rel_err!r}"
            )

        slices = payload.get("slices", [])
        if not isinstance(slices, list) or len(slices) == 0:
            raise RuntimeError(f"{self.summary_path} has no usable slice entries")

        loaded: List[Dict[str, object]] = []
        for idx, entry in enumerate(slices, start=1):
            rel = float(entry.get("xsec_rel_err", float("nan")))
            if not np.isfinite(rel) or rel <= 0:
                raise RuntimeError(
                    f"{self.summary_path} slice #{idx} has invalid xsec_rel_err={rel!r}"
                )

            root_rel = str(entry.get("rootfile", "") or "").strip()
            if root_rel == "":
                raise RuntimeError(
                    f"{self.summary_path} slice #{idx} is missing required rootfile"
                )

            root_path = root_rel if os.path.isabs(root_rel) else os.path.join(self.final_dir, root_rel)
            if not os.path.isfile(root_path):
                raise RuntimeError(
                    f"{self.summary_path} slice #{idx} rootfile does not exist: {root_path}"
                )

            loaded.append(
                {
                    "pt_lo": entry.get("pt_lo", None),
                    "pt_hi": entry.get("pt_hi", None),
                    "xsec_rel_err": rel,
                    "rootfile": root_path,
                }
            )
        self.slices = loaded

    def _build_norm_map(self) -> None:
        accum: Dict[str, Dict[str, object]] = {}
        for slice_info in self.slices:
            rel = float(slice_info["xsec_rel_err"])
            root_path = str(slice_info["rootfile"])
            th1_count = 0
            for leaf, obj, cls, in_ns_dir in _iter_root_objects(root_path):
                if not cls.startswith("TH1"):
                    continue
                try:
                    edges = obj.axes[0].edges()
                    centers = 0.5 * (edges[:-1] + edges[1:])
                    widths = edges[1:] - edges[:-1]
                    vals = np.asarray(obj.values(flow=False), dtype=float)
                except Exception as e:
                    raise RuntimeError(
                        f"Failed reading histogram '{leaf}' from {root_path}: {e}"
                    ) from e

                key = _canonical_hist_key(leaf, in_ns_dir=in_ns_dir)
                term2 = (rel * vals) ** 2
                rec = accum.get(key)
                if rec is None:
                    accum[key] = {
                        "centers": centers.astype(float),
                        "widths": widths.astype(float),
                        "sqsum": term2.astype(float),
                        "seen_count": 1,
                    }
                else:
                    if (
                        len(rec["centers"]) != len(centers)
                        or not np.allclose(rec["centers"], centers, rtol=0.0, atol=1e-9)
                        or not np.allclose(rec["widths"], widths, rtol=0.0, atol=1e-9)
                    ):
                        raise RuntimeError(
                            f"Binning mismatch for histogram '{key}' across per-slice ROOTs (offending file: {root_path})"
                        )
                    rec["sqsum"] = np.asarray(rec["sqsum"], dtype=float) + term2
                    rec["seen_count"] = int(rec["seen_count"]) + 1
                th1_count += 1
            _log(f"[DEBUG] xsec band builder indexed {th1_count} TH1 histograms from {root_path}")
        self._norm_map = accum

    def norm_err_for_hist(
        self,
        hn: str,
        centers: np.ndarray,
        widths: np.ndarray,
        *,
        in_ns_dir: bool = False,
    ) -> np.ndarray:
        key = _canonical_hist_key(hn, in_ns_dir=in_ns_dir)
        rec = self._norm_map.get(key)
        if rec is None:
            raise RuntimeError(
                f"Per-slice xsec band helper is missing histogram '{key}' required by the final merged ROOT"
            )
        if int(rec.get("seen_count", 0)) != len(self.slices):
            raise RuntimeError(
                f"Per-slice xsec band helper saw histogram '{key}' in {int(rec.get('seen_count', 0))}/{len(self.slices)} slice ROOTs"
            )

        centers = np.asarray(centers, dtype=float)
        widths = np.asarray(widths, dtype=float)
        rec_centers = np.asarray(rec["centers"], dtype=float)
        rec_widths = np.asarray(rec["widths"], dtype=float)
        if (
            len(rec_centers) != len(centers)
            or not np.allclose(rec_centers, centers, rtol=0.0, atol=1e-9)
            or not np.allclose(rec_widths, widths, rtol=0.0, atol=1e-9)
        ):
            raise RuntimeError(
                f"Final/per-slice binning mismatch for histogram '{key}' while constructing xsec normalization band"
            )
        return np.sqrt(np.asarray(rec["sqsum"], dtype=float))


def load_xsec_rel_err(final_dir: str) -> float:
    """
    Load σGen relative uncertainty from ${DIR_FINAL}/xsec_summary.json.
    Returns NaN if missing/unreadable/invalid.
    """
    try:
        p = os.path.join(final_dir, "xsec_summary.json")
        with open(p, "r", encoding="utf-8") as f:
            j = json.load(f)
        v = float(j.get("xsec_total_rel_err", float("nan")))
        if not np.isfinite(v) or v <= 0:
            return float("nan")
        return v
    except Exception:
        return float("nan")




def _resolve_selected_dijet_counts_summary_path(final_dir: str) -> str:
    """Resolve the merged selected-dijet count summary path published by merge."""
    try:
        xsec_path = os.path.join(final_dir, "xsec_summary.json")
        if os.path.isfile(xsec_path):
            with open(xsec_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            rel = str(payload.get("selected_dijet_counts_summary_json", "") or "").strip()
            if rel:
                p = rel if os.path.isabs(rel) else os.path.join(final_dir, rel)
                if os.path.isfile(p):
                    return p
    except Exception:
        pass
    return os.path.join(final_dir, "selected_dijet_counts_summary.json")


class SelectedDijetCountResolver:
    """Resolve merged observable-specific selected dijet counts for single-slice labeling."""

    def __init__(self, payload: dict, jet_radius_list, pt_edges):
        self.payload = payload
        self.jet_radius_list = [float(r) for r in jet_radius_list]
        self.pt_edges = [float(x) for x in pt_edges]
        total = payload.get("selected_dijet_counts_total")
        if not isinstance(total, dict):
            raise RuntimeError("selected_dijet_counts_summary.json is missing selected_dijet_counts_total")
        self.count_semantics = str(payload.get("count_semantics") or total.get("count_semantics") or "").strip()
        if self.count_semantics == "":
            raise RuntimeError("selected_dijet_counts_summary.json is missing count_semantics")
        if self.count_semantics != SELECTED_DIJET_COUNT_SEMANTICS_EXPECTED:
            raise RuntimeError(
                "selected_dijet_counts_summary.json has unsupported count_semantics="
                f"{self.count_semantics!r}; expected {SELECTED_DIJET_COUNT_SEMANTICS_EXPECTED!r}"
            )
        self.total = total

    @classmethod
    def load(cls, final_dir: str, jet_radius_list, pt_edges):
        path = _resolve_selected_dijet_counts_summary_path(final_dir)
        if not os.path.isfile(path):
            raise RuntimeError(
                f"SINGLE_SLICE_MODE=1 requires merged selected dijet counts, but summary is missing: {path}"
            )
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        merged_slice_count = int(payload.get("merged_slice_count", -1))
        if merged_slice_count != 1:
            raise RuntimeError(
                f"SINGLE_SLICE_MODE=1 requires merged_slice_count=1 in {path}; got {merged_slice_count}"
            )
        return cls(payload, jet_radius_list, pt_edges), path

    def _branch_block(self, is_nosubfrac: bool) -> dict:
        block = self.total.get("nosubfrac" if is_nosubfrac else "default")
        if not isinstance(block, dict):
            raise RuntimeError("selected dijet count summary is missing the requested branch block")
        return block

    def _match_radius_index(self, r_value: float) -> int:
        if not self.jet_radius_list:
            raise RuntimeError("JET_RADIUS_LIST is empty; cannot map selected dijet counts to histogram R")
        target = float(r_value)
        matches = [i for i, r in enumerate(self.jet_radius_list) if abs(float(r) - target) <= 5e-4]
        if len(matches) != 1:
            raise RuntimeError(
                f"Could not uniquely map histogram R={target:.6g} onto JET_RADIUS_LIST={self.jet_radius_list}"
            )
        return matches[0]

    def _match_pt_bin_index(self, ptlo: float, pthi: float) -> int:
        if len(self.pt_edges) < 2:
            raise RuntimeError("PT_LEAD_BIN_EDGES is too short to map selected dijet count bins")
        matches = []
        for i in range(len(self.pt_edges) - 1):
            if abs(self.pt_edges[i] - float(ptlo)) <= 1e-6 and abs(self.pt_edges[i+1] - float(pthi)) <= 1e-6:
                matches.append(i)
        if len(matches) != 1:
            raise RuntimeError(
                f"Could not uniquely map pT bin [{ptlo},{pthi}] onto PT_LEAD_BIN_EDGES={self.pt_edges}"
            )
        return matches[0]

    def count_for(self, observable: str, Ruse: float, *, is_nosubfrac: bool = False, ptlo=None, pthi=None, is_abs: bool = False) -> int:
        block = self._branch_block(is_nosubfrac)
        ridx = self._match_radius_index(Ruse)
        obs = str(observable).strip().lower()
        if obs == "dphi":
            finite_pt = (ptlo is not None and pthi is not None and np.isfinite(float(ptlo)) and np.isfinite(float(pthi)))
            if finite_pt:
                pidx = self._match_pt_bin_index(float(ptlo), float(pthi))
                field = "dphi_abs_ptlead_per_R" if is_abs else "dphi_ptlead_per_R"
                raw = block[field][ridx][pidx]
            else:
                field = "dphi_abs_all_per_R" if is_abs else "dphi_all_per_R"
                raw = block[field][ridx]
        elif obs == "xj":
            finite_pt = (ptlo is not None and pthi is not None and np.isfinite(float(ptlo)) and np.isfinite(float(pthi)))
            if finite_pt:
                pidx = self._match_pt_bin_index(float(ptlo), float(pthi))
                raw = block["xj_ptlead_per_R"][ridx][pidx]
            else:
                raw = block["xj_all_per_R"][ridx]
        elif obs == "aj":
            finite_pt = (ptlo is not None and pthi is not None and np.isfinite(float(ptlo)) and np.isfinite(float(pthi)))
            if finite_pt:
                pidx = self._match_pt_bin_index(float(ptlo), float(pthi))
                raw = block["aj_ptlead_per_R"][ridx][pidx]
            else:
                raw = block["aj_all_per_R"][ridx]
        elif obs == "mjj":
            raw = block["mjj_all_per_R"][ridx]
        elif obs in ("sel", "jetpt"):
            raw = block["dphi_all_per_R"][ridx]
        else:
            raise RuntimeError(f"Unsupported observable for selected dijet counts: {observable}")
        val = int(raw)
        if val <= 0:
            raise RuntimeError(
                f"Resolved non-positive selected dijet count for observable={observable}, R={Ruse}, pt=[{ptlo},{pthi}], nosubfrac={is_nosubfrac}, abs={is_abs}: {val}"
            )
        return val


def _single_slice_norm_ylabel(observable: str, *, is_abs: bool = False) -> str:
    obs = str(observable).strip().lower()
    if obs == "dphi":
        if is_abs:
            return r"$(1/N_{|\Delta\varphi|\mathrm{-sel}})\,dN/d|\Delta\varphi|$ (1/rad)"
        return r"$(1/N_{\Delta\varphi\mathrm{-sel}})\,dN/d\Delta\varphi$ (1/rad)"
    if obs == "xj":
        return r"$(1/N_{x_J\mathrm{-sel}})\,dN/dx_J$ (1 per unit $x_J$)"
    if obs == "aj":
        return r"$(1/N_{A_J\mathrm{-sel}})\,dN/dA_J$ (1 per unit $A_J$)"
    if obs == "mjj":
        return r"$(1/N_{M_{jj}\mathrm{-sel}})\,dN/dM_{jj}$ (1/GeV)"
    if obs in ("sel", "jetpt"):
        return r"$(1/N_{\mathrm{dijet,sel}})\,dN/dp_T$ (1/GeV)"
    raise ValueError(f"Unsupported observable for normalized y-label: {observable}")


def _single_slice_norm_title(observable: str, *, is_abs: bool = False) -> str:
    obs = str(observable).strip().lower()
    if obs == "dphi":
        if is_abs:
            return r"$1/N_{|\Delta\varphi|\mathrm{-sel}} \cdot dN/d|\Delta\varphi|$"
        return r"$1/N_{\Delta\varphi\mathrm{-sel}} \cdot dN/d\Delta\varphi$"
    if obs == "xj":
        return r"$1/N_{x_J\mathrm{-sel}} \cdot dN/dx_J$"
    if obs == "aj":
        return r"$1/N_{A_J\mathrm{-sel}} \cdot dN/dA_J$"
    if obs == "mjj":
        return r"$1/N_{M_{jj}\mathrm{-sel}} \cdot dN/dM_{jj}$"
    raise ValueError(f"Unsupported observable for normalized title text: {observable}")


def _legend_count_label(observable: str, count: int, *, is_abs: bool = False) -> str:
    obs = str(observable).strip().lower()
    if obs == "dphi":
        key = "N_dijet,|Δφ|-sel" if is_abs else "N_dijet,Δφ-sel"
    elif obs == "xj":
        key = "N_dijet,xJ-sel"
    elif obs == "aj":
        key = "N_dijet,AJ-sel"
    elif obs == "mjj":
        key = "N_dijet,Mjj-sel"
    else:
        key = "N_dijet,sel"
    return f"XSCAPE ({key}={int(count)})"


def apply_logy_with_floor(ax, y, yerr=None, floor_factor=0.5):
    """Apply log y-scale with a safe positive lower bound derived from data.

    This is a plotting-only transform (does not change histogram contents).
    """
    try:
        y = np.asarray(y, dtype=float)
        if yerr is not None:
            yerr = np.asarray(yerr, dtype=float)
            y_low = y - np.abs(yerr)
        else:
            y_low = y
        pos = y_low[np.isfinite(y_low) & (y_low > 0)]
        if pos.size == 0:
            return
        ymin = float(np.min(pos)) * float(floor_factor)
        if not (np.isfinite(ymin) and ymin > 0):
            return
        ax.set_yscale("log")
        # keep existing upper bound if user code set it elsewhere
        cur = ax.get_ylim()
        ax.set_ylim(bottom=ymin, top=cur[1])
    except Exception:
        # Never let plotting cosmetics crash production.
        return

def yerr_for_plot_absolute(y: np.ndarray, ye_stat: np.ndarray, xsec_norm_term) -> np.ndarray:
    """Return error bars for *display* on absolute spectra.

    - Statistical bin errors come from stored ROOT variances (Sumw2).
    - σGen (cross-section) uncertainty is a correlated scale uncertainty across all bins.
      For plotting, we may optionally show stat ⊕ σ_norm(bin).
      For fits/inference, do NOT treat this as uncorrelated per-bin noise.
    - Backward compatibility: scalar xsec_norm_term is interpreted as a global relative error r,
      giving σ_norm(bin)=r*y_bin.
    """
    y = np.asarray(y, dtype=float)
    ye = np.asarray(ye_stat, dtype=float)
    if not INCLUDE_XSEC_NORM_ERR:
        return ye

    try:
        xterm = np.asarray(xsec_norm_term, dtype=float)
    except Exception:
        return ye

    if xterm.ndim == 0:
        rel = float(xterm)
        if np.isfinite(rel) and rel > 0:
            return np.sqrt(ye * ye + (rel * y) * (rel * y))
        return ye

    if xterm.shape == y.shape and np.all(np.isfinite(xterm)):
        return np.sqrt(ye * ye + xterm * xterm)

    return ye


def errorbar_nan_safe(ax, x, y, yerr, *, fmt='o', ms=None, lw=None, capsize=2, label=None, noerr_alpha=0.55):
    """Plot error bars but tolerate NaN/invalid yerr entries.

    Bins with finite y but non-finite yerr are plotted as points WITHOUT error bars.
    This avoids the 'fake zero error' trap while keeping the shape visible.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if yerr is None:
        ax.plot(x, y, fmt, ms=ms, lw=lw if lw is not None else 0, label=label)
        return
    yerr = np.asarray(yerr, dtype=float)

    m_base = np.isfinite(x) & np.isfinite(y)
    m_err  = m_base & np.isfinite(yerr) & (yerr >= 0)
    m_no   = m_base & (~np.isfinite(yerr))

    used_label = False
    if np.any(m_err):
        ax.errorbar(x[m_err], y[m_err], yerr=yerr[m_err], fmt=fmt, ms=ms, lw=lw, capsize=capsize, label=label)
        used_label = True
    if np.any(m_no):
        # Plot the bins that have undefined propagated errors as points only.
        ax.plot(x[m_no], y[m_no], fmt, ms=ms, lw=0, alpha=noerr_alpha, label=(None if used_label else label))
        # small in-plot note (don’t spam legend)
        try:
            ax.text(0.02, 0.96, f"{int(np.sum(m_no))} bins w/o err", transform=ax.transAxes, fontsize=_FONTS['note'], va='top', alpha=0.7)
        except Exception:
            pass

def _ratio_with_nan_safe_errors(yN, eN, yD, eD):
    """Return ratio + propagated errors without dropping finite central values when yerr is invalid."""
    yN = np.asarray(yN, dtype=float)
    eN = np.asarray(eN, dtype=float)
    yD = np.asarray(yD, dtype=float)
    eD = np.asarray(eD, dtype=float)
    r = np.full_like(yN, np.nan, dtype=float)
    er = np.full_like(yN, np.nan, dtype=float)
    m_val = np.isfinite(yN) & np.isfinite(yD) & (yN > 0) & (yD > 0)
    if not np.any(m_val):
        return r, er, m_val
    r[m_val] = yN[m_val] / yD[m_val]
    m_err = m_val & np.isfinite(eN) & np.isfinite(eD)
    if np.any(m_err):
        relN = eN[m_err] / yN[m_err]
        relD = eD[m_err] / yD[m_err]
        er[m_err] = r[m_err] * np.sqrt(relN**2 + relD**2)
    return r, er, m_val

def auto_xlim_hist(xc, yc, bw, *, logx=True, q_lo=0.002, q_hi=0.998, pad_frac=0.12, x_floor=1e-3, x_ceil=None):
    """
    Pick x-limits that hug the populated region of a (density) histogram.
    Uses the CDF of *counts* s = max(y,0)*Δx (so variable bin widths behave).
    - q_lo/q_hi define the central mass fraction kept (e.g. 0.2%..99.8%).
    - pad_frac adds breathing room (in log space when logx=True).
    - x_floor/x_ceil optionally clamp the result.

    Returns (xmin, xmax) with xmin>0 if logx.
    """
    xc = np.asarray(xc, dtype=float)
    yc = np.asarray(yc, dtype=float)
    bw = np.asarray(bw, dtype=float)

    m = np.isfinite(xc) & np.isfinite(yc) & np.isfinite(bw)
    if logx:
        m &= (xc > 0)

    if not np.any(m):
        xmin = float(x_floor)
        xmax = float(x_ceil) if (x_ceil is not None and x_ceil > xmin) else float(xmin * 10.0)
        return xmin, xmax

    x = xc[m]
    y = np.clip(yc[m], 0.0, None)
    w = np.clip(bw[m], 0.0, None)

    s = y * w  # counts per bin
    tot = float(np.nansum(s))

    # Fallback: if everything is empty, just use the available x span (or config clamp).
    if not np.isfinite(tot) or tot <= 0:
        xmin = float(np.nanmin(x))
        xmax = float(np.nanmax(x))
    else:
        o = np.argsort(x)
        x = x[o]; s = s[o]
        cdf = np.cumsum(s)
        lo = q_lo * tot
        hi = q_hi * tot
        i1 = int(np.searchsorted(cdf, lo, side="left"))
        i2 = int(np.searchsorted(cdf, hi, side="left"))
        i1 = max(0, min(i1, x.size - 1))
        i2 = max(0, min(i2, x.size - 1))
        xmin = float(x[i1])
        xmax = float(x[i2])

    # Ensure a sensible, non-degenerate span.
    if not (np.isfinite(xmin) and np.isfinite(xmax)):
        xmin = float(x_floor)
        xmax = float(x_ceil) if (x_ceil is not None and x_ceil > xmin) else float(xmin * 10.0)
        return xmin, xmax

    if xmax <= xmin:
        # Single-bin case: expand a bit around it.
        if logx and xmin > 0:
            xmin = xmin / 1.5
            xmax = xmax * 1.5
        else:
            span = max(1.0, abs(xmin) * 0.1)
            xmin -= span
            xmax += span

    # Padding.
    if logx:
        xmin = max(xmin, x_floor)
        if xmin <= 0:
            xmin = float(x_floor)
        lx1 = math.log10(xmin)
        lx2 = math.log10(max(xmax, xmin * 1.0001))
        d = max(1e-6, lx2 - lx1)
        lx1 -= pad_frac * d
        lx2 += pad_frac * d
        xmin = 10 ** lx1
        xmax = 10 ** lx2
    else:
        d = max(1e-12, xmax - xmin)
        xmin -= pad_frac * d
        xmax += pad_frac * d

    # Clamp to config bounds if provided.
    xmin = max(float(x_floor), float(xmin))
    if x_ceil is not None and np.isfinite(x_ceil) and x_ceil > xmin:
        xmax = min(float(x_ceil), float(xmax))
    else:
        xmax = float(xmax)

    # Final safety.
    if logx:
        xmin = max(float(x_floor), xmin)
        xmax = max(xmin * 1.01, xmax)
    else:
        xmax = max(xmin + 1e-9, xmax)

    return float(xmin), float(xmax)


def _jetpt_populated_xlim(xc, yc, bw, yerr=None, *, x_floor=0.0, x_ceil=None, pad_frac=0.08, min_pad_gev=15.0):
    """Return a linear-x display window that hugs the populated jet-p_T bins.

    This is a plotting-only helper. It preserves the histogram contents and only
    chooses a more informative x-range for steeply falling spectra that were
    booked out to a large analysis ceiling.
    """
    xc = np.asarray(xc, dtype=float)
    yc = np.asarray(yc, dtype=float)
    bw = np.asarray(bw, dtype=float)
    if yerr is None:
        yerr = np.zeros_like(yc, dtype=float)
    else:
        yerr = np.asarray(yerr, dtype=float)

    m = np.isfinite(xc) & np.isfinite(yc) & np.isfinite(bw) & (bw > 0)
    if np.any(np.isfinite(yerr)):
        yhi = np.where(np.isfinite(yerr), yc + np.abs(yerr), yc)
    else:
        yhi = yc
    m &= np.isfinite(yhi) & (yhi > 0)

    if not np.any(m):
        m = np.isfinite(xc) & np.isfinite(bw) & (bw > 0)
        if not np.any(m):
            xmin = float(x_floor)
            xmax = float(x_ceil) if (x_ceil is not None and np.isfinite(x_ceil) and x_ceil > xmin) else float(xmin + 1.0)
            return xmin, xmax

    xlo = float(np.min(xc[m] - 0.5 * bw[m]))
    xhi = float(np.max(xc[m] + 0.5 * bw[m]))
    if not (np.isfinite(xlo) and np.isfinite(xhi)):
        xmin = float(x_floor)
        xmax = float(x_ceil) if (x_ceil is not None and np.isfinite(x_ceil) and x_ceil > xmin) else float(xmin + 1.0)
        return xmin, xmax

    if xhi <= xlo:
        xhi = xlo + max(float(min_pad_gev), 1.0)

    pad = max(float(min_pad_gev), float(pad_frac) * (xhi - xlo))
    xmin = max(float(x_floor), xlo - pad)
    xmax = xhi + pad
    if x_ceil is not None and np.isfinite(x_ceil) and x_ceil > xmin:
        xmax = min(float(x_ceil), float(xmax))
    if xmax <= xmin:
        xmax = xmin + max(float(min_pad_gev), 1.0)
    return float(xmin), float(xmax)


def _annotate_approx_uncertainty(fig) -> None:
    fig.text(
        0.98, 0.02,
        'uncertainties approximate;\nshared-event R correlations neglected',
        ha='right', va='bottom', fontsize=_FONTS['note'],
        bbox=dict(boxstyle='round,pad=0.25', facecolor='white', alpha=0.85, edgecolor='black')
    )

# ----------------------------- logging -----------------------------------
_LOG_FH = None
def _log(msg: str):
    ts = time.strftime("%F %T")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    if _LOG_FH:
        _LOG_FH.write(line + "\n"); _LOG_FH.flush()

def _canon_cov_mode(raw: str):
    """Return (mode, note). Supported: diag, conservative (aka upperbound).

    This normalization MUST match mjj_comparisor_py.py so fitter and comparisor
    cannot silently disagree about covariance handling.
    """
    m = (raw or "").strip().lower()
    if m in ("diag", "diagonal"):
        return "diag", ""
    if m in ("conservative", "upperbound", "upper-bound", "ub"):
        return "conservative", ""
    raise ValueError(f"Unsupported COVARIANCE_MODE: {raw!r}. Allowed: diagonal | conservative (aliases: upperbound, ub).")

# -------------------------- fit definitions ------------------------------
def gauss_const(x, C, A, mu, sigma):
    return C + A * np.exp(-0.5 * ((x - mu) / sigma) ** 2)

def _sanitize_sigma(Y: np.ndarray, E: np.ndarray) -> np.ndarray:
    """
    Replace non-finite/<=0 sigmas with a small floor so curve_fit doesn't divide by zero.
    Floor choice:
      - If there are positive sigmas: use 5th percentile of positive sigmas, but not below a tiny absolute epsilon.
      - Else: use a small fraction of data scale.
    """
    E = np.array(E, dtype=float, copy=True)

    pos = E[np.isfinite(E) & (E > 0)]
    if pos.size > 0:
        floor = float(np.nanpercentile(pos, 5))
        floor = max(floor, 1e-12)
    else:
        # Fall back to a data-scale floor
        scale = float(np.nanmax(np.abs(Y))) if np.any(np.isfinite(Y)) else 1.0
        floor = max(1e-12, 1e-6 * scale)

    bad = (~np.isfinite(E)) | (E <= 0)
    if np.any(bad):
        E[bad] = floor

    # Final safety: no zeros
    E = np.clip(E, floor, None)
    return E

def fit_gauss_const(xc, yc, ye, x1, x2, *, fix_mu: bool=False):
    # window + finite content
    # Only fit bins with real statistical information (avoid empty bins with err=0).
    msk = (xc >= x1) & (xc <= x2) & np.isfinite(yc) & np.isfinite(ye) & (ye > 0) & (yc >= 0)
    # NOTE: Allow yc==0 bins *if* they carry nonzero uncertainty (ye>0).
    # Excluding yc==0 can bias low-stat tails and fake broadening/quenching signatures.
    n_zero_in_fit = int(((xc >= x1) & (xc <= x2) & np.isfinite(yc) & np.isfinite(ye) & (ye > 0) & (yc == 0)).sum())
    if n_zero_in_fit > 0:
        _log(f"fit_gauss_const: including {n_zero_in_fit} zero-content bins (ye>0) in fit window [{x1:.3g}, {x2:.3g}]")
    X = xc[msk]; Y = yc[msk]; E = ye[msk]

    if X.size < 3:
        raise RuntimeError("Not enough points in window to fit.")

    # sanitize sigma to avoid divide-by-zero / non-finite residuals
    E = _sanitize_sigma(Y, E)

    # drop any remaining non-finite points (paranoid but cheap)
    good = np.isfinite(X) & np.isfinite(Y) & np.isfinite(E)
    X = X[good]; Y = Y[good]; E = E[good]
    if X.size < 3:
        raise RuntimeError("Not enough finite points after sigma sanitation.")

    # robust initial guesses from finite Y
    Yfin = Y[np.isfinite(Y)]
    if Yfin.size == 0:
        raise RuntimeError("No finite Y values in fit window.")
    C0 = float(np.nanmedian(Yfin[:max(2, Yfin.size // 10)])) if Yfin.size > 4 else float(np.nanmin(Yfin))
    if not np.isfinite(C0):
        C0 = float(np.nanmin(Yfin))
    A0 = float(max(np.nanmax(Yfin) - C0, 1e-12))
    mu0 = pi
    sg0 = float(max((x2 - x1) / 6.0, 1e-3))

    if fix_mu:
        # For abs Δφ (0..π) histograms the domain truncates at π, so the fit window is one-sided.
        # Constrain μ=π to reduce boundary/truncation bias; σ is still a meaningful width around π.
        def _model_fixed_mu(x, C, A, sg):
            return gauss_const(x, C, A, mu0, sg)

        p0 = [C0, A0, sg0]
        bounds = ([-np.inf, 0.0, 1e-4], [np.inf, np.inf, (x2 - x1)])
        popt, pcov = curve_fit(_model_fixed_mu, X, Y, p0=p0, sigma=E, absolute_sigma=True, bounds=bounds, maxfev=100000)

        C, A, sg = popt
        mu = mu0
        perr = np.sqrt(np.clip(np.diag(pcov), 0, None)) if pcov is not None else np.array([np.nan]*3)
        C_err, A_err, sg_err = perr
        mu_err = 0.0

        yfit = _model_fixed_mu(X, *popt)
        chi2 = float(np.nansum(((Y - yfit) / E) ** 2))
        ndf  = int(max(0, X.size - len(popt)))
        return C, A, mu, sg, C_err, mu_err, sg_err, chi2, ndf

    # Free-μ fit (unfolded Δφ or if requested)
    p0 = [C0, A0, mu0, sg0]
    bounds = ([-np.inf, 0.0, mu0 - (x2 - x1), 1e-4], [np.inf, np.inf, mu0 + (x2 - x1), (x2 - x1)])

    popt, pcov = curve_fit(gauss_const, X, Y, p0=p0, sigma=E, absolute_sigma=True, bounds=bounds, maxfev=100000)
    C, A, mu, sg = popt
    perr = np.sqrt(np.clip(np.diag(pcov), 0, None)) if pcov is not None else np.array([np.nan]*4)
    C_err, A_err, mu_err, sg_err = perr

    # chi2/ndf
    yfit = gauss_const(X, *popt)
    chi2 = float(np.nansum(((Y - yfit) / E) ** 2))
    ndf  = int(max(0, X.size - len(popt)))

    return C, A, mu, sg, C_err, mu_err, sg_err, chi2, ndf


def fit_gauss_const_cov(xc, yc, cov, x1, x2, *, fix_mu: bool=False):
    """Gaussian+constant fit using a full covariance matrix for the selected bins."""
    xc = np.asarray(xc, dtype=float)
    yc = np.asarray(yc, dtype=float)
    cov = np.asarray(cov, dtype=float)
    if cov.ndim != 2 or cov.shape[0] != cov.shape[1] or cov.shape[0] != xc.size:
        raise RuntimeError(f"fit_gauss_const_cov: covariance shape {cov.shape} does not match x size {xc.size}")

    diag = np.diag(cov)
    msk = (xc >= x1) & (xc <= x2) & np.isfinite(yc) & np.isfinite(diag) & (diag > 0) & (yc >= 0)
    n_zero_in_fit = int(((xc >= x1) & (xc <= x2) & np.isfinite(yc) & np.isfinite(diag) & (diag > 0) & (yc == 0)).sum())
    if n_zero_in_fit > 0:
        _log(f"fit_gauss_const_cov: including {n_zero_in_fit} zero-content bins (positive variance) in fit window [{x1:.3g}, {x2:.3g}]")

    X = xc[msk]
    Y = yc[msk]
    Cov = cov[np.ix_(msk, msk)]
    if X.size < 3:
        raise RuntimeError("Not enough points in window to fit with covariance.")
    if not np.all(np.isfinite(Cov)):
        raise RuntimeError("Non-finite covariance entries in fit window.")

    Cov, nugget = _regularize_covariance_matrix(Cov, label="fit_gauss_const_cov")
    if nugget > 0.0:
        _log(f"fit_gauss_const_cov: added covariance nugget={nugget:.6e} for numerical stability in window [{x1:.3g}, {x2:.3g}]")

    Yfin = Y[np.isfinite(Y)]
    if Yfin.size == 0:
        raise RuntimeError("No finite Y values in fit window.")
    C0 = float(np.nanmedian(Yfin[:max(2, Yfin.size // 10)])) if Yfin.size > 4 else float(np.nanmin(Yfin))
    if not np.isfinite(C0):
        C0 = float(np.nanmin(Yfin))
    A0 = float(max(np.nanmax(Yfin) - C0, 1e-12))
    mu0 = pi
    sg0 = float(max((x2 - x1) / 6.0, 1e-3))

    if fix_mu:
        def _model_fixed_mu(x, C, A, sg):
            return gauss_const(x, C, A, mu0, sg)

        p0 = [C0, A0, sg0]
        bounds = ([-np.inf, 0.0, 1e-4], [np.inf, np.inf, (x2 - x1)])
        popt, pcov = curve_fit(_model_fixed_mu, X, Y, p0=p0, sigma=Cov, absolute_sigma=True, bounds=bounds, maxfev=100000)
        C, A, sg = popt
        mu = mu0
        perr = np.sqrt(np.clip(np.diag(pcov), 0, None)) if pcov is not None else np.array([np.nan]*3)
        C_err, A_err, sg_err = perr
        mu_err = 0.0
        yfit = _model_fixed_mu(X, *popt)
        chi2 = _chi2_with_covariance(Y - yfit, Cov)
        ndf = int(max(0, X.size - len(popt)))
        return C, A, mu, sg, C_err, mu_err, sg_err, chi2, ndf

    p0 = [C0, A0, mu0, sg0]
    bounds = ([-np.inf, 0.0, mu0 - (x2 - x1), 1e-4], [np.inf, np.inf, mu0 + (x2 - x1), (x2 - x1)])
    popt, pcov = curve_fit(gauss_const, X, Y, p0=p0, sigma=Cov, absolute_sigma=True, bounds=bounds, maxfev=100000)
    C, A, mu, sg = popt
    perr = np.sqrt(np.clip(np.diag(pcov), 0, None)) if pcov is not None else np.array([np.nan]*4)
    C_err, A_err, mu_err, sg_err = perr
    yfit = gauss_const(X, *popt)
    chi2 = _chi2_with_covariance(Y - yfit, Cov)
    ndf = int(max(0, X.size - len(popt)))
    return C, A, mu, sg, C_err, mu_err, sg_err, chi2, ndf

# -------------------------- ROOT histogram IO ----------------------------
def _iter_root_objects(root_path: str):
    """Yield ROOT objects recursively with normalized leaf names and nosubfrac directory flags."""
    diag = {"path_stripped": 0, "samples": []}
    with uproot.open(root_path) as f:
        def _walk(dir_obj, path_prefix: str=""):
            for name, obj in dir_obj.items():
                key = name.split(";")[0]
                key_leaf = key.split("/")[-1]
                if key_leaf != key:
                    diag["path_stripped"] += 1
                    if len(diag["samples"]) < 8:
                        diag["samples"].append(f"{key} -> {key_leaf}")
                try:
                    cls = getattr(obj, "classname", "")
                except Exception:
                    cls = ""
                if not isinstance(cls, str):
                    try:
                        cls = str(cls)
                    except Exception:
                        cls = ""
                if cls.startswith("TDirectory"):
                    sub_prefix = f"{path_prefix}{key_leaf}/"
                    try:
                        yield from _walk(obj, sub_prefix)
                    except Exception as e:
                        _log(f"[WARN] Failed to walk directory '{sub_prefix}' in {root_path}: {e}")
                    continue
                comps = [c for c in path_prefix.strip("/").split("/") if c]
                in_ns_dir = any(c == "nosubfrac" for c in comps)
                yield (key_leaf, obj, cls, bool(in_ns_dir))

        yield from _walk(f)

    if diag["path_stripped"] > 0:
        _log(f"[DEBUG] ROOT key normalization: stripped path prefixes from {diag['path_stripped']} histogram keys while reading {root_path}")
        for s in diag["samples"]:
            _log(f"[DEBUG]   key path sample: {s}")


def read_root_histograms(root_path: str):
    """Yield TH1 objects as (name, centers, contents, errors, widths, variances, entries, in_nosubfrac_dir)."""
    for key_leaf, obj, cls, in_ns_dir in _iter_root_objects(root_path):
        if not cls.startswith("TH1"):
            continue
        try:
            edges = obj.axes[0].edges()
            centers = 0.5 * (edges[:-1] + edges[1:])
            vals = obj.values(flow=False)
            variances = obj.variances(flow=False)
            if variances is None:
                raise RuntimeError(
                    f"Histogram '{key_leaf}' in {root_path} has no stored variances (Sumw2 missing). "
                    f"Re-run analysis with analyze_dphi_sliced.cpp v6.2+ (TH1::SetDefaultSumw2(true))."
                )
            errs = np.sqrt(np.clip(np.asarray(variances, dtype=float), 0, None))
            widths = edges[1:] - edges[:-1]
            try:
                entries = float(obj.member("fEntries"))
            except Exception:
                entries = float("nan")
            yield (key_leaf,
                   centers.astype(float),
                   np.asarray(vals, dtype=float),
                   errs.astype(float),
                   widths.astype(float),
                   np.asarray(variances, dtype=float),
                   entries,
                   bool(in_ns_dir))
        except RuntimeError:
            raise
        except Exception as e:
            _log(f"[WARN] Skipping object '{key_leaf}': {e}")


def read_root_profiles(root_path: str):
    """Yield TProfile objects as (name, centers, means, errors, widths, variances, entries, in_nosubfrac_dir)."""
    for key_leaf, obj, cls, in_ns_dir in _iter_root_objects(root_path):
        if not cls.startswith("TProfile"):
            continue
        try:
            edges = obj.axes[0].edges()
            centers = 0.5 * (edges[:-1] + edges[1:])
            vals = obj.values(flow=False)
            errs = obj.errors(flow=False)
            variances = obj.variances(flow=False)
            widths = edges[1:] - edges[:-1]
            try:
                entries = float(obj.member("fEntries"))
            except Exception:
                entries = float("nan")
            yield (key_leaf,
                   centers.astype(float),
                   np.asarray(vals, dtype=float),
                   np.asarray(errs, dtype=float),
                   widths.astype(float),
                   np.asarray(variances, dtype=float),
                   entries,
                   bool(in_ns_dir))
        except Exception as e:
            _log(f"[WARN] Skipping TProfile '{key_leaf}': {e}")


def read_root_th2(root_path: str):
    """Yield TH2 objects as (name, xedges, yedges, values, errors, variances, entries, in_nosubfrac_dir)."""
    for key_leaf, obj, cls, in_ns_dir in _iter_root_objects(root_path):
        if not cls.startswith("TH2"):
            continue
        try:
            xedges = obj.axes[0].edges()
            yedges = obj.axes[1].edges()
            vals = obj.values(flow=False)
            variances = obj.variances(flow=False)
            if variances is None:
                raise RuntimeError(
                    f"TH2 '{key_leaf}' in {root_path} has no stored variances (Sumw2 missing). "
                    f"Re-run analysis with analyze_dphi_sliced.cpp v6.2+ (TH1::SetDefaultSumw2(true))."
                )
            errs = np.sqrt(np.clip(np.asarray(variances, dtype=float), 0, None))
            try:
                entries = float(obj.member("fEntries"))
            except Exception:
                entries = float("nan")
            yield (key_leaf,
                   np.asarray(xedges, dtype=float),
                   np.asarray(yedges, dtype=float),
                   np.asarray(vals, dtype=float),
                   errs.astype(float),
                   np.asarray(variances, dtype=float),
                   entries,
                   bool(in_ns_dir))
        except RuntimeError:
            raise
        except Exception as e:
            _log(f"[WARN] Skipping TH2 '{key_leaf}': {e}")


# -------------------------- robust R tag decoding --------------------------
# Older analyzers wrote R tags as round(R*1000) (e.g. R=0.2 → "R200"), while the
# current convention is round(R*100) with zero padding (e.g. "R020").
# We support BOTH so multi-R plots don't silently break when mixing runs.
_DECODE_R_KNOWN = []   # populated in main() from COMBINE_R_LIST / JET_RADIUS_LIST when available
_DECODE_R_WARNED = False

def _set_decode_r_known(rs):
    global _DECODE_R_KNOWN
    try:
        vals = []
        for r in (rs or []):
            try:
                vals.append(round(float(r), 4))
            except Exception:
                pass
        _DECODE_R_KNOWN = sorted(set(vals))
    except Exception:
        _DECODE_R_KNOWN = []

def _decode_r_tag(tag_str: str) -> float:
    # Decode an integer R tag into a float jet radius, supporting /100 and legacy /1000.
    global _DECODE_R_WARNED
    try:
        itag = int(tag_str)
    except Exception:
        return float("nan")

    r100  = itag / 100.0
    r1000 = itag / 1000.0

    def plausible(r):
        return np.isfinite(r) and (r >= 0.05) and (r <= 1.5)

    cands = []
    if plausible(r100):
        cands.append((r100, 100.0))
    if plausible(r1000):
        cands.append((r1000, 1000.0))

    if not cands:
        if r100 <= 1.5:
            return r100
        return r1000

    if len(cands) == 1:
        r, sc = cands[0]
        if sc == 1000.0 and not _DECODE_R_WARNED:
            _log("[WARN] Detected legacy jet-R tags (R*1000) in histogram names; decoding with /1000 where appropriate.")
            _DECODE_R_WARNED = True
        return r

    if _DECODE_R_KNOWN:
        def score(r):
            return min(abs(r - k) for k in _DECODE_R_KNOWN) if _DECODE_R_KNOWN else 1e9
        cands_sorted = sorted(cands, key=lambda t: (score(t[0]), 0 if t[1] == 100.0 else 1))
        r, sc = cands_sorted[0]
    else:
        r, sc = (r1000, 1000.0) if r100 > 1.5 else (r100, 100.0)

    if sc == 1000.0 and not _DECODE_R_WARNED:
        _log("[WARN] Detected legacy jet-R tags (R*1000) in histogram names; decoding with /1000 where appropriate.")
        _DECODE_R_WARNED = True
    return r

# ------------------------------- name parsers -------------------------------
_re_dphi      = re.compile(r"^dphi(?:_R(?P<R>\d{2,4}))?_(?:(?P<lo>\d+)_(?P<hi>\d+)(?P<full>_fullrange)?|all)(?P<ns>_nosubfrac)?$")
_re_dphi_abs  = re.compile(r"^dphi_abs(?:_R(?P<R>\d{2,4}))?_(?:(?P<lo>\d+)_(?P<hi>\d+)(?P<full>_fullrange)?|all)(?P<ns>_nosubfrac)?$")
_re_eta  = re.compile(r"^(?P<kind>eta|y)_(?P<lead>(lead|sub|sublead))_R(?P<R>\d{2,4})_(?:(?P<lo>\d+)_(?P<hi>\d+)_fullrange|all)(?P<ns>_nosubfrac)?$")
_re_eta_legacy = re.compile(r"^(?P<kind>eta|y)_(?P<lead>(lead|sublead))_all(?P<ns>_nosubfrac)?$")
_re_mjj_all = re.compile(r"^mjj_R(?P<R>\d{2,4})_(?:(?P<lo>\d+)_(?P<hi>\d+)_fullrange|all)(?P<ns>_nosubfrac)?$")
_re_mjj_pt  = re.compile(r"^mjj_R(?P<R>\d{2,4})_(?P<lo>\d+)_(?P<hi>\d+)(?P<ns>_nosubfrac)?$")

_re_xj  = re.compile(r"^xj_R(?P<R>\d{2,4})_(?:(?P<lo>\d+)_(?P<hi>\d+)(?P<full>_fullrange)?|all)(?P<ns>_nosubfrac)?$")
_re_aj  = re.compile(r"^aj_R(?P<R>\d{2,4})_(?:(?P<lo>\d+)_(?P<hi>\d+)(?P<full>_fullrange)?|all)(?P<ns>_nosubfrac)?$")
_re_jetpt = re.compile(r"^jetpt_(?P<kind>lead|sublead|incl)_R(?P<R>\d{2,4})_(?:(?P<lo>\d+)_(?P<hi>\d+)_fullrange|all)(?P<ns>_nosubfrac)?$")
_re_particle = re.compile(r"^particle_(?P<kind>pt|eta|phi)_all$")
_re_sublead_vs_lead_h2 = re.compile(r"^h2_sublead_vs_lead_R(?P<R>\d{2,4})_(?:(?P<lo>\d+)_(?P<hi>\d+)_fullrange|all)(?P<ns>_nosubfrac)?$")
_re_sublead_vs_lead_prof = re.compile(r"^prof_sublead_vs_lead_R(?P<R>\d{2,4})_(?:(?P<lo>\d+)_(?P<hi>\d+)_fullrange_)?ptleadbins(?P<ns>_nosubfrac)?$")

def _m_has_ns(m) -> bool:
    try:
        return (m is not None) and (m.group('ns') is not None)
    except Exception:
        return False


def parse_xj_name(hn):
    m = _re_xj.match(hn)
    if not m:
        return None
    lo = m.group('lo')
    hi = m.group('hi')
    is_full = (m.groupdict().get('full') is not None) or (lo is None or hi is None)
    return (_decode_r_tag(m.group('R')), _m_has_ns(m), (float(lo) if lo is not None else float('nan')), (float(hi) if hi is not None else float('nan')), bool(is_full))

def parse_aj_name(hn):
    m = _re_aj.match(hn)
    if not m:
        return None
    lo = m.group('lo')
    hi = m.group('hi')
    is_full = (m.groupdict().get('full') is not None) or (lo is None or hi is None)
    return (_decode_r_tag(m.group('R')), _m_has_ns(m), (float(lo) if lo is not None else float('nan')), (float(hi) if hi is not None else float('nan')), bool(is_full))

def parse_jetpt_name(hn):
    m = _re_jetpt.match(hn)
    if not m:
        return None
    return (m.group('kind'), _decode_r_tag(m.group('R')), _m_has_ns(m))


def parse_particle_name(hn):
    m = _re_particle.match(hn)
    if not m:
        return None
    return m.group('kind')


def parse_sublead_vs_lead_h2_name(hn):
    m = _re_sublead_vs_lead_h2.match(hn)
    if not m:
        return None
    return (_decode_r_tag(m.group('R')), _m_has_ns(m))


def parse_sublead_vs_lead_profile_name(hn):
    m = _re_sublead_vs_lead_prof.match(hn)
    if not m:
        return None
    return (_decode_r_tag(m.group('R')), _m_has_ns(m))


def parse_dphi_name(hn):
    """Parse Δφ histogram names.

    Supported:
      - oriented Δφ in [0,2π):   dphi[_Rxxx]_(lo_hi|<lo>_<hi>_fullrange|all)
      - absolute Δφ in [0,π]:    dphi_abs[_Rxxx]_(lo_hi|<lo>_<hi>_fullrange|all)

    Returns (R, ptlo, pthi, is_abs). Full-range histograms return NaN pt edges so the
    rest of the fitter treats them as inclusive over the configured PT_LEAD_BIN_EDGES span.
    """
    m = _re_dphi_abs.match(hn)
    if m:
        is_abs = True
    else:
        m = _re_dphi.match(hn)
        if not m:
            return None
        is_abs = False

    R = m.group('R')
    lo = m.group('lo')
    hi = m.group('hi')

    # Support both per-bin names and full-range/legacy all names.
    if lo is None or hi is None or m.groupdict().get('full') is not None:
        return (None if R is None else _decode_r_tag(R), float('nan'), float('nan'), is_abs)
    return (None if R is None else _decode_r_tag(R), float(lo), float(hi), is_abs)


def parse_eta_name(hn):
    m = _re_eta.match(hn)
    if m:
        lead_tag = m.group("lead")
        return (m.group("kind"), True if lead_tag=="lead" else False, _decode_r_tag(m.group("R")))
    m = _re_eta_legacy.match(hn)
    if m:
        return (m.group("kind"), True if m.group("lead")=="lead" else False, float("nan"))
    return None

def parse_mjj_name(hn):
    m = _re_mjj_all.match(hn)
    if m:
        lo = m.group("lo")
        hi = m.group("hi")
        return (_decode_r_tag(m.group("R")), (float(lo) if lo is not None else float('nan')), (float(hi) if hi is not None else float('nan')), True)
    m = _re_mjj_pt.match(hn)
    if m:
        return (_decode_r_tag(m.group("R")), float(m.group("lo")), float(m.group("hi")), False)
    return None

# ---------------------- η adaptive rebin (density-aware) -----------------
def _rebin_effective_stats_density(centers, values, errors, widths, variances=None, neff_min=200):
    """
    Merge neighbors until each merged bin has effective stats >= neff_min.
    Use counts s = y*Δx and var_s = (σ_y*Δx)^2 (or variances*Δx^2 when available).
    Output merged density y' = (∑ s)/Δx', σ_y' = sqrt(∑ var_s)/Δx'.
    """
    n = len(centers)
    if n == 0:
        return centers, values, errors, widths
    left = 0
    edges = np.concatenate([centers - widths/2.0, [centers[-1] + widths[-1]/2.0]])
    out_c, out_y, out_e, out_w = [], [], [], []
    acc_s = 0.0
    acc_var_s = 0.0
    while left < n:
        acc_s = 0.0
        acc_var_s = 0.0
        right = left
        while right < n:
            dx = widths[right]
            s = values[right] * dx
            if variances is not None:
                var_y = max(0.0, variances[right])
                var_s = var_y * dx * dx
            else:
                var_s = (errors[right] * dx) ** 2
            acc_s += s
            acc_var_s += var_s
            neff = (acc_s * acc_s / acc_var_s) if acc_var_s > 0 else float('inf')
            right += 1
            if neff >= neff_min or right == n:
                break
        xL = edges[left]
        xR = edges[right]
        dx_tot = xR - xL
        y_prime = acc_s / dx_tot if dx_tot > 0 else 0.0
        e_prime = math.sqrt(max(0.0, acc_var_s)) / dx_tot if dx_tot > 0 else 0.0
        c_prime = 0.5 * (xL + xR)
        out_c.append(c_prime); out_y.append(y_prime); out_e.append(e_prime); out_w.append(dx_tot)
        left = right
    return np.array(out_c), np.array(out_y), np.array(out_e), np.array(out_w)


def apply_plot_style(cfg: dict) -> dict:
    """Apply matplotlib font/style knobs from jetscape.ini.

    Returns a dict with resolved font sizes for local calls that pass explicit fontsize=... .
    """
    import matplotlib as mpl

    def _f(key, default):
        raw = cfg.get(key, default)
        try:
            val = float(raw)
        except Exception:
            _log(f"[WARN] Invalid {key}={raw!r}; using default {float(default):g}")
            return float(default)
        if not np.isfinite(val) or val <= 0.0:
            _log(f"[WARN] Non-positive/non-finite {key}={raw!r}; using default {float(default):g}")
            return float(default)
        return float(val)

    family = str(cfg.get('PLOT_FONT_FAMILY', 'sans-serif')).strip() or 'sans-serif'
    sizes = {
        'base': _f('PLOT_BASE_FONTSIZE', 12),
        'title': _f('PLOT_TITLE_FONTSIZE', 14),
        'suptitle': _f('PLOT_SUPTITLE_FONTSIZE', 16),
        'label': _f('PLOT_LABEL_FONTSIZE', 12),
        'tick': _f('PLOT_TICK_FONTSIZE', 11),
        'legend': _f('PLOT_LEGEND_FONTSIZE', 11),
        'note': _f('PLOT_NOTE_FONTSIZE', 10),
    }
    mpl.rcParams.update({
        'font.family': family,
        'font.size': sizes['base'],
        'axes.titlesize': sizes['title'],
        'axes.labelsize': sizes['label'],
        'xtick.labelsize': sizes['tick'],
        'ytick.labelsize': sizes['tick'],
        'legend.fontsize': sizes['legend'],
        'figure.titlesize': sizes['suptitle'],
    })
    _log(
        "[INFO] Plot font style resolved: "
        + f"family={family!r}, base={sizes['base']}, title={sizes['title']}, "
        + f"suptitle={sizes['suptitle']}, label={sizes['label']}, tick={sizes['tick']}, "
        + f"legend={sizes['legend']}, note={sizes['note']}"
    )
    return sizes

# ------------------------------- main ------------------------------------
def main():
    ini_path = os.environ.get("XSCAPE_INI") or os.environ.get("JETSCAPE_INI") or (sys.argv[1] if len(sys.argv)>1 else "jetscape.ini")
    ini = read_ini(ini_path)
    cfg = ini.kv

    global INCLUDE_XSEC_NORM_ERR, PERDIJET_COV_MODE, SINGLE_SLICE_MODE, JET_RADIUS_LIST_CFG, JET_RADIUS_COMPARE_PAIRS, SELECTED_DIJET_COUNTS

    # Plot styling knobs (optional) from jetscape.ini
    global _FONTS
    _FONTS = apply_plot_style(cfg)


    # Resolve basic paths (supports ${VAR} expansion against ini + env).
    RUN_TAG = cfg.get("RUN_TAG", "run")
    RUNS_BASE = expand_vars(cfg.get("RUNS_BASE", ""), cfg=cfg) if cfg.get("RUNS_BASE") else ""
    DIR_FINAL = expand_vars(cfg.get("DIR_FINAL", ""), cfg=cfg) if cfg.get("DIR_FINAL") else ""
    PLOTS_SUBDIR = cfg.get("PLOTS_SUBDIR", "plots")

    if not DIR_FINAL:
        # Best-effort fallback (keeps old behavior).
        if RUNS_BASE:
            DIR_FINAL = os.path.join(RUNS_BASE, "final")
        else:
            DIR_FINAL = os.path.join(os.getcwd(), "final")

    ensure_dir(DIR_FINAL)

    # logging: open early so ALL messages land in the log (not just stdout).
    global _LOG_FH
    log_path = os.path.join(DIR_FINAL, "fit_py.log")
    _LOG_FH = open(log_path, "a")

    _log(f"dphi_fit_py.py v{__version__}")
    _log(f"PWD={os.getcwd()}")
    _log(f"INI={ini_path}")
    _log(f"INI_KEYS={len(cfg)}")
    _log(f"RUN_TAG={RUN_TAG}")
    _log(f"DIR_FINAL={DIR_FINAL}")

    # --- strict required configuration (no hidden defaults for fit/physics knobs) ---
    def _fatal(msg: str) -> None:
        _log(f"[cfg][FATAL] {msg}")
        raise SystemExit(2)

    def _require(key: str) -> str:
        v = cfg.get(key, None)
        if v is None or str(v).strip() == "":
            _fatal(f"Missing required key {key} in {ini_path}. Add it to jetscape.ini.")
        return str(v)


    # --- input ROOT selection (must match merger output by default) ---
    # Default: merger produces ${DIR_FINAL}/dphi_allSlices.root, and comparisor expects the same.
    # You MAY override via jetscape.ini: INPUT_ROOT=/path/to/some.root (vars expanded).
    INPUT_ROOT = expand_vars(cfg.get("INPUT_ROOT", ""), cfg=cfg) if cfg.get("INPUT_ROOT") else os.path.join(DIR_FINAL, "dphi_allSlices.root")
    _log(f"INPUT_ROOT={INPUT_ROOT}")
    if not os.path.isfile(INPUT_ROOT):
        _fatal(f"INPUT_ROOT not found: {INPUT_ROOT}. Run merger.sh successfully (expected dphi_allSlices.root in DIR_FINAL) or set INPUT_ROOT in {ini_path}.")

    # These keys used to have silent defaults or could be missing without stopping the run.
    _required_keys = [
        "JET_RADIUS", "PARTICLE_ETA_MAX", "JET_ETA_MAX", "JET_ETA_MODE",
        "PT_LEAD_BIN_EDGES", "DPHI_NBINS", "JET_PT_MAX",
        "DIJET_BACKTOBACK_TOL_DEG", "FIT_WIN_DEG",
        "DIJET_REQUIRE_EXACTLY_TWO_JETS", "YSTAR_ENABLE", "YSTAR_MAX",
        "THETA_SCAN_MAX_DEG", "THETA_SCAN_STEP_DEG",
        "TOL_FRACS",
        "INCLUDE_XSEC_NORM_ERR",
        "COVARIANCE_MODE",
        "WIDTH_WEIGHTING",
    ]
    missing = [k for k in _required_keys if (cfg.get(k, None) is None or str(cfg.get(k)).strip() == "")]
    if missing:
        _fatal(f"Missing required jetscape.ini key(s): {missing}. Add them to {ini_path} to run the fitter reproducibly.")

    try:
        SINGLE_SLICE_MODE = bool(parse_bool(cfg.get("SINGLE_SLICE_MODE"), default=False))
    except Exception as e:
        _fatal(f"Invalid SINGLE_SLICE_MODE={cfg.get('SINGLE_SLICE_MODE')!r}: {e}")
    _log(f"[cfg] SINGLE_SLICE_MODE={1 if SINGLE_SLICE_MODE else 0}")
    _log("[cfg] JETPT_PLOT_XMODE=auto_populated_range")

    # Jet acceptance knobs are used for η guide lines and to match the analyzer acceptance scheme.
    try:
        R_cfg = float(_require("JET_RADIUS"))
        particleEtaMax_cfg = float(_require("PARTICLE_ETA_MAX"))
        jetEtaMax_cfg = float(_require("JET_ETA_MAX"))
        jetEtaMode_cfg = int(float(_require("JET_ETA_MODE")))
        JET_PT_MAX = float(_require("JET_PT_MAX"))
    except Exception as e:
        _fatal(f"Invalid jet acceptance/jet-spectrum config (JET_RADIUS/PARTICLE_ETA_MAX/JET_ETA_MAX/JET_ETA_MODE/JET_PT_MAX): {e}")
    _log(f"[cfg] JET_PT_MAX={JET_PT_MAX}")


    # --- reproducibility knobs (ini-first, env override) ---
    try:
        inc_ini = parse_bool(_require("INCLUDE_XSEC_NORM_ERR"), default=False)
    except Exception as e:
        _fatal(f"Invalid INCLUDE_XSEC_NORM_ERR={cfg.get('INCLUDE_XSEC_NORM_ERR')!r}: {e}")
    inc_env = os.environ.get("INCLUDE_XSEC_NORM_ERR")
    if inc_env is not None:
        try:
            INCLUDE_XSEC_NORM_ERR = 1 if parse_bool(inc_env, default=bool(inc_ini)) else 0
        except Exception as e:
            _fatal(f"Invalid INCLUDE_XSEC_NORM_ERR env override {inc_env!r}: {e}")
        _log(f"[cfg] INCLUDE_XSEC_NORM_ERR env override: {inc_env} -> {INCLUDE_XSEC_NORM_ERR}")
    else:
        INCLUDE_XSEC_NORM_ERR = 1 if inc_ini else 0
        _log(f"[cfg] INCLUDE_XSEC_NORM_ERR (ini): {INCLUDE_XSEC_NORM_ERR}")

    # (C) Covariance mode for shape uncertainties (ini required; env override allowed)
    ini_cov_raw = _require("COVARIANCE_MODE").strip()
    ini_legacy = (cfg.get("PERDIJET_COV_MODE") or "").strip()

    # If legacy key is present and disagrees, hard fail (prevents silent mismatches)
    if ini_legacy and (ini_legacy.strip().lower() != ini_cov_raw.strip().lower()):
        _fatal(f"jetscape.ini sets both COVARIANCE_MODE={ini_cov_raw!r} and PERDIJET_COV_MODE={ini_legacy!r} (disagree). "
               f"Use only COVARIANCE_MODE (PERDIJET_COV_MODE is legacy).")
    if ini_legacy:
        _log(f"[cfg] PERDIJET_COV_MODE present but matches COVARIANCE_MODE; legacy key will be ignored.")

    # Env overrides (kept only for convenience, but logged loudly). Canonical key wins.
    env_cov = os.environ.get("COVARIANCE_MODE")
    env_legacy = os.environ.get("PERDIJET_COV_MODE")

    if env_cov and env_legacy and (env_cov.strip().lower() != env_legacy.strip().lower()):
        _fatal(f"Environment sets both COVARIANCE_MODE={env_cov!r} and PERDIJET_COV_MODE={env_legacy!r} (disagree). "
               f"Set only COVARIANCE_MODE (PERDIJET_COV_MODE is legacy).")

    if env_cov or env_legacy:
        env_key_used = "COVARIANCE_MODE" if env_cov else "PERDIJET_COV_MODE"
        cov_raw = ((env_cov or env_legacy) or "").strip()
        try:
            cov_mode, cov_note = _canon_cov_mode(cov_raw)
        except Exception as e:
            _fatal(f"Invalid covariance mode from env {env_key_used}={cov_raw!r}: {e}")
        _log(f"[cfg] Covariance mode resolved: raw={cov_raw!r} -> mode={cov_mode!r} (from env {env_key_used}; ini COVARIANCE_MODE={ini_cov_raw!r})")
    else:
        cov_raw = ini_cov_raw.strip()
        try:
            cov_mode, cov_note = _canon_cov_mode(cov_raw)
        except Exception as e:
            _fatal(f"Invalid covariance mode from ini COVARIANCE_MODE={ini_cov_raw!r}: {e}")
        _log(f"[cfg] Covariance mode resolved: raw={cov_raw!r} -> mode={cov_mode!r} (from ini COVARIANCE_MODE={ini_cov_raw!r})")

    # Apply the resolved mode globally (used by per-dijet normalization)
    PERDIJET_COV_MODE = cov_mode
    if PERDIJET_COV_MODE == "diag":
        _log("[cfg] Normalized Δφ shape fits will use a full propagated covariance matrix built from the current histogram bin errors under the independent raw-bin approximation.")
    else:
        _log("[cfg] Normalized Δφ shape fits will fall back to diagonal-only fitting because conservative mode does not define a trustworthy off-diagonal covariance matrix without upstream replicas.")

    try:
        pt_edges = parse_list(_require("PT_LEAD_BIN_EDGES"))
    except Exception as e:
        _fatal(f"Invalid PT_LEAD_BIN_EDGES={cfg.get('PT_LEAD_BIN_EDGES')!r}: {e}")
    if len(pt_edges) < 2:
        _fatal(f"PT_LEAD_BIN_EDGES must have at least 2 entries; got {pt_edges}")

    try:
        dphi_nbins = int(float(_require("DPHI_NBINS")))
    except Exception as e:
        _fatal(f"Invalid DPHI_NBINS={cfg.get('DPHI_NBINS')!r}: {e}")
    if dphi_nbins <= 0:
        _fatal(f"DPHI_NBINS must be > 0; got {dphi_nbins}")

    mjj_min_cfg = float(cfg.get("MJJ_MIN_GEV", "0"))
    mjj_max_cfg = float(cfg.get("MJJ_MAX_GEV", "3000"))
    try:
        combine_R_list = parse_list(_require("COMBINE_R_LIST"))
    except Exception as e:
        _fatal(f"Invalid or missing COMBINE_R_LIST in jetscape.ini: {e}")
    if not combine_R_list:
        _fatal("COMBINE_R_LIST is required and must be non-empty (example: COMBINE_R_LIST=(0.2 0.4 0.5)).")
    _log(f"[cfg] COMBINE_R_LIST={combine_R_list}")

    # Help robust R-tag decoding choose the right convention when mixing legacy/new analyzers.
    jet_radius_list = parse_list(cfg.get("JET_RADIUS_LIST", cfg.get("JET_R_LIST", "")))
    if not jet_radius_list and cfg.get("JET_RADIUS") is not None:
        try:
            jet_radius_list = [float(cfg.get("JET_RADIUS"))]
        except Exception:
            jet_radius_list = []
    _set_decode_r_known(list(combine_R_list) + list(jet_radius_list))
    try:
        _log(f"[cfg] R-tag decode known radii = {sorted(set([round(float(r),4) for r in (combine_R_list + jet_radius_list)]))}")
    except Exception:
        pass

    JET_RADIUS_LIST_CFG = list(jet_radius_list)
    _seen_compare_r = set()
    JET_RADIUS_COMPARE_PAIRS = []
    if len(JET_RADIUS_LIST_CFG) >= 2:
        r0 = float(JET_RADIUS_LIST_CFG[0])
        for r_other in JET_RADIUS_LIST_CFG[1:]:
            pair = (r0, float(r_other))
            pair_key = (round(pair[0], 6), round(pair[1], 6))
            if pair_key in _seen_compare_r:
                continue
            _seen_compare_r.add(pair_key)
            JET_RADIUS_COMPARE_PAIRS.append(pair)
    _log(f"[cfg] JET_RADIUS_COMPARE_PAIRS={JET_RADIUS_COMPARE_PAIRS}")

    if SINGLE_SLICE_MODE:
        try:
            pt_lo_cfg = parse_list(_require("PT_LO"))
            pt_hi_cfg = parse_list(_require("PT_HI"))
        except Exception as e:
            _fatal(f"SINGLE_SLICE_MODE=1 requires valid PT_LO/PT_HI arrays in {ini_path}: {e}")
        if len(pt_lo_cfg) != 1 or len(pt_hi_cfg) != 1:
            _fatal(f"SINGLE_SLICE_MODE=1 requires exactly one configured pThat slice; got PT_LO={pt_lo_cfg} PT_HI={pt_hi_cfg}")
        try:
            SELECTED_DIJET_COUNTS, counts_path = SelectedDijetCountResolver.load(DIR_FINAL, JET_RADIUS_LIST_CFG, pt_edges)
        except Exception as e:
            _fatal(f"Failed to load single-slice selected dijet counts: {e}")
        _log(f"[cfg] SINGLE_SLICE_MODE enabled; using selected dijet counts from {counts_path}")
        _log(f"[cfg] selected dijet count semantics: {SELECTED_DIJET_COUNTS.count_semantics}")
    else:
        SELECTED_DIJET_COUNTS = None


    raw_mjj_req = str(_require("MJJ_REQUIRE_BACKTOBACK")).strip()
    try:
        mjj_require_backtoback = int(float(raw_mjj_req))
    except Exception as e:
        _fatal(f"Invalid MJJ_REQUIRE_BACKTOBACK={cfg.get('MJJ_REQUIRE_BACKTOBACK')!r}: {e}")
    if mjj_require_backtoback not in (0, 1):
        _fatal(f"MJJ_REQUIRE_BACKTOBACK must be 0 or 1; got {mjj_require_backtoback}")
    try:
        bb_tol_deg = float(_require("DIJET_BACKTOBACK_TOL_DEG"))
    except Exception as e:
        _fatal(f"Invalid DIJET_BACKTOBACK_TOL_DEG={cfg.get('DIJET_BACKTOBACK_TOL_DEG')!r}: {e}")
    try:
        imbalance_require_backtoback = int(float(_require("IMBALANCE_REQUIRE_BACKTOBACK")))
    except Exception as e:
        _fatal(f"Invalid IMBALANCE_REQUIRE_BACKTOBACK={cfg.get('IMBALANCE_REQUIRE_BACKTOBACK')!r}: {e}")
    if imbalance_require_backtoback not in (0, 1):
        _fatal(f"IMBALANCE_REQUIRE_BACKTOBACK must be 0 or 1; got {imbalance_require_backtoback}")
    try:
        imbalance_bb_tol_deg = float(_require("IMBALANCE_BACKTOBACK_TOL_DEG"))
    except Exception as e:
        _fatal(f"Invalid IMBALANCE_BACKTOBACK_TOL_DEG={cfg.get('IMBALANCE_BACKTOBACK_TOL_DEG')!r}: {e}")
    if not np.isfinite(imbalance_bb_tol_deg) or imbalance_bb_tol_deg <= 0.0 or imbalance_bb_tol_deg > 180.0:
        _fatal(f"IMBALANCE_BACKTOBACK_TOL_DEG must be finite and in (0, 180]; got {imbalance_bb_tol_deg}")
    try:
        fit_win_scalar = float(_require("FIT_WIN_DEG"))
    except Exception as e:
        _fatal(f"Invalid FIT_WIN_DEG={cfg.get('FIT_WIN_DEG')!r}: {e}")
    use_array_win = 1
    win_per = parse_list(cfg.get("FIT_WIN_PER_BIN_DEG", ""))
    if not win_per:
        use_array_win = 0

    try:
        dijet_require_exactly_two = int(float(_require("DIJET_REQUIRE_EXACTLY_TWO_JETS")))
    except Exception as e:
        _fatal(f"Invalid DIJET_REQUIRE_EXACTLY_TWO_JETS={cfg.get('DIJET_REQUIRE_EXACTLY_TWO_JETS')!r}: {e}")
    if dijet_require_exactly_two not in (0, 1):
        _fatal(f"DIJET_REQUIRE_EXACTLY_TWO_JETS must be 0 or 1; got {dijet_require_exactly_two}")
    try:
        ystar_enable = int(float(_require("YSTAR_ENABLE")))
    except Exception as e:
        _fatal(f"Invalid YSTAR_ENABLE={cfg.get('YSTAR_ENABLE')!r}: {e}")
    if ystar_enable not in (0, 1):
        _fatal(f"YSTAR_ENABLE must be 0 or 1; got {ystar_enable}")
    try:
        ystar_max = float(_require("YSTAR_MAX"))
    except Exception as e:
        _fatal(f"Invalid YSTAR_MAX={cfg.get('YSTAR_MAX')!r}: {e}")
    ystar_title_suffix = f"; |y*|<{ystar_max:.1f}" if ystar_enable == 1 else ""
    _log(f"[cfg] JET_RADIUS={R_cfg}")
    _log(f"[cfg] PARTICLE_ETA_MAX={particleEtaMax_cfg}")
    _log(f"[cfg] JET_ETA_MAX={jetEtaMax_cfg}  JET_ETA_MODE={jetEtaMode_cfg}")
    _log(f"[cfg] PT_LEAD_BIN_EDGES={pt_edges}")

    # Match mjj_comparisor_py.py: label inclusive lead-pT as a numeric range when possible.
    global PT_LEAD_BIN_EDGES, PT_ALL_LABEL
    PT_LEAD_BIN_EDGES = list(pt_edges)
    if len(pt_edges) >= 2 and all([np.isfinite(x) for x in pt_edges]):
        PT_ALL_LABEL = f"{pt_edges[0]:g}–{pt_edges[-1]:g} GeV"
    else:
        PT_ALL_LABEL = "all"
    _log(f"[cfg] PT_ALL_LABEL={PT_ALL_LABEL}")

    _log(f"[cfg] DPHI_NBINS={dphi_nbins}")
    _log(f"[cfg] MJJ_MIN_GEV={mjj_min_cfg}  MJJ_MAX_GEV={mjj_max_cfg}")
    _log(f"[cfg] MJJ_REQUIRE_BACKTOBACK={mjj_require_backtoback}")
    _log(f"[cfg] DIJET_BACKTOBACK_TOL_DEG={bb_tol_deg}")
    _log(f"[cfg] IMBALANCE_REQUIRE_BACKTOBACK={imbalance_require_backtoback}  IMBALANCE_BACKTOBACK_TOL_DEG={imbalance_bb_tol_deg}")
    _log(f"[cfg] FIT_WIN_DEG={fit_win_scalar}")
    _log(f"[cfg] FIT_WIN_PER_BIN_DEG={win_per if use_array_win else 'disabled'}")
    _log(f"[cfg] DIJET_REQUIRE_EXACTLY_TWO_JETS={dijet_require_exactly_two}")
    _log(f"[cfg] YSTAR_ENABLE={ystar_enable}  YSTAR_MAX={ystar_max}")
    # Paper-style selection text for plot titles (keep plots self-contained when screenshotted).
    # IMPORTANT: For JET_ETA_MODE==1 (cone containment), the effective jet-|η| acceptance is (JET_ETA_MAX - R).
    # We compute this per-R at title-build time to avoid lying in the plot header.
    def _mjj_backtoback_title_tag(mjj_require_backtoback: int, bb_tol_deg: float) -> str:
        if int(mjj_require_backtoback) == 1:
            return f"; back-to-back: $|\\Delta\\varphi-\\pi|\\leq {bb_tol_deg:.0f}^\\circ$"
        return ""

    def _dijet_pair_title_tag() -> str:
        tags = []
        if ystar_enable == 1:
            tags.append(f"|y*|<{ystar_max:.1f}")
        if dijet_require_exactly_two == 1:
            tags.append("exactly 2 accepted jets")
        return ("; " + "; ".join(tags)) if tags else ""

    def _dijet_pair_title_tag_no_ystar() -> str:
        tags = []
        if dijet_require_exactly_two == 1:
            tags.append("exactly 2 accepted jets")
        return ("; " + "; ".join(tags)) if tags else ""

    def _imbalance_pair_title_tag() -> str:
        tags = []
        if ystar_enable == 1:
            tags.append(f"|y*|<{ystar_max:.1f}")
        if dijet_require_exactly_two == 1:
            tags.append("exactly 2 accepted jets")
        if imbalance_require_backtoback == 1:
            tags.append(rf"$|\Delta\varphi-\pi|\leq {imbalance_bb_tol_deg:.0f}^\circ$")
        return ("; " + "; ".join(tags)) if tags else ""

    def _dphi_title_cuts(Ruse):
        try:
            eta_eff = float(jetEtaMax_cfg)
            if int(jetEtaMode_cfg) == 1:
                eta_eff = max(0.0, float(jetEtaMax_cfg) - float(Ruse))
        except Exception:
            eta_eff = float(jetEtaMax_cfg)
        t = rf"$|\eta_{{\mathrm{{jet}}}}|<{eta_eff:g}$"
        if ystar_enable:
            t += rf"; $|y^*|<{ystar_max:g}$"
        if dijet_require_exactly_two == 1:
            t += "; exactly 2 accepted jets"
        return t

    def _ystar_title_tag() -> str:
        return _dijet_pair_title_tag()
    _log(f"[cfg] title cuts (R-dependent when JET_ETA_MODE==1): base_eta={jetEtaMax_cfg:g} mode={jetEtaMode_cfg} exact2={dijet_require_exactly_two}")
    _log("[physics] Δφ fitter outputs are dijet-selected azimuthal-decorrelation observables, not semi-inclusive trigger-recoil Δ_recoil observables.")



    try:
        th_scan_max_deg = float(_require("THETA_SCAN_MAX_DEG"))
    except Exception as e:
        _fatal(f"Invalid THETA_SCAN_MAX_DEG={cfg.get('THETA_SCAN_MAX_DEG')!r}: {e}")
    try:
        th_scan_step_deg = float(_require("THETA_SCAN_STEP_DEG"))
    except Exception as e:
        _fatal(f"Invalid THETA_SCAN_STEP_DEG={cfg.get('THETA_SCAN_STEP_DEG')!r}: {e}")
    if th_scan_step_deg <= 0:
        _fatal(f"THETA_SCAN_STEP_DEG must be > 0; got {th_scan_step_deg}")
    if th_scan_max_deg <= 0:
        _fatal(f"THETA_SCAN_MAX_DEG must be > 0; got {th_scan_max_deg}")
    if th_scan_step_deg > th_scan_max_deg:
        _fatal(f"THETA_SCAN_STEP_DEG ({th_scan_step_deg}) cannot exceed THETA_SCAN_MAX_DEG ({th_scan_max_deg})")
    theta_deg_grid = np.arange(0.0, th_scan_max_deg+1e-9, th_scan_step_deg)
    theta_grid = to_rad(theta_deg_grid)
    _log(f"[cfg] THETA_SCAN_MAX_DEG={th_scan_max_deg}  THETA_SCAN_STEP_DEG={th_scan_step_deg}  Ntheta={theta_deg_grid.size}")


    # Aggregation weighting scheme for width vs R
    width_weighting = _require("WIDTH_WEIGHTING").strip().lower()
    if width_weighting not in ("xsec", "ivar", "equal"):
        _fatal(f"Invalid WIDTH_WEIGHTING={cfg.get('WIDTH_WEIGHTING')!r}. Allowed: xsec | ivar | equal")
    _log(f"Width aggregation weighting: {width_weighting}")

    # CSV (note: includes Δφ integral column used as xsec weight)
    csv_path = os.path.join(DIR_FINAL, "dphi_fit_summary.csv")
    bk_dir = os.path.join(DIR_FINAL, "csv_backups"); ensure_dir(bk_dir)
    if os.path.isfile(csv_path):
        ts = time.strftime("%Y%m%d_%H%M%S")
        os.rename(csv_path, os.path.join(bk_dir, f"dphi_fit_summary.{ts}.csv"))
        _log("Archived old CSV")
    header_cols = [
        "jet_R","hist","pt_bin",
        "mu","mu_deg","mu_err","mu_err_deg",
        "sigma","sigma_deg","sigma_err","sigma_err_deg",
        "const","const_err","A","chi2","ndf",
        "rms_bkgsub","rms_bkgsub_deg","theta_rms","theta_rms_deg","theta_rms_err","theta_rms_err_deg",
        "frac_1sigma","frac_2sigma","frac_RMS","delta_mu_from_pi","delta_mu_from_pi_deg",
        "dphi_integral_mb"
    ]
    tol_fracs = _require("TOL_FRACS")
    fracs = []
    for t in tol_fracs.split(","):
        try: fracs.append(float(t))
        except: pass
    if not fracs:
        _fatal(f"TOL_FRACS parsed to an empty list (raw={tol_fracs!r}). Provide a comma-separated list like '0.68,0.80,0.90,0.95'.")
    _log(f"[cfg] TOL_FRACS={fracs}")
    for a in fracs:
        if (not np.isfinite(a)) or (a <= 0.0) or (a >= 1.0):
            _fatal(f"Invalid TOL_FRACS entry {a!r}. Each fraction must satisfy 0 < f < 1.")

    for a in fracs:
        tag = int(round(a*100))
        header_cols += [f"theta_fit_{tag}", f"theta_fit_{tag}_deg",
                        f"theta_fit_{tag}_err", f"theta_fit_{tag}_err_deg",
                        f"theta_hist_{tag}", f"theta_hist_{tag}_deg"]
    out_csv = open(csv_path, "w"); out_csv.write(",".join(header_cols) + "\n")

    def find_pt_bin(lo, hi):
        for i in range(len(pt_edges)-1):
            if abs(pt_edges[i]-lo) < 1e-9 and abs(pt_edges[i+1]-hi) < 1e-9:
                return i
        return -1

    n_dphi = n_eta = n_mjj = n_frac = n_particle = 0
    want_Rs = {False: {float(r): None for r in combine_R_list}, True: {float(r): None for r in combine_R_list}}  # per-branch stash for combined Mjj
    # Filename tag for combined Mjj plots: reflect actual COMBINE_R_LIST (sorted)
    # e.g. [0.2,0.4,0.6] -> "R020_R040_R060"
    def _r_to_tag(R):
        try:
            return f"R{int(round(float(R)*100.0 + 1e-9)):03d}"
        except Exception:
            return "R???"
    combine_tag = "_".join([_r_to_tag(r) for r in sorted(want_Rs[False].keys())])
    _log(f"[cfg] combined Mjj filename tag = {combine_tag}")

    # For width vs R aggregation (xsec/ivar/equal)
    widths_by_R_full = {False: defaultdict(list), True: defaultdict(list)}  # branch -> R -> list of (sigma_rad, sigma_err_rad, weight_mb) for Δφ in [0,2π)
    widths_by_R_abs  = {False: defaultdict(list), True: defaultdict(list)}  # branch -> R -> list for |Δφ| in [0,π]

    # For combined Mjj plot: stash the three 'all' spectra

        # Legacy plot layout (pre-v3.5): keep for backward compatibility
    out_dir_fit   = os.path.join(DIR_FINAL, PLOTS_SUBDIR, "dphi_fit")
    out_dir_fit_abs = os.path.join(DIR_FINAL, PLOTS_SUBDIR, "dphi_fit_abs0pi")
    out_dir_eta   = os.path.join(DIR_FINAL, PLOTS_SUBDIR, "eta")
    out_dir_mjj   = os.path.join(DIR_FINAL, PLOTS_SUBDIR, "dijet_mass")
    out_dir_sum   = os.path.join(DIR_FINAL, PLOTS_SUBDIR, "summary")
    out_dir_imb   = os.path.join(DIR_FINAL, PLOTS_SUBDIR, "dijet_imbalance")
    out_dir_jetR  = os.path.join(DIR_FINAL, PLOTS_SUBDIR, "jet_R_dependence")

    out_dir_particle = os.path.join(DIR_FINAL, PLOTS_SUBDIR, "particle_level")

    # Standard paper-style layout: explicit SUBFRAC vs NO-SUBFRAC branch roots
    #
    # Canonical layout (no duplicate plots):
    #   plots/absolute/subfrac/<category>/
    #   plots/absolute/nosubfrac/<category>/
    #   plots/dijet_normalized/subfrac/<category>/
    #   plots/dijet_normalized/nosubfrac/<category>/
    #
    # NOTE: Most branchful observables live only under subfrac/nosubfrac canonical trees.
    # Intentional neutral exceptions:
    #   plots/absolute/jet_spectra/         for the analyzer's inclusive absolute jet spectrum
    #   plots/inclusive_unit_normalized/jet_spectra/  for the analyzer's inclusive unit-shape jet spectrum
    # The inclusive jet histogram has no SUBFRAC / NO-SUBFRAC split and is not a dijet-selected observable,
    # so it must not be routed through the dijet_normalized neutral tree.
    plots_abs  = os.path.join(DIR_FINAL, PLOTS_SUBDIR, "absolute")
    plots_norm = os.path.join(DIR_FINAL, PLOTS_SUBDIR, "dijet_normalized")
    plots_unitshape = os.path.join(DIR_FINAL, PLOTS_SUBDIR, "inclusive_unit_normalized")

    plots_abs_sub   = os.path.join(plots_abs,  "subfrac")
    plots_abs_ns    = os.path.join(plots_abs,  "nosubfrac")
    plots_norm_sub  = os.path.join(plots_norm, "subfrac")
    plots_norm_ns   = os.path.join(plots_norm, "nosubfrac")

    out_dir_lead_sublead_corr_sub = os.path.join(plots_abs_sub, "lead_sublead_correlation")
    out_dir_lead_sublead_corr_ns  = os.path.join(plots_abs_ns,  "lead_sublead_correlation")

    out_dir_jetpt_abs_neutral       = os.path.join(plots_abs,       "jet_spectra")
    out_dir_jetpt_unitshape_neutral = os.path.join(plots_unitshape, "jet_spectra")
    out_dir_jetR_sub = os.path.join(out_dir_jetR, "subfrac")
    out_dir_jetR_ns  = os.path.join(out_dir_jetR, "nosubfrac")

    # Category roots (SUBFRAC branch). NO-SUBFRAC outputs are routed by _out_dir/_out_dir_flag.
    out_dir_fit_abs_std         = os.path.join(plots_abs_sub,  "dphi_fit")
    out_dir_fit_abs0pi_std      = os.path.join(plots_abs_sub,  "dphi_fit_abs0pi")
    out_dir_eta_abs_std         = os.path.join(plots_abs_sub,  "eta")
    out_dir_mjj_abs_std         = os.path.join(plots_abs_sub,  "dijet_mass")
    out_dir_imb_abs_std         = os.path.join(plots_abs_sub,  "dijet_imbalance")
    out_dir_jetpt_abs_std       = os.path.join(plots_abs_sub,  "jet_spectra")
    out_dir_sum_abs_std         = os.path.join(plots_abs_sub,  "summary")

    out_dir_fit_norm_std        = os.path.join(plots_norm_sub, "dphi_fit")
    out_dir_fit_abs0pi_norm_std = os.path.join(plots_norm_sub, "dphi_fit_abs0pi")
    out_dir_eta_norm_std        = os.path.join(plots_norm_sub, "eta")
    out_dir_mjj_norm_std        = os.path.join(plots_norm_sub, "dijet_mass")
    out_dir_imb_norm_std        = os.path.join(plots_norm_sub, "dijet_imbalance")
    out_dir_jetpt_norm_std      = os.path.join(plots_norm_sub, "jet_spectra")
    out_dir_sum_norm_std        = os.path.join(plots_norm_sub, "summary")

    # Pre-create branch/category directories so the plot tree is stable even if some histograms are missing.
    for d in (
        out_dir_jetR, out_dir_jetR_sub, out_dir_jetR_ns, out_dir_particle,
        plots_abs, plots_norm, plots_unitshape, out_dir_jetpt_abs_neutral, out_dir_jetpt_unitshape_neutral,
        out_dir_lead_sublead_corr_sub, out_dir_lead_sublead_corr_ns,
        plots_abs_sub, plots_abs_ns, plots_norm_sub, plots_norm_ns,

        # absolute/subfrac categories
        out_dir_fit_abs_std, out_dir_fit_abs0pi_std, out_dir_eta_abs_std, out_dir_mjj_abs_std, out_dir_imb_abs_std, out_dir_jetpt_abs_std, out_dir_sum_abs_std,
        # dijet_normalized/subfrac categories
        out_dir_fit_norm_std, out_dir_fit_abs0pi_norm_std, out_dir_eta_norm_std, out_dir_mjj_norm_std, out_dir_imb_norm_std, out_dir_jetpt_norm_std, out_dir_sum_norm_std,

        # absolute/nosubfrac categories
        os.path.join(plots_abs_ns,  "dphi_fit"),
        os.path.join(plots_abs_ns,  "dphi_fit_abs0pi"),
        os.path.join(plots_abs_ns,  "eta"),
        os.path.join(plots_abs_ns,  "dijet_mass"),
        os.path.join(plots_abs_ns,  "dijet_imbalance"),
        os.path.join(plots_abs_ns,  "jet_spectra"),
        os.path.join(plots_abs_ns,  "summary"),

        # dijet_normalized/nosubfrac categories
        os.path.join(plots_norm_ns, "dphi_fit"),
        os.path.join(plots_norm_ns, "dphi_fit_abs0pi"),
        os.path.join(plots_norm_ns, "eta"),
        os.path.join(plots_norm_ns, "dijet_mass"),
        os.path.join(plots_norm_ns, "dijet_imbalance"),
        os.path.join(plots_norm_ns, "jet_spectra"),
        os.path.join(plots_norm_ns, "summary"),
    ):
        ensure_dir(d)

    # Cleanup: remove old empty dead-end category folders if they exist from earlier runs.
    # (We still intentionally use plots/*/jet_spectra for the branch-neutral inclusive jet spectra.)
    try:
        if os.path.isdir(out_dir_sum) and (len(os.listdir(out_dir_sum)) == 0):
            os.rmdir(out_dir_sum)
    except Exception:
        pass

    for _dead in ("dphi_fit", "dphi_fit_abs0pi", "eta", "dijet_mass", "dijet_imbalance", "summary"):
        for _root in (plots_abs, plots_norm):
            _dd = os.path.join(_root, _dead)
            try:
                if os.path.isdir(_dd) and (len(os.listdir(_dd)) == 0):
                    os.rmdir(_dd)
            except Exception:
                pass

    _log(
        f"[INFO] Plot roots: legacy={os.path.join(DIR_FINAL, PLOTS_SUBDIR)} "
        f"| absolute={plots_abs_sub} (subfrac) + {plots_abs_ns} (nosubfrac) + {out_dir_jetpt_abs_neutral} (inclusive-neutral jet_spectra) "
        f"| dijet_normalized={plots_norm_sub} (subfrac) + {plots_norm_ns} (nosubfrac) "
        f"| inclusive_unit_normalized={out_dir_jetpt_unitshape_neutral} (inclusive-neutral jet_spectra)"
    )
    def _is_nosubfrac(hname: str, in_ns_dir: bool=False) -> bool:
        try:
            return bool(in_ns_dir) or (isinstance(hname, str) and ("_nosubfrac" in hname))
        except Exception:
            return bool(in_ns_dir)

    _canonical_roots = {
        ("absolute", "dphi_fit", False): out_dir_fit_abs_std,
        ("absolute", "dphi_fit", True):  os.path.join(plots_abs_ns,  "dphi_fit"),
        ("absolute", "dphi_fit_abs0pi", False): out_dir_fit_abs0pi_std,
        ("absolute", "dphi_fit_abs0pi", True):  os.path.join(plots_abs_ns,  "dphi_fit_abs0pi"),
        ("absolute", "eta", False): out_dir_eta_abs_std,
        ("absolute", "eta", True):  os.path.join(plots_abs_ns,  "eta"),
        ("absolute", "dijet_mass", False): out_dir_mjj_abs_std,
        ("absolute", "dijet_mass", True):  os.path.join(plots_abs_ns,  "dijet_mass"),
        ("absolute", "dijet_imbalance", False): out_dir_imb_abs_std,
        ("absolute", "dijet_imbalance", True):  os.path.join(plots_abs_ns,  "dijet_imbalance"),
        ("absolute", "lead_sublead_correlation", False): out_dir_lead_sublead_corr_sub,
        ("absolute", "lead_sublead_correlation", True):  out_dir_lead_sublead_corr_ns,
        ("absolute", "jet_spectra", False): out_dir_jetpt_abs_std,
        ("absolute", "jet_spectra", True):  os.path.join(plots_abs_ns,  "jet_spectra"),
        ("absolute", "summary", False): out_dir_sum_abs_std,
        ("absolute", "summary", True):  os.path.join(plots_abs_ns,  "summary"),

        ("dijet_normalized", "dphi_fit", False): out_dir_fit_norm_std,
        ("dijet_normalized", "dphi_fit", True):  os.path.join(plots_norm_ns, "dphi_fit"),
        ("dijet_normalized", "dphi_fit_abs0pi", False): out_dir_fit_abs0pi_norm_std,
        ("dijet_normalized", "dphi_fit_abs0pi", True):  os.path.join(plots_norm_ns, "dphi_fit_abs0pi"),
        ("dijet_normalized", "eta", False): out_dir_eta_norm_std,
        ("dijet_normalized", "eta", True):  os.path.join(plots_norm_ns, "eta"),
        ("dijet_normalized", "dijet_mass", False): out_dir_mjj_norm_std,
        ("dijet_normalized", "dijet_mass", True):  os.path.join(plots_norm_ns, "dijet_mass"),
        ("dijet_normalized", "dijet_imbalance", False): out_dir_imb_norm_std,
        ("dijet_normalized", "dijet_imbalance", True):  os.path.join(plots_norm_ns, "dijet_imbalance"),
        ("dijet_normalized", "jet_spectra", False): out_dir_jetpt_norm_std,
        ("dijet_normalized", "jet_spectra", True):  os.path.join(plots_norm_ns, "jet_spectra"),
        ("dijet_normalized", "summary", False): out_dir_sum_norm_std,
        ("dijet_normalized", "summary", True):  os.path.join(plots_norm_ns, "summary"),
    }
    for _d in _canonical_roots.values():
        ensure_dir(_d)

    _save_counts = {}
    _neutral_save_counts = {}

    _neutral_roots = {
        ("absolute", "jet_spectra"): out_dir_jetpt_abs_neutral,
        ("inclusive_unit_normalized", "jet_spectra"): out_dir_jetpt_unitshape_neutral,
    }
    for _d in _neutral_roots.values():
        ensure_dir(_d)

    def _canonical_dir(kind: str, category: str, is_nosubfrac: bool) -> str:
        key = (kind, category, bool(is_nosubfrac))
        d = _canonical_roots[key]
        ensure_dir(d)
        return d

    def _savefig_branch(fig, kind: str, category: str, is_nosubfrac: bool, fname: str, *, dpi: int) -> str:
        out_dir = _canonical_dir(kind, category, is_nosubfrac)
        out_path = os.path.join(out_dir, fname)
        fig.savefig(out_path, dpi=dpi)
        key = (kind, category, 'nosubfrac' if is_nosubfrac else 'subfrac')
        _save_counts[key] = _save_counts.get(key, 0) + 1
        return out_path

    def _savefig_neutral(fig, kind: str, category: str, fname: str, *, dpi: int) -> str:
        out_dir = _neutral_roots[(kind, category)]
        ensure_dir(out_dir)
        out_path = os.path.join(out_dir, fname)
        fig.savefig(out_path, dpi=dpi)
        key = (kind, category)
        _neutral_save_counts[key] = _neutral_save_counts.get(key, 0) + 1
        return out_path

    def _legacy_branch_dir(base_dir: str, *, is_nosubfrac: bool) -> str:
        d = os.path.join(base_dir, "nosubfrac" if is_nosubfrac else "subfrac")
        ensure_dir(d)
        return d

    def _route_branch_dir(base_dir: str, *, is_nosubfrac: bool) -> str:
        """Return an output directory matching the chosen branch.

        Canonical plot layout (no duplicates):
          plots/absolute/{subfrac,nosubfrac}/<category>/
          plots/dijet_normalized/{subfrac,nosubfrac}/<category>/

        IMPORTANT: If base_dir is already rooted inside one of the canonical
        branch trees, treat it as canonical and only swap the branch token when
        needed. This avoids accidentally creating .../subfrac/subfrac/... .
        """
        if not isinstance(base_dir, str):
            return base_dir

        d = base_dir

        # 1) Already-canonical branch trees
        if d.startswith(plots_abs_sub):
            if is_nosubfrac:
                d = d.replace(plots_abs_sub, plots_abs_ns, 1)
            ensure_dir(d)
            return d
        if d.startswith(plots_abs_ns):
            if not is_nosubfrac:
                d = d.replace(plots_abs_ns, plots_abs_sub, 1)
            ensure_dir(d)
            return d
        if d.startswith(plots_norm_sub):
            if is_nosubfrac:
                d = d.replace(plots_norm_sub, plots_norm_ns, 1)
            ensure_dir(d)
            return d
        if d.startswith(plots_norm_ns):
            if not is_nosubfrac:
                d = d.replace(plots_norm_ns, plots_norm_sub, 1)
            ensure_dir(d)
            return d

        # 2) Neutral category roots (absolute/<category>/ or dijet_normalized/<category>/)
        if d.startswith(plots_abs):
            rel = os.path.relpath(d, plots_abs)
            d = os.path.join(plots_abs_ns if is_nosubfrac else plots_abs_sub, rel)
            ensure_dir(d)
            return d
        if d.startswith(plots_norm):
            rel = os.path.relpath(d, plots_norm)
            d = os.path.join(plots_norm_ns if is_nosubfrac else plots_norm_sub, rel)
            ensure_dir(d)
            return d

        # 3) Legacy/other dirs
        if is_nosubfrac:
            d = os.path.join(d, "nosubfrac")
        ensure_dir(d)
        return d

    def _out_dir(base_dir: str, hname: str, in_ns_dir: bool=False) -> str:
        """Route output directory based on SUBFRAC vs NO-SUBFRAC branch."""
        return _route_branch_dir(base_dir, is_nosubfrac=_is_nosubfrac(hname, in_ns_dir))

    def _out_dir_flag(base_dir: str, is_nosubfrac: bool) -> str:
        """Same routing as _out_dir but driven by explicit branch flag."""
        return _route_branch_dir(base_dir, is_nosubfrac=bool(is_nosubfrac))

    # Cross section normalization uncertainty (if analyzer/merge wrote xsec_summary.json).
    # Used only for plotting error bars when INCLUDE_XSEC_NORM_ERR=1.
    xsec_summary_path = os.path.join(DIR_FINAL, 'xsec_summary.json')
    xsec_band_builder = None
    xsec_rel_err = load_xsec_rel_err(DIR_FINAL)
    _log(f"[cfg] xsec_rel_err={xsec_rel_err} (from {xsec_summary_path})")
    if INCLUDE_XSEC_NORM_ERR and not (np.isfinite(xsec_rel_err) and xsec_rel_err > 0):
        _fatal(f"INCLUDE_XSEC_NORM_ERR=1 but {xsec_summary_path} is missing/unreadable or has invalid xsec_total_rel_err={xsec_rel_err!r}. Rerun merge with valid sigmaErr_mb/xsecerr_mb metadata.")
    if INCLUDE_XSEC_NORM_ERR:
        try:
            xsec_band_builder = SliceNormBandBuilder(DIR_FINAL)
        except Exception as e:
            _fatal(f"INCLUDE_XSEC_NORM_ERR=1 but exact per-slice xsec band reconstruction failed: {e}")
        _log(f"[cfg] exact xsec band builder loaded {len(xsec_band_builder.slices)} per-slice ROOTs from {xsec_summary_path}")

    # Sanity counters (helps debug empty nosubfrac/ trees without guessing).
    n_hist_total = 0
    n_hist_sub = 0
    n_hist_ns = 0
    ns_parse_counts = {'eta': 0, 'mjj': 0, 'dphi': 0, 'other': 0}
    ns_parse_unmatched = []

    for item in read_root_histograms(INPUT_ROOT):
        if len(item) == 8:
            hn, xc, yc, ye, bw, var, entries_val, in_ns_dir = item
        else:
            hn, xc, yc, ye, bw, var, entries_val = item
            in_ns_dir = False

        n_hist_total += 1
        if _is_nosubfrac(hn, in_ns_dir):
            n_hist_ns += 1
        else:
            n_hist_sub += 1

        if INCLUDE_XSEC_NORM_ERR and xsec_band_builder is not None:
            try:
                xsec_plot_term = xsec_band_builder.norm_err_for_hist(hn, xc, bw, in_ns_dir=in_ns_dir)
            except Exception as e:
                _fatal(f"Failed to build exact xsec normalization band for histogram '{_canonical_hist_key(hn, in_ns_dir=in_ns_dir)}': {e}")
        else:
            xsec_plot_term = xsec_rel_err

        # ---------------- particle-level accepted-constituent QA ----------------
        particle_kind = parse_particle_name(hn)
        if particle_kind:
            fig, ax = plt.subplots(figsize=(8.8, 6.2))
            yerr_plot = yerr_for_plot_absolute(yc, ye, xsec_plot_term)
            ax.errorbar(xc, yc, yerr=yerr_plot, fmt="o", ms=DEFAULT_MARKER_SIZE, lw=DEFAULT_LINE_WIDTH, capsize=2, label="simulation")

            if particle_kind == "pt":
                ax.set_xscale("log")
                apply_logy_with_floor(ax, yc, yerr_plot)
                ax.set_xlabel(r"$p_{T}^{\mathrm{particle}}$ [GeV]")
                ax.set_ylabel(r"$d\sigma/dp_{T}^{\mathrm{particle}}$ (mb/GeV)")
                ax.set_title("Accepted particle-level constituents (pre-clustering, inclusive weighted yield): $p_T$")
            elif particle_kind == "eta":
                ax.set_xlabel(r"$\eta^{\mathrm{particle}}$")
                ax.set_ylabel(r"$d\sigma/d\eta^{\mathrm{particle}}$ (mb)")
                ax.set_title(r"Accepted particle-level constituents (pre-clustering, inclusive weighted yield): pseudorapidity $\eta$")
            elif particle_kind == "phi":
                ax.set_xlabel(r"$\phi^{\mathrm{particle}}$ [rad]")
                ax.set_ylabel(r"$d\sigma/d\phi^{\mathrm{particle}}$ (mb/rad)")
                ax.set_title(r"Accepted particle-level constituents (pre-clustering, inclusive weighted yield): azimuth $\phi$")
            else:
                ax.set_xlabel("Observable")
                ax.set_ylabel(r"$d\sigma/dX$")
                ax.set_title(f"Accepted particle-level constituents (pre-clustering, inclusive weighted yield): {particle_kind}")

            ax.legend(loc="best", fontsize=_FONTS['legend'])
            fig.tight_layout()
            fig.savefig(os.path.join(out_dir_particle, f"{hn}.png"), dpi=150)
            plt.close(fig)
            n_particle += 1
            continue

        # ---------------- η plots (density-aware rebin) ----------------
        eta_tag = parse_eta_name(hn)
        if _is_nosubfrac(hn, in_ns_dir):
            if eta_tag:
                ns_parse_counts['eta'] += 1
            else:
                mjj_probe = parse_mjj_name(hn)
                dphi_probe = parse_dphi_name(hn)
                if mjj_probe:
                    ns_parse_counts['mjj'] += 1
                elif dphi_probe:
                    ns_parse_counts['dphi'] += 1
                else:
                    ns_parse_counts['other'] += 1
                    if len(ns_parse_unmatched) < 12:
                        ns_parse_unmatched.append(hn)
        if eta_tag:
            kind, isLead, Rname = eta_tag
            Ruse = R_cfg if (Rname is None or np.isnan(Rname)) else Rname

            xc_rb, yc_rb, ye_rb, bw_rb = _rebin_effective_stats_density(
                xc, yc, ye, bw, variances=var, neff_min=200
            )

            fig, ax = plt.subplots(figsize=(9,7))
            ax.errorbar(xc_rb, yc_rb, yerr=yerr_for_plot_absolute(yc_rb, ye_rb, xsec_plot_term), fmt="o", ms=DEFAULT_MARKER_SIZE, lw=DEFAULT_LINE_WIDTH, capsize=2)
            ax.set_xlabel(r"$\eta$")
            ax.set_ylabel(r"$d\sigma/d\eta$ (mb)")
            ax.set_title(f"Pseudorapidity η of {'leading' if isLead else 'subleading'} jet  [R={Ruse:.2f}{_ystar_title_tag()}]")
            etaMaxJet = float(jetEtaMax_cfg)
            if jetEtaMode_cfg == 1:
                etaMaxJet = max(0.0, jetEtaMax_cfg - Ruse)
            if etaMaxJet > 0:
                ax.axvline(-etaMaxJet, ls="--"); ax.axvline(+etaMaxJet, ls="--")
            if len(xc_rb) < len(xc):
                ax.text(0.02, 0.02, f"adaptive rebin → {len(xc_rb)} bins",
                        transform=ax.transAxes, fontsize=_FONTS['note'], alpha=0.8)
            fig.tight_layout()
            # Legacy + standard absolute output
            # (v4.9.43) Legacy duplicate output removed: eta absolute is written under absolute/eta
            ns = _is_nosubfrac(hn, in_ns_dir)
            _savefig_branch(fig, "absolute", "eta", ns, f"{hn}.png", dpi=140)
            plt.close(fig)

            # Per-dijet normalized η shape (1/σ_sel · dσ/dη)
            sig_eta, yEtaN, eEtaN = normalize_per_dijet_with_cov(
                yc_rb, ye_rb, bw_rb,
                denom_positive_only=False,
                cov_mode=PERDIJET_COV_MODE
            )
            if yEtaN is not None and eEtaN is not None and np.any(np.isfinite(yEtaN)):
                fig, ax = plt.subplots(figsize=(9,7))
                errorbar_nan_safe(ax, xc_rb, yEtaN, eEtaN, fmt="o", ms=DEFAULT_MARKER_SIZE, lw=DEFAULT_LINE_WIDTH, capsize=2)
                ax.set_xlabel(r"$\eta$")
                ax.set_ylabel(r"$(1/\sigma_{\mathrm{sel}})\,d\sigma/d\eta$ (1 per unit $\eta$)")
                ax.set_title(f"Pseudorapidity η of {'leading' if isLead else 'subleading'} jet (per-selection normalized)  [R={Ruse:.2f}{_ystar_title_tag()}]")
                if etaMaxJet > 0:
                    ax.axvline(-etaMaxJet, ls="--"); ax.axvline(+etaMaxJet, ls="--")
                if len(xc_rb) < len(xc):
                    ax.text(0.02, 0.02, f"adaptive rebin → {len(xc_rb)} bins",
                            transform=ax.transAxes, fontsize=_FONTS['note'], alpha=0.8)
                fig.tight_layout()
                # (v4.9.43) Legacy duplicate output removed: eta per-dijet is written under dijet_normalized/eta
                _savefig_branch(fig, "dijet_normalized", "eta", ns, f"{hn}_perdijet.png", dpi=140)
                plt.close(fig)


            n_eta += 1
            continue

        # ---------------- Mjj plots (Mean/Std only) ----------------
        mjj_tag = parse_mjj_name(hn)
        if mjj_tag:
            Rm, ptlo, pthi, isAll = mjj_tag
            Ruse = R_cfg if (Rm is None or np.isnan(Rm)) else Rm

            s = yc * bw
            S = float(np.nansum(s))
            Sw = float(np.nansum(s * xc))
            if S > 0:
                mean = Sw / S
                var_x = float(np.nansum(s * (xc - mean) ** 2) / S)
                std = math.sqrt(max(0.0, var_x))
            else:
                mean, std = float("nan"), float("nan")

            entries = entries_val if np.isfinite(entries_val) else float("nan")
            ns = _is_nosubfrac(hn, in_ns_dir)

            if isAll:
                if round(Ruse, 2) in want_Rs[ns]:
                    want_Rs[ns][round(Ruse, 2)] = dict(
                    xc=xc, yc=yc, ye=ye, bw=bw, R=Ruse, entries=entries, mean=mean, std=std, xsec_norm_err=xsec_plot_term
                )

            fig, ax = plt.subplots(figsize=(9,7))
            ax.set_xscale("log"); ax.set_yscale("log")
            ax.errorbar(xc, np.clip(yc, 1e-30, None), yerr=yerr_for_plot_absolute(yc, ye, xsec_plot_term), fmt="o", ms=DEFAULT_MARKER_SIZE, lw=DEFAULT_LINE_WIDTH)
            x_floor = max(1e-3, mjj_min_cfg if mjj_min_cfg > 0 else 1e-3)
            x_ceil  = (mjj_max_cfg if (np.isfinite(mjj_max_cfg) and mjj_max_cfg > x_floor) else None)
            x_min, x_max = auto_xlim_hist(xc, yc, bw, logx=True, q_lo=0.002, q_hi=0.998, pad_frac=0.12,
                                         x_floor=x_floor, x_ceil=x_ceil)
            ax.set_xlim(x_min, x_max)
            ax.set_ylim(1e-12, max(np.nanmax(yc)*1.5, 1e-11))
            ax.set_xlabel(r"$M_{jj}$ (GeV)")
            ax.set_ylabel(r"$d\sigma/dM_{jj}$ (mb/GeV)")
            ttl_pt = (rf"$p_{{T,1}}$: {PT_ALL_LABEL}" if isAll else rf"$p_{{T,1}}\in[{int(ptlo)},{int(pthi)}]$ GeV")
            pair_txt = _dijet_pair_title_tag()
            mjj_bb_tag = _mjj_backtoback_title_tag(mjj_require_backtoback, bb_tol_deg)
            ax.set_title(
                f"Dijet invariant mass  [{ttl_pt}; R={Ruse:.2f}{mjj_bb_tag}{pair_txt}]"
            )

            lines = []
            if np.isfinite(mean):    lines.append(f"Mean = {mean:.0f} GeV")
            if np.isfinite(std):     lines.append(f"Std Dev = {std:.0f} GeV")
            if lines:
                ax.text(0.98, 0.98, "\n".join(lines), transform=ax.transAxes, va="top", ha="right",
                        fontsize=_FONTS['note'], bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.85, edgecolor="black"))

            fig.tight_layout()
            # (v4.9.43) Legacy duplicate output removed: Mjj absolute is written under absolute/dijet_mass
            _savefig_branch(fig, "absolute", "dijet_mass", ns, f"{hn}.png", dpi=140)
            plt.close(fig)

            # Also write a per-selection normalized view: (1/σ_sel) dσ/dMjj  [1/GeV]
            mjj_sigma_mb, ycn, yen = normalize_per_dijet_with_cov(yc, ye, bw, denom_positive_only=False, cov_mode=PERDIJET_COV_MODE)
            if np.isfinite(mjj_sigma_mb) and mjj_sigma_mb > 0 and ycn is not None:

                fig, ax = plt.subplots(figsize=(9,7))
                ax.set_xscale("log"); ax.set_yscale("log")
                mjj_count = None
                mjj_norm_label = None
                if SINGLE_SLICE_MODE and SELECTED_DIJET_COUNTS is not None:
                    mjj_count = SELECTED_DIJET_COUNTS.count_for("mjj", Ruse, is_nosubfrac=ns, ptlo=(None if isAll else ptlo), pthi=(None if isAll else pthi))
                    mjj_norm_label = _legend_count_label("mjj", mjj_count)
                errorbar_nan_safe(ax, xc, np.clip(ycn, 1e-30, None), yen, fmt="o", ms=DEFAULT_MARKER_SIZE, lw=DEFAULT_LINE_WIDTH, capsize=2, label=mjj_norm_label)

                x_floor = max(1e-3, mjj_min_cfg if mjj_min_cfg > 0 else 1e-3)
                x_ceil  = (mjj_max_cfg if (np.isfinite(mjj_max_cfg) and mjj_max_cfg > x_floor) else None)
                x_min, x_max = auto_xlim_hist(xc, ycn, bw, logx=True, q_lo=0.002, q_hi=0.998, pad_frac=0.12,
                                             x_floor=x_floor, x_ceil=x_ceil)
                ax.set_xlim(x_min, x_max)
                ax.set_ylim(1e-12, max(np.nanmax(ycn)*1.5, 1e-11))
                ax.set_xlabel(r"$M_{jj}$ (GeV)")
                ax.set_ylabel(_single_slice_norm_ylabel("mjj") if SINGLE_SLICE_MODE else r"$(1/\sigma_{\mathrm{sel}})\,d\sigma/dM_{jj}$ (1/GeV)")
                ttl_pt = (rf"$p_{{T,1}}$: {PT_ALL_LABEL}" if isAll else rf"$p_{{T,1}}\in[{int(ptlo)},{int(pthi)}]$ GeV")
                pair_txt = _dijet_pair_title_tag()
                norm_title_tag = "single-slice count normalized" if SINGLE_SLICE_MODE else "per-selection normalized"
                mjj_bb_tag = _mjj_backtoback_title_tag(mjj_require_backtoback, bb_tol_deg)
                ax.set_title(
                    f"Dijet invariant mass ({norm_title_tag})  [{ttl_pt}; R={Ruse:.2f}{mjj_bb_tag}{pair_txt}]"
                )

                if SINGLE_SLICE_MODE and mjj_norm_label is not None:
                    ax.legend(loc="best", frameon=False, fontsize=_FONTS.get("legend", None))
                fig.tight_layout()
                # (v4.9.43) Legacy duplicate output removed: Mjj per-dijet is written under dijet_normalized/dijet_mass
                _savefig_branch(fig, "dijet_normalized", "dijet_mass", ns, f"{hn}_perdijet.png", dpi=140)
                plt.close(fig)

            n_mjj += 1
            continue

        # ---------------- Δφ core flow ----------------
        dphi_tag = parse_dphi_name(hn)
        if not dphi_tag:
            continue

        Rname, ptlo, pthi, is_abs = dphi_tag
        Ruse = R_cfg if (Rname is None or np.isnan(Rname)) else Rname
        isAll = (not np.isfinite(ptlo)) or (not np.isfinite(pthi))
        ttl_pt = (rf"$p_{{T,1}}$: {PT_ALL_LABEL}" if isAll else rf"$p_{{T,1}}\in[{int(ptlo)},{int(pthi)}]$ GeV")

        dphi_integral_mb = float(np.nansum(yc * bw))

        ibin = find_pt_bin(ptlo, pthi)
        fit_win_deg = fit_win_scalar
        if use_array_win and 0 <= ibin < len(win_per):
            fit_win_deg = win_per[ibin]
        win = to_rad(fit_win_deg)

        d_to_pi = np.array([wrap_distance_to_pi(x) for x in xc])
        in_win = d_to_pi <= win
        x1_fit = pi - win
        x2_fit = pi if is_abs else (pi + win)
        canFit = np.count_nonzero(np.isfinite(yc) & np.isfinite(ye) & (ye > 0) & (yc >= 0) & in_win) >= 3

        fit_ok = False
        if canFit:
            try:
                C, A, mu, sg, C_err, mu_err, sg_err, chi2, ndf = fit_gauss_const(xc, yc, ye, x1_fit, x2_fit, fix_mu=is_abs)
                fit_ok = True
            except Exception as e:
                _log(f"[WARN] Fit failed for {hn}: {e}")
                side = ~in_win
                C = np.nanmedian(yc[side]) if np.any(side) else 0.0
                A, mu, sg = 0.0, pi, to_rad(5.0)
                C_err = mu_err = sg_err = float("nan")
                chi2, ndf = float("nan"), 0
        else:
            side = ~in_win
            C = np.nanmedian(yc[side]) if np.any(side) else 0.0
            A, mu, sg = 0.0, pi, to_rad(5.0)
            C_err = mu_err = sg_err = float("nan")
            chi2, ndf = float("nan"), 0

        # Background-subtracted RMS within window
        #
        # IMPORTANT:
        #   - Fraction-like quantities (CDF / within-1σ / within-2σ) need a non-negative
        #     "signal" measure, so we CLIP negative (y-C) bins to 0 for those only.
        #   - For RMS we avoid that clipping bias by using a signed background-subtracted
        #     estimator (can include tiny negative contributions from oversubtraction noise).
        #     Bootstrap below MUST match this RMS estimator (see rms_mode).
        bins = []
        sumw_clip = sumwx_clip = sumwx2_clip = 0.0   # clipped signal (fractions/CDF)
        sumw_rms  = sumwx_rms  = sumwx2_rms  = 0.0   # signed signal (RMS)
        in1 = in2 = 0.0
        total_sig = 0.0
        neg_sig_bins = 0
        neg_sig_mb = 0.0
        for x, y, e, w in zip(xc, yc, ye, bw):
            if wrap_distance_to_pi(x) > win:
                continue
            # Negative bins can happen when the fitted constant C slightly overshoots due to noise.
            sig_raw = y - C
            if sig_raw < 0.0:
                neg_sig_bins += 1
                neg_sig_mb   += (-sig_raw) * w

            # CLIPPED "signal": used only for fractions / CDF proxies (must be non-negative).
            sig_clip = sig_raw if sig_raw > 0.0 else 0.0
            s_clip = sig_clip * w
            total_sig += s_clip
            dmu = abs(math.atan2(math.sin(x - mu), math.cos(x - mu)))
            if dmu <= sg:   in1 += s_clip
            if dmu <= 2*sg: in2 += s_clip
            sumw_clip  += s_clip
            sumwx_clip += s_clip * (x - mu)
            sumwx2_clip+= s_clip * (x - mu) * (x - mu)

            # SIGNED "signal": used for RMS to avoid clipping/truncation bias.
            s_rms = sig_raw * w
            sumw_rms  += s_rms
            sumwx_rms += s_rms * (x - mu)
            sumwx2_rms+= s_rms * (x - mu) * (x - mu)

            # Store per-bin data for bootstrap and CDF calculations.
            bins.append((dmu, sig_clip * w, x, w, y, e))
        # RMS estimator choice:
        #   Prefer signed background-subtracted RMS (no clipping bias).
        #   If the signed total weight is non-positive (pathological oversubtraction / too-low stats),
        #   fall back to the clipped estimator and WARN loudly.
        rms_mode = "signed"
        sumw_use, sumwx_use, sumwx2_use = sumw_rms, sumwx_rms, sumwx2_rms
        if not (np.isfinite(sumw_use) and sumw_use > 0.0) and (np.isfinite(sumw_clip) and sumw_clip > 0.0):
            rms_mode = "clipped_fallback"
            sumw_use, sumwx_use, sumwx2_use = sumw_clip, sumwx_clip, sumwx2_clip
            _log(f"WARN: RMS signed weight non-positive (sumw_rms={sumw_rms:.6g}). Falling back to clipped RMS (sumw_clip={sumw_clip:.6g}).")

        mean_shift = float("nan")
        varr = float("nan")
        if np.isfinite(sumw_use) and sumw_use > 0.0:
            mean_shift = sumwx_use / sumw_use
            varr = (sumwx2_use / sumw_use) - mean_shift**2
            # Guard against tiny negative variance from floating point rounding.
            if np.isfinite(varr) and varr < 0.0 and varr > -1e-15:
                varr = 0.0
            if not (np.isfinite(varr) and varr >= 0.0):
                varr = float("nan")
        rms_bkgsub = math.sqrt(varr) if (np.isfinite(varr) and varr >= 0.0) else float("nan")

        rng = np.random.default_rng(0xC0FFEE ^ int(round(mu*1e6)))
        NBOOT = 400
        rms_samples = []
        if bins:
            C_dist_sigma = C_err if (np.isfinite(C_err) and C_err > 0) else 1e-12
            for _ in range(NBOOT):
                # Toy model: fluctuate fitted background C and each bin content y by its stat error.
                # This captures the dominant finite-stat uncertainty on RMS (not just the C-fit uncertainty).
                Cb = rng.normal(C, C_dist_sigma)
                sw = swx = swx2 = 0.0
                for dmu, s0, x, w, y, e in bins:
                    yb = y
                    if np.isfinite(e) and e > 0.0 and np.isfinite(y):
                        yb = rng.normal(y, e)
                    sig_raw = yb - Cb
                    # Bootstrap MUST match the RMS estimator used for the central value (rms_mode).
                    if rms_mode == "clipped_fallback":
                        sig = sig_raw if sig_raw > 0.0 else 0.0
                    else:
                        sig = sig_raw
                    s = sig * w
                    sw += s
                    swx += s * (x - mu)
                    swx2 += s * (x - mu) * (x - mu)
                if sw > 0:
                    mshift = swx / sw
                    v = (swx2 / sw) - mshift**2
                    # Guard against tiny negative variance from rounding; otherwise skip.
                    if np.isfinite(v) and v < 0.0 and v > -1e-15:
                        v = 0.0
                    if np.isfinite(v) and v >= 0.0:
                        rms_samples.append(math.sqrt(v))
        rms_err = float(np.nanstd(rms_samples)) if rms_samples else float("nan")

        # fraction-based "theta" proxies
        frac_1sigma = in1/total_sig if total_sig>0 else float("nan")
        frac_2sigma = in2/total_sig if total_sig>0 else float("nan")
        frac_RMS    = float("nan")
        if bins and total_sig > 0:
            # cumulative in theta: sort by dmu, then enforce monotone CDF via isotonic regression
            bins_sorted = sorted(bins, key=lambda t: t[0])
            cum = 0.0
            thetas = []
            fracs = []
            for dmu, s, x, w, y, e in bins_sorted:
                cum += s
                thetas.append(dmu)
                fracs.append(cum / total_sig)
            fracs_iso = isotonic_regression_increasing(np.asarray(fracs))
            for dmu, f in zip(thetas, fracs_iso):
                if f >= 0.682689492:
                    frac_RMS = dmu
                    break
            theta_rms = rms_bkgsub
        else:
            theta_rms = float("nan")

        # delta mu from pi
        dmu_pi = abs(math.atan2(math.sin(mu - pi), math.cos(mu - pi)))

        # --------------------------------- plotting ---------------------------------
        ns = _is_nosubfrac(hn, in_ns_dir)
        dphi_title = (r"Dijet azimuthal decorrelation: $|\Delta\varphi|$ (folded to $[0,\pi]$)" if is_abs else r"Dijet azimuthal decorrelation: $\Delta\varphi$")


        fig, ax = plt.subplots(figsize=(9,7))
        ax.errorbar(xc, yc, yerr=yerr_for_plot_absolute(yc, ye, xsec_plot_term), fmt="o", ms=DEFAULT_MARKER_SIZE, lw=DEFAULT_LINE_WIDTH, capsize=2, label="XSCAPE")
        if not is_abs:
            ax.axvline(pi, color="k", ls="--", lw=DEFAULT_LINE_WIDTH)
        if is_abs:
            ax.axvspan(pi-win, pi, alpha=0.1, label=rf"fit window ($|\Delta\varphi-\pi|<{fit_win_deg:g}^\circ$; truncated at $\pi$)")
        else:
            ax.axvspan(pi-win, (pi+win), alpha=0.1, label=rf"fit window ($|\Delta\varphi-\pi|<{fit_win_deg:g}^\circ$)")
        if is_abs:
            ax.set_xlabel(r"$|\Delta\varphi|$ (rad), folded to $[0,\pi]$")
            dphi_abs_ylabel = r"$d\sigma_{\mathrm{dijet}}/d|\Delta\varphi|$ (mb/rad)"
        else:
            ax.set_xlabel(r"$\Delta\varphi$ (rad)")
            dphi_abs_ylabel = r"$d\sigma_{\mathrm{dijet}}/d\Delta\varphi$ (mb/rad)"
        ax.set_ylabel(dphi_abs_ylabel)
        title_str = f"{dphi_title}  [{ttl_pt}; R={Ruse:.2f}; {_dphi_title_cuts(Ruse)}]" + (" [nosubfrac]" if ns else "")
        # NOTE: Analyzer does NOT apply a back-to-back selection for Δφ histograms; keep titles selection-free.
        ax.set_title(title_str)

        # fit curve
        dom_max = (pi if is_abs else 2*pi)
        ax.set_xlim(0, dom_max)
        xx = np.linspace(0, dom_max, 800)
        yy = gauss_const(xx, C, A, mu, sg)
        ax.plot(xx, yy, lw=DEFAULT_LINE_WIDTH*0.5, label="Gaussian+const fit")
        ax.text(0.02, 0.98,
                f"μ={mu:.4f}±{mu_err:.4f}\nσ={sg:.4f}±{sg_err:.4f}\nC={C:.3e}±{C_err:.3e}\nχ²/ndf={chi2:.1f}/{ndf:d}\n"
                f"RMS(bkgsub)={rms_bkgsub:.4f}±{rms_err:.4f}\nΔμ from π={dmu_pi:.4f}\n"
                f"neg bins={neg_sig_bins} (neg mb≈{neg_sig_mb:.2e})",
                transform=ax.transAxes, va="top", ha="left",
                fontsize=_FONTS['note'], bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8, edgecolor="black"))
        try:
            ax.legend(loc="best", frameon=False, fontsize=_FONTS.get("legend", None))
        except Exception:
            pass


        fig.tight_layout()
        # Legacy directory (pre-v3.5)
        out_dphi_dir = out_dir_fit_abs if is_abs else out_dir_fit
        # Standard directories
        out_dphi_dir_abs_std  = out_dir_fit_abs0pi_std if is_abs else out_dir_fit_abs_std
        out_dphi_dir_norm_std = out_dir_fit_abs0pi_norm_std if is_abs else out_dir_fit_norm_std

        # (v4.9.43) Legacy duplicate output removed: Δφ plots are written under absolute/ and dijet_normalized/
        _savefig_branch(fig, "absolute", ("dphi_fit_abs0pi" if is_abs else "dphi_fit"), ns, f"{hn}.png", dpi=140)
        plt.close(fig)

        # ------------------------- per-selection normalized Δφ -------------------------
        # Convert dσ/dX (mb/rad) → (1/σ_sel) dσ/dX (1/rad) for shape comparisons,
        # where X is Δφ for oriented histograms and |Δφ| for folded histograms.
        sig_dijet, ycn, yen, covn, covn_mode = normalize_per_dijet_with_matrix(yc, ye, bw, denom_positive_only=False, cov_mode=PERDIJET_COV_MODE)
        if np.isfinite(sig_dijet) and sig_dijet > 0 and ycn is not None:

            norm_fit_mode = "full normalized covariance" if covn_mode == "full" else "diagonal fallback"
            try:
                if covn is None:
                    raise RuntimeError("normalized covariance matrix is unavailable")
                Cn, An, mun, sgn, Cn_err, mun_err, sgn_err, chi2n, ndfn = fit_gauss_const_cov(xc, ycn, covn, x1_fit, x2_fit, fix_mu=is_abs)
                _log(f"[dphi-shape-fit] {hn}: mode={covn_mode} chi2/ndf={chi2n:.6g}/{ndfn:d} sigma={sgn:.6g}±{sgn_err:.6g}")
            except Exception as e:
                _log(f"[WARN] Normalized covariance fit failed for {hn}: {e}; falling back to diagonal-only normalized fit.")
                norm_fit_mode = "diagonal fallback"
                try:
                    Cn, An, mun, sgn, Cn_err, mun_err, sgn_err, chi2n, ndfn = fit_gauss_const(xc, ycn, yen, x1_fit, x2_fit, fix_mu=is_abs)
                except Exception as e2:
                    _log(f"[WARN] Normalized diagonal fallback fit also failed for {hn}: {e2}; reusing absolute-fit parameters scaled by sigma_sel.")
                    Cn, An, mun, sgn = (C / sig_dijet), (A / sig_dijet), mu, sg
                    Cn_err, mun_err, sgn_err = float("nan"), mu_err, sg_err
                    chi2n, ndfn = float("nan"), 0

            fig, ax = plt.subplots(figsize=(9,7))
            dphi_count = None
            dphi_norm_label = "XSCAPE"
            if SINGLE_SLICE_MODE and SELECTED_DIJET_COUNTS is not None:
                dphi_count = SELECTED_DIJET_COUNTS.count_for("dphi", Ruse, is_nosubfrac=ns, ptlo=ptlo, pthi=pthi, is_abs=is_abs)
                dphi_norm_label = _legend_count_label("dphi", dphi_count, is_abs=is_abs)
            errorbar_nan_safe(ax, xc, ycn, yen, fmt="o", ms=DEFAULT_MARKER_SIZE, lw=DEFAULT_LINE_WIDTH, capsize=2, label=dphi_norm_label)
            if not is_abs:
                ax.axvline(pi, color="k", ls="--", lw=DEFAULT_LINE_WIDTH)
            if is_abs:
                ax.axvspan(pi-win, pi, alpha=0.1, label=rf"fit window ($|\Delta\varphi-\pi|<{fit_win_deg:g}^\circ$; truncated at $\pi$)")
            else:
                ax.axvspan(pi-win, (pi+win), alpha=0.1, label=rf"fit window ($|\Delta\varphi-\pi|<{fit_win_deg:g}^\circ$)")
            if is_abs:
                ax.set_xlabel(r"$|\Delta\varphi|$ (rad), folded to $[0,\pi]$")
                dphi_shape_ylabel = (_single_slice_norm_ylabel("dphi", is_abs=True) if SINGLE_SLICE_MODE else r"$(1/\sigma_{\mathrm{sel}})\,d\sigma/d|\Delta\varphi|$ (1/rad)")
                dphi_shape_title = (_single_slice_norm_title("dphi", is_abs=True) if SINGLE_SLICE_MODE else r"$1/\sigma_{\mathrm{sel}} \cdot d\sigma/d|\Delta\varphi|$")
            else:
                ax.set_xlabel(r"$\Delta\varphi$ (rad)")
                dphi_shape_ylabel = (_single_slice_norm_ylabel("dphi", is_abs=False) if SINGLE_SLICE_MODE else r"$(1/\sigma_{\mathrm{sel}})\,d\sigma/d\Delta\varphi$ (1/rad)")
                dphi_shape_title = (_single_slice_norm_title("dphi", is_abs=False) if SINGLE_SLICE_MODE else r"$1/\sigma_{\mathrm{sel}} \cdot d\sigma/d\Delta\varphi$")
            ax.set_ylabel(dphi_shape_ylabel)
            title_str = rf"{dphi_title} (shape: {dphi_shape_title})  [{ttl_pt}; R={Ruse:.2f}; {_dphi_title_cuts(Ruse)}]" + (" [nosubfrac]" if ns else "")
            # NOTE: Analyzer does NOT apply a back-to-back selection for Δφ histograms; keep titles selection-free.
            ax.set_title(title_str)

            dom_max = (pi if is_abs else 2*pi)
            ax.set_xlim(0, dom_max)
            xx = np.linspace(0, dom_max, 800)
            yy = gauss_const(xx, Cn, An, mun, sgn)
            ax.plot(xx, yy, lw=DEFAULT_LINE_WIDTH*0.5, label="Gaussian+const fit")
            ax.text(0.02, 0.98,
                    f"shape fit mode={norm_fit_mode}\nμ={mun:.4f}±{mun_err:.4f}\nσ={sgn:.4f}±{sgn_err:.4f}\nC={Cn:.3e}±{Cn_err:.3e}\nχ²/ndf={chi2n:.1f}/{ndfn:d}",
                    transform=ax.transAxes, va="top", ha="left",
                    fontsize=_FONTS['note'], bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8, edgecolor="black"))
            try:
                ax.legend(loc="best", frameon=False, fontsize=_FONTS.get("legend", None))
            except Exception:
                pass


            fig.tight_layout()
            # (v4.9.43) Legacy duplicate output removed: Δφ per-dijet plots are written under dijet_normalized/
            _savefig_branch(fig, "dijet_normalized", ("dphi_fit_abs0pi" if is_abs else "dphi_fit"), ns, f"{hn}_perdijet.png", dpi=140)
            plt.close(fig)


        # ----------------------------- frac vs theta plot -----------------------------
        # theta grid up to THETA_SCAN_MAX_DEG
        theta_deg = theta_deg_grid
        theta = theta_grid

        # Build cumulative fraction vs theta using bkg-subtracted signal in window.
        # With UNCLIPPED (signed) bins, the raw cumulative fraction can be non-monotone.
        # For any theta-at-fraction extraction (searchsorted), we enforce a monotone CDF envelope.
        frac_vs_theta = np.zeros_like(theta, dtype=float)
        if bins and total_sig > 0:
            # bins contain (dmu, s, x, w, y, e) with s = (y-C)*w and may be signed.
            bins_sorted = sorted(bins, key=lambda t: t[0])
            cum = 0.0
            bi = 0
            for k, th in enumerate(theta):
                while bi < len(bins_sorted) and bins_sorted[bi][0] <= th:
                    cum += bins_sorted[bi][1]
                    bi += 1
                frac_vs_theta[k] = cum / total_sig

            # Monotone envelope in [0,1] (anchor 0 at start, 1 at end) so searchsorted is well-defined.
            frac_clip = np.clip(frac_vs_theta, 0.0, 1.0)
            frac_clip = np.nan_to_num(frac_clip, nan=0.0, posinf=1.0, neginf=0.0)
            frac_mono = isotonic_regression_increasing(np.concatenate(([0.0], frac_clip, [1.0])))
            frac_vs_theta = frac_mono[1:-1]
        else:
            frac_vs_theta[:] = 0.0

        # Convert a few "theta at fraction" from fit (Gaussian CDF) and from histogram cumulative
        theta_fit = []
        theta_fit_err = []
        theta_hist = []
        if np.isfinite(sg) and sg > 0 and fit_ok:
            for a in fracs:
                # Gaussian around mu: fraction within +/- theta is erf(theta/(sqrt(2)*sg))
                th = math.sqrt(2.0) * sg * erfinv(a)
                theta_fit.append(th)
                # naive propagation for theta from sg_err
                if np.isfinite(sg_err) and sg_err > 0:
                    theta_fit_err.append(abs(th) * (sg_err/sg))
                else:
                    theta_fit_err.append(float("nan"))
        else:
            theta_fit = [float("nan")]*len(fracs)
            theta_fit_err = [float("nan")]*len(fracs)

        for a in fracs:
            idx = int(np.searchsorted(frac_vs_theta, a, side="left"))
            if idx <= 0:
                thh = float(theta[0])
            elif idx >= len(theta):
                thh = float(theta[-1])
            else:
                thh = float(theta[idx])
            theta_hist.append(thh)

        fig, ax3 = plt.subplots(figsize=(6.0, 4.2))
        ax3.plot(theta_deg, frac_vs_theta, lw=DEFAULT_LINE_WIDTH*0.8)
        ax3.set_xlim(0, max(90.0, th_scan_max_deg)); ax3.set_ylim(0, 1.02)
        ax3.set_xlabel(r"$\theta$ (deg)")
        ax3.set_ylabel("Cumulative fraction (bkg-sub)")
        ax3.set_title(f"Frac vs θ  [{ttl_pt}; R={Ruse:.2f}]")
        for a, thf, thh in zip(fracs, theta_fit, theta_hist):
            if np.isfinite(thf):
                ax3.axvline(to_deg(thf), ls="--", lw=DEFAULT_LINE_WIDTH, alpha=0.7)
            if np.isfinite(thh):
                ax3.axvline(to_deg(thh), ls=":", lw=DEFAULT_LINE_WIDTH, alpha=0.7)
        fig.tight_layout()
        _savefig_branch(fig, "absolute", ("dphi_fit_abs0pi" if is_abs else "dphi_fit"), ns, f"frac_vs_theta_{hn}.png", dpi=150)
        plt.close(fig)
        n_frac += 1

        # ----------------------------- CSV row -----------------------------
        row = [
            f"{Ruse:.3f}", hn, (PT_ALL_LABEL if isAll else f"{int(ptlo)}-{int(pthi)}"),
            f"{mu:.10f}", f"{to_deg(mu):.10f}", f"{mu_err:.10f}", f"{to_deg(mu_err):.10f}",
            f"{sg:.10f}", f"{to_deg(sg):.10f}", f"{sg_err:.10f}", f"{to_deg(sg_err):.10f}",
            f"{C:.10e}", f"{C_err:.10e}", f"{A:.10e}",
            f"{chi2:.6f}", f"{ndf:d}",
            f"{rms_bkgsub:.10f}", f"{to_deg(rms_bkgsub):.10f}",
            f"{(theta_rms if np.isfinite(theta_rms) else float('nan')):.10f}",
            f"{(to_deg(theta_rms) if np.isfinite(theta_rms) else float('nan')):.10f}",
            f"{(rms_err if np.isfinite(rms_err) else float('nan')):.10f}",
            f"{(to_deg(rms_err) if np.isfinite(rms_err) else float('nan')):.10f}",
            f"{frac_1sigma:.10f}", f"{frac_2sigma:.10f}",
            f"{(frac_RMS if np.isfinite(frac_RMS) else float('nan')):.10f}",
            f"{dmu_pi:.10f}", f"{to_deg(dmu_pi):.10f}",
            f"{dphi_integral_mb:.10e}"
        ]
        for a, thf, thf_e, thh in zip(fracs, theta_fit, theta_fit_err, theta_hist):
            row += [f"{thf:.10f}", f"{to_deg(thf):.10f}",
                    f"{thf_e:.10f}", f"{to_deg(thf_e):.10f}",
                    f"{thh:.10f}", f"{to_deg(thh):.10f}"]
        out_csv.write(",".join(row) + "\n"); n_dphi += 1

        # Width aggregation: ONLY trust successful fits
        if fit_ok and np.isfinite(sg) and sg > 0:
            width_branch = widths_by_R_abs if is_abs else widths_by_R_full
            width_branch[bool(ns)][Ruse].append(
                (sg, (sg_err if np.isfinite(sg_err) else float("nan")), max(0.0, dphi_integral_mb))
            )

    out_csv.close()


    # ---------------------- NEW: dijet imbalance (xJ/AJ) + jet R dependence ----------------------
    # These histograms are produced by analyze_dphi_sliced.cpp v5.8+.
    try:
        xj_map = {}     # (is_nosubfrac, R) -> dict(hn, xc,yc,ye,bw)
        aj_map = {}     # (is_nosubfrac, R) -> dict(hn, xc,yc,ye,bw)
        jetpt_map = {}  # (is_nosubfrac, kind, R) -> dict(hn, xc,yc,ye,bw)

        for item in read_root_histograms(INPUT_ROOT):
            if len(item) == 8:
                hn, xc, yc, ye, bw, var2, entries2, in_ns_dir2 = item
            else:
                hn, xc, yc, ye, bw, var2, entries2 = item
                in_ns_dir2 = False
            Rxj = parse_xj_name(hn)
            if Rxj is not None:
                Rv, ns, ptlo_xj, pthi_xj, is_full_xj = Rxj
                ns = bool(ns) or bool(in_ns_dir2)
                xj_map[(ns, Rv, ptlo_xj, pthi_xj, bool(is_full_xj))] = dict(hn=hn, xc=xc, yc=yc, ye=ye, bw=bw, xsec_norm_err=(xsec_band_builder.norm_err_for_hist(hn, xc, bw, in_ns_dir=in_ns_dir2) if INCLUDE_XSEC_NORM_ERR and xsec_band_builder is not None else xsec_rel_err))
                continue
            Raj = parse_aj_name(hn)
            if Raj is not None:
                Rv, ns, ptlo_aj, pthi_aj, is_full_aj = Raj
                ns = bool(ns) or bool(in_ns_dir2)
                aj_map[(ns, Rv, ptlo_aj, pthi_aj, bool(is_full_aj))] = dict(hn=hn, xc=xc, yc=yc, ye=ye, bw=bw, xsec_norm_err=(xsec_band_builder.norm_err_for_hist(hn, xc, bw, in_ns_dir=in_ns_dir2) if INCLUDE_XSEC_NORM_ERR and xsec_band_builder is not None else xsec_rel_err))
                continue
            jt = parse_jetpt_name(hn)
            if jt is not None:
                kind, Rj, ns = jt
                ns = bool(ns) or bool(in_ns_dir2)
                # only use the inclusive/lead/sublead all-hists
                jetpt_map[(ns, kind, Rj)] = dict(hn=hn, xc=xc, yc=yc, ye=ye, bw=bw, xsec_norm_err=(xsec_band_builder.norm_err_for_hist(hn, xc, bw, in_ns_dir=in_ns_dir2) if INCLUDE_XSEC_NORM_ERR and xsec_band_builder is not None else xsec_rel_err))
                continue

        def _shape_stats(xc, y, bw):
            s = y * bw
            S = float(np.nansum(s))
            if not (np.isfinite(S) and S > 0):
                return (float('nan'), float('nan'))
            mu = float(np.nansum(s * xc) / S)
            varx = float(np.nansum(s * (xc - mu) ** 2) / S)
            return (mu, math.sqrt(max(0.0, varx)))

        h2_sublead_vs_lead_map = {}
        prof_sublead_vs_lead_map = {}

        for item in read_root_th2(INPUT_ROOT):
            hn2, xedges2, yedges2, zvals2, zerr2, zvar2, entries2, in_ns_dir2 = item
            parsed2 = parse_sublead_vs_lead_h2_name(hn2)
            if parsed2 is None:
                continue
            Rv, ns = parsed2
            ns = bool(ns) or bool(in_ns_dir2)
            h2_sublead_vs_lead_map[(ns, Rv)] = dict(hn=hn2, xedges=xedges2, yedges=yedges2, zvals=zvals2, zerr=zerr2, zvar=zvar2, entries=entries2)

        for item in read_root_profiles(INPUT_ROOT):
            hnp, xcp, yvp, yep, bwp, varp, entriesp, in_ns_dirp = item
            parsedp = parse_sublead_vs_lead_profile_name(hnp)
            if parsedp is None:
                continue
            Rv, ns = parsedp
            ns = bool(ns) or bool(in_ns_dirp)
            prof_sublead_vs_lead_map[(ns, Rv)] = dict(hn=hnp, xc=xcp, yc=yvp, ye=yep, bw=bwp, var=varp, entries=entriesp)

        _log(
            "[parse-summary] lead-sublead observables in second pass: "
            + f"th2={len(h2_sublead_vs_lead_map)} "
            + f"tprofile={len(prof_sublead_vs_lead_map)}"
        )

        for (ns, Ruse), dat in sorted(h2_sublead_vs_lead_map.items(), key=lambda t: (t[0][1], t[0][0])):
            hn2 = dat['hn']
            xedges = np.asarray(dat['xedges'], dtype=float)
            yedges = np.asarray(dat['yedges'], dtype=float)
            zvals = np.asarray(dat['zvals'], dtype=float)
            if zvals.ndim != 2 or zvals.shape != (len(xedges)-1, len(yedges)-1):
                _log(f"[WARN] Skipping {hn2}: unexpected TH2 shape {zvals.shape} for edges {(len(xedges)-1, len(yedges)-1)}")
                continue
            zplot = np.asarray(zvals, dtype=float).T
            finite_pos = zplot[np.isfinite(zplot) & (zplot > 0)]
            fig, ax = plt.subplots(figsize=(8.8, 7.2))
            if finite_pos.size > 0:
                pcm = ax.pcolormesh(xedges, yedges, np.ma.masked_less_equal(zplot, 0.0), shading='auto', norm=LogNorm(vmin=float(np.min(finite_pos)), vmax=float(np.max(finite_pos))))
                cbar = fig.colorbar(pcm, ax=ax)
                cbar.set_label('Weighted dijet yield [mb]')
            else:
                pcm = ax.pcolormesh(xedges, yedges, zplot, shading='auto')
                cbar = fig.colorbar(pcm, ax=ax)
                cbar.set_label('Weighted dijet yield [mb]')
            ax.set_xscale('log')
            ax.set_yscale('log')
            ax.set_xlim(max(1e-6, float(xedges[0])), float(xedges[-1]))
            ax.set_ylim(max(1e-6, float(yedges[0])), float(yedges[-1]))
            ax.plot([max(1e-6, float(xedges[0])), float(xedges[-1])], [max(1e-6, float(xedges[0])), float(xedges[-1])], ls='--', lw=DEFAULT_LINE_WIDTH, color='white', alpha=0.9)
            ax.set_xlabel(r"Leading jet $p_T$ (GeV)")
            ax.set_ylabel(r"Subleading jet $p_T$ (GeV)")
            ax.set_title(f"Subleading vs leading jet $p_T$  [$p_{{T,1}}$: {PT_ALL_LABEL}; R={Ruse:.2f}{_dijet_pair_title_tag()}]" + (" [nosubfrac]" if ns else " [subfrac]"))
            fig.tight_layout()
            _savefig_branch(fig, "absolute", "lead_sublead_correlation", ns, f"{hn2}.png", dpi=160)
            plt.close(fig)

        for (ns, Ruse), dat in sorted(prof_sublead_vs_lead_map.items(), key=lambda t: (t[0][1], t[0][0])):
            hnp = dat['hn']
            xc = np.asarray(dat['xc'], dtype=float)
            yc = np.asarray(dat['yc'], dtype=float)
            ye = np.asarray(dat['ye'], dtype=float)
            bw = np.asarray(dat['bw'], dtype=float)
            m = np.isfinite(xc) & np.isfinite(yc) & np.isfinite(ye) & (xc > 0) & (yc > 0)
            if not np.any(m):
                _log(f"[WARN] Skipping {hnp}: no finite positive profile points")
                continue
            xlo = float(np.min(xc[m] - 0.5*bw[m]))
            xhi = float(np.max(xc[m] + 0.5*bw[m]))
            ylow = yc[m] - np.where(np.isfinite(ye[m]), ye[m], 0.0)
            yhigh = yc[m] + np.where(np.isfinite(ye[m]), ye[m], 0.0)
            ylow_pos = ylow[np.isfinite(ylow) & (ylow > 0)]
            ymin = float(np.min(ylow_pos)) if ylow_pos.size > 0 else float(np.min(yc[m]))
            ymax = float(np.max(yhigh[np.isfinite(yhigh)]))
            fig, ax = plt.subplots(figsize=(8.8, 6.2))
            errorbar_nan_safe(ax, xc[m], yc[m], ye[m], fmt='o-', ms=DEFAULT_MARKER_SIZE, lw=DEFAULT_LINE_WIDTH, capsize=2, label='simulation mean')
            ax.set_xscale('log')
            ax.set_yscale('log')
            ax.set_xlim(max(1e-6, xlo), xhi)
            ax.set_ylim(max(1e-6, ymin), max(max(1e-6, ymin) * 1.05, ymax))
            ax.plot([max(1e-6, xlo), xhi], [max(1e-6, xlo), xhi], ls='--', lw=DEFAULT_LINE_WIDTH, color='k', alpha=0.7, label=r'$p_{T}^{sublead}=p_{T}^{lead}$')
            ax.set_xlabel(r"Leading jet $p_T$ (GeV)")
            ax.set_ylabel(r"$\langle p_T^{sublead} \rangle$ (GeV)")
            ax.set_title(f"Mean subleading jet $p_T$ vs leading jet $p_T$  [$p_{{T,1}}$: {PT_ALL_LABEL}; R={Ruse:.2f}{_dijet_pair_title_tag()}; {_ptlead_profile_title_tag()}]" + (" [nosubfrac]" if ns else " [subfrac]"))
            ax.legend(loc='best', fontsize=_FONTS['legend'])
            fig.tight_layout()
            _savefig_branch(fig, "absolute", "lead_sublead_correlation", ns, f"{hnp}.png", dpi=160)
            plt.close(fig)


        # ---- Jet pT spectra (absolute + per-selection normalized) ----
        # The analyzer produces jetpt_{incl,lead,sublead}_Rxxx_all (and optional *_nosubfrac)
        # but older fitter versions only used these for the R=0.2/0.4 ratio plot.
        # Here we write the actual spectra so every analyzer observable is visible.
        def _jetpt_kind_title(k: str) -> str:
            dijet_tag = _dijet_pair_title_tag()
            if k == "incl":
                return "Inclusive jet $p_T$ spectrum"
            if k == "lead":
                return f"Leading jet $p_T$ spectrum (dijet-selected{dijet_tag})"
            if k == "sublead":
                return f"Subleading jet $p_T$ spectrum (dijet-selected{dijet_tag})"
            return f"Jet $p_T$ spectrum ({k}{dijet_tag})"

        _log(f"[parse-summary] no-SUBFRAC matched in first pass: eta={ns_parse_counts['eta']} mjj={ns_parse_counts['mjj']} dphi/dphi_abs={ns_parse_counts['dphi']} unmatched={ns_parse_counts['other']}")
        if ns_parse_unmatched:
            for _hn_dbg in ns_parse_unmatched:
                _log(f"[parse-summary]   unmatched nosubfrac hist: {_hn_dbg}")
        _log(
            "[parse-summary] no-SUBFRAC matched in second pass: "
            + f"xj={sum(1 for (ns, _R, _ptlo, _pthi, _is_full) in xj_map.keys() if ns)} "
            + f"aj={sum(1 for (ns, _R, _ptlo, _pthi, _is_full) in aj_map.keys() if ns)} "
            + f"jetpt={sum(1 for (ns, _kind, _R) in jetpt_map.keys() if ns)}"
        )

        for (ns, kind, Ruse), dat in sorted(jetpt_map.items(), key=lambda t: (t[0][2], t[0][0], t[0][1])):
            hn_j = dat['hn']; xc = dat['xc']; yc = dat['yc']; ye = dat['ye']; bw = dat['bw']
            is_inclusive = (kind == "incl")
            ns_label = (" [nosubfrac]" if (ns and not is_inclusive) else "")

            yerr_plot = yerr_for_plot_absolute(yc, ye, dat["xsec_norm_err"] if isinstance(dat, dict) and "xsec_norm_err" in dat else xsec_plot_term)
            jetpt_xmin, jetpt_xmax = _jetpt_populated_xlim(xc, yc, bw, yerr_plot, x_floor=0.0, x_ceil=JET_PT_MAX)
            branch_tag = "inclusive-neutral" if is_inclusive else ("nosubfrac" if ns else "subfrac")
            _log(f"[jetpt-zoom] hist={hn_j} branch={branch_tag} R={Ruse:.2f} xlim=[{jetpt_xmin:.3f}, {jetpt_xmax:.3f}] GeV")

            # Absolute
            fig, ax = plt.subplots(figsize=(8.8, 6.2))
            ax.errorbar(xc, yc, yerr=yerr_plot, fmt="o", ms=DEFAULT_MARKER_SIZE, lw=DEFAULT_LINE_WIDTH, capsize=2, label="simulation")
            apply_logy_with_floor(ax, yc, yerr_plot)
            ax.set_xlim(jetpt_xmin, jetpt_xmax)
            ax.set_xlabel(r"$p_T$ (GeV)")
            ax.set_ylabel(r"$d\sigma/dp_T$ (mb/GeV)")
            ax.set_title(_jetpt_kind_title(kind) + f"  [R={Ruse:.2f}]" + ns_label)
            ax.text(0.02, 0.02, "display x-range auto-zoomed to populated bins",
                    transform=ax.transAxes, va="bottom", ha="left", fontsize=_FONTS['note'],
                    bbox=dict(boxstyle="round,pad=0.25", facecolor="white", alpha=0.8, edgecolor="black"))
            ax.legend(loc="best", fontsize=_FONTS['legend'])
            fig.tight_layout()
            if is_inclusive:
                _savefig_neutral(fig, "absolute", "jet_spectra", f"{hn_j}.png", dpi=150)
            else:
                _savefig_branch(fig, "absolute", "jet_spectra", ns, f"{hn_j}.png", dpi=150)
            plt.close(fig)

            # Normalized shape (1/GeV)
            sig, ycn, yen = normalize_per_dijet_with_cov(yc, ye, bw, denom_positive_only=False, cov_mode=PERDIJET_COV_MODE)
            if np.isfinite(sig) and sig > 0 and ycn is not None and yen is not None:
                fig, ax = plt.subplots(figsize=(8.8, 6.2))
                legend_label = "simulation"
                ax.set_xlim(jetpt_xmin, jetpt_xmax)
                ax.set_xlabel(r"$p_T$ (GeV)")
                if is_inclusive:
                    ax.set_ylabel(r"$(1/\sigma_{\mathrm{incl}})\,d\sigma/dp_T$ (1/GeV)")
                    ax.set_title(_jetpt_kind_title(kind) + f" (unit-normalized shape)  [R={Ruse:.2f}]")
                    stat_label = rf"$\sigma_{{\mathrm{{incl}}}}$={sig:.3e} mb"
                else:
                    if SINGLE_SLICE_MODE and SELECTED_DIJET_COUNTS is not None:
                        count_sel = SELECTED_DIJET_COUNTS.count_for("sel", Ruse, is_nosubfrac=ns)
                        ax.set_ylabel(_single_slice_norm_ylabel("sel"))
                        ax.set_title(_jetpt_kind_title(kind) + f" (single-slice count normalized)  [R={Ruse:.2f}]" + ns_label)
                        stat_label = f"N_dijet,sel={count_sel}"
                        legend_label = _legend_count_label("sel", count_sel)
                    else:
                        ax.set_ylabel(r"$(1/\sigma_{\mathrm{sel}})\,d\sigma/dp_T$ (1/GeV)")
                        ax.set_title(_jetpt_kind_title(kind) + f" (per-selection normalized)  [R={Ruse:.2f}]" + ns_label)
                        stat_label = rf"$\sigma_{{\mathrm{{sel}}}}$={sig:.3e} mb"
                errorbar_nan_safe(ax, xc, ycn, yen, fmt="o", ms=DEFAULT_MARKER_SIZE, lw=DEFAULT_LINE_WIDTH, capsize=2, label=legend_label)
                apply_logy_with_floor(ax, ycn, yen)
                ax.text(0.98, 0.98, stat_label,
                        transform=ax.transAxes, va="top", ha="right", fontsize=_FONTS['note'],
                        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.85, edgecolor="black"))
                ax.text(0.02, 0.02, "display x-range auto-zoomed to populated bins",
                        transform=ax.transAxes, va="bottom", ha="left", fontsize=_FONTS['note'],
                        bbox=dict(boxstyle="round,pad=0.25", facecolor="white", alpha=0.8, edgecolor="black"))
                ax.legend(loc="best", fontsize=_FONTS['legend'])
                fig.tight_layout()
                if is_inclusive:
                    _savefig_neutral(fig, "inclusive_unit_normalized", "jet_spectra", f"{hn_j}_unitshape.png", dpi=150)
                else:
                    _savefig_branch(fig, "dijet_normalized", "jet_spectra", ns, f"{hn_j}_perdijet.png", dpi=150)
                plt.close(fig)
        # ---- xJ plots ----
        for (ns, Ruse, ptlo_xj, pthi_xj, is_full_xj), dat in sorted(xj_map.items(), key=lambda t: (t[0][1], t[0][0], 1 if t[0][4] else 0, (-1e99 if not np.isfinite(t[0][2]) else t[0][2]), (-1e99 if not np.isfinite(t[0][3]) else t[0][3]))):
            hn_xj = dat['hn']; xc = dat['xc']; yc = dat['yc']; ye = dat['ye']; bw = dat['bw']
            mu, rms = _shape_stats(xc, yc, bw)
            ttl_pt = (rf"$p_{{T,1}}$: {PT_ALL_LABEL}" if (is_full_xj or (not np.isfinite(ptlo_xj)) or (not np.isfinite(pthi_xj))) else rf"$p_{{T,1}}\in[{int(ptlo_xj)},{int(pthi_xj)}]$ GeV")
            fig, ax = plt.subplots(figsize=(8.5, 6.0))
            yerr_plot = yerr_for_plot_absolute(yc, ye, dat["xsec_norm_err"] if isinstance(dat, dict) and "xsec_norm_err" in dat else xsec_plot_term)
            ax.errorbar(xc, yc, yerr=yerr_plot, fmt='o', ms=DEFAULT_MARKER_SIZE, lw=DEFAULT_LINE_WIDTH, capsize=2)
            apply_logy_with_floor(ax, yc, yerr_plot)
            ax.set_xlabel(r"$x_J = p_{T2}/p_{T1}$")
            ax.set_ylabel(r"$d\sigma/dx_J$ (mb per unit $x_J$)")
            base_title = f"Dijet momentum ratio $x_{{J}}\\equiv p_{{T,2}}/p_{{T,1}}$  [{ttl_pt}; R={Ruse:.2f}{_imbalance_pair_title_tag()}]" + (" [nosubfrac]" if ns else "")
            scale_tag = " (log y)" if ax.get_yscale() == "log" else " (linear y)"
            ax.set_title(base_title + scale_tag)
            ax.set_xlim(0.0, 1.0)
            ax.text(0.98, 0.98, f"mean={mu:.3f}\nRMS={rms:.3f}", transform=ax.transAxes,
                    va='top', ha='right', fontsize=_FONTS['note'],
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.85, edgecolor='black'))
            fig.tight_layout()
            _savefig_branch(fig, "absolute", "dijet_imbalance", ns, f"{hn_xj}.png", dpi=150)
            plt.close(fig)

            sig, ycn, yen = normalize_per_dijet_with_cov(yc, ye, bw, denom_positive_only=False, cov_mode=PERDIJET_COV_MODE)
            if np.isfinite(sig) and sig > 0 and ycn is not None:
                mu_n, rms_n = _shape_stats(xc, ycn, bw)
                fig, ax = plt.subplots(figsize=(8.5, 6.0))
                xj_count = None
                xj_norm_label = None
                if SINGLE_SLICE_MODE and SELECTED_DIJET_COUNTS is not None:
                    xj_count = SELECTED_DIJET_COUNTS.count_for("xj", Ruse, is_nosubfrac=ns,
                                                              ptlo=(None if (is_full_xj or not np.isfinite(ptlo_xj) or not np.isfinite(pthi_xj)) else ptlo_xj),
                                                              pthi=(None if (is_full_xj or not np.isfinite(ptlo_xj) or not np.isfinite(pthi_xj)) else pthi_xj))
                    xj_norm_label = _legend_count_label("xj", xj_count)
                errorbar_nan_safe(ax, xc, ycn, yen, fmt="o", ms=DEFAULT_MARKER_SIZE, lw=DEFAULT_LINE_WIDTH, capsize=2, label=xj_norm_label)
                apply_logy_with_floor(ax, ycn, yen)
                ax.set_xlabel(r"$x_J = p_{T2}/p_{T1}$")
                ax.set_ylabel(_single_slice_norm_ylabel("xj") if SINGLE_SLICE_MODE else r"$(1/\sigma_{\mathrm{sel}})\,d\sigma/dx_J$ (1 per unit $x_J$)")
                norm_title_tag = "single-slice count normalized" if SINGLE_SLICE_MODE else "per-selection normalized"
                base_title = f"Dijet momentum ratio $x_J$ ({norm_title_tag})  [{ttl_pt}; R={Ruse:.2f}{_imbalance_pair_title_tag()}]" + (" [nosubfrac]" if ns else "")
                scale_tag = " (log y)" if ax.get_yscale() == "log" else " (linear y)"
                ax.set_title(base_title + scale_tag)
                ax.set_xlim(0.0, 1.0)
                note_tail = (f"N_dijet={xj_count}" if (SINGLE_SLICE_MODE and xj_count is not None) else f"σ_sel={sig:.3e} mb")
                ax.text(0.98, 0.98, f"mean={mu_n:.3f}\nRMS={rms_n:.3f}\n{note_tail}",
                        transform=ax.transAxes, va='top', ha='right', fontsize=_FONTS['note'],
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.85, edgecolor='black'))
                if SINGLE_SLICE_MODE and xj_norm_label is not None:
                    ax.legend(loc="best", frameon=False, fontsize=_FONTS.get("legend", None))
                fig.tight_layout()
                _savefig_branch(fig, "dijet_normalized", "dijet_imbalance", ns, f"{hn_xj}_perdijet.png", dpi=150)
                plt.close(fig)


        # ---- AJ plots ----
        for (ns, Ruse, ptlo_aj, pthi_aj, is_full_aj), dat in sorted(aj_map.items(), key=lambda t: (t[0][1], t[0][0], 1 if t[0][4] else 0, (-1e99 if not np.isfinite(t[0][2]) else t[0][2]), (-1e99 if not np.isfinite(t[0][3]) else t[0][3]))):
            hn_aj = dat['hn']; xc = dat['xc']; yc = dat['yc']; ye = dat['ye']; bw = dat['bw']
            mu, rms = _shape_stats(xc, yc, bw)
            ttl_pt = (rf"$p_{{T,1}}$: {PT_ALL_LABEL}" if (is_full_aj or (not np.isfinite(ptlo_aj)) or (not np.isfinite(pthi_aj))) else rf"$p_{{T,1}}\in[{int(ptlo_aj)},{int(pthi_aj)}]$ GeV")
            fig, ax = plt.subplots(figsize=(8.5, 6.0))
            yerr_plot = yerr_for_plot_absolute(yc, ye, dat["xsec_norm_err"] if isinstance(dat, dict) and "xsec_norm_err" in dat else xsec_plot_term)
            ax.errorbar(xc, yc, yerr=yerr_plot, fmt='o', ms=DEFAULT_MARKER_SIZE, lw=DEFAULT_LINE_WIDTH, capsize=2)
            apply_logy_with_floor(ax, yc, yerr_plot)
            ax.set_xlabel(r"$A_J = (p_{T1}-p_{T2})/(p_{T1}+p_{T2})$")
            ax.set_ylabel(r"$d\sigma/dA_J$ (mb per unit $A_J$)")
            base_title = f"Dijet momentum imbalance $A_J$  [{ttl_pt}; R={Ruse:.2f}{_imbalance_pair_title_tag()}]" + (" [nosubfrac]" if ns else "")
            scale_tag = " (log y)" if ax.get_yscale() == "log" else " (linear y)"
            ax.set_title(base_title + scale_tag)
            ax.set_xlim(0.0, 1.0)
            ax.text(0.98, 0.98, f"mean={mu:.3f}\nRMS={rms:.3f}", transform=ax.transAxes,
                    va='top', ha='right', fontsize=_FONTS['note'],
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.85, edgecolor='black'))
            fig.tight_layout()
            _savefig_branch(fig, "absolute", "dijet_imbalance", ns, f"{hn_aj}.png", dpi=150)
            plt.close(fig)

            sig, ycn, yen = normalize_per_dijet_with_cov(yc, ye, bw, denom_positive_only=False, cov_mode=PERDIJET_COV_MODE)
            if np.isfinite(sig) and sig > 0 and ycn is not None:
                mu_n, rms_n = _shape_stats(xc, ycn, bw)
                fig, ax = plt.subplots(figsize=(8.5, 6.0))
                aj_count = None
                aj_norm_label = None
                if SINGLE_SLICE_MODE and SELECTED_DIJET_COUNTS is not None:
                    aj_count = SELECTED_DIJET_COUNTS.count_for("aj", Ruse, is_nosubfrac=ns,
                                                              ptlo=(None if (is_full_aj or not np.isfinite(ptlo_aj) or not np.isfinite(pthi_aj)) else ptlo_aj),
                                                              pthi=(None if (is_full_aj or not np.isfinite(ptlo_aj) or not np.isfinite(pthi_aj)) else pthi_aj))
                    aj_norm_label = _legend_count_label("aj", aj_count)
                errorbar_nan_safe(ax, xc, ycn, yen, fmt="o", ms=DEFAULT_MARKER_SIZE, lw=DEFAULT_LINE_WIDTH, capsize=2, label=aj_norm_label)
                apply_logy_with_floor(ax, ycn, yen)
                ax.set_xlabel(r"$A_J = (p_{T1}-p_{T2})/(p_{T1}+p_{T2})$")
                ax.set_ylabel(_single_slice_norm_ylabel("aj") if SINGLE_SLICE_MODE else r"$(1/\sigma_{\mathrm{sel}})\,d\sigma/dA_J$ (1 per unit $A_J$)")
                norm_title_tag = "single-slice count normalized" if SINGLE_SLICE_MODE else "per-selection normalized"
                base_title = f"Dijet momentum imbalance $A_J$ ({norm_title_tag})  [{ttl_pt}; R={Ruse:.2f}{_imbalance_pair_title_tag()}]" + (" [nosubfrac]" if ns else "")
                scale_tag = " (log y)" if ax.get_yscale() == "log" else " (linear y)"
                ax.set_title(base_title + scale_tag)
                ax.set_xlim(0.0, 1.0)
                note_tail = (f"N_dijet={aj_count}" if (SINGLE_SLICE_MODE and aj_count is not None) else f"σ_sel={sig:.3e} mb")
                ax.text(0.98, 0.98, f"mean={mu_n:.3f}\nRMS={rms_n:.3f}\n{note_tail}",
                        transform=ax.transAxes, va='top', ha='right', fontsize=_FONTS['note'],
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.85, edgecolor='black'))
                if SINGLE_SLICE_MODE and aj_norm_label is not None:
                    ax.legend(loc="best", frameon=False, fontsize=_FONTS.get("legend", None))
                fig.tight_layout()
                _savefig_branch(fig, "dijet_normalized", "dijet_imbalance", ns, f"{hn_aj}_perdijet.png", dpi=150)
                plt.close(fig)


        # ---- Jet radius ratios: (dσ/dpT)_{R_first} / (dσ/dpT)_{R_other} from JET_RADIUS_LIST ----
        if not JET_RADIUS_COMPARE_PAIRS:
            _log("[INFO] JetR ratio plots skipped: need at least two radii in JET_RADIUS_LIST.")

        for ns in (False, True):
            for kind in ('incl', 'lead'):
                if kind == 'incl' and ns:
                    continue
                for r_num, r_den in JET_RADIUS_COMPARE_PAIRS:
                    key_num = (ns, kind, float(r_num))
                    key_den = (ns, kind, float(r_den))
                    if key_num not in jetpt_map or key_den not in jetpt_map:
                        if kind == 'incl' and not ns:
                            # Inclusive jet spectra are intentionally branch-neutral; do not expect a nosubfrac copy.
                            continue
                        _log(f"[INFO] JetR ratio {kind} ({'nosubfrac' if ns else 'default'}): missing R={float(r_num):.2f} or R={float(r_den):.2f}, skipping")
                        continue
                    dat_num = jetpt_map[key_num]
                    dat_den = jetpt_map[key_den]
                    xc_num, y_num, e_num = dat_num['xc'], dat_num['yc'], dat_num['ye']
                    xc_den, y_den, e_den = dat_den['xc'], dat_den['yc'], dat_den['ye']
                    if len(xc_num) != len(xc_den) or not np.allclose(xc_num, xc_den, rtol=0, atol=1e-9):
                        _log(f"[WARN] JetR ratio {kind} ({'nosubfrac' if ns else 'default'} R={float(r_num):.2f}/R={float(r_den):.2f}): binning mismatch, skipping")
                        continue
                    rr, err, m = _ratio_with_nan_safe_errors(y_num, e_num, y_den, e_den)
                    if not np.any(m):
                        _log(f"[INFO] JetR ratio {kind} ({'nosubfrac' if ns else 'default'} R={float(r_num):.2f}/R={float(r_den):.2f}): no positive overlapping bins, skipping")
                        continue
                    fig, ax = plt.subplots(figsize=(9, 6.2))
                    ax.axhline(1.0, color='k', ls='--', lw=DEFAULT_LINE_WIDTH)
                    errorbar_nan_safe(ax, xc_num[m], rr[m], err[m], fmt="o", ms=DEFAULT_MARKER_SIZE, lw=DEFAULT_LINE_WIDTH, capsize=2)
                    ax.set_xlabel(r"$p_T$ (GeV)")
                    ax.set_ylabel(rf"$(d\sigma/dp_T)_{{R={float(r_num):.2f}}}/(d\sigma/dp_T)_{{R={float(r_den):.2f}}}$")
                    ratio_title = f"Jet radius dependence ({kind}): R={float(r_num):.2f}/R={float(r_den):.2f}"
                    if kind != 'incl':
                        ratio_title += _dijet_pair_title_tag_no_ystar()
                    ratio_title += (" [nosubfrac]" if (ns and kind != 'incl') else "")
                    ax.set_title(ratio_title)
                    _annotate_approx_uncertainty(fig)
                    fig.tight_layout(rect=(0.0, 0.045, 1.0, 1.0))
                    if kind == 'incl':
                        out_dir_ratio = out_dir_jetR
                    else:
                        out_dir_ratio = _legacy_branch_dir(out_dir_jetR, is_nosubfrac=ns)
                    pair_tag = f"R{int(round(float(r_num)*100)):03d}_over_R{int(round(float(r_den)*100)):03d}"
                    fig.savefig(os.path.join(out_dir_ratio, f"jetR_ratio_{kind}_{pair_tag}.png"), dpi=160)
                    plt.close(fig)
    except Exception as e:
        _log(f"[WARN] imbalance/jetR section failed: {e}")


        # ---------------------- Combined Mjj plot (COMBINE_R_LIST) — NO connected lines ----------------------
    def _write_combined_mjj(branch_want: dict, is_nosubfrac: bool) -> None:
        if not branch_want:
            return
        if not all(v is not None for v in branch_want.values()):
            missing = [f"R={k:.2f}" for k,v in branch_want.items() if v is None]
            tag = "nosubfrac" if is_nosubfrac else "default"
            _log(f"[INFO] Skipping combined Mjj plot ({tag}); missing: {', '.join(missing)}")
            return

        # -------- absolute (mb/GeV) --------
        fig, ax = plt.subplots(figsize=(8.5, 6.5))
        ax.set_xscale("log"); ax.set_yscale("log")
        labels = []
        for Rkey in sorted(branch_want.keys()):
            dat = branch_want[Rkey]
            lbl = f"R={dat['R']:.2f}"
            ax.errorbar(dat["xc"], np.clip(dat["yc"], 1e-30, None),
                        yerr=yerr_for_plot_absolute(dat["yc"], dat["ye"], dat.get("xsec_norm_err", xsec_rel_err)),
                        fmt="o", ms=DEFAULT_MARKER_SIZE, lw=DEFAULT_LINE_WIDTH, label=lbl)
            labels.append((lbl, dat))

        x_all = np.concatenate([branch_want[k]["xc"] for k in branch_want])
        y_all = np.concatenate([branch_want[k]["yc"] for k in branch_want])
        bw_all = np.concatenate([branch_want[k]["bw"] for k in branch_want])

        x_floor = max(1e-3, mjj_min_cfg if mjj_min_cfg > 0 else 1e-3)
        x_ceil  = (mjj_max_cfg if (np.isfinite(mjj_max_cfg) and mjj_max_cfg > x_floor) else None)
        x_min, x_max = auto_xlim_hist(x_all, y_all, bw_all, logx=True, q_lo=0.002, q_hi=0.998, pad_frac=0.12,
                                      x_floor=x_floor, x_ceil=x_ceil)
        ax.set_xlim(x_min, x_max)
        ax.set_ylim(1e-12, max(np.nanmax(y_all)*1.5, 1e-11))
        ax.set_xlabel(r"$M_{jj}$ (GeV)")
        ax.set_ylabel(r"$d\sigma/dM_{jj}$ (mb/GeV)")
        pair_txt = _dijet_pair_title_tag()
        mjj_bb_tag = _mjj_backtoback_title_tag(mjj_require_backtoback, bb_tol_deg)
        ax.set_title(f"Dijet invariant mass  [$p_{{T,1}}$: {PT_ALL_LABEL}{mjj_bb_tag}{pair_txt}]")

        lines = []
        for lbl, dat in labels:
            m = dat["mean"]; s = dat["std"]
            parts = [lbl]
            if np.isfinite(m): parts.append(f"μ={m:.0f} GeV")
            if np.isfinite(s): parts.append(f"σ={s:.0f} GeV")
            lines.append("  ".join(parts))
        if lines:
            ax.text(0.98, 0.98, "\n".join(lines), transform=ax.transAxes, va="top", ha="right",
                    fontsize=_FONTS['note'], bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.85, edgecolor="black"))
        ax.legend(loc="lower left", fontsize=_FONTS['legend'])
        fig.tight_layout()

        out_path = _savefig_branch(fig, "absolute", "summary", is_nosubfrac, f"mjj_all_{combine_tag}.png", dpi=150)
        # (v4.9.43) Legacy duplicate output removed: combined Mjj absolute saved once under absolute/summary
        plt.close(fig)
        tag = "nosubfrac" if is_nosubfrac else "default"
        _log(f"Combined Mjj plot written ({tag}): {out_path}")

        # -------- per-selection normalized (1/GeV) --------
        fig, ax = plt.subplots(figsize=(8.5, 6.5))
        ax.set_xscale("log"); ax.set_yscale("log")
        labels = []
        sigmas = {}
        for Rkey in sorted(branch_want.keys()):
            dat = branch_want[Rkey]
            sig_mb, ycn, yen = normalize_per_dijet_with_cov(dat["yc"], dat["ye"], dat["bw"],
                                                            denom_positive_only=False, cov_mode=PERDIJET_COV_MODE)
            sigmas[Rkey] = sig_mb
            if ycn is None or yen is None or not (np.isfinite(sig_mb) and sig_mb > 0):
                continue
            lbl = f"R={dat['R']:.2f}"
            if SINGLE_SLICE_MODE and SELECTED_DIJET_COUNTS is not None:
                count_mjj = SELECTED_DIJET_COUNTS.count_for("mjj", dat["R"], is_nosubfrac=is_nosubfrac)
                lbl = f"{lbl} (N_dijet,Mjj-sel={count_mjj})"
            ax.errorbar(dat["xc"], np.clip(ycn, 1e-30, None), yerr=yen,
                        fmt="o", ms=DEFAULT_MARKER_SIZE, lw=DEFAULT_LINE_WIDTH, label=lbl)
            labels.append((lbl, dat))

        if labels:
            x_all = np.concatenate([d["xc"] for _, d in labels])
            y_all = np.concatenate([normalize_per_dijet_with_cov(d["yc"], d["ye"], d["bw"], denom_positive_only=False, cov_mode=PERDIJET_COV_MODE)[1] for _, d in labels])
            bw_all = np.concatenate([d["bw"] for _, d in labels])

            x_floor = max(1e-3, mjj_min_cfg if mjj_min_cfg > 0 else 1e-3)
            x_ceil  = (mjj_max_cfg if (np.isfinite(mjj_max_cfg) and mjj_max_cfg > x_floor) else None)
            x_min, x_max = auto_xlim_hist(x_all, y_all, bw_all, logx=True, q_lo=0.002, q_hi=0.998, pad_frac=0.12,
                                          x_floor=x_floor, x_ceil=x_ceil)
            ax.set_xlim(x_min, x_max)
            ax.set_ylim(1e-12, max(np.nanmax(y_all)*1.5, 1e-11))
            ax.set_xlabel(r"$M_{jj}$ (GeV)")
            ax.set_ylabel(_single_slice_norm_ylabel("mjj") if SINGLE_SLICE_MODE else r"$(1/\sigma_{\mathrm{sel}})\,d\sigma/dM_{jj}$ (1/GeV)")
            pair_txt = _dijet_pair_title_tag()
            norm_title_tag = "single-slice count normalized" if SINGLE_SLICE_MODE else "per-selection normalized"
            mjj_bb_tag = _mjj_backtoback_title_tag(mjj_require_backtoback, bb_tol_deg)
            ax.set_title(f"Dijet invariant mass ({norm_title_tag})  [$p_{{T,1}}$: {PT_ALL_LABEL}{mjj_bb_tag}{pair_txt}]")
            ax.legend(loc="lower left", fontsize=_FONTS['legend'])
            fig.tight_layout()
            out_path = _savefig_branch(fig, "dijet_normalized", "summary", is_nosubfrac, f"mjj_all_{combine_tag}_perdijet.png", dpi=150)
            plt.close(fig)
            _log(f"Combined Mjj per-dijet plot written ({tag}): {out_path}")
        else:
            plt.close(fig)

    # Write combined plots separately for default vs nosubfrac branches.
    _write_combined_mjj(want_Rs[False], False)
    _write_combined_mjj(want_Rs[True], True)

# ---------------------- Summary plot: width vs R ----------------------
    def _do_width_vs_R(widths_dict, is_abs_tag, out_name, is_nosubfrac):
        if not widths_dict:
            return False

        Rs = []
        sig_deg = []
        sig_deg_err = []
        for R in sorted(widths_dict.keys()):
            vals = []
            wts  = []
            errs = []
            any_err = False
            for sg, se, wmb in widths_dict[R]:
                if not np.isfinite(sg):
                    continue
                v = to_deg(sg)
                if width_weighting == "xsec":
                    w = wmb if (np.isfinite(wmb) and wmb > 0) else 0.0
                elif width_weighting == "ivar":
                    w = (1.0 / (to_deg(se)**2)) if (np.isfinite(se) and se > 0) else 0.0
                else:
                    w = 1.0
                vals.append(v); wts.append(w)
                errs.append(to_deg(se) if (np.isfinite(se) and se>0) else float("nan"))
                if np.isfinite(se) and se > 0:
                    any_err = True

            if not vals:
                continue

            vals = np.array(vals, dtype=float)
            wts  = np.array(wts,  dtype=float)

            if (not np.any(np.isfinite(wts))) or np.all(wts <= 0):
                wts = np.ones_like(vals)

            m = float(np.sum(wts * vals) / np.sum(wts))

            if any_err and np.sum(wts) > 0:
                es = np.array([e if np.isfinite(e) else 0.0 for e in errs], dtype=float)
                m_err = float(np.sqrt(np.sum((wts**2) * (es**2))) / np.sum(wts))
            else:
                m_err = float(np.sqrt(np.average((vals - m)**2, weights=wts)) / math.sqrt(max(1.0, len(vals))))

            Rs.append(R); sig_deg.append(m); sig_deg_err.append(m_err)

        if not Rs:
            return False

        fig, ax = plt.subplots(figsize=(5.0, 3.8))
        ax.errorbar(Rs, sig_deg, yerr=sig_deg_err, fmt="o-", ms=4, lw=DEFAULT_LINE_WIDTH*0.5, capsize=3)
        ax.set_xlabel("Jet radius R")
        ax.set_ylabel(r"$\sigma(|\Delta\varphi-\pi|)$ [deg]" if is_abs_tag else r"$\sigma(\Delta\varphi-\pi)$ [deg]")
        if width_weighting == "xsec":
            weight_txt = "xsec-weighted"
        elif width_weighting == "ivar":
            weight_txt = r"$1/\sigma_{\mathrm{err}}^2$-weighted"
        else:
            weight_txt = "equal-weighted"

        dom_txt = (r"(abs: $|\mathrm{wrap}(\phi_1-\phi_2)|\in[0,\pi]$)"
                   if is_abs_tag else r"(unfolded: $0\leq\Delta\varphi<2\pi$)")

        ax.set_title(
            r"$\Delta\varphi$ width vs R (Gaussian $\sigma$) — "
            + weight_txt + " " + dom_txt
            + (" [nosubfrac]" if is_nosubfrac else " [subfrac]")
        )

        idx_best = int(np.nanargmin(sig_deg))
        ax.scatter([Rs[idx_best]], [sig_deg[idx_best]], s=150, facecolors='none', edgecolors='red', linewidths=1.4)
        ax.annotate(f"best R = {Rs[idx_best]:.2f}",
                    xy=(Rs[idx_best], sig_deg[idx_best]),
                    xytext=(6, 10), textcoords="offset points", fontsize=_FONTS['note'])

        fig.tight_layout()
        out_path = _savefig_branch(fig, "absolute", "summary", is_nosubfrac, out_name, dpi=150)
        plt.close(fig)
        _log(f"Summary plot written: {out_path}")
        _log(
            f"Best R by Gaussian width ({'xsec-weighted' if width_weighting=='xsec' else width_weighting})"
            + (" [ABS]" if is_abs_tag else " [FULL]")
            + (" [nosubfrac]" if is_nosubfrac else " [subfrac]")
            + f": R={Rs[idx_best]:.2f}, σ={sig_deg[idx_best]:.2f} deg"
        )
        return True

    any_full_sub = _do_width_vs_R(widths_by_R_full[False], False, "width_vs_R_gauss.png", False)
    any_full_ns  = _do_width_vs_R(widths_by_R_full[True],  False, "width_vs_R_gauss.png", True)
    any_abs_sub  = _do_width_vs_R(widths_by_R_abs[False],  True,  "width_vs_R_gauss_abs.png", False)
    any_abs_ns   = _do_width_vs_R(widths_by_R_abs[True],   True,  "width_vs_R_gauss_abs.png", True)

    if not (any_full_sub or any_full_ns or any_abs_sub or any_abs_ns):
        _log("[WARN] width_vs_R: no valid width values to plot (no successful Δφ fits).")

    _log(f"Δφ histograms processed: {n_dphi}")
    _log(f"η histograms plotted: {n_eta}")
    _log(f"Particle-level histograms plotted: {n_particle}")
    _log(f"Mjj histograms plotted: {n_mjj}")
    _log(f"frac_vs_theta plots written: {n_frac}")
    _log(f"ROOT hist inventory: total={n_hist_total} | subfrac(default)={n_hist_sub} | nosubfrac={n_hist_ns}")
    _log(f"CSV: {csv_path}")
    for (_kind, _cat), _n in sorted(_neutral_save_counts.items()):
        _log(f"[save-summary] {_kind}/neutral: {_cat}={_n}")
    for _kind in ("absolute", "dijet_normalized"):
        for _branch in ("subfrac", "nosubfrac"):
            _parts = []
            for _cat in ("dphi_fit", "dphi_fit_abs0pi", "eta", "dijet_mass", "dijet_imbalance", "jet_spectra", "summary"):
                _n = _save_counts.get((_kind, _cat, _branch), 0)
                if _n > 0:
                    _parts.append(f"{_cat}={_n}")
            if _parts:
                _log(f"[save-summary] {_kind}/{_branch}: " + ", ".join(_parts))
            else:
                _log(f"[save-summary] {_kind}/{_branch}: none")
    _LOG_FH.close()
    return 0

if __name__ == "__main__":
    sys.exit(main())
