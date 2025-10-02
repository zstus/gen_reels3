#!/usr/bin/env python3
"""
와이프 전환 효과 로그 분석 스크립트
"""

import os
import glob
import re
from datetime import datetime

def analyze_logs():
    """생성된 로그 파일들을 분석하여 문제점 파악"""
    print("🔍 와이프 전환 효과 로그 분석 시작")
    print("=" * 60)

    # 현재 디렉토리의 모든 로그 파일 찾기
    log_patterns = [
        "main_transition_*.log",
        "worker_transition_*.log",
        "transition_debug_*.log",
        "wipe_test_*.log"
    ]

    all_log_files = []
    for pattern in log_patterns:
        files = glob.glob(pattern)
        all_log_files.extend(files)

    if not all_log_files:
        print("❌ 분석할 로그 파일이 없습니다.")
        print("   1. 먼저 와이프 전환을 선택하여 영상을 생성해보세요.")
        print("   2. 또는 python3 test_wipe_transition.py 를 실행해보세요.")
        return

    print(f"📋 발견된 로그 파일: {len(all_log_files)}개")
    for log_file in sorted(all_log_files):
        file_size = os.path.getsize(log_file)
        print(f"   - {log_file} ({file_size} bytes)")

    print("\n" + "=" * 60)
    print("📊 로그 분석 결과")
    print("=" * 60)

    # 각 로그 파일 분석
    for log_file in sorted(all_log_files):
        print(f"\n🔍 분석 중: {log_file}")
        print("-" * 40)

        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 주요 키워드 검색
            keywords = [
                ('transition_effect', '전환 효과 파라미터'),
                ('wipe', '와이프 설정'),
                ('crossfade', '크로스페이드 설정'),
                ('none', '전환 효과 없음 설정'),
                ('와이프 전환 효과 적용', '와이프 함수 호출'),
                ('apply_smart_wipe_transitions', '와이프 함수 실행'),
                ('와이프 마스크 생성', '마스크 생성'),
                ('오류', '에러 발생'),
                ('실패', '실패 발생'),
                ('Exception', '예외 발생')
            ]

            found_issues = []
            found_successes = []

            for keyword, description in keywords:
                matches = re.findall(f'.*{keyword}.*', content, re.IGNORECASE)
                if matches:
                    if keyword in ['오류', '실패', 'Exception']:
                        found_issues.extend([(description, match.strip()) for match in matches])
                    else:
                        found_successes.extend([(description, match.strip()) for match in matches])

            # 성공적인 단계들
            if found_successes:
                print("✅ 감지된 성공 단계:")
                for desc, match in found_successes[:5]:  # 처음 5개만 표시
                    print(f"   - {desc}: {match[:100]}...")

            # 문제점들
            if found_issues:
                print("❌ 감지된 문제점:")
                for desc, match in found_issues:
                    print(f"   - {desc}: {match[:100]}...")

            # transition_effect 값 추출
            transition_values = re.findall(r"transition_effect[:\s=]*['\"]?(\w+)['\"]?", content, re.IGNORECASE)
            if transition_values:
                print(f"🎯 감지된 transition_effect 값: {list(set(transition_values))}")

        except Exception as e:
            print(f"❌ 로그 파일 읽기 실패: {e}")

    # 종합 진단
    print("\n" + "=" * 60)
    print("🏥 종합 진단")
    print("=" * 60)

    # 모든 로그에서 transition_effect 값 수집
    all_transition_values = []
    wipe_function_called = False
    wipe_function_executed = False

    for log_file in all_log_files:
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # transition_effect 값 수집
            values = re.findall(r"transition_effect[:\s=]*['\"]?(\w+)['\"]?", content, re.IGNORECASE)
            all_transition_values.extend(values)

            # 와이프 함수 호출 확인
            if 'apply_smart_wipe_transitions' in content:
                wipe_function_called = True

            # 와이프 함수 실행 확인
            if '와이프 전환 효과 적용' in content or 'wipe 전환' in content:
                wipe_function_executed = True

        except:
            pass

    # 진단 결과
    unique_values = list(set(all_transition_values))
    print(f"📊 전체 transition_effect 값: {unique_values}")

    if 'wipe' in unique_values:
        print("✅ 'wipe' 값이 올바르게 전달됨")
    else:
        print("❌ 'wipe' 값이 전달되지 않음 - 프론트엔드/API 문제 가능성")

    if wipe_function_called:
        print("✅ 와이프 함수가 호출됨")
    else:
        print("❌ 와이프 함수가 호출되지 않음 - 조건문 문제 가능성")

    if wipe_function_executed:
        print("✅ 와이프 효과가 실행됨")
    else:
        print("❌ 와이프 효과가 실행되지 않음 - 함수 내부 문제 가능성")

    # 권장 사항
    print("\n💡 권장 사항:")
    if 'wipe' not in unique_values:
        print("   1. 프론트엔드에서 transition_effect 값이 올바르게 설정되는지 확인")
        print("   2. API 요청에서 올바른 FormData가 전송되는지 확인")
    elif not wipe_function_called:
        print("   1. video_generator.py의 조건문 (transition_effect == 'wipe') 확인")
        print("   2. 문자열 비교 시 대소문자나 공백 문제 확인")
    elif not wipe_function_executed:
        print("   1. apply_smart_wipe_transitions 함수 내부 로직 확인")
        print("   2. 클립 개수나 미디어 파일 조건 확인")

    print(f"\n📋 상세 로그는 위의 {len(all_log_files)}개 파일을 참조하세요.")

if __name__ == "__main__":
    analyze_logs()