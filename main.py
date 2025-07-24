import requests
import pandas as pd
import json
import time
import random
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from analysis import analyze_sentiment, topic_modeling

# --- 설정 부분 ---
PRODUCT_ID = "5753732771"
OUTPUT_FILE_NAME = "reviews.csv"
NUM_TOPICS = 5

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
]

PROXIES = []

def get_session_with_retry():
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    return session
    
def get_random_headers(product_id):
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": f"https://smartstore.naver.com/products/{product_id}",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }

def random_delay(min_delay=2, max_delay=5):
    delay = random.uniform(min_delay, max_delay)
    time.sleep(delay)

def crawl_reviews(product_id):
    """지정된 상품 ID의 모든 리뷰를 크롤링합니다."""
    all_reviews = []
    page = 1
    session = get_session_with_retry()
    
    print("상품 정보를 가져오는 중...")
    try:
        info_url = f"https://smartstore.naver.com/i/v1/products/{product_id}/summary"
        info_res = session.get(info_url, headers=get_random_headers(product_id), timeout=10)
        info_res.raise_for_status() # 오류 발생 시 예외 발생
        
        product_info = info_res.json()
        # .get()을 사용하여 안전하게 데이터 접근
        merchant_no = product_info.get('product', {}).get('channel', {}).get('channelNo')
        origin_product_no = product_info.get('product', {}).get('productNo')

        if not merchant_no or not origin_product_no:
            print("상품 정보(merchant_no, origin_product_no)를 찾을 수 없습니다.")
            return None
        
        print(f"Merchant No: {merchant_no}, Origin Product No: {origin_product_no}")

    except (requests.exceptions.RequestException, json.JSONDecodeError, KeyError) as e:
        print(f"상품 정보 획득 실패: {e}")
        return None

    while True:
        url = (
            f"https://smartstore.naver.com/main/products/{origin_product_no}/reviews/writable-reviews"
            f"?page={page}&sort=REVIEW_RANKING&merchantNo={merchant_no}"
        )
        try:
            res = session.get(url, headers=get_random_headers(product_id), timeout=15)
            res.raise_for_status()
            
            data = res.json()
            reviews = data.get('contents', [])
            
            if not reviews:
                print("더 이상 리뷰가 없습니다. 크롤링을 종료합니다.")
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
            
            print(f"{page} 페이지의 리뷰 {len(reviews)}건을 가져왔습니다. (총 {len(all_reviews)}건)")
            page += 1
            random_delay(2, 5)

        except requests.exceptions.RequestException as e:
            print(f"네트워크 오류: {e}, 30초 후 재시도합니다.")
            time.sleep(30)
            continue
        except json.JSONDecodeError:
            print("JSON 파싱 오류가 발생했습니다.")
            break
            
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
    else:
        print("크롤링된 리뷰가 없어 분석을 진행하지 않습니다.")