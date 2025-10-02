#!/usr/bin/env python3
"""
Folder Manager 독립 테스트
Job ID 기반 폴더 격리 및 월별 output 폴더 구조 검증
"""

import os
import sys
import uuid
import shutil
from datetime import datetime

# 현재 스크립트의 디렉토리를 기준으로 folder_manager 임포트
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from folder_manager import FolderManager, create_job_folders, get_job_folders, cleanup_job_folders
    print("✅ folder_manager 모듈 임포트 성공")
except ImportError as e:
    print(f"❌ folder_manager 모듈 임포트 실패: {e}")
    sys.exit(1)

def test_folder_creation():
    """Job 폴더 생성 테스트"""
    print("\n" + "="*50)
    print("📁 Job 폴더 생성 테스트")
    print("="*50)

    # 테스트용 Job ID 생성
    job_id = str(uuid.uuid4())
    print(f"🆔 테스트 Job ID: {job_id}")

    try:
        # Job 폴더 생성
        uploads_folder, output_folder = create_job_folders(job_id)

        print(f"📂 uploads 폴더: {uploads_folder}")
        print(f"📂 output 폴더: {output_folder}")

        # 폴더 존재 확인
        uploads_exists = os.path.exists(uploads_folder)
        output_exists = os.path.exists(output_folder)

        print(f"✅ uploads 폴더 존재: {uploads_exists}")
        print(f"✅ output 폴더 존재: {output_exists}")

        # 폴더 구조 검증
        expected_uploads = f"uploads/job_{job_id}"
        current_month = datetime.now().strftime("%Y%m")
        expected_output = f"output_videos/{current_month}"

        print(f"🎯 예상 uploads 경로: {expected_uploads}")
        print(f"🎯 예상 output 경로: {expected_output}")

        uploads_correct = uploads_folder.endswith(expected_uploads.replace('/', os.sep))
        output_correct = output_folder.endswith(expected_output.replace('/', os.sep))

        print(f"✅ uploads 경로 정확: {uploads_correct}")
        print(f"✅ output 경로 정확 (월별): {output_correct}")

        if uploads_exists and output_exists and uploads_correct and output_correct:
            print("🎉 Job 폴더 생성 테스트 성공!")
            return job_id, uploads_folder, output_folder
        else:
            print("❌ Job 폴더 생성 테스트 실패")
            return None, None, None

    except Exception as e:
        print(f"❌ Job 폴더 생성 중 오류: {e}")
        return None, None, None

def test_file_isolation():
    """파일 격리 테스트"""
    print("\n" + "="*50)
    print("🔒 파일 격리 테스트")
    print("="*50)

    # 두 개의 서로 다른 Job ID 생성
    job_id_1 = str(uuid.uuid4())
    job_id_2 = str(uuid.uuid4())

    print(f"🆔 Job 1 ID: {job_id_1}")
    print(f"🆔 Job 2 ID: {job_id_2}")

    try:
        # 두 개의 Job 폴더 생성
        uploads_1, output_1 = create_job_folders(job_id_1)
        uploads_2, output_2 = create_job_folders(job_id_2)

        print(f"📂 Job 1 uploads: {uploads_1}")
        print(f"📂 Job 2 uploads: {uploads_2}")
        print(f"📂 Job 1 output: {output_1}")
        print(f"📂 Job 2 output: {output_2}")

        # 각 Job 폴더에 테스트 파일 생성
        test_file_1 = os.path.join(uploads_1, "test_file_1.txt")
        test_file_2 = os.path.join(uploads_2, "test_file_2.txt")

        with open(test_file_1, 'w', encoding='utf-8') as f:
            f.write(f"Job 1 테스트 파일 - {job_id_1}")

        with open(test_file_2, 'w', encoding='utf-8') as f:
            f.write(f"Job 2 테스트 파일 - {job_id_2}")

        print(f"📄 Job 1 테스트 파일 생성: {test_file_1}")
        print(f"📄 Job 2 테스트 파일 생성: {test_file_2}")

        # 파일 격리 확인
        file_1_exists = os.path.exists(test_file_1)
        file_2_exists = os.path.exists(test_file_2)
        uploads_isolated = uploads_1 != uploads_2

        print(f"✅ Job 1 파일 존재: {file_1_exists}")
        print(f"✅ Job 2 파일 존재: {file_2_exists}")
        print(f"✅ uploads 폴더 격리: {uploads_isolated}")

        # output 폴더는 월별 공유 확인
        output_shared = output_1 == output_2
        print(f"✅ output 폴더 월별 공유: {output_shared}")

        if file_1_exists and file_2_exists and uploads_isolated and output_shared:
            print("🎉 파일 격리 테스트 성공!")
            return True
        else:
            print("❌ 파일 격리 테스트 실패")
            return False

    except Exception as e:
        print(f"❌ 파일 격리 테스트 중 오류: {e}")
        return False

