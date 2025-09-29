#!/bin/bash

echo "🔍 와이프 전환 효과 종합 디버깅 시스템"
echo "======================================"

# 현재 디렉토리로 이동
cd "$(dirname "$0")"

# Python 가상환경 활성화 (있다면)
if [ -d "venv" ]; then
    echo "📦 가상환경 활성화"
    source venv/bin/activate
fi

# Python 경로 설정
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

echo ""
echo "🧹 기존 로그 파일 정리..."
rm -f main_transition_*.log worker_transition_*.log transition_debug_*.log wipe_test_*.log 2>/dev/null

echo ""
echo "🧪 와이프 전환 테스트 실행..."
python3 test_wipe_transition.py

echo ""
echo "📊 로그 분석 실행..."
python3 analyze_wipe_logs.py

echo ""
echo "📁 생성된 파일들:"
echo "--- 로그 파일 ---"
ls -la *.log 2>/dev/null || echo "로그 파일이 없습니다."

echo ""
echo "--- 영상 파일 ---"
ls -la output_videos/*.mp4 2>/dev/null || echo "영상 파일이 없습니다."

echo ""
echo "💡 사용법:"
echo "1. 위의 로그 분석 결과를 확인하세요"
echo "2. 문제가 발견되면 해당 로그 파일을 직접 열어서 상세 내용을 확인하세요"
echo "3. 웹 인터페이스에서도 와이프를 선택하여 테스트해보세요"

echo ""
echo "✅ 디버깅 완료!"