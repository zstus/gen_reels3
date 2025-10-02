#!/usr/bin/env python3
"""
네이버 블로그 스크래핑 테스트 스크립트
"""

import sys
import os

# 현재 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 환경변수 로드
from dotenv import load_dotenv
load_dotenv()

from main import scrape_website_content, scrape_naver_blog
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_naver_blog_scraping():
    """네이버 블로그 스크래핑 테스트"""

    test_urls = [
        "https://blog.naver.com/ilovekwater/221658073924",  # 사용자 제공 URL
        "https://blog.naver.com/sample/123456789",          # 테스트 URL (존재하지 않을 수 있음)
    ]

    print("=" * 70)
    print("🧪 네이버 블로그 스크래핑 테스트")
    print("=" * 70)

    for i, url in enumerate(test_urls, 1):
        print(f"\n{i}. 테스트 URL: {url}")
        print("-" * 50)

        try:
            # 네이버 블로그 스크래핑 시도
            result = scrape_website_content(url)

            if result:
                print(f"✅ 스크래핑 성공!")
                print(f"📝 추출된 텍스트 길이: {len(result)}자")

                # 처음 500자만 출력
                preview = result[:500] if len(result) > 500 else result
                print(f"📄 내용 미리보기:")
                print(f"```")
                print(preview)
                if len(result) > 500:
                    print("... (생략)")
                print(f"```")

                # 릴스 생성 테스트 (OpenAI API 키가 있는 경우만)
                openai_key = os.getenv("OPENAI_API_KEY")
                if openai_key and len(openai_key) > 10:
                    try:
                        print(f"\n🤖 ChatGPT로 릴스 생성 테스트...")
                        from main import generate_reels_with_chatgpt
                        import asyncio

                        reels_content = asyncio.run(generate_reels_with_chatgpt(result))

                        if reels_content:
                            print(f"🎬 릴스 생성 성공!")
                            print(f"제목: {reels_content.title}")

                            body_keys = [k for k in reels_content.model_dump().keys() if k.startswith('body') and getattr(reels_content, k)]
                            print(f"본문: {len(body_keys)}개 장면")

                            for key in body_keys[:3]:  # 처음 3개만 출력
                                print(f"  - {getattr(reels_content, key)}")

                            if len(body_keys) > 3:
                                print(f"  ... 외 {len(body_keys)-3}개")

                    except Exception as reels_error:
                        print(f"⚠️ 릴스 생성 실패: {reels_error}")

                else:
                    print(f"\n⏭️ OpenAI API 키 없음, 릴스 생성 테스트 건너뜀")

            else:
                print(f"❌ 스크래핑 실패: 빈 결과")

        except Exception as e:
            print(f"❌ 스크래핑 실패: {str(e)}")

        print(f"\n" + "="*50)

def test_specific_naver_blog():
    """특정 네이버 블로그 테스트 (사용자 제공 URL)"""

    specific_url = "https://blog.naver.com/ilovekwater/221658073924"

    print("\n" + "=" * 70)
    print("🎯 특정 네이버 블로그 집중 테스트")
    print("=" * 70)
    print(f"URL: {specific_url}")

    try:
        # 직접 네이버 블로그 함수 호출
        print(f"\n1️⃣ 네이버 블로그 전용 함수 테스트...")
        result = scrape_naver_blog(specific_url)

        print(f"✅ 네이버 전용 함수 성공!")
        print(f"📝 텍스트 길이: {len(result)}자")
        print(f"📄 처음 300자:")
        print(result[:300] + "..." if len(result) > 300 else result)

        return True

    except Exception as e:
        print(f"❌ 네이버 전용 함수 실패: {str(e)}")

        # 일반 함수로도 시도
        try:
            print(f"\n2️⃣ 일반 스크래핑 함수 테스트...")
            from main import scrape_general_website
            result = scrape_general_website(specific_url)

            print(f"✅ 일반 함수 성공!")
            print(f"📝 텍스트 길이: {len(result)}자")
            return True

        except Exception as e2:
            print(f"❌ 일반 함수도 실패: {str(e2)}")
            return False

def analyze_request_headers():
    """요청 헤더 분석"""
    print("\n" + "=" * 50)
    print("🔍 요청 헤더 분석")
    print("=" * 50)

    import requests

    url = "https://blog.naver.com/ilovekwater/221658073924"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

    try:
        print(f"🌐 직접 HTTP 요청 테스트...")
        response = requests.get(url, headers=headers, timeout=10)
        print(f"상태 코드: {response.status_code}")
        print(f"응답 길이: {len(response.content)} bytes")
        print(f"Content-Type: {response.headers.get('Content-Type', 'N/A')}")

        if response.status_code == 200:
            print(f"✅ 기본 HTTP 요청 성공")
        else:
            print(f"❌ HTTP 요청 실패: {response.status_code}")
            print(f"응답 내용 미리보기:")
            print(response.text[:500])

    except Exception as e:
        print(f"❌ HTTP 요청 오류: {e}")

if __name__ == "__main__":
    print("🧪 네이버 블로그 스크래핑 종합 테스트")

    # 1. 기본 요청 헤더 분석
    analyze_request_headers()

    # 2. 특정 URL 집중 테스트
    specific_success = test_specific_naver_blog()

    # 3. 전체 테스트
    test_naver_blog_scraping()

    # 결과 요약
    print("\n" + "=" * 70)
    print("📋 테스트 결과 요약")
    print("=" * 70)

    if specific_success:
        print("✅ 네이버 블로그 스크래핑 구현이 개선되어 400 에러가 해결되었습니다!")
        print("🎉 이제 네이버 블로그 URL로 릴스를 생성할 수 있습니다.")
    else:
        print("❌ 네이버 블로그 스크래핑에 여전히 문제가 있습니다.")
        print("💡 추가 개선이 필요할 수 있습니다:")
        print("   - Selenium 브라우저 자동화 사용")
        print("   - 다른 User-Agent 시도")
        print("   - 프록시 서버 사용")

    print(f"\n🔗 테스트 URL: https://blog.naver.com/ilovekwater/221658073924")