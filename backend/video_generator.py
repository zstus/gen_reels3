import os
import subprocess
import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps
from moviepy.editor import *
import numpy as np
import uuid
import tempfile
import edge_tts
import asyncio
import re
import base64
import json
import random
import math
import logging
from datetime import datetime

# 통합 로깅 시스템 import
from utils.logger_config import get_logger
logger = get_logger('video_generator')

# Qwen TTS 서비스 import
try:
    from qwen_tts_service import (
        QwenTTSService,
        QWEN_TTS_AVAILABLE,
        QWEN_SPEAKERS,
        SPEED_PRESETS,
        check_qwen_tts_availability
    )
    logger.info(f"✅ Qwen TTS 모듈 로드 성공 (사용 가능: {QWEN_TTS_AVAILABLE})")
except ImportError as e:
    logger.warning(f"⚠️ Qwen TTS 모듈 로드 실패: {e}")
    QWEN_TTS_AVAILABLE = False
    QwenTTSService = None
    QWEN_SPEAKERS = {}
    SPEED_PRESETS = {}

# HEIC 파일 지원을 위한 pillow-heif
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    logger.info("✅ HEIC 파일 지원 활성화")
except ImportError:
    logger.warning("⚠️ pillow-heif 미설치 - HEIC 파일 지원 불가")

