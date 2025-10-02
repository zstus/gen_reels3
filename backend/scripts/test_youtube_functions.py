#!/usr/bin/env python3
"""
YouTube 기능 테스트 스크립트
새로 추가된 YouTube URL 감지 및 비디오 ID 추출 기능을 테스트합니다.
"""

import re
from urllib.parse import urlparse

def extract_youtube_video_id(url: str) -> str:
    """YouTube URL에서 비디오 ID 추출"""
    youtube_patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
        r'youtube\.com.*[?&]v=([^&\n?#]+)',
    ]
    
    for pattern in youtube_patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def is_youtube_url(url: str) -> bool:
    """YouTube URL 여부 확인"""
    youtube_domains = ['youtube.com', 'youtu.be', 'www.youtube.com', 'm.youtube.com']
    try:
        parsed_url = urlparse(url)
        return parsed_url.netloc.lower() in youtube_domains
    except:
        return False

def test_youtube_functions():
    """YouTube 관련 함수들 테스트"""
    print("🧪 YouTube URL 감지 및 비디오 ID 추출 테스트")
    print("=" * 60)
    
    # 테스트 URL 목록
    test_urls = [
        # YouTube 정규 URL
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com/watch?v=dQw4w9WgXcQ&list=PLg",
        "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
        
        # YouTube 단축 URL
        "https://youtu.be/dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ?t=123",
        
        # YouTube 임베드 URL
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "https://youtube.com/embed/dQw4w9WgXcQ?autoplay=1",
        
        # 일반 웹사이트 URL (YouTube가 아님)
        "https://www.google.com",
        "https://www.naver.com",
        "https://example.com/watch?v=something",
        
        # 잘못된 URL
        "not-a-url",
        "",
    ]
    
    print("1️⃣  YouTube URL 감지 테스트:")
    print("-" * 30)
    for url in test_urls:
        is_yt = is_youtube_url(url)
        status = "✅ YouTube" if is_yt else "❌ 일반 URL"
        print(f"{status}: {url[:50]}{'...' if len(url) > 50 else ''}")
    
    print("\n2️⃣  비디오 ID 추출 테스트:")
    print("-" * 30)
    for url in test_urls:
        if is_youtube_url(url):
            video_id = extract_youtube_video_id(url)
            if video_id:
                print(f"✅ ID 추출 성공: {video_id} <- {url}")
            else:
                print(f"❌ ID 추출 실패: {url}")
    
    print("\n3️⃣  예상 결과 검증:")
    print("-" * 30)
    expected_video_id = "dQw4w9WgXcQ"
    youtube_urls = [url for url in test_urls if is_youtube_url(url)]
    
    success_count = 0
    total_count = len(youtube_urls)
    
    for url in youtube_urls:
        extracted_id = extract_youtube_video_id(url)
        if extracted_id == expected_video_id:
            success_count += 1
            print(f"✅ 정확한 ID 추출: {url}")
        else:
            print(f"❌ 잘못된 ID 추출: {extracted_id} (기대: {expected_video_id}) <- {url}")
    
    print(f"\n📊 테스트 결과: {success_count}/{total_count} 성공 ({success_count/total_count*100:.1f}%)")
    
    if success_count == total_count:
        print("🎉 모든 YouTube URL에서 정확한 비디오 ID를 추출했습니다!")
        return True
    else:
        print("⚠️  일부 URL에서 비디오 ID 추출에 실패했습니다.")
        return False

if __name__ == "__main__":
    success = test_youtube_functions()
    exit(0 if success else 1)