"""
빠른 시작 스크립트
URL만 입력하면 바로 크롤링 시작
"""

import sys
from smart_scheduler import SmartCrawlerScheduler

def quick_crawl(url):
    """URL을 받아서 즉시 크롤링 실행"""
    print("🚀 === 빠른 크롤링 시작 ===")
    print(f"🎯 대상 URL: {url}")
    
    # 스케줄러 생성
    scheduler = SmartCrawlerScheduler()
    
    # 즉시 크롤링 실행
    result = scheduler.manual_crawl(url)
    
    if result:
        print(f"✅ 크롤링 성공!")
        print(f"📁 결과 파일: {result}")
    else:
        print("❌ 크롤링 실패")
        print("💡 해결 방법:")
        print("1. URL이 올바른지 확인")
        print("2. VPN 사용 고려")
        print("3. 시간을 두고 재시도")

def setup_auto_schedule():
    """자동 스케줄링 설정"""
    print("⏰ === 자동 스케줄링 설정 ===")
    
    # 스케줄러 생성
    scheduler = SmartCrawlerScheduler()
    
    # 상품 추가 예제
    sample_urls = [
        "https://smartstore.naver.com/example/products/12345678",
        "https://smartstore.naver.com/another/products/87654321"
    ]
    
    print("📦 샘플 상품들을 추가하시겠습니까? (y/n)")
    if input().lower() == 'y':
        for i, url in enumerate(sample_urls, 1):
            scheduler.add_product(url, f"샘플상품_{i}")
    
    print("🌍 VPN을 설정하시겠습니까? (y/n)")
    if input().lower() == 'y':
        print("VPN 제공업체 (expressvpn/nordvpn/surfshark):")
        provider = input().strip() or "expressvpn"
        
        print("서버 국가들 (쉼표로 구분, 기본: japan,singapore):")
        countries_input = input().strip() or "japan,singapore"
        countries = [c.strip() for c in countries_input.split(",")]
        
        scheduler.setup_vpn(provider, countries)
        print("✅ VPN 설정 완료!")
    
    print("⏰ 자동 스케줄링을 시작합니다...")
    print("   - 매일 새벽 2:00, 3:30, 5:00에 실행")
    print("   - Ctrl+C로 중단 가능")
    
    scheduler.start_scheduler()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 명령행에서 URL 받기
        url = sys.argv[1]
        quick_crawl(url)
    else:
        print("🤖 === 네이버 스마트 크롤러 빠른 시작 ===")
        print()
        print("1. 즉시 크롤링")
        print("2. 자동 스케줄링 설정")
        print("3. 전체 기능 (smart_scheduler.py 실행)")
        print()
        
        choice = input("선택하세요 (1-3): ").strip()
        
        if choice == "1":
            url = input("크롤링할 상품 URL을 입력하세요: ").strip()
            if url:
                quick_crawl(url)
            else:
                print("❌ URL을 입력해주세요")
        elif choice == "2":
            setup_auto_schedule()
        elif choice == "3":
            print("📋 전체 기능을 사용하려면 다음 명령어를 실행하세요:")
            print("python smart_scheduler.py")
        else:
            print("❌ 올바른 번호를 선택해주세요")