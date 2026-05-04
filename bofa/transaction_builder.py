"""BofA transaction builder — maps BofA CSV rows to PortfolioPerformanceRow objects."""

import datetime

from model import PortfolioPerformanceRow, TransactionType


class TransactionBuilder:
    STARTSWITH_MAP: dict[str, TransactionType] = {
        "interest": TransactionType.INTEREST,
        "CD Increase Int Paid": TransactionType.INTEREST,
        "Monthly Interest Paid": TransactionType.INTEREST,
        "withdrawal": TransactionType.WITHDRAWAL,
        "transfer (inbound)": TransactionType.TRANSFER_INBOUND,
    }

    def compute_type(self, description: str) -> TransactionType | None:
        if isinstance(description, str):
            desc_lower = description.strip().lower()
            for prefix, result in self.STARTSWITH_MAP.items():
                if desc_lower.startswith(prefix.lower()):
                    return result
        return None

    def from_bofa_csv_row(self, row) -> PortfolioPerformanceRow | None:
        description = row.get("Original Description", "").strip()
        account_name = row.get("Account Name", "")
        type_ = self.compute_type(description)
        if not type_:
            print(f"WARN IGNORE [{description}] on account [{account_name}]")
            return None
        value = float(str(row.get("Amount", "0")).replace(",", ""))
        return PortfolioPerformanceRow(
            Date=datetime.datetime.strptime(row["Date"], "%m/%d/%Y").date(),
            Type=type_,
            Value=value,
            Transaction_Currency=row.get("Currency", ""),
            Note=f"{account_name} {description}",
        )
