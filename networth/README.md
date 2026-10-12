# networth

Net worth tooling for the finance-data repo (Portfolio Performance CSV exports).

- `common.py` — shared parsing: transactions, quotes, FX, proxy series
- `snapshot.py` — current net worth; JSON by default, `--prices prices.json` for tables
- `history.py` — month-end net worth time series (`--chart out.png` for a chart)
- `attribution.py` — yearly split into contributions / dividends & interest / market gains

Data dir resolution: argv[1], `$FINANCE_DATA_DIR`, `../../finance-data`, `/tmp/finance-data`.
External price/FX data is fetched once and cached under `~/.cache/networth`.
