"""Generic QFX file reader — provider-agnostic parsing of OFX/QFX files."""

from ofxparse import OfxParser

from importer_utils import find_files
from qfx.model import SecurityInfo, Transaction, TransactionBuilder


def _parse_qfx_file(qfx_file: str) -> list[Transaction]:
    print(f"processing {qfx_file}")
    qfx = OfxParser.parse(open(qfx_file, encoding="latin-1"))
    sec_map = {sec.uniqueid: SecurityInfo(sec.ticker, sec.name) for sec in qfx.security_list}
    builder = TransactionBuilder(sec_map)
    return [builder.from_ofx_transaction(t) for t in qfx.account.statement.transactions]


def get_all_transactions(folder: str, file_pattern: str, label: str) -> dict[str, list[Transaction]]:
    """Read all QFX files matching file_pattern and return transactions keyed by label."""
    transactions = []
    for file in find_files(folder, file_pattern, label):
        transactions.extend(_parse_qfx_file(file))
    return {label: transactions}
