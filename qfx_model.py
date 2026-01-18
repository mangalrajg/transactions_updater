class SecurityInfo:
    def __init__(self, ticker, name):
        self.ticker = ticker
        self.name = name

class Transaction:
    def __init__(self, type_, trade_date, tferaction, security, income_type, units, unit_price, total, security_name, ticker):
        self.type = type_
        self.trade_date = trade_date
        self.tferaction = tferaction
        self.security = security
        self.income_type = income_type
        self.units = units
        self.unit_price = unit_price
        self.total = total
        self.security_name = security_name
        self.ticker = ticker

    def to_dict(self):
        return {
            'type': self.type,
            'trade_date': self.trade_date,
            'tferaction': self.tferaction,
            'security': self.security,
            'income_type': self.income_type,
            'units': self.units,
            'unit_price': self.unit_price,
            'total': self.total,
            'security_name': self.security_name,
            'ticker': self.ticker
        }

class TransactionBuilder:
    def __init__(self, sec_map):
        self.sec_map = sec_map

    def from_ofx_transaction(self, t):
        trade_date = t.tradeDate.strftime("%Y-%m-%d")
        sec_info = self.sec_map.get(t.security)
        security_name = sec_info.name if sec_info else None
        ticker = sec_info.ticker if sec_info else None
        return Transaction(
            t.type,
            trade_date,
            t.tferaction,
            t.security,
            t.income_type,
            t.units,
            t.unit_price,
            t.total,
            security_name,
            ticker
        )
