#!/usr/bin/env python3
# paperreadycomparisor_py.py  v1.6
# DERIVED FROM: mjj_comparisor_py.py v5.10
# CHANGELOG
# - 2026-06-06: v1.6 FIX: Make paper-ready comparison defaults and ratio-side inference compatible with realistic vacuum/medium runs.
#   • FIX: Default run-B label is now medium instead of brick when jetscape.ini does not override it.
#   • FIX: Medium-side detection now recognizes current realistic pp medium tags/labels as well as legacy brick tags, so med ratios remain medium/reference even if run order is reversed.
#   • FIX: Active CLI/help text and current-behavior comments now describe medium/reference instead of the retired brick-only workflow.
#   • SAFETY: No ROOT histogram discovery, normalization formulas, output folder taxonomy, filenames, SLURM behavior, or upstream sim/analysis/merge contracts changed.
# - 2026-04-29: v1.5 FIX: Use analyzer count-density ROOT histograms for true single-slice dN normalization.
#   • FIX: In SINGLE_SLICE_MODE, dijet_normalized Mjj, |Delta phi|, xJ/AJ, and selected lead/sublead jet-pT plots now prefer counts/count_* TH1 inputs, so the plotted quantity is true (1/N_dijet,sel)dN/dX.
#   • FALLBACK: If old merged ROOT files do not contain count_* histograms, the comparisor logs a warning and falls back to legacy weighted histograms instead of crashing.
#   • SAFETY: Absolute plots and multi-slice per-selection normalization remain unchanged.
# - 2026-04-26: v1.4 FIX: Make SINGLE_SLICE_MODE dijet-normalized paperready plots truly selected-count normalized.
#   • FIX: Mjj, selected lead/sublead jet-pT, |Delta phi|, xJ, and AJ dijet_normalized outputs now use y/N_dijet,sel and e/N_dijet,sel when SINGLE_SLICE_MODE=1, matching vacbrick_plotter_py.py semantics instead of unit-shape/integral normalization.
#   • FIX: Legends/notes retain selected-dijet counts for the normalized single-slice outputs.
#   • SAFETY: Multi-slice behavior remains shape/per-selection normalized because selected dijet counts are not meaningful across weighted pThat slices.
# - 2026-04-25: v1.3 CONTRACT: Match analyzer v9.8.0 / merge v8.4 selected-dijet count fields.
#   • CHANGE: Use dijet_base_* selected-dijet counts for generic selected-pair denominators after retiring obsolete raw dphi_R* histograms.
#   • CHANGE: Non-absolute legacy dphi requests, if reached by old helper paths, now resolve to the generic dijet_base_* count fields instead of missing raw-dphi metadata.
#   • FIX: |Delta phi| vs |Delta eta| comparison-map colorbars now label the bin-area-normalized differential density.
#   • SAFETY: Plot math and ratio orientation are unchanged; this only updates downstream metadata lookup names.
# - 2026-04-08: v1.2 ADD/FIX: Read and plot analyzer v9.7.3 |Δφ| vs |Δη| TH2 diagnostics, and retire redundant non-absolute Δφ comparison outputs.
#   • NEW: Add h2_dphi_abs_vs_deta family parsing, ROOT TH2 discovery, and vacuum/brick comparison maps (including nosubfrac variants) under plots/absolute/<branch>/dphi_abs_vs_deta.
#   • CHANGE: Stop generating non-absolute Δφ comparison plots into plots/*/dphi_fit; keep the |Δφ| (0..π) dphi_fit_abs0pi outputs only.
#   • SAFETY: No upstream ROOT reading math, normalization formulas, ratio conventions for kept outputs, or sim/analysis/merge job-control behavior changed.
# - 2026-04-03: v1.1 CLEANUP: Remove run-tag text from plot-facing labels, hide optional paper captions by ini knob, drop compare-side note boxes, simplify Δφ/|Δφ| text, and declutter jet-spectrum outputs.
#   • CHANGE: Plot legends, ratio labels, and panel labels now use only COMPARE_LABEL_A / COMPARE_LABEL_B (e.g. vacuum, brick); run tags stay only in folder paths and logs.
#   • ADD: New jetscape.ini knob PAPERREADY_SHOW_CAPTION=1|0 controls all bottom Figure: captions globally.
#   • CHANGE: Remove compare-side annotation boxes for auto-zoom notices, ratio-input rebin notes, jet-R shared-event correlation caveats, and the stray Δφ med/vac tag.
#   • FIX: Convert degree text to a real degree symbol in paper captions (30° instead of 30^\circ / 30\circ) and keep long xJ/AJ selection captions wrapping cleanly.
#   • CHANGE: |Δφ| x-axis/title text no longer says folded to [0,π]; the observable name alone is used on the plot.
#   • CHANGE: Combined all-R Mjj overlays now use a per-R multi-color palette plus Mass.C-inspired marker families instead of collapsing everything into only blue/red.
#   • CHANGE: Retire comparisor-only plots/custom/jet_spectra_ratio outputs; bottom ratio panels on the main jet-spectrum figures remain.
#   • CHANGE: Lead-vs-sublead map panel headers are reduced to simple dataset labels/ratio labels; full figure identification stays in the bottom caption.
#   • SAFETY: No histogram discovery, normalization math, filenames for kept outputs, SLURM parameters, or upstream sim/analysis/merge contracts changed.
# - 2026-04-02: v1.0 ADD: Paper-ready comparison rendering that preserves the existing comparisor's ROOT IO, normalization, folder routing, and workflow contracts while restyling plots after Claude's Mass.C template.
#   • NEW: Use Mass.C-inspired sans-serif typography, ROOT-like inward ticks, legend styling without a border, and the blue/red comparison palette seen in the template.
#   • NEW: Remove the big top titles from saved PNGs and place the same text at the bottom as a centered 'Figure:' caption so the plot area stays paper-clean while the caption remains easy to copy into a manuscript.
#   • NEW: Keep writing into the same comparison folders and filenames as the standard comparisor so ./paperreadycomparisor.sh drops paper-ready PNGs exactly where the current workflow expects them.
#   • DIAG: Log every stage to logs/paperreadycomparisor_py.log.
#   • SAFETY: No histogram discovery, normalization, ratio direction, run-tag resolution, selected-dijet count handling, folder taxonomy, or upstream sim/analysis/merge contracts changed.
#
# Legacy changelog from the source comparisor retained below for provenance.
# CHANGELOG
# - 2026-04-02: v5.10 ADD: Drive compare-side ratio-panel y-ranges from explicit jetscape.ini knobs with no code defaults.
#   • ADD: Require dedicated lower/upper ratio-panel bounds from jetscape.ini for Mjj, jet-pT, Δφ, |Δφ|, xJ, AJ, jet-R, and lead-vs-sublead profile comparison plots.
#   • ADD: Apply the configured bounds verbatim instead of data-driven auto-scaling, and warn in paperreadycomparisor_py.log when plotted ratio points fall outside the configured window so sparse tails are easy to retune.
#   • SAFETY: No histogram IO, normalization numerics, ratio direction, folder layout, filenames, SLURM parameters, or upstream sim/analysis/merge/fitter contracts changed.
# - 2026-03-30: v5.00 ADD: Put comparison ratios directly under the main Mjj and jet-pT overlays, and add optional compare-side Δφ ratio rebinning from jetscape.ini.
#   • ADD: Convert the standard Mjj absolute/per-selection comparison PNGs into 2-panel layouts with the original overlay on top and the configured medium/reference ratio on the bottom; keep the combined all-R Mjj overlay as overlay-only.
#   • ADD: Convert the standard jet-spectrum comparison PNGs (inclusive, leading, and subleading; absolute and normalized; subfrac/nosubfrac/branch-neutral trees) into 2-panel layouts with the original overlay on top and the configured ratio on the bottom.
#   • ADD: Read compare-side Δφ ratio rebin knobs from jetscape.ini and, when enabled, rebin only the ratio inputs with density-preserving scaling (ROOT-style Rebin(N)+Scale(1/N) behavior for uniform bins) before building the Δφ / |Δφ| ratio panel.
#   • ADD: Log the resolved ratio rebin factors and stamp the affected Δφ ratio panels with a small note when ratio-only rebinning is active.
#   • SAFETY: No analyzer histograms, merge numerics, fitter outputs, combined-all-R Mjj overlay behavior, folder layout, filenames, SLURM parameters, or upstream sim/analysis/merge contracts changed.
# - 2026-03-20: v4.90 FIX: Give combined all-R Mjj overlays distinct per-R colors for up to six configured radii so 4-radius comparisons no longer reuse colors across curves.
#   • FIX: Expand the combined_all_plot() A/B color palettes from 3 entries to 6 entries, keeping markers and labels unchanged while preventing the 4th configured R from recycling an earlier color.
#   • SAFETY: No histogram IO, normalization, ratio logic, folder layout, filenames, SLURM behavior, or upstream sim/analysis/merge/fitter contracts changed.
# - 2026-03-20: v4.89 FIX: Repair nosubfrac combined-all-R Mjj discovery, quiet harmless log-scale warnings, count real-vs-placeholder outputs, wrap jet-spectrum titles earlier, and auto-zoom crowded lead-vs-sublead TH2 maps.
#   • FIX: Teach combined_all_plot() to resolve both standard and _nosubfrac explicit-fullrange/legacy Mjj histogram names, so the nosubfrac combined all-R comparison is no longer skipped by a stale non-nosubfrac lookup.
#   • FIX: Harden _apply_logy_with_floor() by setting a positive floor before enabling log-y and suppressing Matplotlib's known harmless "Data has no positive values" warning during that transition; compare stderr stays clean without hiding real comparator warnings.
#   • ADD: Track every saved comparison figure and every placeholder figure, then print an end-of-run exact summary of real plots vs placeholders (including per-output bucket counts) into paperreadycomparisor_py.log / SLURM stdout.
#   • FIX: Force earlier two-line wrapping plus extra top margin for jet-spectrum overlay/ratio titles, so long lead/sublead nosubfrac titles no longer clip on saved PNGs.
#   • FIX: Auto-zoom lead-vs-subleading TH2 comparison maps to populated bins, wrap panel titles cleanly, and keep the full context centered without the giant mostly-empty log-log canvas.
#   • SAFETY: No histogram numerics, run discovery, ROOT IO contracts, SLURM parameters, folder taxonomy, or upstream sim/analysis/merge expectations changed.
# - 2026-03-19: v4.88 FIX: Wrap long comparison titles onto two centered rows at natural break points instead of clipping off the figure canvas.
#   • FIX: Add helper title wrappers that preserve the full title text, prefer clean breaks before selection brackets / after colons, and only insert a newline when the title is actually long.
#   • FIX: Apply the wrapped-title helper to the long Mjj, jet-pT, particle-level, Δφ/|Δφ|, xJ/AJ, lead-vs-sublead, and jet-R comparison titles/suptitles that were getting cut off in saved PNGs.
#   • FIX: Give wrapped figure suptitles a slightly larger top margin so tight_layout no longer squeezes off the second line.
#   • SAFETY: No histogram reading, normalization, filenames, folder layout, SLURM behavior, or upstream sim/analysis/merge contracts changed.
# - 2026-03-19: v4.84 CHANGE: Remove custom 4-panel collage generation from the comparisor.
# - 2026-03-20: v4.87 FIX: Port fitter-style ROOT histogram discovery into the comparisor for Mjj, Δφ, |Δφ|, xJ/AJ, particle-level, and lead-vs-sublead readers so nosubfrac histograms are classified from the ROOT directory tree exactly like the fitter. ADD: Log per-family discovery summaries and sample nosubfrac keys so empty output folders can be debugged directly from compare logs.
#   • CHANGE: Delete the custom Mjj per-selection and xJ/AJ absolute 4-panel collage helpers and remove their main() calls so the comparisor no longer builds any 4-panel collage PNGs.
#   • CHANGE: Stop advertising COLLAGE_R_LIST in startup config because collage-only radius ordering is no longer used anywhere in the current comparisor.
#   • SAFETY: Standard Mjj, jet-pT, Δφ/|Δφ|, xJ/AJ, particle-level, lead/sublead-correlation, and jet-R comparison plots, filenames, normalization logic, and upstream sim/analysis/merge contracts are unchanged.
# - 2026-03-19: v4.83 FIX: Do not abort compare jobs when single-slice selected-dijet counts are zero in sparse high-pT bins.
#   • FIX: Treat zero selected-dijet counts from merged selected_dijet_counts_summary.json as allowed metadata instead of fatal comparator errors; only negative counts remain invalid.
#   • FIX: For single-slice normalized Mjj, Δφ/|Δφ|, xJ/AJ, and dijet-selected jet-pT comparison outputs, write an explicit placeholder PNG and continue when one or both compared runs have zero selected dijets in the requested bin, instead of killing the whole comparison stage.
#   • LOG: Emit clear warnings naming the observable/bin/output whenever a normalized comparison is skipped because the selected-dijet denominator is zero or non-positive.
#   • SAFETY: Absolute overlays, histogram IO, normalization math for populated bins, folder layout, filenames, and upstream sim/analysis/merge contracts are unchanged.
# - 2026-03-19: v4.82 FIX: Stop Mjj comparison titles from crashing on mathtext braces.
#   • FIX: Escape the literal {T,1} mathtext braces in the lead-pT title fragment used by overlay_plot() and overlay_plot_perdijet(), preventing Python f-string interpolation from raising NameError before savefig(...).
#   • SAFETY: No histogram IO, normalization, ratio logic, folder layout, workflow filenames, or upstream analyzer/merge/sim contracts changed.
# - 2026-03-18: v4.81 FIX: Mirror fitter jet-spectrum populated-range auto-zoom in the comparisor.
#   • FIX: Replace center-only jet-spectrum x-range selection with populated-bin edge-aware auto-zooming so wide empty high-p_T tails no longer dominate compare-side jet spectra and jet-R ratio displays.
#   • FIX: Apply the populated-range x-limit helper consistently to absolute and normalized jet-spectrum overlays, jet-spectrum ratio panels, and jet-R ratio/double-ratio panels for subfrac, nosubfrac, and branch-neutral inclusive outputs.
#   • DIAG: Log the resolved auto-zoom x-limits and stamp the affected compare-side jet-spectrum figures with a small note that the display x-range was auto-zoomed to populated bins.
# - 2026-03-17: v4.80 FIX: Preflight single-slice selected-dijet metadata and relabel normalized lead/sublead jet-pT overlays honestly.
#   • FIX: Extend the compare-side single-slice contract to the dijet-selected lead/sublead jet-pT overlays: use 1/N_dijet,sel · dN/dp_T y-axis text, single-slice wording in titles, and selected-dijet counts in legends/notes instead of stale σ_sel text.
#   • FIX: Resolve the generic selected-dijet denominator for these jet-pT overlays from the published dijet_base_all_per_R counts, which track the base accepted dijet-pair selection without extra Mjj/xJ/AJ-specific gates.
#   • SAFETY: No histogram numerics, covariance propagation, ratio direction, folder layout, or upstream analyzer/merge contracts changed.
# - 2026-03-17: v4.79 FIX: Make custom comparison collages obey the configured JET_RADIUS_LIST.
#   • FIX: Replace hard-coded R=0.2/0.4/0.5/0.6 panel selection in the custom Mjj and xJ/AJ collage builders with the parsed JET_RADIUS_LIST from jetscape.ini.
#   • FIX: Keep collage panel titles, PNG lookup, and missing-panel diagnostics aligned with the configured jet-radius order instead of silently assuming one specific four-R setup.
#   • SAFETY: No histogram numerics, ratio conventions, main comparison outputs, folder layout, or upstream analyzer/merge/fitter contracts changed.
# - 2026-03-17: v4.78 FIX: Harden comparator fatal handling, ratio-panel NaN behavior, and jet-R double-ratio consistency.
#   • FIX: Add the missing _die() fatal helper so required-config and single-slice resolution failures terminate cleanly instead of throwing NameError on error paths.
#   • FIX: Buffer early _log() messages until compare_dir/logs/paperreadycomparisor_py.log is opened, then flush them into the standard comparator log so startup/fatal diagnostics are not lost.
#   • FIX: Keep ratio-panel points visible when central values are finite but propagated uncertainties are unavailable by using NaN-safe ratio propagation/plotting in normalized xJ/AJ, Δφ/|Δφ|, jet-spectrum ratio, and jet-R double-ratio panels.
#   • FIX: Make jet-R double-ratio orientation obey the same ratio_mode and vacuum/brick inference used elsewhere in the comparator instead of always forcing runB/runA.
#   • FIX: Validate SINGLE_SLICE_MODE selected-dijet count semantics against the analyzer/merge contract (event_level_selected_dijet_pair_counts) before relabeling normalized plots.
#   • CLEANUP: Remove dead comparator-only helpers that were no longer called and drop stale unused xsec_rel_err reader arguments without changing histogram numerics, folder layout, or upstream contracts.
# - 2026-03-17: v4.77 FIX: Generalize comparator jet-R pair plots from JET_RADIUS_LIST, clarify approximate uncertainty caveats, and remove folded-|Δφ| boundary guides.
#   • FIX: Read JET_RADIUS_LIST in ini order, build jet-R comparison pairs as first-radius divided by each later radius, and write one ratio + double-ratio plot per configured pair instead of hard-coding only R0.2/R0.4.
#   • FIX: Log the resolved jet-R comparison pairs and skip missing pairs explicitly instead of silently assuming only one supported pair.
#   • FIX: Keep the shared-event-correlation caveat visible in a bottom-of-panel note on every jet-R ratio/double-ratio plot.
#   • FIX: Remove the redundant π guide line from folded dphi_abs comparison panels and custom two-row folded-|Δφ| panels.
#   • SAFETY: No histogram names, normalization numerics, compare tags, folder layout, or upstream analyzer/merge contracts changed.
# - 2026-03-16: v4.76 FIX: Make comparisor Mjj titles obey explicit MJJ_REQUIRE_BACKTOBACK.
#   • FIX: Read required MJJ_REQUIRE_BACKTOBACK from jetscape.ini, hard-fail on missing/invalid values, and only advertise the Mjj back-to-back cut in comparison titles when that extra analyzer gate is enabled.
#   • LOG: Startup config now records MJJ_REQUIRE_BACKTOBACK alongside DIJET_BACKTOBACK_TOL_DEG for reproducible comparison labeling.
# - 2026-03-16: v4.75 FIX: Align comparisor histogram parsing, selected-dijet labels, and custom collage inputs with analyzer v9.7.0 / merge v8.2 / fitter v4.9.68.
#   • FIX: Accept explicit <ptmin>_<ptmax>_fullrange histogram names for Δφ/|Δφ|, Mjj, xJ, AJ, jetpt_{lead,sublead}, h2_sublead_vs_lead, and prof_sublead_vs_lead while preserving legacy _all compatibility where applicable.
#   • FIX: Resolve SINGLE_SLICE_MODE selected-dijet legend counts for the new pT-binned xJ/AJ histograms via xj_ptlead_per_R and aj_ptlead_per_R, and stop expecting deprecated mjj_ptlead_per_R bins.
#   • FIX: Update custom Mjj/xJ/AJ comparison-collage inputs and combined all-R Mjj lookup to the new explicit full-range histogram filenames instead of stale _all-only names.
#   • FIX: Comparison titles that include lead-pT selection now use the histogram’s actual configured pT range when available instead of always showing the broad PT_ALL_LABEL.
#   • SAFETY: No ratio conventions, normalization numerics, plotting folders, or upstream job-control logic changed.
# - 2026-03-16: v4.74 ADD: Support SINGLE_SLICE_MODE count-style labels/legends for normalized dijet comparison plots.
#   • NEW: Read SINGLE_SLICE_MODE from jetscape.ini; when enabled, require both compared runs to publish merged selected_dijet_counts_summary metadata and validate that each merged run really contains exactly one pThat slice.
#   • NEW: Load observable/branch/pt-bin specific selected dijet counts for each run and use them in normalized Mjj, Δφ/|Δφ|, xJ, and AJ comparison legends without changing any normalization math.
#   • NEW: Relabel only dijet-normalized comparison plots from (1/σ_sel)dσ/dX to the corresponding observable-specific 1/N_dijet·dN/dX notation when SINGLE_SLICE_MODE=1.
#   • SAFETY: Absolute plots, inclusive unit-normalized jet plots, histogram numerics, ratio logic, and SINGLE_SLICE_MODE=0 behavior are unchanged.
# - 2026-03-15: v4.73 FIX: Match the patched fitter folder taxonomy for inclusive unit-shape jet-spectrum comparison overlays.
#   • FIX: Rename the branch-neutral inclusive unit-shape comparison tree from plots/unit_normalized/jet_spectra/ to plots/inclusive_unit_normalized/jet_spectra/ so it is no longer confused with per-dijet normalized outputs.
#   • FIX: Update inline path documentation/comments to use the fitter-consistent inclusive_unit_normalized name.
#   • SAFETY: No histogram parsing, labels, normalization numerics, ratio logic, filenames, or upstream analyzer/merge contracts changed.
# - 2026-03-15: v4.72 FIX: Make comparisor exact xsec-band histogram lookup use the same normalized recursive ROOT reader pattern as the patched fitter.
#   • FIX: Add _iter_root_objects(root_path) so per-slice xsec-band reconstruction indexes TH1 histograms by normalized leaf name, preserving nosubfrac branch identity exactly like the main merged-ROOT readers.
#   • FIX: SliceNormBandBuilder now uses _iter_root_objects(...) instead of the older direct uproot-open recursion, eliminating false missing-histogram fatals when per-slice ROOT objects are nested under directories.
#   • DIAG: Log how many TH1 histograms each per-slice ROOT contributes to the exact xsec-band helper so future inventory mismatches are visible in comparisor logs.
#   • SAFETY: No histogram names, ratio logic, folder layout, workflow filenames, or upstream analyzer/merge contracts changed.
# - 2026-03-15: v4.71 FIX: Match the patched fitter for folded |Δφ| absolute labels and NaN-safe normalized comparison plotting.
#   • FIX: Folded absolute dphi_abs_* comparison panels now label the observable as $d\sigma_{\mathrm{dijet}}/d|\Delta\varphi|$ instead of the misleading $d\sigma_{\mathrm{dijet}}/d\Delta\varphi$.
#   • FIX: Add fitter-style NaN-safe normalized errorbar helpers so valid normalized comparison points remain visible when propagated uncertainties are undefined, instead of being silently dropped or faked as zero-error bins.
#   • FIX: Apply the NaN-safe normalized plotting path to Δφ/|Δφ| comparison stacks, custom folded-|Δφ| two-row panels, xJ/AJ comparison stacks, and normalized jet-pT overlays, keeping downstream presentation consistent with the fitter.
#   • SAFETY: No histogram names, normalization numerics, ratio-direction conventions, folder layout, workflow filenames, or upstream analyzer/merge contracts changed.
# - 2026-03-15: v4.70 FIX: Make comparisor Δφ labels consistent with the patched fitter notation.
#   • FIX: Per-selection-normalized Δφ comparison labels now use fitter-consistent $\sigma_{\mathrm{sel}}$ wording instead of the stale $\sigma_{\mathrm{dijet,sel}}$ text.
#   • FIX: Folded per-selection-normalized abs-$\Delta\varphi$ comparisons now label the plotted differential as $d\sigma/d|\Delta\varphi|$, matching the fitter-side notation for the folded observable.
#   • SAFETY: Label/docstring-only patch; no histogram parsing, normalization numerics, ratio logic, directory layout, or workflow filenames changed.
# - 2026-03-15: v4.69 FIX: Restore combined all-R Mjj comparison output save path before figure close.
#   • FIX: combined_all_plot() now defines its output filename, writes the PNG with fig.savefig(...) before plt.close(fig), and logs the real saved path.
#   • SAFETY: No changes to histogram parsing, normalization, labels, ratio logic, directory layout, or workflow filenames beyond restoring the intended combined comparison image.
# - 2026-03-15: v4.68 FIX: Keep comparisor consistent with fitter for imbalance-cut honesty, weighted-histogram stats text, exact-two wording, and normalization comments.
#   • FIX: Read required IMBALANCE_REQUIRE_BACKTOBACK and IMBALANCE_BACKTOBACK_TOL_DEG from jetscape.ini, hard-fail on invalid values, and log the resolved imbalance-selection mode at startup.
#   • FIX: xJ/AJ comparison titles now append the active analyzer imbalance back-to-back requirement only when enabled, matching fitter-side selection text without renaming histograms or changing normalization.
#   • FIX: Remove misleading ROOT fEntries-based “Entries” text from the Mjj overlay stats box; comparator stats now report only mean and standard deviation for each run.
#   • FIX: Standardize exact-two wording to “exactly 2 accepted jets” so comparator titles match the fitter/analyzer contract.
#   • FIX: Correct stale normalization comments so they no longer claim positive-only σ_sel integration while the code intentionally uses denom_positive_only=False.
# - 2026-03-15: v4.67 FIX: Match Δφ comparison y-axis labels to fitter-side dijet wording.
#   • FIX: _dphi_ylabel() now uses explicit dijet cross-section labels for both absolute and per-selection-normalized Δφ comparisons, matching the patched fitter and avoiding the remaining generic σ_sel / dσ wording mismatch.
#   • SAFETY: Label-only patch; no histogram names, normalization numerics, ratio logic, folder routing, or workflow filenames changed.
# - 2026-03-15: v4.66 FIX: Retire dimensionful ln-spectrum diagnostics, unclip comparison ratios, and make jet-R uncertainty caveats explicit.
#   • FIX: Retire the non-standard ln(dσ/dp_T) jet-spectrum comparison outputs and their 4-panel collages; the comparisor now logs that those diagnostics are intentionally skipped instead of generating dimensionful-log plots.
#   • FIX: Replace hard-coded ratio-panel limits (0.2–1.8) in Δφ and xJ/AJ comparison stacks with data-driven auto-scaling around unity, so real medium/reference deviations are not silently clipped.
#   • FIX: Use log-x axes for wide-range jet-p_T ratio diagnostics and jet-R dependence plots, matching the absolute jet-spectrum presentation more closely.
#   • FIX: Mark jet-R ratio and double-ratio uncertainty bands as approximate because shared-event correlations between R=0.2 and R=0.4 are not available downstream.
#   • FIX: Clarify Δφ titles as dijet azimuthal decorrelation comparisons, matching fitter-side wording and avoiding semi-inclusive recoil-style overinterpretation.
#   • SAFETY: No histogram names, ROOT parsing, ratio-direction conventions, folder names used by the existing workflow, or upstream analyzer/merge contracts were changed.
# - 2026-03-14: v4.65 FIX: Make inclusive jet-spectrum comparison outputs honest and clarify comparisor scope without changing workflow filenames.
#   • FIX: Inclusive jet p_T unit-shape comparison overlays now write to plots/inclusive_unit_normalized/jet_spectra/ instead of the misleading branch-neutral plots/dijet_normalized/jet_spectra/ tree.
#   • FIX: Inclusive jet p_T unit-shape comparison filenames now end with _overlay_unitshape.png instead of _overlay_perdijet.png, matching the actual (1/\sigma_{incl}) d\sigma/dp_T quantity.
#   • FIX: CLI/log wording now describes this script as a multi-observable run comparison stage rather than an Mjj-only plotter.
#   • SAFETY: Dijet-selected normalized outputs, histogram parsing, ratio conventions, and comparer workflow filenames are unchanged.
# - 2026-03-11: v4.64 FIX: Align comparisor normalization labels, exact-two-jets selection text, jet-spectrum ratio uncertainties, and logging with the current analyzer/fitter contract.
#   • FIX: Per-selection-normalized y-axis labels now use $\sigma_{\mathrm{sel}}$ (or $\sigma_{\mathrm{incl}}$ for inclusive jet shapes) instead of the misleading $\sigma_{\mathrm{dijet}}$ text for Mjj, Δφ, xJ, and AJ comparisons.
#   • FIX: Parse DIJET_REQUIRE_EXACTLY_TWO_JETS strictly from jetscape.ini, log it, and add 'exactly 2 selected jets' to dijet-pair titles/selection text for Mjj, Δφ, lead/sublead jet-pT, xJ/AJ, and lead-vs-sublead correlation plots. Inclusive jet spectra and particle-level QA remain selection-neutral.
#   • FIX: Jet-spectrum ratio diagnostics now propagate the same absolute plotted uncertainties used elsewhere, including optional per-slice xsec normalization bands when INCLUDE_XSEC_NORM_ERR=1.
#   • FIX: Rename the main comparisor log to compare_dir/logs/paperreadycomparisor_py.log so it is no longer mislabeled as fit_py.log.
#   • SAFETY: No histogram names, folder layout, merge expectations, or ratio-direction conventions were changed.
# - 2026-03-11: v4.63 FIX: Make comparisor titles consistent with the fitter/analyzer y* semantics and particle-level QA wording.
#   • FIX: When YSTAR_ENABLE=1 in jetscape.ini, add |y*|<YSTAR_MAX to comparisor titles for the shared dijet-pair observables the comparisor plots: jetpt_{lead,sublead}_*, h2_sublead_vs_lead_*, prof_sublead_vs_lead_*, xj_*, and aj_*.
#   • FIX: Keep inclusive jet spectra branch-neutral and y*-free, matching analyzer behavior.
#   • FIX: Rewrite particle-level QA titles to explicitly say inclusive weighted yields of accepted pre-clustering constituents, so the plots are not mistaken for per-event or per-jet spectra.
#   • SAFETY: No histogram names, folder layout, merge expectations, ratio conventions, or run-tag plumbing were changed.
# - 2026-03-10: v4.62 ADD: Compare analyzer lead-vs-subleading jet correlation observables for both subfrac and nosubfrac branches.
#   • NEW: Read TH2D objects h2_sublead_vs_lead_Rxxx_all(_nosubfrac) and TProfile objects prof_sublead_vs_lead_Rxxx_ptleadbins(_nosubfrac) from merged ROOT files.
#   • NEW: Write comparison outputs under plots/absolute/{subfrac,nosubfrac}/lead_sublead_correlation/, matching fitter folder taxonomy for these observables.
#   • NEW: TH2D comparisons are written as side-by-side vacuum/medium maps with a ratio panel; TProfile comparisons are written as vacuum-vs-medium overlays with a ratio panel and fitter-consistent axis labels/titles.
#   • FIX: Restore missing read_particle_hists() helper so the existing particle-level comparator section cannot crash with NameError.
# - 2026-03-10: v4.61 ADD: Compare accepted particle-level QA histograms particle_pt_all, particle_eta_all, and particle_phi_all.
#   • NEW: Read branch-neutral particle-level histograms from the merged ROOT and write absolute vacuum-vs-medium overlays under plots/particle_level/, matching fitter taxonomy.
#   • NEW: Use fitter-consistent axis labels/titles for accepted pre-clustering constituents: log-x/log-y for pT, linear axes for eta and phi.
#   • SAFETY: No changes to dijet selections, per-selection normalization, branch routing, filenames of existing categories, or workflow submission logic.
# - 2026-03-09: v4.60 FIX: Remove Python invalid-escape warnings from comparator string literals.
#   • FIX: Make the jetpt expected-regex diagnostic string raw so `\d{3}` is logged cleanly without SyntaxWarning.
#   • FIX: Escape Matplotlib mathtext backslashes in Mjj overlay titles (`\Delta`, `\varphi`, `\pi`) so batch runs stay warning-free under Python -Wall.
#   • SAFETY: Presentation/logging-only patch; no changes to histogram IO, normalization, filenames, folder routing, or physics selections.
# - 2026-03-08: v4.59 FIX: Remove hidden INCLUDE_XSEC_NORM_ERR default from comparisor config parsing.
#   • FIX: Require INCLUDE_XSEC_NORM_ERR to exist in jetscape.ini; hard-fail if the key is absent instead of silently defaulting to 1.
#   • FIX: Hard-fail on invalid INCLUDE_XSEC_NORM_ERR ini values so comparisor matches fitter's explicit-config contract more closely.
#   • SAFETY: Environment override behavior is unchanged, but it now layers on top of a required ini value instead of a hidden default.
# - 2026-03-08: v4.58 FIX: Reconstruct absolute-spectrum xsec normalization bands from published per-slice merged ROOT contributions instead of using one run-level xsec_total_rel_err for every bin.
#   • FIX: For each compared run, load slice rootfile/xsec_rel_err entries from ${DIR_FINAL}/xsec_summary.json and compute sigma_norm(bin)=sqrt(sum_s (r_s*y_{bin,s})^2) for absolute Mjj, jet-pT, Δφ, |Δφ|, xJ, and AJ comparisons.
#   • SAFETY: Hard-fail if any required absolute histogram is missing from a published per-slice ROOT or if per-slice/final binning disagrees, so the comparisor cannot quietly plot a fake blanket normalization band.
# - 2026-03-08: v4.57 FIX: Match fitter's xsec normalization uncertainty contract when INCLUDE_XSEC_NORM_ERR=1.
#   • FIX: Comparisor now hard-fails if either compared run is missing/unreadable ${DIR_FINAL}/xsec_summary.json or has non-finite/non-positive xsec_total_rel_err.
#   • FIX: Prevent silent dropping of the requested correlated σGen normalization band from absolute-spectrum display errors.
#   • SAFETY: No changes to histogram IO, per-selection normalization, folder routing, filenames, or SLURM workflow behavior beyond the stricter xsec metadata requirement when enabled.
# - 2026-03-06: v4.56 FIX: Make comparisor font-knob handling match fitter semantics more closely.
#   • FIX: apply_plot_style() now validates PLOT_* values the same way as fitter: invalid/non-finite/non-positive sizes fall back safely and emit warnings.
#   • FIX: Apply plot styling only after compare_dir/logs/paperreadycomparisor_py.log is open, so resolved font settings and any fallback warnings are captured in the comparisor log.
#   • FIX: Informational/statistics text boxes now use PLOT_NOTE_FONTSIZE instead of accidentally borrowing label/tick sizes.
#   • FIX: The one explicit legend override that used tick size now uses PLOT_LEGEND_FONTSIZE.
#   • FIX: 4-panel collage subplot titles now use PLOT_TITLE_FONTSIZE; PLOT_SUPTITLE_FONTSIZE remains reserved for true figure suptitles (same semantics as fitter).
#   • SAFETY: Styling-only patch; no changes to histogram IO, normalization, folder routing, filenames, or SLURM workflow behavior.
# - 2026-03-05: v4.55 FIX: Make comparisor folder/layout + ROOT reading match fitter more closely.
#   • FIX: Standard outputs now write under plots/absolute/{subfrac,nosubfrac}/<category> and
#          plots/dijet_normalized/{subfrac,nosubfrac}/<category> (same branch-first ordering as fitter),
#          instead of the old plots/<category>/{subfrac,nosubfrac} layout.
#   • FIX: Mjj reader now scans ROOT subdirectories recursively, so nosubfrac Mjj histograms written under
#          ROOT subdir nosubfrac/ are no longer silently dropped.
#   • FIX: Recursive ROOT readers now preserve nosubfrac directory context; if a histogram lives under a
#          nosubfrac/ directory but lacks the _nosubfrac suffix, comparisor canonicalizes the key so the branch
#          is still routed correctly.
#   • CHANGE: Jet-spectra comparison outputs now mirror fitter taxonomy better:
#          - absolute overlays -> plots/absolute/.../jet_spectra
#          - normalized overlays -> plots/dijet_normalized/.../jet_spectra
#          - ln overlays / ratio diagnostics remain under plots/custom
#          Inclusive jet spectra stay branch-neutral; lead/sublead keep subfrac/nosubfrac routing.
#   • FIX: Jet-R comparison outputs now use fitter-like branch routing: inclusive stays branch-neutral in
#          plots/jet_R_dependence/, while lead-jet default/nosubfrac go to sibling subfrac/ and nosubfrac/ dirs.
# - 2026-03-04: v4.53 CHANGE: Write comparison plots into sibling branch folders 'subfrac/' and 'nosubfrac/' under plots/absolute and plots/dijet_normalized (mirrors fitter). Default (with SUBFRAC) no longer writes to unlabeled base folders.
# - 2026-03-03: v4.52 CHANGE: Match fitter plot folder structure: write ONLY to plots/absolute and plots/dijet_normalized for duplicated categories (Mjj, xJ/AJ, Δφ); keep non-duplicated outputs under plots/custom and plots/jet_R_dependence.
# - 2026-03-03: v4.52 FIX: Remove duplicate legacy filename write for combined all-R Mjj plot (mjj_all_R020_R040_R050_comparisor.png). Comparisor now mirrors fitter: single output path per plot.
# - 2026-03-03: v4.50 FIX: Matplotlib mathtext: replace unsupported '\\le' with '\\leq' in Δφ comparison title ($0\leq\Delta\varphi<2\pi$).
# - 2026-03-03: v4.49 FIX: xscape_ini.expand_vars expects (p, ini); comparisor wrapper now passes cfg positionally (prevents unexpected keyword crash).
# 2026-03-03: FIX (v4.48): Pass cfg as keyword into shared expand_vars implementation (xscape_ini.expand_vars is keyword-only); prevents startup TypeError.
# 2026-03-03: FIX (v4.47): Make Δφ stats annotations robust to small negative bins (from covariance-aware per-selection normalization):
#   • _pdf_stats and _dphi_broadening_metrics now use a signed-weight estimator by default, but if total weight is non-positive
#     (pathological oversubtraction / low-stat noise), they fall back to a non-negative (clipped) estimator.
#   • This matches fitter v4.9.34 behavior where RMS is computed with a signed estimator and only falls back to clipped when needed.
# 2026-03-03: FIX (v4.46): Label honesty: per-selection normalization uses σ_sel (histogram integral for that selection), not σ_sel. Update titles/y-axis text accordingly to stay consistent with fitter.
# 2026-03-03: FIX (v4.44): read_jetpt_hists now always scans ROOT subdirectories in addition to top-level keys, so nosubfrac/jetpt_*_nosubfrac histograms written by analyze_dphi_sliced.cpp are not silently missed.
# 2026-03-03: FIX (v4.45): Make parse_bool() robust to None/empty inputs and honor default= consistently (match fitter v4.9.29 behavior).
# 2026-03-03: FIX (v4.43): Comparisor logs now go to compare_dir/logs/paperreadycomparisor_py.log (and create logs/ if missing), instead of writing directly into compare_dir.
# 2026-03-02: FIX (v4.42): Actually enforce linear-y for Δφ/|Δφ| stacked comparisons: remove remaining _apply_logy_with_floor() calls inside plot_dphi_stacked().
# 2026-03-02: CHANGE (v4.41): Make comparisor strict + consistent with fitter:
#   • ROOT input selection: remove recursive ROOT auto-discovery; hard-fail if ${DIR_FINAL}/dphi_allSlices.root is missing (unless INPUT_ROOT is set).
#   • Δφ/|Δφ| stacked plots: force linear y (remove unconditional log-y application).
#   • Logging: write to compare_dir/fit_py.log (same log filename convention as fitter).
# 2026-03-02: CHANGE (v4.40): Make covariance-mode handling strict like fitter: require COVARIANCE_MODE (or legacy PERDIJET_COV_MODE) in jetscape.ini; unknown/unsupported values now hard-fail (no silent fallback to 'diag').
# 2026-03-02: FIX (v4.39): Make abs-Δφ axis/title text match fitter: remove explicit $|\mathrm{wrap}(\phi_1-\phi_2)|$ clause; keep 'folded to $[0,\pi]$'.
#   • Presentation-only; no physics/normalization/IO changes.
#   • FIX (v4.37, 2026-03-02): Abs-Δφ labeling aligned with analyzer definition: |Δφ| ≡ |wrap(φ1−φ2)| folded to [0,π].
#     - Titles and x-axis labels now say 'folded to [0,π]' (paper-friendly) while still stating |wrap(φ1−φ2)| to avoid ambiguity.
#     - No physics/normalization/IO changes; presentation-only.
#   • FIX (v4.36, 2026-03-02): Title honesty for xJ/AJ per-selection-normalized stacks: apply safe log-y when possible and annotate suptitle with actual y-axis scaling ('log y' or 'linear y'). Consistent with fitter v4.9.22.
#   • FIX (v4.35, 2026-03-02): Title honesty for xJ/AJ absolute overlays: suptitle now reflects actual y-axis scaling ('log y' only if log scale applied; otherwise 'linear y'). Consistent with fitter v4.9.22.
#   • DOC (v4.34, 2026-03-02): Changelog cleanup only (remove stale legacy path/normalization notes that no longer reflect live code).
#     No changes to plotting, binning, normalization, outputs, or CLI behavior.
#   • CHANGE (v4.32, 2026-03-02): Remove leftover legacy per-selection-count label strings and undefined Δφ_abs output-dir call site; keep σ-based taxonomy consistent with fitter.
#   • CHANGE (2026-03-02): Remove ALL residual legacy per-selection-count comparison code paths to stay consistent with fitter (shape-only per-selection).
#   • CHANGE: Strip unused legacy helper functions and remove any legacy normalization annotations from titles.
#   • NOTE: No changes to histogram reading, binning, or σ-based normalization logic; output set is unchanged except removal of legacy per-selection-count plots.
#
# v4.29 (2026-03-02, abs Δφ definition consistency with fitter v4.9.13):
#   • FIX: For abs-Δφ panels, explicitly define the observable as the minimal wrapped separation $|\mathrm{wrap}(\phi_1-\phi_2)|\in[0,\pi]$ (avoid misreading as a naive |\phi_1-\phi_2|).
#   • STYLE: No physics/normalization changes; presentation-only.
#
# v4.28 (2026-03-02, terminology consistency with fitter v4.9.12):
#   • FIX: Replace misleading 'folded' wording for dphi_abs_* panels with 'abs' and explicitly state the domain 0≤Δφ≤π.
#   • STYLE: No physics/normalization changes; presentation-only.
#
# v4.27 (2026-03-02, Δφ title LaTeX consistency with fitter v4.9.11):
#   • FIX: Replace Unicode 'Δφ' in comparison titles with mathtext $\Delta\varphi$ (paper-friendly rendering).
#   • STYLE: No physics/normalization changes; presentation-only.
#
# v4.26 (2026-03-02, xJ/AJ label/title consistency with fitter v4.9.10):
#   • FIX: For xJ titles, use standard wording 'momentum ratio' (x_J≡p_{T,2}/p_{T,1}); keep AJ as 'momentum imbalance'.
#   • STYLE: No physics/normalization changes; presentation-only.
#
# v4.25 (2026-03-02, title/axis consistency with fitter v4.9.9):
#   • FIX: Make Mjj overlay titles explicitly refer to leading-jet pT (p_{T,1}) bin rather than an unlabeled range.
#   • FIX: For abs Δφ comparison panels, label x-axis as Δφ and state the abs domain (0≤Δφ≤π) directly on the axis label.
#   • STYLE: No physics/normalization changes; presentation-only.
#
# v4.24 (2026-03-02, Δφ labeling/title consistency with fitter v4.9.8):
#   • FIX: Remove |Δφ| notation from abs Δφ labels; use standard Δφ and state the domain in titles.
#   • FIX: Add selection annotations to Δφ comparison suptitles (|η_jet| cut, optional |y*|, and nosubfrac tag).
#   • STYLE: Keep legend semantics unchanged; only labeling/metadata improved.
#
#   • FIX: Add missing _dphi_ylabel() helper (comparisor no longer crashes in dphi stacked plots).
#   • FIX: Correct middle-panel ylabel in plot_dphi_stacked (was accidentally setting ax1 twice).
#   • DOC: Update comments/docstrings to match fitter v4.9.7 semantics.
#
# v4.22 (label/axis accuracy to match fitter v4.9.6):
#   • FIX: Use |Δφ| vs Δφ consistently in y-axis derivative notation for dphi_abs_* histograms.
#
# v4.21 (title LaTeX consistency with fitter v4.9.5):
#   • FIX: Replace Unicode |$\Delta\varphi-\pi$| in Mjj titles with mathtext $|\\Delta\\varphi-\\pi|$ for consistent rendering.
#   • STYLE: Use ASCII '-' in the expression to avoid font/substitution quirks.
#
# v4.20 (label consistency with fitter v4.9.4):
#   • FIX: Clarify xJ/AJ absolute y-axis units to densities ("mb per unit xJ/AJ") to avoid misreading as integrated mb.
#   • STYLE: Keep Δ\varphi notation consistent across all Δφ-related labels (no Δ\phi).

