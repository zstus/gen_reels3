#!/bin/bash

# 간단한 단일 이미지 테스트 (가장 안정적인 방법)

API_URL="http://zstus.synology.me:8097"
TEST_DIR="./test"

echo "=== 간단한 단일 이미지 테스트 ==="

# JSON 데이터
CONTENT_DATA='{
    "title": "간단한 테스트 제목",
    "body1": "첫 번째 본문 내용입니다.",
    "body2": "두 번째 본문 내용입니다."
}'

# 단일 안정적인 이미지 (via.placeholder.com)
IMAGE_URLS='["https://via.placeholder.com/1920x1080/FF5733/FFFFFF?text=Simple+Test"]'

echo "1. 서버 상태 확인..."
curl -s "$API_URL/" | jq .
echo

echo "2. 간단한 영상 생성 테스트..."
echo "⏳ 처리 중..."
echo

curl -X POST "$API_URL/generate-video" \
  -F "content_data=$CONTENT_DATA" \
  -F "music_mood=bright" \
  -F "image_urls=$IMAGE_URLS" \
  -H "Accept: application/json" | jq .

echo
echo "=== 간단 테스트 완료 ==="