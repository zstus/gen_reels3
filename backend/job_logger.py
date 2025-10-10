"""
Job 로깅 시스템 - SQLite 기반
"""
import sqlite3
import json
import os
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Any
import uuid
from utils.logger_config import get_logger

# 로깅 설정
logger = get_logger('job_logger')

class JobLogger:
    def __init__(self, db_path: str = "log/job_logs.db"):
        self.db_path = db_path
        self.assets_dir = "assets"
        self.output_videos_dir = "output_videos"

        # 디렉토리 생성
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        os.makedirs(self.assets_dir, exist_ok=True)
        os.makedirs(os.path.join(self.assets_dir, "images"), exist_ok=True)
        os.makedirs(os.path.join(self.assets_dir, "videos"), exist_ok=True)
        os.makedirs(self.output_videos_dir, exist_ok=True)

        self._init_database()

    def _init_database(self):
        """데이터베이스 초기화 및 테이블 생성"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # jobs 테이블 생성
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT UNIQUE NOT NULL,
                    user_email TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    reels_content TEXT NOT NULL,
                    music_mood TEXT,
                    text_position TEXT,
                    image_allocation_mode TEXT,
                    output_video_path TEXT,
                    error_message TEXT,
                    metadata TEXT
                )
            ''')

            # media_files 테이블 생성 (사용된 미디어 파일들)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS media_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    original_filename TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_size INTEGER,
                    asset_path TEXT NOT NULL,
                    sequence_number INTEGER,
                    created_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (job_id) REFERENCES jobs (job_id)
                )
            ''')

            # 인덱스 생성
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_job_id ON jobs(job_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_user_email ON jobs(user_email)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_media_files_job_id ON media_files(job_id)')

            conn.commit()
            logger.info("데이터베이스 초기화 완료")

    def create_job_log(self,
                       job_id: str,
                       user_email: str,
                       reels_content: Dict[str, str],
                       music_mood: str = "bright",
                       text_position: str = "bottom",
                       image_allocation_mode: str = "2_per_image",
                       metadata: Optional[Dict[str, Any]] = None) -> str:
        """새 Job 로그 생성"""

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    INSERT INTO jobs (
                        job_id, user_email, status, created_at,
                        reels_content, music_mood, text_position,
                        image_allocation_mode, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    job_id,
                    user_email,
                    "pending",
                    datetime.now(),
                    json.dumps(reels_content, ensure_ascii=False),
                    music_mood,
                    text_position,
                    image_allocation_mode,
                    json.dumps(metadata or {}, ensure_ascii=False)
                ))

                conn.commit()
                logger.info(f"Job 로그 생성: {job_id}")
                return job_id

        except Exception as e:
            logger.error(f"Job 로그 생성 실패: {e}")
            raise

    def update_job_status(self, job_id: str, status: str, error_message: Optional[str] = None):
        """Job 상태 업데이트"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                update_fields = ["status = ?"]
                params = [status]

                if status == "processing":
                    update_fields.append("started_at = ?")
                    params.append(datetime.now())
                elif status in ["completed", "failed"]:
                    update_fields.append("completed_at = ?")
                    params.append(datetime.now())

                if error_message:
                    update_fields.append("error_message = ?")
                    params.append(error_message)

                params.append(job_id)

                cursor.execute(f'''
                    UPDATE jobs
                    SET {", ".join(update_fields)}
                    WHERE job_id = ?
                ''', params)

                conn.commit()
                logger.info(f"Job 상태 업데이트: {job_id} -> {status}")

        except Exception as e:
            logger.error(f"Job 상태 업데이트 실패: {e}")
            raise

    def update_job_metadata(self, job_id: str, metadata: Dict[str, Any]):
        """Job의 metadata 업데이트"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    UPDATE jobs
                    SET metadata = ?
                    WHERE job_id = ?
                ''', (json.dumps(metadata, ensure_ascii=False), job_id))

                conn.commit()
                logger.info(f"Job metadata 업데이트: {job_id}")

        except Exception as e:
            logger.error(f"Job metadata 업데이트 실패: {e}")
            raise

    def save_media_file(self,
                        job_id: str,
                        original_file_path: str,
                        original_filename: str,
                        file_type: str,
                        sequence_number: int) -> str:
        """미디어 파일을 assets 폴더에 년월 구조로 저장"""
        try:
            # 파일 확장자 추출
            file_ext = os.path.splitext(original_filename)[1].lower()

            # 고유한 파일명 생성 (job_id + sequence + 확장자)
            new_filename = f"{job_id}_{sequence_number:02d}{file_ext}"

            # 년월 폴더 생성 (YYYYMM 형식)
            year_month = datetime.now().strftime("%Y%m")

            # 저장 경로 결정 (assets/images/202510 또는 assets/videos/202510)
            if file_type == "image":
                asset_folder = os.path.join(self.assets_dir, "images", year_month)
            else:  # video
                asset_folder = os.path.join(self.assets_dir, "videos", year_month)

            # 폴더가 없으면 생성
            os.makedirs(asset_folder, exist_ok=True)

            asset_path = os.path.join(asset_folder, new_filename)

            # 파일 복사
            shutil.copy2(original_file_path, asset_path)

            # 파일 크기 계산
            file_size = os.path.getsize(asset_path)

            # 데이터베이스에 기록
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    INSERT INTO media_files (
                        job_id, original_filename, file_type, file_size,
                        asset_path, sequence_number, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    job_id,
                    original_filename,
                    file_type,
                    file_size,
                    asset_path,
                    sequence_number,
                    datetime.now()
                ))

                conn.commit()

            logger.info(f"미디어 파일 저장: {original_filename} -> {asset_path} ({year_month})")
            return asset_path

        except Exception as e:
            logger.error(f"미디어 파일 저장 실패: {e}")
            raise

    def set_output_video_path(self, job_id: str, video_path: str):
        """최종 출력 비디오 경로 설정"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    UPDATE jobs
                    SET output_video_path = ?
                    WHERE job_id = ?
                ''', (video_path, job_id))

                conn.commit()
                logger.info(f"출력 비디오 경로 설정: {job_id} -> {video_path}")

        except Exception as e:
            logger.error(f"출력 비디오 경로 설정 실패: {e}")
            raise

    def get_job_info(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Job 정보 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Job 기본 정보
                cursor.execute('''
                    SELECT * FROM jobs WHERE job_id = ?
                ''', (job_id,))

                job_row = cursor.fetchone()
                if not job_row:
                    return None

                job_info = dict(job_row)

                # reels_content와 metadata JSON 파싱
                job_info['reels_content'] = json.loads(job_info['reels_content'])
                if job_info['metadata']:
                    job_info['metadata'] = json.loads(job_info['metadata'])

                # 미디어 파일 정보
                cursor.execute('''
                    SELECT * FROM media_files
                    WHERE job_id = ?
                    ORDER BY sequence_number
                ''', (job_id,))

                media_files = [dict(row) for row in cursor.fetchall()]
                job_info['media_files'] = media_files

                return job_info

        except Exception as e:
            logger.error(f"Job 정보 조회 실패: {e}")
            raise

    def get_user_jobs(self, user_email: str, limit: int = 50) -> List[Dict[str, Any]]:
        """사용자별 Job 목록 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT * FROM jobs
                    WHERE user_email = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (user_email, limit))

                jobs = []
                for row in cursor.fetchall():
                    job_info = dict(row)
                    job_info['reels_content'] = json.loads(job_info['reels_content'])
                    if job_info['metadata']:
                        job_info['metadata'] = json.loads(job_info['metadata'])
                    jobs.append(job_info)

                return jobs

        except Exception as e:
            logger.error(f"사용자별 Job 목록 조회 실패: {e}")
            raise

    def get_job_statistics(self) -> Dict[str, Any]:
        """Job 통계 정보"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 전체 통계
                cursor.execute('SELECT COUNT(*) as total FROM jobs')
                total_jobs = cursor.fetchone()[0]

                # 상태별 통계
                cursor.execute('''
                    SELECT status, COUNT(*) as count
                    FROM jobs
                    GROUP BY status
                ''')
                status_stats = {row[0]: row[1] for row in cursor.fetchall()}

                # 일별 통계 (최근 30일)
                cursor.execute('''
                    SELECT DATE(created_at) as date, COUNT(*) as count
                    FROM jobs
                    WHERE created_at >= datetime('now', '-30 days')
                    GROUP BY DATE(created_at)
                    ORDER BY date DESC
                ''')
                daily_stats = {row[0]: row[1] for row in cursor.fetchall()}

                return {
                    'total_jobs': total_jobs,
                    'status_stats': status_stats,
                    'daily_stats': daily_stats
                }

        except Exception as e:
            logger.error(f"Job 통계 조회 실패: {e}")
            raise

# 전역 인스턴스
job_logger = JobLogger()