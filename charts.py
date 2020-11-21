import datetime as dt

import matplotlib.pyplot as plt
import mplfinance as mpf
import pandas as pd
from dateutil.relativedelta import relativedelta
from matplotlib.backends.backend_pdf import PdfPages

import data_loader

today = dt.datetime.now()


def save_charts(df, period_months=24, moving_averages=(20, 50, 100, 200)):
    if period_months <= 12:
        chart_type = "candlestick"
    else:
        chart_type = "line"

    width, height = 11.69, 8.27

    with PdfPages(f'all_screened_charts_{period_months}_months.pdf') as pdf:

        first_page = plt.figure(figsize=(width, height))
        first_page.clf()
        txt = f"{len(df)} {chart_type} charts\nLast {period_months} months with {moving_averages} moving averages\n" \
              f"{today.strftime('%d %B %Y')}"
        first_page.text(0.5, 0.5, txt, transform=first_page.transFigure, size=24, ha="center")
        pdf.savefig()
        plt.close()

        for index, row in df.iterrows():

            symbol = row["Symbol"]
            name = row["Security"]

            div_rate_str = f"{row['dividendRate']}"

            if div_rate_str == "nan":
                div_rate_str = f", div. rate = 0"
            else:
                div_rate_str = f", div. rate = {row['dividendRate']:.4f}"

            title = f"\n\n\n{name} ({symbol})\nCurrent close = {row['Current Close']:.2f}\nRSI = {row['RSI']:.2f} " \
                    f"{div_rate_str}, 50 day MA = {row['50 Day MA']:.2f}"

            df = data_loader.load_price_history(symbol)

            fig, ax = mpf.plot(df[df.index >= today - relativedelta(months=period_months)], type=chart_type,
                               mav=moving_averages, volume=True, title=title, returnfig=True, figsize=(width, height))

            ax[0].legend(["Adjusted close"] + [f"{m} MA" for m in moving_averages])

            pdf.savefig(fig)

            plt.close(fig)


if __name__ == "__main__":
    screened_df = pd.read_csv("old/all_stocks.csv")

    screened_df.sort_values(by="RSI", ascending=False, inplace=True)

    moving_averages_list = [(3, 5, 10), (5, 10, 20), (10, 20, 50), (20, 50, 100)]

    for i, month in enumerate([3, 6, 12, 24]):
        save_charts(screened_df, period_months=month, moving_averages=moving_averages_list[i])
