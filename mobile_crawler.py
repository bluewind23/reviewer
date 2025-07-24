"""
모바일 API 기반 네이버 스마트스토어 리뷰 크롤러
모바일 앱 API 엔드포인트를 활용하여 차단 우회
"""

import requests
import pandas as pd
import json
import time
import random
import hashlib
import uuid
import re
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib3.exceptions import InsecureRequestWarning
# 분석 모듈 import
from analysis import analyze_sentiment, topic_modeling

# SSL 경고 비활성화
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# --- 설정 부분 ---
PRODUCT_ID = "5753732771"
OUTPUT_FILE_NAME = "reviews_mobile.csv"
NUM_TOPICS = 5

MOBILE_USER_AGENTS = [
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; LM-G900N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.6 Mobile/15E148 Safari/604.1",
    "NAVER(inapp; search; 1200; 12.13.1; SAMSUNG-SM-G998B)",
    "NAVER(inapp; search; 1200; 12.13.1; iPhone15,2)",
    "NaverBot(inapp; search; 1200; 12.13.1)",
]

MOBILE_ENDPOINTS = {
    'product_info': 'https://m.smartstore.naver.com/api/products/{product_id}',
    'product_summary': 'https://m.smartstore.naver.com/api/products/{product_id}/summary',
    'reviews': 'https://m.smartstore.naver.com/api/products/{product_id}/reviews',
    'reviews_v2': 'https://shopping.naver.com/v1/products/{product_id}/reviews',
    'app_api': 'https://apis.naver.com/shopping/products/{product_id}/reviews',
}

