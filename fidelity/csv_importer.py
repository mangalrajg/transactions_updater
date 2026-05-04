"""Fidelity CSV importer — converts a Fidelity Accounts History CSV to Portfolio Performance format."""

from collections import defaultdict

import pandas as pd

from fidelity.transaction_builder import TransactionBuilder
from importer_base import BaseImporter
from importer_utils import find_files
from model import PortfolioPerformanceRow

# Maps Fidelity account numbers to human-readable output file names
ACCOUNT_FILE_MAP: dict[str, str] = {
    "Z32333154": "Mangal-Fidelity",
    "268077728": "Mangal-FidelityRothIRA",
    "Z31493183": "Manju-Fidelity",
    "242899894": "Manju-FidelityRothIRA",
    "244713544": "Manju-FidelityIRA",
}


def get_transactions(csv_file: str) -> dict[str, list[PortfolioPerformanceRow]]:
    print(f"processing {csv_file}")
    df = pd.read_csv(csv_file, dtype=str)
    df["Run Date"] = pd.to_datetime(df["Run Date"], format="%m/%d/%Y", errors="coerce")
    df = df[df["Run Date"].notna()]
    builder = TransactionBuilder()
    by_account: dict[str, list] = defaultdict(list)
    for _, row in df.iterrows():
        transaction = builder.from_fidelity_csv_row(row)
        if transaction:
            by_account[row.get("Account Number", "unknown")].append(transaction)
        else:
            print(f"IGNORED: {row.get('Action', '')}")
    return by_account


def get_all_transactions(folder: str, file_pattern: str, label: str) -> dict[str, list[PortfolioPerformanceRow]]:
    all_by_account: dict[str, list] = defaultdict(list)
    for file in find_files(folder, file_pattern, label):
        for account, transactions in get_transactions(file).items():
            all_by_account[account].extend(transactions)
    return all_by_account


class FidelityImporter(BaseImporter):
    label = "Fidelity"

    def load(self, data_folder: str) -> dict[str, pd.DataFrame]:
        all_by_account = get_all_transactions(data_folder, self.file_pattern, self.label)
        return {
            ACCOUNT_FILE_MAP.get(acct_num, acct_num): pd.DataFrame([t.to_dict() for t in transactions])
            for acct_num, transactions in all_by_account.items()
        }


if __name__ == "__main__":
    FidelityImporter("fi*.csv").run(".", "output")
