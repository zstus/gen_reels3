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
    print(f"OpenAI import 오류: {e}")
    OpenAI = None
    OPENAI_AVAILABLE = False
import logging
import re
import uuid
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    YOUTUBE_TRANSCRIPT_AVAILABLE = True
except ImportError as e:
    print(f"YouTube Transcript API import 오류: {e}")
    print("pip install youtube-transcript-api==0.6.1 로 라이브러리를 설치해주세요.")
    YouTubeTranscriptApi = None
    YOUTUBE_TRANSCRIPT_AVAILABLE = False

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError as e:
    print(f"aiohttp import 오류: {e}")
    print("pip install aiohttp==3.9.1 로 라이브러리를 설치해주세요.")
    aiohttp = None
    AIOHTTP_AVAILABLE = False
# Updated with create_simple_group_clip method

# 새로운 모듈들 import (배치 작업 시스템)
try:
    from job_queue import job_queue, JobStatus
    from email_service import email_service
    JOB_QUEUE_AVAILABLE = True
    print("✅ 배치 작업 시스템 로드 성공")
except ImportError as e:
    print(f"⚠️ 배치 작업 시스템 로드 실패: {e}")
    job_queue = None
    email_service = None
    JOB_QUEUE_AVAILABLE = False

# Job 로깅 시스템 import
try:
    from job_logger import job_logger
    JOB_LOGGER_AVAILABLE = True
    print("✅ Job 로깅 시스템 로드 성공")
except ImportError as e:
    print(f"⚠️ Job 로깅 시스템 로드 실패: {e}")
    job_logger = None
    JOB_LOGGER_AVAILABLE = False

# Folder 관리 시스템 import
try:
    from folder_manager import folder_manager
    FOLDER_MANAGER_AVAILABLE = True
    print("✅ Folder 관리 시스템 로드 성공")
except ImportError as e:
    print(f"⚠️ Folder 관리 시스템 로드 실패: {e}")
    folder_manager = None
    FOLDER_MANAGER_AVAILABLE = False

# 썸네일 생성 시스템 import
try:
    from thumbnail_generator import generate_missing_thumbnails
    THUMBNAIL_GENERATOR_AVAILABLE = True
    print("✅ 썸네일 생성 시스템 로드 성공")
except ImportError as e:
    print(f"⚠️ 썸네일 생성 시스템 로드 실패: {e}")
    generate_missing_thumbnails = None
    THUMBNAIL_GENERATOR_AVAILABLE = False

# .env 파일 로드
load_dotenv()

# API 로깅 설정 - 서버 재시작 시 기존 로그 삭제
API_LOG_FILE = "api.log"
if os.path.exists(API_LOG_FILE):
    os.remove(API_LOG_FILE)
    print(f"🗑️ 기존 로그 파일 삭제: {API_LOG_FILE}")

# 로거 설정 - api.log 파일에만 출력 (콘솔 출력 제거)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(API_LOG_FILE, encoding='utf-8')
    ],
    force=True  # 기존 설정 강제 재설정
)
logger = logging.getLogger(__name__)
logger.info(f"✅ API 로그 파일 생성: {API_LOG_FILE}")

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
        media_extensions = ["jpg", "jpeg", "png", "bmp", "gif", "webp", "mp4", "mov", "avi", "webm", "mkv"]
        
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
                       selected_bgm_path: str = "", uploaded_images: List = []):
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
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(content, f, ensure_ascii=False, indent=2)
            print("✅ 직접 JSON 데이터 저장: text.json")
        else:
            raise ValueError("JSON 내용이 필요합니다 (json_url 또는 content_data)")
    
    # 2. 음악 파일 처리 (우선순위: 업로드 > 선택된 파일 > 랜덤)
    global CURRENT_BGM_PATH
    
    if background_music:
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
            raise ValueError("이미지가 필요합니다 (uploaded_images, image_urls 또는 use_test_files=true)")

@app.get("/")
async def root():
    return {"message": "Reels Video Generator API"}

@app.get("/status")
async def get_status():
    """API 상태 및 기능 확인"""
    status = {
        "status": "running",
        "features": {
            "openai": OPENAI_AVAILABLE,
            "youtube_transcript": YOUTUBE_TRANSCRIPT_AVAILABLE,
            "aiohttp": AIOHTTP_AVAILABLE
        },
        "message": "Reels Video Generator API is running"
    }
    
    warnings = []
    if not YOUTUBE_TRANSCRIPT_AVAILABLE:
        warnings.append("YouTube transcript API가 사용할 수 없습니다. pip install youtube-transcript-api==0.6.1 로 설치해주세요.")
    
    if not AIOHTTP_AVAILABLE:
        warnings.append("aiohttp 라이브러리가 사용할 수 없습니다. pip install aiohttp==3.9.1 로 설치해주세요. 병렬 이미지 생성이 순차 처리로 대체됩니다.")
    
    if warnings:
        status["warnings"] = warnings
    
    return status

@app.get("/youtube-test-videos")
async def get_youtube_test_videos():
    """자막이 있는 YouTube 테스트 비디오 목록"""
    return {
        "status": "success",
        "recommended_videos": [
            {
                "title": "Me at the zoo (첫 번째 YouTube 비디오)",
                "url": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
                "language": "English",
                "description": "YouTube 역사상 첫 번째 업로드된 비디오, 영어 자막"
            },
            {
                "title": "PSY - Gangnam Style",
                "url": "https://www.youtube.com/watch?v=9bZkp7q19f0", 
                "language": "Korean/English",
                "description": "세계적으로 유명한 K-POP 비디오, 다국어 자막"
            },
            {
                "title": "TED Talk 예시",
                "url": "https://www.youtube.com/watch?v=ZSHk0I9XHLE",
                "language": "English/Multiple",
                "description": "교육적인 내용으로 자막이 잘 되어있음"
            }
        ],
        "tips": [
            "TED Talks, 기업 공식 채널, 교육 콘텐츠는 보통 자막이 잘 되어있습니다",
            "개인 브이로그, 라이브 스트림, 음악 비디오는 자막이 없는 경우가 많습니다",
            "비디오 재생 시 설정에서 '자막/CC'를 확인해보세요"
        ]
    }

