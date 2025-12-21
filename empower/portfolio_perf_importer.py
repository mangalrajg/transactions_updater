import pandas as pd
from typing import Optional
from dataclasses import dataclass, asdict

@dataclass
class PortfolioPerformanceRow:
    Date: str
    Type: str
    Value: float
    Transaction_Currency: str
    Shares: Optional[float] = None
    ISIN: Optional[str] = ''
    Ticker_Symbol: Optional[str] = ''
    Security_Name: str = ''
    Note: str = ''

class PortfolioPerformanceImporter:
    def __init__(self, csv_path='aa.csv'):
        self.csv_path = csv_path
        self.df = pd.read_csv(csv_path)

    def create_reinvest_buy(self, row):
        return PortfolioPerformanceRow(
            Date=row['trade_date'],
            Type='Buy',
            Value=row['total'],
            Transaction_Currency='USD',
            Shares=row['units'],
            ISIN='',
            Ticker_Symbol=row.get('ticker', ''),
            Security_Name=row.get('security_name', ''),
            Note='Reinvested dividend'
        )

    def create_reinvest_dividend(self, row):
        return PortfolioPerformanceRow(
            Date=row['trade_date'],
            Type='Dividend',
            Value=row['total'],
            Transaction_Currency='USD',
            Shares=None,
            ISIN='',
            Ticker_Symbol=row.get('ticker', ''),
            Security_Name=row.get('security_name', ''),
            Note='Dividend payout for reinvestment'
        )

    def transform_buymf(self, row):
        return PortfolioPerformanceRow(
            Date=row['trade_date'],
            Type='Buy',
            Value=row['total'],
            Transaction_Currency='USD',
            Shares=row['units'],
            ISIN='',
            Ticker_Symbol=row.get('ticker', ''),
            Security_Name=row.get('security_name', ''),
            Note='Buy mutual fund'
        )

    def create_inbound_transfer(self, row):
        return PortfolioPerformanceRow(
            Date=row['trade_date'],
            Type='Transfer (Inbound)',
            Value=-1 * row['total'],
            Transaction_Currency='USD',
            Shares=None,
            ISIN='',
            Ticker_Symbol='',
            Security_Name='',
            Note='Auto-generated for Buy mutual fund'
        )

    def calculate_value(self, row):
        """
        Calculate the value for a transaction row. If total is zero (or near zero),
        calculate as units * unit_price. Always round to two decimal places and handle floating point errors.
        Raise an exception if calculation fails.
        """
        value = row['total']
        try:
            if (isinstance(value, (int, float)) and abs(value) < 1e-8) or (isinstance(value, str) and (value.strip() == '' or abs(float(value)) < 1e-8)):
                value = float(row.get('units', 0)) * float(row.get('unit_price', 0))
        except Exception as e:
            raise ValueError(f"Error calculating value for row: {row}. Exception: {e}")
        # Round value to two decimal places to handle floating point errors
        try:
            value = round(float(value) + 1e-8, 2)
        except Exception as e:
            raise ValueError(f"Error rounding value for row: {row}. Exception: {e}")
        return value

    def transform_transfer(self, row):
        # Set Type as Buy if tferaction is IN, otherwise Sell if OUT
        tferaction = str(row.get('tferaction', '')).upper()
        value = self.calculate_value(row)
        if tferaction == 'IN':
            type_value = 'Buy'
            note = 'Transfer In (Buy)'
            value = -1 * abs(value)
        elif tferaction == 'OUT':
            type_value = 'Sell'
            note = 'Transfer Out (Sell)'
            value = abs(value)
        else:
            type_value = 'Unexpected Type'
            note = 'Transfer'
        return PortfolioPerformanceRow(
            Date=row['trade_date'],
            Type=type_value,
            Value=value,
            Transaction_Currency='USD',
            Shares=row['units'],
            ISIN='',
            Ticker_Symbol=row.get('ticker', ''),
            Security_Name=row.get('security_name', ''),
            Note=note
        )

    def create_fees(self, row):
        """
        Create a PortfolioPerformanceRow for a fee if tferaction == OUT and abs(value) < 50.
        Returns None if not a fee transaction.
        """
        tferaction = str(row.get('tferaction', '')).upper()
        value = self.calculate_value(row)
        if tferaction == 'OUT' and abs(value) < 50:
            return PortfolioPerformanceRow(
                Date=row['trade_date'],
                Type='Fees',
                Value=value,
                Transaction_Currency='USD',
                Shares=None,
                ISIN='',
                Ticker_Symbol=row.get('ticker', ''),
                Security_Name=row.get('security_name', ''),
                Note='Fee transaction (auto-detected)'
            )
        return None

    def transform(self):
        result = []
        for _, row in self.df.iterrows():
            type_value = str(row.get('type', '')).lower()
            if type_value == 'reinvest':
                result.append(self.create_reinvest_buy(row))
                result.append(self.create_reinvest_dividend(row))
            elif type_value == 'buymf':
                result.append(self.transform_buymf(row))
                result.append(self.create_inbound_transfer(row))
            elif type_value == 'transfer':
                result.append(self.transform_transfer(row))
                fee_row = self.create_fees(row)
                if fee_row:
                    result.append(fee_row)
            else:
                raise ValueError(f"Unhandled transaction type: {type_value} in row: {row}")
        return result

    def merge_inbound_transfers(self, df):
        """
        Merge all 'Transfer (Inbound)' transactions for a day into a single transaction.
        For merged inbound transfers, Shares, ISIN, Ticker Symbol, and Security Name are set to None or ''.
        Returns a DataFrame with only merged inbound transfers and all other transactions.
        """
        inbound_mask = df['Type'] == 'Transfer (Inbound)'
        if getattr(inbound_mask, 'any', lambda: False)():
            grouped = df[inbound_mask].groupby('Date', as_index=False).agg({
                'Date': 'first',
                'Type': 'first',
                'Value': 'sum',
                'Transaction Currency': 'first',
                'Note': lambda x: 'Merged inbound transfer'
            })
            # Set ignored columns to None or '' for merged inbound transfers
            grouped['Shares'] = None
            grouped['ISIN'] = None
            grouped['Ticker Symbol'] = None
            grouped['Security Name'] = None
            # Remove original inbound transfers and use only merged
            df = df[~inbound_mask]
            df = pd.concat([df, grouped], ignore_index=True, sort=False)
        return df

    def save_transformed(self, output_path='portfolio_performance_import.csv'):
        transformed = self.transform()
        df = pd.DataFrame([asdict(row) for row in transformed])
        # Rename columns to match Portfolio Performance import format
        df.rename(columns={
            'Transaction_Currency': 'Transaction Currency',
            'Ticker_Symbol': 'Ticker Symbol',
            'Security_Name': 'Security Name'
        }, inplace=True)
        # Map of ticker symbol replacements
        ticker_map = {
            '87281J204': 'TR45HT',
            '06427F314' : 'BNYLCG',
            '06427F694':'BNYSII'
            # Add more mappings here as needed
        }
        if 'Ticker Symbol' in df.columns:
            df['Ticker Symbol'] = df['Ticker Symbol'].replace(ticker_map)
        df = self.merge_inbound_transfers(df)
        # Sort by Date, Type, and Value before saving
        df = df.sort_values(by=["Date", "Type", "Value"])
        df.to_csv(output_path, index=False)

# Example usage:

if __name__ == "__main__":
    importer = PortfolioPerformanceImporter()
    importer.save_transformed()
