from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import Optional, List
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
import json
import os
import requests
import shutil
from urllib.parse import urlparse
from video_generator import VideoGenerator
import random
import glob
import re
from bs4 import BeautifulSoup
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError as e:
    print(f"OpenAI import 오류: {e}")
    OpenAI = None
    OPENAI_AVAILABLE = False
import logging
from dotenv import load_dotenv
# Updated with create_simple_group_clip method

# .env 파일 로드
load_dotenv()

app = FastAPI(title="Reels Video Generator", version="1.0.0")

# Pydantic 모델 정의
class URLExtractRequest(BaseModel):
    url: str

class ReelsContent(BaseModel):
    title: str
    body1: str = ""
    body2: str = ""
    body3: str = ""
    body4: str = ""
    body5: str = ""
    body6: str = ""
    body7: str = ""

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OpenAI import 상태 로깅
if OPENAI_AVAILABLE:
    logger.info("OpenAI 라이브러리 import 성공")
else:
    logger.error("OpenAI 라이브러리 import 실패")

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

# 폴더 생성
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(BGM_FOLDER, exist_ok=True)

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
        media_extensions = ["jpg", "jpeg", "png", "bmp", "gif", "webp", "mp4", "mov", "avi", "webm"]
        
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
                file_type = "비디오" if original_ext.lower() in ['.mp4', '.mov', '.avi', '.webm'] else "이미지"
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
    text_position: str = Form(default="bottom"),  # "top", "middle", "bottom"
    
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
    use_test_files: bool = Form(default=False)  # test 폴더 사용 여부
):
    try:
        print("🚀 웹서비스 API 호출 시작")
        
        # 1. uploads 폴더 준비 및 정리
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
        
        # 이미지 할당 모드 검증
        if image_allocation_mode not in ["2_per_image", "1_per_image"]:
            image_allocation_mode = "2_per_image"  # 기본값
            print(f"⚠️ 잘못된 이미지 할당 모드, 기본값 사용: {image_allocation_mode}")
        
        # 텍스트 위치 검증
        if text_position not in ["top", "middle", "bottom"]:
            text_position = "bottom"  # 기본값
            print(f"⚠️ 잘못된 텍스트 위치, 기본값 사용: {text_position}")
        
        print(f"🖼️ 이미지 할당 모드: {image_allocation_mode}")
        print(f"📝 텍스트 위치: {text_position}")
        
        output_path = video_gen.create_video_from_uploads(OUTPUT_FOLDER, bgm_file, image_allocation_mode, text_position)
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Video generated successfully",
                "video_path": output_path
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

def scrape_website_content(url: str) -> str:
    """웹사이트에서 텍스트 내용을 스크래핑"""
    try:
        # 웹페이지 요청
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        logger.info(f"웹페이지 스크래핑 시작: {url}")
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
        
        # 텍스트 정제
        text_content = re.sub(r'\s+', ' ', text_content).strip()
        
        # 너무 짧은 경우 에러
        if len(text_content) < 100:
            raise ValueError("추출된 텍스트가 너무 짧습니다. 다른 URL을 시도해보세요.")
        
        # 너무 긴 경우 앞부분만 사용 (ChatGPT 토큰 제한 고려)
        if len(text_content) > 8000:
            text_content = text_content[:8000] + "..."
        
        logger.info(f"텍스트 추출 완료: {len(text_content)}자")
        return text_content
        
    except requests.exceptions.RequestException as e:
        logger.error(f"웹페이지 요청 실패: {e}")
        raise ValueError(f"웹페이지에 접근할 수 없습니다: {str(e)}")
    except Exception as e:
        logger.error(f"스크래핑 오류: {e}")
        raise ValueError(f"웹페이지 내용을 추출할 수 없습니다: {str(e)}")

