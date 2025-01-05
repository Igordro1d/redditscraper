import praw
from dotenv import load_dotenv
import os
import re
import yfinance as yf
import csv
from collections import defaultdict

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

csv_dict = defaultdict(int)
potential_stock_symbols = []
for submission in reddit.subreddit("RVSN").hot(limit=25):
    print(submission.title)
    potential_stock_symbols.extend(re.findall(r'\b[A-Z]{2,5}\b', submission.title))

for symbol in potential_stock_symbols:
    if is_stock_symbol(symbol):
        csv_dict[symbol] += 1
with open('stock_symbol_data.txt', 'w') as csvfile:
    writer = csv.writer(csvfile, delimiter=':')
    writer.writerow(csv_dict)