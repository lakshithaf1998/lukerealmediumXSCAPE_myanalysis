#!/usr/bin/env python3
# detect_duplicate_seeds.py
# Version: v1.4
#
# Change log:
#  - v1.4 (2026-03-17):
#      * FIX: Do not report a header-only/empty seeds_seen.csv as a clean pass; try recovering seeds from
#        existing workflow SIM outputs first, then hard-fail with a clear diagnostic if recovery is impossible.
#      * NEW: Recovery mode reconstructs final task seeds from jetscape.ini + ${DIR_SIM}/<pthat>/<batch>/job*_final_state_hadrons.dat
#        using the same deterministic seed formula as the workflow, without changing SIM-side code.
#      * NEW: Writes a recovered CSV snapshot next to the canonical CSV as seeds_seen_recovered.csv for debugging.
#  - v1.3 (2026-03-01):
#      * Prefer $HOME/xscape_runs/<RUN_TAG>/final/seeds_seen.csv as the default (matches your workflow),
#        regardless of RUNS_BASE naming (e.g., xscape_runs vs xscape_runs).
#      * Still respects explicit --csv override and absolute DIR_FINAL in ini.
#  - v1.2 (2026-03-01): Better RUNS_BASE handling; clearer errors.
#  - v1.1 (2026-03-01): INI-based default path resolution; NA handling; clearer summary.
#
# Purpose:
#  - Read seeds_seen.csv (written by merger) and detect duplicate seeds across tasks/bins.
#  - Exit code: 0 if no duplicates, 1 if duplicates found, 2 on error.

import argparse
import csv
import glob
import json
import os
import re
import sys
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

def log(msg: str) -> None:
    print(msg, flush=True)

def parse_ini_value(path: str, key: str):
    if not os.path.isfile(path):
        return None
    pat = re.compile(rf'^\s*{re.escape(key)}\s*=\s*(.*?)\s*$')
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith(";"):
                continue
            # strip inline comments outside quotes
            if "#" in line:
                out = []
                inq = False
                for ch in line:
                    if ch == '"':
                        inq = not inq
                    if ch == "#" and not inq:
                        break
                    out.append(ch)
                line = "".join(out).strip()
            m = pat.match(line)
            if m:
                val = m.group(1).strip()
                if len(val) >= 2 and ((val[0] == '"' and val[-1] == '"') or (val[0] == "'" and val[-1] == "'")):
                    val = val[1:-1]
                return os.path.expandvars(val)
    return None

def is_na(seed: str) -> bool:
    s = (seed or "").strip()
    return (s == "" or s.upper() in ("NA", "N/A", "NONE"))

def strip_inline_comment(line: str) -> str:
    out = []
    in_single = False
    in_double = False
    for ch in line:
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            break
        elif ch == ";" and not in_single and not in_double:
            break
        out.append(ch)
    return "".join(out).strip()

def expand_cfg_vars(val: str, cfg: Dict[str, str]) -> str:
    pattern = re.compile(r'\$(\{)?([A-Za-z_][A-Za-z0-9_]*)\}?')
    def repl(match):
        key = match.group(2)
        if key in cfg:
            return cfg[key]
        return os.environ.get(key, match.group(0))
    prev = None
    cur = val
    for _ in range(8):
        cur = pattern.sub(repl, cur)
        cur = os.path.expandvars(cur)
        if cur == prev:
            break
        prev = cur
    return cur


def parse_ini_file(path: str) -> Dict[str, str]:
    cfg: Dict[str, str] = {}
    if not os.path.isfile(path):
        return cfg
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith('#') or line.startswith(';'):
                continue
            line = strip_inline_comment(line)
            if '=' not in line:
                continue
            key, val = line.split('=', 1)
            key = key.strip()
            val = val.strip()
            if len(val) >= 2 and ((val[0] == '"' and val[-1] == '"') or (val[0] == "'" and val[-1] == "'")):
                val = val[1:-1]
            cfg[key] = expand_cfg_vars(val, cfg)
    return cfg


def parse_ini_array(cfg: Dict[str, str], key: str) -> List[str]:
    raw = (cfg.get(key) or '').strip()
    if not raw:
        return []
    if raw.startswith('(') and raw.endswith(')'):
        raw = raw[1:-1].strip()
    if not raw:
        return []
    return [tok.strip() for tok in raw.replace(',', ' ').split() if tok.strip()]


def as_int(val: Optional[str], default: Optional[int] = None) -> Optional[int]:
    try:
        return int(str(val).strip())
    except Exception:
        return default


def meta_status_ok(meta_path: str) -> bool:
    if not os.path.isfile(meta_path):
        return False
    try:
        with open(meta_path, 'r', encoding='utf-8', errors='replace') as f:
            obj = json.load(f)
        return str(obj.get('status', '')).strip().lower() == 'ok'
    except Exception:
        return False


