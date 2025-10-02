#!/usr/bin/env python3
"""
기존 assets/videos 폴더의 모든 영상을 미디어 자산 데이터베이스에 추가하는 배치 스크립트
"""
import os
import sys
import logging
from datetime import datetime
import argparse

try:
    from media_asset_manager import media_asset_manager
    MEDIA_ASSET_MANAGER_AVAILABLE = True
except ImportError as e:
    print(f"❌ 미디어 자산 관리자 import 오류: {e}")
    print("media_asset_manager.py 파일이 있는지 확인해주세요.")
    sys.exit(1)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('populate_media_assets.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MediaAssetPopulator:
    def __init__(self, videos_dir: str = "assets/videos"):
        self.videos_dir = videos_dir
        self.video_extensions = {'.mp4', '.mov', '.avi', '.webm', '.mkv', '.flv', '.wmv'}

        if not os.path.exists(videos_dir):
            raise FileNotFoundError(f"Videos 디렉토리가 존재하지 않습니다: {videos_dir}")

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

    def populate_database(self, force_update: bool = False):
        """모든 비디오 파일을 데이터베이스에 추가"""
        start_time = datetime.now()
        logger.info(f"🚀 미디어 자산 데이터베이스 생성 시작: {start_time}")

        # 비디오 파일 스캔
        video_files = self.scan_video_files()
        if not video_files:
            logger.warning("⚠️  비디오 파일이 없습니다.")
            return

        # 기존 자산 확인 또는 강제 업데이트
        if force_update:
            logger.info("🔄 강제 업데이트 모드: 모든 자산을 다시 추가합니다")

        # 자산 추가 진행
        success_count = 0
        skipped_count = 0
        error_count = 0

        for i, (filename, file_path) in enumerate(video_files, 1):
            logger.info(f"📊 진행률: {i}/{len(video_files)} ({i/len(video_files)*100:.1f}%)")

            try:
                # 기존 자산 확인
                existing_asset_id = media_asset_manager.get_asset_by_path(file_path)

                if existing_asset_id and not force_update:
                    logger.info(f"⚠️  이미 존재하는 자산 건너뛰기: {filename}")
                    skipped_count += 1
                    continue

                # 자산 추가
                logger.info(f"🎬 자산 추가 시작: {filename}")

                # 기본 제목 생성 (확장자 제거)
                title = os.path.splitext(filename)[0]

                asset_id = media_asset_manager.add_media_asset(
                    file_path=file_path,
                    original_filename=filename,
                    title=title
                )

                if asset_id:
                    success_count += 1
                    logger.info(f"✅ 자산 추가 완료: {filename} (ID: {asset_id})")
                else:
                    error_count += 1
                    logger.error(f"❌ 자산 추가 실패: {filename}")

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
        logger.info("🎉 미디어 자산 데이터베이스 생성 완료!")
        logger.info(f"⏱️  소요 시간: {duration}")
        logger.info(f"✅ 성공: {success_count}개")
        logger.info(f"⚠️  건너뜀: {skipped_count}개")
        logger.info(f"❌ 실패: {error_count}개")
        logger.info(f"📊 전체 처리: {success_count + skipped_count + error_count}개")
        logger.info("=" * 50)

    def check_database_status(self):
        """데이터베이스 상태 확인"""
        try:
            # 전체 자산 개수 조회
            result = media_asset_manager.get_recent_videos(page=1, limit=1)
            total_count = result.get('total_count', 0)

            logger.info(f"📊 현재 데이터베이스에 등록된 자산: {total_count}개")

            # 태그 개수 조회
            tags = media_asset_manager.get_all_tags()
            logger.info(f"🏷️  등록된 태그: {len(tags)}개")
            if tags:
                logger.info(f"   태그 목록: {', '.join(tags[:10])}" + ("..." if len(tags) > 10 else ""))

            return total_count

        except Exception as e:
            logger.error(f"❌ 데이터베이스 상태 확인 실패: {e}")
            return 0

def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description='미디어 자산 데이터베이스 생성 도구')
    parser.add_argument('--videos-dir', default='assets/videos',
                       help='비디오 파일들이 있는 디렉토리 (기본값: assets/videos)')
    parser.add_argument('--force', action='store_true',
                       help='기존 자산이 있어도 강제로 다시 추가')
    parser.add_argument('--status', action='store_true',
                       help='데이터베이스 상태만 확인')

    args = parser.parse_args()

    try:
        populator = MediaAssetPopulator(args.videos_dir)

        if args.status:
            logger.info("🔍 데이터베이스 상태 확인 모드")
            populator.check_database_status()
        else:
            # 데이터베이스 상태 확인
            current_count = populator.check_database_status()

            if current_count > 0 and not args.force:
                logger.info("📋 기존 자산이 발견되었습니다.")
                logger.info("   --force 옵션을 사용하면 강제로 다시 추가할 수 있습니다.")

                # 사용자 확인
                response = input("계속 진행하시겠습니까? (y/N): ").strip().lower()
                if response not in ['y', 'yes', '예']:
                    logger.info("작업이 취소되었습니다.")
                    return

            populator.populate_database(force_update=args.force)

    except KeyboardInterrupt:
        logger.warning("⚠️  사용자에 의해 중단되었습니다")
    except Exception as e:
        logger.error(f"❌ 치명적 오류: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()