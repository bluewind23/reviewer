document.addEventListener('DOMContentLoaded', function() {
    let currentJobId = null;
    let progressInterval = null;

    const alertModal = new bootstrap.Modal(document.getElementById('alertModal'));

    function showAlert(title, message) {
        document.getElementById('alertModalTitle').textContent = title;
        document.getElementById('alertModalBody').textContent = message;
        alertModal.show();
    }

    function resetStartButton() {
        const startBtn = document.getElementById('startCrawlBtn');
        startBtn.disabled = false;
        startBtn.innerHTML = '<i class="fas fa-play"></i> 크롤링 시작';
    }

    function startProgressTracking() {
        if (progressInterval) clearInterval(progressInterval);
        progressInterval = setInterval(() => {
            if (!currentJobId) return;
            fetch(`/api/job_status/${currentJobId}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateProgress(data.job);
                    if (['completed', 'failed'].includes(data.job.status)) {
                        clearInterval(progressInterval);
                        progressInterval = null;
                        resetStartButton();
                    }
                } else {
                    clearInterval(progressInterval);
                    progressInterval = null;
                    console.error('진행상태 확인 오류:', data.error);
                }
            })
            .catch(error => {
                console.error('진행상태 확인 중 네트워크 오류:', error);
                clearInterval(progressInterval);
                progressInterval = null;
            });
        }, 2000);
    }

    function updateProgress(job) {
        document.getElementById('progressBar').style.width = job.progress + '%';
        document.getElementById('progressMessage').textContent = job.message;
        const progressIcon = document.getElementById('progressIcon');
        const progressResult = document.getElementById('progressResult');
        progressIcon.className = `status-icon status-${job.status || 'starting'}`;
        let iconHtml = '';
        switch (job.status) {
            case 'starting': case 'extracting': case 'connecting_vpn':
                iconHtml = '<i class="fas fa-hourglass-start"></i>'; break;
            case 'crawling':
                iconHtml = '<i class="fas fa-spider"></i>'; break;
            case 'completed':
                iconHtml = '<i class="fas fa-check"></i>';
                if (job.result) {
                    progressResult.innerHTML = `<div class="alert alert-success"><strong>크롤링 완료!</strong><br>결과 파일: <code>${job.result}</code><br>사용된 크롤러: ${job.crawler}</div>`;
                    progressResult.style.display = 'block';
                }
                break;
            case 'failed':
                iconHtml = '<i class="fas fa-times"></i>';
                if (job.error) {
                    progressResult.innerHTML = `<div class="alert alert-danger"><strong>크롤링 실패!</strong><br>오류: ${job.error}</div>`;
                    progressResult.style.display = 'block';
                }
                break;
        }
        progressIcon.innerHTML = iconHtml;
    }

    function loadProducts() {
        const productsList = document.getElementById('productsList');
        productsList.innerHTML = `<div class="text-center py-4"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">로딩중...</span></div></div>`;
        fetch('/api/products')
            .then(response => response.json())
            .then(data => {
                if (data.success && data.products.length > 0) {
                    let html = '<div class="table-responsive"><table class="table table-hover align-middle">';
                    html += '<thead><tr><th>상품명</th><th>상품 ID</th><th>성공/실패</th><th>마지막 크롤링</th><th>작업</th></tr></thead><tbody>';
                    data.products.forEach(product => {
                        const lastCrawl = product.last_crawl ? new Date(product.last_crawl).toLocaleString() : '없음';
                        const stats = `${product.success_count || 0} / ${product.fail_count || 0}`;
                        html += `<tr>
                                    <td>${product.name}</td>
                                    <td><code>${product.id}</code></td>
                                    <td><span class="badge bg-light text-dark border">${stats}</span></td>
                                    <td>${lastCrawl}</td>
                                    <td><button class="btn btn-sm btn-outline-danger" onclick="window.removeProduct('${product.id}')"><i class="fas fa-trash"></i></button></td>
                                 </tr>`;
                    });
                    html += '</tbody></table></div>';
                    productsList.innerHTML = html;
                } else {
                    productsList.innerHTML = '<div class="text-center text-muted py-4">등록된 상품이 없습니다.</div>';
                }
            })
            .catch(error => {
                productsList.innerHTML = '<div class="text-center text-danger py-4">상품 목록을 불러오는 데 실패했습니다.</div>';
                console.error('상품 목록 로드 오류:', error);
            });
    }

    function loadVpnStatus() {
        const vpnStatus = document.getElementById('vpnStatus');
        fetch('/api/vpn_status')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const status = data.enabled ? `활성화됨 - 상태: ${data.status}` : '비활성화됨';
                    vpnStatus.innerHTML = `<i class="fas fa-info-circle"></i> ${status}`;
                } else {
                    vpnStatus.innerHTML = '<i class="fas fa-exclamation-triangle"></i> 상태 확인 실패';
                }
            })
            .catch(err => {
                vpnStatus.innerHTML = '<i class="fas fa-exclamation-triangle"></i> 상태 확인 실패 (네트워크 오류)';
            });
    }

    function loadSettings() {
        fetch('/api/settings')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const { vpn, schedule } = data.settings;
                    if (vpn) {
                        document.getElementById('vpnProvider').value = vpn.provider || 'expressvpn';
                        document.getElementById('vpnCountries').value = (vpn.countries || []).join(',');
                    }
                    if (schedule) {
                        document.getElementById('scheduleTime').value = (schedule.auto_run_times || []).join(',');
                        document.getElementById('retryInterval').value = schedule.retry_interval_hours || 6;
                    }
                }
            });
    }

    document.getElementById('extractBtn').addEventListener('click', () => {
        const url = document.getElementById('productUrl').value.trim();
        if (!url) return showAlert('오류', 'URL을 입력해주세요.');
        fetch('/api/extract_product_id', {
            method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({url})
        })
        .then(res => res.json()).then(data => showAlert(data.success ? '성공' : '오류', data.message || data.error))
        .catch(() => showAlert('네트워크 오류', '서버와 통신할 수 없습니다.'));
    });

    document.getElementById('crawlForm').addEventListener('submit', (e) => {
        e.preventDefault();
        const url = document.getElementById('productUrl').value.trim();
        if (!url) return showAlert('오류', 'URL을 입력해주세요.');
        
        const startBtn = document.getElementById('startCrawlBtn');
        startBtn.disabled = true;
        startBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 시작중...';

        const progressResult = document.getElementById('progressResult');
        progressResult.style.display = 'none';
        progressResult.innerHTML = '';
        document.getElementById('progressSection').style.display = 'block';

        const payload = {
            url: url,
            name: document.getElementById('productName').value.trim(),
            crawler: document.getElementById('crawlerType').value
        };
        fetch('/api/start_crawl', {
            method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)
        })
        .then(res => res.json()).then(data => {
            if (data.success) {
                currentJobId = data.job_id;
                startProgressTracking();
            } else {
                showAlert('오류', data.error);
                resetStartButton();
            }
        }).catch(() => {
            showAlert('네트워크 오류', '서버와 통신할 수 없습니다.');
            resetStartButton();
        });
    });

    document.getElementById('addProductForm').addEventListener('submit', (e) => {
        e.preventDefault();
        const payload = {
            url: document.getElementById('newProductUrl').value.trim(),
            name: document.getElementById('newProductName').value.trim()
        };
        fetch('/api/add_product', {
            method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)
        })
        .then(res => res.json()).then(data => {
            if (data.success) {
                showAlert('성공', data.message);
                document.getElementById('addProductForm').reset();
                loadProducts();
            } else {
                showAlert('오류', data.error);
            }
        });
    });

    window.removeProduct = (productId) => {
        if (!confirm('정말 이 상품을 제거하시겠습니까?')) return;
        fetch(`/api/remove_product/${productId}`, { method: 'DELETE' })
            .then(res => res.json()).then(data => {
                showAlert(data.success ? '성공' : '오류', data.message || data.error);
                if (data.success) loadProducts();
            });
    };
    
    // 초기 로드
    loadProducts();
    loadSettings();
    loadVpnStatus();
});