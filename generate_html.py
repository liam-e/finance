import datetime as dt
import os

import markdown


def markdown_to_html(input_file):
    with open(input_file, "r") as f:
        return markdown.markdown(f.read())


def generate_sentiment_html(now, debug=False):
    with open("data/sentiment/html/sentiment_header_snippet.html", "r") as f:
        header_snippet = f.read()

    with open("data/sentiment/html/sentiment_footer_snippet.html", "r") as f:
        footer_snippet = f.read()

    last_updated = f"<p id='timestamp'>Last updated: {now.strftime('%A %d %B, %Y at %I:%M:%S %p')}</p></header>"

    # html = header_snippet + last_updated + markdown_to_html("README.md") + footer_snippet

    html = header_snippet + last_updated + footer_snippet

    with open("public_html/finance/index.html", "w") as f:
        if not debug:
            f.write(html)


def generate_ohlc_html(now, debug=False):
    with open("data/sentiment/html/ohlc_header_snippet.html", "r") as f:
        header_snippet = f.read()

    with open("data/sentiment/html/ohlc_footer_snippet.html", "r") as f:
        footer_snippet = f.read()

    last_updated = f"<p id='timestamp'>Last updated: {now.strftime('%A %d %B, %Y at %I:%M:%S %p')}</p></header>"

    charts_html = ""

    for file_name in os.listdir("public_html/finance/res/img/ohlc"):
        charts_html += f"<div class='imgbox'><img class='center-fit' src='../res/img/ohlc/{file_name}' alt='{file_name.split('_')[0].upper()}' /></div>"

    html = header_snippet + last_updated + charts_html + footer_snippet

    with open("public_html/finance/daily_briefing/index.html", "w") as f:
        if not debug:
            f.write(html)


if __name__ == "__main__":
    generate_sentiment_html(dt.datetime.now())
