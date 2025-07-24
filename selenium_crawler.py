"""
Selenium 기반 네이버 스마트스토어 리뷰 크롤러
실제 브라우저를 사용하여 IP 차단을 우회
"""

import pandas as pd
import json
import time
import random
from datetime import datetime
from konlpy.tag import Okt
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import LatentDirichletAllocation

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("⚠️  Selenium이 설치되지 않았습니다.")
    print("설치 명령어: pip install selenium")
    print("Chrome 드라이버도 필요합니다: https://chromedriver.chromium.org/")

# --- 설정 부분 ---
PRODUCT_ID = "5753732771"
OUTPUT_FILE_NAME = "reviews_selenium.csv"
NUM_TOPICS = 5

class SeleniumNaverCrawler:
    def __init__(self, product_id, headless=True):
        if not SELENIUM_AVAILABLE:
            raise ImportError("Selenium이 설치되지 않았습니다.")
        
        self.product_id = product_id
        self.headless = headless
        self.driver = None
        self.wait = None
        
    def _setup_driver(self):
        """브라우저 드라이버 설정"""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless")
        
        # 기본 설정
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        
        # 봇 탐지 우회
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # 랜덤 사용자 에이전트
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]
        chrome_options.add_argument(f"--user-agent={random.choice(user_agents)}")
        
        # 창 크기 랜덤화
        window_sizes = ["1920,1080", "1366,768", "1440,900", "1536,864"]
        chrome_options.add_argument(f"--window-size={random.choice(window_sizes)}")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            
            # 봇 탐지 우회 스크립트
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.wait = WebDriverWait(self.driver, 30)
            
            print("✅ Chrome 브라우저 초기화 완료")
            return True
            
        except Exception as e:
            print(f"❌ 브라우저 초기화 실패: {e}")
            print("Chrome 드라이버가 설치되어 있는지 확인하세요.")
            return False
    
    def _human_like_scroll(self):
        """인간과 같은 스크롤 동작"""
        # 랜덤한 스크롤 패턴
        scroll_patterns = [
            # 천천히 아래로
            lambda: self.driver.execute_script("window.scrollBy(0, 300);"),
            # 빠르게 아래로
            lambda: self.driver.execute_script("window.scrollBy(0, 800);"),
            # 조금 위로
            lambda: self.driver.execute_script("window.scrollBy(0, -200);"),
            # 페이지 끝까지
            lambda: self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);"),
        ]
        
        for _ in range(random.randint(2, 5)):
            random.choice(scroll_patterns)()
            time.sleep(random.uniform(0.5, 2.0))
    
    def _human_like_delay(self):
        """인간과 같은 지연"""
        delay = random.uniform(2, 5)
        print(f"⏳ {delay:.2f}초 대기...")
        time.sleep(delay)
    
    def _simulate_human_activity(self):
        """인간 활동 시뮬레이션"""
        activities = [
            self._random_mouse_move,
            self._random_scroll,
            self._pause_and_read,
        ]
        
        if random.random() < 0.3:  # 30% 확률로 활동
            activity = random.choice(activities)
            try:
                activity()
            except:
                pass
    
    def _random_mouse_move(self):
        """랜덤 마우스 이동"""
        try:
            actions = ActionChains(self.driver)
            actions.move_by_offset(random.randint(-100, 100), random.randint(-100, 100))
            actions.perform()
            time.sleep(random.uniform(0.1, 0.5))
        except:
            pass
    
    def _random_scroll(self):
        """랜덤 스크롤"""
        scroll_amount = random.randint(100, 500)
        self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        time.sleep(random.uniform(0.5, 1.5))
    
    def _pause_and_read(self):
        """읽기 시뮬레이션"""
        time.sleep(random.uniform(3, 8))
    
    def get_product_info(self):
        """상품 정보 가져오기"""
        print("🔍 브라우저로 상품 정보 수집 중...")
        
        try:
            # 상품 페이지 접속
            product_url = f"https://smartstore.naver.com/i/v1/products/{self.product_id}"
            self.driver.get(product_url)
            
            # 페이지 로딩 대기
            self._human_like_delay()
            
            # 인간 활동 시뮬레이션
            self._simulate_human_activity()
            
            # 상품 정보 추출 시도
            merchant_no = None
            origin_product_no = None
            
            # 여러 방법으로 정보 추출 시도
            try:
                # 방법 1: 페이지 소스에서 JSON 데이터 찾기
                page_source = self.driver.page_source
                
                # JSON 데이터 패턴 검색
                import re
                json_pattern = r'"productNo":\s*"?(\d+)"?'
                match = re.search(json_pattern, page_source)
                if match:
                    origin_product_no = match.group(1)
                
                merchant_pattern = r'"channelNo":\s*"?(\d+)"?'
                match = re.search(merchant_pattern, page_source)
                if match:
                    merchant_no = match.group(1)
                
                if merchant_no and origin_product_no:
                    print(f"✅ 상품 정보 추출 성공!")
                    print(f"   📊 Merchant No: {merchant_no}")
                    print(f"   📊 Origin Product No: {origin_product_no}")
                    return merchant_no, origin_product_no
                
            except Exception as e:
                print(f"⚠️  정보 추출 중 오류: {e}")
            
            # 방법 2: API 호출로 정보 얻기
            try:
                api_url = f"https://smartstore.naver.com/i/v1/products/{self.product_id}/summary"
                self.driver.get(api_url)
                time.sleep(3)
                
                # JSON 응답 파싱
                body_text = self.driver.find_element(By.TAG_NAME, "body").text
                
                if body_text and body_text.strip().startswith('{'):
                    data = json.loads(body_text)
                    merchant_no = data['product']['channel']['channelNo']
                    origin_product_no = data['product']['productNo']
                    
                    print(f"✅ API로 상품 정보 획득!")
                    print(f"   📊 Merchant No: {merchant_no}")
                    print(f"   📊 Origin Product No: {origin_product_no}")
                    return merchant_no, origin_product_no
                    
            except Exception as e:
                print(f"⚠️  API 호출 실패: {e}")
            
            print("❌ 상품 정보를 찾을 수 없습니다")
            return None, None
            
        except Exception as e:
            print(f"❌ 상품 정보 수집 실패: {e}")
            return None, None
    
    def crawl_reviews(self):
        """리뷰 크롤링"""
        merchant_no, origin_product_no = self.get_product_info()
        
        if not merchant_no or not origin_product_no:
            return None
        
        all_reviews = []
        page = 1
        max_pages = 100  # 최대 페이지 제한
        
        print("📝 브라우저로 리뷰 크롤링 시작...")
        
        while page <= max_pages:
            try:
                # 리뷰 API URL 접속
                review_url = (
                    f"https://smartstore.naver.com/main/products/{origin_product_no}/reviews/writable-reviews"
                    f"?page={page}&sort=REVIEW_RANKING&merchantNo={merchant_no}"
                )
                
                print(f"📄 페이지 {page} 수집 중...")
                self.driver.get(review_url)
                
                # 페이지 로딩 대기
                self._human_like_delay()
                
                # JSON 응답 파싱
                try:
                    body_text = self.driver.find_element(By.TAG_NAME, "body").text
                    
                    if not body_text or not body_text.strip().startswith('{'):
                        print(f"❌ 페이지 {page}: 올바른 JSON 응답이 아닙니다")
                        break
                    
                    data = json.loads(body_text)
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
                    
                    print(f"✅ 페이지 {page}: {len(reviews)}개 리뷰 수집 (총 {len(all_reviews)}개)")
                    page += 1
                    
                    # 인간 활동 시뮬레이션
                    self._simulate_human_activity()
                    
                except json.JSONDecodeError as e:
                    print(f"❌ JSON 파싱 오류: {e}")
                    print(f"응답 내용: {body_text[:200]}...")
                    break
                except Exception as e:
                    print(f"❌ 리뷰 파싱 오류: {e}")
                    break
                    
            except Exception as e:
                print(f"❌ 페이지 {page} 처리 중 오류: {e}")
                break
        
        if all_reviews:
            print(f"🎉 총 {len(all_reviews)}개의 리뷰를 수집했습니다!")
            return pd.DataFrame(all_reviews)
        else:
            print("❌ 수집된 리뷰가 없습니다")
            return None
    
    def close(self):
        """브라우저 종료"""
        if self.driver:
            self.driver.quit()
            print("🔚 브라우저 종료")


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
    if not SELENIUM_AVAILABLE:
        print("❌ Selenium이 설치되지 않았습니다.")
        print("설치 방법:")
        print("1. pip install selenium")
        print("2. Chrome 드라이버 다운로드: https://chromedriver.chromium.org/")
        print("3. Chrome 드라이버를 PATH에 추가하거나 현재 폴더에 저장")
        exit(1)
    
    print("🤖 === Selenium 네이버 크롤러 시작 ===")
    print(f"🎯 타겟 상품: {PRODUCT_ID}")
    print("🔧 Chrome 브라우저를 사용합니다")
    
    crawler = None
    try:
        # 크롤러 생성 (headless=False로 하면 브라우저를 볼 수 있음)
        crawler = SeleniumNaverCrawler(PRODUCT_ID, headless=True)
        
        if not crawler._setup_driver():
            print("❌ 브라우저 초기화 실패")
            exit(1)
        
        # 리뷰 크롤링
        review_df = crawler.crawl_reviews()
        
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
            print("1. 상품 ID 확인")
            print("2. Chrome 드라이버 버전 확인")
            print("3. 네트워크 연결 확인")
    
    except KeyboardInterrupt:
        print("\n⛔ 사용자에 의해 중단됨")
    
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
    
    finally:
        if crawler:
            crawler.close()