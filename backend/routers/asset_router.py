"""
자산 관리 라우터
BGM, 폰트 등 미디어 자산 관련 API
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from utils.logger_config import get_logger
import os
import glob

router = APIRouter(tags=["asset"])
logger = get_logger('asset_router')

# 전역 변수 (main.py에서 설정)
BGM_FOLDER = "bgm"


def set_dependencies(bgm_folder):
    """main.py에서 호출하여 폴더 경로 설정"""
    global BGM_FOLDER
    BGM_FOLDER = bgm_folder


@router.get("/bgm-list")
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


@router.get("/bgm/{mood}")
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


@router.get("/font-list")
async def get_font_list():
    """font 폴더의 폰트 파일 목록 조회"""
    try:
        font_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), "font")
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
