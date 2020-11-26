#!/usr/bin/python
import datetime as dt
import os
import sys
import pickle
from collections import Counter
import matplotlib.pyplot as plt
import pandas as pd
import praw
from nltk.sentiment.vader import SentimentIntensityAnalyzer as SIA
from wordcloud import WordCloud
import numpy as np

import data_loader

os.chdir(sys.path[0])
now = dt.datetime.now()
datetime_file_format = '%Y_%m_%d_%H_%M_%S'
date_hour_file_format = "%Y_%m_%d_%H"
date_file_format = '%Y_%m_%d'

print(now.strftime(datetime_file_format))


def subreddit_stock_sentiment(reload_headlines=True, generate_word_cloud=False, generate_scatter_plot=False):

    with open("data/sentiment/auth.txt", "r") as f:
        lines = f.readlines()
        client_id = lines[0].strip()
        client_secret = lines[1].strip()
        username = lines[2].strip()
        subreddit = lines[3].strip()

    if reload_headlines:

        reddit = praw.Reddit(client_id=client_id,
                             client_secret=client_secret,
                             user_agent=username)

        headlines = set()

        for submission in reddit.subreddit(subreddit).new(limit=None):
            headlines.add(submission.title)

        with open("data/headlines.p", "wb") as f:
            pickle.dump(headlines, f)
    else:
        with open("data/headlines.p", "rb") as f:
            headlines = pickle.load(f)

    with open("data/all_symbols.p", "rb") as f:
        all_symbols = pickle.load(f)

    with open("data/sentiment/words_to_remove.p", "rb") as f:
        words_to_remove = pickle.load(f)

    # more_words = []
    # add_words_to_remove(words_to_remove, more_words)

    sia = SIA()
    results = []
    word_list = []
    chars_to_remove = [",", ".", "(", ")", "/", ":", "\"", "'", "?", "!", "$", "-", "🚀"]

    stripped_headlines = []

    for line in headlines:
        line_stripped = line
        for char in chars_to_remove:
            line_stripped = line_stripped.replace(char, "").lower()
        line_stripped = line_stripped.split(" ")
        stripped_headlines.append(line_stripped)
        word_list += line_stripped

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
                # print(f"{word}  {freq}")

    if generate_word_cloud:
        word_cloud = WordCloud(scale=5, max_words=200, relative_scaling=0.5,
                               normalize_plurals=False).generate_from_frequencies(symbols_dict)
        save_image(word_cloud, f"public_html/finance/res/img/sentiment/word_clouds/{now.strftime(datetime_file_format)}_word_cloud.png")

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
        # print(pol_score["compound"], pol_score["headline"])
        results.append(pol_score)

        sentiment_score = pol_score["compound"]

        if -0.3 < sentiment_score < 0.3:
            continue

        mentioned_stocks = []
        for symbol in symbols_list:
            if symbol in stripped_headlines[i]:
                sentiment_dict[symbol]["sentiment"] += sentiment_score
                sentiment_dict[symbol]["sentiment_frequency"] += 1
                mentioned_stocks.append(symbol)

    #     if sentiment_score > 0:
    #         print(f"{mentioned_stocks} - positive :) - \"{line}\"")
    #     elif sentiment_score < 0:
    #         print(f"{mentioned_stocks} - negative :( - \"{line}\"")

    sentiment_list = list(sentiment_dict.values())

    df = pd.DataFrame.from_records(sentiment_list)

    df.sort_values(by="sentiment", ascending=False, inplace=True)

    df = df[["symbol", "word_frequency", "sentiment"]]

    df = df[df["sentiment"] != 0]

    file_path = f"data/sentiment/{subreddit}_sentiment.csv"

    if os.path.isfile(file_path):
        all_df = pd.read_csv(file_path, parse_dates=True)
    else:
        all_df = pd.DataFrame()

    row_index = len(all_df)

    for i, row in df.iterrows():
        symbol = row["symbol"]

        all_df.loc[row_index, "Date"] = now
        all_df.loc[row_index, f"{symbol}_frequency"] = row["word_frequency"]
        all_df.loc[row_index, f"{symbol}_sentiment"] = row["sentiment"]

    all_df.fillna(0, inplace=True)

    # Plot time series
    date_col = pd.to_datetime(all_df["Date"])
    all_df = all_df.drop("Date", 1)
    all_df.sort_values(all_df.last_valid_index(), ascending=False, axis=1, inplace=True)
    all_df["Date"] = date_col

    if now.hour == 18 and now.minute < 15:
        plt.figure(figsize=(10, 6))

        for col in all_df.columns.values:
            if col.endswith("sentiment"):
                symbol = col.split("_")[0]
                if np.max(all_df[f"{symbol}_sentiment"]) > 0.5:
                    company_name = data_loader.load_ticker_info(symbol)['shortName']
                    label = f"{company_name} ({symbol.upper()})"
                    plt.plot(all_df["Date"], all_df[col], label=label)

        plt.title("Sentiment")
        plt.xlabel("Time")
        plt.ylabel("Sentiment x frequency")
        plt.legend(loc="upper left")
        plt.savefig(f"public_html/finance/res/img/sentiment/timeseries_plots/{now.strftime(datetime_file_format)}_sentiment_timeseries_plot.png", dpi=100)

        plt.close()
        plt.clf()

        # Plot time series (daily)
        all_df.set_index("Date", inplace=True)

        df_daily = all_df.resample('D').mean()

        df_daily.sort_values(df_daily.last_valid_index(), ascending=False, axis=1, inplace=True)

        df_daily.reset_index(level=0, inplace=True)

        plt.figure(figsize=(10, 6))

        for col in df_daily.columns.values:
            if col.endswith("sentiment"):
                symbol = col.split("_")[0]
                if np.max(df_daily[f"{symbol}_sentiment"]) > 0.5:
                    company_name = data_loader.load_ticker_info(symbol)['shortName']
                    label = f"{company_name} ({symbol.upper()})"
                    plt.plot(pd.to_datetime(df_daily["Date"]), df_daily[col], label=label)

        plt.title("Daily sentiment")
        plt.xlabel("Date")
        plt.ylabel("Sentiment x frequency")
        plt.legend(loc="upper left")
        plt.savefig(f"public_html/finance/res/img/sentiment/daily_plots/{now.strftime(date_file_format)}_sentiment_timeseries_plot.png", dpi=100)

        plt.close()
        plt.clf()

        # Plot time series (hourly)
        df_hourly = all_df.resample('H').mean()

        df_hourly.sort_values(df_hourly.last_valid_index(), ascending=False, axis=1, inplace=True)

        df_hourly.reset_index(level=0, inplace=True)

        plt.figure(figsize=(10, 6))

        for col in df_hourly.columns.values:
            if col.endswith("sentiment"):
                symbol = col.split("_")[0]
                if np.max(df_hourly[f"{symbol}_sentiment"]) > 0.5:
                    company_name = data_loader.load_ticker_info(symbol)['shortName']
                    label = f"{company_name} ({symbol.upper()})"
                    plt.plot(pd.to_datetime(df_hourly["Date"]), df_hourly[col], label=label)

        plt.title("Hourly sentiment")
        plt.xlabel("Date")
        plt.ylabel("Sentiment x frequency")
        plt.legend(loc="upper left")
        plt.savefig(f"public_html/finance/res/img/sentiment/hourly_plots/{now.strftime(date_hour_file_format)}_sentiment_timeseries_plot.png", dpi=100)

        plt.close()
        plt.clf()

    else:
        all_df.set_index("Date", inplace=True)

    all_df.reset_index(level=0).to_csv(f"data/sentiment/{subreddit}_sentiment.csv", index=False)

    if generate_scatter_plot:

        plt.figure(figsize=(10, 6))

        df_positive = df[df["sentiment"] >= 0.3]
        df_neutral = df[(df["sentiment"] < 0.3) & (df["sentiment"] > -0.3)]
        df_negative = df[df["sentiment"] <= -0.3]

        plt.scatter(df_positive["word_frequency"], df_positive["sentiment"], marker="o", color="green")
        plt.scatter(df_neutral["word_frequency"], df_neutral["sentiment"], marker="o", color="yellow")
        plt.scatter(df_negative["word_frequency"], df_negative["sentiment"], marker="o", color="red")

        for i, row in df.iterrows():
            company_name = data_loader.load_ticker_info(row['symbol'])['shortName']
            label = f"{company_name} ({row['symbol'].upper()})"

            plt.annotate(label, (row["word_frequency"], row["sentiment"]), fontsize=8)

        plt.xscale('log')
        plt.yscale('log')

        plt.xlabel("frequency")
        plt.ylabel("sentiment score")

        plt.savefig(f"public_html/finance/res/img/sentiment/scatter_plots/{now.strftime(datetime_file_format)}_sentiment_scatter_plot.png", dpi=100)

        plt.close()
        plt.clf()


def add_words_to_remove(words_to_remove, more_words):
    for word in more_words:
        words_to_remove.add(word.lower())

    with open("data/sentiment/words_to_remove.p", "wb") as f:
        pickle.dump(words_to_remove, f)

    return words_to_remove


def save_image(data, filename):
    fig = plt.figure()
    fig.set_size_inches(16, 8)
    ax = plt.Axes(fig, [0., 0., 1., 1.])
    ax.set_axis_off()
    fig.add_axes(ax)
    ax.imshow(data)
    plt.savefig(filename, dpi=100)
    plt.close()
    plt.clf()


if __name__ == "__main__":
    subreddit_stock_sentiment(reload_headlines=True, generate_word_cloud=False, generate_scatter_plot=False)
