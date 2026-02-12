"""
Qwen3-TTS 서비스 모듈
Intel Celeron J4125 + 16GB 메모리 저사양 환경에 최적화된 TTS 서비스

사용 모델: Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice (0.6B 경량 모델)
지원 화자: Sohee(한국어), Vivian, Serena, Uncle_Fu, Dylan, Eric, Ryan, Aiden, Ono_Anna
"""

import os
import tempfile
import logging
from typing import Optional, Tuple
import numpy as np

# 통합 로깅 시스템
from utils.logger_config import get_logger
logger = get_logger('qwen_tts')

# Qwen TTS 사용 가능 여부
QWEN_TTS_AVAILABLE = False
_qwen_model = None
_qwen_model_loaded = False

# 지원되는 화자 목록
QWEN_SPEAKERS = {
    'Sohee': {'language': 'Korean', 'description': '한국어 여성 (기본)'},
    'Vivian': {'language': 'Chinese', 'description': '중국어 여성'},
    'Serena': {'language': 'Chinese', 'description': '중국어 여성'},
    'Uncle_Fu': {'language': 'Chinese', 'description': '중국어 남성'},
    'Dylan': {'language': 'Chinese', 'description': '중국어 남성'},
    'Eric': {'language': 'Chinese', 'description': '중국어 남성'},
    'Ryan': {'language': 'English', 'description': '영어 남성'},
    'Aiden': {'language': 'English', 'description': '영어 남성'},
    'Ono_Anna': {'language': 'Japanese', 'description': '일본어 여성'},
}

# 속도 프리셋 (instruct 파라미터용) - 기본값을 빠르고 명확하게 설정
SPEED_PRESETS = {
    'very_slow': 'Speak very slowly and clearly',
    'slow': 'Speak slowly',
    'normal': 'Speak at a brisk, energetic pace with clear pronunciation. Do not speak slowly.',
    'fast': 'Speak quickly and clearly',
    'very_fast': 'Speak very quickly and energetically',
}

# 스타일 프리셋 (말투/감정 스타일) - 크고 명확한 발성 기본 적용
STYLE_PRESETS = {
    'neutral': {
        'description': '기본 (자연스러운 말투)',
        'prompt': 'Speak naturally with a neutral tone. Project your voice clearly and loudly.'
    },
    'cheerful_witty': {
        'description': '쾌활하게 익살스러운 목소리로',
        'prompt': 'Speak cheerfully and playfully with a witty, humorous tone. Be energetic and lively. Project your voice clearly and loudly.'
    },
    'cynical_calm': {
        'description': '덤덤한 말투로 시니컬하게',
        'prompt': 'Speak in a calm, indifferent tone with a cynical and dry delivery. Be deadpan and matter-of-fact. Project your voice clearly.'
    },
    'calm_emotional': {
        'description': '차분하고 감성적인 목소리',
        'prompt': 'Speak in a calm, soft, and emotionally warm tone. Be gentle and sentimental, as if telling a heartfelt story. Project your voice clearly.'
    },
}


def check_qwen_tts_availability() -> bool:
    """Qwen TTS 라이브러리 사용 가능 여부 확인"""
    global QWEN_TTS_AVAILABLE
    try:
        from qwen_tts import Qwen3TTSModel
        QWEN_TTS_AVAILABLE = True
        logger.info("✅ Qwen TTS 라이브러리 사용 가능")
        return True
    except ImportError as e:
        logger.warning(f"⚠️ Qwen TTS 라이브러리 미설치: {e}")
        logger.info("pip install -U qwen-tts 로 설치하세요")
        QWEN_TTS_AVAILABLE = False
        return False