class MobileNaverCrawler:
    def __init__(self, product_id):
        self.product_id = product_id
        self.session = self._create_mobile_session()
        self.device_id = self._generate_device_id()
        self.app_version = self._get_random_app_version()
        self.request_count = 0
        
    def _create_mobile_session(self):
        session = requests.Session()
        retry_strategy = Retry(
            total=8,
            backoff_factor=2,
            status_forcelist=[403, 429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST"]
        )
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=15,
            pool_maxsize=30
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.verify = False
        return session
    
    def _generate_device_id(self):
        return str(uuid.uuid4()).replace('-', '')
    
    def _get_random_app_version(self):
        versions = ["12.13.1", "12.12.5", "12.11.8", "12.10.3", "11.9.7", "11.8.2", "11.7.9"]
        return random.choice(versions)
    
    def _get_mobile_headers(self, endpoint_type="api"):
        user_agent = random.choice(MOBILE_USER_AGENTS)
        headers = {
            "User-Agent": user_agent,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ko-KR,ko;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
        
        if "NAVER" in user_agent or endpoint_type == "app":
            headers.update({
                "X-Naver-Client-Id": self._generate_client_id(),
                "X-Naver-Client-Secret": self._generate_client_secret(),
                "X-Device-Id": self.device_id,
                "X-App-Version": self.app_version,
                "X-Platform": "Android" if "Android" in user_agent else "iOS",
                "X-Timestamp": str(int(time.time())),
            })
        
        if endpoint_type == "mobile_web":
            headers.update({
                "Referer": f"https://m.smartstore.naver.com/products/{self.product_id}",
                "Origin": "https://m.smartstore.naver.com",
                "X-Requested-With": "XMLHttpRequest",
            })
        
        if endpoint_type == "shopping":
            headers.update({
                "Referer": f"https://shopping.naver.com/products/{self.product_id}",
                "Origin": "https://shopping.naver.com",
            })
        
        if random.random() > 0.5: headers["DNT"] = "1"
        if random.random() > 0.4:
            headers["Sec-Fetch-Mode"] = "cors"
            headers["Sec-Fetch-Site"] = "same-origin"
        
        return headers
    
    def _generate_client_id(self):
        prefixes = ["naver_", "shopping_", "store_"]
        suffix = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=16))
        return random.choice(prefixes) + suffix
    
    def _generate_client_secret(self):
        return hashlib.md5(f"{self.device_id}{self.app_version}".encode()).hexdigest()
    
    def _mobile_delay(self):
        base_delay = random.uniform(1.5, 4.0)
        if self.request_count % 10 == 0:
            base_delay += random.uniform(5, 15)
            print("📱 앱 사용 휴식 시뮬레이션")
        
        print(f"📱 {base_delay:.2f}초 대기...")
        time.sleep(base_delay)
        self.request_count += 1
    
    def get_product_info_mobile(self):
        print("📱 모바일 API로 상품 정보 수집 중...")
        endpoints_to_try = [
            ("mobile_web", MOBILE_ENDPOINTS['product_summary'].format(product_id=self.product_id)),
            ("shopping", MOBILE_ENDPOINTS['reviews_v2'].format(product_id=self.product_id)),
            ("app", MOBILE_ENDPOINTS['app_api'].format(product_id=self.product_id)),
        ]
        
        for endpoint_type, url in endpoints_to_try:
            try:
                self._mobile_delay()
                headers = self._get_mobile_headers(endpoint_type)
                print(f"🔗 시도: {endpoint_type} API")
                response = self.session.get(url, headers=headers, timeout=20)
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        merchant_no, origin_product_no = None, None
                        
                        if 'product' in data:
                            product = data['product']
                            if 'channel' in product: merchant_no = product['channel'].get('channelNo')
                            origin_product_no = product.get('productNo')
                        
                        elif 'data' in data:
                            product_data = data['data']
                            if isinstance(product_data, dict):
                                merchant_no = product_data.get('merchantNo') or product_data.get('channelNo')
                                origin_product_no = product_data.get('productNo') or product_data.get('originProductNo')
                        
                        elif 'reviews' in data or 'contents' in data:
                            merchant_match = re.search(r'merchantNo[=:](\d+)', str(data))
                            product_match = re.search(r'productNo[=:](\d+)', str(data))
                            if merchant_match and product_match:
                                merchant_no, origin_product_no = merchant_match.group(1), product_match.group(1)
                        
                        if merchant_no and origin_product_no:
                            print(f"✅ {endpoint_type} API로 정보 획득 성공!")
                            print(f"   📊 Merchant No: {merchant_no}")
                            print(f"   📊 Origin Product No: {origin_product_no}")
                            return merchant_no, origin_product_no
                            
                    except json.JSONDecodeError: continue
                elif response.status_code == 404:
                    print(f"❌ {endpoint_type}: 상품을 찾을 수 없음")
                    continue
                else:
                    print(f"⚠️  {endpoint_type}: HTTP {response.status_code}")
                    continue
            except Exception as e:
                print(f"❌ {endpoint_type} API 오류: {str(e)[:100]}...")
                continue
        
        try:
            print("🖥️  데스크톱 API 최종 시도...")
            self._mobile_delay()
            desktop_url = f"https://smartstore.naver.com/i/v1/products/{self.product_id}/summary"
            headers = self._get_mobile_headers("mobile_web")
            headers["User-Agent"] = random.choice([ua for ua in MOBILE_USER_AGENTS if "Mobile" in ua])
            response = self.session.get(desktop_url, headers=headers, timeout=20)
            
            if response.status_code == 200:
                data = response.json()
                merchant_no = data['product']['channel']['channelNo']
                origin_product_no = data['product']['productNo']
                print(f"✅ 데스크톱 API로 정보 획득!")
                print(f"   📊 Merchant No: {merchant_no}")
                print(f"   📊 Origin Product No: {origin_product_no}")
                return merchant_no, origin_product_no
        except Exception as e:
            print(f"❌ 데스크톱 API 실패: {e}")
        
        print("❌ 모든 방법 실패 - 상품 정보를 가져올 수 없습니다")
        return None, None
    
    def crawl_reviews_mobile(self):
        merchant_no, origin_product_no = self.get_product_info_mobile()
        if not merchant_no or not origin_product_no: return None
        
        all_reviews, page, max_failures, failure_count = [], 1, 5, 0
        print("📱 모바일 API로 리뷰 크롤링 시작...")
        
        review_apis = [
            ("mobile_web", f"https://m.smartstore.naver.com/api/products/{origin_product_no}/reviews"),
            ("desktop_mobile", f"https://smartstore.naver.com/main/products/{origin_product_no}/reviews/writable-reviews"),
            ("shopping", f"https://shopping.naver.com/v1/products/{origin_product_no}/reviews"),
        ]
        
        for api_type, base_url in review_apis:
            print(f"🔄 {api_type} API 시도...")
            page, api_reviews, api_failures = 1, [], 0
            
            while api_failures < 3:
                try:
                    self._mobile_delay()
                    if api_type == "mobile_web": url = f"{base_url}?page={page}&size=20"
                    elif api_type == "shopping": url = f"{base_url}?page={page}&size=20&sort=latest"
                    else: url = f"{base_url}?page={page}&sort=REVIEW_RANKING&merchantNo={merchant_no}"
                    
                    headers = self._get_mobile_headers(api_type.split('_')[0])
                    response = self.session.get(url, headers=headers, timeout=25)
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            reviews = []
                            if 'contents' in data: reviews = data['contents']
                            elif 'data' in data and isinstance(data['data'], list): reviews = data['data']
                            elif 'reviews' in data: reviews = data['reviews']
                            elif isinstance(data, list): reviews = data
                            
                            if not reviews:
                                print(f"✅ {api_type}: 모든 리뷰 수집 완료 ({len(api_reviews)}개)")
                                break
                            
                            for review in reviews:
                                option_text = ""
                                if 'productOptionContents' in review: option_text = " / ".join([opt.get('optionContent', '') for opt in review['productOptionContents'] if opt.get('optionContent')])
                                elif 'options' in review: option_text = " / ".join([opt.get('name', '') for opt in review['options'] if opt.get('name')])
                                api_reviews.append({
                                    'id': review.get('id') or review.get('reviewId'),
                                    'rating': review.get('reviewScore') or review.get('rating') or review.get('score'),
                                    'writer': review.get('writerMemberId') or review.get('writer') or review.get('authorId'),
                                    'date': review.get('createDate') or review.get('createdAt') or review.get('date'),
                                    'content': review.get('reviewContent') or review.get('content') or review.get('text', ''),
                                    'option': option_text,
                                })
                            
                            print(f"📄 {api_type} 페이지 {page}: {len(reviews)}개 리뷰 (총 {len(api_reviews)}개)")
                            page += 1
                            api_failures = 0
                        except json.JSONDecodeError:
                            print(f"❌ {api_type}: JSON 파싱 실패")
                            api_failures += 1; break
                    elif response.status_code == 404:
                        print(f"❌ {api_type}: 데이터 없음"); break
                    else:
                        print(f"⚠️  {api_type}: HTTP {response.status_code}")
                        api_failures += 1; time.sleep(random.uniform(5, 15))
                except Exception as e:
                    print(f"❌ {api_type} 오류: {str(e)[:100]}...")
                    api_failures += 1; time.sleep(random.uniform(10, 20))
            
            if api_reviews:
                all_reviews.extend(api_reviews)
                print(f"✅ {api_type}에서 {len(api_reviews)}개 리뷰 수집 성공!")
                break
        
        if all_reviews:
            print(f"🎉 총 {len(all_reviews)}개의 리뷰를 수집했습니다!")
            return pd.DataFrame(all_reviews)
        else:
            print("❌ 모든 모바일 API에서 리뷰 수집 실패")
            return None