# v4.19 (colors: bright blue/red for 2-run comparisons):
#   • CHANGE: Replace the default vacuum/brick comparison colors (tab:blue/tab:orange) with bright blue + bright red.
#   • NOTE: Multi-color overlays (3+ curves) keep their existing palettes unchanged.

# v4.18 (plot styling knobs):
#   • NEW: Read PLOT_* font-size knobs from jetscape.ini and apply them consistently across all comparison plots.
#   • NOTE: Styling only; physics/normalization and output paths are unchanged.

# v4.17 (log-y for all xJ/AJ comparisons; consistent with fitter):
#   • SAFETY: Apply a small positive y-min floor based on the smallest positive bin value so log scale never crashes on empty tail bins.
#   • LABELS: Suptitles now include '(log y)' to make the scaling explicit in slides/papers.
#
# v4.16 (nosubfrac title tagging to match fitter v4.9.1):
#   • FIX: Add explicit ' [nosubfrac]' tag in figure titles for Δφ/Δφ_abs and xJ/AJ comparison plots when histogram name ends with _nosubfrac.
#   • CONSISTENCY: Keeps all outputs and filenames unchanged; title-only change for clarity in slides/copies.
#
#          rather than the older y/S1 construction that collapses to the same shape as 1/σ plots.
#   • FIX: COMBINE_R_LIST is now REQUIRED in jetscape.ini (no silent defaults).
#   • NEW: Applies to BOTH default and *_nosubfrac branches; existing absolute + 1/σ_sel comparison outputs unchanged.
# v4.12 (nosubfrac support: compare dijet observables without SUBFRAC cut):
#   • NEW: Recursively read ROOT subdirectories so histograms under 'nosubfrac/' are found.
#   • NEW: Accept histogram names ending with '_nosubfrac' for parsing (Δφ, Δφ_abs, jet spectra, xJ/AJ, Mjj).
#   • NEW: For *_nosubfrac histograms, write comparison plots into a 'nosubfrac/' subfolder under the usual output dirs,
#          keeping existing outputs unchanged.
#   • SAFETY: Existing histogram handling and output paths for default (SUBFRAC-applied) observables remain identical.
# v4.11 (remove custom collages requiring specific PT lead bin edges):
#   • CHANGE: Removed the Δφ_abs 4-panel collage helper and its main() call because it hard-coded lead-pT bins
#     (40–50, 50–70, 100–150, 150–200) that may not exist in PT_LEAD_BIN_EDGES, causing missing/empty panels.
# v4.10 (config consistency: covariance mode precedence + strict mismatch fail):
#   • CHANGE: COVARIANCE_MODE is now the canonical key; PERDIJET_COV_MODE is legacy fallback only.
#   • SAFETY: Hard-fail if BOTH keys are set (ini or env) and disagree, preventing silent mismatches vs fitter.
#   • DIAG: Logs exactly which key was used and the final resolved covariance mode.
#
# v4.9 (plot labeling fix):
#   • FIX: plot_dphi_stacked() now labels Δφ_abs histograms with |Δφ| on the x-axis.
#     This matches the observable domain [0,π] and keeps stacked plots consistent with the 4-panel Δφ_abs collage.
# v4.8 (multi-R tag compatibility + remove space-path aliases):
#   • FIX (multi-R): Robust R-tag decoding now supports BOTH conventions:
#       - Canonical R*100 encoding (R020 -> 0.20, R060 -> 0.60)
#       - Legacy R*1000 encoding (R200 -> 0.20, R600 -> 0.60)
#     This prevents combined-R overlays and any R-matched plots from silently dropping curves.
#   • DIAG: When legacy R*1000 tags are detected, a one-time warning is printed to the log.
# v4.7 (robust per-selection errors + no-space canonical dirs + consistent normalization):
#   • FIX (stats): normalize_per_dijet_with_cov() now marks invalid propagated variances as NaN (not 0), matching dphi_fit_py.
#   • FIX (paths): Canonical per-dijet plot root is plots/dijet_normalized (underscored; no spaces).
#   • FIX (consistency): denom_positive_only is now consistently False for ALL per-selection normalization calls (matches fitter).
#   • FIX (minor): savefig calls now occur before plt.close(fig) for any legacy outputs.
# v4.6 (ini-driven compare tags + strict failures):
#   • NEW: Read compare run tags / labels / ratio mode from jetscape.ini (COMPARE_* keys).
#          CLI/env may override but overrides are logged loudly.
#   • SAFETY: Hard-fail early if the run-tag folders do not exist under RUNS_ROOT.
#   • DIAG: Adds explicit source-of-truth logging for runA/runB/labels/ratio.
# v4.5 (bugfix: defaults + Δφ duplication + log cleanup):
#   • FIX: Update RUN_TAG defaults to current twomil tags.
#   • FIX: Ensure main always logs "Done.", closes the log handle, and returns 0 even if jet-pT hists are missing.
# v4.4 (config unification + reproducibility):
#   • NEW: Uses shared xscape_ini.py parser (same as fitter) instead of multiple ad-hoc INI readers.
#   • NEW: Reads COMBINE_R_LIST from jetscape.ini to control the combined all-R Mjj overlay (no hardcoded R list).
#   • NEW: Reads INCLUDE_XSEC_NORM_ERR and covariance mode (COVARIANCE_MODE / PERDIJET_COV_MODE) from jetscape.ini.
#          Environment variables may still override, but overrides are logged loudly.
#   • DIAG: Logs all resolved config values (including overrides) to mjj_comparisor.log for reproducible debugging.
#
# v4.3 (custom: 4-panel ln jet spectra overlay collages):
#   • NEW: After writing ln_jetpt_{lead|sublead|incl}_R0xx_overlay.png in plots/jet_spectra/, automatically creates 2×2 panel images
#     for R={0.2,0.4,0.5,0.6}.
#   • Output: plots/custom/jet_spectra_4panel_ln/ln_jetpt_<kind>_allR_4panel.png
#   • This is a collage step only: it does NOT re-plot or modify any existing outputs.
#
# v4.2 (custom: 4-panel xJ/AJ absolute collages):
#   • NEW: Writes 2×2 panel images combining existing absolute xJ and AJ stacked PNGs:
#       aj_R020/040/050/060_all_stacked.png  -> plots/custom/dijet_imbalance_4panel_abs/aj_allR_stacked_4panel.png
#       xj_R020/040/050/060_all_stacked.png  -> plots/custom/dijet_imbalance_4panel_abs/xj_allR_stacked_4panel.png
#   • This is a collage step only: it does NOT re-plot or modify any existing outputs.
#
# v4.1 (plot style: xJ/AJ absolute overlay, no ratio):
#   • CHANGE: For comparisons written to plots/absolute/dijet_imbalance/, xJ and AJ are now overlaid on a single axis
#     (vacuum + brick on the same plot) instead of the old 3-panel stack (vacuum / brick / ratio).
#   • CHANGE: Ratio panel removed for those absolute imbalance plots (per your request).
#   • COMPAT: Per-dijet-normalized (shape) xJ/AJ comparison plots keep the original stacked layout.
#
# v4.0 (custom: 4-panel Δφ_abs0pi stacks without ratio):
#   • NEW: Writes 2×2 panel images combining Δφ_abs stacked plots (vacuum on top, brick on bottom, NO ratio panel)
#     for R={0.2,0.4,0.5,0.6} and lead-pT bins {40–50, 50–70, 100–150, 150–200} GeV.
#   • Output: plots/custom/dphi_abs0pi_4panel_abs/  (existing plots are untouched).
#
# v3.9 (pT-range labeling + Δφ_abs bin coverage):
#   • NEW: Parse PT_LEAD_BIN_EDGES from jetscape.ini and use it to label inclusive “all” plots with a real pT range.
#   • NEW: Replace “all” with the actual [pTmin–pTmax] range in plot titles for Mjj overlays, Δφ/Δφ_abs stacks, and xJ/AJ stacks.
#   • NEW: Δφ_abs (0..π) comparator now plots all available pT bins from final ROOT files (not just the inclusive “all” hist).
#
# v3.8 (plot output layout: absolute vs dijet-normalized folders):
#   • NEW: Write absolute (rate) comparisons under plots/absolute/...
#   • NEW: Write per-dijet normalized (shape) comparisons under plots/dijet_normalized/...
#   • NEW: Produce absolute (not per-selection) stacked comparisons for Δφ and xJ/AJ alongside the existing per-selection stacks.
#   • NOTE: Output directory taxonomy is plots/absolute/ (rate) and plots/dijet_normalized/ (shape).
#
# v3.7 (feature: 4-panel Mjj per-selection collage):
#   • NEW: After generating dijet_mass_comparisor_perdijet plots, automatically writes a 2×2 panel image
#     combining mjj_R020/040/050/060_all_comparisor_perdijet.png into plots/custom/ (no changes to existing plots).
## v3.6 (bugfix: strict Sumw2 failure path):
#   • FIX: Missing ROOT variances (Sumw2) is now a hard failure (no silent skip that fakes precision).
#
# v3.5 (bugfix, robustness):
#   • FIX: Prevent matplotlib mathtext crashes in xJ/AJ stacked plots by using valid TeX strings and
#     falling back to plain unicode labels if the local Matplotlib mathtext parser rejects them.
#   • FIX: Correct accidental double-backslash TeX in plot_imbalance_stacked() y-axis labels (\sigma, \, \mathrm).
#
# v3.4 (bugfix):
#   • FIX: Define xlabel inside plot_imbalance_stacked() (prevents NameError; correct x-axis label for xJ/AJ plots).
# v3.3 (bugfix):
#   • FIX: Restore missing load_xsec_rel_err() helper (prevents NameError in main when INCLUDE_XSEC_NORM_ERR=1).
#     Reads xsec_total_rel_err from DIR_FINAL/xsec_summary.json (written by merge step).
#
# v3.2 (strict variances + safer uncertainty models):
#   • NEW: Require stored histogram variances (Sumw2). If missing, abort with a clear error.
#   • FIX: Keep σGen normalization uncertainty separate from statistical bin errors.
#     - Plots may optionally show stat⊕norm, but nothing treats σGen as uncorrelated per-bin noise.
#   • FIX: Redesign PERDIJET_COV_MODE=conservative so it cannot shrink uncertainties.
#     (conservative now inflates Var(σ_sel) but applies NO Cov(y_i,σ) term.)
#   • FIX: Define PERDIJET_COV_MODE and INCLUDE_XSEC_NORM_ERR defaults (they were referenced but not set).
#

# v3.1 (uncertainty plumbing + unit labels):
#   • FIX: xJ/AJ y-axis labels corrected to densities for absolute spectra (dσ/dx_J, dσ/dA_J).
#   • NEW: PERDIJET_COV_MODE={diag|conservative} to choose diagonal vs conservative σ_sel uncertainty model.
#   • NEW: optional σGen normalization-uncertainty inflation for absolute-spectrum error bars when each run has final/xsec_summary.json (INCLUDE_XSEC_NORM_ERR=1).
#
# v3.0 (new: Δφ_abs 0..π comparator):
#   • NEW: Compare standard Δφ_abs histograms (dphi_abs_Rxxx_*) in addition to the original ordered Δφ (dphi_Rxxx_*).
#   • NEW: Writes Δφ_abs comparison plots into plots/dphi_abs0pi_comparisor/ (keeps original plots/dphi_comparisor/).
#   • MINOR: Δφ stacked plot title auto-labels Δφ_abs vs Δφ ordered.

# v2.9 (bugfix: jet pT hist parsing):
#   • FIX: parse_jetpt_name() accidentally returned None for all jetpt_* hists due to mis-indentation.
#     This made jet_R_dependence / jet_spectra / jet_spectra_ratio come out empty even when the ROOT file had the hists.
#   • DIAG: When jetpt keys are seen but none are accepted, print the expected regex and a few example keys.

# v2.8 (bugfix):
#   • FIX: Remove a stray '(root_path: str):' line that broke Python parsing (IndentationError at line ~558).
#
# v2.7 (robustness: jet pT hist discovery + better diagnostics):
#   • FIX: If jetpt_* hists are not found at the ROOT top-level, also search recursively in subdirectories.
#   • More explicit guidance when jet pT histograms are missing (usually stale analyzer binary → rerun analysis+merge).
#
# v2.6 (plot hygiene):
#   • FIX: Suppress Matplotlib 'tight_layout' warnings for stacked figures (Δφ, xJ/AJ) without changing plot content.
#     (Warnings were harmless but noisy in batch logs.)
#
# v2.5 (bugfix):
#   • FIX: Remove accidental multi-line f-strings that broke Python parsing (newline -> \n).
#   • FIX: Correct LaTeX label for Δφ axis (\varphi) so matplotlib renders properly.
#   • No physics/plot logic changes.

# v2.4 (new: Δφ + dijet imbalance + jet-R dependence comparisons):
#   • NEW: Δφ comparison: vacuum panel on top, brick panel on bottom, plus a ratio panel (brick/vac or inverse).
#     Includes simple broadening metrics (peak-width proxy + tail fraction) on the plot.
#   • NEW: Dijet momentum imbalance comparisons (xJ and AJ): same stacked layout + ratio.
#   • NEW: Jet radius dependence: (dσ/dpT)_{R=0.2}/(dσ/dpT)_{R=0.4} in each medium, plus a double-ratio.
#
# v2.3 (minor, plot readability + subleading jets):
#   • Combined Mjj all-R comparator now uses SIX distinct colors (one per curve), not 2.
#   • Jet spectra plots now include subleading jets too (requires analyze_dphi_sliced.cpp v5.6+).
#   • Default marker size reduced slightly.
#
# v2.2 (stats fix: correct per-selection uncertainties):
#   • FIX: Per-dijet normalized Mjj overlays now propagate σ_sel uncertainty,
#     including numerator–denominator covariance (σ_sel is computed from the same bins).
#   • Central values are unchanged; only error bars on per-selection-normalized plots change.
#
# v2.1 (minor: ratio + plot hygiene fixes):
#   • FIX: Jet spectrum ratio plot now draws ONE curve by default: brick/vacuum (medium/reference).
#          Use --ratio-mode inv (or COMP_RATIO_MODE=inv) to plot vacuum/brick instead.
#   • NEW: --ms (or COMP_MS) controls marker size everywhere; default is smaller to reveal subtle differences.
#   • FIX: Log-scale spectra plots no longer clip zeros to fake tiny values; non-positive bins are skipped.
#   • FIX: Log-scale errorbars use asymmetric lower errors capped so y - err > 0 (matplotlib log safety).
#   • FIX: Auto x-limits applied consistently based on non-zero bins (no giant empty canvas).
#   • NEW: Robust ROOT input discovery fallback: if final/dphi_allSlices.root is missing, scan run/analysis for best candidate.
#   • FIX: Legend text prints “vacuum” instead of “vaccum” (folders unchanged).
#
# v2.0 (major: per-selection normalization + jet spectra comparisons):
#   • NEW: Makes per-selection normalized Mjj overlays: (1/σ_sel) dσ/dMjj [1/GeV].
#   • NEW: Reads jet pT spectra histograms (jetpt_lead_* and jetpt_incl_*) from each run and plots:
#       - dσ/dpT vs pT (log-log)
#       - ln(dσ/dpT) vs pT (as requested)
#       - Ratio curves: R(pT) = (dσ/dpT)_vac / (dσ/dpT)_brick and its inverse.
#   • Keeps all previous Mjj overlay plots (mb/GeV) unchanged.
#
# v1.1 (minor):
#   • FIX: Auto-pick per-plot X-axis limits from the actual non-zero Mjj bins (vacuum/brick),
#          so plots don’t waste half the canvas on empty log-range.
#   • Combined “all-R” plot now also uses data-driven X limits (with padding).
#
# v1.0 (major):
#   • NEW: Overlay dijet invariant-mass (Mjj) histograms from TWO run-tags (e.g. vaccum vs brick) on the same plots.
#   • Reads ${DIR_FINAL}/dphi_allSlices.root for each tag and writes comparison plots to:
#       $HOME/xscape_runs/comparisons/<TAG_A>_vs_<TAG_B>/plots/dijet_mass_comparisor/
#   • Produces one overlay plot per Mjj histogram (mjj_Rxxx_all and mjj_Rxxx_<ptlo>_<pthi>)
#     plus a combined “all” plot for R=0.20/0.40/0.50 (6 curves total).
#
# Notes:
#   • Edit RUN_TAG_A / RUN_TAG_B below when you want to compare different configurations.
#   • You may also override via environment variables COMP_RUN_TAG_A / COMP_RUN_TAG_B.
#
# (No run instructions here because it's not a .cpp file. You humans can follow your own scripts.)

from __future__ import annotations

import os
import json
import re
import sys
import math
import time
import warnings
import argparse
from collections import Counter
from typing import Dict, Tuple, Optional, List

import numpy as np

# --------------------------- Plot colors (2-run compares) ---------------------------
# Claude doesn't like orange. Fair.
# These are used ONLY when we compare exactly two runs (reference/vacuum vs medium).
# Multi-curve overlays intentionally keep their existing palettes.
COMPARE_COLOR_A = '#0000FF'  # ROOT-like blue
COMPARE_COLOR_B = '#FF0000'  # ROOT-like red
PAPERREADY_MODE = True
PAPERREADY_SHOW_CAPTION = True
PAPERREADY_CAPTION_PREFIX = 'Figure: '
PAPERREADY_STYLE_COLORS_A = ['#0000FF', '#0000FF', '#0000FF', '#0000FF', '#0000FF', '#0000FF']
PAPERREADY_STYLE_COLORS_B = ['#FF0000', '#FF0000', '#FF0000', '#FF0000', '#FF0000', '#FF0000']
PAPERREADY_STYLE_MARKERS = ['s', 'o', 'D', '^', 'v', 'P']
PAPERREADY_MULTI_R_COLORS = ['#1f77b4', '#d62728', '#2ca02c', '#9467bd', '#8c564b', '#17becf', '#e377c2', '#7f7f7f']

from typing import Iterable


# Resolved plot font sizes (overridable via jetscape.ini PLOT_* knobs).
_FONTS = {
    'base': 12.0, 'title': 14.0, 'suptitle': 16.0, 'label': 12.0,
    'tick': 11.0, 'legend': 11.0, 'note': 10.0,
}

def _strip_nosubfrac_suffix(hn: str) -> Tuple[str, bool]:
    """Return (base_name, is_nosubfrac) for histogram names."""
    if hn.endswith("_nosubfrac"):
        return (hn[:-10], True)
    return (hn, False)


def _iter_root_items_recursive(f, prefix: str = "") -> Iterable[Tuple[str, object, str, bool]]:
    """Yield (leaf_name, obj, full_path, in_nosubfrac_dir) pairs, descending into ROOT subdirectories."""
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


def _iter_root_objects(root_path: str):
    """Yield ROOT objects recursively with normalized leaf names and nosubfrac-directory flags."""
    with uproot.open(root_path) as f:
        def _walk(dir_obj, path_prefix: str = ""):
            try:
                items = list(dir_obj.items())
            except Exception:
                items = []
            for name, obj in items:
                key = name.split(";")[0]
                key_leaf = key.split("/")[-1]
                try:
                    cls = getattr(obj, "classname", "")
                    cls = str(cls) if not isinstance(cls, str) else cls
                except Exception:
                    cls = ""
                if cls.startswith("TDirectory") or cls.startswith("TDirectoryFile"):
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


def _canonical_hist_key(hn: str, *, in_ns_dir: bool = False) -> str:
    """Preserve nosubfrac branch identity even when the ROOT directory encodes it but the leaf name does not."""
    if not isinstance(hn, str):
        return hn
    if in_ns_dir and not hn.endswith("_nosubfrac"):
        return f"{hn}_nosubfrac"
    return hn


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
            yield (
                key_leaf,
                centers.astype(float),
                np.asarray(vals, dtype=float),
                errs.astype(float),
                widths.astype(float),
                np.asarray(variances, dtype=float),
                entries,
                bool(in_ns_dir),
            )
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
            yield (
                key_leaf,
                centers.astype(float),
                np.asarray(vals, dtype=float),
                np.asarray(errs, dtype=float),
                widths.astype(float),
                np.asarray(variances, dtype=float),
                entries,
                bool(in_ns_dir),
            )
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
            yield (
                key_leaf,
                np.asarray(xedges, dtype=float),
                np.asarray(yedges, dtype=float),
                np.asarray(vals, dtype=float),
                errs.astype(float),
                np.asarray(variances, dtype=float),
                entries,
                bool(in_ns_dir),
            )
        except RuntimeError:
            raise
        except Exception as e:
            _log(f"[WARN] Skipping TH2 '{key_leaf}': {e}")


def _log_family_discovery_summary(family: str, root_path: str, out: Dict[str, tuple]) -> None:
    total = len(out)
    n_ns = sum(1 for k in out if isinstance(k, str) and k.endswith('_nosubfrac'))
    n_sub = total - n_ns
    _log(f"[DEBUG][{family}] discovery summary from {root_path}: total={total} subfrac={n_sub} nosubfrac={n_ns}")
    if total > 0:
        shown = 0
        for key in sorted(out):
            if isinstance(key, str) and key.endswith('_nosubfrac'):
                _log(f"[DEBUG][{family}] nosubfrac sample: {key}")
                shown += 1
                if shown >= 6:
                    break
    else:
        _log(f"[DEBUG][{family}] no matching histograms discovered in {root_path}")


# ------------------------------ shared INI parser ------------------------------
try:
    from xscape_ini import read_ini as _read_ini_obj, parse_list as _ini_parse_list, parse_bool as _ini_parse_bool, expand_vars as _ini_expand_vars
except Exception as _e:
    raise SystemExit(
        "[FATAL] Could not import shared INI parser 'xscape_ini.py'. "
        "Make sure xscape_ini.py is in the same directory as this script or on PYTHONPATH. "
        f"Import error: {_e}"
    )

# ------------------------------ mathtext safety ----------------------------
# Some clusters ship Matplotlib builds whose mathtext parser is picky about TeX markers.
# We validate labels up-front and fall back to plain-text to avoid savefig crashes in batch.
try:
    from matplotlib.mathtext import MathTextParser  # type: ignore
    _MATH_PARSER = MathTextParser("agg")
except Exception:
    _MATH_PARSER = None

def _mathtext_ok(s: str) -> bool:
    if _MATH_PARSER is None:
        return False
    try:
        _MATH_PARSER.parse(s, dpi=120)
        return True
    except Exception:
        return False

def _choose_label(tex: str, plain: str) -> str:
    return tex if _mathtext_ok(tex) else plain


# ------------------------------ plot layout --------------------------------

def _apply_logy_with_floor(ax, y_arrays, *, floor_factor: float = 0.5) -> None:
    """Apply log-y scaling with a robust positive lower bound.

    Log scaling cannot display y<=0. For weighted/density histograms, tail bins can be exactly zero.
    We set a small positive floor based on the smallest positive bin value across the provided arrays.
    """
    vals = []
    for arr in (y_arrays if isinstance(y_arrays, (list, tuple)) else [y_arrays]):
        if arr is None:
            continue
        a = np.asarray(arr, dtype=float)
        a = a[np.isfinite(a)]
        a = a[a > 0.0]
        if a.size:
            vals.append(float(np.min(a)))
    ymin = (floor_factor * min(vals)) if vals else 1e-12
    if not np.isfinite(ymin) or ymin <= 0.0:
        ymin = 1e-12

    cur = ax.get_ylim()
    if cur and len(cur) == 2 and np.isfinite(cur[1]) and cur[1] > ymin:
        cur_top = float(cur[1])
    elif vals:
        vmax = max(vals)
        cur_top = max(vmax * 1.6, ymin * 10.0)
    else:
        cur_top = max(1.0, ymin * 10.0)

    ax.set_ylim(bottom=ymin, top=cur_top)
    with warnings.catch_warnings():
        warnings.filterwarnings(
            'ignore',
            message=r'.*Data has no positive values, and therefore cannot be log-scaled.*',
            category=UserWarning,
        )
        ax.set_yscale("log")
    ax.set_ylim(bottom=ymin, top=cur_top)

def _safe_tight_layout(fig, *, rect=None) -> None:
    """Apply tight_layout while suppressing Matplotlib's 'not compatible' warning.

    This warning is harmless for our stacked figures but it clutters SLURM logs.
    We keep the exact same layout call (tight_layout) and just silence the noise.
    """
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=r".*Axes that are not compatible with tight_layout.*",
            category=UserWarning,
        )
        if rect is None:
            fig.tight_layout()
        else:
            fig.tight_layout(rect=rect)


def _wrap_title_two_lines(title: str, *, max_chars: int = 110) -> str:
    """Wrap only genuinely long titles onto two centered lines without dropping content.

    Preference order for the split point:
      1) before a trailing selection bracket ' ['
      2) after a colon ': '
      3) after a semicolon or comma near the midpoint
      4) nearest plain space to the midpoint
    """
    s = str(title or "").strip()
    if not s or "\n" in s or len(s) <= max_chars:
        return s

    n = len(s)
    mid = 0.56 * n
    candidates = []

    def _add_candidates(token: str, keep_on_first: int, priority: int) -> None:
        start = 0
        while True:
            idx = s.find(token, start)
            if idx < 0:
                break
            split_at = idx + keep_on_first
            if 0 < split_at < n:
                frac = split_at / max(n, 1)
                if 0.25 <= frac <= 0.82:
                    candidates.append((priority, abs(split_at - mid), split_at))
            start = idx + 1

    _add_candidates(" [", 1, 0)
    _add_candidates(": ", 1, 1)
    _add_candidates("; ", 1, 2)
    _add_candidates(", ", 1, 3)

    if not candidates:
        for idx, ch in enumerate(s):
            if ch == " ":
                frac = idx / max(n, 1)
                if 0.25 <= frac <= 0.82:
                    candidates.append((9, abs(idx - mid), idx))

    if not candidates:
        return s

    _, _, split_at = min(candidates)
    left = s[:split_at].rstrip()
    right = s[split_at:].lstrip()
    if not left or not right:
        return s
    return left + "\n" + right


def _latexish_to_plain_text(s: str) -> str:
    out = str(s or '')
    replacements = [
        ('\\Delta', 'Δ'), ('\\varphi', 'φ'), ('\\phi', 'φ'), ('\\pi', 'π'),
        ('\\sigma', 'σ'), ('\\eta', 'η'), ('\\mathrm', ''), ('\\left', ''), ('\\right', ''),
        ('\\,', ' '), ('\\;', '; '), ('\\_', '_'), ('\\leq', '≤'), ('\\geq', '≥'),
        ('^\\circ', '°'), ('\\circ', '°'), ('\\to', '→'), ('\\times', '×'), ('\\sqrt', 'sqrt'), ('\\/', '/'),
    ]
    for old, new in replacements:
        out = out.replace(old, new)
    out = out.replace('$', '')
    out = out.replace('{', '').replace('}', '')
    while '  ' in out:
        out = out.replace('  ', ' ')
    return out.strip()


def _wrap_caption_text(title: str, *, max_chars: int = 118) -> str:
    base = _latexish_to_plain_text(title)
    if not base:
        return ''
    words = (PAPERREADY_CAPTION_PREFIX + base).split()
    lines = []
    cur = ''
    for word in words:
        proposal = word if not cur else cur + ' ' + word
        if len(proposal) <= max_chars:
            cur = proposal
            continue
        if cur:
            lines.append(cur)
            cur = word
        else:
            lines.append(proposal)
            cur = ''
    if cur:
        lines.append(cur)
    return '\n'.join(lines)


def _set_paperready_caption(fig, title: str, *, max_chars: int = 118) -> str:
    wrapped = _wrap_caption_text(title, max_chars=max_chars)
    setattr(fig, '_paperready_caption', wrapped)
    return wrapped


def _draw_paperready_caption(fig) -> None:
    global PAPERREADY_SHOW_CAPTION
    if not PAPERREADY_SHOW_CAPTION:
        return
    caption = getattr(fig, '_paperready_caption', '')
    if not caption:
        return
    n_lines = max(1, str(caption).count('\n') + 1)
    extra_bottom = 0.12 + 0.04 * max(0, n_lines - 1)
    try:
        cur_bottom = float(fig.subplotpars.bottom)
    except Exception:
        cur_bottom = 0.11
    if extra_bottom > cur_bottom:
        fig.subplots_adjust(bottom=extra_bottom)
    fig.text(0.5, 0.02, caption, ha='center', va='bottom', fontsize=_FONTS.get('caption', _FONTS.get('note', 11)))


def _set_wrapped_ax_title(ax, title: str, *, max_chars: int = 96, pad_single: float = 6.0, pad_wrapped: float = 9.0) -> str:
    wrapped = _wrap_title_two_lines(title, max_chars=max_chars)
    ax.set_title(wrapped, loc='center', pad=(pad_wrapped if '\n' in wrapped else pad_single))
    return wrapped


def _set_wrapped_suptitle(fig, title: str, *, y: float = 0.98, max_chars: int = 110):
    wrapped = _wrap_title_two_lines(title, max_chars=max_chars)
    fig.suptitle(wrapped, x=0.5, y=y, ha='center')
    return wrapped


def _suptitle_rect_top(title: str, top_single: float = 0.97, top_wrapped: float = 0.93) -> float:
    return 0.985


def _ax_title_rect_top(title: str, top_single: float = 0.98, top_wrapped: float = 0.94) -> float:
    return 0.985

# ------------------ per-selection normalization w/ covariance ------------------

