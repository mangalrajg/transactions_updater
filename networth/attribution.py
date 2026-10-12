#!/usr/bin/env python3
"""Yearly net-worth attribution from the finance-data repo.

Splits each year's change into:
  - Contributions : net external money in/out (transfers, deposits, withdrawals)
  - Dividends & interest : cash income paid by holdings
  - Market gains  : residual (price changes, FX moves, fees, withholding taxes)

Note on reinvested dividends: the dividend itself lands in "Dividends &
interest". The reinvestment buy is an internal cash->shares conversion, so it
never touches "Contributions"; growth on the reinvested shares lands in
"Market gains".

Usage:
    python3 attribution.py [repo_dir] [--cache DIR] [--end YYYY-MM-DD]
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (
    default_repo_dir, load_transactions, price_on, get_eurusd,
    CONTRIB_TYPES, INCOME_TYPES,
)
from history import compute_history


def main():
    argv = sys.argv[1:]
    cache_dir = os.path.expanduser("~/.cache/networth")
    end = "2026-08-31"
    repo = None
    i = 0
    while i < len(argv):
        if argv[i] == "--cache":
            cache_dir = argv[i + 1]; i += 2
        elif argv[i] == "--end":
            end = argv[i + 1]; i += 2
        elif not argv[i].startswith("-") and repo is None:
            repo = argv[i]; i += 1
        else:
            i += 1
    repo = repo or default_repo_dir()

    results, txns, eurusd = compute_history(repo, cache_dir, end)
    year_ends = {}
    for snap, total in results:
        if snap[5:7] == "12" or snap == results[-1][0]:
            year_ends[snap[:4]] = total

    fx_series = sorted(eurusd.items())
    per_year = defaultdict(lambda: [0.0, 0.0])  # year -> [contrib, income]
    for t in txns:
        y = t["date"][:4]
        if y < "2018":
            continue
        fx = price_on(fx_series, t["date"]) or 1.0
        usd = t["value"] * (fx if t["ccy"] == "EUR" else 1.0)
        if t["typ"] in CONTRIB_TYPES:
            per_year[y][0] += usd
        elif t["typ"] in INCOME_TYPES:
            per_year[y][1] += usd

    print("| Year | Start | End | Contributions | Dividends & interest | Market gains |")
    print("|---|---|---|---|---|---|")
    for y in sorted(per_year):
        start = year_ends.get(str(int(y) - 1), 0.0)
        end_v = year_ends.get(y, 0.0)
        c, i_ = per_year[y]
        m = (end_v - start) - c - i_
        flag = " *" if y == end[:4] and end[5:] != "12-31" else ""
        print(f"| {y}{flag} | ${start:,.0f} | ${end_v:,.0f} | "
              f"${c:+,.0f} | ${i_:+,.0f} | ${m:+,.0f} |")
    print()
    print("* partial year; market gains are the residual and include price")
    print("  changes, FX moves, fees and withholding taxes.")


if __name__ == "__main__":
    main()
