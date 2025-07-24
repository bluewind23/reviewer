# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Korean e-commerce review analysis tool that crawls product reviews from Naver Smart Store and performs sentiment analysis and topic modeling. The application uses web scraping techniques to gather review data and applies natural language processing to extract insights from Korean text.

## Development Commands

### Setup and Installation
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows)
venv\Scripts\activate

# Activate virtual environment (macOS/Linux)
source venv/bin/activate

# Install required dependencies
pip install requests pandas konlpy scikit-learn
```

### Running the Application
```bash
# Run the basic analysis script (수정된 버전)
python main.py

# Run the advanced stealth crawler (가장 강력한 우회 기능)
python stealth_crawler.py

# Run the Selenium browser automation crawler
python selenium_crawler.py

# Run the mobile API crawler 
python mobile_crawler.py

# 🆕 NEW: Smart Scheduler (자동 URL 파싱 + 스케줄링 + VPN)
python smart_scheduler.py

# 🆕 Quick Start (URL만 입력하면 바로 크롤링)
python quick_start.py

# 🖥️ NEW: GUI 인터페이스 (클릭 한번으로 크롤링!)
python web_gui.py          # 웹 GUI (브라우저)
python desktop_gui.py      # 데스크톱 GUI (윈도우 프로그램)

# 📦 NEW: EXE 파일 생성 (설치 없이 실행)
python build_exe.py        # EXE 파일 빌드

# All scripts will output results to different CSV files
```

## Code Architecture

### Core Components

#### Data Collection (`main.py:14-93`)
- **Review Crawling**: Uses Naver Smart Store API endpoints to fetch product reviews
- **Product Information Retrieval**: Extracts merchant and product IDs from product summary API
- **Pagination Handling**: Iterates through review pages until no more reviews are available
- **Rate Limiting**: Implements 1-second delays between requests to avoid rate limiting

#### Text Processing Pipeline (`main.py:97-146`)
- **Sentiment Analysis**: Keyword-based sentiment classification using predefined positive/negative word lists
- **Topic Modeling**: Uses Latent Dirichlet Allocation (LDA) with TF-IDF vectorization for topic extraction
- **Korean Text Processing**: Leverages KoNLPy's Okt tokenizer for Korean noun extraction

#### Configuration (`main.py:9-12`)
- **PRODUCT_ID**: Target product identifier for analysis
- **OUTPUT_FILE_NAME**: CSV output file name
- **NUM_TOPICS**: Number of topics for LDA clustering

### Data Flow

1. **Product Information Retrieval**: Fetches merchant and origin product numbers from summary API
2. **Review Collection**: Paginated crawling of reviews with comprehensive metadata
3. **Text Processing**: Korean text tokenization and cleaning
4. **Sentiment Classification**: Rule-based sentiment scoring using keyword matching
5. **Topic Extraction**: LDA-based topic modeling on processed review text
6. **Output Generation**: CSV export with enriched review data including sentiment and topic assignments

### API Integration

The application interacts with Naver Smart Store's internal APIs:
- **Product Summary API**: `https://smartstore.naver.com/i/v1/products/{product_id}/summary`
- **Reviews API**: `https://smartstore.naver.com/main/products/{origin_product_no}/reviews/writable-reviews`

Headers include User-Agent and Referer to mimic browser requests and avoid detection.

## Anti-Detection Features

### Advanced Crawler (`advanced_crawler.py`)
The advanced version includes sophisticated anti-detection mechanisms:

- **Dynamic User-Agent Rotation**: 12+ realistic browser user agents with proper header combinations
- **Intelligent Delay System**: Adaptive request timing based on response patterns and request count
- **Session Fingerprinting**: Simulates real browser behavior with preliminary page visits
- **Retry Strategy**: Exponential backoff with circuit breaker patterns for different error types
- **Proxy Support**: Ready for proxy rotation (configure PROXIES list)
- **Enhanced Error Handling**: Detailed status code analysis with appropriate recovery strategies

### Rate Limiting Countermeasures
- **Progressive Delays**: 1-3s initial, 2-5s moderate, 3-8s heavy traffic
- **Failure Recovery**: Up to 5 retry attempts with exponential backoff
- **Circuit Breaker**: Automatic suspension after 3 consecutive failures
- **Long-term Blocks**: 5-10 minute delays for 403 responses

## Key Dependencies

