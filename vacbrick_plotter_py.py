#!/usr/bin/env python3
# vacbrick_plotter_py.py v1.6
# CHANGELOG
# v1.6 (true single-slice count normalization + qhat label context):
#   • FIX: In SINGLE_SLICE_MODE dijet_normalized multibrick plots, prefer analyzer counts/count_* TH1 inputs so the plotted quantity is true (1/N_dijet,sel)dN/dX.
#   • FALLBACK: Old merged ROOT files without count_* histograms still plot with a warning using the legacy weighted input.
#   • FIX: Plot-facing qhat0 labels now mark the scan knob as toy qhat0 instead of showing a bare unlabeled number.
#   • SAFETY: Absolute plots, multi-slice per-selection normalization, ROOT input routing, sim/analysis/merge behavior, and grouped plot structure are unchanged.
# v1.5 (crash diagnostics + load-stage breadcrumbs):
#   • LOGS: Add Python faulthandler, SIGTERM/SIGUSR1 stack dumps, and unhandled-exception traceback logging to the driver-provided traceback log.
#   • LOGS: Add run/root/xsec/count-loading breadcrumbs before expensive I/O so hangs and Slurm kills no longer look silent in vacbrick_plotter_py.log.
#   • SAFETY: No histogram math, count normalization, plotting labels, ROOT input contract, or output folder routing changed.
# v1.4 (single-slice count labels):
#   • FIX: In SINGLE_SLICE_MODE dijet_normalized multibrick plots, append the selected-dijet denominator for vacuum and each brick configuration to the top-panel legends.
#   • KEEP: Existing single-slice normalization remains y/N_dijet,sel and multi-slice normalization remains unit-shape/per-selection.
#   • SAFETY: Plot labels only; no ROOT input contract, histogram math, sim/analysis/merge behavior, or SLURM routing changed.
# v1.3 (paperready formatting parity patch):
#   • FIX: Initialize the same paperready ratio-panel y-axis controls from jetscape.ini for Mjj, jet pT, |Delta phi|, xJ, AJ, jet-R, and lead/sublead profile plots.
#   • FIX: Apply DPHI_ABS_COMPARE_RATIO_REBIN_FACTOR to multibrick |Delta phi| ratio panels exactly as a ratio-only density-preserving rebin, keeping the top overlay unrebinned.
#   • FIX: Use paperready save/caption/tight-layout helpers so bottom Figure captions, wrapped titles, bbox handling, and warning suppression match paperreadycomparisor output style.
#   • FIX: Write explicit placeholder PNGs for unavailable multibrick plots/ratios instead of silently skipping missing or undefined outputs.
#   • LOGS: Add paperready-style final plot-write summary with real vs placeholder counts and bucket counts.
#   • SAFETY: Plotter-only update; no sim, analysis, merge, ROOT contract, histogram definitions, or physics cuts changed.
# v1.2 (paperready-style multibrick ratios + fully dynamic grids):
#   • NEW: Add paperready-style bottom ratio panels for multibrick 1D comparison plots where the two-run paperready comparisor has ratio panels.
#   • NEW: Ratio panels draw one curve per medium variation as brick-variation/vacuum, with the varying L or qhat0 value in the legend.
#   • NEW: Add medium/vacuum ratio-map grids for 2D lead-sublead and |Delta phi| vs |Delta eta| maps.
#   • FIX: 2D grids now adapt to any nonempty number of medium variants instead of assuming vacuum + exactly three brick curves.
#   • KEEP: Particle-level QA and absolute imbalance plots remain overlay-only because the paperready comparisor also treats those as overlay/no-ratio outputs.
#   • SAFETY: Plotter-only update; no sim, analysis, merge, ROOT contract, or histogram-production code changed.
# v1.1 (flexible multisim grid + analyzer v9.8.0 compatibility):
#   • CHANGE: Accept any nonempty MultiSimBrickLengths and MultiSimQhat0Values arrays instead of hard-requiring exactly 3x3.
#   • CHANGE: Grouped overlays now build vacuum + all configured variants for each fixed qhat0 or fixed brick length; marker/color/line styles cycle safely for longer arrays.
#   • FIX: |Delta phi| vs |Delta eta| map colorbars now label the bin-area-normalized differential density instead of mb/bin yield.
#   • NOTE: Superseded by v1.2 for 1D observable ratio panels; jet-R plots remain R_num/R_den within each run.
#   • SAFETY: No upstream sim/analysis/merge job control or histogram math changed.
# v1.0 (vacuum + 3-way medium grouped multisim plotter):
#   • NEW: Read one vacuum merged ROOT and the configured multisim brick merged ROOTs, then build grouped comparison outputs for every supported observable family.
#   • NEW: For each observable, render fixed-qhat0 overlays (vacuum + configured brick lengths) and fixed-length overlays (vacuum + configured qhat0 values).
#   • NEW: Mirror the existing branch taxonomy under group-specific folders so subfrac/nosubfrac, absolute/dijet_normalized, particle_level, lead_sublead_correlation, and jet_R_dependence stay organized consistently.
#   • NEW: Keep the legacy 2-run paperreadycomparisor untouched; this script is only for MultiSimEnabled=1 via vacbrick_plotter.sh.
#   • LOGS: Write detailed discovery / plotting logs to compare_dir/logs/vacbrick_plotter_py.log.
#   • SAFETY: No upstream sim/analysis/merge contracts changed; the script hard-fails on missing canonical final/dphi_allSlices.root inputs instead of auto-discovering stale ROOT files.
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
import traceback
import faulthandler
try:
    import signal
except Exception:  # pragma: no cover
    signal = None
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from matplotlib.gridspec import GridSpec

from xscape_ini import read_ini, expand_vars
import paperreadycomparisor_py as prc


# ---------- logging ----------
_LOG_FH = None
_TRACE_FH = None

def _ts() -> str:
    return prc._ts() if hasattr(prc, '_ts') else __import__('datetime').datetime.now().strftime('%F %T')

def _log(msg: str) -> None:
    s = f"[{_ts()}] {msg}"
    print(s)
    global _LOG_FH
    if _LOG_FH is not None:
        _LOG_FH.write(s + "\n")
        _LOG_FH.flush()



def _setup_crash_logging() -> None:
    """Enable deterministic traceback/fault logging for Slurm jobs."""
    global _TRACE_FH
    trace_path = str(os.environ.get('VACBRICK_PLOTTER_TRACE_LOG', '') or '').strip()
    if trace_path:
        try:
            os.makedirs(os.path.dirname(trace_path), exist_ok=True)
            _TRACE_FH = open(trace_path, 'a', encoding='utf-8', buffering=1)
            _TRACE_FH.write(f"[{_ts()}] [trace] enabled for pid={os.getpid()} argv={sys.argv!r}\n")
            faulthandler.enable(file=_TRACE_FH, all_threads=True)
            if signal is not None:
                for sig_name in ('SIGTERM', 'SIGUSR1'):
                    sig = getattr(signal, sig_name, None)
                    if sig is None:
                        continue
                    try:
                        faulthandler.register(sig, file=_TRACE_FH, all_threads=True, chain=True)
                        _TRACE_FH.write(f"[{_ts()}] [trace] registered {sig_name} stack dump\n")
                    except Exception as exc:
                        _TRACE_FH.write(f"[{_ts()}] [trace][WARN] could not register {sig_name}: {exc}\n")
        except Exception as exc:
            _log(f"[WARN] Could not enable traceback/fault logging at {trace_path}: {exc}")

    def _excepthook(exc_type, exc, tb):
        msg = f"[FATAL] unhandled exception: {exc_type.__name__}: {exc}"
        try:
            _log(msg)
        except Exception:
            print(f"[{_ts()}] {msg}", file=sys.stderr)
        for fh in (_LOG_FH, _TRACE_FH):
            if fh is None:
                continue
            try:
                fh.write(f"[{_ts()}] {msg}\n")
                traceback.print_exception(exc_type, exc, tb, file=fh)
                fh.flush()
            except Exception:
                pass
        sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = _excepthook

def _die(msg: str, code: int = 2) -> int:
    _log(f"[FATAL] {msg}")
    return code


def _save_plot(fig, out_path: str, *, placeholder: bool = False) -> None:
    """Save through paperreadycomparisor's figure pipeline so caption/bbox/counting stay consistent."""
    prc._save_figure(fig, out_path, dpi=170, placeholder=placeholder)
    _log(f"[plot] saved {'placeholder ' if placeholder else ''}{out_path}")


def _write_placeholder(out_path: str, title: str, reason: str, *, ylabel: Optional[str] = None) -> None:
    """Paperready-style explicit placeholder for unavailable multibrick outputs."""
    prc._write_unavailable_placeholder(out_path, title=title, reason=reason, ylabel=ylabel)
    _log(f"[plot] saved placeholder {out_path}")


def _set_caption(fig, title: str, *, max_chars: int = 118) -> str:
    return prc._set_paperready_caption(fig, title, max_chars=max_chars)


def _tight(fig, *, rect=None) -> None:
    prc._safe_tight_layout(fig, rect=rect)


def _parse_positive_int_cfg(cfg: dict, key: str, default: int = 1) -> int:
    raw = str(cfg.get(key, str(default)) or '').strip()
    if raw == '':
        return int(default)
    try:
        val = int(float(raw))
    except Exception:
        raise ValueError(f"Invalid {key}={raw!r}; expected positive integer")
    if val < 1:
        raise ValueError(f"Invalid {key}={raw!r}; expected integer >= 1")
    return val


def _parse_required_ratio_ylim(cfg: dict, kind: str) -> Tuple[float, float]:
    y_min_key = f"{kind}_COMPARE_RATIO_YMIN"
    y_max_key = f"{kind}_COMPARE_RATIO_YMAX"
    raw_min = str(cfg.get(y_min_key, '') or '').strip()
    raw_max = str(cfg.get(y_max_key, '') or '').strip()
    if raw_min == '' or raw_max == '':
        raise ValueError(f"Missing required ratio y-range keys for {kind}: {y_min_key}/{y_max_key}")
    try:
        y_min = float(raw_min)
        y_max = float(raw_max)
    except Exception:
        raise ValueError(f"Invalid {kind} ratio y-range: {y_min_key}={raw_min!r}, {y_max_key}={raw_max!r}")
    if not (np.isfinite(y_min) and np.isfinite(y_max) and y_max > y_min):
        raise ValueError(f"Invalid {kind} ratio y-range: require finite {y_max_key}>{y_min_key}, got [{y_min}, {y_max}]")
    if not (y_min <= 1.0 <= y_max):
        raise ValueError(f"Invalid {kind} ratio y-range: require range to contain unity, got [{y_min}, {y_max}]")
    return y_min, y_max


