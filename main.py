import praw
from dotenv import load_dotenv
import os
import re
import yfinance as yf
from collections import defaultdict
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from flask import Flask, render_template, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": "*"
    }
})

#initialises vader sentiment object
analyzer = SentimentIntensityAnalyzer()

#loads .env file containing reddit info for api connection
load_dotenv()

# initialises reddit object
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    password=os.getenv("REDDIT_PASSWORD"),
    user_agent=os.getenv("REDDIT_USER_AGENT"),
    username=os.getenv("REDDIT_USERNAME")
)

ignored_words = ("DD", "FYI", "CASH", "USA", "YOLO", "FOMO", "OG", "MONEY", "PWOAH", "ONLY", "US")

def is_stock_symbol(stock_symbol):
    """
    :param stock_symbol: compares if a 2-5 string is a real stock symbol in yahoo finance
    :return: returns if it is a real stock symbol
    """
    try:
        stock = yf.Ticker(stock_symbol)
        stock_info = stock.info
        if stock_symbol in ignored_words:
            return False
        if stock_info is not None:
            return True
        else:
            print(f"{stock_symbol} is not a valid stock symbol.")
    except Exception as e:
        print(f"Error checking symbol {stock_symbol}: {e}")
    return False


def get_stock_data():
    symbol_counts = defaultdict(int)
    symbol_sentiment = defaultdict(list)

    for submission in reddit.subreddit("pennystocks").top(time_filter="day"):
        potential_symbols = re.findall(r'\b[A-Z]{2,5}\b', submission.title + "" + submission.selftext)

        for symbol in potential_symbols:
            if is_stock_symbol(symbol):
                symbol_counts[symbol] += 1

                descr_sentiment = analyzer.polarity_scores(submission.selftext)["compound"]
                title_sentiment = analyzer.polarity_scores(submission.title)["compound"]

                avg_sentiment = (title_sentiment + descr_sentiment) / 2
                symbol_sentiment[symbol].append(avg_sentiment)
    #calculates total sentiment of each stock symbol by iterating through the dictionary holding each individual score
    average_sentiments = {symbol: sum(sentiments) / len(sentiments) for symbol, sentiments in symbol_sentiment.items()}
    stock_data = []
    for symbol in symbol_counts:
        stock_data.append({
            'symbol': symbol,
            'mentions': symbol_counts[symbol],
            'sentiment': average_sentiments.get(symbol, 0)
        })
    return stock_data



def sort_by_mentions(data):
    return sorted(data.items(), key=lambda x: x[1]['mentions'], reverse=True)

def sort_by_sentiment(data):
    return sorted(data.items(), key=lambda x: x[1]['sentiment'], reverse=True)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/stock-data')
def stock_data():
    try:
        data = get_stock_data()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)