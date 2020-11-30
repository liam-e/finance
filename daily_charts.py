#!/usr/bin/env python3
import datetime as dt
import glob
import os
import sys
import traceback
from time import time

import pandas as pd

import data_loader
import finance_logger
import generate_html
import ohlc

os.chdir(sys.path[0])
now = dt.datetime.now()
datetime_file_format = '%Y_%m_%d_%H_%M_%S'
date_hour_file_format = "%Y_%m_%d_%H"
date_file_format = '%Y_%m_%d'
date_format = "%d/%m/%Y %H:%M:%S"
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def generate_daily_charts(debug=False):
    charts_path = "public_html/finance/res/img/ohlc"

    # WATCHLIST
    files = glob.glob(f'{charts_path}/watchlist/*')
    for f in files:
        os.remove(f)

    watchlist = data_loader.watchlist()

    if debug:
        watchlist = watchlist[:2]

    for symbol in watchlist:
        ohlc.indicator_chart(symbol, directory="watchlist")

    # REDDIT SENTIMENT
    file_path = f"data/sentiment/reddit_sentiment.csv"

    if os.path.isfile(file_path):
        df = pd.read_csv(file_path, index_col=0, parse_dates=True)

        files = glob.glob(f'{charts_path}/reddit_sentiment/*')
        for f in files:
            os.remove(f)

        with open("data/sentiment/top_daily_tickers.txt", "r") as f:
            sentiment_tickers = f.read().split("\n")

        if debug:
            sentiment_tickers = sentiment_tickers[:2]

        for i, symbol in enumerate(sentiment_tickers):

            if f"{symbol}_sentiment" in df and f"{symbol}_frequency" in df:
                df_daily = df.resample("D").mean()
                sentiment_value = df_daily[f"{symbol}_sentiment"].iloc[-1]
                frequency_value = df_daily[f"{symbol}_frequency"].iloc[-1]

                ohlc.indicator_chart(symbol, frequency_value=frequency_value, sentiment_value=sentiment_value, prefix=i,
                                     directory="reddit_sentiment")

        generate_html.generate_ohlc_html()

    generate_html.generate_screener_html(debug=debug)


def main(debug=False):
    script_name = os.path.basename(__file__)
    start = time()
    finance_logger.setup_log_script(script_name)

    try:
        generate_daily_charts(debug=debug)
        finance_logger.append_log("success", script_name=script_name)
        finance_logger.log_time_taken(time() - start, script_name)
    except:
        traceback.print_exc()
        finance_logger.append_log("failure", script_name=script_name)


if __name__ == "__main__":
    main(debug=False)
