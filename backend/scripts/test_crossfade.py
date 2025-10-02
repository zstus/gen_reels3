#!/usr/bin/env python3
"""
크로스 디졸브 기능 테스트 스크립트
이미지-이미지 전환 구간에서 2초 크로스 디졸브 효과 테스트
"""

import os
import sys
import json
import traceback

# video_generator 모듈 임포트
from video_generator import VideoGenerator

def test_crossfade_functionality():
    """크로스 디졸브 기능 테스트"""
    print("🧪 크로스 디졸브 기능 테스트 시작")
    print("=" * 50)

    try:
        # VideoGenerator 인스턴스 생성 (로깅은 자동으로 초기화됨)
        print("VideoGenerator 인스턴스 생성 중...")
        generator = VideoGenerator()
        print("✅ VideoGenerator 생성 완료 (로깅도 초기화됨)")

        # 테스트용 JSON 내용 읽기
        print("테스트용 JSON 파일 읽기 중...")
        with open('test/text.json', 'r', encoding='utf-8') as f:
            content = json.load(f)
        print("✅ JSON 파일 읽기 완료")

        print("📄 테스트 내용:")
        print(f"  제목: {content.get('title', 'N/A')}")
        for i in range(1, 9):
            body_key = f"body{i}"
            if body_key in content:
                print(f"  {body_key}: {content[body_key]}")

        print("\n🖼️ 테스트 이미지 파일 확인:")
        test_images = []
        for i in range(1, 9):
            for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp']:
                img_path = f"test/{i}{ext}"
                if os.path.exists(img_path):
                    test_images.append(img_path)
                    print(f"  ✅ {img_path} 발견")
                    break

        if len(test_images) < 2:
            print("⚠️ 테스트용 이미지가 부족합니다. 최소 2개의 이미지가 필요합니다.")
            return False

        print(f"\n💫 크로스 디졸브 테스트 설정 (강화된 효과):")
        print(f"  - 이미지 개수: {len(test_images)}개")
        print(f"  - 예상 크로스 디졸브 구간: {len(test_images)-1}개 (모든 이미지 간 전환)")
        print(f"  - 디졸브 시간: 2.0초 (뚜렷한 효과)")
        print(f"  - 겹침 시간: 1.2초 (60% 오버랩)")
        print(f"  - 클립 길이 제한: 70% (더 긴 페이드 허용)")
        print(f"  - 새로운 구현: concatenate_videoclips 기반 (순서 보장)")

        # 테스트 실행
        print("\n🎬 영상 생성 시작...")
        print("=" * 60)

        result_path = generator.create_video_with_local_images(
            content=content,
            music_path="bgm/bright/default.mp3",  # 기본 BGM (없어도 됨)
            output_folder="output_videos",
            image_allocation_mode="1_per_image",  # 각 대사마다 이미지 1개
            text_position="bottom",
            text_style="outline"
        )

        print("=" * 60)

        if result_path and os.path.exists(result_path):
            print(f"\n✅ 테스트 성공!")
            print(f"📹 결과 영상: {result_path}")

            # 파일 크기 확인
            file_size = os.path.getsize(result_path)
            print(f"📊 파일 크기: {file_size:,} bytes ({file_size/1024/1024:.1f} MB)")

            print(f"\n🔍 디버깅 정보:")
            print(f"  - 상세한 디버깅 로그는 'crossfade_debug_YYYYMMDD_HHMMSS.log' 파일에 저장되었습니다")
            print(f"  - 로그 파일에서 다음 메시지들을 확인하세요:")
            print(f"    • '🔍 media_files가 None이므로 자동 생성합니다...' 메시지")
            print(f"    • '📁 자동 감지 [X]: Y.png -> image' 메시지들")
            print(f"    • '🎬 apply_smart_crossfade_transitions 호출됨!' 메시지")
            print(f"    • '🔍 이미지 전환 구간 감지 시작...' 메시지")
            print(f"    • '✅ 전환 구간 발견: X → Y (이미지→이미지)' 메시지들")
            print(f"    • '🎨 apply_crossfade_to_clips 호출됨!' 메시지")
            print(f"    • '✨ 클립 X→Y: 2.0초 크로스 디졸브 적용 완료' 메시지들")

            return True
        else:
            print(f"\n❌ 테스트 실패: 영상 파일이 생성되지 않았습니다.")
            print(f"   'crossfade_debug_YYYYMMDD_HHMMSS.log' 파일을 확인하여 어느 단계에서 실패했는지 파악하세요.")
            return False

    except Exception as e:
        print(f"\n💥 테스트 중 오류 발생:")
        print(f"에러: {str(e)}")
        print("\n상세 에러 정보:")
        traceback.print_exc()
        return False

def check_dependencies():
    """필요한 의존성 확인"""
    print("🔍 의존성 확인...")

    try:
        from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip, concatenate_videoclips
        from moviepy.video.fx import fadein
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
    print("🎭 크로스 디졸브 기능 테스트")
    print("이미지-이미지 전환 구간에서 2초 크로스 디졸브 효과를 테스트합니다.")
    print("상세한 로그는 'crossfade_debug_YYYYMMDD_HHMMSS.log' 파일에 저장됩니다.")
    print()

    # 의존성 확인
    if not check_dependencies():
        print("❌ 의존성 확인 실패. 테스트를 중단합니다.")
        sys.exit(1)

    # 크로스 디졸브 테스트
    success = test_crossfade_functionality()

    print("\n" + "=" * 50)
    if success:
        print("🎉 모든 테스트가 성공적으로 완료되었습니다!")
        print("🎥 생성된 영상에서 이미지 간 부드러운 전환 효과를 확인해보세요.")
        print("📄 로그 파일을 확인하면 크로스 디졸브가 실제로 적용되었는지 알 수 있습니다.")
    else:
        print("💥 테스트가 실패했습니다.")
        print("📄 'crossfade_debug_YYYYMMDD_HHMMSS.log' 파일을 확인하여 문제를 해결해주세요.")

    print("테스트 완료.")