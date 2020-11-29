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


def analyse_sentiment(debug=False):
    file_path = f"data/sentiment/reddit_sentiment.csv"

    if not debug:
        # DOWNLOAD REDDIT HEADLINES
        with open("data/sentiment/auth.txt", "r") as f:
            auth_list = f.read().split("\n")
            client_id, client_secret, username, subreddit = auth_list

        reddit = praw.Reddit(client_id=client_id,
                             client_secret=client_secret,
                             user_agent=username)

        headlines = set()

        for submission in reddit.subreddit("wallstreetbets").new(limit=None):
            headlines.add(submission.title)

        with open("data/sentiment/reddit_headlines.p", "wb") as f:
            pickle.dump(headlines, f)

    else:
        with open("data/sentiment/reddit_headlines.p", "rb") as f:
            headlines = pickle.load(f)

    # REMOVE WORDS THAT AREN'T TICKERS
    with open("data/all_symbols.p", "rb") as f:
        all_symbols = pickle.load(f)

    # add_words_to_remove([])

    with open("data/sentiment/words_to_remove.p", "rb") as f:
        words_to_remove = pickle.load(f)

    word_list = []

    ticker_headlines = []
    stripped_headlines = []

    for line in headlines:
        line_list = [s for s in [s.strip() for s in regex.sub('', line).split(" ")] if
                     s.isupper() and s in all_symbols and s not in words_to_remove]
        if line_list:
            line_set = set(line_list)
            stripped_headlines.append(line_set)
            word_list += line_list
            ticker_headlines.append(line)

    word_freqs = Counter(word_list).most_common()

    sentiment_dict = {}
    for word_freq in word_freqs:
        symbol = word_freq[0]
        if word_freq[1] > 1:
            sentiment_dict[symbol] = {
                "symbol": symbol,
                "frequency": word_freq[1],
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

    if os.path.isfile(file_path):
        df = pd.read_csv(file_path, parse_dates=True)
    else:
        df = pd.DataFrame()

    row_index = len(df)

    df.loc[row_index, "Date"] = now

    for entry in sentiment_dict.values():
        symbol = entry["symbol"]
        df.loc[row_index, f"{symbol}_frequency"] = entry["frequency"]
        df.loc[row_index, f"{symbol}_sentiment"] = entry["sentiment"] / entry["frequency"]

    date_col = df["Date"]
    df = df.drop("Date", 1)
    df.sort_values(df.last_valid_index(), ascending=False, axis=1, inplace=True)
    df.insert(0, "Date", date_col)

    if not debug:
        df.to_csv(f"data/sentiment/reddit_sentiment.csv", index=False)


def add_words_to_remove(more_words):
    with open("data/sentiment/words_to_remove.p", "rb") as f:
        words_to_remove = pickle.load(f)

    for word in more_words:
        words_to_remove.add(word.lower())

    with open("data/sentiment/words_to_remove.p", "wb") as f:
        pickle.dump(words_to_remove, f)


def main(debug=False):
    script_name = os.path.basename(__file__)
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

