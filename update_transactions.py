from __future__ import print_function

import os.path
import numpy as np
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import spreadsheet_snippets as xl
import chase_converter as chase

# If modifying these scopes, delete the file token.json.
#SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
# The ID and range of a sample spreadsheet.
SAMPLE_SPREADSHEET_ID = '1R9qD53BIqgJU7es5pIl1CBd4s6_1i6OQQgFFUPk2YYg'
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
    if existing_row[0] == new_row[0] and existing_row[1]==new_row[1] and existing_row[2] == new_row[2]:
        # if Date, Type and Ticker matches
        existing_units=round(float(existing_row[3]),1)
        new_units = round(new_row[3],1)
        existing_price = round(float(existing_row[4].strip('$')),2)
        new_price = float(np.round(new_row[4],2))
        return existing_units == new_units and abs(existing_price-new_price) <=0.011
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

chase_data=chase.get_transactions('sample_transactions.csv')
chase_data.drop('Amount USD', axis=1, inplace=True)
chase_data['Fee']=0
chase_data['StockSplit']=1.0
chase_data['Trade Date'] = chase_data['Trade Date'].dt.strftime('%Y-%m-%d')
chase_data['Quantity'] = abs(chase_data['Quantity'])

filtered = [row for row in chase_data.values.tolist() if data_contains(current_data, row)] 
#existing = [row for row in chase_data.values.tolist() if not data_contains(current_data, row)] 
if len(filtered) >0:
    print("rows to update")
    print(filtered)
    ret = sheetInterface.append_values(SAMPLE_SPREADSHEET_ID, SAMPLE_RANGE_NAME, "USER_ENTERED", filtered)
    print(ret)
else:
    print("no row to update")
