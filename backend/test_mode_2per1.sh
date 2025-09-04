#!/bin/bash

# Mode 1 테스트: body 2개당 이미지 1개 (기존 방식)

API_URL="http://localhost:8080"
TEST_DIR="./test"

echo "=== Mode 1 테스트: body 2개당 이미지 1개 ==="

# JSON 데이터 읽기
CONTENT_DATA=$(cat "$TEST_DIR/text.json")

echo "1. 서버 상태 확인..."
curl -s "$API_URL/" | jq .
echo

echo "2. Mode 1 (2_per_image) 테스트..."
echo "⏳ 처리 중..."
echo

curl -X POST "$API_URL/generate-video" \
  -F "content_data=$CONTENT_DATA" \
  -F "music_mood=bright" \
  -F "image_allocation_mode=2_per_image" \
  -F "use_test_files=true" \
  -H "Accept: application/json" | jq .

echo
echo "=== Mode 1 테스트 완료 ==="