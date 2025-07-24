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
pip install -r requirements.txt
```

### Running the Application
```bash
# Run the basic analysis script
python main.py

# Run the advanced stealth crawler (most powerful anti-detection)
python stealth_crawler.py

# Run the Selenium browser automation crawler
python selenium_crawler.py

# Run the mobile API crawler 
python mobile_crawler.py

# Smart Scheduler (automatic URL parsing + scheduling + VPN)
python smart_scheduler.py

# Quick Start (input URL and crawl immediately)
python quick_start.py

# GUI interfaces
python web_gui.py          # Web GUI (browser)
python desktop_gui.py      # Desktop GUI (native app)

# Build standalone executable
python build_exe.py
```

### Testing and Development
```bash
# Run individual crawlers with custom product IDs
# Edit PRODUCT_ID constant in the crawler file before running

# Test sentiment analysis separately
python analysis.py

# All scripts output results to CSV files in crawl_results/
```

## Code Architecture

### Core Components

#### Data Collection Layer
The project implements multiple crawler strategies to handle various anti-detection scenarios:

- **Basic Crawler** (`main.py`): Simple HTTP requests with basic headers
- **Advanced Crawler** (`advanced_crawler.py`): Dynamic headers, retry logic, proxy support
- **Stealth Crawler** (`stealth_crawler.py`): Human behavior simulation, 15 retry attempts
- **Selenium Crawler** (`selenium_crawler.py`): Real browser automation
- **Mobile Crawler** (`mobile_crawler.py`): Mobile API endpoints

#### Analysis Engine (`analysis.py`)
- **Sentiment Analysis**: Keyword-based classification using predefined positive/negative word lists
- **Topic Modeling**: LDA (Latent Dirichlet Allocation) with TF-IDF vectorization
- **Korean Text Processing**: KoNLPy's Okt tokenizer for noun extraction

#### Automation System (`smart_scheduler.py`)
- **URL Parsing**: Automatic product ID extraction from various Naver URL formats
- **Scheduled Execution**: Runs at optimal times (2:00, 3:30, 5:00 AM KST)
- **VPN Management**: Automatic connection/disconnection with country rotation
- **Fallback Strategy**: Tries multiple crawlers in priority order

#### User Interfaces
- **Web GUI** (`web_gui.py`): Flask-based interface with real-time progress
- **Desktop GUI** (`desktop_gui.py`): Tkinter-based native application
- **CLI Tools**: Direct command-line execution for automation

### Data Flow

1. **Product Discovery**: Extract merchant and product IDs from Naver APIs
2. **Review Collection**: Paginated crawling with comprehensive metadata
3. **Text Processing**: Korean tokenization and cleaning
4. **Analysis**: Sentiment scoring and topic extraction
5. **Output**: Structured CSV with enriched data

### API Integration

The crawlers interact with Naver Smart Store's internal APIs:
- **Product Summary**: `https://smartstore.naver.com/i/v1/products/{product_id}/summary`
- **Reviews**: `https://smartstore.naver.com/main/products/{origin_product_no}/reviews/writable-reviews`

## Anti-Detection Strategy

### Crawler Selection Guide

1. **stealth_crawler.py** (Recommended)
   - Highest success rate with aggressive anti-detection
   - 15 retry attempts with human-like delays
   - Use when other methods fail

2. **selenium_crawler.py** (High Success)
   - Real browser automation
   - Effective against JavaScript checks
   - Requires Chrome + ChromeDriver

3. **mobile_crawler.py** (Alternative)
   - Uses mobile API endpoints
   - Different detection surface
   - Good when desktop APIs blocked

4. **advanced_crawler.py** (Enhanced)
   - Better than basic with retry logic
   - Proxy support ready
   - First alternative to try

5. **main.py** (Basic)
   - Fastest but least stealthy
   - Good for testing or unblocked IPs

### Rate Limiting and Ethics
- Implements delays between requests (1-8 seconds adaptive)
- Respects server load with exponential backoff
- Circuit breaker pattern for consecutive failures
- Recommended: 1-2 crawls per product per day

## Configuration

### Crawler Configuration (`crawler_config.json`)
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

### Product Configuration
Modify `PRODUCT_ID` constant in crawler files or use GUI/scheduler for dynamic configuration.

## Output Structure

```
crawl_results/
├── {product_id}_{timestamp}_{crawler_type}.csv
├── logs/
│   └── crawler_scheduler_{date}.log
└── analysis_results/
    └── {product_id}_analysis.csv
```

CSV columns include:
- Review metadata (ID, author, date, rating)
- Review content and helpfulness scores
- Sentiment analysis results
- Topic modeling assignments

## Dependencies and Requirements

### Core Dependencies
- **requests**: HTTP client
- **pandas**: Data manipulation
- **konlpy**: Korean NLP (requires Java 8+)
- **scikit-learn**: Machine learning
- **selenium**: Browser automation
- **flask**: Web framework

### System Requirements
- Python 3.7+
- Java 8+ (for KoNLPy)
- Chrome browser (for Selenium)
- 4GB+ RAM recommended

## Common Issues and Solutions

### Java/KoNLPy Issues
If KoNLPy fails, ensure Java 8+ is installed and JAVA_HOME is set correctly.

### Selenium WebDriver
Download ChromeDriver matching your Chrome version from https://chromedriver.chromium.org/

### Rate Limiting (429/403 errors)
- Use stealth_crawler.py with longer delays
- Enable VPN in scheduler
- Reduce crawling frequency

### Memory Issues with Large Reviews
Process in batches by modifying the page iteration logic in crawlers.