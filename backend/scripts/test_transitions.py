#!/usr/bin/env python3
"""
전환 효과 테스트 스크립트
"""

import sys
import os
import json
import tempfile
from video_generator import VideoGenerator

def create_test_content():
    """테스트용 릴스 콘텐츠 생성"""
    return {
        "title": "전환 효과 테스트 영상",
        "body1": "첫 번째 장면입니다",
        "body2": "두 번째 장면으로 전환됩니다",
        "body3": "세 번째 장면이 나타납니다",
        "body4": "네 번째이자 마지막 장면입니다"
    }

def test_transitions():
    """전환 효과 테스트 실행"""
    print("=" * 60)
    print("🎬 전환 효과 테스트 시작")
    print("=" * 60)

    try:
        # VideoGenerator 인스턴스 생성
        generator = VideoGenerator()

        # 테스트 콘텐츠 생성
        test_content = create_test_content()
        print(f"📝 테스트 콘텐츠: {len([k for k in test_content.keys() if k.startswith('body')])}개 장면")

        # 출력 폴더 설정
        output_folder = "output_videos"
        os.makedirs(output_folder, exist_ok=True)

        # 테스트 파일들이 있는지 확인
        test_folder = "test"
        if not os.path.exists(test_folder):
            print(f"❌ 테스트 폴더가 없습니다: {test_folder}")
            return False

        # test 폴더의 미디어 파일들 확인
        media_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'mp4', 'mov', 'avi', 'webm']
        media_files = []
        for filename in os.listdir(test_folder):
            if any(filename.lower().endswith(f".{ext}") for ext in media_extensions):
                media_files.append(os.path.join(test_folder, filename))

        print(f"📁 발견된 미디어 파일: {len(media_files)}개")
        for media_file in media_files:
            print(f"  - {os.path.basename(media_file)}")

        if len(media_files) < 2:
            print("❌ 전환 효과 테스트를 위해 최소 2개의 미디어 파일이 필요합니다")
            return False

        # BGM 설정 (없으면 기본값 사용)
        music_path = None
        bgm_folders = ["bgm/bright", "bgm/calm", "bgm/romantic"]
        for bgm_folder in bgm_folders:
            if os.path.exists(bgm_folder):
                bgm_files = [f for f in os.listdir(bgm_folder) if f.lower().endswith(('.mp3', '.wav', '.m4a'))]
                if bgm_files:
                    music_path = os.path.join(bgm_folder, bgm_files[0])
                    print(f"🎵 BGM 사용: {music_path}")
                    break

        if not music_path:
            print("⚠️ BGM 파일 없음, 음성만 사용")

        print("\n🚀 영상 생성 시작...")
        print("⏳ 이 과정에서 다음 전환 효과들이 랜덤으로 적용됩니다:")
        print("  - Cut: 즉시 전환")
        print("  - Dissolve: 크로스 페이드 (검은 화면 없음)")
        print("  - Wipe: 슬라이딩 전환 (좌우상하 랜덤)")

        # 영상 생성 (전환 효과 포함)
        result_path = generator.create_video_with_local_images(
            content=test_content,
            music_path=music_path,
            output_folder=output_folder,
            image_allocation_mode="1_per_image",  # 각 장면마다 다른 미디어
            text_position="bottom",
            text_style="outline",
            title_area_mode="keep",
            music_mood="bright",
            voice_narration="enabled"
        )

        if result_path and os.path.exists(result_path):
            print(f"\n✅ 전환 효과 테스트 성공!")
            print(f"📹 생성된 영상: {result_path}")

            # 파일 크기 정보
            file_size = os.path.getsize(result_path) / (1024 * 1024)  # MB
            print(f"📊 파일 크기: {file_size:.1f} MB")

            # 영상 정보 표시 시도
            try:
                from moviepy.editor import VideoFileClip
                with VideoFileClip(result_path) as video:
                    print(f"⏱️ 영상 길이: {video.duration:.1f}초")
                    print(f"📐 해상도: {video.w}x{video.h}")
                    print(f"🎞️ FPS: {video.fps}")
            except:
                print("ℹ️ 영상 메타데이터 확인 불가")

            print(f"\n🎉 테스트 완료! 생성된 영상에서 다양한 전환 효과를 확인해보세요.")
            return True

        else:
            print(f"\n❌ 영상 생성 실패")
            return False

    except Exception as e:
        print(f"\n💥 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_transition_methods_only():
    """전환 효과 메소드만 단독 테스트"""
    print("\n" + "=" * 40)
    print("🔧 전환 효과 메소드 단독 테스트")
    print("=" * 40)

    try:
        generator = VideoGenerator()

        # 가상 클립들 생성 (테스트용)
        from moviepy.editor import ColorClip

        clip1 = ColorClip(size=(504, 890), color=(255, 0, 0), duration=2.0)  # 빨강
        clip2 = ColorClip(size=(504, 890), color=(0, 255, 0), duration=2.0)  # 초록
        clip3 = ColorClip(size=(504, 890), color=(0, 0, 255), duration=2.0)  # 파랑

        test_clips = [clip1, clip2, clip3]

        print(f"🎨 테스트 클립: 빨강(2초) → 초록(2초) → 파랑(2초)")

        # 전환 효과 적용
        result_video = generator.apply_random_transitions(test_clips, transition_duration=0.5)

        if result_video:
            print(f"✅ 전환 효과 메소드 테스트 성공")
            print(f"⏱️ 결과 영상 길이: {result_video.duration:.2f}초")

            # 간단한 출력 테스트
            output_path = os.path.join("output_videos", "transition_method_test.mp4")
            try:
                result_video.write_videofile(output_path, fps=30, verbose=False, logger=None)
                print(f"📹 메소드 테스트 영상 저장: {output_path}")
            except Exception as e:
                print(f"⚠️ 테스트 영상 저장 실패: {e}")

            return True
        else:
            print(f"❌ 전환 효과 메소드 테스트 실패")
            return False

    except Exception as e:
        print(f"💥 메소드 테스트 중 오류: {e}")
        return False

if __name__ == "__main__":
    print("🎬 전환 효과 시스템 테스트")
    print("=" * 60)

    # 메소드 단독 테스트 먼저 실행
    method_test_result = test_transition_methods_only()

    # 전체 시스템 테스트
    full_test_result = test_transitions()

    # 결과 요약
    print("\n" + "=" * 60)
    print("📋 테스트 결과 요약")
    print("=" * 60)
    print(f"전환 효과 메소드 테스트: {'✅ 통과' if method_test_result else '❌ 실패'}")
    print(f"전체 시스템 테스트: {'✅ 통과' if full_test_result else '❌ 실패'}")

    if method_test_result and full_test_result:
        print("\n🎊 모든 테스트 통과! 전환 효과 시스템이 정상 작동합니다.")
    elif method_test_result:
        print("\n⚠️ 메소드는 정상이나 전체 시스템에 문제가 있습니다.")
    else:
        print("\n❌ 전환 효과 시스템에 문제가 있습니다.")