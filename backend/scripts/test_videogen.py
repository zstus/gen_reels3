#!/usr/bin/env python3

# VideoGenerator 직접 테스트

import json
from video_generator import VideoGenerator

def test_videogen():
    print("=== VideoGenerator 직접 테스트 ===")
    
    try:
        # VideoGenerator 인스턴스 생성
        video_gen = VideoGenerator()
        print("✅ VideoGenerator 인스턴스 생성 완료")
        
        # create_simple_group_clip 메서드 존재 확인
        if hasattr(video_gen, 'create_simple_group_clip'):
            print("✅ create_simple_group_clip 메서드 존재")
        else:
            print("❌ create_simple_group_clip 메서드 없음")
            return False
        
        # create_video_from_uploads 메서드 존재 확인
        if hasattr(video_gen, 'create_video_from_uploads'):
            print("✅ create_video_from_uploads 메서드 존재")
        else:
            print("❌ create_video_from_uploads 메서드 없음")
            return False
        
        # 실제 uploads 폴더 테스트
        print("🚀 uploads 폴더 기반 영상 생성 테스트 시작...")
        
        output_path = video_gen.create_video_from_uploads("output_videos", None, "2_per_image", "bottom", "outline", "BMYEONSUNG_otf.otf", "BMYEONSUNG_otf.otf", "uploads", "bright")
        print(f"✅ 영상 생성 성공: {output_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ 에러 발생: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_videogen()
    print(f"\n테스트 결과: {'성공' if success else '실패'}")