@app.post("/generate-video")
async def generate_video(
    # 웹서비스용 URL 입력
    json_url: str = Form(default=""),           # JSON 내용 URL
    music_mood: str = Form(default="bright"),   # 배경음악 성격 (bright, calm, romantic, sad, suspense)
    image_urls: str = Form(default="[]"),       # 이미지 URLs JSON 배열
    
    # 기존 호환성 유지 (옵션)
    content_data: str = Form(default=""),       # 직접 JSON 내용
    background_music: Optional[UploadFile] = File(None),  # 직접 음악 업로드
    
    # 새로운 파라미터: 선택된 BGM 파일명
    selected_bgm_path: str = Form(default=""),  # 선택된 BGM 파일 경로
    
    # 이미지 할당 모드 선택
    image_allocation_mode: str = Form(default="2_per_image"),  # "2_per_image" 또는 "1_per_image"
    
    # 텍스트 위치 선택
    text_position: str = Form(default="bottom"),  # "top", "bottom", "bottom-edge"
    
    # 텍스트 스타일 선택
    text_style: str = Form(default="outline"),  # "outline" (외곽선) 또는 "background" (반투명 배경)

    # 타이틀 영역 모드 선택
    title_area_mode: str = Form(default="keep"),  # "keep" (확보) 또는 "remove" (제거)

    # 폰트 설정
    title_font: str = Form(default="BMYEONSUNG_otf.otf"),  # 타이틀 폰트
    body_font: str = Form(default="BMYEONSUNG_otf.otf"),   # 본문 폰트
    title_font_size: int = Form(default=42),               # 타이틀 폰트 크기 (pt)
    body_font_size: int = Form(default=36),                # 본문 폰트 크기 (pt)

    # 자막 읽어주기 설정
    voice_narration: str = Form(default="enabled"),        # "enabled" (추가) 또는 "disabled" (제거)

    # 크로스 디졸브 설정
    cross_dissolve: str = Form(default="enabled"),          # "enabled" (적용) 또는 "disabled" (미적용)

    # 자막 지속 시간 설정 (초 단위)
    subtitle_duration: float = Form(default=0.0),           # 0: 음성 길이 사용, 0 초과: 지정 시간 사용

    # 이미지 파일 업로드 (최대 8개)
    image_1: Optional[UploadFile] = File(None),
    image_2: Optional[UploadFile] = File(None),
    image_3: Optional[UploadFile] = File(None),
    image_4: Optional[UploadFile] = File(None),
    image_5: Optional[UploadFile] = File(None),
    image_6: Optional[UploadFile] = File(None),
    image_7: Optional[UploadFile] = File(None),
    image_8: Optional[UploadFile] = File(None),

    # 모드 설정
    use_test_files: bool = Form(default=False),  # test 폴더 사용 여부

    # Job ID (선택적)
    job_id: Optional[str] = Form(None)  # Job ID 추가
):
    try:
        print("🚀 웹서비스 API 호출 시작")

        # Job ID에 따라 작업 폴더 설정
        global UPLOAD_FOLDER, OUTPUT_FOLDER
        original_upload_folder = UPLOAD_FOLDER
        original_output_folder = OUTPUT_FOLDER

        if job_id and FOLDER_MANAGER_AVAILABLE:
            try:
                job_uploads_folder, job_output_folder = folder_manager.get_job_folders(job_id)
                UPLOAD_FOLDER = job_uploads_folder
                OUTPUT_FOLDER = job_output_folder
                print(f"🗂️ Job 고유 폴더 사용 (영상 생성): uploads={UPLOAD_FOLDER}, output={OUTPUT_FOLDER}")
            except Exception as job_error:
                print(f"⚠️ Job 폴더 사용 실패, 기본 폴더 사용 (영상 생성): {job_error}")

        # 1. uploads 폴더 준비 및 정리
        if job_id and FOLDER_MANAGER_AVAILABLE:
            # Job 폴더 사용 시: 기존 파일들 보존 (이미지 자동생성, 프리뷰 등)
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            print(f"📁 기존 Job 폴더 재사용: {UPLOAD_FOLDER}")
        else:
            # 기본 폴더 사용 시: 기존 방식대로 폴더 초기화
            if os.path.exists(UPLOAD_FOLDER):
                shutil.rmtree(UPLOAD_FOLDER)
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            print("📁 uploads 폴더 준비 완료")
        
        # 2. 파일들을 uploads 폴더에 준비
        # 업로드된 이미지 파일들 수집
        uploaded_images = [
            image_1, image_2, image_3, image_4,
            image_5, image_6, image_7, image_8
        ]
        uploaded_images = [img for img in uploaded_images if img is not None]
        
        await prepare_files(
            json_url, music_mood, image_urls, 
            content_data, background_music, use_test_files,
            selected_bgm_path, uploaded_images
        )
        
        # 3. uploads 폴더의 파일들로 영상 생성
        video_gen = VideoGenerator()
        # bgm 파일 경로 결정 우선순위:
        # 1. 직접 업로드된 음악 파일
        # 2. 선택된 특정 BGM 파일
        # 3. 성격별 랜덤 선택 (기존 방식)
        if background_music:
            bgm_file = os.path.join(UPLOAD_FOLDER, "back.mp3")
            print(f"🎵 직접 업로드된 음악 사용: {bgm_file}")
        elif CURRENT_BGM_PATH:
            bgm_file = CURRENT_BGM_PATH
            print(f"🎵 선택된 BGM 파일 사용: {bgm_file}")
        else:
            bgm_file = None
            print("⚠️ BGM 파일이 설정되지 않았습니다")
        
        # Frontend의 모드를 Backend 형식으로 변환
        # 🎯 미디어 업로드 모드 3가지 옵션:
        # 1. per-script: 대사마다 미디어 1개 (1:1 매핑)
        # 2. per-two-scripts: 대사 2개마다 미디어 1개 (2:1 매핑)
        # 3. single-for-all: 모든 대사에 미디어 1개 (1:ALL 매핑)
        mode_mapping = {
            "per-script": "1_per_image",           # 대사마다 미디어 1개
            "per-two-scripts": "2_per_image",      # 대사 2개마다 미디어 1개
            "single-for-all": "single_for_all"     # 모든 대사에 미디어 1개
        }

        if image_allocation_mode in mode_mapping:
            original_mode = image_allocation_mode
            image_allocation_mode = mode_mapping[image_allocation_mode]
            print(f"🎯 미디어 모드 변환: {original_mode} → {image_allocation_mode}")

        # 이미지 할당 모드 검증
        if image_allocation_mode not in ["2_per_image", "1_per_image", "single_for_all"]:
            image_allocation_mode = "2_per_image"  # 기본값
            print(f"⚠️ 잘못된 이미지 할당 모드, 기본값 사용: {image_allocation_mode}")
        
        # 텍스트 위치 검증
        if text_position not in ["top", "bottom", "bottom-edge"]:
            text_position = "bottom"  # 기본값
            print(f"⚠️ 잘못된 텍스트 위치, 기본값 사용: {text_position}")
        
        # 텍스트 스타일 검증
        if text_style not in ["outline", "background"]:
            text_style = "outline"  # 기본값
            print(f"⚠️ 잘못된 텍스트 스타일, 기본값 사용: {text_style}")
        
        print(f"🖼️ 이미지 할당 모드: {image_allocation_mode}")
        print(f"📝 텍스트 위치: {text_position}")
        print(f"🎨 텍스트 스타일: {text_style}")
        print(f"🏠 타이틀 영역 모드: {title_area_mode}")
        print(f"🔤 타이틀 폰트: {title_font} ({title_font_size}pt)")
        print(f"📝 본문 폰트: {body_font} ({body_font_size}pt)")
        print(f"🎤 자막 읽어주기: {voice_narration}")
        print(f"🎬 크로스 디졸브: {cross_dissolve}")
        print(f"⏱️ 자막 지속 시간: {subtitle_duration}초 (0=음성길이)")

        output_path = video_gen.create_video_from_uploads(
            OUTPUT_FOLDER,
            bgm_file,
            image_allocation_mode,
            text_position,
            text_style,
            title_area_mode,
            title_font,
            body_font,
            title_font_size,
            body_font_size,
            "uploads",
            music_mood,
            voice_narration,
            cross_dissolve,
            subtitle_duration
        )

        # 영상 생성 성공 시 job 폴더 정리
        if job_id and FOLDER_MANAGER_AVAILABLE:
            try:
                # Job 폴더 정리 (output 폴더는 보존, uploads 폴더는 정리)
                cleaned = folder_manager.cleanup_job_folders(job_id, keep_output=True)
                if cleaned:
                    print(f"✅ Job 폴더 정리 완료: {job_id}")
                else:
                    print(f"⚠️ Job 폴더 정리 실패: {job_id}")
            except Exception as cleanup_error:
                print(f"⚠️ Job 폴더 정리 중 오류: {cleanup_error}")

        # 글로벌 변수 복원
        if job_id and FOLDER_MANAGER_AVAILABLE:
            UPLOAD_FOLDER = original_upload_folder
            OUTPUT_FOLDER = original_output_folder

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Video generated successfully",
                "video_path": output_path
            }
        )

    except Exception as e:
        # 에러 시에도 job 폴더 정리 (uploads 폴더 정리)
        if job_id and FOLDER_MANAGER_AVAILABLE:
            try:
                # 에러 시에는 모든 파일 정리 (output 폴더도 정리)
                cleaned = folder_manager.cleanup_job_folders(job_id, keep_output=False)
                if cleaned:
                    print(f"🗑️ 에러 발생으로 Job 폴더 전체 정리: {job_id}")
                else:
                    print(f"⚠️ 에러 시 Job 폴더 정리 실패: {job_id}")
            except Exception as cleanup_error:
                print(f"⚠️ 에러 시 Job 폴더 정리 중 추가 오류: {cleanup_error}")

        # 글로벌 변수 복원 (에러 시에도)
        if job_id and FOLDER_MANAGER_AVAILABLE:
            UPLOAD_FOLDER = original_upload_folder
            OUTPUT_FOLDER = original_output_folder

        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": str(e)
            }
        )

class SingleImageRequest(BaseModel):
    text: Optional[str] = None
    custom_prompt: Optional[str] = None
    additional_context: Optional[str] = None
    job_id: Optional[str] = None  # Job ID 추가 (선택적)

@app.post("/generate-single-image")
async def generate_single_image(request: SingleImageRequest):
    """개별 텍스트에 대한 이미지 자동 생성 (커스텀 프롬프트 지원)"""
    try:
        logger.info(f"🔥 개별 이미지 생성 요청 시작")
        logger.info(f"📝 요청 텍스트: {request.text}")
        logger.info(f"🎨 커스텀 프롬프트: {request.custom_prompt}")
        logger.info(f"📝 추가 컨텍스트: {request.additional_context}")

        # 입력 유효성 검증
        if not request.text and not request.custom_prompt:
            logger.error("❌ 텍스트 또는 커스텀 프롬프트 중 하나는 필수입니다")
            raise HTTPException(status_code=400, detail="텍스트 또는 커스텀 프롬프트 중 하나는 필수입니다")

        if not OPENAI_AVAILABLE:
            logger.error("❌ OpenAI 라이브러리가 설치되지 않음")
            raise HTTPException(status_code=500, detail="OpenAI 라이브러리가 설치되지 않았습니다")

        # OpenAI API 키 확인
        OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
        if not OPENAI_API_KEY:
            logger.error("❌ OpenAI API 키가 설정되지 않음")
            raise HTTPException(status_code=500, detail="OpenAI API 키가 설정되지 않았습니다")

        logger.info("🔑 OpenAI API 키 확인 완료")

        # 이미지 생성용 프롬프트 선택
        if request.custom_prompt and request.custom_prompt.strip():
            # 커스텀 프롬프트 사용
            image_prompt = request.custom_prompt.strip()
            logger.info(f"🎨 커스텀 프롬프트 사용: {image_prompt[:200]}...")
        else:
            # 기존 텍스트 기반 프롬프트 생성
            image_prompt = create_image_generation_prompt(request.text, request.additional_context)
            logger.info(f"🎯 기본 텍스트 기반 프롬프트: {image_prompt[:200]}...")
        
        # OpenAI DALL-E를 통한 이미지 생성
        client = OpenAI(api_key=OPENAI_API_KEY, timeout=30.0)
        logger.info("🤖 DALL-E API 호출 시작...")
        
        try:
            response = client.images.generate(
                model="dall-e-3",
                prompt=image_prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )
            logger.info("✅ DALL-E API 호출 성공")
        except Exception as dalle_error:
            logger.error(f"💥 DALL-E API 호출 실패: {dalle_error}")
            # 프롬프트 안전화 시도
            if "safety system" in str(dalle_error) or "content_policy_violation" in str(dalle_error):
                logger.info("🛡️ 안전 정책 위반 감지 - 프롬프트 안전화 시도")

                if request.custom_prompt and request.custom_prompt.strip():
                    # 커스텀 프롬프트의 경우 기본 안전한 프롬프트로 대체
                    safe_prompt = "A peaceful and beautiful landscape with soft colors, professional photography style"
                    logger.info(f"🔒 커스텀 프롬프트 안전화: {safe_prompt}")
                else:
                    # 기존 텍스트 기반 안전화
                    safe_prompt = create_safe_image_prompt(request.text, request.additional_context)
                    logger.info(f"🔒 텍스트 기반 안전화: {safe_prompt[:200]}...")
                
                response = client.images.generate(
                    model="dall-e-3",
                    prompt=safe_prompt,
                    size="1024x1024",
                    quality="standard",
                    n=1,
                )
                logger.info("✅ 안전화된 프롬프트로 성공")
            else:
                raise dalle_error
        
        image_url = response.data[0].url
        logger.info(f"🌐 이미지 URL 수신: {image_url}")
        
        # 생성된 이미지 다운로드 및 저장
        import requests
        from datetime import datetime
        
        logger.info("📥 이미지 다운로드 시작...")
        image_response = requests.get(image_url, timeout=30)
        image_response.raise_for_status()
        logger.info(f"📥 이미지 다운로드 완료 ({len(image_response.content)} bytes)")
        
        # Job 폴더 또는 기본 uploads 폴더에 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"generated_single_{timestamp}_{uuid.uuid4().hex[:8]}.png"

        if request.job_id and FOLDER_MANAGER_AVAILABLE:
            # Job 고유 폴더에 저장
            try:
                job_uploads_folder, _ = folder_manager.get_job_folders(request.job_id)
                os.makedirs(job_uploads_folder, exist_ok=True)
                local_path = os.path.join(job_uploads_folder, filename)

                with open(local_path, 'wb') as f:
                    f.write(image_response.content)

                logger.info(f"💾 개별 이미지 job 폴더 저장 완료: {filename}")
                logger.info(f"📂 Job 경로: {local_path}")

                # job_id가 있는 경우 job별 URL 반환
                return {
                    "status": "success",
                    "message": "이미지가 성공적으로 생성되었습니다",
                    "image_url": f"/job-uploads/{request.job_id}/{filename}",
                    "local_path": local_path,
                    "job_id": request.job_id
                }

            except Exception as job_error:
                logger.warning(f"⚠️ Job 폴더 저장 실패, 기본 폴더 사용: {job_error}")
                # Job 폴더 저장 실패 시 기본 폴더로 fallback

        # 기본 uploads 폴더에 저장 (Job ID 없음 또는 Job 폴더 저장 실패)
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        local_path = os.path.join(UPLOAD_FOLDER, filename)

        with open(local_path, 'wb') as f:
            f.write(image_response.content)

        logger.info(f"💾 개별 이미지 기본 폴더 저장 완료: {filename}")
        logger.info(f"📂 로컬 경로: {local_path}")

        return {
            "status": "success",
            "message": "이미지가 성공적으로 생성되었습니다",
            "image_url": f"/uploads/{filename}",
            "local_path": local_path
        }
        
    except HTTPException:
        raise  # HTTPException은 그대로 전파
    except Exception as e:
        logger.error(f"💥 개별 이미지 생성 치명적 오류: {e}")
        logger.error(f"🔍 오류 타입: {type(e).__name__}")
        raise HTTPException(status_code=500, detail=f"이미지 생성 실패: {str(e)}")

