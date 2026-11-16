#!/usr/bin/env python3
"""Monthly contributions report, 2018 onward, as a Markdown file.

Two views of the same money, reconciled column by column:

* New-money view: net external cash flows (transfers / deposits /
  withdrawals), split into investment accounts vs. other accounts
  (savings, CDs, Treasury). The total is the year's true contributions.
  New cash to investments is split further into 401(k) accounts vs.
  other investment accounts; transfers between the two groups (401(k)
  -> IRA rollovers) are the same money changing buckets, not new
  money, so matched rollover legs are excluded from both groups.
* Portfolio Performance view: for investment accounts PP counts net
  purchases (buys - sells). The bridge is exact, month by month:

      PP new investments = new cash to investments
                         + dividends (& interest) received in those accounts
                         - fees & taxes in those accounts
                         - cash build-up (money that arrived in the
                           investment accounts but was still uninvested
                           cash at month-end; negative = cash drawn down)

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
K401 = {
    "Mangal-Empower", "Manju-Milliman401K", "Manju-MillimanRoth401K",
    "Manju-MutualsOfOmaha", "Manju-Principal",
}
FLOW_TYPES = {"Transfer (Inbound)", "Transfer (Outbound)", "Deposit",
              "Removal", "Withdrawal"}
FIRST_MONTH = "2018-01"


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

    # Match cross-group internal transfers (401(k) <-> other investment):
    # opposite signs, equal |amount| within $1, dates within 45 days.
    # Both legs are excluded from the 401(k)/non-401(k) split (they net
    # to zero in the total either way).
    from datetime import date as _date

    def _ord(ds):
        return _date(int(ds[:4]), int(ds[5:7]), int(ds[8:10])).toordinal()

    flows = [t for t in txns if t["acct"] in INVEST
             and t["typ"] in FLOW_TYPES and t["date"][:7] >= FIRST_MONTH]
    cands = []
    for i, a in enumerate(flows):
        if a["acct"] not in K401:
            continue
        for j, b in enumerate(flows):
            if b["acct"] in K401 or usd(a) * usd(b) >= 0:
                continue
            if (abs(abs(usd(a)) - abs(usd(b))) <= 1.0
                    and abs(_ord(a["date"]) - _ord(b["date"])) <= 45):
                cands.append((abs(usd(a)), i, j))
    cands.sort(reverse=True)
    used, rollovers = set(), []
    for _amt, i, j in cands:
        if i in used or j in used:
            continue
        used.add(i); used.add(j)
        rollovers.append((flows[i], flows[j]))
    rollover_ids = {id(t) for pair in rollovers for t in pair}

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
        new_cash = other_dep = div_int = fees = pp_inv = 0.0
        new_401k = new_non = 0.0
        for t in by_month.get(m, []):
            v = usd(t)
            if t["acct"] in INVEST:
                cash_usd += v
                if t["typ"] in FLOW_TYPES:
                    new_cash += v
                    if id(t) not in rollover_ids:
                        if t["acct"] in K401:
                            new_401k += v
                        else:
                            new_non += v
                elif t["typ"] in ("Dividend", "Interest"):
                    div_int += v
                elif t["typ"] in ("Fees", "Taxes"):
                    fees += -v
                elif t["typ"] in ("Buy", "Sell"):
                    pp_inv += -v
            elif t["typ"] in FLOW_TYPES:
                other_dep += v
        rows.append({
            "month": m, "other": other_dep, "new_cash": new_cash,
            "new_401k": new_401k, "new_non": new_non,
            "div_int": div_int, "fees": fees, "pp": pp_inv,
            "dcash": cash_usd - prev_cash,
        })
        prev_cash = cash_usd
    rollover_info = [(a["date"], a["acct"], usd(a), b["date"], b["acct"],
                      usd(b)) for a, b in rollovers]
    return rows, last_month, rollover_info


def fmt(v):
    return f"{v:,.0f}"


def render(rows, last_month, rollovers=()):
    lines = []
    lines.append("# Monthly contributions — new money vs Portfolio Performance")
    lines.append("")
    lines.append("Net external cash flows into the tracked accounts, split by "
                 "destination, with the bridge to Portfolio Performance's "
                 "net-purchases figure for investment accounts:")
    lines.append("")
    lines.append("`PP new investments = New cash to investments + Dividends "
                 "& interest − Fees − Cash build-up`")
    lines.append("")
    lines.append("- **Other deposits**: net deposits/withdrawals in savings, "
                 "CD, Capital One, Barclays and Treasury accounts.")
    lines.append("- **New cash to investments**: net transfers/deposits into "
                 "brokerage and retirement accounts.")
    lines.append("- **... to 401(k)**: the part landing in 401(k) accounts "
                 "(Empower, Milliman, Mutual of Omaha, Principal).")
    lines.append("- **... to other investments**: the part landing in "
                 "brokerages, IRAs and the SG share plan. 401(k) -> IRA "
                 "rollovers are excluded from both columns: they move "
                 "existing money between buckets, they are not new money.")
    lines.append("- **Total new money**: the month's true contributions.")
    lines.append("- **Cash build-up**: money that arrived in the investment "
                 "accounts but was still uninvested cash at month-end "
                 "(negative = earlier cash was drawn down and invested).")
    lines.append("- Figures rounded to dollars; a row may be off by 1. "
                 f"Data through {last_month}.")
    lines.append("")

    years = sorted({r["month"][:4] for r in rows})
    lines.append("## Year summary")
    lines.append("")
    lines.append("| Year | Other deposits | New cash to 401(k) | New cash "
                 "to other investments | New cash to investments | Total "
                 "new money | Dividends & interest | Fees | Cash build-up | "
                 "PP new investments |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for y in years:
        ys = [r for r in rows if r["month"].startswith(y)]
        s = lambda k: sum(r[k] for r in ys)
        lines.append(f"| {y} | {fmt(s('other'))} | {fmt(s('new_401k'))} | "
                     f"{fmt(s('new_non'))} | {fmt(s('new_cash'))} | "
                     f"{fmt(s('other') + s('new_cash'))} | {fmt(s('div_int'))} "
                     f"| {fmt(s('fees'))} | {fmt(s('dcash'))} | {fmt(s('pp'))} |")
    s = lambda k: sum(r[k] for r in rows)
    lines.append(f"| **All** | **{fmt(s('other'))}** | **{fmt(s('new_401k'))}** "
                 f"| **{fmt(s('new_non'))}** | **{fmt(s('new_cash'))}** "
                 f"| **{fmt(s('other') + s('new_cash'))}** | "
                 f"**{fmt(s('div_int'))}** | **{fmt(s('fees'))}** | "
                 f"**{fmt(s('dcash'))}** | **{fmt(s('pp'))}** |")
    lines.append("")
    if rollovers:
        lines.append("Rollovers excluded from the 401(k) / other split "
                     "(money moved between the two groups):")
        lines.append("")
        for d1, a1, v1, d2, a2, v2 in sorted(rollovers):
            lines.append(f"- {d1[:10]}: {a1} {fmt(v1)} -> {a2} {fmt(v2)} "
                         f"({d2[:10]})")
        lines.append("")

    for y in years:
        lines.append(f"## {y}")
        lines.append("")
        lines.append("| Month | Other deposits | To 401(k) | To other "
                     "investments | New cash to investments | "
                     "Total new money | + Dividends & interest | − Fees | "
                     "− Cash build-up | = PP new investments |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for r in [r for r in rows if r["month"].startswith(y)]:
            lines.append(
                f"| {r['month']} | {fmt(r['other'])} | {fmt(r['new_401k'])} | "
                f"{fmt(r['new_non'])} | {fmt(r['new_cash'])} | "
                f"{fmt(r['other'] + r['new_cash'])} | {fmt(r['div_int'])} | "
                f"{fmt(r['fees'])} | {fmt(r['dcash'])} | {fmt(r['pp'])} |")
        ys = [r for r in rows if r["month"].startswith(y)]
        t = lambda k: sum(r[k] for r in ys)
        lines.append(
            f"| **Total** | **{fmt(t('other'))}** | **{fmt(t('new_401k'))}** "
            f"| **{fmt(t('new_non'))}** | **{fmt(t('new_cash'))}** "
            f"| **{fmt(t('other') + t('new_cash'))}** | **{fmt(t('div_int'))}** "
            f"| **{fmt(t('fees'))}** | **{fmt(t('dcash'))}** | **{fmt(t('pp'))}** |")
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
    rows, last_month, rollovers = compute(repo, cache_dir)
    md = render(rows, last_month, rollovers)
    if out_path:
        with open(out_path, "w") as f:
            f.write(md)
        print(f"wrote {out_path}", file=sys.stderr)
    else:
        print(md)


if __name__ == "__main__":
    main()