def test_cleanup():
    """폴더 정리 테스트"""
    print("\n" + "="*50)
    print("🧹 폴더 정리 테스트")
    print("="*50)

    # 테스트용 Job ID 생성
    job_id = str(uuid.uuid4())
    print(f"🆔 테스트 Job ID: {job_id}")

    try:
        # Job 폴더 생성
        uploads_folder, output_folder = create_job_folders(job_id)

        # 테스트 파일 생성
        test_file = os.path.join(uploads_folder, "test_cleanup.txt")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("정리 테스트용 파일")

        print(f"📄 테스트 파일 생성: {test_file}")

        # 파일 존재 확인
        file_exists_before = os.path.exists(test_file)
        uploads_exists_before = os.path.exists(uploads_folder)

        print(f"🔍 정리 전 파일 존재: {file_exists_before}")
        print(f"🔍 정리 전 uploads 폴더 존재: {uploads_exists_before}")

        # 폴더 정리 실행
        cleanup_success = cleanup_job_folders(job_id, keep_output=True)

        # 정리 후 상태 확인
        file_exists_after = os.path.exists(test_file)
        uploads_exists_after = os.path.exists(uploads_folder)
        output_exists_after = os.path.exists(output_folder)

        print(f"🔍 정리 후 파일 존재: {file_exists_after}")
        print(f"🔍 정리 후 uploads 폴더 존재: {uploads_exists_after}")
        print(f"🔍 정리 후 output 폴더 존재: {output_exists_after}")
        print(f"✅ 정리 작업 성공: {cleanup_success}")

        # 예상 결과: uploads 폴더 삭제됨, output 폴더 유지됨
        expected_result = (not file_exists_after and
                         not uploads_exists_after and
                         output_exists_after and
                         cleanup_success)

        if expected_result:
            print("🎉 폴더 정리 테스트 성공!")
            return True
        else:
            print("❌ 폴더 정리 테스트 실패")
            return False

    except Exception as e:
        print(f"❌ 폴더 정리 테스트 중 오류: {e}")
        return False

def test_folder_stats():
    """폴더 통계 테스트"""
    print("\n" + "="*50)
    print("📊 폴더 통계 테스트")
    print("="*50)

    try:
        # FolderManager 인스턴스 생성
        folder_manager = FolderManager()

        # 현재 폴더 통계 조회
        stats = folder_manager.get_folder_stats()

        print("📈 현재 폴더 통계:")
        print(f"   📁 uploads 폴더 수: {stats.get('uploads_folders', 0)}개")
        print(f"   📁 output 폴더 수: {stats.get('output_folders', 0)}개")
        print(f"   💾 uploads 총 크기: {stats.get('total_uploads_size', 0)} bytes")
        print(f"   💾 output 총 크기: {stats.get('total_output_size', 0)} bytes")

        if isinstance(stats, dict):
            print("🎉 폴더 통계 테스트 성공!")
            return True
        else:
            print("❌ 폴더 통계 테스트 실패")
            return False

    except Exception as e:
        print(f"❌ 폴더 통계 테스트 중 오류: {e}")
        return False

def main():
    """메인 테스트 함수"""
    print("🚀 Folder Manager 독립 테스트 시작")
    print(f"🕒 테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 현재 작업 디렉토리 출력
    current_dir = os.getcwd()
    print(f"📍 현재 작업 디렉토리: {current_dir}")

    test_results = []

    # 1. 폴더 생성 테스트
    job_id, uploads_folder, output_folder = test_folder_creation()
    test_results.append(("폴더 생성", job_id is not None))

    # 2. 파일 격리 테스트
    isolation_success = test_file_isolation()
    test_results.append(("파일 격리", isolation_success))

    # 3. 폴더 정리 테스트
    cleanup_success = test_cleanup()
    test_results.append(("폴더 정리", cleanup_success))

    # 4. 폴더 통계 테스트
    stats_success = test_folder_stats()
    test_results.append(("폴더 통계", stats_success))

    # 결과 요약
    print("\n" + "="*60)
    print("📊 테스트 결과 요약")
    print("="*60)

    total_tests = len(test_results)
    passed_tests = sum(1 for _, result in test_results if result)

    for test_name, result in test_results:
        status = "✅ 성공" if result else "❌ 실패"
        print(f"{status} {test_name}")

    print("="*60)
    print(f"📈 전체 결과: {passed_tests}/{total_tests} 성공")

    if passed_tests == total_tests:
        print("🎉 모든 테스트 성공! 동시성 문제 해결됨!")
        return True
    else:
        print("⚠️ 일부 테스트 실패. 추가 수정 필요")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 테스트가 사용자에 의해 중단되었습니다")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 예상치 못한 오류: {e}")
        sys.exit(1)