"""
콘텐츠 추출 라우터
URL에서 릴스 대본 추출 API (YouTube, 웹사이트 스크래핑)
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from utils.logger_config import get_logger
from models.request_models import URLExtractRequest, ReelsContent
from urllib.parse import urlparse
from typing import List
import requests
from bs4 import BeautifulSoup
import re
import os
import json

router = APIRouter(tags=["content"])
logger = get_logger('content_router')

# 전역 변수 (main.py에서 설정)
OPENAI_AVAILABLE = False
YOUTUBE_TRANSCRIPT_AVAILABLE = False
YouTubeTranscriptApi = None


def set_dependencies(openai_avail, youtube_avail, youtube_api):
    """main.py에서 호출하여 의존성 설정"""
    global OPENAI_AVAILABLE, YOUTUBE_TRANSCRIPT_AVAILABLE, YouTubeTranscriptApi
    OPENAI_AVAILABLE = openai_avail
    YOUTUBE_TRANSCRIPT_AVAILABLE = youtube_avail
    YouTubeTranscriptApi = youtube_api


def extract_youtube_video_id(url: str) -> str:
    """YouTube URL에서 비디오 ID 추출"""
    # YouTube URL 패턴들
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


def get_youtube_transcript(video_id: str) -> str:
    """YouTube 비디오의 스크립트(자막) 가져오기"""

    # 라이브러리 가용성 확인
    if not YOUTUBE_TRANSCRIPT_AVAILABLE:
        raise ValueError("YouTube transcript API가 설치되지 않았습니다. 서버에 youtube-transcript-api 라이브러리를 설치해주세요.")

    try:
        # 한국어 자막을 우선적으로 시도, 없으면 영어, 그 다음 자동생성 자막
        languages = ['ko', 'en', 'ko-KR', 'en-US']

        for lang in languages:
            try:
                logger.info(f"YouTube 스크립트 시도 언어: {lang}")
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang])

                # 스크립트를 하나의 텍스트로 합치기
                full_text = ' '.join([item['text'] for item in transcript_list])
                logger.info(f"YouTube 스크립트 추출 성공 ({lang}): {len(full_text)}자")
                return full_text

            except Exception as e:
                logger.warning(f"언어 {lang} 스크립트 추출 실패: {e}")
                continue

        # 모든 언어 시도 실패 시, 사용 가능한 자막 언어 확인
        try:
            logger.info("사용 가능한 자막 언어 확인 중...")
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            available_languages = []

            for transcript in transcript_list:
                available_languages.append(f"{transcript.language} ({transcript.language_code})")

            if available_languages:
                logger.info(f"사용 가능한 자막 언어: {', '.join(available_languages)}")

                # 사용 가능한 자막으로 다양한 방법 시도
                for transcript in transcript_list:
                    # 방법 1: 기본 fetch 시도
                    try:
                        logger.info(f"언어 {transcript.language_code} ({transcript.language})로 자막 추출 시도...")
                        transcript_data = transcript.fetch()

                        # 자막 데이터가 실제로 있는지 확인
                        if not transcript_data:
                            logger.warning(f"언어 {transcript.language} 자막이 비어있음")
                            continue

                        full_text = ' '.join([item['text'] for item in transcript_data if item.get('text', '').strip()])

                        # 실제 텍스트 내용이 있는지 확인
                        if not full_text.strip():
                            logger.warning(f"언어 {transcript.language} 자막에 텍스트 내용이 없음")
                            continue

                        logger.info(f"YouTube 스크립트 추출 성공 ({transcript.language}): {len(full_text)}자")
                        return full_text

                    except Exception as transcript_error:
                        error_msg = str(transcript_error)
                        if "no element found" in error_msg.lower():
                            logger.info(f"언어 {transcript.language} 첫 번째 시도 실패 (XML 파싱 에러), 재시도...")

                            # 방법 2: 잠시 대기 후 재시도
                            try:
                                import time
                                time.sleep(1)  # 1초 대기
                                logger.info(f"언어 {transcript.language_code} 재시도 중...")
                                transcript_data = transcript.fetch()

                                if transcript_data:
                                    full_text = ' '.join([item['text'] for item in transcript_data if item.get('text', '').strip()])
                                    if full_text.strip():
                                        logger.info(f"YouTube 스크립트 재시도 성공 ({transcript.language}): {len(full_text)}자")
                                        return full_text

                                logger.warning(f"언어 {transcript.language} 재시도도 비어있음")

                            except Exception as retry_error:
                                logger.warning(f"언어 {transcript.language} 재시도 실패: {retry_error}")
                        else:
                            logger.warning(f"언어 {transcript.language} 자막 추출 실패: {transcript_error}")
                        continue

                # 자막이 있다고 표시되지만 모두 비어있는 경우
                logger.error(f"모든 자막이 비어있거나 접근 불가: {', '.join(available_languages)}")
                raise ValueError("이 YouTube 비디오는 자막이 표시되지만 실제로는 내용이 없습니다. 다른 비디오를 시도해주세요.")
            else:
                raise ValueError("이 YouTube 비디오에는 자막이 없습니다.")

        except Exception as e:
            logger.error(f"자막 확인 실패: {e}")

            # 더 구체적인 에러 메시지 제공
            if "TranscriptsDisabled" in str(e):
                raise ValueError("이 YouTube 비디오는 자막이 비활성화되어 있습니다.")
            elif "VideoUnavailable" in str(e):
                raise ValueError("YouTube 비디오를 찾을 수 없습니다. URL을 확인해주세요.")
            elif "TooManyRequests" in str(e):
                raise ValueError("YouTube API 요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요.")
            elif "No transcripts were found" in str(e):
                raise ValueError("이 YouTube 비디오에는 자막이 없습니다. 자막이 있는 다른 비디오를 시도해주세요.")
            else:
                raise ValueError(f"YouTube 비디오의 자막을 가져올 수 없습니다: {str(e)}")

    except Exception as e:
        logger.error(f"YouTube 스크립트 추출 실패: {e}")
        raise ValueError(f"YouTube 스크립트 추출에 실패했습니다: {str(e)}")


def scrape_website_content(url: str) -> str:
    """웹사이트에서 텍스트 내용을 스크래핑"""
    try:
        logger.info(f"웹페이지 스크래핑 시작: {url}")

        # 네이버 블로그인지 확인
        if 'blog.naver.com' in url:
            return scrape_naver_blog(url)
        else:
            return scrape_general_website(url)

    except Exception as e:
        logger.error(f"스크래핑 오류: {e}")
        raise ValueError(f"웹페이지 내용을 추출할 수 없습니다: {str(e)}")


def scrape_naver_blog(url: str) -> str:
    """네이버 블로그 전용 스크래핑 (재시도 로직 포함)"""
    import time

    max_retries = 3
    retry_delay = 2.0  # 2초 간격

    for attempt in range(max_retries):
        try:
            logger.info(f"네이버 블로그 스크래핑 시도 {attempt + 1}/{max_retries}: {url}")

            # 세션 생성 및 초기화
            session = requests.Session()

            # 네이버 블로그 전용 헤더 (더 상세하게)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': 'https://www.naver.com/',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'cross-site',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
                'DNT': '1'
            }

            # 먼저 네이버 메인 페이지 방문 (쿠키 및 세션 설정)
            try:
                time.sleep(0.5)  # 짧은 딜레이
                session.get('https://www.naver.com/', headers=headers, timeout=8)
                logger.info("네이버 메인 페이지 방문 완료")

                # 블로그 메인 페이지도 방문
                time.sleep(0.5)
                headers['Referer'] = 'https://www.naver.com/'
                session.get('https://blog.naver.com/', headers=headers, timeout=8)
                logger.info("네이버 블로그 메인 페이지 방문 완료")
            except Exception as e:
                logger.warning(f"네이버 선행 방문 실패: {e}")

            # 실제 블로그 포스트 요청
            time.sleep(1.0)  # 요청 전 1초 대기
            headers['Referer'] = 'https://blog.naver.com/'
            response = session.get(url, headers=headers, timeout=20)

            # 상태 코드 체크
            if response.status_code == 403:
                logger.warning(f"접근 차단 (403) - 시도 {attempt + 1}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))  # 점진적 증가
                    continue
                else:
                    raise requests.exceptions.RequestException(f"네이버 블로그 접근이 차단되었습니다 (403)")

            elif response.status_code == 400:
                logger.warning(f"잘못된 요청 (400) - 시도 {attempt + 1}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    raise requests.exceptions.RequestException(f"잘못된 요청입니다. URL을 확인해주세요 (400)")

            response.raise_for_status()
            logger.info(f"네이버 블로그 요청 성공: {response.status_code}")
            break  # 성공시 루프 종료

        except requests.exceptions.Timeout as e:
            logger.warning(f"네이버 블로그 타임아웃 - 시도 {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            else:
                raise ValueError(f"네이버 블로그 응답 시간이 초과되었습니다. 잠시 후 다시 시도해주세요.")

        except requests.exceptions.RequestException as e:
            logger.warning(f"네이버 블로그 요청 실패 - 시도 {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
                continue
            else:
                raise ValueError(f"네이버 블로그에 접근할 수 없습니다: {str(e)}")

    # 여기까지 오면 response가 성공적으로 받아진 상태
    try:
        # BeautifulSoup으로 HTML 파싱
        soup = BeautifulSoup(response.content, 'html.parser')

        # 불필요한 태그 제거
        for script in soup(["script", "style", "nav", "header", "footer", "aside", "form", "button", "iframe"]):
            script.decompose()

        # 네이버 블로그 전용 콘텐츠 셀렉터
        naver_selectors = [
            '.se-main-container',           # 스마트에디터 3.0 메인 컨테이너
            '.post-view',                   # 구 에디터 포스트 뷰
            '#postViewArea',                # 포스트 뷰 영역
            '.se-component-content',        # 스마트에디터 콘텐츠
            '.post_ct',                     # 포스트 내용
            '.se-text-paragraph',           # 스마트에디터 텍스트 단락
            '.blog-post-content',           # 블로그 포스트 콘텐츠
            '.post_body',                   # 포스트 본문
            '.se-section-text',             # 스마트에디터 텍스트 섹션
        ]

        text_content = ""

        # 네이버 블로그 전용 셀렉터로 텍스트 추출
        for selector in naver_selectors:
            elements = soup.select(selector)
            if elements:
                logger.info(f"네이버 블로그 콘텐츠 발견: {selector}")
                for element in elements:
                    text = element.get_text(strip=True, separator=' ')
                    if text and len(text) > 50:  # 의미있는 텍스트만
                        text_content += text + " "
                if text_content:
                    break

        # 네이버 전용 셀렉터로 찾지 못한 경우 일반적인 방법 시도
        if not text_content:
            logger.warning("네이버 전용 셀렉터로 콘텐츠를 찾지 못함, 일반 방법 시도")
            body = soup.find('body')
            if body:
                text_content = body.get_text(strip=True, separator=' ')

        return process_extracted_text(text_content, url)

    except Exception as e:
        logger.error(f"네이버 블로그 파싱 오류: {e}")
        raise ValueError(f"네이버 블로그 내용을 분석할 수 없습니다: {str(e)}")


def scrape_general_website(url: str) -> str:
    """일반 웹사이트 스크래핑"""
    try:
        # 일반 웹사이트용 헤더 (기존 방식 개선)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # BeautifulSoup으로 HTML 파싱
        soup = BeautifulSoup(response.content, 'html.parser')

        # 불필요한 태그 제거
        for script in soup(["script", "style", "nav", "header", "footer", "aside", "form", "button"]):
            script.decompose()

        # 텍스트 추출 - 주요 콘텐츠 영역 우선
        content_selectors = [
            'article', 'main', '.content', '.article', '.post',
            '.entry-content', '.post-content', '.article-content',
            'div[role="main"]', '.main-content'
        ]

        text_content = ""

        # 주요 콘텐츠 영역에서 텍스트 추출 시도
        for selector in content_selectors:
            elements = soup.select(selector)
            if elements:
                for element in elements:
                    text_content += element.get_text(strip=True, separator=' ')
                break

        # 주요 영역을 찾지 못한 경우 body에서 추출
        if not text_content:
            body = soup.find('body')
            if body:
                text_content = body.get_text(strip=True, separator=' ')

        return process_extracted_text(text_content, url)

    except requests.exceptions.RequestException as e:
        logger.error(f"웹페이지 요청 실패: {e}")
        raise ValueError(f"웹페이지에 접근할 수 없습니다: {str(e)}")


def process_extracted_text(text_content: str, url: str) -> str:
    """추출된 텍스트 공통 처리"""
    try:
        # 텍스트 정제
        text_content = re.sub(r'\s+', ' ', text_content).strip()

        # 빈 내용 체크
        if not text_content:
            raise ValueError("추출된 텍스트가 비어있습니다.")

        # 너무 짧은 경우 에러
        if len(text_content) < 100:
            logger.warning(f"짧은 텍스트 추출: {len(text_content)}자")
            raise ValueError("추출된 텍스트가 너무 짧습니다. 다른 URL을 시도해보세요.")

        # 너무 긴 경우 앞부분만 사용 (ChatGPT 토큰 제한 고려)
        original_length = len(text_content)
        if original_length > 8000:
            text_content = text_content[:8000] + "..."
            logger.info(f"텍스트 길이 조정: {original_length}자 → 8000자")

        logger.info(f"텍스트 추출 완료: {len(text_content)}자")
        return text_content

    except Exception as e:
        logger.error(f"텍스트 처리 오류: {e}")
        raise


async def generate_reels_with_chatgpt(
    content: str,
    is_youtube: bool = False,
    *,
    preserve_target: float = 0.60,        # 원문 보존 목표치(정성적 지시)
    preserve_threshold: float = 0.22,     # 보존율 수치 임계치(이보다 낮으면 강화 재작성 시도)
    max_critic_loops: int = 2,            # 비평/수정 자동 루프 횟수
    line_len_min: int = 20,               # body 각 줄 최소 길이
    line_len_max: int = 42,               # body 각 줄 최대 길이
    title_len_max: int = 15               # 제목 최대 길이
) -> ReelsContent:
    """
    원문충실 + 위트 + 강렬한 3초 후킹을 위한 다단계 생성기 (최신 모델 선호, 이전 호출 100% 호환)

    - 기존 호출 방식 유지: generate_reels_with_chatgpt(content, is_youtube=False)
    - pip 추가 설치 불필요(표준 re 사용)
    - 네트워크 프록시 환경 안전장치 포함(기존 모듈 호환)
    - 'OpenAI' import 오류 방지 및 친절한 예외 메시지
    - 최신 모델 우선 시도 후 자동 폴백(가용 모델에 따라 순차 시도)
    - 본문 길이 상/하한 모두 보정(짧은 문장 자연 확장)
    """
    # --- 안전한 OpenAI import (pip 추가 설치 없이, 미탑재 시 친절 메시지) ---
    try:
        from openai import OpenAI  # 최신 파이썬 SDK (Responses/Chat Completions 모두 지원)
    except Exception:
        OpenAI = None

    # FastAPI 사용 환경이 아닐 수도 있으므로, HTTPException은 옵션 취급
    try:
        from fastapi import HTTPException as _HTTPException  # noqa
        _has_http_exc = True
    except Exception:
        _has_http_exc = False

    # --- 환경/키 확인 (이전 모듈과 동일 동작) ---
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_APIKEY") or os.getenv("OPENAI_KEY")
    if not OPENAI_API_KEY:
        raise ValueError("OpenAI API 키가 설정되지 않았습니다.")

    if OpenAI is None:
        # FastAPI 환경이면 HTTPException으로도 대응 가능하지만, ValueError 통일로 단순화
        if _has_http_exc:
            raise _HTTPException(status_code=500, detail="OpenAI 라이브러리를 import할 수 없습니다")
        raise ValueError("OpenAI 라이브러리를 import할 수 없습니다")

    # --- 네트워크 프록시 해제(기존 모듈과 동일한 안전장치) ---
    os.environ.pop('HTTP_PROXY', None)
    os.environ.pop('HTTPS_PROXY', None)

    # --- OpenAI 클라이언트 생성 ---
    client = OpenAI(api_key=OPENAI_API_KEY, timeout=60.0)

    # ---------- 공통 규칙/가이드 ----------
    RULES = rf"""
