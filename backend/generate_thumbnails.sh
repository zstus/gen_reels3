#!/bin/bash

# 썸네일 일괄 생성 스크립트

echo "🎬 비디오 썸네일 일괄 생성 도구"
echo "================================="

# 현재 스크립트 위치로 이동
cd "$(dirname "$0")"

# Python 가상환경 활성화 (있는 경우)
if [ -d "venv" ]; then
    echo "📦 Python 가상환경 활성화..."
    source venv/bin/activate
fi

# Python 버전 확인
echo "🐍 Python 버전 확인..."
python3 --version

# 필요한 패키지 확인
echo "📋 필요한 패키지 확인..."
python3 -c "import moviepy, PIL; print('✅ 필요한 패키지가 모두 설치되어 있습니다.')" 2>/dev/null || {
    echo "❌ 필요한 패키지가 설치되어 있지 않습니다."
    echo "💡 다음 명령어로 설치하세요:"
    echo "   pip install moviepy pillow"
    exit 1
}

# 비디오 디렉토리 확인
if [ ! -d "assets/videos" ]; then
    echo "❌ assets/videos 디렉토리가 존재하지 않습니다."
    exit 1
fi

# 비디오 파일 개수 확인
video_count=$(find assets/videos -type f \( -iname "*.mp4" -o -iname "*.mov" -o -iname "*.avi" -o -iname "*.webm" -o -iname "*.mkv" \) | wc -l)
echo "📊 발견된 비디오 파일: ${video_count}개"

if [ "$video_count" -eq 0 ]; then
    echo "⚠️  처리할 비디오 파일이 없습니다."
    exit 0
fi

# 사용자 옵션 확인
echo ""
echo "옵션을 선택하세요:"
echo "1) 새로운 썸네일만 생성 (기본, 추천)"
echo "2) 모든 썸네일 강제 재생성"
echo "3) 대상 파일만 확인 (실제 생성하지 않음)"
echo ""
read -p "선택 (1-3, 기본값: 1): " choice

case $choice in
    2)
        echo "🔄 모든 썸네일을 강제로 재생성합니다..."
        python3 generate_thumbnails_batch.py --force
        ;;
    3)
        echo "🔍 대상 파일들만 확인합니다..."
        python3 generate_thumbnails_batch.py --dry-run
        ;;
    *)
        echo "🆕 새로운 썸네일만 생성합니다..."
        python3 generate_thumbnails_batch.py
        ;;
esac

echo ""
echo "🎉 작업이 완료되었습니다!"
echo "📁 썸네일 파일들은 assets/videos/ 폴더에 저장됩니다."
echo "📋 자세한 로그는 thumbnail_batch.log 파일을 확인하세요."