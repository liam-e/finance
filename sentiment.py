#!/usr/bin/env python3
import datetime as dt
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
from nltk.sentiment.vader import SentimentIntensityAnalyzer as SIA
from wordcloud import WordCloud

import data_loader
import generate_html

os.chdir(sys.path[0])
now = dt.datetime.now()
datetime_file_format = '%Y_%m_%d_%H_%M_%S'
date_hour_file_format = "%Y_%m_%d_%H"
date_file_format = '%Y_%m_%d'

regex = re.compile('[^a-zA-Z ]')

style.use("dark_background")

labels_dict = {}


def subreddit_stock_sentiment(generate_word_cloud=False, generate_scatter_plot=True, debug=False, dpi=150):
    with open("data/sentiment/auth.txt", "r") as f:
        lines = f.readlines()
        client_id = lines[0].strip()
        client_secret = lines[1].strip()
        username = lines[2].strip()
        subreddit = lines[3].strip()

    if not debug:
        print("Downloading reddit headlines...")

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

    print("Counting words...")

    with open("data/all_symbols.p", "rb") as f:
        all_symbols = pickle.load(f)

    with open("data/sentiment/words_to_remove.p", "rb") as f:
        words_to_remove = pickle.load(f)

    # more_words = []
    # add_words_to_remove(words_to_remove, more_words)

    print("k" in words_to_remove)
    print("b" in words_to_remove)

    sia = SIA()
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

    if generate_word_cloud:
        word_cloud = WordCloud(scale=5, max_words=200, relative_scaling=0.5,
                               normalize_plurals=False).generate_from_frequencies(symbols_dict)
        save_image(word_cloud,
                   f"public_html/finance/res/img/sentiment/word_clouds/{now.strftime(datetime_file_format)}_word_cloud.png",
                   dpi=dpi)

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

        if -0.3 < sentiment_score < 0.3:
            continue

        mentioned_stocks = []
        for symbol in symbols_list:
            if symbol in stripped_headlines[i]:
                sentiment_dict[symbol]["sentiment"] += sentiment_score
                sentiment_dict[symbol]["sentiment_frequency"] += 1
                mentioned_stocks.append(symbol)

    sentiment_list = list(sentiment_dict.values())

    df = pd.DataFrame.from_records(sentiment_list)

    df.sort_values(by="sentiment", ascending=False, inplace=True)

    df = df[["symbol", "word_frequency", "sentiment"]]

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
    all_df.index = date_col

    sentiment_cols = [col for col in all_df.columns.values if col.endswith("sentiment")]
    df_plot = all_df[sentiment_cols]
    df_plot.columns = [s.split("_")[0] for s in sentiment_cols]

    if debug or (now.hour in [0, 6, 12, 18] and now.minute < 30):
        print("Making charts...")

        # ----------- TIMESERIES CHART -----------
        plot_sentiment(df_plot, "timeseries")

        # ----------- HOURLY CHART -----------
        plot_sentiment(df_plot, "hourly")

        # ----------- DAILY CHART -----------
        plot_sentiment(df_plot, "daily")

    all_df.reset_index(level=0).to_csv(f"data/sentiment/{subreddit}_sentiment.csv", index=False)

    if generate_scatter_plot:

        plt.figure(figsize=(20, 10), dpi=dpi)

        df = df[df["sentiment"] != 0]

        df["sentiment"] = df["sentiment"] / df["word_frequency"]

        df["log_word_frequency"] = np.log(df["word_frequency"])

        df_positive = df[df["sentiment"] >= 0.1]
        df_neutral = df[(df["sentiment"] < 0.1) & (df["sentiment"] > -0.1)]
        df_negative = df[df["sentiment"] <= -0.1]

        plt.scatter(df_positive["log_word_frequency"], df_positive["sentiment"], marker="o", color="green")
        plt.scatter(df_neutral["log_word_frequency"], df_neutral["sentiment"], marker="o", color="gold")
        plt.scatter(df_negative["log_word_frequency"], df_negative["sentiment"], marker="o", color="red")

        for i, row in df.iterrows():
            plt.annotate(stock_label(row['symbol'], reload=(not debug)), (row["log_word_frequency"], row["sentiment"]),
                         fontsize=8)

        plt.title("Reddit stock sentiment - scatter plot")
        # plt.xscale('log')
        # plt.yscale('log')
        plt.xlabel("log(frequency)")
        plt.ylabel("sentiment score")
        file_path_scatter = "public_html/finance/res/img/sentiment/scatter_plots"
        plt.savefig(f"{file_path_scatter}/{now.strftime(datetime_file_format)}_sentiment_scatter_plot.png", dpi=dpi)
        copyfile(f"{file_path_scatter}/{now.strftime(datetime_file_format)}_sentiment_scatter_plot.png",
                 f"{file_path_scatter}/current_sentiment_scatter_plot.png")

        plt.close()
        plt.clf()

    generate_html.generate_sentiment_html(now)
    print("Finished.")


