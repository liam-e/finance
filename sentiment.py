#!/usr/bin/python
import datetime as dt
import os
import sys
import pickle
from collections import Counter
from shutil import copyfile
import matplotlib.pyplot as plt
import pandas as pd
import praw
from nltk.sentiment.vader import SentimentIntensityAnalyzer as SIA
from wordcloud import WordCloud
import numpy as np
import re

import data_loader

os.chdir(sys.path[0])
now = dt.datetime.now()
datetime_file_format = '%Y_%m_%d_%H_%M_%S'
date_hour_file_format = "%Y_%m_%d_%H"
date_file_format = '%Y_%m_%d'

regex = re.compile('[^a-zA-Z ]')


def subreddit_stock_sentiment(reload_headlines=True, generate_word_cloud=False, generate_scatter_plot=False, debug=False, dpi=150):

    with open("data/sentiment/auth.txt", "r") as f:
        lines = f.readlines()
        client_id = lines[0].strip()
        client_secret = lines[1].strip()
        username = lines[2].strip()
        subreddit = lines[3].strip()

    if reload_headlines:
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

    sia = SIA()
    results = []
    word_list = []

    stripped_headlines = []

    for line in headlines:
        line_list = regex.sub('', line).lower().split(" ")
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
                # print(f"{word}  {freq}")

    if generate_word_cloud:
        word_cloud = WordCloud(scale=5, max_words=200, relative_scaling=0.5,
                               normalize_plurals=False).generate_from_frequencies(symbols_dict)
        save_image(word_cloud, f"public_html/finance/res/img/sentiment/word_clouds/{now.strftime(datetime_file_format)}_word_cloud.png", dpi=dpi)

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

    # pprint(results)

    #     if sentiment_score > 0:
    #         print(f"{mentioned_stocks} - positive :) - \"{line}\"")
    #     elif sentiment_score < 0:
    #         print(f"{mentioned_stocks} - negative :( - \"{line}\"")

    sentiment_list = list(sentiment_dict.values())

    df = pd.DataFrame.from_records(sentiment_list)

    df.sort_values(by="sentiment", ascending=False, inplace=True)

    df = df[["symbol", "word_frequency", "sentiment"]]

    # df = df[df["sentiment"] != 0]

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

    if debug or (now.hour in [0, 6, 12, 18] and now.minute < 30):
        print("Making charts...")
        # ----------- TIMESERIES CHART -----------
        plt.figure(figsize=(12, 8), dpi=dpi)

        for col in all_df.columns.values:
            if col.endswith("sentiment"):
                symbol = col.split("_")[0]
                if np.max(all_df[f"{symbol}_sentiment"]) > 0.5:
                    plt.plot(all_df["Date"], all_df[col], label=stock_label(symbol))

        plt.title("Sentiment")
        plt.xlabel("Time")
        plt.ylabel("sentiment x frequency")
        plt.legend(loc="upper left")
        file_path_timeseries = "public_html/finance/res/img/sentiment/timeseries_plots"
        plt.savefig(f"{file_path_timeseries}/{now.strftime(datetime_file_format)}_sentiment_timeseries_plot.png")
        copyfile(f"{file_path_timeseries}/{now.strftime(datetime_file_format)}_sentiment_timeseries_plot.png",
                 f"{file_path_timeseries}/current_sentiment_timeseries_plot.png")
        plt.close()
        plt.clf()

        # ----------- DAILY CHART -----------
        all_df.set_index("Date", inplace=True)

        df_daily = all_df.resample('D').mean()

        df_daily.sort_values(df_daily.last_valid_index(), ascending=False, axis=1, inplace=True)

        df_daily.reset_index(level=0, inplace=True)

        plt.figure(figsize=(12, 8), dpi=dpi)

        for col in df_daily.columns.values:
            if col.endswith("sentiment"):
                symbol = col.split("_")[0]
                if np.max(df_daily[f"{symbol}_sentiment"]) > 0.5:
                    company_name = data_loader.load_ticker_info(symbol)['shortName']
                    label = f"{company_name} ({symbol.upper()})"
                    plt.plot(pd.to_datetime(df_daily["Date"]), df_daily[col], label=label)

        plt.title("Daily sentiment")
        plt.xlabel("Date")
        plt.ylabel("sentiment x frequency")
        plt.legend(loc="upper left")
        file_path_daily = "public_html/finance/res/img/sentiment/daily_plots"
        plt.savefig(f"{file_path_daily}/{now.strftime(date_file_format)}_sentiment_daily_plot.png")
        copyfile(f"{file_path_daily}/{now.strftime(date_file_format)}_sentiment_daily_plot.png",
                 f"{file_path_daily}/current_sentiment_daily_plot.png")
        plt.close()
        plt.clf()

        # ----------- HOURLY CHART -----------
        df_hourly = all_df.resample('H').mean()

        df_hourly.sort_values(df_hourly.last_valid_index(), ascending=False, axis=1, inplace=True)

        df_hourly.reset_index(level=0, inplace=True)

        plt.figure(figsize=(12, 8), dpi=dpi)

        for col in df_hourly.columns.values:
            if col.endswith("sentiment"):
                symbol = col.split("_")[0]
                if np.max(df_hourly[f"{symbol}_sentiment"]) > 0.5:
                    company_name = data_loader.load_ticker_info(symbol)['shortName']
                    label = f"{company_name} ({symbol.upper()})"
                    plt.plot(pd.to_datetime(df_hourly["Date"]), df_hourly[col], label=label)
        
        plt.title("Hourly sentiment")
        plt.xlabel("Date")
        plt.ylabel("sentiment x frequency)")
        plt.legend(loc="upper left")
        file_path_hourly = "public_html/finance/res/img/sentiment/hourly_plots"
        plt.savefig(f"{file_path_hourly}/{now.strftime(date_hour_file_format)}_sentiment_hourly_plot.png", dpi=dpi)
        copyfile(f"{file_path_hourly}/{now.strftime(date_hour_file_format)}_sentiment_hourly_plot.png",
                 f"{file_path_hourly}/current_sentiment_hourly_plot.png")

        plt.close()
        plt.clf()

    else:
        all_df.set_index("Date", inplace=True)

    sentiment_cols = [col for col in all_df.columns.values if col.endswith("sentiment")]

    df2 = all_df[sentiment_cols]
    df2.columns = [s.split("_")[0] for s in sentiment_cols]

    table_html = df2.to_html()

    html_before = '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">' \
                  '<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate" />' \
                  '<meta http-equiv="Pragma" content="no-cache" /><meta http-equiv="Expires" content="0" />' \
                  '<title>Reddit stock sentiment</title><link rel="stylesheet" href="style.css"></head><body>'

    html_after = '</body></html>'

    with open("public_html/finance/index.html", "w") as f:
        f.write(html_before + table_html + html_after)

    all_df.reset_index(level=0).to_csv(f"data/sentiment/{subreddit}_sentiment.csv", index=False)

    if generate_scatter_plot:

        plt.figure(figsize=(12, 8), dpi=dpi)

        df_positive = df[df["sentiment"] >= 0.3]
        df_neutral = df[(df["sentiment"] < 0.3) & (df["sentiment"] > -0.3)]
        df_negative = df[df["sentiment"] <= -0.3]

        plt.scatter(df_positive["word_frequency"], df_positive["sentiment"], marker="o", color="green")
        plt.scatter(df_neutral["word_frequency"], df_neutral["sentiment"], marker="o", color="yellow")
        plt.scatter(df_negative["word_frequency"], df_negative["sentiment"], marker="o", color="red")

        for i, row in df.iterrows():
            plt.annotate(stock_label(row['symbol']), (row["word_frequency"], row["sentiment"]), fontsize=8)

        plt.xscale('log')
        plt.yscale('log')
        plt.xlabel("log(frequency)")
        plt.ylabel("sentiment score")
        file_path_scatter = "public_html/finance/res/img/sentiment/scatter_plots"
        plt.savefig(f"{file_path_scatter}/{now.strftime(datetime_file_format)}_sentiment_scatter_plot.png", dpi=dpi)
        copyfile(f"{file_path_scatter}/{now.strftime(datetime_file_format)}_sentiment_scatter_plot.png",
                 f"{file_path_scatter}/current_sentiment_scatter_plot.png")

        plt.close()
        plt.clf()
    print("Finished.")


def stock_label(symbol):
    # df = data_loader.load_price_history(symbol, dt.date.today()-dt.timedelta(days=5), dt.date.today())
    # if df is not None and len(df) >= 2:
    #     old_close = df.iloc[-2]["Adj Close"]
    #     new_close = df.iloc[-1]["Adj Close"]
    #     percent_change = (new_close - old_close) / old_close * 100
    #
    #     if percent_change > 0:
    #         percent_change_str = f" +{percent_change:.2f}%"
    #     else:
    #         percent_change_str = f" {percent_change:.2f}%"
    #
    # else:
    percent_change_str = ""

    info = data_loader.load_ticker_info(symbol)
    if info is not None and 'shortName' in info:
        company_name_str = f"{data_loader.load_ticker_info(symbol)['shortName']} "
    else:
        company_name_str = ""

    return f"{company_name_str}({symbol.upper()}){percent_change_str}"


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
    subreddit_stock_sentiment(reload_headlines=True, generate_word_cloud=False, generate_scatter_plot=True, debug=True)
