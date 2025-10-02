#!/bin/bash

echo "🚀 와이프 전환 효과 테스트 실행"
echo "==============================="

# 현재 디렉토리로 이동
cd "$(dirname "$0")"

# Python 가상환경 활성화 (있다면)
if [ -d "venv" ]; then
    echo "📦 가상환경 활성화"
    source venv/bin/activate
fi

# Python 경로 설정
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

echo "🔍 Python 버전:"
python3 --version

echo ""
echo "🧪 와이프 전환 테스트 시작..."
python3 test_wipe_transition.py

echo ""
echo "📋 생성된 로그 파일들:"
ls -la *.log 2>/dev/null || echo "로그 파일이 없습니다."

echo ""
echo "📁 생성된 영상 파일들:"
ls -la output_videos/*.mp4 2>/dev/null || echo "영상 파일이 없습니다."

echo ""
echo "✅ 테스트 완료!"