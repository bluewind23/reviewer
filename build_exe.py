"""
EXE 파일 빌드 스크립트
PyInstaller를 사용하여 데스크톱 GUI를 독립실행 파일로 변환
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_requirements():
    """필요한 패키지 확인"""
    try:
        import PyInstaller
        print("✅ PyInstaller가 설치되어 있습니다.")
    except ImportError:
        print("❌ PyInstaller가 설치되지 않았습니다.")
        print("설치 명령: pip install pyinstaller")
        return False
    
    # 필요한 파일들 확인
    required_files = [
        'desktop_gui.py',
        'smart_scheduler.py',
        'stealth_crawler.py',
        'selenium_crawler.py',
        'mobile_crawler.py',
        'advanced_crawler.py'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ 필요한 파일들이 없습니다: {', '.join(missing_files)}")
        return False
    
    print("✅ 모든 필요한 파일이 확인되었습니다.")
    return True

def create_build_script():
    """빌드 스크립트 생성"""
    build_script = """
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['desktop_gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('crawler_config_example.json', '.'),
    ],
    hiddenimports=[
        'smart_scheduler',
        'stealth_crawler', 
        'selenium_crawler',
        'mobile_crawler',
        'advanced_crawler',
        'konlpy',
        'sklearn',
        'pandas',
        'requests',
        'selenium',
        'schedule'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='NaverSmartCrawler',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if os.path.exists('icon.ico') else None,
)
"""
    
    with open('naver_crawler.spec', 'w', encoding='utf-8') as f:
        f.write(build_script)
    
    print("✅ 빌드 스크립트 (naver_crawler.spec) 생성 완료")

def download_icon():
    """아이콘 파일 생성 (간단한 텍스트 기반)"""
    # 실제 프로젝트에서는 proper ICO 파일을 사용하세요
    print("💡 아이콘 파일이 필요하면 icon.ico 파일을 현재 폴더에 추가하세요")

def build_exe():
    """EXE 파일 빌드"""
    print("\n🚀 EXE 파일 빌드를 시작합니다...")
    
    try:
        # 이전 빌드 정리
        if os.path.exists('build'):
            shutil.rmtree('build')
            print("🧹 이전 빌드 폴더 정리 완료")
        
        if os.path.exists('dist'):
            shutil.rmtree('dist')
            print("🧹 이전 배포 폴더 정리 완료")
        
        # PyInstaller 실행
        cmd = [
            sys.executable, '-m', 'PyInstaller',
            'naver_crawler.spec',
            '--clean',
            '--noconfirm'
        ]
        
        print("⚙️ PyInstaller 실행 중...")
        print(f"명령어: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ EXE 파일 빌드 성공!")
            
            # 결과 확인
            exe_path = Path('dist/NaverSmartCrawler.exe')
            if exe_path.exists():
                size_mb = exe_path.stat().st_size / (1024 * 1024)
                print(f"📦 생성된 파일: {exe_path}")
                print(f"📏 파일 크기: {size_mb:.2f} MB")
                
                # 추가 파일들 복사
                copy_additional_files()
                
                print("\n🎉 빌드 완료!")
                print("📁 dist 폴더에서 NaverSmartCrawler.exe 파일을 확인하세요")
            else:
                print("❌ EXE 파일이 생성되지 않았습니다")
        else:
            print("❌ 빌드 실패!")
            print("오류 출력:")
            print(result.stderr)
            
    except Exception as e:
        print(f"❌ 빌드 중 오류 발생: {e}")

def copy_additional_files():
    """추가 파일들 복사"""
    try:
        dist_dir = Path('dist')
        
        # README 파일 생성
        readme_content = """
# 네이버 스마트 크롤러

## 사용법
1. NaverSmartCrawler.exe 파일을 실행하세요
2. 상품 URL을 입력하고 크롤링을 시작하세요
3. 결과는 crawl_results 폴더에 저장됩니다

## 기능
- 즉시 크롤링: URL 입력 후 바로 크롤링
- 상품 관리: 여러 상품을 등록하고 관리
- VPN 연동: ExpressVPN, NordVPN, SurfShark 지원
- 자동 스케줄링: 정해진 시간에 자동 실행

## 주의사항
- 크롤링 전에 VPN을 설정하는 것을 권장합니다
- 과도한 크롤링은 IP 차단의 원인이 될 수 있습니다
- 새벽 시간대(2-6시)에 실행하는 것을 권장합니다

## 문제 해결
- Chrome 브라우저가 설치되어 있어야 Selenium 크롤러가 작동합니다
- Windows Defender에서 차단될 수 있으니 예외로 추가해주세요
- 방화벽에서 차단될 수 있으니 허용해주세요
"""
        
        with open(dist_dir / 'README.txt', 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        print("📝 README.txt 파일 생성 완료")
        
        # 예제 설정 파일 복사
        if os.path.exists('crawler_config_example.json'):
            shutil.copy2('crawler_config_example.json', dist_dir / 'crawler_config_example.json')
            print("📄 예제 설정 파일 복사 완료")
        
    except Exception as e:
        print(f"⚠️ 추가 파일 복사 중 오류: {e}")

def create_batch_files():
    """배치 파일 생성"""
    try:
        dist_dir = Path('dist')
        
        # 웹 GUI 실행 배치 파일
        web_batch = """@echo off
echo 웹 GUI를 시작합니다...
echo 브라우저에서 http://localhost:5000 으로 접속하세요
echo 종료하려면 Ctrl+C를 누르세요
python web_gui.py
pause
"""
        with open(dist_dir / 'start_web_gui.bat', 'w', encoding='utf-8') as f:
            f.write(web_batch)
        
        # 빠른 시작 배치 파일
        quick_batch = """@echo off
echo 빠른 크롤링을 시작합니다...
python quick_start.py
pause
"""
        with open(dist_dir / 'quick_start.bat', 'w', encoding='utf-8') as f:
            f.write(quick_batch)
        
        print("📝 배치 파일 생성 완료")
        
    except Exception as e:
        print(f"⚠️ 배치 파일 생성 중 오류: {e}")

def main():
    """메인 실행"""
    print("🔨 네이버 스마트 크롤러 EXE 빌드 도구")
    print("=" * 50)
    
    # 요구사항 확인
    if not check_requirements():
        print("\n❌ 빌드 요구사항이 충족되지 않았습니다.")
        return
    
    print("\n📋 빌드 과정:")
    print("1. 빌드 스크립트 생성")
    print("2. 아이콘 확인")
    print("3. PyInstaller 실행")
    print("4. 추가 파일 복사")
    print("5. 배치 파일 생성")
    
    response = input("\n계속 진행하시겠습니까? (y/n): ").lower()
    if response != 'y':
        print("빌드를 취소했습니다.")
        return
    
    # 빌드 과정 실행
    create_build_script()
    download_icon()
    build_exe()
    create_batch_files()
    
    print("\n" + "=" * 50)
    print("🎯 빌드 완료 요약:")
    print("📁 dist/NaverSmartCrawler.exe - 메인 실행 파일")
    print("📁 dist/README.txt - 사용 가이드")
    print("📁 dist/start_web_gui.bat - 웹 GUI 실행")
    print("📁 dist/quick_start.bat - 빠른 시작")
    print("\n💡 dist 폴더를 다른 컴퓨터로 복사하여 사용할 수 있습니다!")

if __name__ == "__main__":
    main()