def _init_paperready_globals_from_cfg(cfg: dict, jet_radii: Sequence[float]) -> None:
    """Mirror paperreadycomparisor's style/range globals for the multibrick plotter."""
    prc.PAPERREADY_SHOW_CAPTION = bool(int(str(cfg.get('PAPERREADY_SHOW_CAPTION', '1')).strip() or '1'))
    prc.CFG_FOR_TITLES = dict(cfg)
    prc.PERDIJET_COV_MODE = str(cfg.get('PERDIJET_COV_MODE', 'diag')).strip() or 'diag'
    prc.DPHI_RATIO_REBIN_FACTOR = _parse_positive_int_cfg(cfg, 'DPHI_COMPARE_RATIO_REBIN_FACTOR', default=1)
    prc.DPHI_ABS_RATIO_REBIN_FACTOR = _parse_positive_int_cfg(cfg, 'DPHI_ABS_COMPARE_RATIO_REBIN_FACTOR', default=1)
    prc.RATIO_YLIMS = {
        'MJJ': _parse_required_ratio_ylim(cfg, 'MJJ'),
        'JETPT': _parse_required_ratio_ylim(cfg, 'JETPT'),
        'DPHI': _parse_required_ratio_ylim(cfg, 'DPHI'),
        'DPHI_ABS': _parse_required_ratio_ylim(cfg, 'DPHI_ABS'),
        'XJ': _parse_required_ratio_ylim(cfg, 'XJ'),
        'AJ': _parse_required_ratio_ylim(cfg, 'AJ'),
        'JETR': _parse_required_ratio_ylim(cfg, 'JETR'),
        'LEAD_SUBLEAD_PROFILE': _parse_required_ratio_ylim(cfg, 'LEAD_SUBLEAD_PROFILE'),
    }
    try:
        prc.JET_PT_MAX_CFG = float(str(cfg.get('JET_PT_MAX', 'nan')).strip() or 'nan')
    except Exception:
        prc.JET_PT_MAX_CFG = float('nan')
    try:
        prc.EXACT_TWO_JETS_REQUIRED = bool(int(str(cfg.get('DIJET_REQUIRE_EXACTLY_TWO_JETS', '0')).strip() or '0'))
    except Exception:
        prc.EXACT_TWO_JETS_REQUIRED = False
    try:
        prc.IMBALANCE_REQUIRE_BACKTOBACK = bool(int(float(str(cfg.get('IMBALANCE_REQUIRE_BACKTOBACK', '0')).strip() or '0')))
    except Exception:
        prc.IMBALANCE_REQUIRE_BACKTOBACK = False
    try:
        prc.IMBALANCE_BACKTOBACK_TOL_DEG = float(str(cfg.get('IMBALANCE_BACKTOBACK_TOL_DEG', 'nan')).strip() or 'nan')
    except Exception:
        prc.IMBALANCE_BACKTOBACK_TOL_DEG = float('nan')
    prc.JET_RADIUS_COMPARE_PAIRS = []
    uniq_r = sorted({round(float(r), 6) for r in jet_radii})
    if len(uniq_r) >= 2:
        prc.JET_RADIUS_COMPARE_PAIRS = [(uniq_r[i], uniq_r[0]) for i in range(1, len(uniq_r))]
    # Reset paperready plot counters for this standalone multibrick run.
    try:
        prc._PLOT_WRITE_COUNTS = {'real': 0, 'placeholder': 0}
        prc._PLOT_WRITE_BY_BUCKET = {'real': prc.Counter(), 'placeholder': prc.Counter()}
    except Exception:
        pass
    _log(f"[cfg] PAPERREADY_SHOW_CAPTION={int(prc.PAPERREADY_SHOW_CAPTION)}")
    _log(f"[cfg] DPHI_COMPARE_RATIO_REBIN_FACTOR={prc.DPHI_RATIO_REBIN_FACTOR}")
    _log(f"[cfg] DPHI_ABS_COMPARE_RATIO_REBIN_FACTOR={prc.DPHI_ABS_RATIO_REBIN_FACTOR}")
    for key, val in sorted(prc.RATIO_YLIMS.items()):
        _log(f"[cfg] {key}_COMPARE_RATIO_YRANGE=[{val[0]}, {val[1]}]")


def _log_plot_summary() -> None:
    try:
        real = int(prc._PLOT_WRITE_COUNTS.get('real', 0))
        placeholder = int(prc._PLOT_WRITE_COUNTS.get('placeholder', 0))
        _log(f"[summary] plot files written: total={real + placeholder} real={real} placeholders={placeholder}")
        for kind in ('real', 'placeholder'):
            bucket_counts = prc._PLOT_WRITE_BY_BUCKET.get(kind, {})
            if not bucket_counts:
                continue
            parts = [f"{bucket}={int(count)}" for bucket, count in sorted(bucket_counts.items())]
            _log(f"[summary] {kind} plot counts by bucket: " + ', '.join(parts))
    except Exception as exc:
        _log(f"[WARN] could not summarize plot counts: {exc}")


# ---------- constants / styling ----------
VAC_COLOR = '#FF0000'   # requested visible red
MED_COLORS = ['#0000FF', '#008000', '#8000FF', '#00AAAA', '#CC6600', '#AA00AA']  # cycles for arbitrary MultiSim arrays
MARKERS = ['o', 's', '^', 'D', 'v', 'P', 'X', '*']
LINESTYLES = ['-', '--', '-.', ':']


@dataclass
class RunSet:
    tag: str
    label: str
    root_path: str
    final_dir: str
    is_vacuum: bool
    brick_length: Optional[float]
    qhat0: Optional[float]
    xsec_band: Optional[object] = None
    selected_counts: Optional[object] = None
    mjj: Optional[Dict[str, tuple]] = None
    jetpt: Optional[Dict[str, tuple]] = None
    dphi_abs: Optional[Dict[str, tuple]] = None
    imbalance: Optional[Dict[str, tuple]] = None
    count_density: Optional[Dict[str, tuple]] = None
    particle: Optional[Dict[str, tuple]] = None
    lead_sublead_prof: Optional[Dict[str, tuple]] = None
    lead_sublead_h2: Optional[Dict[str, tuple]] = None
    dphi_abs_vs_deta_h2: Optional[Dict[str, tuple]] = None


@dataclass
class GroupSpec:
    kind: str  # by_qhat | by_length
    fixed_value: float
    runs: List[RunSet]  # vacuum first, then configured medium runs
    out_root: str

    @property
    def fixed_tag(self) -> str:
        return f"q{sanitize_tag_value(self.fixed_value)}" if self.kind == 'by_qhat' else f"L{sanitize_tag_value(self.fixed_value)}"

    @property
    def fixed_title(self) -> str:
        if self.kind == 'by_qhat':
            return f"toy qhat0={self.fixed_value:g}"
        return rf"$L={self.fixed_value:g}\,\mathrm{{fm}}$"

    @property
    def varying_title(self) -> str:
        return "brick length" if self.kind == 'by_qhat' else "toy qhat0"


def sanitize_tag_value(raw: float | str) -> str:
    s = str(raw).strip().replace(' ', '')
    s = s.replace('.', 'p').replace('-', '_m_')
    return s


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _label_for_run(run: RunSet, group_kind: str) -> str:
    if run.is_vacuum:
        return run.label
    if group_kind == 'by_qhat':
        return f"L={run.brick_length:g} fm"
    return f"toy qhat0={run.qhat0:g}"


def _label_for_run_with_count(run: RunSet, group_kind: str, hist_name: str, family: str, mode: str) -> str:
    label = _label_for_run(run, group_kind)
    if mode == 'dijet_normalized' and prc.SINGLE_SLICE_MODE:
        try:
            count = _resolve_single_slice_count(run, hist_name, 'jetpt_sel' if family == 'jetpt' else family)
            if count is not None and int(count) >= 0:
                return f"{label} (N_dijet,sel={int(count)})"
        except Exception as exc:
            _log(f"[WARN] selected-dijet legend count unavailable for {run.tag}:{hist_name}:{family}: {exc}")
    return label


def _color_for_index(idx: int) -> str:
    if idx == 0:
        return VAC_COLOR
    return MED_COLORS[(idx - 1) % len(MED_COLORS)]


def _style_for_index(idx: int) -> tuple:
    return _color_for_index(idx), MARKERS[idx % len(MARKERS)], LINESTYLES[idx % len(LINESTYLES)]


def _run_root_and_final(cfg: dict, run_tag: str) -> Tuple[str, str, str]:
    run_base = str(cfg.get('RUNS_BASE', f"{os.path.expanduser('~')}/xscape_runs/{cfg.get('RUN_TAG','')}"))
    run_base = expand_vars(run_base, cfg)
    runs_root = run_base.rsplit('/' + str(cfg.get('RUN_TAG', '')), 1)[0] if str(cfg.get('RUN_TAG', '')) and run_base.endswith('/' + str(cfg.get('RUN_TAG'))) else str(Path(run_base).parent)
    if not runs_root:
        runs_root = os.path.join(os.path.expanduser('~'), 'xscape_runs')
    run_dir = os.path.join(runs_root, run_tag)
    final_dir = os.path.join(run_dir, 'final')
    root_path = os.path.join(final_dir, 'dphi_allSlices.root')
    return runs_root, run_dir, root_path


