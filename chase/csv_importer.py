import glob

import pandas as pd

from chase.transaction_builder import TransactionBuilder


def get_transactions(csv_file):
    print(f"processing {csv_file}")
    df = pd.read_csv(csv_file)
    raw = []
    # Build sec_map from unique Ticker/Cusip/Security Name if needed
    builder = TransactionBuilder()
    for _, row in df.iterrows():
        transaction = builder.from_chase_csv_row(row)
        if transaction:
            raw.append(transaction)
    return raw


def get_all_transactions(folder: str):
    t_all = []
    for file in glob.glob(f"{folder}/transactions.csv"):
        xtions = get_transactions(file)
        t_all.extend(xtions)
    return t_all


if __name__ == "__main__":
    all_t = get_all_transactions(".")
    df = pd.DataFrame([t.to_dict() for t in all_t])
    df = df.sort_values(by=["Date", "Type", "Value"])
    df.to_csv("chase_aa.csv", index=False)
    print("done")