- **requests**: HTTP client for API communication
- **pandas**: Data manipulation and CSV export
- **konlpy**: Korean language processing (Okt tokenizer)
- **scikit-learn**: Machine learning tools (TF-IDF, LDA)
- **urllib3**: Advanced HTTP features and SSL handling

## Configuration Notes

To analyze a different product, modify the `PRODUCT_ID` constant in either script. The sentiment analysis keywords can be customized by editing the positive_keywords and negative_keywords lists.

## 크롤러 선택 가이드

### 1. **stealth_crawler.py** (가장 권장)
- **장점**: 가장 강력한 IP 차단 우회 기능
- **특징**: 15번 재시도, 인간 행동 시뮬레이션, 극도로 정교한 지연
- **사용 시기**: 다른 모든 방법이 실패했을 때

### 2. **selenium_crawler.py** (높은 성공률)
- **장점**: 실제 브라우저 사용으로 탐지 어려움
- **특징**: Chrome 브라우저 자동화, 봇 탐지 우회
- **사용 시기**: GUI 환경에서 안정적인 크롤링 필요시
- **요구사항**: Chrome 브라우저 + ChromeDriver 설치

### 3. **mobile_crawler.py** (차별화된 접근)
- **장점**: 모바일 API 엔드포인트 활용
- **특징**: 앱 시뮬레이션, 다양한 모바일 User-Agent
- **사용 시기**: 데스크톱 API가 차단된 경우

### 4. **advanced_crawler.py** (기본 고급 버전)
- **장점**: 향상된 우회 기능
- **특징**: 동적 헤더, 재시도 로직, 프록시 지원
- **사용 시기**: 기본 크롤링 실패시 첫 번째 대안

### 5. **main.py** (기본 버전)
- **장점**: 가볍고 빠름
- **특징**: 기본적인 우회 기능만 포함
- **사용 시기**: IP 차단이 없거나 테스트용

## 성공률 향상 팁

### 권장 실행 순서
1. `stealth_crawler.py` (가장 높은 성공률)
2. `selenium_crawler.py` (브라우저 자동화)
3. `mobile_crawler.py` (모바일 API)
4. `advanced_crawler.py` (향상된 기본)
5. `main.py` (기본 버전)

### 최적 실행 환경
- **시간**: 한국 시간 새벽 2-6시 (트래픽 최소)
- **네트워크**: VPN 또는 프록시 사용 권장
- **빈도**: 같은 상품당 하루 1-2회 제한
- **인내심**: stealth_crawler는 매우 느리게 작동 (안전성을 위해)

### 추가 설정
- 프록시 서버가 있다면 각 크롤러의 PROXIES 리스트에 추가
- Selenium 사용시 Chrome 브라우저와 ChromeDriver 필요
- 장시간 실행시 중간에 중단될 수 있으므로 여러 번 나누어 실행 권장

## 🆕 스마트 스케줄러 (NEW!)

### 주요 기능
- **URL 자동 파싱**: 상품 페이지 URL에서 상품 ID 자동 추출
- **자동 스케줄링**: 정해진 시간(새벽 2시, 3시 30분, 5시)에 자동 실행
- **VPN 자동 관리**: ExpressVPN, NordVPN, SurfShark 지원
- **다중 크롤러 통합**: 실패시 자동으로 다음 크롤러 시도
- **설정 파일 관리**: JSON 기반 영구 설정 저장
- **상세한 로그**: 성공/실패 추적 및 분석

### 빠른 시작

#### 1. 즉시 크롤링
```bash
# URL만 입력하면 바로 크롤링
python quick_start.py

# 또는 명령행에서 직접
python quick_start.py "https://smartstore.naver.com/store/products/12345678"
```

#### 2. 자동 스케줄링 설정
```bash
# 대화형 설정
python smart_scheduler.py

# 메뉴에서 선택:
# 1. 상품 추가 (URL 입력)
# 2. VPN 설정 
# 3. 스케줄러 시작
```

### 지원하는 URL 형식
- `https://smartstore.naver.com/store/products/12345678`
- `https://shopping.naver.com/products/12345678`
- `https://m.smartstore.naver.com/store/products/12345678`
- `https://shopping.naver.com/search?query=상품&nvMid=12345678`

### VPN 설정 예제
```bash
# ExpressVPN
expressvpn connect japan

# NordVPN  
nordvpn connect japan

# SurfShark
surfshark-vpn attack japan
```

