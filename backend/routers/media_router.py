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
import json
from datetime import datetime
from moviepy.editor import VideoFileClip
from PIL import Image

router = APIRouter(tags=["media"])
logger = get_logger('media_router')

# 전역 변수 (main.py에서 설정)
folder_manager = None
FOLDER_MANAGER_AVAILABLE = False
BOOKMARK_VIDEOS_FOLDER = "assets/videos/bookmark"
BOOKMARK_IMAGES_FOLDER = "assets/images/bookmark"
UPLOAD_FOLDER = "uploads"


def set_dependencies(fm, fm_avail, bookmark_folder, upload_folder):
    """main.py에서 호출하여 의존성 설정"""
    global folder_manager, FOLDER_MANAGER_AVAILABLE
    global BOOKMARK_VIDEOS_FOLDER, BOOKMARK_IMAGES_FOLDER, UPLOAD_FOLDER
    folder_manager = fm
    FOLDER_MANAGER_AVAILABLE = fm_avail
    BOOKMARK_VIDEOS_FOLDER = bookmark_folder
    BOOKMARK_IMAGES_FOLDER = "assets/images/bookmark"
    UPLOAD_FOLDER = upload_folder


def load_video_metadata(meta_path: str) -> dict:
    """메타데이터 JSON 파일 읽기"""
    try:
        with open(meta_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"❌ 메타데이터 읽기 실패 ({os.path.basename(meta_path)}): {e}")
        return None


def generate_video_metadata(video_path: str, meta_path: str) -> dict:
    """비디오 메타데이터 생성 및 JSON 파일 저장"""
    try:
        logger.info(f"📊 메타데이터 생성 시작: {os.path.basename(video_path)}")

        filename = os.path.basename(video_path)
        display_name = os.path.splitext(filename)[0]

        # 파일 크기
        file_size = os.path.getsize(video_path)
        size_mb = round(file_size / (1024 * 1024), 2)

        # 파일 수정 시간
        modified_time = os.path.getmtime(video_path)

        # 비디오 duration 추출
        duration = 0
        try:
            with VideoFileClip(video_path) as clip:
                duration = round(clip.duration, 1)
        except Exception as e:
            logger.warning(f"⚠️ Duration 추출 실패: {e}")

        # 썸네일 파일명 확인
        thumbnail_filename_webp = f"{display_name}_thumb.webp"
        thumbnail_filename_jpg = f"{display_name}_thumb.jpg"
        video_dir = os.path.dirname(video_path)
        thumbnail_path_webp = os.path.join(video_dir, thumbnail_filename_webp)
        thumbnail_path_jpg = os.path.join(video_dir, thumbnail_filename_jpg)

        has_thumbnail = False
        thumbnail_filename = None
        if os.path.exists(thumbnail_path_webp):
            has_thumbnail = True
            thumbnail_filename = thumbnail_filename_webp
        elif os.path.exists(thumbnail_path_jpg):
            has_thumbnail = True
            thumbnail_filename = thumbnail_filename_jpg

        # 메타데이터 구조
        metadata = {
            "filename": filename,
            "display_name": display_name,
            "duration": duration,
            "size_mb": size_mb,
            "modified_time": modified_time,
            "created_at": datetime.now().strftime("%Y-%m-%d"),
            "has_thumbnail": has_thumbnail,
            "thumbnail_filename": thumbnail_filename,
            "extension": os.path.splitext(filename)[1].lower()
        }

        # JSON 파일로 저장
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        logger.info(f"✅ 메타데이터 생성 완료: {os.path.basename(meta_path)}")
        return metadata

    except Exception as e:
        logger.error(f"❌ 메타데이터 생성 실패 ({os.path.basename(video_path)}): {e}")
        return None