[규칙 - 반드시 지켜]
- 원문 충실도 최우선: 원문 문장을 그대로 또는 아주 가볍게 다듬어 사용(핵심 어휘/감정/말투 보존).
- 날조/추측 금지(없는 사실 추가 금지), 과장 금지, 이모지 금지.
- 톤: 끝까지 친근한 반말. 존댓말/반말 섞지 말 것.
- 길이: 길이: body1~body50 각 {line_len_min}자 이상, 가능하면 {line_len_max}자 안팎. 제목 {title_len_max}자 이내.
- 구조(최대 50줄): 자유롭게 구성하되 강렬한 후킹으로 시작해 댓글 유도로 마무리.
- 출력은 아래 JSON 스키마만. 여분 텍스트/설명/코드블록 절대 금지.
{{
  "title": "...",
  "body1": "...",
  "body2": "...",
  ...
  "body50": "..."
}}
"""

    STYLE_HINT = ("YouTube 스크립트" if is_youtube else "웹 본문")

    # ---------- 유틸 ----------
    def _pick_json(s: str) -> str:
        m = re.search(r'\{[\s\S]*\}', s)
        return m.group(0) if m else s

    def _len_ok(line: str) -> bool:
        return line_len_min <= len(line.strip()) <= line_len_max

    def _strip_emoji(s: str) -> str:
        # 대부분의 이모지, 확장 기호 제거(표준 re 기반)
        return re.sub(r'[\U00010000-\U0010FFFF]', '', s)

    def _soft_shorten(line: str) -> str:
        # 자연 축약 사전(말맛 유지)
        repl = [
            (" 것은", "건"), (" 인거야", "인 거야"),
            (" 하는 거야", "하는 거야"), (" 것 같아", " 같아"),
            (" 하는 것은", "하는 건"), (" 그런데", " 근데"),
            (" 이렇게", " 이렇게"), (" 저렇게", " 저렇게"),
            (" 정말", ""), (" 진짜", ""), (" 너무", ""),  # 추가 축약
        ]
        out = line.strip()
        for _ in range(6):
            if len(out) <= line_len_max:
                break
            for a, b in repl:
                if len(out) <= line_len_max:
                    break
                out = out.replace(a, b)
        return out

    def _soft_lengthen(line: str, target_min: int) -> str:
        # 짧은 문장을 자연스럽게 확장
        s = line.strip()
        fillers: List[str] = [
            " 그래서 말이야.", " 근데 여기서 고민돼.", " 결국 이게 포인트야.",
            " 네 생각은 어때?", " 솔직히 좀 묘하지?", " 인정하지?",
            " 이 부분이 핵심이야.", " 다시 생각해보자."
        ]
        i = 0
        # 과도 확장을 방지하기 위해 한 번에 한 문장씩만 붙여가며 target_min까지
        while len(s) < target_min and i < len(fillers):
            s = (s.rstrip("….,!?") + fillers[i]).strip()
            i += 1
        # 그래도 모자라면 말줄임표로 마무리
        if len(s) < target_min:
            s = s + "…"
        return s

    def _post_fix(data: dict) -> dict:
        # 이모지 제거 + 길이 보정(길면 줄이고, 짧으면 늘리고) + 제목 길이 제한
        for i in range(1, 51):  # body1 ~ body50
            k = f"body{i}"
            if k in data and isinstance(data[k], str):
                s = _strip_emoji(data[k]).strip()
                if not _len_ok(s):
                    if len(s) > line_len_max:
                        s = _soft_shorten(s)
                    if len(s) < line_len_min:
                        s = _soft_lengthen(s, line_len_min)
                data[k] = s
        if "title" in data and isinstance(data["title"], str):
            t = _strip_emoji(data["title"]).strip()
            if len(t) > title_len_max:
                t = t[:title_len_max]
            data["title"] = t
        return data

    def _preserve_score(original: str, draft_texts: str) -> float:
        """
        간단 토큰 보존율: 공백/구두점 기준 토큰화 후 교집합 비율
        (한국어 한계는 있으나 과도 의역 감지용으로 충분)
        """
        def tok(s: str):
            s = re.sub(r'[^0-9A-Za-z가-힣\s]', ' ', s)
            s = re.sub(r'\s+', ' ', s).strip().lower()
            return set(s.split()) if s else set()
        a, b = tok(original), tok(draft_texts)
        if not a or not b:
            return 0.0
        return len(a & b) / max(1, len(a))

    # ---------- OpenAI 모델 선택(최신 선호 + 폴백) ----------
    # chat.completions에서 흔히 사용 가능한 최신 계열 우선순위
    PREFERRED_MODELS = [
        "gpt-4.1",        # 최신 계열(가용 시 우선)
        "gpt-4.1-mini",   # 경량 최신
        "gpt-4o",         # 고성능 멀티모달(광범위 가용)
        "gpt-4o-mini"     # 경량 4o
    ]

    def _chat_complete_or_raise(model: str, system: str, user: str, temperature: float, max_tokens: int):
        return client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            temperature=temperature,
            max_tokens=max_tokens
        )

    def _try_models(system: str, user: str, temperature: float, max_tokens: int):
        last_err = None
        for m in PREFERRED_MODELS:
            try:
                return _chat_complete_or_raise(m, system, user, temperature, max_tokens), m
            except Exception as e:
                last_err = e
                continue
        # 모든 모델 실패 시 원인 전달
        raise ValueError(f"모델 호출에 실패했습니다: {str(last_err) if last_err else '알 수 없는 오류'}")

    # ---------- 1) EXTRACT ----------
    extract_prompt = f"""