def create_image_generation_prompt(text: str, additional_context: Optional[str] = None) -> str:
    """텍스트 기반 이미지 생성 프롬프트 생성"""
    
    # 실사풍 기본 프롬프트 구성
    base_prompt = f"""
Create a photorealistic digital painting with soft, natural lighting and seamless blending based on this Korean text: "{text}"

The image should have:
- No visible outlines or hard edges between objects
- Natural shadows and highlights
- Realistic textures and materials
- Soft gradients and smooth color transitions
- Professional photography-like composition
- Warm, ambient lighting
- High detail and depth
- Suitable for vertical video format (9:16 aspect ratio content)
- Safe for all audiences
"""
    
    # 추가 컨텍스트가 있으면 포함
    if additional_context:
        base_prompt += f"\nAdditional context: \"{additional_context}\""
    
    base_prompt += """

Style: Digital painting, photorealistic, cinematic lighting, professional photography aesthetic
Quality: High resolution, sharp details, realistic depth of field
Mood: Natural, engaging, appropriate for social media
Avoid: Vector graphics, line art, cartoon style, bold outlines, flat colors, text, letters, words, typography, captions, labels, any written content
"""
    
    return base_prompt.strip()

def create_safe_image_prompt(text: str, additional_context: Optional[str] = None) -> str:
    """안전 정책 위반을 피하기 위한 안전화된 프롬프트 생성"""
    
    # 폭력적/위험한 표현들을 안전한 표현으로 대체
    safe_text = text.replace("때리", "터치").replace("때린", "터치").replace("펀치", "움직임")
    safe_text = safe_text.replace("타격", "접촉").replace("공격", "동작").replace("폭발", "반응")
    safe_text = safe_text.replace("충격", "에너지").replace("파괴", "변화").replace("깨", "변형")
    
    if additional_context:
        safe_additional = additional_context.replace("때리", "터치").replace("때린", "터치").replace("펀치", "움직임")
        safe_additional = safe_additional.replace("타격", "접촉").replace("공격", "동작").replace("폭발", "반응")
    else:
        safe_additional = None
    
    # 매우 안전한 프롬프트 구성
    base_prompt = f"""
Create a peaceful, educational illustration about marine life and science based on this Korean text: "{safe_text}"

The image should be:
- Educational and informative
- Bright, colorful, and family-friendly
- Featuring marine creatures in their natural habitat
- Scientific and nature-focused
- Suitable for educational content
- Completely safe for all audiences

Focus on:
- Beautiful ocean scenes
- Colorful marine life
- Scientific concepts visualization
- Peaceful underwater environments
"""
    
    if safe_additional:
        base_prompt += f"\nAdditional educational context: \"{safe_additional}\""
    
    base_prompt += """

Style: Educational illustration, nature documentary style
Quality: High resolution, sharp details
Mood: Peaceful, educational, wonder and discovery
No violence, conflict, or aggressive themes
"""
    
    return base_prompt.strip()

@app.get("/uploads/{filename}")
async def serve_uploaded_file(filename: str):
    """업로드된 파일 제공"""
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")

    return FileResponse(file_path)

@app.get("/job-uploads/{job_id}/{filename}")
async def serve_job_uploaded_file(job_id: str, filename: str):
    """Job별 업로드된 파일 제공"""
    try:
        if not FOLDER_MANAGER_AVAILABLE:
            raise HTTPException(status_code=500, detail="폴더 관리 시스템이 사용 불가능합니다.")

        # Job 폴더 경로 조회
        job_uploads_folder, _ = folder_manager.get_job_folders(job_id)
        file_path = os.path.join(job_uploads_folder, filename)

        if not os.path.exists(file_path):
            logger.warning(f"🔍 Job 파일 없음: {file_path}")
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")

        logger.info(f"📁 Job 파일 제공: {job_id}/{filename}")
        return FileResponse(file_path)

    except Exception as e:
        logger.error(f"❌ Job 파일 제공 실패: {job_id}/{filename} - {e}")
        raise HTTPException(status_code=500, detail="파일 제공 중 오류가 발생했습니다")

@app.get("/bgm-list")
async def get_bgm_list():
    """BGM 폴더 목록 및 각 폴더의 파일 목록 조회"""
    try:
        bgm_data = {}
        valid_moods = ["bright", "calm", "romantic", "sad", "suspense"]
        
        for mood in valid_moods:
            mood_folder = os.path.join(BGM_FOLDER, mood)
            files = []
            
            if os.path.exists(mood_folder):
                # 음악 파일들 검색
                music_patterns = ["*.mp3", "*.wav", "*.m4a"]
                for pattern in music_patterns:
                    found_files = glob.glob(os.path.join(mood_folder, pattern))
                    for file_path in found_files:
                        filename = os.path.basename(file_path)
                        # 파일명에서 아티스트와 제목 분리
                        display_name = filename.replace('.mp3', '').replace('.wav', '').replace('.m4a', '')
                        if ' - ' in display_name:
                            parts = display_name.split(' - ')
                            display_name = parts[0] if len(parts) > 1 else display_name
                        
                        files.append({
                            "filename": filename,
                            "displayName": display_name,
                            "mood": mood,
                            "url": f"/bgm/{mood}/{filename}"
                        })
            
            bgm_data[mood] = {
                "mood": mood,
                "displayName": {
                    "bright": "밝은 음악",
                    "calm": "차분한 음악", 
                    "romantic": "로맨틱한 음악",
                    "sad": "슬픈 음악",
                    "suspense": "긴장감 있는 음악"
                }.get(mood, mood),
                "files": files
            }
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "data": bgm_data
            }
        )
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": str(e)
            }
        )

@app.get("/bgm/{mood}")
async def get_bgm_by_mood(mood: str):
    """특정 성격의 BGM 파일 목록 조회"""
    try:
        if mood not in ["bright", "calm", "romantic", "sad", "suspense"]:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": "Invalid mood. Available moods: bright, calm, romantic, sad, suspense"
                }
            )
        
        mood_folder = os.path.join(BGM_FOLDER, mood)
        files = []
        
        if os.path.exists(mood_folder):
            music_patterns = ["*.mp3", "*.wav", "*.m4a"]
            for pattern in music_patterns:
                found_files = glob.glob(os.path.join(mood_folder, pattern))
                for file_path in found_files:
                    filename = os.path.basename(file_path)
                    display_name = filename.replace('.mp3', '').replace('.wav', '').replace('.m4a', '')
                    if ' - ' in display_name:
                        parts = display_name.split(' - ')
                        display_name = parts[0] if len(parts) > 1 else display_name
                    
                    files.append({
                        "filename": filename,
                        "displayName": display_name,
                        "mood": mood,
                        "url": f"/bgm/{mood}/{filename}"
                    })
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "data": files
            }
        )
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": str(e)
            }
        )

@app.get("/font-list")
async def get_font_list():
    """font 폴더의 폰트 파일 목록 조회"""
    try:
        font_folder = os.path.join(os.path.dirname(__file__), "font")
        fonts = []

        if os.path.exists(font_folder):
            # 폰트 파일 확장자
            font_patterns = ["*.ttf", "*.otf", "*.woff", "*.woff2"]
            for pattern in font_patterns:
                found_files = glob.glob(os.path.join(font_folder, pattern))
                for file_path in found_files:
                    filename = os.path.basename(file_path)
                    # 확장자 제거한 표시 이름
                    display_name = os.path.splitext(filename)[0]

                    # 파일 크기 정보
                    file_size = os.path.getsize(file_path)
                    file_size_mb = round(file_size / (1024 * 1024), 2)

                    fonts.append({
                        "filename": filename,
                        "display_name": display_name,
                        "file_path": filename,  # 상대 경로
                        "size_mb": file_size_mb,
                        "extension": os.path.splitext(filename)[1].lower()
                    })

        # 파일명 순으로 정렬
        fonts.sort(key=lambda x: x['display_name'])

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"{len(fonts)}개의 폰트 파일을 찾았습니다",
                "data": fonts
            }
        )

    except Exception as e:
        logger.error(f"폰트 목록 조회 오류: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": str(e)
            }
        )

