"""
Response Pydantic 모델 정의
API 응답에 사용되는 모델들
"""

from pydantic import BaseModel
from typing import Optional


class JobStatusResponse(BaseModel):
    """Job 상태 조회 응답"""
    job_id: str
    status: str
    created_at: str
    updated_at: str
    result: Optional[dict] = None
    error_message: Optional[str] = None


class CreateJobFolderResponse(BaseModel):
    """Job 폴더 생성 응답"""
    status: str
    message: str
    job_id: str
    uploads_folder: Optional[str] = None
    output_folder: Optional[str] = None


class CleanupJobFolderResponse(BaseModel):
    """Job 폴더 정리 응답"""
    status: str
    message: str
    job_id: str
    cleaned: bool
