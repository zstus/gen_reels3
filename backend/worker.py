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

# 통합 로깅 시스템 import
from utils.logger_config import get_logger
logger = get_logger('worker')

from job_queue import job_queue, JobStatus
from email_service import email_service
from video_generator import VideoGenerator

# Job 로깅 시스템 import
try:
    from job_logger import job_logger
    JOB_LOGGER_AVAILABLE = True
    logger.info("✅ Worker: Job 로깅 시스템 로드 성공")
except ImportError as e:
    logger.warning(f"⚠️ Worker: Job 로깅 시스템 로드 실패: {e}")
    job_logger = None
    JOB_LOGGER_AVAILABLE = False

# Folder 관리 시스템 import
try:
    from folder_manager import folder_manager
    FOLDER_MANAGER_AVAILABLE = True
    logger.info("✅ Worker: Folder 관리 시스템 로드 성공")
except ImportError as e:
    logger.warning(f"⚠️ Worker: Folder 관리 시스템 로드 실패: {e}")
    folder_manager = None
    FOLDER_MANAGER_AVAILABLE = False

logger.info("🤖 Worker 프로세스 시작")

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
            title_font_size = video_params.get('title_font_size', 42)
            body_font_size = video_params.get('body_font_size', 36)
            # 자막 읽어주기 파라미터 추출
            voice_narration = video_params.get('voice_narration', 'enabled')
            # 크로스 디졸브 파라미터 추출
            cross_dissolve = video_params.get('cross_dissolve', 'enabled')
            # 자막 지속 시간 파라미터 추출
            subtitle_duration = video_params.get('subtitle_duration', 0.0)

            # 영상 파라미터 로깅
            logger.info(f"📋 영상 파라미터: 음악={music_mood}, 테스트파일={use_test_files}, 텍스트위치={text_position}, 타이틀폰트={title_font}({title_font_size}pt), 본문폰트={body_font}({body_font_size}pt), 자막음성={voice_narration}, 크로스디졸브={cross_dissolve}, 자막지속시간={subtitle_duration}초")
            logger.debug(f"🔍 voice_narration='{voice_narration}' (타입: {type(voice_narration).__name__})")
            logger.debug(f"🔍 subtitle_duration={subtitle_duration} (타입: {type(subtitle_duration).__name__})")

            # 콘텐츠 데이터 파싱
            try:
                content = json.loads(content_data) if isinstance(content_data, str) else content_data
                video_title = content.get('title', '릴스 영상')

                # 🎯 수정된 텍스트 적용 (per-two-scripts 모드)
                edited_texts_str = video_params.get('edited_texts', '{}')
                try:
                    edited_texts_dict = json.loads(edited_texts_str) if isinstance(edited_texts_str, str) else edited_texts_str
                    if edited_texts_dict:
                        logger.info(f"📝 수정된 텍스트 적용: {len(edited_texts_dict)}개 이미지 인덱스")
                        for image_idx_str, texts in edited_texts_dict.items():
                            image_idx = int(image_idx_str)
                            # per-two-scripts: imageIndex * 2로 body 인덱스 계산
                            text_idx = image_idx * 2
                            if texts and len(texts) > 0 and texts[0]:
                                body_key = f'body{text_idx + 1}'
                                content[body_key] = texts[0]
                                logger.info(f"✏️ {body_key} 수정: {texts[0][:30]}...")
                            if texts and len(texts) > 1 and texts[1]:
                                body_key = f'body{text_idx + 2}'
                                content[body_key] = texts[1]
                                logger.info(f"✏️ {body_key} 수정: {texts[1][:30]}...")
                except (json.JSONDecodeError, ValueError, KeyError) as e:
                    logger.warning(f"⚠️ 수정된 텍스트 파싱 실패, 원본 사용: {e}")
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

            # uploads 폴더 설정 - Job 폴더 우선 사용
            if FOLDER_MANAGER_AVAILABLE:
                try:
                    # Job별 고유 폴더 사용
                    job_uploads_folder, job_output_folder = folder_manager.get_job_folders(job_id)
                    uploads_folder = job_uploads_folder
                    # output_folder도 job별 폴더 사용 (월별 구조)
                    output_folder = job_output_folder
                    logger.info(f"📁 Job 폴더 사용: {uploads_folder}")
                    logger.info(f"📁 Job 출력 폴더: {output_folder}")
                except Exception as job_error:
                    logger.warning(f"⚠️ Job 폴더 가져오기 실패, 기본 폴더 사용: {job_error}")
                    uploads_folder = os.path.join(current_dir, "uploads")
            else:
                # Folder Manager 미사용 시 기본 폴더
                uploads_folder = os.path.join(current_dir, "uploads")
                logger.info(f"📁 기본 폴더 사용: {uploads_folder}")

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
                    title_font_size=title_font_size,
                    body_font_size=body_font_size,
                    music_mood=music_mood,
                    voice_narration=voice_narration,
                    cross_dissolve=cross_dissolve,
                    subtitle_duration=subtitle_duration
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
                    title_font_size=title_font_size,
                    body_font_size=body_font_size,
                    music_mood=music_mood,
                    voice_narration=voice_narration,
                    cross_dissolve=cross_dissolve,
                    subtitle_duration=subtitle_duration
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

                # 실패 이메일 발송은 재시도 불가능할 때만 (run 메서드에서 처리)
                # 이렇게 하면 재시도마다 이메일이 발송되지 않음

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

            # 실패 이메일 발송은 재시도 불가능할 때만 (run 메서드에서 처리)
            # 이렇게 하면 재시도마다 이메일이 발송되지 않음

            return False

        finally:
            # Job 폴더 정리 (성공/실패 관계없이)
            if FOLDER_MANAGER_AVAILABLE:
                try:
                    logger.info(f"🗑️ Job 폴더 정리 시작: {job_id}")
                    cleaned = folder_manager.cleanup_job_folders(job_id, keep_output=True)
                    if cleaned:
                        logger.info(f"✅ Job 폴더 정리 완료: {job_id}")
                    else:
                        logger.warning(f"⚠️ Job 폴더 정리 부분 실패: {job_id}")
                except Exception as cleanup_error:
                    logger.error(f"❌ Job 폴더 정리 실패: {job_id} - {cleanup_error}")
            else:
                logger.info(f"ℹ️ Folder Manager 미사용으로 폴더 정리 생략: {job_id}")

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
                        can_retry = job_queue.retry_job(job_id)
                        if can_retry:
                            logger.info(f"🔄 작업 재시도 큐에 추가: {job_id}")
                        else:
                            # 최대 재시도 횟수 초과 - 최종 실패 이메일 발송
                            logger.error(f"💀 최종 실패: {job_id} - 실패 이메일 발송")
                            try:
                                # job_data에서 user_email 추출
                                user_email = job_data.get('user_email', 'unknown')

                                # job_queue에서 최신 error_message 가져오기
                                latest_job_data = job_queue.get_job(job_id)
                                error_msg = latest_job_data.get('error_message', '알 수 없는 오류') if latest_job_data else '작업 처리 실패'

                                email_service.send_error_email(
                                    user_email=user_email,
                                    job_id=job_id,
                                    error_message=error_msg
                                )
                                logger.info(f"📧 최종 실패 이메일 발송 완료: {user_email}")
                            except Exception as email_error:
                                logger.error(f"❌ 실패 이메일 발송 실패: {email_error}")

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