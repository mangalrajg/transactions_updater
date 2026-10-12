#!/usr/bin/env python3
"""Net worth calculator from finance-data repo (Portfolio Performance CSV exports).

Computes per-account cash balances and security positions from account_transactions/.

Usage:
    python3 networth.py [repo_dir]                     # JSON of accounts -> stdout, ticker list -> stderr
    python3 networth.py [repo_dir] --prices prices.json  # markdown tables (accounts + tickers) -> stdout

prices.json is a flat object: {"QQQM": 309.39, ..., "EURUSD": 1.1217}.
A price may also be {"price": 90.42, "estimated": true} to flag modeled quotes.
repo_dir defaults to $FINANCE_DATA_DIR, ../finance-data, or /tmp/finance-data.
"""
import csv, os, sys, json, glob
from collections import defaultdict

KNOWN_TYPES = {
    "Buy", "Sell", "Deposit", "Removal", "Withdrawal", "Interest",
    "Interest Charge", "Dividend", "Fees", "Taxes",
    "Transfer (Inbound)", "Transfer (Outbound)",
}
SHARE_TYPES = ("Buy", "Sell", "Transfer (Inbound)", "Transfer (Outbound)")


def parse_num(s):
    if s is None:
        return 0.0
    s = s.strip().replace(",", "")
    if not s:
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def default_repo_dir():
    here = os.path.dirname(os.path.abspath(__file__))
    for cand in (os.environ.get("FINANCE_DATA_DIR"),
                 os.path.join(here, "..", "finance-data")):
        if cand and os.path.isdir(os.path.join(cand, "portfolio_performance")):
            return cand
    return "/tmp/finance-data"


def load_accounts(repo):
    acct_dir = os.path.join(repo, "portfolio_performance", "account_transactions")
    sec_dir = os.path.join(repo, "portfolio_performance", "securities")

    # security currency lookup from Master Data
    sec_ccy = {}
    mp = os.path.join(sec_dir, "Master Data.csv")
    if os.path.exists(mp):
        with open(mp, newline="") as f:
            for r in csv.DictReader(f):
                if r.get("ISIN"):
                    sec_ccy[r["ISIN"]] = r.get("Currency", "USD")
                if r.get("Ticker Symbol"):
                    sec_ccy[r["Ticker Symbol"]] = r.get("Currency", "USD")

    accounts = {}
    for path in sorted(glob.glob(os.path.join(acct_dir, "*.csv"))):
        base = os.path.basename(path)
        if base.lower().startswith("costbasis"):  # PP auxiliary cost-basis accounts, skip
            continue
        acct = base[:-4]
        cash = defaultdict(float)      # currency -> balance
        positions = defaultdict(float)  # isin -> shares
        meta = {}                       # isin -> (ticker, name, currency)
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
                if typ in SHARE_TYPES and (isin or ticker) and shares:
                    key = isin or ticker
                    if typ in ("Sell", "Transfer (Outbound)"):
                        shares = -shares  # sells/outbound reduce the position
                    positions[key] += shares
                    if key not in meta:
                        meta[key] = (ticker, name,
                                     sec_ccy.get(isin) or sec_ccy.get(ticker) or ccy)
                n_rows += 1
                if date > last_date:
                    last_date = date
        # drop dust positions
        positions = {k: v for k, v in positions.items() if abs(v) > 1e-9}
        accounts[acct] = {"cash": dict(cash), "positions": positions,
                          "meta": meta, "rows": n_rows, "last_date": last_date}
    return accounts


def load_prices(path):
    raw = json.load(open(path))
    prices, estimated = {}, set()
    for t, v in raw.items():
        if isinstance(v, dict):
            prices[t] = float(v["price"])
            if v.get("estimated"):
                estimated.add(t)
        else:
            prices[t] = float(v)
    return prices, estimated


def print_tables(accounts, prices, estimated):
    eurusd = prices.get("EURUSD", 1.0)
    if "EURUSD" not in prices and any("EUR" in v["cash"] for v in accounts.values()):
        print("warning: no EURUSD in prices file, EUR cash converted at 1.0",
              file=sys.stderr)

    acct_rows = []
    tick_tot = defaultdict(float)   # ticker -> shares
    tick_accts = defaultdict(set)   # ticker -> set of accounts
    for a in sorted(accounts):
        v = accounts[a]
        cash = v["cash"].get("USD", 0.0) + v["cash"].get("EUR", 0.0) * eurusd
        sec = 0.0
        for k, sh in v["positions"].items():
            t = v["meta"][k][0] or k
            if t in prices:
                sec += sh * prices[t]
                tick_tot[t] += sh
                tick_accts[t].add(a)
        acct_rows.append((a, cash, sec, cash + sec))

    total = sum(r[3] for r in acct_rows)
    print("| Account | Cash | Securities | Total |")
    print("|---|---|---|---|")
    for a, c, s, t in acct_rows:
        print(f"| {a} | ${c:,.0f} | ${s:,.0f} | ${t:,.0f} |")
    print(f"| **Total** | | | **${total:,.0f}** |")

    print()
    print("| Ticker | Shares | Price | Value | Held in |")
    print("|---|---|---|---|---|")
    for t, sh in sorted(tick_tot.items(), key=lambda x: -x[1] * prices[x[0]]):
        p = prices[t]
        flag = "*" if t in estimated else ""
        who = ", ".join(sorted(tick_accts[t]))
        print(f"| {t}{flag} | {sh:,.2f} | ${p:,.2f} | ${sh * p:,.0f} | {who} |")
    # tickers held but missing a price
    missing = sorted({(v["meta"][k][0] or k)
                      for a, v in accounts.items() for k in v["positions"]}
                     - set(prices))
    for t in missing:
        print(f"| {t} | n/a | n/a | n/a | price missing |")
    if estimated:
        print()
        print("* estimated price")


def main():
    argv = sys.argv[1:]
    prices_path = None
    if "--prices" in argv:
        i = argv.index("--prices")
        prices_path = argv[i + 1]
        del argv[i:i + 2]
    repo = argv[0] if argv and not argv[0].startswith("-") else default_repo_dir()

    accounts = load_accounts(repo)

    if prices_path:
        prices, estimated = load_prices(prices_path)
        print_tables(accounts, prices, estimated)
        return

    print(json.dumps({"accounts": accounts}))
    tickers = set()
    for a, d in accounts.items():
        for k, (t, n, c) in d["meta"].items():
            if t:
                tickers.add((t, c))
    print("TICKERS:" + json.dumps(sorted(tickers)), file=sys.stderr)


if __name__ == "__main__":
    main()
