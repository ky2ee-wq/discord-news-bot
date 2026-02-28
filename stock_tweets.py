import json
import os
import re
from datetime import datetime, timezone

import feedparser
import requests
import yfinance as yf
from openai import OpenAI

from stock_config import (
    DISCORD_WEBHOOK_URL,
    FEAR_GREED_URL,
    FINANCIAL_RSS_FEEDS,
    INDICES,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    SENT_TWEETS_FILE,
    STOCKS,
    TWEET_COUNT,
)

# 금지 표현 목록
BANNED_PHRASES = [
    "buy", "sell", "should", "recommend", "prediction",
    "will reach", "will hit", "guaranteed", "must buy",
    "to the moon", "not financial advice", "NFA", "DYOR",
]


def load_sent_tweets():
    """이미 보낸 트윗 목록을 불러옵니다."""
    if os.path.exists(SENT_TWEETS_FILE):
        with open(SENT_TWEETS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_sent_tweets(sent_tweets):
    """보낸 트윗 목록을 저장합니다. 최근 100개만 유지."""
    with open(SENT_TWEETS_FILE, "w", encoding="utf-8") as f:
        json.dump(sent_tweets[-100:], f, ensure_ascii=False)


def fetch_market_data():
    """yfinance로 주요 지수/종목 데이터를 수집합니다."""
    print("  시장 데이터 수집 중...")
    market_data = {"indices": {}, "stocks": {}}

    # 지수 데이터
    for symbol, name in INDICES.items():
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="2d")
            if len(hist) >= 2:
                prev_close = hist["Close"].iloc[-2]
                curr_close = hist["Close"].iloc[-1]
                change_pct = ((curr_close - prev_close) / prev_close) * 100
                market_data["indices"][name] = {
                    "price": round(curr_close, 2),
                    "change_pct": round(change_pct, 2),
                }
            elif len(hist) == 1:
                market_data["indices"][name] = {
                    "price": round(hist["Close"].iloc[-1], 2),
                    "change_pct": 0,
                }
        except Exception as e:
            print(f"    {name} 데이터 수집 실패: {e}")

    # 종목 데이터
    for symbol in STOCKS:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="2d")
            if len(hist) >= 2:
                prev_close = hist["Close"].iloc[-2]
                curr_close = hist["Close"].iloc[-1]
                change_pct = ((curr_close - prev_close) / prev_close) * 100
                market_data["stocks"][symbol] = {
                    "price": round(curr_close, 2),
                    "change_pct": round(change_pct, 2),
                }
            elif len(hist) == 1:
                market_data["stocks"][symbol] = {
                    "price": round(hist["Close"].iloc[-1], 2),
                    "change_pct": 0,
                }
        except Exception as e:
            print(f"    {symbol} 데이터 수집 실패: {e}")

    print(f"    지수 {len(market_data['indices'])}개, 종목 {len(market_data['stocks'])}개 수집 완료")
    return market_data


