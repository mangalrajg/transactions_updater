import glob
import os

import pandas as pd
from ofxparse import OfxParser

from qfx_model import SecurityInfo, TransactionBuilder


def rename_qfx(qfx_file):
    qfx = OfxParser.parse(open(qfx_file, encoding="latin-1"))
    ed = qfx.account.statement.end_date
    sd = qfx.account.statement.start_date
    new_filename = f"EmpowerRetirement_{sd.strftime('%Y-%m-%d')}_to_{ed.strftime('%Y-%m-%d')}"
    new_file = f"{os.path.dirname(qfx_file)}\\{new_filename}.qfx"
    print(new_file)
    os.rename(qfx_file, new_file)


def get_transactions(qfx_file):
    print(f"processing {qfx_file}")
    qfx = OfxParser.parse(open(qfx_file, encoding="latin-1"))
    raw = []
    sec_map = {}
    for sec in qfx.security_list:
        sec_map[sec.uniqueid] = SecurityInfo(sec.ticker, sec.name)
    builder = TransactionBuilder(sec_map)
    for t in qfx.account.statement.transactions:
        transaction = builder.from_ofx_transaction(t)
        raw.append(transaction)
    return raw


def get_all_transactions(folder: str):
    t_all = []
    files = glob.glob(f"{folder}/Em*.qfx")
    if not files:
        print(f"ERROR: No Empower files found matching pattern '{folder}/Em*.qfx'")
        return t_all
    for file in files:
        xtions = get_transactions(file)
        t_all.extend(xtions)
    return t_all


def import_all_empower(data_folder: str = ".", output_folder: str = "output"):
    """Import all Empower transactions from the specified data folder"""
    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    all_t = get_all_transactions(data_folder)
    if not all_t:
        print("WARNING: No transactions found for Empower")
        return

    df = pd.DataFrame([t.to_dict() for t in all_t])
    df = df.sort_values(by=["trade_date", "ticker", "units"])
    out_file = os.path.join(output_folder, "empower_aa.csv")
    df.to_csv(out_file, index=False)
    print(f"Wrote {out_file}")
    print("Empower import done")


if __name__ == "__main__":
    import_all_empower("data")
