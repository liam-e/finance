#!/usr/bin/env python3
import datetime as dt
import logging
import os
import sys
from shutil import copyfile

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import style
from wordcloud import WordCloud

import data_loader
import generate_html

os.chdir(sys.path[0])
now = dt.datetime.now()
date_format = "%d/%m/%Y %H:%M:%S"
datetime_file_format = "%Y_%m_%d_%H_%M_%S"
date_hour_file_format = "%Y_%m_%d_%H"
date_file_format = "%Y_%m_%d"
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

style.use("dark_background")

labels_dict = {}


def plot_sentiment_charts(dpi=150, simple_labels=False, stocks_count=10, scatter_stocks_count=30):
    logging.basicConfig(filename="sentiment_charts.log", filemode="w", format=log_format, datefmt=date_format,
                        level=logging.INFO)

    df = load_sentiment_data()

    if df is None or len(df) == 0:
        return

    # df.fillna(0, inplace=True)

    df.sort_values(df.last_valid_index(), ascending=False, axis=1, inplace=True)

    frequency_cols = [col for col in df.columns if col.endswith("frequency")]
    df_freqency = df[frequency_cols]
    df_freqency.columns = [s.split("_")[0] for s in frequency_cols]

    most_frequent = df_freqency.columns[:stocks_count]

    df_daily = df_freqency.resample("D").mean()
    df_daily.sort_values(df_daily.last_valid_index(), ascending=False, axis=1, inplace=True)
    most_frequent_daily = df_daily.columns[:stocks_count].values

    df_hourly = df_freqency.resample("H").mean()
    df_hourly.sort_values(df_hourly.last_valid_index(), ascending=False, axis=1, inplace=True)
    most_frequent_hourly = df_hourly.columns[:stocks_count].values

    logging.info("Generating charts...")

    log_values = True

    # ----------- FREQUENCY -----------
    plot_sentiment(df_freqency, value_type="frequency", plot_type="daily", log=log_values, dpi=dpi,
                   simple_labels=simple_labels)
    plot_sentiment(df_freqency, value_type="frequency", plot_type="hourly", log=log_values, dpi=dpi,
                   simple_labels=simple_labels)
    plot_sentiment(df_freqency, value_type="frequency", plot_type="timeseries", log=log_values, dpi=dpi,
                   simple_labels=simple_labels)

    # ----------- SENTIMENT -----------
    sentiment_cols = [col for col in df.columns if
                      col.endswith("sentiment") and col.split("_")[0] in most_frequent_daily]
    df_sentiment = df[sentiment_cols]
    df_sentiment.columns = [s.split("_")[0] for s in sentiment_cols]

    plot_sentiment(df_sentiment, value_type="sentiment", plot_type="daily", dpi=dpi, simple_labels=simple_labels)

    sentiment_cols = [col for col in df.columns if
                      col.endswith("sentiment") and col.split("_")[0] in most_frequent_hourly]
    df_sentiment = df[sentiment_cols]
    df_sentiment.columns = [s.split("_")[0] for s in sentiment_cols]

    plot_sentiment(df_sentiment, value_type="sentiment", plot_type="hourly", dpi=dpi, simple_labels=simple_labels)

    sentiment_cols = [col for col in df.columns if col.endswith("sentiment") and col.split("_")[0] in most_frequent]
    df_sentiment = df[sentiment_cols]
    df_sentiment.columns = [s.split("_")[0] for s in sentiment_cols]

    plot_sentiment(df_sentiment, value_type="sentiment", plot_type="timeseries", dpi=dpi, simple_labels=simple_labels)

    # ----------- SCATTERPLOT -----------
    most_frequent_daily = df_daily.columns[:scatter_stocks_count].values
    sentiment_cols = [col for col in df.columns if
                      col.endswith("sentiment") and col.split("_")[0] in most_frequent_daily]
    df_sentiment = df[sentiment_cols]
    df_sentiment.columns = [s.split("_")[0] for s in sentiment_cols]

    df = pd.concat([df_daily.iloc[-1, :scatter_stocks_count], df_sentiment.iloc[-1]], axis=1)

    df.reset_index(inplace=True)

    df.columns = ["symbol", "frequency", "sentiment"]

    plt.figure(figsize=(20, 10), dpi=dpi)

    df = df[df["sentiment"] != 0]

    with open("data/sentiment/top_daily_tickers.txt", "w") as f:
        f.write("\n".join(df["symbol"].values))

    df["log_frequency"] = np.log(df["frequency"])

    df_positive = df[df["sentiment"] >= 0.1]
    df_neutral = df[(df["sentiment"] < 0.1) & (df["sentiment"] > -0.1)]
    df_negative = df[df["sentiment"] <= -0.1]

    plt.scatter(df_positive["log_frequency"], df_positive["sentiment"], marker="o", color="green")
    plt.scatter(df_neutral["log_frequency"], df_neutral["sentiment"], marker="o", color="gold")
    plt.scatter(df_negative["log_frequency"], df_negative["sentiment"], marker="o", color="red")

    for i, row in df.iterrows():
        plt.annotate(
            stock_label(row["symbol"], simple=simple_labels),
            (row["log_frequency"], row["sentiment"]),
            fontsize=12,
            color="white"
        )

    plt.title("Scatter plot - most recent day")
    # plt.xscale("log")
    # plt.yscale("log")
    plt.xlabel("log(frequency)")
    plt.ylabel("sentiment score")

    file_path = f"public_html/finance/res/img/sentiment/sentiment"
    file_name = f"sentiment_scatter_plot.png"

    if not os.path.exists(file_path):
        os.makedirs(file_path)
    plt.savefig(f"{file_path}/{now.strftime(date_hour_file_format)}_{file_name}", dpi=dpi)
    copyfile(f"{file_path}/{now.strftime(date_hour_file_format)}_{file_name}",
             f"{file_path}/current_{file_name}")

    plt.close()
    plt.clf()

    logging.info(f"scatter plot of sentiment completed.")
    logging.info(f"Scatter plot completed.")

    generate_html.generate_sentiment_html()
    logging.info("Success.")


