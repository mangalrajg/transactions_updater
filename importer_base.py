"""Abstract base class that all importers must implement."""

from abc import ABC, abstractmethod

import pandas as pd

from importer_utils import save_dataframe

SORT_BY = ["Date", "Type", "Value"]


class BaseImporter(ABC):
    """
    Contract for every importer.

    Subclasses declare a fixed `label` (the provider name) and receive the
    glob file_pattern at construction time so patterns stay in one place (main.py).
    """

    label: str = ""  # overridden by each subclass, e.g. "BofA", "Chase"

    def __init__(self, file_pattern: str):
        self.file_pattern = file_pattern

    @abstractmethod
    def load(self, data_folder: str) -> dict[str, pd.DataFrame]:
        """
        Read source files from data_folder and return one DataFrame per account.

        Returns:
            {account_name: DataFrame} — each DataFrame is in Portfolio Performance format.
        """

    def run(self, data_folder: str, output_folder: str):
        """Load and save all accounts. Used by main.py and standalone __main__ scripts."""
        results = self.load(data_folder)
        if not results:
            print(f"WARNING: No transactions found for {self.label}")
            return
        for account_name, df in results.items():
            save_dataframe(df, output_folder, f"{account_name}.csv", sort_by=SORT_BY)
        print(f"{self.label} import done")
