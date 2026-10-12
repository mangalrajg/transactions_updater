#!/usr/bin/env python3
"""Net worth history from finance-data repo (Portfolio Performance CSV exports).

Replays every transaction in account_transactions/ and values the portfolio at
each month-end using portfolio_performance/historic_quotes/.

Special cases:
- FTIHX has no ISIN in the exports; its quotes live in historic_quotes/null.csv.
- TR45HT / BNYLCG / BNYSII are legacy 401k funds with no public quotes; they are
  proxied by total-return scaling of a public equivalent, anchored at their last
  observed trade price (method documented in PROXY_FUNDS below). Yahoo adjusted
  closes are fetched once and cached.
- EUR cash and GLE.PA (EUR) are converted with daily EURUSD from FRED (cached).

Usage:
    python3 networth_history.py [repo_dir] [--cache DIR] [--end YYYY-MM-DD] [--chart out.png]
    python3 networth_history.py [repo_dir] --attribution   # yearly split: contributions / income / market

Prints a markdown table of month-end totals to stdout.
"""
import csv, os, sys, json, glob, urllib.request
from collections import defaultdict
from datetime import date

KNOWN_TYPES = {
    "Buy", "Sell", "Deposit", "Removal", "Withdrawal", "Interest",
    "Interest Charge", "Dividend", "Fees", "Taxes",
    "Transfer (Inbound)", "Transfer (Outbound)",
}

# (fund_key, anchor_date, anchor_price, proxy_yahoo_symbol)
PROXY_FUNDS = [
    ("TR45HT", "2018-10-18", 20.27, "TRRKX"),   # T. Rowe Price Retirement 2045 Trust-B
    ("BNYLCG", "2021-08-20", 429.30, "FSPGX"),  # BNY Mellon NSL Large Cap Growth
    ("BNYSII", "2020-07-17", 370.28, "FXAIX"),  # BNY Mellon NSL Stock Institutional
]


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


def load_transactions(repo):
    """Return (txns, meta): txns = list of dicts sorted by date."""
    acct_dir = os.path.join(repo, "portfolio_performance", "account_transactions")
    txns = []
    meta = {}
    for path in sorted(glob.glob(os.path.join(acct_dir, "*.csv"))):
        base = os.path.basename(path)
        if base.lower().startswith("costbasis"):
            continue
        acct = base[:-4]
        with open(path, newline="") as f:
            for r in csv.DictReader(f):
                typ = (r.get("Type") or "").strip()
                if typ not in KNOWN_TYPES:
                    continue
                d = (r.get("Date") or "")[:10]
                if not d:
                    continue
                val = parse_num(r.get("Value"))
                ccy = (r.get("Transaction Currency") or "USD").strip() or "USD"
                shares = parse_num(r.get("Shares"))
                isin = (r.get("ISIN") or "").strip()
                ticker = (r.get("Ticker Symbol") or "").strip()
                key = isin or ticker
                dshares = 0.0
                if key and shares:
                    if typ in ("Buy", "Transfer (Inbound)"):
                        dshares = shares
                    elif typ in ("Sell", "Transfer (Outbound)"):
                        dshares = -shares
                if key and key not in meta:
                    meta[key] = ticker or key
                txns.append({"date": d, "acct": acct, "typ": typ, "value": val, "ccy": ccy,
                             "key": key, "dshares": dshares})
    txns.sort(key=lambda t: t["date"])
    return txns, meta


def load_quotes(repo):
    """ISIN/filename -> sorted [(date, price)]. FTIHX lives in null.csv."""
    qdir = os.path.join(repo, "portfolio_performance", "historic_quotes")
    quotes = {}
    for path in glob.glob(os.path.join(qdir, "*.csv")):
        name = os.path.basename(path)[:-4]
        series = []
        with open(path, newline="") as f:
            for r in csv.DictReader(f):
                d = (r.get("Date") or "").strip()
                q = parse_num(r.get("Quote"))
                if d and q:
                    series.append((d, q))
        series.sort()
        quotes[name] = series
    return quotes


def fetch_yahoo_adj(symbol, start="2016-01-01", end="2026-09-01"):
    import datetime
    p1 = int(datetime.datetime.fromisoformat(start).replace(
        tzinfo=datetime.timezone.utc).timestamp())
    p2 = int(datetime.datetime.fromisoformat(end).replace(
        tzinfo=datetime.timezone.utc).timestamp())
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
           f"?period1={p1}&period2={p2}&interval=1d&events=div")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    res = json.load(urllib.request.urlopen(req, timeout=30))["chart"]["result"][0]
    ts = res["timestamp"]
    adj = res["indicators"]["adjclose"][0]["adjclose"]
    out = {}
    for t, a in zip(ts, adj):
        if a:
            out[datetime.datetime.fromtimestamp(t, datetime.timezone.utc).date().isoformat()] = a
    return out


def fetch_eurusd(cache_dir):
    p = os.path.join(cache_dir, "eurusd.json")
    if os.path.exists(p):
        return json.load(open(p))
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXUSEU"
    series = {}
    with urllib.request.urlopen(url, timeout=30) as fh:
        lines = fh.read().decode().splitlines()
    for line in lines[1:]:
        d, v = line.split(",")
        if v and v != ".":
            series[d] = float(v)
    os.makedirs(cache_dir, exist_ok=True)
    json.dump(series, open(p, "w"))
    return series


def month_ends(start_d, end_d):
    y, m = int(start_d[:4]), int(start_d[5:7])
    out = []
    while True:
        nm = m + 1
        ny = y + (1 if nm > 12 else 0)
        nm = nm - 12 if nm > 12 else nm
        last = (date(ny, nm, 1) - date(y, m, 1)).days
        d = f"{y:04d}-{m:02d}-{last:02d}"
        if d > end_d:
            break
        out.append(d)
        y, m = ny, nm
    return out


