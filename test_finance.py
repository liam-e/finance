import unittest

import daily_charts
import finance_logger
import generate_html
import sentiment_charts
import sentiment_words


class TestFinance(unittest.TestCase):

    def test_sentiment_words(self):
        sentiment_words.main(debug=False)
        self.assertTrue(finance_logger.was_successful("sentiment_words"))

    def test_sentiment_charts(self):
        sentiment_charts.main(debug=False)
        self.assertTrue(finance_logger.was_successful("sentiment_charts"))

    def test_daily_charts(self):
        daily_charts.main(debug=False)
        self.assertTrue(finance_logger.was_successful("daily_charts"))

    def test_generate_html(self):
        generate_html.main(debug=False)
        self.assertTrue(finance_logger.was_successful("generate_html"))


if __name__ == '__main__':
    unittest.main()