def choose_batch_id(slice_root: str, marker_path: str, default_batch: str) -> str:
    if os.path.isfile(marker_path):
        try:
            batch = open(marker_path, 'r', encoding='utf-8', errors='replace').read().strip()
            if batch:
                return batch
        except Exception:
            pass
    if os.path.isdir(slice_root):
        try:
            subdirs = sorted([d for d in os.listdir(slice_root) if os.path.isdir(os.path.join(slice_root, d))])
            if len(subdirs) == 1:
                return subdirs[0]
        except Exception:
            pass
    return default_batch


def write_recovered_csv(csv_path: str, rows: List[Dict[str, str]]) -> Optional[str]:
    out_path = os.path.join(os.path.dirname(csv_path), 'seeds_seen_recovered.csv')
    try:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, 'w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, fieldnames=['pthat_low', 'pthat_high', 'task', 'seed'])
            w.writeheader()
            for row in rows:
                w.writerow(row)
        return out_path
    except Exception:
        return None


def recover_rows_from_sim(ini_path: str) -> Tuple[List[Dict[str, str]], List[str]]:
    cfg = parse_ini_file(ini_path)
    notes: List[str] = []
    if not cfg:
        return [], ['INI parse failed or file missing; cannot recover from SIM outputs.']

    if str(cfg.get('SEED_SALT_TIME', '0')).strip() == '1':
        return [], ['SEED_SALT_TIME=1 makes launched seeds time-salted and non-reconstructible from SIM outputs.']

    base_seed = as_int(cfg.get('BASE_SEED'), 1)
    stride = as_int(cfg.get('SeedStrideSlice'), 1000000)
    sim_batch_default = (cfg.get('SIM_BATCH_ID') or 'batch0').strip() or 'batch0'

    run_tag = (cfg.get('RUN_TAG') or 'UNKNOWN_RUN_TAG').strip() or 'UNKNOWN_RUN_TAG'
    runs_base = (cfg.get('RUNS_BASE') or os.path.join(os.path.expandvars('$HOME'), 'xscape_runs', run_tag)).strip()
    dir_sim = (cfg.get('DIR_SIM') or os.path.join(runs_base, 'sim')).strip()
    dir_log_sim = (cfg.get('DIR_LOG_SIM') or os.path.join(runs_base, 'logs', 'sim')).strip()

    pt_lo = parse_ini_array(cfg, 'PT_LO')
    pt_hi = parse_ini_array(cfg, 'PT_HI')
    jobs = parse_ini_array(cfg, 'JOBS')
    if not pt_lo or not pt_hi or not jobs:
        return [], ['PT_LO/PT_HI/JOBS are missing or empty in jetscape.ini; cannot recover from SIM outputs.']
    if not (len(pt_lo) == len(pt_hi) == len(jobs)):
        return [], [f'PT_LO/PT_HI/JOBS length mismatch: {len(pt_lo)} / {len(pt_hi)} / {len(jobs)}']

    rows: List[Dict[str, str]] = []
    tasks_seen = 0
    for slice_index, (pl, ph, nj_raw) in enumerate(zip(pt_lo, pt_hi, jobs)):
        nj = as_int(nj_raw, None)
        if nj is None or nj < 1:
            notes.append(f'skipping slice {pl}-{ph}: invalid JOBS entry {nj_raw!r}')
            continue
        slice_root = os.path.join(dir_sim, f'{pl}-{ph}')
        marker = os.path.join(dir_log_sim, f'subdir_sim_{pl}_{ph}.txt')
        batch_id = choose_batch_id(slice_root, marker, sim_batch_default)
        slice_dir = os.path.join(slice_root, batch_id)
        qdir = os.path.join(slice_dir, 'quarantine')
        notes.append(f'slice {pl}-{ph}: batch_id={batch_id} slice_dir={slice_dir}')
        for task in range(1, nj + 1):
            hadron = os.path.join(slice_dir, f'job{task}_final_state_hadrons.dat')
            meta = os.path.join(slice_dir, 'meta', f'job{task}.json')
            live_ok = os.path.isfile(hadron) and os.path.getsize(hadron) > 0
            meta_ok = meta_status_ok(meta)
            if not (live_ok or meta_ok):
                continue
            retry_offset = 0
            if os.path.isdir(qdir):
                retry_offset = len(glob.glob(os.path.join(qdir, f'job{task}_*')))
            seed_raw = int(base_seed) + int(slice_index) * int(stride) + int(task) + int(retry_offset) * 7919
            seed = (seed_raw % 2000000000) + 1
            rows.append({
                'pthat_low': str(pl),
                'pthat_high': str(ph),
                'task': str(task),
                'seed': str(seed),
            })
            tasks_seen += 1
    if tasks_seen == 0:
        notes.append(f'No completed task outputs found under DIR_SIM={dir_sim}')
    else:
        notes.append(f'Recovered {tasks_seen} task seed rows from existing SIM outputs under DIR_SIM={dir_sim}')
    return rows, notes


