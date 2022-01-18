import os,glob
from ofxparse import OfxParser
import pandas as pd
cusip_converter = {
    "87281J204" : "TR45HT",
    "06427F314" : "BNYLCG",
    "315911750" : "FXAIX",
    "77954Q403" : "TBCIX",
    "31635V729" : "FSPGX",
    "06427F694" : "BNYSII",
    "74149P762" : "TRRKX"
}

def rename_qfx(qfx_file):
    qfx = OfxParser.parse(open(qfx_file, encoding="latin-1"))
    ed = qfx.account.statement.end_date
    sd = qfx.account.statement.start_date
    
    new_filename = f"EmpowerRetirement_{sd.strftime('%Y-%m-%d')}_to_{ed.strftime('%Y-%m-%d')}"
    new_file = f"{os.path.dirname(qfx_file)}\\{new_filename}.qfx"
    print(new_file)
    os.rename(qfx_file, new_file)


def get_transactions(qfx_file):
    qfx = OfxParser.parse(open(qfx_file, encoding="latin-1"))
    trans=[]
    raw={
        "buymf": [],
        "transfer": [],
        "reinvest": [],
    }
    for t in qfx.account.statement.transactions:
        if t.type == "buymf":
            trans.append([t.tradeDate.strftime("%Y-%m-%d"), "Buy", cusip_converter[t.security],t.units,t.unit_price,t.total])
        elif t.type == "transfer":
            if abs(t.units*t.unit_price) <50:
                print("fee ignored")
                #trans.append([t.tradeDate.strftime("%Y-%m-%d"), "Fee", cusip_converter[t.security],t.units,t.unit_price,t.units*t.unit_price])
            else:
                print(f"Update manually: {cusip_converter[t.security]} : {t.tferaction} : {t.units*t.unit_price}")
        elif t.type == "reinvest" and t.income_type== "DIV":
            trans.append([t.tradeDate.strftime("%Y-%m-%d"), "Div", cusip_converter[t.security],t.units,t.unit_price,t.total])
        else:
            print(t)
        raw[t.type].append(t)
    return trans, raw

def get_all_transactions():
    t_all=[]
    for file in glob.glob(f"G:\My Drive\Bank\EmpowerRetirement\*.qfx"):
        #print(file)
        xtions=get_transactions(file)[0]
        t_all.extend(xtions)
    return t_all
    #df=pd.DataFrame(df_all, columns=["date", "ticker","type", "unit", "unit_price", "total","total2" ])
    #return df[["date", "ticker","type", "unit", "unit_price", "total"]]

