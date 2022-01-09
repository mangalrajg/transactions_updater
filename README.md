# Sheets transactions updater
Script to automate updation of my personal investment transactions google sheet from bank statement 

## spreadsheet_snippets.py
Class taken directly from Google sample code to interact with google sheets. 

## chase_converter.py
Class that parse chase transaction statement and extract trading + divident transactions, and compute quantity and divident from descriptions.

## update_transactions.py

Driver script that
- Get existing transactions from google sheets
- Get Chase transactions from bank statement (using chase_converter.py)
- Reconsile and find new transactions in chase
- Update Google sheets with new transactions data
