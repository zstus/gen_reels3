#!/usr/bin/env python3
"""
크로스 디졸브 disabled 테스트 스크립트
크로스 디졸브를 끄고 기본 연결 방식이 사용되는지 테스트
"""

import os
import sys
import json
import traceback
import logging
from datetime import datetime

# video_generator 모듈 임포트
from video_generator import VideoGenerator

def setup_test_logging():
    """테스트용 로깅 설정"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"crossfade_disabled_test_{timestamp}.log"

    # 기존 핸들러 제거
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # 파일 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
        ]
    )

    print(f"🗒️ 로그 파일: {log_file}")
    return log_file

def test_crossfade_disabled():
    """크로스 디졸브 disabled 기능 테스트"""
    print("🧪 크로스 디졸브 DISABLED 테스트 시작")
    print("==" * 30)

    try:
        # 로깅 설정
        log_file = setup_test_logging()

        # VideoGenerator 인스턴스 생성
        print("VideoGenerator 인스턴스 생성 중...")
        logging.info("🧪 크로스 디졸브 DISABLED 테스트 시작")
        generator = VideoGenerator()
        logging.info("✅ VideoGenerator 생성 완료")

        # 테스트용 JSON 내용 읽기
        print("테스트용 JSON 파일 읽기 중...")
        with open('test/text.json', 'r', encoding='utf-8') as f:
            content = json.load(f)
        logging.info("✅ JSON 파일 읽기 완료")

        logging.info("📄 테스트 내용:")
        logging.info(f"  제목: {content.get('title', 'N/A')}")
        for i in range(1, 9):
            body_key = f"body{i}"
            if body_key in content and content[body_key]:
                logging.info(f"  {body_key}: {content[body_key]}")

        print("\\n🖼️ 테스트 이미지 파일 확인:")
        test_images = []
        for i in range(1, 9):
            for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp']:
                img_path = f"test/{i}{ext}"
                if os.path.exists(img_path):
                    test_images.append(img_path)
                    logging.info(f"  ✅ {img_path} 발견")
                    break

        if len(test_images) < 2:
            logging.warning("⚠️ 테스트용 이미지가 부족합니다. 최소 2개의 이미지가 필요합니다.")
            return False

        logging.info(f"\\n🚫 크로스 디졸브 DISABLED 테스트 설정:")
        logging.info(f"  - 이미지 개수: {len(test_images)}개")
        logging.info(f"  - cross_dissolve: disabled (크로스 디졸브 꺼짐)")
        logging.info(f"  - 예상 결과: 기본 연결 방식 사용, 바로 전환")

        # 테스트 실행 - cross_dissolve="disabled"로 설정
        print("\\n🎬 영상 생성 시작 (크로스 디졸브 DISABLED)...")
        logging.info("=" * 60)
        logging.info("🎬 영상 생성 시작 - 크로스 디졸브 DISABLED")

        result_path = generator.create_video_with_local_images(
            content=content,
            music_path="bgm/bright/default.mp3",  # 기본 BGM
            output_folder="output_videos",
            image_allocation_mode="1_per_image",  # 각 대사마다 이미지 1개
            text_position="bottom",
            cross_dissolve="disabled"  # 🚫 크로스 디졸브 끄기
        )

        logging.info("=" * 60)

        if result_path and os.path.exists(result_path):
            logging.info(f"\\n✅ 테스트 성공!")
            logging.info(f"📹 결과 영상: {result_path}")

            # 파일 크기 확인
            file_size = os.path.getsize(result_path)
            logging.info(f"📊 파일 크기: {file_size:,} bytes ({file_size/1024/1024:.1f} MB)")

            logging.info(f"\\n🔍 테스트 결과 확인 포인트:")
            logging.info(f"  - 로그에서 '🔍 cross_dissolve 값: disabled' 메시지 확인")
            logging.info(f"  - 로그에서 '🎬 기본 연결 방식 사용 (크로스 디졸브 미적용)' 메시지 확인")
            logging.info(f"  - 로그에서 '🎨 크로스 디졸브 효과 적용' 메시지가 나오면 안됨")
            logging.info(f"  - apply_smart_crossfade_transitions 호출이 없어야 함")

            print(f"\\n✅ 테스트 완료! 로그 파일 확인: {log_file}")
            return True
        else:
            logging.error(f"\\n❌ 테스트 실패: 영상 파일이 생성되지 않았습니다.")
            return False

    except Exception as e:
        logging.error(f"\\n💥 테스트 중 오류 발생:")
        logging.error(f"에러: {str(e)}")
        logging.error("\\n상세 에러 정보:")
        logging.error(traceback.format_exc())
        return False

def check_dependencies():
    """필요한 의존성 확인"""
    print("🔍 의존성 확인...")

    try:
        from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip, concatenate_videoclips
        print("  ✅ MoviePy 라이브러리 OK")
    except ImportError as e:
        print(f"  ❌ MoviePy 라이브러리 오류: {e}")
        return False

    try:
        from PIL import Image, ImageDraw, ImageFont
        print("  ✅ PIL/Pillow 라이브러리 OK")
    except ImportError as e:
        print(f"  ❌ PIL/Pillow 라이브러리 오류: {e}")
        return False

    # 테스트 폴더 확인
    if not os.path.exists('test'):
        print("  ❌ test 폴더가 없습니다.")
        return False

    if not os.path.exists('test/text.json'):
        print("  ❌ test/text.json 파일이 없습니다.")
        return False

    print("  ✅ 테스트 환경 OK")
    return True

if __name__ == "__main__":
    print("🚫 크로스 디졸브 DISABLED 테스트")
    print("크로스 디졸브를 끄고 기본 연결 방식이 사용되는지 테스트합니다.")
    print("상세한 로그는 'crossfade_disabled_test_YYYYMMDD_HHMMSS.log' 파일에 저장됩니다.")
    print()

    # 의존성 확인
    if not check_dependencies():
        print("❌ 의존성 확인 실패. 테스트를 중단합니다.")
        sys.exit(1)

    # 크로스 디졸브 disabled 테스트
    success = test_crossfade_disabled()

    print("\\n" + "==" * 30)
    if success:
        print("🎉 크로스 디졸브 DISABLED 테스트가 완료되었습니다!")
        print("📄 로그 파일을 확인하여 크로스 디졸브가 실제로 꺼졌는지 확인해보세요.")
        print("🔍 확인할 메시지들:")
        print("   - '🔍 cross_dissolve 값: disabled'")
        print("   - '🎬 기본 연결 방식 사용 (크로스 디졸브 미적용)'")
        print("   - '🎨 크로스 디졸브 효과 적용' 메시지가 없어야 함")
    else:
        print("💥 테스트가 실패했습니다.")
        print("📄 로그 파일을 확인하여 문제를 해결해주세요.")

    print("테스트 완료.")