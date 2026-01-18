import datetime
import re

from model import PortfolioPerformanceRow, TransactionType


class TransactionBuilder:
    TYPE_MAP: dict[str, TransactionType] = {
        "Buy": TransactionType.BUY,
        "Sell": TransactionType.SELL,
        "Dividend": TransactionType.DIVIDEND,
        "Interest": TransactionType.INTEREST,
        "Reinvest": TransactionType.BUY
        # Add other mappings as needed
    }

    def parse_trade_date(self, trade_date_str) -> datetime.date:
        """Parse trade_date as a date object (format: month/date/year)"""
        if trade_date_str:
            return datetime.datetime.strptime(trade_date_str.split()[0], '%m/%d/%Y').date()
        return None

    def get_qty(self, row):
        qty = row.get('Quantity', '')
        if row.get('Type', '') == TransactionType.DIVIDEND.value:
            desc = row.get('Description', '')
            # Extract the number before 'SHS' using regex
            match = re.search(r'([\d.]+)\s*SHS', desc)
            if match:
                qty = match.group(1)
            else:
                raise ValueError(f"No quantity found before 'SHS' in description: {desc}")
        return qty

    def to_transaction_type(self, type_val) -> TransactionType:
        if type_val == 'DBS':
            return None
        return self.TYPE_MAP.get(type_val)

    def from_chase_csv_row(self, row):
        trade_date = self.parse_trade_date(row.get('Trade Date', ''))
        qty = self.get_qty(row)
        type_val = row.get('Type', '')
        type_enum = self.to_transaction_type(type_val)
        if type_enum is None:
            return None  # Do not create PortfolioPerformanceRow if type_val is DBS
        return PortfolioPerformanceRow(
            Date=trade_date,
            Type=type_enum,
            Value=row.get('Amount USD', ''),
            Transaction_Currency=row.get('Local Currency', ''),
            Shares=qty,
            Ticker_Symbol=row.get('Ticker', ''),
            Note=row.get('Description', ''),
            Security_Name=''
        )
