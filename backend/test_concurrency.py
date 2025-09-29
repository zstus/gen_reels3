"""
동시성 문제 해결 검증 테스트
여러 사용자가 동시에 영상을 생성할 때 파일 충돌이 발생하지 않는지 확인
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime

# 테스트 설정
BASE_URL = "http://localhost:8080"
TEST_USERS = [
    {"email": "user1@test.com", "title": "사용자1 테스트 영상"},
    {"email": "user2@test.com", "title": "사용자2 테스트 영상"},
    {"email": "user3@test.com", "title": "사용자3 테스트 영상"},
]

async def create_test_video(session, user_data, user_id):
    """개별 사용자의 영상 생성 테스트"""
    try:
        print(f"🎬 사용자 {user_id} 영상 생성 시작: {user_data['email']}")

        # 테스트용 릴스 콘텐츠
        content_data = {
            "title": user_data["title"],
            "body1": f"사용자 {user_id}의 첫 번째 메시지입니다",
            "body2": f"사용자 {user_id}의 두 번째 메시지입니다",
            "body3": f"사용자 {user_id}의 세 번째 메시지입니다"
        }

        # 비동기 영상 생성 요청 (배치 작업)
        form_data = aiohttp.FormData()
        form_data.add_field('user_email', user_data["email"])
        form_data.add_field('content_data', json.dumps(content_data, ensure_ascii=False))
        form_data.add_field('music_mood', 'bright')
        form_data.add_field('text_position', 'bottom')
        form_data.add_field('use_test_files', 'true')

        start_time = time.time()

        async with session.post(f"{BASE_URL}/generate-video-async", data=form_data) as response:
            result = await response.json()

            if result.get("status") == "success":
                job_id = result["job_id"]
                print(f"✅ 사용자 {user_id} 작업 큐 추가 성공: {job_id}")

                # 작업 완료까지 대기 (상태 폴링)
                poll_count = 0
                max_polls = 60  # 최대 5분 대기

                while poll_count < max_polls:
                    await asyncio.sleep(5)  # 5초마다 상태 확인
                    poll_count += 1

                    async with session.get(f"{BASE_URL}/job-status/{job_id}") as status_response:
                        if status_response.status == 200:
                            status_data = await status_response.json()
                            current_status = status_data.get("status", "unknown")

                            print(f"ℹ️ 사용자 {user_id} 상태 ({poll_count}번째): {current_status}")

                            if current_status in ["completed", "failed"]:
                                end_time = time.time()
                                duration = end_time - start_time

                                if current_status == "completed":
                                    print(f"🎉 사용자 {user_id} 영상 생성 완료 ({duration:.1f}초)")
                                    result_data = status_data.get('result', {})
                                    print(f"   📁 영상 경로: {result_data.get('video_path', 'N/A')}")
                                    return {"user_id": user_id, "status": "success", "duration": duration, "job_id": job_id}
                                else:
                                    error_msg = status_data.get('error_message', 'Unknown error')
                                    print(f"❌ 사용자 {user_id} 영상 생성 실패: {error_msg}")
                                    return {"user_id": user_id, "status": "failed", "duration": duration, "job_id": job_id, "error": error_msg}
                        else:
                            print(f"⚠️ 사용자 {user_id} 상태 조회 실패: HTTP {status_response.status}")

                # 시간 초과
                print(f"⏰ 사용자 {user_id} 작업 시간 초과 (5분)")
                return {"user_id": user_id, "status": "timeout", "job_id": job_id}
            else:
                print(f"❌ 사용자 {user_id} 작업 요청 실패: {result}")
                return {"user_id": user_id, "status": "request_failed"}

    except Exception as e:
        print(f"💥 사용자 {user_id} 테스트 중 예외 발생: {e}")
        return {"user_id": user_id, "status": "exception", "error": str(e)}

async def test_concurrent_video_generation():
    """동시 영상 생성 테스트"""
    print("🚀 동시성 테스트 시작")
    print(f"📊 테스트 사용자 수: {len(TEST_USERS)}")
    print(f"🕒 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    async with aiohttp.ClientSession() as session:
        # 모든 사용자의 영상 생성을 동시에 시작
        tasks = []
        for i, user_data in enumerate(TEST_USERS, 1):
            task = create_test_video(session, user_data, i)
            tasks.append(task)

        # 모든 작업 완료까지 대기
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()

        # 결과 분석
        print("\n" + "=" * 60)
        print("📊 동시성 테스트 결과")
        print(f"🕒 총 소요 시간: {end_time - start_time:.1f}초")
        print("=" * 60)

        success_count = 0
        failed_count = 0

        for result in results:
            if isinstance(result, dict):
                if result["status"] == "success":
                    success_count += 1
                    print(f"✅ 사용자 {result['user_id']}: 성공 ({result['duration']:.1f}초)")
                else:
                    failed_count += 1
                    print(f"❌ 사용자 {result['user_id']}: 실패 ({result['status']})")
            else:
                failed_count += 1
                print(f"💥 예외 발생: {result}")

        print("=" * 60)
        print(f"📈 성공: {success_count}개, 실패: {failed_count}개")

        if success_count == len(TEST_USERS):
            print("🎉 동시성 테스트 성공! 모든 사용자가 독립적으로 영상을 생성했습니다.")
        else:
            print("⚠️ 일부 사용자의 영상 생성이 실패했습니다.")

async def test_folder_isolation():
    """폴더 격리 테스트"""
    print("\n🔍 폴더 격리 상태 확인")

    async with aiohttp.ClientSession() as session:
        # 폴더 통계 조회
        async with session.get(f"{BASE_URL}/folder-stats") as response:
            if response.status == 200:
                stats = await response.json()
                folder_stats = stats.get("folder_stats", {})

                print(f"📁 uploads 폴더: {folder_stats.get('uploads_folders', 0)}개")
                print(f"📁 output 폴더: {folder_stats.get('output_folders', 0)}개")
                print(f"💾 uploads 크기: {folder_stats.get('total_uploads_size', 0)} bytes")
                print(f"💾 output 크기: {folder_stats.get('total_output_size', 0)} bytes")
            else:
                print("❌ 폴더 통계 조회 실패")

        # 정리 스케줄러 상태 조회
        async with session.get(f"{BASE_URL}/cleanup-status") as response:
            if response.status == 200:
                status = await response.json()
                cleanup_status = status.get("cleanup_status", {})

                print(f"🧹 정리 스케줄러 실행 중: {cleanup_status.get('is_running', False)}")
                print(f"🕒 정리 간격: {cleanup_status.get('cleanup_interval_hours', 0)}시간")
                print(f"📅 다음 정리: {cleanup_status.get('next_cleanup', 'N/A')}")
            else:
                print("❌ 정리 스케줄러 상태 조회 실패")

async def main():
    """메인 테스트 함수"""
    try:
        # 1. 서버 연결 확인
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/") as response:
                if response.status != 200:
                    print("❌ 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.")
                    return

        print("✅ 서버 연결 확인")

        # 2. 동시성 테스트 실행
        await test_concurrent_video_generation()

        # 3. 폴더 격리 상태 확인
        await test_folder_isolation()

        print("\n🎯 테스트 완료!")

    except Exception as e:
        print(f"💥 테스트 실행 중 오류: {e}")

if __name__ == "__main__":
    asyncio.run(main())