def normalize_per_dijet_with_cov(
    y: np.ndarray,
    ye: np.ndarray,
    bw: np.ndarray,
    *,
    denom_positive_only: bool=False,
    cov_mode: str="diag",
) -> Tuple[float, Optional[np.ndarray], Optional[np.ndarray]]:
    """
    Per-dijet normalization for differential spectra:

        y_n = y / σ   with   σ = ∑_j (y_j * bw_j)

    If σ is computed from the SAME histogram bins, y and σ are correlated.
    Two (approximate) covariance models are supported:

      • cov_mode="diag" (default): independent-bin approximation (diagonal covariance only),
        but includes the shared-denominator correlation via Cov(y_i,σ)=bw_i Var(y_i).

      • cov_mode="conservative" (alias: "upperbound"): inflates Var(σ) using an upper-bound style model.
        To guarantee it never *shrinks* uncertainties, it does NOT apply a Cov(y_i,σ) term (cov=0).
        Use "diag" for the correlated-denominator model.

    denom_positive_only:
        If True, σ integrates only bins with y>0. Then Cov(y_i,σ)=0 for bins with y<=0.
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
        var_sigma = float(np.sum((bw_d*bw_d) * np.where(m_denom, var_y, 0.0)))
        cov = np.where(m_denom, bw * var_y, 0.0)

    y_n = y / sigma

    var_n = (var_y / (sigma*sigma)) + ((y*y) * var_sigma / (sigma**4)) - (2.0 * y * cov / (sigma**3))
    bad = (~np.isfinite(var_n)) | (var_n < 0)
    if np.any(bad):
        # Do NOT clip to 0: that fakes “perfect” error bars in unstable / undefined regimes.
        # Match fitter behavior: mark invalid propagated bins with NaN.
        try:
            _log(f"[WARN] per-selection variance invalid in {int(np.sum(bad))}/{var_n.size} bins; setting those errors to NaN (not 0).")
        except Exception:
            pass
        var_n = var_n.astype(float, copy=True)
        var_n[bad] = np.nan
    ye_n = np.sqrt(var_n)

    return sigma, y_n, ye_n


def normalize_by_selected_dijet_count(
    y: np.ndarray,
    ye: np.ndarray,
    count: int,
) -> Tuple[float, Optional[np.ndarray], Optional[np.ndarray]]:
    """Single-slice selected-count normalization for dijet-normalized plots.

    Analyzer histograms entering the comparisor are already bin-width scaled.
    In SINGLE_SLICE_MODE, the merged count summary provides the corresponding
    selected dijet denominator, so the plotted density is y / N_dijet,sel with
    statistical errors propagated by the same constant factor.
    """
    try:
        c = float(count)
    except Exception:
        return float("nan"), None, None
    if not (np.isfinite(c) and c > 0.0):
        return float("nan"), None, None
    y = np.asarray(y, dtype=float)
    ye = np.asarray(ye, dtype=float)
    return c, y / c, ye / c
import matplotlib
matplotlib.use("Agg")  # headless (SLURM)
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec
from matplotlib.colors import LogNorm

import uproot


# --------------------------- USER EDIT (defaults) ---------------------------
# Compare targets are now read from jetscape.ini (single source of truth):
#   COMPARE_RUN_TAG_A / COMPARE_RUN_TAG_B
#   COMPARE_LABEL_A   / COMPARE_LABEL_B
#   COMPARE_RATIO_MODE (med|inv)
# You may still override via CLI (--runA/--runB/--labelA/--labelB/--ratio-mode) or env
# (COMP_RUN_TAG_A/B, COMP_LABEL_A/B, COMP_RATIO_MODE). Overrides are logged loudly.
RUN_TAG_A_DEFAULT = ""
RUN_TAG_B_DEFAULT = ""

LABEL_A_DEFAULT = "vacuum"
LABEL_B_DEFAULT = "medium"

# Want this combined plot too (configured via jetscape.ini: COMBINE_R_LIST=(...)):
COMBINED_R_LIST: List[float] = []  # set in main() after reading ini
JET_RADIUS_COMPARE_PAIRS: List[Tuple[float, float]] = []  # first configured R over each later configured R

# Plot controls (can override via CLI/env)
DEFAULT_RATIO_MODE = "med"  # 'med' => medium/reference, 'inv' => reference/medium
DEFAULT_MARKER_SIZE = 1.8    # smaller markers help reveal subtle differences


# -------------------------- uncertainty knobs ---------------------------
# PERDIJET_COV_MODE controls the propagated uncertainty on (1/σ_sel)·dσ/dx style shapes.
#   diag         : diagonal-bin approximation with Cov(y_i,σ)=bw_i Var(y_i) (correlated denominator).
#   conservative : upper-bound Var(σ_sel) but NO Cov(y_i,σ) term (cannot shrink uncertainties).
PERDIJET_COV_MODE: str = "diag"  # set in main() from jetscape.ini (env override allowed)

# INCLUDE_XSEC_NORM_ERR affects *plotting only* for absolute spectra (mb/GeV, mb/rad, ...).
# σGen is a correlated normalization uncertainty and must not be treated as uncorrelated bin noise.
INCLUDE_XSEC_NORM_ERR: int = 1  # set in main() from jetscape.ini (env override allowed)

# Global σGen-relative uncertainties for the two runs (set in main, used only for plotting/logging).
XSEC_REL_A: float = float("nan")
XSEC_REL_B: float = float("nan")
XSEC_BAND_A = None
XSEC_BAND_B = None


# Leading-jet pT bin edges (from jetscape.ini) for nicer, presentation-friendly titles.
# If PT_LEAD_BIN_EDGES cannot be parsed, plots will fall back to showing "all".
PT_LEAD_BIN_EDGES: List[float] = []
PT_ALL_LABEL: str = "all"
JET_PT_MAX_CFG: float = float("nan")
DPHI_RATIO_REBIN_FACTOR: int = 1
DPHI_ABS_RATIO_REBIN_FACTOR: int = 1
RATIO_YLIMS: Dict[str, Tuple[float, float]] = {}
CFG_FOR_TITLES: Dict[str, str] = {}
EXACT_TWO_JETS_REQUIRED: bool = False
IMBALANCE_REQUIRE_BACKTOBACK: bool = False
IMBALANCE_BACKTOBACK_TOL_DEG: float = float("nan")

def init_pt_lead_labels_from_ini(cfg: Dict[str, str]) -> None:
    """Initialize PT_LEAD_BIN_EDGES and PT_ALL_LABEL from jetscape.ini."""
    global PT_LEAD_BIN_EDGES, PT_ALL_LABEL
    raw = (cfg.get("PT_LEAD_BIN_EDGES", "") or "").strip()
    edges = parse_list(raw)
    PT_LEAD_BIN_EDGES = edges
    if len(edges) >= 2 and all(np.isfinite(edges)):
        PT_ALL_LABEL = f"{edges[0]:g}–{edges[-1]:g} GeV"
    else:
        PT_ALL_LABEL = "all"
    _log(f"[cfg] PT_LEAD_BIN_EDGES(raw)={raw!r}")
    _log(f"[cfg] PT_LEAD_BIN_EDGES(parsed)={PT_LEAD_BIN_EDGES}")
    _log(f"[cfg] PT_ALL_LABEL={PT_ALL_LABEL}")

def _pt_label(lo: float, hi: float, is_all: bool) -> str:
    if is_all:
        return PT_ALL_LABEL
    return f"{lo:g}–{hi:g} GeV"


def _hist_edge_tag(v: float) -> str:
    fv = float(v)
    if np.isfinite(fv) and abs(fv - round(fv)) <= 1e-9:
        return str(int(round(fv)))
    return f"{fv:g}"


def _fullrange_hist_name(prefix: str, R: float) -> str:
    rtag = f"R{int(round(float(R) * 100)):03d}"
    if len(PT_LEAD_BIN_EDGES) >= 2 and all(np.isfinite(float(x)) for x in PT_LEAD_BIN_EDGES):
        return f"{prefix}_{rtag}_{_hist_edge_tag(PT_LEAD_BIN_EDGES[0])}_{_hist_edge_tag(PT_LEAD_BIN_EDGES[-1])}_fullrange"
    return f"{prefix}_{rtag}_all"


def _legacy_all_hist_name(prefix: str, R: float) -> str:
    return f"{prefix}_R{int(round(float(R) * 100)):03d}_all"


def _hist_name_candidates(prefix: str, R: float, *, is_nosubfrac: bool = False) -> List[str]:
    base = [_fullrange_hist_name(prefix, R), _legacy_all_hist_name(prefix, R)]
    if is_nosubfrac:
        return [f"{name}_nosubfrac" for name in base]
    return base


def _existing_hist_name(prefix: str, R: float, existing_a=None, existing_b=None, *, is_nosubfrac: bool = False) -> str:
    candidates = _hist_name_candidates(prefix, R, is_nosubfrac=is_nosubfrac)
    if existing_a is None and existing_b is None:
        return candidates[0]
    for name in candidates:
        have_name = ((existing_a is None or name in existing_a) and (existing_b is None or name in existing_b))
        if have_name:
            return name
    return candidates[0]


def _pt_label_from_hist_name(hn: str) -> str:
    parsers = []
    if hn.startswith("dphi_abs_"):
        parsers.append(parse_dphi_abs_name)
    if hn.startswith("dphi_"):
        parsers.append(parse_dphi_name)
    if hn.startswith("xj_"):
        parsers.append(parse_xj_name)
    if hn.startswith("aj_"):
        parsers.append(parse_aj_name)
    if hn.startswith("mjj_"):
        parsers.append(parse_mjj_name)
    if hn.startswith("h2_dphi_abs_vs_deta_"):
        parsers.append(lambda name: parse_dphi_abs_vs_deta_h2_name(name)[:4] if parse_dphi_abs_vs_deta_h2_name(name) is not None else None)
    for fn in parsers:
        try:
            tag = fn(hn)
        except Exception:
            tag = None
        if tag is None:
            continue
        try:
            _Rv, lo, hi, is_all = tag
            return _pt_label(float(lo), float(hi), bool(is_all))
        except Exception:
            continue
    return PT_ALL_LABEL


# --------------------------- tiny utils / logging ---------------------------
_LOG_FH = None
_LOG_BUFFER: List[str] = []
SELECTED_DIJET_COUNT_SEMANTICS_EXPECTED = "event_level_selected_dijet_pair_counts"
_PLOT_WRITE_COUNTS = {'real': 0, 'placeholder': 0}
_PLOT_WRITE_BY_BUCKET = {'real': Counter(), 'placeholder': Counter()}

def _ts() -> str:
    return time.strftime("%F %T")

def _set_log_file(path: str, mode: str = "a") -> None:
    global _LOG_FH, _LOG_BUFFER
    if _LOG_FH:
        try:
            _LOG_FH.close()
        except Exception:
            pass
        _LOG_FH = None
    _LOG_FH = open(path, mode, encoding="utf-8")
    if _LOG_BUFFER:
        for s in _LOG_BUFFER:
            _LOG_FH.write(s + "\n")
        _LOG_FH.flush()
        _LOG_BUFFER = []

def _log(msg: str) -> None:
    s = f"[{_ts()}] {msg}"
    print(s)
    global _LOG_FH, _LOG_BUFFER
    if _LOG_FH:
        _LOG_FH.write(s + "\n")
        _LOG_FH.flush()
    else:
        _LOG_BUFFER.append(s)


def _plot_bucket(out_path: str) -> str:
    rp = str(out_path or '').replace('\\', '/')
    if '/plots/dijet_normalized/' in rp:
        return 'plots/dijet_normalized'
    if '/plots/absolute/' in rp:
        return 'plots/absolute'
    if '/plots/particle_level/' in rp:
        return 'plots/particle_level'
    if '/plots/lead_sublead_correlation/' in rp:
        return 'plots/lead_sublead_correlation'
    if '/plots/jet_R_dependence/' in rp:
        return 'plots/jet_R_dependence'
    if '/plots/custom/' in rp:
        return 'plots/custom'
    return os.path.basename(os.path.dirname(rp)) or 'other'


def _record_plot_write(out_path: str, *, placeholder: bool) -> None:
    kind = 'placeholder' if placeholder else 'real'
    _PLOT_WRITE_COUNTS[kind] += 1
    _PLOT_WRITE_BY_BUCKET[kind][_plot_bucket(out_path)] += 1


def _save_figure(fig, out_path: str, *, dpi: int = 170, placeholder: bool = False) -> None:
    ensure_dir(os.path.dirname(out_path))
    _draw_paperready_caption(fig)
    with warnings.catch_warnings():
        warnings.filterwarnings(
            'ignore',
            message=r'.*Data has no positive values, and therefore cannot be log-scaled.*',
            category=UserWarning,
        )
        fig.savefig(out_path, dpi=dpi, bbox_inches='tight', pad_inches=0.03)
    _record_plot_write(out_path, placeholder=placeholder)


def _log_plot_write_summary() -> None:
    real = int(_PLOT_WRITE_COUNTS.get('real', 0))
    placeholder = int(_PLOT_WRITE_COUNTS.get('placeholder', 0))
    total = real + placeholder
    _log(f"[summary] plot files written: total={total} real={real} placeholders={placeholder}")
    for kind in ('real', 'placeholder'):
        bucket_counts = _PLOT_WRITE_BY_BUCKET.get(kind, Counter())
        if not bucket_counts:
            continue
        parts = [f"{bucket}={int(count)}" for bucket, count in sorted(bucket_counts.items())]
        _log(f"[summary] {kind} plot counts by bucket: " + ', '.join(parts))


def _die(msg: str, code: int = 2) -> None:
    _log(f"[FATAL] {msg}")
    raise SystemExit(code)

def _canon_cov_mode(raw: str) -> Tuple[str, str]:
    """Return (mode, note). Supported: diag, conservative (aka upperbound).

    Strict by design: unknown/unsupported values hard-fail to prevent silent
    mismatch between fitter and comparisor.
    """
    m = (raw or "").strip().lower()
    if m in ("diag", "diagonal"):
        return "diag", ""
    if m in ("conservative", "upperbound", "upper-bound", "ub"):
        return "conservative", ""
    if not m:
        raise ValueError("missing covariance mode (empty string)")
    raise ValueError(f"unsupported covariance mode {raw!r} (supported: diag, conservative)")
def ensure_dir(p: str) -> None:
    os.makedirs(p, exist_ok=True)


def _selected_count_is_positive(count: Optional[int]) -> bool:
    return count is not None and int(count) > 0


def _selected_count_skip_reason(labelA: str, countA: Optional[int], labelB: str, countB: Optional[int], observable_label: str) -> str:
    def _fmt(label: str, count: Optional[int]) -> str:
        if count is None:
            return f"{label}: unavailable"
        return f"{label}: {int(count)}"
    return (
        f"Single-slice normalized {observable_label} comparison is undefined because the selected-dijet denominator is zero or non-positive in at least one compared run.\n"
        f"{_fmt(labelA, countA)}\n"
        f"{_fmt(labelB, countB)}"
    )


def _write_unavailable_placeholder(out_path: str, title: str, reason: str, *, ylabel: Optional[str] = None) -> None:
    ensure_dir(os.path.dirname(out_path))
    fig, ax = plt.subplots(figsize=(9, 7))
    ax.set_axis_off()
    wrapped_title = _set_wrapped_suptitle(fig, title, y=0.98, max_chars=96)
    body = "Output intentionally skipped.\n\n" + str(reason).strip()
    if ylabel:
        body += f"\n\nExpected y-axis: {ylabel}"
    ax.text(
        0.5, 0.5, body,
        transform=ax.transAxes,
        ha='center', va='center', fontsize=_FONTS['note'],
        bbox=dict(boxstyle='round,pad=0.45', facecolor='white', alpha=0.92, edgecolor='black')
    )
    fig.tight_layout(rect=[0, 0, 1, _suptitle_rect_top(wrapped_title, top_single=0.95, top_wrapped=0.90)])
    _save_figure(fig, out_path, dpi=170, placeholder=True)
    plt.close(fig)


def load_xsec_rel_err(final_dir: str) -> float:
    """Load σGen relative uncertainty from ${DIR_FINAL}/xsec_summary.json.

    Returns NaN if missing/unreadable.
    """
    try:
        p = os.path.join(final_dir, "xsec_summary.json")
        with open(p, "r", encoding="utf-8") as f:
            j = json.load(f)
        v = float(j.get("xsec_total_rel_err", float("nan")))
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
        finite_pt = (ptlo is not None and pthi is not None and np.isfinite(float(ptlo)) and np.isfinite(float(pthi)))
        if obs == "dphi":
            if finite_pt:
                pidx = self._match_pt_bin_index(float(ptlo), float(pthi))
                field = "dphi_abs_ptlead_per_R" if is_abs else "dijet_base_ptlead_per_R"
                raw = block[field][ridx][pidx]
            else:
                field = "dphi_abs_all_per_R" if is_abs else "dijet_base_all_per_R"
                raw = block[field][ridx]
        elif obs == "xj":
            if finite_pt:
                pidx = self._match_pt_bin_index(float(ptlo), float(pthi))
                raw = block["xj_ptlead_per_R"][ridx][pidx]
            else:
                raw = block["xj_all_per_R"][ridx]
        elif obs == "aj":
            if finite_pt:
                pidx = self._match_pt_bin_index(float(ptlo), float(pthi))
                raw = block["aj_ptlead_per_R"][ridx][pidx]
            else:
                raw = block["aj_all_per_R"][ridx]
        elif obs == "mjj":
            raw = block["mjj_all_per_R"][ridx]
        elif obs in ("sel", "jetpt"):
            raw = block["dijet_base_all_per_R"][ridx]
        else:
            raise RuntimeError(f"Unsupported observable for selected dijet counts: {observable}")
        val = int(raw)
        if val < 0:
            raise RuntimeError(
                f"Resolved negative selected dijet count for observable={observable}, R={Ruse}, pt=[{ptlo},{pthi}], nosubfrac={is_nosubfrac}, abs={is_abs}: {val}"
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


def _legend_count_label(base_label: str, observable: str, count: int, *, is_abs: bool = False) -> str:
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
    return f"{base_label} ({key}={int(count)})"


class SliceNormBandBuilder:
    """Build exact bin-by-bin xsec normalization bands from published per-slice merged ROOTs."""

    def __init__(self, final_dir: str, *, label: str = "run"):
        self.final_dir = final_dir
        self.label = label
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
                f"{self.label}: {self.summary_path} has invalid xsec_total_rel_err={self.global_rel_err!r}"
            )

        slices = payload.get("slices", [])
        if not isinstance(slices, list) or len(slices) == 0:
            raise RuntimeError(f"{self.label}: {self.summary_path} has no usable slice entries")

        loaded: List[Dict[str, object]] = []
        for idx, entry in enumerate(slices, start=1):
            rel = float(entry.get("xsec_rel_err", float("nan")))
            if not np.isfinite(rel) or rel <= 0:
                raise RuntimeError(
                    f"{self.label}: {self.summary_path} slice #{idx} has invalid xsec_rel_err={rel!r}"
                )

            root_rel = str(entry.get("rootfile", "") or "").strip()
            if root_rel == "":
                raise RuntimeError(
                    f"{self.label}: {self.summary_path} slice #{idx} is missing required rootfile"
                )

            root_path = root_rel if os.path.isabs(root_rel) else os.path.join(self.final_dir, root_rel)
            if not os.path.isfile(root_path):
                raise RuntimeError(
                    f"{self.label}: {self.summary_path} slice #{idx} rootfile does not exist: {root_path}"
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
                hn = _canonical_hist_key(leaf, in_ns_dir=in_ns_dir)
                try:
                    edges = obj.axes[0].edges()
                    centers = 0.5 * (edges[:-1] + edges[1:])
                    widths = (edges[1:] - edges[:-1]).astype(float)
                    vals = np.asarray(obj.values(flow=False), dtype=float)
                except Exception as e:
                    raise RuntimeError(
                        f"{self.label}: failed reading histogram '{hn}' from {root_path}: {e}"
                    ) from e

                term2 = (rel * vals) ** 2
                rec = accum.get(hn)
                if rec is None:
                    accum[hn] = {
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
                            f"{self.label}: binning mismatch for histogram '{hn}' across per-slice ROOTs (offending file: {root_path})"
                        )
                    rec["sqsum"] = np.asarray(rec["sqsum"], dtype=float) + term2
                    rec["seen_count"] = int(rec["seen_count"]) + 1
                th1_count += 1
            _log(f"[DEBUG] {self.label}: xsec band builder indexed {th1_count} TH1 histograms from {root_path}")
        self._norm_map = accum

    def norm_err_for_hist(self, hn: str, centers: np.ndarray, widths: np.ndarray) -> np.ndarray:
        key = _canonical_hist_key(hn, in_ns_dir=False)
        rec = self._norm_map.get(key)
        if rec is None:
            raise RuntimeError(
                f"{self.label}: per-slice xsec band helper is missing histogram '{key}' required by the final merged ROOT"
            )
        if int(rec.get("seen_count", 0)) != len(self.slices):
            raise RuntimeError(
                f"{self.label}: per-slice xsec band helper saw histogram '{key}' in {int(rec.get('seen_count', 0))}/{len(self.slices)} slice ROOTs"
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
                f"{self.label}: final/per-slice binning mismatch for histogram '{key}' while constructing xsec normalization band"
            )
        return np.sqrt(np.asarray(rec["sqsum"], dtype=float))


def xsec_norm_term_for_hist(band, hn: str, centers: np.ndarray, widths: np.ndarray):
    if not INCLUDE_XSEC_NORM_ERR or band is None:
        return float("nan")
    return band.norm_err_for_hist(hn, centers, widths)


def yerr_for_plot_absolute(y: np.ndarray, ye_stat: np.ndarray, xsec_norm_term) -> np.ndarray:
    """Return error bars for *display* on absolute spectra.

    - Statistical bin errors come from stored ROOT variances (Sumw2).
    - σGen (cross-section) uncertainty is a correlated scale uncertainty across all bins.
      For plotting, we may optionally show stat ⊕ σ_norm(bin).
      For inference, do NOT treat σGen as uncorrelated per-bin noise.
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

def read_ini(path: str) -> Dict[str, str]:
    """Read jetscape.ini into a dict[str,str] using the shared parser (xscape_ini.py)."""
    ini = _read_ini_obj(path)
    return dict(ini.kv)

def expand_vars(s: str, cfg: Dict[str, str]) -> str:
    """Expand $VAR and ${VAR} using ini keys first, then environment vars (shared impl)."""
    return _ini_expand_vars(s, cfg)  # xscape_ini.expand_vars(p, ini) positional

def parse_list(s: str) -> List[float]:
    """Parse '(a b c)' or 'a,b,c' into floats (shared impl)."""
    return list(_ini_parse_list(str(s)))

def parse_bool(s, default: bool=False) -> bool:
    """Parse ini-style booleans with a safe default.

    Accepts None/empty values (treat as missing -> return default).
    """
    if s is None:
        return bool(default)
    ss = str(s).strip()
    if ss == "":
        return bool(default)
    return bool(_ini_parse_bool(ss, default=default))


def apply_plot_style(cfg: Dict[str, str]) -> Dict[str, float]:
    """Apply a Mass.C-inspired paper-ready matplotlib style and return resolved sizes."""
    import matplotlib as mpl

    def _f(keys, default: float) -> float:
        if isinstance(keys, str):
            keys = [keys]
        raw = None
        for key in keys:
            if key in cfg and str(cfg.get(key, '')).strip() != '':
                raw = cfg.get(key)
                break
        if raw is None:
            return float(default)
        try:
            val = float(raw)
        except Exception:
            _log(f"[WARN] Invalid paper-ready font knob {keys[0]}={raw!r}; using default {float(default):g}")
            return float(default)
        if not np.isfinite(val) or val <= 0.0:
            _log(f"[WARN] Non-positive/non-finite paper-ready font knob {keys[0]}={raw!r}; using default {float(default):g}")
            return float(default)
        return float(val)

    family = str(cfg.get('PAPERREADY_FONT_FAMILY', cfg.get('PLOT_FONT_FAMILY', 'sans-serif'))).strip() or 'sans-serif'
    sizes = {
        'base': _f(['PAPERREADY_BASE_FONTSIZE', 'PLOT_BASE_FONTSIZE'], 16),
        'title': _f(['PAPERREADY_TITLE_FONTSIZE', 'PLOT_TITLE_FONTSIZE'], 18),
        'suptitle': _f(['PAPERREADY_SUPTITLE_FONTSIZE', 'PLOT_SUPTITLE_FONTSIZE'], 18),
        'label': _f(['PAPERREADY_LABEL_FONTSIZE', 'PLOT_LABEL_FONTSIZE'], 16),
        'tick': _f(['PAPERREADY_TICK_FONTSIZE', 'PLOT_TICK_FONTSIZE'], 14),
        'legend': _f(['PAPERREADY_LEGEND_FONTSIZE', 'PLOT_LEGEND_FONTSIZE'], 14),
        'note': _f(['PAPERREADY_NOTE_FONTSIZE', 'PLOT_NOTE_FONTSIZE'], 12),
        'caption': _f('PAPERREADY_CAPTION_FONTSIZE', 12),
    }
    mpl.rcParams.update({
        'font.family': family,
        'font.size': sizes['base'],
        'axes.titlesize': sizes['title'],
        'axes.labelsize': sizes['label'],
        'axes.linewidth': 1.2,
        'axes.grid': False,
        'xtick.labelsize': sizes['tick'],
        'ytick.labelsize': sizes['tick'],
        'xtick.direction': 'in',
        'ytick.direction': 'in',
        'xtick.top': True,
        'ytick.right': True,
        'xtick.major.width': 1.1,
        'ytick.major.width': 1.1,
        'xtick.minor.width': 0.9,
        'ytick.minor.width': 0.9,
        'legend.fontsize': sizes['legend'],
        'legend.frameon': False,
        'figure.titlesize': sizes['suptitle'],
        'savefig.facecolor': 'white',
        'figure.facecolor': 'white',
        'axes.facecolor': 'white',
        'mathtext.default': 'regular',
    })
    _log(
        '[INFO] Paper-ready plot style resolved: ' +
        f"family={family!r}, base={sizes['base']}, title={sizes['title']}, label={sizes['label']}, " +
        f"tick={sizes['tick']}, legend={sizes['legend']}, note={sizes['note']}, caption={sizes['caption']}"
    )
    _log('[INFO] Paper-ready Mass.C style anchors: 800x800-like square canvas, left/right/top/bottom margins ≈ 0.15/0.05/0.05/0.17, legend border off, blue/red comparison palette, ROOT-like inward ticks.')
    return sizes


# ------------------------------- ROOT IO -----------------------------------
# R-tag decoding: support canonical R*100 (R020 -> 0.20) AND legacy R*1000 (R200 -> 0.20).
# We choose the interpretation that best matches known jet radii from jetscape.ini when available.
KNOWN_R_VALUES: List[float] = []
_WARNED_LEGACY_RTAG = False

def _set_known_r_values(vals: List[float]) -> None:
    # Set global list of expected jet radii (for robust decoding).
    global KNOWN_R_VALUES
    clean: List[float] = []
    for v in vals or []:
        try:
            fv = float(v)
        except Exception:
            continue
        if np.isfinite(fv) and fv > 0:
            clean.append(round(fv, 3))
    KNOWN_R_VALUES = sorted(set(clean))


def _unique_preserve_order_floats(values: Iterable[float], *, atol: float = 1e-9) -> List[float]:
    out: List[float] = []
    for raw in values:
        try:
            v = float(raw)
        except Exception:
            continue
        if not np.isfinite(v) or v <= 0.0:
            continue
        if any(abs(v - prev) <= atol for prev in out):
            continue
        out.append(v)
    return out


def _r_tag_code(R: float) -> str:
    return f"R{int(round(float(R) * 100.0)):03d}"


def _jetr_pair_slug(r_num: float, r_den: float) -> str:
    return f"{_r_tag_code(r_num)}_over_{_r_tag_code(r_den)}"


def _jetr_pair_label(r_num: float, r_den: float) -> str:
    return f"R{float(r_num):.2f}/R{float(r_den):.2f}"


def _add_jetr_uncertainty_note(ax) -> None:
    return


def _add_autozoom_note(ax) -> None:
    return


def _format_xlim_for_log(xmin: float, xmax: float) -> str:
    return f"[{float(xmin):.3f}, {float(xmax):.3f}] GeV"


def decode_r_from_tag(tag_digits: str) -> float:
    # Decode an R-tag integer string from hist names into a jet radius float.
    # Supports:
    #   - canonical: tag = round(R*100)   -> R = tag/100
    #   - legacy:    tag = round(R*1000)  -> R = tag/1000
    global _WARNED_LEGACY_RTAG
    n = int(tag_digits)

    cand100  = n / 100.0
    cand1000 = n / 1000.0

    def _closest_diff(x: float) -> float:
        if not KNOWN_R_VALUES:
            return float("inf")
        return min(abs(x - r) for r in KNOWN_R_VALUES)

    # Prefer whichever candidate matches known radii best (within a small tolerance)
    tol = 0.015
    d100  = _closest_diff(cand100)
    d1000 = _closest_diff(cand1000)

    chosen: Optional[float] = None
    if KNOWN_R_VALUES:
        if d100 <= tol and d1000 > tol:
            chosen = cand100
        elif d1000 <= tol and d100 > tol:
            chosen = cand1000
        elif d100 <= tol and d1000 <= tol:
            chosen = cand100 if d100 <= d1000 else cand1000

    if chosen is None:
        # Plausibility heuristic (jets typically use R in ~[0.1, 1.0]).
        p100  = (0.05 <= cand100  <= 1.2)
        p1000 = (0.05 <= cand1000 <= 1.2)
        if p100 and not p1000:
            chosen = cand100
        elif p1000 and not p100:
            chosen = cand1000
        elif p100 and p1000:
            # Prefer the value in [0.1,0.8] if exactly one is in that range.
            in100  = (0.1 <= cand100  <= 0.8)
            in1000 = (0.1 <= cand1000 <= 0.8)
            if in100 and not in1000:
                chosen = cand100
            elif in1000 and not in100:
                chosen = cand1000
            else:
                # Fall back to canonical /100 unless it is clearly unphysical (>1.2).
                chosen = cand100 if cand100 <= 1.2 else cand1000
        else:
            # If both look unphysical, keep canonical as a last resort.
            chosen = cand100

    if chosen == cand1000 and not _WARNED_LEGACY_RTAG:
        _log("[WARN] Detected legacy histogram R-tag scaling (R*1000). "
             "Decoding tags like 'R200' as R=0.20 when appropriate.")
        _WARNED_LEGACY_RTAG = True

    return round(float(chosen), 3)

_re_mjj_all = re.compile(r"^mjj_R(?P<R>\d{2,4})_(?:(?P<lo>\d+)_(?P<hi>\d+)_fullrange|all)$")
_re_mjj_pt  = re.compile(r"^mjj_R(?P<R>\d{2,4})_(?P<lo>\d+)_(?P<hi>\d+)$")


def parse_mjj_name(hn: str) -> Optional[Tuple[float, Optional[float], Optional[float], bool]]:
    """Parse Mjj histogram names.

    Returns (R, ptlo, pthi, isAll) or None if not an mjj histogram name.

    Accepts optional '_nosubfrac' suffix (and/or storage under ROOT subdir nosubfrac/).
    """
    base, _is_ns = _strip_nosubfrac_suffix(hn)
    m = _re_mjj_all.match(base)
    if m:
        lo = m.groupdict().get("lo")
        hi = m.groupdict().get("hi")
        return (
            decode_r_from_tag(m.group("R")),
            (float(lo) if lo is not None else float('nan')),
            (float(hi) if hi is not None else float('nan')),
            True,
        )
    m = _re_mjj_pt.match(base)
    if m:
        return (decode_r_from_tag(m.group("R")), float(m.group("lo")), float(m.group("hi")), False)
    return None

def parse_jetpt_name(hn: str) -> Optional[Tuple[str, float, bool]]:
    """Parse jet pT spectrum histogram names.

    Supports analyzer full-range dijet jet spectra like:
      - jetpt_lead_R040_20_4000_fullrange
      - jetpt_sublead_R040_20_4000_fullrange
    plus legacy/new inclusive spectra:
      - jetpt_incl_R040_all

    No-SUBFRAC variants add a suffix and may live under a ROOT subdir.

    Returns:
      (kind, R, is_nosubfrac) where kind in {"lead","sublead","incl"} and R is float (e.g. 0.40),
      or None if not a recognized jet spectrum hist.
    """
    base, is_ns = _strip_nosubfrac_suffix(hn)
    m = re.match(r"^jetpt_(lead|sublead)_R(\d{2,4})_(?:(\d+)_(\d+)_fullrange|all)$", base)
    if m:
        return m.group(1), decode_r_from_tag(m.group(2)), is_ns
    m = re.match(r"^jetpt_(incl)_R(\d{2,4})_all$", base)
    if m:
        return m.group(1), decode_r_from_tag(m.group(2)), is_ns
    return None

_re_dphi = re.compile(r"^dphi(?:_R(?P<R>\d{2,4}))?_(?:(?P<lo>\d+)_(?P<hi>\d+)(?P<full>_fullrange)?|all)$")
_re_dphi_abs = re.compile(r"^dphi_abs(?:_R(?P<R>\d{2,4}))?_(?:(?P<lo>\d+)_(?P<hi>\d+)(?P<full>_fullrange)?|all)$")
_re_xj   = re.compile(r"^xj_R(?P<R>\d{2,4})_(?:(?P<lo>\d+)_(?P<hi>\d+)(?P<full>_fullrange)?|all)$")
_re_aj   = re.compile(r"^aj_R(?P<R>\d{2,4})_(?:(?P<lo>\d+)_(?P<hi>\d+)(?P<full>_fullrange)?|all)$")
_re_particle = re.compile(r"^particle_(?P<kind>pt|eta|phi)_all$")
_re_sublead_vs_lead_h2 = re.compile(r"^h2_sublead_vs_lead_R(?P<R>\d{2,4})_(?:(?P<lo>\d+)_(?P<hi>\d+)_fullrange|all)$")
_re_sublead_vs_lead_prof = re.compile(r"^prof_sublead_vs_lead_R(?P<R>\d{2,4})_(?:(?P<lo>\d+)_(?P<hi>\d+)_fullrange_)?ptleadbins$")
_re_dphi_abs_vs_deta_h2 = re.compile(r"^h2_dphi_abs_vs_deta_R(?P<R>\d{2,4})_(?:(?P<lo>\d+)_(?P<hi>\d+)(?P<full>_fullrange)?|all)$")

def parse_dphi_name(hn: str):
    """Return (R, lo, hi, isAll) where lo/hi are NaN for full-range names. Accepts optional '_nosubfrac' suffix."""
    base, _is_ns = _strip_nosubfrac_suffix(hn)
    m = _re_dphi.match(base)
    if not m:
        return None
    R = m.group('R')
    lo = m.group('lo')
    hi = m.group('hi')
    is_all = (m.groupdict().get('full') is not None) or (lo is None or hi is None)
    Rv = decode_r_from_tag(R) if R is not None else float('nan')
    if lo is None or hi is None:
        return (Rv, float('nan'), float('nan'), True)
    return (Rv, float(lo), float(hi), bool(is_all))



def parse_dphi_abs_name(hn: str):
    """Return (R, lo, hi, isAll) for Δφ_abs (0..π) hist names. Accepts optional '_nosubfrac' suffix."""
    base, _is_ns = _strip_nosubfrac_suffix(hn)
    m = _re_dphi_abs.match(base)
    if not m:
        return None
    R = m.group('R')
    lo = m.group('lo')
    hi = m.group('hi')
    is_all = (m.groupdict().get('full') is not None) or (lo is None or hi is None)
    Rv = decode_r_from_tag(R) if R is not None else float('nan')
    if lo is None or hi is None:
        return (Rv, float('nan'), float('nan'), True)
    return (Rv, float(lo), float(hi), bool(is_all))

def parse_xj_name(hn: str):
    base, _is_ns = _strip_nosubfrac_suffix(hn)
    m = _re_xj.match(base)
    if not m:
        return None
    lo = m.group('lo')
    hi = m.group('hi')
    is_all = (m.groupdict().get('full') is not None) or (lo is None or hi is None)
    Rv = decode_r_from_tag(m.group('R'))
    if lo is None or hi is None:
        return (Rv, float('nan'), float('nan'), True)
    return (Rv, float(lo), float(hi), bool(is_all))

def parse_aj_name(hn: str):
    base, _is_ns = _strip_nosubfrac_suffix(hn)
    m = _re_aj.match(base)
    if not m:
        return None
    lo = m.group('lo')
    hi = m.group('hi')
    is_all = (m.groupdict().get('full') is not None) or (lo is None or hi is None)
    Rv = decode_r_from_tag(m.group('R'))
    if lo is None or hi is None:
        return (Rv, float('nan'), float('nan'), True)
    return (Rv, float(lo), float(hi), bool(is_all))


def parse_particle_name(hn: str) -> Optional[str]:
    base, is_ns = _strip_nosubfrac_suffix(hn)
    if is_ns:
        return None
    m = _re_particle.match(base)
    if not m:
        return None
    return str(m.group('kind'))


def parse_sublead_vs_lead_h2_name(hn: str) -> Optional[Tuple[float, bool]]:
    base, is_ns = _strip_nosubfrac_suffix(hn)
    m = _re_sublead_vs_lead_h2.match(base)
    if not m:
        return None
    return decode_r_from_tag(m.group('R')), bool(is_ns)


def parse_sublead_vs_lead_profile_name(hn: str) -> Optional[Tuple[float, bool]]:
    base, is_ns = _strip_nosubfrac_suffix(hn)
    m = _re_sublead_vs_lead_prof.match(base)
    if not m:
        return None
    return decode_r_from_tag(m.group('R')), bool(is_ns)


def parse_dphi_abs_vs_deta_h2_name(hn: str):
    """Return (R, lo, hi, isAll, is_nosubfrac) for |Δφ| vs |Δη| TH2 hist names."""
    base, is_ns = _strip_nosubfrac_suffix(hn)
    m = _re_dphi_abs_vs_deta_h2.match(base)
    if not m:
        return None
    lo = m.group('lo')
    hi = m.group('hi')
    is_all = (m.groupdict().get('full') is not None) or (lo is None or hi is None)
    Rv = decode_r_from_tag(m.group('R'))
    if lo is None or hi is None:
        return (Rv, float('nan'), float('nan'), True, bool(is_ns))
    return (Rv, float(lo), float(hi), bool(is_all), bool(is_ns))


def _pretty_label(s: str) -> str:
    """
    Purely cosmetic: fix common typos in plot labels without changing folder/run tags.
    """
    if s is None:
        return ""
    # preserve case-ish but fix the classic typo
    return re.sub(r"vaccum", "vacuum", str(s), flags=re.IGNORECASE)


def _is_medium_like(tag: str) -> bool:
    """Detect the active medium side for ratio ordering.

    Accepts current realistic pp medium run tags/labels and legacy brick scan tags.
    The legacy _is_brick() wrapper below is kept so older internal call sites remain stable.
    """
    t = str(tag).lower()
    if "brick" in t or "medium" in t or "qgp" in t or "quench" in t:
        return True
    return t.startswith("med") or ("_med" in t) or ("-med" in t)


def _is_brick(tag: str) -> bool:
    return _is_medium_like(tag)


def _is_vacuum(tag: str) -> bool:
    t = str(tag).lower()
    if "vacuum" in t or "vaccum" in t:
        return True
    # common run tags: vac_*, vacuum_*, vaccum_*
    return t.startswith("vac") or ("_vac" in t) or ("-vac" in t)


def _asym_yerr_for_log(y: np.ndarray, ey: np.ndarray) -> np.ndarray:
    """
    Matplotlib log-scale can't draw errorbars that cross y<=0.
    Convert symmetric +/- ey into an asymmetric (low, high) pair
    with the lower capped so (y - low) stays positive.
    """
    y = np.asarray(y, dtype=float)
    ey = np.asarray(ey, dtype=float)
    low = np.minimum(ey, 0.999 * y)
    low = np.where(np.isfinite(low) & (low >= 0), low, 0.0)
    high = np.where(np.isfinite(ey) & (ey >= 0), ey, 0.0)
    return np.vstack([low, high])


def errorbar_nan_safe(ax, x, y, yerr, *, fmt='o', ms=None, lw=None, capsize=2, label=None, color=None, noerr_alpha=0.55):
    """Plot error bars but keep finite points whose propagated yerr is NaN/invalid.

    This mirrors the fitter-side helper: bins with finite y but undefined propagated
    uncertainties are drawn as points only, rather than being dropped or shown with
    fake zero error bars.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if yerr is None:
        ax.plot(x, y, fmt, ms=ms, lw=lw if lw is not None else 0, label=label)
        return
    yerr = np.asarray(yerr, dtype=float)

    m_base = np.isfinite(x) & np.isfinite(y)
    m_err = m_base & np.isfinite(yerr) & (yerr >= 0)
    m_no = m_base & (~np.isfinite(yerr))

    used_label = False
    if np.any(m_err):
        ax.errorbar(x[m_err], y[m_err], yerr=yerr[m_err], fmt=fmt, ms=ms, lw=lw, capsize=capsize, label=label, color=color)
        used_label = True
    if np.any(m_no):
        ax.plot(x[m_no], y[m_no], fmt, ms=ms, lw=0, alpha=noerr_alpha, color=color, label=(None if used_label else label))
        try:
            ax.text(0.02, 0.96, f"{int(np.sum(m_no))} bins w/o err", transform=ax.transAxes, fontsize=_FONTS['note'], va='top', alpha=0.7)
        except Exception:
            pass


def errorbar_nan_safe_log(ax, x, y, yerr, *, fmt='o', ms=None, lw=None, capsize=2, label=None, color=None, noerr_alpha=0.55):
    """Log-y variant of errorbar_nan_safe().

    Finite-error bins use asymmetric lower errors clipped to stay positive on log axes;
    finite points with undefined propagated errors are still shown as point-only markers.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if yerr is None:
        ax.plot(x, y, fmt, ms=ms, lw=lw if lw is not None else 0, label=label)
        return
    yerr = np.asarray(yerr, dtype=float)

    m_base = np.isfinite(x) & np.isfinite(y) & (y > 0)
    m_err = m_base & np.isfinite(yerr) & (yerr >= 0)
    m_no = m_base & (~np.isfinite(yerr))

    used_label = False
    if np.any(m_err):
        ax.errorbar(
            x[m_err],
            y[m_err],
            yerr=_asym_yerr_for_log(y[m_err], yerr[m_err]),
            fmt=fmt,
            ms=ms,
            lw=lw,
            capsize=capsize,
            label=label,
            color=color,
        )
        used_label = True
    if np.any(m_no):
        ax.plot(x[m_no], y[m_no], fmt, ms=ms, lw=0, alpha=noerr_alpha, color=color, label=(None if used_label else label))
        try:
            ax.text(0.02, 0.96, f"{int(np.sum(m_no))} bins w/o err", transform=ax.transAxes, fontsize=_FONTS['note'], va='top', alpha=0.7)
        except Exception:
            pass


