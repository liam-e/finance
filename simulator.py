import datetime as dt
import os

import numpy as np
import yfinance as yf
from pandas_datareader import data as pdr

# pd.options.mode.chained_assignment = None

yf.pdr_override()

start = dt.datetime(2020, 5, 1)
now = dt.datetime.now()

info_types = ["info", "options", "dividends",
              "mutualfund_holders", "institutional_holders",
              "major_holders", "calendar", "actions", "splits"]


def date_parse(d):
    return dt.datetime.strptime(d, '%Y-%m-%d')


def simulate_ema_strategy(df, symbol, reload=False):
    file_path = f"data/sandp500/ema_sim/{start.strftime('%Y-%m-%d')}/{symbol}.csv"

    if reload or not os.path.isfile(file_path):
        df = pdr.get_data_yahoo(symbol, start, now)

        df.reset_index(level=0, inplace=True)

        df.to_csv(file_path, index=False, date_format="%Y-%m-%d")

    if len(df) == 0:
        return np.nan

    smas_min = [3, 5, 8, 10, 12, 15]
    smas_max = [30, 35, 40, 45, 50, 60]
    smas_used = smas_min + smas_max
    len_cols = len(df.columns)

    for sma in smas_used:
        df[f"ema_{sma}"] = np.round(df.loc[:, "Adj Close"].rolling(window=sma).mean(), 2)
    pos = 0
    num = 0
    percent_change = []
    bp = 0
    for i in range(len(df)):
        c_min = np.min(df.iloc[i, len_cols:len_cols + len(smas_min)])
        c_max = np.max(df.iloc[i, len_cols + len(smas_min):len_cols + len(smas_min) + len(smas_max)])
        close = df["Adj Close"].iloc[i]
        if c_min > c_max:
            if pos == 0:
                bp = close
                pos = 1
        elif c_min < c_max:
            if pos == 1:
                pos = 0
                sp = close
                pc = (sp / bp - 1) * 100
                percent_change.append(pc)

        if num >= len(df) and pos == 1:
            pos = 0
            sp = close
            pc = (sp / bp - 1) * 100
            percent_change.append(pc)

        num += 1
    gains = 0
    num_gains = 0
    losses = 0
    num_losses = 0
    total_return = 1
    for i in percent_change:
        if i > 0:
            gains += i
            num_gains += 1
        else:
            losses += i
            num_losses += 1
        total_return = total_return * ((i / 100) + 1)

    total_return = round((total_return - 1) * 100, 2)

    return total_return
