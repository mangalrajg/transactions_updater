#!/usr/bin/env python3
"""Current net worth snapshot from the finance-data repo.

Replays every transaction, then values cash balances and security positions.

Usage:
    python3 snapshot.py [repo_dir]                    # JSON of accounts -> stdout
    python3 snapshot.py [repo_dir] --prices prices.json  # account + ticker tables
"""
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import default_repo_dir, load_transactions, load_prices


def main():
    argv = sys.argv[1:]
    prices_path = None
    if "--prices" in argv:
        i = argv.index("--prices")
        prices_path = argv[i + 1]
        del argv[i:i + 2]
    repo = argv[0] if argv and not argv[0].startswith("-") else default_repo_dir()

    txns, meta, key_ccy = load_transactions(repo)

    cash = defaultdict(float)   # (acct, ccy) -> balance
    pos = defaultdict(float)    # (acct, key) -> shares
    last_date = {}
    for t in txns:
        cash[(t["acct"], t["ccy"])] += t["value"]
        if t["key"] and t["dshares"]:
            pos[(t["acct"], t["key"])] += t["dshares"]
        last_date[t["acct"]] = t["date"]

    accounts = {}
    for (acct, ccy), bal in cash.items():
        accounts.setdefault(acct, {"cash": {}, "positions": {}})
        accounts[acct]["cash"][ccy] = bal
    for (acct, key), sh in pos.items():
        if abs(sh) < 1e-9:
            continue
        accounts.setdefault(acct, {"cash": {}, "positions": {}})
        accounts[acct]["positions"][key] = sh
        accounts[acct].setdefault("meta", {})[key] = meta.get(key, key)
    for acct in accounts:
        accounts[acct]["last_date"] = last_date.get(acct, "")

    if not prices_path:
        print(json.dumps({"accounts": accounts}))
        tickers = sorted({meta[k] for a in accounts
                          for k in accounts[a].get("meta", {}) if meta.get(k)})
        print("TICKERS:" + json.dumps(tickers), file=sys.stderr)
        return

    prices, estimated = load_prices(prices_path)
    eurusd = prices.get("EURUSD", 1.0)

    acct_rows, tick_tot, tick_accts = [], defaultdict(float), defaultdict(set)
    for acct in sorted(accounts):
        a = accounts[acct]
        cash_usd = a["cash"].get("USD", 0.0) + a["cash"].get("EUR", 0.0) * eurusd
        sec = 0.0
        for key, sh in a["positions"].items():
            t = a["meta"][key]
            if t in prices:
                sec += sh * prices[t]
                tick_tot[t] += sh
                tick_accts[t].add(acct)
        acct_rows.append((acct, cash_usd, sec, cash_usd + sec))

    print("| Account | Cash | Securities | Total |")
    print("|---|---|---|---|")
    for acct, c, s, t in acct_rows:
        print(f"| {acct} | ${c:,.0f} | ${s:,.0f} | ${t:,.0f} |")
    print(f"| **Total** | | | **${sum(r[3] for r in acct_rows):,.0f}** |")
    print()
    print("| Ticker | Shares | Price | Value | Held in |")
    print("|---|---|---|---|---|")
    for t, sh in sorted(tick_tot.items(), key=lambda x: -x[1] * prices[x[0]]):
        flag = "*" if t in estimated else ""
        print(f"| {t}{flag} | {sh:,.2f} | ${prices[t]:,.2f} | "
              f"${sh * prices[t]:,.0f} | {', '.join(sorted(tick_accts[t]))} |")
    missing = sorted({a["meta"][k] for a in accounts for k in a["positions"]}
                     - set(prices))
    for t in missing:
        print(f"| {t} | n/a | n/a | n/a | price missing |")
    if estimated:
        print()
        print("* estimated price")


if __name__ == "__main__":
    main()
