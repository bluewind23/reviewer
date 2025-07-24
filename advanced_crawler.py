"""
고급 네이버 스마트스토어 리뷰 크롤러
IP 차단 우회를 위한 다양한 기법들을 포함
"""

import requests
import pandas as pd
import json
import time
import random
import hashlib
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib3.exceptions import InsecureRequestWarning
from konlpy.tag import Okt
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import LatentDirichletAllocation

# SSL 경고 비활성화
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# --- 설정 부분 ---
PRODUCT_ID = "5753732771"  # 분석하고 싶은 상품의 ID
OUTPUT_FILE_NAME = "reviews.csv"
NUM_TOPICS = 5 # 분류할 주제(토픽)의 개수

# 더 다양한 User-Agent 목록 (실제 브라우저 통계 기반)
USER_AGENTS = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    
    # Chrome on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    
    # Safari on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    
    # Firefox
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/119.0",
    
    # Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    
    # Mobile User Agents
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36"
]

# 프록시 설정 (필요한 경우)
PROXIES = [
    # 무료 프록시 서비스들 (실제 사용시 검증 필요)
    # {'http': 'http://proxy1:port', 'https': 'https://proxy1:port'},
    # 실제 프록시 서버가 있을 경우 여기에 추가
]

class AdvancedNaverCrawler:
    def __init__(self, product_id):
        self.product_id = product_id
        self.session = self._create_session()
        self.request_count = 0
        self.last_request_time = 0
        
    def _create_session(self):
        """고급 세션 설정"""
        session = requests.Session()
        
        # 재시도 전략
        retry_strategy = Retry(
            total=5,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504, 403],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=20
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # 기본 세션 설정
        session.verify = False  # SSL 검증 비활성화 (필요시)
        
        return session
    
    def _get_dynamic_headers(self, referer_url=None):
        """동적 헤더 생성"""
        user_agent = random.choice(USER_AGENTS)
        
        # 브라우저별 헤더 차이점 구현
        headers = {
            "User-Agent": user_agent,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache"
        }
        
        if referer_url:
            headers["Referer"] = referer_url
        
        # Chrome 기반 브라우저인 경우
        if "Chrome" in user_agent and "Edge" not in user_agent:
            headers["sec-ch-ua"] = '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"'
            headers["sec-ch-ua-mobile"] = "?0"
            headers["sec-ch-ua-platform"] = '"Windows"' if "Windows" in user_agent else '"macOS"'
        
        # Firefox인 경우
        if "Firefox" in user_agent:
            headers["DNT"] = "1"
            headers["Upgrade-Insecure-Requests"] = "1"
        
        # 랜덤하게 일부 헤더 추가/제거
        if random.random() > 0.5:
            headers["X-Requested-With"] = "XMLHttpRequest"
        
        if random.random() > 0.7:
            headers["Origin"] = "https://smartstore.naver.com"
            
        return headers
    
    def _intelligent_delay(self):
        """지능적 지연 시스템"""
        current_time = time.time()
        
        # 이전 요청으로부터의 시간 간격 계산
        if self.last_request_time > 0:
            elapsed = current_time - self.last_request_time
            
            # 요청 빈도에 따른 동적 지연
            if self.request_count > 10:  # 많은 요청 후
                min_delay = 3
                max_delay = 8
            elif self.request_count > 5:  # 적당한 요청 후
                min_delay = 2
                max_delay = 5
            else:  # 초기 요청
                min_delay = 1
                max_delay = 3
            
            # 최소 간격 보장
            if elapsed < min_delay:
                additional_delay = min_delay - elapsed + random.uniform(0, max_delay - min_delay)
                print(f"지연 시간: {additional_delay:.2f}초")
                time.sleep(additional_delay)
        
        self.last_request_time = time.time()
        self.request_count += 1
    
    def _generate_session_fingerprint(self):
        """세션 핑거프린트 생성"""
        # 브라우저 세션을 시뮬레이션하기 위한 추가 요청들
        fingerprint_urls = [
            "https://smartstore.naver.com/",
            f"https://smartstore.naver.com/i/v1/products/{self.product_id}"
        ]
        
        for url in fingerprint_urls:
            try:
                headers = self._get_dynamic_headers()
                response = self.session.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    print(f"핑거프린트 생성: {url}")
                time.sleep(random.uniform(0.5, 2))
            except:
                continue
    
    def get_product_info(self):
        """상품 정보 가져오기 (향상된 버전)"""
        print("상품 정보를 가져오는 중...")
        
        # 세션 핑거프린트 생성
        self._generate_session_fingerprint()
        
        info_url = f"https://smartstore.naver.com/i/v1/products/{self.product_id}/summary"
        
        for attempt in range(5):  # 최대 5번 시도
            try:
                self._intelligent_delay()
                
                headers = self._get_dynamic_headers(
                    referer_url=f"https://smartstore.naver.com/i/v1/products/{self.product_id}"
                )
                
                # 프록시 사용 (설정된 경우)
                proxy = random.choice(PROXIES) if PROXIES else None
                
                response = self.session.get(
                    info_url,
                    headers=headers,
                    proxies=proxy,
                    timeout=15,
                    allow_redirects=True
                )
                
                if response.status_code == 200:
                    try:
                        product_info = response.json()
                        merchant_no = product_info['product']['channel']['channelNo']
                        origin_product_no = product_info['product']['productNo']
                        print(f"✅ 상품 정보 획득: Merchant No: {merchant_no}, Origin Product No: {origin_product_no}")
                        return merchant_no, origin_product_no
                    except (json.JSONDecodeError, KeyError) as e:
                        print(f"❌ 상품 정보 파싱 실패: {e}")
                        return None, None
                        
                elif response.status_code == 429:
                    delay = min(60 * (2 ** attempt), 300)  # 지수 백오프, 최대 5분
                    print(f"⚠️  Rate limit 감지. {delay}초 대기 후 재시도...")
                    time.sleep(delay)
                    
                elif response.status_code == 403:
                    delay = min(120 * (attempt + 1), 600)  # 최대 10분
                    print(f"🚫 접근 거부됨. {delay}초 대기 후 재시도...")
                    time.sleep(delay)
                    
                else:
                    print(f"❌ 예상치 못한 상태 코드: {response.status_code}")
                    if attempt < 4:
                        time.sleep(random.uniform(10, 30))
                        
            except requests.exceptions.RequestException as e:
                print(f"❌ 네트워크 오류 (시도 {attempt + 1}): {e}")
                if attempt < 4:
                    time.sleep(random.uniform(10, 30))
        
        print("❌ 상품 정보를 가져오는데 실패했습니다.")
        return None, None
    
    def crawl_reviews(self):
        """리뷰 크롤링 (향상된 버전)"""
        merchant_no, origin_product_no = self.get_product_info()
        
        if not merchant_no or not origin_product_no:
            return None
            
        all_reviews = []
        page = 1
        consecutive_failures = 0
        max_consecutive_failures = 3
        
        print("리뷰 크롤링을 시작합니다...")
        
        while True:
            url = (
                f"https://smartstore.naver.com/main/products/{origin_product_no}/reviews/writable-reviews"
                f"?page={page}&sort=REVIEW_RANKING"
                f"&merchantNo={merchant_no}"
            )
            
            try:
                self._intelligent_delay()
                
                headers = self._get_dynamic_headers(
                    referer_url=f"https://smartstore.naver.com/i/v1/products/{self.product_id}"
                )
                
                # 프록시 로테이션
                proxy = random.choice(PROXIES) if PROXIES else None
                
                response = self.session.get(
                    url,
                    headers=headers,
                    proxies=proxy,
                    timeout=20
                )
                
                if response.status_code == 200:
                    consecutive_failures = 0  # 성공시 실패 카운트 리셋
                    
                    try:
                        data = response.json()
                        reviews = data.get('contents', [])
                        
                        if not reviews:
                            print("✅ 모든 리뷰를 가져왔습니다.")
                            break
                        
                        for review in reviews:
                            option_text = " / ".join([
                                opt['optionContent'] 
                                for opt in review.get('productOptionContents', []) 
                                if 'optionContent' in opt
                            ])
                            
                            all_reviews.append({
                                'id': review.get('id'),
                                'rating': review.get('reviewScore'),
                                'writer': review.get('writerMemberId'),
                                'date': review.get('createDate'),
                                'content': review.get('reviewContent', ''),
                                'option': option_text,
                            })
                        
                        print(f"📄 {page} 페이지: {len(reviews)}개 리뷰 수집 완료 (총 {len(all_reviews)}개)")
                        page += 1
                        
                    except json.JSONDecodeError as e:
                        print(f"❌ JSON 파싱 오류: {e}")
                        consecutive_failures += 1
                        
                elif response.status_code == 429:
                    print("⚠️  Rate limit 감지. 긴 대기 시간 적용...")
                    time.sleep(random.uniform(120, 180))  # 2-3분 대기
                    consecutive_failures += 1
                    
                elif response.status_code == 403:
                    print("🚫 접근 거부. IP 차단 가능성 높음.")
                    time.sleep(random.uniform(300, 600))  # 5-10분 대기
                    consecutive_failures += 1
                    
                else:
                    print(f"❌ HTTP {response.status_code} 오류")
                    consecutive_failures += 1
                    time.sleep(random.uniform(30, 60))
                
                # 연속 실패 시 중단
                if consecutive_failures >= max_consecutive_failures:
                    print(f"❌ {max_consecutive_failures}회 연속 실패로 중단합니다.")
                    break
                    
            except requests.exceptions.RequestException as e:
                print(f"❌ 네트워크 오류: {e}")
                consecutive_failures += 1
                if consecutive_failures >= max_consecutive_failures:
                    break
                time.sleep(random.uniform(60, 120))
        
        if all_reviews:
            print(f"✅ 총 {len(all_reviews)}개의 리뷰를 수집했습니다.")
            return pd.DataFrame(all_reviews)
        else:
            print("❌ 수집된 리뷰가 없습니다.")
            return None

