import datetime as dt
import json
import os
from datetime import datetime

import bs4
import numpy as np
import pandas as pd
import requests
import yfinance as yf
from pandas_datareader import data as pdr

yf.pdr_override()

info_types = ["info", "options", "dividends",
              "mutualfund_holders", "institutional_holders",
              "major_holders", "calendar", "actions", "splits"]


def date_parse(d):
    return datetime.strptime(d, "%Y-%m-%d")


def load_price_history(symbol, start_date=dt.date(2000, 1, 1), end_date=dt.date.today(), market="us",
                       reload=True):
    start_date = np.datetime64(start_date)
    end_date = np.datetime64(end_date)

    today = dt.datetime.now()

    symbol_filename = "-".join(symbol.split("."))

    file_path = f"data/{market}/price_history/{symbol_filename}.csv"
    if reload:
        if os.path.isfile(file_path):  # download only data from one day after latest date in csv
            df_old = pd.read_csv(file_path, index_col=0, parse_dates=True)

            if len(df_old) == 0:
                df = pdr.get_data_yahoo(symbol, start_date, end_date)
                df.reset_index(level=0).to_csv(file_path, index=False, date_format="%Y-%m-%d")

                return df

            oldest_saved_date = df_old.index[0]
            lastest_saved_date = df_old.index[-1]

            try:
                if start_date < oldest_saved_date:
                    df_older = pdr.get_data_yahoo(symbol, start_date, oldest_saved_date - dt.timedelta(days=1))
                    df_older = df_older[(df_older.index >= start_date) & (df_older.index < oldest_saved_date)]
                    df_old = pd.concat([df_older, df_old])

                df_old = df_old[df_old.index < lastest_saved_date]
                df_new = pdr.get_data_yahoo(symbol, lastest_saved_date, today)
                df_new = df_new[df_new.index >= lastest_saved_date]
                df_new = df_new[~df_new.index.duplicated(keep="first")]
                df = pd.concat([df_old, df_new])

                df.reset_index(level=0).to_csv(file_path, index=False, date_format="%Y-%m-%d")

                return df[(df.index >= start_date) & (df.index <= end_date)]
            except TypeError:
                df = pdr.get_data_yahoo(symbol, start_date, end_date)
                df.reset_index(level=0).to_csv(file_path, index=False, date_format="%Y-%m-%d")

                return df

        else:  # no csv exits
            df = pdr.get_data_yahoo(symbol, start_date, end_date)

            directory = f"data/{market}/price_history"
            if not os.path.exists(directory):
                os.makedirs(directory)
            df.reset_index(level=0).to_csv(file_path, index=False, date_format="%Y-%m-%d")

            return df
    else:  # don't reload
        df = pd.read_csv(file_path, index_col=0, parse_dates=True)
        return df[
            (pd.to_datetime(df.index).floor('D') >= start_date) & (pd.to_datetime(df.index).floor('D') <= end_date)]


def reload_all(symbols, start_date=dt.datetime(2000, 1, 1), end_date=dt.datetime.now()):
    symbols = remove_duplicates(symbols)
    for symbol in symbols:
        df = load_price_history(symbol, start_date, end_date)
        print(df.index[0], df.index[-1])


def reload_sandp500():
    symbols = load_sandp500_symbols()
    print(symbols)
    reload_all(load_sandp500_symbols())


def load_ticker_info(symbol, market="us", type_str="info", reload=False):
    if type_str in ["info", "isin", "options"]:
        extn = "json"
    else:
        extn = "csv"

    symbol_filename = "-".join(symbol.split("."))

    file_path = f"data/{market}/info/{type_str}/{symbol_filename}.{extn}"

    if reload or not os.path.isfile(file_path):
        print(f"Downloading {type_str} for {symbol}..")

        ticker = yf.Ticker(symbol)

        if type_str in ["info", "options"]:
            extn = "json"
            file_path = f"data/{market}/info/{type_str}/{symbol}.{extn}"
            if type_str == "info":
                try:
                    info_dict = ticker.info
                except ValueError:
                    print(f"Error, no info found for {symbol}.")
                    return
            else:
                info_dict = ticker.options

            with open(file_path, "w") as f:
                json.dump(info_dict, f, indent=4)

            return info_dict
        else:
            extn = "csv"
            file_path = f"data/{market}/info/{type_str}/{symbol}.{extn}"

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
                print(f"Error - info type \"{type_str}\" is not a valid option.")
                return

            info_df.to_csv(file_path)
            return info_df

    else:
        if extn == "json":
            with open(file_path, "r") as f:
                return json.load(f)
        elif extn == "csv":
            return pd.read_csv(file_path)


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

        with open("data/us/symbols.txt", "w") as f:
            for symbol in symbols:
                f.write(symbol + "\n")

        return symbols
    else:
        with open("data/us/symbols.txt", "r") as f:
            return [line.strip() for line in f]


def remove_duplicates(seq):
    seen = set()
    seen_add = seen.add
    return [x for x in seq if not (x in seen or seen_add(x))]


def all_prices_df(market="us", reload=True):
    if reload:
        symbols = load_sandp500_symbols()

        all_df = pd.DataFrame()

        for symbol in symbols:
            df = load_price_history(symbol, reload=False)[["Adj Close"]].rename({"Adj Close": symbol}, axis=1)
            all_df = all_df.join(df, how="outer")

        all_df.reset_index(level=0).to_csv(f"data/{market}/price_history/all/all.csv", index=False,
                                           date_format="%Y-%m-%d")

        return all_df

    else:
        return pd.read_csv(f"data/{market}/price_history/all/all.csv", index_col=0, parse_dates=True)


def weekly(df):
    return df.resample("W", label="left").agg({"Open": "first", "High": "max", "Low": "min",
                                               "Close": "last", "Adj Close": "last", "Volume": "sum"})


def monthly(df):
    return df.resample("M", label="left").agg({"Open": "first", "High": "max", "Low": "min",
                                               "Close": "last", "Adj Close": "last", "Volume": "sum"})