def _ratio_with_optional_errors(
    num_y: np.ndarray,
    num_e: Optional[np.ndarray],
    den_y: np.ndarray,
    den_e: Optional[np.ndarray],
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return ratio arrays while preserving finite central values whose propagated yerr is unavailable."""
    num_y = np.asarray(num_y, dtype=float)
    den_y = np.asarray(den_y, dtype=float)
    if num_y.shape != den_y.shape:
        raise ValueError(f"ratio shape mismatch: numerator {num_y.shape} vs denominator {den_y.shape}")

    ratio = np.full_like(num_y, np.nan, dtype=float)
    ratio_err = np.full_like(num_y, np.nan, dtype=float)
    m_plot = np.isfinite(num_y) & np.isfinite(den_y) & (num_y > 0) & (den_y > 0)
    if not np.any(m_plot):
        return ratio, ratio_err, m_plot, np.zeros_like(m_plot, dtype=bool)

    ratio[m_plot] = num_y[m_plot] / den_y[m_plot]

    if num_e is None or den_e is None:
        return ratio, ratio_err, m_plot, np.zeros_like(m_plot, dtype=bool)

    num_e = np.asarray(num_e, dtype=float)
    den_e = np.asarray(den_e, dtype=float)
    if num_e.shape != num_y.shape or den_e.shape != den_y.shape:
        raise ValueError(
            f"ratio error shape mismatch: num_e {num_e.shape}, num_y {num_y.shape}, den_e {den_e.shape}, den_y {den_y.shape}"
        )

    m_err = m_plot & np.isfinite(num_e) & np.isfinite(den_e) & (num_e >= 0) & (den_e >= 0)
    if np.any(m_err):
        rel_num = num_e[m_err] / num_y[m_err]
        rel_den = den_e[m_err] / den_y[m_err]
        ratio_err[m_err] = ratio[m_err] * np.sqrt(rel_num**2 + rel_den**2)
    return ratio, ratio_err, m_plot, m_err


def _resolve_ratio_order(
    ratio_mode: str,
    labelA: str,
    labelB: str,
    *,
    run_tag_a: Optional[str] = None,
    run_tag_b: Optional[str] = None,
) -> Tuple[str, str, str]:
    """Return (numerator_key, denominator_key, legend_label) for med/inv compare ratios."""
    probeA = str(run_tag_a or labelA or "")
    probeB = str(run_tag_b or labelB or "")
    A_is_brick = _is_brick(probeA)
    B_is_brick = _is_brick(probeB)
    A_is_vac = _is_vacuum(probeA)
    B_is_vac = _is_vacuum(probeB)

    if (ratio_mode or 'med').strip().lower() == 'inv':
        if A_is_vac and B_is_brick:
            return 'A', 'B', f"{labelA}/{labelB}"
        if B_is_vac and A_is_brick:
            return 'B', 'A', f"{labelB}/{labelA}"
        return 'A', 'B', f"{labelA}/{labelB}"

    if A_is_brick and B_is_vac:
        return 'A', 'B', f"{labelA}/{labelB}"
    if B_is_brick and A_is_vac:
        return 'B', 'A', f"{labelB}/{labelA}"
    return 'B', 'A', f"{labelB}/{labelA}"


def _rebin_hist_density_for_ratio(
    xc: np.ndarray,
    y: np.ndarray,
    e: Optional[np.ndarray],
    bw: np.ndarray,
    factor: int,
    *,
    hist_name: str = "",
    observable_label: str = "hist",
) -> Tuple[np.ndarray, np.ndarray, Optional[np.ndarray], np.ndarray, bool]:
    """Rebin a density histogram by an integer factor for compare-side ratio panels only.

    The content is treated as a density (per unit x), so merged groups preserve the
    integrated weight: y_new = sum(y_i * bw_i) / sum(bw_i). This matches the usual
    ROOT-style Rebin(N) + Scale(1/N) behavior for uniform-width bins while also working
    for variable widths. Uncertainties are propagated from the integrated quantities
    assuming no inter-bin covariance downstream.
    """
    xc = np.asarray(xc, dtype=float)
    y = np.asarray(y, dtype=float)
    bw = np.asarray(bw, dtype=float)
    e_arr = None if e is None else np.asarray(e, dtype=float)

    try:
        factor_i = int(factor)
    except Exception:
        factor_i = 1
    if factor_i <= 1:
        return xc, y, e_arr, bw, False

    n = int(xc.size)
    if y.size != n or bw.size != n or (e_arr is not None and e_arr.size != n):
        _log(f"[WARN] {observable_label} ratio rebin skipped for {hist_name or '<unnamed>'}: array-size mismatch")
        return xc, y, e_arr, bw, False
    if n == 0:
        return xc, y, e_arr, bw, False
    if n % factor_i != 0:
        _log(f"[WARN] {observable_label} ratio rebin skipped for {hist_name or '<unnamed>'}: nbins={n} not divisible by factor={factor_i}")
        return xc, y, e_arr, bw, False

    xlo = xc - 0.5 * bw
    xhi = xc + 0.5 * bw
    xc_new = []
    y_new = []
    e_new = [] if e_arr is not None else None
    bw_new = []

    for start in range(0, n, factor_i):
        stop = start + factor_i
        sl = slice(start, stop)

        w = bw[sl]
        yy = y[sl]
        valid_y = np.isfinite(w) & (w > 0) & np.isfinite(yy)
        width = float(np.nansum(w[valid_y]))
        if not (np.isfinite(width) and width > 0):
            xc_new.append(float('nan'))
            y_new.append(float('nan'))
            bw_new.append(float('nan'))
            if e_new is not None:
                e_new.append(float('nan'))
            continue

        left = float(xlo[start]) if np.isfinite(xlo[start]) else float(np.nanmin(xlo[sl]))
        right = float(xhi[stop - 1]) if np.isfinite(xhi[stop - 1]) else float(np.nanmax(xhi[sl]))
        if not (np.isfinite(left) and np.isfinite(right) and right > left):
            left = float(np.nanmin(xlo[sl]))
            right = float(np.nanmax(xhi[sl]))
        xc_new.append(0.5 * (left + right))
        bw_new.append(right - left if (np.isfinite(right) and np.isfinite(left) and right > left) else width)
        y_new.append(float(np.nansum(yy[valid_y] * w[valid_y]) / width))

        if e_new is not None:
            ee = e_arr[sl]
            valid_e = np.isfinite(w) & (w > 0) & np.isfinite(ee) & (ee >= 0)
            if np.any(valid_e):
                e_new.append(float(np.sqrt(np.nansum((ee[valid_e] * w[valid_e]) ** 2)) / width))
            else:
                e_new.append(float('nan'))

    return (
        np.asarray(xc_new, dtype=float),
        np.asarray(y_new, dtype=float),
        (None if e_new is None else np.asarray(e_new, dtype=float)),
        np.asarray(bw_new, dtype=float),
        True,
    )


def _dphi_ratio_rebin_factor_for_hist(hn: str) -> int:
    return int(DPHI_ABS_RATIO_REBIN_FACTOR if str(hn).startswith('dphi_abs_') else DPHI_RATIO_REBIN_FACTOR)


def _ratio_rebin_note(hn: str) -> str:
    fac = _dphi_ratio_rebin_factor_for_hist(hn)
    if fac <= 1:
        return ''
    obs = '|Δφ|' if str(hn).startswith('dphi_abs_') else 'Δφ'
    return f"ratio inputs rebinned ×{fac} ({obs}, density preserved)"


def _log_ylim_from_positive(arrays: List[np.ndarray], pad_factor: float = 1.6) -> Tuple[float, float]:
    """
    Pick (ymin, ymax) for log-scale axes from the union of positive values.
    """
    vals = []
    for a in arrays:
        if a is None:
            continue
        a = np.asarray(a, dtype=float)
        m = np.isfinite(a) & (a > 0)
        if np.any(m):
            vals.append(a[m])
    if not vals:
        return (1e-30, 1.0)
    v = np.concatenate(vals)
    ymin = float(np.nanmin(v))
    ymax = float(np.nanmax(v))
    if not (np.isfinite(ymin) and np.isfinite(ymax)) or ymax <= 0:
        return (1e-30, 1.0)
    ymin = max(ymin / pad_factor, 1e-30)
    ymax = max(ymax * pad_factor, ymin * 10.0)
    return (ymin, ymax)


def find_best_root_for_run(run_dir: str, preferred: str) -> Optional[str]:
    """STRICT (fitter-consistent): use the canonical ROOT only.

    The comparisor must not silently scan for "some" ROOT file, because it can
    accidentally pick stale artifacts from other runs/directories.

    Returns preferred if it exists; otherwise None.
    """
    _ = run_dir  # kept for API compatibility / log messaging
    if preferred and os.path.isfile(preferred):
        return preferred
    return None


def read_mjj_hists(root_path: str) -> Dict[str, Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]]:
    """Return dict: name -> (centers, values, errors, widths, entries) for Mjj TH1 histograms."""
    out: Dict[str, Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]] = {}
    for item in read_root_histograms(root_path):
        hn_leaf, centers, vals, errs, widths, _variances, entries, in_ns_dir = item
        hn = _canonical_hist_key(hn_leaf, in_ns_dir=in_ns_dir)
        if parse_mjj_name(hn) is None:
            continue
        out[hn] = (centers, vals, errs, widths, entries)
    _log_family_discovery_summary('mjj', root_path, out)
    return out


def read_jetpt_hists(root_path: str) -> Dict[str, Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]]:
    """Return dict: name -> (centers, values, errors, widths, entries) for jet pT TH1 histograms."""
    out: Dict[str, Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]] = {}
    for item in read_root_histograms(root_path):
        hn_leaf, centers, vals, errs, widths, _variances, entries, in_ns_dir = item
        hn = _canonical_hist_key(hn_leaf, in_ns_dir=in_ns_dir)
        if parse_jetpt_name(hn) is None:
            continue
        out[hn] = (centers, vals, errs, widths, entries)
    _log_family_discovery_summary('jetpt', root_path, out)
    return out


def read_dphi_hists(root_path: str):
    """Return dict: name -> (centers, values, errors, widths, entries) for Δφ TH1 histograms."""
    out = {}
    for item in read_root_histograms(root_path):
        hn_leaf, centers, vals, errs, widths, _variances, entries, in_ns_dir = item
        hn = _canonical_hist_key(hn_leaf, in_ns_dir=in_ns_dir)
        if parse_dphi_name(hn) is None:
            continue
        out[hn] = (centers, vals, errs, widths, entries)
    _log_family_discovery_summary('dphi', root_path, out)
    return out


def read_dphi_abs_hists(root_path: str):
    """Return dict: name -> (centers, values, errors, widths, entries) for Δφ_abs (0..π) TH1 histograms."""
    out = {}
    for item in read_root_histograms(root_path):
        hn_leaf, centers, vals, errs, widths, _variances, entries, in_ns_dir = item
        hn = _canonical_hist_key(hn_leaf, in_ns_dir=in_ns_dir)
        if parse_dphi_abs_name(hn) is None:
            continue
        out[hn] = (centers, vals, errs, widths, entries)
    _log_family_discovery_summary('dphi_abs', root_path, out)
    return out


def read_imbalance_hists(root_path: str):
    """Return dict for xJ/AJ histos: name -> (centers, values, errors, widths, entries)."""
    out = {}
    for item in read_root_histograms(root_path):
        hn_leaf, centers, vals, errs, widths, _variances, entries, in_ns_dir = item
        hn = _canonical_hist_key(hn_leaf, in_ns_dir=in_ns_dir)
        if parse_xj_name(hn) is None and parse_aj_name(hn) is None:
            continue
        out[hn] = (centers, vals, errs, widths, entries)
    _log_family_discovery_summary('imbalance', root_path, out)
    return out


def _count_hist_base_name(hn: str) -> Optional[str]:
    """Translate analyzer count_* TH1 names back to the weighted-histogram key they mirror."""
    if not isinstance(hn, str) or not hn.startswith("count_"):
        return None
    base = hn[len("count_"):]
    if not base:
        return None
    return base


def read_count_density_hists(root_path: str) -> Dict[str, Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]]:
    """Return analyzer unweighted count-density TH1 histograms keyed by their mirrored weighted-hist name."""
    out: Dict[str, Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]] = {}
    for item in read_root_histograms(root_path):
        hn_leaf, centers, vals, errs, widths, _variances, entries, in_ns_dir = item
        hn = _canonical_hist_key(hn_leaf, in_ns_dir=in_ns_dir)
        base = _count_hist_base_name(hn)
        if base is None:
            continue
        # Only keep count-density mirrors used by dijet_normalized 1D plots.
        if (parse_mjj_name(base) is None
            and parse_dphi_abs_name(base) is None
            and parse_xj_name(base) is None
            and parse_aj_name(base) is None
            and parse_jetpt_name(base) is None):
            continue
        out[base] = (centers, vals, errs, widths, entries)
    _log_family_discovery_summary('count_density', root_path, out)
    return out


def _single_slice_hist_for_norm(count_map: Dict[str, tuple], weighted_map: Dict[str, tuple], hn: str, *, label: str) -> tuple:
    """Prefer analyzer count-density histograms for true (1/N)dN/dX in SINGLE_SLICE_MODE; fall back to weighted histograms for old ROOT files."""
    if SINGLE_SLICE_MODE and isinstance(count_map, dict) and hn in count_map:
        return count_map[hn]
    if SINGLE_SLICE_MODE:
        _log(f"[WARN] SINGLE_SLICE_MODE true dN normalization requested, but count-density histogram is missing for {label}:{hn}; falling back to legacy weighted histogram.")
    return weighted_map[hn]


def read_particle_hists(root_path: str) -> Dict[str, Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]]:
    """Return dict for branch-neutral particle-level TH1 histograms: name -> (centers, values, errors, widths, entries)."""
    out: Dict[str, Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]] = {}
    for item in read_root_histograms(root_path):
        hn_leaf, centers, vals, errs, widths, _variances, entries, in_ns_dir = item
        hn = _canonical_hist_key(hn_leaf, in_ns_dir=in_ns_dir)
        if parse_particle_name(hn) is None:
            continue
        out[hn] = (centers, vals, errs, widths, entries)
    _log_family_discovery_summary('particle', root_path, out)
    return out


def read_sublead_vs_lead_h2_hists(root_path: str) -> Dict[str, Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]]:
    """Return dict for TH2 lead-vs-sublead maps: name -> (xedges, yedges, values, errors, entries)."""
    out: Dict[str, Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]] = {}
    for item in read_root_th2(root_path):
        hn_leaf, xedges, yedges, vals, errs, _variances, entries, in_ns_dir = item
        hn = _canonical_hist_key(hn_leaf, in_ns_dir=in_ns_dir)
        if parse_sublead_vs_lead_h2_name(hn) is None:
            continue
        out[hn] = (xedges, yedges, vals, errs, entries)
    _log_family_discovery_summary('lead_sublead_h2', root_path, out)
    return out


def read_dphi_abs_vs_deta_h2_hists(root_path: str) -> Dict[str, Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]]:
    """Return dict for TH2 |Δφ| vs |Δη| maps: name -> (xedges, yedges, values, errors, entries)."""
    out: Dict[str, Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]] = {}
    for item in read_root_th2(root_path):
        hn_leaf, xedges, yedges, vals, errs, _variances, entries, in_ns_dir = item
        hn = _canonical_hist_key(hn_leaf, in_ns_dir=in_ns_dir)
        if parse_dphi_abs_vs_deta_h2_name(hn) is None:
            continue
        out[hn] = (xedges, yedges, vals, errs, entries)
    _log_family_discovery_summary('dphi_abs_vs_deta_h2', root_path, out)
    return out


def read_sublead_vs_lead_profile_hists(root_path: str) -> Dict[str, Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]]:
    """Return dict for TProfile lead-vs-sublead means: name -> (centers, means, errors, widths, entries)."""
    out: Dict[str, Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]] = {}
    for item in read_root_profiles(root_path):
        hn_leaf, centers, vals, errs, widths, _variances, entries, in_ns_dir = item
        hn = _canonical_hist_key(hn_leaf, in_ns_dir=in_ns_dir)
        if parse_sublead_vs_lead_profile_name(hn) is None:
            continue
        out[hn] = (centers, vals, errs, widths, entries)
    _log_family_discovery_summary('lead_sublead_profile', root_path, out)
    return out


def mjj_stats(xc: np.ndarray, yc: np.ndarray, bw: np.ndarray) -> Tuple[float, float]:
    """
    Mean/std using counts-weighted (density * binwidth) like your fitter.
    """
    s = yc * bw
    S = float(np.nansum(s))
    if S <= 0:
        return (float("nan"), float("nan"))
    mean = float(np.nansum(s * xc) / S)
    var = float(np.nansum(s * (xc - mean) ** 2) / S)
    return (mean, math.sqrt(max(0.0, var)))


# ------------------------------- plotting ----------------------------------



def _angdiff_to_pi(phi: np.ndarray) -> np.ndarray:
    """|Δφ-π| wrapped into [0, π]."""
    return np.abs(np.arctan2(np.sin(phi - np.pi), np.cos(phi - np.pi)))


def _weighted_mean_rms(xc: np.ndarray, y: np.ndarray, bw: np.ndarray) -> tuple:
    s = y * bw
    S = float(np.nansum(s))
    if not (np.isfinite(S) and S > 0):
        return (float('nan'), float('nan'))
    mu = float(np.nansum(s * xc) / S)
    var = float(np.nansum(s * (xc - mu) ** 2) / S)
    return (mu, math.sqrt(max(0.0, var)))


def sort_key(hn: str):
    tag = parse_mjj_name(hn)
    if tag is None:
        return (999, 999999, 999999, hn)
    R, lo, hi, isAll = tag
    # put full-range first within each R
    return (int(round(R * 1000)), 0 if isAll else 1, lo if lo is not None else -1, hi if hi is not None else -1, hn)

def _data_xrange_from_nonzero(
    xc: np.ndarray,
    y: np.ndarray,
    bw: np.ndarray,
) -> Optional[Tuple[float, float]]:
    """
    Return (xmin, xmax) from bins with y>0, using bin edges derived from centers and widths.
    Returns None if no suitable bins.
    """
    try:
        xc = np.asarray(xc, dtype=float)
        y = np.asarray(y, dtype=float)
        bw = np.asarray(bw, dtype=float)
    except Exception:
        return None

    m = np.isfinite(xc) & np.isfinite(y) & np.isfinite(bw) & (bw > 0) & (y > 0)
    if not np.any(m):
        return None

    lo = xc[m] - 0.5 * bw[m]
    hi = xc[m] + 0.5 * bw[m]

    # Log-scale safety: x must be > 0
    m2 = np.isfinite(lo) & np.isfinite(hi) & (hi > 0)
    if not np.any(m2):
        return None

    lo = lo[m2]
    hi = hi[m2]
    lo = lo[lo > 0]
    if lo.size == 0 or hi.size == 0:
        return None

    xmin = float(np.nanmin(lo))
    xmax = float(np.nanmax(hi))
    if not (np.isfinite(xmin) and np.isfinite(xmax)) or xmin <= 0 or xmax <= xmin:
        return None
    return (xmin, xmax)

def _auto_xlim(
    series: List[Tuple[np.ndarray, np.ndarray, np.ndarray]],
    mjj_min_cfg: float,
    mjj_max_cfg: float,
    pad_decades: float = 0.05,
) -> Tuple[float, float]:
    """
    Choose good log-scale x-limits based on the union of non-zero bins across series.
    Applies a small log padding and then *soft clamps* to ini min/max if they don't break the range.
    """
    xmins = []
    xmaxs = []
    for xc, y, bw in series:
        r = _data_xrange_from_nonzero(xc, y, bw)
        if r:
            xmins.append(r[0])
            xmaxs.append(r[1])

    if xmins and xmaxs:
        xmin_d = float(min(xmins))
        xmax_d = float(max(xmaxs))

        # pad in log space: multiply by 10^(±pad)
        pad_lo = 10.0 ** (-pad_decades)
        pad_hi = 10.0 ** (+pad_decades)
        xmin = max(1e-6, xmin_d * pad_lo)
        xmax = xmax_d * pad_hi

        # soft clamp to cfg if it doesn't invert the range
        xmin_c = xmin
        xmax_c = xmax
        if mjj_min_cfg and mjj_min_cfg > 0:
            xmin_c = max(xmin_c, float(mjj_min_cfg))
        if mjj_max_cfg and mjj_max_cfg > 0:
            xmax_c = min(xmax_c, float(mjj_max_cfg))

        if xmax_c > xmin_c:
            xmin, xmax = xmin_c, xmax_c

        # avoid absurdly narrow ranges on log plots
        if xmax / xmin < 3.0:
            mid = math.sqrt(xmin * xmax)
            xmin = max(1e-6, mid / math.sqrt(3.0))
            xmax = mid * math.sqrt(3.0)

        return (xmin, xmax)

    # fallback: original config behavior
    xmin = max(1e-3, mjj_min_cfg if mjj_min_cfg > 0 else 1e-3)
    xmax = max(xmin * 10.0, mjj_max_cfg if mjj_max_cfg > xmin else xmin * 10.0)
    return (xmin, xmax)

def _mjj_backtoback_title_tag(mjj_require_backtoback: int, bb_tol_deg: float) -> str:
    if int(mjj_require_backtoback) == 1:
        return f"; back-to-back: $|\\Delta\\varphi-\\pi|$ ≤ {bb_tol_deg:.0f}°"
    return ""

def overlay_plot(
    hn: str,
    A: Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float],
    B: Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float],
    labelA: str,
    labelB: str,
    out_dir: str,
    mjj_min_cfg: float,
    mjj_max_cfg: float,
    bb_tol_deg: float,
    mjj_require_backtoback: int,
    ystar_title_suffix: str,
    ms: float,
    *,
    ratio_mode: str = 'med',
    run_tag_a: Optional[str] = None,
    run_tag_b: Optional[str] = None,
) -> None:
    xcA, yA, eA, bwA, entA = A
    xcB, yB, eB, bwB, entB = B

    fig, (ax, axr) = plt.subplots(
        2, 1, figsize=(9, 8.4), sharex=True,
        gridspec_kw=dict(height_ratios=[1.0, 0.58], hspace=0.05)
    )
    ax.set_xscale("log")
    ax.set_yscale("log")
    axr.set_xscale("log")

    # data-driven x range (with ini as soft clamp/fallback)
    x_min, x_max = _auto_xlim(
        series=[(xcA, yA, bwA), (xcB, yB, bwB)],
        mjj_min_cfg=mjj_min_cfg,
        mjj_max_cfg=mjj_max_cfg,
        pad_decades=0.06,
    )
    ax.set_xlim(x_min, x_max)

    normA = xsec_norm_term_for_hist(XSEC_BAND_A, hn, xcA, bwA)
    normB = xsec_norm_term_for_hist(XSEC_BAND_B, hn, xcB, bwB)
    eA_plot = yerr_for_plot_absolute(yA, eA, normA)
    eB_plot = yerr_for_plot_absolute(yB, eB, normB)

    # Only plot bins that are actually legal on log axes (y>0, x>0).
    mA = np.isfinite(xcA) & np.isfinite(yA) & np.isfinite(eA_plot) & (xcA > 0) & (yA > 0)
    mB = np.isfinite(xcB) & np.isfinite(yB) & np.isfinite(eB_plot) & (xcB > 0) & (yB > 0)

    ymin, ymax = _log_ylim_from_positive([yA[mA] if np.any(mA) else None, yB[mB] if np.any(mB) else None])
    ax.set_ylim(ymin, ymax)

    if np.any(mA):
        ax.errorbar(
            xcA[mA],
            yA[mA],
            yerr=_asym_yerr_for_log(yA[mA], eA_plot[mA]),
            fmt="o",
            ms=ms,
            lw=0.8,
            color=COMPARE_COLOR_A,
            label=labelA,
            capsize=2,
        )
    if np.any(mB):
        ax.errorbar(
            xcB[mB],
            yB[mB],
            yerr=_asym_yerr_for_log(yB[mB], eB_plot[mB]),
            fmt="s",
            ms=ms,
            lw=0.8,
            color=COMPARE_COLOR_B,
            label=labelB,
            capsize=2,
        )

    ax.set_ylabel(r"$d\sigma/dM_{jj}$ (mb/GeV)")

    tag = parse_mjj_name(hn)
    if tag:
        R, lo, hi, isAll = tag
        pt_lbl = PT_ALL_LABEL if isAll else f"{lo}–{hi} GeV"
        lead_pt_lbl = rf"lead $p_{{T,1}}$: {pt_lbl}"
        mjj_bb_tag = _mjj_backtoback_title_tag(mjj_require_backtoback, bb_tol_deg)
        wrapped_title = _set_paperready_caption(
            fig,
            f"Dijet invariant mass overlay  [{lead_pt_lbl}; R={R:.2f}{mjj_bb_tag}{ystar_title_suffix}]",
        )
    else:
        wrapped_title = _set_paperready_caption(fig, f"Dijet invariant mass overlay  [{hn}]")

    ax.legend(loc="best", frameon=False)

    meanA, stdA = mjj_stats(xcA, yA, bwA)
    meanB, stdB = mjj_stats(xcB, yB, bwB)
    lines = [
        f"{labelA}: Mean={meanA:.0f} Std={stdA:.0f}",
        f"{labelB}: Mean={meanB:.0f} Std={stdB:.0f}",
    ]
    ax.text(
        0.02,
        0.02,
        "\n".join(lines),
        transform=ax.transAxes,
        va="bottom",
        ha="left",
        fontsize=_FONTS['note'],
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.85, edgecolor="black"),
    )

    bin_match = (
        len(xcA) == len(xcB)
        and np.allclose(xcA, xcB, rtol=0, atol=1e-9)
        and np.allclose(bwA, bwB, rtol=0, atol=1e-9)
    )
    ratio_num_key, _ratio_den_key, ratio_label = _resolve_ratio_order(
        ratio_mode,
        labelA,
        labelB,
        run_tag_a=run_tag_a,
        run_tag_b=run_tag_b,
    )
    if bin_match:
        if ratio_num_key == 'A':
            num_y, num_e = yA, eA_plot
            den_y, den_e = yB, eB_plot
        else:
            num_y, num_e = yB, eB_plot
            den_y, den_e = yA, eA_plot
        r, er, m_plot, _m_err = _ratio_with_optional_errors(num_y, num_e, den_y, den_e)
        if np.any(m_plot):
            errorbar_nan_safe(axr, xcA[m_plot], r[m_plot], er[m_plot], fmt='o', ms=ms, lw=0.8, capsize=2, color='tab:red', label=ratio_label)
            _apply_configured_ratio_ylim(axr, 'MJJ', r[m_plot], er[m_plot], context=hn)
            axr.legend(loc='best', frameon=False)
        else:
            axr.text(0.5, 0.5, 'ratio unavailable', transform=axr.transAxes, ha='center', va='center', fontsize=_FONTS['note'])
    else:
        axr.text(0.5, 0.5, 'ratio unavailable (binning mismatch)', transform=axr.transAxes, ha='center', va='center', fontsize=_FONTS['note'])

    axr.axhline(1.0, color='k', ls='--', lw=1)
    axr.set_ylabel('ratio')
    axr.set_xlabel(r"$M_{jj}$ (GeV)")

    out_path = os.path.join(out_dir, f"{hn}_comparisor.png")
    _safe_tight_layout(fig, rect=[0, 0, 1, _ax_title_rect_top(wrapped_title, top_single=0.98, top_wrapped=0.93)])
    _save_figure(fig, out_path, dpi=160)
    plt.close(fig)


def overlay_plot_perdijet(
    hn: str,
    A: Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float],
    B: Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float],
    labelA: str,
    labelB: str,
    out_dir: str,
    mjj_min_cfg: float,
    mjj_max_cfg: float,
    bb_tol_deg: float,
    mjj_require_backtoback: int,
    ystar_title_suffix: str,
    ms: float,
    *,
    countA: int = None,
    countB: int = None,
    ratio_mode: str = 'med',
    run_tag_a: Optional[str] = None,
    run_tag_b: Optional[str] = None,
) -> None:
    """
    Dijet-normalized overlay.

    SINGLE_SLICE_MODE=1 uses the merged integer selected-dijet count:
      y -> y / N_dijet,sel

    Multi-slice mode keeps the legacy shape/per-selection normalization because
    weighted pThat slices do not have one meaningful integer selected-dijet count.
    """
    xcA, yA, eA, bwA, entA = A
    xcB, yB, eB, bwB, entB = B

    out_path = os.path.join(out_dir, f"{hn}_comparisor_perdijet.png")
    if SINGLE_SLICE_MODE:
        if not (_selected_count_is_positive(countA) and _selected_count_is_positive(countB)):
            reason = _selected_count_skip_reason(labelA, countA, labelB, countB, "Mjj")
            _log(f"[WARN] {hn}: {reason.replace(chr(10), ' | ')}; writing placeholder: {out_path}")
            _write_unavailable_placeholder(
                out_path,
                title=f"Dijet invariant mass overlay skipped [{hn}]",
                reason=reason,
                ylabel=_single_slice_norm_ylabel("mjj"),
            )
            return
        sigA, yAn, eAn = normalize_by_selected_dijet_count(yA, eA, countA)
        sigB, yBn, eBn = normalize_by_selected_dijet_count(yB, eB, countB)
        if yAn is None or eAn is None or yBn is None or eBn is None:
            _log(f"[WARN] {hn}: cannot selected-count normalize (countA={countA}, countB={countB})")
            return
    else:
        sigA, yAn, eAn = normalize_per_dijet_with_cov(yA, eA, bwA, denom_positive_only=False, cov_mode=PERDIJET_COV_MODE)
        sigB, yBn, eBn = normalize_per_dijet_with_cov(yB, eB, bwB, denom_positive_only=False, cov_mode=PERDIJET_COV_MODE)
        if not (np.isfinite(sigA) and sigA > 0 and np.isfinite(sigB) and sigB > 0):
            _log(f"[WARN] {hn}: cannot per-selection normalize (σA={sigA}, σB={sigB})")
            return

    fig, (ax, axr) = plt.subplots(
        2, 1, figsize=(9, 8.4), sharex=True,
        gridspec_kw=dict(height_ratios=[1.0, 0.58], hspace=0.05)
    )
    ax.set_xscale("log")
    ax.set_yscale("log")
    axr.set_xscale("log")

    x_min, x_max = _auto_xlim(
        series=[(xcA, yA, bwA), (xcB, yB, bwB)],
        mjj_min_cfg=mjj_min_cfg,
        mjj_max_cfg=mjj_max_cfg,
        pad_decades=0.06,
    )
    ax.set_xlim(x_min, x_max)

    mA = np.isfinite(xcA) & np.isfinite(yAn) & np.isfinite(eAn) & (xcA > 0) & (yAn > 0)
    mB = np.isfinite(xcB) & np.isfinite(yBn) & np.isfinite(eBn) & (xcB > 0) & (yBn > 0)

    ymin, ymax = _log_ylim_from_positive([yAn[mA] if np.any(mA) else None, yBn[mB] if np.any(mB) else None])
    ax.set_ylim(ymin, ymax)

    if np.any(mA):
        ax.errorbar(
            xcA[mA],
            yAn[mA],
            yerr=_asym_yerr_for_log(yAn[mA], eAn[mA]),
            fmt="o",
            ms=ms,
            lw=0.8,
            color=COMPARE_COLOR_A,
            label=(_legend_count_label(labelA, "mjj", countA) if (SINGLE_SLICE_MODE and countA is not None) else f"{labelA} (σ={sigA:.3e} mb)"),
            capsize=2,
        )
    if np.any(mB):
        ax.errorbar(
            xcB[mB],
            yBn[mB],
            yerr=_asym_yerr_for_log(yBn[mB], eBn[mB]),
            fmt="s",
            ms=ms,
            lw=0.8,
            color=COMPARE_COLOR_B,
            label=(_legend_count_label(labelB, "mjj", countB) if (SINGLE_SLICE_MODE and countB is not None) else f"{labelB} (σ={sigB:.3e} mb)"),
            capsize=2,
        )

    ax.set_ylabel(_single_slice_norm_ylabel("mjj") if SINGLE_SLICE_MODE else r"$(1/\sigma_{\mathrm{sel}})\,d\sigma/dM_{jj}$ (1/GeV)")

    tag = parse_mjj_name(hn)
    if tag:
        R, lo, hi, isAll = tag
        pt_lbl = PT_ALL_LABEL if isAll else f"{lo}–{hi} GeV"
        lead_pt_lbl = rf"lead $p_{{T,1}}$: {pt_lbl}"
        mjj_bb_tag = _mjj_backtoback_title_tag(mjj_require_backtoback, bb_tol_deg)
        wrapped_title = _set_paperready_caption(
            fig,
            f"Dijet invariant mass overlay ({'single-slice count normalized' if SINGLE_SLICE_MODE else 'per selection normalized'})  [{lead_pt_lbl}; R={R:.2f}{mjj_bb_tag}{ystar_title_suffix}]",
        )
    else:
        wrapped_title = _set_paperready_caption(fig, f"Dijet invariant mass overlay (per selection normalized)  [{hn}]")

    ax.legend(loc="best", frameon=False)

    bin_match = (
        len(xcA) == len(xcB)
        and np.allclose(xcA, xcB, rtol=0, atol=1e-9)
        and np.allclose(bwA, bwB, rtol=0, atol=1e-9)
    )
    ratio_num_key, _ratio_den_key, ratio_label = _resolve_ratio_order(
        ratio_mode,
        labelA,
        labelB,
        run_tag_a=run_tag_a,
        run_tag_b=run_tag_b,
    )
    if bin_match:
        if ratio_num_key == 'A':
            num_y, num_e = yAn, eAn
            den_y, den_e = yBn, eBn
        else:
            num_y, num_e = yBn, eBn
            den_y, den_e = yAn, eAn
        r, er, m_plot, _m_err = _ratio_with_optional_errors(num_y, num_e, den_y, den_e)
        if np.any(m_plot):
            errorbar_nan_safe(axr, xcA[m_plot], r[m_plot], er[m_plot], fmt='o', ms=ms, lw=0.8, capsize=2, color='tab:red', label=ratio_label)
            _apply_configured_ratio_ylim(axr, 'MJJ', r[m_plot], er[m_plot], context=hn)
            axr.legend(loc='best', frameon=False)
        else:
            axr.text(0.5, 0.5, 'ratio unavailable', transform=axr.transAxes, ha='center', va='center', fontsize=_FONTS['note'])
    else:
        axr.text(0.5, 0.5, 'ratio unavailable (binning mismatch)', transform=axr.transAxes, ha='center', va='center', fontsize=_FONTS['note'])

    axr.axhline(1.0, color='k', ls='--', lw=1)
    axr.set_ylabel('ratio')
    axr.set_xlabel(r"$M_{jj}$ (GeV)")

    _safe_tight_layout(fig, rect=[0, 0, 1, _ax_title_rect_top(wrapped_title, top_single=0.98, top_wrapped=0.93)])
    _save_figure(fig, out_path, dpi=160)
    plt.close(fig)


def combined_all_plot(
    hA: Dict[str, Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]],
    hB: Dict[str, Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]],
    labelA: str,
    labelB: str,
    out_dir: str,
    mjj_min_cfg: float,
    mjj_max_cfg: float,
    bb_tol_deg: float,
    mjj_require_backtoback: int,
    ystar_title_suffix: str,
    R_list: List[float],
    ms: float,
) -> None:
    use_nosubfrac = bool(hA) and all(str(k).endswith('_nosubfrac') for k in hA.keys()) and bool(hB) and all(str(k).endswith('_nosubfrac') for k in hB.keys())
    names = [_existing_hist_name("mjj", R, hA, hB, is_nosubfrac=use_nosubfrac) for R in R_list]
    missing = [n for n in names if (n not in hA) or (n not in hB)]
    if missing:
        _log(f"[INFO] Skipping combined all-R plot; missing in one or both files: {', '.join(missing)}")
        return

    markers = list(PAPERREADY_STYLE_MARKERS)
    colorsR = list(PAPERREADY_MULTI_R_COLORS)
    fig, ax = plt.subplots(figsize=(9, 7))
    ax.set_xscale("log")
    ax.set_yscale("log")

    # data-driven x range across ALL curves in this combined plot
    series = []
    for n in names:
        xcA, yA, _, bwA, _ = hA[n]
        xcB, yB, _, bwB, _ = hB[n]
        series.append((xcA, yA, bwA))
        series.append((xcB, yB, bwB))

    x_min, x_max = _auto_xlim(
        series=series,
        mjj_min_cfg=mjj_min_cfg,
        mjj_max_cfg=mjj_max_cfg,
        pad_decades=0.06,
    )
    ax.set_xlim(x_min, x_max)

    # y-limits from all positive bins across all curves
    yvals = []
    for n in names:
        _, yA, _, _, _ = hA[n]
        _, yB, _, _, _ = hB[n]
        yvals.append(yA)
        yvals.append(yB)
    ymin, ymax = _log_ylim_from_positive(yvals)
    ax.set_ylim(ymin, ymax)

    for i, R in enumerate(R_list):
        n = _existing_hist_name("mjj", R, hA, hB, is_nosubfrac=use_nosubfrac)
        xcA, yA, eA, bwA, _ = hA[n]
        xcB, yB, eB, bwB, _ = hB[n]
        normA = xsec_norm_term_for_hist(XSEC_BAND_A, n, xcA, bwA)
        normB = xsec_norm_term_for_hist(XSEC_BAND_B, n, xcB, bwB)

        mk = markers[i % len(markers)]
        color_r = colorsR[i % len(colorsR)]

        mA = np.isfinite(xcA) & np.isfinite(yA) & np.isfinite(eA) & (xcA > 0) & (yA > 0)
        mB = np.isfinite(xcB) & np.isfinite(yB) & np.isfinite(eB) & (xcB > 0) & (yB > 0)

        if np.any(mA):
            ax.errorbar(
                xcA[mA],
                yA[mA],
                yerr=_asym_yerr_for_log(yA[mA], yerr_for_plot_absolute(yA[mA], eA[mA], normA[mA] if np.ndim(normA) > 0 else normA)),
                fmt=mk,
                ms=ms,
                lw=1.0,
                linestyle='-',
                color=color_r,
                markerfacecolor=color_r,
                markeredgecolor=color_r,
                capsize=2,
                label=f"{labelA} R={R:.2f}",
            )
        if np.any(mB):
            ax.errorbar(
                xcB[mB],
                yB[mB],
                yerr=_asym_yerr_for_log(yB[mB], yerr_for_plot_absolute(yB[mB], eB[mB], normB[mB] if np.ndim(normB) > 0 else normB)),
                fmt=mk,
                ms=ms,
                lw=1.0,
                linestyle='--',
                color=color_r,
                markerfacecolor='white',
                markeredgecolor=color_r,
                markeredgewidth=1.0,
                capsize=2,
                label=f"{labelB} R={R:.2f}",
            )

    ax.set_xlabel(r"$M_{jj}$ (GeV)")
    ax.set_ylabel(r"$d\sigma/dM_{jj}$ (mb/GeV)")
    mjj_bb_tag = _mjj_backtoback_title_tag(mjj_require_backtoback, bb_tol_deg)
    combined_sel_tag = (mjj_bb_tag[2:] if mjj_bb_tag.startswith('; ') else mjj_bb_tag)
    _set_paperready_caption(
        fig,
        f"Dijet invariant mass overlay (lead pT {PT_ALL_LABEL})  [{combined_sel_tag}{ystar_title_suffix}]",
    )
    ax.legend(loc="best", fontsize=_FONTS['legend'], frameon=False)

    tag = "_".join([f"R{int(round(r*100)):03d}" for r in R_list])
    out_path = os.path.join(out_dir, f"mjj_allR_{tag}_comparisor.png")
    fig.tight_layout()
    _save_figure(fig, out_path, dpi=170)
    plt.close(fig)
    _log(f"Combined all-R plot written: {out_path}")


# --------------------------- custom ln(jet spectra) 4-panel collages ---------------------------

def make_jetpt_ln_overlay_4panel(out_dir_jet: str, out_dir_custom: str, *, kind: str) -> Optional[str]:
    """Retired helper: ln(dσ/dp_T) collages are intentionally no longer produced."""
    _log(
        f"[INFO] Retired custom collage skipped: ln(dσ/dp_T) 4-panel image for kind={kind}. "
        f"Use the standard jet-spectrum overlays and ratio diagnostics instead."
    )
    return None

# --------------------------- custom Δφ_abs 4-panel (no ratio) ---------------------------

def _dphi_abs_hist_name(R: float, lo: int, hi: int) -> str:
    """Canonical Δφ_abs histogram name used by the analyzer."""
    return f"dphi_abs_R{int(round(R*100)):03d}_{lo}_{hi}"


def _plot_dphi_two_row_no_ratio(
    ax_top,
    ax_bot,
    hn: str,
    vac: Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float],
    brick: Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float],
    *,
    label_vac: str,
    label_brick: str,
    ms: float = 3.0,
    use_perdijet: bool = False,
) -> None:
    """Draw vacuum on ax_top and brick on ax_bot, no ratio panel.

    This is meant for multi-panel collages where the third "ratio" row would be visual clutter.
    """
    xcV, yV, eV, bwV, _ = vac
    xcB, yB, eB, bwB, _ = brick

    yVn = eVn = yBn = eBn = None
    using_norm = False
    if use_perdijet:
        _, yVn, eVn = normalize_per_dijet_with_cov(yV, eV, bwV, denom_positive_only=False, cov_mode=PERDIJET_COV_MODE)
        _, yBn, eBn = normalize_per_dijet_with_cov(yB, eB, bwB, denom_positive_only=False, cov_mode=PERDIJET_COV_MODE)
        using_norm = ((yVn is not None) and (yBn is not None))

    if using_norm:
        yVplot, eVplot = yVn, eVn
        yBplot, eBplot = yBn, eBn
    else:
        yVplot, eVplot = yV, eV
        yBplot, eBplot = yB, eB

    spV, tailV = _dphi_broadening_metrics(xcV, yVplot, bwV)
    spB, tailB = _dphi_broadening_metrics(xcB, yBplot, bwB)

    errorbar_nan_safe(ax_top, xcV, yVplot, eVplot, fmt='o', ms=ms, lw=0.8, capsize=2, color=COMPARE_COLOR_A)
    ax_top.text(0.02, 0.90, label_vac, transform=ax_top.transAxes, ha='left', va='top', fontsize=_FONTS['note'],
                bbox=dict(boxstyle='round,pad=0.20', facecolor='white', alpha=0.85, edgecolor='black'))
    ax_top.text(0.98, 0.90, f"σ≈{spV:.4f}\n tail≈{tailV:.3f}", transform=ax_top.transAxes,
                ha='right', va='top', fontsize=_FONTS['note'],
                bbox=dict(boxstyle='round,pad=0.18', facecolor='white', alpha=0.85, edgecolor='black'))

    errorbar_nan_safe(ax_bot, xcB, yBplot, eBplot, fmt='o', ms=ms, lw=0.8, capsize=2, color=COMPARE_COLOR_B)
    ax_bot.text(0.02, 0.90, label_brick, transform=ax_bot.transAxes, ha='left', va='top', fontsize=_FONTS['note'],
                bbox=dict(boxstyle='round,pad=0.20', facecolor='white', alpha=0.85, edgecolor='black'))
    ax_bot.text(0.98, 0.90, f"σ≈{spB:.4f}\n tail≈{tailB:.3f}", transform=ax_bot.transAxes,
                ha='right', va='top', fontsize=_FONTS['note'],
                bbox=dict(boxstyle='round,pad=0.18', facecolor='white', alpha=0.85, edgecolor='black'))

    ax_top.set_xlim(0.0, float(np.pi))
    ax_bot.set_xlim(0.0, float(np.pi))

    # y-label is set by the caller (to avoid repeating on every panel)



def _pt_xrange_from_nonzero(
    xc: np.ndarray,
    y: np.ndarray,
    bw: np.ndarray,
    pad_frac: float = 0.08,
    *,
    x_floor: float = 1.0,
    x_ceil: Optional[float] = None,
    min_pad_gev: float = 15.0,
) -> Tuple[float, float]:
    xc = np.asarray(xc, dtype=float)
    y = np.asarray(y, dtype=float)
    bw = np.asarray(bw, dtype=float)

    mask = np.isfinite(xc) & np.isfinite(y) & np.isfinite(bw) & (bw > 0) & (y > 0)
    finite_x = xc[np.isfinite(xc)]
    if not np.any(mask):
        if finite_x.size == 0:
            lo = max(1e-6, float(x_floor))
            hi = float(x_ceil) if (x_ceil is not None and np.isfinite(x_ceil) and x_ceil > lo) else lo * 10.0
            return lo, hi
        lo = max(1e-6, float(np.nanmin(finite_x)))
        hi = float(np.nanmax(finite_x))
        if x_ceil is not None and np.isfinite(x_ceil) and x_ceil > lo:
            hi = min(hi, float(x_ceil))
        return lo, hi if hi > lo else max(lo * 10.0, lo + 1.0)

    lo_edges = xc[mask] - 0.5 * bw[mask]
    hi_edges = xc[mask] + 0.5 * bw[mask]
    valid = np.isfinite(lo_edges) & np.isfinite(hi_edges) & (hi_edges > 0)
    if not np.any(valid):
        lo = max(1e-6, float(np.nanmin(xc[mask])))
        hi = float(np.nanmax(xc[mask]))
        if x_ceil is not None and np.isfinite(x_ceil) and x_ceil > lo:
            hi = min(hi, float(x_ceil))
        return lo, hi if hi > lo else max(lo * 10.0, lo + 1.0)

    lo_edges = lo_edges[valid]
    hi_edges = hi_edges[valid]
    lo_edges = lo_edges[lo_edges > 0]
    if lo_edges.size == 0 or hi_edges.size == 0:
        lo = max(1e-6, float(np.nanmin(xc[mask])))
        hi = float(np.nanmax(xc[mask]))
        if x_ceil is not None and np.isfinite(x_ceil) and x_ceil > lo:
            hi = min(hi, float(x_ceil))
        return lo, hi if hi > lo else max(lo * 10.0, lo + 1.0)

    x_min = float(np.nanmin(lo_edges))
    x_max = float(np.nanmax(hi_edges))
    if not (np.isfinite(x_min) and np.isfinite(x_max)):
        lo = max(1e-6, float(x_floor))
        hi = float(x_ceil) if (x_ceil is not None and np.isfinite(x_ceil) and x_ceil > lo) else lo * 10.0
        return lo, hi

    span = max(x_max - x_min, 0.0)
    pad = max(span * pad_frac, float(min_pad_gev))
    x_min = max(1e-6, x_min - pad)
    x_max = x_max + pad

    if np.isfinite(x_floor) and float(x_floor) > 0:
        x_min = max(x_min, float(x_floor))
    if x_ceil is not None and np.isfinite(x_ceil) and float(x_ceil) > x_min:
        x_max = min(x_max, float(x_ceil))
    if not (np.isfinite(x_max) and x_max > x_min):
        x_max = max(x_min * 10.0, x_min + 1.0)
    return x_min, x_max


def _auto_ratio_ylim(
    ratio: np.ndarray,
    ratio_err: Optional[np.ndarray] = None,
    *,
    center: float = 1.0,
    default: Tuple[float, float] = (0.2, 1.8),
    min_halfspan: float = 0.12,
    max_halfspan: float = 4.0,
    pad_frac: float = 0.15,
) -> Tuple[float, float]:
    """Choose ratio-panel y-limits from finite values/errors instead of hard clipping."""
    r = np.asarray(ratio, dtype=float)
    m = np.isfinite(r)
    if not np.any(m):
        return default

    candidates = [r[m]]
    if ratio_err is not None:
        er = np.asarray(ratio_err, dtype=float)
        me = m & np.isfinite(er) & (er >= 0)
        if np.any(me):
            candidates.append(r[me] - er[me])
            candidates.append(r[me] + er[me])

    vals = np.concatenate(candidates) if len(candidates) > 1 else candidates[0]
    vals = vals[np.isfinite(vals)]
    if vals.size == 0:
        return default

    halfspan = float(np.nanmax(np.abs(vals - center)))
    if not np.isfinite(halfspan):
        return default

    halfspan = min(max_halfspan, max(min_halfspan, (1.0 + pad_frac) * halfspan))
    ymin = max(0.0, center - halfspan)
    ymax = center + halfspan
    if not (np.isfinite(ymin) and np.isfinite(ymax)) or ymax <= ymin:
        return default
    return ymin, ymax


def _configured_ratio_ylim(kind: str) -> Tuple[float, float]:
    try:
        ymin, ymax = RATIO_YLIMS[kind]
    except KeyError as exc:
        _die(f"Missing configured ratio y-limits for kind={kind!r}. Update jetscape.ini compare ratio range knobs.")
        raise exc
    return float(ymin), float(ymax)


def _apply_configured_ratio_ylim(ax, kind: str, ratio: Optional[np.ndarray] = None, ratio_err: Optional[np.ndarray] = None, *, context: str = "") -> None:
    ymin, ymax = _configured_ratio_ylim(kind)
    ax.set_ylim(ymin, ymax)

    if ratio is None:
        return

    r = np.asarray(ratio, dtype=float)
    m = np.isfinite(r)
    candidates = [r[m]] if np.any(m) else []
    if ratio_err is not None:
        er = np.asarray(ratio_err, dtype=float)
        me = m & np.isfinite(er) & (er >= 0)
        if np.any(me):
            candidates.append(r[me] - er[me])
            candidates.append(r[me] + er[me])

    if not candidates:
        return

    vals = np.concatenate(candidates) if len(candidates) > 1 else candidates[0]
    vals = vals[np.isfinite(vals)]
    if vals.size == 0:
        return

    vmin = float(np.nanmin(vals))
    vmax = float(np.nanmax(vals))
    if vmin < ymin or vmax > ymax:
        ctx = f" ({context})" if context else ""
        _log(f"[ratio-range][WARN] kind={kind}{ctx}: plotted ratio extent [{vmin:.6g}, {vmax:.6g}] exceeds configured window [{ymin:.6g}, {ymax:.6g}]")


def plot_particle_overlay(
    hn: str,
    vac: Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float],
    med: Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float],
    label_vac: str,
    label_med: str,
    out_dir: str,
    *,
    xsec_band_vac=None,
    xsec_band_med=None,
    ms: float = 3.0,
) -> None:
    """Overlay accepted particle-level constituent spectra for the compared runs."""
    kind = parse_particle_name(hn)
    if kind is None:
        return

    xcV, yV, eV, bwV, _ = vac
    xcM, yM, eM, bwM, _ = med

    eV_plot = yerr_for_plot_absolute(yV, eV, xsec_norm_term_for_hist(xsec_band_vac, hn, xcV, bwV))
    eM_plot = yerr_for_plot_absolute(yM, eM, xsec_norm_term_for_hist(xsec_band_med, hn, xcM, bwM))

    fig, ax = plt.subplots(figsize=(8.8, 6.2))

    if kind == 'pt':
        mV = np.isfinite(xcV) & np.isfinite(yV) & np.isfinite(eV_plot) & (xcV > 0) & (yV > 0)
        mM = np.isfinite(xcM) & np.isfinite(yM) & np.isfinite(eM_plot) & (xcM > 0) & (yM > 0)
        if not (np.any(mV) or np.any(mM)):
            _log(f"[WARN] particle-level {hn}: no positive bins to plot")
            plt.close(fig)
            return
        ax.set_xscale('log')
        _apply_logy_with_floor(ax, [yV[mV] if np.any(mV) else None, yM[mM] if np.any(mM) else None])
        x_min, x_max = _pt_xrange_from_nonzero(
            np.concatenate([xcV[mV] if np.any(mV) else np.array([]), xcM[mM] if np.any(mM) else np.array([])]),
            np.concatenate([yV[mV] if np.any(mV) else np.array([]), yM[mM] if np.any(mM) else np.array([])]),
            np.concatenate([bwV[mV] if np.any(mV) else np.array([]), bwM[mM] if np.any(mM) else np.array([])]),
        )
        ax.set_xlim(max(1e-6, x_min), x_max)
        if np.any(mV):
            ax.errorbar(xcV[mV], yV[mV], yerr=_asym_yerr_for_log(yV[mV], eV_plot[mV]), fmt='o', ms=ms, lw=0.8, capsize=2, color=COMPARE_COLOR_A, label=label_vac)
        if np.any(mM):
            ax.errorbar(xcM[mM], yM[mM], yerr=_asym_yerr_for_log(yM[mM], eM_plot[mM]), fmt='s', ms=ms, lw=0.8, capsize=2, color=COMPARE_COLOR_B, label=label_med)
        ax.set_xlabel(r"$p_{T}^{\mathrm{particle}}$ [GeV]")
        ax.set_ylabel(r"$d\sigma/dp_{T}^{\mathrm{particle}}$ (mb/GeV)")
        _set_paperready_caption(fig, "Inclusive weighted yield of accepted particle-level constituents (pre-clustering): $p_T$ comparison", max_chars=118)
    elif kind == 'eta':
        mV = np.isfinite(xcV) & np.isfinite(yV) & np.isfinite(eV_plot)
        mM = np.isfinite(xcM) & np.isfinite(yM) & np.isfinite(eM_plot)
        if not (np.any(mV) or np.any(mM)):
            _log(f"[WARN] particle-level {hn}: no finite bins to plot")
            plt.close(fig)
            return
        if np.any(mV):
            ax.errorbar(xcV[mV], yV[mV], yerr=eV_plot[mV], fmt='o', ms=ms, lw=0.8, capsize=2, color=COMPARE_COLOR_A, label=label_vac)
        if np.any(mM):
            ax.errorbar(xcM[mM], yM[mM], yerr=eM_plot[mM], fmt='s', ms=ms, lw=0.8, capsize=2, color=COMPARE_COLOR_B, label=label_med)
        x_all = np.concatenate([xcV[mV] if np.any(mV) else np.array([]), xcM[mM] if np.any(mM) else np.array([])])
        if x_all.size:
            x_min = float(np.nanmin(x_all))
            x_max = float(np.nanmax(x_all))
            pad = 0.05 * (x_max - x_min) if x_max > x_min else 0.2
            ax.set_xlim(x_min - pad, x_max + pad)
        ax.set_xlabel(r"$\eta^{\mathrm{particle}}$")
        ax.set_ylabel(r"$d\sigma/d\eta^{\mathrm{particle}}$ (mb)")
        _set_paperready_caption(fig, r"Inclusive weighted yield of accepted particle-level constituents (pre-clustering): pseudorapidity $\eta$ comparison", max_chars=118)
    else:
        mV = np.isfinite(xcV) & np.isfinite(yV) & np.isfinite(eV_plot)
        mM = np.isfinite(xcM) & np.isfinite(yM) & np.isfinite(eM_plot)
        if not (np.any(mV) or np.any(mM)):
            _log(f"[WARN] particle-level {hn}: no finite bins to plot")
            plt.close(fig)
            return
        if np.any(mV):
            ax.errorbar(xcV[mV], yV[mV], yerr=eV_plot[mV], fmt='o', ms=ms, lw=0.8, capsize=2, color=COMPARE_COLOR_A, label=label_vac)
        if np.any(mM):
            ax.errorbar(xcM[mM], yM[mM], yerr=eM_plot[mM], fmt='s', ms=ms, lw=0.8, capsize=2, color=COMPARE_COLOR_B, label=label_med)
        x_all = np.concatenate([xcV[mV] if np.any(mV) else np.array([]), xcM[mM] if np.any(mM) else np.array([])])
        if x_all.size:
            x_min = float(np.nanmin(x_all))
            x_max = float(np.nanmax(x_all))
            pad = 0.05 * (x_max - x_min) if x_max > x_min else 0.2
            ax.set_xlim(x_min - pad, x_max + pad)
        ax.set_xlabel(r"$\phi^{\mathrm{particle}}$ [rad]")
        ax.set_ylabel(r"$d\sigma/d\phi^{\mathrm{particle}}$ (mb/rad)")
        _set_paperready_caption(fig, r"Inclusive weighted yield of accepted particle-level constituents (pre-clustering): azimuth $\phi$ comparison", max_chars=118)

    ax.legend(loc='best', fontsize=_FONTS['legend'], frameon=False)
    _safe_tight_layout(fig)
    _save_figure(fig, os.path.join(out_dir, f"{hn}_overlay.png"), dpi=170)
    plt.close(fig)


def _common_profile_ratio(
    x_num: np.ndarray, y_num: np.ndarray, e_num: np.ndarray,
    x_den: np.ndarray, y_den: np.ndarray, e_den: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return matched-bin ratio arrays for profile overlays using common x centers."""
    out_x, out_r, out_e = [], [], []
    if len(x_num) == 0 or len(x_den) == 0:
        return np.array([]), np.array([]), np.array([])
    for i, xv in enumerate(x_num):
        if not (np.isfinite(xv) and np.isfinite(y_num[i]) and np.isfinite(e_num[i]) and y_num[i] > 0):
            continue
        hits = np.where(np.isfinite(x_den) & np.isclose(x_den, xv, rtol=1e-10, atol=1e-10))[0]
        if hits.size == 0:
            continue
        j = int(hits[0])
        if not (np.isfinite(y_den[j]) and np.isfinite(e_den[j]) and y_den[j] > 0):
            continue
        ratio = float(y_num[i] / y_den[j])
        rel2 = 0.0
        if e_num[i] > 0 and np.isfinite(e_num[i]):
            rel2 += (float(e_num[i]) / float(y_num[i])) ** 2
        if e_den[j] > 0 and np.isfinite(e_den[j]):
            rel2 += (float(e_den[j]) / float(y_den[j])) ** 2
        out_x.append(float(xv))
        out_r.append(ratio)
        out_e.append(abs(ratio) * math.sqrt(max(0.0, rel2)))
    return np.asarray(out_x, dtype=float), np.asarray(out_r, dtype=float), np.asarray(out_e, dtype=float)


def plot_sublead_vs_lead_profile_compare(
    hn: str,
    vac: Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float],
    med: Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float],
    label_vac: str,
    label_med: str,
    out_dir: str,
    *,
    ratio_mode: str = 'med',
    ms: float = 3.0,
) -> None:
    """Overlay vacuum vs medium TProfile mean subleading-vs-leading jet pT curves with a ratio panel."""
    parsed = parse_sublead_vs_lead_profile_name(hn)
    if parsed is None:
        return
    Rv, is_ns = parsed
    xcV, yV, eV, bwV, _ = vac
    xcM, yM, eM, bwM, _ = med

    mV = np.isfinite(xcV) & np.isfinite(yV) & np.isfinite(eV) & (xcV > 0) & (yV > 0)
    mM = np.isfinite(xcM) & np.isfinite(yM) & np.isfinite(eM) & (xcM > 0) & (yM > 0)
    if not (np.any(mV) or np.any(mM)):
        _log(f"[WARN] profile {hn}: no positive finite bins to plot")
        return

    fig = plt.figure(figsize=(8.8, 7.4))
    gs = GridSpec(2, 1, height_ratios=[3.2, 1.1], hspace=0.08)
    ax = fig.add_subplot(gs[0, 0])
    rax = fig.add_subplot(gs[1, 0], sharex=ax)

    if np.any(mV):
        ax.errorbar(xcV[mV], yV[mV], yerr=eV[mV], fmt='o-', ms=ms, lw=0.8, capsize=2, color=COMPARE_COLOR_A, label=label_vac)
    if np.any(mM):
        ax.errorbar(xcM[mM], yM[mM], yerr=eM[mM], fmt='s-', ms=ms, lw=0.8, capsize=2, color=COMPARE_COLOR_B, label=label_med)

    x_all = np.concatenate([xcV[mV] if np.any(mV) else np.array([]), xcM[mM] if np.any(mM) else np.array([])])
    bw_all = np.concatenate([bwV[mV] if np.any(mV) else np.array([]), bwM[mM] if np.any(mM) else np.array([])])
    if x_all.size == 0:
        _log(f"[WARN] profile {hn}: no finite x values after masking")
        plt.close(fig)
        return
    xlo = float(np.min(x_all - 0.5 * bw_all))
    xhi = float(np.max(x_all + 0.5 * bw_all))

    ylow = np.concatenate([yV[mV] - eV[mV] if np.any(mV) else np.array([]), yM[mM] - eM[mM] if np.any(mM) else np.array([])])
    yhigh = np.concatenate([yV[mV] + eV[mV] if np.any(mV) else np.array([]), yM[mM] + eM[mM] if np.any(mM) else np.array([])])
    ylow_pos = ylow[np.isfinite(ylow) & (ylow > 0)]
    ymin = float(np.min(ylow_pos)) if ylow_pos.size else float(np.min(np.concatenate([yV[mV] if np.any(mV) else np.array([]), yM[mM] if np.any(mM) else np.array([])])))
    ymax = float(np.max(yhigh[np.isfinite(yhigh)])) if np.any(np.isfinite(yhigh)) else max(1.0, ymin * 1.1)

    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlim(max(1e-6, xlo), xhi)
    ax.set_ylim(max(1e-6, ymin), max(max(1e-6, ymin) * 1.05, ymax))
    ax.plot([max(1e-6, xlo), xhi], [max(1e-6, xlo), xhi], ls='--', lw=0.8, color='k', alpha=0.7, label=r'$p_{T}^{sublead}=p_{T}^{lead}$')
    ax.set_ylabel(r'$\langle p_{T}^{\mathrm{sublead}}\rangle$ [GeV]')
    _set_wrapped_ax_title(
        ax,
        f"Mean subleading jet $p_T$ vs leading jet $p_T$ comparison"
        + _pair_title_bracket(Rv, hn, include_ystar=True),
    )
    ax.legend(loc='best', fontsize=_FONTS['legend'], frameon=False)

    if (ratio_mode or 'med').strip().lower() == 'inv':
        xr, rr, er = _common_profile_ratio(xcV[mV], yV[mV], eV[mV], xcM[mM], yM[mM], eM[mM])
        ratio_label = f"{label_vac}/{label_med}"
    else:
        xr, rr, er = _common_profile_ratio(xcM[mM], yM[mM], eM[mM], xcV[mV], yV[mV], eV[mV])
        ratio_label = f"{label_med}/{label_vac}"

    rax.axhline(1.0, color='k', ls='--', lw=0.8)
    if xr.size > 0:
        rax.errorbar(xr, rr, yerr=er, fmt='o', ms=ms, lw=0.8, capsize=2, color='k')
        _apply_configured_ratio_ylim(rax, 'LEAD_SUBLEAD_PROFILE', rr, er, context=hn)
    else:
        rax.text(0.5, 0.5, 'No common positive bins for ratio', transform=rax.transAxes, ha='center', va='center', fontsize=_FONTS['note'])
    rax.set_xscale('log')
    rax.set_ylabel(ratio_label)
    rax.set_xlabel(r'Leading jet $p_T$ [GeV]')

    _safe_tight_layout(fig)
    _save_figure(fig, os.path.join(out_dir, f"{hn}_overlay.png"), dpi=170)
    plt.close(fig)


