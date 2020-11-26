#!/usr/bin/python
import datetime as dt
import os
import sys
import pandas as pd

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)

os.chdir(sys.path[0])
now = dt.datetime.now()
datetime_file_format = '%Y_%m_%d_%H_%M_%S'
date_hour_file_format = "%Y_%m_%d_%H"
date_file_format = '%Y_%m_%d'

if __name__ == "__main__":
    with open("data/sentiment/auth.txt", "r") as f:
        lines = f.readlines()
        subreddit = lines[3].strip()

    file_path = f"data/sentiment/{subreddit}_sentiment.csv"

    if os.path.isfile(file_path):
        df = pd.read_csv(file_path, index_col=0, parse_dates=True)

        sentiment_cols = [col for col in df.columns.values if col.endswith("sentiment")]

        df2 = df[sentiment_cols]
        df2.columns = [s.split("_")[0] for s in sentiment_cols]

        print(df2.head())