async def generate_reels_with_chatgpt(content: str) -> ReelsContent:
    """ChatGPT를 사용하여 릴스 대본 생성"""
    try:
        if not OPENAI_API_KEY:
            raise ValueError("OpenAI API 키가 설정되지 않았습니다.")
        
        logger.info("ChatGPT API 호출 시작")
        
        prompt = f"""
다음 웹페이지 내용을 분석하여 메뉴/광고들을 제외하고 콘텐츠를 추출하여, 흥미롭고 매력적인 릴스(Reels) 대본을 작성해주세요.

웹페이지 내용:
{content}

요구사항:
1. 첫 3초가 중요하므로 해당 콘텐츠의 핵심에 해당하는 내용으로 강력하고 궁금한 물음으로 시작해줘.(예. 냉장고를 열어 에어컨을 대신할 수 있을까?) 
2. 그리고, 그러한 상황의 원인, 그리고 마지막으로 해결이나 결말을 유도해줘. 마지막 라인은 두가지 선택지 중 너는 어떤 선택을 할지 물어봐줘.
   (예. 너라면 짧은 바지를 입고 잔다, 안 입고 잔다. 어떤 선택을 할래?)
3. 이모지는 사용하지 말 것. 내용을 충실히 전달할 것. 처음부터 끝까지 친근한 반말을 쓸 것.
4. 최대 7개의 대사로 구성 (body1~body7) body는 너무 짧지 않게 20자 내외로 구성해 줘. 
5. 제목은 클릭을 유도하는 매력적인 문구로 작성 (15자 이내)
6. 한국어로 작성하고, 문장의 흐름 자체가 논리적이고 자연스러워야 해. 재미는 항상 기본이야. 잊지마.

다음 JSON 형식으로만 응답해주세요 (다른 텍스트 없이):
{{
  "title": "매력적인 제목",
  "body1": "첫 번째 대사",
  "body2": "두 번째 대사",
  "body3": "세 번째 대사",
  "body4": "네 번째 대사",
  "body5": "다섯 번째 대사",
  "body6": "여섯 번째 대사",
  "body7": "일곱 번째 대사"
}}
"""
        
        # OpenAI API 호출
        if not OpenAI:
            raise HTTPException(status_code=500, detail="OpenAI 라이브러리를 import할 수 없습니다")
        
        if not OPENAI_API_KEY:
            raise HTTPException(status_code=500, detail="OpenAI API 키가 설정되지 않았습니다")
            
        logger.info("OpenAI 클라이언트 초기화 시작")
        try:
            # 기본 설정으로 클라이언트 생성 (proxy 관련 설정 제외)
            import os
            os.environ.pop('HTTP_PROXY', None)
            os.environ.pop('HTTPS_PROXY', None)
            client = OpenAI(
                api_key=OPENAI_API_KEY,
                timeout=30.0
            )
            logger.info("OpenAI 클라이언트 초기화 성공")
        except Exception as e:
            logger.error(f"OpenAI 클라이언트 초기화 오류: {e}")
            import traceback
            logger.error(f"상세 오류: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"OpenAI 클라이언트 초기화 실패: {str(e)}")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "당신은 릴스(Reels) 콘텐츠 제작 전문가입니다. 웹 콘텐츠를 분석하여 매력적이고 바이럴될 가능성이 높은 릴스 대본을 작성해주세요."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.8
        )
        
        # 응답에서 JSON 추출
        gpt_response = response.choices[0].message.content.strip()
        logger.info(f"ChatGPT 응답: {gpt_response}")
        
        # JSON 파싱
        try:
            # JSON만 추출 (마크다운 코드블록 제거)
            json_match = re.search(r'\{.*\}', gpt_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                reels_data = json.loads(json_str)
            else:
                reels_data = json.loads(gpt_response)
            
            # ReelsContent 객체로 변환
            reels_content = ReelsContent(
                title=reels_data.get("title", ""),
                body1=reels_data.get("body1", ""),
                body2=reels_data.get("body2", ""),
                body3=reels_data.get("body3", ""),
                body4=reels_data.get("body4", ""),
                body5=reels_data.get("body5", ""),
                body6=reels_data.get("body6", ""),
                body7=reels_data.get("body7", "")
            )
            
            logger.info("릴스 대본 생성 완료")
            return reels_content
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 실패: {e}")
            raise ValueError("AI 응답을 해석할 수 없습니다. 다시 시도해주세요.")
            
    except Exception as e:
        logger.error(f"ChatGPT API 오류: {e}")
        raise ValueError(f"AI 대본 생성에 실패했습니다: {str(e)}")

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
        
        # 웹사이트 스크래핑
        try:
            scraped_content = scrape_website_content(request.url)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        # ChatGPT로 릴스 대본 생성
        try:
            reels_content = await generate_reels_with_chatgpt(scraped_content)
        except ValueError as e:
            raise HTTPException(status_code=500, detail=str(e))
        
        return JSONResponse(
            content={
                "status": "success",
                "message": "릴스 대본이 성공적으로 생성되었습니다.",
                "reels_content": reels_content.dict()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"릴스 추출 중 예외 발생: {e}")
        raise HTTPException(status_code=500, detail="릴스 대본 추출 중 오류가 발생했습니다.")

# 정적 파일 서빙
app.mount("/bgm", StaticFiles(directory=BGM_FOLDER), name="bgm")
app.mount("/videos", StaticFiles(directory=OUTPUT_FOLDER), name="videos")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)