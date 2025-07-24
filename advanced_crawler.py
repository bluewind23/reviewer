"""
고급 네이버 스마트스토어 리뷰 크롤러
IP 차단 우회를 위한 다양한 기법들을 포함
"""

import requests
import pandas as pd
import json
import time
import random
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib3.exceptions import InsecureRequestWarning
from analysis import analyze_sentiment, topic_modeling

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# --- 설정 부분 ---
PRODUCT_ID = "5753732771"
OUTPUT_FILE_NAME = "reviews_advanced.csv"
NUM_TOPICS = 5

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

class AdvancedNaverCrawler:
    def __init__(self, product_id):
        self.product_id = product_id
        self.session = self._create_session()
        
    def _create_session(self):
        session = requests.Session()
        retry_strategy = Retry(
            total=5, backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504, 403],
            allowed_methods=["GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.verify = False
        return session
    
    def _get_dynamic_headers(self, referer_url=None):
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "application/json, text/plain, */*",
            "Referer": referer_url or f"https://smartstore.naver.com/products/{self.product_id}"
        }
        return headers
    
    def get_product_info(self):
        print("상품 정보를 가져오는 중...")
        info_url = f"https://smartstore.naver.com/i/v1/products/{self.product_id}/summary"
        status_code = None
        try:
            response = self.session.get(info_url, headers=self._get_dynamic_headers(), timeout=15)
            status_code = response.status_code
            response.raise_for_status()
            product_info = response.json()

            product_data = product_info.get('product', {})
            merchant_no = product_data.get('channel', {}).get('channelNo')
            origin_product_no = product_data.get('productNo')

            if not merchant_no or not origin_product_no:
                print("❌ 상품 정보(merchant_no, origin_product_no)를 찾을 수 없습니다.")
                return None, None, status_code
            
            print(f"✅ 상품 정보 획득: Merchant No: {merchant_no}, Product No: {origin_product_no}")
            return merchant_no, origin_product_no, status_code

        except requests.exceptions.HTTPError as e:
            print(f"❌ 상품 정보 획득 HTTP 오류: {e}")
            return None, None, e.response.status_code
        except Exception as e:
            print(f"❌ 상품 정보 획득 실패: {e}")
            return None, None, status_code

    def crawl_reviews(self):
        merchant_no, origin_product_no, _ = self.get_product_info()
        if not merchant_no or not origin_product_no:
            return None
            
        all_reviews, page = [], 1
        print("리뷰 크롤링을 시작합니다...")
        
        while True:
            url = f"https://smartstore.naver.com/main/products/{origin_product_no}/reviews/writable-reviews?page={page}&sort=REVIEW_RANKING&merchantNo={merchant_no}"
            try:
                time.sleep(random.uniform(2, 5))
                response = self.session.get(url, headers=self._get_dynamic_headers(), timeout=20)
                response.raise_for_status()
                data = response.json()
                reviews = data.get('contents', [])
                
                if not reviews:
                    print("✅ 모든 리뷰를 가져왔습니다.")
                    break
                
                for review in reviews:
                    option_contents = review.get('productOptionContents', [])
                    option_text = " / ".join([opt.get('optionContent', '') for opt in option_contents])
                    all_reviews.append({
                        'id': review.get('id'), 'rating': review.get('reviewScore'),
                        'writer': review.get('writerMemberId'), 'date': review.get('createDate'),
                        'content': review.get('reviewContent', ''), 'option': option_text,
                    })
                
                print(f"📄 {page} 페이지: {len(reviews)}개 리뷰 수집 완료 (총 {len(all_reviews)}개)")
                page += 1
            
            except Exception as e:
                print(f"❌ 오류로 크롤링 중단: {e}")
                break
        
        return pd.DataFrame(all_reviews) if all_reviews else None

if __name__ == '__main__':
    crawler = AdvancedNaverCrawler(PRODUCT_ID)
    review_df = crawler.crawl_reviews()
    if review_df is not None and not review_df.empty:
        positive_keywords = ['좋아요', '만족', '추천', '최고', '빠른']
        negative_keywords = ['불편', '별로', '실망', '아쉬', '불만']
        review_df['sentiment'] = review_df['content'].apply(lambda x: analyze_sentiment(x, positive_keywords, negative_keywords))
        review_df = topic_modeling(review_df, NUM_TOPICS)
        review_df.to_csv(OUTPUT_FILE_NAME, index=False, encoding='utf-8-sig')
        print(f"\n✅ 분석 완료! 결과가 '{OUTPUT_FILE_NAME}' 파일로 저장되었습니다.")