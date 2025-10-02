"""
Request Pydantic 모델 정의
API 요청에 사용되는 모델들
"""

from pydantic import BaseModel
from typing import Optional, List


class URLExtractRequest(BaseModel):
    """URL에서 릴스 추출 요청"""
    url: str


class ImageGenerateRequest(BaseModel):
    """다중 이미지 생성 요청"""
    texts: List[str]  # 이미지 생성할 텍스트 리스트
    mode: str = "per_script"  # "per_script" 또는 "per_two_scripts"
    job_id: Optional[str] = None  # Job ID 추가 (선택적)


class SingleImageRequest(BaseModel):
    """개별 이미지 생성 요청"""
    text: Optional[str] = None
    custom_prompt: Optional[str] = None
    additional_context: Optional[str] = None
    job_id: Optional[str] = None  # Job ID 추가 (선택적)


class ReelsContent(BaseModel):
    """릴스 콘텐츠 데이터"""
    title: str
    body1: str = ""
    body2: str = ""
    body3: str = ""
    body4: str = ""
    body5: str = ""
    body6: str = ""
    body7: str = ""


class AsyncVideoRequest(BaseModel):
    """비동기 영상 생성 요청"""
    user_email: str
    content_data: str
    music_mood: str = "bright"
    image_allocation_mode: str = "2_per_image"
    text_position: str = "bottom"
    text_style: str = "outline"
    title_area_mode: str = "keep"
    selected_bgm_path: str = ""
    use_test_files: bool = False


class CreateJobFolderRequest(BaseModel):
    """Job 폴더 생성 요청"""
    job_id: str


class CleanupJobFolderRequest(BaseModel):
    """Job 폴더 정리 요청"""
    job_id: str
    keep_output: bool = True


class CopyBookmarkVideoRequest(BaseModel):
    """북마크 비디오 복사 요청"""
    job_id: str
    video_filename: str
    image_index: int
