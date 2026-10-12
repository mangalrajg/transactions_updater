#!/usr/bin/env python3
"""Shared parsing helpers for the networth scripts.

Covers the finance-data repo layout (Portfolio Performance CSV exports):
- account_transactions/ : per-account transaction CSVs (CostBasis* shadow files skipped)
- securities/Master Data.csv : ISIN/ticker -> currency
- historic_quotes/ : ISIN-named daily quote CSVs (FTIHX lives in null.csv)
"""
import csv
import glob
import json
import os
import urllib.request
from collections import defaultdict
from datetime import date

KNOWN_TYPES = {
    "Buy", "Sell", "Deposit", "Removal", "Withdrawal", "Interest",
    "Interest Charge", "Dividend", "Fees", "Taxes",
    "Transfer (Inbound)", "Transfer (Outbound)",
}

# External money in/out of the tracked accounts.
CONTRIB_TYPES = {"Transfer (Inbound)", "Transfer (Outbound)", "Deposit",
                 "Removal", "Withdrawal"}
# Cash income paid by holdings.
INCOME_TYPES = {"Dividend", "Interest", "Interest Charge"}

# Legacy 401k funds with no public quotes: (key, anchor_date, anchor_price,
# yahoo_proxy_symbol). Valued by total-return scaling of the proxy.
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
                 os.path.join(here, "..", "..", "finance-data")):
        if cand and os.path.isdir(os.path.join(cand, "portfolio_performance")):
            return cand
    return "/tmp/finance-data"


def load_transactions(repo):
    """Return (txns, meta, key_ccy).

    txns: list of dicts sorted by date with keys date, acct, typ, value, ccy,
          key (isin or ticker), dshares (signed share delta, 0 if n/a).
    meta: key -> ticker symbol (or key itself).
    key_ccy: key -> currency.
    """
    acct_dir = os.path.join(repo, "portfolio_performance", "account_transactions")
    sec_dir = os.path.join(repo, "portfolio_performance", "securities")

    sec_ccy = {}
    mp = os.path.join(sec_dir, "Master Data.csv")
    if os.path.exists(mp):
        with open(mp, newline="") as f:
            for r in csv.DictReader(f):
                if r.get("ISIN"):
                    sec_ccy[r["ISIN"]] = r.get("Currency", "USD")
                if r.get("Ticker Symbol"):
                    sec_ccy[r["Ticker Symbol"]] = r.get("Currency", "USD")

    txns, meta, key_ccy = [], {}, {}
    for path in sorted(glob.glob(os.path.join(acct_dir, "*.csv"))):
        base = os.path.basename(path)
        if base.lower().startswith("costbasis"):  # PP shadow accounts, skip
            continue
        acct = base[:-4]
        with open(path, newline="") as f:
            for r in csv.DictReader(f):
                typ = (r.get("Type") or "").strip()
                if typ not in KNOWN_TYPES:
                    continue  # junk/comment rows (e.g. SG-Shares notes)
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
                    key_ccy[key] = (sec_ccy.get(isin) or sec_ccy.get(ticker)
                                    or ccy)
                txns.append({"date": d, "acct": acct, "typ": typ,
                             "value": val, "ccy": ccy,
                             "key": key, "dshares": dshares})
    txns.sort(key=lambda t: t["date"])
    return txns, meta, key_ccy


def load_quotes(repo):
    """filename-stem -> sorted [(date, price)] list."""
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


def price_on(series, d):
    """Last quote on or before d; falls back to earliest quote."""
    best = None
    for qd, q in series:
        if qd <= d:
            best = q
        else:
            break
    if best is None and series:
        best = series[0][1]
    return best or 0.0


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


def get_eurusd(cache_dir):
    """Daily EURUSD (FRED DEXUSEU), cached as JSON."""
    p = os.path.join(cache_dir, "eurusd.json")
    if os.path.exists(p):
        return json.load(open(p))
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXUSEU"
    series = {}
    with urllib.request.urlopen(url, timeout=30) as fh:
        for line in fh.read().decode().splitlines()[1:]:
            d, v = line.split(",")
            if v and v != ".":
                series[d] = float(v)
    os.makedirs(cache_dir, exist_ok=True)
    json.dump(series, open(p, "w"))
    return series


def fetch_yahoo_adj(symbol, start="2016-01-01", end="2026-09-01"):
    return fetch_yahoo_ohlc(symbol, start, end, field="adjclose")


def fetch_yahoo_daily(symbol, start="2016-01-01", end="2026-09-01"):
    """Raw daily closes (not dividend-adjusted) — for position valuation."""
    return fetch_yahoo_ohlc(symbol, start, end, field="close")


def fetch_yahoo_ohlc(symbol, start, end, field):
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
    vals = res["indicators"]["quote"][0]["close"] if field == "close" \
        else res["indicators"]["adjclose"][0]["adjclose"]
    out = {}
    for t, v in zip(ts, vals):
        if v:
            out[datetime.datetime.fromtimestamp(
                t, datetime.timezone.utc).date().isoformat()] = v
    return out


def get_missing_quotes(cache_dir, meta, quotes, proxy_series):
    """Yahoo daily closes (cached) for real tickers lacking quote files."""
    proxy_tickers = {p[0] for p in PROXY_FUNDS}
    out = {}
    for key, ticker in meta.items():
        if key in quotes or not ticker or ticker in proxy_tickers:
            continue
        if ticker == "FTIHX":  # covered by null.csv via series_for
            continue
        cp = os.path.join(cache_dir, f"yahoo_daily_{ticker}.json")
        if os.path.exists(cp):
            series = json.load(open(cp))
        else:
            try:
                series = fetch_yahoo_daily(ticker)
            except Exception:
                continue
            if not series:
                continue
            os.makedirs(cache_dir, exist_ok=True)
            json.dump(series, open(cp, "w"))
        out[key] = sorted(series.items())
    return out


def get_proxy_series(cache_dir):
    """Legacy-fund price series via total-return-scaled public equivalents."""
    out = {}
    for fund, anchor_d, anchor_p, sym in PROXY_FUNDS:
        cp = os.path.join(cache_dir, f"yahoo_{sym}.json")
        if os.path.exists(cp):
            adj = json.load(open(cp))
        else:
            adj = fetch_yahoo_adj(sym)
            os.makedirs(cache_dir, exist_ok=True)
            json.dump(adj, open(cp, "w"))
        if anchor_d not in adj:
            anchor_d = min(d for d in adj if d >= anchor_d)
        base = adj[anchor_d]
        out[fund] = sorted((d, anchor_p * a / base) for d, a in adj.items())
    return out


def series_for(key, meta, quotes, proxy_series):
    """Return (price_series, currency) for a holding key."""
    ticker = meta.get(key, key)
    if key in quotes:
        ccy = "EUR" if key.startswith("FR") else "USD"
        return quotes[key], ccy
    if ticker == "FTIHX" and "null" in quotes:
        return quotes["null"], "USD"
    if ticker in proxy_series:
        return proxy_series[ticker], "USD"
    return [], "USD"


def load_prices(path):
    """Flat {ticker: price} JSON; values may be {"price": x, "estimated": true}."""
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