def plot_sublead_vs_lead_h2_compare(
    hn: str,
    vac: Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float],
    med: Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float],
    label_vac: str,
    label_med: str,
    out_dir: str,
    *,
    ratio_mode: str = 'med',
) -> None:
    """Compare vacuum vs medium TH2 lead-vs-sublead maps with shared normalization and a ratio panel."""
    parsed = parse_sublead_vs_lead_h2_name(hn)
    if parsed is None:
        return
    Rv, is_ns = parsed
    xedgesV, yedgesV, zV, _eV, _nV = vac
    xedgesM, yedgesM, zM, _eM, _nM = med

    if zV.ndim != 2 or zM.ndim != 2:
        _log(f"[WARN] TH2 {hn}: unexpected dimensions vac={zV.shape} med={zM.shape}; skipping")
        return

    if not (np.array_equal(xedgesV, xedgesM) and np.array_equal(yedgesV, yedgesM) and zV.shape == zM.shape):
        _log(f"[WARN] TH2 {hn}: vacuum/medium binning mismatch; ratio panel will be omitted")
        use_ratio = False
        xedges = xedgesV
        yedges = yedgesV
    else:
        use_ratio = True
        xedges = xedgesV
        yedges = yedgesV

    def _positive_extent(xedges_local, yedges_local, *arrays) -> Optional[Tuple[float, float, float, float]]:
        mask = None
        for arr in arrays:
            if arr is None:
                continue
            a = np.asarray(arr, dtype=float)
            cur = np.isfinite(a) & (a > 0)
            mask = cur if mask is None else (mask | cur)
        if mask is None or not np.any(mask):
            return None
        ix, iy = np.where(mask)
        x0 = float(xedges_local[int(np.min(ix))])
        x1 = float(xedges_local[int(np.max(ix)) + 1])
        y0 = float(yedges_local[int(np.min(iy))])
        y1 = float(yedges_local[int(np.max(iy)) + 1])
        return (x0, x1, y0, y1)

    extent = _positive_extent(xedges, yedges, zV, zM)
    if extent is None:
        xlo, xhi = max(1e-6, float(xedges[0])), float(xedges[-1])
        ylo, yhi = max(1e-6, float(yedges[0])), float(yedges[-1])
        autozoom_note = False
    else:
        xlo, xhi, ylo, yhi = extent
        xlo = max(1e-6, xlo)
        ylo = max(1e-6, ylo)
        autozoom_note = (xlo > max(1e-6, float(xedges[0])) or xhi < float(xedges[-1]) or ylo > max(1e-6, float(yedges[0])) or yhi < float(yedges[-1]))

    zV_plot = np.asarray(zV, dtype=float).T
    zM_plot = np.asarray(zM, dtype=float).T
    pos_all = np.concatenate([zV_plot[np.isfinite(zV_plot) & (zV_plot > 0)], zM_plot[np.isfinite(zM_plot) & (zM_plot > 0)]])

    fig = plt.figure(figsize=(17.2, 6.4))
    gs = GridSpec(1, 3, width_ratios=[1.0, 1.0, 1.06], wspace=0.34)
    axV = fig.add_subplot(gs[0, 0])
    axM = fig.add_subplot(gs[0, 1], sharex=axV, sharey=axV)
    axR = fig.add_subplot(gs[0, 2], sharex=axV, sharey=axV)

    if pos_all.size > 0:
        vmin = float(np.min(pos_all))
        vmax = float(np.max(pos_all))
        norm = LogNorm(vmin=vmin, vmax=vmax)
        pcmV = axV.pcolormesh(xedgesV, yedgesV, np.ma.masked_less_equal(zV_plot, 0.0), shading='auto', norm=norm)
        pcmM = axM.pcolormesh(xedgesM, yedgesM, np.ma.masked_less_equal(zM_plot, 0.0), shading='auto', norm=norm)
    else:
        pcmV = axV.pcolormesh(xedgesV, yedgesV, zV_plot, shading='auto')
        pcmM = axM.pcolormesh(xedgesM, yedgesM, zM_plot, shading='auto')

    diag_lo = max(1e-6, min(xlo, ylo))
    diag_hi = max(xhi, yhi)
    for ax in (axV, axM, axR):
        ax.set_xscale('log')
        ax.set_yscale('log')
        ax.set_xlim(xlo, xhi)
        ax.set_ylim(ylo, yhi)
        ax.plot([diag_lo, diag_hi], [diag_lo, diag_hi], ls='--', lw=0.8, color='white' if ax in (axV, axM) else 'k', alpha=0.8)
        ax.set_xlabel(r'Leading jet $p_T$ [GeV]')
    axV.set_ylabel(r'Subleading jet $p_T$ [GeV]')

    pair_tag = _pair_title_bracket(Rv, hn, include_ystar=True)
    _set_wrapped_ax_title(axV, f"{label_vac}", max_chars=54, pad_single=5.0, pad_wrapped=8.5)
    _set_wrapped_ax_title(axM, f"{label_med}", max_chars=54, pad_single=5.0, pad_wrapped=8.5)

    cbar_vm = fig.colorbar(pcmM, ax=[axV, axM], shrink=0.88, pad=0.02)
    cbar_vm.set_label('Weighted dijet yield [mb]')

    if use_ratio:
        if (ratio_mode or 'med').strip().lower() == 'inv':
            num = np.asarray(zV, dtype=float)
            den = np.asarray(zM, dtype=float)
            ratio_title = f"{label_vac}/{label_med}"
        else:
            num = np.asarray(zM, dtype=float)
            den = np.asarray(zV, dtype=float)
            ratio_title = f"{label_med}/{label_vac}"
        ratio = np.full_like(num, np.nan, dtype=float)
        mask = np.isfinite(num) & np.isfinite(den) & (num > 0) & (den > 0)
        ratio[mask] = num[mask] / den[mask]
        ratio_plot = ratio.T
        pos_ratio = ratio_plot[np.isfinite(ratio_plot) & (ratio_plot > 0)]
        if pos_ratio.size > 0:
            rmin = float(np.min(pos_ratio))
            rmax = float(np.max(pos_ratio))
            if np.isfinite(rmin) and np.isfinite(rmax) and rmax > 0:
                pcmR = axR.pcolormesh(xedges, yedges, np.ma.masked_invalid(ratio_plot), shading='auto', norm=LogNorm(vmin=max(rmin, 1e-12), vmax=max(rmax, max(rmin, 1e-12) * 1.01)))
            else:
                pcmR = axR.pcolormesh(xedges, yedges, np.ma.masked_invalid(ratio_plot), shading='auto')
            cbar_r = fig.colorbar(pcmR, ax=axR, shrink=0.88, pad=0.02)
            cbar_r.set_label(ratio_title)
        else:
            axR.text(0.5, 0.5, 'No valid positive ratio bins', transform=axR.transAxes, ha='center', va='center', fontsize=_FONTS['note'])
        _set_wrapped_ax_title(axR, f"{ratio_title}", max_chars=48, pad_single=5.0, pad_wrapped=8.0)
    else:
        axR.text(0.5, 0.5, 'Binning mismatch: ratio omitted', transform=axR.transAxes, ha='center', va='center', fontsize=_FONTS['note'])
        _set_wrapped_ax_title(axR, 'Ratio unavailable', max_chars=48, pad_single=5.0, pad_wrapped=8.0)

    wrapped_suptitle = _set_paperready_caption(fig, 'Subleading vs leading jet $p_T$ comparison map' + pair_tag, max_chars=118)
    _safe_tight_layout(fig, rect=[0, 0, 1, _suptitle_rect_top(wrapped_suptitle, top_single=0.955, top_wrapped=0.89)])
    _save_figure(fig, os.path.join(out_dir, f"{hn}_compare.png"), dpi=170)
    plt.close(fig)


def plot_dphi_abs_vs_deta_h2_compare(
    hn: str,
    vac: Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float],
    med: Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float],
    label_vac: str,
    label_med: str,
    out_dir: str,
    *,
    ratio_mode: str = 'med',
) -> None:
    """Compare vacuum vs medium TH2 |Δφ| vs |Δη| maps with a ratio panel."""
    parsed = parse_dphi_abs_vs_deta_h2_name(hn)
    if parsed is None:
        return
    Rv, _lo, _hi, _is_all, _is_ns = parsed
    xedgesV, yedgesV, zV, _eV, _nV = vac
    xedgesM, yedgesM, zM, _eM, _nM = med

    if zV.ndim != 2 or zM.ndim != 2:
        _log(f"[WARN] TH2 {hn}: unexpected dimensions vac={zV.shape} med={zM.shape}; skipping")
        return

    same_binning = (np.array_equal(xedgesV, xedgesM) and np.array_equal(yedgesV, yedgesM) and zV.shape == zM.shape)
    xedges = xedgesV
    yedges = yedgesV

    zV_plot = np.asarray(zV, dtype=float).T
    zM_plot = np.asarray(zM, dtype=float).T
    pos_all = np.concatenate([zV_plot[np.isfinite(zV_plot) & (zV_plot > 0)], zM_plot[np.isfinite(zM_plot) & (zM_plot > 0)]])

    fig = plt.figure(figsize=(17.2, 6.2))
    gs = GridSpec(1, 3, width_ratios=[1.0, 1.0, 1.06], wspace=0.34)
    axV = fig.add_subplot(gs[0, 0])
    axM = fig.add_subplot(gs[0, 1], sharex=axV, sharey=axV)
    axR = fig.add_subplot(gs[0, 2], sharex=axV, sharey=axV)

    if pos_all.size > 0:
        vmin = float(np.min(pos_all))
        vmax = float(np.max(pos_all))
        norm = LogNorm(vmin=max(vmin, 1e-12), vmax=max(vmax, max(vmin, 1e-12) * 1.01))
        pcmV = axV.pcolormesh(xedgesV, yedgesV, np.ma.masked_less_equal(zV_plot, 0.0), shading='auto', norm=norm)
        pcmM = axM.pcolormesh(xedgesM, yedgesM, np.ma.masked_less_equal(zM_plot, 0.0), shading='auto', norm=norm)
    else:
        pcmV = axV.pcolormesh(xedgesV, yedgesV, zV_plot, shading='auto')
        pcmM = axM.pcolormesh(xedgesM, yedgesM, zM_plot, shading='auto')

    for ax in (axV, axM, axR):
        ax.set_xlim(float(xedges[0]), float(xedges[-1]))
        ax.set_ylim(float(yedges[0]), float(yedges[-1]))
        ax.set_xlabel(r'$|\Delta\varphi|$ [rad]')
    axV.set_ylabel(r'$|\Delta\eta|$')

    _set_wrapped_ax_title(axV, f"{label_vac}", max_chars=54, pad_single=5.0, pad_wrapped=8.5)
    _set_wrapped_ax_title(axM, f"{label_med}", max_chars=54, pad_single=5.0, pad_wrapped=8.5)
    cbar_vm = fig.colorbar(pcmM, ax=[axV, axM], shrink=0.88, pad=0.02)
    cbar_vm.set_label(r'$d^2\sigma_{\mathrm{dijet}}/(d|\Delta\varphi|\,d|\Delta\eta|)$ [mb/rad]')

    if same_binning:
        if (ratio_mode or 'med').strip().lower() == 'inv':
            num = np.asarray(zV, dtype=float)
            den = np.asarray(zM, dtype=float)
            ratio_title = f"{label_vac}/{label_med}"
        else:
            num = np.asarray(zM, dtype=float)
            den = np.asarray(zV, dtype=float)
            ratio_title = f"{label_med}/{label_vac}"
        ratio = np.full_like(num, np.nan, dtype=float)
        mask = np.isfinite(num) & np.isfinite(den) & (num > 0) & (den > 0)
        ratio[mask] = num[mask] / den[mask]
        ratio_plot = ratio.T
        finite_ratio = ratio_plot[np.isfinite(ratio_plot)]
        if finite_ratio.size > 0:
            pcmR = axR.pcolormesh(xedges, yedges, np.ma.masked_invalid(ratio_plot), shading='auto')
            cbar_r = fig.colorbar(pcmR, ax=axR, shrink=0.88, pad=0.02)
            cbar_r.set_label(ratio_title)
        else:
            axR.text(0.5, 0.5, 'No valid ratio bins', transform=axR.transAxes, ha='center', va='center', fontsize=_FONTS['note'])
        _set_wrapped_ax_title(axR, f"{ratio_title}", max_chars=48, pad_single=5.0, pad_wrapped=8.0)
    else:
        axR.text(0.5, 0.5, 'Binning mismatch: ratio omitted', transform=axR.transAxes, ha='center', va='center', fontsize=_FONTS['note'])
        _set_wrapped_ax_title(axR, 'Ratio unavailable', max_chars=48, pad_single=5.0, pad_wrapped=8.0)

    wrapped_suptitle = _set_paperready_caption(fig, 'Dijet azimuthal decorrelation |Δφ| vs |Δη| comparison map' + _pair_title_bracket(Rv, hn, include_ystar=True, include_ptlead=True), max_chars=118)
    _safe_tight_layout(fig, rect=[0, 0, 1, _suptitle_rect_top(wrapped_suptitle, top_single=0.955, top_wrapped=0.89)])
    _save_figure(fig, os.path.join(out_dir, f"{hn}_compare.png"), dpi=170)
    plt.close(fig)


