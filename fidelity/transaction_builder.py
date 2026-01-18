import datetime

import pandas as pd

from model import PortfolioPerformanceRow, TransactionType


class TransactionBuilder:
    # Map of action prefixes to transaction types (static context)
    STARTSWITH_MAP: dict[str, TransactionType] = {
        "YOU BOUGHT": TransactionType.BUY,
        "ROLLOVER CASH": TransactionType.TRANSFER_INBOUND,
        "DIVIDEND": TransactionType.DIVIDEND,
        "REINVESTMENT": TransactionType.BUY,
        "ELECTRONIC FUNDS TRANSFER PAID": TransactionType.TRANSFER_OUTBOUND,
        "DIRECT DEPOSIT": TransactionType.TRANSFER_INBOUND,
        "ELECTRONIC FUNDS TRANSFER RECEIVED": TransactionType.TRANSFER_INBOUND,
        "CASH ADVANCE ATM": TransactionType.TRANSFER_OUTBOUND,
        "INTEREST": TransactionType.INTEREST,
        "CASH CONTRIBUTION CURRENT YEAR": TransactionType.TRANSFER_INBOUND
    }

    def parse_run_date(self, date_val) -> datetime.date:
        if isinstance(date_val, (datetime.date, pd.Timestamp)):
            # If already a date or Timestamp, convert to date
            return date_val.date() if hasattr(date_val, 'date') else date_val
        raise ValueError(f"Unknown or unsupported run date: {date_val}")

    def compute_type(self, action: str) -> TransactionType:
        if isinstance(action, str):
            action_upper = action.upper()
            for prefix, result in self.STARTSWITH_MAP.items():
                if action_upper.startswith(prefix):
                    return result
        raise ValueError(f"Unknown or unsupported action for transaction type: {action}")

    def from_fidelity_csv_row(self, row):
        # Map Fidelity columns to PortfolioPerformanceRow fields
        date = self.parse_run_date(row["Run Date"])
        type_ = self.compute_type(row.get("Action", ""))
        value = float(row.get("Amount", "0") or 0)
        currency = row.get("Currency", "")
        shares = float(row.get("Quantity", "0") or 0) if row.get("Quantity") else None
        ticker = row.get("Symbol", "")
        security_name = row.get("Description", "")
        note = row.get("Action", "")
        # Do not create a row when ticker is SPAXX and type is Buy
        if ticker == "SPAXX" and type_ == TransactionType.BUY:
            return None

        if ticker == "SPAXX" and type_ == TransactionType.DIVIDEND:
            type_ = TransactionType.INTEREST
        if security_name.startswith("UNITED STATES TREAS") and type_ == TransactionType.INTEREST:
            type_ = TransactionType.DIVIDEND
        return PortfolioPerformanceRow(
            Date=date,
            Type=type_,
            Value=value,
            Transaction_Currency=currency,
            Shares=shares,
            Ticker_Symbol=ticker,
            Security_Name=security_name,
            Note=note
        )
