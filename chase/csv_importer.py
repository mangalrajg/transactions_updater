"""Chase CSV importer — converts a Chase brokerage CSV to Portfolio Performance format."""

import pandas as pd

from chase.transaction_builder import TransactionBuilder
from importer_base import BaseImporter
from importer_utils import find_files
from model import PortfolioPerformanceRow

ACCOUNT_NAME = "Mangal-Chase"


def get_transactions(csv_file: str) -> dict[str, list[PortfolioPerformanceRow]]:
    print(f"processing {csv_file}")
    df = pd.read_csv(csv_file)
    builder = TransactionBuilder()
    transactions = []
    for _, row in df.iterrows():
        transaction = builder.from_chase_csv_row(row)
        if transaction:
            transactions.append(transaction)
    return {ACCOUNT_NAME: transactions}


def get_all_transactions(folder: str, file_pattern: str, label: str) -> dict[str, list[PortfolioPerformanceRow]]:
    all_by_account: dict[str, list] = {}
    for file in find_files(folder, file_pattern, label):
        for account, transactions in get_transactions(file).items():
            all_by_account.setdefault(account, []).extend(transactions)
    return all_by_account


class ChaseImporter(BaseImporter):
    label = "Chase"

    def load(self, data_folder: str) -> dict[str, pd.DataFrame]:
        all_by_account = get_all_transactions(data_folder, self.file_pattern, self.label)
        return {
            account: pd.DataFrame([t.to_dict() for t in transactions])
            for account, transactions in all_by_account.items()
        }


if __name__ == "__main__":
    ChaseImporter("ch*.csv").run(".", "output")
