#!/usr/bin/env python3
import datetime as dt
import os
import pickle
import re
import sys
import traceback
from collections import Counter
from time import time

import pandas as pd
import praw
from matplotlib import style
from nltk.sentiment.vader import SentimentIntensityAnalyzer

import finance_logger

os.chdir(sys.path[0])
now = dt.datetime.now()
date_format = '%d/%m/%Y %H:%M:%S'
datetime_file_format = '%Y_%m_%d_%H_%M_%S'
date_hour_file_format = "%Y_%m_%d_%H"
date_file_format = '%Y_%m_%d'
regex = re.compile('[^a-zA-Z ]')
style.use("dark_background")
labels_dict = {}
script_name = os.path.basename(__file__)
words_blacklist_path = "data/sentiment/words_blacklist.txt"


def analyse_sentiment(debug=False):
    df_file_path = f"data/sentiment/reddit_sentiment.csv"

    headlines_file_path = "data/sentiment/reddit_headlines.p"

    if not debug or not os.path.isfile(headlines_file_path):
        # DOWNLOAD REDDIT HEADLINES
        with open("data/sentiment/auth.txt", "r") as f:
            auth_list = f.read().split("\n")
            client_id = auth_list[0]
            client_secret = auth_list[1]
            username = auth_list[2]
            subreddit = auth_list[3]

        reddit = praw.Reddit(client_id=client_id,
                             client_secret=client_secret,
                             user_agent=username)

        headlines = set()

        for submission in reddit.subreddit(subreddit).new(limit=None):
            headlines.add(submission.title)

        with open(headlines_file_path, "wb") as f:
            pickle.dump(headlines, f)

    else:
        with open(headlines_file_path, "rb") as f:
            headlines = pickle.load(f)

    finance_logger.append_log(f"number of headlines = {len(headlines)}", script_name=script_name)

    # REMOVE WORDS THAT AREN'T TICKERS
    with open("data/all_symbols.p", "rb") as f:
        all_symbols = pickle.load(f)

    with open(words_blacklist_path, "r") as f:
        words_blacklist = set(f.read().split("\n"))

    word_list = []

    ticker_headlines = []
    stripped_headlines = []

    for line in headlines:
        line_list = [s for s in [s.strip() for s in regex.sub('', line).split(" ")] if
                     s.isupper() and s in all_symbols and s not in words_blacklist]
        if line_list:
            # if "" in line_list:
            #     print(line)
            line_set = set(line_list)
            stripped_headlines.append(line_set)
            word_list += line_list
            ticker_headlines.append(line)

    ticker_count = len(word_list)

    finance_logger.append_log(f"number of times tickers are mentioned = {ticker_count}", script_name=script_name)

    word_freqs = Counter(word_list).most_common()

    sentiment_dict = {}
    for word_freq in word_freqs:
        symbol = word_freq[0]
        if word_freq[1] > 1:
            sentiment_dict[symbol] = {
                "symbol": symbol,
                "frequency": 0,
                "sentiment": 0,
            }

    symbols_set = set(sentiment_dict.keys())

    # ANALYSE TICKER SENTIMENT
    sia = SentimentIntensityAnalyzer()

    for i, line in enumerate(ticker_headlines):
        pol_score = sia.polarity_scores(line)
        sentiment_score = pol_score["compound"]
        if -0.3 < sentiment_score < 0.3:
            continue
        pol_score['headline'] = line
        for symbol in symbols_set:
            if symbol in stripped_headlines[i]:
                sentiment_dict[symbol]["sentiment"] += sentiment_score
                sentiment_dict[symbol]["frequency"] += 1

    if os.path.isfile(df_file_path):
        df = pd.read_csv(df_file_path, parse_dates=True)
    else:
        df = pd.DataFrame()

    row_index = len(df)

    df.loc[row_index, "Date"] = now

    labels_to_drop = []
    for column in df.columns.values:
        if column.split("_")[0] in words_blacklist:
            labels_to_drop.append(column)

    df.drop(labels=labels_to_drop, axis=1, inplace=True)

    for entry in sentiment_dict.values():
        if entry["frequency"] < 1:
            continue
        symbol = entry["symbol"]
        df.loc[row_index, f"{symbol}_frequency"] = entry["frequency"] / ticker_count  # changed to proportional
        df.loc[row_index, f"{symbol}_sentiment"] = entry["sentiment"] / entry["frequency"]

    date_col = df["Date"]
    df = df.drop("Date", 1)
    df.sort_values(df.last_valid_index(), ascending=False, axis=1, inplace=True)
    df.insert(0, "Date", date_col)

    if not debug:
        df.to_csv(f"data/sentiment/reddit_sentiment.csv", index=False)


def main(debug=False):
    start = time()
    finance_logger.setup_log_script(script_name)

    try:
        analyse_sentiment(debug=debug)
        finance_logger.append_log("success", script_name=script_name)
        finance_logger.log_time_taken(time() - start, script_name)
    except:
        traceback.print_exc()
        finance_logger.append_log("failure", script_name=script_name)


if __name__ == "__main__":
    main(debug=False)
