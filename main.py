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

@lru_cache(maxsize=1)
def get_stock_data():
    #force cache refresh every 5 min
    timestamp = int(time.time() / 300)
    print(f"Fetching fresh data at timestamp: {timestamp}")

    #track frequency of stock mentions and their sentiment scores
    symbol_counts = defaultdict(int)
    symbol_sentiment = defaultdict(list)

    for submission in reddit.subreddit("pennystocks").top(time_filter="hour"):
        #find all uppercase words 2-5 letters long that could be stock symbols
        potential_symbols = re.findall(r'\b[A-Z]{2,5}\b', submission.title + "" + submission.selftext)

        for symbol in potential_symbols:
            if is_stock_symbol(symbol):
                symbol_counts[symbol] += 1

                #calculate sentiment scores for both title and post content
                descr_sentiment = analyzer.polarity_scores(submission.selftext)["compound"]
                title_sentiment = analyzer.polarity_scores(submission.title)["compound"]

                avg_sentiment = (title_sentiment + descr_sentiment) / 2
                symbol_sentiment[symbol].append(avg_sentiment)
    #calculates total sentiment of each stock symbol by iterating through the dictionary holding each individual score
    average_sentiments = {symbol: sum(sentiments) / len(sentiments) for symbol, sentiments in symbol_sentiment.items()}

    #format data for frontend display
    stock_data = []
    for symbol in symbol_counts:
        stock_data.append({
            'symbol': symbol,
            'mentions': symbol_counts[symbol],
            'sentiment': average_sentiments.get(symbol, 0)
        })
    return stock_data


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