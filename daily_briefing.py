#!/usr/bin/env python3
import datetime as dt
import logging
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
date_format = "%d/%m/%Y %H:%M:%S"
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


if __name__ == "__main__":

    logging.basicConfig(filename="sentiment_words.log", filemode="w", format=log_format, datefmt=date_format,
                        level=logging.INFO)

    charts_path = "public_html/finance/res/img/ohlc"

    # WATCHLIST
    files = glob.glob(f'{charts_path}/watchlist/*')
    for f in files:
        os.remove(f)

    watchlist = data_loader.watchlist()

    print("Making watchlist charts...")
    logging.info("Making watchlist charts...")

    for symbol in watchlist:
        ohlc.indicator_chart(symbol, directory="watchlist")

    # REDDIT SENTIMENT
    with open("data/sentiment/auth.txt", "r") as f:
        lines = f.readlines()
        subreddit = lines[3].strip()

    file_path = f"data/sentiment/{subreddit}_sentiment.csv"

    if os.path.isfile(file_path):
        df = pd.read_csv(file_path, index_col=0, parse_dates=True)

        files = glob.glob(f'{charts_path}/reddit_sentiment/*')
        for f in files:
            os.remove(f)

        with open("data/sentiment/top_daily_tickers.txt", "r") as f:
            sentiment_tickers = f.read().split("\n")

        print("Making sentiment charts...")
        logging.info("Making sentiment charts...")

        for i, symbol in enumerate(sentiment_tickers):

            if f"{symbol}_sentiment" in df and f"{symbol}_frequency" in df:
                df_daily = df.resample("D").mean()
                sentiment_value = df_daily[f"{symbol}_sentiment"].iloc[-1]
                frequency_value = df_daily[f"{symbol}_frequency"].iloc[-1]

                ohlc.indicator_chart(symbol, frequency_value=frequency_value, sentiment_value=sentiment_value, prefix=i, directory="reddit_sentiment")

        generate_html.generate_ohlc_html(now)

        print("Success.")
        logging.info("Success.")
