"""
Pydantic 모델 정의
Request/Response 모델들을 관리하는 패키지
"""

from .request_models import (
    URLExtractRequest,
    ImageGenerateRequest,
    SingleImageRequest,
    ReelsContent,
    AsyncVideoRequest,
    CreateJobFolderRequest,
    CleanupJobFolderRequest,
    CopyBookmarkVideoRequest,
)

from .response_models import (
    JobStatusResponse,
    CreateJobFolderResponse,
    CleanupJobFolderResponse,
)

__all__ = [
    # Request Models
    "URLExtractRequest",
    "ImageGenerateRequest",
    "SingleImageRequest",
    "ReelsContent",
    "AsyncVideoRequest",
    "CreateJobFolderRequest",
    "CleanupJobFolderRequest",
    "CopyBookmarkVideoRequest",
    # Response Models
    "JobStatusResponse",
    "CreateJobFolderResponse",
    "CleanupJobFolderResponse",
]
