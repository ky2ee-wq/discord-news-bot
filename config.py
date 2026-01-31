import os

# 디스코드 웹훅 URL (환경변수 또는 직접 입력)
DISCORD_WEBHOOK_URL = os.environ.get(
    "DISCORD_WEBHOOK_URL",
    "YOUR_WEBHOOK_URL_HERE"  # 로컬 테스트시 여기에 입력
)

# 구독할 RSS 피드 목록
RSS_FEEDS = [
    {
        "name": "BBC News",
        "url": "http://feeds.bbci.co.uk/news/rss.xml"
    },
    {
        "name": "CNN",
        "url": "http://rss.cnn.com/rss/edition.rss"
    },
    {
        "name": "NPR News",
        "url": "https://feeds.npr.org/1001/rss.xml"
    },
    {
        "name": "The Guardian",
        "url": "https://www.theguardian.com/world/rss"
    },
    # 기술 뉴스가 필요하면 아래 주석 해제
    # {
    #     "name": "TechCrunch",
    #     "url": "https://techcrunch.com/feed/"
    # },
]

# 가져올 뉴스 개수 (전체 피드에서 최신순)
NEWS_COUNT = 3

# 이미 보낸 뉴스를 저장할 파일
SENT_NEWS_FILE = "sent_news.json"
