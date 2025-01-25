import praw
from dotenv import load_dotenv
import os
import re
import yfinance as yf
from collections import defaultdict
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from flask import Flask, render_template, jsonify
from flask_cors import CORS
from flask import request
import traceback
from functools import lru_cache
import time
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

#enable CORS for all API routes
CORS(app, resources={
    r"/api/*": {
        "origins": "*"
    }
})

#initialises vader sentiment object
analyzer = SentimentIntensityAnalyzer()

#loads .env file containing reddit info for api connection
load_dotenv()

#initialises reddit object
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    password=os.getenv("REDDIT_PASSWORD"),
    user_agent=os.getenv("REDDIT_USER_AGENT"),
    username=os.getenv("REDDIT_USERNAME")
)

# common words that match stock symbol pattern but aren't stocks
ignored_words = ("DD", "FYI", "CASH", "USA", "YOLO", "FOMO", "OG", "MONEY", "PWOAH", "ONLY", "US")

#cache to store validated stock symbols to prevent repeated API calls
symbol_cache = {}

def is_stock_symbol(stock_symbol):
    """
    :param stock_symbol: compares if a 2-5 string is a real stock symbol in yahoo finance
    :return: returns if it is a real stock symbol
    """
    #check cache before making API call
    if stock_symbol in symbol_cache:
        return symbol_cache[stock_symbol]

    if stock_symbol in ignored_words:
        symbol_cache[stock_symbol] = False
        return False
    try:
        stock = yf.Ticker(stock_symbol)
        stock_info = stock.info
        if stock_info is not None:
            symbol_cache[stock_symbol] = True
            return True
        else:
            symbol_cache[stock_symbol] = False
            print(f"{stock_symbol} is not a valid stock symbol.")
            return False
    except Exception as e:
        print(f"Error checking symbol {stock_symbol}: {e}")

def find_stock_symbols(text):
    pattern = [
       r'\$[A-Z]{1,5}\b',
       r'\b[A-Z]{2,5}\b'
   ]

    symbols = set()
    for p in pattern:
        found_symbols = re.findall(p, text)

        cleaned_symbols = {symbol.replace("$", "") for symbol in found_symbols}
        symbols.update(cleaned_symbols)

    return {symbol for symbol in symbols if is_stock_symbol(symbol)}

def get_weighted_sentiment(title, body):
   title_sentiment = analyzer.polarity_scores(title)["compound"] * 0.6
   body_sentiment = analyzer.polarity_scores(body)["compound"] * 0.4
   return title_sentiment + body_sentiment

def process_single_submission(submission):
   text = f"{submission.title} {submission.selftext}"
   symbols = find_stock_symbols(text)
   sentiment = get_weighted_sentiment(submission.title, submission.selftext)
   return symbols, sentiment

def get_all_submissions():
    return list(reddit.subreddit("pennystocks").top(time_filter="hour"))

def process_submission(submissions):
    symbol_data = defaultdict(lambda: {"mentions": 0, "sentiments": []})

    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(process_single_submission, submissions))
        for symbols, sentiment in results:
            for symbol in symbols:
                symbol_data[symbol]['mentions'] += 1
                symbol_data[symbol]['sentiments'].append(sentiment)
    return symbol_data

def format_data_for_frontend(symbol_data):
    formatted_data = []

    for symbol, data in symbol_data.items():
        avg_sentiment = sum(data['sentiments']) / len(data['sentiments']) if data['sentiments'] else 0
        formatted_data.append({
            'symbol': symbol,
            'mentions': data['mentions'],
            'sentiment': avg_sentiment
        })
    return formatted_data

@lru_cache(maxsize=1)
def get_stock_data():
    #force cache refresh every 5 min
    timestamp = int(time.time() / 300)
    print(f"Fetching fresh data at timestamp: {timestamp}")

    submissions = get_all_submissions()
    symbol_data = process_submission(submissions)
    return format_data_for_frontend(symbol_data)

#sort functions for API endpoints
def sort_by_mentions(data, ascending = False):
    return sorted(data, key=lambda x: x['mentions'], reverse= not ascending)

def sort_by_sentiment(data, ascending = False):
    return sorted(data, key=lambda x: x['sentiment'], reverse= not ascending)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/stock-data')
def stock_data():
    try:
        print("getting data")
        data = get_stock_data()
        print(f"Data retrieved: {data}")
        sort_type = request.args.get('sort')
        ascending = request.args.get('ascending') == 'true'

        if sort_type == 'mentions':
            data = sort_by_mentions(data, ascending)
        elif sort_type == 'sentiment':
            data = sort_by_sentiment(data, ascending)
        return jsonify(data)
    except Exception as e:
        print(f"Error in stock_data route: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)