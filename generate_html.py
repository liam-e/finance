import datetime as dt
import os
import sys
import traceback
from time import time
from bs4 import BeautifulSoup as bs
import markdown

import data_loader
import finance_logger
import stock_screener

os.chdir(sys.path[0])


def markdown_to_html(input_file):
    with open(input_file, "r") as f:
        return markdown.markdown(f.read())


def time_updated_tag():
    return f"<p id='timestamp'>Last updated: {dt.datetime.now().strftime('%A, %d %B, %Y at %I:%M:%S %p')}</p>"


def generate_sentiment_html():

    with open("public_html/finance/sentiment/index.html", "r") as f:
        html = f.read()

    soup = bs(html, "lxml")

    div = soup.find("p", {"id": "timestamp"})
    div.string.replace_with(f"Last updated: {dt.datetime.now().strftime('%A, %d %B, %Y at %I:%M:%S %p')}")

    html = str(soup)

    # title = "Reddit stock sentiment"
    # header_snippet, footer_snippet = header_and_footer(title)
    #
    # root_path = "public_html/finance/res/img/sentiment"
    #
    # html_root_path = "../res/img/sentiment"
    #
    # html_content = f"\n<header>\n<h1>Wallstreetbets tracker</h1>\n{time_updated_tag()}\n</header>\n"
    #
    # for subdir in ["sentiment", "frequency"]:
    #     subheading = " ".join(subdir.title().split("_"))
    #     html_content += f"\n<h2>{subheading}</h2>\n"
    #     for root, subdirs, files in os.walk(f"{root_path}/{subdir}"):
    #         for file in files:
    #             img_path = f"{html_root_path}/{subdir}/{file}"
    #             img_name = f"{subdir.title()} {img_path.split('_')[-2]} plot"
    #             img_tag = f"<div class='imgbox'><img class='center-fit' src='{img_path}' alt='{img_name}'/></div>\n"
    #             html_content += img_tag
    #
    # html = header_snippet + html_content + footer_snippet

    with open("public_html/finance/sentiment/index.html", "w") as f:
        f.write(html)


def generate_ohlc_html():
    title = "Daily charts"
    header_snippet, footer_snippet = header_and_footer(title)

    root_path = "public_html/finance/res/img/ohlc"

    html_root_path = "../res/img/ohlc"

    html_content = f"\n<header>\n<h1>Daily Charts</h1>\n{time_updated_tag()}\n</header>\n"

    for subdir in ["watchlist", "reddit_sentiment"]:
        subheading = " ".join(subdir.title().split("_"))
        html_content += f"\n<h2>{subheading}</h2>\n"
        for root, subdirs, files in os.walk(f"{root_path}/{subdir}"):
            for file in files:
                img_path = f"{html_root_path}/{subdir}/{file}"
                img_name = f"{img_path.split('/')[-1].split('_')[-2].upper()} OHLC plot"
                img_tag = f"<div class='imgbox'><img class='center-fit' src='{img_path}' alt='{img_name}'/></div>\n"
                html_content += img_tag

    html = header_snippet + html_content + footer_snippet

    with open("public_html/finance/daily_charts/index.html", "w") as f:
        f.write(html)


def generate_screener_html(debug=False):
    title = "Stock Screener"
    header_snippet, footer_snippet = header_and_footer(title)

    tablesorter_snippet = "\n\n<link rel='stylesheet' href='../res/css/theme.dark.min.css'>\n" \
                          "<script src='../res/js/jquery-3.5.1.min.js'></script>\n" \
                          "<script src='../res/js/jquery.tablesorter.min.js'></script>\n" \
                          "<script id='js'>$(function() {$('.dataframe').tablesorter({theme:'dark',sortList: [[0,0],[1,0]]});});</script>\n\n"

    header_snippet = header_snippet.replace("</title>", "</title>" + tablesorter_snippet)

    watchlist = data_loader.watchlist()

    if debug:
        watchlist = watchlist[:2]

    df = stock_screener.screen_stocks(watchlist, remove_screened=False, reload=True)

    table = df.to_html(index=False, na_rep="")

    table = table.replace('<table border="1" class="dataframe">', '<table border="1" class="dataframe tablesorter">')

    table = table.replace("<td>", "<td><div class='table-cell'>")
    table = table.replace("</td>", "</div></td>")

    table = table.replace("<th>", "<th><div class='table-cell'>")
    table = table.replace("</th>", "</div></th>")

    table = table.replace("PASS", "<span class='pass'>PASS</span>")
    table = table.replace("FAIL", "<span class='fail'>FAIL</span>")

    table = table.replace("NaT", "")

    html_content = f"\n<header>\n<h1>Stock screener</h1>\n{time_updated_tag()}\n</header>\n" \
                   f"<h2>Watchlist stocks</h2>" + table

    with open("data/sentiment/top_daily_tickers.txt", "r") as f:
        reddit_top_symbols = f.read().split("\n")

    if debug:
        reddit_top_symbols = reddit_top_symbols[:2]

    df2 = stock_screener.screen_stocks(reddit_top_symbols, remove_screened=False, reload=True)

    table = df2.to_html(index=False, na_rep="")

    table = table.replace('<table border="1" class="dataframe">', '<table border="1" class="dataframe tablesorter">')

    table = table.replace("<td>", "<td><div class='table-cell'>")
    table = table.replace("</td>", "</div></td>")

    table = table.replace("<th>", "<th><div class='table-cell'>")
    table = table.replace("</th>", "</div></th>")

    table = table.replace("PASS", "<span class='pass'>PASS</span>")
    table = table.replace("FAIL", "<span class='fail'>FAIL</span>")

    table = table.replace("NaT", "")

    html_content += f"\n<h2>Daily top {len(reddit_top_symbols)} reddit stocks</h2>\n" + table

    html = header_snippet + html_content + footer_snippet

    with open("public_html/finance/screener/index.html", "w") as f:
        f.write(html)


def header_and_footer(title):
    with open("data/html_snippets/header_snippet.html", "r") as f:
        header_snippet = f.read()

    header_snippet = header_snippet.replace("<title></title>", f"<title>{title}</title>")

    with open("data/html_snippets/footer_snippet.html", "r") as f:
        footer_snippet = f.read()

    return header_snippet, footer_snippet


def generate_all_html(debug=False):
    generate_sentiment_html()
    generate_ohlc_html()
    generate_screener_html(debug=debug)


def main(debug=False):
    script_name = os.path.basename(__file__)
    start = time()
    finance_logger.setup_log_script(script_name)

    try:
        generate_all_html(debug=debug)
        finance_logger.append_log("success", script_name=script_name)
        finance_logger.log_time_taken(time() - start, script_name)
    except:
        traceback.print_exc()
        finance_logger.append_log("failure", script_name=script_name)


if __name__ == "__main__":
    # main(debug=False)
    generate_sentiment_html()
