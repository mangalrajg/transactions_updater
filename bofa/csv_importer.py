import datetime
import glob
import os
from collections import defaultdict

import pandas as pd

from model import PortfolioPerformanceRow, TransactionType


class BofaTransactionBuilder:
    # Map of description prefixes to transaction types
    STARTSWITH_MAP: dict[str, TransactionType] = {
        'interest': TransactionType.INTEREST,
        'CD Increase Int Paid': TransactionType.INTEREST,
        'Monthly Interest Paid': TransactionType.INTEREST,
        'withdrawal': TransactionType.WITHDRAWAL,
        'transfer (inbound)': TransactionType.TRANSFER_INBOUND
    }

    @staticmethod
    def compute_type(description: str):
        if isinstance(description, str):
            desc_lower = description.strip().lower()
            for prefix, result in BofaTransactionBuilder.STARTSWITH_MAP.items():
                if desc_lower.startswith(prefix.lower()):
                    return result
        return None

    @staticmethod
    def from_bofa_csv_row(row):
        description = row.get('Original Description', '').strip()
        # Remove commas from the amount string before converting to float
        amount_str = str(row.get('Amount', '0')).replace(',', '')
        value = float(amount_str)
        currency = row.get('Currency', '')
        account_name = row.get('Account Name', '')
        type_ = BofaTransactionBuilder.compute_type(description)
        if not type_:
            print(f"WARN IGNORE [{description}] on account [{account_name}]")
            return None
        date = datetime.datetime.strptime(row['Date'], '%m/%d/%Y').date()
        return PortfolioPerformanceRow(
            Date=date,
            Type=type_,
            Value=value,
            Transaction_Currency=currency,
            Shares=None,
            Ticker_Symbol='',
            Security_Name='',
            Note=f"{account_name} {description}"
        )


allowed_accounts: list[str] = [
    'Manju-Marcus-Saving',
    'Manju-Marcus-CD',
    'Mangal-Marcus-Saving',
    'Mangal-Marcus-CD',
    'Mangal-Barclays',
    'Manju-Barclays',
    'CapitalOne-Manju-CD',
    'CapitalOne-Mangal-CD'
]


def filter_and_replace_account_names(transactions_df):
    transactions_df['Account Group'] = transactions_df['Account Name'].apply(
        lambda name: next((sub for sub in allowed_accounts if sub in name), name)
    )
    return transactions_df[transactions_df['Account Group'].isin(allowed_accounts)]


def import_bofa_interest_transactions(csv_file):
    transactions_df = pd.read_csv(csv_file, dtype=str)
    transactions_df = filter_and_replace_account_names(transactions_df)
    transactions_by_account = defaultdict(list)
    builder = BofaTransactionBuilder()
    for _, row in transactions_df.iterrows():
        transaction = builder.from_bofa_csv_row(row)
        if transaction:
            account_name = row.get('Account Group', 'unknown')
            transactions_by_account[account_name].append(transaction)
    return transactions_by_account


def get_all_transactions(folder: str):
    all_by_account = defaultdict(list)
    files = glob.glob(f"{folder}/bo*.csv")
    if not files:
        print(f"ERROR: No BofA files found matching pattern '{folder}/bo*.csv'")
        return all_by_account
    for file in files:
        file_xtions = import_bofa_interest_transactions(file)
        for account_number, xtions in file_xtions.items():
            all_by_account[account_number].extend(xtions)
    return all_by_account


def import_all_bofa(data_folder: str = ".", output_folder: str = "output"):
    """Import all Bofa transactions from the specified data folder"""
    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    all_by_account = get_all_transactions(data_folder)
    if not all_by_account:
        print("WARNING: No transactions found for BofA")
        return

    for account_name, transactions in all_by_account.items():
        df = pd.DataFrame([t.to_dict() for t in transactions])
        df = df.sort_values(by=["Date", "Type", "Value"])
        out_file = os.path.join(output_folder, f"{account_name.replace(' ', '_').replace('/', '-')}.csv")
        df.to_csv(out_file, index=False)
        print(f"Wrote {out_file}")
    print("Bofa import done")


if __name__ == "__main__":
    # List of allowed account names
    import_all_bofa('.')