너는 카피라이터다. 다음 {STYLE_HINT}에서 '직접 인용 또는 보존할 만한 핵심 문장'을 뽑아라.
- 훅/갈등/감정/규범(공정성)/양자택일 신호가 있는 문장을 우선.
- 각 항목은 그대로 인용 가능한 문장 또는 가볍게 문장부호만 손본 형태.
- 각 항목에 role=hook|situation|feeling|norms|conflict|self_doubt|choice 중 하나의 태그를 붙여라.
- 10개 이내로 JSON 배열만 출력.

[원문]
{content}

[출력 형식(JSON만)]
[
  {{ "role": "hook", "text": "..." }},
  {{ "role": "situation", "text": "..." }}
]
"""
    extract_resp, _ = _try_models(
        system="문장 추출가이자 언어정제자.",
        user=extract_prompt,
        temperature=0.3,
        max_tokens=1000
    )
    extract = extract_resp.choices[0].message.content

    try:
        cand_json = json.loads(re.findall(r'\[[\s\S]*\]', extract)[0])
    except Exception:
        cand_json = []

    # ---------- 2) WRITE (초안) ----------
    write_prompt = f"""
다음은 원문에서 추출한 '보존 후보 문장들'이다. 이를 최대한 활용해 릴스 대사를 작성하라.
- 직접 인용 또는 원문 어구 보존 비율을 높여라(목표: 약 {int(preserve_target*100)}% 이상).
- 부족한 연결만 최소한으로 자연스럽게 보완.
- [규칙]을 엄격히 준수.

