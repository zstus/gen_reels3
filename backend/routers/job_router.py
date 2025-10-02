"""
Job 관리 라우터
작업 상태 조회, Job 폴더 관리, 통계 등 Job 관련 API
"""

from fastapi import APIRouter, HTTPException
from utils.logger_config import get_logger
from models.request_models import CreateJobFolderRequest, CleanupJobFolderRequest
from models.response_models import (
    JobStatusResponse,
    CreateJobFolderResponse,
    CleanupJobFolderResponse,
)

router = APIRouter(tags=["job"])
logger = get_logger('job_router')

# 전역 변수 (main.py에서 설정)
job_queue = None
job_logger = None
folder_manager = None
JOB_QUEUE_AVAILABLE = False
JOB_LOGGER_AVAILABLE = False
FOLDER_MANAGER_AVAILABLE = False


def set_dependencies(jq, jl, fm, jq_avail, jl_avail, fm_avail):
    """main.py에서 호출하여 의존성 설정"""
    global job_queue, job_logger, folder_manager
    global JOB_QUEUE_AVAILABLE, JOB_LOGGER_AVAILABLE, FOLDER_MANAGER_AVAILABLE
    job_queue = jq
    job_logger = jl
    folder_manager = fm
    JOB_QUEUE_AVAILABLE = jq_avail
    JOB_LOGGER_AVAILABLE = jl_avail
    FOLDER_MANAGER_AVAILABLE = fm_avail


@router.get("/job-status/{job_id}")
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


@router.get("/queue-stats")
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


@router.get("/job-logs/{job_id}")
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


@router.get("/user-jobs/{user_email}")
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


@router.get("/job-statistics")
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


@router.post("/create-job-folder")
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


@router.post("/cleanup-job-folder")
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
