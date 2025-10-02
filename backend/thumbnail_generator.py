"""
북마크 비디오 썸네일 자동 생성 유틸리티

이 모듈은 assets/videos/bookmark 폴더의 MP4 파일들에 대해
자동으로 썸네일 이미지를 생성합니다.
"""

import os
import glob
from typing import List, Tuple
from PIL import Image
from utils.logger_config import get_logger

# MoviePy import
try:
    from moviepy.editor import VideoFileClip
    MOVIEPY_AVAILABLE = True
except ImportError:
    print("⚠️ MoviePy를 찾을 수 없습니다. pip install moviepy로 설치해주세요.")
    MOVIEPY_AVAILABLE = False

# 로거 설정
logger = get_logger('thumbnail_generator')


class ThumbnailGenerator:
    """비디오 썸네일 생성기"""

    def __init__(self, thumbnail_size: Tuple[int, int] = (200, 200), use_webp: bool = True):
        """
        Args:
            thumbnail_size: 썸네일 크기 (width, height) - 기본값 200x200으로 최적화
            use_webp: WebP 포맷 사용 여부 (기본값 True)
        """
        self.thumbnail_size = thumbnail_size
        self.use_webp = use_webp
        self.generated_count = 0
        self.skipped_count = 0
        self.error_count = 0

    def extract_frame_from_video(self, video_path: str, output_path: str, time_sec: float = 0.5) -> bool:
        """
        비디오에서 특정 시점의 프레임을 추출하여 썸네일로 저장

        Args:
            video_path: 비디오 파일 경로
            output_path: 썸네일 저장 경로
            time_sec: 프레임 추출 시간 (초)

        Returns:
            bool: 성공 여부
        """
        if not MOVIEPY_AVAILABLE:
            logger.error("MoviePy가 설치되지 않아 썸네일을 생성할 수 없습니다.")
            return False

        try:
            # 비디오 파일 로드
            video = VideoFileClip(video_path)

            # 비디오 길이 확인
            duration = video.duration
            if duration < time_sec:
                time_sec = duration / 2  # 중간 지점 사용

            # 프레임 추출
            frame = video.get_frame(time_sec)

            # PIL Image로 변환
            img = Image.fromarray(frame)

            # 정사각형으로 크롭 (중앙 기준)
            width, height = img.size
            if width > height:
                left = (width - height) // 2
                img = img.crop((left, 0, left + height, height))
            else:
                top = (height - width) // 2
                img = img.crop((0, top, width, top + width))

            # 리사이즈
            img = img.resize(self.thumbnail_size, Image.Resampling.LANCZOS)

            # 포맷별 저장 (WebP 우선)
            if self.use_webp:
                # WebP 포맷: 50-70% 용량 감소, 고품질 유지
                img.save(output_path, 'WEBP', quality=80, method=4, optimize=True)
                logger.info(f"✅ WebP 썸네일 생성 성공: {os.path.basename(output_path)} (200x200)")
            else:
                # JPEG 포맷 (하위 호환)
                img.save(output_path, 'JPEG', quality=85, optimize=True)
                logger.info(f"✅ JPEG 썸네일 생성 성공: {os.path.basename(output_path)}")

            # 리소스 정리
            video.close()

            return True

        except Exception as e:
            logger.error(f"❌ 썸네일 생성 실패: {os.path.basename(video_path)} - {e}")
            return False

    def generate_missing_thumbnails(self, bookmark_folder: str) -> dict:
        """
        북마크 폴더의 모든 MP4 파일에 대해 썸네일 생성

        Args:
            bookmark_folder: 북마크 비디오 폴더 경로

        Returns:
            dict: 생성 결과 통계
        """
        if not os.path.exists(bookmark_folder):
            logger.warning(f"⚠️ 북마크 폴더가 존재하지 않습니다: {bookmark_folder}")
            return {
                'generated': 0,
                'skipped': 0,
                'errors': 0,
                'total': 0
            }

        # 초기화
        self.generated_count = 0
        self.skipped_count = 0
        self.error_count = 0

        # 모든 MP4 파일 검색
        video_files = glob.glob(os.path.join(bookmark_folder, "*.mp4"))
        total_videos = len(video_files)

        logger.info(f"🔍 북마크 비디오 스캔: {total_videos}개 발견")

        for video_path in video_files:
            filename = os.path.basename(video_path)

            # WebP 또는 JPEG 썸네일 확장자 결정
            thumbnail_ext = '.webp' if self.use_webp else '.jpg'
            thumbnail_name = filename.replace('.mp4', thumbnail_ext)
            thumbnail_path = os.path.join(bookmark_folder, thumbnail_name)

            # 이미 썸네일이 존재하는지 확인 (WebP 및 JPEG 모두 체크)
            webp_path = os.path.join(bookmark_folder, filename.replace('.mp4', '.webp'))
            jpg_path = os.path.join(bookmark_folder, filename.replace('.mp4', '.jpg'))

            if os.path.exists(webp_path) or os.path.exists(jpg_path):
                logger.debug(f"⏭️ 썸네일 이미 존재: {thumbnail_name}")
                self.skipped_count += 1
                continue

            # 썸네일 생성
            logger.info(f"🎬 썸네일 생성 중: {filename}")
            success = self.extract_frame_from_video(video_path, thumbnail_path)

            if success:
                self.generated_count += 1
            else:
                self.error_count += 1

        # 결과 로깅
        logger.info(f"📊 썸네일 생성 완료:")
        logger.info(f"  - 새로 생성: {self.generated_count}개")
        logger.info(f"  - 이미 존재: {self.skipped_count}개")
        logger.info(f"  - 생성 실패: {self.error_count}개")
        logger.info(f"  - 전체: {total_videos}개")

        return {
            'generated': self.generated_count,
            'skipped': self.skipped_count,
            'errors': self.error_count,
            'total': total_videos
        }

    def generate_thumbnail_for_file(self, video_path: str) -> bool:
        """
        단일 비디오 파일에 대해 썸네일 생성

        Args:
            video_path: 비디오 파일 경로

        Returns:
            bool: 성공 여부
        """
        if not os.path.exists(video_path):
            logger.error(f"❌ 비디오 파일을 찾을 수 없습니다: {video_path}")
            return False

        # WebP 또는 JPEG 썸네일 경로 생성
        thumbnail_ext = '.webp' if self.use_webp else '.jpg'
        thumbnail_path = video_path.replace('.mp4', thumbnail_ext)

        # 이미 존재하면 스킵 (WebP 및 JPEG 모두 체크)
        webp_path = video_path.replace('.mp4', '.webp')
        jpg_path = video_path.replace('.mp4', '.jpg')

        if os.path.exists(webp_path) or os.path.exists(jpg_path):
            logger.info(f"⏭️ 썸네일 이미 존재: {os.path.basename(thumbnail_path)}")
            return True

        # 썸네일 생성
        return self.extract_frame_from_video(video_path, thumbnail_path)


