# Copyright (c) 2026 mrQhere. All rights reserved.

"""
llm_agent.py  —  Hermes Agent
==============================
A thin wrapper around a locally-running Ollama server (or any OpenAI-compatible
endpoint) that gives the quant terminal a persistent, self-improving LLM brain.

Design goals
------------
* Works entirely offline — no API keys, no cloud calls.
* Fails gracefully — if Ollama is not running, every public method returns a
  neutral placeholder string so the rest of the system is unaffected.
* Improves over time — per-ticker memory (last N decisions + outcomes) is
  prepended to every prompt so the model can reason about its own track record.
* Lightweight — defaults to phi3:mini (~2.3 GB), runs on 4 GB RAM with no GPU.

Quick start
-----------
1. Install Ollama:  https://ollama.com/download   (one-click installer)
2. Pull the model:  ollama pull phi3:mini
3. Run the server:  ollama serve          (auto-started on most installs)
That's it.  The agent auto-detects the server on http://localhost:11434.
"""

import json
import os
import time
import logging
from datetime import datetime, timezone
from typing import Optional

# ── optional imports ──────────────────────────────────────────────────────────
try:
    import ollama as _ollama
    _OLLAMA_AVAILABLE = True
except ImportError:
    _OLLAMA_AVAILABLE = False

# ── paths ─────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR    = os.path.join(BASE_DIR, "data_lake")
MEMORY_FILE = os.path.join(DATA_DIR, "hermes_memory.json")
LOG_DIR     = os.path.join(BASE_DIR, "logs")
HERMES_LOG  = os.path.join(LOG_DIR, "hermes.log")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR,  exist_ok=True)

_log = logging.getLogger("hermes")
if not _log.handlers:
    fh = logging.FileHandler(HERMES_LOG)
    fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    _log.addHandler(fh)
    _log.setLevel(logging.INFO)

# ── constants ─────────────────────────────────────────────────────────────────
DEFAULT_MODEL   = "phi3:mini"
MEMORY_CAP      = 200          # max entries kept in memory file (all tickers)
TICKER_MEM_CAP  = 5            # last N entries fed into each ticker's prompt
LLM_TIMEOUT     = 30           # seconds — if ollama takes longer, return placeholder
OLLAMA_HOST     = "http://localhost:11434"

_SYSTEM_PROMPT = (
    "You are Hermes, a disciplined quantitative research assistant embedded in a "
    "local stock analysis terminal. Your job is to provide a brief, honest, risk-first "
    "commentary on a single ticker's current AI signal and fundamentals. "
    "Rules: (1) 3 sentences maximum. (2) Never say 'invest' or 'buy' — say 'the signal "
    "suggests' instead. (3) Always mention the biggest risk factor. (4) If the signal is "
    "HOLD or SELL, validate the caution. (5) Reference any past memory context if provided."
)


# ── memory helpers ────────────────────────────────────────────────────────────

def _load_memory() -> dict:
    """Load the full memory dict from disk. Returns {} on any error."""
    try:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        _log.warning(f"Memory load failed: {e}")
    return {}


def _save_memory(mem: dict) -> None:
    """Persist memory dict to disk, pruning to MEMORY_CAP total entries."""
    try:
        # Flatten all entries, sort by timestamp, keep newest MEMORY_CAP
        all_entries = []
        for ticker, entries in mem.items():
            for e in entries:
                all_entries.append((ticker, e))
        all_entries.sort(key=lambda x: x[1].get("ts", ""), reverse=True)
        all_entries = all_entries[:MEMORY_CAP]

        # Rebuild dict
        pruned: dict = {}
        for ticker, e in all_entries:
            pruned.setdefault(ticker, []).append(e)

        with open(MEMORY_FILE, "w") as f:
            json.dump(pruned, f, indent=2)
    except Exception as e:
        _log.warning(f"Memory save failed: {e}")


def _get_ticker_memory(ticker: str, mem: dict) -> str:
    """Return the last TICKER_MEM_CAP entries for a ticker as a formatted string."""
    entries = mem.get(ticker, [])[-TICKER_MEM_CAP:]
    if not entries:
        return ""
    lines = ["--- Past Hermes Notes for this ticker ---"]
    for e in entries:
        lines.append(f"[{e.get('ts','?')}] Signal={e.get('signal','?')} | "
                     f"Outcome={e.get('outcome','pending')} | Note={e.get('note','')}")
    return "\n".join(lines)


