import glob
import os

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
    files = glob.glob(f"{folder}/ch*.csv")
    if not files:
        print(f"ERROR: No Chase files found matching pattern '{folder}/ch*.csv'")
        return t_all
    for file in files:
        xtions = get_transactions(file)
        t_all.extend(xtions)
    return t_all


def import_all_chase(data_folder: str = ".", output_folder: str = "output"):
    """Import all Chase transactions from the specified data folder"""
    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    all_t = get_all_transactions(data_folder)
    if not all_t:
        print("WARNING: No transactions found for Chase")
        return

    df = pd.DataFrame([t.to_dict() for t in all_t])
    df = df.sort_values(by=["Date", "Type", "Value"])
    out_file = os.path.join(output_folder, "Mangal-Chase.csv")
    df.to_csv(out_file, index=False)
    print(f"Wrote {out_file}")
    print("Chase import done")


if __name__ == "__main__":
    import_all_chase(".")
