#!/bin/bash

# 완전 오프라인 테스트 (외부 이미지 URL 없이)
# 기본 생성 이미지만 사용

API_URL="http://zstus.synology.me:8097"
TEST_DIR="./test"

echo "=== 완전 오프라인 테스트 ==="
echo "외부 인터넷 연결 없이 기본 생성 이미지 사용"
echo

# 더미 이미지 URL (실제로는 다운로드되지 않고 fallback 이미지가 생성됨)
IMAGE_URLS='["http://offline-test/image1", "http://offline-test/image2", "http://offline-test/image3"]'

# 간단한 JSON 데이터
CONTENT_DATA='{
    "title": "오프라인 테스트 📱",
    "body1": "첫 번째 내용입니다 🎬",
    "body2": "두 번째 내용 (다른 색상 배경)",
    "body3": "세 번째 내용 (또 다른 색상)",
    "body4": "네 번째 내용 (색상 순환) ✨"
}'

echo "1. 서버 상태 확인..."
curl -s "$API_URL/" | jq .
echo

echo "2. 오프라인 영상 생성 중..."
echo "⏳ 기본 이미지 생성 모드로 처리됩니다..."
echo

curl -X POST "$API_URL/generate-video" \
  -F "content_data=$CONTENT_DATA" \
  -F "background_music=@$TEST_DIR/Gil Kita - A Random Encounter.mp3" \
  -F "image_urls=$IMAGE_URLS" \
  -H "Accept: application/json" | jq .

echo
echo "=== 오프라인 테스트 완료 ==="
echo "📝 결과: 각 이미지마다 다른 색상의 기본 배경이 생성되었습니다"