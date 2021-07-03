import pandas as pd
import datetime as dt

df = pd.read_csv("reddit_sentiment.csv", index_col=0, parse_dates=True)

today = dt.datetime.today()

df_1 = df[df.index < today - dt.timedelta(days=10*7)]
df_2 = df[df.index >= today - dt.timedelta(days=10*7)]

df_1.reset_index(inplace=True)
df_2.reset_index(inplace=True)

df_1.to_csv("reddit_sentiment_1.csv", index=False)
df_2.to_csv("reddit_sentiment.csv", index=False)
