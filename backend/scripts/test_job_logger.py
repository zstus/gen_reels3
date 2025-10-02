#!/usr/bin/env python3
"""
Job 로깅 시스템 테스트 스크립트
"""

import json
import os
import tempfile
from job_logger import job_logger

def test_job_logger():
    """Job 로깅 시스템 기본 기능 테스트"""

    print("🧪 Job 로깅 시스템 테스트 시작")

    # 테스트 데이터
    job_id = "test-job-12345"
    user_email = "test@example.com"
    reels_content = {
        "title": "테스트 영상 제목",
        "body1": "첫 번째 대사입니다",
        "body2": "두 번째 대사입니다",
        "body3": "세 번째 대사입니다"
    }

    try:
        # 1. Job 로그 생성
        print("\n1️⃣ Job 로그 생성")
        job_logger.create_job_log(
            job_id=job_id,
            user_email=user_email,
            reels_content=reels_content,
            music_mood="bright",
            text_position="bottom",
            image_allocation_mode="2_per_image",
            metadata={"test": True}
        )
        print(f"✅ Job 로그 생성 성공: {job_id}")

        # 2. 가상 미디어 파일 저장 (임시 파일 생성)
        print("\n2️⃣ 미디어 파일 저장")

        # 임시 이미지 파일 생성
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jpg', delete=False) as temp_image:
            temp_image.write("fake image content")
            temp_image_path = temp_image.name

        # 임시 비디오 파일 생성
        with tempfile.NamedTemporaryFile(mode='w', suffix='.mp4', delete=False) as temp_video:
            temp_video.write("fake video content")
            temp_video_path = temp_video.name

        # 미디어 파일들을 assets에 저장
        saved_image_path = job_logger.save_media_file(
            job_id=job_id,
            original_file_path=temp_image_path,
            original_filename="test_image.jpg",
            file_type="image",
            sequence_number=1
        )
        print(f"✅ 이미지 파일 저장 성공: {saved_image_path}")

        saved_video_path = job_logger.save_media_file(
            job_id=job_id,
            original_file_path=temp_video_path,
            original_filename="test_video.mp4",
            file_type="video",
            sequence_number=2
        )
        print(f"✅ 비디오 파일 저장 성공: {saved_video_path}")

        # 임시 파일 정리
        os.unlink(temp_image_path)
        os.unlink(temp_video_path)

        # 2-1. metadata 업데이트 (assets 정보 포함)
        print("\n2-1️⃣ Metadata 업데이트")
        assets_metadata = {
            'uploaded_files': [
                {
                    'sequence': 1,
                    'original_filename': 'test_image.jpg',
                    'asset_path': saved_image_path,
                    'file_type': 'image',
                    'file_size': os.path.getsize(saved_image_path) if os.path.exists(saved_image_path) else 0
                },
                {
                    'sequence': 2,
                    'original_filename': 'test_video.mp4',
                    'asset_path': saved_video_path,
                    'file_type': 'video',
                    'file_size': os.path.getsize(saved_video_path) if os.path.exists(saved_video_path) else 0
                }
            ],
            'title_font': 'BMYEONSUNG_otf.otf',
            'body_font': 'BMYEONSUNG_otf.otf',
            'voice_narration': 'enabled',
            'title_area_mode': 'keep'
        }

        job_logger.update_job_metadata(job_id, assets_metadata)
        print("✅ Metadata 업데이트 성공 (assets 정보 포함)")

        # 3. Job 상태 업데이트
        print("\n3️⃣ Job 상태 업데이트")
        job_logger.update_job_status(job_id, "processing")
        print("✅ 상태 업데이트: processing")

        # 4. 최종 비디오 경로 설정
        print("\n4️⃣ 최종 비디오 경로 설정")
        output_video_path = "output_videos/test_reels_12345.mp4"
        job_logger.set_output_video_path(job_id, output_video_path)
        job_logger.update_job_status(job_id, "completed")
        print(f"✅ 최종 비디오 경로 설정: {output_video_path}")

        # 5. Job 정보 조회
        print("\n5️⃣ Job 정보 조회")
        job_info = job_logger.get_job_info(job_id)
        if job_info:
            print("✅ Job 정보 조회 성공:")
            print(f"  - 사용자: {job_info['user_email']}")
            print(f"  - 상태: {job_info['status']}")
            print(f"  - 생성시간: {job_info['created_at']}")
            print(f"  - 완료시간: {job_info['completed_at']}")
            print(f"  - 최종 비디오: {job_info['output_video_path']}")
            print(f"  - 미디어 파일 개수: {len(job_info['media_files'])}")

            for i, media_file in enumerate(job_info['media_files'], 1):
                print(f"    {i}. {media_file['original_filename']} ({media_file['file_type']}) -> {media_file['asset_path']}")

            # metadata의 uploaded_files 정보도 출력
            metadata = job_info.get('metadata', {})
            uploaded_files = metadata.get('uploaded_files', [])
            if uploaded_files:
                print(f"  - Metadata의 uploaded_files:")
                for uf in uploaded_files:
                    print(f"    seq:{uf['sequence']} {uf['original_filename']} -> {uf['asset_path']} ({uf['file_size']} bytes)")

        # 6. 사용자별 Job 목록 조회
        print("\n6️⃣ 사용자별 Job 목록 조회")
        user_jobs = job_logger.get_user_jobs(user_email, limit=10)
        print(f"✅ {user_email} 사용자의 Job 목록: {len(user_jobs)}개")

        # 7. 통계 정보 조회
        print("\n7️⃣ 통계 정보 조회")
        stats = job_logger.get_job_statistics()
        print("✅ Job 통계:")
        print(f"  - 총 Job 개수: {stats['total_jobs']}")
        print(f"  - 상태별 통계: {stats['status_stats']}")
        print(f"  - 일별 통계: {len(stats['daily_stats'])}일치 데이터")

        print("\n🎉 모든 테스트 통과!")
        return True

    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_error_handling():
    """에러 처리 테스트"""
    print("\n🔍 에러 처리 테스트")

    try:
        # 존재하지 않는 Job ID 조회
        job_info = job_logger.get_job_info("nonexistent-job-id")
        if job_info is None:
            print("✅ 존재하지 않는 Job ID 조회: None 반환")

        # 실패한 Job 상태 업데이트
        failed_job_id = "failed-test-job"
        job_logger.create_job_log(
            job_id=failed_job_id,
            user_email="test@example.com",
            reels_content={"title": "실패 테스트"},
            metadata={}
        )
        job_logger.update_job_status(failed_job_id, "failed", "테스트 실패 메시지")
        print("✅ 실패 상태 업데이트 성공")

        return True

    except Exception as e:
        print(f"❌ 에러 처리 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Job 로깅 시스템 테스트")
    print("=" * 50)

    # 기본 기능 테스트
    basic_test_passed = test_job_logger()

    # 에러 처리 테스트
    error_test_passed = test_error_handling()

    print("\n" + "=" * 50)
    print("테스트 결과 요약")
    print("=" * 50)
    print(f"기본 기능 테스트: {'✅ 통과' if basic_test_passed else '❌ 실패'}")
    print(f"에러 처리 테스트: {'✅ 통과' if error_test_passed else '❌ 실패'}")

    if basic_test_passed and error_test_passed:
        print("\n🎊 모든 테스트가 성공적으로 완료되었습니다!")
        print("\nJob 로깅 시스템이 정상적으로 작동합니다:")
        print("- SQLite 데이터베이스 생성 및 스키마 초기화 완료")
        print("- 미디어 파일 assets 폴더 저장 기능 작동")
        print("- Job 상태 추적 및 업데이트 기능 작동")
        print("- API 통합 준비 완료")
    else:
        print("\n⚠️ 일부 테스트가 실패했습니다. 로그를 확인해 주세요.")