#!/usr/bin/env python3
"""
URL에서 릴스 대본 추출 기능 테스트 스크립트
"""

import requests
import json
import sys

def test_url_extract(url):
    """URL에서 릴스 대본 추출 테스트"""
    api_url = "http://localhost:8080/extract-reels-from-url"
    
    payload = {
        "url": url
    }
    
    print(f"🔍 테스트 URL: {url}")
    print(f"📡 API 호출: {api_url}")
    
    try:
        response = requests.post(api_url, json=payload, timeout=30)
        
        print(f"📊 응답 상태: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                print("✅ 성공!")
                print(f"💬 메시지: {data.get('message')}")
                
                reels_content = data.get("reels_content", {})
                print("\n📝 생성된 릴스 대본:")
                print(f"🎬 제목: {reels_content.get('title')}")
                
                for i in range(1, 9):
                    body_key = f"body{i}"
                    body_text = reels_content.get(body_key, "")
                    if body_text.strip():
                        print(f"   {i}. {body_text}")
                
                print(f"\n📄 전체 JSON:")
                print(json.dumps(reels_content, ensure_ascii=False, indent=2))
                
            else:
                print(f"❌ 실패: {data.get('message')}")
        else:
            print(f"❌ HTTP 오류: {response.status_code}")
            try:
                error_data = response.json()
                print(f"💥 오류 내용: {error_data.get('detail', 'Unknown error')}")
            except:
                print(f"💥 오류 내용: {response.text}")
                
    except requests.exceptions.Timeout:
        print("⏰ 요청 시간 초과 (30초)")
    except requests.exceptions.ConnectionError:
        print("🔌 서버 연결 실패 - 백엔드 서버가 실행 중인지 확인하세요")
    except Exception as e:
        print(f"💥 예외 발생: {e}")

def main():
    """메인 함수"""
    if len(sys.argv) != 2:
        print("사용법: python test_url_extract.py <URL>")
        print("예시: python test_url_extract.py https://example.com/article")
        sys.exit(1)
    
    test_url = sys.argv[1]
    test_url_extract(test_url)

if __name__ == "__main__":
    main()