def resolve_default_csv(ini_path: str) -> str:
    # ✅ Your preferred convention (most reliable):
    #   $HOME/xscape_runs/<RUN_TAG>/final/seeds_seen.csv
    run_tag = parse_ini_value(ini_path, "RUN_TAG")
    run_tag = os.path.expandvars(run_tag) if run_tag else None
    if not run_tag:
        run_tag = "UNKNOWN_RUN_TAG"
    preferred = os.path.join(os.path.expandvars("$HOME"), "xscape_runs", run_tag, "final", "seeds_seen.csv")

    # If ini explicitly sets DIR_FINAL as absolute, honor it.
    dir_final = parse_ini_value(ini_path, "DIR_FINAL")
    dir_final = os.path.expandvars(dir_final) if dir_final else None
    if dir_final and os.path.isabs(dir_final):
        return os.path.join(dir_final, "seeds_seen.csv")

    # Otherwise prefer the conventional location
    return preferred

def main():
    ap = argparse.ArgumentParser(description="Detect duplicate RNG seeds in seeds_seen.csv (from merger or recovered from SIM outputs).")
    ap.add_argument("--ini", default="jetscape.ini", help="Path to jetscape.ini (default: ./jetscape.ini)")
    ap.add_argument("--csv", default=None, help="Path to seeds_seen.csv (overrides default).")
    ap.add_argument("--ignore-na", action="store_true", help="Ignore rows where seed is NA/empty.")
    args = ap.parse_args()

    csv_path = args.csv if args.csv else resolve_default_csv(args.ini)

    log(f"[dupseed] INI: {args.ini}")
    log(f"[dupseed] CSV: {csv_path}")

    rows: List[Dict[str, str]] = []
    raw_rows = 0
    csv_exists = os.path.isfile(csv_path)

    if csv_exists:
        with open(csv_path, "r", encoding="utf-8", errors="replace", newline="") as f:
            reader = csv.DictReader(f)
            required = {"pthat_low", "pthat_high", "task", "seed"}
            if not required.issubset(set(reader.fieldnames or [])):
                log(f"[dupseed] ERROR: CSV missing required columns. Found: {reader.fieldnames}")
                return 2
            for r in reader:
                raw_rows += 1
                rows.append({
                    'pthat_low': (r.get('pthat_low') or '').strip(),
                    'pthat_high': (r.get('pthat_high') or '').strip(),
                    'task': (r.get('task') or '').strip(),
                    'seed': (r.get('seed') or '').strip(),
                })

    if (not csv_exists) or raw_rows == 0:
        if not csv_exists:
            log(f"[dupseed] WARN: seeds CSV not found at canonical path: {csv_path}")
        else:
            log(f"[dupseed] WARN: seeds CSV is header-only/empty: {csv_path}")
            log("[dupseed] WARN: This commonly happens when submit_sliced_sim.sh is rerun and resets seeds_seen.csv before new workers append.")
        recovered_rows, notes = recover_rows_from_sim(args.ini)
        for note in notes:
            log(f"[dupseed] RECOVER: {note}")
        if recovered_rows:
            rows = recovered_rows
            snap = write_recovered_csv(csv_path, rows)
            if snap:
                log(f"[dupseed] RECOVER: wrote recovered CSV snapshot -> {snap}")
        else:
            log("[dupseed] ERROR: no usable seed rows found in CSV, and SIM-output recovery failed.")
            return 2

    seed_to_locs = defaultdict(list)
    total = 0
    for r in rows:
        seed = (r.get("seed") or "").strip()
        if args.ignore_na and is_na(seed):
            continue
        total += 1
        loc = f"pthat=({r.get('pthat_low','?')},{r.get('pthat_high','?')}), task={r.get('task','?')}"
        seed_to_locs[seed].append(loc)

    dup = {s: locs for s, locs in seed_to_locs.items() if len(locs) > 1 and not (args.ignore_na and is_na(s))}

    log(f"[dupseed] Rows available: {len(rows)}")
    log(f"[dupseed] Rows checked: {total}")
    log(f"[dupseed] Unique seeds: {len(seed_to_locs)}")

    if not dup:
        log("[dupseed] OK: no duplicate seeds detected.")
        return 0

    log(f"[dupseed] FAIL: duplicate seeds detected: {len(dup)}")
    for seed in sorted(dup.keys(), key=lambda x: (is_na(x), x)):
        locs = dup[seed]
        log(f"[dupseed] DUP seed={seed} count={len(locs)}")
        for loc in locs:
            log(f"  - {loc}")

    return 1

if __name__ == "__main__":
    sys.exit(main())
