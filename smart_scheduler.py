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
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Tuple

try:
    from stealth_crawler import StealthNaverCrawler
    from selenium_crawler import SeleniumNaverCrawler
    from mobile_crawler import MobileNaverCrawler
    from advanced_crawler import AdvancedNaverCrawler
    CRAWLERS_AVAILABLE = True
except ImportError:
    CRAWLERS_AVAILABLE = False
    print("⚠️  크롤러 모듈들을 찾을 수 없습니다. 동일한 폴더에 있는지 확인하세요.")

def _is_valid_time_format(time_str: str) -> bool:
    """ 'HH:MM' 형식인지 검증하는 함수 """
    return bool(re.fullmatch(r"([01]?[0-9]|2[0-3]):[0-5][0-9]", time_str.strip()))

class SmartCrawlerScheduler:
    def __init__(self, config_file="crawler_config.json"):
        self.config_file = config_file
        self.config = self._load_config()
        self.setup_logging()

    def _load_config(self) -> Dict:
        default_config = {
            "schedule": {"auto_run_times": ["02:00", "03:30", "05:00"], "retry_interval_hours": 6},
            "vpn": {"enabled": False, "provider": "expressvpn", "countries": ["japan", "singapore"], "connect_command": "expressvpn connect {country}", "disconnect_command": "expressvpn disconnect", "status_command": "expressvpn status"},
            "crawlers": {"priority_order": ["stealth", "selenium", "mobile", "advanced"], "max_retries_per_crawler": 2, "delay_between_crawlers": 300},
            "output": {"base_directory": "crawl_results", "filename_pattern": "{product_id}_{timestamp}_{crawler}.csv", "keep_logs_days": 30},
            "products": []
        }
        if not os.path.exists(self.config_file):
            self._save_config(default_config)
            return default_config
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            # 기본 설정으로 누락된 키 보완
            for key, value in default_config.items():
                if key not in config: config[key] = value
                elif isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        if sub_key not in config.get(key, {}): config[key][sub_key] = sub_value
            return config
        except Exception as e:
            print(f"⚠️  설정 파일 로드 실패: {e}")
            return default_config

    def _save_config(self, config: Dict):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ 설정 파일 저장 실패: {e}")

    def setup_logging(self):
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"crawler_scheduler_{datetime.now().strftime('%Y%m%d')}.log"
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.FileHandler(log_file, encoding='utf-8'), logging.StreamHandler()])
        self.logger = logging.getLogger(__name__)
    
    def extract_product_id(self, url: str) -> Optional[str]:
        patterns = [
            r'smartstore\.naver\.com/[^/]+/products/(\d+)', r'shopping\.naver\.com/.*?nvMid=(\d+)',
            r'm\.smartstore\.naver\.com/.*?/products/(\d+)', r'm\.shopping\.naver\.com/.*?nvMid=(\d+)',
            r'[?&]productId=(\d+)', r'[?&]id=(\d+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                self.logger.info(f"✅ URL에서 상품 ID 추출 성공: {match.group(1)}")
                return match.group(1)
        self.logger.error(f"❌ URL에서 상품 ID를 찾을 수 없습니다: {url}")
        return None

    def add_product(self, url: str, name: str = "", priority: int = 1) -> bool:
        product_id = self.extract_product_id(url)
        if not product_id: return False
        
        products = self.config.get('products', [])
        if any(p.get('id') == product_id for p in products):
            self.logger.info(f"⚠️  상품 {product_id}는 이미 등록되어 있습니다.")
            return True # 이미 있으므로 성공으로 간주
        
        product = {"id": product_id, "url": url, "name": name or f"상품_{product_id}", "priority": priority, "added_date": datetime.now().isoformat(), "last_crawl": None, "success_count": 0, "fail_count": 0, "enabled": True}
        products.append(product)
        self.config['products'] = products
        self._save_config(self.config)
        self.logger.info(f"✅ 상품 추가 완료: {name} ({product_id})")
        return True

    def remove_product(self, product_id: str) -> bool:
        products = self.config.get('products', [])
        original_count = len(products)
        self.config['products'] = [p for p in products if p.get('id') != product_id]
        if len(self.config['products']) < original_count:
            self._save_config(self.config)
            self.logger.info(f"✅ 상품 {product_id} 제거 완료")
            return True
        return False
    
    def list_products(self) -> List[Dict]:
        return self.config.get('products', [])

    def connect_vpn(self) -> bool:
        vpn_config = self.config.get('vpn', {})
        if not vpn_config.get('enabled'): return True
        try:
            country = random.choice(vpn_config.get('countries', []))
            command = vpn_config.get('connect_command', "").format(country=country)
            self.logger.info(f"🔗 VPN 연결 시도: {country}")
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                self.logger.info(f"✅ VPN 연결 성공: {country}"); time.sleep(10); return True
            self.logger.error(f"❌ VPN 연결 실패: {result.stderr or result.stdout}"); return False
        except Exception as e:
            self.logger.error(f"❌ VPN 연결 오류: {e}"); return False

    def disconnect_vpn(self) -> bool:
        vpn_config = self.config.get('vpn', {})
        if not vpn_config.get('enabled'): return True
        try:
            command = vpn_config.get('disconnect_command', "")
            self.logger.info("🔌 VPN 연결 해제 중...")
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
            if result.returncode == 0: self.logger.info("✅ VPN 연결 해제 완료"); return True
            self.logger.error(f"❌ VPN 해제 실패: {result.stderr or result.stdout}"); return False
        except Exception as e:
            self.logger.error(f"❌ VPN 해제 오류: {e}"); return False

    def get_vpn_status(self) -> str:
        vpn_config = self.config.get('vpn', {})
        if not vpn_config.get('enabled'): return "비활성화됨"
        try:
            command = vpn_config.get('status_command', "")
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
            return result.stdout.strip()
        except: return "상태 확인 불가"

    def crawl_product(self, product: Dict) -> Optional[str]:
        product_id = product.get("id")
        self.logger.info(f"🎯 크롤링 시작: {product.get('name', '')} ({product_id})")
        
        vpn_config = self.config.get("vpn", {})
        if vpn_config.get("enabled"):
            if not self.connect_vpn():
                self.logger.error("❌ VPN 연결 실패로 크롤링 중단")
                return None
        
        success_file = None
        crawler_config = self.config.get('crawlers', {})
        crawler_order = crawler_config.get('priority_order', [])
        
        try:
            for crawler_name in crawler_order:
                for retry in range(crawler_config.get('max_retries_per_crawler', 1)):
                    self.logger.info(f"🤖 {crawler_name} 크롤러 시도 ({retry + 1})")
                    result_path, status_code = self._run_crawler(crawler_name, product_id)
                    
                    if result_path:
                        success_file = result_path
                        self.logger.info(f"✅ {crawler_name} 크롤러로 성공!")
                        product['success_count'] = product.get('success_count', 0) + 1
                        break # 성공 시 다음 크롤러로 넘어가지 않음
                    
                    self.logger.warning(f"⚠️ {crawler_name} 크롤러 실패 (상태: {status_code})")
                    if status_code in [403, 429] and vpn_config.get("enabled"):
                        self.logger.warning("🚫 IP 차단 가능성. VPN 재연결 시도.")
                        self.disconnect_vpn(); time.sleep(5); self.connect_vpn()
                if success_file: break
            
            if not success_file:
                product['fail_count'] = product.get('fail_count', 0) + 1
                self.logger.error(f"❌ 모든 크롤러 실패: {product.get('name')}")
            product['last_crawl'] = datetime.now().isoformat()
            self._save_config(self.config)
        finally:
            if vpn_config.get("enabled"):
                self.disconnect_vpn()
        return success_file
    
    def _run_crawler(self, crawler_name: str, product_id: str) -> Tuple[Optional[str], Optional[int]]:
        if not CRAWLERS_AVAILABLE: return None, None
        
        output_config = self.config.get('output', {})
        output_dir = Path(output_config.get('base_directory', 'crawl_results'))
        output_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_pattern = output_config.get('filename_pattern', '{product_id}_{timestamp}_{crawler}.csv')
        filename = filename_pattern.format(product_id=product_id, timestamp=timestamp, crawler=crawler_name)
        output_file = output_dir / filename
        status_code = None

        try:
            crawler_map = {
                "advanced": AdvancedNaverCrawler, "stealth": StealthNaverCrawler,
                "mobile": MobileNaverCrawler, "selenium": SeleniumNaverCrawler,
            }
            if crawler_name not in crawler_map:
                self.logger.error(f"알 수 없는 크롤러: {crawler_name}"); return None, None

            crawler_instance = crawler_map[crawler_name](product_id)
            
            # 각 크롤러 인스턴스의 정보 획득 메서드를 호출하여 상태 코드 확인
            info_method_map = {
                "advanced": "get_product_info", "stealth": "get_product_info_stealth",
                "mobile": "get_product_info_mobile", "selenium": "get_product_info"
            }
            if hasattr(crawler_instance, info_method_map[crawler_name]):
                 _, _, status_code = getattr(crawler_instance, info_method_map[crawler_name])()
            
            result_df = None
            if status_code == 200:
                result_df = crawler_instance.crawl_reviews()

            if result_df is not None and not result_df.empty:
                result_df.to_csv(output_file, index=False, encoding='utf-8-sig')
                self.logger.info(f"💾 결과 저장: {output_file}")
                return str(output_file), 200
            else:
                return None, status_code
        except Exception as e:
            self.logger.error(f"❌ {crawler_name} 실행 오류: {e}")
            return None, status_code

    def start_scheduler(self):
        self.logger.info("🎬 스케줄러 시작 - Ctrl+C로 중단")
        schedule_times = self.config.get('schedule', {}).get('auto_run_times', [])
        for run_time in schedule_times:
            if _is_valid_time_format(run_time):
                schedule.every().day.at(run_time).do(self.crawl_all_products)
                self.logger.info(f"⏰ 스케줄 등록: 매일 {run_time}")
        try:
            while True:
                schedule.run_pending(); time.sleep(60)
        except KeyboardInterrupt:
            self.logger.info("⛔ 스케줄러 중단됨")

    def crawl_all_products(self):
        self.logger.info(f"🚀 전체 크롤링 시작")
        active_products = [p for p in self.list_products() if p.get("enabled", True)]
        for product in active_products:
            self.crawl_product(product)

    def manual_crawl(self, product_id_or_url: str) -> Optional[str]:
        if product_id_or_url.startswith("http"):
            product_id = self.extract_product_id(product_id_or_url)
            if not product_id: return None
        else:
            product_id = product_id_or_url
        
        temp_product = {"id": product_id, "name": f"수동_{product_id}", "url": product_id_or_url}
        return self.crawl_product(temp_product)

if __name__ == "__main__":
    scheduler = SmartCrawlerScheduler()
    while True:
        print("\n🤖 === 스마트 네이버 크롤링 스케줄러 ===")
        print("1. 상품 추가")
        print("2. 상품 목록 보기")
        print("3. 상품 제거")
        print("4. VPN/스케줄 설정")
        print("5. 수동 크롤링 (URL/ID 입력)")
        print("6. 스케줄러 시작 (자동 실행)")
        print("7. 전체 상품 즉시 크롤링")
        print("0. 종료")
        choice = input("선택하세요: ").strip()

        if choice == '1':
            url = input("상품 URL: ").strip()
            name = input("상품 이름 (선택사항): ").strip()
            scheduler.add_product(url, name)
        elif choice == '2':
            for p in scheduler.list_products(): print(p)
        elif choice == '3':
            pid = input("제거할 상품 ID: ").strip()
            scheduler.remove_product(pid)
        elif choice == '4':
            print("--- VPN 설정 ---")
            provider = input("VPN 제공업체 (expressvpn/nordvpn/surfshark): ").strip()
            countries_str = input("국가 목록 (쉼표로 구분): ").strip()
            if provider and countries_str:
                scheduler.config['vpn']['provider'] = provider
                scheduler.config['vpn']['countries'] = [c.strip() for c in countries_str.split(',')]
                scheduler.config['vpn']['enabled'] = True
            print("--- 스케줄 설정 ---")
            times_str = input("자동 실행 시간 (HH:MM, 쉼표 구분): ").strip()
            times = [t.strip() for t in times_str.split(',')]
            if all(_is_valid_time_format(t) for t in times):
                scheduler.config['schedule']['auto_run_times'] = times
                print("✅ 스케줄 시간이 설정되었습니다.")
            else:
                print("❌ 잘못된 시간 형식이 포함되어 있습니다.")
            scheduler._save_config(scheduler.config)
        elif choice == '5':
            url_or_id = input("크롤링할 URL 또는 상품 ID: ").strip()
            scheduler.manual_crawl(url_or_id)
        elif choice == '6':
            scheduler.start_scheduler()
        elif choice == '7':
            scheduler.crawl_all_products()
        elif choice == '0':
            break