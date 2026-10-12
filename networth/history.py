#!/usr/bin/env python3
"""Net worth history from the finance-data repo.

Replays every transaction and values the portfolio at each month-end using
portfolio_performance/historic_quotes/ (plus cached EURUSD / proxy series).

Usage:
    python3 history.py [repo_dir] [--cache DIR] [--end YYYY-MM-DD] [--chart out.png]

Prints a markdown table of month-end totals to stdout.
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (
    default_repo_dir, load_transactions, load_quotes, price_on, month_ends,
    get_eurusd, get_proxy_series, series_for,
)


def compute_history(repo, cache_dir, end="2026-08-31"):
    """Return (results, txns, eurusd); results = [(month_end, total_usd)]."""
    os.makedirs(cache_dir, exist_ok=True)
    txns, meta, key_ccy = load_transactions(repo)
    quotes = load_quotes(repo)
    eurusd = get_eurusd(cache_dir)
    proxy_series = get_proxy_series(cache_dir)
    series_cache = {k: series_for(k, meta, quotes, proxy_series) for k in meta}
    fx_series = sorted(eurusd.items())

    snaps = month_ends(txns[0]["date"][:7] + "-01", end)
    cash = defaultdict(float)
    pos = defaultdict(float)
    results = []
    ti = 0
    for snap in snaps:
        while ti < len(txns) and txns[ti]["date"] <= snap:
            t = txns[ti]
            cash[(t["acct"], t["ccy"])] += t["value"]
            if t["key"] and t["dshares"]:
                pos[(t["acct"], t["key"])] += t["dshares"]
            ti += 1
        fx = price_on(fx_series, snap) or 1.0
        total = sum(bal * (fx if ccy == "EUR" else 1.0)
                    for (acct, ccy), bal in cash.items())
        for (acct, key), sh in pos.items():
            if abs(sh) < 1e-9:
                continue
            series, ccy = series_cache[key]
            total += sh * price_on(series, snap) * (fx if ccy == "EUR" else 1.0)
        results.append((snap, total))
    return results, txns, eurusd


def main():
    argv = sys.argv[1:]
    cache_dir = os.path.expanduser("~/.cache/networth")
    end = "2026-08-31"
    chart_path = None
    repo = None
    i = 0
    while i < len(argv):
        if argv[i] == "--cache":
            cache_dir = argv[i + 1]; i += 2
        elif argv[i] == "--end":
            end = argv[i + 1]; i += 2
        elif argv[i] == "--chart":
            chart_path = argv[i + 1]; i += 2
        elif not argv[i].startswith("-") and repo is None:
            repo = argv[i]; i += 1
        else:
            i += 1
    repo = repo or default_repo_dir()

    results, _, _ = compute_history(repo, cache_dir, end)
    print("| Month | Net worth |")
    print("|---|---|")
    for snap, total in results:
        print(f"| {snap[:7]} | ${total:,.0f} |")

    if chart_path:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.ticker as mticker
        xs = [r[0][:7] for r in results]
        ys = [r[1] for r in results]
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(xs, ys, linewidth=1.8)
        ax.set_title("Net worth over time (investable assets)")
        ax.set_ylabel("USD")
        ax.yaxis.set_major_formatter(
            mticker.FuncFormatter(lambda v, _: f"${v / 1e6:.1f}M"))
        ax.set_xticks(xs[::12])
        plt.xticks(rotation=45)
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(chart_path, dpi=110)
        print(f"\nchart: {chart_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
