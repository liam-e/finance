import datetime as dt
import os
import pickle
from collections import Counter

import matplotlib.pyplot as plt
import pandas as pd
import praw
from nltk.sentiment.vader import SentimentIntensityAnalyzer as SIA
from wordcloud import WordCloud

import data_loader


def subreddit_stock_sentiment(generate_word_cloud=False, generate_scatter_plot=False):
    with open("data/sentiment/auth.txt", "r") as f:
        lines = f.readlines()
        client_id = lines[0].strip()
        client_secret = lines[1].strip()
        username = lines[2].strip()
        subreddit = lines[3].strip()

    reddit = praw.Reddit(client_id=client_id,
                         client_secret=client_secret,
                         user_agent=username)

    headlines = set()

    for submission in reddit.subreddit(subreddit).new(limit=None):
        headlines.add(submission.title)

    with open("data/all_symbols.p", "rb") as f:
        all_symbols = pickle.load(f)

    with open("data/sentiment/words_to_remove.p", "rb") as f:
        words_to_remove = pickle.load(f)

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
        save_image(word_cloud, f"out/word_clouds/{subreddit}_word_cloud.png")

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

        # if mentioned_stocks and "pltr" not in mentioned_stocks and "nio" not in mentioned_stocks and "tsla" not in mentioned_stocks:
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

        all_df.loc[row_index, "Date"] = dt.datetime.now()
        all_df.loc[row_index, f"{symbol}_frequency"] = row["word_frequency"]
        all_df.loc[row_index, f"{symbol}_sentiment"] = row["sentiment"]

    all_df.to_csv(f"data/sentiment/{subreddit}_sentiment.csv", index=False)

    if generate_scatter_plot:

        plt.figure(figsize=(16, 10))

        df_positive = df[df["sentiment"] >= 0.3]
        df_neutral = df[(df["sentiment"] < 0.3) & (df["sentiment"] > -0.3)]
        df_negative = df[df["sentiment"] <= -0.3]

        plt.scatter(df_positive["word_frequency"], df_positive["sentiment"], marker="o", color="green")
        plt.scatter(df_neutral["word_frequency"], df_neutral["sentiment"], marker="o", color="yellow")
        plt.scatter(df_negative["word_frequency"], df_negative["sentiment"], marker="o", color="red")

        for i, row in df.iterrows():
            company_name = data_loader.load_ticker_info(row['symbol'])['shortName']
            label = f"{company_name} ({row['symbol']})"

            plt.annotate(label, (row["word_frequency"], row["sentiment"]), fontsize=8)

        plt.xlabel("frequency")
        plt.ylabel("sentiment score")

        plt.savefig(f"out/sentiment_plots/{subreddit}_sentiment.png", dpi=200)


def save_image(data, filename):
    fig = plt.figure()
    fig.set_size_inches(16, 8)
    ax = plt.Axes(fig, [0., 0., 1., 1.])
    ax.set_axis_off()
    fig.add_axes(ax)
    ax.imshow(data)
    plt.savefig(filename, dpi=100)
    plt.close()


if __name__ == "__main__":
    subreddit_stock_sentiment()
