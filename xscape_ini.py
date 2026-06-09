#!/usr/bin/env python3
# xscape_ini.py v1.2
# CHANGELOG
# v1.2 (robust boolean + list parsing):
#   • FIX: Normalize file to LF line endings (no CRLF).
#   • FIX: Ini.get_bool() now uses parse_bool() for consistent parsing of 0/1, true/false, yes/no, on/off.
#   • FIX: parse_list() is now STRICT: any non-numeric token raises ValueError (fails fast instead of silently truncating).
#   • NEW: parse_bool() can be strict (default True) and raises on unrecognized tokens (except empty -> default).
#
# v1.1: Add expand_vars() + parse_bool(); strip surrounding quotes on read so Python matches bash/c++ expectations.
#       expand_vars() expands $VAR and ${VAR} using ini values first, then env vars.
#
# v1.0: Shared jetscape.ini parser for Python tools (fits/comparisor/plotters).
#       Matches the C++ analyzer parsing rules:
#         • KEY=VALUE lines
#         • bash-style lists: KEY=(a b c) or KEY=(a,b,c)
#         • inline comments start with # (ignored outside quotes)
#         • quoted strings preserved (strip_quotes() helper provided)

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

def _strip_quotes(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and ((s[0] == s[-1] == '"') or (s[0] == s[-1] == "'")):
        return s[1:-1]
    return s

def _strip_inline_comment(line: str) -> str:
    in_s = False
    in_d = False
    out_chars: List[str] = []
    prev = ''
    for ch in line:
        esc = (prev == '\\')
        if ch == '"' and (not in_s) and (not esc):
            in_d = not in_d
        elif ch == "'" and (not in_d) and (not esc):
            in_s = not in_s
        elif ch == '#' and (not in_s) and (not in_d):
            break
        out_chars.append(ch)
        prev = ch
    return ''.join(out_chars)

def parse_list(val: str) -> List[float]:
    """Parse '(a b c)' or 'a,b,c' into floats.

    STRICT: any non-numeric token raises ValueError instead of silently truncating.
    """
    v = _strip_quotes(val).strip()
    if v == '':
        return []
    if v.startswith('(') and v.endswith(')'):
        v = v[1:-1]
    v = v.replace(',', ' ')
    parts = [p for p in v.split() if p]
    out: List[float] = []
    bad: List[str] = []
    for p in parts:
        try:
            out.append(float(p))
        except ValueError:
            bad.append(p)
    if bad:
        raise ValueError(f"Invalid numeric token(s) in list: {bad}  (raw={val!r})")
    return out
def parse_bool(val: str, *, default: bool=False, strict: bool=True) -> bool:
    """Parse common boolean spellings.

    Accepted true:  1, true, t, yes, y, on
    Accepted false: 0, false, f, no, n, off

    If val is empty: returns default.
    If strict=True and val is unrecognized: raises ValueError.
    """
    v = _strip_quotes(str(val)).strip().lower()
    if v == '':
        return default
    if v in ('1','true','t','yes','y','on'):
        return True
    if v in ('0','false','f','no','n','off'):
        return False
    # fallback: try numeric
    try:
        return bool(int(float(v)))
    except Exception:
        if strict:
            raise ValueError(f"Invalid boolean value: {val!r}")
        return default

def expand_vars(p: str, ini: Dict[str, str]) -> str:
    """Expand $VAR and ${VAR} using ini first, then environment variables."""
    if p is None:
        return ''
    s = str(p)
    s = os.path.expanduser(s) if s.startswith('~') else s

    def repl(m):
        k = m.group(1) or m.group(2)
        if k in ini:
            return str(ini[k])
        return os.environ.get(k, m.group(0))

    out = s
    for _ in range(12):
        prev = out
        out = re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", lambda m: repl(m), out)
        out = re.sub(r"\$([A-Za-z_][A-Za-z0-9_]*)", lambda m: repl(m), out)
        if out == prev:
            break
    return out
@dataclass
class Ini:
    path: str
    kv: Dict[str, str]

    def has(self, key: str) -> bool:
        return key in self.kv

    def get_str(self, key: str, default: str = '', required: bool = False) -> str:
        if key in self.kv:
            return self.kv[key]
        if required:
            raise KeyError(f"Missing required INI key: {key}")
        return default

    def get_int(self, key: str, default: int = 0, required: bool = False) -> int:
        raw = _strip_quotes(self.get_str(key, str(default), required=required)).strip()
        return int(raw)

    def get_float(self, key: str, default: float = 0.0, required: bool = False) -> float:
        raw = _strip_quotes(self.get_str(key, str(default), required=required)).strip()
        return float(raw)

    def get_bool(self, key: str, default: bool = False, required: bool = False) -> bool:
        raw = self.get_str(key, '1' if default else '0', required=required)
        return parse_bool(raw, default=default, strict=True)

    def get_list(self, key: str, default: Optional[List[float]] = None) -> List[float]:
        if default is None:
            default = []
        if key not in self.kv:
            return list(default)
        return parse_list(self.kv[key])

def read_ini(path: str) -> Ini:
    kv: Dict[str, str] = {}
    section = ''
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        for raw in f:
            line = _strip_inline_comment(raw).strip()
            if not line or line.startswith('#') or line.startswith(';'):
                continue
            if line.startswith('[') and line.endswith(']'):
                section = line[1:-1].strip()
                # jetscape.ini currently does not use sections; we ignore 'section' for now.
                continue
            if '=' not in line:
                continue
            key, val = line.split('=', 1)
            key = key.strip()
            val = val.strip()
            if key.startswith('export '):
                key = key[len('export '):].strip()
            if key:
                kv[key] = _strip_quotes(val)
    return Ini(path=path, kv=kv)













