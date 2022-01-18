from __future__ import print_function

import os.path
import numpy as np
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import spreadsheet_snippets as xl
import empower_converter as empower

# If modifying these scopes, delete the file token.json.
#SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
# The ID and range of a sample spreadsheet.
SAMPLE_SPREADSHEET_ID = '1oUH0KuqN53-gYxuIQoyQNclnE1XfJYTnrC0FUqzPIno'
SAMPLE_RANGE_NAME = 'Transactions_OSV!A1:G'

def create_service():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    try:
        service = build('sheets', 'v4', credentials=creds)
        return service
    except HttpError as err:
        print(err)

def compare_row(existing_row, new_row):
    if existing_row[0] == new_row[0] and existing_row[2] == new_row[2]:
        # if Date, Type and Ticker matches
        
        existing_units=round(float(existing_row[4]),1)
        new_units = round(new_row[3],1)
        existing_price = round(float(existing_row[5].strip('$')),2)
        print(new_row[4])
        new_price = float(np.round(float(new_row[4]),2))
        ret= existing_units == new_units and abs(existing_price-new_price) <=0.011
        if not ret:
            print(f"{existing_row} {new_row}")
            print(f"existing_units == new_units")
        return ret
    else:
        return False

def data_contains(data, row):
    found = [f for f in data if compare_row(f,row) ]
    return not found

#if __name__ == '__main__':
service = create_service()

sheetInterface=xl.SpreadsheetSnippets(service)
result = sheetInterface.get_values(SAMPLE_SPREADSHEET_ID,SAMPLE_RANGE_NAME)
current_data=result.get('values', [])

empower_data=empower.get_all_transactions()

filtered = [row for row in empower_data if data_contains(current_data, row)] 
#existing = [row for row in empower_data.values.tolist() if not data_contains(current_data, row)] 
if len(filtered) >0:
    print("rows to update")
    print(*filtered, sep='\n')
    ret = sheetInterface.append_values(SAMPLE_SPREADSHEET_ID, SAMPLE_RANGE_NAME, "USER_ENTERED", filtered)
    print(ret)
else:
    print("no row to update")