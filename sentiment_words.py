#!/usr/bin/env python3
import datetime as dt
import logging
import os
import pickle
import re
import sys
from collections import Counter
from shutil import copyfile

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import praw
from matplotlib import style
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from wordcloud import WordCloud

import data_loader
import generate_html

os.chdir(sys.path[0])
now = dt.datetime.now()
date_format = '%d/%m/%Y %H:%M:%S'
datetime_file_format = '%Y_%m_%d_%H_%M_%S'
date_hour_file_format = "%Y_%m_%d_%H"
date_file_format = '%Y_%m_%d'
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

regex = re.compile('[^a-zA-Z ]')

style.use("dark_background")

labels_dict = {}


def subreddit_stock_sentiment(debug=False):
    logging.basicConfig(filename="sentiment_words.log", filemode="w", format=log_format, datefmt=date_format, level=logging.INFO)

    with open("data/sentiment/auth.txt", "r") as f:
        lines = f.readlines()
        client_id = lines[0].strip()
        client_secret = lines[1].strip()
        username = lines[2].strip()
        subreddit = lines[3].strip()

    file_path = f"data/sentiment/{subreddit}_sentiment.csv"

    logging.info("Downloading reddit headlines...")

    reddit = praw.Reddit(client_id=client_id,
                         client_secret=client_secret,
                         user_agent=username)

    headlines = set()

    for submission in reddit.subreddit(subreddit).new(limit=None):
        headlines.add(submission.title)

    logging.info("Counting words...")

    with open("data/all_symbols.p", "rb") as f:
        all_symbols = pickle.load(f)

    with open("data/sentiment/words_to_remove.p", "rb") as f:
        words_to_remove = pickle.load(f)

    sia = SentimentIntensityAnalyzer()
    results = []
    word_list = []

    stripped_headlines = []

    for line in headlines:
        line_list = [s.strip() for s in regex.sub('', line).lower().split(" ")]
        stripped_headlines.append(line_list)
        word_list += line_list

    word_freqs = Counter(word_list).most_common()

    symbols_dict = {}
    symbols_list = []

    for word_freq in word_freqs:
        symbol = word_freq[0]
        freq = word_freq[1]

        if symbol not in words_to_remove:
            if freq > 1 and symbol in all_symbols:
                symbols_dict[symbol] = freq
                symbols_list.append(symbol)

    sentiment_dict = {}
    for symbol, frequency in symbols_dict.items():
        symbol_dict = {
            "symbol": symbol,
            "word_frequency": frequency,
            "sentiment": 0,
            "sentiment_frequency": 0
        }
        sentiment_dict[symbol] = symbol_dict

    for i, line in enumerate(headlines):
        pol_score = sia.polarity_scores(line)
        pol_score['headline'] = line
        results.append(pol_score)

        sentiment_score = pol_score["compound"]

        mentioned_stocks = []
        for symbol in symbols_list:
            if symbol in stripped_headlines[i]:
                sentiment_dict[symbol]["sentiment"] += sentiment_score
                sentiment_dict[symbol]["sentiment_frequency"] += 1
                mentioned_stocks.append(symbol)

    sentiment_list = list(sentiment_dict.values())

    new_df = pd.DataFrame.from_records(sentiment_list)

    new_df.sort_values(by="word_frequency", ascending=False, inplace=True)

    new_df["sentiment"] = new_df["sentiment"] / new_df["sentiment_frequency"]

    new_df = new_df[["symbol", "word_frequency", "sentiment"]]

    if os.path.isfile(file_path):
        df = pd.read_csv(file_path, parse_dates=True)
    else:
        df = pd.DataFrame()

    row_index = len(df)

    for i, row in new_df.iterrows():
        symbol = row["symbol"]

        df.loc[row_index, "Date"] = now
        df.loc[row_index, f"{symbol}_frequency"] = row["word_frequency"]
        df.loc[row_index, f"{symbol}_sentiment"] = row["sentiment"]

    df.fillna(0, inplace=True)

    date_col = pd.to_datetime(df["Date"])
    df = df.drop("Date", 1)
    df.sort_values(df.last_valid_index(), ascending=False, axis=1, inplace=True)
    df.index = date_col

    if not debug:
        df.reset_index(level=0).to_csv(f"data/sentiment/{subreddit}_sentiment.csv", index=False)

    generate_html.generate_sentiment_html(now, debug)
    logging.info("Success.")


def add_words_to_remove(more_words):
    with open("data/sentiment/words_to_remove.p", "rb") as f:
        words_to_remove = pickle.load(f)

    for word in more_words:
        words_to_remove.add(word.lower())

    with open("data/sentiment/words_to_remove.p", "wb") as f:
        pickle.dump(words_to_remove, f)


if __name__ == "__main__":
    # add_words_to_remove([])

    subreddit_stock_sentiment(debug=False)