def _load_run(cfg: dict, run_tag: str, *, label: str, is_vacuum: bool, brick_length: Optional[float], qhat0: Optional[float], include_xsec_err: bool, single_slice_mode: bool, jet_radii: List[float], pt_edges: List[float]) -> RunSet:
    _log(f"[load] begin run={run_tag} label={label!r} is_vacuum={int(is_vacuum)} L={brick_length} qhat0={qhat0}")
    runs_root, run_dir, root_path = _run_root_and_final(cfg, run_tag)
    _log(f"[load] expected run_dir={run_dir}")
    _log(f"[load] expected root={root_path}")
    if not os.path.isdir(run_dir):
        raise RuntimeError(f"Run directory missing for {run_tag}: {run_dir}")
    resolved_root = prc.find_best_root_for_run(run_dir, root_path)
    if not resolved_root or not os.path.isfile(resolved_root):
        raise RuntimeError(f"Missing canonical final ROOT for {run_tag}: {root_path}")
    _log(f"[load] canonical root resolved for {run_tag}: {resolved_root}")
    final_dir = os.path.dirname(resolved_root)
    xsec_band = None
    if include_xsec_err:
        _log(f"[xsec] building xsec normalization band for {run_tag} from final_dir={final_dir}")
        t0 = time.time()
        xsec_band = prc.SliceNormBandBuilder(final_dir, label=run_tag)
        _log(f"[xsec] finished xsec normalization band for {run_tag} in {time.time() - t0:.1f} s")
    selected_counts = None
    if single_slice_mode:
        _log(f"[counts] loading selected dijet counts for {run_tag} from final_dir={final_dir}")
        selected_counts, counts_path = prc.SelectedDijetCountResolver.load(final_dir, jet_radii, pt_edges)
        _log(f"[counts] loaded selected dijet counts for {run_tag}: {counts_path}")
    return RunSet(
        tag=run_tag,
        label=label,
        root_path=resolved_root,
        final_dir=final_dir,
        is_vacuum=is_vacuum,
        brick_length=brick_length,
        qhat0=qhat0,
        xsec_band=xsec_band,
        selected_counts=selected_counts,
    )


def _ensure_hist_cache(run: RunSet) -> None:
    if run.mjj is None:
        _log(f"[read] loading histograms for {run.tag}")
        run.mjj = prc.read_mjj_hists(run.root_path)
        run.jetpt = prc.read_jetpt_hists(run.root_path)
        run.dphi_abs = prc.read_dphi_abs_hists(run.root_path)
        run.imbalance = prc.read_imbalance_hists(run.root_path)
        run.count_density = prc.read_count_density_hists(run.root_path) if prc.SINGLE_SLICE_MODE else {}
        run.particle = prc.read_particle_hists(run.root_path)
        run.lead_sublead_prof = prc.read_sublead_vs_lead_profile_hists(run.root_path)
        run.lead_sublead_h2 = prc.read_sublead_vs_lead_h2_hists(run.root_path)
        run.dphi_abs_vs_deta_h2 = prc.read_dphi_abs_vs_deta_h2_hists(run.root_path)


def _finite_positive(vals: np.ndarray) -> np.ndarray:
    arr = np.asarray(vals, dtype=float)
    return arr[np.isfinite(arr) & (arr > 0)]


def _resolve_single_slice_count(run: RunSet, hist_name: str, family: str):
    if run.selected_counts is None:
        return None
    is_ns = hist_name.endswith('_nosubfrac')
    if family == 'mjj':
        parsed = prc.parse_mjj_name(hist_name)
        if parsed is None:
            return None
        Rv, lo, hi, is_all = parsed
        return run.selected_counts.count_for('mjj', Rv, is_nosubfrac=is_ns, ptlo=None if is_all else lo, pthi=None if is_all else hi)
    if family == 'dphi_abs':
        parsed = prc.parse_dphi_abs_name(hist_name)
        if parsed is None:
            return None
        Rv, lo, hi, is_all = parsed
        return run.selected_counts.count_for('dphi', Rv, is_nosubfrac=is_ns, ptlo=None if is_all else lo, pthi=None if is_all else hi, is_abs=True)
    if family == 'xj':
        parsed = prc.parse_xj_name(hist_name)
        if parsed is None:
            return None
        Rv, lo, hi, is_all = parsed
        return run.selected_counts.count_for('xj', Rv, is_nosubfrac=is_ns, ptlo=None if is_all else lo, pthi=None if is_all else hi)
    if family == 'aj':
        parsed = prc.parse_aj_name(hist_name)
        if parsed is None:
            return None
        Rv, lo, hi, is_all = parsed
        return run.selected_counts.count_for('aj', Rv, is_nosubfrac=is_ns, ptlo=None if is_all else lo, pthi=None if is_all else hi)
    if family == 'jetpt_sel':
        parsed = prc.parse_jetpt_name(hist_name)
        if parsed is None:
            return None
        kind, Rv, is_ns = parsed
        if kind == 'incl':
            return None
        return run.selected_counts.count_for('sel', Rv, is_nosubfrac=is_ns)
    return None


def _normalize_hist(run: RunSet, hist_name: str, hist: tuple, *, family: str, mode: str, single_slice_mode: bool) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    if mode == 'dijet_normalized' and single_slice_mode:
        count_map = run.count_density if isinstance(run.count_density, dict) else {}
        if hist_name in count_map:
            hist = count_map[hist_name]
        else:
            _log(f"[WARN] SINGLE_SLICE_MODE true dN normalization requested, but count-density histogram is missing for {run.tag}:{hist_name}; falling back to legacy weighted histogram.")
    xc, y, e, bw, _entries = hist
    xc = np.asarray(xc, dtype=float)
    y = np.asarray(y, dtype=float)
    e = np.asarray(e, dtype=float)
    bw = np.asarray(bw, dtype=float)
    if mode == 'absolute':
        norm_term = prc.xsec_norm_term_for_hist(run.xsec_band, hist_name, xc, bw) if run.xsec_band is not None else None
        e_plot = prc.yerr_for_plot_absolute(y, e, norm_term) if norm_term is not None else e
        return xc, y, e_plot, bw
    if mode == 'unitshape':
        _sigma, y_n, e_n = prc.normalize_per_dijet_with_cov(y, e, bw, denom_positive_only=False, cov_mode=getattr(prc, 'PERDIJET_COV_MODE', 'diag'))
        if y_n is None or e_n is None:
            raise RuntimeError(f"Unit-shape normalization failed for {run.tag}:{hist_name}")
        return xc, y_n, e_n, bw
    if mode == 'dijet_normalized':
        if single_slice_mode:
            obs_key = family
            count = _resolve_single_slice_count(run, hist_name, 'jetpt_sel' if family == 'jetpt' else family)
            if count is None or int(count) <= 0:
                raise RuntimeError(f"Single-slice selected dijet count unavailable/non-positive for {run.tag}:{hist_name}")
            c = float(count)
            return xc, y / c, e / c, bw
        _sigma, y_n, e_n = prc.normalize_per_dijet_with_cov(y, e, bw, denom_positive_only=False, cov_mode=getattr(prc, 'PERDIJET_COV_MODE', 'diag'))
        if y_n is None or e_n is None:
            raise RuntimeError(f"Per-selection normalization failed for {run.tag}:{hist_name}")
        return xc, y_n, e_n, bw
    raise ValueError(f"Unsupported mode: {mode}")


def _mjj_title(hist_name: str, group: GroupSpec, *, mode: str) -> str:
    parsed = prc.parse_mjj_name(hist_name)
    branch = 'nosubfrac' if hist_name.endswith('_nosubfrac') else 'subfrac'
    if parsed is None:
        return f"Dijet mass comparison ({mode}; {branch}; {group.fixed_title})"
    Rv, lo, hi, is_all = parsed
    pt_label = prc._pt_label(lo, hi, is_all)
    return f"Dijet mass comparison ({mode}; {branch}; R={Rv:.2f}; lead pT {pt_label}; fixed {group.fixed_title})"


def _dphi_title(hist_name: str, group: GroupSpec, *, mode: str) -> str:
    parsed = prc.parse_dphi_abs_name(hist_name)
    branch = 'nosubfrac' if hist_name.endswith('_nosubfrac') else 'subfrac'
    if parsed is None:
        return f"|Δφ| comparison ({mode}; {branch}; fixed {group.fixed_title})"
    Rv, lo, hi, is_all = parsed
    pt_label = prc._pt_label(lo, hi, is_all)
    return f"|Δφ| comparison ({mode}; {branch}; R={Rv:.2f}; lead pT {pt_label}; fixed {group.fixed_title})"


def _imb_title(hist_name: str, group: GroupSpec, *, mode: str) -> str:
    is_aj = hist_name.startswith('aj_')
    parsed = prc.parse_aj_name(hist_name) if is_aj else prc.parse_xj_name(hist_name)
    branch = 'nosubfrac' if hist_name.endswith('_nosubfrac') else 'subfrac'
    obs = r"$A_J$" if is_aj else r"$x_J$"
    if parsed is None:
        return f"{obs} comparison ({mode}; {branch}; fixed {group.fixed_title})"
    Rv, lo, hi, is_all = parsed
    pt_label = prc._pt_label(lo, hi, is_all)
    return f"{obs} comparison ({mode}; {branch}; R={Rv:.2f}; lead pT {pt_label}; fixed {group.fixed_title})"


def _jetpt_title(hist_name: str, group: GroupSpec, *, mode: str) -> str:
    parsed = prc.parse_jetpt_name(hist_name)
    if parsed is None:
        return f"Jet pT comparison ({mode}; fixed {group.fixed_title})"
    kind, Rv, is_ns = parsed
    branch = 'branch-neutral' if kind == 'incl' else ('nosubfrac' if is_ns else 'subfrac')
    return f"Jet pT comparison ({kind}; {mode}; {branch}; R={Rv:.2f}; fixed {group.fixed_title})"


def _particle_title(hist_name: str, group: GroupSpec) -> str:
    kind = prc.parse_particle_name(hist_name) or hist_name
    return f"Accepted-particle {kind} comparison (fixed {group.fixed_title})"


def _leadsub_prof_title(hist_name: str, group: GroupSpec) -> str:
    parsed = prc.parse_sublead_vs_lead_profile_name(hist_name)
    branch = 'nosubfrac' if hist_name.endswith('_nosubfrac') else 'subfrac'
    if parsed is None:
        return f"Mean subleading-vs-leading jet pT comparison ({branch}; fixed {group.fixed_title})"
    Rv, _is_ns = parsed
    return f"Mean subleading-vs-leading jet pT comparison ({branch}; R={Rv:.2f}; fixed {group.fixed_title})"


