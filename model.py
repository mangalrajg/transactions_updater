import datetime
import enum
from dataclasses import dataclass
from typing import Optional


class TransactionType(enum.Enum):
    """Enumeration for different types of financial transactions."""
    BUY = "Buy"
    SELL = "Sell"
    TRANSFER_INBOUND = "Transfer (Inbound)"
    TRANSFER_OUTBOUND = "Transfer (Outbound)"
    DIVIDEND = "Dividend"
    FEES = "Fees"
    INTEREST = "Interest"
    WITHDRAWAL = "Removal"
    DEPOSIT = "Deposit"
    TO_CHECK = "TO_CHECK"
    # Add more as needed


@dataclass
class PortfolioPerformanceRow:
    Date: datetime.date
    Type: TransactionType
    Value: float
    Transaction_Currency: str
    Shares: Optional[float] = None
    Ticker_Symbol: Optional[str] = ''
    Security_Name: str = ''
    Note: str = ''

    def to_dict(self):
        return {
            'Date': self.Date,
            'Type': self.Type.value,
            'Value': self.Value,
            'Transaction Currency': self.Transaction_Currency,
            'Shares': self.Shares,
            'Ticker Symbol': self.Ticker_Symbol,
            'Security Name': self.Security_Name,
            'Note': self.Note
        }
