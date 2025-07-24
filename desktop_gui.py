"""
네이버 스마트 크롤러 데스크톱 GUI
Tkinter 기반 데스크톱 애플리케이션
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading
import time
import os
from datetime import datetime
from smart_scheduler import SmartCrawlerScheduler
import queue
import json

class CrawlerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("네이버 스마트 크롤러 v2.0")
        self.root.geometry("900x700")
        self.root.configure(bg='#f0f0f0')
        
        # 스케줄러 초기화
        self.scheduler = SmartCrawlerScheduler()
        
        # 메시지 큐 (스레드 간 통신)
        self.message_queue = queue.Queue()
        
        # 크롤링 상태
        self.is_crawling = False
        self.current_job = None
        
        self.setup_ui()
        self.load_settings()
        
        # 메시지 큐 확인 타이머
        self.root.after(100, self.check_queue)
    
    def setup_ui(self):
        """UI 구성"""
        # 스타일 설정
        style = ttk.Style()
        style.theme_use('clam')
        
        # 메인 프레임
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 제목
        title_label = ttk.Label(main_frame, text="🕷️ 네이버 스마트 크롤러", 
                               font=('Arial', 16, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # 노트북 (탭 컨테이너)
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # 탭들 생성
        self.create_crawl_tab()
        self.create_products_tab()
        self.create_settings_tab()
        self.create_log_tab()
        
        # 하단 상태바
        self.create_status_bar(main_frame)
    
    def create_crawl_tab(self):
        """즉시 크롤링 탭"""
        crawl_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(crawl_frame, text="즉시 크롤링")
        
        # URL 입력 그룹
        url_group = ttk.LabelFrame(crawl_frame, text="상품 정보", padding="10")
        url_group.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(url_group, text="상품 URL:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.url_entry = ttk.Entry(url_group, width=80)
        self.url_entry.grid(row=0, column=1, columnspan=2, sticky=tk.EW, padx=(10, 0), pady=5)
        url_group.columnconfigure(1, weight=1)
        
        ttk.Label(url_group, text="상품명:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.name_entry = ttk.Entry(url_group, width=40)
        self.name_entry.grid(row=1, column=1, sticky=tk.EW, padx=(10, 0), pady=5)
        
        self.extract_btn = ttk.Button(url_group, text="상품 ID 확인", command=self.extract_product_id)
        self.extract_btn.grid(row=1, column=2, padx=(10, 0), pady=5)
        
        # 크롤러 선택 그룹
        crawler_group = ttk.LabelFrame(crawl_frame, text="크롤러 설정", padding="10")
        crawler_group.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(crawler_group, text="크롤러 선택:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.crawler_var = tk.StringVar(value="auto")
        crawler_combo = ttk.Combobox(crawler_group, textvariable=self.crawler_var, width=20, state="readonly")
        crawler_combo['values'] = ('auto', 'stealth', 'selenium', 'mobile', 'advanced')
        crawler_combo.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        # VPN 설정
        self.vpn_var = tk.BooleanVar()
        ttk.Checkbutton(crawler_group, text="VPN 사용", variable=self.vpn_var).grid(row=0, column=2, padx=(20, 0), pady=5)
        
        # 크롤링 버튼
        button_frame = ttk.Frame(crawl_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.crawl_btn = ttk.Button(button_frame, text="🚀 크롤링 시작", 
                                   command=self.start_crawling, style='Accent.TButton')
        self.crawl_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        self.stop_btn = ttk.Button(button_frame, text="⏹️ 중단", 
                                  command=self.stop_crawling, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.RIGHT)
        
        # 진행 상태 그룹
        progress_group = ttk.LabelFrame(crawl_frame, text="진행 상태", padding="10")
        progress_group.pack(fill=tk.BOTH, expand=True)
        
        # 진행률 바
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_group, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=(0, 10))
        
        # 상태 메시지
        self.status_var = tk.StringVar(value="대기중...")
        ttk.Label(progress_group, textvariable=self.status_var, font=('Arial', 10)).pack(anchor=tk.W)
        
        # 결과 표시
        self.result_text = scrolledtext.ScrolledText(progress_group, height=15, wrap=tk.WORD)
        self.result_text.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
    
    def create_products_tab(self):
        """상품 관리 탭"""
        products_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(products_frame, text="상품 관리")
        
        # 상품 추가 그룹
        add_group = ttk.LabelFrame(products_frame, text="상품 추가", padding="10")
        add_group.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(add_group, text="URL:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.new_url_entry = ttk.Entry(add_group, width=50)
        self.new_url_entry.grid(row=0, column=1, sticky=tk.EW, padx=(10, 0), pady=5)
        
        ttk.Label(add_group, text="이름:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.new_name_entry = ttk.Entry(add_group, width=30)
        self.new_name_entry.grid(row=1, column=1, sticky=tk.EW, padx=(10, 0), pady=5)
        
        ttk.Button(add_group, text="추가", command=self.add_product).grid(row=0, column=2, rowspan=2, padx=(10, 0))
        add_group.columnconfigure(1, weight=1)
        
        # 상품 목록 그룹
        list_group = ttk.LabelFrame(products_frame, text="등록된 상품", padding="10")
        list_group.pack(fill=tk.BOTH, expand=True)
        
        # 트리뷰 (테이블)
        columns = ('name', 'id', 'success', 'fail', 'last_crawl')
        self.products_tree = ttk.Treeview(list_group, columns=columns, show='headings', height=15)
        
        # 컬럼 헤더
        self.products_tree.heading('name', text='상품명')
        self.products_tree.heading('id', text='상품 ID')
        self.products_tree.heading('success', text='성공')
        self.products_tree.heading('fail', text='실패')
        self.products_tree.heading('last_crawl', text='마지막 크롤링')
        
        # 컬럼 너비
        self.products_tree.column('name', width=200)
        self.products_tree.column('id', width=100)
        self.products_tree.column('success', width=60)
        self.products_tree.column('fail', width=60)
        self.products_tree.column('last_crawl', width=150)
        
        # 스크롤바
        products_scroll = ttk.Scrollbar(list_group, orient=tk.VERTICAL, command=self.products_tree.yview)
        self.products_tree.configure(yscrollcommand=products_scroll.set)
        
        self.products_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        products_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 버튼 프레임
        products_btn_frame = ttk.Frame(list_group)
        products_btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(products_btn_frame, text="새로고침", command=self.refresh_products).pack(side=tk.LEFT)
        ttk.Button(products_btn_frame, text="제거", command=self.remove_product).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Button(products_btn_frame, text="전체 크롤링", command=self.crawl_all_products).pack(side=tk.RIGHT)
    
    def create_settings_tab(self):
        """설정 탭"""
        settings_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(settings_frame, text="설정")
        
        # VPN 설정 그룹
        vpn_group = ttk.LabelFrame(settings_frame, text="VPN 설정", padding="10")
        vpn_group.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(vpn_group, text="제공업체:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.vpn_provider_var = tk.StringVar(value="expressvpn")
        vpn_combo = ttk.Combobox(vpn_group, textvariable=self.vpn_provider_var, width=15, state="readonly")
        vpn_combo['values'] = ('expressvpn', 'nordvpn', 'surfshark')
        vpn_combo.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        ttk.Label(vpn_group, text="국가:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.vpn_countries_entry = ttk.Entry(vpn_group, width=40)
        self.vpn_countries_entry.insert(0, "japan,singapore,australia")
        self.vpn_countries_entry.grid(row=1, column=1, columnspan=2, sticky=tk.EW, padx=(10, 0), pady=5)
        
        ttk.Button(vpn_group, text="VPN 설정 저장", command=self.save_vpn_settings).grid(row=2, column=0, columnspan=3, pady=10)
        vpn_group.columnconfigure(2, weight=1)
        
        # 스케줄 설정 그룹
        schedule_group = ttk.LabelFrame(settings_frame, text="스케줄 설정", padding="10")
        schedule_group.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(schedule_group, text="자동 실행 시간:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.schedule_entry = ttk.Entry(schedule_group, width=30)
        self.schedule_entry.insert(0, "02:00,03:30,05:00")
        self.schedule_entry.grid(row=0, column=1, sticky=tk.EW, padx=(10, 0), pady=5)
        
        ttk.Label(schedule_group, text="재시도 간격(시간):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.retry_interval_entry = ttk.Entry(schedule_group, width=10)
        self.retry_interval_entry.insert(0, "6")
        self.retry_interval_entry.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        ttk.Button(schedule_group, text="스케줄 설정 저장", command=self.save_schedule_settings).grid(row=2, column=0, columnspan=2, pady=10)
        schedule_group.columnconfigure(1, weight=1)
        
        # 출력 설정 그룹
        output_group = ttk.LabelFrame(settings_frame, text="출력 설정", padding="10")
        output_group.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(output_group, text="저장 폴더:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.output_dir_var = tk.StringVar(value="crawl_results")
        ttk.Entry(output_group, textvariable=self.output_dir_var, width=40).grid(row=0, column=1, sticky=tk.EW, padx=(10, 0), pady=5)
        ttk.Button(output_group, text="찾아보기", command=self.select_output_dir).grid(row=0, column=2, padx=(10, 0), pady=5)
        
        ttk.Button(output_group, text="폴더 열기", command=self.open_output_dir).grid(row=1, column=0, pady=10)
        ttk.Button(output_group, text="설정 저장", command=self.save_output_settings).grid(row=1, column=1, pady=10)
        output_group.columnconfigure(1, weight=1)
    
    def create_log_tab(self):
        """로그 탭"""
        log_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(log_frame, text="로그")
        
        # 로그 표시
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, font=('Consolas', 9))
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 로그 제어 버튼
        log_btn_frame = ttk.Frame(log_frame)
        log_btn_frame.pack(fill=tk.X)
        
        ttk.Button(log_btn_frame, text="로그 지우기", command=self.clear_log).pack(side=tk.LEFT)
        ttk.Button(log_btn_frame, text="로그 저장", command=self.save_log).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Button(log_btn_frame, text="새로고침", command=self.refresh_log).pack(side=tk.RIGHT)
    
    def create_status_bar(self, parent):
        """상태바 생성"""
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        # 구분선
        ttk.Separator(status_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 5))
        
        # 상태 정보
        self.status_label = ttk.Label(status_frame, text="준비됨", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 시간 표시
        self.time_label = ttk.Label(status_frame, text="", relief=tk.SUNKEN, width=20)
        self.time_label.pack(side=tk.RIGHT)
        
        self.update_time()
    
    def update_time(self):
        """시간 업데이트"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=current_time)
        self.root.after(1000, self.update_time)
    
    def extract_product_id(self):
        """상품 ID 추출"""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("경고", "URL을 입력해주세요.")
            return
        
        try:
            product_id = self.scheduler.extract_product_id(url)
            if product_id:
                messagebox.showinfo("성공", f"상품 ID: {product_id}")
                self.log_message(f"상품 ID 추출 성공: {product_id}")
            else:
                messagebox.showerror("오류", "URL에서 상품 ID를 찾을 수 없습니다.")
        except Exception as e:
            messagebox.showerror("오류", f"상품 ID 추출 실패: {str(e)}")
    
    def start_crawling(self):
        """크롤링 시작"""
        if self.is_crawling:
            messagebox.showwarning("경고", "이미 크롤링이 진행 중입니다.")
            return
        
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("경고", "URL을 입력해주세요.")
            return
        
        # UI 상태 변경
        self.is_crawling = True
        self.crawl_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.progress_var.set(0)
        self.status_var.set("크롤링 시작...")
        self.result_text.delete(1.0, tk.END)
        
        # 크롤링 스레드 시작
        self.current_job = {
            'url': url,
            'name': self.name_entry.get().strip(),
            'crawler': self.crawler_var.get(),
            'use_vpn': self.vpn_var.get()
        }
        
        thread = threading.Thread(target=self.crawling_worker, daemon=True)
        thread.start()
        
        self.log_message(f"크롤링 시작: {url}")
    
    def crawling_worker(self):
        """크롤링 작업 스레드"""
        try:
            job = self.current_job
            
            # 메시지 큐를 통해 UI 업데이트
            self.message_queue.put(('progress', 10, '상품 ID 추출 중...'))
            
            # 상품 ID 추출
            product_id = self.scheduler.extract_product_id(job['url'])
            if not product_id:
                self.message_queue.put(('error', 'URL에서 상품 ID를 찾을 수 없습니다.'))
                return
            
            self.message_queue.put(('log', f'상품 ID: {product_id}'))
            
            # VPN 연결
            if job['use_vpn']:
                self.message_queue.put(('progress', 20, 'VPN 연결 중...'))
                vpn_success = self.scheduler.connect_vpn()
                if not vpn_success and self.scheduler.config["vpn"]["enabled"]:
                    self.message_queue.put(('log', 'VPN 연결 실패, 크롤링 계속 진행'))
                else:
                    self.message_queue.put(('log', 'VPN 연결 성공'))
            
            # 크롤링 실행
            self.message_queue.put(('progress', 30, f'{job["crawler"]} 크롤러로 크롤링 중...'))
            
            if job['crawler'] == 'auto':
                # 자동 모드
                crawler_order = self.scheduler.config["crawlers"]["priority_order"]
                result = None
                
                for i, crawler_name in enumerate(crawler_order):
                    progress = 30 + (i * 15)
                    self.message_queue.put(('progress', progress, f'{crawler_name} 크롤러 시도 중...'))
                    
                    result = self.scheduler._run_crawler(crawler_name, product_id)
                    if result:
                        self.message_queue.put(('log', f'{crawler_name} 크롤러 성공'))
                        break
                    else:
                        self.message_queue.put(('log', f'{crawler_name} 크롤러 실패'))
                    
                    if not self.is_crawling:  # 중단 확인
                        break
                    
                    time.sleep(5)
            else:
                # 특정 크롤러
                result = self.scheduler._run_crawler(job['crawler'], product_id)
            
            # VPN 해제
            if job['use_vpn']:
                self.message_queue.put(('progress', 90, 'VPN 연결 해제 중...'))
                self.scheduler.disconnect_vpn()
                self.message_queue.put(('log', 'VPN 연결 해제'))
            
            # 결과 처리
            if result and self.is_crawling:
                self.message_queue.put(('progress', 100, '크롤링 완료!'))
                self.message_queue.put(('success', f'크롤링 성공!\n결과 파일: {result}'))
            elif self.is_crawling:
                self.message_queue.put(('error', '크롤링 실패'))
            
        except Exception as e:
            self.message_queue.put(('error', f'크롤링 오류: {str(e)}'))
        finally:
            if self.is_crawling:  # 정상 완료인 경우만
                self.message_queue.put(('complete', None))
    
    def stop_crawling(self):
        """크롤링 중단"""
        self.is_crawling = False
        self.crawl_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_var.set("크롤링 중단됨")
        self.log_message("사용자에 의해 크롤링 중단됨")
    
    def check_queue(self):
        """메시지 큐 확인 (UI 업데이트)"""
        try:
            while True:
                msg_type, data, *extra = self.message_queue.get_nowait()
                
                if msg_type == 'progress':
                    progress, message = data, extra[0] if extra else ""
                    self.progress_var.set(progress)
                    self.status_var.set(message)
                    
                elif msg_type == 'log':
                    self.log_message(data)
                    
                elif msg_type == 'success':
                    self.result_text.insert(tk.END, f"✅ {data}\n")
                    self.result_text.see(tk.END)
                    
                elif msg_type == 'error':
                    self.result_text.insert(tk.END, f"❌ {data}\n")
                    self.result_text.see(tk.END)
                    messagebox.showerror("오류", data)
                    
                elif msg_type == 'complete':
                    self.is_crawling = False
                    self.crawl_btn.config(state=tk.NORMAL)
                    self.stop_btn.config(state=tk.DISABLED)
                    self.status_var.set("완료")
                    
        except queue.Empty:
            pass
        
        self.root.after(100, self.check_queue)
    
    def add_product(self):
        """상품 추가"""
        url = self.new_url_entry.get().strip()
        name = self.new_name_entry.get().strip()
        
        if not url:
            messagebox.showwarning("경고", "URL을 입력해주세요.")
            return
        
        try:
            if self.scheduler.add_product(url, name):
                messagebox.showinfo("성공", "상품이 추가되었습니다.")
                self.new_url_entry.delete(0, tk.END)
                self.new_name_entry.delete(0, tk.END)
                self.refresh_products()
                self.log_message(f"상품 추가: {name or url}")
            else:
                messagebox.showerror("오류", "상품 추가에 실패했습니다.")
        except Exception as e:
            messagebox.showerror("오류", f"상품 추가 오류: {str(e)}")
    
    def remove_product(self):
        """선택된 상품 제거"""
        selection = self.products_tree.selection()
        if not selection:
            messagebox.showwarning("경고", "제거할 상품을 선택해주세요.")
            return
        
        item = self.products_tree.item(selection[0])
        product_id = item['values'][1]  # ID 컬럼
        
        if messagebox.askyesno("확인", f"상품 ID {product_id}를 정말 제거하시겠습니까?"):
            try:
                if self.scheduler.remove_product(product_id):
                    messagebox.showinfo("성공", "상품이 제거되었습니다.")
                    self.refresh_products()
                    self.log_message(f"상품 제거: {product_id}")
                else:
                    messagebox.showerror("오류", "상품을 찾을 수 없습니다.")
            except Exception as e:
                messagebox.showerror("오류", f"상품 제거 오류: {str(e)}")
    
    def refresh_products(self):
        """상품 목록 새로고침"""
        try:
            # 기존 항목 제거
            for item in self.products_tree.get_children():
                self.products_tree.delete(item)
            
            # 상품 목록 로드
            products = self.scheduler.list_products()
            for product in products:
                last_crawl = product.get('last_crawl', '')
                if last_crawl:
                    try:
                        last_crawl = datetime.fromisoformat(last_crawl).strftime('%Y-%m-%d %H:%M')
                    except:
                        pass
                
                self.products_tree.insert('', tk.END, values=(
                    product['name'],
                    product['id'],
                    product.get('success_count', 0),
                    product.get('fail_count', 0),
                    last_crawl
                ))
        except Exception as e:
            messagebox.showerror("오류", f"상품 목록 로드 오류: {str(e)}")
    
    def crawl_all_products(self):
        """전체 상품 크롤링"""
        products = self.scheduler.list_products()
        if not products:
            messagebox.showinfo("알림", "등록된 상품이 없습니다.")
            return
        
        if messagebox.askyesno("확인", f"{len(products)}개의 상품을 모두 크롤링하시겠습니까?\n시간이 오래 걸릴 수 있습니다."):
            # 별도 창에서 진행상태 표시
            self.show_batch_crawl_window(products)
    
    def show_batch_crawl_window(self, products):
        """일괄 크롤링 진행 창"""
        batch_window = tk.Toplevel(self.root)
        batch_window.title("일괄 크롤링")
        batch_window.geometry("500x400")
        batch_window.transient(self.root)
        batch_window.grab_set()
        
        # 진행 상태
        ttk.Label(batch_window, text="일괄 크롤링 진행 상태", font=('Arial', 12, 'bold')).pack(pady=10)
        
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(batch_window, variable=progress_var, maximum=len(products))
        progress_bar.pack(fill=tk.X, padx=20, pady=10)
        
        status_var = tk.StringVar(value="준비 중...")
        ttk.Label(batch_window, textvariable=status_var).pack(pady=5)
        
        # 결과 로그
        result_log = scrolledtext.ScrolledText(batch_window, height=15, wrap=tk.WORD)
        result_log.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # 중단 버튼
        def stop_batch():
            nonlocal batch_running
            batch_running = False
            status_var.set("중단 중...")
        
        batch_running = True
        stop_btn = ttk.Button(batch_window, text="중단", command=stop_batch)
        stop_btn.pack(pady=10)
        
        # 일괄 크롤링 스레드
        def batch_worker():
            try:
                for i, product in enumerate(products):
                    if not batch_running:
                        break
                    
                    status_var.set(f"[{i+1}/{len(products)}] {product['name']} 크롤링 중...")
                    result_log.insert(tk.END, f"🚀 {product['name']} 시작...\n")
                    result_log.see(tk.END)
                    batch_window.update()
                    
                    try:
                        result = self.scheduler.crawl_product(product)
                        if result:
                            result_log.insert(tk.END, f"✅ {product['name']} 성공: {result}\n")
                        else:
                            result_log.insert(tk.END, f"❌ {product['name']} 실패\n")
                    except Exception as e:
                        result_log.insert(tk.END, f"❌ {product['name']} 오류: {str(e)}\n")
                    
                    progress_var.set(i + 1)
                    result_log.see(tk.END)
                    batch_window.update()
                    
                    if i < len(products) - 1 and batch_running:
                        time.sleep(10)  # 상품 간 대기
                
                if batch_running:
                    status_var.set("모든 크롤링 완료!")
                    result_log.insert(tk.END, "\n🎉 일괄 크롤링 완료!\n")
                else:
                    status_var.set("사용자에 의해 중단됨")
                    result_log.insert(tk.END, "\n⏹️ 크롤링 중단됨\n")
                
                stop_btn.config(text="닫기", command=batch_window.destroy)
                self.refresh_products()
                
            except Exception as e:
                result_log.insert(tk.END, f"\n💥 일괄 크롤링 오류: {str(e)}\n")
                stop_btn.config(text="닫기", command=batch_window.destroy)
        
        thread = threading.Thread(target=batch_worker, daemon=True)
        thread.start()
    
    def save_vpn_settings(self):
        """VPN 설정 저장"""
        try:
            provider = self.vpn_provider_var.get()
            countries_str = self.vpn_countries_entry.get().strip()
            countries = [c.strip() for c in countries_str.split(',') if c.strip()]
            
            if not countries:
                messagebox.showwarning("경고", "최소 하나의 국가를 입력해주세요.")
                return
            
            self.scheduler.setup_vpn(provider, countries)
            messagebox.showinfo("성공", "VPN 설정이 저장되었습니다.")
            self.log_message(f"VPN 설정 저장: {provider}, {countries}")
            
        except Exception as e:
            messagebox.showerror("오류", f"VPN 설정 저장 오류: {str(e)}")
    
    def save_schedule_settings(self):
        """스케줄 설정 저장"""
        try:
            times_str = self.schedule_entry.get().strip()
            retry_interval = int(self.retry_interval_entry.get())
            
            times = [t.strip() for t in times_str.split(',') if t.strip()]
            
            self.scheduler.config['schedule']['auto_run_times'] = times
            self.scheduler.config['schedule']['retry_interval_hours'] = retry_interval
            self.scheduler._save_config(self.scheduler.config)
            
            messagebox.showinfo("성공", "스케줄 설정이 저장되었습니다.")
            self.log_message(f"스케줄 설정 저장: {times}, 재시도 간격: {retry_interval}시간")
            
        except Exception as e:
            messagebox.showerror("오류", f"스케줄 설정 저장 오류: {str(e)}")
    
    def save_output_settings(self):
        """출력 설정 저장"""
        try:
            output_dir = self.output_dir_var.get().strip()
            
            self.scheduler.config['output']['base_directory'] = output_dir
            self.scheduler._save_config(self.scheduler.config)
            
            # 디렉토리 생성
            os.makedirs(output_dir, exist_ok=True)
            
            messagebox.showinfo("성공", "출력 설정이 저장되었습니다.")
            self.log_message(f"출력 디렉토리 설정: {output_dir}")
            
        except Exception as e:
            messagebox.showerror("오류", f"출력 설정 저장 오류: {str(e)}")
    
    def select_output_dir(self):
        """출력 디렉토리 선택"""
        directory = filedialog.askdirectory()
        if directory:
            self.output_dir_var.set(directory)
    
    def open_output_dir(self):
        """출력 디렉토리 열기"""
        output_dir = self.output_dir_var.get()
        if os.path.exists(output_dir):
            os.startfile(output_dir) if os.name == 'nt' else os.system(f'open "{output_dir}"')
        else:
            messagebox.showwarning("경고", "디렉토리가 존재하지 않습니다.")
    
    def log_message(self, message):
        """로그 메시지 추가"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        
        # 상태바 업데이트
        self.status_label.config(text=message)
    
    def clear_log(self):
        """로그 지우기"""
        self.log_text.delete(1.0, tk.END)
    
    def save_log(self):
        """로그 저장"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("텍스트 파일", "*.txt"), ("모든 파일", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.get(1.0, tk.END))
                messagebox.showinfo("성공", "로그가 저장되었습니다.")
            except Exception as e:
                messagebox.showerror("오류", f"로그 저장 오류: {str(e)}")
    
    def refresh_log(self):
        """로그 새로고침 (실제 로그 파일에서 로드)"""
        # TODO: 실제 로그 파일이 있다면 여기서 로드
        self.log_message("로그 새로고침")
    
    def load_settings(self):
        """설정 로드"""
        try:
            config = self.scheduler.config
            
            # VPN 설정
            if 'vpn' in config:
                vpn = config['vpn']
                self.vpn_provider_var.set(vpn.get('provider', 'expressvpn'))
                countries = vpn.get('countries', ['japan', 'singapore', 'australia'])
                self.vpn_countries_entry.delete(0, tk.END)
                self.vpn_countries_entry.insert(0, ','.join(countries))
            
            # 스케줄 설정
            if 'schedule' in config:
                schedule = config['schedule']
                times = schedule.get('auto_run_times', ['02:00', '03:30', '05:00'])
                self.schedule_entry.delete(0, tk.END)
                self.schedule_entry.insert(0, ','.join(times))
                
                interval = schedule.get('retry_interval_hours', 6)
                self.retry_interval_entry.delete(0, tk.END)
                self.retry_interval_entry.insert(0, str(interval))
            
            # 출력 설정
            if 'output' in config:
                output = config['output']
                output_dir = output.get('base_directory', 'crawl_results')
                self.output_dir_var.set(output_dir)
            
            # 상품 목록 로드
            self.refresh_products()
            
            self.log_message("설정 로드 완료")
            
        except Exception as e:
            self.log_message(f"설정 로드 오류: {str(e)}")

def main():
    """메인 실행 함수"""
    root = tk.Tk()
    app = CrawlerGUI(root)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("프로그램 종료")

if __name__ == "__main__":
    main()