[보존 후보 문장들(JSON)]
{json.dumps(cand_json, ensure_ascii=False, indent=2)}

{RULES}
"""
    draft_resp, _ = _try_models(
        system="릴스 카피라이팅 전문가.",
        user=write_prompt,
        temperature=0.6,
        max_tokens=1000
    )
    draft = draft_resp.choices[0].message.content

    # ---------- 3) CRITIC 루프 ----------
    def _critic_fix(text: str) -> str:
        critic_prompt = f"""
너는 엄격한 에디터다. 아래 초안이 [규칙]을 위반하면 스스로 고쳐서 최종 JSON만 출력하라.
특히 길이({line_len_min}~{line_len_max}자), 반말 통일, 이모지 제거, 날조 금지, 구조(7줄) 준수, 제목 {title_len_max}자 이내를 점검하라.

[초안]
{text}

{RULES}
"""
        resp, _ = _try_models(
            system="형식·제약 검수 전문가.",
            user=critic_prompt,
            temperature=0.2,
            max_tokens=800
        )
        return resp.choices[0].message.content.strip()

    final_out = draft
    for _ in range(max(0, int(max_critic_loops))):
        final_out = _critic_fix(final_out)

    # ---------- 4) JSON 파싱 + POST ----------
    try:
        data = json.loads(_pick_json(final_out))
    except Exception:
        repair_prompt = f"""
