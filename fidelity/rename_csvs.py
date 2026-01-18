import glob
import os

import pandas as pd


def rename_fidelity_files(folder: str):
    for file in glob.glob(f"{folder}/Accounts_History*.csv"):
        print(f"processing file {file}")
        try:
            df = pd.read_csv(file, dtype=str)
            # Parse 'Run Date' as datetime, coerce errors to NaT
            df["Run Date"] = pd.to_datetime(df["Run Date"], format="%m/%d/%Y", errors="coerce")
            # Filter out rows with invalid dates
            valid_dates = df["Run Date"].dropna()
            if valid_dates.empty:
                print(f"No valid Run Date found in {file}, skipping.")
                continue
            min_date = valid_dates.min().strftime("%Y-%m-%d")
            max_date = valid_dates.max().strftime("%Y-%m-%d")
            new_file = f"{min_date}_to_{max_date}_fidelity_transactions.csv"
            os.rename(file, new_file)
            print(f"Renamed {file} to {new_file}")
        except Exception as e:
            print(f"Error processing {file}: {e}")


if __name__ == "__main__":
    rename_fidelity_files(".")
    # Map account numbers to filenames