def plot_sentiment(df, value_type, plot_type, dpi=150, stocks_count=10, log=False, simple_labels=False):
    if df is None or len(df) == 0:
        logging.info(f"Dataframe is empty for {value_type} {plot_type} plot.")
        return

    if plot_type == "daily":
        df = df.resample("D").mean()
        df = df[df.index >= df.index[-1] - dt.timedelta(days=30)]

    elif plot_type == "hourly":
        df = df.resample("H").mean()
        df = df[df.index >= df.index[-1] - dt.timedelta(days=7)]
    elif plot_type == "timeseries":
        df = df
        df = df[df.index >= df.index[-1] - dt.timedelta(days=7)]
    else:
        logging.info(f"{plot_type} not supported.")
        return

    if len(df) == 0:
        logging.info(f"Dataframe is empty for {value_type} {plot_type} plot.")
        return

    df.replace(0, np.nan, inplace=True)

    if value_type == "frequency":
        df = df[df.columns[:stocks_count]]

    if log:
        for symbol in df.columns.values:
            df[symbol] = np.log(df[symbol] - np.min(df[symbol]) + 1)

    df = df.sort_values(df.last_valid_index(), ascending=False, axis=1)

    plt.figure(figsize=(20, 10), dpi=dpi)

    for symbol in df.columns.values:
        plt.plot(pd.to_datetime(df.index), df[symbol],
                 label=f"{df[symbol][-1]:.2f} - {stock_label(symbol, simple=simple_labels)}")

    plt.title(f"{value_type.title()} - {plot_type}")
    plt.xlabel("Date")
    if log:
        plt.ylabel(f"log({value_type})")
    else:
        plt.ylabel(value_type)
    plt.legend(loc="upper left")

    file_path = f"public_html/finance/res/img/sentiment/{value_type}"
    file_name = f"{value_type}_{plot_type}_plot.png"
    if not os.path.exists(file_path):
        os.makedirs(file_path)
    plt.savefig(f"{file_path}/{now.strftime(date_hour_file_format)}_{file_name}", dpi=dpi)
    copyfile(f"{file_path}/{now.strftime(date_hour_file_format)}_{file_name}",
             f"{file_path}/current_{file_name}")

    plt.close()
    plt.clf()

    logging.info(f"{plot_type} plot of {value_type} completed.")


def stock_label(symbol, simple=False):
    if simple:
        return f" {symbol.upper()}"

    if symbol in labels_dict:
        return labels_dict[symbol]
    else:
        df = data_loader.load_price_history(symbol, dt.date.today() - dt.timedelta(days=5), dt.date.today(),
                                            reload=True)
        if df is not None and len(df) >= 2:
            old_close = df.iloc[-2]["Adj Close"]
            new_close = df.iloc[-1]["Adj Close"]

            current_price_str = f" {new_close:.2f}"

            percent_change = (new_close - old_close) / old_close * 100

            if percent_change > 0:
                percent_change_str = f" +{percent_change:.2f}%"
            else:
                percent_change_str = f" {percent_change:.2f}%"

        else:
            current_price_str = ""
            percent_change_str = ""

        info = data_loader.load_ticker_info(symbol, reload=False)
        if info is not None and "shortName" in info:
            company_name_str = f"{data_loader.load_ticker_info(symbol)['shortName']} "
        else:
            company_name_str = ""

        label = f" {company_name_str}({symbol.upper()}){current_price_str}{percent_change_str}"

        labels_dict[symbol] = label
        return label


def generate_word_cloud(symbols_dict, dpi=150):
    word_cloud = WordCloud(scale=5, max_words=200, relative_scaling=0.5,
                           normalize_plurals=False).generate_from_frequencies(symbols_dict)
    save_image(word_cloud,
               f"public_html/finance/res/img/sentiment/word_clouds/"
               f"{now.strftime(datetime_file_format)}_word_cloud.png",
               dpi=dpi)


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


def load_sentiment_data():
    with open("data/sentiment/auth.txt", "r") as f:
        lines = f.readlines()
        subreddit = lines[3].strip()

    file_path = f"data/sentiment/{subreddit}_sentiment.csv"

    if os.path.isfile(file_path):
        return pd.read_csv(file_path, index_col=0, parse_dates=True)


if __name__ == "__main__":
    plot_sentiment_charts(simple_labels=False)
