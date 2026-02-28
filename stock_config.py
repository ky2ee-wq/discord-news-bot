import os

# Google Gemini API 설정
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE")
GEMINI_MODEL = "gemini-2.0-flash"

# 디스코드 웹훅 URL
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "YOUR_WEBHOOK_URL_HERE")

# 추적 종목
STOCKS = ["AAPL", "MSFT", "NVDA", "TSLA", "GOOGL", "AMZN", "META"]

# 추적 지수
INDICES = {
    "^GSPC": "S&P 500",
    "^IXIC": "NASDAQ",
    "^DJI": "Dow Jones",
    "^VIX": "VIX",
}

# 금융 뉴스 RSS 피드
FINANCIAL_RSS_FEEDS = [
    {
        "name": "CNBC Markets",
        "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258",
    },
    {
        "name": "MarketWatch",
        "url": "https://feeds.marketwatch.com/marketwatch/topstories/",
    },
]

# CNN Fear & Greed Index
FEAR_GREED_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"

# 트윗 생성 개수
TWEET_COUNT = 5

# 중복 방지 파일
SENT_TWEETS_FILE = "sent_tweets.json"