def fetch_fear_greed_index():
    """CNN Fear & Greed Index를 조회합니다."""
    print("  Fear & Greed Index 수집 중...")
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(FEAR_GREED_URL, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            score = data.get("fear_and_greed", {}).get("score", None)
            rating = data.get("fear_and_greed", {}).get("rating", None)
            if score is not None:
                print(f"    Fear & Greed: {score:.0f} ({rating})")
                return {"score": round(score), "rating": rating}
    except Exception as e:
        print(f"    Fear & Greed 수집 실패: {e}")
    return None


def fetch_financial_headlines():
    """금융 뉴스 RSS 헤드라인을 수집합니다."""
    print("  금융 뉴스 헤드라인 수집 중...")
    headlines = []

    for feed_config in FINANCIAL_RSS_FEEDS:
        feed_name = feed_config["name"]
        feed_url = feed_config["url"]

        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:
                title = entry.get("title", "")
                if title:
                    headlines.append(f"[{feed_name}] {title}")
        except Exception as e:
            print(f"    {feed_name} 수집 실패: {e}")

    print(f"    헤드라인 {len(headlines)}개 수집 완료")
    return headlines


def build_gpt_prompt(market_data, fear_greed, headlines):
    """수집한 데이터를 GPT 프롬프트로 조립합니다."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # 지수 요약
    index_lines = []
    for name, data in market_data.get("indices", {}).items():
        sign = "+" if data["change_pct"] >= 0 else ""
        index_lines.append(f"- {name}: {data['price']:,.2f} ({sign}{data['change_pct']}%)")

    # 종목 요약
    stock_lines = []
    for symbol, data in market_data.get("stocks", {}).items():
        sign = "+" if data["change_pct"] >= 0 else ""
        stock_lines.append(f"- ${symbol}: ${data['price']:,.2f} ({sign}{data['change_pct']}%)")

    # Fear & Greed
    fg_line = ""
    if fear_greed:
        fg_line = f"CNN Fear & Greed Index: {fear_greed['score']} ({fear_greed['rating']})"

    # 헤드라인
    headline_text = "\n".join(f"- {h}" for h in headlines[:10]) if headlines else "No headlines available"

    system_prompt = (
        "You are a stock market tweet writer. Rules:\n"
        "1. Write ONLY facts based on the provided data. NO predictions, NO recommendations.\n"
        "2. Each tweet must be 280 characters or fewer.\n"
        "3. Use cashtags like $AAPL and hashtags like #StockMarket, #SP500, #NASDAQ.\n"
        "4. Vary the style: some data-focused, some headline-based, some sentiment-based.\n"
        "5. NEVER use phrases like 'buy', 'sell', 'should', 'recommend', 'prediction', 'will reach', 'guaranteed'.\n"
        "6. Write in English.\n"
        "7. Make tweets engaging and informative for retail investors.\n"
        "8. Each tweet should cover a different topic or angle."
    )

    user_prompt = (
        f"Date: {today}\n\n"
        f"=== MARKET INDICES ===\n"
        f"{chr(10).join(index_lines) if index_lines else 'No index data'}\n\n"
        f"=== STOCK PRICES ===\n"
        f"{chr(10).join(stock_lines) if stock_lines else 'No stock data'}\n\n"
        f"=== MARKET SENTIMENT ===\n"
        f"{fg_line if fg_line else 'No sentiment data'}\n\n"
        f"=== TOP HEADLINES ===\n"
        f"{headline_text}\n\n"
        f"Generate exactly {TWEET_COUNT} tweets based on the data above. "
        f"Return them as a JSON array of strings, nothing else."
    )

    return system_prompt, user_prompt


def generate_tweets(system_prompt, user_prompt):
    """OpenAI API를 호출하여 트윗을 생성합니다."""
    print("  GPT로 트윗 생성 중...")

    client = OpenAI(api_key=OPENAI_API_KEY)

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.8,
        max_tokens=1500,
    )

    content = response.choices[0].message.content.strip()

    # JSON 블록에서 배열 추출
    json_match = re.search(r'\[.*\]', content, re.DOTALL)
    if json_match:
        tweets = json.loads(json_match.group())
    else:
        raise ValueError(f"GPT 응답에서 JSON 배열을 찾을 수 없습니다: {content[:200]}")

    # 280자 초과 검증 및 금지 표현 필터링
    valid_tweets = []
    for tweet in tweets:
        if len(tweet) > 280:
            print(f"    [SKIP] 280자 초과 ({len(tweet)}자): {tweet[:50]}...")
            continue

        has_banned = False
        tweet_lower = tweet.lower()
        for phrase in BANNED_PHRASES:
            if phrase.lower() in tweet_lower:
                print(f"    [SKIP] 금지 표현 '{phrase}': {tweet[:50]}...")
                has_banned = True
                break

        if not has_banned:
            valid_tweets.append(tweet)

    print(f"    유효한 트윗 {len(valid_tweets)}개 생성 완료")
    return valid_tweets


def send_tweets_to_discord(tweets):
    """트윗 후보를 Discord embed로 전송합니다."""
    print("  Discord로 트윗 전송 중...")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # 헤더 메시지
    header = f"**STOCK TWEET CANDIDATES | {today}**\n\n"

    # 각 트윗을 코드블록으로 포맷
    tweet_blocks = []
    for i, tweet in enumerate(tweets, 1):
        char_count = len(tweet)
        tweet_blocks.append(f"**Tweet {i}** ({char_count}/280 chars)\n```\n{tweet}\n```")

    description = header + "\n".join(tweet_blocks)

    # Discord embed 최대 4096자 제한 체크
    if len(description) > 4096:
        description = description[:4093] + "..."

    embed = {
        "title": "Stock Tweet Candidates",
        "description": description,
        "color": 0x1DA1F2,  # Twitter blue
        "footer": {"text": "Copy and paste to Twitter"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    data = {"embeds": [embed]}
    response = requests.post(
        DISCORD_WEBHOOK_URL,
        json=data,
        headers={"Content-Type": "application/json"},
    )

    if response.status_code == 204:
        print("    Discord 전송 성공!")
        return True
    else:
        print(f"    Discord 전송 실패: {response.status_code} {response.text}")
        return False


def main():
    print(f"[{datetime.now()}] Stock Tweet Generator 시작...")

    if DISCORD_WEBHOOK_URL == "YOUR_WEBHOOK_URL_HERE":
        print("오류: DISCORD_WEBHOOK_URL을 설정해주세요.")
        return

    if OPENAI_API_KEY == "YOUR_OPENAI_API_KEY_HERE":
        print("오류: OPENAI_API_KEY를 설정해주세요.")
        return

    # 1. 데이터 수집
    market_data = fetch_market_data()
    fear_greed = fetch_fear_greed_index()
    headlines = fetch_financial_headlines()

    # 2. 프롬프트 생성
    system_prompt, user_prompt = build_gpt_prompt(market_data, fear_greed, headlines)

    # 3. 트윗 생성
    tweets = generate_tweets(system_prompt, user_prompt)

    if not tweets:
        print("생성된 트윗이 없습니다.")
        return

    # 4. 중복 체크
    sent_tweets = load_sent_tweets()
    new_tweets = [t for t in tweets if t not in sent_tweets]

    if not new_tweets:
        print("모든 트윗이 이미 전송되었습니다.")
        return

    # 5. Discord로 전송
    if send_tweets_to_discord(new_tweets):
        sent_tweets.extend(new_tweets)
        save_sent_tweets(sent_tweets)

    print(f"[{datetime.now()}] 완료! {len(new_tweets)}개 트윗 후보 전송")


if __name__ == "__main__":
    main()
