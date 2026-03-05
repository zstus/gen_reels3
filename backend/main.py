from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import Optional, List
from pydantic import BaseModel
import json
import os
import requests
import shutil
import time
from urllib.parse import urlparse
from video_generator import VideoGenerator
import random
import glob
import re
import asyncio
from bs4 import BeautifulSoup
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError as e:
    # logger는 아직 초기화 전이므로 임시로 print 사용
    print(f"OpenAI import 오류: {e}")
    OpenAI = None
    OPENAI_AVAILABLE = False
import logging
import re
import uuid
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv

# .env 파일 먼저 로드
load_dotenv()

# 통합 로깅 시스템 import
from utils.logger_config import get_logger
logger = get_logger('main')

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    YOUTUBE_TRANSCRIPT_AVAILABLE = True
except ImportError as e:
    logger.error(f"YouTube Transcript API import 오류: {e}")
    logger.info("pip install youtube-transcript-api==0.6.1 로 라이브러리를 설치해주세요.")
    YouTubeTranscriptApi = None
    YOUTUBE_TRANSCRIPT_AVAILABLE = False

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError as e:
    logger.error(f"aiohttp import 오류: {e}")
    logger.info("pip install aiohttp==3.9.1 로 라이브러리를 설치해주세요.")
    aiohttp = None
    AIOHTTP_AVAILABLE = False

# 새로운 모듈들 import (배치 작업 시스템)
try:
    from job_queue import job_queue, JobStatus
    from email_service import email_service
    JOB_QUEUE_AVAILABLE = True
    logger.info("✅ 배치 작업 시스템 로드 성공")
except ImportError as e:
    logger.warning(f"⚠️ 배치 작업 시스템 로드 실패: {e}")
    job_queue = None
    email_service = None
    JOB_QUEUE_AVAILABLE = False

# Job 로깅 시스템 import
try:
    from job_logger import job_logger
    JOB_LOGGER_AVAILABLE = True
    logger.info("✅ Job 로깅 시스템 로드 성공")
except ImportError as e:
    logger.warning(f"⚠️ Job 로깅 시스템 로드 실패: {e}")
    job_logger = None
    JOB_LOGGER_AVAILABLE = False

# Folder 관리 시스템 import
try:
    from folder_manager import folder_manager
    FOLDER_MANAGER_AVAILABLE = True
    logger.info("✅ Folder 관리 시스템 로드 성공")
except ImportError as e:
    logger.warning(f"⚠️ Folder 관리 시스템 로드 실패: {e}")
    folder_manager = None
    FOLDER_MANAGER_AVAILABLE = False

# 썸네일 생성 시스템 import
try:
    from thumbnail_generator import generate_missing_thumbnails
    THUMBNAIL_GENERATOR_AVAILABLE = True
    logger.info("✅ 썸네일 생성 시스템 로드 성공")
except ImportError as e:
    logger.warning(f"⚠️ 썸네일 생성 시스템 로드 실패: {e}")
    generate_missing_thumbnails = None
    THUMBNAIL_GENERATOR_AVAILABLE = False

# 통합 로깅 시스템 초기화 완료
logger.info("🚀 Main 서버 초기화 시작")

app = FastAPI(title="Reels Video Generator", version="1.0.0")

# uploads 디렉토리 생성 (정적 파일 마운트는 nginx에서 처리)
uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(uploads_dir, exist_ok=True)

# Pydantic 모델 정의
class URLExtractRequest(BaseModel):
    url: str

class ImageGenerateRequest(BaseModel):
    texts: List[str]  # 이미지 생성할 텍스트 리스트
    mode: str = "per_script"  # "per_script" 또는 "per_two_scripts"
    job_id: Optional[str] = None  # Job ID 추가 (선택적)

