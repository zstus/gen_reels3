"""
다운로드 관리 라우터
보안 비디오 다운로드 API
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from utils.logger_config import get_logger
import os

router = APIRouter(tags=["download"])
logger = get_logger('download_router')

# 전역 변수 (main.py에서 설정)
email_service = None
JOB_QUEUE_AVAILABLE = False
OUTPUT_FOLDER = "output_videos"


def set_dependencies(es, jq_avail, output_folder):
    """main.py에서 호출하여 의존성 설정"""
    global email_service, JOB_QUEUE_AVAILABLE, OUTPUT_FOLDER
    email_service = es
    JOB_QUEUE_AVAILABLE = jq_avail
    OUTPUT_FOLDER = output_folder


@router.get("/download-video")
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


@router.get("/api/download-video")
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