class VideoGenerator:
    def __init__(self):
        # 통합 로깅 시스템 사용 (더 이상 개별 로그 파일 생성 안함)
        logger.info("🎬 VideoGenerator 초기화")

        self.video_width = 504
        self.video_height = 890  # 쇼츠/릴스 해상도 (504x890)
        self.fps = 30

        # 레이아웃 설정 (릴스 기본값)
        self.title_height = 220
        self.work_height_keep = 670      # title_area_mode='keep'일 때 (video_height - title_height)
        self.work_height_remove = 890    # title_area_mode='remove'일 때 (video_height)
        self.text_y_top = 430            # 상단 텍스트 영역 중앙 Y
        self.text_y_bottom = 610         # 하단 텍스트 영역 중앙 Y
        self.text_y_bottom_edge_margin = 80  # 최하단 텍스트 여백
        self.panning_range = 60          # 패닝 최대 범위 (px)
        self.font_path = os.path.join(os.path.dirname(__file__), "font", "BMYEONSUNG_otf.otf")

        # Naver Clova Voice 설정 (환경변수에서 가져오기)
        self.naver_client_id = os.getenv('NAVER_CLIENT_ID')
        self.naver_client_secret = os.getenv('NAVER_CLIENT_SECRET')

        # Microsoft Azure Speech 설정
        self.azure_speech_key = os.getenv('AZURE_SPEECH_KEY')
        self.azure_speech_region = os.getenv('AZURE_SPEECH_REGION', 'koreacentral')

        # 발음 사전 초기화 (다국어 → 한글 발음 변환)
        from utils.pronunciation_dict import PronunciationDictionary
        self.pronunciation_dict = PronunciationDictionary()
        logger.info("📚 발음 사전 초기화 완료")

        # 외부 사전 파일이 있으면 로드 (선택사항)
        custom_dict_path = os.path.join(os.path.dirname(__file__), "pronunciation_dict.json")
        if os.path.exists(custom_dict_path):
            self.pronunciation_dict.load_from_file(custom_dict_path)
            logger.info(f"📚 커스텀 발음 사전 로드: {custom_dict_path}")

        # Qwen TTS 서비스 초기화 (지연 로딩)
        self.qwen_tts_service = None
        self.tts_engine = "edge"  # 기본 TTS 엔진: edge
        self.qwen_speaker = "Sohee"  # 기본 Qwen 화자 (한국어)
        self.qwen_speed = "normal"   # 기본 Qwen 속도
        self.qwen_style = "neutral"  # 기본 Qwen 스타일
        self.per_body_tts_settings = None  # 대사별 TTS 설정 (None이면 전역 설정 사용)
        self.edge_speaker = "female"   # 기본 Edge 화자
        self.edge_speed = "normal"     # 기본 Edge 속도
        self.edge_pitch = "normal"     # 기본 Edge 톤
        logger.info(f"🎤 기본 TTS 엔진: {self.tts_engine}")

    def set_video_format(self, video_format: str):
        """
        영상 포맷 설정 (레이아웃 관련 인스턴스 변수 일괄 변경)

        Args:
            video_format: 'reels' (세로 504x890) 또는 'youtube' (가로 1280x720)
        """
        if video_format == 'youtube':
            self.video_width = 1280
            self.video_height = 720
            self.title_height = 120
            self.work_height_keep = 600
            self.work_height_remove = 720
            self.text_y_top = 340
            self.text_y_bottom = 520
            self.text_y_bottom_edge_margin = 60
            self.panning_range = 60
        else:  # reels (기본값)
            self.video_width = 504
            self.video_height = 890
            self.title_height = 220
            self.work_height_keep = 670
            self.work_height_remove = 890
            self.text_y_top = 430
            self.text_y_bottom = 610
            self.text_y_bottom_edge_margin = 80
            self.panning_range = 60
        logger.info(f"🎬 영상 포맷 설정: {video_format} ({self.video_width}x{self.video_height})")

    def get_video_rotation(self, video_path):
        """ffprobe로 비디오 회전 메타데이터 감지

        iPhone 등 스마트폰 촬영 영상은 1920x1080으로 저장하고 회전 메타데이터(90°/270°)로
        세로 방향을 표시합니다. MoviePy는 이를 올바르게 처리하지 못해 영상이 찌그러집니다.

        Returns:
            int: 회전 각도 (0, 90, 180, 270)
        """
        try:
            # 방법 1: stream_tags에서 rotate 태그 확인
            result = subprocess.run(
                ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                 '-show_entries', 'stream_tags=rotate',
                 '-of', 'default=noprint_wrappers=1:nokey=1',
                 video_path],
                capture_output=True, text=True, timeout=10
            )
            rotation_str = result.stdout.strip()
            if rotation_str:
                rotation = int(rotation_str)
                print(f"🔍 ffprobe 회전 감지 (stream_tags): {rotation}°")
                return rotation

            # 방법 2: side_data에서 rotation 확인 (일부 MOV 컨테이너)
            result2 = subprocess.run(
                ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                 '-show_entries', 'side_data=rotation',
                 '-of', 'default=noprint_wrappers=1:nokey=1',
                 video_path],
                capture_output=True, text=True, timeout=10
            )
            rotation_str2 = result2.stdout.strip()
            if rotation_str2:
                rotation = int(float(rotation_str2))
                print(f"🔍 ffprobe 회전 감지 (side_data): {rotation}°")
                return rotation

            # 방법 3: displaymatrix에서 회전 확인 (최신 FFmpeg)
            result3 = subprocess.run(
                ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                 '-show_entries', 'stream_side_data_list',
                 '-of', 'json',
                 video_path],
                capture_output=True, text=True, timeout=10
            )
            if result3.stdout.strip():
                try:
                    probe_data = json.loads(result3.stdout)
                    for stream in probe_data.get('streams', []):
                        for side_data in stream.get('side_data_list', []):
                            if 'rotation' in side_data:
                                rotation = int(float(side_data['rotation']))
                                print(f"🔍 ffprobe 회전 감지 (side_data_list): {rotation}°")
                                return rotation
                            if 'displaymatrix' in side_data:
                                display_matrix = side_data['displaymatrix']
                                print(f"🔍 ffprobe displaymatrix 감지: {display_matrix}")
                                # displaymatrix에서 회전 추출
                                if 'rotation' in side_data:
                                    return int(float(side_data['rotation']))
                except (json.JSONDecodeError, KeyError, ValueError):
                    pass

            # 방법 4: ffprobe 전체 출력에서 "rotation" 검색 (최종 fallback)
            result4 = subprocess.run(
                ['ffprobe', '-v', 'verbose', '-select_streams', 'v:0',
                 '-show_streams',
                 video_path],
                capture_output=True, text=True, timeout=10
            )
            full_output = result4.stdout + result4.stderr
            rotation_match = re.search(r'rotation\s*[=:]\s*(-?\d+)', full_output)
            if rotation_match:
                rotation = int(rotation_match.group(1))
                # 음수 회전을 양수로 변환 (예: -90 → 270)
                if rotation < 0:
                    rotation = 360 + rotation
                print(f"🔍 ffprobe 회전 감지 (verbose 검색): {rotation}°")
                return rotation

            print(f"✅ 회전 메타데이터 없음: 0°")
            return 0

        except FileNotFoundError:
            print(f"⚠️ ffprobe를 찾을 수 없습니다. 회전 감지 불가.")
            return 0
        except Exception as e:
            print(f"⚠️ 회전 메타데이터 감지 실패: {e}")
            return 0

    def normalize_video_rotation(self, video_path):
        """회전 메타데이터가 있는 비디오를 정상 방향으로 변환

        FFmpeg로 회전을 실제 픽셀에 적용하고 메타데이터를 제거한 임시 파일을 생성합니다.
        MoviePy의 잘못된 프레임 reshape 문제를 근본적으로 해결합니다.

        Returns:
            tuple: (사용할_비디오_경로, 임시파일_여부)
        """
        rotation = self.get_video_rotation(video_path)

        if rotation == 0:
            print(f"✅ 회전 없음, 원본 사용: {os.path.basename(video_path)}")
            return video_path, False

        print(f"🔄 비디오 회전 정상화 시작: {rotation}° → 0° ({os.path.basename(video_path)})")

        # 임시 파일 경로 생성
        temp_dir = tempfile.gettempdir()
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        temp_path = os.path.join(temp_dir, f"rotfix_{base_name}_{uuid.uuid4().hex[:8]}.mp4")

        try:
            # FFmpeg로 회전 적용 + 메타데이터 제거
            # FFmpeg은 자동으로 rotation 메타데이터를 적용하여 프레임을 올바른 방향으로 출력
            result = subprocess.run(
                ['ffmpeg', '-i', video_path,
                 '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '18',
                 '-an',       # 오디오 불필요 (TTS 별도 사용)
                 '-y',        # 기존 파일 덮어쓰기
                 temp_path],
                capture_output=True, text=True, timeout=120
            )

            if result.returncode == 0 and os.path.exists(temp_path):
                # 변환 후 실제 크기 확인
                probe = subprocess.run(
                    ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                     '-show_entries', 'stream=width,height',
                     '-of', 'csv=p=0',
                     temp_path],
                    capture_output=True, text=True, timeout=10
                )
                new_dims = probe.stdout.strip()
                print(f"✅ 회전 정상화 완료: {rotation}° → 0° (새 크기: {new_dims})")
                return temp_path, True
            else:
                print(f"⚠️ FFmpeg 회전 변환 실패 (returncode={result.returncode})")
                if result.stderr:
                    # 에러 로그 마지막 3줄만 출력
                    stderr_lines = result.stderr.strip().split('\n')
                    for line in stderr_lines[-3:]:
                        print(f"   FFmpeg: {line}")
                return video_path, False

        except subprocess.TimeoutExpired:
            print(f"⚠️ FFmpeg 회전 변환 타임아웃 (120초 초과)")
            return video_path, False
        except Exception as e:
            print(f"⚠️ 비디오 회전 변환 실패: {e}")
            return video_path, False

    def set_tts_engine(self, engine: str, speaker: str = None, speed: str = None, style: str = None, per_body_tts_settings: dict = None, edge_speaker: str = None, edge_speed: str = None, edge_pitch: str = None):
        """
        TTS 엔진 설정

        Args:
            engine: 'edge' 또는 'qwen'
            speaker: Qwen 화자 (Sohee, Vivian 등)
            speed: Qwen 속도 (very_slow, slow, normal, fast, very_fast)
            style: Qwen 스타일 (neutral, cheerful_witty, cynical_calm)
            per_body_tts_settings: 대사별 TTS 설정 dict (예: {"body1": {"speaker": "Sohee", "style": "cheerful_witty"}, ...})
            edge_speaker: Edge TTS 화자 (female, male_news, male_young)
            edge_speed: Edge TTS 속도 (fast, normal, slow)
            edge_pitch: Edge TTS 톤 (high, normal, low)
        """
        if engine not in ['edge', 'qwen']:
            logger.warning(f"⚠️ 알 수 없는 TTS 엔진 '{engine}', 기본값 'edge' 사용")
            engine = 'edge'

        self.tts_engine = engine
        logger.info(f"🎤 TTS 엔진 설정: {engine}")

        if engine == 'edge':
            if edge_speaker:
                self.edge_speaker = edge_speaker
            if edge_speed:
                self.edge_speed = edge_speed
            if edge_pitch:
                self.edge_pitch = edge_pitch
            logger.info(f"🔊 Edge TTS 설정: 화자={self.edge_speaker}, 속도={self.edge_speed}, 톤={self.edge_pitch}")
        elif engine == 'qwen':
            if speaker:
                self.qwen_speaker = speaker
                logger.info(f"🎤 Qwen 화자 설정: {speaker}")
            if speed:
                self.qwen_speed = speed
                logger.info(f"⏱️ Qwen 속도 설정: {speed}")
            if style:
                self.qwen_style = style
                logger.info(f"🎭 Qwen 스타일 설정: {style}")

        # 대사별 TTS 설정 저장 (명시적으로 전달된 경우에만 덮어쓰기)
        if per_body_tts_settings is not None:
            self.per_body_tts_settings = per_body_tts_settings
            if per_body_tts_settings:
                logger.info(f"🎭 대사별 TTS 설정 적용: {list(per_body_tts_settings.keys())}")

    def _init_qwen_tts(self):
        """Qwen TTS 서비스 지연 초기화"""
        if self.qwen_tts_service is None and QWEN_TTS_AVAILABLE and QwenTTSService:
            try:
                self.qwen_tts_service = QwenTTSService(preload_model=False)
                self.qwen_tts_service.set_speaker(self.qwen_speaker)
                self.qwen_tts_service.set_speed(self.qwen_speed)
                self.qwen_tts_service.set_style(self.qwen_style)
                logger.info("✅ Qwen TTS 서비스 초기화 완료")
            except Exception as e:
                logger.error(f"❌ Qwen TTS 서비스 초기화 실패: {e}")
                self.qwen_tts_service = None
        return self.qwen_tts_service is not None

    def create_tts_audio_qwen(self, text, lang='ko'):
        """Qwen TTS로 음성 생성 (저사양 최적화)"""
        try:
            logger.info(f"🎙️ Qwen TTS 생성 중: {text[:50]}...")

            # Qwen TTS 서비스 초기화 확인
            if not self._init_qwen_tts():
                logger.warning("⚠️ Qwen TTS 사용 불가, Edge TTS로 폴백")
                return self.create_tts_audio_edge(text, lang)

            # 화자, 속도, 스타일 설정 업데이트
            self.qwen_tts_service.set_speaker(self.qwen_speaker)
            self.qwen_tts_service.set_speed(self.qwen_speed)
            self.qwen_tts_service.set_style(self.qwen_style)

            # 텍스트 전처리
            processed_text = self.preprocess_korean_text(text)

            # Qwen TTS로 음성 생성
            audio_path = self.qwen_tts_service.generate(processed_text, output_format="mp3")

            if audio_path and os.path.exists(audio_path):
                logger.info(f"✅ Qwen TTS 원본 생성 완료: {audio_path}")

                # 볼륨 정규화 및 증폭 적용
                normalized_path = self._normalize_and_boost_audio(audio_path)
                if normalized_path != audio_path:
                    # 원본 파일 정리
                    if os.path.exists(audio_path):
                        os.unlink(audio_path)
                    audio_path = normalized_path
                    logger.info(f"✅ Qwen TTS 볼륨 정규화 완료: {audio_path}")

                # Qwen 속도 옵션에 따른 후처리 배속 적용
                qwen_speed_factors = {
                    'very_slow': 0.5,
                    'slow': 0.8,
                    'normal': 1.0,
                    'fast': 1.5,
                    'very_fast': 1.8,
                }
                speed_factor = qwen_speed_factors.get(self.qwen_speed, 1.0)
                if speed_factor != 1.0:
                    speed_adjusted_path = self.speed_up_audio(audio_path, speed_factor=speed_factor)
                    if speed_adjusted_path != audio_path and os.path.exists(speed_adjusted_path):
                        if os.path.exists(audio_path):
                            os.unlink(audio_path)
                        audio_path = speed_adjusted_path
                        logger.info(f"✅ Qwen TTS 속도 조정 완료 ({speed_factor}x): {audio_path}")
                else:
                    logger.info(f"✅ Qwen TTS 속도 조정 생략 (normal: 원본 속도 유지)")

                return audio_path
            else:
                logger.warning("⚠️ Qwen TTS 생성 실패, Edge TTS로 폴백")
                return self.create_tts_audio_edge(text, lang)

        except Exception as e:
            logger.error(f"❌ Qwen TTS 생성 오류: {e}")
            logger.info("🔄 Edge TTS로 폴백 시도...")
            return self.create_tts_audio_edge(text, lang)

    def _normalize_and_boost_audio(self, audio_path, target_db=-14.0):
        """오디오 볼륨 정규화 및 증폭 (Qwen TTS용)"""
        try:
            from pydub import AudioSegment
            from pydub.effects import normalize

            logger.info(f"🔊 오디오 볼륨 정규화 시작 (목표: {target_db}dB)")

            # 오디오 로드
            audio = AudioSegment.from_file(audio_path)
            original_dbfs = audio.dBFS
            logger.info(f"📊 원본 볼륨: {original_dbfs:.1f}dBFS")

            # 정규화 적용
            normalized_audio = normalize(audio)

            # 목표 볼륨까지 증폭
            current_dbfs = normalized_audio.dBFS
            boost_db = target_db - current_dbfs
            if boost_db > 0:
                normalized_audio = normalized_audio + boost_db
                logger.info(f"📈 볼륨 증폭: +{boost_db:.1f}dB")

            # 새 파일로 저장
            output_path = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3').name
            normalized_audio.export(output_path, format="mp3")

            final_dbfs = normalized_audio.dBFS
            logger.info(f"✅ 볼륨 정규화 완료: {original_dbfs:.1f}dBFS → {final_dbfs:.1f}dBFS")

            return output_path

        except Exception as e:
            logger.warning(f"⚠️ 볼륨 정규화 실패, 원본 사용: {e}")
            return audio_path

    def create_tts_audio_edge(self, text, lang='ko'):
        """Edge TTS로 음성 생성 (화자/속도/톤 옵션 적용)"""
        try:
            logger.info(f"Edge TTS 생성 중: {text[:50]}...")

            # 한국어 텍스트 전처리 (더 자연스럽게)
            processed_text = self.preprocess_korean_text(text)

            # 화자 매핑
            voice_map = {
                'female': 'ko-KR-SunHiNeural',
                'male_news': 'ko-KR-InJoonNeural',
                'male_young': 'ko-KR-HyunsuNeural',
            }
            voice = voice_map.get(self.edge_speaker, 'ko-KR-SunHiNeural')

            # 속도 매핑
            rate_map = {'fast': '+80%', 'normal': '+40%', 'slow': '+0%'}
            rate = rate_map.get(self.edge_speed, '+40%')

            # 톤 매핑
            pitch_map = {'high': '+5Hz', 'normal': '+0Hz', 'low': '-5Hz'}
            pitch = pitch_map.get(self.edge_pitch, '+0Hz')

            logger.info(f"🔊 Edge TTS 옵션: voice={voice}, rate={rate}, pitch={pitch}")

            # edge-tts는 async이므로 asyncio.run() 사용
            original_temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            original_temp_file.close()

            async def _generate():
                communicate = edge_tts.Communicate(processed_text, voice, rate=rate, pitch=pitch)
                await communicate.save(original_temp_file.name)

            asyncio.run(_generate())
            logger.info(f"Edge TTS 생성 완료: {original_temp_file.name}")

            # Edge TTS 자체에서 속도를 제어하므로 후처리 speed_up_audio 스킵
            return original_temp_file.name

        except Exception as e:
            logger.error(f"Edge TTS 생성 실패: {e}")
            return None

    def get_emoji_font(self):
        """이모지 지원 폰트 경로 반환"""
        emoji_fonts = [
            "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
            "/System/Library/Fonts/Apple Color Emoji.ttc",
            "/Windows/Fonts/seguiemj.ttf",
            "/usr/share/fonts/truetype/noto/NotoEmoji-Regular.ttf"
        ]
        
        for font_path in emoji_fonts:
            if os.path.exists(font_path):
                return font_path
        return None
    
    def has_emoji(self, text):
        """텍스트에 이모지가 포함되어 있는지 확인"""
        emoji_pattern = re.compile(
            "[\U0001F600-\U0001F64F"  # 감정 표현
            "\U0001F300-\U0001F5FF"  # 기호 및 그림문자
            "\U0001F680-\U0001F6FF"  # 교통 및 지도 기호
            "\U0001F1E0-\U0001F1FF"  # 국기
            "\U00002600-\U000026FF"  # 기타 기호
            "\U00002700-\U000027BF"  # 장식 기호
            "\U0001F900-\U0001F9FF"  # 추가 그림문자
            "\U0001FA70-\U0001FAFF"  # 확장된 그림문자-A
            "]+", re.UNICODE)
        return emoji_pattern.search(text) is not None
    
    def split_text_and_emoji(self, text):
        """텍스트와 이모지를 분리"""
        emoji_pattern = re.compile(
            "[\U0001F600-\U0001F64F"
            "\U0001F300-\U0001F5FF"
            "\U0001F680-\U0001F6FF"
            "\U0001F1E0-\U0001F1FF"
            "\U00002600-\U000026FF"
            "\U00002700-\U000027BF"
            "\U0001F900-\U0001F9FF"
            "\U0001FA70-\U0001FAFF"
            "]", re.UNICODE)
        
        parts = []
        last_end = 0
        
        for match in emoji_pattern.finditer(text):
            if match.start() > last_end:
                parts.append(('text', text[last_end:match.start()]))
            parts.append(('emoji', match.group()))
            last_end = match.end()
        
        if last_end < len(text):
            parts.append(('text', text[last_end:]))
        
        return parts
    
    def draw_text_with_emoji(self, draw, text, x, y, text_font, emoji_font, color):
        """텍스트와 이모지를 함께 렌더링"""
        parts = self.split_text_and_emoji(text)
        current_x = x
        
        for part_type, content in parts:
            if part_type == 'text' and content.strip():
                draw.text((current_x, y), content, font=text_font, fill=color)
                bbox = draw.textbbox((0, 0), content, font=text_font)
                current_x += bbox[2] - bbox[0]
            elif part_type == 'emoji':
                # 이모지 폰트가 있으면 사용, 없으면 기본 폰트로 시도
                if emoji_font:
                    try:
                        draw.text((current_x, y + 2), content, font=emoji_font, fill=color)
                        bbox = draw.textbbox((0, 0), content, font=emoji_font)
                    except:
                        # 이모지 폰트 실패시 기본 폰트로 시도
                        draw.text((current_x, y), content, font=text_font, fill=color)
                        bbox = draw.textbbox((0, 0), content, font=text_font)
                else:
                    # 이모지 폰트가 없으면 기본 폰트로 시도
                    draw.text((current_x, y), content, font=text_font, fill=color)
                    bbox = draw.textbbox((0, 0), content, font=text_font)
                
                current_x += bbox[2] - bbox[0]
        
    def create_fallback_image(self, width=1920, height=1080, color_index=0):
        """인터넷 연결 없이 기본 이미지 생성"""
        try:
            # 다양한 색상 팔레트
            colors = [
                (255, 87, 51),   # 주황색
                (51, 255, 87),   # 초록색  
                (51, 87, 255),   # 파란색
                (255, 51, 245),  # 자주색
                (255, 195, 0),   # 노란색
                (0, 195, 255),   # 하늘색
            ]
            
            color = colors[color_index % len(colors)]
            
            # 이미지 생성
            img = Image.new('RGB', (width, height), color=color)
            draw = ImageDraw.Draw(img)
            
            # 텍스트 추가
            try:
                font = ImageFont.truetype(self.font_path, 60)
            except:
                font = ImageFont.load_default()
            
            text = f"배경 이미지 {color_index + 1}"
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (width - text_width) // 2
            y = (height - text_height) // 2
            
            # 텍스트 그림자
            draw.text((x + 2, y + 2), text, font=font, fill=(0, 0, 0))
            # 흰색 텍스트
            draw.text((x, y), text, font=font, fill=(255, 255, 255))
            
            # 임시 파일로 저장
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            img.save(temp_file.name, "JPEG", quality=85)
            temp_file.close()
            
            print(f"기본 이미지 생성 완료: {temp_file.name}")
            return temp_file.name
            
        except Exception as e:
            print(f"기본 이미지 생성 실패: {e}")
            return None

    def download_image(self, image_url):
        """이미지 URL에서 이미지 다운로드 (fallback 포함)"""
        try:
            print(f"이미지 다운로드 시도: {image_url}")
            
            # 타임아웃과 헤더 추가
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(image_url, headers=headers, timeout=10)  # 타임아웃 단축
            
            print(f"응답 상태: {response.status_code}")
            response.raise_for_status()
            
            # 이미지 콘텐츠 유효성 검사
            if len(response.content) < 1000:
                raise Exception(f"이미지 파일이 너무 작습니다: {len(response.content)} bytes")
            
            # 임시 파일로 저장
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            temp_file.write(response.content)
            temp_file.close()
            
            print(f"이미지 다운로드 완료: {temp_file.name} ({len(response.content)} bytes)")
            return temp_file.name
            
        except Exception as e:
            print(f"이미지 다운로드 실패 ({str(e)}), 기본 이미지로 대체")
            # URL에서 색상 인덱스 추출 시도
            color_index = 0
            try:
                if "Image+1" in image_url or "random=1" in image_url:
                    color_index = 0
                elif "Image+2" in image_url or "random=2" in image_url:
                    color_index = 1
                elif "Image+3" in image_url or "random=3" in image_url:
                    color_index = 2
                elif "Image+4" in image_url or "random=4" in image_url:
                    color_index = 3
            except:
                pass
                
            fallback_image = self.create_fallback_image(1920, 1080, color_index)
            if fallback_image:
                return fallback_image
            else:
                raise Exception(f"이미지 다운로드 및 기본 이미지 생성 모두 실패: {str(e)}")

    def parse_colored_title(self, title: str):
        """
        타이틀 텍스트에서 색상 태그 파싱 (기본 색상 + 커스텀 HEX 지원)

        형식 1 (기본 색상): [color:단어]
        형식 2 (커스텀 HEX): [#RRGGBB:단어]

        예시:
        - "나는 [yellow:학교]에서 [blue:친구]를 만났어"
        - "오늘은 [#FF5733:좋은] 날씨입니다"
        - "[yellow:기본]과 [#9B59B6:커스텀] 혼합"

        Args:
            title: 색상 태그가 포함된 타이틀 텍스트

        Returns:
            파트 리스트: [{'text': '나는 ', 'color': 'white'},
                        {'text': '학교', 'color': '#FDCA03'}, ...]
        """
        import re

        # 색상 매핑 (7가지 + 기본 흰색)
        COLOR_MAP = {
            'yellow': '#FDCA03',
            'blue': '#0090FF',
            'red': '#FE0102',
            'green': '#02D330',
            'orange': '#FF822B',
            'mint': '#6FDAA5',
            'sky': '#02FDFE'
        }

        parts = []
        pattern = r'\[([#\w]+):([^\]]+)\]'  # [color:text] 또는 [#HEX:text] 패턴
        last_end = 0

        for match in re.finditer(pattern, title):
            # 태그 앞의 일반 텍스트
            if match.start() > last_end:
                plain_text = title[last_end:match.start()]
                if plain_text:
                    parts.append({'text': plain_text, 'color': 'white'})

            # 색상 태그
            color_input = match.group(1)
            word = match.group(2)

            # 1순위: HEX 색상 코드 체크 (#RRGGBB 형식)
            if color_input.startswith('#') and len(color_input) == 7:
                try:
                    # HEX 코드 유효성 검증 (0-9, A-F)
                    int(color_input[1:], 16)
                    hex_color = color_input.upper()  # 대문자로 통일
                    parts.append({'text': word, 'color': hex_color})
                    logger.info(f"🎨 커스텀 HEX 색상: [{color_input}:{word}] → {hex_color}")
                except ValueError:
                    # 잘못된 HEX 코드는 흰색 처리
                    parts.append({'text': word, 'color': 'white'})
                    logger.warning(f"⚠️ 잘못된 HEX 코드: {color_input}, 흰색으로 처리")
            # 2순위: 기존 색상 이름 (yellow, blue 등)
            elif color_input.lower() in COLOR_MAP:
                color_name = color_input.lower()
                parts.append({'text': word, 'color': COLOR_MAP[color_name]})
                logger.info(f"🎨 색상 이름 감지: [{color_name}:{word}] → {COLOR_MAP[color_name]}")
            # 3순위: 알 수 없는 색상은 흰색으로
            else:
                parts.append({'text': word, 'color': 'white'})
                logger.warning(f"⚠️ 알 수 없는 색상: {color_input}, 흰색으로 처리")

            last_end = match.end()

        # 마지막 남은 텍스트
        if last_end < len(title):
            remaining = title[last_end:]
            if remaining:
                parts.append({'text': remaining, 'color': 'white'})

        # 파트가 없으면 전체를 흰색으로
        if not parts:
            parts.append({'text': title, 'color': 'white'})

        return parts

    def create_title_image(self, title, width, height, title_font="BMYEONSUNG_otf.otf", title_font_size=42):
        """제목 이미지 생성 - 지정 영역(50,65)~(444,200)에 아래 정렬 (색상 태그 지원)"""
        # 검은 배경 이미지 생성 (전체 타이틀 영역)
        img = Image.new('RGB', (width, height), color='black')
        draw = ImageDraw.Draw(img)

        # 타이틀 텍스트 영역 정의: (50, 65) ~ (444, 200)
        title_left = 50
        title_top = 65
        title_right = 444  # 사용자 요구사항: (50,65) ~ (444,200)
        title_bottom = 200  # 텍스트 영역 하단을 200으로 제한 (하단 20px 여백 확보)
        title_width = title_right - title_left  # 394px (444-50)
        title_height = title_bottom - title_top  # 135px (200-65)

        # 타이틀 폰트 설정
        title_font_path = os.path.join(os.path.dirname(__file__), "font", title_font)
        try:
            font = ImageFont.truetype(title_font_path, title_font_size)

            # Variable 폰트의 경우 굵기 설정
            if 'variable' in title_font.lower() or 'vf' in title_font.lower():
                try:
                    weight = 600  # 타이틀은 SemiBold
                    font.set_variation_by_name('wght', weight)
                    print(f"✅ Variable 타이틀 폰트 로드 성공: {title_font} ({title_font_size}pt, weight={weight})")
                except Exception as var_error:
                    print(f"⚠️ Variable 폰트 굵기 설정 실패 (기본 굵기 사용): {var_error}")
            else:
                print(f"✅ 타이틀 폰트 로드 성공: {title_font} ({title_font_size}pt)")
        except Exception as e:
            print(f"❌ 타이틀 폰트 로드 실패 ({title_font}): {e}")
            # 기본 폰트로 fallback
            try:
                font = ImageFont.truetype(self.font_path, title_font_size)
                print(f"✅ 기본 타이틀 폰트로 fallback: {self.font_path}")
            except Exception as e2:
                print(f"❌ 기본 타이틀 폰트도 실패: {e2}")
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", title_font_size)
                except:
                    font = ImageFont.load_default()
        
        # 🎨 색상 태그 파싱
        colored_parts = self.parse_colored_title(title)
        logger.info(f"📝 색상 파트 수: {len(colored_parts)}")

        # 색상 정보를 유지하며 단어 단위로 분리
        words_with_colors = []
        for part in colored_parts:
            part_words = part['text'].split(' ')
            for word in part_words:
                if word:  # 빈 문자열 제외
                    words_with_colors.append({
                        'text': word,
                        'color': part['color']
                    })

        # 줄바꿈 처리 (색상 정보 유지)
        lines = []  # [{'words': [{text, color}, ...], 'total_width': ...}, ...]
        current_line_words = []

        for word_info in words_with_colors:
            # 현재 줄에 단어를 추가했을 때 텍스트 생성 (공백 포함)
            test_words = current_line_words + [word_info]
            test_text = ' '.join([w['text'] for w in test_words])
            bbox = draw.textbbox((0, 0), test_text, font=font)
            test_width = bbox[2] - bbox[0]

            if test_width < title_width - 20:  # 타이틀 영역 내 여백 10px씩
                current_line_words.append(word_info)
            else:
                # 현재 줄 저장
                if current_line_words:
                    line_text = ' '.join([w['text'] for w in current_line_words])
                    bbox = draw.textbbox((0, 0), line_text, font=font)
                    lines.append({
                        'words': current_line_words,
                        'total_width': bbox[2] - bbox[0]
                    })
                current_line_words = [word_info]

        # 마지막 줄 저장
        if current_line_words:
            line_text = ' '.join([w['text'] for w in current_line_words])
            bbox = draw.textbbox((0, 0), line_text, font=font)
            lines.append({
                'words': current_line_words,
                'total_width': bbox[2] - bbox[0]
            })
        
        # 이모지 폰트 준비 (제목 폰트 크기에 맞춤)
        emoji_font_path = self.get_emoji_font()
        emoji_font = None
        if emoji_font_path:
            try:
                emoji_font = ImageFont.truetype(emoji_font_path, 44)  # 22 → 44로 2배 증가
            except:
                emoji_font = None
        
        # 텍스트 아래 정렬 (타이틀 영역 하단에서 위로 배치)
        line_height = 50  # 48px 폰트에 맞춘 적정 줄간격
        total_text_height = len(lines) * line_height
        
        # 아래 정렬: 타이틀 영역 하단에서 텍스트 높이만큼 위로
        start_y = title_bottom - total_text_height - 5  # 안전 여백 5px
        
        print(f"📐 타이틀 배치: 영역({title_left},{title_top})~({title_right},{title_bottom})")
        print(f"📝 텍스트 시작: Y={start_y}, 줄수={len(lines)}, 전체높이={total_text_height}px")
        
        # 🎨 색상별로 각 줄 렌더링
        for i, line_info in enumerate(lines):
            y = start_y + i * line_height

            # 타이틀 영역 범위 체크
            if y < title_top:
                y = title_top + 10  # 최소 상단 여백 확보

            # 줄 전체 폭 (중앙 정렬용)
            total_width = line_info['total_width']

            # 시작 X 좌표 (중앙 정렬)
            start_x = title_left + (title_width - total_width) // 2
            current_x = start_x

            # 줄 텍스트 생성 (디버깅용)
            line_text = ' '.join([w['text'] for w in line_info['words']])
            logger.info(f"📍 줄 {i+1}: '{line_text}' at Y={y}")

            # 각 단어를 순차적으로 렌더링 (색상 적용)
            for j, word_info in enumerate(line_info['words']):
                word = word_info['text']
                color = word_info['color']

                # 공백 추가 (첫 번째 단어 제외)
                if j > 0:
                    space_bbox = draw.textbbox((0, 0), ' ', font=font)
                    space_width = space_bbox[2] - space_bbox[0]
                    current_x += space_width

                # 텍스트 렌더링 (색상 적용)
                try:
                    draw.text((current_x, y), word, font=font, fill=color)
                    if color != 'white':
                        logger.info(f"🎨 색상 적용: '{word}' → {color}")
                except Exception as e:
                    logger.error(f"텍스트 렌더링 오류: {e}")
                    # 폴백으로 기본 폰트 사용
                    default_font = ImageFont.load_default()
                    draw.text((current_x, y), word, font=default_font, fill=color)

                # X 좌표 이동 (다음 단어 위치로)
                word_bbox = draw.textbbox((0, 0), word, font=font)
                word_width = word_bbox[2] - word_bbox[0]
                current_x += word_width
        
        # 임시 파일로 저장
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        img.save(temp_file.name, "PNG")
        temp_file.close()
        
        return temp_file.name
    
    def create_text_image(self, text, width, height, text_position="bottom", text_style="outline", is_title=False, title_font="BMYEONSUNG_otf.otf", body_font="BMYEONSUNG_otf.otf", title_area_mode="keep", title_font_size=42, body_font_size=36):
        """텍스트 이미지 생성 (배경 박스 포함)"""
        # 투명 배경 이미지 생성
        img = Image.new('RGBA', (width, height), color=(0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # 폰트 선택 (타이틀/바디 구분)
        selected_font = title_font if is_title else body_font
        font_path = os.path.join(os.path.dirname(__file__), "font", selected_font)

        # 폰트 크기 설정 (사용자 지정 크기 우선, white_background는 2pt 작게)
        # 최소 12pt 보장하여 PIL "font size must be greater than 0" 에러 방지
        if text_style == "white_background":
            # white_background 스타일은 2포인트 작게 (최소 12pt 보장)
            font_size = max(12, (title_font_size - 2)) if is_title else max(12, (body_font_size - 2))
        else:
            # 일반 스타일은 사용자 지정 크기 사용 (최소 12pt 보장)
            font_size = max(12, title_font_size) if is_title else max(12, body_font_size)

        # 한글 폰트 설정
        try:
            font = ImageFont.truetype(font_path, font_size)

            # Variable 폰트의 경우 굵기 설정 (Pretendard Variable 등)
            if 'variable' in selected_font.lower() or 'vf' in selected_font.lower():
                try:
                    # Variable 폰트의 weight 설정 (400=Regular, 600=SemiBold, 700=Bold)
                    weight = 600 if is_title else 500  # 타이틀은 SemiBold, 본문은 Medium
                    font.set_variation_by_name('wght', weight)
                    print(f"✅ Variable 폰트 굵기 설정: {selected_font} ({font_size}pt, weight={weight})")
                except Exception as var_error:
                    print(f"⚠️ Variable 폰트 굵기 설정 실패 (기본 굵기 사용): {var_error}")
            else:
                print(f"✅ 폰트 로드 성공: {selected_font} ({font_size}pt)")
        except Exception as e:
            print(f"❌ 사용자 폰트 로드 실패 ({selected_font}): {e}")
            # 기본 폰트로 fallback
            try:
                font = ImageFont.truetype(self.font_path, font_size)
                print(f"✅ 기본 폰트로 fallback: {self.font_path}")
            except Exception as e2:
                print(f"❌ 기본 폰트도 실패: {e2}")
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
                except:
                    font = ImageFont.load_default()
        
        # 텍스트를 여러 줄로 나누기
        # 본문은 캔버스 폭의 70%만 사용 (타이틀은 별도 처리)
        if is_title:
            max_text_width = width - 60  # 타이틀: 좌우 30px 여백
        else:
            max_text_width = int(width * 0.70)  # 본문: 캔버스 폭의 70%만 사용

        words = text.split(' ')
        lines = []
        current_line = ""

        for word in words:
            test_line = current_line + " " + word if current_line else word
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] < max_text_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)
        
        # 전체 텍스트 박스 크기 계산 (폰트 크기에 비례하는 줄간격)
        # 폰트 크기 * 1.11 = 36pt → 40px, 26pt → 29px
        line_height = max(font_size + 4, int(font_size * 1.11))
        total_height = len(lines) * line_height
        padding = 20  # 패딩 조정
        
        # 텍스트 위치 계산 (새로운 영역 구성)
        # 전체 해상도: 504x890, 타이틀 영역: 220px
        # 상단 텍스트 영역: 340-520 (중앙: 430px)
        # 하단 텍스트 영역: 520-700 (중앙: 610px)

        title_height = self.title_height  # 타이틀 영역 높이

        if text_position == "top":
            # 상단 텍스트 영역 중앙
            zone_center_y = self.text_y_top
            start_y = zone_center_y - (total_height // 2)
        elif text_position == "bottom-edge":
            # 최하단: 바닥에서 여백만큼 위
            start_y = self.video_height - self.text_y_bottom_edge_margin - total_height
        else:  # bottom (middle도 bottom과 동일하게 처리)
            # 하단 텍스트 영역 중앙
            zone_center_y = self.text_y_bottom
            start_y = zone_center_y - (total_height // 2)

        # 최소값 보장 (타이틀 영역 침범 방지) - bottom-edge는 예외
        if text_position != "bottom-edge":
            start_y = max(start_y, title_height + padding)
        
        # 이모지 폰트 준비 (본문 폰트 크기에 맞춤)
        emoji_font_path = self.get_emoji_font()
        emoji_font = None
        if emoji_font_path:
            try:
                emoji_font = ImageFont.truetype(emoji_font_path, 32)  # 36pt 본문에 맞춘 이모지 크기
            except:
                emoji_font = None
        
        # text_style에 따른 텍스트 렌더링 (font_size 파라미터 전달)
        if text_style == "background":
            # 반투명 배경 스타일 (폰트 크기 비례 패딩)
            self._render_text_with_background(draw, lines, font, emoji_font, width, start_y, line_height, font_size)
        elif text_style == "white_background":
            # 흰색 반투명 배경 + 검은색 글자 + 둥근 모서리 (폰트 크기 비례)
            self._render_text_with_white_background(draw, lines, font, emoji_font, width, start_y, line_height, font_size)
        elif text_style == "black_text_white_outline":
            # 검은색 글씨 + 흰색 외곽선
            self._render_text_with_black_text_white_outline(draw, lines, font, emoji_font, width, start_y, line_height, font_size)
        else:
            # 외곽선 스타일 (기본값)
            self._render_text_with_outline(draw, lines, font, emoji_font, width, start_y, line_height, font_size)
        
        # 임시 파일로 저장
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        img.save(temp_file.name, "PNG")
        temp_file.close()
        
        return temp_file.name
    
    def _render_text_with_outline(self, draw, lines, font, emoji_font, width, start_y, line_height, font_size):
        """외곽선 스타일로 텍스트 렌더링 (기존 방식)"""
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x = (width - text_width) // 2
            y = start_y + i * line_height
            
            # 텍스트 렌더링 (부드러운 외곽선 효과)
            try:
                # 더 부드러운 외곽선 (3px 두께, 1.5배 강화)
                outline_positions = [
                    (-3, -3), (-3, -2), (-3, -1), (-3, 0), (-3, 1), (-3, 2), (-3, 3),
                    (-2, -3), (-2, -2), (-2, -1), (-2, 0), (-2, 1), (-2, 2), (-2, 3),
                    (-1, -3), (-1, -2), (-1, -1), (-1, 0), (-1, 1), (-1, 2), (-1, 3),
                    (0, -3), (0, -2), (0, -1),            (0, 1), (0, 2), (0, 3),
                    (1, -3), (1, -2), (1, -1), (1, 0), (1, 1), (1, 2), (1, 3),
                    (2, -3), (2, -2), (2, -1), (2, 0), (2, 1), (2, 2), (2, 3),
                    (3, -3), (3, -2), (3, -1), (3, 0), (3, 1), (3, 2), (3, 3)
                ]
                
                # 검은색 외곽선 그리기
                for dx, dy in outline_positions:
                    draw.text((x + dx, y + dy), line, font=font, fill='black')
                
                # 흰색 텍스트 (중앙)
                draw.text((x, y), line, font=font, fill='white')
                
            except Exception as e:
                print(f"본문 텍스트 렌더링 오류: {e}")
                # 폴백: 기본 외곽선
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        if dx != 0 or dy != 0:
                            draw.text((x + dx, y + dy), line, font=font, fill='black')
                draw.text((x, y), line, font=font, fill='white')
    
    def _render_text_with_background(self, draw, lines, font, emoji_font, width, start_y, line_height, font_size):
        """반투명 배경 스타일로 텍스트 렌더링 (폰트 크기 비례 패딩)"""
        # 전체 텍스트 영역 크기 계산
        max_text_width = 0
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            if text_width > max_text_width:
                max_text_width = text_width

        # 배경 박스 크기와 위치 계산 (폰트 크기에 비례)
        # 36pt 기준: padding_x=15px (36*0.42=15.12), padding_y=8px (36*0.22=7.92)
        padding_x = max(10, int(font_size * 0.42))  # 최소 10px
        padding_y = max(6, int(font_size * 0.22))   # 최소 6px
        background_width = max_text_width + padding_x * 2
        background_height = len(lines) * line_height + padding_y * 2
        
        background_x = (width - background_width) // 2
        background_y = start_y - padding_y
        
        # 반투명 검은 배경 직접 그리기
        draw.rectangle(
            [background_x, background_y, background_x + background_width, background_y + background_height],
            fill=(0, 0, 0, 178)  # 검은색 70% 투명도
        )
        
        # 텍스트 렌더링 (배경 위에 흰색 텍스트)
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            # 배경 박스 내부 중앙 정렬
            x = background_x + (background_width - text_width) // 2
            y = start_y + i * line_height

            # 흰색 텍스트 (배경이 있으므로 외곽선 불필요)
            draw.text((x, y), line, font=font, fill='white')

    def _render_text_with_white_background(self, draw, lines, font, emoji_font, width, start_y, line_height, font_size):
        """흰색 반투명 배경 + 검은색 글자 + 둥근 모서리 스타일로 텍스트 렌더링 (폰트 크기 비례)"""
        # 전체 텍스트 영역 크기 계산
        max_text_width = 0
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            if text_width > max_text_width:
                max_text_width = text_width

        # 배경 박스 크기와 위치 계산 (폰트 크기에 비례)
        # 36pt 기준: padding_x=15px, padding_y=8px
        padding_x = max(10, int(font_size * 0.42))  # 최소 10px
        padding_y = max(6, int(font_size * 0.22))   # 최소 6px
        background_width = max_text_width + padding_x * 2
        background_height = len(lines) * line_height + padding_y * 2

        background_x = (width - background_width) // 2
        background_y = start_y - padding_y

        # 둥근 모서리 흰색 반투명 배경 그리기
        # 둥근 모서리 반지름 (폰트 크기에 비례: 36pt → 12px)
        corner_radius = max(8, int(font_size * 0.33))

        # 반투명 흰색 배경 (투명도 80%)
        # PIL에서 둥근 사각형을 그리는 함수
        def draw_rounded_rectangle(draw, xy, radius, fill):
            x1, y1, x2, y2 = xy
            # 네 모서리의 원 그리기
            draw.ellipse([x1, y1, x1 + radius*2, y1 + radius*2], fill=fill)  # 왼쪽 위
            draw.ellipse([x2 - radius*2, y1, x2, y1 + radius*2], fill=fill)  # 오른쪽 위
            draw.ellipse([x1, y2 - radius*2, x1 + radius*2, y2], fill=fill)  # 왼쪽 아래
            draw.ellipse([x2 - radius*2, y2 - radius*2, x2, y2], fill=fill)  # 오른쪽 아래

            # 중앙 사각형들 그리기
            draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)  # 가로 중앙
            draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)  # 세로 중앙

        # 둥근 모서리 흰색 반투명 배경 그리기
        draw_rounded_rectangle(
            draw,
            [background_x, background_y, background_x + background_width, background_y + background_height],
            corner_radius,
            (255, 255, 255, 204)  # 흰색 80% 투명도
        )

        # 텍스트 렌더링 (배경 박스 내부에 검은색 텍스트)
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            # 배경 박스 내부 중앙 정렬
            x = background_x + (background_width - text_width) // 2
            y = start_y + i * line_height

            # 검은색 텍스트 (배경이 있으므로 외곽선 불필요)
            draw.text((x, y), line, font=font, fill='black')

    def _render_text_with_black_text_white_outline(self, draw, lines, font, emoji_font, width, start_y, line_height, font_size):
        """검은색 글씨 + 흰색 외곽선 스타일로 텍스트 렌더링"""
        # 각 줄별로 텍스트 렌더링
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x = (width - text_width) // 2
            y = start_y + i * line_height

            try:
                # 더 부드러운 흰색 외곽선 (3px 두께)
                outline_positions = [
                    (-3, -3), (-3, -2), (-3, -1), (-3, 0), (-3, 1), (-3, 2), (-3, 3),
                    (-2, -3), (-2, -2), (-2, -1), (-2, 0), (-2, 1), (-2, 2), (-2, 3),
                    (-1, -3), (-1, -2), (-1, -1), (-1, 0), (-1, 1), (-1, 2), (-1, 3),
                    (0, -3), (0, -2), (0, -1),            (0, 1), (0, 2), (0, 3),
                    (1, -3), (1, -2), (1, -1), (1, 0), (1, 1), (1, 2), (1, 3),
                    (2, -3), (2, -2), (2, -1), (2, 0), (2, 1), (2, 2), (2, 3),
                    (3, -3), (3, -2), (3, -1), (3, 0), (3, 1), (3, 2), (3, 3)
                ]

                # 흰색 외곽선 그리기
                for dx, dy in outline_positions:
                    draw.text((x + dx, y + dy), line, font=font, fill='white')

                # 검은색 텍스트 (중앙)
                draw.text((x, y), line, font=font, fill='black')

            except Exception as e:
                print(f"본문 텍스트 렌더링 오류: {e}")
                # 폴백: 기본 외곽선
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        if dx != 0 or dy != 0:
                            draw.text((x + dx, y + dy), line, font=font, fill='white')
                draw.text((x, y), line, font=font, fill='black')

    def _ensure_valid_image(self, image_path):
        """이미지 파일 검증 및 포맷 자동변환. 유효한 이미지 경로 반환 (실패 시 None)"""
        try:
            with Image.open(image_path) as img:
                img.verify()  # 파일 무결성 검증
            return image_path  # 정상 파일 그대로 반환
        except Exception:
            logger.warning(f"⚠️ 이미지 검증 실패, 자동 변환 시도: {image_path}")
            try:
                # verify() 후에는 다시 열어야 함
                with Image.open(image_path) as img:
                    rgb_img = img.convert('RGB')
                    converted_path = image_path + '.converted.jpg'
                    rgb_img.save(converted_path, 'JPEG', quality=95)
                    logger.info(f"✅ 이미지 자동 변환 완료: {converted_path}")
                    return converted_path
            except Exception as e2:
                logger.error(f"❌ 이미지 자동 변환 실패: {image_path} - {e2}")
                # 에러 이미지를 error_img 폴더에 보존 (원인 분석용)
                try:
                    import shutil
                    error_img_dir = os.path.join(os.path.dirname(__file__), "uploads", "error_img")
                    os.makedirs(error_img_dir, exist_ok=True)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    original_name = os.path.basename(image_path)
                    error_copy_name = f"{timestamp}_{original_name}"
                    error_copy_path = os.path.join(error_img_dir, error_copy_name)
                    shutil.copy2(image_path, error_copy_path)
                    logger.info(f"📋 에러 이미지 보존: {error_copy_path}")
                except Exception as copy_err:
                    logger.warning(f"⚠️ 에러 이미지 보존 실패: {copy_err}")
                return None

    def crop_to_square(self, image_path):
        """이미지를 중앙 기준 정사각형으로 크롭하여 716x716으로 리사이즈"""
        # 이미지 파일 검증 및 포맷 자동변환
        validated_path = self._ensure_valid_image(image_path)
        if validated_path is None:
            logger.error(f"❌ 유효하지 않은 이미지, 원본 경로 반환: {image_path}")
            return image_path
        image_path = validated_path

        try:
            with Image.open(image_path) as img:
                # ✅ EXIF orientation 적용 (아이폰 사진 회전 문제 해결)
                img = ImageOps.exif_transpose(img) or img
                width, height = img.size
                print(f"🔳 이미지 로드: {image_path} ({width}x{height})")
                
                # 이미 716x716인 경우 그대로 반환
                if width == 716 and height == 716:
                    print(f"🔳 이미 716x716: 변환 불필요")
                    return image_path
                
                # 짧은 변을 기준으로 정사각형 크기 결정
                crop_size = min(width, height)
                
                # 중앙 기준 크롭 좌표 계산
                left = (width - crop_size) // 2
                top = (height - crop_size) // 2
                right = left + crop_size
                bottom = top + crop_size
                
                # 크롭 실행 (정사각형이 아닌 경우만)
                if width != height:
                    cropped_img = img.crop((left, top, right, bottom))
                    print(f"🔳 크롭 실행: {width}x{height} → {crop_size}x{crop_size}")
                else:
                    cropped_img = img.copy()
                    print(f"🔳 정사각형 이미지: 크롭 생략")
                
                # 항상 716x716으로 리사이즈 (PIL 버전 호환성 고려)
                try:
                    # Pillow 10.0.0+ 버전
                    resized_img = cropped_img.resize((716, 716), Image.Resampling.LANCZOS)
                except AttributeError:
                    # 이전 버전 호환성
                    resized_img = cropped_img.resize((716, 716), Image.LANCZOS)
                
                # RGBA 모드인 경우 RGB로 변환 (JPEG 저장 위해)
                if resized_img.mode in ('RGBA', 'LA', 'P'):
                    # 흰색 배경으로 변환
                    background = Image.new('RGB', resized_img.size, (255, 255, 255))
                    if resized_img.mode == 'P':
                        resized_img = resized_img.convert('RGBA')
                    background.paste(resized_img, mask=resized_img.split()[-1] if resized_img.mode in ('RGBA', 'LA') else None)
                    resized_img = background
                    print(f"🔳 RGBA → RGB 변환 완료")
                
                # 임시 파일로 저장
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
                resized_img.save(temp_file.name, 'JPEG', quality=95)
                
                print(f"🔳 최종 리사이즈: → 716x716")
                print(f"🔳 임시 파일 생성: {temp_file.name}")
                
                return temp_file.name
                
        except Exception as e:
            print(f"❌ 이미지 변환 에러: {image_path}")
            print(f"❌ 에러 내용: {str(e)}")
            # 에러 발생시 원본 파일 그대로 반환
            return image_path

    def easing_function(self, p):
        """더욱 부드러운 이징 함수 (cubic ease-in-out)"""
        if p < 0.5:
            return 4 * p * p * p
        else:
            return 1 - pow(-2 * p + 2, 3) / 2
    
    def linear_easing_function(self, p):
        """일정한 속도의 선형 이징 함수 (패닝 전용)"""
        return p

    def create_background_clip(self, image_path, duration, enable_panning=True, title_area_mode="keep"):
        """새로운 영상/이미지 배치 및 패닝 규칙 적용 (EXIF + 고품질 리사이즈)

        Args:
            image_path: 이미지 파일 경로
            duration: 클립 지속 시간
            enable_panning: 패닝 효과 사용 여부 (기본값: True)
            title_area_mode: 타이틀 영역 모드 ("keep" 또는 "remove")
        """
        panning_status = "패닝 적용" if enable_panning else "패닝 없음"
        print(f"🎬 배경 클립 생성 시작: {image_path} (duration: {duration:.1f}s, {panning_status})")
        logger.debug(f"🔍 [DEBUG] create_background_clip() 함수 진입 (이미지 처리)")
        logger.debug(f"🔍 [DEBUG] 이미지 파일 존재 여부: {os.path.exists(image_path)}")

        # 이미지 파일 검증 및 포맷 자동변환
        validated_path = self._ensure_valid_image(image_path)
        if validated_path is not None:
            image_path = validated_path

        try:
            # 이미지 로드 + EXIF 적용 + 고품질 리사이즈
            with Image.open(image_path) as img:
                # ✅ EXIF orientation 적용 (아이폰/HEIC 사진 회전 문제 해결)
                img = ImageOps.exif_transpose(img) or img
                orig_width, orig_height = img.size
                print(f"📐 이미지 원본: {orig_width}x{orig_height}")

                # 작업 영역 정의: 타이틀 모드에 따라 결정
                work_width = self.video_width
                if title_area_mode == "keep":
                    work_height = self.work_height_keep
                    y_offset = self.title_height  # 타이틀 아래 시작
                else:
                    work_height = self.work_height_remove
                    y_offset = 0  # 맨 위부터 시작

                work_aspect_ratio = work_width / work_height
                image_aspect_ratio = orig_width / orig_height

                print(f"📊 종횡비 비교: 이미지 {image_aspect_ratio:.3f} vs 작업영역 {work_aspect_ratio:.3f}")

                # 패닝 옵션에 따른 리사이즈 전략 결정
                if enable_panning:
                    # 패닝 활성화: 기존 로직 (한 쪽을 꽉 채우고 여유 공간 확보)
                    if image_aspect_ratio > work_aspect_ratio:
                        # 가로형: 세로를 work_height에 맞춤
                        new_height = work_height
                        new_width = int(orig_width * work_height / orig_height)
                        print(f"🔄 가로형 이미지 (패닝용): 리사이즈 {new_width}x{new_height}")
                    else:
                        # 세로형: 가로를 work_width에 맞춤
                        new_width = work_width
                        new_height = int(orig_height * work_width / orig_width)
                        print(f"🔄 세로형 이미지 (패닝용): 리사이즈 {new_width}x{new_height}")
                else:
                    # 패닝 비활성화: 가로(width)를 캔버스에 꽉 채우기
                    # 모든 이미지를 가로 기준으로 리사이즈 (위아래 검은 패딩)
                    new_width = work_width  # 504px 고정
                    new_height = int(orig_height * work_width / orig_width)
                    print(f"{'='*60}")
                    print(f"🔄 [패닝 OFF] 이미지 가로 기준 리사이즈")
                    print(f"   원본 이미지: {orig_width}x{orig_height}")
                    print(f"   캔버스 폭: {work_width}px (504px 고정)")
                    print(f"   리사이즈 결과: {new_width}x{new_height}")
                    print(f"   종횡비: {orig_width/orig_height:.3f} → {new_width/new_height:.3f}")
                    print(f"   위아래 검은 패딩: {max(0, work_height - new_height)}px")
                    print(f"{'='*60}")

                # PIL 고품질 리사이즈 (LANCZOS)
                try:
                    resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                except AttributeError:
                    resized_img = img.resize((new_width, new_height), Image.LANCZOS)

                print(f"✨ 고품질 리사이즈 완료: LANCZOS 알고리즘 사용")

                # RGBA → RGB 변환
                if resized_img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', resized_img.size, (0, 0, 0))
                    if resized_img.mode == 'P':
                        resized_img = resized_img.convert('RGBA')
                    background.paste(resized_img, mask=resized_img.split()[-1] if resized_img.mode in ('RGBA', 'LA') else None)
                    resized_img = background
                    print(f"🔳 RGBA → RGB 변환 완료")

                # 임시 파일로 저장 (고품질)
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
                resized_img.save(temp_file.name, 'JPEG', quality=95)
                processed_image_path = temp_file.name
                print(f"💾 고품질 임시 파일 생성: {processed_image_path}")

            # MoviePy로 처리된 이미지 로드
            bg_clip = ImageClip(processed_image_path).set_duration(duration)
            resized_width = new_width
            resized_height = new_height
            image_aspect_ratio = orig_width / orig_height

            if enable_panning:
                # === 패닝 활성화: 기존 패닝 로직 ===
                if image_aspect_ratio > work_aspect_ratio:
                    # 가로형 이미지: 좌우 패닝
                    pan_range = min(self.panning_range, (resized_width - work_width) // 2)
                    pattern = random.randint(1, 2)

                    if pattern == 1:
                        # 패턴 1: 좌 → 우 패닝
                        def left_to_right(t):
                            progress = self.linear_easing_function(t / duration)
                            x_offset = -((resized_width - work_width) // 2 - pan_range * progress)
                            return (x_offset, y_offset)

                        bg_clip = bg_clip.set_position(left_to_right)
                        print(f"🎬 패턴 1: 좌 → 우 패닝 ({pan_range}px 이동)")
                    else:
                        # 패턴 2: 우 → 좌 패닝
                        def right_to_left(t):
                            progress = self.linear_easing_function(t / duration)
                            x_offset = -((resized_width - work_width) // 2 - pan_range * (1 - progress))
                            return (x_offset, y_offset)

                        bg_clip = bg_clip.set_position(right_to_left)
                        print(f"🎬 패턴 2: 우 → 좌 패닝 ({pan_range}px 이동)")
                else:
                    # 세로형 이미지: 상하 패닝
                    pan_range = min(self.panning_range, (resized_height - work_height) // 2)
                    pattern = random.randint(3, 4)

                    if pattern == 3:
                        # 패턴 3: 위 → 아래 패닝
                        def top_to_bottom(t):
                            progress = self.linear_easing_function(t / duration)
                            y_offset_dynamic = y_offset - ((resized_height - work_height) // 2 - pan_range * progress)
                            return (0, y_offset_dynamic)

                        bg_clip = bg_clip.set_position(top_to_bottom)
                        print(f"🎬 패턴 3: 위 → 아래 패닝 ({pan_range}px 이동)")
                    else:
                        # 패턴 4: 아래 → 위 패닝
                        def bottom_to_top(t):
                            progress = self.linear_easing_function(t / duration)
                            y_offset_dynamic = y_offset - ((resized_height - work_height) // 2 - pan_range * (1 - progress))
                            return (0, y_offset_dynamic)

                        bg_clip = bg_clip.set_position(bottom_to_top)
                        print(f"🎬 패턴 4: 아래 → 위 패닝 ({pan_range}px 이동)")
            else:
                # === 패닝 비활성화: 위로 붙이기 + 아래 검은색 패딩 ===
                # 이미지를 작업영역 위쪽에 붙임 (아래 남는 영역은 검게 보임)
                x_pos = 0  # 가로는 꽉 채움 (width=504)
                y_pos = y_offset  # 위로 붙임

                bg_clip = bg_clip.set_position((x_pos, y_pos))
                print(f"📍 패닝 없음: 위로 붙임 ({x_pos}, {y_pos})")
                print(f"   이미지 크기: {resized_width}x{resized_height}")
                print(f"   작업 영역: {work_width}x{work_height} (Y offset: {y_offset})")
                print(f"   아래 검은 패딩: {max(0, work_height - resized_height)}px")

                # 검은색 배경으로 남는 영역 채우기
                black_bg = ColorClip(size=(work_width, work_height), color=(0, 0, 0))
                black_bg = black_bg.set_duration(duration).set_position((0, y_offset))

                # 검은 배경 위에 이미지 합성
                bg_clip = CompositeVideoClip([black_bg, bg_clip])
                print(f"✅ 검은색 배경 추가 완료")

            return bg_clip
                
        except Exception as e:
            print(f"❌ 배경 클립 생성 에러: {str(e)}")
            # 에러 발생시 기본 클립 반환 (PIL로 안전하게 리사이즈)
            try:
                fallback_img = Image.open(image_path)
                orig_w, orig_h = fallback_img.size
                new_h = 670
                new_w = int(orig_w * new_h / orig_h)

                try:
                    resized_fallback = fallback_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                except AttributeError:
                    resized_fallback = fallback_img.resize((new_w, new_h), Image.LANCZOS)

                fallback_temp = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
                resized_fallback.save(fallback_temp.name, 'JPEG', quality=95)
                fallback_clip = ImageClip(fallback_temp.name).set_duration(duration).set_position((0, self.title_height))
                os.unlink(fallback_temp.name)
            except:
                # 최종 fallback: 원본 그대로 사용
                fallback_clip = ImageClip(image_path).set_duration(duration).set_position((0, self.title_height))
            return fallback_clip


    
    def create_continuous_background_clip(self, image_path, total_duration, start_offset=0.0, enable_panning=True, title_area_mode="keep"):
        """2개 body 동안 연속적으로 움직이는 배경 클립 생성 (EXIF + 고품질 적용)

        Args:
            image_path: 이미지 파일 경로
            total_duration: 전체 클립 지속 시간
            start_offset: 시작 오프셋 (현재 미사용)
            enable_panning: 패닝 효과 사용 여부 (기본값: True)
            title_area_mode: 타이틀 영역 모드 ("keep" 또는 "remove")
        """
        panning_status = "패닝 적용" if enable_panning else "패닝 없음"
        print(f"🎬 연속 배경 클립 생성: {image_path} (duration: {total_duration:.1f}s, {panning_status})")
        logger.debug(f"🔍 [DEBUG] create_continuous_background_clip() 함수 진입")
        logger.debug(f"🔍 [DEBUG] 이미지 파일 존재 여부: {os.path.exists(image_path)}")

        # 이미지 파일 검증 및 포맷 자동변환
        validated_path = self._ensure_valid_image(image_path)
        if validated_path is not None:
            image_path = validated_path

        # 패닝 활성화 시에만 정사각형 크롭 (패닝 비활성화 시에는 원본 유지)
        if enable_panning:
            # 패닝 ON: 정사각형으로 크롭 후 716x716으로 리사이즈
            # ✅ crop_to_square()에서 EXIF orientation + LANCZOS 리사이즈 적용됨
            square_image_path = self.crop_to_square(image_path)
        else:
            # 패닝 OFF: 원본 이미지 그대로 사용 (미리보기와 동일한 처리)
            square_image_path = image_path

        try:
            # 배경 클립 생성
            bg_clip = ImageClip(square_image_path).set_duration(total_duration)

            # 타이틀 영역 모드에 따른 Y 오프셋 결정
            if title_area_mode == "keep":
                y_offset = self.title_height  # 타이틀 아래 시작
                work_height = self.work_height_keep
            else:
                y_offset = 0  # 맨 위부터 시작
                work_height = self.work_height_remove

            if enable_panning:
                # === 패닝 활성화: 기존 패닝 로직 ===
                # 2가지 패닝 패턴 중 랜덤 선택
                pattern = random.randint(1, 2)

                if pattern == 1:
                    # 패턴 1: 연속 좌 → 우 패닝 (Linear 이징 + 60px 이동)
                    def continuous_left_to_right(t):
                        progress = self.linear_easing_function(t / total_duration)
                        x_offset = -(151 - 60 * progress)
                        return (x_offset, y_offset)

                    bg_clip = bg_clip.set_position(continuous_left_to_right)
                    print(f"🎬 연속 패턴 1: 좌 → 우 패닝 (duration: {total_duration:.1f}s)")

                else:
                    # 패턴 2: 연속 우 → 좌 패닝 (Linear 이징 + 60px 이동)
                    def continuous_right_to_left(t):
                        progress = self.linear_easing_function(t / total_duration)
                        x_offset = -(151 - 60 * (1 - progress))
                        return (x_offset, y_offset)

                    bg_clip = bg_clip.set_position(continuous_right_to_left)
                    print(f"🎬 연속 패턴 2: 우 → 좌 패닝 (duration: {total_duration:.1f}s)")
            else:
                # === 패닝 비활성화: 가로 꽉 채우기 + 위아래 검은색 패딩 ===
                # 원본 이미지를 작업영역 가로에 맞춤 (미리보기와 동일한 처리)
                work_width = 504

                # 원본 이미지 파일에서 크기 확인 (EXIF 적용)
                with Image.open(square_image_path) as img:
                    img = ImageOps.exif_transpose(img) or img
                    img_width, img_height = img.size

                # 패닝 비활성화 시: 항상 가로를 캔버스 폭(504px)에 맞춤
                new_width = work_width  # 504px 고정
                new_height = int(img_height * work_width / img_width)

                print(f"{'='*60}")
                print(f"🔄 [연속 클립 - 패닝 OFF] 이미지 가로 기준 리사이즈")
                print(f"   원본 이미지: {img_width}x{img_height}")
                print(f"   캔버스 폭: {work_width}px (504px 고정)")
                print(f"   리사이즈 결과: {new_width}x{new_height}")
                print(f"   종횡비: {img_width/img_height:.3f} → {new_width/new_height:.3f}")
                print(f"   위아래 검은 패딩: {max(0, work_height - new_height)}px")
                print(f"{'='*60}")

                # 원본 이미지 파일에서 PIL로 로드 (EXIF 적용)
                pil_img = Image.open(square_image_path)
                pil_img = ImageOps.exif_transpose(pil_img) or pil_img

                # PIL 리사이즈 (호환성 처리)
                try:
                    resized_pil = pil_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                except AttributeError:
                    resized_pil = pil_img.resize((new_width, new_height), Image.LANCZOS)

                # RGBA → RGB 변환
                if resized_pil.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', resized_pil.size, (0, 0, 0))
                    if resized_pil.mode == 'P':
                        resized_pil = resized_pil.convert('RGBA')
                    background.paste(resized_pil, mask=resized_pil.split()[-1] if resized_pil.mode in ('RGBA', 'LA') else None)
                    resized_pil = background

                # 새 임시 파일로 저장
                resized_temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
                resized_pil.save(resized_temp_file.name, format='JPEG', quality=95)
                resized_temp_file.close()

                # 새 ImageClip 생성 (global import 사용)
                bg_clip = ImageClip(resized_temp_file.name).set_duration(total_duration)

                # 임시 파일 정리
                try:
                    os.unlink(resized_temp_file.name)
                except:
                    pass

                # 위로 붙이기 좌표 계산 (아래 검은 패딩)
                x_pos = 0  # 가로는 꽉 채움 (width=504)
                y_pos = y_offset  # 위로 붙임

                bg_clip = bg_clip.set_position((x_pos, y_pos))
                print(f"📍 연속 패닝 없음: 위로 붙임 ({x_pos}, {y_pos})")
                print(f"   이미지 크기: {new_width}x{new_height}")
                print(f"   작업 영역: {work_width}x{work_height}")
                print(f"   아래 검은 패딩: {max(0, work_height - new_height)}px")

                # 검은색 배경으로 남는 영역 채우기
                black_bg = ColorClip(size=(work_width, work_height), color=(0, 0, 0))
                black_bg = black_bg.set_duration(total_duration).set_position((0, y_offset))

                # 검은 배경 위에 이미지 합성
                bg_clip = CompositeVideoClip([black_bg, bg_clip])
                print(f"✅ 연속 클립 검은색 배경 추가 완료")

            return bg_clip
                
        except Exception as e:
            print(f"❌ 연속 배경 클립 에러: {str(e)}")
            # 에러 발생시 기본 클립 반환
            fallback_clip = ImageClip(image_path).set_duration(total_duration)
            try:
                from moviepy.video.fx.all import resize as fx_resize
                fallback_clip = fallback_clip.fx(fx_resize, height=670).set_position((0, 0))
            except:
                fallback_clip = fallback_clip.resize(height=670).set_position((0, 0))
            return fallback_clip
            
        finally:
            # 임시 파일 정리
            if square_image_path != image_path and os.path.exists(square_image_path):
                try:
                    os.unlink(square_image_path)
                    print(f"🗑️ 연속 임시 파일 정리: {square_image_path}")
                except:
                    pass

    
    def create_video_background_clip(self, video_path, duration, enable_panning=True):
        """새로운 비디오 배치 및 패닝 규칙 적용

        Args:
            video_path: 비디오 파일 경로
            duration: 클립 지속 시간
            enable_panning: 패닝 활성화 여부 (기본값: True)
        """
        from moviepy.editor import VideoFileClip, ColorClip, CompositeVideoClip

        print(f"🎬 비디오 배경 클립 생성 시작: {video_path} (duration: {duration:.1f}s, panning: {enable_panning})")
        logger.debug(f"🔍 [DEBUG] create_video_background_clip() 함수 진입")
        logger.debug(f"🔍 [DEBUG] 비디오 파일 존재 여부: {os.path.exists(video_path)}")

        # ★ 비디오 회전 메타데이터 감지 및 정규화 (iPhone .mov 등)
        normalized_path, is_temp_file = self.normalize_video_rotation(video_path)

        try:
            # 비디오 파일 로드 (정규화된 파일 사용)
            logger.debug(f"🔍 [DEBUG] VideoFileClip() 호출 시작 (경로: {normalized_path})")
            video_clip = VideoFileClip(normalized_path)
            logger.debug(f"🔍 [DEBUG] VideoFileClip() 호출 성공")

            # 비디오 메타데이터 검증
            if video_clip.duration is None or video_clip.duration <= 0:
                raise Exception(f"비디오 파일의 지속 시간 정보가 올바르지 않습니다: {video_clip.duration}")

            # 비디오 원본 크기
            orig_width = video_clip.w
            orig_height = video_clip.h
            print(f"📐 비디오 크기: {orig_width}x{orig_height} (정규화: {'예' if is_temp_file else '아니오'})")

            # 진단 로그: 첫 프레임의 실제 numpy shape 확인
            try:
                first_frame = video_clip.get_frame(0)
                print(f"🔍 진단: first_frame.shape = {first_frame.shape} (h={first_frame.shape[0]}, w={first_frame.shape[1]})")
            except Exception as e:
                print(f"⚠️ 진단 프레임 추출 실패: {e}")

            # 비디오 파일 정보 검증
            if orig_width <= 0 or orig_height <= 0:
                raise Exception(f"비디오 해상도 정보가 올바르지 않습니다: {orig_width}x{orig_height}")
            
            # 작업 영역 정의: (0, 220) ~ (504, 890)
            work_width = 504
            work_height = self.work_height_keep
            work_aspect_ratio = work_width / work_height  # 252:335 = 0.751
            video_aspect_ratio = orig_width / orig_height
            
            print(f"📊 종횡비 비교: 비디오 {video_aspect_ratio:.3f} vs 작업영역 {work_aspect_ratio:.3f}")
            
            # 비디오 길이 조정 (안전한 처리)
            original_duration = video_clip.duration
            print(f"📏 비디오 원본 길이: {original_duration:.2f}초, 목표 길이: {duration:.2f}초")

            if original_duration > duration:
                # 비디오가 긴 경우: 안전하게 자르기 (약간의 여유를 둠)
                logger.debug(f"🔍 [DEBUG] 비디오 길이 조정 분기: 긴 비디오 자르기 (original={original_duration:.2f}s > target={duration:.2f}s)")
                safe_duration = min(duration, original_duration - 0.2)  # 0.2초 여유
                safe_duration = max(safe_duration, 0.5)  # 최소 0.5초는 보장
                print(f"⏂ 비디오 길이 조정: {safe_duration:.2f}초로 안전하게 잘라냄")
                video_clip = video_clip.subclip(0, safe_duration)
            elif original_duration < duration:
                logger.debug(f"🔍 [DEBUG] 비디오 길이 조정 분기: 짧은 비디오 반복/연장 (original={original_duration:.2f}s < target={duration:.2f}s)")
                # 비디오가 짧은 경우: 반복 재생으로 길이 맞춤
                try:
                    # 안전한 반복 처리
                    loop_count = int(duration // original_duration) + 1
                    print(f"🔁 비디오 반복 처리: {loop_count}회 반복하여 {duration}초 달성")

                    # 개별 클립들을 생성해서 연결하는 방식으로 변경
                    clips = []
                    current_time = 0

                    while current_time < duration:
                        remaining_time = duration - current_time
                        if remaining_time >= original_duration:
                            # 전체 클립 추가
                            clips.append(video_clip)
                            current_time += original_duration
                        else:
                            # 부분 클립 추가 (안전하게)
                            safe_remaining = min(remaining_time, original_duration - 0.2)
                            if safe_remaining > 0.2:  # 최소 0.2초는 있어야 함
                                print(f"📏 부분 클립 생성: 0초 ~ {safe_remaining:.2f}초")
                                clips.append(video_clip.subclip(0, safe_remaining))
                            current_time = duration  # 루프 종료

                    if clips:
                        from moviepy.editor import concatenate_videoclips
                        video_clip = concatenate_videoclips(clips)
                        print(f"✅ 비디오 반복 완성: 최종 길이 {video_clip.duration:.2f}초")

                except Exception as e:
                    print(f"⚠️ 비디오 반복 처리 실패: {e}")
                    logger.error(f"🔍 [DEBUG] ============ 예외 처리 블록 진입 ============")
                    logger.error(f"🔍 [DEBUG] 예외 타입: {type(e).__name__}")
                    logger.error(f"🔍 [DEBUG] 예외 메시지: {str(e)}")

                    # 실패 시 원본 비디오를 마지막 프레임으로 연장
                    print("📸 대안: 마지막 프레임으로 연장 처리")
                    logger.debug(f"🔍 [DEBUG] 마지막 프레임 연장 처리 시작")

                    # 원본 비디오 + 마지막 프레임 정지 이미지 (global import 사용)
                    safe_frame_time = max(0, min(original_duration - 0.3, original_duration * 0.9))
                    print(f"📸 안전한 프레임 추출 시간: {safe_frame_time:.2f}초")

                    logger.debug(f"🔍 [DEBUG] video_clip.to_ImageClip() 호출 직전")
                    logger.debug(f"🔍 [DEBUG] video_clip 타입: {type(video_clip)}")
                    logger.debug(f"🔍 [DEBUG] ImageClip 타입: {type(ImageClip)}")
                    last_frame = video_clip.to_ImageClip(t=safe_frame_time)
                    logger.debug(f"🔍 [DEBUG] video_clip.to_ImageClip() 호출 완료")

                    extension_duration = duration - original_duration
                    extension_clip = last_frame.set_duration(extension_duration)

                    video_clip = concatenate_videoclips([video_clip, extension_clip])
                    print(f"🖼️ 마지막 프레임 연장: {extension_duration:.2f}초 추가")
                    logger.debug(f"🔍 [DEBUG] ============ 예외 처리 블록 종료 ============")
            
            if video_aspect_ratio > work_aspect_ratio:
                # 가로형 비디오: 세로 높이를 작업 영역에 맞춰 배치하고 좌우 패닝
                print(f"🔄 가로형 비디오 처리: 세로 높이를 {work_height}에 맞춤")

                # 세로를 작업 영역에 맞춰 리사이즈
                resized_width = int(orig_width * work_height / orig_height)

                try:
                    # MoviePy resize with newer API - newsize로 명시적 크기 지정 (회전 보정 대응)
                    from moviepy.video.fx.all import resize as fx_resize
                    video_clip = video_clip.fx(fx_resize, newsize=(resized_width, work_height))
                except:
                    # Fallback to direct resize
                    try:
                        video_clip = video_clip.resize(newsize=(resized_width, work_height))
                    except AttributeError as e:
                        # PIL ANTIALIAS 이슈 - 프레임 추출 후 수동 리사이즈
                        print(f"⚠️ MoviePy resize 실패 (PIL 호환성): {e}")
                        print(f"🔄 프레임 추출 방식으로 전환")

                        fps = 30
                        duration_temp = video_clip.duration
                        frames = []

                        for t in [i/fps for i in range(int(duration_temp * fps))]:
                            if t <= duration_temp:
                                frame = video_clip.get_frame(t)
                                pil_frame = Image.fromarray(frame)

                                try:
                                    resized_frame = pil_frame.resize((resized_width, work_height), Image.Resampling.LANCZOS)
                                except AttributeError:
                                    resized_frame = pil_frame.resize((resized_width, work_height), Image.LANCZOS)

                                frames.append(np.array(resized_frame))

                        from moviepy.editor import ImageSequenceClip
                        video_clip = ImageSequenceClip(frames, fps=fps)

                print(f"🔧 리사이즈 완료: {resized_width}x{work_height}")

                # 🎨 패닝 옵션에 따른 처리
                if enable_panning:
                    # 좌우 패닝 범위 계산
                    pan_range = min(self.panning_range, (resized_width - work_width) // 2)  # 최대 60px 또는 여유 공간의 절반

                    # 2가지 좌우 패닝 패턴 중 랜덤 선택
                    pattern = random.randint(1, 2)

                    if pattern == 1:
                        # 패턴 1: 좌 → 우 패닝
                        def left_to_right(t):
                            progress = self.linear_easing_function(t / duration)
                            x_offset = -((resized_width - work_width) // 2 - pan_range * progress)
                            return (x_offset, 220)  # Y는 타이틀 바로 아래

                        video_clip = video_clip.set_position(left_to_right)
                        print(f"🎬 패턴 1: 좌 → 우 패닝 ({pan_range}px 이동)")

                    else:
                        # 패턴 2: 우 → 좌 패닝
                        def right_to_left(t):
                            progress = self.linear_easing_function(t / duration)
                            x_offset = -((resized_width - work_width) // 2 - pan_range * (1 - progress))
                            return (x_offset, 220)  # Y는 타이틀 바로 아래

                        video_clip = video_clip.set_position(right_to_left)
                        print(f"🎬 패턴 2: 우 → 좌 패닝 ({pan_range}px 이동)")
                else:
                    # 패닝 비활성화: 중앙 고정 배치
                    x_offset = -((resized_width - work_width) // 2)
                    video_clip = video_clip.set_position((x_offset, self.title_height))
                    print(f"🎨 패닝 비활성화: 중앙 고정 배치 (x_offset: {x_offset})")
                    
            else:
                # 세로형 비디오: 가로 폭을 작업 영역에 맞춰 배치하고 상하 패닝
                print(f"🔄 세로형 비디오 처리: 가로 폭을 {work_width}에 맞춤")

                # 가로를 작업 영역에 맞춰 리사이즈
                resized_height = int(orig_height * work_width / orig_width)

                try:
                    # MoviePy resize with newer API - newsize로 명시적 크기 지정 (회전 보정 대응)
                    from moviepy.video.fx.all import resize as fx_resize
                    video_clip = video_clip.fx(fx_resize, newsize=(work_width, resized_height))
                except:
                    # Fallback to direct resize
                    try:
                        video_clip = video_clip.resize(newsize=(work_width, resized_height))
                    except AttributeError as e:
                        # PIL ANTIALIAS 이슈 - 프레임 추출 후 수동 리사이즈
                        print(f"⚠️ MoviePy resize 실패 (PIL 호환성): {e}")
                        print(f"🔄 프레임 추출 방식으로 전환")

                        fps = 30
                        duration_temp = video_clip.duration
                        frames = []

                        for t in [i/fps for i in range(int(duration_temp * fps))]:
                            if t <= duration_temp:
                                frame = video_clip.get_frame(t)
                                pil_frame = Image.fromarray(frame)

                                try:
                                    resized_frame = pil_frame.resize((work_width, resized_height), Image.Resampling.LANCZOS)
                                except AttributeError:
                                    resized_frame = pil_frame.resize((work_width, resized_height), Image.LANCZOS)

                                frames.append(np.array(resized_frame))

                        from moviepy.editor import ImageSequenceClip
                        video_clip = ImageSequenceClip(frames, fps=fps)

                print(f"🔧 리사이즈 완료: {work_width}x{resized_height}")

                # 🎨 패닝 옵션에 따른 처리
                if enable_panning:
                    # 상하 패닝 범위 계산
                    pan_range = min(self.panning_range, (resized_height - work_height) // 2)  # 최대 60px 또는 여유 공간의 절반

                    # 2가지 상하 패닝 패턴 중 랜덤 선택
                    pattern = random.randint(3, 4)  # 패턴 3, 4로 구분

                    if pattern == 3:
                        # 패턴 3: 위 → 아래 패닝
                        def top_to_bottom(t):
                            progress = self.linear_easing_function(t / duration)
                            y_offset = self.title_height - ((resized_height - work_height) // 2 - pan_range * progress)
                            return (0, y_offset)  # X는 중앙

                        video_clip = video_clip.set_position(top_to_bottom)
                        print(f"🎬 패턴 3: 위 → 아래 패닝 ({pan_range}px 이동)")

                    else:
                        # 패턴 4: 아래 → 위 패닝
                        def bottom_to_top(t):
                            progress = self.linear_easing_function(t / duration)
                            y_offset = self.title_height - ((resized_height - work_height) // 2 - pan_range * (1 - progress))
                            return (0, y_offset)  # X는 중앙

                        video_clip = video_clip.set_position(bottom_to_top)
                        print(f"🎬 패턴 4: 아래 → 위 패닝 ({pan_range}px 이동)")
                else:
                    # 패닝 비활성화: 중앙 고정 배치
                    y_offset = self.title_height - ((resized_height - work_height) // 2)
                    video_clip = video_clip.set_position((0, y_offset))
                    print(f"🎨 패닝 비활성화: 중앙 고정 배치 (y_offset: {y_offset})")

            logger.debug(f"🔍 [DEBUG] create_video_background_clip() 정상 종료")
            return video_clip

        except Exception as e:
            print(f"❌ 비디오 배경 클립 생성 실패: {e}")
            logger.error(f"🔍 [DEBUG] ============ 최상위 예외 처리 블록 ============")
            logger.error(f"🔍 [DEBUG] 예외 타입: {type(e).__name__}")
            logger.error(f"🔍 [DEBUG] 예외 메시지: {str(e)}")
            import traceback
            traceback.print_exc()

            # 실패 시 검은 화면으로 대체
            fallback_clip = ColorClip(size=(self.video_width, self.work_height_keep), color=(0,0,0), duration=duration)
            fallback_clip = fallback_clip.set_position((0, self.title_height))
            print(f"🔄 검은 화면으로 대체: 504x670")
            return fallback_clip

        finally:
            # 회전 정규화 임시 파일 정리
            if is_temp_file and os.path.exists(normalized_path):
                try:
                    os.remove(normalized_path)
                    print(f"🗑️ 회전 임시 파일 정리: {os.path.basename(normalized_path)}")
                except Exception:
                    pass
    
    def create_tts_with_naver(self, text):
        """네이버 Clova Voice TTS 생성"""
        if not self.naver_client_id or not self.naver_client_secret:
            return None
            
        try:
            print(f"네이버 TTS 생성 중: {text[:50]}...")
            
            # Naver Clova Voice API 호출
            url = "https://naveropenapi.apigw.ntruss.com/tts-premium/v1/tts"
            headers = {
                "X-NCP-APIGW-API-KEY-ID": self.naver_client_id,
                "X-NCP-APIGW-API-KEY": self.naver_client_secret,
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            data = {
                "speaker": "nara",  # 여성 음성 (clara, matt, shinji, nara 등 선택 가능)
                "volume": "0",      # 볼륨 (-5~5)
                "speed": "0",       # 속도 (-5~5)
                "pitch": "0",       # 음높이 (-5~5)
                "format": "mp3",    # 출력 포맷
                "text": text
            }
            
            response = requests.post(url, headers=headers, data=data)
            
            if response.status_code == 200:
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                temp_file.write(response.content)
                temp_file.close()
                print(f"네이버 TTS 생성 완료: {temp_file.name}")
                return temp_file.name
            else:
                print(f"네이버 TTS API 오류: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"네이버 TTS 생성 실패: {e}")
            return None
    
    def create_tts_with_azure(self, text):
        """Microsoft Azure Cognitive Services TTS 생성"""
        if not self.azure_speech_key:
            return None
            
        try:
            print(f"Azure TTS 생성 중: {text[:50]}...")
            
            # Azure Cognitive Services Speech API 호출
            url = f"https://{self.azure_speech_region}.tts.speech.microsoft.com/cognitiveservices/v1"
            headers = {
                "Ocp-Apim-Subscription-Key": self.azure_speech_key,
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3"
            }
            
            # SSML 형식으로 요청 생성 (한국어 여성 음성)
            ssml = f"""<speak version='1.0' xml:lang='ko-KR'>
                <voice xml:lang='ko-KR' xml:gender='Female' name='ko-KR-SunHiNeural'>
                    <prosody rate='medium' pitch='medium'>
                        {text}
                    </prosody>
                </voice>
            </speak>"""
            
            response = requests.post(url, headers=headers, data=ssml.encode('utf-8'))
            
            if response.status_code == 200:
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                temp_file.write(response.content)
                temp_file.close()
                print(f"Azure TTS 생성 완료: {temp_file.name}")
                return temp_file.name
            else:
                print(f"Azure TTS API 오류: {response.status_code}, {response.text}")
                return None
                
        except Exception as e:
            print(f"Azure TTS 생성 실패: {e}")
            return None
    
    def create_tts_audio(self, text, lang='ko'):
        """
        TTS 음성 생성 - 엔진에 따라 분기

        설정된 TTS 엔진(self.tts_engine)에 따라 적절한 TTS 서비스 호출
        - edge: Edge TTS (edge-tts) - 기본값
        - qwen: Qwen TTS (저사양 최적화 0.6B 모델)
        """
        logger.info(f"🎤 TTS 생성 요청 (엔진: {self.tts_engine}): {text[:50]}...")

        if self.tts_engine == 'qwen':
            if not QWEN_TTS_AVAILABLE:
                logger.warning("⚠️ TTS 'qwen' 요청 → QWEN_TTS_AVAILABLE=False → Edge 폴백!")
            else:
                return self.create_tts_audio_qwen(text, lang)
        return self.create_tts_audio_edge(text, lang)
    
    def speed_up_audio(self, audio_path, speed_factor=1.5):
        """고급 오디오 속도 조정 (다중 알고리즘 지원)"""
        try:
            print(f"🎵 고급 오디오 속도 조정 시작: {speed_factor}x 속도")
            
            # 방법 1: FFmpeg 직접 사용 (가장 안정적)
            try:
                return self._speed_up_with_ffmpeg(audio_path, speed_factor)
            except Exception as e:
                print(f"⚠️ FFmpeg 방법 실패: {e}")
            
            # 방법 2: MoviePy 다중 방식
            try:
                return self._speed_up_with_moviepy(audio_path, speed_factor)
            except Exception as e:
                print(f"⚠️ MoviePy 방법 실패: {e}")
            
            # 방법 3: Pydub 사용
            try:
                return self._speed_up_with_pydub(audio_path, speed_factor)
            except Exception as e:
                print(f"⚠️ Pydub 방법 실패: {e}")
            
            # 방법 4: 샘플링 기반 간단한 속도 조정
            try:
                return self._speed_up_with_sampling(audio_path, speed_factor)
            except Exception as e:
                print(f"⚠️ 샘플링 방법 실패: {e}")
            
            print(f"❌ 모든 속도 조정 방법 실패, 원본 파일 사용: {audio_path}")
            return audio_path
            
        except Exception as e:
            print(f"❌ 오디오 속도 조정 전체 실패: {e}")
            return audio_path

    def _speed_up_with_ffmpeg(self, audio_path, speed_factor):
        """방법 1: FFmpeg를 직접 사용한 고품질 속도 조정"""
        print(f"🔧 FFmpeg 방식 속도 조정 시도...")
        
        import subprocess
        import shutil
        
        # FFmpeg 설치 확인
        if not shutil.which('ffmpeg'):
            raise Exception("FFmpeg가 설치되지 않았습니다")
        
        # 출력 파일 생성
        speed_adjusted_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        speed_adjusted_file.close()
        
        # FFmpeg 명령어로 속도 조정 (atempo 필터 사용)
        # atempo는 피치 변경 없이 속도만 조정 (최대 2.0배까지)
        if speed_factor <= 2.0:
            atempo_filter = f"atempo={speed_factor}"
        else:
            # 2.0배 초과시 여러 단계로 나눔
            atempo_filter = "atempo=2.0,atempo=" + str(speed_factor / 2.0)
        
        cmd = [
            'ffmpeg', '-y',  # 덮어쓰기 허용
            '-i', audio_path,
            '-filter:a', atempo_filter,
            '-loglevel', 'error',  # 에러만 출력
            speed_adjusted_file.name
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ FFmpeg 속도 조정 성공: {speed_factor}x")
            return speed_adjusted_file.name
        else:
            raise Exception(f"FFmpeg 실행 실패: {result.stderr}")
    
    def _speed_up_with_moviepy(self, audio_path, speed_factor):
        """방법 2: MoviePy 다중 방식 시도"""
        print(f"🎬 MoviePy 방식 속도 조정 시도...")
        
        from moviepy.editor import AudioFileClip
        
        audio_clip = AudioFileClip(audio_path)
        original_duration = audio_clip.duration
        
        # 시도 1: speedx import
        try:
            from moviepy.audio.fx import speedx
            speed_adjusted_clip = audio_clip.fx(speedx.speedx, speed_factor)
        except ImportError:
            try:
                from moviepy.audio.fx.speedx import speedx
                speed_adjusted_clip = audio_clip.fx(speedx, speed_factor)
            except ImportError:
                # 시도 2: 직접 시간 매핑
                print("📐 직접 시간 매핑으로 속도 조정...")
                def speed_function(get_frame, t):
                    return get_frame(t * speed_factor)
                
                speed_adjusted_clip = audio_clip.fl(speed_function, apply_to=['mask'])
                speed_adjusted_clip = speed_adjusted_clip.set_duration(audio_clip.duration / speed_factor)
        
        new_duration = speed_adjusted_clip.duration
        
        # 파일 저장
        speed_adjusted_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        speed_adjusted_clip.write_audiofile(
            speed_adjusted_file.name, 
            verbose=False, 
            logger=None,
            temp_audiofile=None  # 임시 파일 경로 문제 방지
        )
        speed_adjusted_file.close()
        
        # 리소스 해제
        audio_clip.close()
        speed_adjusted_clip.close()
        
        print(f"✅ MoviePy 속도 조정 완료: {original_duration:.1f}초 → {new_duration:.1f}초")
        return speed_adjusted_file.name
    
    def _speed_up_with_pydub(self, audio_path, speed_factor):
        """방법 3: Pydub를 사용한 속도 조정"""
        print(f"🎵 Pydub 방식 속도 조정 시도...")
        
        try:
            from pydub import AudioSegment
            from pydub.playback import play
        except ImportError:
            raise Exception("pydub 라이브러리가 설치되지 않았습니다")
        
        # 오디오 로드
        audio = AudioSegment.from_mp3(audio_path)
        
        # 속도 조정 (재생 속도 변경)
        # frame_rate를 증가시켜 속도를 빠르게 함
        new_sample_rate = int(audio.frame_rate * speed_factor)
        speed_adjusted_audio = audio._spawn(audio.raw_data, overrides={"frame_rate": new_sample_rate})
        speed_adjusted_audio = speed_adjusted_audio.set_frame_rate(audio.frame_rate)
        
        # 파일 저장
        speed_adjusted_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        speed_adjusted_audio.export(speed_adjusted_file.name, format="mp3")
        speed_adjusted_file.close()
        
        print(f"✅ Pydub 속도 조정 완료: {len(audio)}ms → {len(speed_adjusted_audio)}ms")
        return speed_adjusted_file.name
    
    def _speed_up_with_sampling(self, audio_path, speed_factor):
        """방법 4: 간단한 샘플링 기반 속도 조정"""
        print(f"📊 샘플링 방식 속도 조정 시도...")
        
        try:
            import numpy as np
            import wave
        except ImportError:
            raise Exception("numpy 라이브러리가 필요합니다")
        
        # WAV로 먼저 변환 (필요한 경우)
        from moviepy.editor import AudioFileClip
        temp_wav = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        temp_wav.close()
        
        audio_clip = AudioFileClip(audio_path)
        audio_clip.write_audiofile(temp_wav.name, verbose=False, logger=None)
        audio_clip.close()
        
        # WAV 파일 읽기
        with wave.open(temp_wav.name, 'rb') as wav_file:
            frames = wav_file.readframes(-1)
            sound_info = wav_file.getparams()
            audio_data = np.frombuffer(frames, dtype=np.int16)
        
        # 샘플링으로 속도 조정 (간단한 방법)
        step = int(1 / speed_factor * len(audio_data))
        if step > 0:
            speed_adjusted_data = audio_data[::int(1/speed_factor)]
        else:
            speed_adjusted_data = audio_data
        
        # 새로운 WAV 파일 생성
        speed_adjusted_wav = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        with wave.open(speed_adjusted_wav.name, 'wb') as new_wav:
            new_wav.setparams(sound_info)
            new_wav.writeframes(speed_adjusted_data.tobytes())
        speed_adjusted_wav.close()
        
        # MP3로 변환
        speed_adjusted_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        converted_clip = AudioFileClip(speed_adjusted_wav.name)
        converted_clip.write_audiofile(speed_adjusted_file.name, verbose=False, logger=None)
        converted_clip.close()
        speed_adjusted_file.close()
        
        # 임시 파일 정리
        os.unlink(temp_wav.name)
        os.unlink(speed_adjusted_wav.name)
        
        print(f"✅ 샘플링 속도 조정 완료")
        return speed_adjusted_file.name
    
    def convert_foreign_to_korean(self, text: str) -> str:
        """
        텍스트 내 외국어(영어, 일본어, 중국어 등)를 한글 발음으로 변환
        외국어 뒤에 한글이 붙어있어도 외국어 부분만 정확히 추출하여 변환

        예시:
        - "LAS이외의" → "라스이외의" (LAS만 검색)
        - "AI가" → "에이아이가"
        - "YouTube를" → "유튜브를"

        Args:
            text: 원본 텍스트

        Returns:
            외국어가 한글 발음으로 변환된 텍스트
        """
        import re

        # 외국어 패턴 + 뒤에 붙은 한글 (0개 이상)
        # 그룹1: 외국어 부분 (영어+숫자, 일본어, 중국어)
        # 그룹2: 뒤에 붙은 한글 부분 (조사, 복합명사 등)
        foreign_pattern = re.compile(
            r'([A-Za-z0-9]+|[ぁ-ゔァ-ヴー]+|[\u4e00-\u9fff]+)'  # 외국어
            r'([가-힣]*)'  # 뒤에 붙은 한글 (0개 이상)
        )

        def replace_word(match):
            foreign_part = match.group(1)  # 외국어 부분 (예: "LAS", "AI", "YouTube")
            korean_part = match.group(2)   # 뒤에 붙은 한글 (예: "이외의", "가", "를", "")

            # 순수 한글만 있는 경우 스킵
            if re.match(r'^[가-힣]+$', foreign_part):
                return match.group(0)  # 원본 그대로

            # 딕셔너리에서 외국어 부분만 검색
            if self.pronunciation_dict.has_pronunciation(foreign_part):
                korean_pronunciation = self.pronunciation_dict.get_pronunciation(foreign_part)
                logger.info(f"🔄 외국어→한글 변환: {foreign_part}{korean_part} → {korean_pronunciation}{korean_part}")
                return korean_pronunciation + korean_part  # 변환된 발음 + 원본 한글
            else:
                # 사전에 없으면 원본 유지
                logger.debug(f"📖 사전 미등록: {foreign_part}")
                return match.group(0)  # 원본 그대로

        # 모든 외국어 단어를 한글 발음으로 변환
        converted_text = foreign_pattern.sub(replace_word, text)

        return converted_text

    def preprocess_korean_text(self, text):
        """한국어 TTS 품질 향상을 위한 텍스트 전처리 (외국어 변환 + 괄호 제거 포함)"""
        try:
            import re
            processed = text.strip()

            # 1. 외국어 → 한글 발음 변환 (영어, 일본어, 중국어 등)
            processed = self.convert_foreign_to_korean(processed)

            # 2. 괄호 내용 제거 (괄호와 그 안의 모든 내용)
            processed = re.sub(r'\([^)]*\)', '', processed)

            # 3. 이모지 제거 (한글 텍스트는 보존)
            emoji_pattern = re.compile("["
                u"\U0001F600-\U0001F64F"  # emoticons
                u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                u"\U0001F680-\U0001F6FF"  # transport & map symbols
                u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                "]+", flags=re.UNICODE)
            processed = emoji_pattern.sub(' ', processed)

            # 4. 물음표, 느낌표, 물결표시를 마침표로 변환
            processed = re.sub(r'[?!~]+', '.', processed)

            # 5. 공백 정리
            processed = re.sub(r'\s+', ' ', processed).strip()
            if processed and not processed.endswith('.'):
                processed += '.'

            logger.info(f"TTS 전처리 전: {text}")
            logger.info(f"TTS 전처리 후: {processed}")

            return processed

        except Exception as e:
            logger.error(f"텍스트 전처리 실패: {e}")
            return text  # 실패시 원본 반환
    
    def get_audio_duration(self, audio_path):
        """오디오 파일의 실제 재생 시간 반환"""
        try:
            audio = AudioFileClip(audio_path)
            duration = audio.duration
            audio.close()
            return duration
        except Exception as e:
            print(f"오디오 길이 확인 실패: {e}")
            return 3.0  # 기본값
    
    def get_local_images(self, test_folder="./test"):
        """test 폴더에서 이미지 파일들을 이름순으로 가져오기"""
        import glob
        
        # 이미지 확장자 패턴 (webp 추가)
        image_patterns = ["*.jpg", "*.jpeg", "*.png", "*.bmp", "*.gif", "*.webp"]
        image_files = []
        
        for pattern in image_patterns:
            files = glob.glob(os.path.join(test_folder, pattern))
            files.extend(glob.glob(os.path.join(test_folder, pattern.upper())))
            image_files.extend(files)
        
        # 숫자 순서대로 정렬 (1.png, 2.png, 3.png, 4.png)
        import re
        def natural_sort_key(path):
            filename = os.path.basename(path).lower()
            # 숫자 부분 추출
            numbers = re.findall(r'\d+', filename)
            if numbers:
                return int(numbers[0])  # 첫 번째 숫자로 정렬
            else:
                return float('inf')  # 숫자가 없으면 맨 뒤로
        
        image_files.sort(key=natural_sort_key)
        
        print(f"로컬 이미지 파일 발견: {len(image_files)}개 (숫자 순서대로)")
        for i, file in enumerate(image_files):
            print(f"  {i+1}. {os.path.basename(file)}")
        
        if len(image_files) == 0:
            print("❌ test 폴더에 이미지 파일이 없습니다")
        else:
            print(f"✅ 이미지 사용 순서: {' → '.join([os.path.basename(f) for f in image_files])}")
        
        return image_files
    
    def create_video_with_local_images(self, content, music_path, output_folder, image_allocation_mode="2_per_image", text_position="bottom", text_style="outline", title_area_mode="keep", title_font="BMYEONSUNG_otf.otf", body_font="BMYEONSUNG_otf.otf", title_font_size=42, body_font_size=36, music_mood="bright", media_files=None, voice_narration="enabled", cross_dissolve="enabled", subtitle_duration=0.0, image_panning_options=None, tts_engine="edge", qwen_speaker="Sohee", qwen_speed="normal", qwen_style="neutral", edge_speaker="female", edge_speed="normal", edge_pitch="normal"):
        """로컬 이미지 파일들을 사용한 릴스 영상 생성

        Args:
            image_panning_options: 이미지별 패닝 옵션 딕셔너리 (예: {0: True, 1: False, 2: True})
                                   None이면 모든 이미지에 패닝 적용 (기본값)
        """
        try:
            # 디버깅: 파라미터 확인
            print(f"🔍 create_video_with_local_images 호출됨!")
            print(f"🔍 cross_dissolve 파라미터: '{cross_dissolve}' (타입: {type(cross_dissolve)})")
            print(f"🔍 image_panning_options: {image_panning_options}")
            logging.info(f"🔍 create_video_with_local_images 호출됨!")
            logging.info(f"🔍 cross_dissolve 파라미터: '{cross_dissolve}' (타입: {type(cross_dissolve)})")
            logging.info(f"🔍 image_panning_options: {image_panning_options}")

            # TTS 엔진 설정 적용
            self.set_tts_engine(tts_engine, qwen_speaker, qwen_speed, qwen_style,
                               edge_speaker=edge_speaker, edge_speed=edge_speed, edge_pitch=edge_pitch)
            logger.info(f"🎤 TTS 설정: 엔진={tts_engine}, Qwen화자={qwen_speaker}, Qwen속도={qwen_speed}, Qwen스타일={qwen_style}, Edge화자={edge_speaker}, Edge속도={edge_speed}, Edge톤={edge_pitch}")

            # 로컬 이미지 파일들 가져오기
            local_images = self.get_local_images()

            if not local_images:
                raise Exception("test 폴더에 이미지 파일이 없습니다")

            print(f"로컬 이미지 {len(local_images)}개를 사용하여 영상 생성")

            # media_files가 없는 경우 로컬 파일들의 타입 정보 생성
            if media_files is None:
                logging.info("🔍 media_files가 None이므로 자동 생성합니다...")
                print("🔍 media_files가 None이므로 자동 생성합니다...")
                media_files = []
                video_extensions = ['.mp4', '.mov', '.avi', '.webm', '.mkv', '.gif']
                for i, image_path in enumerate(local_images):
                    # 파일 확장자로 타입 판단
                    is_video = any(image_path.lower().endswith(ext) for ext in video_extensions)
                    file_type = "video" if is_video else "image"
                    media_files.append((image_path, file_type))
                    msg = f"  📁 자동 감지 [{i}]: {os.path.basename(image_path)} -> {file_type}"
                    print(msg)
                    logging.info(msg)
            else:
                msg = f"🔍 media_files가 이미 제공됨: {len(media_files)}개"
                print(msg)
                logging.info(msg)

            msg = f"💽 최종 미디어 파일 정보: {len(media_files)}개"
            print(msg)
            logging.info(msg)
            for i, (path, file_type) in enumerate(media_files):
                msg = f"  [{i}] {os.path.basename(path)} -> {file_type}"
                print(msg)
                logging.info(msg)
            print(f"🏠 타이틀 영역 모드: {title_area_mode}")

            # 타이틀 영역 모드에 따른 처리
            title_image_path = None
            if title_area_mode == "keep":
                # 기존 방식: 타이틀 영역 유지 (504x220)
                title_image_path = self.create_title_image(
                    content['title'],
                    self.video_width,
                    220,
                    title_font,
                    title_font_size
                )
                print("✅ 타이틀 영역 확보: 220px 타이틀 + 670px 미디어")
            else:
                # remove 모드: 타이틀 제거, 전체 화면 미디어
                print("✅ 타이틀 영역 제거: 전체 890px 미디어")
            
            # 각 body별로 개별 TTS 생성 (빈 값 제외, 순서 보장)
            body_keys = [key for key in content.keys() if key.startswith('body') and content[key].strip()]
            body_keys.sort(key=lambda x: int(x.replace('body', '')))  # body1, body2, ... 순서로 정렬
            logger.info(f"🎯 body 순서 확인: {body_keys}")
            logger.info(f"🔍 [디버깅] voice_narration='{voice_narration}' (타입: {type(voice_narration).__name__})")
            logger.info(f"🔍 [디버깅] subtitle_duration={subtitle_duration} (타입: {type(subtitle_duration).__name__})")
            logger.info(f"🔍 [디버깅] 조건 체크: voice_narration == 'disabled' = {voice_narration == 'disabled'}")
            logger.info(f"🔍 [디버깅] 조건 체크: subtitle_duration > 0 = {subtitle_duration > 0}")
            tts_files = []

            for body_key in body_keys:
                # 자막 지속 시간 최적화: voice_narration=disabled이고 subtitle_duration > 0이면 TTS 생성 건너뜀
                if voice_narration == "disabled" and subtitle_duration > 0:
                    logger.info(f"⏱️ {body_key} TTS 건너뜀 (자막 지속 시간 {subtitle_duration}초 사용)")
                    tts_files.append((body_key, None, subtitle_duration))
                else:
                    # 대사별 TTS 설정이 있으면 임시로 화자/스타일 교체
                    original_speaker = self.qwen_speaker
                    original_style = self.qwen_style
                    if self.per_body_tts_settings and self.tts_engine == 'qwen' and body_key in self.per_body_tts_settings:
                        body_setting = self.per_body_tts_settings[body_key]
                        self.qwen_speaker = body_setting.get('speaker', original_speaker)
                        self.qwen_style = body_setting.get('style', original_style)
                        logger.info(f"🎭 {body_key} 개별 TTS: 화자={self.qwen_speaker}, 스타일={self.qwen_style}")

                    logger.info(f"🎙️ {body_key} TTS 생성 중... 내용: '{content[body_key][:50]}...'")
                    body_tts = self.create_tts_audio(content[body_key])

                    # 원래 설정 복원
                    self.qwen_speaker = original_speaker
                    self.qwen_style = original_style

                    if body_tts:
                        body_duration = self.get_audio_duration(body_tts)
                        tts_files.append((body_key, body_tts, body_duration))
                        logger.info(f"✅ {body_key} TTS 완료: {body_duration:.1f}초")
                    else:
                        logger.error(f"❌ {body_key} TTS 생성 실패")

            # 이미지 할당 모드에 따른 처리 분기
            print(f"🎬 이미지 할당 모드: {image_allocation_mode}")

            group_clips = []
            audio_segments = []
            
            if image_allocation_mode == "1_per_image":
                # Mode 2: body 1개당 이미지 1개 (1:1 매칭)
                print("🖼️ 1:1 매칭 모드: body별로 각각 다른 이미지 사용")
                
                for i, body_key in enumerate(body_keys):
                    # body별로 개별 이미지 할당 (이미지가 부족하면 마지막 이미지 사용)
                    image_index = min(i, len(local_images) - 1)
                    current_image_path = local_images[image_index]
                    print(f"🎯 매칭 디버그: i={i}, body_key={body_key}, image_index={image_index}, image={os.path.basename(current_image_path)}")
                    
                    # 해당 body의 TTS 정보 찾기
                    body_tts_info = None
                    body_duration = 3.0
                    for tts_key, tts_path, tts_duration in tts_files:
                        if tts_key == body_key:
                            body_tts_info = (body_key, content[body_key], tts_path, tts_duration)
                            body_duration = tts_duration
                            break
                    else:
                        body_tts_info = (body_key, content[body_key], None, 3.0)
                    
                    # 파일 타입 확인 (비디오 vs 이미지)
                    video_extensions = ['.mp4', '.mov', '.avi', '.webm', '.mkv', '.gif']
                    is_video = any(current_image_path.lower().endswith(ext) for ext in video_extensions)
                    file_type = "비디오" if is_video else "이미지"
                    
                    print(f"📸 {body_key}: {file_type} {image_index + 1}/{len(local_images)} → '{os.path.basename(current_image_path)}' ({body_duration:.1f}초)")
                    
                    # 이미지별 패닝 옵션 확인
                    enable_panning = True  # 기본값
                    if image_panning_options is not None and image_index in image_panning_options:
                        enable_panning = image_panning_options[image_index]
                        print(f"🎨 이미지 {image_index}: 패닝 옵션 = {enable_panning}")

                    # 타이틀 영역 모드에 따른 배경 클립 생성
                    if title_area_mode == "keep":
                        # 기존 방식: 타이틀 영역 + 미디어 영역
                        if is_video:
                            # 비디오는 항상 패닝 off (중앙 고정 배치)
                            bg_clip = self.create_video_background_clip(current_image_path, body_duration, enable_panning=False)
                        else:
                            bg_clip = self.create_background_clip(current_image_path, body_duration, enable_panning=enable_panning, title_area_mode=title_area_mode)
                        black_top = ColorClip(size=(self.video_width, self.title_height), color=(0,0,0)).set_duration(body_duration).set_position((0, 0))
                        title_clip = ImageClip(title_image_path).set_duration(body_duration).set_position((0, 0))

                        # 텍스트 클립 (기존 위치)
                        text_image_path = self.create_text_image(content[body_key], self.video_width, self.video_height, text_position, text_style, is_title=False, title_font=title_font, body_font=body_font, title_area_mode=title_area_mode, title_font_size=title_font_size, body_font_size=body_font_size)
                        text_clip = ImageClip(text_image_path).set_duration(body_duration).set_position((0, 0))

                        # 기존 방식 합성
                        individual_clip = CompositeVideoClip([bg_clip, black_top, title_clip, text_clip], size=(self.video_width, self.video_height))
                    else:
                        # remove 모드: 전체 화면 미디어 + 동일한 텍스트 위치
                        if is_video:
                            # 비디오는 항상 패닝 off (중앙 고정 배치)
                            bg_clip = self.create_fullscreen_video_clip(current_image_path, body_duration, enable_panning=False)
                        else:
                            bg_clip = self.create_fullscreen_background_clip(current_image_path, body_duration, enable_panning=enable_panning)

                        # 텍스트 클립 (기존과 동일한 위치 유지)
                        text_image_path = self.create_text_image(content[body_key], self.video_width, self.video_height, text_position, text_style, is_title=False, title_font=title_font, body_font=body_font, title_area_mode=title_area_mode, title_font_size=title_font_size, body_font_size=body_font_size)
                        text_clip = ImageClip(text_image_path).set_duration(body_duration).set_position((0, 0))

                        # 전체 화면 합성 (타이틀 없음)
                        individual_clip = CompositeVideoClip([bg_clip, text_clip], size=(self.video_width, self.video_height))
                    group_clips.append(individual_clip)
                    print(f"    ✅ {body_key} 완료: 개별 이미지 적용")
                    
                    # 오디오 추가 (voice_narration이 enabled일 때만)
                    if body_tts_info[2] and voice_narration == "enabled":  # tts_path가 있고 자막 읽어주기가 활성화된 경우에만
                        audio_segments.append(AudioFileClip(body_tts_info[2]))

            elif image_allocation_mode == "2_per_image":
                # Mode 1: body 2개당 이미지 1개 (그룹 방식)
                print("🖼️ 2:1 매칭 모드: body 2개당 이미지 1개 사용")
                
                for group_idx in range(0, len(body_keys), 2):
                    group_bodies = body_keys[group_idx:group_idx + 2]
                    # 그룹 순서대로 이미지 사용 (body1,2 → image0, body3,4 → image1)
                    image_index = min(group_idx // 2, len(local_images) - 1)
                    current_image_path = local_images[image_index]
                    print(f"그룹 {group_idx//2 + 1}: 이미지 인덱스 {image_index}, 파일: {os.path.basename(current_image_path)}")
                    
                    # 그룹 TTS 정보 수집
                    group_tts_info = []
                    group_total_duration = 0.0
                    
                    for body_key in group_bodies:
                        for tts_key, tts_path, tts_duration in tts_files:
                            if tts_key == body_key:
                                group_tts_info.append((body_key, content[body_key], tts_path, tts_duration))
                                group_total_duration += tts_duration
                                break
                        else:
                            group_tts_info.append((body_key, content[body_key], None, 3.0))
                            group_total_duration += 3.0
                    
                    # 파일 타입 확인 (비디오 vs 이미지)
                    video_extensions = ['.mp4', '.mov', '.avi', '.webm', '.mkv', '.gif']
                    is_video = any(current_image_path.lower().endswith(ext) for ext in video_extensions)
                    file_type = "비디오" if is_video else "이미지"
                    
                    print(f"📸 그룹 {group_idx//2 + 1}: {[info[0] for info in group_tts_info]} → '{os.path.basename(current_image_path)}' ({file_type}, {group_total_duration:.1f}초)")

                    # 이미지별 패닝 옵션 확인
                    enable_panning = True  # 기본값
                    if image_panning_options is not None and image_index in image_panning_options:
                        enable_panning = image_panning_options[image_index]
                        print(f"🎨 이미지 {image_index}: 패닝 옵션 = {enable_panning}")

                    # 타이틀 영역 모드에 따른 배경 클립 생성
                    if title_area_mode == "keep":
                        # 기존 방식: 타이틀 영역 + 미디어 영역
                        if is_video:
                            # 비디오는 항상 패닝 off (중앙 고정 배치)
                            bg_clip = self.create_video_background_clip(current_image_path, group_total_duration, enable_panning=False)
                        else:
                            bg_clip = self.create_continuous_background_clip(current_image_path, group_total_duration, 0.0, enable_panning=enable_panning, title_area_mode=title_area_mode)
                        black_top = ColorClip(size=(self.video_width, self.title_height), color=(0,0,0)).set_duration(group_total_duration)
                        title_clip = ImageClip(title_image_path).set_duration(group_total_duration).set_position((0, 0))

                        # 텍스트 클립들 (기존 위치)
                        text_clips = []
                        current_time = 0.0
                        for body_key, body_text, tts_path, duration in group_tts_info:
                            text_image_path = self.create_text_image(body_text, self.video_width, self.video_height, text_position, text_style, is_title=False, title_font=title_font, body_font=body_font, title_area_mode=title_area_mode, title_font_size=title_font_size, body_font_size=body_font_size)
                            text_clip = ImageClip(text_image_path).set_start(current_time).set_duration(duration).set_position((0, 0))
                            text_clips.append(text_clip)
                            print(f"      {body_key}: {current_time:.1f}~{current_time + duration:.1f}초")
                            current_time += duration

                        # 기존 방식 합성
                        group_clip = CompositeVideoClip([bg_clip, black_top, title_clip] + text_clips, size=(self.video_width, self.video_height))
                    else:
                        # remove 모드: 전체 화면 미디어 + 동일한 텍스트 위치
                        if is_video:
                            # 비디오는 항상 패닝 off (중앙 고정 배치)
                            bg_clip = self.create_fullscreen_video_clip(current_image_path, group_total_duration, enable_panning=False)
                        else:
                            bg_clip = self.create_fullscreen_background_clip(current_image_path, group_total_duration, enable_panning=enable_panning)

                        # 텍스트 클립들 (기존과 동일한 위치 유지)
                        text_clips = []
                        current_time = 0.0
                        for body_key, body_text, tts_path, duration in group_tts_info:
                            text_image_path = self.create_text_image(body_text, self.video_width, self.video_height, text_position, text_style, is_title=False, title_font=title_font, body_font=body_font, title_area_mode=title_area_mode, title_font_size=title_font_size, body_font_size=body_font_size)
                            text_clip = ImageClip(text_image_path).set_start(current_time).set_duration(duration).set_position((0, 0))
                            text_clips.append(text_clip)
                            print(f"      {body_key}: {current_time:.1f}~{current_time + duration:.1f}초")
                            current_time += duration

                        # 전체 화면 합성 (타이틀 없음)
                        group_clip = CompositeVideoClip([bg_clip] + text_clips, size=(self.video_width, self.video_height))
                    group_clips.append(group_clip)
                    print(f"    ✅ 그룹 {group_idx//2 + 1} 완료: 배경 연속 보장")
                    
                    # 오디오 추가 (voice_narration이 enabled일 때만)
                    for _, _, tts_path, _ in group_tts_info:
                        if tts_path and voice_narration == "enabled":
                            audio_segments.append(AudioFileClip(tts_path))

            else:  # image_allocation_mode == "single_for_all"
                # Mode 3: 모든 대사에 미디어 1개 (단일 이미지/비디오 연속 사용)
                print("🖼️ 1:ALL 매칭 모드: 모든 대사에 동일한 미디어 1개 연속 사용")
                logger.debug(f"🔍 [DEBUG] single_for_all 모드 진입 - body 개수: {len(body_keys)}")

                # 첫 번째 이미지/비디오만 사용
                if local_images:
                    single_media_path = local_images[0]
                    print(f"사용할 미디어: {os.path.basename(single_media_path)}")
                    logger.debug(f"🔍 [DEBUG] 미디어 파일 경로: {single_media_path}")
                    logger.debug(f"🔍 [DEBUG] 파일 존재 여부: {os.path.exists(single_media_path)}")

                    # 모든 대사의 TTS 정보 수집
                    all_tts_info = []
                    total_duration = 0.0

                    for body_key in body_keys:
                        for tts_key, tts_path, tts_duration in tts_files:
                            if tts_key == body_key:
                                all_tts_info.append((body_key, content[body_key], tts_path, tts_duration))
                                total_duration += tts_duration
                                break
                        else:
                            all_tts_info.append((body_key, content[body_key], None, 3.0))
                            total_duration += 3.0

                    # 파일 타입 확인 (비디오 vs 이미지)
                    video_extensions = ['.mp4', '.mov', '.avi', '.webm', '.mkv', '.gif']
                    is_video = any(single_media_path.lower().endswith(ext) for ext in video_extensions)
                    file_type = "비디오" if is_video else "이미지"
                    logger.debug(f"🔍 [DEBUG] 파일 타입 판별: is_video={is_video}, file_type={file_type}")

                    print(f"📍 모든 대사 ({len(body_keys)}개): {file_type} 연속 사용 - {os.path.basename(single_media_path)} (총 {total_duration:.1f}초)")

                    # 이미지별 패닝 옵션 확인 (단일 이미지는 인덱스 0)
                    enable_panning = True  # 기본값
                    if image_panning_options is not None and 0 in image_panning_options:
                        enable_panning = image_panning_options[0]
                        print(f"🎨 단일 이미지: 패닝 옵션 = {enable_panning}")

                    # 타이틀 영역 모드에 따른 배경 클립 생성
                    logger.debug(f"🔍 [DEBUG] title_area_mode={title_area_mode}, is_video={is_video}")
                    if title_area_mode == "keep":
                        # 기존 방식: 타이틀 영역 + 미디어 영역
                        if is_video:
                            # 비디오는 항상 패닝 off (중앙 고정 배치)
                            logger.debug(f"🔍 [DEBUG] create_video_background_clip() 호출 시작 (keep 모드)")
                            bg_clip = self.create_video_background_clip(single_media_path, total_duration, enable_panning=False)
                            logger.debug(f"🔍 [DEBUG] create_video_background_clip() 호출 완료 (keep 모드)")
                        else:
                            bg_clip = self.create_continuous_background_clip(single_media_path, total_duration, 0.0, enable_panning=enable_panning, title_area_mode=title_area_mode)
                        black_top = ColorClip(size=(self.video_width, self.title_height), color=(0,0,0)).set_duration(total_duration)
                        title_clip = ImageClip(title_image_path).set_duration(total_duration).set_position((0, 0))

                        # 텍스트 클립들 (기존 위치)
                        text_clips = []
                        current_time = 0.0
                        for body_key, body_text, tts_path, duration in all_tts_info:
                            text_image_path = self.create_text_image(body_text, self.video_width, self.video_height, text_position, text_style, is_title=False, title_font=title_font, body_font=body_font, title_area_mode=title_area_mode, title_font_size=title_font_size, body_font_size=body_font_size)
                            text_clip = ImageClip(text_image_path).set_start(current_time).set_duration(duration).set_position((0, 0))
                            text_clips.append(text_clip)
                            print(f"      {body_key}: {current_time:.1f}~{current_time + duration:.1f}초")
                            current_time += duration

                        # 기존 방식 합성
                        single_clip = CompositeVideoClip([bg_clip, black_top, title_clip] + text_clips, size=(self.video_width, self.video_height))
                    else:
                        # remove 모드: 전체 화면 미디어 + 동일한 텍스트 위치
                        if is_video:
                            # 비디오는 항상 패닝 off (중앙 고정 배치)
                            logger.debug(f"🔍 [DEBUG] create_fullscreen_video_clip() 호출 시작 (remove 모드)")
                            bg_clip = self.create_fullscreen_video_clip(single_media_path, total_duration, enable_panning=False)
                            logger.debug(f"🔍 [DEBUG] create_fullscreen_video_clip() 호출 완료 (remove 모드)")
                        else:
                            bg_clip = self.create_fullscreen_background_clip(single_media_path, total_duration, enable_panning=enable_panning)

                        # 텍스트 클립들 (기존과 동일한 위치 유지)
                        text_clips = []
                        current_time = 0.0
                        for body_key, body_text, tts_path, duration in all_tts_info:
                            text_image_path = self.create_text_image(body_text, self.video_width, self.video_height, text_position, text_style, is_title=False, title_font=title_font, body_font=body_font, title_area_mode=title_area_mode, title_font_size=title_font_size, body_font_size=body_font_size)
                            text_clip = ImageClip(text_image_path).set_start(current_time).set_duration(duration).set_position((0, 0))
                            text_clips.append(text_clip)
                            print(f"      {body_key}: {current_time:.1f}~{current_time + duration:.1f}초")
                            current_time += duration

                        # 전체 화면 합성 (타이틀 없음)
                        single_clip = CompositeVideoClip([bg_clip] + text_clips, size=(self.video_width, self.video_height))

                    group_clips.append(single_clip)
                    print(f"    ✅ 모든 대사 완료: 단일 미디어 연속 적용 ({total_duration:.1f}초)")

                    # 오디오 추가 (voice_narration이 enabled일 때만)
                    for _, _, tts_path, _ in all_tts_info:
                        if tts_path and voice_narration == "enabled":
                            audio_segments.append(AudioFileClip(tts_path))

            # 그룹들 연결 (크로스 디졸브 옵션에 따라 처리)
            print(f"🎬 영상 클립들 연결: {len(group_clips)}개 클립")
            print(f"🔍 [그룹모드] cross_dissolve 값: '{cross_dissolve}' (타입: {type(cross_dissolve)})")
            logging.info(f"🎬 영상 클립들 연결: {len(group_clips)}개 클립")
            logging.info(f"🔍 [그룹모드] cross_dissolve 값: '{cross_dissolve}' (타입: {type(cross_dissolve)})")
            if cross_dissolve == "enabled":
                print("🎨 [그룹모드] 크로스 디졸브 효과 적용")
                logging.info("🎨 [그룹모드] 크로스 디졸브 효과 적용")
                final_video = self.apply_smart_crossfade_transitions(group_clips, media_files, image_allocation_mode)
            else:
                print("🎬 [그룹모드] 기본 연결 방식 사용 (크로스 디졸브 미적용)")
                logging.info("🎬 [그룹모드] 기본 연결 방식 사용 (크로스 디졸브 미적용)")
                final_video = concatenate_videoclips(group_clips, method="compose")
            
            # 8. TTS 오디오들 연결
            final_audio = None
            if audio_segments:
                final_audio = concatenate_audioclips(audio_segments)

                # 자막 읽어주기 설정에 따른 TTS 볼륨 조절
                if voice_narration == "disabled":
                    print("🔇 자막 읽어주기 제거: TTS 볼륨을 0으로 설정")
                    final_audio = final_audio.volumex(0)  # TTS 음성 무음 처리
            else:
                print("📢 TTS 오디오 없음 (자막 지속 시간 모드 또는 생성 실패)")

            # 9. 배경음악 또는 원본 비디오 소리 추가
            if music_mood == "none":
                # 음악 선택 안함: 원본 비디오 파일에서 직접 오디오 추출
                print("🔇 음악 선택 안함 모드: 원본 비디오 파일에서 오디오 추출")
                video_audio = None
                video_extensions = ['.mp4', '.mov', '.avi', '.webm', '.mkv', '.gif']

                if media_files:
                    for media_path, file_type in media_files:
                        if file_type == "video" and any(media_path.lower().endswith(ext) for ext in video_extensions):
                            try:
                                source_clip = VideoFileClip(media_path)
                                if source_clip.audio is not None:
                                    video_audio = source_clip.audio
                                    # 오디오 길이를 영상 길이에 맞춤
                                    target_duration = final_audio.duration if final_audio else final_video.duration
                                    if video_audio.duration < target_duration:
                                        video_audio = video_audio.loop(duration=target_duration)
                                    else:
                                        video_audio = video_audio.subclip(0, target_duration)
                                    print(f"📹 원본 비디오 오디오 추출 성공: {os.path.basename(media_path)} ({video_audio.duration:.1f}초)")
                                    break  # 첫 번째 비디오의 오디오만 사용
                                else:
                                    print(f"📸 비디오에 오디오 없음: {os.path.basename(media_path)}")
                            except Exception as e:
                                print(f"⚠️ 비디오 오디오 추출 실패 ({os.path.basename(media_path)}): {e}")
                                continue
                else:
                    print("⚠️ 미디어 파일 정보 없음 - 원본 비디오 소리 사용 불가")

                # 비디오 오디오와 TTS 합성
                if video_audio is not None:
                    if voice_narration == "disabled" or final_audio is None:
                        # 자막 읽어주기 제거: 원본 비디오 소리 100%
                        final_audio = video_audio.volumex(1.0)
                        print("🔊 자막 읽어주기 꺼짐 - 원본 비디오 소리 100%")
                    else:
                        # 자막 읽어주기 추가: TTS(70%) + 원본 비디오 소리(50%) 믹싱
                        video_audio = video_audio.volumex(0.5)
                        final_audio = CompositeAudioClip([
                            final_audio.volumex(0.7),
                            video_audio
                        ])
                        print("🎵 TTS(70%) + 비디오 원본 오디오(50%) 합성 완료")
                else:
                    if voice_narration == "disabled" or final_audio is None:
                        print("🔇 자막 읽어주기 제거 + 비디오 오디오 없음: 완전 무음")
                    else:
                        print("🔇 비디오 오디오 없음: TTS만 사용")

            elif music_path and os.path.exists(music_path):
                # 배경음악 사용
                background_music = AudioFileClip(music_path)

                # 배경음악 길이 조정 기준: final_audio가 있으면 그 길이, 없으면 영상 길이
                target_duration = final_audio.duration if final_audio else final_video.duration

                # 배경음악이 영상보다 짧으면 반복, 길면 자르기
                if background_music.duration < target_duration:
                    background_music = background_music.loop(duration=target_duration)
                else:
                    background_music = background_music.subclip(0, target_duration)

                if voice_narration == "disabled" or final_audio is None:
                    # 자막 읽어주기 제거: 배경음악 100%
                    final_audio = background_music.volumex(1.0)  # 배경음악 볼륨 100%
                    print("🔇 자막 읽어주기 제거: 배경음악 100%")
                else:
                    # 자막 읽어주기 추가: TTS + 배경음악 합성
                    background_music = background_music.volumex(0.15)  # 볼륨 15% (TTS가 잘 들리도록)
                    final_audio = CompositeAudioClip([final_audio, background_music])
                    print("🎵 TTS + 배경음악 합성 완료")

            if final_audio:
                final_video = final_video.set_audio(final_audio)
            else:
                print("🔇 최종 오디오 없음: 무음 영상 생성")
            
            # 10. 최종 영상 저장
            video_id = str(uuid.uuid4())[:8]
            # 타이틀을 파일명에 포함 (파일 시스템 안전 문자로 변환)
            safe_title = re.sub(r'[\\/*?:"<>|\n\r\t]', '', content.get('title', '')).strip()
            safe_title = safe_title[:50]  # 최대 50자 제한
            if safe_title:
                output_filename = f"reels_{video_id}_{safe_title}.mp4"
            else:
                output_filename = f"reels_{video_id}.mp4"
            output_path = os.path.join(output_folder, output_filename)
            
            print(f"최종 영상 렌더링 시작: {output_path}")
            final_video.write_videofile(
                output_path,
                fps=self.fps,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                verbose=False,
                logger=None
            )
            
            print(f"영상 생성 완료: {output_path}")
            return output_path
            
        except Exception as e:
            raise Exception(f"로컬 이미지 영상 생성 실패: {str(e)}")
    
    def create_video(self, content, image_urls, music_path, output_folder, image_allocation_mode="2_per_image", text_position="bottom", text_style="outline"):
        """릴스 영상 생성 (414x896 해상도, 여러 이미지 지원)"""
        try:
            # 여러 이미지 다운로드
            image_paths = []
            for i, image_url in enumerate(image_urls):
                print(f"이미지 {i+1}/{len(image_urls)} 다운로드 중: {image_url}")
                image_path = self.download_image(image_url)
                image_paths.append(image_path)
            
            # 제목 이미지 생성 (504x220, 정확한 타이틀 영역)
            title_image_path = self.create_title_image(
                content['title'],
                self.video_width,
                220,
                title_font
            )
            
            # 각 body별로 개별 TTS 생성 (빈 값 제외, 순서 보장)
            body_keys = [key for key in content.keys() if key.startswith('body') and content[key].strip()]
            body_keys.sort(key=lambda x: int(x.replace('body', '')))  # body1, body2, ... 순서로 정렬
            print(f"🎯 body 순서 확인: {body_keys}")
            tts_files = []
            
            # 제목 TTS 생성
            print("제목 TTS 생성 중...")
            title_tts = self.create_tts_audio(content['title'])
            if title_tts:
                title_duration = self.get_audio_duration(title_tts)
                tts_files.append(('title', title_tts, title_duration))
                print(f"제목 TTS 완료: {title_duration:.1f}초")
            
            # 각 body TTS 생성
            logger.info(f"🔍 [디버깅-1per] voice_narration='{voice_narration}' (타입: {type(voice_narration).__name__})")
            logger.info(f"🔍 [디버깅-1per] subtitle_duration={subtitle_duration} (타입: {type(subtitle_duration).__name__})")
            for body_key in body_keys:
                # 자막 지속 시간 최적화: voice_narration=disabled이고 subtitle_duration > 0이면 TTS 생성 건너뜀
                if voice_narration == "disabled" and subtitle_duration > 0:
                    logger.info(f"⏱️ {body_key} TTS 건너뜀 (자막 지속 시간 {subtitle_duration}초 사용)")
                    tts_files.append((body_key, None, subtitle_duration))
                else:
                    # 대사별 TTS 설정이 있으면 임시로 화자/스타일 교체
                    original_speaker = self.qwen_speaker
                    original_style = self.qwen_style
                    if self.per_body_tts_settings and self.tts_engine == 'qwen' and body_key in self.per_body_tts_settings:
                        body_setting = self.per_body_tts_settings[body_key]
                        self.qwen_speaker = body_setting.get('speaker', original_speaker)
                        self.qwen_style = body_setting.get('style', original_style)
                        logger.info(f"🎭 {body_key} 개별 TTS: 화자={self.qwen_speaker}, 스타일={self.qwen_style}")

                    logger.info(f"🎙️ {body_key} TTS 생성 중... 내용: '{content[body_key][:50]}...'")
                    body_tts = self.create_tts_audio(content[body_key])

                    # 원래 설정 복원
                    self.qwen_speaker = original_speaker
                    self.qwen_style = original_style

                    if body_tts:
                        body_duration = self.get_audio_duration(body_tts)
                        tts_files.append((body_key, body_tts, body_duration))
                        logger.info(f"✅ {body_key} TTS 완료: {body_duration:.1f}초")
                    else:
                        logger.error(f"❌ {body_key} TTS 생성 실패")

            # 이미지 할당 모드에 따른 처리 분기
            print(f"🎬 이미지 할당 모드: {image_allocation_mode}")
            body_clips = []
            audio_segments = []  # TTS 오디오 세그먼트들
            
            if image_allocation_mode == "1_per_image":
                # Mode 2: body 1개당 이미지 1개 (1:1 매칭)
                print("🖼️ 1:1 매칭 모드: body별로 각각 다른 이미지 사용")

                for i, body_key in enumerate(body_keys):
                    print(f"🎯 디버그 2: i={i}, body_key={body_key} (create_video_with_local_images)")
                    # 해당 body의 TTS 정보 찾기
                    body_tts_info = None
                    for tts_key, tts_path, tts_duration in tts_files:
                        if tts_key == body_key:
                            body_tts_info = (tts_path, tts_duration)
                            break
                    
                    if not body_tts_info:
                        print(f"{body_key}의 TTS를 찾을 수 없습니다. 기본 시간 사용.")
                        clip_duration = 3.0
                        tts_path = None
                    else:
                        tts_path, clip_duration = body_tts_info
                    
                    # body별로 개별 이미지 할당 (이미지가 부족하면 마지막 이미지 사용)
                    image_index = min(i, len(image_paths) - 1)  # body1 → image0, body2 → image1, body3 → image2
                    current_image_path = image_paths[image_index]
                    
                    print(f"{body_key} 클립 생성: {clip_duration:.1f}초, 이미지: {image_index + 1}/{len(image_paths)} (1:1 매칭)")
                    
                    # 개별 body 클립 생성
                    bg_clip = self.create_background_clip(current_image_path, clip_duration)
                    black_top = ColorClip(size=(self.video_width, self.title_height), color=(0,0,0)).set_duration(clip_duration).set_position((0, 0))
                    title_clip = ImageClip(title_image_path).set_duration(clip_duration).set_position((0, 0))

                    text_image_path = self.create_text_image(content[body_key], self.video_width, self.video_height, text_position, text_style, is_title=False, title_font=title_font, body_font=body_font, title_area_mode=title_area_mode)
                    text_clip = ImageClip(text_image_path).set_duration(clip_duration).set_position((0, 0))
                    
                    # 개별 클립 합성
                    combined_clip = CompositeVideoClip([bg_clip, black_top, title_clip, text_clip], size=(self.video_width, self.video_height))
                    body_clips.append(combined_clip)
                    
                    # 오디오 세그먼트 추가
                    if tts_path and os.path.exists(tts_path):
                        body_audio = AudioFileClip(tts_path)
                        audio_segments.append(body_audio)
                        print(f"{body_key} 오디오 세그먼트 추가")
                        
            elif image_allocation_mode == "2_per_image":
                # Mode 1: body 2개당 이미지 1개 (그룹 방식)
                print("🖼️ 2:1 매칭 모드: body 2개당 이미지 1개 사용")

                for i, body_key in enumerate(body_keys):
                    print(f"🎯 디버그 3: i={i}, body_key={body_key} (2_per_image mode)")
                    # 해당 body의 TTS 정보 찾기
                    body_tts_info = None
                    for tts_key, tts_path, tts_duration in tts_files:
                        if tts_key == body_key:
                            body_tts_info = (tts_path, tts_duration)
                            break
                    
                    if not body_tts_info:
                        print(f"{body_key}의 TTS를 찾을 수 없습니다. 기본 시간 사용.")
                        clip_duration = 3.0
                        tts_path = None
                    else:
                        tts_path, clip_duration = body_tts_info
                    
                    # body 2개당 이미지 1개 할당 (body1,2 → image0, body3,4 → image1)
                    image_index = min(i // 2, len(image_paths) - 1)
                    current_image_path = image_paths[image_index]
                    
                    print(f"{body_key} 클립 생성: {clip_duration:.1f}초, 이미지: {image_index + 1}/{len(image_paths)} (2:1 매칭)")
                    
                    # 기존 방식대로 클립 생성
                    bg_clip = self.create_background_clip(current_image_path, clip_duration)
                    black_top = ColorClip(size=(self.video_width, self.title_height), color=(0,0,0)).set_duration(clip_duration).set_position((0, 0))
                    title_clip = ImageClip(title_image_path).set_duration(clip_duration).set_position((0, 0))

                    text_image_path = self.create_text_image(content[body_key], self.video_width, self.video_height, text_position, text_style, is_title=False, title_font=title_font, body_font=body_font, title_area_mode=title_area_mode)
                    text_clip = ImageClip(text_image_path).set_duration(clip_duration).set_position((0, 0))
                    
                    # 클립 합성
                    combined_clip = CompositeVideoClip([bg_clip, black_top, title_clip, text_clip], size=(self.video_width, self.video_height))
                    body_clips.append(combined_clip)
                    
                    # 오디오 세그먼트 추가
                    if tts_path and os.path.exists(tts_path):
                        body_audio = AudioFileClip(tts_path)
                        audio_segments.append(body_audio)
                        print(f"{body_key} 오디오 세그먼트 추가")

            else:  # image_allocation_mode == "single_for_all"
                # Mode 3: 모든 대사에 미디어 1개 (단일 이미지 연속 사용)
                print("🖼️ 1:ALL 매칭 모드: 모든 대사에 동일한 이미지 1개 연속 사용")

                # 첫 번째 이미지만 사용
                if image_paths:
                    single_image_path = image_paths[0]
                    print(f"사용할 이미지: {single_image_path}")

                    # 모든 대사의 TTS 정보 수집
                    all_tts_info = []
                    total_duration = 0.0

                    for body_key in body_keys:
                        body_tts_info = None
                        for tts_key, tts_path, tts_duration in tts_files:
                            if tts_key == body_key:
                                body_tts_info = (tts_path, tts_duration)
                                break

                        if not body_tts_info:
                            print(f"{body_key}의 TTS를 찾을 수 없습니다. 기본 시간 사용.")
                            all_tts_info.append((body_key, None, 3.0))
                            total_duration += 3.0
                        else:
                            tts_path, clip_duration = body_tts_info
                            all_tts_info.append((body_key, tts_path, clip_duration))
                            total_duration += clip_duration

                    print(f"📍 모든 대사 ({len(body_keys)}개): 이미지 연속 사용 - {single_image_path} (총 {total_duration:.1f}초)")

                    # 이미지별 패닝 옵션 확인 (단일 이미지는 인덱스 0)
                    enable_panning = True  # 기본값
                    if image_panning_options is not None and 0 in image_panning_options:
                        enable_panning = image_panning_options[0]
                        print(f"🎨 단일 이미지: 패닝 옵션 = {enable_panning}")

                    # 연속된 배경 클립 생성
                    bg_clip = self.create_continuous_background_clip(single_image_path, total_duration, 0.0, enable_panning=enable_panning, title_area_mode=title_area_mode)
                    black_top = ColorClip(size=(self.video_width, self.title_height), color=(0,0,0)).set_duration(total_duration)

                    # 타이틀 클립 생성
                    title_image_path = self.create_text_image(content['title'], self.video_width, 220, text_position, text_style, title_font)
                    title_clip = ImageClip(title_image_path).set_duration(total_duration).set_position((0, 0))

                    # 텍스트 클립들 생성 (시간에 따라 순차 표시)
                    text_clips = []
                    current_time = 0.0
                    for body_key, tts_path, duration in all_tts_info:
                        body_image_path = self.create_text_image(content[body_key], self.video_width, self.video_height, text_position, text_style, body_font)
                        text_clip = ImageClip(body_image_path).set_start(current_time).set_duration(duration).set_position((0, 0))
                        text_clips.append(text_clip)
                        print(f"      {body_key}: {current_time:.1f}~{current_time + duration:.1f}초")
                        current_time += duration

                    # 하나의 연속된 클립으로 합성
                    single_continuous_clip = CompositeVideoClip([bg_clip, black_top, title_clip] + text_clips, size=(self.video_width, self.video_height))
                    body_clips.append(single_continuous_clip)

                    # 오디오 세그먼트 추가
                    for body_key, tts_path, duration in all_tts_info:
                        if tts_path and os.path.exists(tts_path):
                            body_audio = AudioFileClip(tts_path)
                            audio_segments.append(body_audio)
                            print(f"{body_key} 오디오 세그먼트 추가")

                    print(f"    ✅ 모든 대사 완료: 단일 이미지 연속 적용 ({total_duration:.1f}초)")

            # 전체 영상 연결 (크로스 디졸브 옵션에 따라 처리)
            print(f"🎬 본문 클립들 연결: {len(body_clips)}개 클립")
            print(f"🔍 [일반모드] cross_dissolve 값: '{cross_dissolve}' (타입: {type(cross_dissolve)})")
            logging.info(f"🎬 본문 클립들 연결: {len(body_clips)}개 클립")
            logging.info(f"🔍 [일반모드] cross_dissolve 값: '{cross_dissolve}' (타입: {type(cross_dissolve)})")
            if cross_dissolve == "enabled":
                print("🎨 [일반모드] 크로스 디졸브 효과 적용")
                logging.info("🎨 [일반모드] 크로스 디졸브 효과 적용")
                final_video = self.apply_smart_crossfade_transitions(body_clips, media_files, image_allocation_mode)
            else:
                print("🎬 [일반모드] 기본 연결 방식 사용 (크로스 디졸브 미적용)")
                logging.info("🎬 [일반모드] 기본 연결 방식 사용 (크로스 디졸브 미적용)")
                final_video = concatenate_videoclips(body_clips, method="compose")
            print(f"최종 비디오 길이: {final_video.duration:.1f}초")
            
            # TTS 오디오 세그먼트들을 순서대로 연결
            combined_tts = None
            if audio_segments:
                print(f"TTS 오디오 세그먼트 개수: {len(audio_segments)}")
                combined_tts = concatenate_audioclips(audio_segments)
                print(f"결합된 TTS 길이: {combined_tts.duration:.1f}초")

                # 자막 읽어주기 설정에 따른 TTS 볼륨 조절
                if voice_narration == "disabled":
                    print("🔇 자막 읽어주기 제거: TTS 볼륨을 0으로 설정")
                    combined_tts = combined_tts.volumex(0)  # TTS 음성 무음 처리

                # 배경음악 또는 원본 비디오 소리 추가
                audio_tracks = [combined_tts]
            else:
                print("📢 TTS 오디오 없음 (자막 지속 시간 모드 또는 생성 실패)")
                audio_tracks = []

                if music_mood == "none":
                    print("음악 선택 안함 - 원본 비디오 소리 추출 및 추가 중...")
                    # 원본 비디오 소리 추출
                    video_extensions = ['.mp4', '.mov', '.avi', '.webm', '.mkv', '.gif']
                    if media_files:
                        for media_file in media_files:
                            media_path, file_type = media_file
                            if file_type == "video" and any(media_path.lower().endswith(ext) for ext in video_extensions):
                                try:
                                    video_audio = VideoFileClip(media_path).audio
                                    if video_audio is not None:
                                        # 비디오 오디오 길이 조정: TTS가 있으면 TTS 길이에, 없으면 영상 길이에 맞춤
                                        target_duration = combined_tts.duration if combined_tts else final_video.duration
                                        if video_audio.duration < target_duration:
                                            video_audio = video_audio.loop(duration=target_duration)
                                        else:
                                            video_audio = video_audio.subclip(0, target_duration)
                                        # 자막 읽어주기 설정에 따른 비디오 볼륨 조절
                                        if voice_narration == "disabled":
                                            # TTS 음성이 꺼진 경우 원본 비디오 소리를 100%로 설정
                                            video_audio = video_audio.volumex(1.0)
                                            print("🔊 자막 읽어주기 꺼짐 - 원본 비디오 소리 100%")
                                        else:
                                            # TTS와 균형을 맞추기 위해 50% 볼륨으로 설정
                                            video_audio = video_audio.volumex(0.5)
                                            print("🔊 자막 읽어주기 켜짐 - 원본 비디오 소리 50%")
                                        audio_tracks.append(video_audio)
                                        print(f"원본 비디오 소리 추가: {media_path}")
                                        break  # 첫 번째 비디오의 소리만 사용
                                except Exception as e:
                                    print(f"비디오 오디오 추출 실패 ({media_path}): {e}")
                                    continue
                    else:
                        print("⚠️ 미디어 파일 정보 없음 - 원본 비디오 소리 사용 불가")
                elif os.path.exists(music_path):
                    print("배경음악 추가 중...")
                    # 자막 읽어주기 설정에 따른 배경음악 볼륨 조절
                    if voice_narration == "disabled" or combined_tts is None:
                        # TTS 음성이 꺼진 경우 또는 TTS 없는 경우 배경음악을 100%로 설정
                        bg_music = AudioFileClip(music_path).volumex(1.0)
                        print("🎵 자막 읽어주기 꺼짐 - 배경음악 100%")
                    else:
                        # TTS가 더 잘 들리도록 15%로 낮춤
                        bg_music = AudioFileClip(music_path).volumex(0.15)
                        print("🎵 자막 읽어주기 켜짐 - 배경음악 15%")

                    # 배경음악 길이 조정: TTS가 있으면 TTS 길이에, 없으면 영상 길이에 맞춤
                    target_duration = combined_tts.duration if combined_tts else final_video.duration
                    if bg_music.duration < target_duration:
                        bg_music = bg_music.loop(duration=target_duration)
                    else:
                        bg_music = bg_music.subclip(0, target_duration)
                    audio_tracks.append(bg_music)
                
                # 오디오 합성
                if len(audio_tracks) > 1:
                    print("TTS + 배경음악 합성 중...")
                    final_audio = CompositeAudioClip(audio_tracks)
                    final_video = final_video.set_audio(final_audio)
                    print("최종 비디오에 오디오 추가 완료")
                elif len(audio_tracks) == 1:
                    print("단일 오디오 트랙 사용")
                    final_audio = audio_tracks[0]
                    final_video = final_video.set_audio(final_audio)
                    print("최종 비디오에 오디오 추가 완료")
                else:
                    print("🔇 오디오 트랙 없음: 무음 영상 생성")

            # 출력 파일 경로 생성
            video_id = uuid.uuid4().hex[:8]
            # 타이틀을 파일명에 포함 (파일 시스템 안전 문자로 변환)
            safe_title = re.sub(r'[\\/*?:"<>|\n\r\t]', '', content.get('title', '')).strip()
            safe_title = safe_title[:50]  # 최대 50자 제한
            if safe_title:
                output_filename = f"reels_{video_id}_{safe_title}.mp4"
            else:
                output_filename = f"reels_{video_id}.mp4"
            output_path = os.path.join(output_folder, output_filename)
            
            # 영상 렌더링 (이미 414x896으로 구성됨)
            final_video.write_videofile(
                output_path,
                fps=self.fps,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                verbose=False,
                logger=None
            )
            
            # 임시 파일 정리
            if os.path.exists(image_path):
                os.unlink(image_path)
            if os.path.exists(title_image_path):
                os.unlink(title_image_path)
            
            # 모든 TTS 파일 정리
            for tts_key, tts_path, tts_duration in tts_files:
                if os.path.exists(tts_path):
                    os.unlink(tts_path)
                    print(f"{tts_key} TTS 파일 정리: {tts_path}")
            
            return output_path
            
        except Exception as e:
            raise Exception(f"Video generation failed: {str(e)}")
    
    def scan_uploads_folder(self, uploads_folder="uploads"):
        """uploads 폴더를 스캔하여 파일들을 찾고 분류"""
        scan_result = {
            'json_file': None,
            'image_files': [],  # 호환성 유지
            'media_files': []   # 새로운 미디어 파일 리스트
        }
        
        if not os.path.exists(uploads_folder):
            print(f"❌ {uploads_folder} 폴더가 존재하지 않습니다")
            return scan_result
        
        # JSON 파일 찾기 (text.json)
        json_path = os.path.join(uploads_folder, "text.json")
        if os.path.exists(json_path):
            scan_result['json_file'] = json_path
            print(f"✅ JSON 파일 발견: {json_path}")
        
        # 음악 파일은 더 이상 uploads에서 찾지 않음 (bgm 폴더 직접 사용)
        
        # 미디어 파일들 찾기 (이미지 + 비디오)
        image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.heic', '.heif']
        video_extensions = ['.mp4', '.mov', '.avi', '.webm', '.mkv']
        all_extensions = image_extensions + video_extensions
        
        # 숫자로 시작하는 미디어 파일들을 찾아서 정렬
        media_files = []
        image_files = []  # 호환성을 위한 기존 이미지 파일 리스트
        
        # re 모듈 import (패턴 2에서 사용)
        import re

        for filename in os.listdir(uploads_folder):
            if any(filename.lower().endswith(ext) for ext in all_extensions):
                # 파일명에서 숫자 추출 (엄격한 패턴만 허용)
                name_without_ext = os.path.splitext(filename)[0]
                file_number = None

                # 패턴 1: 순수 숫자 (예: "1.jpg", "10.png", "25.webp")
                if name_without_ext.isdigit():
                    file_number = int(name_without_ext)
                    print(f"✅ 패턴 1 매칭: {filename} → {file_number}")
                # 패턴 2: 숫자로 시작 + 언더스코어 (예: "1_image.jpg", "10_video.mp4")
                elif re.match(r'^(\d+)_', name_without_ext):
                    match = re.match(r'^(\d+)_', name_without_ext)
                    file_number = int(match.group(1))
                    print(f"✅ 패턴 2 매칭: {filename} → {file_number}")
                # 그 외 모든 파일은 무시 (preview_, screenshot_, generated_image_pair_ 등)
                else:
                    print(f"⏭️ 무시: {filename} (업로드 파일 패턴 아님)")
                    continue

                # file_number가 추출된 경우만 처리
                if file_number is not None:
                    full_path = os.path.join(uploads_folder, filename)

                    # 파일 타입 결정
                    is_video = any(filename.lower().endswith(ext) for ext in video_extensions)
                    file_type = "video" if is_video else "image"

                    media_files.append((file_number, full_path, file_type))

                    # 호환성을 위해 기존 image_files에도 추가
                    image_files.append((file_number, full_path))
        
        # 숫자 순서대로 정렬
        media_files.sort(key=lambda x: x[0])
        image_files.sort(key=lambda x: x[0])
        
        # 결과 저장
        scan_result['media_files'] = [(path, file_type) for _, path, file_type in media_files]
        scan_result['image_files'] = [path for _, path in image_files]  # 호환성 유지
        
        print(f"📊 미디어 파일 {len(scan_result['media_files'])}개 발견:")
        for i, (media_path, file_type) in enumerate(scan_result['media_files'], 1):
            print(f"   {i}. {os.path.basename(media_path)} ({file_type})")
        
        return scan_result
    
    def create_video_from_uploads(self, output_folder, bgm_file_path=None, image_allocation_mode="2_per_image", text_position="bottom", text_style="outline", title_area_mode="keep", title_font="BMYEONSUNG_otf.otf", body_font="BMYEONSUNG_otf.otf", title_font_size=42, body_font_size=36, uploads_folder="uploads", music_mood="bright", voice_narration="enabled", cross_dissolve="enabled", subtitle_duration=0.0, image_panning_options=None, tts_engine="edge", qwen_speaker="Sohee", qwen_speed="normal", qwen_style="neutral", edge_speaker="female", edge_speed="normal", edge_pitch="normal"):
        """uploads 폴더의 파일들을 사용하여 영상 생성 (기존 메서드 재사용)

        Args:
            image_panning_options: 이미지별 패닝 옵션 딕셔너리 (예: {0: True, 1: False})
        """
        try:
            print("🚀 uploads 폴더 기반 영상 생성 시작")

            # uploads 폴더 스캔
            scan_result = self.scan_uploads_folder(uploads_folder)

            # 필수 파일 검증
            if not scan_result['json_file']:
                raise Exception("text.json 파일이 없습니다")

            if not scan_result['image_files']:
                raise Exception("이미지 파일이 없습니다")

            # JSON 내용 로드
            with open(scan_result['json_file'], 'r', encoding='utf-8') as f:
                content = json.load(f)
            print(f"✅ JSON 내용 로드: {scan_result['json_file']}")

            # 음악 파일 설정 (bgm_file_path 직접 사용)
            music_path = bgm_file_path or ""
            if music_path and os.path.exists(music_path):
                print(f"✅ 음악 파일 사용: {music_path}")
            else:
                print("⚠️  음악 파일 없음 - 음성만 사용")
                music_path = ""

            # 기존 create_video_with_local_images 방식 재사용
            # 스캔된 이미지 파일들로 로컬 이미지 리스트 대체
            self._temp_local_images = scan_result['image_files']

            # 기존 메서드 호출 (이미지 할당 모드, 텍스트 위치, 텍스트 스타일, 타이틀 영역 모드, 폰트 설정, 폰트 크기, 자막 읽어주기, 자막 지속 시간, 패닝 옵션, TTS 설정 전달)
            return self.create_video_with_local_images(content, music_path, output_folder, image_allocation_mode, text_position, text_style, title_area_mode, title_font, body_font, title_font_size, body_font_size, music_mood, scan_result['media_files'], voice_narration, cross_dissolve, subtitle_duration, image_panning_options, tts_engine, qwen_speaker, qwen_speed, qwen_style, edge_speaker, edge_speed, edge_pitch)

        except Exception as e:
            raise Exception(f"uploads 폴더 기반 영상 생성 실패: {str(e)}")
    
    def get_local_images(self, test_folder="./test"):
        """test 폴더에서 이미지 파일들을 이름순으로 가져오기"""
        # uploads 폴더 사용 시 임시 이미지 리스트가 있으면 그것을 사용
        if hasattr(self, '_temp_local_images') and self._temp_local_images:
            images = self._temp_local_images
            self._temp_local_images = None  # 사용 후 정리
            print(f"업로드 이미지 파일 발견: {len(images)}개 (순서대로)")
            for i, file in enumerate(images):
                print(f"  {i+1}. {os.path.basename(file)}")
            return images
        
        # 기존 test 폴더 로직
        import glob
        
        # 이미지 확장자 패턴 (webp 추가)
        image_patterns = ["*.jpg", "*.jpeg", "*.png", "*.bmp", "*.gif", "*.webp"]
        image_files = []
        
        for pattern in image_patterns:
            files = glob.glob(os.path.join(test_folder, pattern))
            files.extend(glob.glob(os.path.join(test_folder, pattern.upper())))
            image_files.extend(files)
        
        # 숫자 순서대로 정렬 (1.png, 2.png, 3.png, 4.png)
        import re
        def natural_sort_key(path):
            filename = os.path.basename(path).lower()
            # 숫자 부분 추출
            numbers = re.findall(r'\d+', filename)
            if numbers:
                return int(numbers[0])  # 첫 번째 숫자로 정렬
            else:
                return float('inf')  # 숫자가 없으면 맨 뒤로
        
        image_files.sort(key=natural_sort_key)
        
        print(f"로컬 이미지 파일 발견: {len(image_files)}개 (숫자 순서대로)")
        for i, file in enumerate(image_files):
            print(f"  {i+1}. {os.path.basename(file)}")
        
        if len(image_files) == 0:
            print("❌ test 폴더에 이미지 파일이 없습니다")
        else:
            print(f"✅ 이미지 사용 순서: {' → '.join([os.path.basename(f) for f in image_files])}")
        
        return image_files
    def create_fullscreen_background_clip(self, image_path, duration, enable_panning=True):
        """전체 화면(504x890)용 이미지 배경 클립 생성 (EXIF + 고품질)

        Args:
            image_path: 이미지 파일 경로
            duration: 클립 지속 시간
            enable_panning: 패닝 활성화 여부 (기본값: True)
        """
        logger.info(f"🖼️ 전체 화면 이미지 클립 생성: {os.path.basename(image_path)} (panning: {enable_panning})")

        try:
            # 이미지 로드 + EXIF 적용 + 고품질 리사이즈
            with Image.open(image_path) as img:
                # ✅ EXIF orientation 적용 (아이폰/HEIC 사진 회전 문제 해결)
                img = ImageOps.exif_transpose(img) or img
                orig_width, orig_height = img.size
                logger.info(f"📐 원본 이미지: {orig_width}x{orig_height}")

                # 작업 영역: 전체 화면 504x890
                work_width = self.video_width
                work_height = self.video_height
                work_aspect_ratio = work_width / work_height
                image_aspect_ratio = orig_width / orig_height

                logger.info(f"🎯 목표: 전체 화면 {work_width}x{work_height}")
                logger.info(f"📊 이미지 종횡비: {image_aspect_ratio:.3f}")

                # ============================================
                # 1단계: 리사이징 (패닝 옵션에 따라 분기)
                # ============================================
                logger.info(f"\n{'='*50}")
                logger.info(f"📐 1단계: 리사이징 시작 (패닝: {enable_panning})")
                logger.info(f"{'='*50}")

                if enable_panning:
                    # 패닝 활성화: 기존 3가지 타입 분류 로직
                    if image_aspect_ratio > 0.590:
                        # 가로형: 높이 890px 고정
                        resized_height = work_height
                        resized_width = int(orig_width * resized_height / orig_height)

                        logger.info(f"🔳 가로형 이미지 (aspect > 0.590)")
                        logger.info(f"   원본: {orig_width}x{orig_height} → resizedImage: {resized_width}x{resized_height}")

                        # PIL 리사이즈
                        try:
                            resized_img = img.resize((resized_width, resized_height), Image.Resampling.LANCZOS)
                        except AttributeError:
                            resized_img = img.resize((resized_width, resized_height), Image.LANCZOS)

                    elif image_aspect_ratio >= 0.540:
                        # 특수비율: 2단계 리사이징 (1100px → 890px 크롭)
                        logger.info(f"⭐ 특수비율 이미지 (0.540 ≤ aspect ≤ 0.590)")

                        # Step A: 높이 1100px로 리사이즈
                        temp_height = 1100
                        temp_width = int(orig_width * temp_height / orig_height)

                        logger.info(f"   Step A: 원본 {orig_width}x{orig_height} → 임시 {temp_width}x{temp_height}")

                        try:
                            temp_img = img.resize((temp_width, temp_height), Image.Resampling.LANCZOS)
                        except AttributeError:
                            temp_img = img.resize((temp_width, temp_height), Image.LANCZOS)

                        # Step B: 상하 크롭하여 890px로 조정
                        crop_top = (temp_height - work_height) // 2  # (1100-890)/2 = 105
                        crop_bottom = crop_top + work_height         # 105 + 890 = 995

                        logger.info(f"   Step B: 상하 크롭 {crop_top}px → resizedImage: {temp_width}x{work_height}")

                        resized_img = temp_img.crop((0, crop_top, temp_width, crop_bottom))

                        resized_width = temp_width
                        resized_height = work_height

                    else:
                        # 세로형: 폭 504px 고정
                        resized_width = work_width
                        resized_height = int(orig_height * resized_width / orig_width)

                        logger.info(f"🔳 세로형 이미지 (aspect < 0.540)")
                        logger.info(f"   원본: {orig_width}x{orig_height} → resizedImage: {resized_width}x{resized_height}")

                        # PIL 리사이즈
                        try:
                            resized_img = img.resize((resized_width, resized_height), Image.Resampling.LANCZOS)
                        except AttributeError:
                            resized_img = img.resize((resized_width, resized_height), Image.LANCZOS)
                else:
                    # 패닝 비활성화: 가로를 504px에 맞춤 (모든 이미지 동일 처리)
                    resized_width = work_width  # 504px 고정
                    resized_height = int(orig_height * resized_width / orig_width)

                    logger.info(f"{'='*60}")
                    logger.info(f"🔄 [전체화면 - 패닝 OFF] 이미지 가로 기준 리사이즈")
                    logger.info(f"   원본 이미지: {orig_width}x{orig_height}")
                    logger.info(f"   캔버스 폭: {work_width}px (504px 고정)")
                    logger.info(f"   리사이즈 결과: {resized_width}x{resized_height}")
                    logger.info(f"   종횡비: {orig_width/orig_height:.3f} → {resized_width/resized_height:.3f}")
                    logger.info(f"   위아래 검은 패딩: {max(0, work_height - resized_height)}px")
                    logger.info(f"{'='*60}")

                    # PIL 리사이즈
                    try:
                        resized_img = img.resize((resized_width, resized_height), Image.Resampling.LANCZOS)
                    except AttributeError:
                        resized_img = img.resize((resized_width, resized_height), Image.LANCZOS)

                logger.info(f"✅ 1단계 리사이징 완료: LANCZOS 알고리즘 사용")

                # RGBA → RGB 변환
                if resized_img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', resized_img.size, (0, 0, 0))
                    if resized_img.mode == 'P':
                        resized_img = resized_img.convert('RGBA')
                    background.paste(resized_img, mask=resized_img.split()[-1] if resized_img.mode in ('RGBA', 'LA') else None)
                    resized_img = background
                    logger.info(f"🔳 RGBA → RGB 변환 완료")

                # 임시 파일로 저장 (고품질)
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
                resized_img.save(temp_file.name, 'JPEG', quality=95)
                processed_image_path = temp_file.name
                logger.info(f"💾 resizedImage 저장 완료: {processed_image_path}")

            # MoviePy 이미지 클립 생성
            clip = ImageClip(processed_image_path).set_duration(duration)

            # ============================================
            # 2단계: 패닝 (resizedImage 크기 기준) - 🎨 패닝 옵션 체크
            # ============================================
            print(f"\n{'='*50}")
            logger.info(f"🎬 2단계: 패닝 {'활성화' if enable_panning else '비활성화'}")
            logger.info(f"{'='*50}")

            if enable_panning:
                # 패닝 활성화: resizedImage 크기 기준으로 패닝 타입 먼저 결정
                if resized_width > work_width:
                    # 가로 패닝 확정
                    available_margin = (resized_width - work_width) // 2
                    safe_pan_range = min(self.panning_range, available_margin)

                    # 가로 패닝 방향만 랜덤 선택
                    pattern = random.choice([1, 2])

                    if pattern == 1:
                        # 좌→우 패닝: 이미지를 왼쪽으로 이동 (왼쪽 부분 → 오른쪽 부분 보여주기)
                        start_x = 0
                        end_x = -safe_pan_range
                        logger.info(f"🎬 가로 패닝 - 패턴 {pattern}: 좌→우 ({start_x} → {end_x})")
                    else:  # pattern == 2
                        # 우→좌 패닝: 이미지를 오른쪽으로 이동 (오른쪽 부분 → 왼쪽 부분 보여주기)
                        start_x = -(resized_width - work_width)
                        end_x = start_x + safe_pan_range
                        logger.info(f"🎬 가로 패닝 - 패턴 {pattern}: 우→좌 ({start_x} → {end_x})")

                    start_y = (work_height - resized_height) // 2
                    end_y = start_y

                elif resized_height > work_height:
                    # 세로 패닝 확정
                    available_margin = (resized_height - work_height) // 2
                    safe_pan_range = min(self.panning_range, available_margin)

                    # 세로 패닝 방향만 랜덤 선택
                    pattern = random.choice([1, 2])

                    if pattern == 1:
                        # 상→하 패닝: 이미지를 위쪽으로 이동 (위쪽 부분 → 아래쪽 부분 보여주기)
                        start_y = 0
                        end_y = -safe_pan_range
                        logger.info(f"🎬 세로 패닝 - 패턴 {pattern}: 상→하 ({start_y} → {end_y})")
                    else:  # pattern == 2
                        # 하→상 패닝: 이미지를 아래쪽으로 이동 (아래쪽 부분 → 위쪽 부분 보여주기)
                        start_y = -(resized_height - work_height)
                        end_y = start_y + safe_pan_range
                        logger.info(f"🎬 세로 패닝 - 패턴 {pattern}: 하→상 ({start_y} → {end_y})")

                    start_x = (work_width - resized_width) // 2
                    end_x = start_x

                else:
                    # 고정: 중앙 배치 (정사각형 또는 캔버스와 동일)
                    start_x = (work_width - resized_width) // 2
                    start_y = (work_height - resized_height) // 2
                    end_x = start_x
                    end_y = start_y

                    logger.info(f"📐 고정 모드 (resizedImage와 캔버스 크기 동일)")
                    logger.info(f"   중앙 배치: ({start_x}, {start_y})")

                # Linear 이징으로 패닝 적용
                def pos_func(t):
                    progress = t / duration if duration > 0 else 0
                    x = start_x + (end_x - start_x) * progress
                    y = start_y + (end_y - start_y) * progress
                    return (x, y)

                clip = clip.set_position(pos_func)

                logger.info(f"✅ 2단계 패닝 완료: Linear 이징 적용")
                logger.info(f"   시작 좌표: ({start_x}, {start_y}) → 종료 좌표: ({end_x}, {end_y})")
            else:
                # 패닝 비활성화: 위로 붙이기 (아래 검은 패딩)
                x_pos = 0  # 가로는 꽉 채움 (width=504)
                y_pos = 0  # 위로 붙임
                clip = clip.set_position((x_pos, y_pos))
                logger.info(f"🎨 패닝 비활성화: 위로 붙임 ({x_pos}, {y_pos})")
                logger.info(f"   이미지 크기: {resized_width}x{resized_height}")
                logger.info(f"   아래 검은 패딩: {max(0, work_height - resized_height)}px")

            logger.info(f"{'='*50}\n")
            logger.info(f"✅ 전체 화면 이미지 클립 생성 완료!")

            return clip

        except Exception as e:
            logger.error(f"❌ 전체 화면 이미지 클립 생성 실패: {e}")
            # 폴백: 검은 배경
            return ColorClip(size=(self.video_width, self.video_height),
                           color=(0,0,0), duration=duration)

    def create_fullscreen_video_clip(self, video_path, duration, enable_panning=True):
        """전체 화면(504x890)용 비디오 배경 클립 생성

        Args:
            video_path: 비디오 파일 경로
            duration: 클립 지속 시간
            enable_panning: 패닝 활성화 여부 (기본값: True)
        """
        print(f"🎬 전체 화면 비디오 클립 생성: {os.path.basename(video_path)} (panning: {enable_panning})")

        # ★ 비디오 회전 메타데이터 감지 및 정규화 (iPhone .mov 등)
        normalized_path, is_temp_file = self.normalize_video_rotation(video_path)

        try:
            # 비디오 클립 로드 (정규화된 파일 사용)
            video_clip = VideoFileClip(normalized_path)
            orig_width, orig_height = video_clip.size
            print(f"📐 비디오 크기: {orig_width}x{orig_height} (정규화: {'예' if is_temp_file else '아니오'})")

            # 진단 로그: 첫 프레임의 실제 numpy shape 확인
            try:
                first_frame = video_clip.get_frame(0)
                print(f"🔍 진단: first_frame.shape = {first_frame.shape} (h={first_frame.shape[0]}, w={first_frame.shape[1]})")
            except Exception as e:
                print(f"⚠️ 진단 프레임 추출 실패: {e}")

            # 전체 화면에 맞춰 리사이즈 (종횡비 유지하면서 화면 꽉 채움)
            work_width = self.video_width
            work_height = self.video_height
            work_aspect_ratio = work_width / work_height
            video_aspect_ratio = orig_width / orig_height

            print(f"🎯 목표: 전체 화면 {work_width}x{work_height}")

            # 화면비에 따른 크롭 및 리사이즈
            if video_aspect_ratio > work_aspect_ratio:
                # 가로형 비디오: 높이 맞춤 후 양옆 크롭
                new_height = work_height
                new_width = int(orig_width * new_height / orig_height)
                print(f"📐 가로형 비디오: 높이 기준 리사이즈 {new_width}x{new_height}")

                try:
                    # MoviePy resize with newer API - newsize로 명시적 크기 지정 (회전 보정 대응)
                    from moviepy.video.fx.all import resize as fx_resize
                    video_clip = video_clip.fx(fx_resize, newsize=(new_width, new_height))
                except:
                    # Fallback to direct resize
                    try:
                        video_clip = video_clip.resize(newsize=(new_width, new_height))
                    except AttributeError as e:
                        # PIL ANTIALIAS 이슈 - 프레임 추출 후 수동 리사이즈
                        print(f"⚠️ MoviePy resize 실패 (PIL 호환성): {e}")
                        print(f"🔄 프레임 추출 방식으로 전환")

                        # 프레임 추출 (원본 비디오 길이 사용, 파라미터 duration 보존)
                        fps = 30
                        video_duration = video_clip.duration  # 지역 변수 사용
                        frames = []

                        for t in [i/fps for i in range(int(video_duration * fps))]:
                            if t <= video_duration:
                                frame = video_clip.get_frame(t)
                                pil_frame = Image.fromarray(frame)

                                # PIL로 리사이즈
                                try:
                                    resized_frame = pil_frame.resize((new_width, new_height), Image.Resampling.LANCZOS)
                                except AttributeError:
                                    resized_frame = pil_frame.resize((new_width, new_height), Image.LANCZOS)

                                frames.append(np.array(resized_frame))

                        # 새 비디오 클립 생성
                        from moviepy.editor import ImageSequenceClip
                        video_clip = ImageSequenceClip(frames, fps=fps)

                # 중앙 크롭
                crop_x = (new_width - work_width) // 2
                video_clip = video_clip.crop(x1=crop_x, x2=crop_x + work_width)
            else:
                # 세로형 비디오: 폭 맞춤 후 상하 크롭
                new_width = work_width
                new_height = int(orig_height * new_width / orig_width)
                print(f"📐 세로형 비디오: 폭 기준 리사이즈 {new_width}x{new_height}")

                try:
                    # MoviePy resize with newer API - newsize로 명시적 크기 지정 (회전 보정 대응)
                    from moviepy.video.fx.all import resize as fx_resize
                    video_clip = video_clip.fx(fx_resize, newsize=(new_width, new_height))
                except:
                    # Fallback to direct resize
                    try:
                        video_clip = video_clip.resize(newsize=(new_width, new_height))
                    except AttributeError as e:
                        # PIL ANTIALIAS 이슈 - 프레임 추출 후 수동 리사이즈
                        print(f"⚠️ MoviePy resize 실패 (PIL 호환성): {e}")
                        print(f"🔄 프레임 추출 방식으로 전환")

                        # 프레임 추출 (원본 비디오 길이 사용, 파라미터 duration 보존)
                        fps = 30
                        video_duration = video_clip.duration  # 지역 변수 사용
                        frames = []

                        for t in [i/fps for i in range(int(video_duration * fps))]:
                            if t <= video_duration:
                                frame = video_clip.get_frame(t)
                                pil_frame = Image.fromarray(frame)

                                # PIL로 리사이즈
                                try:
                                    resized_frame = pil_frame.resize((new_width, new_height), Image.Resampling.LANCZOS)
                                except AttributeError:
                                    resized_frame = pil_frame.resize((new_width, new_height), Image.LANCZOS)

                                frames.append(np.array(resized_frame))

                        # 새 비디오 클립 생성
                        from moviepy.editor import ImageSequenceClip
                        video_clip = ImageSequenceClip(frames, fps=fps)

                # 중앙 크롭
                crop_y = (new_height - work_height) // 2
                video_clip = video_clip.crop(y1=crop_y, y2=crop_y + work_height)

            # 길이 조정
            original_duration = video_clip.duration
            print(f"📏 비디오 원본 길이: {original_duration:.2f}초, 목표 길이: {duration:.2f}초")

            if original_duration > duration:
                # 비디오가 긴 경우: 안전하게 자르기
                safe_duration = min(duration, original_duration - 0.2)
                video_clip = video_clip.subclip(0, safe_duration)
                print(f"⏂ 비디오 길이 조정: {safe_duration:.2f}초로 잘라냄")
            elif original_duration < duration:
                # 비디오가 짧은 경우: 반복 재생으로 길이 맞춤
                try:
                    loop_count = int(duration // original_duration) + 1
                    print(f"🔁 전체화면 비디오 반복 처리: {loop_count}회 반복하여 {duration}초 달성")

                    # 개별 클립들을 생성해서 연결하는 방식
                    clips = []
                    current_time = 0

                    while current_time < duration:
                        remaining_time = duration - current_time
                        if remaining_time >= original_duration:
                            # 전체 클립 추가
                            clips.append(video_clip)
                            current_time += original_duration
                        else:
                            # 부분 클립 추가 (안전하게)
                            safe_remaining = min(remaining_time, original_duration - 0.2)
                            if safe_remaining > 0.2:  # 최소 0.2초는 있어야 함
                                print(f"📏 부분 클립 생성: 0초 ~ {safe_remaining:.2f}초")
                                clips.append(video_clip.subclip(0, safe_remaining))
                            current_time = duration  # 루프 종료

                    if clips:
                        from moviepy.editor import concatenate_videoclips
                        video_clip = concatenate_videoclips(clips)
                        print(f"✅ 전체화면 비디오 반복 완성: 최종 길이 {video_clip.duration:.2f}초")

                except Exception as e:
                    print(f"⚠️ 전체화면 비디오 반복 처리 실패: {e}")
                    # 실패 시 마지막 프레임으로 연장 (기존 로직 유지)
                    print("📸 대안: 마지막 프레임으로 연장 처리")
                    safe_frame_time = max(0, min(original_duration - 0.3, original_duration * 0.9))
                    last_frame = video_clip.to_ImageClip(t=safe_frame_time)
                    extension_duration = duration - original_duration
                    extension_clip = last_frame.set_duration(extension_duration)
                    from moviepy.editor import concatenate_videoclips
                    video_clip = concatenate_videoclips([video_clip, extension_clip])
                    print(f"🖼️ 마지막 프레임 연장: {extension_duration:.2f}초 추가")

            # 위치 설정 (화면 가득)
            video_clip = video_clip.set_position((0, 0))

            print(f"✅ 전체 화면 비디오 클립 생성 완료!")

            return video_clip

        except Exception as e:
            print(f"❌ 전체 화면 비디오 클립 생성 실패: {e}")
            # 폴백: 검은 배경
            return ColorClip(size=(self.video_width, self.video_height),
                           color=(0,0,0), duration=duration)

        finally:
            # 회전 정규화 임시 파일 정리
            if is_temp_file and os.path.exists(normalized_path):
                try:
                    os.remove(normalized_path)
                    print(f"🗑️ 회전 임시 파일 정리: {os.path.basename(normalized_path)}")
                except Exception:
                    pass

    # ==================== 전환 효과 메소드들 ====================


    def apply_random_transitions(self, clips, transition_duration=0.4):
        """클립들 사이에 랜덤 전환 효과 적용"""
        if len(clips) <= 1:
            return concatenate_videoclips(clips, method="compose") if clips else None

        # 원래 총 길이 계산 (TTS와 맞춰야 할 기준)
        original_total_duration = sum(clip.duration for clip in clips)
        print(f"🎬 랜덤 전환 효과 적용: {len(clips)}개 클립, 원본 총 길이 {original_total_duration:.2f}초")

        # 디졸브 전환 효과만 사용 (테스트용)
        print("🎬 디졸브 전환 효과 테스트: 모든 전환을 디졸브로 고정")

        # 모든 클립들을 처리할 리스트
        processed_clips = []

        for i in range(len(clips)):
            if i == 0:
                # 첫 번째 클립은 그대로 추가
                processed_clips.append(clips[i])
                print(f"  📹 클립 {i+1}: 첫 번째 클립 (전환 없음)")
            else:
                # 디졸브 전환 적용
                print(f"  🔄 클립 {i+1}: 디졸브 전환 적용")

                try:
                    # 이전 클립과 현재 클립 사이에 디졸브 적용
                    prev_clip = processed_clips[-1]
                    curr_clip = clips[i]

                    # 안전한 전환 시간 계산 (0.5초)
                    transition_duration = 0.5
                    safe_duration = min(transition_duration, prev_clip.duration * 0.3, curr_clip.duration * 0.3)
                    safe_duration = max(0.2, safe_duration)  # 최소 0.2초

                    # 현재 클립을 이전 클립 끝에서 겹치도록 시작 시간 설정
                    curr_clip_overlapped = curr_clip.set_start(prev_clip.duration - safe_duration)

                    # fadein 효과 적용 (디졸브)
                    from moviepy.video.fx.fadein import fadein
                    curr_clip_faded = curr_clip_overlapped.fx(fadein, safe_duration)
                    processed_clips.append(curr_clip_faded)

                    print(f"    ✨ 디졸브 적용: {safe_duration:.2f}초 블렌딩")

                except Exception as e:
                    print(f"    ⚠️ 디졸브 실패, cut으로 대체: {e}")
                    processed_clips.append(clips[i])

        # CompositeVideoClip으로 처리 (겹치는 클립들 때문에)
        try:
            final_video = CompositeVideoClip(processed_clips)
            print(f"✅ 디졸브 전환 적용 완료: 최종 길이 {final_video.duration:.2f}초")
        except Exception as e:
            print(f"⚠️ Composite 실패, concatenate로 대체: {e}")
            final_video = concatenate_videoclips([clip for clip in processed_clips if hasattr(clip, 'duration')], method="compose")
            print(f"✅ 디졸브 전환 적용 완료 (Fallback): 최종 길이 {final_video.duration:.2f}초")

        return final_video

        # 기존 전환 효과 코드 (일시적으로 비활성화)
        """
        transitions = ['cut', 'dissolve', 'wipe']

        # 모든 클립들을 처리할 리스트
        processed_clips = []

        for i in range(len(clips)):
            if i == 0:
                # 첫 번째 클립은 그대로 추가
                processed_clips.append(clips[i])
            else:
                # 이전 클립과 현재 클립 사이에 전환 효과 적용
                transition_type = random.choice(transitions)
                print(f"  🔄 클립 {i}: {transition_type} 전환")

                if transition_type == 'cut':
                    # 단순 연결 (기존 방식)
                    processed_clips.append(clips[i])

                elif transition_type == 'dissolve':
                    # 크로스 디졸브 - 더 간단한 방식
                    try:
                        # 이전 클립의 끝 부분과 현재 클립의 시작 부분을 오버랩
                        prev_clip = processed_clips[-1]
                        curr_clip = clips[i]

                        # 안전한 전환 시간 계산
                        safe_duration = min(transition_duration, prev_clip.duration * 0.2, curr_clip.duration * 0.2)
                        safe_duration = max(0.1, safe_duration)

                        # 현재 클립을 이전 클립 끝에서 겹치도록 시작 시간 설정
                        curr_clip_overlapped = curr_clip.set_start(prev_clip.duration - safe_duration)

                        # fadein 효과 적용
                        curr_clip_faded = curr_clip_overlapped.fx(fadein, safe_duration)
                        processed_clips.append(curr_clip_faded)

                        print(f"    ✨ Cross dissolve: {safe_duration:.2f}초 블렌딩")

                    except Exception as e:
                        print(f"    ⚠️ Dissolve 실패, cut으로 대체: {e}")
                        processed_clips.append(clips[i])

                elif transition_type == 'wipe':
                    # 와이프 전환
                    try:
                        processed_clip = self._apply_wipe_transition(
                            processed_clips[-1], clips[i], transition_duration * 0.7
                        )
                        # 전체 composite를 리스트의 마지막 요소로 교체
                        processed_clips[-1] = processed_clip
                    except Exception as e:
                        print(f"    ⚠️ Wipe 실패, cut으로 대체: {e}")
                        processed_clips.append(clips[i])

        # dissolve나 wipe에 의해 겹친 클립들은 CompositeVideoClip으로 처리하고
        # 나머지는 concatenate로 처리
        try:
            final_video = CompositeVideoClip(processed_clips)
            print(f"✅ 랜덤 전환 적용 완료 (Composite): 최종 길이 {final_video.duration:.2f}초")
        except:
            # 실패 시 기본 concatenate 사용
            final_video = concatenate_videoclips([clip for clip in processed_clips if hasattr(clip, 'duration')], method="compose")
            print(f"✅ 랜덤 전환 적용 완료 (Fallback): 최종 길이 {final_video.duration:.2f}초")

        return final_video
        """

    def _apply_cross_dissolve(self, clip1, clip2, duration=0.4):
        """크로스 디졸브 효과 적용 (진짜 크로스 디졸브 - 검은 화면 없음)"""
        try:
            # 안전한 duration 계산
            safe_duration = min(duration, clip1.duration * 0.3, clip2.duration * 0.3)
            safe_duration = max(0.1, safe_duration)  # 최소 0.1초

            # clip1을 그대로 유지
            clip1_part = clip1

            # clip2를 clip1 끝에서 safe_duration만큼 앞당겨 시작
            # clip2의 시작 부분에 transparency 애니메이션 적용
            def make_mask(t):
                # 0초에서 safe_duration까지 opacity가 0에서 1로 변화
                if t < safe_duration:
                    opacity = t / safe_duration  # 0 → 1
                    return opacity
                else:
                    return 1.0

            # clip2를 투명도 애니메이션과 함께 오버랩
            clip2_with_alpha = clip2.set_start(clip1.duration - safe_duration)

            # 간단한 linear fade-in 적용 (검은색 페이드가 아닌 투명도 변화)
            try:
                # MoviePy의 crossfadein 사용 시도
                clip2_crossfade = clip2_with_alpha.fx(fadein, safe_duration)
                print(f"    ✨ Cross dissolve: {safe_duration:.2f}초 블렌딩")
                return clip1_part, clip2_crossfade
            except:
                # 실패 시 간단한 composite 적용
                print(f"    ✨ Cross dissolve (simple): {safe_duration:.2f}초 블렌딩")
                return clip1_part, clip2_with_alpha

        except Exception as e:
            print(f"    ⚠️ Cross dissolve 실패, cut으로 대체: {e}")
            return clip1, clip2

    def _apply_wipe_transition(self, clip1, clip2, duration=0.3):
        """와이프 전환 효과 적용 (4방향 랜덤)"""
        try:
            wipe_directions = ['left_to_right', 'right_to_left', 'top_to_bottom', 'bottom_to_top']
            direction = random.choice(wipe_directions)

            # 안전한 duration 계산
            safe_duration = min(duration, clip1.duration * 0.2)
            safe_duration = max(0.1, safe_duration)

            print(f"    🌊 Wipe {direction}: {safe_duration:.2f}초")

            # 와이프 마스크 생성
            mask_clip = self._create_wipe_mask(direction, safe_duration)

            # clip1의 마지막 부분과 clip2의 시작 부분을 오버랩
            clip1_end = clip1.duration

            # clip2를 clip1 끝에서 시작하되, 와이프 duration만큼 앞당김
            clip2_with_wipe = clip2.set_start(clip1_end - safe_duration)
            clip2_with_mask = clip2_with_wipe.set_mask(mask_clip.set_start(clip1_end - safe_duration))

            # 두 클립을 합성
            composite = CompositeVideoClip([clip1, clip2_with_mask])

            return composite

        except Exception as e:
            print(f"    ⚠️ Wipe 전환 실패, cut으로 대체: {e}")
            # 실패 시 단순 연결
            return concatenate_videoclips([clip1, clip2], method="compose")

    def _create_wipe_mask(self, direction, duration):
        """와이프 전환용 마스크 클립 생성"""
        def make_frame(t):
            # 진행 비율 (0 → 1)
            progress = t / duration

            # 마스크 배열 생성 (0=투명, 255=불투명)
            mask = np.zeros((self.video_height, self.video_width))

            if direction == 'left_to_right':
                # 좌에서 우로
                cutoff = int(self.video_width * progress)
                mask[:, :cutoff] = 255

            elif direction == 'right_to_left':
                # 우에서 좌로
                cutoff = int(self.video_width * (1 - progress))
                mask[:, cutoff:] = 255

            elif direction == 'top_to_bottom':
                # 상에서 하로
                cutoff = int(self.video_height * progress)
                mask[:cutoff, :] = 255

            elif direction == 'bottom_to_top':
                # 하에서 상으로
                cutoff = int(self.video_height * (1 - progress))
                mask[cutoff:, :] = 255

            return mask

        # numpy import가 필요할 수 있음
        try:
            import numpy as np
        except ImportError:
            print("    ⚠️ numpy 없음, 간단한 마스크 사용")
            # numpy 없을 경우 간단한 페이드 마스크
            return ColorClip(size=(self.video_width, self.video_height),
                           color=(255, 255, 255)).set_duration(duration).fx(fadein, duration)

        mask_clip = VideoClip(make_frame, duration=duration)
        return mask_clip

    def detect_image_transitions(self, clips, media_files, image_allocation_mode):
        """클립과 미디어 파일을 매핑하여 모든 전환 구간의 인덱스를 반환 (영상-영상, 이미지-이미지, 영상-이미지, 이미지-영상)"""
        msg = f"🔍 미디어 전환 구간 감지 시작..."
        print(msg)
        logging.info(msg)

        msg = f"   clips 개수: {len(clips) if clips else 0}"
        print(msg)
        logging.info(msg)

        msg = f"   media_files 개수: {len(media_files) if media_files else 0}"
        print(msg)
        logging.info(msg)

        msg = f"   image_allocation_mode: {image_allocation_mode}"
        print(msg)
        logging.info(msg)

        if not media_files or not clips:
            msg = "   ⚠️ media_files 또는 clips가 없습니다"
            print(msg)
            logging.warning(msg)
            return []

        # 클립과 미디어 파일 매핑 생성
        clip_to_media_mapping = self._create_clip_media_mapping(clips, media_files, image_allocation_mode)

        msg = f"   클립-미디어 매핑: {clip_to_media_mapping}"
        print(msg)
        logging.info(msg)

        transition_indices = []
        for i in range(len(clips) - 1):
            try:
                curr_media_idx = clip_to_media_mapping.get(i)
                next_media_idx = clip_to_media_mapping.get(i+1)

                if curr_media_idx is None or next_media_idx is None:
                    msg = f"   [{i}] 매핑 없음: {curr_media_idx} → {next_media_idx}"
                    print(msg)
                    logging.info(msg)
                    continue

                curr_media = media_files[curr_media_idx]
                next_media = media_files[next_media_idx]

                curr_type = curr_media[1] if len(curr_media) > 1 else "unknown"
                next_type = next_media[1] if len(next_media) > 1 else "unknown"

                msg = f"   클립 [{i}] → [{i+1}]: 미디어 [{curr_media_idx}] ({curr_type}) → [{next_media_idx}] ({next_type})"
                print(msg)
                logging.info(msg)

                # 모든 타입의 전환에 dissolve 적용 (영상-영상, 이미지-이미지, 영상-이미지, 이미지-영상)
                transition_indices.append(i)
                msg = f"  ✅ 전환 구간 발견: 클립 {i} → {i+1} ({curr_type}→{next_type})"
                print(msg)
                logging.info(msg)

            except Exception as e:
                msg = f"   ⚠️ 클립 [{i}] 처리 중 오류: {e}"
                print(msg)
                logging.error(msg)
                continue

        msg = f"🎭 총 {len(transition_indices)}개 크로스 디졸브 구간 감지 (모든 미디어 전환): {transition_indices}"
        print(msg)
        logging.info(msg)
        return transition_indices

    def _create_clip_media_mapping(self, clips, media_files, image_allocation_mode):
        """클립과 미디어 파일 간의 매핑 생성"""
        mapping = {}

        if image_allocation_mode == "1_per_image":
            # 각 클립마다 미디어 1개
            for i, clip in enumerate(clips):
                media_idx = i % len(media_files)  # 미디어 파일 순환 사용
                mapping[i] = media_idx
        elif image_allocation_mode == "2_per_image":
            # 클립 2개당 미디어 1개
            for i, clip in enumerate(clips):
                media_idx = (i // 2) % len(media_files)  # 2개씩 묶어서 미디어 사용
                mapping[i] = media_idx
        else:
            # 기본: 1:1 매핑
            for i, clip in enumerate(clips):
                if i < len(media_files):
                    mapping[i] = i

        return mapping


    def apply_crossfade_to_clips(self, clips, transition_indices, fade_duration=0.4):
        """지정된 전환 구간의 클립들에 fade 효과 적용"""
        msg = "🎨 apply_crossfade_to_clips 호출됨!"
        print(msg)
        logging.info(msg)

        msg = f"   전환 구간: {transition_indices}"
        print(msg)
        logging.info(msg)

        msg = f"   페이드 시간: {fade_duration}초"
        print(msg)
        logging.info(msg)

        try:
            # MoviePy fade 모듈 import 시도 (최신 버전 호환)
            from moviepy.video.fx.fadein import fadein
            from moviepy.video.fx.fadeout import fadeout
            msg = "✅ MoviePy fade 모듈 import 성공"
            print(msg)
            logging.info(msg)
        except ImportError as e:
            msg = f"❌ MoviePy fade 모듈 import 실패: {e}"
            print(msg)
            logging.error(msg)
            return clips

        processed_clips = []

        for i, clip in enumerate(clips):
            try:
                clip_copy = clip.copy()

                # 크로스 디졸브 로직:
                # transition_indices에 있는 인덱스는 "전환이 시작되는 클립"을 의미
                # 즉, 클립 i에서 클립 i+1로 전환

                # 현재 클립에서 다음 클립으로의 전환 (fadeout)
                if i in transition_indices:
                    if clip_copy.duration >= fade_duration:
                        clip_copy = clip_copy.fx(fadeout, fade_duration)
                        msg = f"✨ 클립 {i}→{i+1}: 2초 크로스 디졸브 적용 완료 (fadeout)"
                        print(msg)
                        logging.info(msg)
                    else:
                        msg = f"⚠️ 클립 {i}: 길이({clip_copy.duration:.1f}초)가 페이드 시간보다 짧아 fadeout 생략"
                        print(msg)
                        logging.warning(msg)

                # 이전 클립에서 현재 클립으로의 전환 (fadein)
                # i-1이 transition_indices에 있으면 현재 클립에 fadein 적용
                if i > 0 and (i-1) in transition_indices:
                    clip_copy = clip_copy.fx(fadein, fade_duration)
                    msg = f"✨ 클립 {i-1}→{i}: 2초 크로스 디졸브 적용 완료 (fadein)"
                    print(msg)
                    logging.info(msg)

                processed_clips.append(clip_copy)
                msg = f"✅ 클립 {i} 처리 완료"
                print(msg)
                logging.info(msg)

            except Exception as e:
                msg = f"⚠️ 클립 {i} 처리 실패: {e}"
                print(msg)
                logging.error(msg)
                # 실패 시 원본 클립 사용
                processed_clips.append(clip)

        msg = f"🎨 크로스페이드 효과 적용 완료: {len(processed_clips)}개 클립"
        print(msg)
        logging.info(msg)

        return processed_clips

    def apply_smart_crossfade_transitions(self, clips, media_files=None, image_allocation_mode="1_per_image", fade_duration=0.4):
        """기존 구조를 유지하면서 스마트 크로스 디졸브 적용"""
        msg = f"🎬 apply_smart_crossfade_transitions 호출됨!"
        print(msg)
        logging.info(msg)

        msg = f"   clips 개수: {len(clips) if clips else 0}"
        print(msg)
        logging.info(msg)

        msg = f"   media_files 타입: {type(media_files)}"
        print(msg)
        logging.info(msg)

        msg = f"   media_files 개수: {len(media_files) if media_files else 0}"
        print(msg)
        logging.info(msg)

        msg = f"   image_allocation_mode: {image_allocation_mode}"
        print(msg)
        logging.info(msg)

        msg = f"   fade_duration: {fade_duration}"
        print(msg)
        logging.info(msg)

        if not clips or len(clips) <= 1:
            msg = "   ⚠️ 클립이 없거나 1개 이하입니다. 기본 연결 사용"
            print(msg)
            logging.warning(msg)
            return concatenate_videoclips(clips, method="compose") if clips else None

        msg = f"🎬 스마트 크로스 디졸브 전환 시작: {len(clips)}개 클립 (강화된 2초 효과)"
        print(msg)
        logging.info(msg)

        # 모든 미디어 전환 구간 감지 (영상-영상, 이미지-이미지, 영상-이미지, 이미지-영상)
        msg = "🔍 미디어 전환 구간 감지 호출..."
        print(msg)
        logging.info(msg)

        transition_indices = self.detect_image_transitions(clips, media_files, image_allocation_mode)

        msg = f"🔍 감지 결과: {transition_indices}"
        print(msg)
        logging.info(msg)

        if not transition_indices:
            msg = "ℹ️ 전환 구간이 없어 일반 연결 사용"
            print(msg)
            logging.info(msg)

            msg = "   -> concatenate_videoclips로 기본 연결합니다"
            print(msg)
            logging.info(msg)
            return concatenate_videoclips(clips, method="compose")

        # 개별 클립에 fade 효과 적용
        print("🔄 개별 클립에 fade 효과 적용 호출...")
        processed_clips = self.apply_crossfade_to_clips(clips, transition_indices, fade_duration)
        print(f"🔄 fade 효과 적용 완료. 처리된 클립 개수: {len(processed_clips)}")

        # 기존 방식으로 순차 연결 (CompositeVideoClip 사용 안함)
        try:
            print("🔗 최종 영상 연결 시작...")
            print(f"   연결할 클립 개수: {len(processed_clips)}")

            # 각 클립의 상태 확인
            for i, clip in enumerate(processed_clips):
                try:
                    print(f"   클립 [{i}]: 길이 {clip.duration:.2f}초, 크기 {clip.size}")
                except Exception as e:
                    print(f"   클립 [{i}]: 정보 확인 실패 - {e}")

            final_video = concatenate_videoclips(processed_clips, method="compose")
            print(f"✅ 크로스 디졸브 전환 완료: 최종 길이 {final_video.duration:.2f}초")
            return final_video
        except Exception as e:
            print(f"⚠️ 전환 효과 적용 실패: {e}")
            import traceback
            traceback.print_exc()
            print("   -> 원본 클립들로 기본 연결을 시도합니다...")
            # 실패 시 원본 클립들로 기본 연결
            try:
                fallback_video = concatenate_videoclips(clips, method="compose")
                print(f"✅ 기본 연결 성공: 길이 {fallback_video.duration:.2f}초")
                return fallback_video
            except Exception as e2:
                print(f"⚠️ 기본 연결도 실패: {e2}")
                return None