def cleanup_orphaned_files(video_folder: str):
    """고아 파일 정리: 비디오가 삭제된 경우 관련 meta.json과 썸네일 삭제"""
    try:
        logger.info("🧹 고아 파일 정리 시작...")
        cleaned_count = 0

        # 모든 meta.json 파일 찾기
        meta_files = glob.glob(os.path.join(video_folder, "*_meta.json"))

        for meta_path in meta_files:
            meta_filename = os.path.basename(meta_path)
            display_name = meta_filename.replace("_meta.json", "")

            # meta.json 읽기
            metadata = load_video_metadata(meta_path)
            if not metadata:
                # JSON 읽기 실패 시 삭제
                logger.warning(f"⚠️ 손상된 meta.json 삭제: {meta_filename}")
                os.remove(meta_path)
                cleaned_count += 1
                continue

            # 비디오 파일 존재 확인
            video_filename = metadata.get("filename")
            if video_filename:
                video_path = os.path.join(video_folder, video_filename)
                if not os.path.exists(video_path):
                    # 비디오가 없으면 meta.json 삭제
                    logger.info(f"🗑️ 비디오 없음, meta.json 삭제: {meta_filename}")
                    os.remove(meta_path)
                    cleaned_count += 1

                    # 관련 썸네일도 삭제
                    thumbnail_filename = metadata.get("thumbnail_filename")
                    if thumbnail_filename:
                        thumbnail_path = os.path.join(video_folder, thumbnail_filename)
                        if os.path.exists(thumbnail_path):
                            logger.info(f"🗑️ 썸네일 삭제: {thumbnail_filename}")
                            os.remove(thumbnail_path)
                            cleaned_count += 1

        # 추가: 비디오 파일이 없는데 썸네일만 남아있는 경우 정리
        thumbnail_files = glob.glob(os.path.join(video_folder, "*_thumb.webp"))
        thumbnail_files.extend(glob.glob(os.path.join(video_folder, "*_thumb.jpg")))

        for thumb_path in thumbnail_files:
            thumb_filename = os.path.basename(thumb_path)
            # example_thumb.webp → example
            if thumb_filename.endswith("_thumb.webp"):
                display_name = thumb_filename.replace("_thumb.webp", "")
            else:
                display_name = thumb_filename.replace("_thumb.jpg", "")

            # 원본 비디오 확인 (여러 확장자 시도)
            video_exists = False
            for ext in ['.mp4', '.mov', '.avi', '.webm']:
                video_path = os.path.join(video_folder, f"{display_name}{ext}")
                if os.path.exists(video_path):
                    video_exists = True
                    break

            if not video_exists:
                logger.info(f"🗑️ 고아 썸네일 삭제: {thumb_filename}")
                os.remove(thumb_path)
                cleaned_count += 1

        if cleaned_count > 0:
            logger.info(f"✅ 고아 파일 정리 완료: {cleaned_count}개 삭제")
        else:
            logger.info("✅ 정리할 고아 파일 없음")

    except Exception as e:
        logger.error(f"❌ 고아 파일 정리 실패: {e}")


def generate_video_thumbnail(video_path: str, thumbnail_path: str) -> bool:
    """비디오에서 썸네일 자동 생성 (WebP 200x200)"""
    try:
        logger.info(f"🎬 썸네일 생성 시작: {os.path.basename(video_path)}")

        with VideoFileClip(video_path) as clip:
            # 동영상 0.5초 지점에서 썸네일 추출
            thumbnail_time = min(0.5, clip.duration - 0.1)

            # 프레임 추출
            frame = clip.get_frame(thumbnail_time)

            # PIL Image로 변환
            image = Image.fromarray(frame)

            # 정사각형으로 크롭 (중앙 기준)
            width, height = image.size
            if width > height:
                left = (width - height) // 2
                image = image.crop((left, 0, left + height, height))
            else:
                top = (height - width) // 2
                image = image.crop((0, top, width, top + width))

            # 200x200으로 리사이즈 (LANCZOS 고품질)
            image = image.resize((200, 200), Image.Resampling.LANCZOS)

            # WebP 포맷으로 저장 (80% 품질, method=4 최적화)
            image.save(thumbnail_path, 'WEBP', quality=80, method=4, optimize=True)

            logger.info(f"✅ 썸네일 생성 완료: {os.path.basename(thumbnail_path)} (200x200)")
            return True

    except Exception as e:
        logger.error(f"❌ 썸네일 생성 실패 ({os.path.basename(video_path)}): {e}")
        return False


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
    """북마크 비디오 목록 조회 (썸네일 자동 생성 + 고아 파일 정리)"""
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

        # 1단계: 고아 파일 정리 (비디오 없이 meta.json이나 썸네일만 남은 경우)
        cleanup_orphaned_files(BOOKMARK_VIDEOS_FOLDER)

        # 2단계: 비디오 파일 검색 (.mp4, .mov, .avi, .webm)
        video_patterns = ["*.mp4", "*.mov", "*.avi", "*.webm"]

        for pattern in video_patterns:
            found_files = glob.glob(os.path.join(BOOKMARK_VIDEOS_FOLDER, pattern))
            for video_path in found_files:
                filename = os.path.basename(video_path)
                display_name = os.path.splitext(filename)[0]

                # 메타데이터 JSON 파일 경로
                meta_filename = f"{display_name}_meta.json"
                meta_path = os.path.join(BOOKMARK_VIDEOS_FOLDER, meta_filename)

                # 1단계: 메타데이터 JSON 확인
                metadata = None
                if os.path.exists(meta_path):
                    # JSON 파일이 있으면 읽기 (빠름!)
                    logger.info(f"📄 메타데이터 캐시 사용: {meta_filename}")
                    metadata = load_video_metadata(meta_path)

                # 2단계: 메타데이터가 없거나 읽기 실패 시 생성
                if not metadata:
                    logger.info(f"🔄 메타데이터 생성 필요: {filename}")
                    metadata = generate_video_metadata(video_path, meta_path)

                    # 메타데이터 생성 중 썸네일도 함께 생성
                    if metadata and not metadata.get('has_thumbnail'):
                        thumbnail_path_webp = os.path.join(BOOKMARK_VIDEOS_FOLDER, f"{display_name}_thumb.webp")
                        if generate_video_thumbnail(video_path, thumbnail_path_webp):
                            metadata['has_thumbnail'] = True
                            metadata['thumbnail_filename'] = f"{display_name}_thumb.webp"
                            # 메타데이터 업데이트
                            with open(meta_path, 'w', encoding='utf-8') as f:
                                json.dump(metadata, f, ensure_ascii=False, indent=2)

                # 3단계: 메타데이터를 응답 형식으로 변환
                if metadata:
                    videos.append({
                        "filename": metadata["filename"],
                        "display_name": metadata["display_name"],
                        "video_url": f"/bookmark-videos/{metadata['filename']}",
                        "thumbnail_url": f"/bookmark-videos/{metadata['thumbnail_filename']}" if metadata.get('thumbnail_filename') else None,
                        "has_thumbnail": metadata.get('has_thumbnail', False),
                        "size_mb": metadata["size_mb"],
                        "modified_time": metadata["modified_time"],
                        "duration": metadata["duration"],
                        "extension": metadata["extension"]
                    })
                else:
                    logger.error(f"❌ 메타데이터 처리 실패: {filename}")

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


