#!/usr/bin/env python3
"""
네이버 블로그 스크래핑 독립 테스트 스크립트
"""

import requests
import time
from bs4 import BeautifulSoup
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def scrape_naver_blog(url: str) -> str:
    """네이버 블로그 전용 스크래핑 (재시도 로직 포함)"""
    max_retries = 3
    retry_delay = 2.0

    # 고급 헤더 설정 (실제 브라우저 모방)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0'
    }

    # 세션 생성 및 단계별 접근
    session = requests.Session()

    for attempt in range(max_retries):
        try:
            logger.info(f"네이버 블로그 스크래핑 시도 {attempt + 1}/{max_retries}: {url}")

            # 1단계: 네이버 메인 페이지 방문 (쿠키 설정)
            logger.info("1단계: 네이버 메인 페이지 방문")
            session.get('https://www.naver.com', headers=headers, timeout=10)

            # 2단계: 네이버 블로그 메인 방문
            logger.info("2단계: 네이버 블로그 메인 방문")
            session.get('https://blog.naver.com', headers=headers, timeout=10)
            time.sleep(1.0)  # 자연스러운 브라우징 패턴

            # 3단계: 실제 블로그 포스트 접근
            logger.info("3단계: 대상 블로그 포스트 접근")

            # Referer 헤더 추가 (네이버 블로그에서 온 것처럼)
            blog_headers = headers.copy()
            blog_headers['Referer'] = 'https://blog.naver.com'

            response = session.get(url, headers=blog_headers, timeout=15)
            response.raise_for_status()

            logger.info(f"✅ HTTP 요청 성공: {response.status_code}")
            logger.info(f"응답 크기: {len(response.content)} bytes")
            logger.info(f"Content-Type: {response.headers.get('Content-Type', 'N/A')}")

            # HTML 파싱
            soup = BeautifulSoup(response.text, 'html.parser')

            # 네이버 블로그 전용 콘텐츠 선택자들
            naver_selectors = [
                '.se-main-container',  # 스마트에디터 3.0
                '.se-component-content',  # 스마트에디터 컴포넌트
                '#postViewArea',  # 구버전 블로그
                '.post-view',     # 일반 블로그 뷰
                '.blog-content',  # 블로그 콘텐츠 영역
                '#content',       # 일반 콘텐츠
                '.contents_style'  # 네이버 블로그 콘텐츠 스타일
            ]

            content_text = ""

            # 네이버 블로그 전용 선택자로 콘텐츠 추출
            for selector in naver_selectors:
                elements = soup.select(selector)
                if elements:
                    logger.info(f"✅ 콘텐츠 선택자 매칭: {selector}")
                    for elem in elements:
                        # 스크립트, 스타일 태그 제거
                        for script in elem(["script", "style"]):
                            script.decompose()
                        content_text += elem.get_text(strip=True, separator='\n') + "\n"
                    break

            # 네이버 블로그 콘텐츠를 찾지 못한 경우 전체 텍스트 추출
            if not content_text.strip():
                logger.warning("❌ 네이버 블로그 전용 선택자로 콘텐츠를 찾을 수 없음")
                logger.info("전체 페이지에서 텍스트 추출 시도")

                # 불필요한 태그들 제거
                for unwanted in soup(["script", "style", "nav", "header", "footer", "aside"]):
                    unwanted.decompose()

                content_text = soup.get_text(strip=True, separator='\n')

            # 텍스트 정리
            lines = [line.strip() for line in content_text.split('\n') if line.strip()]
            clean_text = '\n'.join(lines)

            # Debug: Show what we actually extracted
            logger.info(f"Debug: Extracted content preview: '{clean_text[:200]}'")

            if len(clean_text) < 100:
                logger.warning(f"WARNING: Extracted text too short: {len(clean_text)} chars")
                logger.info(f"Full extracted content: '{clean_text}'")

                # Also check raw HTML for debugging
                logger.info(f"Raw HTML preview (first 1000 chars): {response.text[:1000]}")

                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 1.5  # Exponential backoff
                    continue

            logger.info(f"SUCCESS: Content extraction complete: {len(clean_text)} chars")

            # 너무 긴 텍스트는 앞부분만 사용 (GPT 토큰 제한 고려)
            max_chars = 8000
            if len(clean_text) > max_chars:
                clean_text = clean_text[:max_chars]
                logger.info(f"📝 텍스트 길이 제한: {max_chars}자로 잘라냄")

            return clean_text

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else 'unknown'
            logger.error(f"❌ HTTP 에러 (시도 {attempt + 1}): {status_code}")

            if status_code == 403:
                logger.warning("⚠️ 접근 금지 (403) - IP 차단 또는 봇 감지 가능성")
            elif status_code == 400:
                logger.warning("⚠️ 잘못된 요청 (400) - 헤더 또는 요청 형식 문제")

            if attempt < max_retries - 1:
                logger.info(f"재시도 대기: {retry_delay}초")
                time.sleep(retry_delay)
                retry_delay *= 1.5
            else:
                raise

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ 요청 에러 (시도 {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 1.5
            else:
                raise
        except Exception as e:
            logger.error(f"❌ 예상치 못한 에러 (시도 {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 1.5
            else:
                raise

def test_naver_blog_extraction():
    """네이버 블로그 추출 테스트"""

    test_url = "https://blog.naver.com/ilovekwater/221658073924"

    print("=" * 70)
    print("Naver Blog Scraping Test")
    print("=" * 70)
    print(f"Target URL: {test_url}")
    print()

    try:
        result = scrape_naver_blog(test_url)

        if result and len(result) > 100:
            print("SUCCESS: Scraping completed!")
            print(f"Extracted text length: {len(result)} characters")
            print()
            print("Content preview (first 500 chars):")
            print("-" * 50)
            preview = result[:500] if len(result) > 500 else result
            print(preview)
            if len(result) > 500:
                print("... (truncated)")
            print("-" * 50)

            return True
        else:
            print("FAILED: Content is empty or too short")
            return False

    except Exception as e:
        print(f"FAILED: Scraping error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_naver_blog_extraction()

    print("\n" + "=" * 50)
    print("Test Results")
    print("=" * 50)

    if success:
        print("SUCCESS: Naver blog 400 error has been resolved!")
        print("The enhanced scraping implementation is working:")
        print("   - Advanced browser header simulation")
        print("   - Session-based step-by-step access")
        print("   - Retry logic with exponential backoff")
        print("   - Naver blog-specific content selectors")
    else:
        print("FAILED: Still encountering issues.")
        print("Additional improvement suggestions:")
        print("   - Longer wait times")
        print("   - Different User-Agent attempts")
        print("   - Proxy server usage")
        print("   - Consider Selenium browser automation")