### 설정 파일 (crawler_config.json)
```json
{
  "schedule": {
    "auto_run_times": ["02:00", "03:30", "05:00"]
  },
  "vpn": {
    "enabled": true,
    "provider": "expressvpn",
    "countries": ["japan", "singapore", "australia"]
  },
  "crawlers": {
    "priority_order": ["stealth", "selenium", "mobile", "advanced"]
  }
}
```

### 자동화 워크플로우
1. **상품 등록**: URL 입력 → 자동 상품 ID 추출
2. **스케줄 실행**: 설정된 시간에 자동 시작
3. **VPN 연결**: 랜덤 국가 서버로 자동 연결
4. **크롤링 시도**: 우선순위 순으로 크롤러 실행
5. **결과 저장**: 타임스탬프가 포함된 CSV 파일 생성
6. **VPN 해제**: 크롤링 완료 후 자동 연결 해제
7. **로그 기록**: 성공/실패 통계 업데이트

### 출력 파일 형식
```
crawl_results/
├── 12345678_20240123_143022_stealth.csv
├── 87654321_20240123_143532_selenium.csv
└── logs/
    └── crawler_scheduler_20240123.log
```

## 🖥️ GUI 인터페이스 (NEW!)

### 웹 GUI (추천)
```bash
# 웹 서버 시작
python web_gui.py

# 브라우저에서 접속
http://localhost:5000
```

**특징:**
- 🌐 **브라우저 기반**: Chrome, Safari, Firefox 등 모든 브라우저
- 📱 **모바일 지원**: 스마트폰, 태블릿에서도 사용 가능
- 🎨 **모던 디자인**: Bootstrap 기반 반응형 UI
- ⚡ **실시간 진행률**: 크롤링 진행 상황 실시간 표시
- 📊 **대시보드**: 상품 관리, 설정, 통계 한눈에 보기

### 데스크톱 GUI
```bash
# 윈도우 프로그램처럼 실행
python desktop_gui.py
```

**특징:**
- 🖥️ **네이티브 앱**: Windows 프로그램처럼 동작
- 🎛️ **다중 탭**: 크롤링, 상품관리, 설정, 로그
- 📋 **일괄 처리**: 여러 상품 동시 크롤링
- 💾 **로그 저장**: 모든 과정을 파일로 저장
- 🔧 **고급 설정**: 세밀한 옵션 조정

### EXE 파일 (배포용)
```bash
# EXE 파일 빌드
python build_exe.py

# 생성된 파일 실행 (Python 설치 불필요)
dist/NaverSmartCrawler.exe
```

**특징:**
- 📦 **독립실행**: Python 설치 없이 실행 가능
- 🚀 **간편배포**: 다른 컴퓨터에서도 바로 실행
- 💻 **Windows 호환**: Windows 7/10/11 지원
- 📁 **완전패키지**: 모든 의존성 포함

### GUI 기능 비교

| 기능 | 웹 GUI | 데스크톱 GUI | EXE 파일 |
|------|--------|--------------|----------|
| 설치 복잡도 | 쉬움 | 중간 | 매우 쉬움 |
| 접근성 | 모든 기기 | 로컬만 | 로컬만 |
| 성능 | 중간 | 빠름 | 빠름 |
| 업데이트 | 쉬움 | 중간 | 어려움 |
| 배포 | 어려움 | 어려움 | 매우 쉬움 |

### 사용 시나리오

#### 🏠 개인 사용자
```bash
# 간단한 크롤링
python web_gui.py
# → 브라우저에서 URL 입력하고 클릭
```

#### 🏢 사무실 환경
```bash
# 여러 직원이 공유
python web_gui.py
# → 각자 브라우저에서 http://서버IP:5000 접속
```

#### 📦 외부 배포
```bash
# EXE 파일 생성 후 USB로 전달
python build_exe.py
# → dist 폴더를 다른 PC에 복사
```

### GUI 장점

#### ✨ 사용자 친화적
- **직관적 인터페이스**: 클릭만으로 모든 기능 사용
- **실시간 피드백**: 진행 상황과 결과 즉시 확인
- **오류 알림**: 문제 발생시 친절한 안내 메시지

#### 🚀 효율성 극대화
- **원클릭 크롤링**: URL 붙여넣기 → 클릭 → 완료
- **일괄 처리**: 여러 상품을 한번에 크롤링
- **자동 재시도**: 실패시 다른 크롤러로 자동 전환

#### 🔧 고급 기능
- **VPN 통합**: GUI에서 바로 VPN 설정 및 연결
- **스케줄링**: 원하는 시간에 자동 실행 설정
- **결과 분석**: 크롤링 결과를 차트와 표로 시각화