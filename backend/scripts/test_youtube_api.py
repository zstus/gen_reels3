#!/usr/bin/env python3
"""
YouTube API 기능 테스트 스크립트
YouTube 자막 추출 기능이 제대로 작동하는지 확인합니다.
"""

import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_youtube_imports():
    """YouTube 관련 import 테스트"""
    print("📦 YouTube 라이브러리 import 테스트")
    print("=" * 50)
    
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        print("✅ youtube-transcript-api import 성공")
        return True
    except ImportError as e:
        print(f"❌ youtube-transcript-api import 실패: {e}")
        print("💡 해결방법: pip install youtube-transcript-api==0.6.1")
        return False

def test_youtube_functions():
    """YouTube 기능 테스트"""
    print("\n🔧 YouTube 기능 테스트")
    print("=" * 50)
    
    # main.py의 함수들 import 시도
    try:
        from main import is_youtube_url, extract_youtube_video_id, get_youtube_transcript
        print("✅ YouTube 관련 함수 import 성공")
    except ImportError as e:
        print(f"❌ main.py 함수 import 실패: {e}")
        return False
    except Exception as e:
        print(f"❌ 함수 import 중 오류: {e}")
        return False
    
    # 테스트 YouTube URLs (자막이 있는 비디오들)
    test_urls = [
        "https://www.youtube.com/watch?v=jNQXAC9IVRw",  # Me at the zoo (첫 YouTube 비디오, 자막 있음)
        "https://youtu.be/jNQXAC9IVRw",                # 단축 URL
    ]
    
    print("\n1️⃣  YouTube URL 감지 테스트:")
    for url in test_urls:
        is_yt = is_youtube_url(url)
        print(f"   {'✅' if is_yt else '❌'} {url[:50]}...")
    
    print("\n2️⃣  비디오 ID 추출 테스트:")
    for url in test_urls:
        if is_youtube_url(url):
            video_id = extract_youtube_video_id(url)
            print(f"   ✅ ID: {video_id} <- {url[:50]}...")
    
    print("\n3️⃣  자막 추출 테스트:")
    test_video_ids = [
        ("jNQXAC9IVRw", "Me at the zoo (첫 YouTube 비디오)"),
        ("9bZkp7q19f0", "PSY - Gangnam Style (한국어 자막)"),
    ]
    
    success_count = 0
    for video_id, description in test_video_ids:
        try:
            transcript = get_youtube_transcript(video_id)
            print(f"   ✅ {description}: {len(transcript)} 문자")
            print(f"      📝 첫 100자: {transcript[:100]}...")
            success_count += 1
        except Exception as e:
            print(f"   ❌ {description} 실패: {e}")
    
    print(f"   📊 테스트 결과: {success_count}/{len(test_video_ids)} 성공")
    return success_count > 0

def test_api_request():
    """실제 API 요청 테스트"""
    print("\n🌐 API 요청 테스트")
    print("=" * 50)
    
    try:
        import requests
        
        # 테스트할 YouTube URL (자막이 있는 비디오)
        test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
        
        api_url = "http://localhost:8097/extract-reels-from-url"
        payload = {"url": test_url}
        
        print(f"📡 API 요청: {api_url}")
        print(f"📋 데이터: {payload}")
        
        response = requests.post(api_url, json=payload, timeout=30)
        
        print(f"📊 상태 코드: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ API 요청 성공!")
            print(f"📄 응답: {result.get('message', 'No message')}")
            return True
        else:
            print(f"❌ API 요청 실패: {response.status_code}")
            print(f"📄 에러: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해주세요.")
        return False
    except Exception as e:
        print(f"❌ API 테스트 실패: {e}")
        return False

def main():
    """메인 테스트 실행"""
    print("🧪 YouTube 기능 종합 테스트")
    print("=" * 60)
    
    # 1. Import 테스트
    imports_ok = test_youtube_imports()
    
    # 2. 함수 테스트
    functions_ok = test_youtube_functions()
    
    # 3. API 테스트 (선택사항)
    print("\n❓ API 요청 테스트를 실행하시겠습니까? (서버가 실행 중이어야 함)")
    print("   y/n (기본값: n): ", end="")
    try:
        choice = input().strip().lower()
        if choice == 'y':
            api_ok = test_api_request()
        else:
            api_ok = None
            print("⏭️  API 테스트 생략")
    except:
        api_ok = None
        print("⏭️  API 테스트 생략")
    
    # 결과 요약
    print("\n📊 테스트 결과 요약")
    print("=" * 50)
    print(f"📦 라이브러리 Import: {'✅ 성공' if imports_ok else '❌ 실패'}")
    print(f"🔧 YouTube 함수들: {'✅ 성공' if functions_ok else '❌ 실패'}")
    if api_ok is not None:
        print(f"🌐 API 요청: {'✅ 성공' if api_ok else '❌ 실패'}")
    
    if not imports_ok:
        print("\n💡 해결방법:")
        print("   1. pip install youtube-transcript-api==0.6.1")
        print("   2. 서버 재시작")
    
    return imports_ok and functions_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)