def _ylabel_for_family(family: str, mode: str, *, hist_name: str = '') -> str:
    if family == 'mjj':
        if mode == 'absolute':
            return r"$d\sigma/dM_{jj}$ (mb/GeV)"
        return prc._single_slice_norm_ylabel('mjj') if prc.SINGLE_SLICE_MODE else r"$(1/\sigma_{sel})\,d\sigma/dM_{jj}$ (1/GeV)"
    if family == 'dphi_abs':
        if mode == 'absolute':
            return r"$d\sigma/d|\Delta\varphi|$ (mb/rad)"
        return prc._single_slice_norm_ylabel('dphi', is_abs=True) if prc.SINGLE_SLICE_MODE else r"$(1/\sigma_{sel})\,d\sigma/d|\Delta\varphi|$ (1/rad)"
    if family == 'xj':
        if mode == 'absolute':
            return r"$d\sigma/dx_J$ (mb)"
        return prc._single_slice_norm_ylabel('xj') if prc.SINGLE_SLICE_MODE else r"$(1/\sigma_{sel})\,d\sigma/dx_J$"
    if family == 'aj':
        if mode == 'absolute':
            return r"$d\sigma/dA_J$ (mb)"
        return prc._single_slice_norm_ylabel('aj') if prc.SINGLE_SLICE_MODE else r"$(1/\sigma_{sel})\,d\sigma/dA_J$"
    if family == 'jetpt':
        if mode == 'absolute':
            return r"$d\sigma/dp_T$ (mb/GeV)"
        if mode == 'unitshape':
            return r"$(1/\sigma_{incl})\,d\sigma/dp_T$ (1/GeV)"
        return prc._single_slice_norm_ylabel('sel') if prc.SINGLE_SLICE_MODE else r"$(1/\sigma_{sel})\,d\sigma/dp_T$ (1/GeV)"
    if family == 'particle_pt':
        return r"$d\sigma/dp_T$ (mb/GeV)"
    if family == 'particle_eta':
        return r"$d\sigma/d\eta$ (mb)"
    if family == 'particle_phi':
        return r"$d\sigma/d\varphi$ (mb/rad)"
    if family == 'lead_sublead_profile':
        return r"$\langle p_{T,sublead}\rangle$ (GeV)"
    return 'yield'


def _xlabel_for_family(family: str, *, hist_name: str = '') -> str:
    if family == 'mjj':
        return r"$M_{jj}$ (GeV)"
    if family == 'dphi_abs':
        return r"$|\Delta\varphi|$ (rad)"
    if family == 'xj':
        return r"$x_J$"
    if family == 'aj':
        return r"$A_J$"
    if family == 'jetpt':
        return r"$p_T$ (GeV)"
    if family == 'particle_pt':
        return r"$p_T$ (GeV)"
    if family == 'particle_eta':
        return r"$\eta$"
    if family == 'particle_phi':
        return r"$\varphi$ (rad)"
    if family == 'lead_sublead_profile':
        return r"$p_{T,lead}$ (GeV)"
    return 'x'


def _overlay_1d(group: GroupSpec, hist_name: str, hists: List[tuple], *, family: str, mode: str, out_path: str, title: str, logx: bool = False, logy: bool = False) -> None:
    fig, ax = plt.subplots(figsize=(9.2, 7.2))
    positive_y_chunks = []
    x_chunks = []
    for idx, (run, hist) in enumerate(zip(group.runs, hists)):
        xc, y, e, bw = _normalize_hist(run, hist_name, hist, family=family, mode=mode, single_slice_mode=prc.SINGLE_SLICE_MODE)
        color, marker, ls = _style_for_index(idx)
        label = _label_for_run_with_count(run, group.kind, hist_name, family, mode)
        if logy:
            mask = np.isfinite(xc) & np.isfinite(y) & (xc > 0) & (y > 0)
            if np.any(mask):
                prc.errorbar_nan_safe_log(ax, xc[mask], y[mask], e[mask], fmt=marker, ms=3.3, lw=0.9, capsize=2, label=label, color=color)
                positive_y_chunks.append(y[mask])
                x_chunks.append(xc[mask])
        else:
            mask = np.isfinite(xc) & np.isfinite(y)
            if np.any(mask):
                prc.errorbar_nan_safe(ax, xc[mask], y[mask], e[mask], fmt=marker, ms=3.3, lw=0.9, capsize=2, label=label, color=color)
                positive_y_chunks.append(y[mask][np.isfinite(y[mask])])
                x_chunks.append(xc[mask][np.isfinite(xc[mask])])
    if logx:
        ax.set_xscale('log')
    if logy:
        ax.set_yscale('log')
    if x_chunks:
        x_all = np.concatenate(x_chunks)
        x_all = x_all[np.isfinite(x_all)]
        if x_all.size > 0:
            ax.set_xlim(float(np.min(x_all) * (0.95 if np.min(x_all) > 0 else 1.0)), float(np.max(x_all) * 1.05))
    if logy and positive_y_chunks:
        y_all = np.concatenate([_finite_positive(chunk) for chunk in positive_y_chunks if np.asarray(chunk).size > 0])
        if y_all.size > 0:
            ymin = max(float(np.min(y_all)) * 0.6, 1e-12)
            ymax = float(np.max(y_all)) * 2.0
            if ymax > ymin:
                ax.set_ylim(ymin, ymax)
    ax.set_xlabel(_xlabel_for_family(family, hist_name=hist_name))
    ax.set_ylabel(_ylabel_for_family(family if not family.startswith('particle_') else family, mode, hist_name=hist_name))
    ax.legend(loc='best', frameon=False)
    prc._set_wrapped_ax_title(ax, title, max_chars=96)
    _set_caption(fig, title, max_chars=118)
    _tight(fig, rect=[0, 0, 1, prc._ax_title_rect_top(title, top_single=0.98, top_wrapped=0.93)])
    _save_plot(fig, out_path)
    plt.close(fig)



def _ratio_config_key_for_family(family: str, hist_name: str) -> str:
    if family == 'mjj':
        return 'MJJ'
    if family == 'dphi_abs':
        return 'DPHI_ABS'
    if family == 'xj':
        return 'XJ'
    if family == 'aj':
        return 'AJ'
    if family == 'jetpt':
        return 'JETPT'
    if family == 'lead_sublead_profile':
        return 'LEAD_SUBLEAD_PROFILE'
    return family.upper()


def _auto_ratio_ylim_multiline(ax, ys: List[np.ndarray], es: List[np.ndarray], *, fallback=(0.0, 2.0)) -> None:
    vals = []
    for y, e in zip(ys, es):
        yy = np.asarray(y, dtype=float)
        ee = np.asarray(e, dtype=float)
        for arr in (yy, yy - ee, yy + ee):
            good = arr[np.isfinite(arr)]
            if good.size:
                vals.append(good)
    if not vals:
        ax.set_ylim(*fallback)
        return
    allv = np.concatenate(vals)
    if allv.size == 0:
        ax.set_ylim(*fallback)
        return
    lo = float(np.nanpercentile(allv, 2.0))
    hi = float(np.nanpercentile(allv, 98.0))
    lo = min(lo, 1.0)
    hi = max(hi, 1.0)
    pad = 0.12 * max(hi - lo, 0.25)
    lo -= pad
    hi += pad
    if not (np.isfinite(lo) and np.isfinite(hi) and hi > lo):
        lo, hi = fallback
    ax.set_ylim(lo, hi)


def _same_1d_binning(a: tuple, b: tuple) -> bool:
    xa, _ya, _ea, bwa, _enta = a
    xb, _yb, _eb, bwb, _entb = b
    return (
        len(xa) == len(xb)
        and np.allclose(np.asarray(xa, dtype=float), np.asarray(xb, dtype=float), rtol=0, atol=1e-9)
        and np.allclose(np.asarray(bwa, dtype=float), np.asarray(bwb, dtype=float), rtol=0, atol=1e-9)
    )


