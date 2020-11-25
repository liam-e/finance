import datetime as dt

import matplotlib.pyplot as plt
import mplfinance as mpf
import numpy as np
import pandas as pd

import data_loader as dl

now = dt.datetime.today()

df = dl.load_price_history("aapl", start_date=dt.datetime(2018, 1, 1))

df.drop(df[df["Volume"] < 1000].index, inplace=True)

df_monthly = dl.monthly(df)

# GLV: green line value

gl_date = 0
last_glv = 0
current_date = None
current_glv = 0
counter = 0

glv_list = []
gl_date_list = []

for index, value in df_monthly["High"].items():
    if value > current_glv:
        current_glv = value
        current_date = index
        counter = 0

    if value < current_glv:
        counter += 1

        if counter == 3 and ((index.month != now.month) or (index.year != now.year)):
            if current_glv != last_glv:
                glv_list.append({"date": current_date, "value": current_glv})
            gl_date = current_date
            last_glv = current_glv
            counter = 0

print(glv_list)

plt.plot(df_monthly.index, df_monthly["High"])

apds = []

for gl in glv_list:
    print(gl["date"])
    df_gl = pd.DataFrame({"GLV": np.repeat(gl["value"], len(df_monthly))}, index=df_monthly.index)
    df_gl.loc[df_gl.index < gl["date"], "GLV"] = np.nan
    apds.append(mpf.make_addplot(df_gl, type="line", color="g", linestyle="dotted", width=1.5))

fig, ax = mpf.plot(df_monthly, type="ohlc", volume=True, addplot=apds, title="", returnfig=True, figsize=(12, 8))

plt.show()
plt.close(fig)