def price_on(series, d):
    """Last quote on or before d; backfill with earliest if none."""
    lo, best = 0, None
    # series sorted by date
    for qd, q in series:
        if qd <= d:
            best = q
        else:
            break
    if best is None and series:
        best = series[0][1]
    return best or 0.0


def print_attribution(txns, eurusd, year_ends):
    """Split each year's net-worth change into contributions, income, market."""
    CONTRIB = {"Transfer (Inbound)", "Transfer (Outbound)", "Deposit",
               "Removal", "Withdrawal"}
    INCOME = {"Dividend", "Interest", "Interest Charge"}
    fx_series = sorted(eurusd.items())
    per_year = defaultdict(lambda: [0.0, 0.0])  # year -> [contrib, income]
    for t in txns:
        y = t["date"][:4]
        if y < "2018":
            continue
        fx = price_on(fx_series, t["date"]) or 1.0
        usd = t["value"] * (fx if t["ccy"] == "EUR" else 1.0)
        if t["typ"] in CONTRIB:
            per_year[y][0] += usd
        elif t["typ"] in INCOME:
            per_year[y][1] += usd
    print("| Year | Start | End | Contributions | Dividends & interest | Market gains |")
    print("|---|---|---|---|---|---|")
    for y in sorted(per_year):
        start = year_ends.get(str(int(y) - 1), 0.0)
        end = year_ends.get(y, 0.0)
        c, i = per_year[y]
        m = (end - start) - c - i
        flag = " *" if y == "2026" else ""
        print(f"| {y}{flag} | ${start:,.0f} | ${end:,.0f} | "
              f"${c:+,.0f} | ${i:+,.0f} | ${m:+,.0f} |")
    print()
    print("* 2026 through Aug 31; market gains are the residual and include price")
    print("  changes, FX moves, fees and withholding taxes.")


def main():
    argv = sys.argv[1:]
    cache_dir = os.path.expanduser("~/.cache/networth_history")
    end = "2026-08-31"
    chart_path = None
    attribution = False
    repo = None
    i = 0
    while i < len(argv):
        if argv[i] == "--cache":
            cache_dir = argv[i + 1]; i += 2
        elif argv[i] == "--end":
            end = argv[i + 1]; i += 2
        elif argv[i] == "--chart":
            chart_path = argv[i + 1]; i += 2
        elif argv[i] == "--attribution":
            attribution = True; i += 1
        elif not argv[i].startswith("-") and repo is None:
            repo = argv[i]; i += 1
        else:
            i += 1
    repo = repo or default_repo_dir()
    os.makedirs(cache_dir, exist_ok=True)

    txns, meta = load_transactions(repo)
    quotes = load_quotes(repo)
    eurusd = fetch_eurusd(cache_dir)

    # proxy series for legacy funds: total-return scaled public equivalent
    proxy_series = {}
    for fund, anchor_d, anchor_p, sym in PROXY_FUNDS:
        cp = os.path.join(cache_dir, f"yahoo_{sym}.json")
        if os.path.exists(cp):
            adj = json.load(open(cp))
        else:
            adj = fetch_yahoo_adj(sym)
            json.dump(adj, open(cp, "w"))
        if anchor_d not in adj:
            anchor_d = min(d for d in adj if d >= anchor_d)
        base = adj[anchor_d]
        proxy_series[fund] = sorted(
            (d, anchor_p * a / base) for d, a in adj.items())

    # resolve quote series per holding key
    def series_for(key):
        ticker = meta.get(key, key)
        if key in quotes:
            return quotes[key], "USD" if not key.startswith("FR") else "EUR"
        if ticker == "FTIHX" and "null" in quotes:
            return quotes["null"], "USD"
        if ticker in proxy_series:
            return proxy_series[ticker], "USD"
        return [], "USD"

    series_cache = {k: series_for(k) for k in meta}

    snaps = month_ends(txns[0]["date"][:7] + "-01", end)
    cash = defaultdict(float)   # (acct, ccy) -> balance
    pos = defaultdict(float)    # (acct, key) -> shares
    results = []
    ti = 0
    for snap in snaps:
        while ti < len(txns) and txns[ti]["date"] <= snap:
            t = txns[ti]
            cash[(t["acct"], t["ccy"])] += t["value"]
            if t["key"] and t["dshares"]:
                pos[(t["acct"], t["key"])] += t["dshares"]
            ti += 1
        fx = price_on(sorted(eurusd.items()), snap) or 1.0
        total = 0.0
        for (acct, ccy), bal in cash.items():
            total += bal * (fx if ccy == "EUR" else 1.0)
        for (acct, key), sh in pos.items():
            if abs(sh) < 1e-9:
                continue
            series, ccy = series_cache[key]
            p = price_on(series, snap)
            total += sh * p * (fx if ccy == "EUR" else 1.0)
        results.append((snap, total))

    print("| Month | Net worth |")
    print("|---|---|")
    for snap, total in results:
        print(f"| {snap[:7]} | ${total:,.0f} |")

    if attribution:
        print()
        year_ends = {}
        for snap, total in results:
            if snap[5:7] == "12" or snap == results[-1][0]:
                year_ends[snap[:4]] = total
        print_attribution(txns, eurusd, year_ends)
        return

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
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"${v/1e6:.1f}M"))
        ax.set_xticks(xs[::12])
        plt.xticks(rotation=45)
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(chart_path, dpi=110)
        print(f"\nchart: {chart_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
