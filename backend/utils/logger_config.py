"""
통합 로깅 시스템 설정
모든 모듈에서 일관된 로깅 제공
"""
import logging
import os
import shutil
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# 환경변수로 모듈별 로그 레벨 제어
LOG_LEVELS = {
    'main': os.getenv('LOG_LEVEL_MAIN', 'INFO'),
    'video_generator': os.getenv('LOG_LEVEL_VIDEO_GENERATOR', 'INFO'),
    'worker': os.getenv('LOG_LEVEL_WORKER', 'INFO'),
    'routers': os.getenv('LOG_LEVEL_ROUTERS', 'INFO'),
    'services': os.getenv('LOG_LEVEL_SERVICES', 'INFO'),
    'job_queue': os.getenv('LOG_LEVEL_JOB_QUEUE', 'INFO'),
    'email_service': os.getenv('LOG_LEVEL_EMAIL_SERVICE', 'INFO'),
    'job_logger': os.getenv('LOG_LEVEL_JOB_LOGGER', 'INFO'),
    'folder_manager': os.getenv('LOG_LEVEL_FOLDER_MANAGER', 'INFO'),
    'thumbnail_generator': os.getenv('LOG_LEVEL_THUMBNAIL_GENERATOR', 'INFO'),
    'media_asset_manager': os.getenv('LOG_LEVEL_MEDIA_ASSET_MANAGER', 'INFO'),
    'cleanup_scheduler': os.getenv('LOG_LEVEL_CLEANUP_SCHEDULER', 'INFO'),
    'default': os.getenv('LOG_LEVEL_DEFAULT', 'INFO'),
}

# 통합 로그 파일
LOG_FILE = "backend.log"
LOG_BACKUP_DIR = "log/backendlog"
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5

# 이미 설정된 로거들을 캐시
_loggers = {}
_log_initialized = False


def backup_existing_log():
    """
    서버 시작 시 기존 backend.log를 백업 폴더로 이동
    파일명 형식: backend_until20251002_143025.log
    """
    global _log_initialized

    # 이미 초기화되었으면 스킵 (중복 실행 방지)
    if _log_initialized:
        return

    _log_initialized = True

    # 기존 로그 파일이 없으면 스킵
    if not os.path.exists(LOG_FILE):
        return

    # 백업 디렉토리 생성
    os.makedirs(LOG_BACKUP_DIR, exist_ok=True)

    # 현재 시간으로 백업 파일명 생성
    now = datetime.now()
    backup_filename = f"backend_until{now.strftime('%Y%m%d_%H%M%S')}.log"
    backup_path = os.path.join(LOG_BACKUP_DIR, backup_filename)

    # 기존 로그 파일 이동
    try:
        shutil.move(LOG_FILE, backup_path)
        print(f"📦 기존 로그 백업 완료: {backup_path}")
    except Exception as e:
        print(f"⚠️ 로그 백업 실패: {e}")


def setup_logger(module_name: str) -> logging.Logger:
    """
    모듈별 로거 생성

    Args:
        module_name: 모듈 이름 (예: 'video_generator', 'main', 'worker')

    Returns:
        설정된 Logger 객체
    """
    # 첫 로거 생성 시 기존 로그 백업
    backup_existing_log()

    # 이미 생성된 로거가 있으면 반환
    if module_name in _loggers:
        return _loggers[module_name]

    logger = logging.getLogger(module_name)

    # 로그 레벨 설정 (모듈별 또는 기본값)
    log_level_str = LOG_LEVELS.get(module_name, LOG_LEVELS['default'])
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    logger.setLevel(log_level)

    # 이미 핸들러가 있으면 재설정 방지
    if logger.handlers:
        _loggers[module_name] = logger
        return logger

    # 공통 포맷 (모듈명 포함)
    formatter = logging.Formatter(
        '%(asctime)s - [%(name)s] - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 파일 핸들러 (로테이션)
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 콘솔 핸들러 (운영 환경에서는 비활성화 가능)
    if os.getenv('LOG_CONSOLE', 'false').lower() == 'true':
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # 캐시에 저장
    _loggers[module_name] = logger

    return logger


def get_logger(module_name: str) -> logging.Logger:
    """
    로거 가져오기 (캐싱)

    Usage:
        from utils.logger_config import get_logger
        logger = get_logger(__name__)
        logger.info("메시지")
    """
    return setup_logger(module_name)
