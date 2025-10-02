#!/usr/bin/env python3
"""
기존 assets/videos 폴더의 모든 영상에 대해 썸네일을 일괄 생성하는 배치 스크립트
"""
import os
import sys
import logging
from datetime import datetime
try:
    from moviepy.editor import VideoFileClip
    from PIL import Image
    MOVIEPY_AVAILABLE = True
except ImportError as e:
    print(f"❌ MoviePy import 오류: {e}")
    print("pip install moviepy pillow 로 라이브러리를 설치해주세요.")
    sys.exit(1)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('thumbnail_batch.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ThumbnailBatchGenerator:
    def __init__(self, videos_dir: str = "assets/videos"):
        self.videos_dir = videos_dir
        self.video_extensions = {'.mp4', '.mov', '.avi', '.webm', '.mkv', '.flv', '.wmv'}

        if not os.path.exists(videos_dir):
            raise FileNotFoundError(f"Videos 디렉토리가 존재하지 않습니다: {videos_dir}")

    def generate_video_thumbnail(self, video_path: str, thumbnail_path: str) -> bool:
        """비디오 파일에서 썸네일 이미지 생성 (WebP 200x200)"""
        try:
            logger.info(f"🎬 썸네일 생성 시작: {os.path.basename(video_path)}")

            with VideoFileClip(video_path) as clip:
                # 동영상 0.5초 지점에서 썸네일 추출
                thumbnail_time = min(0.5, clip.duration - 0.1)

                # 프레임 추출
                frame = clip.get_frame(thumbnail_time)

                # PIL Image로 변환
                image = Image.fromarray(frame)

                # 정사각형으로 크롭 (중앙 기준)
                width, height = image.size
                if width > height:
                    left = (width - height) // 2
                    image = image.crop((left, 0, left + height, height))
                else:
                    top = (height - width) // 2
                    image = image.crop((0, top, width, top + width))

                # 200x200으로 리사이즈 (LANCZOS 고품질)
                image = image.resize((200, 200), Image.Resampling.LANCZOS)

                # WebP 포맷으로 저장 (80% 품질, method=4 최적화)
                image.save(thumbnail_path, 'WEBP', quality=80, method=4, optimize=True)

                logger.info(f"✅ WebP 썸네일 생성 완료: {os.path.basename(thumbnail_path)} (200x200)")
                return True

        except Exception as e:
            logger.error(f"❌ 썸네일 생성 실패 ({os.path.basename(video_path)}): {e}")
            return False

    def scan_video_files(self):
        """비디오 파일들을 스캔하여 목록 반환"""
        video_files = []

        logger.info(f"📁 비디오 폴더 스캔 시작: {self.videos_dir}")

        for filename in os.listdir(self.videos_dir):
            file_path = os.path.join(self.videos_dir, filename)

            if os.path.isfile(file_path):
                _, ext = os.path.splitext(filename.lower())
                if ext in self.video_extensions:
                    video_files.append((filename, file_path))

        logger.info(f"📊 총 {len(video_files)}개의 비디오 파일 발견")
        return video_files

    def check_existing_thumbnails(self, video_files):
        """기존 썸네일이 있는지 확인 (WebP 우선, JPG 폴백)"""
        need_thumbnail = []
        already_exists = []

        for filename, file_path in video_files:
            # 썸네일 파일명 생성
            filename_without_ext = os.path.splitext(filename)[0]
            thumbnail_filename_webp = f"{filename_without_ext}_thumb.webp"
            thumbnail_filename_jpg = f"{filename_without_ext}_thumb.jpg"
            thumbnail_path_webp = os.path.join(self.videos_dir, thumbnail_filename_webp)
            thumbnail_path_jpg = os.path.join(self.videos_dir, thumbnail_filename_jpg)

            # WebP 우선, 없으면 JPG 확인
            if os.path.exists(thumbnail_path_webp):
                already_exists.append((filename, thumbnail_path_webp))
            elif os.path.exists(thumbnail_path_jpg):
                already_exists.append((filename, thumbnail_path_jpg))
            else:
                # 새로운 WebP 썸네일 경로
                need_thumbnail.append((filename, file_path, thumbnail_path_webp))

        logger.info(f"📋 썸네일 현황:")
        logger.info(f"  ✅ 이미 존재: {len(already_exists)}개")
        logger.info(f"  🔄 생성 필요: {len(need_thumbnail)}개")

        return need_thumbnail, already_exists

    def generate_all_thumbnails(self, force_regenerate: bool = False):
        """모든 비디오 파일의 썸네일 생성"""
        start_time = datetime.now()
        logger.info(f"🚀 썸네일 배치 생성 시작: {start_time}")

        # 비디오 파일 스캔
        video_files = self.scan_video_files()
        if not video_files:
            logger.warning("⚠️  비디오 파일이 없습니다.")
            return

        # 기존 썸네일 확인
        if force_regenerate:
            logger.info("🔄 강제 재생성 모드: 모든 썸네일을 WebP로 다시 생성합니다")
            to_process = [(filename, file_path, os.path.join(self.videos_dir, f"{os.path.splitext(filename)[0]}_thumb.webp"))
                         for filename, file_path in video_files]
        else:
            to_process, already_exists = self.check_existing_thumbnails(video_files)

        if not to_process:
            logger.info("🎉 모든 썸네일이 이미 존재합니다!")
            return

        # 썸네일 생성 진행
        success_count = 0
        error_count = 0

        for i, (filename, video_path, thumbnail_path) in enumerate(to_process, 1):
            logger.info(f"📊 진행률: {i}/{len(to_process)} ({i/len(to_process)*100:.1f}%)")

            try:
                if self.generate_video_thumbnail(video_path, thumbnail_path):
                    success_count += 1
                else:
                    error_count += 1
            except KeyboardInterrupt:
                logger.warning("⚠️  사용자에 의해 중단되었습니다")
                break
            except Exception as e:
                logger.error(f"❌ 예상치 못한 오류 ({filename}): {e}")
                error_count += 1

        # 결과 요약
        end_time = datetime.now()
        duration = end_time - start_time

        logger.info("=" * 50)
        logger.info("🎉 썸네일 배치 생성 완료!")
        logger.info(f"⏱️  소요 시간: {duration}")
        logger.info(f"✅ 성공: {success_count}개")
        logger.info(f"❌ 실패: {error_count}개")
        logger.info(f"📊 전체 처리: {success_count + error_count}개")
        logger.info("=" * 50)

def main():
    """메인 실행 함수"""
    import argparse

    parser = argparse.ArgumentParser(description='비디오 썸네일 일괄 생성 도구')
    parser.add_argument('--videos-dir', default='assets/videos',
                       help='비디오 파일들이 있는 디렉토리 (기본값: assets/videos)')
    parser.add_argument('--force', action='store_true',
                       help='기존 썸네일이 있어도 강제로 재생성')
    parser.add_argument('--dry-run', action='store_true',
                       help='실제 생성하지 않고 대상 파일들만 확인')

    args = parser.parse_args()

    try:
        generator = ThumbnailBatchGenerator(args.videos_dir)

        if args.dry_run:
            logger.info("🔍 Dry-run 모드: 대상 파일들만 확인합니다")
            video_files = generator.scan_video_files()
            need_thumbnail, already_exists = generator.check_existing_thumbnails(video_files)

            if need_thumbnail:
                logger.info("🔄 생성이 필요한 파일들:")
                for filename, _, _ in need_thumbnail:
                    logger.info(f"  - {filename}")

            if already_exists:
                logger.info("✅ 이미 썸네일이 있는 파일들:")
                for filename, _ in already_exists:
                    logger.info(f"  - {filename}")
        else:
            generator.generate_all_thumbnails(force_regenerate=args.force)

    except KeyboardInterrupt:
        logger.warning("⚠️  사용자에 의해 중단되었습니다")
    except Exception as e:
        logger.error(f"❌ 치명적 오류: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()