def plot_sentiment(df, plot_type, dpi=150, max_count=10):
    if df is None or len(df) == 0:
        return

    if plot_type == "daily":
        df_plot = df.resample('D').mean()
        df_plot = df_plot[df_plot.index >= df_plot.index[-1] - dt.timedelta(days=30)]
    elif plot_type == "hourly":
        df_plot = df.resample('H').mean()
        df_plot = df_plot[df_plot.index >= df_plot.index[-1] - dt.timedelta(days=7)]
    elif plot_type == "timeseries":
        df_plot = df
        df_plot = df_plot[df_plot.index >= df_plot.index[-1] - dt.timedelta(days=7)]
    else:
        print(f"{plot_type} not supported.")
        return

    if len(df) == 0:
        print("Dataframe is empty.")
        return

    df_plot = df_plot.sort_values(df_plot.last_valid_index(), ascending=False, axis=1)

    plt.figure(figsize=(20, 10), dpi=dpi)

    count = 0

    for symbol in df_plot.columns.values:
        plt.plot(pd.to_datetime(df_plot.index), np.log(df_plot[symbol] - np.min(df_plot[symbol]) + 1),
                 label=stock_label(symbol))
        count += 1
        if count >= max_count:
            break

    plt.title(f"{plot_type[0].upper()}{plot_type[1:]}")
    plt.xlabel("Date")
    plt.ylabel("log(sentiment x frequency) - higher is better")
    plt.legend(loc="upper left")
    file_path_hourly = f"public_html/finance/res/img/sentiment/{plot_type}_plots"
    file_name = f"_sentiment_{plot_type}_plot.png"
    plt.savefig(f"{file_path_hourly}/{now.strftime(date_hour_file_format)}{file_name}", dpi=dpi)
    copyfile(f"{file_path_hourly}/{now.strftime(date_hour_file_format)}{file_name}",
             f"{file_path_hourly}/current{file_name}")

    plt.close()
    plt.clf()


def stock_label(symbol, reload=True):
    if symbol in labels_dict:
        return labels_dict[symbol]
    else:
        df = data_loader.load_price_history(symbol, dt.date.today() - dt.timedelta(days=5), dt.date.today(),
                                            reload=reload)
        if df is not None and len(df) >= 2:
            old_close = df.iloc[-2]["Adj Close"]
            new_close = df.iloc[-1]["Adj Close"]
            percent_change = (new_close - old_close) / old_close * 100

            if percent_change > 0:
                percent_change_str = f" +{percent_change:.2f}%"
            else:
                percent_change_str = f" {percent_change:.2f}%"

        else:
            percent_change_str = ""

        info = data_loader.load_ticker_info(symbol, reload=False)
        if info is not None and 'shortName' in info:
            company_name_str = f"{data_loader.load_ticker_info(symbol)['shortName']} "
        else:
            company_name_str = ""

        label = f"{company_name_str}({symbol.upper()}){percent_change_str}"

        labels_dict[symbol] = label
        return label


def add_words_to_remove(words_to_remove, more_words):
    for word in more_words:
        words_to_remove.add(word.lower())

    with open("data/sentiment/words_to_remove.p", "wb") as f:
        pickle.dump(words_to_remove, f)

    return words_to_remove


def save_image(data, filename, dpi=150):
    fig = plt.figure()
    fig.set_size_inches(16, 8)
    ax = plt.Axes(fig, [0., 0., 1., 1.])
    ax.set_axis_off()
    fig.add_axes(ax)
    ax.imshow(data)
    plt.savefig(filename, dpi=dpi)
    plt.close()
    plt.clf()


if __name__ == "__main__":
    subreddit_stock_sentiment(debug=False, generate_scatter_plot=True)
