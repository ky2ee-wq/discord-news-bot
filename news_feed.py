import json
import os
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser
import requests

from config import DISCORD_WEBHOOK_URL, NEWS_COUNT, RSS_FEEDS, SENT_NEWS_FILE


def load_sent_news():
    """이미 보낸 뉴스 ID 목록을 불러옵니다."""
    if os.path.exists(SENT_NEWS_FILE):
        with open(SENT_NEWS_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_sent_news(sent_news):
    """보낸 뉴스 ID 목록을 저장합니다."""
    with open(SENT_NEWS_FILE, "w", encoding="utf-8") as f:
        json.dump(list(sent_news), f, ensure_ascii=False)


def parse_date(date_str):
    """날짜 문자열을 datetime 객체로 변환합니다."""
    try:
        return parsedate_to_datetime(date_str)
    except Exception:
        return datetime.now(timezone.utc)


def fetch_all_news():
    """모든 피드에서 뉴스를 수집합니다."""
    all_news = []

    for feed_config in RSS_FEEDS:
        feed_name = feed_config["name"]
        feed_url = feed_config["url"]

        print(f"  {feed_name} 피드 수집 중...")

        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:10]:  # 각 피드에서 최대 10개씩 수집
                news_id = entry.get("id") or entry.get("link")
                published_str = entry.get("published", "")
                published_dt = parse_date(published_str)

                # 뉴스 요약 가져오기
                summary = entry.get("summary") or entry.get("description") or ""
                # HTML 태그 제거
                summary = re.sub(r'<[^>]+>', '', summary).strip()
                summary = summary[:1000] if summary else ""  # 최대 1000자

                all_news.append({
                    "id": news_id,
                    "title": entry.get("title", "제목 없음"),
                    "link": entry.get("link", ""),
                    "summary": summary,
                    "published": published_str,
                    "published_dt": published_dt,
                    "source": feed_name
                })
        except Exception as e:
            print(f"    오류 발생: {e}")

    # 최신순으로 정렬
    all_news.sort(key=lambda x: x["published_dt"], reverse=True)
    return all_news


def send_to_discord(webhook_url, embed):
    """디스코드 웹훅으로 메시지를 보냅니다."""
    data = {"embeds": [embed]}
    response = requests.post(
        webhook_url,
        json=data,
        headers={"Content-Type": "application/json"}
    )
    return response.status_code == 204


def create_embed(title, url, source_name, summary=""):
    """디스코드 임베드 메시지를 생성합니다."""
    embed = {
        "title": title[:256],
        "url": url,
        "color": 0x3498db,
        "footer": {"text": source_name},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    if summary:
        embed["description"] = summary[:4096]  # 디스코드 제한
    return embed


def main():
    print(f"[{datetime.now()}] 뉴스 피드 확인 시작...")

    if DISCORD_WEBHOOK_URL == "YOUR_WEBHOOK_URL_HERE":
        print("오류: config.py에서 DISCORD_WEBHOOK_URL을 설정해주세요.")
        return

    sent_news = load_sent_news()
    all_news = fetch_all_news()

    # 아직 보내지 않은 뉴스만 필터링
    new_news = [n for n in all_news if n["id"] not in sent_news]

    print(f"\n  새 뉴스 {len(new_news)}개 발견, 상위 {NEWS_COUNT}개 전송...")

    sent_count = 0
    for news in new_news[:NEWS_COUNT]:
        embed = create_embed(
            news["title"],
            news["link"],
            news["source"],
            news["summary"]
        )

        if send_to_discord(DISCORD_WEBHOOK_URL, embed):
            sent_news.add(news["id"])
            sent_count += 1
            print(f"    [OK] [{news['source']}] {news['title'][:40]}...")
        else:
            print(f"    [FAIL] {news['title'][:40]}...")

    save_sent_news(sent_news)
    print(f"\n[{datetime.now()}] 완료! {sent_count}개 전송")


if __name__ == "__main__":
    main()
