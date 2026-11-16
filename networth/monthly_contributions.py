#!/usr/bin/env python3
"""Monthly contributions report, 2018 onward, as a Markdown file.

The layout is a sources-and-uses statement. Money available to put to
work in a period:

    Put to work = New money + Dividends + Interest - Fees - Cash build-up

* New money: net external cash flows (transfers / deposits /
  withdrawals) into all tracked accounts.
* Dividends / Interest / Fees: across ALL accounts (interest at
  Marcus and TreasuryDirect counts too, not just investment income).
* Cash build-up: change in uninvested cash inside the investment
  accounts only (bank balances are a destination below, not "cash").

Where it went — four destinations that sum exactly to Put to work:

* Retirement: net purchases (buys - sells) in the 401(k) and IRA
  accounts. 401(k) -> IRA rollovers stay inside this bucket and so
  never show up as money leaving retirement.
* Treasury: US Treasury buying with I Bonds and bonds merged —
  balance growth of the two TreasuryDirect accounts (deposits +
  accrued interest - redemptions) plus Treasury bonds bought - sold
  at Fidelity (CUSIP prefix 912).
* CDs, savings: balance growth of the Marcus / Barclays / Capital One
  accounts (deposits + interest - withdrawals).
* Brokerage: net purchases in the taxable brokerage accounts
  (Fidelity, Chase, SG shares), excluding Treasury bonds.

Memo column:

* PP new investments: Portfolio Performance's net purchases across
  all investment accounts = Retirement + Brokerage + Treasury bonds
  bought at Fidelity. (I Bonds and savings are not security purchases
  in PP, so they are not in it.) It also equals the older bridge:
  new cash to investments + dividends & interest in those accounts
  - fees there - cash build-up.

All inputs are read fresh from the finance-data repo on every run.

Usage:
    python3 monthly_contributions.py [repo_dir] [--cache DIR] [--out FILE]
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import default_repo_dir, load_transactions, get_eurusd

INVEST = {
    "Mangal-ChaseInvestment", "Mangal-Empower", "Mangal-Fidelity",
    "Mangal-FidelityRoth", "Manju-Fidelity", "Manju-FidelityIRA",
    "Manju-FidelityRothIRA", "Manju-Milliman401K", "Manju-MillimanRoth401K",
    "Manju-MutualsOfOmaha", "Manju-Principal", "SG-Shares-Wise",
}
RETIREMENT = {
    "Mangal-Empower", "Manju-Milliman401K", "Manju-MillimanRoth401K",
    "Manju-MutualsOfOmaha", "Manju-Principal",
    "Mangal-FidelityRoth", "Manju-FidelityIRA", "Manju-FidelityRothIRA",
}
TREASURY_DIRECT = {"Mangal-Treasury", "Manju-Treasury"}
BANK = {
    "Mangal-Barclays", "Mangal-CapitalOne", "Mangal-Marcus-CD",
    "Mangal-Marcus-Savings", "Manju-Barclays", "Manju-CapitalOne",
    "Manju-Marcus-CD", "Manju-Marcus-Saving",
}
FLOW_TYPES = {"Transfer (Inbound)", "Transfer (Outbound)", "Deposit",
              "Removal", "Withdrawal"}
FIRST_MONTH = "2018-01"


def is_treasury(t):
    # US Treasury CUSIPs all start with 912; the key is ISIN else ticker.
    key = t.get("key") or ""
    return key.startswith("US912") or key.startswith("912")


def month_range(start, end):
    y, m = int(start[:4]), int(start[5:7])
    ey, em = int(end[:4]), int(end[5:7])
    out = []
    while (y, m) <= (ey, em):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def compute(repo, cache_dir):
    txns, meta, key_ccy = load_transactions(repo)
    eurusd = get_eurusd(cache_dir)
    fx_series = sorted(eurusd.items())

    def fx_on(d, ccy):
        if ccy != "EUR":
            return 1.0
        best = 1.0
        for fd, fv in fx_series:
            if fd <= d:
                best = fv
            else:
                break
        return best

    last_month = max(t["date"][:7] for t in txns)
    months = month_range(FIRST_MONTH, last_month)
    by_month = defaultdict(list)
    for t in txns:
        by_month[t["date"][:7]].append(t)

    def usd(t):
        return t["value"] * fx_on(t["date"], t["ccy"])

    # Seed: investment-account cash carried into FIRST_MONTH (cash is kept
    # in USD at transaction-date rates, so month differences are exact).
    cash_usd = 0.0
    for m, mtxns in by_month.items():
        if m < FIRST_MONTH:
            for t in mtxns:
                if t["acct"] in INVEST:
                    cash_usd += usd(t)

    rows = []
    prev_cash = cash_usd
    for m in months:
        nm = div = intr = fees = pp_inv = 0.0
        ret = treas = bank = brok = 0.0
        for t in by_month.get(m, []):
            v = usd(t)
            if t["typ"] in FLOW_TYPES:
                nm += v  # internal transfers cancel across accounts
            elif t["typ"] == "Dividend":
                div += v
            elif t["typ"] == "Interest":
                intr += v
            elif t["typ"] in ("Fees", "Taxes"):
                fees += -v
            if t["acct"] in INVEST:
                cash_usd += v
                if t["typ"] in ("Buy", "Sell"):
                    pp_inv += -v
                    if is_treasury(t):
                        treas += -v  # Treasury bond at a broker
                    elif t["acct"] in RETIREMENT:
                        ret += -v
                    else:
                        brok += -v
            if t["acct"] in TREASURY_DIRECT:
                treas += v  # I Bond balance growth (deposits + interest)
            elif t["acct"] in BANK:
                bank += v  # savings/CD balance growth
        dcash = cash_usd - prev_cash
        prev_cash = cash_usd
        rows.append({
            "month": m, "nm": nm, "div": div, "intr": intr, "fees": fees,
            "dcash": dcash, "pool": nm + div + intr - fees - dcash,
            "ret": ret, "treas": treas, "bank": bank, "brok": brok,
            "pp": pp_inv,
        })
    return rows, last_month


def fmt(v):
    return f"{v:,.0f}"


COLS = [("nm", "New money"), ("div", "Dividends"), ("intr", "Interest"),
        ("fees", "Fees"), ("dcash", "Cash build-up"),
        ("pool", "Put to work"), ("ret", "Retirement"),
        ("treas", "Treasury"), ("bank", "CDs, savings"),
        ("brok", "Brokerage"), ("pp", "PP new investments")]


def render(rows, last_month):
    lines = []
    lines.append("# Monthly contributions — sources and uses")
    lines.append("")
    lines.append("Where the money came from, and where it was put to work:")
    lines.append("")
    lines.append("`Put to work = New money + Dividends + Interest − Fees "
                 "− Cash build-up = Retirement + Treasury + CDs, savings "
                 "+ Brokerage`")
    lines.append("")
    lines.append("- **New money**: net external cash flows into all "
                 "tracked accounts.")
    lines.append("- **Dividends / Interest / Fees**: across all accounts, "
                 "including interest at Marcus and TreasuryDirect.")
    lines.append("- **Cash build-up**: change in uninvested cash inside "
                 "the investment accounts (negative = earlier cash was "
                 "drawn down and invested). Bank balances are not cash "
                 "here — they are the CDs, savings destination.")
    lines.append("- **Retirement**: net purchases in the 401(k) and IRA "
                 "accounts. 401(k) → IRA rollovers stay inside this "
                 "bucket, so they never appear as money leaving "
                 "retirement.")
    lines.append("- **Treasury**: I Bonds and Treasury bonds merged — "
                 "balance growth of the two TreasuryDirect accounts "
                 "(deposits + accrued interest − redemptions) plus "
                 "Treasury bonds bought − sold at Fidelity.")
    lines.append("- **CDs, savings**: balance growth of the Marcus, "
                 "Barclays and Capital One accounts (deposits + "
                 "interest − withdrawals).")
    lines.append("- **Brokerage**: net purchases in the taxable "
                 "brokerage accounts, excluding Treasury bonds.")
    lines.append("- **PP new investments**: Portfolio Performance's net "
                 "purchases across all investment accounts = Retirement "
                 "+ Brokerage + Treasury bonds bought at Fidelity. "
                 "Memo column; I Bonds and savings are not in it.")
    lines.append("- Figures rounded to dollars; a row may be off by 1. "
                 f"Data through {last_month}.")
    lines.append("")

    years = sorted({r["month"][:4] for r in rows})
    lines.append("## Year summary")
    lines.append("")
    lines.append("| Year | " + " | ".join(h for _, h in COLS) + " |")
    lines.append("|---|" + "---:|" * len(COLS))
    for y in years:
        ys = [r for r in rows if r["month"].startswith(y)]
        s = lambda k: sum(r[k] for r in ys)
        lines.append(f"| {y} | " + " | ".join(fmt(s(k)) for k, _ in COLS)
                     + " |")
    s = lambda k: sum(r[k] for r in rows)
    lines.append("| **All** | " + " | ".join(f"**{fmt(s(k))}**"
                                             for k, _ in COLS) + " |")
    lines.append("")

    for y in years:
        ys = [r for r in rows if r["month"].startswith(y)]
        t = lambda k: sum(r[k] for r in ys)
        lines.append(f"## {y}")
        lines.append("")
        lines.append("| Month | " + " | ".join(h for _, h in COLS) + " |")
        lines.append("|---|" + "---:|" * len(COLS))
        for r in ys:
            lines.append(f"| {r['month']} | "
                         + " | ".join(fmt(r[k]) for k, _ in COLS) + " |")
        lines.append("| **Total** | "
                     + " | ".join(f"**{fmt(t(k))}**" for k, _ in COLS)
                     + " |")
        lines.append("")
    return "\n".join(lines)


def main():
    argv = sys.argv[1:]
    cache_dir = os.path.expanduser("~/.cache/networth")
    out_path = None
    repo = None
    i = 0
    while i < len(argv):
        if argv[i] == "--cache":
            cache_dir = argv[i + 1]; i += 2
        elif argv[i] == "--out":
            out_path = argv[i + 1]; i += 2
        elif not argv[i].startswith("-") and repo is None:
            repo = argv[i]; i += 1
        else:
            i += 1
    repo = repo or default_repo_dir()
    rows, last_month = compute(repo, cache_dir)
    md = render(rows, last_month)
    if out_path:
        with open(out_path, "w") as f:
            f.write(md)
        print(f"wrote {out_path}", file=sys.stderr)
    else:
        print(md)


if __name__ == "__main__":
    main()
