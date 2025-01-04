import praw
from dotenv import load_dotenv
import os
import logging
import re
import yfinance as yf

handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
for logger_name in ("praw", "prawcore"):
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)

load_dotenv()
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    password=os.getenv("REDDIT_PASSWORD"),
    user_agent=os.getenv("REDDIT_USER_AGENT"),
    username=os.getenv("REDDIT_USERNAME")
)

def is_stock_symbol(symbol):
    try:
        stock = yf.Ticker(symbol)
        print(f"Checking symbol: {symbol}")
        print(stock.info)
        if stock.info.get("regularMarketPrice") is not None:
            return True
    except Exception:
        pass
    return False

real_symbols = []
for submission in reddit.subreddit("RVSN").hot(limit=25):
    print(submission.title)
    potential_symbol = re.findall(r'\b[A-Z]{2,5}\b', submission.title)
    real_symbols.extend([symbol for symbol in potential_symbol if is_stock_symbol(symbol)])
print(real_symbols)
