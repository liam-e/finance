#!/usr/bin/env python3
import datetime as dt
import os
import sys
import pandas as pd

import data_loader
import generate_html
import ohlc
import glob

os.chdir(sys.path[0])
now = dt.datetime.now()
datetime_file_format = '%Y_%m_%d_%H_%M_%S'
date_hour_file_format = "%Y_%m_%d_%H"
date_file_format = '%Y_%m_%d'

if __name__ == "__main__":
    with open("data/sentiment/auth.txt", "r") as f:
        lines = f.readlines()
        subreddit = lines[3].strip()

    file_path = f"data/sentiment/{subreddit}_sentiment.csv"

    if os.path.isfile(file_path):
        df = pd.read_csv(file_path, index_col=0, parse_dates=True)

        sentiment_cols = [col for col in df.columns.values if col.endswith("sentiment")]

        df2 = df[sentiment_cols]

        sentiment_symbols = [s.split("_")[0] for s in sentiment_cols]

        df2.columns = sentiment_symbols

        watchlist = data_loader.watchlist()

        charts_path = "public_html/finance/res/img/ohlc"

        files = glob.glob(f'{charts_path}/from_watchlist/*') + glob.glob(f'{charts_path}/reddit_sentiment/*')
        for f in files:
            os.remove(f)

        for symbol in watchlist:
            ohlc.indicator_chart(symbol, directory="from_watchlist")

        for symbol in sentiment_symbols[:2]:
            sentiment_value = df2[symbol].iloc[-1]

            if df2[symbol].iloc[-1] > 0:
                ohlc.indicator_chart(symbol, sentiment_value=sentiment_value, directory="reddit_sentiment")

        generate_html.generate_ohlc_html(now)
