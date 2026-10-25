"""Shared helpers for the CG4 harness: paths, config, JSONL, hashing, chain ids, logging."""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import sys
from pathlib import Path
from typing import Iterable, Iterator

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIGS = ROOT / "configs"
DATA = ROOT / "data"
SOURCES = DATA / "sources"
CORPORA = DATA / "corpora"
HELDOUT = DATA / "heldout"
PROBES = DATA / "probes"
RESULTS = ROOT / "results"
CHAINS = RESULTS / "chains"
LOGS = ROOT / "logs"
SCHEMAS = ROOT / "schemas"

LANGUAGES = ["EN", "BN"]
REGIMES = ["REPLACE", "ACCUMULATE", "ACCUMULATE-FILTER"]
BENGALI_RANGE = ("ঀ", "৿")


def utf8_stdout() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


RUNTIME_KEYS = {("training", "micro_batch_seqs")}   # operational only (00_AGENT_BRIEF.md section 6); never a design value


def load_chains_cfg(path: Path | None = None) -> dict:
    """configs/chains.yaml (frozen, registered) with the whitelisted operational overrides of configs/runtime.yaml on top."""
    with open(path or CONFIGS / "chains.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    rt_path = CONFIGS / "runtime.yaml"
    if path is None and rt_path.exists():
        rt = yaml.safe_load(open(rt_path, encoding="utf-8")) or {}
        for sect, vals in rt.items():
            for k, v in (vals or {}).items():
                if (sect, k) not in RUNTIME_KEYS:
                    raise SystemExit(f"configs/runtime.yaml: {sect}.{k} is not an operational setting (allowed: {sorted(RUNTIME_KEYS)}); design values live in chains.yaml")
                cfg[sect][k] = v
        eff, micro = int(cfg["training"]["effective_batch_seqs"]), int(cfg["training"]["micro_batch_seqs"])
        if micro <= 0 or eff % micro:
            raise SystemExit(f"micro_batch_seqs {micro} must divide effective_batch_seqs {eff} (the effective batch is fixed)")
    return cfg


def load_corpora_cfg(path: Path | None = None) -> dict:
    with open(path or CONFIGS / "corpora.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def ensure_dirs() -> None:
    for p in (SOURCES, CORPORA, HELDOUT, PROBES, RESULTS, CHAINS, LOGS, RESULTS / "analysis", RESULTS / "samples", RESULTS / "human_read"):
        p.mkdir(parents=True, exist_ok=True)


def read_jsonl(path: Path) -> Iterator[dict]:
    if not Path(path).exists():
        return iter(())
    def gen():
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    yield json.loads(line)
    return gen()


def write_jsonl(path: Path, records: Iterable[dict]) -> int:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
    return n


def append_jsonl(path: Path, records: Iterable[dict]) -> int:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(path, "a", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
    return n


def write_json(path: Path, obj) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def read_json(path: Path, default=None):
    p = Path(path)
    if not p.exists():
        return default
    return json.load(open(p, encoding="utf-8"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def sha256_dir(path: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(x for x in Path(path).rglob("*") if x.is_file()):
        h.update(p.name.encode()); h.update(sha256_file(p).encode())
    return h.hexdigest()


def chain_id(language: str, regime: str, tokenizer_condition: str = "SUBWORD") -> str:
    return f"{language}-{regime}" + ("" if tokenizer_condition == "SUBWORD" else f"-{tokenizer_condition}")


CHAIN_DEFAULTS = {"tokenizer_condition": "SUBWORD", "seed_offset": 0, "priority": 0, "variant": None, "tokens": None, "gen0": None,
                  "sampling": None, "until": None, "purpose": None, "enabled": True}


def with_defaults(c: dict) -> dict:
    return {**CHAIN_DEFAULTS, **c}


def confirmatory_chains(cfg: dict) -> list[dict]:
    """The 2 x 3 pre-registered chains (seed offset 0, priority 0)."""
    return [with_defaults({"id": chain_id(l, r), "language": l, "regime": r}) for l in cfg["languages"] for r in cfg["regimes"]]


def robustness_chains(cfg: dict) -> list[dict]:
    """Pre-registered additions in priority order (configs/chains.yaml robustness_chains, enabled only)."""
    return sorted((with_defaults(c) for c in cfg.get("robustness_chains", []) if c.get("enabled", True)), key=lambda c: (c["priority"], c["id"]))


def all_chains(cfg: dict) -> list[dict]:
    return confirmatory_chains(cfg) + robustness_chains(cfg) + [with_defaults(c) for c in cfg.get("exploratory_chains", []) if c.get("enabled")]


def chain_meta(cfg: dict) -> dict[str, dict]:
    return {c["id"]: c for c in all_chains(cfg)}


def script_ratio(text: str, language: str) -> float:
    """Share of letters (digits and punctuation ignored) in the target script: Bengali block for BN, Latin script for EN
    (accented Latin letters count as in-script; reviewer fix 2026-10-12, previously isascii)."""
    import regex
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    if language == "BN":
        n = sum(1 for c in letters if BENGALI_RANGE[0] <= c <= BENGALI_RANGE[1])
    else:
        n = len(regex.findall(r"\p{Script=Latin}", text))
    return min(1.0, n / len(letters))


def repeat_4gram_rate(tokens: list[str]) -> float:
    if len(tokens) < 8:
        return 0.0
    grams = [tuple(tokens[i:i + 4]) for i in range(len(tokens) - 3)]
    return 1.0 - len(set(grams)) / len(grams)


_WORD_RE = None


def words(text: str) -> list[str]:
    """Grapheme-aware word split, identical for both languages: runs of letters/marks (Bengali vowel signs, conjuncts) or
    digits; ZWJ/ZWNJ (U+200D/U+200C) are kept inside words (e.g. র‍্যাব), reviewer fix 2026-10-12."""
    global _WORD_RE
    if _WORD_RE is None:
        import regex
        _WORD_RE = regex.compile(r"[\p{L}\p{M}\u200C\u200D]+|\p{N}+")
    return _WORD_RE.findall(text)


# ---------------- MinHash near-duplicate detection (shared by prepare_corpora.py and the ACCUMULATE-FILTER rule) ----------------
def minhash(tokens: list[str], perms: int = 64, seed: int = 1):
    """MinHash signature over word 3-gram shingles (lower-cased tokens). Returns a uint64 array of length perms."""
    import hashlib
    import numpy as np
    toks = [t.lower() for t in tokens]
    shingles = {" ".join(toks[i:i + 3]) for i in range(max(1, len(toks) - 2))}
    if not shingles:
        return np.zeros(perms, dtype=np.uint64)
    hs = np.array([int(hashlib.md5(s.encode()).hexdigest()[:16], 16) for s in shingles], dtype=np.uint64)
    rng = np.random.default_rng(seed)
    a = rng.integers(1, 2**61 - 1, size=perms, dtype=np.uint64); b = rng.integers(0, 2**61 - 1, size=perms, dtype=np.uint64)
    mod = np.uint64(2**61 - 1)
    return np.array([((a[i] * hs + b[i]) % mod).min() for i in range(perms)], dtype=np.uint64)


class NearDupIndex:
    """Banded LSH over MinHash signatures; a document is a near-duplicate if its estimated Jaccard with any indexed
    signature is >= threshold. Incremental, so the ACCUMULATE-FILTER rule can index the seed corpus and every kept
    synthetic document and test each new one (configs/chains.yaml filter.near_dup_jaccard)."""

    def __init__(self, perms: int = 64, threshold: float = 0.8, bands: int = 8):
        self.perms, self.threshold, self.bands = perms, threshold, bands
        self.rows = perms // bands
        self.buckets: dict[tuple, list[int]] = {}
        self.sigs: list = []

    def _keys(self, sig):
        return [(b, sig[b * self.rows:(b + 1) * self.rows].tobytes()) for b in range(self.bands)]

    def is_dup(self, sig) -> bool:
        cands = set()
        for key in self._keys(sig):
            cands.update(self.buckets.get(key, []))
        return any((self.sigs[j] == sig).mean() >= self.threshold for j in cands)

    def add(self, sig) -> int:
        idx = len(self.sigs); self.sigs.append(sig)
        for key in self._keys(sig):
            self.buckets.setdefault(key, []).append(idx)
        return idx

    def add_if_new(self, sig) -> bool:
        if self.is_dup(sig):
            return False
        self.add(sig); return True


def log_decision(text: str) -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    with open(LOGS / "decisions.md", "a", encoding="utf-8") as f:
        f.write(f"- {now_iso()} — {text}\n")
