#!/usr/bin/env python3
"""
와이프 전환 효과 테스트 스크립트
"""

import os
import sys
import json
import logging
from datetime import datetime

# 현재 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from video_generator import VideoGenerator

# 로깅 설정 - 파일에만 저장
log_filename = f"wipe_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# 기존 핸들러 제거
logger = logging.getLogger()
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# 파일 핸들러만 추가
file_handler = logging.FileHandler(log_filename, encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)

logger.addHandler(file_handler)
logger.setLevel(logging.INFO)

logger = logging.getLogger(__name__)

def test_wipe_transition():
    """와이프 전환 효과 테스트"""
    print("🧪 와이프 전환 효과 테스트 시작")
    logger.info("🧪 와이프 전환 효과 테스트 시작")

    try:
        # 1. VideoGenerator 인스턴스 생성
        video_gen = VideoGenerator()
        print("✅ VideoGenerator 인스턴스 생성 완료")
        logger.info("✅ VideoGenerator 인스턴스 생성 완료")

        # 2. uploads 폴더 준비
        uploads_folder = os.path.join(current_dir, "uploads")
        os.makedirs(uploads_folder, exist_ok=True)

        # 3. 테스트용 text.json 생성
        test_content = {
            "title": "와이프 전환 테스트",
            "body1": "첫 번째 대사입니다",
            "body2": "두 번째 대사입니다",
            "body3": "세 번째 대사입니다"
        }

        text_json_path = os.path.join(uploads_folder, "text.json")
        with open(text_json_path, 'w', encoding='utf-8') as f:
            json.dump(test_content, f, ensure_ascii=False, indent=2)

        print(f"✅ 테스트 text.json 생성: {text_json_path}")
        logger.info(f"✅ 테스트 text.json 생성: {text_json_path}")

        # 4. 테스트 이미지 복사 (test 폴더에서 uploads 폴더로)
        test_folder = os.path.join(current_dir, "test")
        if os.path.exists(test_folder):
            import shutil
            for i in range(1, 4):  # 1.jpg, 2.jpg, 3.jpg 복사
                for ext in ['jpg', 'png', 'webp', 'mp4']:
                    src_file = os.path.join(test_folder, f"{i}.{ext}")
                    if os.path.exists(src_file):
                        dst_file = os.path.join(uploads_folder, f"{i}.{ext}")
                        shutil.copy2(src_file, dst_file)
                        print(f"✅ 테스트 파일 복사: {src_file} → {dst_file}")
                        logger.info(f"✅ 테스트 파일 복사: {src_file} → {dst_file}")
                        break

        # 5. 출력 폴더 준비
        output_folder = os.path.join(current_dir, "output_videos")
        os.makedirs(output_folder, exist_ok=True)

        # 6. 와이프 전환 효과로 영상 생성 테스트
        print("\n🌊 와이프 전환 효과 테스트 시작...")
        logger.info("🌊 와이프 전환 효과 테스트 시작...")

        # 파라미터 로깅
        params = {
            'transition_effect': 'wipe',
            'image_allocation_mode': '1_per_image',
            'text_position': 'bottom',
            'text_style': 'outline',
            'title_area_mode': 'keep'
        }

        print(f"📋 테스트 파라미터: {params}")
        logger.info(f"📋 테스트 파라미터: {params}")

        result = video_gen.create_video_from_uploads(
            output_folder=output_folder,
            bgm_file_path=None,
            image_allocation_mode=params['image_allocation_mode'],
            text_position=params['text_position'],
            text_style=params['text_style'],
            title_area_mode=params['title_area_mode'],
            uploads_folder=uploads_folder,
            music_mood="bright",
            voice_narration="enabled",
            transition_effect=params['transition_effect']  # 와이프 전환 효과
        )

        if result and isinstance(result, str):
            print(f"✅ 와이프 전환 테스트 성공: {result}")
            logger.info(f"✅ 와이프 전환 테스트 성공: {result}")

            # 파일 크기 확인
            if os.path.exists(result):
                file_size = os.path.getsize(result) / (1024 * 1024)  # MB
                print(f"📁 생성된 파일 크기: {file_size:.2f} MB")
                logger.info(f"📁 생성된 파일 크기: {file_size:.2f} MB")

            return True
        else:
            print(f"❌ 와이프 전환 테스트 실패: {result}")
            logger.error(f"❌ 와이프 전환 테스트 실패: {result}")
            return False

    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
        logger.error(f"❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        logger.error(traceback.format_exc())
        return False

def test_all_transitions():
    """모든 전환 효과 비교 테스트"""
    print("\n🔄 모든 전환 효과 비교 테스트")
    logger.info("🔄 모든 전환 효과 비교 테스트")

    effects = ['none', 'crossfade', 'wipe']
    results = {}

    for effect in effects:
        print(f"\n--- {effect.upper()} 전환 테스트 ---")
        logger.info(f"--- {effect.upper()} 전환 테스트 ---")

        try:
            video_gen = VideoGenerator()
            uploads_folder = os.path.join(current_dir, "uploads")
            output_folder = os.path.join(current_dir, "output_videos")

            result = video_gen.create_video_from_uploads(
                output_folder=output_folder,
                bgm_file_path=None,
                image_allocation_mode='1_per_image',
                text_position='bottom',
                text_style='outline',
                title_area_mode='keep',
                uploads_folder=uploads_folder,
                music_mood="bright",
                voice_narration="enabled",
                transition_effect=effect
            )

            if result:
                print(f"✅ {effect} 테스트 성공")
                logger.info(f"✅ {effect} 테스트 성공")
                results[effect] = "성공"
            else:
                print(f"❌ {effect} 테스트 실패")
                logger.error(f"❌ {effect} 테스트 실패")
                results[effect] = "실패"

        except Exception as e:
            print(f"❌ {effect} 테스트 오류: {e}")
            logger.error(f"❌ {effect} 테스트 오류: {e}")
            results[effect] = f"오류: {e}"

    print(f"\n📊 테스트 결과 요약: {results}")
    logger.info(f"📊 테스트 결과 요약: {results}")

    return results

if __name__ == "__main__":
    print("🚀 와이프 전환 효과 종합 테스트 시작")
    print(f"📋 로그 파일: {log_filename}")

    # 단일 와이프 테스트
    wipe_success = test_wipe_transition()

    # 모든 전환 효과 비교 테스트
    all_results = test_all_transitions()

    print(f"\n🏁 테스트 완료!")
    print(f"📋 상세 로그: {log_filename}")

    if wipe_success:
        print("✅ 와이프 전환 테스트 성공")
    else:
        print("❌ 와이프 전환 테스트 실패 - 로그를 확인하세요")