"""
시스템 관리 라우터
상태 확인, 테스트 등 시스템 관련 API
"""

from fastapi import APIRouter
from datetime import datetime

router = APIRouter(tags=["system"])

# main.py에서 가져올 전역 변수들 (나중에 main.py에서 import)
OPENAI_AVAILABLE = True
YOUTUBE_TRANSCRIPT_AVAILABLE = True
AIOHTTP_AVAILABLE = True
JOB_QUEUE_AVAILABLE = True


@router.get("/")
async def root():
    """루트 엔드포인트"""
    return {"message": "Reels Video Generator API"}


@router.get("/status")
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


@router.get("/youtube-test-videos")
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


@router.get("/api/test")
async def api_test():
    """nginx /api 라우팅 테스트용 엔드포인트"""
    return {
        "status": "success",
        "message": "nginx /api 라우팅이 정상 작동합니다",
        "timestamp": datetime.now().isoformat(),
        "endpoint": "/api/test"
    }


def set_availability_flags(openai_avail, youtube_avail, aiohttp_avail, job_queue_avail):
    """main.py에서 호출하여 가용성 플래그 설정"""
    global OPENAI_AVAILABLE, YOUTUBE_TRANSCRIPT_AVAILABLE, AIOHTTP_AVAILABLE, JOB_QUEUE_AVAILABLE
    OPENAI_AVAILABLE = openai_avail
    YOUTUBE_TRANSCRIPT_AVAILABLE = youtube_avail
    AIOHTTP_AVAILABLE = aiohttp_avail
    JOB_QUEUE_AVAILABLE = job_queue_avail
