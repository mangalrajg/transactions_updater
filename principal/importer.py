"""
Comprehensive Principal importer that handles both steps:
1. QFX to CSV format conversion
2. CSV to Portfolio Performance format conversion
"""

import glob
import os
import tempfile

import pandas as pd

from principal.portfolio_perf_importer import PortfolioPerformanceImporter
from principal.qfx_importer import get_all_transactions as qfx_to_csv


def import_principal(data_folder: str = ".", output_folder: str = "output"):
    """
    Import Principal transactions from QFX files in a 2-step process:
    1. Convert QFX to CSV format
    2. Transform CSV to Portfolio Performance format
    """
    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    print("\n--- Principal Import: Step 1 - QFX to CSV conversion ---")

    # Step 1: Convert QFX to CSV format
    files = glob.glob(f"{data_folder}/pr*.qfx")
    if not files:
        print(f"ERROR: No Principal files found matching pattern '{data_folder}/pr*.qfx'")
        return

    # Get transactions from QFX
    all_transactions = qfx_to_csv(data_folder)
    if not all_transactions:
        print("WARNING: No transactions found for Principal")
        return

    # Create temporary CSV with QFX data
    temp_csv = os.path.join(tempfile.gettempdir(), "principal_temp.csv")
    df_qfx = pd.DataFrame([t.to_dict() for t in all_transactions])
    df_qfx = df_qfx.sort_values(by=["trade_date", "ticker", "units"])
    df_qfx.to_csv(temp_csv, index=False)
    print(f"Created temporary CSV from QFX: {temp_csv}")

    print("\n--- Principal Import: Step 2 - CSV to Portfolio Performance format ---")

    # Step 2: Transform CSV to Portfolio Performance format
    try:
        importer = PortfolioPerformanceImporter(temp_csv)
        output_file = os.path.join(output_folder, "Manju-Principal.csv")
        importer.save_transformed(output_file)
        print(f"Wrote {output_file}")
    except Exception as e:
        print(f"ERROR during Portfolio Performance transformation: {e}")
        import traceback
        traceback.print_exc()
        return
    finally:
        # Clean up temporary file
        if os.path.exists(temp_csv):
            os.remove(temp_csv)
            print(f"Cleaned up temporary file: {temp_csv}")

    print("Principal import done")


if __name__ == "__main__":
    import_principal("data")
