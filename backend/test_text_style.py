#!/usr/bin/env python3
"""
텍스트 스타일 기능 테스트 스크립트
새로 추가된 반투명 배경 vs 외곽선 스타일 선택 기능을 테스트합니다.
"""

import os
import sys
from PIL import Image, ImageDraw, ImageFont

# video_generator 모듈을 import하기 위한 패스 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from video_generator import VideoGenerator
except ImportError as e:
    print(f"❌ VideoGenerator 모듈 import 실패: {e}")
    sys.exit(1)

def test_text_styles():
    """두 가지 텍스트 스타일 비교 테스트"""
    print("🧪 텍스트 스타일 기능 테스트")
    print("=" * 50)
    
    # VideoGenerator 인스턴스 생성
    video_gen = VideoGenerator()
    
    # 테스트 텍스트
    test_text = "안녕하세요! 😊\n새로운 텍스트 스타일 기능을 테스트합니다.\n반투명 배경과 외곽선 중 어떤 것이 더 보기 좋을까요?"
    
    # 테스트 이미지 크기 (릴스 해상도)
    width, height = 414, 896
    
    print("📝 테스트 텍스트:")
    print(f"   {repr(test_text)}")
    print()
    
    # 1. 외곽선 스타일 테스트
    print("1️⃣  외곽선 스타일 테스트 (기존 방식)")
    try:
        outline_image = video_gen.create_text_image(
            test_text, width, height, 
            text_position="middle", 
            text_style="outline"
        )
        print(f"   ✅ 외곽선 이미지 생성 성공: {outline_image}")
        
        # 파일 존재 확인
        if os.path.exists(outline_image):
            file_size = os.path.getsize(outline_image)
            print(f"   📊 파일 크기: {file_size:,} bytes")
        else:
            print(f"   ❌ 파일이 생성되지 않음: {outline_image}")
            
    except Exception as e:
        print(f"   ❌ 외곽선 스타일 테스트 실패: {e}")
    
    print()
    
    # 2. 반투명 배경 스타일 테스트
    print("2️⃣  반투명 배경 스타일 테스트 (새 기능)")
    try:
        background_image = video_gen.create_text_image(
            test_text, width, height, 
            text_position="middle", 
            text_style="background"
        )
        print(f"   ✅ 반투명 배경 이미지 생성 성공: {background_image}")
        
        # 파일 존재 확인
        if os.path.exists(background_image):
            file_size = os.path.getsize(background_image)
            print(f"   📊 파일 크기: {file_size:,} bytes")
        else:
            print(f"   ❌ 파일이 생성되지 않음: {background_image}")
            
    except Exception as e:
        print(f"   ❌ 반투명 배경 스타일 테스트 실패: {e}")
    
    print()
    
    # 3. 다양한 텍스트 위치에서 테스트
    print("3️⃣  다양한 텍스트 위치 테스트")
    positions = ["top", "middle", "bottom"]
    styles = ["outline", "background"]
    
    for position in positions:
        for style in styles:
            try:
                test_image = video_gen.create_text_image(
                    f"위치: {position}\n스타일: {style}", 
                    width, height, 
                    text_position=position, 
                    text_style=style
                )
                print(f"   ✅ {position}-{style}: {os.path.basename(test_image)}")
                
                # 생성된 임시 파일 정리 (선택사항)
                # os.unlink(test_image)
                
            except Exception as e:
                print(f"   ❌ {position}-{style} 실패: {e}")
    
    print()
    print("🎉 텍스트 스타일 기능 테스트 완료!")
    print()
    print("💡 API 사용법:")
    print("   text_style='outline'  - 기존 외곽선 방식 (기본값)")
    print("   text_style='background' - 새로운 반투명 배경 방식")
    print()
    print("📋 API 파라미터 예시:")
    print("   curl -X POST 'http://localhost:8097/generate-video' \\")
    print("        -F 'content_data={\"title\":\"테스트\",\"body1\":\"내용\"}' \\")
    print("        -F 'music_mood=bright' \\")
    print("        -F 'text_style=background' \\")
    print("        -F 'use_test_files=true'")

def check_font_availability():
    """폰트 가용성 확인"""
    print("🔤 폰트 가용성 확인")
    print("-" * 30)
    
    video_gen = VideoGenerator()
    
    # 한글 폰트 확인
    font_path = video_gen.font_path
    print(f"한글 폰트: {font_path}")
    if os.path.exists(font_path):
        print("   ✅ 사용 가능")
    else:
        print("   ❌ 찾을 수 없음")
    
    # 이모지 폰트 확인
    emoji_font_path = video_gen.get_emoji_font()
    print(f"이모지 폰트: {emoji_font_path}")
    if emoji_font_path and os.path.exists(emoji_font_path):
        print("   ✅ 사용 가능")
    else:
        print("   ❌ 찾을 수 없음 (이모지가 제대로 표시되지 않을 수 있음)")
    
    print()

if __name__ == "__main__":
    check_font_availability()
    test_text_styles()
    print("✨ 모든 테스트 완료!")