class ReelsContent(BaseModel):
    title: str
    body1: str = ""
    body2: str = ""
    body3: str = ""
    body4: str = ""
    body5: str = ""
    body6: str = ""
    body7: str = ""
    body8: str = ""
    body9: str = ""
    body10: str = ""
    body11: str = ""
    body12: str = ""
    body13: str = ""
    body14: str = ""
    body15: str = ""
    body16: str = ""
    body17: str = ""
    body18: str = ""
    body19: str = ""
    body20: str = ""
    body21: str = ""
    body22: str = ""
    body23: str = ""
    body24: str = ""
    body25: str = ""
    body26: str = ""
    body27: str = ""
    body28: str = ""
    body29: str = ""
    body30: str = ""
    body31: str = ""
    body32: str = ""
    body33: str = ""
    body34: str = ""
    body35: str = ""
    body36: str = ""
    body37: str = ""
    body38: str = ""
    body39: str = ""
    body40: str = ""
    body41: str = ""
    body42: str = ""
    body43: str = ""
    body44: str = ""
    body45: str = ""
    body46: str = ""
    body47: str = ""
    body48: str = ""
    body49: str = ""
    body50: str = ""

# 배치 작업 관련 모델들
class AsyncVideoRequest(BaseModel):
    user_email: str
    content_data: str
    music_mood: str = "bright"
    image_allocation_mode: str = "2_per_image"
    text_position: str = "bottom"
    text_style: str = "outline"
    title_area_mode: str = "keep"
    selected_bgm_path: str = ""
    use_test_files: bool = False

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    created_at: str
    updated_at: str
    result: Optional[dict] = None
    error_message: Optional[str] = None

# Job 폴더 관련 모델들
class CreateJobFolderRequest(BaseModel):
    job_id: str

class CreateJobFolderResponse(BaseModel):
    status: str
    message: str
    job_id: str
    uploads_folder: Optional[str] = None
    output_folder: Optional[str] = None

class CleanupJobFolderRequest(BaseModel):
    job_id: str
    keep_output: bool = True

class CleanupJobFolderResponse(BaseModel):
    status: str
    message: str
    job_id: str
    cleaned: bool

# OpenAI import 상태 로깅
if OPENAI_AVAILABLE:
    logger.info("OpenAI 라이브러리 import 성공")
else:
    logger.error("OpenAI 라이브러리 import 실패")

# aiohttp import 상태 로깅
if AIOHTTP_AVAILABLE:
    logger.info("aiohttp 라이브러리 import 성공 - 병렬 이미지 처리 가능")
else:
    logger.warning("aiohttp 라이브러리 import 실패 - 순차 이미지 처리로 대체됩니다")

# OpenAI API 키 설정 (환경변수에서 로드)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
if not OPENAI_API_KEY:
    logger.warning("OpenAI API 키가 설정되지 않았습니다. URL에서 릴스 추출 기능이 비활성화됩니다.")
else:
    logger.info("OpenAI API 키 로드 성공")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://zstus.synology.me:8097"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 영상 출력 폴더 설정
OUTPUT_FOLDER = "output_videos"
UPLOAD_FOLDER = "uploads"
BGM_FOLDER = "bgm"
BOOKMARK_VIDEOS_FOLDER = os.path.join("assets", "videos", "bookmark")

# 폴더 생성
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(BGM_FOLDER, exist_ok=True)
os.makedirs(BOOKMARK_VIDEOS_FOLDER, exist_ok=True)

# 글로벌 변수
CURRENT_BGM_PATH = None

# ============================================================================
# Helper Functions
# ============================================================================

async def download_file(url: str, save_path: str):
    """URL에서 파일 다운로드"""
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()

        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"✅ 다운로드 완료: {url} → {os.path.basename(save_path)}")
        return True
    except Exception as e:
        print(f"❌ 다운로드 실패: {url} - {e}")
        return False

