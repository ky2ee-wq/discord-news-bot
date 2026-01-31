import os

# 디스코드 웹훅 URL (환경변수 또는 직접 입력)
DISCORD_WEBHOOK_URL = os.environ.get(
    "DISCORD_WEBHOOK_URL",
    "YOUR_WEBHOOK_URL_HERE"  # 로컬 테스트시 여기에 입력
)

# 구독할 RSS 피드 목록 (텍스트 기사 위주)
RSS_FEEDS = [
    {
        "name": "AP News",
        "url": "https://apnews.com/world-news.rss"
    },
    {
        "name": "NYTimes World",
        "url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"
    },
    {
        "name": "The Guardian",
        "url": "https://www.theguardian.com/world/rss"
    },
    {
        "name": "Al Jazeera",
        "url": "https://www.aljazeera.com/xml/rss/all.xml"
    },
]

# 가져올 뉴스 개수 (전체 피드에서 최신순)
NEWS_COUNT = 3

# 이미 보낸 뉴스를 저장할 파일
SENT_NEWS_FILE = "sent_news.json"
