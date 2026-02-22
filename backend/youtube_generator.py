"""
YouTube (16:9) 전용 영상 생성기

릴스/쇼츠 생성 로직(video_generator.py)에 영향 없이
YouTube 16:9 포맷을 독립적으로 처리합니다.

주요 특징:
- 캔버스: 1280x720 (16:9)
- 타이틀 영역 없음 (전체 화면을 미디어로 사용)
- letterbox fit: 이미지/비디오 비율 유지 + 검은 여백으로 채움
- 패닝(Ken Burns) 완전 비활성화
"""

import os
import tempfile
from PIL import Image, ImageOps
from moviepy.editor import ImageClip, ColorClip, CompositeVideoClip, VideoFileClip

from utils.logger_config import get_logger
from video_generator import VideoGenerator

logger = get_logger('youtube_generator')


class YouTubeVideoGenerator(VideoGenerator):
    """YouTube (16:9) 전용 영상 생성기.

    VideoGenerator를 상속하여 TTS, 텍스트 렌더링, 영상 합성 등의
    공통 로직을 재사용하면서, 배경 클립 생성 메서드만 오버라이드합니다.

    릴스/쇼츠를 생성하는 부모 클래스 코드는 수정하지 않습니다.
    """

    CANVAS_W = 1280
    CANVAS_H = 720

    def __init__(self):
        super().__init__()

        # 캔버스 크기 재설정
        self.video_width = self.CANVAS_W
        self.video_height = self.CANVAS_H

        # 타이틀 영역 없음 (YouTube 모드에서는 항상 title_area_mode='remove')
        self.title_height = 0
        self.work_height_keep = self.CANVAS_H
        self.work_height_remove = self.CANVAS_H

        # 텍스트 위치 (1280x720 기준)
        # 상단: 캔버스 높이의 25% (180px)
        # 하단: 캔버스 높이의 75% (540px)
        self.text_y_top = 180
        self.text_y_bottom = 540
        self.text_y_bottom_edge_margin = 60

        # 패닝 없음 (letterbox fit이므로 overflow 공간 없음)
        self.panning_range = 0

        logger.info(
            f"🎬 YouTubeVideoGenerator 초기화 완료: "
            f"{self.video_width}x{self.video_height}, 타이틀 없음, 패닝 없음"
        )

    # ------------------------------------------------------------------
    # letterbox 계산 헬퍼
    # ------------------------------------------------------------------

    def _calc_letterbox(self, orig_w: int, orig_h: int):
        """종횡비를 유지하면서 1280x720 안에 들어오는 크기와 중앙 오프셋을 반환.

        Returns:
            (new_w, new_h, x_offset, y_offset)
        """
        scale = min(self.CANVAS_W / orig_w, self.CANVAS_H / orig_h)
        new_w = int(orig_w * scale)
        new_h = int(orig_h * scale)
        x_off = (self.CANVAS_W - new_w) // 2
        y_off = (self.CANVAS_H - new_h) // 2
        return new_w, new_h, x_off, y_off

    # ------------------------------------------------------------------
    # 이미지 배경 클립 오버라이드 (letterbox, 패닝 없음)
    # ------------------------------------------------------------------

    def create_fullscreen_background_clip(self, image_path, duration, enable_panning=True):
        """YouTube 16:9 letterbox fit 이미지 클립 생성.

        Args:
            image_path: 이미지 파일 경로
            duration: 클립 지속 시간
            enable_panning: 무시됨 - YouTube 모드에서는 항상 패닝 없음
        """
        logger.info(
            f"🖼️ [YouTube] 이미지 letterbox 클립 생성: "
            f"{os.path.basename(image_path)} ({duration:.1f}s, 패닝 무시)"
        )

        try:
            # 이미지 파일 검증 및 포맷 자동변환 (부모 메서드 재사용)
            validated = self._ensure_valid_image(image_path)
            if validated:
                image_path = validated

            with Image.open(image_path) as img:
                # EXIF orientation 보정 (아이폰/HEIC 등 회전 문제 해결)
                img = ImageOps.exif_transpose(img) or img
                orig_w, orig_h = img.size
                logger.info(f"📐 원본: {orig_w}x{orig_h}")

                new_w, new_h, x_off, y_off = self._calc_letterbox(orig_w, orig_h)
                logger.info(f"📐 letterbox 결과: {new_w}x{new_h}, 오프셋=({x_off},{y_off})")

                # LANCZOS 고품질 리사이즈
                try:
                    resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                except AttributeError:
                    resized = img.resize((new_w, new_h), Image.LANCZOS)

                # RGBA/LA/P → RGB 변환
                if resized.mode in ('RGBA', 'LA', 'P'):
                    bg = Image.new('RGB', resized.size, (0, 0, 0))
                    if resized.mode == 'P':
                        resized = resized.convert('RGBA')
                    mask = resized.split()[-1] if resized.mode in ('RGBA', 'LA') else None
                    bg.paste(resized, mask=mask)
                    resized = bg
                elif resized.mode != 'RGB':
                    resized = resized.convert('RGB')

                # 검은 1280x720 캔버스에 중앙 paste
                canvas = Image.new('RGB', (self.CANVAS_W, self.CANVAS_H), (0, 0, 0))
                canvas.paste(resized, (x_off, y_off))

                # 임시 파일 저장 (고품질 JPEG)
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
                canvas.save(tmp.name, 'JPEG', quality=95)
                tmp.close()

            logger.info(f"✅ [YouTube] 이미지 letterbox 완료")

            # MoviePy 클립 (고정 위치, 패닝 없음)
            clip = ImageClip(tmp.name).set_duration(duration).set_position((0, 0))
            return clip

        except Exception as e:
            logger.error(f"❌ [YouTube] 이미지 letterbox 클립 생성 실패: {e}")
            return ColorClip(
                size=(self.CANVAS_W, self.CANVAS_H),
                color=(0, 0, 0),
                duration=duration
            )

    # ------------------------------------------------------------------
    # 비디오 배경 클립 오버라이드 (letterbox, 패닝 없음)
    # ------------------------------------------------------------------

    def create_fullscreen_video_clip(self, video_path, duration, enable_panning=True):
        """YouTube 16:9 letterbox fit 비디오 클립 생성.

        Args:
            video_path: 비디오 파일 경로
            duration: 클립 지속 시간
            enable_panning: 무시됨 - YouTube 모드에서는 항상 패닝 없음
        """
        logger.info(
            f"🎬 [YouTube] 비디오 letterbox 클립 생성: "
            f"{os.path.basename(video_path)} ({duration:.1f}s, 패닝 무시)"
        )

        try:
            # 회전 메타데이터 정규화 (iPhone .mov 등, 부모 메서드 재사용)
            norm_path, is_temp = self.normalize_video_rotation(video_path)

            video_clip = VideoFileClip(norm_path)
            orig_w, orig_h = video_clip.size
            logger.info(f"📐 원본 비디오: {orig_w}x{orig_h}")

            new_w, new_h, x_off, y_off = self._calc_letterbox(orig_w, orig_h)
            logger.info(f"📐 letterbox 결과: {new_w}x{new_h}, 오프셋=({x_off},{y_off})")

            # 비디오 리사이즈
            video_clip = video_clip.resize((new_w, new_h))

            # 길이 조정
            if video_clip.duration > duration:
                # 앞부분만 사용
                video_clip = video_clip.subclip(0, duration)
            elif video_clip.duration < duration:
                # 마지막 프레임 고정으로 부족한 시간 채우기
                last_frame = video_clip.to_ImageClip(t=video_clip.duration - 0.1)
                ext_clip = last_frame.set_duration(duration - video_clip.duration)
                from moviepy.editor import concatenate_videoclips
                video_clip = concatenate_videoclips([video_clip, ext_clip])

            # 검은 배경(1280x720) 위에 letterbox 배치
            black_bg = ColorClip(
                size=(self.CANVAS_W, self.CANVAS_H),
                color=(0, 0, 0),
                duration=duration
            )
            video_clip = video_clip.set_position((x_off, y_off))
            final = CompositeVideoClip(
                [black_bg, video_clip],
                size=(self.CANVAS_W, self.CANVAS_H)
            )

            # 회전 정규화로 생성된 임시 파일 정리
            if is_temp and os.path.exists(norm_path):
                try:
                    os.unlink(norm_path)
                except Exception:
                    pass

            logger.info(f"✅ [YouTube] 비디오 letterbox 완료")
            return final

        except Exception as e:
            logger.error(f"❌ [YouTube] 비디오 letterbox 클립 생성 실패: {e}")
            return ColorClip(
                size=(self.CANVAS_W, self.CANVAS_H),
                color=(0, 0, 0),
                duration=duration
            )