def plot_jetpt_overlay(
    kind: str,
    R: float,
    hnA: str,
    hnB: str,
    A: Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float],
    B: Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float],
    labelA: str,
    labelB: str,
    out_dir: str,
    ms: float,
    *,
    use_perdijet: bool = False,
    is_inclusive: bool = False,
    ratio_mode: str = 'med',
    run_tag_a: Optional[str] = None,
    run_tag_b: Optional[str] = None,
) -> None:
    """Overlay jet pT spectra for the two runs on log-y axes, with the compare ratio below."""
    xcA, yA, eA, bwA, _ = A
    xcB, yB, eB, bwB, _ = B

    countA = countB = None
    labelA_plot = labelA
    labelB_plot = labelB

    if use_perdijet:
        fname = f"jetpt_{kind}_R{int(round(R*100)):03d}_overlay_unitshape.png" if is_inclusive else f"jetpt_{kind}_R{int(round(R*100)):03d}_overlay_perdijet.png"
        if is_inclusive:
            title_core = f"Jet pT comparison ({kind}, unit-normalized shape)" + _pair_title_bracket(R, hnA, include_ystar=(kind != 'incl'), include_branch=(kind != 'incl'))
            ylabel = r"$(1/\sigma_{\mathrm{incl}})\,d\sigma/dp_T$ (1/GeV)"
        else:
            if SINGLE_SLICE_MODE:
                countA = SELECTED_DIJET_COUNTS_A.count_for("sel", R, is_nosubfrac=hnA.endswith('_nosubfrac'))
                countB = SELECTED_DIJET_COUNTS_B.count_for("sel", R, is_nosubfrac=hnB.endswith('_nosubfrac'))
                title_core = f"Jet pT comparison ({kind}, single-slice count normalized)" + _pair_title_bracket(R, hnA, include_ystar=True, include_branch=True)
                ylabel = _single_slice_norm_ylabel("sel")
                if not (_selected_count_is_positive(countA) and _selected_count_is_positive(countB)):
                    out_path = os.path.join(out_dir, fname)
                    reason = _selected_count_skip_reason(labelA, countA, labelB, countB, f"jet pT ({kind})")
                    _log(f"[WARN] jetpt {kind} R={R:.2f}: {reason.replace(chr(10), ' | ')}; writing placeholder: {out_path}")
                    _write_unavailable_placeholder(
                        out_path,
                        title=f"Jet pT comparison skipped ({kind})" + _pair_title_bracket(R, hnA, include_ystar=True, include_branch=True),
                        reason=reason,
                        ylabel=ylabel,
                    )
                    return
                labelA_plot = _legend_count_label(labelA, "sel", countA)
                labelB_plot = _legend_count_label(labelB, "sel", countB)
            else:
                title_core = f"Jet pT comparison ({kind}, per-selection normalized)" + _pair_title_bracket(R, hnA, include_ystar=True, include_branch=True)
                ylabel = r"$(1/\sigma_{\mathrm{sel}})\,d\sigma/dp_T$ (1/GeV)"
        if SINGLE_SLICE_MODE and not is_inclusive:
            sigA, yA_plot, eA_plot = normalize_by_selected_dijet_count(yA, eA, countA)
            sigB, yB_plot, eB_plot = normalize_by_selected_dijet_count(yB, eB, countB)
            fail_label = "selected-count"
        else:
            sigA, yA_plot, eA_plot = normalize_per_dijet_with_cov(yA, eA, bwA, denom_positive_only=False, cov_mode=PERDIJET_COV_MODE)
            sigB, yB_plot, eB_plot = normalize_per_dijet_with_cov(yB, eB, bwB, denom_positive_only=False, cov_mode=PERDIJET_COV_MODE)
            fail_label = "per-selection"
        if yA_plot is None or eA_plot is None or yB_plot is None or eB_plot is None:
            _log(f"[WARN] jetpt {kind} R={R:.2f}: {fail_label} normalization failed; skipping overlay")
            return
    else:
        sigA = sigB = float('nan')
        normA = xsec_norm_term_for_hist(XSEC_BAND_A, hnA, xcA, bwA)
        normB = xsec_norm_term_for_hist(XSEC_BAND_B, hnB, xcB, bwB)
        yA_plot, eA_plot = yA, yerr_for_plot_absolute(yA, eA, normA)
        yB_plot, eB_plot = yB, yerr_for_plot_absolute(yB, eB, normB)
        title_core = f"Jet pT comparison ({kind}, absolute overlay)" + _pair_title_bracket(R, hnA, include_ystar=(kind != 'incl'), include_branch=(kind != 'incl'))
        ylabel = r"$d\sigma/dp_T$ (mb/GeV)"
        fname = f"jetpt_{kind}_R{int(round(R*100)):03d}_overlay.png"

    if use_perdijet:
        mA = np.isfinite(xcA) & np.isfinite(yA_plot) & (xcA > 0) & (yA_plot > 0)
        mB = np.isfinite(xcB) & np.isfinite(yB_plot) & (xcB > 0) & (yB_plot > 0)
    else:
        mA = np.isfinite(xcA) & np.isfinite(yA_plot) & np.isfinite(eA_plot) & (xcA > 0) & (yA_plot > 0)
        mB = np.isfinite(xcB) & np.isfinite(yB_plot) & np.isfinite(eB_plot) & (xcB > 0) & (yB_plot > 0)
    if not (np.any(mA) or np.any(mB)):
        _log(f"[WARN] jetpt {kind} R={R:.2f}: no positive bins to plot")
        return

    fig, (ax, axr) = plt.subplots(
        2, 1, figsize=(9, 8.5), sharex=True,
        gridspec_kw=dict(height_ratios=[1.0, 0.58], hspace=0.05)
    )
    ax.set_xscale("log")
    ax.set_yscale("log")
    axr.set_xscale("log")

    x_min, x_max = _pt_xrange_from_nonzero(
        np.concatenate([xcA[mA] if np.any(mA) else np.array([]), xcB[mB] if np.any(mB) else np.array([])]),
        np.concatenate([yA_plot[mA] if np.any(mA) else np.array([]), yB_plot[mB] if np.any(mB) else np.array([])]),
        np.concatenate([bwA[mA] if np.any(mA) else np.array([]), bwB[mB] if np.any(mB) else np.array([])]),
        x_floor=1.0,
        x_ceil=(JET_PT_MAX_CFG if np.isfinite(JET_PT_MAX_CFG) and JET_PT_MAX_CFG > 1.0 else None),
    )
    ax.set_xlim(x_min, x_max)
    _log(f"[jetpt-zoom][compare][overlay] kind={kind} R={R:.2f} inclusive={int(is_inclusive)} perdijet={int(use_perdijet)} xlim={_format_xlim_for_log(x_min, x_max)}")

    ymin, ymax = _log_ylim_from_positive([yA_plot[mA] if np.any(mA) else None, yB_plot[mB] if np.any(mB) else None])
    ax.set_ylim(ymin, ymax)

    if np.any(mA):
        if use_perdijet:
            errorbar_nan_safe_log(ax, xcA[mA], yA_plot[mA], eA_plot[mA], fmt="o", ms=ms, lw=0.8, capsize=2, label=labelA_plot, color=COMPARE_COLOR_A)
        else:
            ax.errorbar(
                xcA[mA],
                yA_plot[mA],
                yerr=_asym_yerr_for_log(yA_plot[mA], eA_plot[mA]),
                fmt="o",
                ms=ms,
                lw=0.8,
                capsize=2,
                color=COMPARE_COLOR_A,
                label=labelA_plot,
            )
    if np.any(mB):
        if use_perdijet:
            errorbar_nan_safe_log(ax, xcB[mB], yB_plot[mB], eB_plot[mB], fmt="s", ms=ms, lw=0.8, capsize=2, label=labelB_plot, color='tab:red')
        else:
            ax.errorbar(
                xcB[mB],
                yB_plot[mB],
                yerr=_asym_yerr_for_log(yB_plot[mB], eB_plot[mB]),
                fmt="s",
                ms=ms,
                lw=0.8,
                capsize=2,
                color='tab:red',
                label=labelB_plot,
            )

    ax.set_ylabel(ylabel)
    wrapped_title = _set_paperready_caption(fig, title_core, max_chars=118)
    if use_perdijet and np.isfinite(sigA) and np.isfinite(sigB):
        if SINGLE_SLICE_MODE and not is_inclusive and countA is not None and countB is not None:
            note_text = f"N_dijet,sel^A={int(countA)}\nN_dijet,sel^B={int(countB)}"
        else:
            sig_label = 'incl' if is_inclusive else 'sel'
            note_text = rf"$\sigma_{{\mathrm{{{sig_label}}}}}^A$={sigA:.3e} mb\n$\sigma_{{\mathrm{{{sig_label}}}}}^B$={sigB:.3e} mb"
        ax.text(
            0.98, 0.98,
            note_text,
            transform=ax.transAxes, va='top', ha='right', fontsize=_FONTS['note'],
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.85, edgecolor='black')
        )
    _add_autozoom_note(ax)
    ax.legend(loc="best", frameon=False)

    bin_match = (
        len(xcA) == len(xcB)
        and np.allclose(xcA, xcB, rtol=0, atol=1e-9)
        and np.allclose(bwA, bwB, rtol=0, atol=1e-9)
    )
    ratio_num_key, _ratio_den_key, ratio_label = _resolve_ratio_order(
        ratio_mode,
        labelA,
        labelB,
        run_tag_a=run_tag_a,
        run_tag_b=run_tag_b,
    )
    if bin_match:
        if ratio_num_key == 'A':
            num_y, num_e = yA_plot, eA_plot
            den_y, den_e = yB_plot, eB_plot
        else:
            num_y, num_e = yB_plot, eB_plot
            den_y, den_e = yA_plot, eA_plot
        r, er, m_plot, _m_err = _ratio_with_optional_errors(num_y, num_e, den_y, den_e)
        if np.any(m_plot):
            errorbar_nan_safe(axr, xcA[m_plot], r[m_plot], er[m_plot], fmt='o', ms=ms, lw=0.8, capsize=2, label=ratio_label, color='tab:red')
            _apply_configured_ratio_ylim(axr, 'JETPT', r[m_plot], er[m_plot], context=f'{hnA}|{hnB}')
            axr.legend(loc='best', frameon=False)
        else:
            axr.text(0.5, 0.5, 'ratio unavailable', transform=axr.transAxes, ha='center', va='center', fontsize=_FONTS['note'])
    else:
        axr.text(0.5, 0.5, 'ratio unavailable (binning mismatch)', transform=axr.transAxes, ha='center', va='center', fontsize=_FONTS['note'])

    axr.axhline(1.0, color="k", ls='--', lw=1)
    axr.set_ylabel('ratio')
    axr.set_xlabel(r"$p_T$ (GeV)")
    _add_autozoom_note(axr)

    out_path = os.path.join(out_dir, fname)
    _safe_tight_layout(fig, rect=[0, 0, 1, _ax_title_rect_top(wrapped_title, top_single=0.98, top_wrapped=0.93)])
    _save_figure(fig, out_path, dpi=170)
    plt.close(fig)


def plot_ln_jetpt_overlay(
    kind: str,
    R: float,
    hnA: str,
    hnB: str,
    A: Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float],
    B: Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float],
    labelA: str,
    labelB: str,
    out_dir: str,
    ms: float,
) -> None:
    """Retired diagnostic: ln(dσ/dp_T) is dimensionful and is no longer plotted."""
    _log(
        f"[INFO] Retired diagnostic skipped: ln(dσ/dp_T) jet-spectrum overlay for kind={kind}, R={R:.2f}. "
        f"Use the standard absolute/unit-shape overlays and ratio plots instead."
    )
    return


def plot_jetpt_ratio(
    kind: str,
    R: float,
    numerator: Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float],
    denominator: Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float],
    ratio_label: str,
    out_dir: str,
    ms: float,
    *,
    hn_num: str,
    hn_den: str,
    xsec_band_num=None,
    xsec_band_den=None,
) -> None:
    """Plot ONE ratio curve: numerator/denominator with downstream-only propagated uncertainties."""
    xcN, yN, eN, bwN, _ = numerator
    xcD, yD, eD, bwD, _ = denominator

    if len(xcN) != len(xcD) or not np.allclose(xcN, xcD, rtol=0, atol=1e-9) or not np.allclose(bwN, bwD, rtol=0, atol=1e-9):
        _log(f"[WARN] jetpt {kind} R={R:.2f}: binning mismatch, skipping ratio")
        return

    eN_plot = yerr_for_plot_absolute(yN, eN, xsec_norm_term_for_hist(xsec_band_num, hn_num, xcN, bwN))
    eD_plot = yerr_for_plot_absolute(yD, eD, xsec_norm_term_for_hist(xsec_band_den, hn_den, xcD, bwD))

    r, er, m_plot, _m_err = _ratio_with_optional_errors(yN, eN_plot, yD, eD_plot)
    m_plot = m_plot & np.isfinite(xcN)
    if not np.any(m_plot):
        _log(f"[WARN] jetpt {kind} R={R:.2f}: no bins with positive numerator/denominator for ratio")
        return

    fig, ax = plt.subplots(figsize=(9, 6.5))
    ax.axhline(1.0, color="k", ls="--", lw=1)
    ax.set_xscale("log")
    errorbar_nan_safe(ax, xcN[m_plot], r[m_plot], er[m_plot], fmt="o", ms=ms, lw=0.8, capsize=2, label=ratio_label)

    x_min, x_max = _pt_xrange_from_nonzero(
        xcN[m_plot],
        np.ones_like(xcN[m_plot], dtype=float),
        bwN[m_plot],
        x_floor=1.0,
        x_ceil=(JET_PT_MAX_CFG if np.isfinite(JET_PT_MAX_CFG) and JET_PT_MAX_CFG > 1.0 else None),
    )
    if np.isfinite(x_min) and np.isfinite(x_max) and x_max > x_min:
        ax.set_xlim(x_min, x_max)
        _log(f"[jetpt-zoom][compare][ratio] kind={kind} R={R:.2f} xlim={_format_xlim_for_log(x_min, x_max)}")
    _apply_configured_ratio_ylim(ax, 'JETPT', r[m_plot], er[m_plot], context=f'{hn_num}|{hn_den}')

    ax.set_xlabel(r"$p_T$ (GeV)")
    ax.set_ylabel("ratio")
    if kind == "incl":
        title_suffix = _title_bracket([f"R={R:.2f}"])
    else:
        title_suffix = _pair_title_bracket(R, hn_num, include_ystar=True, include_branch=True)
    wrapped_title = _set_paperready_caption(fig, f"Jet spectrum ratio ({kind})" + title_suffix, max_chars=118)
    _add_autozoom_note(ax)
    ax.legend(loc="best", frameon=False)

    out_path = os.path.join(out_dir, f"ratio_jetpt_{kind}_R{int(round(R*100)):03d}.png")
    _safe_tight_layout(fig, rect=[0, 0, 1, _ax_title_rect_top(wrapped_title, top_single=0.98, top_wrapped=0.93)])
    _save_figure(fig, out_path, dpi=170)
    plt.close(fig)



def _wrap_delta_pi(x: np.ndarray) -> np.ndarray:
    """Return |Δφ-π| wrapped to [0,π]."""
    return np.abs(np.arctan2(np.sin(x - np.pi), np.cos(x - np.pi)))


def _pdf_stats(xc: np.ndarray, y: np.ndarray, bw: np.ndarray):
    """Return (mean, RMS) for a binned PDF y(x) with bin widths bw.

    NOTE: y can contain small negative bins when it comes from covariance-aware
    per-selection normalization. The physically meaningful PDF is non-negative,
    but we prefer a signed-weight estimator for stability and consistency with
    fitter v4.9.34. If the signed total weight is non-positive, fall back to a
    clipped (non-negative) estimator and log a warning.
    """
    s = y * bw
    S = float(np.nansum(s))

    use_clipped = False
    if not (np.isfinite(S) and S > 0):
        s_pos = np.where(np.isfinite(s), np.maximum(0.0, s), np.nan)
        S_pos = float(np.nansum(s_pos))
        if not (np.isfinite(S_pos) and S_pos > 0):
            return (float('nan'), float('nan'))
        s = s_pos
        S = S_pos
        use_clipped = True

    if use_clipped:
        _log("[WARN] _pdf_stats: signed total weight <= 0; falling back to clipped (non-negative) weights for mean/RMS.")

    mu = float(np.nansum(s * xc) / S)
    var = float(np.nansum(s * (xc - mu) ** 2) / S)
    return (mu, math.sqrt(max(0.0, var)))


def _dphi_broadening_metrics(xc: np.ndarray, y_pdf: np.ndarray, bw: np.ndarray, *, peak_window_rad: float = 0.6):
    """Return (sigma_peak, tail_frac) using δ=|Δφ-π|.

    Uses signed weights by default (consistent with fitter v4.9.34). If the
    signed total weight is non-positive, falls back to clipped weights and logs
    a warning. Tail fraction is always computed from non-negative weights.
    """
    delta = _wrap_delta_pi(xc)
    s_signed = y_pdf * bw
    S_signed = float(np.nansum(s_signed))

    # Prepare a non-negative version for tail fraction (and for fallback)
    s_pos = np.where(np.isfinite(s_signed), np.maximum(0.0, s_signed), np.nan)
    S_pos = float(np.nansum(s_pos))
    if not (np.isfinite(S_pos) and S_pos > 0):
        return (float('nan'), float('nan'))

    # For sigma_peak: prefer signed if it is well-defined; else use clipped.
    use_clipped_for_sigma = not (np.isfinite(S_signed) and S_signed > 0)
    s_for_sigma = s_pos if use_clipped_for_sigma else s_signed

    if use_clipped_for_sigma:
        _log("[WARN] _dphi_broadening_metrics: signed total weight <= 0; using clipped (non-negative) weights for sigma_peak.")

    m = np.isfinite(delta) & np.isfinite(s_for_sigma) & np.isfinite(s_pos)
    if not np.any(m):
        return (float('nan'), float('nan'))

    delta_m = delta[m]
    s_m_sigma = s_for_sigma[m]
    s_m_pos = s_pos[m]
    S_m_pos = float(np.nansum(s_m_pos))
    if S_m_pos <= 0:
        return (float('nan'), float('nan'))

    win = delta_m <= peak_window_rad
    # Tail fraction must be computed from non-negative weights.
    S_win_pos = float(np.nansum(s_m_pos[win]))
    tail = max(0.0, 1.0 - (S_win_pos / S_m_pos))

    # For sigma_peak, use the chosen estimator (signed when possible; else clipped).
    S_win_sigma = float(np.nansum(s_m_sigma[win]))
    if S_win_sigma <= 0:
        return (float('nan'), tail)

    mu = float(np.nansum(s_m_sigma[win] * delta_m[win]) / S_win_sigma)
    var = float(np.nansum(s_m_sigma[win] * (delta_m[win] - mu) ** 2) / S_win_sigma)
    return (math.sqrt(max(0.0, var)), tail)


def _title_branch_tag(hn: str, *, include_subfrac: bool = False) -> str:
    if isinstance(hn, str) and hn.endswith('_nosubfrac'):
        return ' [nosubfrac]'
    return ' [subfrac]' if include_subfrac else ''


def _ystar_text_from_cfg(ini: Optional[Dict[str, str]]) -> str:
    if not isinstance(ini, dict):
        return ''
    try:
        ystar_enable = int(str(ini.get('YSTAR_ENABLE', '0')).strip() or '0')
    except Exception:
        ystar_enable = 0
    if ystar_enable != 1:
        return ''
    try:
        ystar_max = float(ini.get('YSTAR_MAX', 'nan'))
    except Exception:
        ystar_max = float('nan')
    if math.isfinite(ystar_max) and ystar_max > 0:
        return rf"$|y^*|<{ystar_max:.2f}$"
    return ''


def _parse_exact_two_jets_required(ini: Dict[str, str]) -> bool:
    raw = '' if not isinstance(ini, dict) else str(ini.get('DIJET_REQUIRE_EXACTLY_TWO_JETS', '') or '').strip()
    if raw == '':
        raise ValueError("jetscape.ini missing required key DIJET_REQUIRE_EXACTLY_TWO_JETS")
    if raw not in ('0', '1'):
        raise ValueError(f"Invalid DIJET_REQUIRE_EXACTLY_TWO_JETS={raw!r}; expected 0 or 1")
    return raw == '1'


def _exact_two_text_from_cfg(ini: Optional[Dict[str, str]]) -> str:
    global EXACT_TWO_JETS_REQUIRED
    if isinstance(ini, dict):
        try:
            if _parse_exact_two_jets_required(ini):
                return 'exactly 2 accepted jets'
            return ''
        except Exception:
            pass
    return 'exactly 2 accepted jets' if EXACT_TWO_JETS_REQUIRED else ''


def _imbalance_backtoback_text_from_cfg(ini: Optional[Dict[str, str]]) -> str:
    global IMBALANCE_REQUIRE_BACKTOBACK, IMBALANCE_BACKTOBACK_TOL_DEG
    if isinstance(ini, dict):
        raw_req = str(ini.get('IMBALANCE_REQUIRE_BACKTOBACK', '') or '').strip()
        raw_tol = str(ini.get('IMBALANCE_BACKTOBACK_TOL_DEG', '') or '').strip()
        if raw_req != '':
            try:
                req_val = int(float(raw_req))
                if req_val not in (0, 1):
                    raise ValueError
                if req_val == 0:
                    return ''
                tol_val = float(raw_tol)
                if not math.isfinite(tol_val) or tol_val <= 0.0 or tol_val > 180.0:
                    raise ValueError
                return rf"$|\Delta\varphi-\pi|\leq {tol_val:.0f}^\circ$"
            except Exception:
                pass
    if IMBALANCE_REQUIRE_BACKTOBACK and math.isfinite(IMBALANCE_BACKTOBACK_TOL_DEG):
        return rf"$|\Delta\varphi-\pi|\leq {IMBALANCE_BACKTOBACK_TOL_DEG:.0f}^\circ$"
    return ''


def _title_bracket(parts: List[str]) -> str:
    parts = [str(p) for p in parts if isinstance(p, str) and str(p).strip()]
    return f" [{'; '.join(parts)}]" if parts else ''


def _pair_title_bracket(R: float, hn: str, *, include_ystar: bool, include_ptlead: bool = False, include_branch: bool = True, include_imbalance_backtoback: bool = False) -> str:
    parts: List[str] = [f'R={float(R):.2f}']
    if include_ptlead:
        parts.append(f'lead pT {_pt_label_from_hist_name(hn)}')
    exact2 = _exact_two_text_from_cfg(CFG_FOR_TITLES)
    if exact2:
        parts.append(exact2)
    if include_ystar:
        ytxt = _ystar_text_from_cfg(CFG_FOR_TITLES)
        if ytxt:
            parts.append(ytxt)
    if include_imbalance_backtoback:
        imb_txt = _imbalance_backtoback_text_from_cfg(CFG_FOR_TITLES)
        if imb_txt:
            parts.append(imb_txt)
    return _title_bracket(parts) + (_title_branch_tag(hn, include_subfrac=True) if include_branch else '')


def _dphi_ylabel(hn: str, using_norm: bool) -> str:
    """Return fitter-consistent y-axis label for Δφ comparison histograms."""
    is_abs = hn.startswith("dphi_abs_")
    if using_norm:
        if SINGLE_SLICE_MODE:
            return _single_slice_norm_ylabel("dphi", is_abs=is_abs)
        if is_abs:
            return r"$(1/\sigma_{\mathrm{sel}})\,d\sigma/d|\Delta\varphi|$ (1/rad)"
        return r"$(1/\sigma_{\mathrm{sel}})\,d\sigma/d\Delta\varphi$ (1/rad)"
    if is_abs:
        return r"$d\sigma_{\mathrm{dijet}}/d|\Delta\varphi|$ (mb/rad)"
    return r"$d\sigma_{\mathrm{dijet}}/d\Delta\varphi$ (mb/rad)"

def _dphi_selection_text(ini: Dict[str, str], R: float, hn: str) -> str:
    """Build a compact, paper-style selection annotation for Δφ plots.

    Includes |η_jet| acceptance (with optional cone containment), optional |y*| cut if enabled,
    and a clear nosubfrac tag when plotting the *_nosubfrac branch.
    """
    parts: List[str] = []

    # Jet η acceptance
    try:
        eta_max = float(ini.get('JET_ETA_MAX', 'nan'))
    except Exception:
        eta_max = float('nan')
    try:
        eta_mode = int(str(ini.get('JET_ETA_MODE', '0')).strip() or '0')
    except Exception:
        eta_mode = 0

    if math.isfinite(eta_max) and eta_max > 0:
        eta_eff = eta_max - float(R) if eta_mode == 1 else eta_max
        if eta_eff > 0:
            parts.append(rf"$|\eta_\mathrm{{jet}}|<{eta_eff:.2f}$")
        else:
            # If someone sets eta_max <= R, don't print nonsense.
            parts.append(rf"$|\eta_\mathrm{{jet}}|<{eta_max:.2f}$")

    exact2 = _exact_two_text_from_cfg(ini)
    if exact2:
        parts.append(exact2)

    # Optional |y*| cut for dijet-pair observables when enabled in the analyzer via jetscape.ini)
    try:
        ystar_enable = int(str(ini.get('YSTAR_ENABLE', '0')).strip() or '0')
    except Exception:
        ystar_enable = 0
    if ystar_enable == 1:
        try:
            ystar_max = float(ini.get('YSTAR_MAX', 'nan'))
        except Exception:
            ystar_max = float('nan')
        if math.isfinite(ystar_max) and ystar_max > 0:
            parts.append(rf"$|y^*|<{ystar_max:.2f}$")

    if hn.endswith('_nosubfrac'):
        parts.append("[nosubfrac]")

    return "; ".join(parts)

def plot_dphi_stacked(
    hn: str,
    vac: Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float],
    brick: Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float],
    label_vac: str,
    label_brick: str,
    out_dir: str,
    *,
    xsec_band_vac=None,
    xsec_band_brick=None,
    ini: Dict[str, str] = None,
    ratio_mode: str = 'med',
    ms: float = 3.0,
    use_perdijet: bool = True,
    count_vac: int = None,
    count_brick: int = None,
) -> None:
    """Vacuum (top), brick (middle), ratio (bottom).

    If use_perdijet=True, SINGLE_SLICE_MODE uses y/N_dijet,sel; multi-slice mode uses legacy shape/per-selection normalization.
    If use_perdijet=False, plots are absolute (mb/rad) so rate suppression/enhancement is visible.
    """
    ini = ini or {}
    xcV, yV, eV, bwV, _ = vac
    xcB, yB, eB, bwB, _ = brick

    out_path = os.path.join(out_dir, f"{hn}_stacked.png")
    if use_perdijet and SINGLE_SLICE_MODE and (count_vac is not None or count_brick is not None):
        if not (_selected_count_is_positive(count_vac) and _selected_count_is_positive(count_brick)):
            obs_label = "|Δφ|" if hn.startswith("dphi_abs_") else "Δφ"
            reason = _selected_count_skip_reason(label_vac, count_vac, label_brick, count_brick, obs_label)
            _log(f"[WARN] {hn}: {reason.replace(chr(10), ' | ')}; writing placeholder: {out_path}")
            _write_unavailable_placeholder(
                out_path,
                title=f"Dijet azimuthal decorrelation comparison skipped [{hn}]",
                reason=reason,
                ylabel=_single_slice_norm_ylabel("dphi", is_abs=hn.startswith("dphi_abs_")),
            )
            return

    bin_match = (
        len(xcV) == len(xcB)
        and np.allclose(xcV, xcB, rtol=0, atol=1e-9)
        and np.allclose(bwV, bwB, rtol=0, atol=1e-9)
    )

    yVn = eVn = yBn = eBn = None
    using_norm = False
    if use_perdijet:
        if SINGLE_SLICE_MODE:
            _, yVn, eVn = normalize_by_selected_dijet_count(yV, eV, count_vac)
            _, yBn, eBn = normalize_by_selected_dijet_count(yB, eB, count_brick)
        else:
            _, yVn, eVn = normalize_per_dijet_with_cov(yV, eV, bwV, denom_positive_only=False, cov_mode=PERDIJET_COV_MODE)
            _, yBn, eBn = normalize_per_dijet_with_cov(yB, eB, bwB, denom_positive_only=False, cov_mode=PERDIJET_COV_MODE)
        using_norm = ((yVn is not None) and (yBn is not None))

    if using_norm:
        yVplot, eVplot = yVn, eVn
        yBplot, eBplot = yBn, eBn
    else:
        yVplot = yV
        yBplot = yB
        eVplot = yerr_for_plot_absolute(yV, eV, xsec_norm_term_for_hist(xsec_band_vac, hn, xcV, bwV))
        eBplot = yerr_for_plot_absolute(yB, eB, xsec_norm_term_for_hist(xsec_band_brick, hn, xcB, bwB))

    spV, tailV = _dphi_broadening_metrics(xcV, yVplot, bwV)
    spB, tailB = _dphi_broadening_metrics(xcB, yBplot, bwB)

    fig, (ax1, ax2, ax3) = plt.subplots(
        3, 1, figsize=(9.5, 9.5), sharex=True,
        gridspec_kw=dict(height_ratios=[1.0, 1.0, 0.7], hspace=0.05)
    )

    errorbar_nan_safe(ax1, xcV, yVplot, eVplot, fmt='o', ms=ms, lw=0.8, capsize=2, label=(_legend_count_label(label_vac, 'dphi', count_vac, is_abs=hn.startswith('dphi_abs_')) if (SINGLE_SLICE_MODE and count_vac is not None and using_norm) else label_vac), color=COMPARE_COLOR_A)
    ax1.set_ylabel(_dphi_ylabel(hn, using_norm))
    if not hn.startswith("dphi_abs_"):
        ax1.axvline(np.pi, color='k', ls='--', lw=1)
    ax1.legend(loc='upper left', frameon=False)
    ax1.text(0.98, 0.92, f"σ_peak≈{spV:.4f} rad\n tail≈{tailV:.3f}", transform=ax1.transAxes,
             ha='right', va='top', fontsize=_FONTS['note'],
             bbox=dict(boxstyle='round,pad=0.25', facecolor='white', alpha=0.85, edgecolor='black'))

    errorbar_nan_safe(ax2, xcB, yBplot, eBplot, fmt='o', ms=ms, lw=0.8, capsize=2, label=(_legend_count_label(label_brick, 'dphi', count_brick, is_abs=hn.startswith('dphi_abs_')) if (SINGLE_SLICE_MODE and count_brick is not None and using_norm) else label_brick), color=COMPARE_COLOR_B)
    ax2.set_ylabel(_dphi_ylabel(hn, using_norm))
    if not hn.startswith("dphi_abs_"):
        ax2.axvline(np.pi, color='k', ls='--', lw=1)
    ax2.legend(loc='upper left', frameon=False)
    ax2.text(0.98, 0.92, f"σ_peak≈{spB:.4f} rad\n tail≈{tailB:.3f}", transform=ax2.transAxes,
             ha='right', va='top', fontsize=_FONTS['note'],
             bbox=dict(boxstyle='round,pad=0.25', facecolor='white', alpha=0.85, edgecolor='black'))

    ratio_rebin_note = ''
    if bin_match:
        if ratio_mode == 'inv':
            num_xc, num_y, num_e, num_bw = xcV, yVplot, eVplot, bwV
            den_xc, den_y, den_e, den_bw = xcB, yBplot, eBplot, bwB
            rlab = f"{label_vac}/{label_brick}"
        else:
            num_xc, num_y, num_e, num_bw = xcB, yBplot, eBplot, bwB
            den_xc, den_y, den_e, den_bw = xcV, yVplot, eVplot, bwV
            rlab = f"{label_brick}/{label_vac}"

        ratio_x = xcV
        rebin_factor = _dphi_ratio_rebin_factor_for_hist(hn)
        if rebin_factor > 1:
            num_xc_rb, num_y_rb, num_e_rb, num_bw_rb, num_did = _rebin_hist_density_for_ratio(num_xc, num_y, num_e, num_bw, rebin_factor, hist_name=hn, observable_label='dphi')
            den_xc_rb, den_y_rb, den_e_rb, den_bw_rb, den_did = _rebin_hist_density_for_ratio(den_xc, den_y, den_e, den_bw, rebin_factor, hist_name=hn, observable_label='dphi')
            if num_did and den_did and len(num_xc_rb) == len(den_xc_rb) and np.allclose(num_xc_rb, den_xc_rb, rtol=0, atol=1e-9) and np.allclose(num_bw_rb, den_bw_rb, rtol=0, atol=1e-9):
                num_y, num_e = num_y_rb, num_e_rb
                den_y, den_e = den_y_rb, den_e_rb
                ratio_x = num_xc_rb
                ratio_rebin_note = _ratio_rebin_note(hn)
            else:
                _log(f"[WARN] {hn}: ratio-only Δφ rebin requested (factor={rebin_factor}) but rebinned numerator/denominator no longer match; keeping original bins")

        r, er, m_plot, _m_err = _ratio_with_optional_errors(num_y, num_e, den_y, den_e)
        if np.any(m_plot):
            errorbar_nan_safe(ax3, ratio_x[m_plot], r[m_plot], er[m_plot], fmt='o', ms=ms, lw=0.8, capsize=2, color='tab:red', label=rlab)
            _apply_configured_ratio_ylim(ax3, ('DPHI_ABS' if hn.startswith('dphi_abs_') else 'DPHI'), r[m_plot], er[m_plot], context=hn)
            ax3.legend(loc='best', frameon=False)
        else:
            ax3.text(0.5, 0.5, 'ratio unavailable', transform=ax3.transAxes, ha='center', va='center', fontsize=_FONTS['note'])
    else:
        ax3.text(0.5, 0.5, 'ratio unavailable (binning mismatch)', transform=ax3.transAxes, ha='center', va='center', fontsize=_FONTS['note'])

    ax3.axhline(1.0, color='k', ls='--', lw=1)
    ax3.set_xlabel((r"$|\Delta\varphi|$ (rad)" if hn.startswith("dphi_abs_") else r"$\Delta\varphi$ (rad)"))
    ax3.set_ylabel('ratio')

    base_title = r"Dijet azimuthal decorrelation $|\Delta\varphi|$ comparison" if hn.startswith("dphi_abs_") else r"Dijet azimuthal decorrelation $\Delta\varphi$ comparison ($0\leq \Delta\varphi < 2\pi$)"
    tag = parse_dphi_abs_name(hn) if hn.startswith("dphi_abs_") else parse_dphi_name(hn)
    suffix = (("single-slice count normalized" if SINGLE_SLICE_MODE else "per-selection normalized") if using_norm else "absolute")
    if tag:
        Rv, lo, hi, isAll = tag
        pt_lbl = _pt_label(lo, hi, isAll)
        sel_txt = _dphi_selection_text(ini, Rv, hn)
        sel_part = f"  [{sel_txt}]" if sel_txt else ""
        wrapped_suptitle = _set_paperready_caption(fig, f"{base_title} ({suffix})  [R={Rv:.2f}; lead pT {pt_lbl}]{sel_part}", max_chars=118)
    else:
        sel_txt = _dphi_selection_text(ini, float('nan'), hn)
        sel_part = f"  [{sel_txt}]" if sel_txt else ""
        wrapped_suptitle = _set_paperready_caption(fig, f"{base_title} ({suffix}): {hn}{sel_part}", max_chars=118)

    _safe_tight_layout(fig, rect=[0, 0, 1, _suptitle_rect_top(wrapped_suptitle, top_single=0.97, top_wrapped=0.92)])
    _save_figure(fig, out_path, dpi=170)
    plt.close(fig)


