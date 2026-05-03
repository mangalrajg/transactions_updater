import glob
import os
from collections import defaultdict

import pandas as pd

from fidelity.transaction_builder import TransactionBuilder


def get_transactions(csv_file):
    print(f"processing {csv_file}")
    df = pd.read_csv(csv_file, dtype=str)
    # Try to parse 'Run Date' as datetime, coerce errors to NaT
    df["Run Date"] = pd.to_datetime(df["Run Date"], format="%m/%d/%Y", errors="coerce")
    # Only keep rows where 'Run Date' is a valid date (not NaT)
    df = df[df["Run Date"].notna()]
    builder = TransactionBuilder()
    transactions_by_account = defaultdict(list)
    for _, row in df.iterrows():
        transaction = builder.from_fidelity_csv_row(row)
        if transaction:
            account_number = row.get("Account Number", "unknown")
            transactions_by_account[account_number].append(transaction)
        else:
            print(f"IGNORED: {row.get('Action', '')}")
    return transactions_by_account


def get_all_transactions(folder: str):
    all_by_account = defaultdict(list)
    files = glob.glob(f"{folder}/fi*.csv")
    if not files:
        print(f"ERROR: No Fidelity files found matching pattern '{folder}/fi*.csv'")
        return all_by_account
    for file in files:
        file_xtions = get_transactions(file)
        for account_number, xtions in file_xtions.items():
            all_by_account[account_number].extend(xtions)
    return all_by_account


def import_all_fidelity(data_folder: str = ".", output_folder: str = "output"):
    """Import all Fidelity transactions from the specified data folder"""
    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    # Map account numbers to filenames
    account_file_map = {
        'Z32333154': 'Mangal-Fidelity',
        '268077728': 'Mangal-FidelityRothIRA',
        'Z31493183': 'Manju-Fidelity',
        '242899894': 'Manju-FidelityRothIRA',
        '244713544': 'Manju-FidelityIRA'
    }
    all_by_account = get_all_transactions(data_folder)
    if not all_by_account:
        print("WARNING: No transactions found for Fidelity")
        return

    for account_number, transactions in all_by_account.items():
        df = pd.DataFrame([t.to_dict() for t in transactions])
        df = df.sort_values(by=["Date", "Type", "Value"])
        account_name = account_file_map.get(account_number, account_number)
        out_file = os.path.join(output_folder, f"{account_name}.csv")
        df.to_csv(out_file, index=False)
        print(f"Wrote {out_file}")
    print("Fidelity import done")


if __name__ == "__main__":
    import_all_fidelity(".")
