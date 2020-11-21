import datetime as dt

import numpy as np
import pandas as pd
import yfinance as yf

import data_loader
import simulator

yf.pdr_override()

start_date = dt.datetime(2017, 12, 1)
end_date = dt.datetime.now()

info_types = ["info", "options", "dividends",
              "mutualfund_holders", "institutional_holders",
              "major_holders", "calendar", "actions", "splits"]

cols_to_remove = ["longName",
                  "sector",
                  "address1",
                  "address2",
                  "companyOfficers",
                  "fax",
                  "isEsgPopulated",
                  "logo_url",
                  "market",
                  "phone",
                  "quoteType",
                  "symbol",
                  "tradeable",
                  "payoutRatio", "gmtOffSetMilliseconds", "market", "maxAge", ]

date_cols = ["dateShortInterest", "exDividendDate", "lastDividendDate", "lastFiscalYearEnd", "lastSplitDate",
             "mostRecentQuarter", "nextFiscalYearEnd", "sharesShortPreviousMonthDate"]


def rsi(df, time_period=14):
    adj_close_idx = list(df.columns).index("Adj Close")

    up_down = df.iloc[-time_period:-1, adj_close_idx].values - df.iloc[-time_period - 1:-2, adj_close_idx].values

    smma_up = np.sum(up_down[up_down > 0]) / time_period
    smma_down = -np.sum(up_down[up_down < 0]) / time_period

    if smma_down == 0:
        return 100

    rs = smma_up / smma_down

    rs_rating = 100 - 100 / (1 + rs)

    return rs_rating


def screen_stock(symbol, reload=False, remove_screened=True):
    print(symbol)

    try:
        df = data_loader.load_price_history(symbol, reload)

        if df is None:
            raise ValueError

        print(df.head())

        if not reload and isinstance(df.index[-1], dt.datetime) and not (
                (end_date.weekday() >= 5 and df.index[-1] >= end_date - dt.timedelta(days=3))
                or (end_date.weekday() < 5 and df.index[-1] >= end_date - dt.timedelta(days=2))):
            df = data_loader.load_price_history(symbol, reload=True)

        if df is None or len(df) == 0:
            raise ValueError
    except ValueError:
        print(f"{symbol} not found.")
        return None

    smas_used = [50, 150, 200]
    for sma in smas_used:
        df[f"SMA_{sma}"] = np.round(df["Adj Close"].rolling(window=sma).mean(), 2)

    current_close = df["Adj Close"].iloc[-1]
    moving_average_50 = df["SMA_50"].iloc[-1]
    moving_average_150 = df["SMA_150"].iloc[-1]
    moving_average_200 = df["SMA_200"].iloc[-1]

    try:
        low_of_52_week = np.min(df["Adj Close"].iloc[-260:])
        high_of_52_week = np.max(df["Adj Close"].iloc[-260:])

        rs_rating = rsi(df)
    except IndexError:
        return None

    try:
        moving_average_200_20 = df["SMA_200"].iloc[-20]
    except IndexError:
        moving_average_200_20 = 0

    # Condition 1: Current Price > 150 SMA and > 200 SMA
    cond_1 = current_close > moving_average_150 > moving_average_200
    # Condition 2: 150 SMA > 200 SMA
    cond_2 = moving_average_150 > moving_average_200
    # Condition 3: 200 SMA trending up for at least 1 month (ideally 4-5 months)
    cond_3 = moving_average_200 > moving_average_200_20
    # Condition 4: 50 SMA > 150 SMA and 150 SMA > 200 SMA
    cond_4 = moving_average_50 > moving_average_150 > moving_average_200
    # Condition 5: Current Price > 50 SMA
    cond_5 = current_close > moving_average_50
    # Condition 6: Current Price is at least 30% above 52 week low (Many of the best are up 100-300% before
    # coming out of consolidation)
    cond_6 = current_close >= (1.3 * low_of_52_week)
    # Condition 7: Current Price is within 25% of 52 week high
    cond_7 = current_close >= (0.75 * high_of_52_week)
    # Condition 8: IBD RS rating >70 and the higher the better
    cond_8 = rs_rating > 70

    is_screened = (cond_1 and cond_2 and cond_3 and cond_4 and cond_5 and cond_6 and cond_7 and cond_8)

    if remove_screened and not is_screened:
        return None

    if is_screened:
        is_screened_str = "PASS"
    else:
        is_screened_str = "FAIL"

    info_dict = data_loader.load_ticker_info(symbol, "info", reload)

    for key in ["longName", "sector", "dividendRate", "dividendYield", "payoutRatio"]:
        if key not in info_dict:
            info_dict[key] = np.nan

    row = {
        "Symbol": symbol,
        "Security": info_dict["longName"],
        "Sector": info_dict["sector"],
        "RSI": rs_rating,
        "Passes Mark Minervini screening": is_screened_str,
        "Current Close": current_close,
        "dividendRate": info_dict["dividendRate"],
        "dividendYield": info_dict["dividendYield"],
        "Payout Ratio": info_dict["payoutRatio"],
        "Simulation Percent Return": simulator.simulate_ema_strategy(df, symbol, reload),
        "50 Day MA": moving_average_50,
        "150 Day MA": moving_average_150,
        "200 Day MA": moving_average_200,
        "52 Week Low": low_of_52_week,
        "52 Week High": high_of_52_week,
    }

    for k, v in info_dict.items():
        if k not in cols_to_remove and v is not None:
            row[k] = v

    return row


def screen_stocks(symbols, file_path, reload=False, remove_screened=True):
    out_df = None

    for symbol in symbols:
        row = screen_stock(symbol, reload, remove_screened)
        if row:
            if out_df is None:
                out_df = pd.DataFrame(columns=list(row.keys()))
            out_df = out_df.append(row, ignore_index=True)

    for date_col in date_cols:
        try:
            out_df[date_col] = pd.to_datetime(out_df[date_col], unit="s", errors="coerce")
        except:
            pass

    out_df["industry"] = out_df["industry"].apply(lambda x: x.replace("—", "-") if isinstance(x, str) else "")
    cols = list(out_df.columns)
    cols.remove("longBusinessSummary")
    cols.append("longBusinessSummary")

    out_df = out_df[cols]

    out_df.to_csv(file_path, index=False, date_format="%Y-%m-%d", header=True)
    writer = pd.ExcelWriter('.'.join(file_path.split('.')[:-1]) + ".xlsx", engine="xlsxwriter",
                            date_format="YYYY-MM-DD")
    out_df.to_excel(writer, sheet_name="sheet1")
    worksheet = writer.sheets["sheet1"]
    for idx, col in enumerate(out_df):
        series = out_df[col]
        max_len = max((
            series.astype(str).map(len).max(),  # len of largest item
            len(str(series.name))  # len of column name/header
        )) + 1  # adding a little extra space
        worksheet.set_column(idx, idx, max_len)  # set column width

    writer.save()

    print(f"Successfully screened {len(symbols)} stocks down to {len(out_df)}.")
    return out_df
