"""
스텔스 네이버 스마트스토어 리뷰 크롤러
극도로 강화된 IP 차단 우회 기법들을 포함
"""

import requests
import pandas as pd
import json
import time
import random
import hashlib
import base64
from datetime import datetime
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
NUM_TOPICS = 5

# 극도로 다양한 User-Agent 목록 (최신 브라우저 통계 기반)
STEALTH_USER_AGENTS = [
    # 한국에서 많이 사용되는 브라우저들
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
    
    # 모바일 브라우저들 (한국 선호도 높음)
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    
    # 태블릿
    "Mozilla/5.0 (iPad; CPU OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
]

# 무료 프록시 서버들 (실제 사용시 검증 필요)
FREE_PROXIES = [
    # 여기에 실제 작동하는 프록시 주소들을 추가
    # {'http': 'http://proxy:port', 'https': 'https://proxy:port'},
]

class StealthNaverCrawler:
    def __init__(self, product_id):
        self.product_id = product_id
        self.session = None
        self.request_count = 0
        self.last_request_time = 0
        self.current_proxy = None
        self.failed_proxies = set()
        self.session_start_time = time.time()
        
    def _create_stealth_session(self):
        """극도로 은밀한 세션 생성"""
        session = requests.Session()
        
        # 매우 관대한 재시도 전략
        retry_strategy = Retry(
            total=10,  # 최대 10번 재시도
            backoff_factor=3,  # 3초씩 증가
            status_forcelist=[403, 429, 500, 502, 503, 504, 520, 521, 522, 523, 524],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=20,
            pool_maxsize=50,
            pool_block=True
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # 고급 세션 설정
        session.verify = False
        session.trust_env = False
        session.max_redirects = 10
        
        return session
    
    def _rotate_proxy(self):
        """프록시 로테이션"""
        if not FREE_PROXIES:
            return None
            
        available_proxies = [p for p in FREE_PROXIES if str(p) not in self.failed_proxies]
        
        if available_proxies:
            return random.choice(available_proxies)
        else:
            # 모든 프록시가 실패한 경우 초기화
            self.failed_proxies.clear()
            return random.choice(FREE_PROXIES)
    
    def _generate_stealth_headers(self, referer=None, is_mobile=False):
        """극도로 정교한 스텔스 헤더 생성"""
        user_agent = random.choice(STEALTH_USER_AGENTS)
        is_mobile_ua = "Mobile" in user_agent or "iPhone" in user_agent or "Android" in user_agent
        
        # 기본 헤더
        headers = {
            "User-Agent": user_agent,
            "Accept": "application/json, text/plain, */*" if not is_mobile_ua else "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
        
        # Referer 설정
        if referer:
            headers["Referer"] = referer
        else:
            # 랜덤 Referer 생성
            referers = [
                f"https://smartstore.naver.com/i/v1/products/{self.product_id}",
                "https://search.shopping.naver.com/",
                "https://www.naver.com/",
                "https://m.shopping.naver.com/",
            ]
            headers["Referer"] = random.choice(referers)
        
        # 브라우저별 특화 헤더
        if "Chrome" in user_agent and "Edge" not in user_agent:
            headers.update({
                "sec-ch-ua": '\"Not_A Brand\";v=\"8\", \"Chromium\";v=\"120\", \"Google Chrome\";v=\"120\"',
                "sec-ch-ua-mobile": "?1" if is_mobile_ua else "?0",
                "sec-ch-ua-platform": '\"Android\"' if "Android" in user_agent else ('\"iOS\"' if "iPhone" in user_agent else '\"Windows\"'),
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
            })
        elif "Firefox" in user_agent:
            headers.update({
                "DNT": "1",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
            })
        elif "Safari" in user_agent and "Chrome" not in user_agent:
            headers.update({
                "Accept": "application/json, text/javascript, */*; q=0.01",
            })
        
        # 모바일 특화 헤더
        if is_mobile_ua:
            headers.update({
                "X-Requested-With": "XMLHttpRequest",
                "Origin": "https://m.smartstore.naver.com" if random.random() > 0.5 else "https://smartstore.naver.com",
            })
        
        # 랜덤 추가 헤더들
        random_headers = {}
        
        if random.random() > 0.3:
            random_headers["DNT"] = "1"
        
        if random.random() > 0.4:
            random_headers["X-Forwarded-For"] = f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
        
        if random.random() > 0.5:
            random_headers["X-Real-IP"] = f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
        
        if random.random() > 0.6:
            random_headers["CF-Connecting-IP"] = f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
        
        headers.update(random_headers)
        
        return headers
    
    def _extreme_delay(self):
        """극도로 정교한 지연 시스템"""
        current_time = time.time()
        
        # 세션 지속 시간에 따른 지연 조정
        session_duration = current_time - self.session_start_time
        
        if session_duration > 3600:  # 1시간 이상
            self.session_start_time = current_time
            self.request_count = 0
            print("🔄 세션 리셋 - 새로운 세션 시작")
        
        # 요청 빈도에 따른 지연
        base_delay = 3
        if self.request_count > 50:
            base_delay = 10
        elif self.request_count > 20:
            base_delay = 7
        elif self.request_count > 10:
            base_delay = 5
        
        # 시간대별 지연 (한국 시간 기준)
        current_hour = datetime.now().hour
        if 9 <= current_hour <= 18:  # 업무시간
            time_multiplier = 2.0
        elif 19 <= current_hour <= 23:  # 저녁시간
            time_multiplier = 1.5
        else:  # 새벽/밤
            time_multiplier = 1.0
        
        # 랜덤 지연 계산
        delay = random.uniform(base_delay * time_multiplier, (base_delay + 5) * time_multiplier)
        
        # 이전 요청으로부터의 최소 간격 보장
        if self.last_request_time > 0:
            elapsed = current_time - self.last_request_time
            if elapsed < delay:
                actual_delay = delay - elapsed
                print(f"⏳ {actual_delay:.2f}초 대기 (요청#{self.request_count}, 시간대 계수: {time_multiplier:.1f})")
                time.sleep(actual_delay)
        
        self.last_request_time = time.time()
        self.request_count += 1
    
    def _simulate_human_behavior(self):
        """인간 행동 시뮬레이션"""
        behaviors = [
            self._visit_main_page,
            self._search_random_product,
            self._visit_category_page,
        ]
        
        # 20% 확률로 인간 행동 시뮬레이션
        if random.random() < 0.2:
            behavior = random.choice(behaviors)
            try:
                behavior()
            except:
                pass
    
    def _visit_main_page(self):
        """메인 페이지 방문"""
        try:
            headers = self._generate_stealth_headers()
            self.session.get("https://smartstore.naver.com/", headers=headers, timeout=10)
            time.sleep(random.uniform(2, 5))
        except:
            pass
    
    def _search_random_product(self):
        """랜덤 상품 검색"""
        try:
            keywords = ["패션", "뷰티", "생활", "디지털", "스포츠", "반려동물"]
            keyword = random.choice(keywords)
            headers = self._generate_stealth_headers()
            self.session.get(f"https://search.shopping.naver.com/search/all?query={keyword}", headers=headers, timeout=10)
            time.sleep(random.uniform(1, 3))
        except:
            pass
    
    def _visit_category_page(self):
        """카테고리 페이지 방문"""
        try:
            headers = self._generate_stealth_headers()
            self.session.get("https://shopping.naver.com/category", headers=headers, timeout=10)
            time.sleep(random.uniform(1, 4))
        except:
            pass
    
    def get_product_info_stealth(self):
        """스텔스 상품 정보 획득"""
        print("🕵️  스텔스 모드로 상품 정보 수집 중...")
        
        # 새로운 세션 생성
        self.session = self._create_stealth_session()
        
        # 인간 행동 시뮬레이션
        self._simulate_human_behavior()
        
        info_url = f"https://smartstore.naver.com/i/v1/products/{self.product_id}/summary"
        
        for attempt in range(15):  # 최대 15번 시도
            try:
                self._extreme_delay()
                
                # 프록시 로테이션
                self.current_proxy = self._rotate_proxy()
                
                headers = self._generate_stealth_headers(
                    referer=f"https://smartstore.naver.com/i/v1/products/{self.product_id}"
                )
                
                print(f"🎯 시도 {attempt + 1}: {headers.get('User-Agent', '')[:50]}...")
                
                response = self.session.get(
                    info_url,
                    headers=headers,
                    proxies=self.current_proxy,
                    timeout=30,
                    allow_redirects=True,
                    stream=False
                )
                
                if response.status_code == 200:
                    try:
                        product_info = response.json()
                        merchant_no = product_info['product']['channel']['channelNo']
                        origin_product_no = product_info['product']['productNo']
                        print(f"✅ 상품 정보 획득 성공!")
                        print(f"   📊 Merchant No: {merchant_no}")
                        print(f"   📊 Origin Product No: {origin_product_no}")
                        return merchant_no, origin_product_no
                    except (json.JSONDecodeError, KeyError) as e:
                        print(f"❌ JSON 파싱 실패: {e}")
                        continue
                
                elif response.status_code == 403:
                    if self.current_proxy:
                        self.failed_proxies.add(str(self.current_proxy))
                    delay = min(300 * (attempt + 1), 1800)  # 최대 30분
                    print(f"🚫 403 Forbidden - {delay//60}분 대기...")
                    time.sleep(delay)
                    
                elif response.status_code == 429:
                    delay = min(600 * (2 ** (attempt // 3)), 3600)  # 최대 1시간
                    print(f"⚠️  429 Rate Limit - {delay//60}분 대기...")
                    time.sleep(delay)
                    
                elif response.status_code == 404:
                    print(f"❌ 상품을 찾을 수 없습니다 (404)")
                    return None, None
                    
                else:
                    print(f"❌ HTTP {response.status_code}")
                    time.sleep(random.uniform(30, 120))
                
                # 인간 행동 시뮬레이션 (중간에)
                if attempt % 3 == 0:
                    self._simulate_human_behavior()
                    
            except requests.exceptions.RequestException as e:
                print(f"❌ 네트워크 오류 (시도 {attempt + 1}): {str(e)[:100]}...")
                if self.current_proxy:
                    self.failed_proxies.add(str(self.current_proxy))
                time.sleep(random.uniform(60, 180))
        
        print("❌ 모든 시도 실패 - 상품 정보를 가져올 수 없습니다")
        return None, None
    
    def crawl_reviews_stealth(self):
        """스텔스 리뷰 크롤링"""
        merchant_no, origin_product_no = self.get_product_info_stealth()
        
        if not merchant_no or not origin_product_no:
            return None
        
        all_reviews = []
        page = 1
        consecutive_failures = 0
        max_consecutive_failures = 5
        
        print("🕵️  스텔스 리뷰 크롤링 시작...")
        
        while True:
            url = (
                f"https://smartstore.naver.com/main/products/{origin_product_no}/reviews/writable-reviews"
                f"?page={page}&sort=REVIEW_RANKING"
                f"&merchantNo={merchant_no}"
            )
            
            try:
                self._extreme_delay()
                
                # 프록시 로테이션
                self.current_proxy = self._rotate_proxy()
                
                headers = self._generate_stealth_headers(
                    referer=f"https://smartstore.naver.com/i/v1/products/{self.product_id}"
                )
                
                response = self.session.get(
                    url,
                    headers=headers,
                    proxies=self.current_proxy,
                    timeout=30
                )
                
                if response.status_code == 200:
                    consecutive_failures = 0
                    
                    try:
                        data = response.json()
                        reviews = data.get('contents', [])
                        
                        if not reviews:
                            print("✅ 모든 리뷰 수집 완료!")
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
                        
                        print(f"📝 페이지 {page}: {len(reviews)}개 리뷰 수집 (총 {len(all_reviews)}개)")
                        page += 1
                        
                        # 인간 행동 시뮬레이션 (가끔)
                        if page % 5 == 0:
                            self._simulate_human_behavior()
                        
                    except json.JSONDecodeError as e:
                        print(f"❌ JSON 파싱 오류: {e}")
                        consecutive_failures += 1
                
                elif response.status_code == 403:
                    print("🚫 403 Forbidden - 긴 대기...")
                    if self.current_proxy:
                        self.failed_proxies.add(str(self.current_proxy))
                    time.sleep(random.uniform(600, 1200))  # 10-20분
                    consecutive_failures += 1
                    
                elif response.status_code == 429:
                    print("⚠️  429 Rate Limit - 매우 긴 대기...")
                    time.sleep(random.uniform(1200, 1800))  # 20-30분
                    consecutive_failures += 1
                    
                else:
                    print(f"❌ HTTP {response.status_code}")
                    consecutive_failures += 1
                    time.sleep(random.uniform(120, 300))
                
                if consecutive_failures >= max_consecutive_failures:
                    print(f"❌ {max_consecutive_failures}회 연속 실패로 중단")
                    break
                    
            except requests.exceptions.RequestException as e:
                print(f"❌ 네트워크 오류: {str(e)[:100]}...")
                consecutive_failures += 1
                if consecutive_failures >= max_consecutive_failures:
                    break
                time.sleep(random.uniform(180, 360))
        
        if all_reviews:
            print(f"🎉 총 {len(all_reviews)}개의 리뷰를 수집했습니다!")
            return pd.DataFrame(all_reviews)
        else:
            print("❌ 수집된 리뷰가 없습니다")
            return None


def analyze_sentiment(text, positive_keywords, negative_keywords):
    """감성 분석"""
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
    """토픽 모델링"""
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
    print("🕵️  === 스텔스 네이버 크롤러 시작 ===")
    print(f"🎯 타겟 상품: {PRODUCT_ID}")
    print("⚠️  이 크롤러는 극도로 신중하게 작동합니다. 시간이 오래 걸릴 수 있습니다.")
    
    # 크롤러 생성
    crawler = StealthNaverCrawler(PRODUCT_ID)
    
    # 리뷰 크롤링
    review_df = crawler.crawl_reviews_stealth()
    
    if review_df is not None and not review_df.empty:
        print("\n📊 === 데이터 분석 시작 ===")
        
        # 감성 분석
        positive_keywords = ['좋아요', '만족', '추천', '최고', '빠른', '편하고', '예뻐요', '가볍고', '튼튼', '잘', '맘에']
        negative_keywords = ['불편', '별로', '실망', '아쉬', '불만', '느린', '무거', '약한', '문제', '고장']
        
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
        print(f"\n✅ 분석 완료! 결과가 '{OUTPUT_FILE_NAME}' 파일로 저장되었습니다")
        
        # 통계 정보
        print(f"\n--- 📊 수집 통계 ---")
        print(f"📝 총 리뷰 수: {len(review_df)}")
        print(f"⭐ 평균 평점: {review_df['rating'].mean():.2f}")
        print(f"😊 긍정 리뷰: {len(review_df[review_df['sentiment'] == '긍정'])}")
        print(f"😞 부정 리뷰: {len(review_df[review_df['sentiment'] == '부정'])}")
        print(f"😐 중립 리뷰: {len(review_df[review_df['sentiment'] == '중립'])}")
        
    else:
        print("\n❌ === 크롤링 실패 ===")
        print("🔧 해결 방안:")
        print("1. VPN 사용 고려")
        print("2. 다른 시간대에 재시도 (새벽 2-6시 권장)")
        print("3. 프록시 서버 추가")
        print("4. 상품 ID 확인")