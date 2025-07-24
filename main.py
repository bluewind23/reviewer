import requests
import pandas as pd
import json
import time
import random
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
# 분석 모듈 import
from analysis import analyze_sentiment, topic_modeling

# --- 설정 부분 ---
PRODUCT_ID = "5753732771"
OUTPUT_FILE_NAME = "reviews.csv"
NUM_TOPICS = 5

# 다양한 User-Agent 목록
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/119.0"
]

# 프록시 설정 (필요한 경우 추가)
PROXIES = [
    # 예시: {'http': 'http://proxy1:port', 'https': 'https://proxy1:port'},
]

def get_session_with_retry():
    """재시도 로직이 포함된 세션을 생성합니다."""
    session = requests.Session()
    
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

def get_random_headers(product_id):
    """랜덤한 헤더를 생성합니다."""
    user_agent = random.choice(USER_AGENTS)
    
    headers = {
        "User-Agent": user_agent,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Referer": f"https://smartstore.naver.com/i/v1/products/{product_id}",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache"
    }
    
    if random.random() > 0.5:
        headers["DNT"] = "1"
    
    if random.random() > 0.5:
        headers["Upgrade-Insecure-Requests"] = "1"
        
    return headers

def random_delay(min_delay=2, max_delay=5):
    """랜덤한 지연 시간을 적용합니다."""
    delay = random.uniform(min_delay, max_delay)
    print(f"{delay:.2f}초 대기 중...")
    time.sleep(delay)

def crawl_reviews(product_id):
    """지정된 상품 ID의 모든 리뷰를 크롤링합니다."""
    all_reviews = []
    page = 1
    failed_attempts = 0
    max_failed_attempts = 3
    
    session = get_session_with_retry()
    
    print("상품 정보를 가져오는 중...")
    
    for attempt in range(3):
        try:
            headers = get_random_headers(product_id)
            info_url = f"https://smartstore.naver.com/i/v1/products/{product_id}/summary"
            proxy = random.choice(PROXIES) if PROXIES else None
            
            info_res = session.get(info_url, headers=headers, proxies=proxy, timeout=10)
            
            if info_res.status_code == 200:
                break
            elif info_res.status_code == 429:
                print(f"Rate limit 감지됨. {30 * (attempt + 1)}초 대기 후 재시도...")
                time.sleep(30 * (attempt + 1))
            else:
                print(f"시도 {attempt + 1}: 상태 코드 {info_res.status_code}")
                if attempt < 2:
                    random_delay(5, 10)
                    
        except requests.exceptions.RequestException as e:
            print(f"시도 {attempt + 1} 실패: {e}")
            if attempt < 2:
                random_delay(5, 10)
    else:
        print("상품 정보를 가져오는 데 실패했습니다. 모든 재시도 완료.")
        return None
        
    try:
        product_info = info_res.json()
        merchant_no = product_info['product']['channel']['channelNo']
        origin_product_no = product_info['product']['productNo']
        print(f"Merchant No: {merchant_no}, Origin Product No: {origin_product_no}")
    except (json.JSONDecodeError, KeyError) as e:
        print(f"상품 정보 파싱에 실패했습니다: {e}")
        return None

    while True:
        url = (
            f"https://smartstore.naver.com/main/products/{origin_product_no}/reviews/writable-reviews"
            f"?page={page}&sort=REVIEW_RANKING"
            f"&merchantNo={merchant_no}"
        )
        
        try:
            headers = get_random_headers(product_id)
            proxy = random.choice(PROXIES) if PROXIES else None
            
            res = session.get(url, headers=headers, proxies=proxy, timeout=15)
            
            if res.status_code == 429:
                print(f"Rate limit 감지됨. 60초 대기 후 재시도...")
                time.sleep(60)
                failed_attempts += 1
                if failed_attempts >= max_failed_attempts:
                    print("너무 많은 실패로 인해 크롤링을 중단합니다.")
                    break
                continue
            elif res.status_code == 403:
                print(f"접근 거부됨 (403). IP가 차단되었을 수 있습니다.")
                failed_attempts += 1
                if failed_attempts >= max_failed_attempts:
                    print("접근이 지속적으로 거부되어 크롤링을 중단합니다.")
                    break
                random_delay(60, 120)
                continue
            elif res.status_code != 200:
                print(f"예상치 못한 상태 코드: {res.status_code}")
                failed_attempts += 1
                if failed_attempts >= max_failed_attempts:
                    break
                random_delay(10, 30)
                continue
            
            failed_attempts = 0
            
            data = res.json()
            reviews = data.get('contents', [])
            
            if not reviews:
                print("더 이상 리뷰가 없습니다. 크롤링을 종료합니다.")
                break

            for review in reviews:
                option_text = " / ".join([opt['optionContent'] for opt in review.get('productOptionContents', []) if 'optionContent' in opt])
                
                all_reviews.append({
                    'id': review.get('id'),
                    'rating': review.get('reviewScore'),
                    'writer': review.get('writerMemberId'),
                    'date': review.get('createDate'),
                    'content': review.get('reviewContent', ''),
                    'option': option_text,
                })
            
            print(f"{page} 페이지의 리뷰 {len(reviews)}건을 가져왔습니다. (총 {len(all_reviews)}건)")
            page += 1
            
            random_delay(2, 5)

        except requests.exceptions.RequestException as e:
            print(f"네트워크 오류가 발생했습니다: {e}")
            failed_attempts += 1
            if failed_attempts >= max_failed_attempts:
                print("연속된 네트워크 오류로 인해 크롤링을 중단합니다.")
                break
            random_delay(10, 30)
            continue
            
        except json.JSONDecodeError:
            print("JSON 파싱 오류가 발생했습니다. 응답 내용을 확인하세요.")
            print(f"응답 상태 코드: {res.status_code}")
            print(f"응답 내용 (처음 500자): {res.text[:500]}")
            failed_attempts += 1
            if failed_attempts >= max_failed_attempts:
                break
            random_delay(10, 30)
            continue
            
    return pd.DataFrame(all_reviews)

if __name__ == '__main__':
    review_df = crawl_reviews(PRODUCT_ID)

    if review_df is not None and not review_df.empty:
        positive_keywords = ['좋아요', '만족', '추천', '최고', '빠른', '편하고', '예뻐요', '가볍고', '튼튼', '잘', '맘에']
        negative_keywords = ['불편', '별로', '실망', '아쉬', '불만', '느린', '무거', '약한', '문제', '고장']
        
        review_df['sentiment'] = review_df['content'].apply(lambda x: analyze_sentiment(x, positive_keywords, negative_keywords))
        print("\n--- 감성 분석 결과 ---")
        print(review_df['sentiment'].value_counts())
        
        print("\n--- 토픽 모델링 결과 ---")
        review_df = topic_modeling(review_df, NUM_TOPICS)

        review_df.to_csv(OUTPUT_FILE_NAME, index=False, encoding='utf-8-sig')
        print(f"\n분석이 완료되었으며, 결과가 '{OUTPUT_FILE_NAME}' 파일로 저장되었습니다.")
        print("파일 내용 미리보기:")
        print(review_df.head())
    else:
        print("크롤링된 리뷰가 없어 분석을 진행하지 않습니다.")