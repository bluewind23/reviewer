"""
스마트 네이버 크롤링 스케줄러
- URL에서 상품코드 자동 추출
- 정해진 시간에 자동 실행
- VPN 자동 연결/해제
- 다중 크롤러 통합 관리
"""

import requests
import pandas as pd
import json
import time
import random
import re
import subprocess
import os
import schedule
import threading
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
from pathlib import Path
import logging
from typing import Optional, Dict, List, Tuple

# 기존 크롤러들 import
try:
    from stealth_crawler import StealthNaverCrawler
    from selenium_crawler import SeleniumNaverCrawler
    from mobile_crawler import MobileNaverCrawler
    from advanced_crawler import AdvancedNaverCrawler
    CRAWLERS_AVAILABLE = True
except ImportError:
    CRAWLERS_AVAILABLE = False
    print("⚠️  크롤러 모듈들을 찾을 수 없습니다. 동일한 폴더에 있는지 확인하세요.")

class SmartCrawlerScheduler:
    def __init__(self, config_file="crawler_config.json"):
        self.config_file = config_file
        self.config = self._load_config()
        self.setup_logging()
        self.running_jobs = {}
        
    def _load_config(self) -> Dict:
        """설정 파일 로드 또는 기본 설정 생성"""
        default_config = {
            "schedule": {
                "auto_run_times": ["02:00", "03:30", "05:00"],  # 새벽 시간대
                "timezone": "Asia/Seoul",
                "retry_interval_hours": 6
            },
            "vpn": {
                "enabled": False,
                "provider": "expressvpn",  # expressvpn, nordvpn, surfshark
                "countries": ["japan", "singapore", "australia"],  # 한국 근처 서버
                "connect_command": "expressvpn connect {country}",
                "disconnect_command": "expressvpn disconnect",
                "status_command": "expressvpn status"
            },
            "crawlers": {
                "priority_order": ["stealth", "selenium", "mobile", "advanced"],
                "max_retries_per_crawler": 2,
                "delay_between_crawlers": 300  # 5분
            },
            "output": {
                "base_directory": "crawl_results",
                "filename_pattern": "{product_id}_{timestamp}_{crawler}.csv",
                "keep_logs_days": 30
            },
            "products": []  # 크롤링할 상품 목록
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # 기본 설정으로 누락된 키 보완
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
            except Exception as e:
                print(f"⚠️  설정 파일 로드 실패: {e}")
                return default_config
        else:
            # 기본 설정 파일 생성
            self._save_config(default_config)
            return default_config
    
    def _save_config(self, config: Dict):
        """설정 파일 저장"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ 설정 파일 저장 실패: {e}")
    
    def setup_logging(self):
        """로깅 시스템 설정"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f"crawler_scheduler_{datetime.now().strftime('%Y%m%d')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def extract_product_id(self, url: str) -> Optional[str]:
        """URL에서 상품 ID 자동 추출"""
        try:
            # 다양한 네이버 쇼핑 URL 패턴 지원
            patterns = [
                # 스마트스토어 직접 링크
                r'smartstore\.naver\.com/[^/]+/products/(\d+)',
                r'smartstore\.naver\.com/.*?/(\d+)',
                
                # API 엔드포인트
                r'/products/(\d+)',
                r'/v1/products/(\d+)',
                
                # 쇼핑 검색 결과
                r'shopping\.naver\.com/.*?nvMid=(\d+)',
                r'shopping\.naver\.com/.*?productId=(\d+)',
                
                # 모바일 링크
                r'm\.smartstore\.naver\.com/.*?/(\d+)',
                r'm\.shopping\.naver\.com/.*?nvMid=(\d+)',
                
                # 쿼리 파라미터
                r'[?&]productId=(\d+)',
                r'[?&]nvMid=(\d+)',
                r'[?&]id=(\d+)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    product_id = match.group(1)
                    self.logger.info(f"✅ URL에서 상품 ID 추출 성공: {product_id}")
                    return product_id
            
            # 마지막 시도: URL 끝의 숫자
            url_numbers = re.findall(r'/(\d{6,})', url)
            if url_numbers:
                product_id = url_numbers[-1]
                self.logger.info(f"✅ URL 패턴 매칭으로 상품 ID 추출: {product_id}")
                return product_id
            
            self.logger.error(f"❌ URL에서 상품 ID를 찾을 수 없습니다: {url}")
            return None
            
        except Exception as e:
            self.logger.error(f"❌ URL 파싱 오류: {e}")
            return None
    
    def add_product(self, url: str, name: str = "", priority: int = 1) -> bool:
        """상품 추가"""
        product_id = self.extract_product_id(url)
        if not product_id:
            return False
        
        product = {
            "id": product_id,
            "url": url,
            "name": name or f"상품_{product_id}",
            "priority": priority,
            "added_date": datetime.now().isoformat(),
            "last_crawl": None,
            "success_count": 0,
            "fail_count": 0,
            "enabled": True
        }
        
        # 중복 체크
        for existing in self.config["products"]:
            if existing["id"] == product_id:
                self.logger.info(f"⚠️  상품 {product_id}는 이미 등록되어 있습니다.")
                return False
        
        self.config["products"].append(product)
        self._save_config(self.config)
        self.logger.info(f"✅ 상품 추가 완료: {name} ({product_id})")
        return True
    
    def remove_product(self, product_id: str) -> bool:
        """상품 제거"""
        original_count = len(self.config["products"])
        self.config["products"] = [p for p in self.config["products"] if p["id"] != product_id]
        
        if len(self.config["products"]) < original_count:
            self._save_config(self.config)
            self.logger.info(f"✅ 상품 {product_id} 제거 완료")
            return True
        else:
            self.logger.warning(f"⚠️  상품 {product_id}를 찾을 수 없습니다.")
            return False
    
    def list_products(self) -> List[Dict]:
        """등록된 상품 목록 반환"""
        return self.config["products"]
    
    def setup_vpn(self, provider: str, countries: List[str]):
        """VPN 설정"""
        self.config["vpn"]["provider"] = provider
        self.config["vpn"]["countries"] = countries
        self.config["vpn"]["enabled"] = True
        
        # 제공업체별 명령어 설정
        vpn_commands = {
            "expressvpn": {
                "connect": "expressvpn connect {country}",
                "disconnect": "expressvpn disconnect", 
                "status": "expressvpn status"
            },
            "nordvpn": {
                "connect": "nordvpn connect {country}",
                "disconnect": "nordvpn disconnect",
                "status": "nordvpn status"
            },
            "surfshark": {
                "connect": "surfshark-vpn attack {country}",
                "disconnect": "surfshark-vpn down",
                "status": "surfshark-vpn status"
            }
        }
        
        if provider in vpn_commands:
            self.config["vpn"].update(vpn_commands[provider])
        
        self._save_config(self.config)
        self.logger.info(f"✅ VPN 설정 완료: {provider}")
    
    def connect_vpn(self) -> bool:
        """VPN 연결"""
        if not self.config["vpn"]["enabled"]:
            return True
        
        try:
            # 랜덤 국가 선택
            country = random.choice(self.config["vpn"]["countries"])
            command = self.config["vpn"]["connect_command"].format(country=country)
            
            self.logger.info(f"🔗 VPN 연결 시도: {country}")
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                self.logger.info(f"✅ VPN 연결 성공: {country}")
                time.sleep(10)  # 연결 안정화 대기
                return True
            else:
                self.logger.error(f"❌ VPN 연결 실패: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ VPN 연결 오류: {e}")
            return False
    
    def disconnect_vpn(self) -> bool:
        """VPN 연결 해제"""
        if not self.config["vpn"]["enabled"]:
            return True
        
        try:
            command = self.config["vpn"]["disconnect_command"]
            self.logger.info("🔌 VPN 연결 해제 중...")
            
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                self.logger.info("✅ VPN 연결 해제 완료")
                return True
            else:
                self.logger.error(f"❌ VPN 해제 실패: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ VPN 해제 오류: {e}")
            return False
    
    def get_vpn_status(self) -> str:
        """VPN 상태 확인"""
        if not self.config["vpn"]["enabled"]:
            return "disabled"
        
        try:
            command = self.config["vpn"]["status_command"]
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
            return result.stdout.strip()
        except:
            return "unknown"
    
    def crawl_product(self, product: Dict) -> Optional[str]:
        """단일 상품 크롤링"""
        product_id = product["id"]
        product_name = product["name"]
        
        self.logger.info(f"🎯 크롤링 시작: {product_name} ({product_id})")
        
        # VPN 연결
        vpn_connected = self.connect_vpn()
        if not vpn_connected and self.config["vpn"]["enabled"]:
            self.logger.error("❌ VPN 연결 실패로 크롤링 중단")
            return None
        
        success_file = None
        crawler_order = self.config["crawlers"]["priority_order"]
        
        try:
            for crawler_name in crawler_order:
                for retry in range(self.config["crawlers"]["max_retries_per_crawler"]):
                    try:
                        self.logger.info(f"🤖 {crawler_name} 크롤러 시도 {retry + 1}")
                        
                        # 크롤러 실행
                        result = self._run_crawler(crawler_name, product_id)
                        
                        if result:
                            success_file = result
                            self.logger.info(f"✅ {crawler_name} 크롤러로 성공!")
                            
                            # 성공 통계 업데이트
                            product["success_count"] = product.get("success_count", 0) + 1
                            product["last_crawl"] = datetime.now().isoformat()
                            self._save_config(self.config)
                            
                            break
                        else:
                            self.logger.warning(f"⚠️  {crawler_name} 크롤러 실패")
                            time.sleep(30)  # 재시도 전 대기
                            
                    except Exception as e:
                        self.logger.error(f"❌ {crawler_name} 크롤러 오류: {e}")
                
                if success_file:
                    break
                
                # 다음 크롤러 시도 전 대기
                if crawler_name != crawler_order[-1]:
                    delay = self.config["crawlers"]["delay_between_crawlers"]
                    self.logger.info(f"⏳ 다음 크롤러 시도까지 {delay//60}분 대기...")
                    time.sleep(delay)
            
            if not success_file:
                # 실패 통계 업데이트
                product["fail_count"] = product.get("fail_count", 0) + 1
                self._save_config(self.config)
                self.logger.error(f"❌ 모든 크롤러 실패: {product_name}")
            
        finally:
            # VPN 연결 해제
            self.disconnect_vpn()
        
        return success_file
    
    def _run_crawler(self, crawler_name: str, product_id: str) -> Optional[str]:
        """개별 크롤러 실행"""
        if not CRAWLERS_AVAILABLE:
            self.logger.error("❌ 크롤러 모듈을 사용할 수 없습니다")
            return None
        
        try:
            output_dir = Path(self.config["output"]["base_directory"])
            output_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename_pattern = self.config["output"]["filename_pattern"]
            output_file = output_dir / filename_pattern.format(
                product_id=product_id,
                timestamp=timestamp,
                crawler=crawler_name
            )
            
            crawler = None
            result_df = None
            
            # 크롤러별 실행
            if crawler_name == "stealth":
                crawler = StealthNaverCrawler(product_id)
                result_df = crawler.crawl_reviews_stealth()
            elif crawler_name == "selenium":
                crawler = SeleniumNaverCrawler(product_id, headless=True)
                if crawler._setup_driver():
                    result_df = crawler.crawl_reviews()
                    crawler.close()
            elif crawler_name == "mobile":
                crawler = MobileNaverCrawler(product_id)
                result_df = crawler.crawl_reviews_mobile()
            elif crawler_name == "advanced":
                crawler = AdvancedNaverCrawler(product_id)
                result_df = crawler.crawl_reviews()
            
            # 결과 저장
            if result_df is not None and not result_df.empty:
                result_df.to_csv(output_file, index=False, encoding='utf-8-sig')
                self.logger.info(f"💾 결과 저장: {output_file}")
                return str(output_file)
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"❌ {crawler_name} 크롤러 실행 오류: {e}")
            return None
    
    def crawl_all_products(self):
        """모든 활성 상품 크롤링"""
        active_products = [p for p in self.config["products"] if p.get("enabled", True)]
        
        if not active_products:
            self.logger.info("📭 크롤링할 활성 상품이 없습니다")
            return
        
        self.logger.info(f"🚀 전체 크롤링 시작: {len(active_products)}개 상품")
        
        # 우선순위별 정렬
        active_products.sort(key=lambda x: x.get("priority", 1), reverse=True)
        
        results = []
        for i, product in enumerate(active_products, 1):
            self.logger.info(f"📦 [{i}/{len(active_products)}] {product['name']}")
            
            result = self.crawl_product(product)
            results.append({
                "product": product["name"],
                "success": result is not None,
                "file": result
            })
            
            # 상품 간 대기 (마지막 상품 제외)
            if i < len(active_products):
                wait_time = random.randint(300, 900)  # 5-15분
                self.logger.info(f"⏳ 다음 상품까지 {wait_time//60}분 대기...")
                time.sleep(wait_time)
        
        # 결과 요약
        successful = sum(1 for r in results if r["success"])
        self.logger.info(f"🎉 전체 크롤링 완료: {successful}/{len(results)} 성공")
    
    def schedule_daily_crawling(self):
        """일일 크롤링 스케줄 설정"""
        for run_time in self.config["schedule"]["auto_run_times"]:
            schedule.every().day.at(run_time).do(self.crawl_all_products)
            self.logger.info(f"⏰ 스케줄 등록: 매일 {run_time}에 크롤링 실행")
    
    def start_scheduler(self):
        """스케줄러 시작"""
        self.schedule_daily_crawling()
        self.logger.info("🎬 스케줄러 시작 - Ctrl+C로 중단")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # 1분마다 스케줄 체크
        except KeyboardInterrupt:
            self.logger.info("⛔ 스케줄러 중단됨")
    
    def manual_crawl(self, product_id_or_url: str) -> Optional[str]:
        """수동 크롤링 실행"""
        # URL인지 상품 ID인지 판단
        if product_id_or_url.startswith("http"):
            product_id = self.extract_product_id(product_id_or_url)
            if not product_id:
                self.logger.error("❌ URL에서 상품 ID를 추출할 수 없습니다")
                return None
        else:
            product_id = product_id_or_url
        
        # 임시 상품 객체 생성
        temp_product = {
            "id": product_id,
            "name": f"수동_크롤링_{product_id}",
            "url": product_id_or_url if product_id_or_url.startswith("http") else "",
            "priority": 1
        }
        
        return self.crawl_product(temp_product)


def main():
    """메인 실행 함수"""
    scheduler = SmartCrawlerScheduler()
    
    print("🤖 === 스마트 네이버 크롤링 스케줄러 ===")
    print("1. 상품 추가")
    print("2. 상품 목록 보기")
    print("3. 상품 제거")
    print("4. VPN 설정")
    print("5. 수동 크롤링")
    print("6. 스케줄러 시작")
    print("7. 전체 크롤링 (즉시 실행)")
    print("0. 종료")
    
    while True:
        try:
            choice = input("\n선택하세요 (0-7): ").strip()
            
            if choice == "0":
                break
            elif choice == "1":
                url = input("상품 URL을 입력하세요: ").strip()
                name = input("상품 이름 (선택사항): ").strip()
                if scheduler.add_product(url, name):
                    print("✅ 상품이 추가되었습니다!")
                else:
                    print("❌ 상품 추가에 실패했습니다.")
                    
            elif choice == "2":
                products = scheduler.list_products()
                if products:
                    print("\n📦 등록된 상품 목록:")
                    for i, product in enumerate(products, 1):
                        status = "🟢" if product.get("enabled", True) else "🔴"
                        print(f"{i}. {status} {product['name']} ({product['id']})")
                        print(f"   성공: {product.get('success_count', 0)}, 실패: {product.get('fail_count', 0)}")
                else:
                    print("📭 등록된 상품이 없습니다.")
                    
            elif choice == "3":
                product_id = input("제거할 상품 ID를 입력하세요: ").strip()
                if scheduler.remove_product(product_id):
                    print("✅ 상품이 제거되었습니다!")
                else:
                    print("❌ 상품을 찾을 수 없습니다.")
                    
            elif choice == "4":
                print("\n지원되는 VPN: expressvpn, nordvpn, surfshark")
                provider = input("VPN 제공업체를 입력하세요: ").strip().lower()
                countries_input = input("국가 목록 (쉼표로 구분, 예: japan,singapore): ").strip()
                countries = [c.strip() for c in countries_input.split(",") if c.strip()]
                
                if provider and countries:
                    scheduler.setup_vpn(provider, countries)
                    print("✅ VPN 설정이 완료되었습니다!")
                else:
                    print("❌ 올바른 정보를 입력해주세요.")
                    
            elif choice == "5":
                url_or_id = input("크롤링할 상품 URL 또는 ID를 입력하세요: ").strip()
                print("🚀 크롤링을 시작합니다...")
                result = scheduler.manual_crawl(url_or_id)
                if result:
                    print(f"✅ 크롤링 성공! 결과: {result}")
                else:
                    print("❌ 크롤링에 실패했습니다.")
                    
            elif choice == "6":
                print("⏰ 스케줄러를 시작합니다...")
                scheduler.start_scheduler()
                
            elif choice == "7":
                print("🚀 전체 크롤링을 시작합니다...")
                scheduler.crawl_all_products()
                
            else:
                print("❌ 올바른 번호를 선택해주세요.")
                
        except KeyboardInterrupt:
            print("\n⛔ 프로그램을 종료합니다.")
            break
        except Exception as e:
            print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    main()