"""
Selenium 기반 네이버 스마트스토어 리뷰 크롤러
실제 브라우저를 사용하여 IP 차단을 우회
"""
import pandas as pd
import json
import time
import random
from datetime import datetime
from analysis import analyze_sentiment, topic_modeling

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
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        ]
        chrome_options.add_argument(f"--user-agent={random.choice(user_agents)}")
        
        window_sizes = ["1920,1080", "1366,768", "1440,900"]
        chrome_options.add_argument(f"--window-size={random.choice(window_sizes)}")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.wait = WebDriverWait(self.driver, 30)
            print("✅ Chrome 브라우저 초기화 완료")
            return True
        except Exception as e:
            print(f"❌ 브라우저 초기화 실패: {e}")
            print("Chrome 드라이버가 설치되어 있고 PATH에 추가되었는지 확인하세요.")
            return False
    
    def _human_like_delay(self, min_delay=2, max_delay=5):
        """인간과 같은 지연"""
        delay = random.uniform(min_delay, max_delay)
        print(f"⏳ {delay:.2f}초 대기...")
        time.sleep(delay)

    def get_product_info(self):
        """상품 정보 가져오기"""
        print("🔍 브라우저로 상품 정보 수집 중...")
        api_url = f"https://smartstore.naver.com/i/v1/products/{self.product_id}/summary"
        try:
            self.driver.get(api_url)
            self._human_like_delay()
            
            body_text = self.driver.find_element(By.TAG_NAME, "body").text
            if not body_text or not body_text.strip().startswith('{'):
                raise json.JSONDecodeError("응답이 JSON 형식이 아닙니다.", body_text, 0)

            data = json.loads(body_text)
            product_data = data.get('product', {})
            channel_data = product_data.get('channel', {})
            merchant_no = channel_data.get('channelNo')
            origin_product_no = product_data.get('productNo')
            
            if merchant_no and origin_product_no:
                print(f"✅ API로 상품 정보 획득!")
                print(f"   📊 Merchant No: {merchant_no}")
                print(f"   📊 Origin Product No: {origin_product_no}")
                return merchant_no, origin_product_no
            else:
                print("❌ 상품 정보(merchant_no, origin_product_no)를 찾을 수 없습니다.")
                return None, None
        except Exception as e:
            print(f"❌ 상품 정보 수집 실패: {e}")
            return None, None
    
    def crawl_reviews(self):
        """리뷰 크롤링"""
        merchant_no, origin_product_no = self.get_product_info()
        if not merchant_no or not origin_product_no:
            return None
        
        all_reviews, page, max_pages = [], 1, 100
        print("📝 브라우저로 리뷰 크롤링 시작...")
        
        while page <= max_pages:
            try:
                review_url = f"https://smartstore.naver.com/main/products/{origin_product_no}/reviews/writable-reviews?page={page}&sort=REVIEW_RANKING&merchantNo={merchant_no}"
                print(f"📄 페이지 {page} 수집 중...")
                self.driver.get(review_url)
                self._human_like_delay()
                
                body_text = self.driver.find_element(By.TAG_NAME, "body").text
                if not body_text or not body_text.strip().startswith('{'):
                    print(f"❌ 페이지 {page}: 올바른 JSON 응답이 아닙니다. 크롤링을 중단합니다.")
                    break
                
                data = json.loads(body_text)
                reviews = data.get('contents', [])
                if not reviews:
                    print("✅ 모든 리뷰 수집 완료!")
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
                
                print(f"✅ 페이지 {page}: {len(reviews)}개 리뷰 수집 (총 {len(all_reviews)}개)")
                page += 1
                
            except Exception as e:
                print(f"❌ 페이지 {page} 처리 중 오류 발생: {e}")
                break
        
        return pd.DataFrame(all_reviews) if all_reviews else None
    
    def close(self):
        """브라우저 종료"""
        if self.driver:
            self.driver.quit()
            print("🔚 브라우저 종료")

if __name__ == '__main__':
    if not SELENIUM_AVAILABLE:
        exit(1)
    
    print("🤖 === Selenium 네이버 크롤러 시작 ===")
    print(f"🎯 타겟 상품: {PRODUCT_ID}")
    
    crawler = None
    try:
        crawler = SeleniumNaverCrawler(PRODUCT_ID, headless=True)
        if not crawler._setup_driver():
            exit(1)
        
        review_df = crawler.crawl_reviews()
        
        if review_df is not None and not review_df.empty:
            print("\n📊 === 데이터 분석 시작 ===")
            positive_keywords = ['좋아요', '만족', '추천', '최고', '빠른', '편하고', '예뻐요']
            negative_keywords = ['불편', '별로', '실망', '아쉬', '불만', '느린', '무거']
            
            review_df['sentiment'] = review_df['content'].apply(lambda x: analyze_sentiment(x, positive_keywords, negative_keywords))
            print("\n--- 📈 감성 분석 결과 ---")
            print(review_df['sentiment'].value_counts())
            
            print("\n--- 🏷️ 토픽 모델링 결과 ---")
            review_df = topic_modeling(review_df, NUM_TOPICS)
            
            review_df.to_csv(OUTPUT_FILE_NAME, index=False, encoding='utf-8-sig')
            print(f"\n✅ 분석 완료! 결과가 '{OUTPUT_FILE_NAME}' 파일로 저장되었습니다.")
        else:
            print("\n❌ === 크롤링 실패 ===")
    except Exception as e:
        print(f"\n❌ 치명적인 오류 발생: {e}")
    finally:
        if crawler:
            crawler.close()