def plot_imbalance_stacked(
    hn: str,
    vac: Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float],
    brick: Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float],
    label_vac: str,
    label_brick: str,
    out_dir: str,
    *,
    xsec_band_vac=None,
    xsec_band_brick=None,
    ratio_mode: str = 'med',
    ms: float = 3.0,
    use_perdijet: bool = True,
    count_vac: int = None,
    count_brick: int = None,
) -> None:
    """Comparison plots for xJ/AJ.

    - If use_perdijet=True, SINGLE_SLICE_MODE uses y/N_dijet,sel; multi-slice mode uses legacy shape/per-selection normalization.
    - If use_perdijet=False, plots are absolute (mb) so rate effects are visible.

    CHANGE (v4.1):
      • Absolute comparisons are now a single-axis overlay (vacuum+brick) with NO ratio panel.
      • Per-dijet normalized comparisons keep the legacy stacked + ratio style.
    """
    xcV, yV, eV, bwV, _ = vac
    xcB, yB, eB, bwB, _ = brick

    out_path = os.path.join(out_dir, f"{hn}_stacked.png")
    if use_perdijet and SINGLE_SLICE_MODE and (count_vac is not None or count_brick is not None):
        if not (_selected_count_is_positive(count_vac) and _selected_count_is_positive(count_brick)):
            obs_label = "A_J" if hn.startswith("aj_") else "x_J"
            reason = _selected_count_skip_reason(label_vac, count_vac, label_brick, count_brick, obs_label)
            _log(f"[WARN] {hn}: {reason.replace(chr(10), ' | ')}; writing placeholder: {out_path}")
            _write_unavailable_placeholder(
                out_path,
                title=f"Dijet imbalance comparison skipped [{hn}]",
                reason=reason,
                ylabel=_single_slice_norm_ylabel("aj" if hn.startswith("aj_") else "xj"),
            )
            return

    bin_match = (
        len(xcV) == len(xcB)
        and np.allclose(xcV, xcB, rtol=0, atol=1e-9)
        and np.allclose(bwV, bwB, rtol=0, atol=1e-9)
    )

    yVn = eVn = yBn = eBn = None
    using_norm = False
    if use_perdijet:
        if SINGLE_SLICE_MODE:
            _, yVn, eVn = normalize_by_selected_dijet_count(yV, eV, count_vac)
            _, yBn, eBn = normalize_by_selected_dijet_count(yB, eB, count_brick)
        else:
            _, yVn, eVn = normalize_per_dijet_with_cov(yV, eV, bwV, denom_positive_only=False, cov_mode=PERDIJET_COV_MODE)
            _, yBn, eBn = normalize_per_dijet_with_cov(yB, eB, bwB, denom_positive_only=False, cov_mode=PERDIJET_COV_MODE)
        using_norm = ((yVn is not None) and (yBn is not None))

    if using_norm:
        yVplot, eVplot = yVn, eVn
        yBplot, eBplot = yBn, eBn
    else:
        yVplot = yV
        yBplot = yB
        eVplot = yerr_for_plot_absolute(yV, eV, xsec_norm_term_for_hist(xsec_band_vac, hn, xcV, bwV))
        eBplot = yerr_for_plot_absolute(yB, eB, xsec_norm_term_for_hist(xsec_band_brick, hn, xcB, bwB))

    muV, rmsV = _pdf_stats(xcV, yVplot, bwV)
    muB, rmsB = _pdf_stats(xcB, yBplot, bwB)

    is_aj = (parse_aj_name(hn) is not None)
    xlabel = r"$A_J$" if is_aj else r"$x_J$"

    if is_aj:
        ylab_abs_tex   = r"$d\sigma/dA_J$ (mb per unit $A_J$)"
        ylab_norm_tex  = (_single_slice_norm_ylabel("aj") if SINGLE_SLICE_MODE else r"$(1/\sigma_{\mathrm{sel}})\,d\sigma/dA_J$")
        ylab_abs_plain = "dσ/dA_J (mb per unit A_J)"
        ylab_norm_plain= "(1/σ_sel) dσ/dA_J (1 per unit A_J)"
    else:
        ylab_abs_tex   = r"$d\sigma/dx_J$ (mb per unit $x_J$)"
        ylab_norm_tex  = (_single_slice_norm_ylabel("xj") if SINGLE_SLICE_MODE else r"$(1/\sigma_{\mathrm{sel}})\,d\sigma/dx_J$")
        ylab_abs_plain = "dσ/dx_J (mb per unit x_J)"
        ylab_norm_plain= "(1/σ_sel) dσ/dx_J (1 per unit x_J)"

    ylab_abs  = _choose_label(ylab_abs_tex,  ylab_abs_plain)
    ylab_norm = _choose_label(ylab_norm_tex, ylab_norm_plain)
    ylab_use = ylab_norm if using_norm else ylab_abs

    if not use_perdijet:
        fig, ax = plt.subplots(figsize=(9.5, 6.8))
        ax.errorbar(xcV, yVplot, yerr=eVplot, fmt='o', ms=ms, lw=0.8, capsize=2, color=COMPARE_COLOR_A, label=label_vac)
        ax.errorbar(xcB, yBplot, yerr=eBplot, fmt='o', ms=ms, lw=0.8, capsize=2, color=COMPARE_COLOR_B, label=label_brick)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylab_abs)
        ax.set_xlim(0.0, 1.0)
        ax.legend(loc='best', frameon=False)
        _apply_logy_with_floor(ax, [yVplot, yBplot])
        ax.text(
            0.98, 0.98,
            f"{label_vac}: mean={muV:.3f}, RMS={rmsV:.3f}\n{label_brick}: mean={muB:.3f}, RMS={rmsB:.3f}",
            transform=ax.transAxes, ha='right', va='top', fontsize=_FONTS['note'],
            bbox=dict(boxstyle='round,pad=0.25', facecolor='white', alpha=0.85, edgecolor='black')
        )

        parsed_tag = parse_xj_name(hn) if hn.startswith("xj_") else (parse_aj_name(hn) if hn.startswith("aj_") else None)
        Rv = (parsed_tag[0] if parsed_tag is not None else None)
        obs = (r"Dijet momentum ratio $x_J$" if hn.startswith("xj_") else (r"Dijet momentum imbalance $A_J$" if hn.startswith("aj_") else "xJ/AJ"))
        scale_tag = ("log y" if ax.get_yscale() == "log" else "linear y")
        if Rv is not None:
            wrapped_suptitle = _set_paperready_caption(fig, f"{obs} comparison (absolute overlay, {scale_tag})" + _pair_title_bracket(Rv, hn, include_ystar=True, include_ptlead=True, include_imbalance_backtoback=True), max_chars=118)
        else:
            wrapped_suptitle = _set_paperready_caption(fig, f"{obs} comparison (absolute overlay, {scale_tag}): {hn}{' [nosubfrac]' if hn.endswith('_nosubfrac') else ''}", max_chars=118)

        _safe_tight_layout(fig, rect=[0, 0, 1, _suptitle_rect_top(wrapped_suptitle, top_single=0.96, top_wrapped=0.91)])
        _save_figure(fig, out_path, dpi=170)
        plt.close(fig)
        return

    fig, (ax1, ax2, ax3) = plt.subplots(
        3, 1, figsize=(9.5, 9.2), sharex=True,
        gridspec_kw=dict(height_ratios=[1.0, 1.0, 0.7], hspace=0.05)
    )

    errorbar_nan_safe(ax1, xcV, yVplot, eVplot, fmt='o', ms=ms, lw=0.8, capsize=2, label=(_legend_count_label(label_vac, ('aj' if is_aj else 'xj'), count_vac) if (SINGLE_SLICE_MODE and count_vac is not None and using_norm) else label_vac), color=COMPARE_COLOR_A)
    ax1.set_ylabel(ylab_use)
    ax1.legend(loc='upper left', frameon=False)
    ax1.text(
        0.98, 0.92, f"mean={muV:.3f}\nRMS={rmsV:.3f}", transform=ax1.transAxes,
        ha='right', va='top', fontsize=_FONTS['note'],
        bbox=dict(boxstyle='round,pad=0.25', facecolor='white', alpha=0.85, edgecolor='black')
    )

    errorbar_nan_safe(ax2, xcB, yBplot, eBplot, fmt='o', ms=ms, lw=0.8, capsize=2, label=(_legend_count_label(label_brick, ('aj' if is_aj else 'xj'), count_brick) if (SINGLE_SLICE_MODE and count_brick is not None and using_norm) else label_brick), color=COMPARE_COLOR_B)
    ax2.set_ylabel(ylab_use)
    ax2.legend(loc='upper left', frameon=False)
    ax2.text(
        0.98, 0.92, f"mean={muB:.3f}\nRMS={rmsB:.3f}", transform=ax2.transAxes,
        ha='right', va='top', fontsize=_FONTS['note'],
        bbox=dict(boxstyle='round,pad=0.25', facecolor='white', alpha=0.85, edgecolor='black')
    )

    if bin_match:
        if ratio_mode == 'inv':
            num_y, num_e = yVplot, eVplot
            den_y, den_e = yBplot, eBplot
            rlab = f"{label_vac}/{label_brick}"
        else:
            num_y, num_e = yBplot, eBplot
            den_y, den_e = yVplot, eVplot
            rlab = f"{label_brick}/{label_vac}"

        r, er, m_plot, _m_err = _ratio_with_optional_errors(num_y, num_e, den_y, den_e)
        if np.any(m_plot):
            errorbar_nan_safe(ax3, xcV[m_plot], r[m_plot], er[m_plot], fmt='o', ms=ms, lw=0.8, capsize=2, color='tab:red', label=rlab)
            _apply_configured_ratio_ylim(ax3, ('AJ' if is_aj else 'XJ'), r[m_plot], er[m_plot], context=hn)
            ax3.legend(loc='best', frameon=False)
        else:
            ax3.text(0.5, 0.5, 'ratio unavailable', transform=ax3.transAxes, ha='center', va='center', fontsize=_FONTS['note'])
    else:
        ax3.text(0.5, 0.5, 'ratio unavailable (binning mismatch)', transform=ax3.transAxes, ha='center', va='center', fontsize=_FONTS['note'])

    ax3.axhline(1.0, color='k', ls='--', lw=1)
    ax3.set_xlabel(xlabel)
    ax3.set_ylabel('ratio')

    suffix = (("single-slice count normalized" if SINGLE_SLICE_MODE else "per-selection normalized") if using_norm else "absolute (per-selection norm unavailable)")
    parsed_tag = parse_xj_name(hn) if hn.startswith("xj_") else (parse_aj_name(hn) if hn.startswith("aj_") else None)
    Rv = (parsed_tag[0] if parsed_tag is not None else None)
    obs = (r"Dijet momentum ratio $x_J$" if hn.startswith("xj_") else (r"Dijet momentum imbalance $A_J$" if hn.startswith("aj_") else "xJ/AJ"))
    scale_tag = ("log y" if ax1.get_yscale() == "log" else "linear y")
    if Rv is not None:
        wrapped_suptitle = _set_paperready_caption(fig, f"{obs} comparison ({suffix}, {scale_tag})" + _pair_title_bracket(Rv, hn, include_ystar=True, include_ptlead=True, include_imbalance_backtoback=True), max_chars=118)
    else:
        wrapped_suptitle = _set_paperready_caption(fig, f"{obs} comparison ({suffix}, {scale_tag}): {hn}{' [nosubfrac]' if hn.endswith('_nosubfrac') else ''}", max_chars=118)

    _safe_tight_layout(fig, rect=[0, 0, 1, _suptitle_rect_top(wrapped_suptitle, top_single=0.97, top_wrapped=0.92)])
    _save_figure(fig, out_path, dpi=170)
    plt.close(fig)


def plot_jetR_ratio_compare(
    kind: str,
    mapA,
    mapB,
    labelA: str,
    labelB: str,
    out_dir: str,
    *,
    ms: float = 3.0,
    branch_ns: Optional[bool] = None,
    ratio_mode: str = 'med',
    run_tag_a: Optional[str] = None,
    run_tag_b: Optional[str] = None,
) -> None:
    """Plot first-configured-R over later-configured-R ratios for each run, plus a double ratio per pair.

    Jet-R ratio and double-ratio uncertainties remain downstream-only approximations because
    shared-event cross-R covariance is not published by the upstream merge products.
    """
    if not JET_RADIUS_COMPARE_PAIRS:
        branch_name = 'branch-neutral' if branch_ns is None else ('nosubfrac' if branch_ns else 'subfrac')
        _log(f"[INFO] jet-R dependence skipped for kind={kind}, branch={branch_name}: need at least two unique radii in JET_RADIUS_LIST.")
        return

    def _key_for(hist_map, obs_kind: str, radius: float, ns_flag: Optional[bool]):
        if ns_flag is None:
            candidates = [(obs_kind, radius), (obs_kind, radius, False)]
        else:
            candidates = [(obs_kind, radius, ns_flag), (obs_kind, radius)]
        return next((k for k in candidates if k in hist_map), None)

    def _ratio(xcN,yN,eN,bwN, xcD,yD,eD,bwD):
        if len(xcN) != len(xcD) or not np.allclose(xcN, xcD, rtol=0, atol=1e-9) or not np.allclose(bwN, bwD, rtol=0, atol=1e-9):
            return None
        if not np.any(np.isfinite(xcN)):
            return None
        r, er, m_plot, m_err = _ratio_with_optional_errors(yN, eN, yD, eD)
        if not np.any(m_plot):
            return None
        return (xcN, r, er, m_plot, m_err)

    branch_tag = " [nosubfrac]" if (branch_ns and kind != 'incl') else ""
    branch_name = 'branch-neutral' if branch_ns is None else ('nosubfrac' if branch_ns else 'subfrac')

    for r_num, r_den in JET_RADIUS_COMPARE_PAIRS:
        key_num_A = _key_for(mapA, kind, r_num, branch_ns)
        key_den_A = _key_for(mapA, kind, r_den, branch_ns)
        key_num_B = _key_for(mapB, kind, r_num, branch_ns)
        key_den_B = _key_for(mapB, kind, r_den, branch_ns)
        if key_num_A is None or key_den_A is None or key_num_B is None or key_den_B is None:
            _log(
                f"[INFO] jet-R dependence pair skipped for kind={kind}, branch={branch_name}, pair={_jetr_pair_label(r_num, r_den)}: "
                f"missing histogram(s) in one or both compared runs."
            )
            continue

        xcA_num, yA_num, eA_num, bwA_num, _ = mapA[key_num_A]
        xcA_den, yA_den, eA_den, bwA_den, _ = mapA[key_den_A]
        xcB_num, yB_num, eB_num, bwB_num, _ = mapB[key_num_B]
        xcB_den, yB_den, eB_den, bwB_den, _ = mapB[key_den_B]

        ratioA = _ratio(xcA_num, yA_num, eA_num, bwA_num, xcA_den, yA_den, eA_den, bwA_den)
        ratioB = _ratio(xcB_num, yB_num, eB_num, bwB_num, xcB_den, yB_den, eB_den, bwB_den)
        if ratioA is None or ratioB is None:
            _log(
                f"[INFO] jet-R dependence pair skipped for kind={kind}, branch={branch_name}, pair={_jetr_pair_label(r_num, r_den)}: "
                f"binning mismatch or no common positive bins."
            )
            continue

        pair_slug = _jetr_pair_slug(r_num, r_den)
        pair_label = _jetr_pair_label(r_num, r_den)
        fname_base = f"jetR_ratio_{kind}_{pair_slug}"

        xcA, rA, erA, mA, _mA_err = ratioA
        xcB, rB, erB, mB, _mB_err = ratioB

        fig, ax = plt.subplots(figsize=(9.2, 6.2))
        ax.axhline(1.0, color='k', ls='--', lw=1)
        ax.set_xscale('log')
        errorbar_nan_safe(ax, xcA[mA], rA[mA], erA[mA], fmt='o', ms=ms, lw=0.8, capsize=2, color=COMPARE_COLOR_A, label=f"{labelA}: {pair_label}")
        errorbar_nan_safe(ax, xcB[mB], rB[mB], erB[mB], fmt='s', ms=ms, lw=0.8, capsize=2, color=COMPARE_COLOR_B, label=f"{labelB}: {pair_label}")
        x_plot = np.concatenate([xcA[mA], xcB[mB]])
        bw_plot = np.concatenate([bwA_num[mA], bwB_num[mB]])
        x_min, x_max = _pt_xrange_from_nonzero(
            x_plot,
            np.ones_like(x_plot, dtype=float),
            bw_plot,
            x_floor=1.0,
            x_ceil=(JET_PT_MAX_CFG if np.isfinite(JET_PT_MAX_CFG) and JET_PT_MAX_CFG > 1.0 else None),
        )
        if np.isfinite(x_min) and np.isfinite(x_max) and x_max > x_min:
            ax.set_xlim(x_min, x_max)
            _log(f"[jetpt-zoom][compare][jetR] kind={kind} branch={branch_name} pair={pair_label} xlim={_format_xlim_for_log(x_min, x_max)}")
        _apply_configured_ratio_ylim(ax, 'JETR', np.concatenate([rA[mA], rB[mB]]), np.concatenate([erA[mA], erB[mB]]), context=f'{kind}:{pair_label}')
        ax.set_xlabel(r"$p_T$ (GeV)")
        ax.set_ylabel(rf"$(d\sigma/dp_T)_{{R={float(r_num):.2f}}}/(d\sigma/dp_T)_{{R={float(r_den):.2f}}}$")
        _set_paperready_caption(fig, f"Jet radius dependence ({kind}){branch_tag}: {pair_label}")
        _add_autozoom_note(ax)
        _add_jetr_uncertainty_note(ax)
        ax.legend(loc='best', frameon=False)
        fig.tight_layout()
        _save_figure(fig, os.path.join(out_dir, f"{fname_base}.png"), dpi=170)
        plt.close(fig)

        if len(xcA) == len(xcB) and np.allclose(xcA, xcB, rtol=0, atol=1e-9):
            num_key, den_key, dr_label = _resolve_ratio_order(ratio_mode, labelA, labelB, run_tag_a=run_tag_a, run_tag_b=run_tag_b)
            dr_num = (rA, erA) if num_key == 'A' else (rB, erB)
            dr_den = (rB, erB) if den_key == 'B' else (rA, erA)
            dr, edr, m_plot, _m_err = _ratio_with_optional_errors(dr_num[0], dr_num[1], dr_den[0], dr_den[1])
            m_plot = m_plot & mA & mB
            if np.any(m_plot):
                fig, ax = plt.subplots(figsize=(9.2, 6.0))
                ax.axhline(1.0, color='k', ls='--', lw=1)
                ax.set_xscale('log')
                errorbar_nan_safe(ax, xcA[m_plot], dr[m_plot], edr[m_plot], fmt='o', ms=ms, lw=0.8, capsize=2, color=COMPARE_COLOR_B, label=dr_label)
                x_min, x_max = _pt_xrange_from_nonzero(
                    xcA[m_plot],
                    np.ones_like(xcA[m_plot], dtype=float),
                    bwA_num[m_plot],
                    x_floor=1.0,
                    x_ceil=(JET_PT_MAX_CFG if np.isfinite(JET_PT_MAX_CFG) and JET_PT_MAX_CFG > 1.0 else None),
                )
                if np.isfinite(x_min) and np.isfinite(x_max) and x_max > x_min:
                    ax.set_xlim(x_min, x_max)
                    _log(f"[jetpt-zoom][compare][jetR-double] kind={kind} branch={branch_name} pair={pair_label} xlim={_format_xlim_for_log(x_min, x_max)}")
                _apply_configured_ratio_ylim(ax, 'JETR', dr[m_plot], edr[m_plot], context=f'{kind}:{pair_label}:double')
                ax.set_xlabel(r"$p_T$ (GeV)")
                ax.set_ylabel('double ratio')
                _set_paperready_caption(fig, f"Double ratio of jet-R dependence ({kind}){branch_tag}: {pair_label}")
                _add_autozoom_note(ax)
                _add_jetr_uncertainty_note(ax)
                ax.legend(loc='best', frameon=False)
                fig.tight_layout()
                _save_figure(fig, os.path.join(out_dir, f"jetR_double_ratio_{kind}_{pair_slug}.png"), dpi=170)
                plt.close(fig)
            else:
                _log(
                    f"[INFO] jet-R double ratio skipped for kind={kind}, branch={branch_name}, pair={pair_label}: "
                    f"no common positive bins between the two runs."
                )
        else:
            _log(
                f"[INFO] jet-R double ratio skipped for kind={kind}, branch={branch_name}, pair={pair_label}: "
                f"run A and run B ratio curves do not share identical binning."
            )


