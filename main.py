import praw
from dotenv import load_dotenv
import os
import re
import yfinance as yf
import csv
import logging
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
    except Exception as e:
        logging.error(f"Error checking symbol {symbol}: {e}")
    return False

symbol_counts = defaultdict(int)
for submission in reddit.subreddit("RVSN").hot(limit=25):
    print(submission.title)
    potential_symbols = re.findall(r'\b[A-Z]{2,5}\b', submission.title)
    for symbol in potential_symbols:
        if is_stock_symbol(symbol):
            symbol_counts[symbol] += 1


with open('stock_symbol_data.csv', 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['Symbol', 'Count'])
    for symbol, count in symbol_counts.items():
        writer.writerow([symbol, count])