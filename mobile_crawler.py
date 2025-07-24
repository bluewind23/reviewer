"""
모바일 API 기반 네이버 스마트스토어 리뷰 크롤러
모바일 앱 API 엔드포인트를 활용하여 차단 우회
"""
import requests
import pandas as pd
import json
import time
import random
import uuid
import re
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib3.exceptions import InsecureRequestWarning
from analysis import analyze_sentiment, topic_modeling

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# --- 설정 부분 ---
PRODUCT_ID = "5753732771"
OUTPUT_FILE_NAME = "reviews_mobile.csv"
NUM_TOPICS = 5

MOBILE_USER_AGENTS = [
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
]

MOBILE_ENDPOINTS = {
    'product_summary': 'https://m.smartstore.naver.com/api/products/{product_id}/summary',
    'reviews_v1': 'https://m.smartstore.naver.com/api/products/{product_id}/reviews',
    'reviews_v2': 'https://shopping.naver.com/v1/products/{product_id}/reviews',
}

class MobileNaverCrawler:
    def __init__(self, product_id):
        self.product_id = product_id
        self.session = self._create_mobile_session()
        self.request_count = 0
        
    def _create_mobile_session(self):
        session = requests.Session()
        retry_strategy = Retry(
            total=8, backoff_factor=2,
            status_forcelist=[403, 429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=15, pool_maxsize=30)
        session.mount("https://", adapter)
        session.verify = False
        return session
    
    def _get_mobile_headers(self, referer_url=None):
        headers = {
            "User-Agent": random.choice(MOBILE_USER_AGENTS),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ko-KR,ko;q=0.9",
            "Referer": referer_url or f"https://m.smartstore.naver.com/products/{self.product_id}",
        }
        return headers

    def _mobile_delay(self):
        delay = random.uniform(1.5, 4.0)
        print(f"📱 {delay:.2f}초 대기...")
        time.sleep(delay)
        self.request_count += 1
    
    def get_product_info_mobile(self):
        print("📱 모바일 API로 상품 정보 수집 중...")
        url = MOBILE_ENDPOINTS['product_summary'].format(product_id=self.product_id)
        try:
            response = self.session.get(url, headers=self._get_mobile_headers(), timeout=20)
            response.raise_for_status()
            data = response.json()
            
            product_data = data.get('data', {})
            merchant_no = product_data.get('channel', {}).get('channelNo')
            origin_product_no = product_data.get('productNo')
            
            if merchant_no and origin_product_no:
                print(f"✅ 정보 획득 성공! Merchant No: {merchant_no}, Product No: {origin_product_no}")
                return merchant_no, origin_product_no
            else:
                print("❌ 응답에서 상품 정보를 찾을 수 없습니다.")
                return None, None
        except Exception as e:
            print(f"❌ 모바일 API 상품 정보 수집 실패: {e}")
            return None, None

    def crawl_reviews_mobile(self):
        merchant_no, origin_product_no = self.get_product_info_mobile()
        if not merchant_no or not origin_product_no:
            return None
        
        all_reviews = []
        page = 1
        print("📱 모바일 API로 리뷰 크롤링 시작...")

        while True:
            try:
                self._mobile_delay()
                url = MOBILE_ENDPOINTS['reviews_v1'].format(product_id=origin_product_no) + f"?page={page}&size=20"
                headers = self._get_mobile_headers(referer_url=f"https://m.smartstore.naver.com/products/{origin_product_no}")
                
                response = self.session.get(url, headers=headers, timeout=25)
                response.raise_for_status()
                data = response.json()
                
                reviews = data.get('contents', [])
                if not reviews:
                    print(f"✅ 모든 리뷰 수집 완료 (총 {len(all_reviews)}개)")
                    break
                
                for review in reviews:
                    option_contents = review.get('productOptionContents', [])
                    option_text = " / ".join([opt.get('optionContent', '') for opt in option_contents])
                    all_reviews.append({
                        'id': review.get('id'),
                        'rating': review.get('reviewScore'),
                        'writer': review.get('writerMemberId'),
                        'date': review.get('createDate'),
                        'content': review.get('reviewContent', ''),
                        'option': option_text,
                    })
                
                print(f"📄 페이지 {page}: {len(reviews)}개 리뷰 수집 (총 {len(all_reviews)}개)")
                page += 1
            
            except Exception as e:
                print(f"❌ 페이지 {page} 처리 중 오류: {e}. 크롤링을 중단합니다.")
                break

        return pd.DataFrame(all_reviews) if all_reviews else None

if __name__ == '__main__':
    print("📱 === 모바일 네이버 크롤러 시작 ===")
    print(f"🎯 타겟 상품: {PRODUCT_ID}")
    
    crawler = MobileNaverCrawler(PRODUCT_ID)
    review_df = crawler.crawl_reviews_mobile()
    
    if review_df is not None and not review_df.empty:
        print("\n📊 === 데이터 분석 시작 ===")
        positive_keywords = ['좋아요', '만족', '추천', '최고', '빠른', '편하고', '예뻐요']
        negative_keywords = ['불편', '별로', '실망', '아쉬', '불만', '느린', '무거']
        
        review_df['sentiment'] = review_df['content'].apply(lambda x: analyze_sentiment(x, positive_keywords, negative_keywords))
        review_df = topic_modeling(review_df, NUM_TOPICS)
        
        review_df.to_csv(OUTPUT_FILE_NAME, index=False, encoding='utf-8-sig')
        print(f"\n✅ 분석 완료! 결과가 '{OUTPUT_FILE_NAME}' 파일로 저장되었습니다.")
    else:
        print("\n❌ === 크롤링 실패 ===")