def main() -> int:
    # CLI is optional; SLURM wrappers usually call:  python mjj_comparisor_py.py jetscape.ini
    parser = argparse.ArgumentParser(
        description="Compare merged XSCAPE observables between two runs (vacuum vs medium/reference), including Mjj, jet pT, Δφ, xJ/AJ, particle-level QA, and lead-sublead correlations."
    )
    parser.add_argument(
        "ini",
        nargs="?",
        default=os.environ.get("XSCAPE_INI") or os.environ.get("JETSCAPE_INI") or "jetscape.ini",
        help="Path to jetscape.ini (default: env XSCAPE_INI/JETSCAPE_INI or ./jetscape.ini)",
    )
    parser.add_argument(
        "--ratio-mode",
        choices=["med", "inv"],
        default=None,
        help="med: medium/reference. inv: reference/medium.",
    )
    parser.add_argument(
        "--ms",
        type=float,
        default=float(os.environ.get("COMP_MS", str(DEFAULT_MARKER_SIZE))),
        help="Marker size used everywhere (default is intentionally small).",
    )
    parser.add_argument("--runA", default=None, help="Run tag A override (otherwise jetscape.ini: COMPARE_RUN_TAG_A)")
    parser.add_argument("--runB", default=None, help="Run tag B override (otherwise jetscape.ini: COMPARE_RUN_TAG_B)")
    parser.add_argument("--labelA", default=None, help="Label A override (otherwise jetscape.ini: COMPARE_LABEL_A)")
    parser.add_argument("--labelB", default=None, help="Label B override (otherwise jetscape.ini: COMPARE_LABEL_B)")
    args = parser.parse_args()

    ms = float(args.ms)
    if not np.isfinite(ms) or ms <= 0:
        ms = DEFAULT_MARKER_SIZE

    cfg = read_ini(args.ini)

    # ------------------------- config knobs from jetscape.ini -------------------------
    global INCLUDE_XSEC_NORM_ERR, PERDIJET_COV_MODE, COMBINED_R_LIST, JET_RADIUS_COMPARE_PAIRS, SINGLE_SLICE_MODE, SELECTED_DIJET_COUNTS_A, SELECTED_DIJET_COUNTS_B, JET_PT_MAX_CFG, DPHI_RATIO_REBIN_FACTOR, DPHI_ABS_RATIO_REBIN_FACTOR, RATIO_YLIMS, PAPERREADY_SHOW_CAPTION

    # (A) Combined-R list for the "all-R" Mjj overlay plot (REQUIRED; no defaults)
    if "COMBINE_R_LIST" not in cfg:
        _die("Missing required key COMBINE_R_LIST in jetscape.ini (no default).")
    comb_raw = (cfg.get("COMBINE_R_LIST") or "").strip()
    if not comb_raw:
        _die("COMBINE_R_LIST is empty in jetscape.ini (no default).")
    comb_list = parse_list(comb_raw)
    # sanitize: unique + sorted
    comb_list = sorted({float(x) for x in comb_list if np.isfinite(x) and x > 0})
    if not comb_list:
        _die(f"COMBINE_R_LIST parsed to empty/invalid list from raw={comb_raw!r}.")
    COMBINED_R_LIST = comb_list
    # (A.1) Known jet radii for robust decoding of histogram R-tags (supports legacy R*1000).
    jetR_raw = (cfg.get("JET_RADIUS_LIST") or cfg.get("JET_R_LIST") or "").strip()
    jetR_list = _unique_preserve_order_floats(parse_list(jetR_raw) if jetR_raw else [])
    JET_RADIUS_COMPARE_PAIRS = [(jetR_list[0], r_other) for r_other in jetR_list[1:]] if len(jetR_list) >= 2 else []
    _set_known_r_values(list(jetR_list) + list(COMBINED_R_LIST))

    try:
        SINGLE_SLICE_MODE = bool(parse_bool(cfg.get("SINGLE_SLICE_MODE"), default=False))
    except Exception as e:
        _die(f"Invalid SINGLE_SLICE_MODE={cfg.get('SINGLE_SLICE_MODE')!r}: {e}")
    _log(f"[cfg] SINGLE_SLICE_MODE={1 if SINGLE_SLICE_MODE else 0}")

    # (B) Absolute-spectrum σGen plotting inflation (ini required; env override allowed)
    if "INCLUDE_XSEC_NORM_ERR" not in cfg:
        _die("Missing required key INCLUDE_XSEC_NORM_ERR in jetscape.ini (no default).")
    inc_raw_ini = (cfg.get("INCLUDE_XSEC_NORM_ERR") or "").strip()
    if not inc_raw_ini:
        _die("INCLUDE_XSEC_NORM_ERR is empty in jetscape.ini (no default).")
    try:
        include_ini = 1 if parse_bool(inc_raw_ini, default=False) else 0
    except Exception as e:
        _die(f"Invalid INCLUDE_XSEC_NORM_ERR={cfg.get('INCLUDE_XSEC_NORM_ERR')!r}: {e}")
    INCLUDE_XSEC_NORM_ERR = include_ini
    if "INCLUDE_XSEC_NORM_ERR" in os.environ:
        try:
            INCLUDE_XSEC_NORM_ERR = 1 if parse_bool(os.environ.get("INCLUDE_XSEC_NORM_ERR", ""), default=bool(include_ini)) else 0
        except Exception as e:
            _die(f"Invalid INCLUDE_XSEC_NORM_ERR env override {os.environ.get('INCLUDE_XSEC_NORM_ERR')!r}: {e}")

    # (C) Covariance mode for shape uncertainties (ini default; env override allowed)
    ini_cov = (cfg.get("COVARIANCE_MODE") or "").strip()
    ini_legacy = (cfg.get("PERDIJET_COV_MODE") or "").strip()

    # If both keys are present in ini and disagree, hard fail (prevents silent mismatches)
    if ini_cov and ini_legacy and (ini_cov.strip().lower() != ini_legacy.strip().lower()):
        _log(f"[cfg][FATAL] jetscape.ini sets both COVARIANCE_MODE={ini_cov!r} and PERDIJET_COV_MODE={ini_legacy!r} (disagree). "
             f"Use only COVARIANCE_MODE (PERDIJET_COV_MODE is legacy).")
        raise SystemExit(2)

    # Require explicit ini setting (canonical key preferred). No silent defaults.
    if (not ini_cov) and (not ini_legacy):
        _log("[cfg][FATAL] jetscape.ini missing required key COVARIANCE_MODE (or legacy PERDIJET_COV_MODE). Refusing to default to 'diag'.")
        raise SystemExit(2)

    ini_key_used = "COVARIANCE_MODE" if ini_cov else "PERDIJET_COV_MODE"
    cov_raw_ini = (ini_cov or ini_legacy)

    try:
        cov_mode, cov_note = _canon_cov_mode(cov_raw_ini)
    except Exception as e:
        _log(f"[cfg][FATAL] Unsupported covariance mode in jetscape.ini: {cov_raw_ini!r}. {e}")
        raise SystemExit(2)

    PERDIJET_COV_MODE = cov_mode

    # Env overrides (kept only for convenience, but logged loudly). Canonical key wins.
    env_cov = os.environ.get("COVARIANCE_MODE")
    env_legacy = os.environ.get("PERDIJET_COV_MODE")

    if env_cov and env_legacy and (env_cov.strip().lower() != env_legacy.strip().lower()):
        _log(f"[cfg][FATAL] Environment sets both COVARIANCE_MODE={env_cov!r} and PERDIJET_COV_MODE={env_legacy!r} (disagree). "
             f"Set only COVARIANCE_MODE (PERDIJET_COV_MODE is legacy).")
        raise SystemExit(2)

    if env_cov or env_legacy:
        env_key_used = "COVARIANCE_MODE" if env_cov else "PERDIJET_COV_MODE"
        try:
            cov_mode_env, cov_note_env = _canon_cov_mode((env_cov or env_legacy) or "")
        except Exception as e:
            _log(f"[cfg][FATAL] Unsupported covariance mode from environment {env_key_used}={(env_cov or env_legacy)!r}. {e}")
            raise SystemExit(2)
        PERDIJET_COV_MODE = cov_mode_env
        cov_note = (cov_note_env or f"overridden by env {env_key_used}={(env_cov or env_legacy)!r}")

    _log(f"[cfg] Covariance mode resolved: ini {ini_key_used}={cov_raw_ini!r} -> {cov_mode!r}; final mode={PERDIJET_COV_MODE!r}"
         + (f" ({cov_note})" if cov_note else ""))
    # ------------------------- compare targets (ini-driven) -------------------------
    def _resolve(cli_val, env_key: str, ini_key: str, *, default: str = '', required: bool = False):
        if cli_val is not None and str(cli_val).strip() != '':
            return str(cli_val).strip(), 'cli'
        if env_key in os.environ and str(os.environ.get(env_key, '')).strip() != '':
            return str(os.environ.get(env_key, '')).strip(), f'env:{env_key}'
        v = (cfg.get(ini_key, '') or '').strip()
        if v != '':
            return v, f'ini:{ini_key}'
        if default != '':
            return default, 'default'
        if required:
            raise KeyError(f'Missing required compare key: {ini_key} (set it in jetscape.ini)')
        return '', 'unset'

    try:
        runA, srcA = _resolve(args.runA, 'COMP_RUN_TAG_A', 'COMPARE_RUN_TAG_A', required=True)
        runB, srcB = _resolve(args.runB, 'COMP_RUN_TAG_B', 'COMPARE_RUN_TAG_B', required=True)
    except KeyError as e:
        _log(f'[ERROR] {e}')
        _log('[ERROR] You must set COMPARE_RUN_TAG_A and COMPARE_RUN_TAG_B in jetscape.ini for ini-driven comparisons.')
        return 2

    labelA_raw, srcLA = _resolve(args.labelA, 'COMP_LABEL_A', 'COMPARE_LABEL_A', default=LABEL_A_DEFAULT)
    labelB_raw, srcLB = _resolve(args.labelB, 'COMP_LABEL_B', 'COMPARE_LABEL_B', default=LABEL_B_DEFAULT)

    ratio_mode_raw, srcRM = _resolve(args.ratio_mode, 'COMP_RATIO_MODE', 'COMPARE_RATIO_MODE', default=DEFAULT_RATIO_MODE)
    ratio_mode = (ratio_mode_raw or DEFAULT_RATIO_MODE).strip().lower()
    if ratio_mode not in ('med', 'inv'):
        _log(f"[WARN] Invalid ratio mode '{ratio_mode_raw}' (src={srcRM}); using default '{DEFAULT_RATIO_MODE}'")
        ratio_mode = DEFAULT_RATIO_MODE
        srcRM = 'default'
    args.ratio_mode = ratio_mode

    _log(f"[cfg] compare RUN_TAG_A={runA!r} (src={srcA})")
    _log(f"[cfg] compare RUN_TAG_B={runB!r} (src={srcB})")
    _log(f"[cfg] compare LABEL_A={labelA_raw!r} (src={srcLA})")
    _log(f"[cfg] compare LABEL_B={labelB_raw!r} (src={srcLB})")
    _log(f"[cfg] compare RATIO_MODE={ratio_mode!r} (src={srcRM})")

    # Pretty display labels (folders stay exactly as your run tags)
    dispA = _pretty_label(labelA_raw)
    dispB = _pretty_label(labelB_raw)

    # Derive runs root from current RUNS_BASE in ini (dirname of .../RUN_TAG)
    runs_base_cur = expand_vars(cfg.get("RUNS_BASE", "$HOME/xscape_runs/${RUN_TAG}"), cfg)
    runs_root = os.path.dirname(runs_base_cur.rstrip("/")) if runs_base_cur else os.path.expandvars("$HOME/xscape_runs")

    compare_dir = os.path.join(runs_root, "comparisons", f"{runA}_vs_{runB}")
    # Plot layout: mirror fitter branch-first trees for the standard categories, with a separate
    # branch-neutral inclusive_unit_normalized tree for the analyzer's inclusive jet unit-shape overlays.
    plots_abs       = os.path.join(compare_dir, "plots", "absolute")
    plots_norm      = os.path.join(compare_dir, "plots", "dijet_normalized")
    plots_unitshape = os.path.join(compare_dir, "plots", "inclusive_unit_normalized")

    plots_abs_sub  = os.path.join(plots_abs,  "subfrac")
    plots_abs_ns   = os.path.join(plots_abs,  "nosubfrac")
    plots_norm_sub = os.path.join(plots_norm, "subfrac")
    plots_norm_ns  = os.path.join(plots_norm, "nosubfrac")

    out_dir_mjj_abs_sub      = os.path.join(plots_abs_sub,  "dijet_mass")
    out_dir_mjj_abs_ns       = os.path.join(plots_abs_ns,   "dijet_mass")
    out_dir_mjj_norm_sub     = os.path.join(plots_norm_sub, "dijet_mass")
    out_dir_mjj_norm_ns      = os.path.join(plots_norm_ns,  "dijet_mass")
    out_dir_dphiabs_abs_sub  = os.path.join(plots_abs_sub,  "dphi_fit_abs0pi")
    out_dir_dphiabs_abs_ns   = os.path.join(plots_abs_ns,   "dphi_fit_abs0pi")
    out_dir_dphiabs_norm_sub = os.path.join(plots_norm_sub, "dphi_fit_abs0pi")
    out_dir_dphiabs_norm_ns  = os.path.join(plots_norm_ns,  "dphi_fit_abs0pi")
    out_dir_imb_abs_sub      = os.path.join(plots_abs_sub,  "dijet_imbalance")
    out_dir_imb_abs_ns       = os.path.join(plots_abs_ns,   "dijet_imbalance")
    out_dir_imb_norm_sub     = os.path.join(plots_norm_sub, "dijet_imbalance")
    out_dir_imb_norm_ns      = os.path.join(plots_norm_ns,  "dijet_imbalance")

    # Jet spectra: inclusive is branch-neutral (like fitter); absolute inclusive overlays live under
    # plots/absolute/jet_spectra while inclusive unit-shape overlays live under plots/inclusive_unit_normalized/jet_spectra.
    # Lead/sublead spectra keep the existing branch-routed absolute/dijet_normalized trees.
    out_dir_jetpt_abs_neutral       = os.path.join(plots_abs,       "jet_spectra")
    out_dir_jetpt_unitshape_neutral = os.path.join(plots_unitshape, "jet_spectra")
    out_dir_jetpt_abs_sub           = os.path.join(plots_abs_sub,   "jet_spectra")
    out_dir_jetpt_abs_ns       = os.path.join(plots_abs_ns,   "jet_spectra")
    out_dir_jetpt_norm_sub     = os.path.join(plots_norm_sub, "jet_spectra")
    out_dir_jetpt_norm_ns      = os.path.join(plots_norm_ns,  "jet_spectra")

    out_dir_jetR   = os.path.join(compare_dir, "plots", "jet_R_dependence")
    out_dir_jetR_sub = os.path.join(out_dir_jetR, "subfrac")
    out_dir_jetR_ns  = os.path.join(out_dir_jetR, "nosubfrac")
    out_dir_particle = os.path.join(compare_dir, "plots", "particle_level")
    out_dir_lead_sublead_corr_sub = os.path.join(plots_abs_sub, "lead_sublead_correlation")
    out_dir_lead_sublead_corr_ns  = os.path.join(plots_abs_ns,  "lead_sublead_correlation")
    out_dir_dphiabs_deta_sub      = os.path.join(plots_abs_sub, "dphi_abs_vs_deta")
    out_dir_dphiabs_deta_ns       = os.path.join(plots_abs_ns,  "dphi_abs_vs_deta")

    for d in [
        plots_abs, plots_norm, plots_unitshape,
        plots_abs_sub, plots_abs_ns, plots_norm_sub, plots_norm_ns,
        out_dir_mjj_abs_sub, out_dir_mjj_abs_ns, out_dir_mjj_norm_sub, out_dir_mjj_norm_ns,
        out_dir_dphiabs_abs_sub, out_dir_dphiabs_abs_ns, out_dir_dphiabs_norm_sub, out_dir_dphiabs_norm_ns,
        out_dir_imb_abs_sub, out_dir_imb_abs_ns, out_dir_imb_norm_sub, out_dir_imb_norm_ns,
        out_dir_jetpt_abs_neutral, out_dir_jetpt_unitshape_neutral,
        out_dir_jetpt_abs_sub, out_dir_jetpt_abs_ns, out_dir_jetpt_norm_sub, out_dir_jetpt_norm_ns,
        out_dir_jetR, out_dir_jetR_sub, out_dir_jetR_ns, out_dir_particle, out_dir_lead_sublead_corr_sub, out_dir_lead_sublead_corr_ns, out_dir_dphiabs_deta_sub, out_dir_dphiabs_deta_ns,
    ]:
        ensure_dir(d)
    # Logging (fitter-consistent filename): write into compare_dir/logs/paperreadycomparisor_py.log
    # so both python stages use the same log naming convention.
    logs_dir = os.path.join(compare_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    log_path = os.path.join(logs_dir, "paperreadycomparisor_py.log")
    _set_log_file(log_path, mode="a")

    # Plot styling knobs (optional) from jetscape.ini. Apply after log setup so
    # any fallback warnings and resolved values land in paperreadycomparisor_py.log.
    global _FONTS
    _FONTS = apply_plot_style(cfg)
    PAPERREADY_SHOW_CAPTION = bool(parse_bool(cfg.get('PAPERREADY_SHOW_CAPTION', '1'), default=True))

    _log("stage: paper-ready merged-observable comparison (not Mjj-only)")
    _log(f"config ini: {args.ini}")
    _log(f"RUN_TAG_A={runA}  RUN_TAG_B={runB}")
    _log(f"ratio_mode={args.ratio_mode}  marker_size={ms}")
    _log(f"compare_dir: {compare_dir}")
    _log(f"[cfg] PAPERREADY_SHOW_CAPTION={int(PAPERREADY_SHOW_CAPTION)}")

    _log(f"[cfg] COMBINE_R_LIST(raw)={comb_raw!r}")
    _log(f"[cfg] COMBINED_R_LIST(parsed)={COMBINED_R_LIST}")
    _log(f"[cfg] JET_RADIUS_LIST(raw)={jetR_raw!r}")
    _log(f"[cfg] JET_RADIUS_LIST(parsed)={jetR_list}")
    _log(f"[cfg] JET_RADIUS_COMPARE_PAIRS={JET_RADIUS_COMPARE_PAIRS}")
    _log(f"[cfg] KNOWN_R_VALUES(for decoding)={KNOWN_R_VALUES}")
    _log(f"[cfg] INCLUDE_XSEC_NORM_ERR(ini_raw)={inc_raw_ini!r} -> {INCLUDE_XSEC_NORM_ERR}")
    if 'INCLUDE_XSEC_NORM_ERR' in os.environ:
        _log(f"[cfg] ENV override INCLUDE_XSEC_NORM_ERR={os.environ.get('INCLUDE_XSEC_NORM_ERR')!r} -> {INCLUDE_XSEC_NORM_ERR}")
    _log(f"[cfg] cov_mode(ini_raw)={cov_raw_ini!r} -> PERDIJET_COV_MODE={PERDIJET_COV_MODE}")
    if cov_note:
        _log(f"[cfg] cov_note: {cov_note}")
    if 'PERDIJET_COV_MODE' in os.environ:
        _log(f"[cfg] ENV override PERDIJET_COV_MODE={os.environ.get('PERDIJET_COV_MODE')!r} -> {PERDIJET_COV_MODE}")
    if 'COVARIANCE_MODE' in os.environ and 'PERDIJET_COV_MODE' not in os.environ:
        _log(f"[cfg] ENV override COVARIANCE_MODE={os.environ.get('COVARIANCE_MODE')!r} -> {PERDIJET_COV_MODE}")

    raw_jet_pt_max = str(cfg.get("JET_PT_MAX", "") or "").strip()
    if raw_jet_pt_max == "":
        JET_PT_MAX_CFG = float("nan")
        _log("[cfg] JET_PT_MAX missing in jetscape.ini -> compare-side jet-spectrum auto-zoom will use populated bins only")
    else:
        try:
            JET_PT_MAX_CFG = float(raw_jet_pt_max)
        except Exception:
            _log(f"[cfg][FATAL] Invalid JET_PT_MAX={raw_jet_pt_max!r}; expected finite float")
            raise SystemExit(2)
        _log(f"[cfg] JET_PT_MAX={JET_PT_MAX_CFG}")

    def _parse_compare_rebin_factor(key: str, default: int = 1) -> int:
        raw = str(cfg.get(key, str(default)) or '').strip()
        if raw == '':
            return int(default)
        try:
            val = int(float(raw))
        except Exception:
            _die(f"Invalid {key}={raw!r}; expected positive integer")
        if val < 1:
            _die(f"Invalid {key}={raw!r}; expected integer >= 1")
        return val

    DPHI_RATIO_REBIN_FACTOR = _parse_compare_rebin_factor('DPHI_COMPARE_RATIO_REBIN_FACTOR', default=1)
    DPHI_ABS_RATIO_REBIN_FACTOR = _parse_compare_rebin_factor('DPHI_ABS_COMPARE_RATIO_REBIN_FACTOR', default=1)
    _log(f"[cfg] DPHI_COMPARE_RATIO_REBIN_FACTOR={DPHI_RATIO_REBIN_FACTOR}")
    _log(f"[cfg] DPHI_ABS_COMPARE_RATIO_REBIN_FACTOR={DPHI_ABS_RATIO_REBIN_FACTOR}")

    def _parse_required_ratio_ylim(kind: str) -> Tuple[float, float]:
        y_min_key = f"{kind}_COMPARE_RATIO_YMIN"
        y_max_key = f"{kind}_COMPARE_RATIO_YMAX"
        raw_min = str(cfg.get(y_min_key, '') or '').strip()
        raw_max = str(cfg.get(y_max_key, '') or '').strip()
        if raw_min == '':
            _die(f"Missing required key {y_min_key} in jetscape.ini (no default).")
        if raw_max == '':
            _die(f"Missing required key {y_max_key} in jetscape.ini (no default).")
        try:
            y_min = float(raw_min)
            y_max = float(raw_max)
        except Exception:
            _die(f"Invalid {kind} compare ratio y-range: {y_min_key}={raw_min!r}, {y_max_key}={raw_max!r}; expected finite floats")
        if not (np.isfinite(y_min) and np.isfinite(y_max)):
            _die(f"Invalid {kind} compare ratio y-range: {y_min_key}={raw_min!r}, {y_max_key}={raw_max!r}; expected finite floats")
        if y_max <= y_min:
            _die(f"Invalid {kind} compare ratio y-range: require {y_max_key} > {y_min_key}, got {y_max} <= {y_min}")
        if not (y_min <= 1.0 <= y_max):
            _die(f"Invalid {kind} compare ratio y-range: require {y_min_key} <= 1 <= {y_max_key}, got [{y_min}, {y_max}]")
        _log(f"[cfg] {y_min_key}={y_min}")
        _log(f"[cfg] {y_max_key}={y_max}")
        return y_min, y_max

    RATIO_YLIMS = {
        'MJJ': _parse_required_ratio_ylim('MJJ'),
        'JETPT': _parse_required_ratio_ylim('JETPT'),
        'DPHI': _parse_required_ratio_ylim('DPHI'),
        'DPHI_ABS': _parse_required_ratio_ylim('DPHI_ABS'),
        'XJ': _parse_required_ratio_ylim('XJ'),
        'AJ': _parse_required_ratio_ylim('AJ'),
        'JETR': _parse_required_ratio_ylim('JETR'),
        'LEAD_SUBLEAD_PROFILE': _parse_required_ratio_ylim('LEAD_SUBLEAD_PROFILE'),
    }

    # pT binning info (used only for nicer plot titles)
    init_pt_lead_labels_from_ini(cfg)
    global CFG_FOR_TITLES
    CFG_FOR_TITLES = dict(cfg)

    # resolve DIR_FINAL for each run tag by overriding RUN_TAG and re-expanding
    cfgA = dict(cfg); cfgA["RUN_TAG"] = runA
    cfgB = dict(cfg); cfgB["RUN_TAG"] = runB

    dir_final_A = expand_vars(cfg.get("DIR_FINAL", "$HOME/xscape_runs/${RUN_TAG}/final"), cfgA)
    dir_final_B = expand_vars(cfg.get("DIR_FINAL", "$HOME/xscape_runs/${RUN_TAG}/final"), cfgB)

    if SINGLE_SLICE_MODE:
        try:
            pt_lo_cfg = parse_list(cfg.get("PT_LO") or "")
            pt_hi_cfg = parse_list(cfg.get("PT_HI") or "")
        except Exception as e:
            _die(f"SINGLE_SLICE_MODE=1 requires valid PT_LO/PT_HI arrays in {args.ini}: {e}")
        if len(pt_lo_cfg) != 1 or len(pt_hi_cfg) != 1:
            _die(f"SINGLE_SLICE_MODE=1 requires exactly one configured pThat slice; got PT_LO={pt_lo_cfg} PT_HI={pt_hi_cfg}")
        pt_edges_cfg = parse_list((cfg.get("PT_LEAD_BIN_EDGES") or "").strip())
        if len(pt_edges_cfg) < 2:
            _die("SINGLE_SLICE_MODE=1 requires PT_LEAD_BIN_EDGES with at least two edges in jetscape.ini")
        try:
            SELECTED_DIJET_COUNTS_A, counts_path_A = SelectedDijetCountResolver.load(dir_final_A, jetR_list, pt_edges_cfg)
            SELECTED_DIJET_COUNTS_B, counts_path_B = SelectedDijetCountResolver.load(dir_final_B, jetR_list, pt_edges_cfg)
        except Exception as e:
            _die(str(e))
        _log(f"[cfg] SINGLE_SLICE_MODE enabled; runA selected dijet counts: {counts_path_A}")
        _log(f"[cfg] SINGLE_SLICE_MODE enabled; runB selected dijet counts: {counts_path_B}")

    preferredA = os.path.join(dir_final_A, "dphi_allSlices.root")
    preferredB = os.path.join(dir_final_B, "dphi_allSlices.root")

    # STRICT (fitter-consistent): only accept the canonical final/dphi_allSlices.root.
    run_dir_A = os.path.join(runs_root, runA)
    run_dir_B = os.path.join(runs_root, runB)


    def _list_run_tags(root: str) -> List[str]:
        try:
            tags: List[str] = []
            for name in sorted(os.listdir(root)):
                if name.startswith('.') or name == 'comparisons':
                    continue
                p = os.path.join(root, name)
                if os.path.isdir(p):
                    tags.append(name)
            return tags
        except Exception:
            return []

    if not os.path.isdir(run_dir_A):
        _log(f"[ERROR] Run folder missing for runA='{runA}' at: {run_dir_A}")
        _log(f"[ERROR] RUNS_ROOT resolved to: {runs_root}")
        tags = _list_run_tags(runs_root)
        if tags:
            _log('[ERROR] Available tags (first 30): ' + ', '.join(tags[:30]))
        return 2
    if not os.path.isdir(run_dir_B):
        _log(f"[ERROR] Run folder missing for runB='{runB}' at: {run_dir_B}")
        _log(f"[ERROR] RUNS_ROOT resolved to: {runs_root}")
        tags = _list_run_tags(runs_root)
        if tags:
            _log('[ERROR] Available tags (first 30): ' + ', '.join(tags[:30]))
        return 2

    rootA = find_best_root_for_run(run_dir_A, preferredA)
    rootB = find_best_root_for_run(run_dir_B, preferredB)

    _log(f"ROOT_A: {rootA}")
    _log(f"ROOT_B: {rootB}")

    if not rootA or not os.path.isfile(rootA):
        _log(f"[ERROR] Missing final ROOT for runA: {preferredA}")
        _log("[ERROR] Run merge.sh successfully (expected dphi_allSlices.root in DIR_FINAL).")
        return 2
    if not rootB or not os.path.isfile(rootB):
        _log(f"[ERROR] Missing final ROOT for runB: {preferredB}")
        _log("[ERROR] Run merge.sh successfully (expected dphi_allSlices.root in DIR_FINAL).")
        return 2

    # σGen normalization relative uncertainty (optional, for displayed error bars on absolute spectra)
    dir_final_A = os.path.dirname(rootA)
    dir_final_B = os.path.dirname(rootB)
    xsec_rel_A = float("nan")
    xsec_rel_B = float("nan")
    xsec_band_A = None
    xsec_band_B = None
    if INCLUDE_XSEC_NORM_ERR:
        xsec_summary_A = os.path.join(dir_final_A, "xsec_summary.json")
        xsec_summary_B = os.path.join(dir_final_B, "xsec_summary.json")
        xsec_rel_A = load_xsec_rel_err(dir_final_A)
        xsec_rel_B = load_xsec_rel_err(dir_final_B)
        if not (np.isfinite(xsec_rel_A) and xsec_rel_A > 0):
            _log(f"[xsec][FATAL] INCLUDE_XSEC_NORM_ERR=1 but runA {xsec_summary_A} is missing/unreadable or has invalid xsec_total_rel_err={xsec_rel_A!r}. Rerun merge with valid sigmaErr_mb/xsecerr_mb metadata.")
            raise SystemExit(2)
        if not (np.isfinite(xsec_rel_B) and xsec_rel_B > 0):
            _log(f"[xsec][FATAL] INCLUDE_XSEC_NORM_ERR=1 but runB {xsec_summary_B} is missing/unreadable or has invalid xsec_total_rel_err={xsec_rel_B!r}. Rerun merge with valid sigmaErr_mb/xsecerr_mb metadata.")
            raise SystemExit(2)
        try:
            xsec_band_A = SliceNormBandBuilder(dir_final_A, label="runA")
            xsec_band_B = SliceNormBandBuilder(dir_final_B, label="runB")
        except Exception as e:
            _log(f"[xsec][FATAL] INCLUDE_XSEC_NORM_ERR=1 but exact per-slice xsec band reconstruction failed: {e}")
            raise SystemExit(2)
        _log(f"[xsec] runA xsec_total_rel_err={xsec_rel_A:.6g} from {xsec_summary_A}")
        _log(f"[xsec] runB xsec_total_rel_err={xsec_rel_B:.6g} from {xsec_summary_B}")
        _log(f"[xsec] runA exact-band slices={len(xsec_band_A.slices)} ; runB exact-band slices={len(xsec_band_B.slices)}")

    global XSEC_REL_A, XSEC_REL_B, XSEC_BAND_A, XSEC_BAND_B
    XSEC_REL_A = float(xsec_rel_A)
    XSEC_REL_B = float(xsec_rel_B)
    XSEC_BAND_A = xsec_band_A
    XSEC_BAND_B = xsec_band_B

    mjj_min_cfg = float(cfg.get("MJJ_MIN_GEV", "0"))
    mjj_max_cfg = float(cfg.get("MJJ_MAX_GEV", "3000"))
    raw_mjj_req = str(cfg.get("MJJ_REQUIRE_BACKTOBACK", "") or "").strip()
    if raw_mjj_req == "":
        _log("[cfg][FATAL] jetscape.ini missing required key MJJ_REQUIRE_BACKTOBACK")
        raise SystemExit(2)
    try:
        mjj_require_backtoback = int(float(raw_mjj_req))
    except Exception:
        _log(f"[cfg][FATAL] Invalid MJJ_REQUIRE_BACKTOBACK={raw_mjj_req!r}; expected 0 or 1")
        raise SystemExit(2)
    if mjj_require_backtoback not in (0, 1):
        _log(f"[cfg][FATAL] Invalid MJJ_REQUIRE_BACKTOBACK={raw_mjj_req!r}; expected 0 or 1")
        raise SystemExit(2)
    bb_tol_deg = float(cfg.get("DIJET_BACKTOBACK_TOL_DEG", "20"))
    _log(f"[cfg] MJJ_REQUIRE_BACKTOBACK={mjj_require_backtoback}")
    ystar_enable = int(cfg.get("YSTAR_ENABLE", "0"))
    ystar_max = float(cfg.get("YSTAR_MAX", "0.6"))
    try:
        exact_two_required = _parse_exact_two_jets_required(cfg)
    except Exception as e:
        _log(f"[cfg][FATAL] {e}")
        raise SystemExit(2)
    raw_imb_req = str(cfg.get("IMBALANCE_REQUIRE_BACKTOBACK", "") or "").strip()
    if raw_imb_req == "":
        _log("[cfg][FATAL] jetscape.ini missing required key IMBALANCE_REQUIRE_BACKTOBACK")
        raise SystemExit(2)
    try:
        imbalance_require_backtoback = int(float(raw_imb_req))
    except Exception:
        _log(f"[cfg][FATAL] Invalid IMBALANCE_REQUIRE_BACKTOBACK={raw_imb_req!r}; expected 0 or 1")
        raise SystemExit(2)
    if imbalance_require_backtoback not in (0, 1):
        _log(f"[cfg][FATAL] Invalid IMBALANCE_REQUIRE_BACKTOBACK={raw_imb_req!r}; expected 0 or 1")
        raise SystemExit(2)
    raw_imb_tol = str(cfg.get("IMBALANCE_BACKTOBACK_TOL_DEG", "") or "").strip()
    if raw_imb_tol == "":
        _log("[cfg][FATAL] jetscape.ini missing required key IMBALANCE_BACKTOBACK_TOL_DEG")
        raise SystemExit(2)
    try:
        imbalance_bb_tol_deg = float(raw_imb_tol)
    except Exception:
        _log(f"[cfg][FATAL] Invalid IMBALANCE_BACKTOBACK_TOL_DEG={raw_imb_tol!r}; expected finite float in (0, 180]")
        raise SystemExit(2)
    if not math.isfinite(imbalance_bb_tol_deg) or imbalance_bb_tol_deg <= 0.0 or imbalance_bb_tol_deg > 180.0:
        _log(f"[cfg][FATAL] Invalid IMBALANCE_BACKTOBACK_TOL_DEG={raw_imb_tol!r}; expected finite float in (0, 180]")
        raise SystemExit(2)
    global EXACT_TWO_JETS_REQUIRED, IMBALANCE_REQUIRE_BACKTOBACK, IMBALANCE_BACKTOBACK_TOL_DEG
    EXACT_TWO_JETS_REQUIRED = bool(exact_two_required)
    IMBALANCE_REQUIRE_BACKTOBACK = bool(imbalance_require_backtoback)
    IMBALANCE_BACKTOBACK_TOL_DEG = float(imbalance_bb_tol_deg)
    ystar_title_suffix = f"; |y*|<{ystar_max:.1f}" if ystar_enable == 1 else ""
    if EXACT_TWO_JETS_REQUIRED:
        ystar_title_suffix += '; exactly 2 accepted jets'
    _log(f"[cfg] DIJET_REQUIRE_EXACTLY_TWO_JETS={1 if EXACT_TWO_JETS_REQUIRED else 0}")
    _log(f"[cfg] IMBALANCE_REQUIRE_BACKTOBACK={1 if IMBALANCE_REQUIRE_BACKTOBACK else 0}  IMBALANCE_BACKTOBACK_TOL_DEG={IMBALANCE_BACKTOBACK_TOL_DEG}")

    countA_hists: Dict[str, tuple] = {}
    countB_hists: Dict[str, tuple] = {}
    if SINGLE_SLICE_MODE:
        _log("Reading count-density histograms for true single-slice dN normalization...")
        countA_hists = read_count_density_hists(rootA)
        countB_hists = read_count_density_hists(rootB)
        _log(f"Count-density hists: A={len(countA_hists)}  B={len(countB_hists)}")

    _log("Reading Mjj histograms...")
    hA = read_mjj_hists(rootA)
    hB = read_mjj_hists(rootB)
    _log(f"Mjj hists: A={len(hA)}  B={len(hB)}")

    # Jet pT spectra (if present in ROOT)
    jA = read_jetpt_hists(rootA)
    jB = read_jetpt_hists(rootB)
    _log(f"Jet pT hists: A={len(jA)}  B={len(jB)}")

    all_names = sorted(set(hA.keys()) | set(hB.keys()), key=sort_key)

    n_done = 0
    n_skip = 0

    for hn in all_names:
        if hn not in hA or hn not in hB:
            n_skip += 1
            miss = []
            if hn not in hA: miss.append("A")
            if hn not in hB: miss.append("B")
            _log(f"[WARN] Skipping {hn}: missing in {','.join(miss)}")
            continue

        is_ns = hn.endswith('_nosubfrac')
        out_dir_mjj_abs_local = out_dir_mjj_abs_ns if is_ns else out_dir_mjj_abs_sub
        out_dir_mjj_norm_local = out_dir_mjj_norm_ns if is_ns else out_dir_mjj_norm_sub


        overlay_plot(
            hn, hA[hn], hB[hn],
            labelA=dispA,
            labelB=dispB,
            out_dir=out_dir_mjj_abs_local,
            mjj_min_cfg=mjj_min_cfg,
            mjj_max_cfg=mjj_max_cfg,
            bb_tol_deg=bb_tol_deg,
            mjj_require_backtoback=mjj_require_backtoback,
            ystar_title_suffix=ystar_title_suffix,
            ms=ms,
            ratio_mode=args.ratio_mode,
            run_tag_a=runA,
            run_tag_b=runB,
        )


        countA = countB = None
        if SINGLE_SLICE_MODE:
            try:
                tag = parse_mjj_name(hn)
                if tag is None:
                    raise RuntimeError(f"could not parse Mjj histogram name '{hn}'")
                countA = SELECTED_DIJET_COUNTS_A.count_for("mjj", tag[0], is_nosubfrac=is_ns, ptlo=(None if tag[3] else tag[1]), pthi=(None if tag[3] else tag[2]))
                countB = SELECTED_DIJET_COUNTS_B.count_for("mjj", tag[0], is_nosubfrac=is_ns, ptlo=(None if tag[3] else tag[1]), pthi=(None if tag[3] else tag[2]))
            except Exception as e:
                _die(f"[single-slice] {hn}: failed to resolve Mjj selected dijet counts: {e}")
        hA_norm = _single_slice_hist_for_norm(countA_hists, hA, hn, label=dispA)
        hB_norm = _single_slice_hist_for_norm(countB_hists, hB, hn, label=dispB)
        overlay_plot_perdijet(
            hn, hA_norm, hB_norm,
            labelA=dispA,
            labelB=dispB,
            out_dir=out_dir_mjj_norm_local,
            mjj_min_cfg=mjj_min_cfg,
            mjj_max_cfg=mjj_max_cfg,
            bb_tol_deg=bb_tol_deg,
            mjj_require_backtoback=mjj_require_backtoback,
            ystar_title_suffix=ystar_title_suffix,
            ms=ms,
            countA=countA,
            countB=countB,
            ratio_mode=args.ratio_mode,
            run_tag_a=runA,
            run_tag_b=runB,
        )

        n_done += 1

    _log(f"Overlay plots written: {n_done}")
    if n_skip:
        _log(f"Skipped (missing in one file): {n_skip}")

    # combined “all” plot
    combined_all_plot(
        hA, hB,
        labelA=dispA,
        labelB=dispB,
        out_dir=out_dir_mjj_abs_sub,
        mjj_min_cfg=mjj_min_cfg,
        mjj_max_cfg=mjj_max_cfg,
        bb_tol_deg=bb_tol_deg,
        mjj_require_backtoback=mjj_require_backtoback,
        ystar_title_suffix=ystar_title_suffix,
        R_list=COMBINED_R_LIST,
        ms=ms,
    )

    # nosubfrac combined plots (if present)
    hA_ns = {k:v for k,v in hA.items() if k.endswith("_nosubfrac")}
    hB_ns = {k:v for k,v in hB.items() if k.endswith("_nosubfrac")}
    if hA_ns and hB_ns:
        out_dir_abs_ns = out_dir_mjj_abs_ns
        out_dir_norm_ns = out_dir_mjj_norm_ns
        combined_all_plot(
            hA_ns, hB_ns,
            labelA=dispA,
            labelB=dispB,
            out_dir=out_dir_abs_ns,
            mjj_min_cfg=mjj_min_cfg,
            mjj_max_cfg=mjj_max_cfg,
            bb_tol_deg=bb_tol_deg,
            mjj_require_backtoback=mjj_require_backtoback,
            ystar_title_suffix=ystar_title_suffix,
            R_list=COMBINED_R_LIST,
            ms=ms,
        )

    # ------------------------- Jet pT spectrum comparisons -------------------------
    if jA and jB:
        # Match by (kind, R) so we can overlay and ratio
        mapA: Dict[Tuple[str, float], Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]] = {}
        mapB: Dict[Tuple[str, float], Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]] = {}
        mapA_name: Dict[Tuple[str, float], str] = {}
        mapB_name: Dict[Tuple[str, float], str] = {}
        for hn, dat in jA.items():
            tag = parse_jetpt_name(hn)
            if tag:
                mapA[tag] = dat
                mapA_name[tag] = hn
        for hn, dat in jB.items():
            tag = parse_jetpt_name(hn)
            if tag:
                mapB[tag] = dat
                mapB_name[tag] = hn

        keys = sorted(set(mapA.keys()) & set(mapB.keys()), key=lambda t: (t[2], t[0], t[1]))
        _log(f"Jet spectrum overlays to write: {len(keys)}")

        # Decide which run is medium-like vs vacuum-like once, for ratio convention
        A_is_brick = _is_brick(runA)
        B_is_brick = _is_brick(runB)
        A_is_vac = _is_vacuum(runA)
        B_is_vac = _is_vacuum(runB)

        for kind, R, is_ns in keys:
            A = mapA[(kind, R, is_ns)]
            B = mapB[(kind, R, is_ns)]
            hnA = mapA_name[(kind, R, is_ns)]
            hnB = mapB_name[(kind, R, is_ns)]

            branch_ns = bool(is_ns) and (kind != 'incl')
            out_dir_jet_abs_local = out_dir_jetpt_abs_neutral if kind == 'incl' else (out_dir_jetpt_abs_ns if branch_ns else out_dir_jetpt_abs_sub)
            out_dir_jet_norm_local = out_dir_jetpt_unitshape_neutral if kind == 'incl' else (out_dir_jetpt_norm_ns if branch_ns else out_dir_jetpt_norm_sub)

            plot_jetpt_overlay(
                kind=kind, R=R,
                hnA=hnA, hnB=hnB,
                A=A, B=B,
                labelA=dispA,
                labelB=dispB,
                out_dir=out_dir_jet_abs_local,
                ms=ms,
                use_perdijet=False,
                is_inclusive=(kind == 'incl'),
                ratio_mode=args.ratio_mode,
                run_tag_a=runA,
                run_tag_b=runB,
            )
            A_norm = _single_slice_hist_for_norm(countA_hists, jA, hnA, label=dispA) if (SINGLE_SLICE_MODE and kind != 'incl') else A
            B_norm = _single_slice_hist_for_norm(countB_hists, jB, hnB, label=dispB) if (SINGLE_SLICE_MODE and kind != 'incl') else B
            plot_jetpt_overlay(
                kind=kind, R=R,
                hnA=hnA, hnB=hnB,
                A=A_norm, B=B_norm,
                labelA=dispA,
                labelB=dispB,
                out_dir=out_dir_jet_norm_local,
                ms=ms,
                use_perdijet=True,
                is_inclusive=(kind == 'incl'),
                ratio_mode=args.ratio_mode,
                run_tag_a=runA,
                run_tag_b=runB,
            )

            # Ratio convention
            if args.ratio_mode == "med":
                # medium/reference
                if A_is_brick and B_is_vac:
                    num, den = A, B
                    rlab = f"{dispA}/{dispB}"
                elif B_is_brick and A_is_vac:
                    num, den = B, A
                    rlab = f"{dispB}/{dispA}"
                else:
                    # fallback: assume B is the "medium" and A is the reference
                    num, den = B, A
                    rlab = f"{dispB}/{dispA}"
            else:
                # inv: reference/medium
                if A_is_vac and B_is_brick:
                    num, den = A, B
                    rlab = f"{dispA}/{dispB}"
                elif B_is_vac and A_is_brick:
                    num, den = B, A
                    rlab = f"{dispB}/{dispA}"
                else:
                    # fallback: assume A is the reference and B is medium, so inverse is A/B
                    num, den = A, B
                    rlab = f"{dispA}/{dispB}"
        _log("[INFO] Retired diagnostic skipped: ln(dσ/dp_T) jet-spectrum overlays/collages are disabled in this comparisor version.")
    else:
        _log("[INFO] No jet pT histograms found in merged ROOT. This usually means the analysis arrays ran with an older analyzer binary (stale analyze_dphi_sliced). Force a rebuild (delete the binary or set FORCE_REBUILD_ANALYZER=1) and re-run analysis + merge for both run tags.")



    # Decide which compare side is vacuum/reference vs medium for stacked dijet-observable layouts.
    A_is_vac = _is_vacuum(runA)
    B_is_vac = _is_vacuum(runB)
    A_is_brick = _is_brick(runA)
    B_is_brick = _is_brick(runB)

    if A_is_vac and B_is_brick:
        vac_tag, brick_tag = 'A', 'B'
        lab_v, lab_b = dispA, dispB
    elif B_is_vac and A_is_brick:
        vac_tag, brick_tag = 'B', 'A'
        lab_v, lab_b = dispB, dispA
    else:
        vac_tag, brick_tag = 'A', 'B'
        lab_v, lab_b = dispA, dispB

# ------------------------- Δφ_abs comparisons (0..π, standard) -------------------------
    _log("Reading Δφ_abs (0..π) histograms...")
    dA_abs = read_dphi_abs_hists(rootA)
    dB_abs = read_dphi_abs_hists(rootB)
    _log(f"Δφ_abs hists: A={len(dA_abs)}  B={len(dB_abs)}")

    # Use the same vacuum/reference vs medium mapping chosen above (vac_tag).
    if vac_tag == 'A':
        vac_abs, brick_abs = dA_abs, dB_abs
    else:
        vac_abs, brick_abs = dB_abs, dA_abs

    names_abs = sorted(set(vac_abs.keys()) & set(brick_abs.keys()))
    for hn in names_abs:
        tag = parse_dphi_abs_name(hn)
        if not tag:
            continue
        Rv, lo, hi, isAll = tag
        is_ns = hn.endswith('_nosubfrac')
        out_dir_dphiabs_norm_local = out_dir_dphiabs_norm_ns if is_ns else out_dir_dphiabs_norm_sub
        out_dir_dphiabs_abs_local  = out_dir_dphiabs_abs_ns if is_ns else out_dir_dphiabs_abs_sub
        countA = countB = None
        if SINGLE_SLICE_MODE:
            try:
                countA = SELECTED_DIJET_COUNTS_A.count_for("dphi", Rv, is_nosubfrac=is_ns, ptlo=(None if isAll else lo), pthi=(None if isAll else hi), is_abs=True)
                countB = SELECTED_DIJET_COUNTS_B.count_for("dphi", Rv, is_nosubfrac=is_ns, ptlo=(None if isAll else lo), pthi=(None if isAll else hi), is_abs=True)
                if vac_tag == 'B':
                    countA, countB = countB, countA
            except Exception as e:
                _die(f"[single-slice] {hn}: failed to resolve |Δφ| selected dijet counts: {e}")
        vac_abs_norm = _single_slice_hist_for_norm((countA_hists if vac_tag == 'A' else countB_hists), vac_abs, hn, label=lab_v) if SINGLE_SLICE_MODE else vac_abs[hn]
        brick_abs_norm = _single_slice_hist_for_norm((countB_hists if vac_tag == 'A' else countA_hists), brick_abs, hn, label=lab_b) if SINGLE_SLICE_MODE else brick_abs[hn]
        plot_dphi_stacked(
            hn,
            vac_abs_norm,
            brick_abs_norm,
            label_vac=lab_v,
            label_brick=lab_b,
            out_dir=out_dir_dphiabs_norm_local,
            xsec_band_vac=(XSEC_BAND_A if vac_tag == 'A' else XSEC_BAND_B),
            xsec_band_brick=(XSEC_BAND_B if vac_tag == 'A' else XSEC_BAND_A),
            ini=cfg,
            ratio_mode=args.ratio_mode,
            ms=ms,
            use_perdijet=True,
            count_vac=countA,
            count_brick=countB,
        )

        plot_dphi_stacked(
            hn,
            vac_abs[hn],
            brick_abs[hn],
            label_vac=lab_v,
            label_brick=lab_b,
            out_dir=out_dir_dphiabs_abs_local,
            xsec_band_vac=(XSEC_BAND_A if vac_tag == 'A' else XSEC_BAND_B),
            xsec_band_brick=(XSEC_BAND_B if vac_tag == 'A' else XSEC_BAND_A),
            ini=cfg,
            ratio_mode=args.ratio_mode,
            ms=ms,
            use_perdijet=False,
        )


    # ------------------------- |Δφ| vs |Δη| TH2 comparisons -------------------------
    _log("Reading |Δφ| vs |Δη| TH2 histograms...")
    h2dphiA = read_dphi_abs_vs_deta_h2_hists(rootA)
    h2dphiB = read_dphi_abs_vs_deta_h2_hists(rootB)
    _log(f"|Δφ| vs |Δη| TH2 hists: A={len(h2dphiA)}  B={len(h2dphiB)}")

    if vac_tag == 'A':
        vac_h2dphi, brick_h2dphi = h2dphiA, h2dphiB
    else:
        vac_h2dphi, brick_h2dphi = h2dphiB, h2dphiA

    shared_h2dphi = sorted(set(vac_h2dphi.keys()) & set(brick_h2dphi.keys()))
    if not shared_h2dphi:
        _log("[WARN] No shared |Δφ| vs |Δη| TH2 maps found; skipping dphi_abs_vs_deta comparisons")
    for hn in shared_h2dphi:
        parsed = parse_dphi_abs_vs_deta_h2_name(hn)
        if parsed is None:
            continue
        _Rtmp, _lo, _hi, _is_all, is_ns = parsed
        out_dir_dphiabs_deta_local = out_dir_dphiabs_deta_ns if is_ns else out_dir_dphiabs_deta_sub
        plot_dphi_abs_vs_deta_h2_compare(
            hn,
            vac_h2dphi[hn],
            brick_h2dphi[hn],
            label_vac=lab_v,
            label_med=lab_b,
            out_dir=out_dir_dphiabs_deta_local,
            ratio_mode=args.ratio_mode,
        )

    # ------------------------- Particle-level accepted-constituent comparisons -------------------------
    _log("Reading particle-level histograms...")
    pA = read_particle_hists(rootA)
    pB = read_particle_hists(rootB)
    _log(f"particle-level hists: A={len(pA)}  B={len(pB)}")

    if vac_tag == 'A':
        vac_p, brick_p = pA, pB
    else:
        vac_p, brick_p = pB, pA

    particle_names = sorted(set(vac_p.keys()) & set(brick_p.keys()))
    if not particle_names:
        _log("[WARN] No shared particle-level histograms found; skipping plots/particle_level comparisons")
    for hn in particle_names:
        if parse_particle_name(hn) is None:
            continue
        plot_particle_overlay(
            hn,
            vac_p[hn],
            brick_p[hn],
            label_vac=lab_v,
            label_med=lab_b,
            out_dir=out_dir_particle,
            xsec_band_vac=(XSEC_BAND_A if vac_tag == 'A' else XSEC_BAND_B),
            xsec_band_med=(XSEC_BAND_B if vac_tag == 'A' else XSEC_BAND_A),
            ms=ms,
        )


    # ------------------------- Lead-vs-subleading jet correlation comparisons -------------------------
    _log("Reading lead-vs-subleading jet correlation histograms...")
    h2A = read_sublead_vs_lead_h2_hists(rootA)
    h2B = read_sublead_vs_lead_h2_hists(rootB)
    profA = read_sublead_vs_lead_profile_hists(rootA)
    profB = read_sublead_vs_lead_profile_hists(rootB)
    _log(f"lead-vs-sublead TH2 hists: A={len(h2A)}  B={len(h2B)}")
    _log(f"lead-vs-sublead TProfile hists: A={len(profA)}  B={len(profB)}")

    if vac_tag == 'A':
        vac_h2, brick_h2 = h2A, h2B
        vac_prof, brick_prof = profA, profB
    else:
        vac_h2, brick_h2 = h2B, h2A
        vac_prof, brick_prof = profB, profA

    shared_h2 = sorted(set(vac_h2.keys()) & set(brick_h2.keys()))
    if not shared_h2:
        _log("[WARN] No shared TH2 lead-vs-subleading jet maps found; skipping lead_sublead_correlation TH2 comparisons")
    for hn in shared_h2:
        parsed = parse_sublead_vs_lead_h2_name(hn)
        if parsed is None:
            continue
        _Rtmp, is_ns = parsed
        out_dir_lead_sublead_local = out_dir_lead_sublead_corr_ns if is_ns else out_dir_lead_sublead_corr_sub
        plot_sublead_vs_lead_h2_compare(
            hn,
            vac_h2[hn],
            brick_h2[hn],
            label_vac=lab_v,
            label_med=lab_b,
            out_dir=out_dir_lead_sublead_local,
            ratio_mode=args.ratio_mode,
        )

    shared_prof = sorted(set(vac_prof.keys()) & set(brick_prof.keys()))
    if not shared_prof:
        _log("[WARN] No shared TProfile lead-vs-subleading jet curves found; skipping lead_sublead_correlation profile comparisons")
    for hn in shared_prof:
        parsed = parse_sublead_vs_lead_profile_name(hn)
        if parsed is None:
            continue
        _Rtmp, is_ns = parsed
        out_dir_lead_sublead_local = out_dir_lead_sublead_corr_ns if is_ns else out_dir_lead_sublead_corr_sub
        plot_sublead_vs_lead_profile_compare(
            hn,
            vac_prof[hn],
            brick_prof[hn],
            label_vac=lab_v,
            label_med=lab_b,
            out_dir=out_dir_lead_sublead_local,
            ratio_mode=args.ratio_mode,
            ms=ms,
        )

# ------------------------- Dijet imbalance comparisons (xJ, AJ) -------------------------
    _log("Reading xJ/AJ histograms...")
    iA = read_imbalance_hists(rootA)
    iB = read_imbalance_hists(rootB)
    _log(f"xJ/AJ hists: A={len(iA)}  B={len(iB)}")

    # use same top/bottom mapping as Δφ
    if vac_tag == 'A':
        vac_i, brick_i = iA, iB
    else:
        vac_i, brick_i = iB, iA

    names = sorted(set(vac_i.keys()) & set(brick_i.keys()))
    for hn in names:
        parsed_tag = parse_xj_name(hn) if hn.startswith("xj_") else (parse_aj_name(hn) if hn.startswith("aj_") else None)
        if parsed_tag is None:
            continue
        Rv, ptlo, pthi, is_fullrange = parsed_tag
        is_ns = hn.endswith('_nosubfrac')
        out_dir_imb_norm_local = out_dir_imb_norm_ns if is_ns else out_dir_imb_norm_sub
        out_dir_imb_abs_local  = out_dir_imb_abs_ns if is_ns else out_dir_imb_abs_sub
        countA = countB = None
        if SINGLE_SLICE_MODE:
            try:
                obs_key = "aj" if hn.startswith("aj_") else "xj"
                c_ptlo = None if is_fullrange else ptlo
                c_pthi = None if is_fullrange else pthi
                countA = SELECTED_DIJET_COUNTS_A.count_for(obs_key, Rv, is_nosubfrac=is_ns, ptlo=c_ptlo, pthi=c_pthi)
                countB = SELECTED_DIJET_COUNTS_B.count_for(obs_key, Rv, is_nosubfrac=is_ns, ptlo=c_ptlo, pthi=c_pthi)
                if vac_tag == 'B':
                    countA, countB = countB, countA
            except Exception as e:
                _die(f"[single-slice] {hn}: failed to resolve imbalance selected dijet counts: {e}")
        vac_i_norm = _single_slice_hist_for_norm((countA_hists if vac_tag == 'A' else countB_hists), vac_i, hn, label=lab_v) if SINGLE_SLICE_MODE else vac_i[hn]
        brick_i_norm = _single_slice_hist_for_norm((countB_hists if vac_tag == 'A' else countA_hists), brick_i, hn, label=lab_b) if SINGLE_SLICE_MODE else brick_i[hn]
        plot_imbalance_stacked(
            hn,
            vac_i_norm,
            brick_i_norm,
            label_vac=lab_v,
            label_brick=lab_b,
            out_dir=out_dir_imb_norm_local,
            xsec_band_vac=(XSEC_BAND_A if vac_tag == 'A' else XSEC_BAND_B),
            xsec_band_brick=(XSEC_BAND_B if vac_tag == 'A' else XSEC_BAND_A),
            ratio_mode=args.ratio_mode,
            ms=ms,
            use_perdijet=True,
            count_vac=countA,
            count_brick=countB,
        )

        plot_imbalance_stacked(
            hn,
            vac_i[hn],
            brick_i[hn],
            label_vac=lab_v,
            label_brick=lab_b,
            out_dir=out_dir_imb_abs_local,
            xsec_band_vac=(XSEC_BAND_A if vac_tag == 'A' else XSEC_BAND_B),
            xsec_band_brick=(XSEC_BAND_B if vac_tag == 'A' else XSEC_BAND_A),
            ratio_mode=args.ratio_mode,
            ms=ms,
            use_perdijet=False,
        )

    # ------------------------- Jet-R dependence: first configured R over each later configured R + double ratios -------------------------
    if jA and jB:
        # mapA/mapB are already built above if we had jet spectra; if not, build quickly
        if 'mapA' not in locals():
            mapA = {parse_jetpt_name(hn): dat for hn,dat in jA.items() if parse_jetpt_name(hn)}
            mapB = {parse_jetpt_name(hn): dat for hn,dat in jB.items() if parse_jetpt_name(hn)}

        # keep it minimal: inclusive jets are branch-neutral; leading jets follow fitter-style subfrac/nosubfrac dirs.
        plot_jetR_ratio_compare('incl', mapA, mapB, labelA=dispA, labelB=dispB, out_dir=out_dir_jetR, ms=ms, branch_ns=None, ratio_mode=args.ratio_mode, run_tag_a=runA, run_tag_b=runB)
        plot_jetR_ratio_compare('lead', mapA, mapB, labelA=dispA, labelB=dispB, out_dir=out_dir_jetR_sub, ms=ms, branch_ns=False, ratio_mode=args.ratio_mode, run_tag_a=runA, run_tag_b=runB)
        plot_jetR_ratio_compare('lead', mapA, mapB, labelA=dispA, labelB=dispB, out_dir=out_dir_jetR_ns, ms=ms, branch_ns=True, ratio_mode=args.ratio_mode, run_tag_a=runA, run_tag_b=runB)
    else:
        _log("[WARN] Jet pT histograms missing (or analyzer too old) -> skipping jet spectra / jet-R plots")

    _log_plot_write_summary()
    _log("Done (paper-ready comparisor).")
    try:
        if _LOG_FH:
            _LOG_FH.close()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    finally:
        try:
            if "_LOG_FH" in globals() and _LOG_FH:
                _LOG_FH.close()
        except Exception:
            pass