def _append_memory(ticker: str, mem: dict, entry: dict) -> None:
    """Append one entry to a ticker's memory list (in-place)."""
    entry["ts"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")
    mem.setdefault(ticker, []).append(entry)


# ── LLM call helper ───────────────────────────────────────────────────────────

def _ollama_chat(prompt: str, timeout: int = LLM_TIMEOUT) -> Optional[str]:
    """
    Call the local Ollama server synchronously.
    Returns the model's text response, or None on any failure.
    """
    if not _OLLAMA_AVAILABLE:
        return None
    try:
        client = _ollama.Client(host=OLLAMA_HOST)
        resp = client.chat(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            options={"num_predict": 200, "temperature": 0.3},
        )
        return resp["message"]["content"].strip()
    except Exception as e:
        _log.debug(f"Ollama call failed: {e}")
        return None


# ── public API ────────────────────────────────────────────────────────────────

class HermesAgent:
    """
    Main agent class.  Instantiate once and reuse across the backend cycle.

    Usage::
        agent = HermesAgent()
        comment = agent.analyze(rep_dict)          # per-ticker
        review  = agent.daily_review(lb_list)      # once per cycle
        suggestions = agent.suggest_asset_changes(lb_list)  # weekly pruning suggestions
    """

    def __init__(self):
        self._available = _OLLAMA_AVAILABLE and self._check_server()
        if self._available:
            _log.info(f"Hermes online — model: {DEFAULT_MODEL}")
        else:
            _log.info("Hermes offline — LLM commentary disabled (ollama not running or not installed).")

    # ── internal ──────────────────────────────────────────────────────────────

    @staticmethod
    def _check_server() -> bool:
        """Ping the Ollama server. Returns True if reachable within 2s."""
        try:
            import urllib.request
            with urllib.request.urlopen(OLLAMA_HOST, timeout=2):
                return True
        except Exception:
            return False

    @property
    def is_available(self) -> bool:
        return self._available

    # ── per-ticker analysis ───────────────────────────────────────────────────

    def analyze(self, rep: dict) -> str:
        """
        Generate a 3-sentence Hermes commentary for a single ticker.

        Parameters
        ----------
        rep : dict
            The full prediction JSON blob from the backend (same dict stored in DB).

        Returns
        -------
        str
            Plain-English 3-sentence analysis, or a neutral placeholder if the
            LLM is unavailable.
        """
        ticker  = rep.get("Ticker", "UNKNOWN")
        signal  = rep.get("Signal", "HOLD")
        sharpe  = rep.get("Sharpe", 0)
        max_dd  = rep.get("MaxDD", 0)
        prob    = rep.get("Prob", 50)
        pio     = rep.get("Piotroski_Score")
        sent    = rep.get("Sentiment_Score", 0)
        mmode   = rep.get("Market_Mode", "N/A")
        cagr    = rep.get("Investing_Tools", {}).get("CAGR", 0)
        ghost   = rep.get("Ghost", [])
        fwd_ret = ((ghost[-1] - rep.get("Price", 1)) / rep.get("Price", 1) * 100) if ghost and rep.get("Price") else 0

        mem  = _load_memory()
        past = _get_ticker_memory(ticker, mem)

        prompt = f"""Ticker: {ticker}
Signal: {signal}
Market Mode: {mmode}
7-Day Projected Return: {fwd_ret:.2f}%
Win Probability (Monte Carlo): {prob:.1f}%
Sharpe Ratio: {sharpe:.2f}
Max Historical Drawdown: {max_dd:.2f}%
5Y CAGR: {cagr:.2f}%
Piotroski F-Score: {pio if pio is not None else 'N/A'}/9
News Sentiment: {sent:.3f}  (range: -1 bearish → +1 bullish)

{past}

Write a 3-sentence analysis. Sentence 1: market positioning. Sentence 2: key risk. Sentence 3: how the fundamentals align with or contradict the signal."""

        if not self._available:
            return f"[Hermes offline] Signal {signal} — Sharpe {sharpe:.2f}, MaxDD {max_dd:.2f}%. Enable Ollama for detailed analysis."

        t0 = time.time()
        result = _ollama_chat(prompt)
        elapsed = time.time() - t0

        if result is None:
            result = f"[Hermes unavailable after {elapsed:.1f}s] Signal: {signal}."
        else:
            _log.info(f"[{ticker}] Analysis in {elapsed:.1f}s")

        # Persist to memory
        _append_memory(ticker, mem, {
            "signal":  signal,
            "sharpe":  sharpe,
            "max_dd":  max_dd,
            "prob":    prob,
            "note":    result[:200],    # truncate for storage
            "outcome": "pending",       # updated by daily_review()
        })
        _save_memory(mem)

        return result

    # ── daily cycle review ────────────────────────────────────────────────────

    def daily_review(self, lb_data: list, price_changes: dict) -> str:
        """
        End-of-cycle review.  Compares yesterday's signals to today's actual
        price direction and updates memory with outcomes.

        Parameters
        ----------
        lb_data : list
            Current leaderboard entries (same format as `leaderboard` DB table).
        price_changes : dict
            {ticker: float} — today's % price change vs yesterday.

        Returns
        -------
        str
            A brief review summary from Hermes (or placeholder if offline).
        """
        mem = _load_memory()
        outcomes = []

        for entry in lb_data:
            ticker = entry.get("Asset", "")
            chg    = price_changes.get(ticker, None)
            if chg is None or ticker not in mem or not mem[ticker]:
                continue

            # Update the most recent pending entry for this ticker
            last = mem[ticker][-1]
            if last.get("outcome") == "pending":
                signal = last.get("signal", "")
                correct = (
                    ("BUY" in signal and chg > 0) or
                    ("SELL" in signal and chg < 0) or
                    ("HOLD" in signal)          # HOLD is always 'neutral correct'
                )
                last["outcome"] = f"{'✓' if correct else '✗'} {chg:+.2f}%"
                outcomes.append(f"{ticker}: {signal} → {chg:+.2f}% ({'hit' if correct else 'miss'})")

        _save_memory(mem)

        if not outcomes:
            return "No outcomes to review this cycle."

        summary_lines = "\n".join(outcomes[:20])

        if not self._available:
            return f"[Hermes offline] Daily review — {len(outcomes)} signal outcomes logged.\n{summary_lines}"

        prompt = f"""Daily signal outcome review:
{summary_lines}

In 2 sentences: (1) what pattern do you see in today's hits and misses? (2) what should the system watch for tomorrow?"""

        result = _ollama_chat(prompt, timeout=20) or f"Review logged: {len(outcomes)} outcomes."
        _log.info(f"Daily review: {result[:120]}")
        return result

    # ── self-improvement: asset suggestions ───────────────────────────────────

    def suggest_asset_changes(self, lb_data: list) -> str:
        """
        Scan leaderboard and memory for persistently failing tickers.
        Returns a suggestion string (never modifies assets.json automatically).

        A ticker is flagged if:
        - Last 5 memory entries exist and < 30% were correct outcomes
        - Sharpe from LB is negative

        Returns human-readable suggestions only.
        """
        mem = _load_memory()
        weak = []

        for entry in lb_data:
            ticker = entry.get("Asset", "")
            entries = mem.get(ticker, [])
            resolved = [e for e in entries if e.get("outcome", "pending") != "pending"]
            if len(resolved) < 5:
                continue
            last5 = resolved[-5:]
            hits  = sum(1 for e in last5 if "✓" in e.get("outcome", ""))
            acc   = hits / 5

            try:
                sharpe = float(entry.get("Sharpe", "0"))
            except (ValueError, TypeError):
                sharpe = 0.0

            if acc < 0.30 and sharpe < 0:
                weak.append(f"  • {ticker}: {acc*100:.0f}% accuracy (last 5), Sharpe={sharpe:.2f} — consider reviewing or removing.")

        if not weak:
            return "✅ All tracked assets are performing within expected bounds. No removal suggestions."

        report = "📋 Hermes Asset Review — Potential underperformers (suggestion only, never auto-removed):\n"
        report += "\n".join(weak)
        report += "\n\nTo remove a ticker, edit `assets.json` and restart the backend."
        _log.info(f"Asset suggestions:\n{report}")
        return report