아래 텍스트에서 JSON만 추출해 유효한 JSON으로 정리해라. 필드 누락시 공백 문자열로 채워라.
필드는 title, body1~body50 이다. 설명 금지. JSON만 출력.

[텍스트]
{final_out}
"""
        fixed_resp, _ = _try_models(
            system="JSON 정리자",
            user=repair_prompt,
            temperature=0.0,
            max_tokens=300
        )
        fixed = fixed_resp.choices[0].message.content
        data = json.loads(_pick_json(fixed))

    data = _post_fix(data)

    # ---------- 5) 보존율 검사(낮으면 1회 재작성) ----------
    joined_bodies = " ".join([data.get(f"body{i}", "") for i in range(1, 51)])
    score = _preserve_score(content, joined_bodies)

    if score < preserve_threshold:
        reinforce_prompt = f"""
보존율(원문 어구 보존)이 낮다. 아래 JSON을 참고하여 원문 표현을 더 직접적으로 살려 다시 써라.
- 가능한 문장은 '거의 그대로' 사용하되 길이 규칙을 지켜라.
- 특히 훅/갈등/감정 문장은 원문 직인용 우선.
- JSON만 출력.

[현재 결과(JSON)]
{json.dumps(data, ensure_ascii=False, indent=2)}

[원문]
{content}