def _overlay_1d_with_ratio(group: GroupSpec, hist_name: str, hists: List[tuple], *, family: str, mode: str, out_path: str, title: str, logx: bool = False, logy: bool = False) -> None:
    """Overlay vacuum + medium variations with a brick/vacuum ratio panel.

    This is the multibrick analogue of the paperready two-run ratio plots: the top
    panel keeps all visible curves, and the bottom panel draws one ratio curve for
    every non-vacuum run against the vacuum denominator.
    """
    if len(group.runs) != len(hists):
        raise RuntimeError(f"Internal plotting mismatch for {hist_name}: runs={len(group.runs)} hists={len(hists)}")
    if len(group.runs) < 2:
        _overlay_1d(group, hist_name, hists, family=family, mode=mode, out_path=out_path, title=title, logx=logx, logy=logy)
        return

    fig = plt.figure(figsize=(9.4, 8.6))
    gs = GridSpec(2, 1, height_ratios=[3.2, 1.15], hspace=0.06, figure=fig)
    ax = fig.add_subplot(gs[0, 0])
    rax = fig.add_subplot(gs[1, 0], sharex=ax)

    normed: List[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = []
    positive_y_chunks = []
    x_chunks = []
    visible_top_curves = 0
    for idx, (run, hist) in enumerate(zip(group.runs, hists)):
        try:
            xc, y, e, bw = _normalize_hist(run, hist_name, hist, family=family, mode=mode, single_slice_mode=prc.SINGLE_SLICE_MODE)
        except Exception as exc:
            _log(f"[WARN] normalize failed for {run.tag}:{hist_name}:{mode}: {exc}")
            xc0, y0, e0, bw0, _ = hist
            xc = np.asarray(xc0, dtype=float)
            y = np.full_like(xc, np.nan, dtype=float)
            e = np.full_like(xc, np.nan, dtype=float)
            bw = np.asarray(bw0, dtype=float)
        normed.append((xc, y, e, bw))
        color, marker, _ls = _style_for_index(idx)
        label = _label_for_run_with_count(run, group.kind, hist_name, family, mode)
        if logy:
            mask = np.isfinite(xc) & np.isfinite(y) & np.isfinite(e) & (xc > 0) & (y > 0)
            if np.any(mask):
                prc.errorbar_nan_safe_log(ax, xc[mask], y[mask], e[mask], fmt=marker, ms=3.2, lw=0.9, capsize=2, label=label, color=color)
                visible_top_curves += 1
                positive_y_chunks.append(y[mask])
                x_chunks.append(xc[mask])
        else:
            mask = np.isfinite(xc) & np.isfinite(y) & np.isfinite(e)
            if np.any(mask):
                prc.errorbar_nan_safe(ax, xc[mask], y[mask], e[mask], fmt=marker, ms=3.2, lw=0.9, capsize=2, label=label, color=color)
                visible_top_curves += 1
                ygood = y[mask][np.isfinite(y[mask])]
                if ygood.size:
                    positive_y_chunks.append(ygood)
                x_chunks.append(xc[mask])

    if logx:
        ax.set_xscale('log')
        rax.set_xscale('log')
    if logy:
        ax.set_yscale('log')
    if x_chunks:
        x_all = np.concatenate(x_chunks)
        x_all = x_all[np.isfinite(x_all)]
        if x_all.size > 0:
            xmin = float(np.min(x_all))
            xmax = float(np.max(x_all))
            if logx:
                xmin = max(xmin * 0.95, 1e-12)
            ax.set_xlim(xmin, xmax * 1.05)
    if logy and positive_y_chunks:
        y_all = np.concatenate([_finite_positive(chunk) for chunk in positive_y_chunks if np.asarray(chunk).size > 0])
        if y_all.size > 0:
            ymin = max(float(np.min(y_all)) * 0.6, 1e-12)
            ymax = float(np.max(y_all)) * 2.0
            if ymax > ymin:
                ax.set_ylim(ymin, ymax)

    vac_hist = hists[0]
    xvac, yvac, evac, bwvac = normed[0]
    ratio_ys: List[np.ndarray] = []
    ratio_es: List[np.ndarray] = []
    any_ratio = False
    for idx in range(1, len(group.runs)):
        if not _same_1d_binning(vac_hist, hists[idx]):
            _log(f"[WARN] ratio skipped for {group.runs[idx].tag}:{hist_name}: binning mismatch with vacuum")
            continue
        xmed, ymed, emed, bwmed = normed[idx]
        ratio_x = xvac
        num_y, num_e, num_bw = ymed, emed, bwmed
        den_y, den_e, den_bw = yvac, evac, bwvac
        if family == 'dphi_abs':
            rebin_factor = int(getattr(prc, 'DPHI_ABS_RATIO_REBIN_FACTOR', 1) or 1)
            if rebin_factor > 1:
                num_xc_rb, num_y_rb, num_e_rb, num_bw_rb, num_did = prc._rebin_hist_density_for_ratio(xmed, ymed, emed, bwmed, rebin_factor, hist_name=hist_name, observable_label='dphi_abs')
                den_xc_rb, den_y_rb, den_e_rb, den_bw_rb, den_did = prc._rebin_hist_density_for_ratio(xvac, yvac, evac, bwvac, rebin_factor, hist_name=hist_name, observable_label='dphi_abs')
                if num_did and den_did and len(num_xc_rb) == len(den_xc_rb) and np.allclose(num_xc_rb, den_xc_rb, rtol=0, atol=1e-9) and np.allclose(num_bw_rb, den_bw_rb, rtol=0, atol=1e-9):
                    ratio_x = num_xc_rb
                    num_y, num_e, num_bw = num_y_rb, num_e_rb, num_bw_rb
                    den_y, den_e, den_bw = den_y_rb, den_e_rb, den_bw_rb
                else:
                    _log(f"[WARN] {hist_name}: requested |Delta phi| ratio rebin factor={rebin_factor}, but rebinned medium/vacuum binning did not match for {group.runs[idx].tag}; keeping original bins")
        ratio, ratio_err, m_plot, _m_err = prc._ratio_with_optional_errors(num_y, num_e, den_y, den_e)
        if not np.any(m_plot):
            continue
        color, marker, _ls = _style_for_index(idx)
        label = f"{_label_for_run(group.runs[idx], group.kind)}/vac"
        prc.errorbar_nan_safe(rax, ratio_x[m_plot], ratio[m_plot], ratio_err[m_plot], fmt=marker, ms=3.0, lw=0.9, capsize=2, color=color, label=label)
        ratio_ys.append(ratio[m_plot])
        ratio_es.append(ratio_err[m_plot])
        any_ratio = True
    rax.axhline(1.0, color='k', ls='--', lw=1.0)
    rax.set_ylabel('brick/vac')
    rax.set_xlabel(_xlabel_for_family(family, hist_name=hist_name))
    if any_ratio:
        key = _ratio_config_key_for_family(family, hist_name)
        if hasattr(prc, '_apply_configured_ratio_ylim'):
            all_r = np.concatenate([r[np.isfinite(r)] for r in ratio_ys if np.asarray(r).size]) if ratio_ys else np.array([])
            all_e = np.concatenate([e[np.isfinite(e)] for e in ratio_es if np.asarray(e).size]) if ratio_es else np.array([])
            try:
                prc._apply_configured_ratio_ylim(rax, key, all_r, all_e, context=hist_name)
            except Exception:
                _auto_ratio_ylim_multiline(rax, ratio_ys, ratio_es)
        else:
            _auto_ratio_ylim_multiline(rax, ratio_ys, ratio_es)
        rax.legend(loc='best', frameon=False, fontsize=max(7, prc._FONTS.get('legend', 9) - 1))
    else:
        rax.text(0.5, 0.5, 'ratio unavailable', transform=rax.transAxes, ha='center', va='center', fontsize=prc._FONTS.get('note', 9))
        rax.set_ylim(0.0, 2.0)

    ax.set_ylabel(_ylabel_for_family(family if not family.startswith('particle_') else family, mode, hist_name=hist_name))
    ax.legend(loc='best', frameon=False, fontsize=prc._FONTS.get('legend', 9))
    _set_caption(fig, title, max_chars=118)
    for label in ax.get_xticklabels():
        label.set_visible(False)
    _tight(fig, rect=[0, 0, 1, 0.985])
    _save_plot(fig, out_path, placeholder=(visible_top_curves == 0))
    plt.close(fig)

def _overlay_profile(group: GroupSpec, hist_name: str, hists: List[tuple], *, out_path: str, title: str) -> None:
    fig, ax = plt.subplots(figsize=(9.2, 7.2))
    for idx, (run, hist) in enumerate(zip(group.runs, hists)):
        xc, y, e, _bw, _entries = hist
        color, marker, _ls = _style_for_index(idx)
        prc.errorbar_nan_safe(ax, xc, y, e, fmt=marker, ms=3.3, lw=0.9, capsize=2, label=_label_for_run(run, group.kind), color=color)
    ax.set_xlabel(_xlabel_for_family('lead_sublead_profile'))
    ax.set_ylabel(_ylabel_for_family('lead_sublead_profile', 'absolute'))
    ax.legend(loc='best', frameon=False)
    prc._set_wrapped_ax_title(ax, title, max_chars=96)
    _set_caption(fig, title, max_chars=118)
    _tight(fig, rect=[0, 0, 1, prc._ax_title_rect_top(title, top_single=0.98, top_wrapped=0.93)])
    _save_plot(fig, out_path)
    plt.close(fig)



def _overlay_profile_with_ratio(group: GroupSpec, hist_name: str, hists: List[tuple], *, out_path: str, title: str) -> None:
    if len(group.runs) < 2:
        _overlay_profile(group, hist_name, hists, out_path=out_path, title=title)
        return
    fig = plt.figure(figsize=(9.4, 8.4))
    gs = GridSpec(2, 1, height_ratios=[3.2, 1.15], hspace=0.06, figure=fig)
    ax = fig.add_subplot(gs[0, 0])
    rax = fig.add_subplot(gs[1, 0], sharex=ax)
    x_chunks, y_pos_chunks = [], []
    normed = []
    for idx, (run, hist) in enumerate(zip(group.runs, hists)):
        xc, y, e, bw, _entries = hist
        xc = np.asarray(xc, dtype=float)
        y = np.asarray(y, dtype=float)
        e = np.asarray(e, dtype=float)
        bw = np.asarray(bw, dtype=float)
        normed.append((xc, y, e, bw))
        m = np.isfinite(xc) & np.isfinite(y) & np.isfinite(e) & (xc > 0) & (y > 0)
        if np.any(m):
            color, marker, _ls = _style_for_index(idx)
            prc.errorbar_nan_safe(ax, xc[m], y[m], e[m], fmt=marker, ms=3.2, lw=0.9, capsize=2, label=_label_for_run(run, group.kind), color=color)
            x_chunks.append(xc[m])
            y_pos_chunks.append(y[m])
    ax.set_xscale('log')
    ax.set_yscale('log')
    if x_chunks:
        x_all = np.concatenate(x_chunks)
        x_all = x_all[np.isfinite(x_all) & (x_all > 0)]
        if x_all.size:
            ax.set_xlim(max(1e-12, float(np.min(x_all)) * 0.95), float(np.max(x_all)) * 1.05)
    if y_pos_chunks:
        y_all = np.concatenate(y_pos_chunks)
        y_all = y_all[np.isfinite(y_all) & (y_all > 0)]
        if y_all.size:
            ax.set_ylim(max(1e-12, float(np.min(y_all)) * 0.6), float(np.max(y_all)) * 1.5)

    xvac, yvac, evac, bwvac = normed[0]
    ratio_ys, ratio_es = [], []
    any_ratio = False
    for idx in range(1, len(group.runs)):
        xmed, ymed, emed, bwmed = normed[idx]
        # TProfile binning is expected to match. Keep this strict so we never draw fake interpolated ratios.
        if len(xmed) != len(xvac) or not np.allclose(xmed, xvac, rtol=0, atol=1e-9):
            _log(f"[WARN] profile ratio skipped for {group.runs[idx].tag}:{hist_name}: binning mismatch with vacuum")
            continue
        ratio, ratio_err, m_plot, _m_err = prc._ratio_with_optional_errors(ymed, emed, yvac, evac)
        if not np.any(m_plot):
            continue
        color, marker, _ls = _style_for_index(idx)
        prc.errorbar_nan_safe(rax, xvac[m_plot], ratio[m_plot], ratio_err[m_plot], fmt=marker, ms=3.0, lw=0.9, capsize=2, color=color, label=f"{_label_for_run(group.runs[idx], group.kind)}/vac")
        ratio_ys.append(ratio[m_plot])
        ratio_es.append(ratio_err[m_plot])
        any_ratio = True
    rax.axhline(1.0, color='k', ls='--', lw=1.0)
    rax.set_xscale('log')
    rax.set_ylabel('brick/vac')
    rax.set_xlabel(_xlabel_for_family('lead_sublead_profile'))
    if any_ratio:
        try:
            all_r = np.concatenate([r[np.isfinite(r)] for r in ratio_ys if np.asarray(r).size]) if ratio_ys else np.array([])
            all_e = np.concatenate([e[np.isfinite(e)] for e in ratio_es if np.asarray(e).size]) if ratio_es else np.array([])
            prc._apply_configured_ratio_ylim(rax, 'LEAD_SUBLEAD_PROFILE', all_r, all_e, context=hist_name)
        except Exception:
            _auto_ratio_ylim_multiline(rax, ratio_ys, ratio_es)
        rax.legend(loc='best', frameon=False, fontsize=max(7, prc._FONTS.get('legend', 9) - 1))
    else:
        rax.text(0.5, 0.5, 'ratio unavailable', transform=rax.transAxes, ha='center', va='center', fontsize=prc._FONTS.get('note', 9))
        rax.set_ylim(0.0, 2.0)
    ax.set_ylabel(_ylabel_for_family('lead_sublead_profile', 'absolute'))
    ax.legend(loc='best', frameon=False, fontsize=prc._FONTS.get('legend', 9))
    _set_caption(fig, title, max_chars=118)
    for label in ax.get_xticklabels():
        label.set_visible(False)
    _tight(fig, rect=[0, 0, 1, 0.985])
    _save_plot(fig, out_path)
    plt.close(fig)

def _grid_shape(n_items: int) -> Tuple[int, int]:
    n = max(1, int(n_items))
    ncols = min(3, n)
    nrows = int(math.ceil(n / ncols))
    return nrows, ncols


def _grid_2d(group: GroupSpec, hist_name: str, hists: List[tuple], *, out_path: str, title: str, xlab: str, ylab: str) -> None:
    n = len(hists)
    nrows, ncols = _grid_shape(n)
    fig = plt.figure(figsize=(5.2 * ncols, 4.45 * nrows + 0.8))
    gs = GridSpec(nrows, ncols, figure=fig, hspace=0.28, wspace=0.22)
    positive_vals = []
    for h in hists:
        xedges, yedges, vals, _errs, _entries = h
        arr = np.asarray(vals, dtype=float)
        pos = arr[np.isfinite(arr) & (arr > 0)]
        if pos.size > 0:
            positive_vals.append(pos)
    norm = None
    if positive_vals:
        all_pos = np.concatenate(positive_vals)
        if all_pos.size > 0:
            vmin = max(float(np.min(all_pos)), 1e-12)
            vmax = max(float(np.max(all_pos)), vmin * 1.01)
            norm = LogNorm(vmin=vmin, vmax=vmax)
    pcms = []
    axes = []
    for idx, (run, hist) in enumerate(zip(group.runs, hists)):
        ax = fig.add_subplot(gs[idx // ncols, idx % ncols])
        axes.append(ax)
        xedges, yedges, vals, _errs, _entries = hist
        arr = np.asarray(vals, dtype=float).T
        if norm is not None:
            pcm = ax.pcolormesh(xedges, yedges, np.ma.masked_less_equal(arr, 0.0), shading='auto', norm=norm)
        else:
            pcm = ax.pcolormesh(xedges, yedges, arr, shading='auto')
        pcms.append(pcm)
        ax.set_xlabel(xlab)
        ax.set_ylabel(ylab)
        prc._set_wrapped_ax_title(ax, _label_for_run(run, group.kind), max_chars=54, pad_single=5.0, pad_wrapped=8.0)
    for idx in range(n, nrows * ncols):
        ax = fig.add_subplot(gs[idx // ncols, idx % ncols])
        ax.axis('off')
    if pcms:
        cbar = fig.colorbar(pcms[-1], ax=axes, shrink=0.88, pad=0.02)
        if hist_name.startswith('h2_dphi_abs_vs_deta_'):
            cbar.set_label(r'$d^2\sigma_{\mathrm{dijet}}/(d|\Delta\varphi|\,d|\Delta\eta|)$ [mb/rad]')
        else:
            cbar.set_label('Weighted dijet yield [mb]')
    _set_caption(fig, title, max_chars=118)
    _tight(fig, rect=[0, 0, 1, 0.985])
    _save_plot(fig, out_path)
    plt.close(fig)


def _grid_2d_ratio_to_vacuum(group: GroupSpec, hist_name: str, hists: List[tuple], *, out_path: str, title: str, xlab: str, ylab: str) -> None:
    if len(hists) < 2:
        return
    vac = hists[0]
    xedges_v, yedges_v, vals_v, _errs_v, _entries_v = vac
    xedges_v = np.asarray(xedges_v, dtype=float)
    yedges_v = np.asarray(yedges_v, dtype=float)
    vals_v = np.asarray(vals_v, dtype=float)

    ratio_items = []
    for idx in range(1, len(hists)):
        xedges_m, yedges_m, vals_m, _errs_m, _entries_m = hists[idx]
        xedges_m = np.asarray(xedges_m, dtype=float)
        yedges_m = np.asarray(yedges_m, dtype=float)
        vals_m = np.asarray(vals_m, dtype=float)
        if not (np.array_equal(xedges_v, xedges_m) and np.array_equal(yedges_v, yedges_m) and vals_v.shape == vals_m.shape):
            _log(f"[WARN] 2D ratio skipped for {group.runs[idx].tag}:{hist_name}: binning mismatch with vacuum")
            continue
        ratio = np.full_like(vals_v, np.nan, dtype=float)
        mask = np.isfinite(vals_m) & np.isfinite(vals_v) & (vals_m > 0) & (vals_v > 0)
        ratio[mask] = vals_m[mask] / vals_v[mask]
        if np.any(np.isfinite(ratio)):
            ratio_items.append((idx, ratio))
    if not ratio_items:
        _write_placeholder(out_path, title, f"No finite positive brick/vacuum 2D ratio bins were available for {hist_name}.")
        return

    nrows, ncols = _grid_shape(len(ratio_items))
    fig = plt.figure(figsize=(5.2 * ncols, 4.45 * nrows + 0.8))
    gs = GridSpec(nrows, ncols, figure=fig, hspace=0.28, wspace=0.22)
    positive_vals = [r[np.isfinite(r) & (r > 0)] for _idx, r in ratio_items]
    positive_vals = [r for r in positive_vals if r.size]
    norm = None
    if positive_vals:
        all_pos = np.concatenate(positive_vals)
        if all_pos.size:
            vmin = max(float(np.nanpercentile(all_pos, 2.0)), 1e-12)
            vmax = max(float(np.nanpercentile(all_pos, 98.0)), vmin * 1.01)
            # Make ratio color range include unity when possible.
            vmin = min(vmin, 1.0)
            vmax = max(vmax, 1.0)
            if vmax > vmin:
                norm = LogNorm(vmin=max(vmin, 1e-12), vmax=vmax)
    pcms = []
    axes = []
    for panel_idx, (run_idx, ratio) in enumerate(ratio_items):
        ax = fig.add_subplot(gs[panel_idx // ncols, panel_idx % ncols])
        axes.append(ax)
        arr = np.asarray(ratio, dtype=float).T
        if norm is not None:
            pcm = ax.pcolormesh(xedges_v, yedges_v, np.ma.masked_invalid(np.ma.masked_less_equal(arr, 0.0)), shading='auto', norm=norm)
        else:
            pcm = ax.pcolormesh(xedges_v, yedges_v, np.ma.masked_invalid(arr), shading='auto')
        pcms.append(pcm)
        ax.set_xlabel(xlab)
        ax.set_ylabel(ylab)
        ax.set_title(f"{_label_for_run(group.runs[run_idx], group.kind)}/vac")
    for idx in range(len(ratio_items), nrows * ncols):
        ax = fig.add_subplot(gs[idx // ncols, idx % ncols])
        ax.axis('off')
    if pcms:
        cbar = fig.colorbar(pcms[-1], ax=axes, shrink=0.88, pad=0.02)
        cbar.set_label('brick/vac')
    _set_caption(fig, title, max_chars=118)
    _tight(fig, rect=[0, 0, 1, 0.985])
    _save_plot(fig, out_path)
    plt.close(fig)


def _jetR_ratio_from_map(hist_map: Dict[tuple, tuple], kind: str, r_num: float, r_den: float, branch_ns: Optional[bool]) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray]]:
    def _key(obs_kind: str, radius: float, ns_flag: Optional[bool]):
        if ns_flag is None:
            candidates = [(obs_kind, radius), (obs_kind, radius, False)]
        else:
            candidates = [(obs_kind, radius, ns_flag), (obs_kind, radius)]
        return next((k for k in candidates if k in hist_map), None)
    kn = _key(kind, r_num, branch_ns)
    kd = _key(kind, r_den, branch_ns)
    if kn is None or kd is None:
        return None
    xcN, yN, eN, bwN, _ = hist_map[kn]
    xcD, yD, eD, bwD, _ = hist_map[kd]
    if len(xcN) != len(xcD) or not np.allclose(xcN, xcD, rtol=0, atol=1e-9) or not np.allclose(bwN, bwD, rtol=0, atol=1e-9):
        return None
    r, er, m_plot, _m_err = prc._ratio_with_optional_errors(yN, eN, yD, eD)
    if not np.any(m_plot):
        return None
    return xcN[m_plot], r[m_plot], er[m_plot]


def _plot_jetR_group(group: GroupSpec, runs_maps: List[Dict[tuple, tuple]], *, kind: str, branch_ns: Optional[bool], out_dir: str) -> None:
    if len(prc.JET_RADIUS_COMPARE_PAIRS) == 0:
        return
    branch_name = 'branch-neutral' if branch_ns is None else ('nosubfrac' if branch_ns else 'subfrac')
    for r_num, r_den in prc.JET_RADIUS_COMPARE_PAIRS:
        fig, ax = plt.subplots(figsize=(9.2, 7.2))
        any_curve = False
        for idx, (run, hist_map) in enumerate(zip(group.runs, runs_maps)):
            ratio = _jetR_ratio_from_map(hist_map, kind, r_num, r_den, branch_ns)
            if ratio is None:
                continue
            x, y, e = ratio
            color, marker, _ls = _style_for_index(idx)
            prc.errorbar_nan_safe(ax, x, y, e, fmt=marker, ms=3.3, lw=0.9, capsize=2, label=_label_for_run(run, group.kind), color=color)
            any_curve = True
        out_path = os.path.join(out_dir, f"jetR_{kind}_R{int(round(r_num*100)):03d}_over_R{int(round(r_den*100)):03d}_{group.fixed_tag}.png")
        if not any_curve:
            plt.close(fig)
            _write_placeholder(out_path, f"Jet-R dependence ({kind}; {branch_name}; fixed {group.fixed_title}; ratio R={r_num:.2f}/R={r_den:.2f})", "No common positive bins were available for this jet-R ratio.", ylabel=rf"R={r_num:.2f}/R={r_den:.2f}")
            continue
        ax.axhline(1.0, color='k', ls='--', lw=1.0)
        ax.set_xscale('log')
        ax.set_xlabel(r'$p_T$ (GeV)')
        ax.set_ylabel(rf'$R={r_num:.2f}/R={r_den:.2f}$')
        ax.legend(loc='best', frameon=False)
        title = f"Jet-R dependence ({kind}; {branch_name}; fixed {group.fixed_title}; ratio R={r_num:.2f}/R={r_den:.2f})"
        _set_caption(fig, title, max_chars=118)
        _tight(fig, rect=[0, 0, 1, 0.985])
        _save_plot(fig, out_path)
        plt.close(fig)


def _group_out_dirs(group: GroupSpec) -> dict:
    root = group.out_root
    plots_abs = os.path.join(root, 'plots', 'absolute')
    plots_norm = os.path.join(root, 'plots', 'dijet_normalized')
    plots_unitshape = os.path.join(root, 'plots', 'inclusive_unit_normalized')
    d = {
        'mjj_abs_sub': os.path.join(plots_abs, 'subfrac', 'dijet_mass'),
        'mjj_abs_ns': os.path.join(plots_abs, 'nosubfrac', 'dijet_mass'),
        'mjj_norm_sub': os.path.join(plots_norm, 'subfrac', 'dijet_mass'),
        'mjj_norm_ns': os.path.join(plots_norm, 'nosubfrac', 'dijet_mass'),
        'dphi_abs_sub': os.path.join(plots_abs, 'subfrac', 'dphi_fit_abs0pi'),
        'dphi_abs_ns': os.path.join(plots_abs, 'nosubfrac', 'dphi_fit_abs0pi'),
        'dphi_norm_sub': os.path.join(plots_norm, 'subfrac', 'dphi_fit_abs0pi'),
        'dphi_norm_ns': os.path.join(plots_norm, 'nosubfrac', 'dphi_fit_abs0pi'),
        'imb_abs_sub': os.path.join(plots_abs, 'subfrac', 'dijet_imbalance'),
        'imb_abs_ns': os.path.join(plots_abs, 'nosubfrac', 'dijet_imbalance'),
        'imb_norm_sub': os.path.join(plots_norm, 'subfrac', 'dijet_imbalance'),
        'imb_norm_ns': os.path.join(plots_norm, 'nosubfrac', 'dijet_imbalance'),
        'jetpt_abs_neutral': os.path.join(plots_abs, 'jet_spectra'),
        'jetpt_unitshape_neutral': os.path.join(plots_unitshape, 'jet_spectra'),
        'jetpt_abs_sub': os.path.join(plots_abs, 'subfrac', 'jet_spectra'),
        'jetpt_abs_ns': os.path.join(plots_abs, 'nosubfrac', 'jet_spectra'),
        'jetpt_norm_sub': os.path.join(plots_norm, 'subfrac', 'jet_spectra'),
        'jetpt_norm_ns': os.path.join(plots_norm, 'nosubfrac', 'jet_spectra'),
        'particle': os.path.join(root, 'plots', 'particle_level'),
        'lead_sublead_corr_sub': os.path.join(plots_abs, 'subfrac', 'lead_sublead_correlation'),
        'lead_sublead_corr_ns': os.path.join(plots_abs, 'nosubfrac', 'lead_sublead_correlation'),
        'dphiabs_deta_sub': os.path.join(plots_abs, 'subfrac', 'dphi_abs_vs_deta'),
        'dphiabs_deta_ns': os.path.join(plots_abs, 'nosubfrac', 'dphi_abs_vs_deta'),
        'jetR': os.path.join(root, 'plots', 'jet_R_dependence'),
        'jetR_sub': os.path.join(root, 'plots', 'jet_R_dependence', 'subfrac'),
        'jetR_ns': os.path.join(root, 'plots', 'jet_R_dependence', 'nosubfrac'),
    }
    for v in d.values():
        ensure_dir(v)
    return d


def _plot_group(group: GroupSpec) -> None:
    _log(f"[group] plotting {group.kind} fixed={group.fixed_value:g} -> out={group.out_root}")
    for run in group.runs:
        _ensure_hist_cache(run)
    dirs = _group_out_dirs(group)

    # Mjj
    shared = sorted(set.intersection(*[set(r.mjj.keys()) for r in group.runs]))
    for hn in shared:
        is_ns = hn.endswith('_nosubfrac')
        hists = [r.mjj[hn] for r in group.runs]
        _overlay_1d_with_ratio(group, hn, hists, family='mjj', mode='absolute', out_path=os.path.join(dirs['mjj_abs_ns' if is_ns else 'mjj_abs_sub'], f"{hn}_{group.fixed_tag}.png"), title=_mjj_title(hn, group, mode='absolute'), logx=True, logy=True)
        _overlay_1d_with_ratio(group, hn, hists, family='mjj', mode='dijet_normalized', out_path=os.path.join(dirs['mjj_norm_ns' if is_ns else 'mjj_norm_sub'], f"{hn}_{group.fixed_tag}.png"), title=_mjj_title(hn, group, mode=('single-slice' if prc.SINGLE_SLICE_MODE else 'dijet_normalized')), logx=True, logy=True)

    # dphi abs
    shared = sorted(set.intersection(*[set(r.dphi_abs.keys()) for r in group.runs]))
    for hn in shared:
        is_ns = hn.endswith('_nosubfrac')
        hists = [r.dphi_abs[hn] for r in group.runs]
        _overlay_1d_with_ratio(group, hn, hists, family='dphi_abs', mode='absolute', out_path=os.path.join(dirs['dphi_abs_ns' if is_ns else 'dphi_abs_sub'], f"{hn}_{group.fixed_tag}.png"), title=_dphi_title(hn, group, mode='absolute'), logx=False, logy=False)
        _overlay_1d_with_ratio(group, hn, hists, family='dphi_abs', mode='dijet_normalized', out_path=os.path.join(dirs['dphi_norm_ns' if is_ns else 'dphi_norm_sub'], f"{hn}_{group.fixed_tag}.png"), title=_dphi_title(hn, group, mode=('single-slice' if prc.SINGLE_SLICE_MODE else 'dijet_normalized')), logx=False, logy=False)

    # xJ/AJ
    shared = sorted(set.intersection(*[set(r.imbalance.keys()) for r in group.runs]))
    for hn in shared:
        is_ns = hn.endswith('_nosubfrac')
        fam = 'aj' if hn.startswith('aj_') else 'xj'
        hists = [r.imbalance[hn] for r in group.runs]
        _overlay_1d(group, hn, hists, family=fam, mode='absolute', out_path=os.path.join(dirs['imb_abs_ns' if is_ns else 'imb_abs_sub'], f"{hn}_{group.fixed_tag}.png"), title=_imb_title(hn, group, mode='absolute'), logx=False, logy=False)
        _overlay_1d_with_ratio(group, hn, hists, family=fam, mode='dijet_normalized', out_path=os.path.join(dirs['imb_norm_ns' if is_ns else 'imb_norm_sub'], f"{hn}_{group.fixed_tag}.png"), title=_imb_title(hn, group, mode=('single-slice' if prc.SINGLE_SLICE_MODE else 'dijet_normalized')), logx=False, logy=False)

    # Jet pT
    shared = sorted(set.intersection(*[set(r.jetpt.keys()) for r in group.runs]))
    for hn in shared:
        kind, _Rv, is_ns = prc.parse_jetpt_name(hn)
        hists = [r.jetpt[hn] for r in group.runs]
        if kind == 'incl':
            _overlay_1d_with_ratio(group, hn, hists, family='jetpt', mode='absolute', out_path=os.path.join(dirs['jetpt_abs_neutral'], f"{hn}_{group.fixed_tag}.png"), title=_jetpt_title(hn, group, mode='absolute'), logx=True, logy=True)
            _overlay_1d_with_ratio(group, hn, hists, family='jetpt', mode='unitshape', out_path=os.path.join(dirs['jetpt_unitshape_neutral'], f"{hn}_{group.fixed_tag}.png"), title=_jetpt_title(hn, group, mode='unitshape'), logx=True, logy=True)
        else:
            _overlay_1d_with_ratio(group, hn, hists, family='jetpt', mode='absolute', out_path=os.path.join(dirs['jetpt_abs_ns' if is_ns else 'jetpt_abs_sub'], f"{hn}_{group.fixed_tag}.png"), title=_jetpt_title(hn, group, mode='absolute'), logx=True, logy=True)
            _overlay_1d_with_ratio(group, hn, hists, family='jetpt', mode='dijet_normalized', out_path=os.path.join(dirs['jetpt_norm_ns' if is_ns else 'jetpt_norm_sub'], f"{hn}_{group.fixed_tag}.png"), title=_jetpt_title(hn, group, mode=('single-slice' if prc.SINGLE_SLICE_MODE else 'dijet_normalized')), logx=True, logy=True)

    # Particle-level
    shared = sorted(set.intersection(*[set(r.particle.keys()) for r in group.runs]))
    for hn in shared:
        kind = prc.parse_particle_name(hn)
        fam = f'particle_{kind}'
        hists = [r.particle[hn] for r in group.runs]
        logx = (kind == 'pt')
        logy = False
        _overlay_1d(group, hn, hists, family=fam, mode='absolute', out_path=os.path.join(dirs['particle'], f"{hn}_{group.fixed_tag}.png"), title=_particle_title(hn, group), logx=logx, logy=logy)

    # Lead/sublead TProfile
    shared = sorted(set.intersection(*[set(r.lead_sublead_prof.keys()) for r in group.runs]))
    for hn in shared:
        is_ns = hn.endswith('_nosubfrac')
        hists = [r.lead_sublead_prof[hn] for r in group.runs]
        _overlay_profile_with_ratio(group, hn, hists, out_path=os.path.join(dirs['lead_sublead_corr_ns' if is_ns else 'lead_sublead_corr_sub'], f"{hn}_{group.fixed_tag}.png"), title=_leadsub_prof_title(hn, group))

    # Lead/sublead TH2
    shared = sorted(set.intersection(*[set(r.lead_sublead_h2.keys()) for r in group.runs]))
    for hn in shared:
        is_ns = hn.endswith('_nosubfrac')
        hists = [r.lead_sublead_h2[hn] for r in group.runs]
        parsed = prc.parse_sublead_vs_lead_h2_name(hn)
        title = f"Lead-vs-subleading jet map ({'nosubfrac' if is_ns else 'subfrac'}; R={(parsed[0] if parsed else float('nan')):.2f}; fixed {group.fixed_title})"
        _grid_2d(group, hn, hists, out_path=os.path.join(dirs['lead_sublead_corr_ns' if is_ns else 'lead_sublead_corr_sub'], f"{hn}_{group.fixed_tag}_grid.png"), title=title, xlab=r'$p_{T,lead}$ (GeV)', ylab=r'$p_{T,sublead}$ (GeV)')
        _grid_2d_ratio_to_vacuum(group, hn, hists, out_path=os.path.join(dirs['lead_sublead_corr_ns' if is_ns else 'lead_sublead_corr_sub'], f"{hn}_{group.fixed_tag}_ratio_to_vac.png"), title=title + ' — brick/vac ratio maps', xlab=r'$p_{T,lead}$ (GeV)', ylab=r'$p_{T,sublead}$ (GeV)')

    # |dphi| vs |deta| TH2
    shared = sorted(set.intersection(*[set(r.dphi_abs_vs_deta_h2.keys()) for r in group.runs]))
    for hn in shared:
        is_ns = hn.endswith('_nosubfrac')
        hists = [r.dphi_abs_vs_deta_h2[hn] for r in group.runs]
        parsed = prc.parse_dphi_abs_vs_deta_h2_name(hn)
        Rv = parsed[0] if parsed else float('nan')
        title = f"|Δφ| vs |Δη| map ({'nosubfrac' if is_ns else 'subfrac'}; R={Rv:.2f}; fixed {group.fixed_title})"
        _grid_2d(group, hn, hists, out_path=os.path.join(dirs['dphiabs_deta_ns' if is_ns else 'dphiabs_deta_sub'], f"{hn}_{group.fixed_tag}_grid.png"), title=title, xlab=r'$|\Delta\varphi|$ (rad)', ylab=r'$|\Delta\eta|$')
        _grid_2d_ratio_to_vacuum(group, hn, hists, out_path=os.path.join(dirs['dphiabs_deta_ns' if is_ns else 'dphiabs_deta_sub'], f"{hn}_{group.fixed_tag}_ratio_to_vac.png"), title=title + ' — brick/vac ratio maps', xlab=r'$|\Delta\varphi|$ (rad)', ylab=r'$|\Delta\eta|$')

    # Jet-R dependence from jetpt maps
    runs_maps = []
    for r in group.runs:
        mapping = {}
        for hn, dat in r.jetpt.items():
            parsed = prc.parse_jetpt_name(hn)
            if parsed is not None:
                mapping[parsed] = dat
        runs_maps.append(mapping)
    _plot_jetR_group(group, runs_maps, kind='incl', branch_ns=None, out_dir=dirs['jetR'])
    _plot_jetR_group(group, runs_maps, kind='lead', branch_ns=False, out_dir=dirs['jetR_sub'])
    _plot_jetR_group(group, runs_maps, kind='lead', branch_ns=True, out_dir=dirs['jetR_ns'])


def _build_groups(cfg: dict, runs_root: str, vacuum_tag: str, brick_base_tag: str, lengths: Sequence[float], qvals: Sequence[float], include_xsec_err: bool, single_slice_mode: bool, jet_radii: List[float], pt_edges: List[float]) -> Tuple[List[RunSet], List[GroupSpec], str]:
    vac = _load_run(cfg, vacuum_tag, label=str(cfg.get('MULTISIM_PLOT_VAC_LABEL', cfg.get('COMPARE_LABEL_A', 'vacuum'))), is_vacuum=True, brick_length=None, qhat0=None, include_xsec_err=include_xsec_err, single_slice_mode=single_slice_mode, jet_radii=jet_radii, pt_edges=pt_edges)
    variants: Dict[Tuple[float, float], RunSet] = {}
    brick_label = str(cfg.get('MULTISIM_PLOT_BRICK_LABEL', cfg.get('COMPARE_LABEL_B', 'brick')))
    for L in lengths:
        for q in qvals:
            tag = f"{brick_base_tag}_L{sanitize_tag_value(L)}_q{sanitize_tag_value(q)}"
            variants[(float(L), float(q))] = _load_run(cfg, tag, label=brick_label, is_vacuum=False, brick_length=float(L), qhat0=float(q), include_xsec_err=include_xsec_err, single_slice_mode=single_slice_mode, jet_radii=jet_radii, pt_edges=pt_edges)
    compare_dir = os.path.join(runs_root, 'comparisons_multisim', f"{vacuum_tag}_vs_{brick_base_tag}")
    ensure_dir(compare_dir)
    groups: List[GroupSpec] = []
    for q in qvals:
        runs = [vac] + [variants[(float(L), float(q))] for L in lengths]
        out_root = os.path.join(compare_dir, 'by_qhat', f"q{sanitize_tag_value(q)}")
        groups.append(GroupSpec(kind='by_qhat', fixed_value=float(q), runs=runs, out_root=out_root))
    for L in lengths:
        runs = [vac] + [variants[(float(L), float(q))] for q in qvals]
        out_root = os.path.join(compare_dir, 'by_length', f"L{sanitize_tag_value(L)}")
        groups.append(GroupSpec(kind='by_length', fixed_value=float(L), runs=runs, out_root=out_root))
    return [vac] + list(variants.values()), groups, compare_dir


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description='Grouped vacuum + configured-grid medium multisim plotter')
    parser.add_argument('--ini', required=True, help='Path to jetscape.ini')
    args = parser.parse_args(argv)

    ini = read_ini(args.ini)
    cfg = dict(ini.kv)
    if str(cfg.get('MultiSimEnabled', '')).strip() != '1':
        return _die('vacbrick_plotter_py.py requires MultiSimEnabled=1; use paperreadycomparisor.sh for single compares.')

    # logging / style
    run_base = expand_vars(str(cfg.get('RUNS_BASE', f"{os.path.expanduser('~')}/xscape_runs/{cfg.get('RUN_TAG','')}")), cfg)
    runs_root = run_base.rsplit('/' + str(cfg.get('RUN_TAG', '')), 1)[0] if str(cfg.get('RUN_TAG', '')) and run_base.endswith('/' + str(cfg.get('RUN_TAG'))) else str(Path(run_base).parent)
    if not runs_root:
        runs_root = os.path.join(os.path.expanduser('~'), 'xscape_runs')

    vac_tag = str(cfg.get('MULTISIM_PLOT_VAC_RUN_TAG', cfg.get('COMPARE_RUN_TAG_A', ''))).strip()
    brick_base_tag = str(cfg.get('MULTISIM_PLOT_BRICK_BASE_RUN_TAG', cfg.get('RUN_TAG', ''))).strip()
    if not vac_tag or not brick_base_tag:
        return _die('Missing MULTISIM_PLOT_VAC_RUN_TAG / MULTISIM_PLOT_BRICK_BASE_RUN_TAG (or valid fallbacks) in jetscape.ini')

    compare_root = os.path.join(runs_root, 'comparisons_multisim', f"{vac_tag}_vs_{brick_base_tag}")
    logs_dir = os.path.join(compare_root, 'logs')
    ensure_dir(logs_dir)
    global _LOG_FH
    _LOG_FH = open(os.path.join(logs_dir, 'vacbrick_plotter_py.log'), 'a', encoding='utf-8')
    _setup_crash_logging()
    _log(f'[diagnostics] python_pid={os.getpid()} trace_log={os.environ.get("VACBRICK_PLOTTER_TRACE_LOG", "")}')
    try:
        prc._LOG_FH = _LOG_FH
    except Exception:
        pass

    _log('stage: multisim grouped vacuum + brick plotting')
    _log(f'ini={args.ini}')
    _log(f'vacuum_tag={vac_tag}')
    _log(f'brick_base_tag={brick_base_tag}')
    _log(f'runs_root={runs_root}')

    lengths = ini.get_list('MultiSimBrickLengths')
    qvals = ini.get_list('MultiSimQhat0Values')
    if len(lengths) < 1 or len(qvals) < 1:
        return _die(f'MultiSim plotting requires nonempty MultiSimBrickLengths and MultiSimQhat0Values arrays; got lengths={lengths}, qhat0={qvals}')

    jet_radii = ini.get_list('JET_RADIUS_LIST')
    pt_edges = ini.get_list('PT_LEAD_BIN_EDGES')
    prc._set_known_r_values(jet_radii)
    prc.init_pt_lead_labels_from_ini(cfg)
    prc.SINGLE_SLICE_MODE = bool(int(str(cfg.get('SINGLE_SLICE_MODE', '0')).strip() or '0'))
    prc._FONTS = prc.apply_plot_style(cfg)
    try:
        _init_paperready_globals_from_cfg(cfg, jet_radii)
    except Exception as exc:
        return _die(f"Paperready-style plotting configuration invalid: {exc}")

    include_xsec_err = bool(int(str(cfg.get('INCLUDE_XSEC_NORM_ERR', '0')).strip() or '0'))
    _log(f'[load] preparing run list: include_xsec_err={int(include_xsec_err)} single_slice_mode={int(prc.SINGLE_SLICE_MODE)}')
    all_runs, groups, compare_dir = _build_groups(cfg, runs_root, vac_tag, brick_base_tag, lengths, qvals, include_xsec_err, prc.SINGLE_SLICE_MODE, jet_radii, pt_edges)
    _log(f'[cfg] compare_dir={compare_dir}')
    _log(f'[cfg] MultiSimBrickLengths={lengths}')
    _log(f'[cfg] MultiSimQhat0Values={qvals}')
    _log(f'[cfg] JET_RADIUS_LIST={jet_radii}')
    _log(f'[cfg] PT_LEAD_BIN_EDGES={pt_edges}')
    _log(f'[cfg] INCLUDE_XSEC_NORM_ERR={int(include_xsec_err)}')
    _log(f'[cfg] SINGLE_SLICE_MODE={int(prc.SINGLE_SLICE_MODE)}')
    _log(f'[load] loaded {len(all_runs)} run definitions and built {len(groups)} plot groups')

    failures = 0
    for group in groups:
        try:
            _plot_group(group)
        except Exception as exc:
            failures += 1
            _log(f'[ERROR] group {group.kind} fixed={group.fixed_value:g} failed: {exc}')

    _log_plot_summary()
    _log(f'done: groups={len(groups)} failures={failures}')
    try:
        _LOG_FH.close()
    except Exception:
        pass
    return 0 if failures == 0 else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException as exc:
        try:
            _log(f"[FATAL] unhandled exception escaped main: {type(exc).__name__}: {exc}")
            for fh in (_LOG_FH, _TRACE_FH):
                if fh is not None:
                    traceback.print_exc(file=fh)
                    fh.flush()
        finally:
            raise
