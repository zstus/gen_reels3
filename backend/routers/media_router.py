"""
미디어 파일 관리 라우터
업로드 파일, Job별 파일, 북마크 비디오 관련 API
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from utils.logger_config import get_logger
from models.request_models import CopyBookmarkVideoRequest
import os
import glob
from moviepy.editor import VideoFileClip

router = APIRouter(tags=["media"])
logger = get_logger('media_router')

# 전역 변수 (main.py에서 설정)
folder_manager = None
FOLDER_MANAGER_AVAILABLE = False
BOOKMARK_VIDEOS_FOLDER = "assets/videos/bookmark"
UPLOAD_FOLDER = "uploads"


def set_dependencies(fm, fm_avail, bookmark_folder, upload_folder):
    """main.py에서 호출하여 의존성 설정"""
    global folder_manager, FOLDER_MANAGER_AVAILABLE
    global BOOKMARK_VIDEOS_FOLDER, UPLOAD_FOLDER
    folder_manager = fm
    FOLDER_MANAGER_AVAILABLE = fm_avail
    BOOKMARK_VIDEOS_FOLDER = bookmark_folder
    UPLOAD_FOLDER = upload_folder


@router.get("/uploads/{filename}")
async def serve_uploaded_file(filename: str):
    """업로드된 파일 제공"""
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")

    return FileResponse(file_path)


@router.get("/job-uploads/{job_id}/{filename}")
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


@router.get("/bookmark-videos")
async def get_bookmark_videos():
    """북마크 비디오 목록 조회 (썸네일 자동 생성)"""
    try:
        videos = []

        if not os.path.exists(BOOKMARK_VIDEOS_FOLDER):
            logger.warning(f"북마크 비디오 폴더 없음: {BOOKMARK_VIDEOS_FOLDER}")
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": "북마크 비디오 폴더가 비어있습니다",
                    "data": []
                }
            )

        # 비디오 파일 검색 (.mp4, .mov, .avi, .webm)
        video_patterns = ["*.mp4", "*.mov", "*.avi", "*.webm"]

        for pattern in video_patterns:
            found_files = glob.glob(os.path.join(BOOKMARK_VIDEOS_FOLDER, pattern))
            for video_path in found_files:
                filename = os.path.basename(video_path)
                display_name = os.path.splitext(filename)[0]

                # 썸네일 확인 (실시간 생성 제거 - 사전 생성된 썸네일만 사용)
                thumbnail_filename_webp = f"{display_name}_thumb.webp"
                thumbnail_filename_jpg = f"{display_name}_thumb.jpg"
                thumbnail_path_webp = os.path.join(BOOKMARK_VIDEOS_FOLDER, thumbnail_filename_webp)
                thumbnail_path_jpg = os.path.join(BOOKMARK_VIDEOS_FOLDER, thumbnail_filename_jpg)

                # WebP 썸네일 우선 사용, 없으면 JPG
                thumbnail_filename = None
                if os.path.exists(thumbnail_path_webp):
                    thumbnail_filename = thumbnail_filename_webp
                elif os.path.exists(thumbnail_path_jpg):
                    thumbnail_filename = thumbnail_filename_jpg
                # 썸네일이 없으면 None 반환 (실시간 생성하지 않음)

                # 파일 크기 정보
                file_size = os.path.getsize(video_path)
                file_size_mb = round(file_size / (1024 * 1024), 2)

                # 파일 수정 시간
                modified_time = os.path.getmtime(video_path)

                # 비디오 정보 (길이 등)
                try:
                    video_clip = VideoFileClip(video_path)
                    duration = video_clip.duration
                    video_clip.close()
                except:
                    duration = 0

                videos.append({
                    "filename": filename,
                    "display_name": display_name,
                    "video_url": f"/bookmark-videos/{filename}",
                    "thumbnail_url": f"/bookmark-videos/{thumbnail_filename}" if thumbnail_filename else None,
                    "has_thumbnail": thumbnail_filename is not None,
                    "size_mb": file_size_mb,
                    "modified_time": modified_time,
                    "duration": round(duration, 1),
                    "extension": os.path.splitext(filename)[1].lower()
                })

        # 파일명 순으로 정렬
        videos.sort(key=lambda x: x['display_name'])

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"{len(videos)}개의 북마크 비디오를 찾았습니다",
                "data": videos
            }
        )

    except Exception as e:
        logger.error(f"북마크 비디오 목록 조회 오류: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": str(e)
            }
        )


@router.get("/bookmark-videos/{filename}")
async def serve_bookmark_video(filename: str):
    """북마크 비디오 또는 썸네일 파일 제공"""
    file_path = os.path.join(BOOKMARK_VIDEOS_FOLDER, filename)

    if not os.path.exists(file_path):
        logger.warning(f"북마크 파일 없음: {filename}")
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")

    return FileResponse(file_path)


@router.post("/copy-bookmark-video")
async def copy_bookmark_video(request: CopyBookmarkVideoRequest):
    """북마크 비디오를 Job 폴더로 복사"""
    try:
        if not FOLDER_MANAGER_AVAILABLE:
            raise HTTPException(status_code=500, detail="폴더 관리 시스템이 사용 불가능합니다.")

        logger.info(f"📋 북마크 비디오 복사 요청: {request.video_filename} → {request.job_id}")

        # 원본 파일 경로
        source_path = os.path.join(BOOKMARK_VIDEOS_FOLDER, request.video_filename)
        if not os.path.exists(source_path):
            raise HTTPException(status_code=404, detail="북마크 비디오를 찾을 수 없습니다")

        # Job 폴더 경로
        job_uploads_folder, _ = folder_manager.get_job_folders(request.job_id)

        # Job 폴더가 없으면 생성
        if not os.path.exists(job_uploads_folder):
            logger.info(f"📁 Job 폴더 생성: {request.job_id}")
            folder_manager.create_job_folders(request.job_id)

        # 파일 복사
        import shutil
        target_path = os.path.join(job_uploads_folder, request.video_filename)
        shutil.copy2(source_path, target_path)

        logger.info(f"✅ 북마크 비디오 복사 완료: {request.video_filename}")

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "북마크 비디오가 성공적으로 복사되었습니다",
                "data": {
                    "filename": request.video_filename,
                    "file_url": f"/job-uploads/{request.job_id}/{request.video_filename}",
                    "image_index": request.image_index
                }
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 북마크 비디오 복사 실패: {e}")
        raise HTTPException(status_code=500, detail=f"비디오 복사 실패: {str(e)}")
