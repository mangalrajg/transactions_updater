#!/usr/bin/env python3
"""Net worth calculator from finance-data repo (Portfolio Performance CSV exports).
Computes per-account cash balances and security positions from account_transactions/.
Usage: python3 networth.py [repo_dir] [--prices prices.json]
"""
import csv, os, sys, json, glob, re
from collections import defaultdict

KNOWN_TYPES = {
    "Buy", "Sell", "Deposit", "Removal", "Withdrawal", "Interest",
    "Interest Charge", "Dividend", "Fees", "Taxes",
    "Transfer (Inbound)", "Transfer (Outbound)",
}

def parse_num(s):
    if s is None: return 0.0
    s = s.strip().replace(",", "")
    if not s: return 0.0
    try: return float(s)
    except ValueError: return 0.0

def default_repo_dir():
    here = os.path.dirname(os.path.abspath(__file__))
    for cand in (os.environ.get("FINANCE_DATA_DIR"),
                 os.path.join(here, "..", "finance-data")):
        if cand and os.path.isdir(os.path.join(cand, "portfolio_performance")):
            return cand
    return "/tmp/finance-data"

def main():
    repo = sys.argv[1] if len(sys.argv) > 1 else default_repo_dir()
    acct_dir = os.path.join(repo, "portfolio_performance", "account_transactions")
    sec_dir = os.path.join(repo, "portfolio_performance", "securities")

    # security currency lookup from Master Data
    sec_ccy = {}
    mp = os.path.join(sec_dir, "Master Data.csv")
    if os.path.exists(mp):
        with open(mp, newline="") as f:
            for r in csv.DictReader(f):
                if r.get("ISIN"): sec_ccy[r["ISIN"]] = r.get("Currency", "USD")
                if r.get("Ticker Symbol"): sec_ccy[r["Ticker Symbol"]] = r.get("Currency", "USD")

    accounts = {}
    for path in sorted(glob.glob(os.path.join(acct_dir, "*.csv"))):
        base = os.path.basename(path)
        if base.lower().startswith("costbasis"):  # PP auxiliary cost-basis accounts, skip
            continue
        acct = base[:-4]
        cash = defaultdict(float)   # currency -> balance
        positions = defaultdict(float)  # isin -> shares
        meta = {}                   # isin -> (ticker, name)
        n_rows = 0
        last_date = ""
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            for r in reader:
                typ = (r.get("Type") or "").strip()
                date = (r.get("Date") or "")[:10]
                if typ not in KNOWN_TYPES:
                    continue  # junk/comment rows (e.g. SG-Shares notes)
                val = parse_num(r.get("Value"))
                ccy = (r.get("Transaction Currency") or "USD").strip() or "USD"
                shares = parse_num(r.get("Shares"))
                isin = (r.get("ISIN") or "").strip()
                ticker = (r.get("Ticker Symbol") or "").strip()
                name = (r.get("Security Name") or "").strip()
                cash[ccy] += val
                if typ in ("Buy", "Sell", "Transfer (Inbound)", "Transfer (Outbound)") and (isin or ticker) and shares:
                    key = isin or ticker
                    if typ in ("Sell", "Transfer (Outbound)"):
                        shares = -shares  # sells/outbound reduce the position
                    positions[key] += shares
                    if key not in meta:
                        meta[key] = (ticker, name, sec_ccy.get(isin) or sec_ccy.get(ticker) or ccy)
                n_rows += 1
                if date > last_date: last_date = date
        # drop dust positions
        positions = {k: v for k, v in positions.items() if abs(v) > 1e-9}
        accounts[acct] = {"cash": dict(cash), "positions": positions,
                          "meta": meta, "rows": n_rows, "last_date": last_date}

    out = {"accounts": accounts}
    print(json.dumps(out))
    tickers = set()
    for a, d in accounts.items():
        for k, (t, n, c) in d["meta"].items():
            tickers.add((t, c))
    print("TICKERS:" + json.dumps(sorted((t, c) for t, c in tickers if t)), file=sys.stderr)

if __name__ == "__main__":
    main()
