import os, glob
from ofxparse import OfxParser
import pandas as pd

from empower.model import SecurityInfo, TransactionBuilder


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

def get_all_transactions():
    t_all = []
    for file in glob.glob(f"G:\My Drive\Bank\EmpowerRetirement\*.qfx"):
        xtions = get_transactions(file)
        t_all.extend(xtions)
    return t_all

if __name__ == "__main__":
    all_t = get_all_transactions()
    df = pd.DataFrame([t.to_dict() for t in all_t])
    df = df.sort_values(by=["trade_date", "ticker", "units"])
    df.to_csv("aa.csv", index=False)
    print("done")