def get_local_model_path() -> Optional[str]:
    """
    로컬 모델 경로 반환 (backend/qwen 폴더)

    다음 구조를 지원:
    1. backend/qwen/config.json (직접 복사)
    2. backend/qwen/models--Qwen--Qwen3-TTS-12Hz-0.6B-CustomVoice/snapshots/*/config.json (HuggingFace 캐시 구조)
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    qwen_dir = os.path.join(current_dir, "qwen")

    # 1. 직접 복사된 경우 (config.json이 qwen 폴더에 바로 있음)
    if os.path.exists(os.path.join(qwen_dir, "config.json")):
        return qwen_dir

    # 2. HuggingFace 캐시 구조인 경우
    hf_cache_model_dir = os.path.join(qwen_dir, "models--Qwen--Qwen3-TTS-12Hz-0.6B-CustomVoice", "snapshots")
    if os.path.exists(hf_cache_model_dir):
        # snapshots 폴더 내 첫 번째 디렉토리 (해시값) 찾기
        try:
            snapshot_dirs = [d for d in os.listdir(hf_cache_model_dir)
                           if os.path.isdir(os.path.join(hf_cache_model_dir, d)) and not d.startswith('.')]
            if snapshot_dirs:
                snapshot_path = os.path.join(hf_cache_model_dir, snapshot_dirs[0])
                if os.path.exists(os.path.join(snapshot_path, "config.json")):
                    logger.info(f"🔍 HuggingFace 캐시 구조 감지: {snapshot_path}")
                    return snapshot_path
        except Exception as e:
            logger.warning(f"⚠️ HuggingFace 캐시 경로 탐색 실패: {e}")

    return None


def load_qwen_model(force_reload: bool = False) -> bool:
    """
    Qwen TTS 모델 로드 (저사양 최적화)

    - 싱글톤 패턴으로 메모리 효율적 관리
    - CPU 추론 최적화
    - 0.6B 경량 모델 사용
    - 로컬 모델 경로 우선 사용 (backend/qwen)
    """
    global _qwen_model, _qwen_model_loaded, QWEN_TTS_AVAILABLE

    if not QWEN_TTS_AVAILABLE:
        if not check_qwen_tts_availability():
            return False

    if _qwen_model_loaded and not force_reload:
        logger.info("✅ Qwen TTS 모델 이미 로드됨 (캐시 사용)")
        return True

    try:
        import torch
        from qwen_tts import Qwen3TTSModel

        # 로컬 모델 경로 확인
        local_model_path = get_local_model_path()

        # 로컬 경로에 모델이 있는지 확인
        if local_model_path:
            model_path = local_model_path
            logger.info(f"🔄 Qwen TTS 모델 로딩 시작 (로컬 경로: {local_model_path})...")
        else:
            model_path = "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"
            logger.info(f"🔄 Qwen TTS 모델 로딩 시작 (HuggingFace 허브)...")
            logger.info(f"ℹ️ 로컬 모델을 사용하려면 backend/qwen 폴더에 모델 파일을 복사하세요.")

        # 모델 로드 (Qwen3TTSModel은 래퍼 클래스로 내부적으로 device 관리)
        _qwen_model = Qwen3TTSModel.from_pretrained(
            model_path,
            dtype=torch.float32,  # CPU에서는 float32 사용
        )

        # Qwen3TTSModel은 래퍼 클래스라 .to(), .eval() 메서드 없음
        # 내부적으로 CPU/GPU 관리됨

        _qwen_model_loaded = True
        logger.info("✅ Qwen TTS 모델 로딩 완료")
        return True

    except Exception as e:
        logger.error(f"❌ Qwen TTS 모델 로딩 실패: {e}")
        import traceback
        traceback.print_exc()
        _qwen_model = None
        _qwen_model_loaded = False
        return False


def unload_qwen_model():
    """Qwen TTS 모델 언로드 (메모리 해제)"""
    global _qwen_model, _qwen_model_loaded

    if _qwen_model is not None:
        try:
            import gc
            import torch

            del _qwen_model
            _qwen_model = None
            _qwen_model_loaded = False

            # 가비지 컬렉션 강제 실행
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            logger.info("✅ Qwen TTS 모델 언로드 완료")
        except Exception as e:
            logger.warning(f"⚠️ 모델 언로드 중 오류: {e}")


def generate_speech_qwen(
    text: str,
    speaker: str = "Sohee",
    speed: str = "normal",
    style: str = "neutral",
    output_format: str = "mp3"
) -> Optional[str]:
    """
    Qwen TTS로 음성 생성

    Args:
        text: 변환할 텍스트
        speaker: 화자 이름 (기본: Sohee - 한국어)
        speed: 속도 프리셋 (very_slow, slow, normal, fast, very_fast)
        style: 스타일 프리셋 (neutral, cheerful_witty, cynical_calm)
        output_format: 출력 형식 (mp3, wav)

    Returns:
        생성된 오디오 파일 경로 또는 None
    """
    global _qwen_model, _qwen_model_loaded

    # 모델 로드 확인
    if not _qwen_model_loaded:
        if not load_qwen_model():
            logger.error("❌ Qwen TTS 모델 로드 실패")
            return None

    try:
        import torch
        import soundfile as sf

        logger.info(f"🎙️ Qwen TTS 생성 중: {text[:50]}... (화자: {speaker}, 속도: {speed}, 스타일: {style})")

        # 화자 검증
        if speaker not in QWEN_SPEAKERS:
            logger.warning(f"⚠️ 알 수 없는 화자 '{speaker}', 기본값 'Sohee' 사용")
            speaker = "Sohee"

        # 스타일 검증
        if style not in STYLE_PRESETS:
            logger.warning(f"⚠️ 알 수 없는 스타일 '{style}', 기본값 'neutral' 사용")
            style = "neutral"

        # 언어 자동 감지
        language = "Auto"

        # 속도 + 스타일 지시문 조합
        speed_instruction = SPEED_PRESETS.get(speed, SPEED_PRESETS['normal'])
        style_instruction = STYLE_PRESETS[style]['prompt']

        # 최종 지시문: 스타일 + 속도 조합
        combined_instruction = f"{style_instruction} {speed_instruction}."
        logger.debug(f"📝 TTS 지시문: {combined_instruction}")

        # 음성 생성 (CPU 최적화 - no_grad 컨텍스트)
        with torch.no_grad():
            wavs, sample_rate = _qwen_model.generate_custom_voice(
                text=text,
                language=language,
                speaker=speaker,
                instruct=combined_instruction,
                do_sample=True,
            )

        # 결과 검증
        if wavs is None or len(wavs) == 0:
            logger.error("❌ 음성 생성 실패: 빈 결과")
            return None

        # numpy 배열로 변환
        if isinstance(wavs, torch.Tensor):
            audio_data = wavs.cpu().numpy()
        else:
            audio_data = np.array(wavs)

        # 1차원으로 변환
        if audio_data.ndim > 1:
            audio_data = audio_data.squeeze()

        # 임시 파일에 저장
        suffix = f".{output_format}"
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        temp_path = temp_file.name
        temp_file.close()

        # soundfile로 저장
        sf.write(temp_path, audio_data, sample_rate)

        logger.info(f"✅ Qwen TTS 생성 완료: {temp_path}")
        return temp_path

    except Exception as e:
        logger.error(f"❌ Qwen TTS 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_available_speakers() -> dict:
    """사용 가능한 화자 목록 반환"""
    return QWEN_SPEAKERS.copy()


def get_speed_presets() -> dict:
    """사용 가능한 속도 프리셋 목록 반환"""
    return SPEED_PRESETS.copy()


def get_style_presets() -> dict:
    """사용 가능한 스타일 프리셋 목록 반환"""
    return STYLE_PRESETS.copy()


class QwenTTSService:
    """
    Qwen TTS 서비스 클래스
    VideoGenerator에서 사용하기 위한 래퍼 클래스
    """

    def __init__(self, preload_model: bool = False):
        """
        초기화

        Args:
            preload_model: True면 초기화 시 모델 미리 로드 (메모리 사용량 증가)
        """
        self.is_available = check_qwen_tts_availability()
        self.speaker = "Sohee"  # 기본 화자 (한국어)
        self.speed = "normal"   # 기본 속도
        self.style = "neutral"  # 기본 스타일

        if preload_model and self.is_available:
            load_qwen_model()

    def set_speaker(self, speaker: str):
        """화자 설정"""
        if speaker in QWEN_SPEAKERS:
            self.speaker = speaker
            logger.info(f"🎤 화자 설정: {speaker} ({QWEN_SPEAKERS[speaker]['description']})")
        else:
            logger.warning(f"⚠️ 알 수 없는 화자 '{speaker}', 현재 설정 유지: {self.speaker}")

    def set_speed(self, speed: str):
        """속도 설정"""
        if speed in SPEED_PRESETS:
            self.speed = speed
            logger.info(f"⏱️ 속도 설정: {speed}")
        else:
            logger.warning(f"⚠️ 알 수 없는 속도 '{speed}', 현재 설정 유지: {self.speed}")

    def set_style(self, style: str):
        """스타일 설정"""
        if style in STYLE_PRESETS:
            self.style = style
            logger.info(f"🎭 스타일 설정: {style} ({STYLE_PRESETS[style]['description']})")
        else:
            logger.warning(f"⚠️ 알 수 없는 스타일 '{style}', 현재 설정 유지: {self.style}")

    def generate(self, text: str, output_format: str = "mp3") -> Optional[str]:
        """
        음성 생성

        Args:
            text: 변환할 텍스트
            output_format: 출력 형식 (mp3, wav)

        Returns:
            생성된 오디오 파일 경로 또는 None
        """
        if not self.is_available:
            logger.error("❌ Qwen TTS를 사용할 수 없습니다")
            return None

        return generate_speech_qwen(
            text=text,
            speaker=self.speaker,
            speed=self.speed,
            style=self.style,
            output_format=output_format
        )

    def cleanup(self):
        """리소스 정리"""
        unload_qwen_model()


# 모듈 로드 시 사용 가능 여부 확인
check_qwen_tts_availability()
