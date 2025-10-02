"""
폴더 관리 시스템
Job ID 기반 격리된 작업 폴더 생성 및 관리
"""

import os
import shutil
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from pathlib import Path
from utils.logger_config import get_logger

logger = get_logger('folder_manager')

class FolderManager:
    """Job별 격리된 폴더 관리 클래스"""

    def __init__(self, base_dir: str = None):
        self.base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
        self.uploads_base = os.path.join(self.base_dir, "uploads")
        self.output_base = os.path.join(self.base_dir, "output_videos")

        # 기본 폴더들 생성
        os.makedirs(self.uploads_base, exist_ok=True)
        os.makedirs(self.output_base, exist_ok=True)

        logger.info(f"📁 FolderManager 초기화: base_dir={self.base_dir}")

    def create_job_folders(self, job_id: str) -> Tuple[str, str]:
        """
        Job ID 기반으로 격리된 uploads 폴더와 월별 output 폴더 생성

        Args:
            job_id: 고유 작업 ID

        Returns:
            tuple: (uploads_folder_path, output_folder_path)
        """
        try:
            # Job별 uploads 폴더 경로 생성 (격리 필요)
            job_uploads_folder = os.path.join(self.uploads_base, f"job_{job_id}")

            # Output은 월별 폴더 구조 사용 (예: output_videos/202502/)
            from datetime import datetime
            current_month = datetime.now().strftime("%Y%m")
            monthly_output_folder = os.path.join(self.output_base, current_month)

            # 폴더 생성
            os.makedirs(job_uploads_folder, exist_ok=True)
            os.makedirs(monthly_output_folder, exist_ok=True)

            logger.info(f"✅ Job 폴더 생성 완료: {job_id}")
            logger.info(f"   📁 uploads: {job_uploads_folder}")
            logger.info(f"   📁 output: {monthly_output_folder} (월별)")

            return job_uploads_folder, monthly_output_folder

        except Exception as e:
            logger.error(f"❌ Job 폴더 생성 실패: {job_id} - {e}")
            raise

    def get_job_folders(self, job_id: str) -> Tuple[str, str]:
        """
        기존 Job 폴더 경로 반환 (생성하지 않음)

        Args:
            job_id: 작업 ID

        Returns:
            tuple: (uploads_folder_path, output_folder_path)
        """
        job_uploads_folder = os.path.join(self.uploads_base, f"job_{job_id}")

        # Output은 현재 월 기준으로 폴더 경로 반환
        from datetime import datetime
        current_month = datetime.now().strftime("%Y%m")
        monthly_output_folder = os.path.join(self.output_base, current_month)

        return job_uploads_folder, monthly_output_folder

    def cleanup_job_folders(self, job_id: str, keep_output: bool = True) -> bool:
        """
        Job 완료 후 임시 폴더 정리

        Args:
            job_id: 작업 ID
            keep_output: 출력 비디오 폴더 유지 여부 (월별 폴더는 항상 유지)

        Returns:
            bool: 정리 성공 여부
        """
        try:
            job_uploads_folder, monthly_output_folder = self.get_job_folders(job_id)

            # uploads 폴더는 항상 삭제 (임시 파일)
            if os.path.exists(job_uploads_folder):
                shutil.rmtree(job_uploads_folder)
                logger.info(f"🗑️ Job uploads 폴더 삭제: {job_uploads_folder}")

            # output은 월별 폴더이므로 개별 Job 폴더는 삭제하지 않음
            # (월별 폴더 전체를 삭제하면 다른 영상들도 함께 삭제됨)
            logger.info(f"ℹ️ Output은 월별 폴더로 유지: {monthly_output_folder}")

            return True

        except Exception as e:
            logger.error(f"❌ Job 폴더 정리 실패: {job_id} - {e}")
            return False

    def get_unique_filename(self, job_id: str, original_filename: str, folder_type: str = "uploads") -> str:
        """
        Job 폴더 내에서 고유한 파일명 생성

        Args:
            job_id: 작업 ID
            original_filename: 원본 파일명
            folder_type: 폴더 타입 ("uploads" or "output")

        Returns:
            str: 전체 파일 경로
        """
        timestamp = int(time.time())
        unique_id = uuid.uuid4().hex[:8]

        # 확장자 분리
        name, ext = os.path.splitext(original_filename)

        # 고유 파일명 생성
        unique_filename = f"{name}_{timestamp}_{unique_id}{ext}"

        # 전체 경로 생성
        if folder_type == "uploads":
            folder_path = os.path.join(self.uploads_base, f"job_{job_id}")
        else:
            folder_path = os.path.join(self.output_base, f"job_{job_id}")

        full_path = os.path.join(folder_path, unique_filename)

        logger.debug(f"🏷️ 고유 파일명 생성: {original_filename} -> {unique_filename}")

        return full_path

    def save_uploaded_file(self, job_id: str, uploaded_file, target_filename: str = None) -> str:
        """
        업로드된 파일을 Job 폴더에 안전하게 저장

        Args:
            job_id: 작업 ID
            uploaded_file: FastAPI UploadFile 객체
            target_filename: 대상 파일명 (None이면 고유명 자동 생성)

        Returns:
            str: 저장된 파일의 전체 경로
        """
        try:
            # Job uploads 폴더 확인
            job_uploads_folder = os.path.join(self.uploads_base, f"job_{job_id}")
            os.makedirs(job_uploads_folder, exist_ok=True)

            # 파일명 결정
            if target_filename:
                file_path = os.path.join(job_uploads_folder, target_filename)
            else:
                file_path = self.get_unique_filename(job_id, uploaded_file.filename, "uploads")

            # 파일 저장
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(uploaded_file.file, buffer)

            logger.info(f"💾 파일 저장 완료: {uploaded_file.filename} -> {file_path}")

            return file_path

        except Exception as e:
            logger.error(f"❌ 파일 저장 실패: {uploaded_file.filename} - {e}")
            raise

    def cleanup_old_folders(self, age_hours: int = 48) -> int:
        """
        오래된 Job 폴더들 정리

        Args:
            age_hours: 정리 기준 시간 (시간)

        Returns:
            int: 정리된 폴더 수
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=age_hours)
            cleaned_count = 0

            # uploads 폴더 정리
            for folder_name in os.listdir(self.uploads_base):
                if folder_name.startswith("job_"):
                    folder_path = os.path.join(self.uploads_base, folder_name)

                    if os.path.isdir(folder_path):
                        # 폴더 생성 시간 확인
                        folder_time = datetime.fromtimestamp(os.path.getctime(folder_path))

                        if folder_time < cutoff_time:
                            shutil.rmtree(folder_path)
                            logger.info(f"🗑️ 오래된 uploads 폴더 삭제: {folder_name}")
                            cleaned_count += 1

            # output 폴더는 월별 구조이므로 더 오랜 기간 보존 (6개월)
            output_cutoff_time = datetime.now() - timedelta(days=180)

            for folder_name in os.listdir(self.output_base):
                # 월별 폴더 형식 확인 (YYYYMM)
                if len(folder_name) == 6 and folder_name.isdigit():
                    folder_path = os.path.join(self.output_base, folder_name)

                    if os.path.isdir(folder_path):
                        folder_time = datetime.fromtimestamp(os.path.getctime(folder_path))

                        if folder_time < output_cutoff_time:
                            shutil.rmtree(folder_path)
                            logger.info(f"🗑️ 오래된 월별 output 폴더 삭제: {folder_name}")
                            cleaned_count += 1

            logger.info(f"🧹 폴더 정리 완료: {cleaned_count}개 폴더 삭제")
            return cleaned_count

        except Exception as e:
            logger.error(f"❌ 폴더 정리 실패: {e}")
            return 0

    def get_folder_stats(self) -> dict:
        """폴더 사용 통계 조회"""
        try:
            stats = {
                'uploads_folders': 0,
                'output_folders': 0,
                'total_uploads_size': 0,
                'total_output_size': 0
            }

            # uploads 폴더 통계
            if os.path.exists(self.uploads_base):
                for folder_name in os.listdir(self.uploads_base):
                    if folder_name.startswith("job_"):
                        stats['uploads_folders'] += 1
                        folder_path = os.path.join(self.uploads_base, folder_name)
                        stats['total_uploads_size'] += self._get_folder_size(folder_path)

            # output 폴더 통계 (월별 구조)
            if os.path.exists(self.output_base):
                for folder_name in os.listdir(self.output_base):
                    # 월별 폴더 확인 (YYYYMM 형식)
                    if len(folder_name) == 6 and folder_name.isdigit():
                        stats['output_folders'] += 1
                        folder_path = os.path.join(self.output_base, folder_name)
                        stats['total_output_size'] += self._get_folder_size(folder_path)

            return stats

        except Exception as e:
            logger.error(f"❌ 폴더 통계 조회 실패: {e}")
            return {}

    def _get_folder_size(self, folder_path: str) -> int:
        """폴더 크기 계산 (바이트)"""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(folder_path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)
        except:
            pass
        return total_size

# 전역 폴더 매니저 인스턴스
folder_manager = FolderManager()

# 편의 함수들
def create_job_folders(job_id: str) -> Tuple[str, str]:
    """Job 폴더 생성"""
    return folder_manager.create_job_folders(job_id)

def get_job_folders(job_id: str) -> Tuple[str, str]:
    """Job 폴더 경로 조회"""
    return folder_manager.get_job_folders(job_id)

def cleanup_job_folders(job_id: str, keep_output: bool = True) -> bool:
    """Job 폴더 정리"""
    return folder_manager.cleanup_job_folders(job_id, keep_output)

def save_uploaded_file(job_id: str, uploaded_file, target_filename: str = None) -> str:
    """업로드 파일 저장"""
    return folder_manager.save_uploaded_file(job_id, uploaded_file, target_filename)

def cleanup_old_folders(age_hours: int = 48) -> int:
    """오래된 폴더 정리"""
    return folder_manager.cleanup_old_folders(age_hours)