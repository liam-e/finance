import datetime as dt
import json
import os
from datetime import datetime

import bs4
import pandas as pd
import requests
import yfinance as yf
from pandas_datareader import data as pdr

yf.pdr_override()

start_date = dt.datetime(2017, 12, 1)
end_date = dt.datetime.now()

info_types = ["info", "options", "dividends",
              "mutualfund_holders", "institutional_holders",
              "major_holders", "calendar", "actions", "splits"]


def date_parse(d):
    return datetime.strptime(d, "%Y-%m-%d")


def load_sandp500_symbols(reload=False):
    if reload:
        symbols = []
        with requests.get("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies") as resp:
            soup = bs4.BeautifulSoup(resp.content, "lxml")
            for table in soup.find_all("table", {"class": "wikitable"}):
                for tr in table.find("tbody").find_all("tr"):
                    td = tr.find("td")
                    if td:
                        symbols.append("-".join(td.text.strip().split(".")).lower())
                break

        with open("data/sandp500/symbols.txt", "w") as f:
            for symbol in symbols:
                f.write(symbol + "\n")

        return symbols
    else:
        with open("data/sandp500/symbols.txt", "r") as f:
            return [line.strip() for line in f]


def load_price_history(symbol, reload=False):
    file_path = f"data/sandp500/price_history/{symbol}.csv"
    if reload or not os.path.isfile(file_path):
        try:
            print(f"Downloading price history for {symbol}..")

            df = pdr.get_data_yahoo(symbol, start_date, end_date)
            if len(df) == 0:
                raise ValueError

            df.reset_index(level=0).to_csv(file_path, index=False, date_format="%Y-%m-%d")

            return df
        except ValueError:
            return None
    else:
        return pd.read_csv(file_path, index_col=0, parse_dates=True)


def load_ticker_info(symbol, type_str, reload=False):
    if type_str in ["info", "isin", "options"]:
        extn = "json"
    else:
        extn = "csv"

    file_path = f"data/sandp500/info/{type_str}/{symbol}.{extn}"

    if reload or not os.path.isfile(file_path):
        print(f"Downloading {type_str} for {symbol}..")

        ticker = yf.Ticker(symbol)

        if type_str in ["info", "options"]:
            extn = "json"
            file_path = f"data/sandp500/info/{type_str}/{symbol}.{extn}"
            if type_str == "info":
                info_dict = ticker.info
            elif type_str == "isin":
                info_dict = ticker.isin
            elif type_str == "options":
                info_dict = ticker.options
            else:
                print("error")
                return

            with open(file_path, "w") as f:
                json.dump(info_dict, f, indent=4)

            return info_dict
        else:
            extn = "csv"
            file_path = f"data/sandp500/info/{type_str}/{symbol}.{extn}"

            if type_str == "actions":
                info_df = ticker.actions
            elif type_str == "calendar":
                info_df = ticker.calendar
            elif type_str == "dividends":
                info_df = ticker.dividends
            elif type_str == "institutional_holders":
                info_df = ticker.institutional_holders
            elif type_str == "major_holders":
                info_df = ticker.major_holders
            elif type_str == "mutualfund_holders":
                info_df = ticker.mutualfund_holders
            elif type_str == "splits":
                info_df = ticker.splits
            else:
                print("error")
                return

            info_df.to_csv(file_path)
            return info_df

    else:
        if extn == "json":
            with open(file_path, "r") as f:
                return json.load(f)
        elif extn == "csv":
            return pd.read_csv(file_path)
