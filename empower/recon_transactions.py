import pandas as pd

def load_and_compare(portfolio_file, empower_file):
    df_portfolio = pd.read_csv(portfolio_file, dtype=str)
    df_empower = pd.read_csv(empower_file, dtype=str)
    # Normalize Date column to only the date part (YYYY-MM-DD)
    for df in [df_portfolio, df_empower]:
        df.loc[:, 'Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.strftime('%Y-%m-%d')
        # Remove commas from Value and convert to float with decimals (as string for merge)
        df.loc[:, 'Value'] = pd.to_numeric(df['Value'].str.replace(',', '', regex=False), errors='coerce').round(2).astype(str)
    key_cols = ['Date', 'Type', 'Value', 'Ticker Symbol']
    df_portfolio = df_portfolio.loc[:, key_cols].copy()
    df_empower = df_empower.loc[:, key_cols].copy()
    # Add a source column to each using .loc
    df_portfolio.loc[:, '__source'] = 'portfolio_performance_import.csv'
    df_empower.loc[:, '__source'] = 'Mangal-Empower.csv'
    # Concatenate and drop duplicates (keep=False removes all exact duplicates)
    combined = pd.concat([df_portfolio, df_empower], ignore_index=True)
    deduped = combined.drop_duplicates(subset=key_cols, keep=False).copy()
    # For each row, check if a row with the same Date exists in the other file, and if so, which columns differ
    def find_diff_reason(row):
        this_source = row['__source']
        other_source = 'Mangal-Empower.csv' if this_source == 'portfolio_performance_import.csv' else 'portfolio_performance_import.csv'
        other_rows = combined[(combined['Date'] == row['Date']) & (combined['__source'] == other_source)]
        if other_rows.empty:
            return f"Row only in {this_source}"
        diffs = []
        for col in key_cols[1:]:  # skip Date, already matched
            other_vals = other_rows[col].unique()
            if not (other_rows[col] == row[col]).any():
                diffs.append(f"{col}: {row[col]} ({this_source}), {other_vals.tolist()} ({other_source})")
        if diffs:
            return f"Different column(s): {'; '.join(diffs)}"
        return f"Row only in {this_source}"
    deduped.loc[:, 'Difference Reason'] = deduped.apply(find_diff_reason, axis=1)
    deduped = deduped.drop(columns=['__source'])
    return deduped

if __name__ == "__main__":
    diff_df = load_and_compare('portfolio_performance_import.csv', 'Mangal-Empower.csv')
    diff_df.to_csv('recon_differences.csv', index=False)
    print('Differences saved to recon_differences.csv')