if __name__ == '__main__':
    print("📱 === 모바일 네이버 크롤러 시작 ===")
    print(f"🎯 타겟 상품: {PRODUCT_ID}")
    print("📱 모바일 API와 앱 시뮬레이션을 사용합니다")
    
    crawler = MobileNaverCrawler(PRODUCT_ID)
    review_df = crawler.crawl_reviews_mobile()
    
    if review_df is not None and not review_df.empty:
        print("\n📊 === 데이터 분석 시작 ===")
        review_df = review_df.dropna(subset=['content'])
        review_df = review_df[review_df['content'].str.len() > 0]
        
        if review_df.empty:
            print("❌ 유효한 리뷰 데이터가 없습니다")
        else:
            positive_keywords = ['좋아요', '만족', '추천', '최고', '빠른', '편하고', '예뻐요', '가볍고', '튼튼', '잘', '맘에']
            negative_keywords = ['불편', '별로', '실망', '아쉬', '불만', '느린', '무거', '약한', '문제', '고장']
            
            review_df['sentiment'] = review_df['content'].apply(lambda x: analyze_sentiment(x, positive_keywords, negative_keywords))
            
            print("\n--- 📈 감성 분석 결과 ---")
            print(review_df['sentiment'].value_counts())
            
            print("\n--- 🏷️  토픽 모델링 결과 ---")
            review_df = topic_modeling(review_df, NUM_TOPICS)
            
            review_df.to_csv(OUTPUT_FILE_NAME, index=False, encoding='utf-8-sig')
            print(f"\n✅ 분석 완료! 결과가 '{OUTPUT_FILE_NAME}' 파일로 저장되었습니다")
            
            print(f"\n--- 📊 수집 통계 ---")
            print(f"📝 총 리뷰 수: {len(review_df)}")
            if 'rating' in review_df.columns and review_df['rating'].notna().any():
                print(f"⭐ 평균 평점: {review_df['rating'].mean():.2f}")
            print(f"😊 긍정 리뷰: {len(review_df[review_df['sentiment'] == '긍정'])}")
            print(f"😞 부정 리뷰: {len(review_df[review_df['sentiment'] == '부정'])}")
            print(f"😐 중립 리뷰: {len(review_df[review_df['sentiment'] == '중립'])}")
    
    else:
        print("\n❌ === 크롤링 실패 ===")
        print("🔧 해결 방안:")
        print("1. 상품 ID 확인")
        print("2. 네트워크 연결 상태 확인")
        print("3. 다른 시간대에 재시도")
        print("4. VPN 사용 고려")