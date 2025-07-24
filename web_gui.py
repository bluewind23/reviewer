"""
네이버 스마트 크롤러 웹 GUI
Flask 기반 웹 인터페이스
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
import threading
import time
import json
from datetime import datetime
import logging
from smart_scheduler import SmartCrawlerScheduler
import uuid

app = Flask(__name__)
app.secret_key = 'naver_crawler_secret_key_2024'

# 글로벌 변수
scheduler = SmartCrawlerScheduler()
crawl_jobs = {}  # 크롤링 작업 상태 추적

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/')
def index():
    """메인 페이지"""
    return render_template('index.html')

@app.route('/api/extract_product_id', methods=['POST'])
def extract_product_id():
    """URL에서 상품 ID 추출"""
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({'success': False, 'error': 'URL을 입력해주세요.'})
        
        product_id = scheduler.extract_product_id(url)
        
        if product_id:
            return jsonify({
                'success': True, 
                'product_id': product_id,
                'message': f'상품 ID {product_id}를 추출했습니다.'
            })
        else:
            return jsonify({
                'success': False, 
                'error': 'URL에서 상품 ID를 찾을 수 없습니다. 올바른 네이버 쇼핑 URL인지 확인해주세요.'
            })
            
    except Exception as e:
        logger.error(f"상품 ID 추출 오류: {e}")
        return jsonify({'success': False, 'error': f'오류가 발생했습니다: {str(e)}'})

@app.route('/api/start_crawl', methods=['POST'])
def start_crawl():
    """크롤링 시작"""
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        name = data.get('name', '').strip()
        crawler_type = data.get('crawler', 'auto')  # auto, stealth, selenium, mobile, advanced
        
        if not url:
            return jsonify({'success': False, 'error': 'URL을 입력해주세요.'})
        
        # 작업 ID 생성
        job_id = str(uuid.uuid4())
        
        # 작업 상태 초기화
        crawl_jobs[job_id] = {
            'status': 'starting',
            'progress': 0,
            'message': '크롤링을 준비중입니다...',
            'url': url,
            'name': name,
            'crawler': crawler_type,
            'start_time': datetime.now().isoformat(),
            'result': None,
            'error': None
        }
        
        # 백그라운드에서 크롤링 실행
        thread = threading.Thread(target=run_crawl_job, args=(job_id, url, name, crawler_type))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': '크롤링이 시작되었습니다.'
        })
        
    except Exception as e:
        logger.error(f"크롤링 시작 오류: {e}")
        return jsonify({'success': False, 'error': f'오류가 발생했습니다: {str(e)}'})

def run_crawl_job(job_id, url, name, crawler_type):
    """백그라운드 크롤링 작업"""
    try:
        job = crawl_jobs[job_id]
        
        # 상품 ID 추출
        job['status'] = 'extracting'
        job['progress'] = 10
        job['message'] = 'URL에서 상품 ID를 추출중입니다...'
        
        product_id = scheduler.extract_product_id(url)
        if not product_id:
            job['status'] = 'failed'
            job['error'] = 'URL에서 상품 ID를 찾을 수 없습니다.'
            return
        
        # VPN 연결
        job['status'] = 'connecting_vpn'
        job['progress'] = 20
        job['message'] = 'VPN에 연결중입니다...'
        
        vpn_connected = scheduler.connect_vpn()
        if not vpn_connected and scheduler.config["vpn"]["enabled"]:
            job['status'] = 'warning'
            job['message'] = 'VPN 연결에 실패했지만 크롤링을 계속 진행합니다...'
        
        # 크롤링 실행
        job['status'] = 'crawling'
        job['progress'] = 30
        job['message'] = f'{crawler_type} 크롤러로 크롤링중입니다...'
        
        if crawler_type == 'auto':
            # 자동 모드: 여러 크롤러 시도
            crawler_order = scheduler.config["crawlers"]["priority_order"]
            result = None
            
            for i, crawler_name in enumerate(crawler_order):
                job['progress'] = 30 + (i * 15)
                job['message'] = f'{crawler_name} 크롤러로 시도중입니다...'
                
                result = scheduler._run_crawler(crawler_name, product_id)
                if result:
                    job['crawler'] = crawler_name
                    break
                
                time.sleep(5)  # 다음 크롤러 시도 전 대기
        else:
            # 특정 크롤러 모드
            result = scheduler._run_crawler(crawler_type, product_id)
        
        # VPN 연결 해제
        job['progress'] = 90
        job['message'] = 'VPN 연결을 해제중입니다...'
        scheduler.disconnect_vpn()
        
        # 결과 처리
        if result:
            job['status'] = 'completed'
            job['progress'] = 100
            job['message'] = '크롤링이 성공적으로 완료되었습니다!'
            job['result'] = result
            job['end_time'] = datetime.now().isoformat()
        else:
            job['status'] = 'failed'
            job['error'] = '모든 크롤링 방법이 실패했습니다.'
            
    except Exception as e:
        logger.error(f"크롤링 작업 오류: {e}")
        crawl_jobs[job_id]['status'] = 'failed'
        crawl_jobs[job_id]['error'] = str(e)

@app.route('/api/job_status/<job_id>')
def job_status(job_id):
    """작업 상태 조회"""
    if job_id in crawl_jobs:
        return jsonify({'success': True, 'job': crawl_jobs[job_id]})
    else:
        return jsonify({'success': False, 'error': '작업을 찾을 수 없습니다.'})

@app.route('/api/products')
def get_products():
    """등록된 상품 목록"""
    try:
        products = scheduler.list_products()
        return jsonify({'success': True, 'products': products})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/add_product', methods=['POST'])
def add_product():
    """상품 추가"""
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        name = data.get('name', '').strip()
        
        if scheduler.add_product(url, name):
            return jsonify({'success': True, 'message': '상품이 추가되었습니다.'})
        else:
            return jsonify({'success': False, 'error': '상품 추가에 실패했습니다.'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/remove_product/<product_id>', methods=['DELETE'])
def remove_product(product_id):
    """상품 제거"""
    try:
        if scheduler.remove_product(product_id):
            return jsonify({'success': True, 'message': '상품이 제거되었습니다.'})
        else:
            return jsonify({'success': False, 'error': '상품을 찾을 수 없습니다.'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/vpn_setup', methods=['POST'])
def vpn_setup():
    """VPN 설정"""
    try:
        data = request.get_json()
        provider = data.get('provider', '').strip()
        countries = data.get('countries', [])
        
        if provider and countries:
            scheduler.setup_vpn(provider, countries)
            return jsonify({'success': True, 'message': 'VPN 설정이 완료되었습니다.'})
        else:
            return jsonify({'success': False, 'error': '올바른 정보를 입력해주세요.'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/vpn_status')
def vpn_status():
    """VPN 상태 확인"""
    try:
        status = scheduler.get_vpn_status()
        return jsonify({
            'success': True, 
            'status': status,
            'enabled': scheduler.config["vpn"]["enabled"]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/settings')
def get_settings():
    """설정 조회"""
    try:
        return jsonify({'success': True, 'settings': scheduler.config})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/settings', methods=['POST'])
def update_settings():
    """설정 업데이트"""
    try:
        data = request.get_json()
        
        # 설정 업데이트
        if 'schedule' in data:
            scheduler.config['schedule'].update(data['schedule'])
        if 'crawlers' in data:
            scheduler.config['crawlers'].update(data['crawlers'])
        if 'output' in data:
            scheduler.config['output'].update(data['output'])
            
        scheduler._save_config(scheduler.config)
        
        return jsonify({'success': True, 'message': '설정이 저장되었습니다.'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    # 템플릿 폴더 생성
    templates_dir = 'templates'
    os.makedirs(templates_dir, exist_ok=True)
    
    print("🌐 네이버 스마트 크롤러 웹 GUI 시작")
    print("🔗 브라우저에서 http://localhost:8080 으로 접속하세요")
    print("⛔ 종료하려면 Ctrl+C를 누르세요")
    
    app.run(debug=True, host='0.0.0.0', port=9090)