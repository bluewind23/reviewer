"""
네이버 스마트 크롤러 웹 GUI
Flask 기반 웹 인터페이스
"""
from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import threading
import time
from datetime import datetime
import logging
import uuid
from smart_scheduler import SmartCrawlerScheduler

# --- Flask 앱 설정 ---
app = Flask(__name__, static_folder='static')
# 환경변수에서 시크릿 키를 가져오고, 없으면 기본값을 사용합니다.
# 터미널에서 `export FLASK_SECRET_KEY='your-secret-key'`로 설정하세요.
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'default-secret-key-for-development')

# --- 글로벌 변수 ---
scheduler = SmartCrawlerScheduler()
crawl_jobs = {}
jobs_lock = threading.Lock() # 작업 딕셔너리 접근을 위한 Lock

# --- 로깅 설정 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- 라우팅 ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

@app.route('/api/extract_product_id', methods=['POST'])
def extract_product_id():
    data = request.get_json()
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'success': False, 'error': 'URL을 입력해주세요.'}), 400
    
    product_id = scheduler.extract_product_id(url)
    if product_id:
        return jsonify({'success': True, 'message': f'상품 ID {product_id}를 추출했습니다.'})
    else:
        return jsonify({'success': False, 'error': 'URL에서 상품 ID를 찾을 수 없습니다. 올바른 네이버 쇼핑 URL인지 확인해주세요.'})

@app.route('/api/start_crawl', methods=['POST'])
def start_crawl():
    data = request.get_json()
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'success': False, 'error': 'URL을 입력해주세요.'}), 400
    
    job_id = str(uuid.uuid4())
    with jobs_lock:
        crawl_jobs[job_id] = {
            'status': 'starting', 'progress': 0, 'message': '크롤링을 준비중입니다...',
            'url': url, 'name': data.get('name', '').strip(),
            'crawler': data.get('crawler', 'auto'), 'start_time': datetime.now().isoformat(),
            'result': None, 'error': None
        }
    
    thread = threading.Thread(target=run_crawl_job, args=(job_id, url, data.get('name'), data.get('crawler')))
    thread.daemon = True
    thread.start()
    
    return jsonify({'success': True, 'job_id': job_id})

@app.route('/api/job_status/<job_id>')
def job_status(job_id):
    with jobs_lock:
        job = crawl_jobs.get(job_id)
    if job:
        return jsonify({'success': True, 'job': job})
    else:
        return jsonify({'success': False, 'error': '작업을 찾을 수 없습니다.'}), 404

@app.route('/api/products', methods=['GET'])
def get_products():
    return jsonify({'success': True, 'products': scheduler.list_products()})

@app.route('/api/add_product', methods=['POST'])
def add_product():
    data = request.get_json()
    url = data.get('url', '').strip()
    if not url: return jsonify({'success': False, 'error': 'URL을 입력해주세요.'}), 400
    
    if scheduler.add_product(url, data.get('name', '')):
        return jsonify({'success': True, 'message': '상품이 추가되었습니다.'})
    else:
        return jsonify({'success': False, 'error': '상품 추가에 실패했습니다. URL을 확인해주세요.'})

@app.route('/api/remove_product/<product_id>', methods=['DELETE'])
def remove_product(product_id):
    if scheduler.remove_product(product_id):
        return jsonify({'success': True, 'message': '상품이 제거되었습니다.'})
    else:
        return jsonify({'success': False, 'error': '상품을 찾을 수 없습니다.'}), 404

@app.route('/api/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        data = request.get_json()
        # 여기에 설정 저장 로직 추가 (VPN, 스케줄 등)
        # 예: scheduler.setup_vpn(...) or scheduler.setup_schedule(...)
        return jsonify({'success': True, 'message': '설정이 저장되었습니다.'})
    else: # GET
        return jsonify({'success': True, 'settings': scheduler.config})

@app.route('/api/vpn_status', methods=['GET'])
def vpn_status():
    status = scheduler.get_vpn_status()
    return jsonify({'success': True, 'status': status, 'enabled': scheduler.config.get("vpn", {}).get("enabled")})


# --- 백그라운드 작업 ---
def run_crawl_job(job_id, url, name, crawler_type):
    job = crawl_jobs[job_id]
    
    def update_job(status, progress, message, error=None, result=None):
        with jobs_lock:
            job['status'] = status
            job['progress'] = progress
            job['message'] = message
            if error: job['error'] = error
            if result: job['result'] = result

    try:
        update_job('extracting', 10, 'URL에서 상품 ID를 추출중입니다...')
        product_id = scheduler.extract_product_id(url)
        if not product_id:
            raise ValueError('URL에서 상품 ID를 찾을 수 없습니다.')
        
        # VPN 연결 로직은 scheduler.crawl_product 내부에서 처리됨
        
        update_job('crawling', 30, f'{crawler_type} 크롤러로 크롤링을 시작합니다...')
        
        # 임시 상품 객체 생성
        temp_product = {
            "id": product_id, "name": name or f"즉시크롤링_{product_id}",
            "url": url
        }
        
        # 특정 크롤러 또는 자동 크롤러 실행
        # crawl_product가 내부적으로 VPN 연결/해제 및 다중 크롤러를 시도함
        if crawler_type != 'auto':
            scheduler.config['crawlers']['priority_order'] = [crawler_type]
        
        result_file = scheduler.crawl_product(temp_product)
        
        if result_file:
            update_job('completed', 100, '크롤링이 성공적으로 완료되었습니다!', result=result_file)
        else:
            raise Exception("모든 크롤러가 실패했습니다. 네트워크 상태나 상품 URL을 확인해주세요.")
            
    except Exception as e:
        logger.error(f"크롤링 작업(job_id: {job_id}) 오류: {e}")
        update_job('failed', 100, '크롤링 중 오류가 발생했습니다.', error=str(e))


# --- 앱 실행 ---
if __name__ == '__main__':
    # templates 폴더가 없으면 생성
    if not os.path.exists('templates'):
        os.makedirs('templates')
    # static 폴더가 없으면 생성
    if not os.path.exists('static'):
        os.makedirs('static')

    print("🌐 네이버 스마트 크롤러 웹 GUI 시작")
    print("🔗 브라우저에서 http://localhost:9090 으로 접속하세요")
    print("⛔ 종료하려면 Ctrl+C를 누르세요")
    app.run(host='0.0.0.0', port=9090, debug=False)