{RULES}
"""
        reinforced_resp, _ = _try_models(
            system="원문 보존 강화 리라이터",
            user=reinforce_prompt,
            temperature=0.4,
            max_tokens=900
        )
        reinforced = reinforced_resp.choices[0].message.content

        try:
            data2 = json.loads(_pick_json(reinforced))
            data2 = _post_fix(data2)
            joined2 = " ".join([data2.get(f"body{i}", "") for i in range(1, 51)])
            score2 = _preserve_score(content, joined2)
            if score2 >= score:
                data = data2
        except Exception:
            pass

    # ---------- 모델 객체로 반환 (body1-body50 지원) ----------
    reels_content = ReelsContent(
        title=data.get("title", ""),
        **{f"body{i}": data.get(f"body{i}", "") for i in range(1, 51)}
    )
    return reels_content


@router.post("/extract-reels-from-url")
async def extract_reels_from_url(request: URLExtractRequest):
    """URL에서 릴스 대본 추출"""
    try:
        logger.info(f"릴스 추출 요청: {request.url}")

        # URL 검증
        if not request.url.strip():
            raise HTTPException(status_code=400, detail="URL을 입력해주세요.")

        # URL 형식 검증
        try:
            parsed_url = urlparse(request.url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise ValueError("올바른 URL 형식이 아닙니다.")
        except Exception:
            raise HTTPException(status_code=400, detail="올바른 URL 형식이 아닙니다.")

        # YouTube URL인지 확인하고 적절한 콘텐츠 추출
        try:
            if is_youtube_url(request.url):
                # YouTube 비디오 스크립트 추출
                video_id = extract_youtube_video_id(request.url)
                if not video_id:
                    logger.error(f"YouTube 비디오 ID 추출 실패: {request.url}")
                    raise ValueError("YouTube 비디오 ID를 추출할 수 없습니다.")

                logger.info(f"YouTube 비디오 감지: {video_id}")
                scraped_content = get_youtube_transcript(video_id)
                logger.info(f"YouTube 스크립트 추출 완료: {len(scraped_content)} 문자")
            else:
                # 일반 웹사이트 스크래핑
                logger.info(f"일반 웹사이트 스크래핑 시작: {request.url}")
                scraped_content = scrape_website_content(request.url)
                logger.info(f"웹사이트 스크래핑 완료: {len(scraped_content)} 문자")
        except ValueError as e:
            logger.error(f"콘텐츠 추출 실패 - ValueError: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"콘텐츠 추출 실패 - 예상치 못한 오류: {str(e)}")
            raise HTTPException(status_code=500, detail=f"콘텐츠 추출 중 오류가 발생했습니다: {str(e)}")

        # ChatGPT로 릴스 대본 생성
        try:
            is_youtube_content = is_youtube_url(request.url)
            reels_content = await generate_reels_with_chatgpt(scraped_content, is_youtube_content)
        except ValueError as e:
            raise HTTPException(status_code=500, detail=str(e))

        return JSONResponse(
            content={
                "status": "success",
                "message": "릴스 대본이 성공적으로 생성되었습니다.",
                "reels_content": reels_content.model_dump()
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"릴스 추출 중 예외 발생: {e}")
        raise HTTPException(status_code=500, detail="릴스 대본 추출 중 오류가 발생했습니다.")
