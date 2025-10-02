"""
파일 기반 작업 큐 시스템
Redis 없이 JSON 파일을 사용한 간단한 작업 큐 관리
"""

import json
import uuid
import os
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
import time
from utils.logger_config import get_logger

logger = get_logger('job_queue')

class JobStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class JobQueue:
    def __init__(self, queue_file: str = "jobs.json"):
        self.queue_file = queue_file
        self.lock = threading.Lock()
        self._ensure_queue_file()

    def _ensure_queue_file(self):
        """큐 파일이 없으면 생성"""
        if not os.path.exists(self.queue_file):
            with open(self.queue_file, 'w') as f:
                json.dump({}, f)

    def _load_queue(self) -> Dict[str, Any]:
        """큐 데이터 로드"""
        try:
            with open(self.queue_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_queue(self, queue_data: Dict[str, Any]):
        """큐 데이터 저장"""
        with open(self.queue_file, 'w', encoding='utf-8') as f:
            json.dump(queue_data, f, ensure_ascii=False, indent=2)

    def add_job(self, user_email: str, video_params: Dict[str, Any], job_id: str = None) -> str:
        """새 작업을 큐에 추가"""
        if job_id is None:
            job_id = str(uuid.uuid4())
        else:
            job_id = str(job_id)  # 문자열로 변환

        job_data = {
            'job_id': job_id,
            'user_email': user_email,
            'status': JobStatus.PENDING.value,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'video_params': video_params,
            'result': None,
            'error_message': None,
            'retry_count': 0,
            'max_retries': 2
        }

        with self.lock:
            queue_data = self._load_queue()
            queue_data[job_id] = job_data
            self._save_queue(queue_data)

        logger.info(f"✅ 새 작업 추가됨: {job_id} (이메일: {user_email})")
        return job_id

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """특정 작업 정보 조회"""
        queue_data = self._load_queue()
        return queue_data.get(job_id)

    def update_job_status(self, job_id: str, status: JobStatus,
                         result: Optional[Dict[str, Any]] = None,
                         error_message: Optional[str] = None):
        """작업 상태 업데이트"""
        with self.lock:
            queue_data = self._load_queue()
            if job_id in queue_data:
                queue_data[job_id]['status'] = status.value
                queue_data[job_id]['updated_at'] = datetime.now().isoformat()

                if result:
                    queue_data[job_id]['result'] = result

                if error_message:
                    queue_data[job_id]['error_message'] = error_message

                self._save_queue(queue_data)
                logger.info(f"🔄 작업 상태 업데이트: {job_id} → {status.value}")

    def get_pending_jobs(self) -> List[Dict[str, Any]]:
        """대기 중인 작업 목록 조회"""
        queue_data = self._load_queue()
        pending_jobs = []

        for job_id, job_data in queue_data.items():
            if job_data['status'] == JobStatus.PENDING.value:
                pending_jobs.append(job_data)

        # 생성 시간 순으로 정렬 (오래된 것부터)
        pending_jobs.sort(key=lambda x: x['created_at'])
        return pending_jobs

    def claim_job(self, job_id: str) -> bool:
        """작업을 처리 상태로 변경 (워커가 작업 시작할 때 호출)"""
        with self.lock:
            queue_data = self._load_queue()
            if job_id in queue_data and queue_data[job_id]['status'] == JobStatus.PENDING.value:
                queue_data[job_id]['status'] = JobStatus.PROCESSING.value
                queue_data[job_id]['updated_at'] = datetime.now().isoformat()
                self._save_queue(queue_data)
                logger.info(f"🏃 작업 시작: {job_id}")
                return True
            return False

    def retry_job(self, job_id: str) -> bool:
        """실패한 작업을 재시도 큐에 추가"""
        with self.lock:
            queue_data = self._load_queue()
            if job_id in queue_data:
                job = queue_data[job_id]
                if job['retry_count'] < job['max_retries']:
                    job['status'] = JobStatus.PENDING.value
                    job['retry_count'] += 1
                    job['updated_at'] = datetime.now().isoformat()
                    job['error_message'] = None
                    self._save_queue(queue_data)
                    logger.info(f"🔄 작업 재시도: {job_id} (시도 {job['retry_count']}/{job['max_retries']})")
                    return True
                else:
                    logger.warning(f"❌ 최대 재시도 횟수 초과: {job_id}")
            return False

    def get_job_stats(self) -> Dict[str, int]:
        """작업 통계 조회"""
        queue_data = self._load_queue()
        stats = {
            'total': len(queue_data),
            'pending': 0,
            'processing': 0,
            'completed': 0,
            'failed': 0
        }

        for job_data in queue_data.values():
            status = job_data['status']
            if status in stats:
                stats[status] += 1

        return stats

    def cleanup_old_jobs(self, days: int = 7):
        """오래된 완료/실패 작업 정리"""
        with self.lock:
            queue_data = self._load_queue()
            current_time = datetime.now()

            jobs_to_remove = []
            for job_id, job_data in queue_data.items():
                if job_data['status'] in [JobStatus.COMPLETED.value, JobStatus.FAILED.value]:
                    updated_at = datetime.fromisoformat(job_data['updated_at'])
                    if (current_time - updated_at).days > days:
                        jobs_to_remove.append(job_id)

            for job_id in jobs_to_remove:
                del queue_data[job_id]
                logger.info(f"🗑️ 오래된 작업 정리: {job_id}")

            if jobs_to_remove:
                self._save_queue(queue_data)
                logger.info(f"✅ {len(jobs_to_remove)}개 오래된 작업 정리 완료")

# 전역 인스턴스
job_queue = JobQueue()

# 사용 예제
if __name__ == "__main__":
    # 테스트용 작업 추가
    test_params = {
        'content_data': '{"title": "테스트", "body1": "첫 번째 내용"}',
        'music_mood': 'bright',
        'use_test_files': True
    }

    job_id = job_queue.add_job("test@example.com", test_params)
    print(f"생성된 Job ID: {job_id}")

    # 작업 정보 조회
    job_info = job_queue.get_job(job_id)
    print(f"작업 정보: {job_info}")

    # 통계 조회
    stats = job_queue.get_job_stats()
    print(f"작업 통계: {stats}")