def get_file_extension(url: str) -> str:
    """URL에서 파일 확장자 추출"""
    parsed = urlparse(url)
    path = parsed.path.lower()

    # 일반적인 확장자들
    for ext in ['.mp3', '.wav', '.m4a', '.json', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp']:
        if path.endswith(ext):
            return ext

    # 쿼리 파라미터에서 확장자 찾기
    if '.' in path:
        return os.path.splitext(path)[1]

    return ''  # 확장자 없음

def select_random_bgm(mood: str) -> str:
    """bgm 폴더에서 지정된 성격의 음악을 랜덤 선택"""
    valid_moods = ["bright", "calm", "romantic", "sad", "suspense"]

    if mood not in valid_moods:
        print(f"⚠️ 잘못된 음악 성격: {mood}, 기본값 'bright' 사용")
        mood = "bright"

    mood_folder = os.path.join(BGM_FOLDER, mood)

    # bgm 폴더가 없는 경우
    if not os.path.exists(mood_folder):
        print(f"❌ bgm/{mood} 폴더가 없습니다. test 폴더 음악 사용")
        return None

    # 음악 파일들 검색 (mp3, wav, m4a 지원)
    music_patterns = ["*.mp3", "*.wav", "*.m4a"]
    music_files = []

    for pattern in music_patterns:
        music_files.extend(glob.glob(os.path.join(mood_folder, pattern)))

    if not music_files:
        print(f"❌ bgm/{mood} 폴더에 음악 파일이 없습니다. test 폴더 음악 사용")
        return None

    # 랜덤 선택
    selected_music = random.choice(music_files)
    print(f"🎵 선택된 {mood} 음악: {os.path.basename(selected_music)}")

    return selected_music

def copy_test_images():
    """test 폴더에서 uploads 폴더로 이미지 및 비디오 파일들 복사"""
    try:
        test_folder = "./test"
        media_extensions = ["jpg", "jpeg", "png", "bmp", "gif", "webp", "heic", "heif", "mp4", "mov", "avi", "webm", "mkv"]

        # 1, 2, 3, 4 순서로 미디어 파일 찾기
        copied_count = 0
        for i in range(1, 5):  # 1, 2, 3, 4
            found_file = None
            for ext in media_extensions:
                test_path = os.path.join(test_folder, f"{i}.{ext}")
                if os.path.exists(test_path):
                    found_file = test_path
                    break

            if found_file:
                # 원본 확장자 유지하여 uploads에 복사
                original_ext = os.path.splitext(found_file)[1]
                target_name = f"{i}{original_ext}"
                target_path = os.path.join(UPLOAD_FOLDER, target_name)

                shutil.copy2(found_file, target_path)
                file_type = "비디오" if original_ext.lower() in ['.mp4', '.mov', '.avi', '.webm', '.mkv'] else "이미지"
                print(f"✅ test {file_type} 복사: {os.path.basename(found_file)} → {target_name}")
                copied_count += 1
            else:
                print(f"⚠️ {i}번 미디어 파일을 찾을 수 없습니다 (지원 형식: {', '.join(media_extensions)})")

        print(f"📊 test 폴더에서 {copied_count}개 미디어 파일 복사 완료")
        return True

    except Exception as e:
        print(f"❌ test 이미지 복사 실패: {e}")
        return False

async def prepare_files(json_url: str, music_mood: str, image_urls: str,
                       content_data: str, background_music, use_test_files: bool,
                       selected_bgm_path: str = "", uploaded_images: List = [],
                       edited_texts: str = "{}"):
    """모든 파일을 uploads 폴더에 준비"""

    # 1. JSON 파일 처리
    if use_test_files:
        # test 폴더의 JSON 복사
        test_json = "./test/text.json"
        if os.path.exists(test_json):
            shutil.copy2(test_json, os.path.join(UPLOAD_FOLDER, "text.json"))
            print("✅ test JSON 복사: text.json → text.json")
        else:
            raise ValueError("test/text.json 파일이 없습니다")
    else:
        # URL 또는 직접 데이터로 JSON 처리
        if json_url:
            json_path = os.path.join(UPLOAD_FOLDER, "text.json")
            await download_file(json_url, json_path)
        elif content_data:
            json_path = os.path.join(UPLOAD_FOLDER, "text.json")
            content = json.loads(content_data)  # 검증

            # 🎯 수정된 텍스트 적용 (per-two-scripts 모드)
            try:
                edited_texts_dict = json.loads(edited_texts) if isinstance(edited_texts, str) else edited_texts
                if edited_texts_dict:
                    print(f"📝 수정된 텍스트 적용: {len(edited_texts_dict)}개 이미지 인덱스")
                    for image_idx_str, texts in edited_texts_dict.items():
                        image_idx = int(image_idx_str)
                        # per-two-scripts: imageIndex * 2로 body 인덱스 계산
                        text_idx = image_idx * 2
                        if texts and len(texts) > 0 and texts[0]:
                            body_key = f'body{text_idx + 1}'
                            content[body_key] = texts[0]
                            print(f"✏️ {body_key} 수정: {texts[0][:30]}...")
                        if texts and len(texts) > 1 and texts[1]:
                            body_key = f'body{text_idx + 2}'
                            content[body_key] = texts[1]
                            print(f"✏️ {body_key} 수정: {texts[1][:30]}...")
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                print(f"⚠️ 수정된 텍스트 파싱 실패, 원본 사용: {e}")

            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(content, f, ensure_ascii=False, indent=2)
            print("✅ 직접 JSON 데이터 저장: text.json")
        else:
            raise ValueError("JSON 내용이 필요합니다 (json_url 또는 content_data)")

    # 2. 음악 파일 처리 (우선순위: 업로드 > 선택된 파일 > 랜덤)
    global CURRENT_BGM_PATH

    if music_mood == "none":
        # 음악 선택 안함: BGM 없이 원본 비디오 소리 사용
        CURRENT_BGM_PATH = None
        print("🔇 음악 선택 안함 - BGM 건너뜀 (원본 비디오 소리 사용)")
    elif background_music:
        # 직접 업로드된 음악 파일 저장 (우선순위 1)
        music_path = os.path.join(UPLOAD_FOLDER, "back.mp3")
        with open(music_path, "wb") as f:
            content = await background_music.read()
            f.write(content)
        print("✅ 업로드 음악 저장: back.mp3")
        CURRENT_BGM_PATH = None  # 업로드 파일 사용시 글로벌 변수 초기화
    elif selected_bgm_path:
        # 특정 BGM 파일이 선택된 경우 (우선순위 2)
        bgm_file_path = os.path.join(BGM_FOLDER, music_mood, selected_bgm_path)
        if os.path.exists(bgm_file_path):
            CURRENT_BGM_PATH = bgm_file_path
            print(f"🎵 선택된 BGM 파일 사용: {selected_bgm_path}")
        else:
            # 선택된 파일이 없으면 랜덤 선택으로 폴백
            print(f"⚠️ 선택된 파일({selected_bgm_path})을 찾을 수 없어 랜덤 선택으로 변경")
            selected_bgm = select_random_bgm(music_mood)
            if not selected_bgm:
                raise ValueError(f"배경음악을 찾을 수 없습니다. bgm/{music_mood} 폴더에 음악 파일을 추가해주세요.")
            CURRENT_BGM_PATH = selected_bgm
    else:
        # bgm 폴더에서 성격별 랜덤 음악 선택 (우선순위 3)
        print(f"🎵 음악 성격 '{music_mood}' 기반으로 bgm 랜덤 선택 중...")
        selected_bgm = select_random_bgm(music_mood)

        if not selected_bgm:
            raise ValueError(f"배경음악을 찾을 수 없습니다. bgm/{music_mood} 폴더에 음악 파일(.mp3/.wav/.m4a)을 추가해주세요.")

        CURRENT_BGM_PATH = selected_bgm
        print(f"🎵 랜덤 선택된 BGM: {os.path.basename(selected_bgm)}")

    # 3. 이미지 파일들 처리
    if use_test_files:
        # test 폴더에서 이미지들만 복사
        copy_test_images()
        print("📊 test 폴더 이미지 사용")
    elif uploaded_images:
        # 업로드된 이미지 파일들 저장
        for i, image_file in enumerate(uploaded_images, 1):
            if image_file:
                # 파일 확장자 추출
                ext = os.path.splitext(image_file.filename)[1] or '.png'
                image_path = os.path.join(UPLOAD_FOLDER, f"{i}{ext}")

                # 업로드된 파일 저장
                with open(image_path, "wb") as f:
                    content = await image_file.read()
                    f.write(content)

                print(f"✅ 이미지 {i} 저장: {image_file.filename} → {i}{ext}")

        print(f"📊 {len(uploaded_images)}개 이미지 파일 업로드 완료")
    else:
        # URL에서 이미지 다운로드 (기존 방식)
        try:
            image_url_list = json.loads(image_urls) if image_urls else []
        except:
            image_url_list = []

        if image_url_list:
            for i, img_url in enumerate(image_url_list, 1):
                ext = get_file_extension(img_url)
                if not ext:
                    ext = '.png'
                img_path = os.path.join(UPLOAD_FOLDER, f"{i}{ext}")
                await download_file(img_url, img_path)
            print(f"📊 {len(image_url_list)}개 이미지 URL에서 다운로드 완료")
        else:
            print("ℹ️ 이미지 없이 진행 (텍스트 전용 영상)")

    # CURRENT_BGM_PATH 값을 반환하여 호출자가 사용할 수 있도록 함
    return CURRENT_BGM_PATH

def build_illustration_prompt(source_text: str) -> str:
    """
    '실사 사진 같은(photorealistic), 톤다운' 이미지를 생성하기 위한 프롬프트.
    입력 텍스트의 의미를 주제로 삼아 충실히 시각화하며,
    과도한 채도/대비를 피하고 자연광과 영화적 톤으로 묘사하도록 지시합니다.
    """
    return f"""
Create a photorealistic color photograph that faithfully visualizes the meaning and main subject of this sentence:

"{source_text}"

Output intent:
- Show a believable real-world scene that clearly expresses the sentence's core idea.
- Stay faithful to the content; do not introduce objects, characters, or events that are not implied.

Look & grading:
- Muted, toned-down palette with soft natural/ambient lighting.
- Gentle contrast and highlights; subtle filmic grain; realistic materials and textures.
- Cinematic color grading leaning warm neutrals; avoid neon or oversaturated colors.

Camera & optics:
- Full-frame aesthetic, 35–50mm equivalent, f/2.8–f/4 for shallow-to-moderate depth of field.
- Physically plausible shadows/reflections and coherent global illumination.
- Accurate perspective and scale; natural bokeh if applicable.

Composition:
- Clean and uncluttered; contemporary, minimal styling.
- Square format (1024×1024) with balanced framing and negative space allowed.

Strict rules:
- Do NOT render any words, letters, numbers, captions, UI, logos, brands, watermarks, or signage.
- Avoid illustration, vector art, cartoon/comic style, heavy outlines, flat primary colors, 3D render look, HDR/over-processed effects, or surreal elements.
- People (if any) must be generic and anonymous (no celebrity likeness, no identifying details).

Keywords: photorealistic, filmic, muted colors, natural light, soft shadows, depth of field, realistic textures, subtle grain, cinematic, refined.
""".strip()

def build_safe_retry_prompt(source_text: str) -> str:
    """
    콘텐츠 필터 재시도용: '실사(photorealistic), 톤다운' 이미지 지시문.
    입력 문장의 의미를 보존하되, 식별 가능한 디테일을 줄이기 위해
    '그림자/실루엣/반사' 위주로 안전하게 시각화한다.
    """
    return f"""
Create a muted, photorealistic color photograph that conveys the core meaning of this sentence
through silhouettes, soft shadows, or subtle reflections only (no readable details):

"{source_text}"

Output intent:
- Depict a believable real-world scene that clearly relates to the sentence above.
- Visualize the subject via silhouettes/shadows/reflections on simple surfaces (walls, floors, curtains, tables),
  or through diffused light and occlusion; avoid identifiable details.
- If the sentence implies people, show backlit figures or partial silhouettes only; otherwise, prefer object/environment shadows.

Look & grading:
- Muted, toned-down colors; soft ambient/natural light (overcast or late-afternoon backlight).
- Gentle contrast; subtle filmic grain; realistic materials and textures.
- Coherent global illumination and physically plausible shadows/reflections.

Camera & optics:
- 35–50mm full-frame equivalent, f/2.8–f/4 for shallow-to-moderate depth of field.
- Accurate perspective and scale; natural bokeh if applicable.

Composition:
- Clean, uncluttered frame; negative space allowed.
- Square format (1024×1024); balanced, minimal composition focused on silhouettes/shadows.

Strict safety rules:
- No readable text, letters, numbers, logos, brands, UI, or watermarks.
- No identifiable faces or unique personal details (tattoos, plates, IDs).
- Avoid violence, medical/graphic content, sexual/suggestive elements, minors.
- Avoid illustration/vector/cartoon look, heavy outlines, HDR/over-processed effects, surreal/fantasy.

Keywords: photorealistic, silhouette, shadow play, muted colors, natural light, subtle grain, cinematic calm, minimal, safe content.
""".strip()

# ============================================================================
# Router Integration
# ============================================================================

from routers import (
    system_router,
    job_router,
    asset_router,
    media_router,
    download_router,
    content_router,
    image_router,
    video_router,
    external_api_router,
)

# Set dependencies for each router
system_router.set_availability_flags(
    OPENAI_AVAILABLE,
    YOUTUBE_TRANSCRIPT_AVAILABLE,
    AIOHTTP_AVAILABLE,
    JOB_QUEUE_AVAILABLE
)

job_router.set_dependencies(
    job_queue,
    job_logger,
    folder_manager,
    JOB_QUEUE_AVAILABLE,
    JOB_LOGGER_AVAILABLE,
    FOLDER_MANAGER_AVAILABLE
)

asset_router.set_dependencies(BGM_FOLDER)

media_router.set_dependencies(
    folder_manager,
    FOLDER_MANAGER_AVAILABLE,
    BOOKMARK_VIDEOS_FOLDER,
    UPLOAD_FOLDER
)

download_router.set_dependencies(
    email_service,
    JOB_QUEUE_AVAILABLE,
    OUTPUT_FOLDER
)

content_router.set_dependencies(
    OPENAI_AVAILABLE,
    YOUTUBE_TRANSCRIPT_AVAILABLE,
    YouTubeTranscriptApi
)

image_router.set_dependencies(
    OPENAI_AVAILABLE,
    OPENAI_API_KEY,
    folder_manager,
    FOLDER_MANAGER_AVAILABLE,
    UPLOAD_FOLDER,
    OpenAI
)

video_router.set_dependencies(
    folder_manager,
    job_queue,
    job_logger,
    FOLDER_MANAGER_AVAILABLE,
    JOB_QUEUE_AVAILABLE,
    JOB_LOGGER_AVAILABLE,
    UPLOAD_FOLDER,
    OUTPUT_FOLDER,
    CURRENT_BGM_PATH,
    VideoGenerator,
    prepare_files
)

external_api_router.set_dependencies(
    folder_manager,
    job_queue,
    FOLDER_MANAGER_AVAILABLE,
    JOB_QUEUE_AVAILABLE,
    UPLOAD_FOLDER,
    OUTPUT_FOLDER,
)

# Include routers
app.include_router(system_router.router)
app.include_router(job_router.router)
app.include_router(asset_router.router)
app.include_router(media_router.router)
app.include_router(download_router.router)
app.include_router(content_router.router)
app.include_router(image_router.router)
app.include_router(video_router.router)
app.include_router(external_api_router.router)

# ============================================================================
# Static File Mounts
# ============================================================================

# 정적 파일 서빙
app.mount("/bgm", StaticFiles(directory=BGM_FOLDER), name="bgm")
app.mount("/videos", StaticFiles(directory=OUTPUT_FOLDER), name="videos")

# ============================================================================
# Server Startup
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