@app.get("/bookmark-videos")
async def get_bookmark_videos():
    """북마크 비디오 목록 조회 (최근 등록순, 썸네일 포함)"""
    try:
        videos = []

        if os.path.exists(BOOKMARK_VIDEOS_FOLDER):
            # 썸네일 자동 생성 (누락된 썸네일만)
            if THUMBNAIL_GENERATOR_AVAILABLE:
                try:
                    logger.info("🎬 썸네일 생성 시작...")
                    result = generate_missing_thumbnails(BOOKMARK_VIDEOS_FOLDER)
                    logger.info(f"✅ 썸네일 생성 완료: 새로 생성 {result['generated']}개, 기존 {result['skipped']}개, 실패 {result['errors']}개")
                except Exception as thumbnail_error:
                    logger.warning(f"⚠️ 썸네일 생성 중 오류 발생 (계속 진행): {thumbnail_error}")
            else:
                logger.warning("⚠️ 썸네일 생성기를 사용할 수 없습니다")

            # mp4 파일들만 검색
            video_files = glob.glob(os.path.join(BOOKMARK_VIDEOS_FOLDER, "*.mp4"))

            for video_path in video_files:
                filename = os.path.basename(video_path)

                # 파일 정보
                file_stat = os.stat(video_path)
                file_size = file_stat.st_size
                file_size_mb = round(file_size / (1024 * 1024), 2)
                modified_time = file_stat.st_mtime

                # 썸네일 이미지 찾기 (같은 이름의 .jpg 파일)
                thumbnail_name = filename.replace('.mp4', '.jpg')
                thumbnail_path = os.path.join(BOOKMARK_VIDEOS_FOLDER, thumbnail_name)
                has_thumbnail = os.path.exists(thumbnail_path)

                videos.append({
                    "filename": filename,
                    "display_name": filename.replace('.mp4', ''),
                    "size_mb": file_size_mb,
                    "modified_time": modified_time,
                    "video_url": f"/bookmark-videos/{filename}",
                    "thumbnail_url": f"/bookmark-videos/{thumbnail_name}" if has_thumbnail else None,
                    "has_thumbnail": has_thumbnail
                })

        # 최근 등록순으로 정렬 (modified_time 기준 내림차순)
        videos.sort(key=lambda x: x['modified_time'], reverse=True)

        logger.info(f"✅ 북마크 비디오 목록 조회 완료: {len(videos)}개")

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"{len(videos)}개의 북마크 비디오를 찾았습니다",
                "data": videos
            }
        )

    except Exception as e:
        logger.error(f"❌ 북마크 비디오 목록 조회 오류: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": str(e)
            }
        )

@app.get("/bookmark-videos/{filename}")
async def serve_bookmark_video(filename: str):
    """북마크 비디오 또는 썸네일 파일 제공"""
    try:
        file_path = os.path.join(BOOKMARK_VIDEOS_FOLDER, filename)

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")

        # 파일 확장자에 따라 적절한 미디어 타입 반환
        if filename.endswith('.mp4'):
            media_type = "video/mp4"
        elif filename.endswith('.jpg') or filename.endswith('.jpeg'):
            media_type = "image/jpeg"
        else:
            media_type = "application/octet-stream"

        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=filename
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 북마크 파일 제공 실패: {filename} - {e}")
        raise HTTPException(status_code=500, detail="파일 제공 중 오류가 발생했습니다")

class CopyBookmarkVideoRequest(BaseModel):
    job_id: str
    video_filename: str
    image_index: int

@app.post("/copy-bookmark-video")
async def copy_bookmark_video(request: CopyBookmarkVideoRequest):
    """북마크 비디오를 Job 폴더로 복사하여 사용"""
    try:
        logger.info(f"🎬 북마크 비디오 복사 요청: job_id={request.job_id}, video={request.video_filename}, index={request.image_index}")

        # 1. 원본 비디오 파일 경로 확인
        source_video_path = os.path.join(BOOKMARK_VIDEOS_FOLDER, request.video_filename)

        if not os.path.exists(source_video_path):
            raise HTTPException(status_code=404, detail=f"북마크 비디오를 찾을 수 없습니다: {request.video_filename}")

        # 2. Job 폴더 확인 (없으면 생성)
        if FOLDER_MANAGER_AVAILABLE:
            job_uploads_folder, job_output_folder = folder_manager.get_job_folders(request.job_id)
            if not os.path.exists(job_uploads_folder):
                job_uploads_folder, job_output_folder = folder_manager.create_job_folders(request.job_id)
                logger.info(f"📁 Job 폴더 생성: {job_uploads_folder}")
            uploads_folder = job_uploads_folder
        else:
            # Fallback: 기본 uploads 폴더 사용
            uploads_folder = UPLOAD_FOLDER
            os.makedirs(uploads_folder, exist_ok=True)

        # 3. 대상 파일 경로 설정 (image_index 사용)
        file_extension = os.path.splitext(request.video_filename)[1]
        dest_filename = f"{request.image_index + 1}{file_extension}"
        dest_video_path = os.path.join(uploads_folder, dest_filename)

        # 4. 비디오 파일 복사
        shutil.copy2(source_video_path, dest_video_path)
        logger.info(f"✅ 비디오 파일 복사 완료: {source_video_path} → {dest_video_path}")

        # 5. 파일 URL 반환
        if FOLDER_MANAGER_AVAILABLE:
            file_url = f"/job-uploads/{request.job_id}/{dest_filename}"
        else:
            file_url = f"/uploads/{dest_filename}"

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "북마크 비디오를 성공적으로 복사했습니다",
                "data": {
                    "filename": dest_filename,
                    "file_url": file_url,
                    "image_index": request.image_index
                }
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 북마크 비디오 복사 실패: {e}")
        raise HTTPException(status_code=500, detail=f"비디오 복사 중 오류가 발생했습니다: {str(e)}")

