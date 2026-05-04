"""BofA CSV importer — converts a BofA/Marcus/Barclays/CapitalOne CSV to Portfolio Performance format."""

from collections import defaultdict

import pandas as pd

from bofa.transaction_builder import TransactionBuilder
from importer_base import BaseImporter
from importer_utils import find_files
from model import PortfolioPerformanceRow

ALLOWED_ACCOUNTS: list[str] = [
    "Manju-Marcus-Saving", "Manju-Marcus-CD",
    "Mangal-Marcus-Saving", "Mangal-Marcus-CD",
    "Mangal-Barclays", "Manju-Barclays",
    "CapitalOne-Manju-CD", "CapitalOne-Mangal-CD",
]


def _filter_accounts(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only rows belonging to known accounts and add an Account Group column."""
    df["Account Group"] = df["Account Name"].apply(
        lambda name: next((sub for sub in ALLOWED_ACCOUNTS if sub in name), name)
    )
    return df[df["Account Group"].isin(ALLOWED_ACCOUNTS)]


def get_transactions(csv_file: str) -> dict[str, list[PortfolioPerformanceRow]]:
    print(f"processing {csv_file}")
    df = _filter_accounts(pd.read_csv(csv_file, dtype=str))
    builder = TransactionBuilder()
    by_account: dict[str, list] = defaultdict(list)
    for _, row in df.iterrows():
        transaction = builder.from_bofa_csv_row(row)
        if transaction:
            by_account[row["Account Group"]].append(transaction)
    return by_account


def get_all_transactions(folder: str, file_pattern: str, label: str) -> dict[str, list[PortfolioPerformanceRow]]:
    all_by_account: dict[str, list] = defaultdict(list)
    for file in find_files(folder, file_pattern, label):
        for account, transactions in get_transactions(file).items():
            all_by_account[account].extend(transactions)
    return all_by_account


class BofaImporter(BaseImporter):
    label = "BofA"

    def load(self, data_folder: str) -> dict[str, pd.DataFrame]:
        all_by_account = get_all_transactions(data_folder, self.file_pattern, self.label)
        return {
            account: pd.DataFrame([t.to_dict() for t in transactions])
            for account, transactions in all_by_account.items()
        }


if __name__ == "__main__":
    BofaImporter("bo*.csv").run(".", "output")
