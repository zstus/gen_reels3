"""
주기적 임시 파일 정리 시스템
오래된 Job 폴더들을 자동으로 정리하는 스케줄러
"""

import os
import time
import threading
import logging
from datetime import datetime, timedelta
from typing import Optional
from folder_manager import folder_manager

logger = logging.getLogger(__name__)

class CleanupScheduler:
    """주기적 임시 파일 정리 스케줄러"""

    def __init__(self, cleanup_interval_hours: int = 6,
                 uploads_age_hours: int = 48,
                 output_age_days: int = 7):
        """
        Args:
            cleanup_interval_hours: 정리 작업 실행 간격 (시간)
            uploads_age_hours: uploads 폴더 정리 기준 나이 (시간)
            output_age_days: output 폴더 정리 기준 나이 (일)
        """
        self.cleanup_interval_hours = cleanup_interval_hours
        self.uploads_age_hours = uploads_age_hours
        self.output_age_days = output_age_days
        self.is_running = False
        self.cleanup_thread: Optional[threading.Thread] = None

        logger.info(f"🗑️ CleanupScheduler 초기화:")
        logger.info(f"   정리 간격: {cleanup_interval_hours}시간")
        logger.info(f"   uploads 폐기: {uploads_age_hours}시간 후")
        logger.info(f"   output 폐기: {output_age_days}일 후")

    def start(self):
        """정리 스케줄러 시작"""
        if self.is_running:
            logger.warning("⚠️ CleanupScheduler가 이미 실행 중입니다")
            return

        self.is_running = True
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()
        logger.info("🚀 CleanupScheduler 시작")

    def stop(self):
        """정리 스케줄러 중지"""
        if not self.is_running:
            return

        self.is_running = False
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=5)
        logger.info("🛑 CleanupScheduler 중지")

    def _cleanup_loop(self):
        """정리 작업 루프"""
        while self.is_running:
            try:
                self._perform_cleanup()

                # 다음 정리까지 대기
                sleep_seconds = self.cleanup_interval_hours * 3600
                for _ in range(sleep_seconds):
                    if not self.is_running:
                        break
                    time.sleep(1)

            except Exception as e:
                logger.error(f"❌ 정리 작업 중 오류: {e}")
                time.sleep(300)  # 5분 대기 후 재시도

    def _perform_cleanup(self):
        """실제 정리 작업 수행"""
        logger.info("🧹 주기적 정리 작업 시작")

        try:
            # 1. 오래된 uploads 폴더 정리
            uploads_cleaned = self._cleanup_old_uploads()

            # 2. 오래된 output 폴더 정리
            output_cleaned = self._cleanup_old_outputs()

            # 3. 통계 정보 로깅
            stats = folder_manager.get_folder_stats()
            logger.info(f"📊 정리 완료:")
            logger.info(f"   uploads 폴더 정리: {uploads_cleaned}개")
            logger.info(f"   output 폴더 정리: {output_cleaned}개")
            logger.info(f"   남은 uploads 폴더: {stats.get('uploads_folders', 0)}개")
            logger.info(f"   남은 output 폴더: {stats.get('output_folders', 0)}개")
            logger.info(f"   총 uploads 크기: {self._format_size(stats.get('total_uploads_size', 0))}")
            logger.info(f"   총 output 크기: {self._format_size(stats.get('total_output_size', 0))}")

        except Exception as e:
            logger.error(f"❌ 정리 작업 실패: {e}")

    def _cleanup_old_uploads(self) -> int:
        """오래된 uploads 폴더 정리"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=self.uploads_age_hours)
            cleaned_count = 0

            uploads_base = folder_manager.uploads_base
            if not os.path.exists(uploads_base):
                return 0

            for folder_name in os.listdir(uploads_base):
                if folder_name.startswith("job_"):
                    folder_path = os.path.join(uploads_base, folder_name)

                    if os.path.isdir(folder_path):
                        # 폴더 생성 시간 확인
                        folder_time = datetime.fromtimestamp(os.path.getctime(folder_path))

                        if folder_time < cutoff_time:
                            try:
                                import shutil
                                shutil.rmtree(folder_path)
                                logger.debug(f"🗑️ 오래된 uploads 폴더 삭제: {folder_name}")
                                cleaned_count += 1
                            except Exception as e:
                                logger.warning(f"⚠️ uploads 폴더 삭제 실패 {folder_name}: {e}")

            return cleaned_count

        except Exception as e:
            logger.error(f"❌ uploads 폴더 정리 실패: {e}")
            return 0

    def _cleanup_old_outputs(self) -> int:
        """오래된 output 폴더 정리"""
        try:
            cutoff_time = datetime.now() - timedelta(days=self.output_age_days)
            cleaned_count = 0

            output_base = folder_manager.output_base
            if not os.path.exists(output_base):
                return 0

            for folder_name in os.listdir(output_base):
                if folder_name.startswith("job_"):
                    folder_path = os.path.join(output_base, folder_name)

                    if os.path.isdir(folder_path):
                        # 폴더 생성 시간 확인
                        folder_time = datetime.fromtimestamp(os.path.getctime(folder_path))

                        if folder_time < cutoff_time:
                            try:
                                import shutil
                                shutil.rmtree(folder_path)
                                logger.debug(f"🗑️ 오래된 output 폴더 삭제: {folder_name}")
                                cleaned_count += 1
                            except Exception as e:
                                logger.warning(f"⚠️ output 폴더 삭제 실패 {folder_name}: {e}")

            return cleaned_count

        except Exception as e:
            logger.error(f"❌ output 폴더 정리 실패: {e}")
            return 0

    def _format_size(self, size_bytes: int) -> str:
        """파일 크기를 읽기 쉬운 형태로 변환"""
        if size_bytes == 0:
            return "0B"

        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1

        return f"{size_bytes:.1f}{size_names[i]}"

    def force_cleanup(self):
        """강제 정리 실행 (테스트용)"""
        logger.info("🔧 강제 정리 작업 실행")
        self._perform_cleanup()

    def get_status(self) -> dict:
        """스케줄러 상태 조회"""
        stats = folder_manager.get_folder_stats()

        return {
            'is_running': self.is_running,
            'cleanup_interval_hours': self.cleanup_interval_hours,
            'uploads_age_hours': self.uploads_age_hours,
            'output_age_days': self.output_age_days,
            'folder_stats': stats,
            'next_cleanup': self._get_next_cleanup_time() if self.is_running else None
        }

    def _get_next_cleanup_time(self) -> str:
        """다음 정리 시간 계산"""
        next_time = datetime.now() + timedelta(hours=self.cleanup_interval_hours)
        return next_time.strftime("%Y-%m-%d %H:%M:%S")

# 전역 스케줄러 인스턴스
cleanup_scheduler = CleanupScheduler()

def start_cleanup_scheduler():
    """정리 스케줄러 시작"""
    cleanup_scheduler.start()

def stop_cleanup_scheduler():
    """정리 스케줄러 중지"""
    cleanup_scheduler.stop()

def get_cleanup_status():
    """정리 스케줄러 상태 조회"""
    return cleanup_scheduler.get_status()

def force_cleanup():
    """강제 정리 실행"""
    cleanup_scheduler.force_cleanup()