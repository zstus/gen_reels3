#!/usr/bin/env python3
"""
릴스 영상 생성 API 테스트 클라이언트
"""

import requests
import json
import os

def test_api():
    # API 서버 URL
    API_URL = "http://localhost"
    
    # 테스트 데이터
    content_data = {
        "title": "트럼프 말 한마디에 뒤집힌 극우 팬덤",
        "body1": "트럼프가 '숙청·혁명 있다' 글 올리자, 윤 전 대통령 지지자들 잔뜩 고무!",
        "body2": "'윤 전 대통령 구해준다!'며 벌써 망상 풀가동~",
        "body3": "근데 정상회담 들어가서 트럼프가… \"그거 오해야~\"",
        "body4": "순식간에 분위기 급냉각… 유튜브 방송도 뚝! 🤯",
        "body5": "게다가 이재명 대통령 당선 축하까지 하자, 지지자들 멘붕 😱",
        "body6": "급기야 '트럼프 대역설' '트럼프 친중 좌파설'까지 등장ㅋㅋ",
        "body7": "결론: 국제정치 앞에선 망상이 산산조각난다 ✂️"
    }
    
    # 여러 이미지 URL (테스트용 - 실제 사용시 적절한 이미지 URL로 변경)
    image_urls = [
        "https://via.placeholder.com/1920x1080/FF5733/FFFFFF?text=Image+1",
        "https://via.placeholder.com/1920x1080/33FF57/FFFFFF?text=Image+2", 
        "https://via.placeholder.com/1920x1080/3357FF/FFFFFF?text=Image+3",
        "https://via.placeholder.com/1920x1080/FF33F5/FFFFFF?text=Image+4"
    ]
    
    print("API 서버 연결 테스트...")
    
    # 서버 상태 확인
    try:
        response = requests.get(f"{API_URL}/")
        if response.status_code == 200:
            print("✅ API 서버 연결 성공")
            print(f"응답: {response.json()}")
        else:
            print("❌ API 서버 연결 실패")
            return
    except Exception as e:
        print(f"❌ API 서버 연결 오류: {e}")
        return
    
    # 영상 생성 테스트 (배경음악 없이)
    print("\n영상 생성 테스트 (배경음악 없이)...")
    
    try:
        # 더미 MP3 파일 생성 (실제로는 업로드할 MP3 파일이 필요)
        dummy_mp3_content = b"dummy mp3 content"  # 실제 환경에서는 실제 MP3 파일을 사용하세요
        
        files = {
            'background_music': ('test_music.mp3', dummy_mp3_content, 'audio/mpeg')
        }
        
        data = {
            'content_data': json.dumps(content_data),
            'image_urls': json.dumps(image_urls)  # 단일 URL → 여러 URL로 변경
        }
        
        response = requests.post(f"{API_URL}/generate-video", files=files, data=data)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 영상 생성 API 호출 성공")
            print(f"결과: {result}")
        else:
            print(f"❌ 영상 생성 실패: {response.status_code}")
            print(f"오류 내용: {response.text}")
            
    except Exception as e:
        print(f"❌ API 호출 오류: {e}")

def test_with_real_files():
    """실제 파일을 이용한 테스트"""
    API_URL = "http://localhost"
    
    # MP3 파일 경로 (실제 파일 경로로 변경하세요)
    mp3_file_path = "/path/to/your/background_music.mp3"
    
    if not os.path.exists(mp3_file_path):
        print(f"❌ MP3 파일을 찾을 수 없습니다: {mp3_file_path}")
        print("test_client.py 파일의 mp3_file_path를 실제 파일 경로로 수정하세요.")
        return
    
    content_data = {
        "title": "실제 테스트 제목",
        "body1": "첫 번째 내용입니다.",
        "body2": "두 번째 내용입니다.",
        "body3": "세 번째 내용입니다."
    }
    
    # 여러 안정적인 placeholder 이미지
    image_urls = [
        "https://via.placeholder.com/1920x1080/FF5733/FFFFFF?text=Real+Test+Image+1",
        "https://via.placeholder.com/1920x1080/33FF57/FFFFFF?text=Real+Test+Image+2", 
        "https://via.placeholder.com/1920x1080/3357FF/FFFFFF?text=Real+Test+Image+3"
    ]
    
    try:
        with open(mp3_file_path, 'rb') as f:
            files = {
                'background_music': ('background_music.mp3', f, 'audio/mpeg')
            }
            
            data = {
                'content_data': json.dumps(content_data),
                'image_urls': json.dumps(image_urls)  # 단일 URL → 여러 URL로 변경
            }
            
            print("실제 파일을 이용한 영상 생성 중...")
            response = requests.post(f"{API_URL}/generate-video", files=files, data=data)
            
            if response.status_code == 200:
                result = response.json()
                print("✅ 영상 생성 성공!")
                print(f"생성된 영상 경로: {result.get('video_path')}")
            else:
                print(f"❌ 영상 생성 실패: {response.status_code}")
                print(f"오류: {response.text}")
                
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    print("=== 릴스 영상 생성 API 테스트 클라이언트 ===\n")
    
    print("1. 기본 연결 테스트")
    test_api()
    
    print("\n" + "="*50)
    print("2. 실제 파일 테스트를 원하시면 test_with_real_files() 함수를 사용하세요.")
    print("   (mp3_file_path 변수를 실제 MP3 파일 경로로 수정 필요)")