@router.get("/bookmark-images")
async def get_bookmark_images():
    """북마크 이미지 목록 조회"""
    try:
        images = []

        if not os.path.exists(BOOKMARK_IMAGES_FOLDER):
            logger.warning(f"북마크 이미지 폴더 없음: {BOOKMARK_IMAGES_FOLDER}")
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": "북마크 이미지 폴더가 비어있습니다",
                    "data": []
                }
            )

        # 이미지 파일 검색 (.jpg, .jpeg, .png, .webp, .gif)
        image_patterns = ["*.jpg", "*.jpeg", "*.png", "*.webp", "*.gif"]

        for pattern in image_patterns:
            found_files = glob.glob(os.path.join(BOOKMARK_IMAGES_FOLDER, pattern))
            for image_path in found_files:
                filename = os.path.basename(image_path)
                display_name = os.path.splitext(filename)[0]

                # 파일 크기 정보
                file_size = os.path.getsize(image_path)
                file_size_mb = round(file_size / (1024 * 1024), 2)

                # 파일 수정 시간
                modified_time = os.path.getmtime(image_path)

                images.append({
                    "filename": filename,
                    "display_name": display_name,
                    "image_url": f"/bookmark-images/{filename}",
                    "thumbnail_url": f"/bookmark-images/{filename}",
                    "size_mb": file_size_mb,
                    "modified_time": modified_time,
                    "extension": os.path.splitext(filename)[1].lower()
                })

        # 파일명 순으로 정렬
        images.sort(key=lambda x: x['display_name'])

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"{len(images)}개의 북마크 이미지를 찾았습니다",
                "data": images
            }
        )

    except Exception as e:
        logger.error(f"북마크 이미지 목록 조회 오류: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": str(e)
            }
        )


@router.get("/bookmark-images/{filename}")
async def serve_bookmark_image(filename: str):
    """북마크 이미지 파일 제공"""
    file_path = os.path.join(BOOKMARK_IMAGES_FOLDER, filename)

    if not os.path.exists(file_path):
        logger.warning(f"북마크 이미지 없음: {filename}")
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


@router.post("/copy-bookmark-image")
async def copy_bookmark_image(request: CopyBookmarkVideoRequest):
    """북마크 이미지를 Job 폴더로 복사 (비디오와 동일한 구조)"""
    try:
        if not FOLDER_MANAGER_AVAILABLE:
            raise HTTPException(status_code=500, detail="폴더 관리 시스템이 사용 불가능합니다.")

        logger.info(f"📋 북마크 이미지 복사 요청: {request.video_filename} → {request.job_id}")

        # 원본 파일 경로
        source_path = os.path.join(BOOKMARK_IMAGES_FOLDER, request.video_filename)
        if not os.path.exists(source_path):
            raise HTTPException(status_code=404, detail="북마크 이미지를 찾을 수 없습니다")

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

        logger.info(f"✅ 북마크 이미지 복사 완료: {request.video_filename}")

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "북마크 이미지가 성공적으로 복사되었습니다",
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
        logger.error(f"❌ 북마크 이미지 복사 실패: {e}")
        raise HTTPException(status_code=500, detail=f"이미지 복사 실패: {str(e)}")
