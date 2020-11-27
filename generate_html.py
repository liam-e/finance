import markdown
import datetime as dt


def markdown_to_html(input_file):
    with open(input_file, "r") as f:
        return markdown.markdown(f.read())


def generate_sentiment_html(now):
    with open("data/sentiment/html/sentiment_header_snippet.html", "r") as f:
        header_snippet = f.read()

    with open("data/sentiment/html/sentiment_footer_snippet.html", "r") as f:
        footer_snippet = f.read()

    last_updated = f"<p id='timestamp'>Last updated: {now.strftime('%A %d %B, %Y at %I:%M:%S %p')}</p></header>"

    # html = header_snippet + last_updated + markdown_to_html("README.md") + footer_snippet

    html = header_snippet + last_updated + footer_snippet

    with open("public_html/finance/index.html", "w") as f:
        f.write(html)


if __name__ == "__main__":
    generate_sentiment_html(dt.datetime.now())
