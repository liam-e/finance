import datetime as dt

import matplotlib.pyplot as plt
import numpy as np

import data_loader

start = dt.datetime(2019, 6, 1)
now = dt.datetime.now()

df = data_loader.load_price_history("amd", start, now)

df["High"].plot(label="High")

pivots = []
dates = []
counter = 0
last_pivot = 0

value_range = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
date_range = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

for i in df.index:

    current_max = max(value_range, default=0)
    value = np.round(df["High"][i], 2)

    value_range = value_range[1:9]
    date_range = date_range[1:9]

    value_range.append(value)
    date_range.append(i)

    if current_max == max(value_range, default=0):
        counter += 1
    else:
        counter = 0

    if counter == 5:
        last_pivot = current_max
        date_loc = value_range.index(last_pivot)
        last_date = date_range[date_loc]

        pivots.append(last_pivot)
        dates.append(last_date)

# print(f"{pivots}")
# print(f"{dates}")

for index in range(len(pivots)):
    print(f"{pivots[index]}: {dates[index]}")

    plt.plot_date([dates[index], dates[index] + dt.timedelta(days=30)], [pivots[index], pivots[index]],
                  linestyle="-", linewidth=2, marker=",")

plt.show()