def analyze_sentiment(text, positive_keywords, negative_keywords):
    """감성 분석 (기존과 동일)"""
    score = 0
    for keyword in positive_keywords:
        if keyword in text:
            score += 1
    for keyword in negative_keywords:
        if keyword in text:
            score -= 1
    
    if score > 0:
        return '긍정'
    elif score < 0:
        return '부정'
    else:
        return '중립'

def topic_modeling(df, num_topics):
    """토픽 모델링 (기존과 동일)"""
    okt = Okt()
    
    def tokenize(text):
        if isinstance(text, str):
            return [token for token in okt.nouns(text) if len(token) > 1]
        return []

    df['tokens'] = df['content'].apply(tokenize)
    
    texts = [" ".join(tokens) for tokens in df['tokens']]

    if not any(texts):
        print("분석할 텍스트가 없습니다. 토픽 모델링을 건너뜁니다.")
        df['topic'] = '분석 불가'
        return df

    vectorizer = TfidfVectorizer(max_features=1000, max_df=0.95, min_df=2)
    tfidf_matrix = vectorizer.fit_transform(texts)
    
    lda = LatentDirichletAllocation(n_components=num_topics, random_state=42)
    lda.fit(tfidf_matrix)
    
    topic_results = lda.transform(tfidf_matrix)
    df['topic'] = topic_results.argmax(axis=1)

    feature_names = vectorizer.get_feature_names_out()
    for topic_idx, topic in enumerate(lda.components_):
        top_keywords = [feature_names[i] for i in topic.argsort()[:-10 - 1:-1]]
        print(f"토픽 #{topic_idx}: {', '.join(top_keywords)}")
        
    return df