# 전역 썸네일 생성기 인스턴스
thumbnail_generator = ThumbnailGenerator()


def generate_missing_thumbnails(bookmark_folder: str) -> dict:
    """
    편의 함수: 북마크 폴더의 누락된 썸네일 생성

    Args:
        bookmark_folder: 북마크 비디오 폴더 경로

    Returns:
        dict: 생성 결과 통계
    """
    return thumbnail_generator.generate_missing_thumbnails(bookmark_folder)


def generate_thumbnail(video_path: str) -> bool:
    """
    편의 함수: 단일 비디오 파일의 썸네일 생성

    Args:
        video_path: 비디오 파일 경로

    Returns:
        bool: 성공 여부
    """
    return thumbnail_generator.generate_thumbnail_for_file(video_path)


if __name__ == "__main__":
    # 테스트 실행
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    if len(sys.argv) > 1:
        # 명령줄에서 폴더 경로 지정
        bookmark_folder = sys.argv[1]
    else:
        # 기본 폴더
        bookmark_folder = os.path.join("assets", "videos", "bookmark")

    print(f"📁 북마크 폴더: {bookmark_folder}")
    print(f"🎬 썸네일 생성 시작...\n")

    result = generate_missing_thumbnails(bookmark_folder)

    print(f"\n✅ 작업 완료!")
    print(f"   새로 생성: {result['generated']}개")
    print(f"   이미 존재: {result['skipped']}개")
    print(f"   생성 실패: {result['errors']}개")
    print(f"   전체: {result['total']}개")