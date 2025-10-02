#!/usr/bin/env python3
"""
특정 YouTube 비디오 테스트 스크립트
사용자가 제공한 특정 비디오의 자막을 테스트합니다.
"""

import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_specific_video(video_id, description="사용자 제공 비디오"):
    """특정 비디오 ID로 자막 추출 테스트"""
    print(f"🎬 {description} 테스트")
    print(f"📺 비디오 ID: {video_id}")
    print("=" * 60)
    
    try:
        # 함수 import
        from main import get_youtube_transcript, is_youtube_url, extract_youtube_video_id
        
        print("1️⃣  자막 추출 시도...")
        transcript = get_youtube_transcript(video_id)
        
        print(f"✅ 자막 추출 성공!")
        print(f"📊 텍스트 길이: {len(transcript)} 문자")
        print(f"📝 첫 200자 미리보기:")
        print(f"   {transcript[:200]}...")
        
        if len(transcript) > 1000:
            print(f"📝 마지막 200자 미리보기:")
            print(f"   ...{transcript[-200:]}")
        
        return True
        
    except Exception as e:
        print(f"❌ 자막 추출 실패: {e}")
        return False

def test_url_parsing():
    """URL 파싱 기능 테스트"""
    print("\n🔗 URL 파싱 테스트")
    print("=" * 30)
    
    test_urls = [
        "https://youtu.be/HQaUhKzJF58?si=TK2Unu-h2g_luo3v",
        "https://www.youtube.com/watch?v=HQaUhKzJF58",
    ]
    
    try:
        from main import is_youtube_url, extract_youtube_video_id
        
        for url in test_urls:
            print(f"📎 URL: {url}")
            is_yt = is_youtube_url(url)
            print(f"   YouTube URL 인식: {'✅' if is_yt else '❌'}")
            
            if is_yt:
                video_id = extract_youtube_video_id(url)
                print(f"   추출된 비디오 ID: {video_id}")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ URL 파싱 테스트 실패: {e}")
        return False

def test_api_request():
    """실제 API 요청 테스트"""
    print("\n🌐 API 요청 테스트")
    print("=" * 30)
    
    try:
        import requests
        
        test_url = "https://youtu.be/HQaUhKzJF58?si=TK2Unu-h2g_luo3v"
        
        api_url = "http://localhost:8097/extract-reels-from-url"
        payload = {"url": test_url}
        
        print(f"📡 API 요청: {api_url}")
        print(f"📋 데이터: {payload}")
        
        response = requests.post(api_url, json=payload, timeout=60)
        
        print(f"📊 상태 코드: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ API 요청 성공!")
            print(f"📄 메시지: {result.get('message', 'No message')}")
            
            # reels_content가 있으면 일부 출력
            if 'reels_content' in result:
                content = result['reels_content']
                print(f"🎯 제목: {content.get('title', 'No title')}")
                print(f"📝 본문 개수: {len([k for k in content.keys() if k.startswith('body')])}")
            
            return True
        else:
            print(f"❌ API 요청 실패: {response.status_code}")
            try:
                error_detail = response.json()
                print(f"📄 에러 내용: {error_detail}")
            except:
                print(f"📄 에러 텍스트: {response.text[:500]}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해주세요.")
        return False
    except Exception as e:
        print(f"❌ API 테스트 실패: {e}")
        return False

def main():
    """메인 테스트 실행"""
    print("🧪 특정 YouTube 비디오 테스트")
    print("🎬 비디오: https://youtu.be/HQaUhKzJF58?si=TK2Unu-h2g_luo3v")
    print("=" * 70)
    
    # 1. URL 파싱 테스트
    parsing_ok = test_url_parsing()
    
    # 2. 직접 자막 추출 테스트
    transcript_ok = test_specific_video("HQaUhKzJF58", "사용자 제공 비디오")
    
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
    print(f"🔗 URL 파싱: {'✅ 성공' if parsing_ok else '❌ 실패'}")
    print(f"📺 자막 추출: {'✅ 성공' if transcript_ok else '❌ 실패'}")
    if api_ok is not None:
        print(f"🌐 API 요청: {'✅ 성공' if api_ok else '❌ 실패'}")
    
    if transcript_ok:
        print("\n🎉 해당 YouTube 비디오의 자막 추출이 성공했습니다!")
        print("💡 이제 릴스 대본 생성을 위해 API를 사용해보세요.")
    else:
        print("\n🔧 자막 추출에 문제가 있습니다.")
        print("💡 서버 로그를 확인하여 구체적인 원인을 파악해보세요.")
    
    return parsing_ok and transcript_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)