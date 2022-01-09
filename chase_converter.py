import pandas as pd
import re

def div_filter(row):
    return row['Type']=='Dividend'

def get_qty_div(desc):
    m = re.search(' ON (.+?) SHS', desc)
    if m:
        return float(m.group(1))
    m = re.search(' GNS (.+?) SHS', desc)
    if m:
        return m.group(1)
    raise NameError(desc)

def get_divs(df):
    col=['Trade Date', 'Type','Ticker','Amount USD', 'Description']
    df_div = df[df.apply(div_filter,axis=1)][col]
    df_div.Type = df_div.Type.str[0:3]
    df_div['Quantity'] = df_div.Description.apply(get_qty_div).astype(float)
    df_div['Price'] = df_div['Amount USD']/df_div['Quantity']
    return df_div[['Trade Date', 'Type','Ticker','Quantity','Price','Amount USD']]

def xtion_filter(row):
    return row['Type']=='Buy' or row['Type']=='Sell' 

def get_xtions(df):
    col = ['Trade Date', 'Type','Ticker','Price USD','Quantity','Amount USD', 'Description'] 
    df_xtion = df[df.apply(xtion_filter,axis=1)][col]
    df_xtion.rename(columns={'Price USD': 'Price'}, inplace=True)

    return df_xtion[['Trade Date', 'Type','Ticker','Quantity','Price', 'Amount USD']]

def get_transactions(filename):
    df = pd.read_csv(filename,parse_dates=['Trade Date'])

    df_div = get_divs(df)
    df_x = get_xtions(df)

    result = pd.concat([df_div, df_x])
    result.sort_values('Trade Date',ignore_index=True, inplace=True)
    return result
    
if __name__ == '__main__':
    df=get_transactions('sample_transactions.csv')
    print(df)