if __name__ == '__main__':
    print("🚀 고급 네이버 스마트스토어 리뷰 크롤러 시작")
    print(f"📦 분석 대상 상품 ID: {PRODUCT_ID}")
    
    # 크롤러 인스턴스 생성
    crawler = AdvancedNaverCrawler(PRODUCT_ID)
    
    # 리뷰 크롤링
    review_df = crawler.crawl_reviews()
    
    if review_df is not None and not review_df.empty:
        print("\n📊 데이터 분석을 시작합니다...")
        
        # 감성 분석 키워드
        positive_keywords = ['좋아요', '만족', '추천', '최고', '빠른', '편하고', '예뻐요', '가볍고', '튼튼', '잘', '맘에']
        negative_keywords = ['불편', '별로', '실망', '아쉬', '불만', '느린', '무거', '약한', '문제', '고장']
        
        # 감성 분석
        review_df['sentiment'] = review_df['content'].apply(
            lambda x: analyze_sentiment(x, positive_keywords, negative_keywords)
        )
        
        print("\n--- 📈 감성 분석 결과 ---")
        print(review_df['sentiment'].value_counts())
        
        # 토픽 모델링
        print("\n--- 🏷️  토픽 모델링 결과 ---")
        review_df = topic_modeling(review_df, NUM_TOPICS)
        
        # 결과 저장
        review_df.to_csv(OUTPUT_FILE_NAME, index=False, encoding='utf-8-sig')
        print(f"\n✅ 분석 완료! 결과가 '{OUTPUT_FILE_NAME}' 파일로 저장되었습니다.")
        
        # 결과 미리보기
        print("\n--- 📋 결과 미리보기 ---")
        print(review_df.head())
        
        # 통계 정보
        print(f"\n--- 📊 수집 통계 ---")
        print(f"총 리뷰 수: {len(review_df)}")
        print(f"평균 평점: {review_df['rating'].mean():.2f}")
        print(f"긍정 리뷰: {len(review_df[review_df['sentiment'] == '긍정'])}")
        print(f"부정 리뷰: {len(review_df[review_df['sentiment'] == '부정'])}")
        print(f"중립 리뷰: {len(review_df[review_df['sentiment'] == '중립'])}")
        
    else:
        print("❌ 크롤링된 리뷰가 없어 분석을 진행하지 않습니다.")
        print("\n🔧 문제 해결 방법:")
        print("1. 상품 ID가 올바른지 확인")
        print("2. 네트워크 연결 상태 확인")
        print("3. 프록시 설정 추가 고려")
        print("4. 더 긴 대기 시간 설정")