@app.post("/preview-video")
async def preview_video(
    title: str = Form(...),
    body1: str = Form(...),
    text_position: str = Form(default="bottom"),
    text_style: str = Form(default="outline"),
    title_area_mode: str = Form(default="keep"),
    title_font: str = Form(default="BMYEONSUNG_otf.otf"),
    body_font: str = Form(default="BMYEONSUNG_otf.otf"),
    title_font_size: int = Form(default=42),
    body_font_size: int = Form(default=36),
    image_1: Optional[UploadFile] = File(None),
    job_id: Optional[str] = Form(None),  # Job ID 추가
):
    """미리보기 이미지 생성"""
    try:
        logger.info(f"미리보기 요청: {title[:20]}...")

        # VideoGenerator 인스턴스 생성
        video_generator = VideoGenerator()

        # 업로드 폴더 설정 (Job ID에 따라 분기)
        if job_id and FOLDER_MANAGER_AVAILABLE:
            try:
                job_uploads_folder, _ = folder_manager.get_job_folders(job_id)
                uploads_folder = job_uploads_folder
                os.makedirs(uploads_folder, exist_ok=True)
                logger.info(f"🗂️ Job 고유 폴더 사용 (프리뷰): {uploads_folder}")
            except Exception as job_error:
                logger.warning(f"⚠️ Job 폴더 사용 실패, 기본 폴더 사용 (프리뷰): {job_error}")
                uploads_folder = os.path.join(os.path.dirname(__file__), "uploads")
                os.makedirs(uploads_folder, exist_ok=True)
        else:
            uploads_folder = os.path.join(os.path.dirname(__file__), "uploads")
            os.makedirs(uploads_folder, exist_ok=True)

        # 이미지/비디오 파일 처리
        preview_image_path = None
        if image_1 and hasattr(image_1, 'filename') and image_1.filename:
            # 업로드된 파일 저장
            image_filename = f"preview_{int(time.time())}_{image_1.filename}"
            image_save_path = os.path.join(uploads_folder, image_filename)

            with open(image_save_path, "wb") as buffer:
                shutil.copyfileobj(image_1.file, buffer)

            # 비디오 파일인지 확인
            video_extensions = ['.mp4', '.mov', '.avi', '.webm', '.mkv']
            is_video = any(image_1.filename.lower().endswith(ext) for ext in video_extensions)
            
            if is_video:
                # 비디오 파일에서 첫 번째 프레임 추출
                try:
                    from moviepy.editor import VideoFileClip
                    import tempfile
                    
                    # 비디오에서 첫 번째 프레임 추출
                    video_clip = VideoFileClip(image_save_path)
                    frame = video_clip.get_frame(0)  # 첫 번째 프레임 (t=0)
                    video_clip.close()
                    
                    # 프레임을 이미지로 저장
                    from PIL import Image
                    frame_image = Image.fromarray(frame)
                    
                    # 비디오 파일명을 이미지 파일명으로 변경
                    frame_filename = f"preview_{int(time.time())}_frame.png"
                    frame_save_path = os.path.join(uploads_folder, frame_filename)
                    frame_image.save(frame_save_path, "PNG")
                    
                    # 원본 비디오 파일 삭제
                    os.unlink(image_save_path)
                    preview_image_path = frame_save_path
                    
                    logger.info(f"비디오에서 프레임 추출 완료: {frame_filename}")
                    
                except Exception as e:
                    logger.warning(f"비디오 프레임 추출 실패: {e}, 기본 이미지 사용")
                    # 비디오 처리 실패 시 원본 파일 삭제하고 기본 이미지 사용
                    try:
                        os.unlink(image_save_path)
                    except:
                        pass
                    preview_image_path = None
            else:
                # 이미지 파일은 그대로 사용
                preview_image_path = image_save_path
        else:
            # 테스트 이미지 사용
            test_folder = os.path.join(os.path.dirname(__file__), "test")
            test_images = []
            for ext in ["jpg", "jpeg", "png", "webp", "gif", "bmp"]:
                test_files = glob.glob(os.path.join(test_folder, f"1.{ext}"))
                test_images.extend(test_files)

            if test_images:
                preview_image_path = test_images[0]

        if not preview_image_path or not os.path.exists(preview_image_path):
            raise HTTPException(status_code=400, detail="미리보기용 이미지를 찾을 수 없습니다")

        # PIL로 미리보기 이미지 합성
        from PIL import Image

        # 배경 이미지 (504x890)
        final_image = Image.new('RGB', (504, 890), color=(0, 0, 0))

        title_image_path = None

        if title_area_mode == "keep":
            # 기존 방식: 타이틀 영역 + 미디어 영역
            # 타이틀 이미지 생성 (504x220)
            title_image_path = video_generator.create_title_image(
                title,
                504,
                220,
                title_font,
                title_font_size
            )

            # 배경 이미지 처리 (670px 영역)
            if os.path.exists(preview_image_path):
                bg_image = Image.open(preview_image_path)
                work_area_height = 670  # 890 - 220
                bg_image = bg_image.resize((504, work_area_height), Image.Resampling.LANCZOS)
                final_image.paste(bg_image, (0, 220))  # 타이틀 아래에 배치

            # 타이틀 이미지 합성 (상단)
            if os.path.exists(title_image_path):
                title_img = Image.open(title_image_path)
                final_image.paste(title_img, (0, 0))
        else:
            # remove 모드: 전체 화면 미디어
            # 배경 이미지 처리 (전체 890px)
            if os.path.exists(preview_image_path):
                bg_image = Image.open(preview_image_path)
                bg_image = bg_image.resize((504, 890), Image.Resampling.LANCZOS)
                final_image.paste(bg_image, (0, 0))  # 전체 화면

        # 본문 텍스트 이미지 생성 (504x890) - 모든 모드 공통
        body_text_image_path = video_generator.create_text_image(
            body1,
            504,
            890,
            text_position,
            text_style,
            is_title=False,
            title_font=title_font,
            body_font=body_font,
            title_area_mode=title_area_mode,
            title_font_size=title_font_size,
            body_font_size=body_font_size
        )

        # 본문 텍스트 이미지 합성 (오버레이)
        if os.path.exists(body_text_image_path):
            body_img = Image.open(body_text_image_path).convert('RGBA')
            final_image.paste(body_img, (0, 0), body_img)

        # 미리보기 이미지 저장
        preview_filename = f"preview_{int(time.time())}.png"
        preview_save_path = os.path.join(uploads_folder, preview_filename)
        final_image.save(preview_save_path, "PNG")

        # 임시 파일 정리
        for temp_file in [title_image_path, body_text_image_path]:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except:
                    pass

        logger.info(f"미리보기 생성 완료: {preview_filename}")

        # Job ID에 따라 URL 경로 설정
        if job_id and FOLDER_MANAGER_AVAILABLE:
            preview_url = f"/job-uploads/{job_id}/{preview_filename}"
        else:
            preview_url = f"/uploads/{preview_filename}"

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "미리보기 생성 성공",
                "preview_url": preview_url,
                "preview_path": preview_save_path
            }
        )

    except Exception as e:
        logger.error(f"미리보기 생성 오류: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"미리보기 생성 실패: {str(e)}"
            }
        )

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
- 길이: 길이: body1~body7 각 {line_len_min}자 이상, 가능하면 {line_len_max}자 안팎. 제목 {title_len_max}자 이내.
- 구조(7줄): ①후킹(강렬 의문/갈등) → ②상황 → ③감정 → ④규범/공정성 → ⑤갈등 가중 → ⑥자의문 → ⑦양자택일(+댓글 유도 가능).
- 출력은 아래 JSON 스키마만. 여분 텍스트/설명/코드블록 절대 금지.
{{
  "title": "...",
  "body1": "...",
  "body2": "...",
  "body3": "...",
  "body4": "...",
  "body5": "...",
  "body6": "...",
  "body7": "..."
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
            # 여전히 길면 '문장 단위'로 부드럽게 잘라보기
            if len(out) > line_len_max:
                # 마침표/물음표/느낌표 기준으로 가장 가까운 이전 경계로 자르기
                m = re.findall(r'^(.{,' + str(line_len_max) + r'}[.!?])', out)
                if m:
                    out = m[0].strip()
                    break
                # 그래도 없으면 '…' 없이 하드 컷 (말미 구두점 제거)
                out = re.sub(r'[,.…!?]*$', '', out)
                out = out[:line_len_max].rstrip()
                break
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
        for k in ["body1", "body2", "body3", "body4", "body5", "body6", "body7"]:
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
필드는 title, body1~body7 이다. 설명 금지. JSON만 출력.

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
    joined_bodies = " ".join([data.get(k, "") for k in ["body1", "body2", "body3", "body4", "body5", "body6", "body7"]])
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
            joined2 = " ".join([data2.get(k, "") for k in ["body1", "body2", "body3", "body4", "body5", "body6", "body7"]])
            score2 = _preserve_score(content, joined2)
            if score2 >= score:
                data = data2
        except Exception:
            pass

    # ---------- 모델 객체로 반환 (이전과 동일 ReelsContent) ----------
    reels_content = ReelsContent(
        title=data.get("title", ""),
        body1=data.get("body1", ""),
        body2=data.get("body2", ""),
        body3=data.get("body3", ""),
        body4=data.get("body4", ""),
        body5=data.get("body5", ""),
        body6=data.get("body6", ""),
        body7=data.get("body7", "")
    )
    return reels_content


# 공통 프롬프트 빌더 -----------------------------------------------------------
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

# ---------------------------------------------------------------------------
# 1) 병렬(비동기) 생성 함수
# ---------------------------------------------------------------------------
async def generate_images_with_dalle(texts: List[str], job_id: Optional[str] = None) -> List[str]:
    """DALL-E를 사용하여 이미지 생성하고 로컬에 저장 (병렬 처리로 60-80% 성능 향상)"""
    import requests
    import aiohttp
    from openai import OpenAI
    from urllib.parse import urlparse

    # aiohttp 사용 가능 여부 확인
    try:
        _ = aiohttp.__version__
        AIOHTTP_AVAILABLE = True
    except Exception:
        AIOHTTP_AVAILABLE = False

    if not AIOHTTP_AVAILABLE:
        logger.warning("aiohttp가 설치되지 않아 순차 처리로 대체합니다.")
        # 순차 처리 fallback 사용 (job_id 전달)
        return await generate_images_with_dalle_sequential(texts, job_id)

    try:
        if not OPENAI_API_KEY:
            raise ValueError("OpenAI API 키가 설정되지 않았습니다.")

        logger.info(f"🚀 병렬 DALL-E 이미지 생성 시작: {len(texts)}개 (성능 최적화 모드)")

        # OpenAI 클라이언트 초기화
        client = OpenAI(api_key=OPENAI_API_KEY, timeout=60.0)

        # uploads 디렉토리 설정 (Job ID에 따라 분기)
        if job_id and FOLDER_MANAGER_AVAILABLE:
            try:
                job_uploads_folder, _ = folder_manager.get_job_folders(job_id)
                uploads_dir = job_uploads_folder
                os.makedirs(uploads_dir, exist_ok=True)
                logger.info(f"🗂️ Job 고유 폴더 사용: {uploads_dir}")
            except Exception as job_error:
                logger.warning(f"⚠️ Job 폴더 사용 실패, 기본 폴더 사용: {job_error}")
                uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
                os.makedirs(uploads_dir, exist_ok=True)
        else:
            uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
            os.makedirs(uploads_dir, exist_ok=True)

        async def generate_single_image(i: int, text: str) -> str:
            """단일 이미지 생성 함수 (비동기 처리)"""
            try:
                logger.info(f"📸 이미지 {i+1}/{len(texts)} 생성 시작: {text[:30]}...")

                prompt = build_illustration_prompt(text)
                logger.info(f"🎯 이미지 {i+1} DALL-E 프롬프트(요약): {prompt.splitlines()[0]} ...")

                # DALL-E API 호출 (동기 함수를 비동기 래퍼로 처리)
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: client.images.generate(
                        model="dall-e-3",
                        prompt=prompt,
                        size="1024x1024",
                        quality="standard",
                        n=1,
                    ),
                )

                # 이미지 URL 추출
                image_url = response.data[0].url
                logger.info(f"✅ 이미지 {i+1} 생성 완료, 다운로드 중...")

                # 비동기 이미지 다운로드
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                    async with session.get(image_url) as img_response:
                        if img_response.status == 200:
                            filename = f"generated_{uuid.uuid4().hex[:8]}_{i+1}.png"
                            file_path = os.path.join(uploads_dir, filename)
                            with open(file_path, "wb") as f:
                                f.write(await img_response.read())

                            # Job ID에 따라 URL 경로 설정
                            if job_id and FOLDER_MANAGER_AVAILABLE:
                                image_url_path = f"/job-uploads/{job_id}/{filename}"
                            else:
                                image_url_path = f"/get-image/{filename}"

                            logger.info(f"💾 이미지 {i+1} 저장 완료: {filename}")
                            return image_url_path
                        else:
                            logger.error(f"❌ 이미지 {i+1} 다운로드 실패: HTTP {img_response.status}")
                            return ""

            except Exception as e:
                logger.error(f"💥 이미지 {i+1} 처리 실패: {e}")

                # 콘텐츠 필터링 에러인 경우 재시도
                if "content_policy_violation" in str(e).lower():
                    logger.info(f"🔄 이미지 {i+1} 콘텐츠 필터링으로 인한 재시도 중...")
                    try:
                        retry_prompt = build_safe_retry_prompt(text)
                        loop = asyncio.get_event_loop()
                        retry_response = await loop.run_in_executor(
                            None,
                            lambda: client.images.generate(
                                model="dall-e-3",
                                prompt=retry_prompt,
                                size="1024x1024",
                                quality="standard",
                                n=1,
                            ),
                        )

                        retry_image_url = retry_response.data[0].url
                        logger.info(f"🔄 이미지 {i+1} 재시도 성공, 다운로드 중...")

                        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                            async with session.get(retry_image_url) as retry_img_response:
                                if retry_img_response.status == 200:
                                    retry_filename = f"generated_{uuid.uuid4().hex[:8]}_{i+1}_retry.png"
                                    retry_file_path = os.path.join(uploads_dir, retry_filename)
                                    with open(retry_file_path, "wb") as f:
                                        f.write(await retry_img_response.read())

                                    retry_image_url_path = f"/get-image/{retry_filename}"
                                    logger.info(f"💾 이미지 {i+1} 재시도 저장 완료: {retry_filename}")
                                    return retry_image_url_path
                                else:
                                    logger.error(
                                        f"❌ 이미지 {i+1} 재시도 다운로드 실패: HTTP {retry_img_response.status}"
                                    )
                                    return ""
                    except Exception as retry_e:
                        logger.error(f"💥 이미지 {i+1} 재시도 실패: {retry_e}")
                        return ""
                else:
                    return ""

        # 🚀 병렬 처리로 모든 이미지 동시 생성
        logger.info(f"⚡ {len(texts)}개 이미지를 병렬로 처리 시작... (기존 대비 60-80% 시간 단축)")
        # (선택) 레이트리밋 대비 동시성 제한을 걸고 싶으면 아래 세마포어 사용
        # sem = asyncio.Semaphore(5)
        # tasks = [run_with_sem(sem, generate_single_image, i, text) for i, text in enumerate(texts)]
        tasks = [generate_single_image(i, text) for i, text in enumerate(texts)]
        generated_image_paths = await asyncio.gather(*tasks)

        success_count = sum(1 for path in generated_image_paths if path)
        logger.info(f"🎉 병렬 DALL-E 이미지 생성 완료: {success_count}/{len(texts)}개 성공")

        return generated_image_paths

    except Exception as e:
        logger.error(f"DALL-E API 오류: {e}")
        raise ValueError(f"이미지 생성에 실패했습니다: {str(e)}")


# ---------------------------------------------------------------------------
# 2) 순차(동기) 폴백 함수
# ---------------------------------------------------------------------------
async def generate_images_with_dalle_sequential(texts: List[str], job_id: Optional[str] = None) -> List[str]:
    """DALL-E를 사용하여 이미지 생성하고 로컬에 저장 (순차 처리 fallback)"""
    import requests
    from openai import OpenAI
    from urllib.parse import urlparse

    try:
        if not OPENAI_API_KEY:
            raise ValueError("OpenAI API 키가 설정되지 않았습니다.")

        logger.info(f"🔄 순차 DALL-E 이미지 생성 시작: {len(texts)}개 (fallback 모드)")

        # OpenAI 클라이언트 초기화
        client = OpenAI(api_key=OPENAI_API_KEY, timeout=60.0)

        # uploads 디렉토리 설정 (Job ID에 따라 분기)
        if job_id and FOLDER_MANAGER_AVAILABLE:
            try:
                job_uploads_folder, _ = folder_manager.get_job_folders(job_id)
                uploads_dir = job_uploads_folder
                os.makedirs(uploads_dir, exist_ok=True)
                logger.info(f"🗂️ Job 고유 폴더 사용 (순차 처리): {uploads_dir}")
            except Exception as job_error:
                logger.warning(f"⚠️ Job 폴더 사용 실패, 기본 폴더 사용 (순차 처리): {job_error}")
                uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
                os.makedirs(uploads_dir, exist_ok=True)
        else:
            uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
            os.makedirs(uploads_dir, exist_ok=True)

        generated_image_paths: List[str] = []

        for i, text in enumerate(texts):
            try:
                logger.info(f"📸 이미지 {i+1}/{len(texts)} 생성 시작: {text[:30]}...")

                prompt = build_illustration_prompt(text)
                logger.info(f"🎯 이미지 {i+1} DALL-E 프롬프트(요약): {prompt.splitlines()[0]} ...")

                # DALL-E API 호출
                response = client.images.generate(
                    model="dall-e-3",
                    prompt=prompt,
                    size="1024x1024",
                    quality="standard",
                    n=1,
                )

                image_url = response.data[0].url
                logger.info(f"✅ 이미지 {i+1} 생성 완료, 다운로드 중...")

                # 순차 이미지 다운로드 (requests 사용)
                img_response = requests.get(image_url, timeout=30)
                if img_response.status_code == 200:
                    filename = f"generated_{uuid.uuid4().hex[:8]}_{i+1}.png"
                    file_path = os.path.join(uploads_dir, filename)
                    with open(file_path, "wb") as f:
                        f.write(img_response.content)

                    # Job ID에 따라 URL 경로 설정
                    if job_id and FOLDER_MANAGER_AVAILABLE:
                        image_url_path = f"/job-uploads/{job_id}/{filename}"
                    else:
                        image_url_path = f"/get-image/{filename}"

                    logger.info(f"💾 이미지 {i+1} 저장 완료: {filename}")
                    generated_image_paths.append(image_url_path)
                else:
                    logger.error(f"❌ 이미지 {i+1} 다운로드 실패: HTTP {img_response.status_code}")
                    generated_image_paths.append("")

            except Exception as e:
                logger.error(f"💥 이미지 {i+1} 처리 실패: {e}")

                # 콘텐츠 필터링 에러인 경우 재시도(순차)
                if "content_policy_violation" in str(e).lower():
                    try:
                        retry_prompt = build_safe_retry_prompt(text)
                        retry_response = client.images.generate(
                            model="dall-e-3",
                            prompt=retry_prompt,
                            size="1024x1024",
                            quality="standard",
                            n=1,
                        )
                        retry_image_url = retry_response.data[0].url

                        retry_img = requests.get(retry_image_url, timeout=30)
                        if retry_img.status_code == 200:
                            retry_filename = f"generated_{uuid.uuid4().hex[:8]}_{i+1}_retry.png"
                            retry_file_path = os.path.join(uploads_dir, retry_filename)
                            with open(retry_file_path, "wb") as f:
                                f.write(retry_img.content)

                            # Job ID에 따라 URL 경로 설정 (재시도)
                            if job_id and FOLDER_MANAGER_AVAILABLE:
                                retry_image_url_path = f"/job-uploads/{job_id}/{retry_filename}"
                            else:
                                retry_image_url_path = f"/get-image/{retry_filename}"

                            logger.info(f"💾 이미지 {i+1} 재시도 저장 완료: {retry_filename}")
                            generated_image_paths.append(retry_image_url_path)
                        else:
                            logger.error(f"❌ 이미지 {i+1} 재시도 다운로드 실패: HTTP {retry_img.status_code}")
                            generated_image_paths.append("")
                    except Exception as retry_e:
                        logger.error(f"💥 이미지 {i+1} 재시도 실패: {retry_e}")
                        generated_image_paths.append("")
                else:
                    generated_image_paths.append("")

        success_count = sum(1 for path in generated_image_paths if path)
        logger.info(f"🎉 순차 DALL-E 이미지 생성 완료: {success_count}/{len(texts)}개 성공 (fallback 모드)")

        return generated_image_paths

    except Exception as e:
        logger.error(f"순차 DALL-E API 오류: {e}")
        raise ValueError(f"순차 이미지 생성에 실패했습니다: {str(e)}")

@app.post("/generate-images")
async def generate_images(request: ImageGenerateRequest):
    """텍스트 기반 이미지 자동 생성"""
    try:
        logger.info(f"이미지 생성 요청: {len(request.texts)}개 텍스트")
        
        # 텍스트 검증
        if not request.texts or len(request.texts) == 0:
            raise HTTPException(status_code=400, detail="생성할 텍스트가 필요합니다.")
        
        # 모드에 따른 텍스트 처리
        if request.mode == "per_two_scripts":
            # 2개씩 묶어서 처리
            processed_texts = []
            for i in range(0, len(request.texts), 2):
                combined_text = request.texts[i]
                if i + 1 < len(request.texts):
                    combined_text += f" {request.texts[i + 1]}"
                processed_texts.append(combined_text)
        else:
            # 각각 개별 처리
            processed_texts = request.texts
        
        # DALL-E로 이미지 생성 (Job ID 전달)
        try:
            image_urls = await generate_images_with_dalle(processed_texts, request.job_id)
        except ValueError as e:
            raise HTTPException(status_code=500, detail=str(e))
        
        return JSONResponse(
            content={
                "status": "success",
                "message": f"{len([url for url in image_urls if url])}개 이미지가 생성되었습니다.",
                "image_urls": image_urls  # 프론트엔드에서 기대하는 형식
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"이미지 생성 중 예외 발생: {e}")
        raise HTTPException(status_code=500, detail="이미지 생성 중 오류가 발생했습니다.")

@app.get("/get-image/{filename}")
async def get_image(filename: str):
    """생성된 이미지 파일 서빙"""
    try:
        file_path = os.path.join(uploads_dir, filename)
        
        # 파일 존재 여부 확인
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="이미지 파일을 찾을 수 없습니다.")
        
        # 보안을 위해 파일명 검증
        if not filename.startswith("generated_") or not filename.endswith(".png"):
            raise HTTPException(status_code=403, detail="접근이 허용되지 않은 파일입니다.")
        
        return FileResponse(
            path=file_path,
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=3600"}  # 1시간 캐시
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"이미지 파일 서빙 오류: {e}")
        raise HTTPException(status_code=500, detail="이미지 파일을 읽을 수 없습니다.")

@app.get("/download-image/{filename}")
async def download_image(filename: str):
    """생성된 이미지 파일 다운로드 (attachment로)"""
    try:
        file_path = os.path.join(uploads_dir, filename)
        
        # 파일 존재 여부 확인
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="이미지 파일을 찾을 수 없습니다.")
        
        # 보안을 위해 파일명 검증
        if not filename.startswith("generated_") or not filename.endswith(".png"):
            raise HTTPException(status_code=403, detail="접근이 허용되지 않은 파일입니다.")
        
        # 더 친화적인 파일명 생성 (타임스탬프 기반)
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        download_filename = f"reels_image_{timestamp}.png"
        
        return FileResponse(
            path=file_path,
            media_type="image/png",
            filename=download_filename,
            headers={
                "Content-Disposition": f"attachment; filename={download_filename}",
                "Cache-Control": "no-cache"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"이미지 다운로드 오류: {e}")
        raise HTTPException(status_code=500, detail="이미지 다운로드에 실패했습니다.")

@app.post("/extract-reels-from-url")
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

# 배치 작업 관련 API 엔드포인트들
@app.post("/generate-video-async")
async def generate_video_async(
    user_email: str = Form(...),
    content_data: str = Form(...),
    music_mood: str = Form(default="bright"),
    image_allocation_mode: str = Form(default="2_per_image"),
    text_position: str = Form(default="bottom"),
    text_style: str = Form(default="outline"),
    title_area_mode: str = Form(default="keep"),
    selected_bgm_path: str = Form(default=""),
    use_test_files: bool = Form(default=False),
    
    # 폰트 설정 추가
    title_font: str = Form(default="BMYEONSUNG_otf.otf"),  # 타이틀 폰트
    body_font: str = Form(default="BMYEONSUNG_otf.otf"),   # 본문 폰트
    title_font_size: int = Form(default=42),               # 타이틀 폰트 크기 (pt)
    body_font_size: int = Form(default=36),                # 본문 폰트 크기 (pt)

    # 자막 읽어주기 설정
    voice_narration: str = Form(default="enabled"),        # "enabled" (추가) 또는 "disabled" (제거)

    # 크로스 디졸브 설정
    cross_dissolve: str = Form(default="enabled"),          # "enabled" (적용) 또는 "disabled" (미적용)

    # 자막 지속 시간 설정 (초 단위)
    subtitle_duration: float = Form(default=0.0),           # 0: 음성 길이 사용, 0 초과: 지정 시간 사용

    # Job ID (선택적)
    job_id: Optional[str] = Form(None),  # Job ID 추가

    # 이미지 파일 업로드 (최대 8개)
    image_1: Optional[UploadFile] = File(None),
    image_2: Optional[UploadFile] = File(None),
    image_3: Optional[UploadFile] = File(None),
    image_4: Optional[UploadFile] = File(None),
    image_5: Optional[UploadFile] = File(None),
    image_6: Optional[UploadFile] = File(None),
    image_7: Optional[UploadFile] = File(None),
    image_8: Optional[UploadFile] = File(None),
):
    """비동기 영상 생성 요청 - 즉시 Job ID 반환"""
    try:
        if not JOB_QUEUE_AVAILABLE:
            raise HTTPException(
                status_code=500,
                detail="배치 작업 시스템이 사용 불가능합니다. 관리자에게 문의하세요."
            )

        logger.info(f"🚀 비동기 영상 생성 요청: {user_email}")

        # 1. Job ID 처리: 전달받은 job_id 사용 또는 새로 생성
        if job_id:
            logger.info(f"🆔 기존 Job ID 사용: {job_id}")
        else:
            job_id = str(uuid.uuid4())
            logger.info(f"🆔 새 Job ID 생성: {job_id}")

        # 2. Job 폴더 처리: 기존 폴더 사용 또는 새로 생성
        if FOLDER_MANAGER_AVAILABLE:
            try:
                # 기존 job 폴더가 있는지 확인하고 사용
                try:
                    job_uploads_folder, job_output_folder = folder_manager.get_job_folders(job_id)
                    if os.path.exists(job_uploads_folder):
                        uploads_folder_to_use = job_uploads_folder
                        logger.info(f"📁 기존 Job 폴더 사용: {uploads_folder_to_use}")
                    else:
                        # 폴더가 없으면 새로 생성
                        job_uploads_folder, job_output_folder = folder_manager.create_job_folders(job_id)
                        uploads_folder_to_use = job_uploads_folder
                        logger.info(f"📁 새 Job 폴더 생성: {uploads_folder_to_use}")
                except Exception:
                    # get_job_folders 실패 시 새로 생성
                    job_uploads_folder, job_output_folder = folder_manager.create_job_folders(job_id)
                    uploads_folder_to_use = job_uploads_folder
                    logger.info(f"📁 Job 폴더 생성 완료: {uploads_folder_to_use}")
            except Exception as job_error:
                logger.warning(f"⚠️ Job 폴더 생성 실패, 기본 폴더 사용: {job_error}")
                uploads_folder_to_use = UPLOAD_FOLDER
                # 기본 폴더 정리 및 생성
                if os.path.exists(uploads_folder_to_use):
                    shutil.rmtree(uploads_folder_to_use)
                os.makedirs(uploads_folder_to_use, exist_ok=True)
        else:
            # Folder Manager 미사용 시 기본 폴더
            uploads_folder_to_use = UPLOAD_FOLDER
            if os.path.exists(uploads_folder_to_use):
                shutil.rmtree(uploads_folder_to_use)
            os.makedirs(uploads_folder_to_use, exist_ok=True)
            logger.info(f"📁 기본 폴더 사용: {uploads_folder_to_use}")

        # 업로드된 파일들 저장
        uploaded_files = [
            ("image_1", image_1), ("image_2", image_2), ("image_3", image_3), ("image_4", image_4),
            ("image_5", image_5), ("image_6", image_6), ("image_7", image_7), ("image_8", image_8)
        ]

        saved_files = []
        for field_name, uploaded_file in uploaded_files:
            if uploaded_file and uploaded_file.filename:
                # 파일명에서 숫자 추출 (1, 2, 3, 4...)
                file_number = field_name.split('_')[1]
                file_extension = uploaded_file.filename.split('.')[-1].lower()
                save_filename = f"{file_number}.{file_extension}"
                save_path = os.path.join(uploads_folder_to_use, save_filename)

                with open(save_path, "wb") as buffer:
                    shutil.copyfileobj(uploaded_file.file, buffer)

                saved_files.append(save_filename)
                logger.info(f"📁 파일 저장: {save_filename}")

        # 2. 작업 파라미터 구성
        video_params = {
            'content_data': content_data,
            'music_mood': music_mood,
            'image_allocation_mode': image_allocation_mode,
            'text_position': text_position,
            'text_style': text_style,
            'title_area_mode': title_area_mode,
            'selected_bgm_path': selected_bgm_path,
            'use_test_files': use_test_files,
            'uploaded_files': saved_files,
            # 폰트 파라미터 추가
            'title_font': title_font,
            'body_font': body_font,
            'title_font_size': title_font_size,
            'body_font_size': body_font_size,
            # 자막 읽어주기 파라미터 추가
            'voice_narration': voice_narration,
            # 크로스 디졸브 파라미터 추가
            'cross_dissolve': cross_dissolve,
            # 자막 지속 시간 파라미터 추가
            'subtitle_duration': subtitle_duration
        }

        # 3. 작업을 큐에 추가 (미리 생성된 job_id 사용)
        actual_job_id = job_queue.add_job(user_email, video_params, job_id=job_id)

        # 4. Job 로깅 시스템에 로그 생성
        if JOB_LOGGER_AVAILABLE:
            try:
                # JSON 파싱
                reels_content_dict = json.loads(content_data)

                # 먼저 Job 로그 생성 (uploaded_files는 나중에 업데이트)
                job_logger.create_job_log(
                    job_id=job_id,
                    user_email=user_email,
                    reels_content=reels_content_dict,
                    music_mood=music_mood,
                    text_position=text_position,
                    image_allocation_mode=image_allocation_mode,
                    metadata={}  # 일단 빈 metadata로 생성
                )

                # 미디어 파일들을 assets 폴더에 저장하면서 정보 수집
                saved_assets_info = []
                for i, filename in enumerate(saved_files, 1):
                    upload_file_path = os.path.join(UPLOAD_FOLDER, filename)
                    if os.path.exists(upload_file_path):
                        # 파일 타입 확인 (확장자 기반)
                        file_ext = filename.split('.')[-1].lower()
                        video_extensions = ['mp4', 'mov', 'avi', 'webm']
                        file_type = 'video' if file_ext in video_extensions else 'image'

                        # assets 폴더에 저장
                        asset_path = job_logger.save_media_file(
                            job_id=job_id,
                            original_file_path=upload_file_path,
                            original_filename=filename,
                            file_type=file_type,
                            sequence_number=i
                        )

                        # assets 정보 수집
                        saved_assets_info.append({
                            'sequence': i,
                            'original_filename': filename,
                            'asset_path': asset_path,
                            'file_type': file_type,
                            'file_size': os.path.getsize(asset_path) if os.path.exists(asset_path) else 0
                        })

                # metadata에 assets 정보와 기타 설정 포함
                metadata = {
                    'uploaded_files': saved_assets_info,  # assets 저장 후 정보
                    'title_font': title_font,
                    'body_font': body_font,
                    'voice_narration': voice_narration,
                    'title_area_mode': title_area_mode
                }

                # metadata 업데이트
                job_logger.update_job_metadata(job_id, metadata)

                logger.info(f"✅ Job 로깅 시스템에 기록 완료: {job_id}")
            except Exception as log_error:
                logger.error(f"⚠️ Job 로깅 실패 (작업은 계속 진행): {log_error}")

        logger.info(f"✅ 작업 큐에 추가 완료: {job_id}")

        return JSONResponse(
            content={
                "status": "success",
                "message": "영상 생성 작업이 시작되었습니다. 완료되면 이메일로 알려드립니다.",
                "job_id": job_id,
                "user_email": user_email,
                "estimated_time": "약 3-10분"
            }
        )

    except Exception as e:
        logger.error(f"❌ 비동기 영상 생성 요청 실패: {e}")
        raise HTTPException(status_code=500, detail=f"작업 요청 실패: {str(e)}")

@app.get("/job-status/{job_id}")
async def get_job_status(job_id: str):
    """작업 상태 조회"""
    try:
        if not JOB_QUEUE_AVAILABLE:
            raise HTTPException(status_code=500, detail="배치 작업 시스템이 사용 불가능합니다.")

        job_data = job_queue.get_job(job_id)
        if not job_data:
            raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")

        # Job 로깅 정보도 함께 반환
        response_data = {
            "job_id": job_data['job_id'],
            "status": job_data['status'],
            "created_at": job_data['created_at'],
            "updated_at": job_data['updated_at'],
            "result": job_data.get('result'),
            "error_message": job_data.get('error_message')
        }

        # 로깅 시스템에서 추가 정보 조회 (가능한 경우)
        if JOB_LOGGER_AVAILABLE:
            try:
                job_log_info = job_logger.get_job_info(job_id)
                if job_log_info:
                    response_data["detailed_info"] = {
                        "media_files": job_log_info.get('media_files', []),
                        "reels_content": job_log_info.get('reels_content', {}),
                        "metadata": job_log_info.get('metadata', {})
                    }
            except Exception as log_error:
                logger.warning(f"Job 로깅 정보 조회 실패: {log_error}")

        return JobStatusResponse(**response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 작업 상태 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="작업 상태 조회 중 오류가 발생했습니다.")

@app.get("/download-video")
async def download_video(token: str = Query(...)):
    """보안 다운로드 링크를 통한 영상 다운로드"""
    try:
        logger.info(f"📥 다운로드 요청 시작 (기존 엔드포인트): token={token[:20]}...")

        if not JOB_QUEUE_AVAILABLE:
            logger.error("❌ 배치 작업 시스템 사용 불가")
            raise HTTPException(status_code=500, detail="배치 작업 시스템이 사용 불가능합니다.")

        # 토큰 검증
        logger.info("🔐 토큰 검증 시작")
        payload = email_service.verify_download_token(token)
        if not payload:
            logger.error("❌ 토큰 검증 실패")
            raise HTTPException(status_code=401, detail="유효하지 않거나 만료된 다운로드 링크입니다.")

        video_path = payload.get('video_path')
        user_email = payload.get('user_email')
        logger.info(f"✅ 토큰 검증 성공: user={user_email}, video_path={video_path}")

        # 파일 경로 처리 개선
        if os.path.isabs(video_path):
            # 절대 경로인 경우 그대로 사용
            full_video_path = video_path
            logger.info(f"📁 절대 경로 사용: {full_video_path}")
        else:
            # 상대 경로인 경우 OUTPUT_FOLDER와 결합
            full_video_path = os.path.join(OUTPUT_FOLDER, video_path)
            logger.info(f"📁 상대 경로 결합: {OUTPUT_FOLDER} + {video_path} = {full_video_path}")

        # 파일 존재 확인
        if not os.path.exists(full_video_path):
            logger.error(f"❌ 영상 파일 없음: {full_video_path}")
            # 대체 경로들 시도
            basename = os.path.basename(video_path)
            alternative_path = os.path.join(OUTPUT_FOLDER, basename)
            logger.info(f"🔍 대체 경로 확인: {alternative_path}")

            if os.path.exists(alternative_path):
                full_video_path = alternative_path
                logger.info(f"✅ 대체 경로에서 파일 발견: {full_video_path}")
            else:
                # 출력 폴더의 모든 파일 나열
                try:
                    files_in_output = os.listdir(OUTPUT_FOLDER) if os.path.exists(OUTPUT_FOLDER) else []
                    logger.error(f"❌ OUTPUT_FOLDER 내용: {files_in_output}")
                except Exception as list_error:
                    logger.error(f"❌ OUTPUT_FOLDER 접근 실패: {list_error}")
                raise HTTPException(status_code=404, detail="영상 파일을 찾을 수 없습니다.")

        file_size = os.path.getsize(full_video_path)
        logger.info(f"📥 영상 다운로드 시작: {user_email} → {os.path.basename(video_path)} ({file_size} bytes)")

        # 파일 다운로드 응답
        return FileResponse(
            path=full_video_path,
            filename=os.path.basename(video_path),
            media_type='video/mp4'
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 영상 다운로드 실패: {e}")
        raise HTTPException(status_code=500, detail="영상 다운로드 중 오류가 발생했습니다.")

@app.get("/api/download-video")
async def api_download_video(token: str = Query(...)):
    """보안 다운로드 링크를 통한 영상 다운로드 (nginx 라우팅용 /api 경로)"""
    try:
        logger.info(f"📥 다운로드 요청 시작: token={token[:20]}...")

        if not JOB_QUEUE_AVAILABLE:
            logger.error("❌ 배치 작업 시스템 사용 불가")
            raise HTTPException(status_code=500, detail="배치 작업 시스템이 사용 불가능합니다.")

        # 토큰 검증
        logger.info("🔐 토큰 검증 시작")
        payload = email_service.verify_download_token(token)
        if not payload:
            logger.error("❌ 토큰 검증 실패")
            raise HTTPException(status_code=401, detail="유효하지 않거나 만료된 다운로드 링크입니다.")

        video_path = payload.get('video_path')
        user_email = payload.get('user_email')
        logger.info(f"✅ 토큰 검증 성공: user={user_email}, video_path={video_path}")

        # 파일 경로 처리 개선
        if os.path.isabs(video_path):
            # 절대 경로인 경우 그대로 사용
            full_video_path = video_path
            logger.info(f"📁 절대 경로 사용: {full_video_path}")
        else:
            # 상대 경로인 경우 OUTPUT_FOLDER와 결합
            full_video_path = os.path.join(OUTPUT_FOLDER, video_path)
            logger.info(f"📁 상대 경로 결합: {OUTPUT_FOLDER} + {video_path} = {full_video_path}")

        # 파일 존재 확인
        if not os.path.exists(full_video_path):
            logger.error(f"❌ 영상 파일 없음: {full_video_path}")
            # 대체 경로들 시도
            basename = os.path.basename(video_path)
            alternative_path = os.path.join(OUTPUT_FOLDER, basename)
            logger.info(f"🔍 대체 경로 확인: {alternative_path}")

            if os.path.exists(alternative_path):
                full_video_path = alternative_path
                logger.info(f"✅ 대체 경로에서 파일 발견: {full_video_path}")
            else:
                # 출력 폴더의 모든 파일 나열
                try:
                    files_in_output = os.listdir(OUTPUT_FOLDER) if os.path.exists(OUTPUT_FOLDER) else []
                    logger.error(f"❌ OUTPUT_FOLDER 내용: {files_in_output}")
                except Exception as list_error:
                    logger.error(f"❌ OUTPUT_FOLDER 접근 실패: {list_error}")
                raise HTTPException(status_code=404, detail="영상 파일을 찾을 수 없습니다.")

        file_size = os.path.getsize(full_video_path)
        logger.info(f"📥 영상 다운로드 시작: {user_email} → {os.path.basename(video_path)} ({file_size} bytes)")

        # 파일 다운로드 응답
        return FileResponse(
            path=full_video_path,
            filename=os.path.basename(video_path),
            media_type='video/mp4'
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 영상 다운로드 실패: {e}")
        raise HTTPException(status_code=500, detail="영상 다운로드 중 오류가 발생했습니다.")

@app.get("/api/test")
async def api_test():
    """nginx /api 라우팅 테스트용 엔드포인트"""
    return {
        "status": "success",
        "message": "nginx /api 라우팅이 정상 작동합니다",
        "timestamp": datetime.now().isoformat(),
        "endpoint": "/api/test"
    }

@app.get("/queue-stats")
async def get_queue_stats():
    """작업 큐 통계 조회 (관리용)"""
    try:
        if not JOB_QUEUE_AVAILABLE:
            raise HTTPException(status_code=500, detail="배치 작업 시스템이 사용 불가능합니다.")

        stats = job_queue.get_job_stats()
        return {"status": "success", "stats": stats}

    except Exception as e:
        logger.error(f"❌ 큐 통계 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="큐 통계 조회 중 오류가 발생했습니다.")

# Job 로깅 시스템 API 엔드포인트들
@app.get("/job-logs/{job_id}")
async def get_job_logs(job_id: str):
    """특정 Job의 상세 로그 조회"""
    try:
        if not JOB_LOGGER_AVAILABLE:
            raise HTTPException(status_code=500, detail="Job 로깅 시스템이 사용 불가능합니다.")

        job_info = job_logger.get_job_info(job_id)
        if not job_info:
            raise HTTPException(status_code=404, detail="Job 로그를 찾을 수 없습니다.")

        return {"status": "success", "job_info": job_info}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Job 로그 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="Job 로그 조회 중 오류가 발생했습니다.")

@app.get("/user-jobs/{user_email}")
async def get_user_jobs(user_email: str, limit: int = 20):
    """사용자별 Job 로그 목록 조회"""
    try:
        if not JOB_LOGGER_AVAILABLE:
            raise HTTPException(status_code=500, detail="Job 로깅 시스템이 사용 불가능합니다.")

        jobs = job_logger.get_user_jobs(user_email, limit)
        return {"status": "success", "jobs": jobs, "total": len(jobs)}

    except Exception as e:
        logger.error(f"❌ 사용자 Job 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="사용자 Job 목록 조회 중 오류가 발생했습니다.")

@app.get("/job-statistics")
async def get_job_statistics():
    """Job 로그 통계 정보 조회 (관리용)"""
    try:
        if not JOB_LOGGER_AVAILABLE:
            raise HTTPException(status_code=500, detail="Job 로깅 시스템이 사용 불가능합니다.")

        stats = job_logger.get_job_statistics()
        return {"status": "success", "statistics": stats}

    except Exception as e:
        logger.error(f"❌ Job 통계 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="Job 통계 조회 중 오류가 발생했습니다.")

# Job 폴더 관리 API 엔드포인트들
@app.post("/create-job-folder")
async def create_job_folder(request: CreateJobFolderRequest):
    """Job별 격리된 폴더 생성"""
    try:
        if not FOLDER_MANAGER_AVAILABLE:
            raise HTTPException(status_code=500, detail="폴더 관리 시스템이 사용 불가능합니다.")

        logger.info(f"🚀 Job 폴더 생성 요청: {request.job_id}")

        # Job 폴더 생성
        uploads_folder, output_folder = folder_manager.create_job_folders(request.job_id)

        logger.info(f"✅ Job 폴더 생성 완료: {request.job_id}")
        logger.info(f"   📁 uploads: {uploads_folder}")
        logger.info(f"   📁 output: {output_folder}")

        return CreateJobFolderResponse(
            status="success",
            message="Job 폴더가 성공적으로 생성되었습니다.",
            job_id=request.job_id,
            uploads_folder=uploads_folder,
            output_folder=output_folder
        )

    except Exception as e:
        logger.error(f"❌ Job 폴더 생성 실패: {request.job_id} - {e}")
        raise HTTPException(status_code=500, detail=f"Job 폴더 생성 실패: {str(e)}")

@app.post("/cleanup-job-folder")
async def cleanup_job_folder(request: CleanupJobFolderRequest):
    """Job 완료 후 임시 폴더 정리"""
    try:
        if not FOLDER_MANAGER_AVAILABLE:
            raise HTTPException(status_code=500, detail="폴더 관리 시스템이 사용 불가능합니다.")

        logger.info(f"🗑️ Job 폴더 정리 요청: {request.job_id} (keep_output: {request.keep_output})")

        # Job 폴더 정리
        cleaned = folder_manager.cleanup_job_folders(request.job_id, request.keep_output)

        if cleaned:
            logger.info(f"✅ Job 폴더 정리 완료: {request.job_id}")
            return CleanupJobFolderResponse(
                status="success",
                message="Job 폴더가 성공적으로 정리되었습니다.",
                job_id=request.job_id,
                cleaned=True
            )
        else:
            logger.warning(f"⚠️ Job 폴더 정리 부분 실패: {request.job_id}")
            return CleanupJobFolderResponse(
                status="warning",
                message="Job 폴더 정리가 부분적으로만 완료되었습니다.",
                job_id=request.job_id,
                cleaned=False
            )

    except Exception as e:
        logger.error(f"❌ Job 폴더 정리 실패: {request.job_id} - {e}")
        raise HTTPException(status_code=500, detail=f"Job 폴더 정리 실패: {str(e)}")

# 정적 파일 서빙
app.mount("/bgm", StaticFiles(directory=BGM_FOLDER), name="bgm")
app.mount("/videos", StaticFiles(directory=OUTPUT_FOLDER), name="videos")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)