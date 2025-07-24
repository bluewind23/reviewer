"""
스텔스 네이버 스마트스토어 리뷰 크롤러
극도로 강화된 IP 차단 우회 기법들을 포함
"""
import requests
import pandas as pd
import json
import time
import random
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib3.exceptions import InsecureRequestWarning
from analysis import analyze_sentiment, topic_modeling

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

PRODUCT_ID = "5753732771"
OUTPUT_FILE_NAME = "reviews_stealth.csv"
NUM_TOPICS = 5

STEALTH_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36",
]

FREE_PROXIES = []

class StealthNaverCrawler:
    def __init__(self, product_id):
        self.product_id = product_id
        self.session = self._create_stealth_session()
        self.request_count = 0
        self.last_request_time = 0
        self.current_proxy = None
        self.failed_proxies = set()
        
    def _create_stealth_session(self):
        session = requests.Session()
        retry_strategy = Retry(
            total=10, backoff_factor=3,
            status_forcelist=[403, 429, 500, 502, 503, 504],
            allowed_methods={"GET", "POST", "OPTIONS"}
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.verify = False
        return session
    
    def _rotate_proxy(self):
        if not FREE_PROXIES: return None
        available = [p for p in FREE_PROXIES if str(p) not in self.failed_proxies]
        if not available: self.failed_proxies.clear(); available = FREE_PROXIES
        self.current_proxy = random.choice(available) if available else None
        return self.current_proxy
    
    def _generate_stealth_headers(self, referer=None):
        user_agent = random.choice(STEALTH_USER_AGENTS)
        is_mobile = "Mobile" in user_agent or "iPhone" in user_agent or "Android" in user_agent
        headers = {
            "User-Agent": user_agent,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": referer or "https://shopping.naver.com/",
            "Origin": "https://smartstore.naver.com",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
        }
        if is_mobile: headers["X-Requested-With"] = "XMLHttpRequest"
        return headers
    
    def _extreme_delay(self):
        delay = random.uniform(5, 12)
        print(f"⏳ {delay:.2f}초 대기 (스텔스 모드)...")
        time.sleep(delay)

    def get_product_info_stealth(self):
        print("🕵️  스텔스 모드로 상품 정보 수집 중...")
        info_url = f"https://smartstore.naver.com/i/v1/products/{self.product_id}/summary"
        for attempt in range(5):
            try:
                self._extreme_delay()
                response = self.session.get(info_url, headers=self._generate_stealth_headers(), proxies=self._rotate_proxy(), timeout=30)
                
                if response.status_code == 200:
                    product_info = response.json()
                    product_data = product_info.get('product', {})
                    merchant_no = product_data.get('channel', {}).get('channelNo')
                    origin_product_no = product_data.get('productNo')
                    
                    if merchant_no and origin_product_no:
                        print(f"✅ 상품 정보 획득 성공! (시도 {attempt + 1})")
                        return merchant_no, origin_product_no, 200
                else:
                    print(f"❌ 정보 획득 시도 {attempt + 1} 실패 - 상태 코드: {response.status_code}")
                    if self.current_proxy: self.failed_proxies.add(str(self.current_proxy))

            except Exception as e:
                print(f"❌ 정보 획득 시도 {attempt + 1} 중 네트워크 오류: {e}")
                if self.current_proxy: self.failed_proxies.add(str(self.current_proxy))
        
        print("❌ 모든 시도 실패 - 상품 정보를 가져올 수 없습니다")
        return None, None, None

    def crawl_reviews_stealth(self):
        merchant_no, origin_product_no, _ = self.get_product_info_stealth()
        if not merchant_no or not origin_product_no:
            return None
        
        all_reviews, page = [], 1
        print("🕵️  스텔스 리뷰 크롤링 시작...")
        
        while True:
            try:
                self._extreme_delay()
                url = f"https://smartstore.naver.com/main/products/{origin_product_no}/reviews/writable-reviews?page={page}&sort=REVIEW_RANKING&merchantNo={merchant_no}"
                response = self.session.get(url, headers=self._generate_stealth_headers(), timeout=30)
                
                if response.status_code != 200:
                    print(f"❌ 페이지 {page} 로드 실패, 상태 코드: {response.status_code}. 크롤링을 중단합니다.")
                    break

                data = response.json()
                reviews = data.get('contents', [])
                if not reviews:
                    print("✅ 모든 리뷰 수집 완료!")
                    break
                
                for review in reviews:
                    option_contents = review.get('productOptionContents', [])
                    option_text = " / ".join([opt.get('optionContent', '') for opt in option_contents])
                    all_reviews.append({
                        'id': review.get('id'), 'rating': review.get('reviewScore'),
                        'writer': review.get('writerMemberId'), 'date': review.get('createDate'),
                        'content': review.get('reviewContent', ''), 'option': option_text,
                    })
                print(f"📝 페이지 {page}: {len(reviews)}개 리뷰 수집 (총 {len(all_reviews)}개)")
                page += 1
            except Exception as e:
                print(f"❌ 오류로 크롤링 중단: {e}")
                break
                
        return pd.DataFrame(all_reviews) if all_reviews else None

if __name__ == '__main__':
    print("🕵️  === 스텔스 네이버 크롤러 시작 ===")
    print(f"🎯 타겟 상품: {PRODUCT_ID}")
    
    crawler = StealthNaverCrawler(PRODUCT_ID)
    review_df = crawler.crawl_reviews_stealth()
    
    if review_df is not None and not review_df.empty:
        print("\n📊 === 데이터 분석 시작 ===")
        positive_keywords = ['좋아요', '만족', '추천', '최고', '빠른']
        negative_keywords = ['불편', '별로', '실망', '아쉬', '불만']
        review_df['sentiment'] = review_df['content'].apply(lambda x: analyze_sentiment(x, positive_keywords, negative_keywords))
        review_df = topic_modeling(review_df, NUM_TOPICS)
        review_df.to_csv(OUTPUT_FILE_NAME, index=False, encoding='utf-8-sig')
        print(f"\n✅ 분석 완료! 결과가 '{OUTPUT_FILE_NAME}' 파일로 저장되었습니다.")
    else:
        print("\n❌ === 크롤링 실패 ===")