"""
백그라운드 워커 시스템
영상 생성 작업을 백그라운드에서 처리하고 완료 시 이메일을 발송하는 워커
"""

import os
import sys
import time
import json
import logging
import signal
import threading
from datetime import datetime
from typing import Dict, Any, Optional

# 현재 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from job_queue import job_queue, JobStatus
from email_service import email_service
from video_generator import VideoGenerator

# Job 로깅 시스템 import
try:
    from job_logger import job_logger
    JOB_LOGGER_AVAILABLE = True
    print("✅ Worker: Job 로깅 시스템 로드 성공")
except ImportError as e:
    print(f"⚠️ Worker: Job 로깅 시스템 로드 실패: {e}")
    job_logger = None
    JOB_LOGGER_AVAILABLE = False

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VideoWorker:
    def __init__(self, worker_id: str = "worker-1"):
        self.worker_id = worker_id
        self.is_running = False
        self.current_job = None
        self.video_generator = VideoGenerator()

        # 정상 종료를 위한 시그널 핸들러 설정
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info(f"🤖 워커 초기화: {self.worker_id}")

    def _signal_handler(self, signum, frame):
        """정상 종료 시그널 처리"""
        logger.info(f"📥 종료 신호 수신 ({signum}). 현재 작업 완료 후 종료합니다...")
        self.is_running = False

    def process_job(self, job_data: Dict[str, Any]) -> bool:
        """개별 작업 처리"""
        job_id = job_data['job_id']
        user_email = job_data['user_email']
        video_params = job_data['video_params']

        logger.info(f"🎬 작업 시작: {job_id} (사용자: {user_email})")

        try:
            # 작업을 처리 중 상태로 변경
            if not job_queue.claim_job(job_id):
                logger.warning(f"⚠️ 작업 클레임 실패: {job_id} (이미 처리 중이거나 완료됨)")
                return False

            self.current_job = job_id

            # Job 로거 상태 업데이트 (처리 시작)
            if JOB_LOGGER_AVAILABLE:
                try:
                    job_logger.update_job_status(job_id, "processing")
                    logger.info(f"✅ Job 로그 상태 업데이트: {job_id} -> processing")
                except Exception as log_error:
                    logger.warning(f"⚠️ Job 로그 상태 업데이트 실패: {log_error}")

            # 영상 생성 파라미터 준비
            output_folder = os.path.join(current_dir, "output_videos")
            os.makedirs(output_folder, exist_ok=True)

            # 파라미터 추출
            content_data = video_params.get('content_data', '{}')
            music_mood = video_params.get('music_mood', 'bright')
            use_test_files = video_params.get('use_test_files', False)
            image_allocation_mode = video_params.get('image_allocation_mode', '2_per_image')
            text_position = video_params.get('text_position', 'bottom')
            text_style = video_params.get('text_style', 'outline')
            title_area_mode = video_params.get('title_area_mode', 'keep')
            selected_bgm_path = video_params.get('selected_bgm_path', '')
            # 폰트 파라미터 추출
            title_font = video_params.get('title_font', 'BMYEONSUNG_otf.otf')
            body_font = video_params.get('body_font', 'BMYEONSUNG_otf.otf')
            # 자막 읽어주기 파라미터 추출
            voice_narration = video_params.get('voice_narration', 'enabled')

            logger.info(f"📋 영상 파라미터: 음악={music_mood}, 테스트파일={use_test_files}, 텍스트위치={text_position}, 타이틀폰트={title_font}, 본문폰트={body_font}, 자막음성={voice_narration}")

            # 콘텐츠 데이터 파싱
            try:
                content = json.loads(content_data) if isinstance(content_data, str) else content_data
                video_title = content.get('title', '릴스 영상')
            except (json.JSONDecodeError, AttributeError):
                video_title = '릴스 영상'

            # BGM 파일 경로 설정
            bgm_file_path = None
            if selected_bgm_path:
                bgm_folder = os.path.join(current_dir, "bgm", music_mood)
                bgm_file_path = os.path.join(bgm_folder, selected_bgm_path)

                if not os.path.exists(bgm_file_path):
                    logger.warning(f"⚠️ 지정된 BGM 파일 없음: {bgm_file_path}")
                    bgm_file_path = None

            # uploads 폴더 설정
            uploads_folder = os.path.join(current_dir, "uploads")

            # text.json 파일을 uploads 폴더에 저장 (VideoGenerator가 기대하는 파일명)
            content_file_path = os.path.join(uploads_folder, "text.json")
            try:
                os.makedirs(uploads_folder, exist_ok=True)
                with open(content_file_path, 'w', encoding='utf-8') as f:
                    json.dump(content, f, ensure_ascii=False, indent=2)
                logger.info(f"📄 text.json 저장 완료: {content_file_path}")
            except Exception as e:
                logger.error(f"❌ text.json 저장 실패: {e}")
                raise

            # 영상 생성 실행
            if use_test_files:
                # 테스트 파일 사용
                logger.info("🧪 테스트 파일 모드로 영상 생성")
                result = self.video_generator.create_video_from_uploads(
                    output_folder=output_folder,
                    bgm_file_path=bgm_file_path,
                    image_allocation_mode=image_allocation_mode,
                    text_position=text_position,
                    text_style=text_style,
                    title_area_mode=title_area_mode,
                    uploads_folder=uploads_folder,
                    title_font=title_font,
                    body_font=body_font,
                    music_mood=music_mood,
                    voice_narration=voice_narration
                )
            else:
                # 업로드된 파일 사용
                logger.info("📁 업로드 파일 모드로 영상 생성")
                result = self.video_generator.create_video_from_uploads(
                    output_folder=output_folder,
                    bgm_file_path=bgm_file_path,
                    image_allocation_mode=image_allocation_mode,
                    text_position=text_position,
                    text_style=text_style,
                    title_area_mode=title_area_mode,
                    uploads_folder=uploads_folder,
                    title_font=title_font,
                    body_font=body_font,
                    music_mood=music_mood,
                    voice_narration=voice_narration
                )

            if result and isinstance(result, str):
                # 영상 생성 성공 (VideoGenerator는 성공 시 파일 경로 문자열 반환)
                video_path = result
                duration = '약 10-30초'  # VideoGenerator에서 duration 정보를 제공하지 않으므로 기본값 사용

                logger.info(f"✅ 영상 생성 완료: {video_path}")

                # Job 로거에 출력 비디오 경로 설정
                if JOB_LOGGER_AVAILABLE:
                    try:
                        job_logger.set_output_video_path(job_id, video_path)
                        job_logger.update_job_status(job_id, "completed")
                        logger.info(f"✅ Job 로그 완료 업데이트: {job_id} -> completed")
                    except Exception as log_error:
                        logger.warning(f"⚠️ Job 로그 완료 업데이트 실패: {log_error}")

                # 작업 완료 상태로 업데이트
                job_queue.update_job_status(
                    job_id=job_id,
                    status=JobStatus.COMPLETED,
                    result={
                        'video_path': video_path,
                        'duration': duration,
                        'completed_at': datetime.now().isoformat()
                    }
                )

                # 완료 이메일 발송
                logger.info(f"📧 완료 이메일 발송 시작: {user_email}")
                email_sent = email_service.send_completion_email(
                    user_email=user_email,
                    video_path=video_path,
                    video_title=video_title,
                    duration=duration
                )

                if email_sent:
                    logger.info(f"✅ 완료 이메일 발송 성공: {user_email}")
                else:
                    logger.error(f"❌ 완료 이메일 발송 실패: {user_email}")

                return True

            else:
                # 영상 생성 실패 (예상하지 못한 반환값)
                error_msg = f"예상하지 못한 결과 형태: {type(result)} - {str(result)}" if result else '영상 생성 실패'
                logger.error(f"❌ 영상 생성 실패: {error_msg}")

                # Job 로거 상태 업데이트 (실패)
                if JOB_LOGGER_AVAILABLE:
                    try:
                        job_logger.update_job_status(job_id, "failed", error_msg)
                        logger.info(f"✅ Job 로그 실패 업데이트: {job_id} -> failed")
                    except Exception as log_error:
                        logger.warning(f"⚠️ Job 로그 실패 업데이트 실패: {log_error}")

                # 작업 실패 상태로 업데이트
                job_queue.update_job_status(
                    job_id=job_id,
                    status=JobStatus.FAILED,
                    error_message=error_msg
                )

                # 실패 이메일 발송
                email_service.send_error_email(
                    user_email=user_email,
                    job_id=job_id,
                    error_message=error_msg
                )

                return False

        except Exception as e:
            logger.error(f"❌ 작업 처리 중 예외 발생: {e}")

            # Job 로거 상태 업데이트 (예외로 인한 실패)
            if JOB_LOGGER_AVAILABLE:
                try:
                    job_logger.update_job_status(job_id, "failed", str(e))
                    logger.info(f"✅ Job 로그 예외 실패 업데이트: {job_id} -> failed")
                except Exception as log_error:
                    logger.warning(f"⚠️ Job 로그 예외 실패 업데이트 실패: {log_error}")

            # 작업 실패 상태로 업데이트
            job_queue.update_job_status(
                job_id=job_id,
                status=JobStatus.FAILED,
                error_message=str(e)
            )

            # 실패 이메일 발송
            email_service.send_error_email(
                user_email=user_email,
                job_id=job_id,
                error_message=str(e)
            )

            return False

        finally:
            self.current_job = None

    def start(self, poll_interval: int = 5):
        """워커 시작"""
        logger.info(f"🚀 워커 시작: {self.worker_id} (폴링 간격: {poll_interval}초)")
        self.is_running = True

        processed_jobs = 0

        while self.is_running:
            try:
                # 대기 중인 작업 조회
                pending_jobs = job_queue.get_pending_jobs()

                if pending_jobs:
                    logger.info(f"📋 대기 중인 작업: {len(pending_jobs)}개")

                    # 첫 번째 작업 처리
                    job_data = pending_jobs[0]
                    job_id = job_data['job_id']

                    logger.info(f"🎯 작업 선택: {job_id}")

                    # 작업 처리
                    success = self.process_job(job_data)
                    processed_jobs += 1

                    if success:
                        logger.info(f"✅ 작업 처리 완료: {job_id} (총 처리: {processed_jobs}개)")
                    else:
                        logger.error(f"❌ 작업 처리 실패: {job_id}")

                        # 재시도 가능한 경우 재시도 큐에 추가
                        if job_queue.retry_job(job_id):
                            logger.info(f"🔄 작업 재시도 큐에 추가: {job_id}")

                else:
                    # 작업이 없으면 대기
                    time.sleep(poll_interval)

            except Exception as e:
                logger.error(f"❌ 워커 루프 중 오류: {e}")
                time.sleep(poll_interval)

        logger.info(f"🛑 워커 종료: {self.worker_id} (총 처리: {processed_jobs}개)")

    def stop(self):
        """워커 중지"""
        logger.info(f"🛑 워커 중지 요청: {self.worker_id}")
        self.is_running = False

    def get_status(self) -> Dict[str, Any]:
        """워커 상태 조회"""
        return {
            'worker_id': self.worker_id,
            'is_running': self.is_running,
            'current_job': self.current_job,
            'queue_stats': job_queue.get_job_stats()
        }

def run_worker(worker_id: str = None, poll_interval: int = 5):
    """워커 실행 함수"""
    if worker_id is None:
        worker_id = f"worker-{os.getpid()}"

    worker = VideoWorker(worker_id)

    try:
        # 시작 전 큐 정리 (오래된 작업 제거)
        job_queue.cleanup_old_jobs(days=7)

        # 워커 시작
        worker.start(poll_interval=poll_interval)

    except KeyboardInterrupt:
        logger.info("🛑 키보드 인터럽트로 종료")
    except Exception as e:
        logger.error(f"❌ 워커 실행 중 오류: {e}")
    finally:
        worker.stop()

if __name__ == "__main__":
    # 명령행 인자 처리
    import argparse

    parser = argparse.ArgumentParser(description='릴스 영상 생성 워커')
    parser.add_argument('--worker-id', default=None, help='워커 ID')
    parser.add_argument('--poll-interval', type=int, default=5, help='폴링 간격(초)')

    args = parser.parse_args()

    # 워커 실행
    run_worker(worker_id=args.worker_id, poll_interval=args.poll_interval)