import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_requirements():
    try:
        import PyInstaller
        print("✅ PyInstaller가 설치되어 있습니다.")
    except ImportError:
        print("❌ PyInstaller가 설치되지 않았습니다. 'pip install pyinstaller'로 설치해주세요.")
        return False
    
    required_files = ['desktop_gui.py', 'smart_scheduler.py', 'stealth_crawler.py', 'selenium_crawler.py', 'mobile_crawler.py', 'advanced_crawler.py', 'analysis.py']
    if all(os.path.exists(f) for f in required_files):
        print("✅ 모든 필요한 파일이 확인되었습니다.")
        return True
    else:
        print(f"❌ 필요한 파일이 없습니다: {[f for f in required_files if not os.path.exists(f)]}")
        return False

def create_build_script():
    icon_str = "'icon.ico' if os.path.exists('icon.ico') else None"
    
    build_script = f"""
# -*- mode: python ; coding: utf-8 -*-
import os
block_cipher = None
a = Analysis(
    ['desktop_gui.py'],
    pathex=[], binaries=[],
    datas=[('templates', 'templates'), ('crawler_config_example.json', '.')],
    hiddenimports=['smart_scheduler', 'stealth_crawler', 'selenium_crawler', 'mobile_crawler', 'advanced_crawler', 'analysis', 'konlpy', 'sklearn', 'pandas', 'requests', 'selenium', 'schedule'],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[],
    win_no_prefer_redirects=False, win_private_assemblies=False,
    cipher=block_cipher, noarchive=False
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
    name='NaverSmartCrawler',
    debug=False, bootloader_ignore_signals=False, strip=False, upx=True,
    runtime_tmpdir=None, console=False, disable_windowed_traceback=False,
    argv_emulation=False, target_arch=None, codesign_identity=None,
    entitlements_file=None, icon={icon_str}
)
"""
    with open('naver_crawler.spec', 'w', encoding='utf-8') as f:
        f.write(build_script)
    print("✅ 빌드 스크립트 (naver_crawler.spec) 생성 완료")

def build_exe():
    print("\n🚀 EXE 파일 빌드를 시작합니다...")
    try:
        for folder in ['build', 'dist']:
            if os.path.exists(folder):
                shutil.rmtree(folder)
                print(f"🧹 이전 {folder} 폴더 정리 완료")
        
        cmd = [sys.executable, '-m', 'PyInstaller', 'naver_crawler.spec', '--clean', '--noconfirm']
        print(f"⚙️  PyInstaller 실행 중... (명령어: {' '.join(cmd)})")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        print("✅ EXE 파일 빌드 성공!")
        exe_path = Path('dist/NaverSmartCrawler.exe')
        if exe_path.exists():
            print(f"📦 생성된 파일: {exe_path} (크기: {exe_path.stat().st_size / (1024*1024):.2f} MB)")
            copy_additional_files()
            print("\n🎉 빌드 완료! 'dist' 폴더에서 결과물을 확인하세요.")
        else:
            print("❌ EXE 파일이 생성되지 않았습니다.")
            
    except subprocess.CalledProcessError as e:
        print("❌ 빌드 실패!")
        print("--- STDOUT ---")
        print(e.stdout)
        print("--- STDERR ---")
        print(e.stderr)
    except Exception as e:
        print(f"❌ 빌드 중 오류 발생: {e}")

def copy_additional_files():
    try:
        dist_dir = Path('dist')
        readme_content = """
# 네이버 스마트 크롤러
1. NaverSmartCrawler.exe 파일을 실행하세요.
2. 결과는 crawl_results 폴더에 저장됩니다.
주의: JDK 8 이상이 설치되어 있어야 합니다.
"""
        with open(dist_dir / 'README.txt', 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        config_example = 'crawler_config_example.json'
        if os.path.exists(config_example):
            shutil.copy2(config_example, dist_dir / config_example)
            print("📄 예제 설정 파일 복사 완료")
        else:
            print(f"⚠️  '{config_example}' 파일이 없어 복사하지 못했습니다.")
            
    except Exception as e:
        print(f"⚠️ 추가 파일 복사 중 오류: {e}")

def main():
    print("🔨 네이버 스마트 크롤러 EXE 빌드 도구")
    if not check_requirements():
        return
    if input("\n계속 진행하시겠습니까? (y/n): ").lower() != 'y':
        print("빌드를 취소했습니다."); return
    
    create_build_script()
    build_exe()

if __name__ == "__main__":
    main()