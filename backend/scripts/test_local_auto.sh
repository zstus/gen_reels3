#!/bin/bash

# test 폴더의 파일을 직접 사용하는 테스트 (새로운 API 구조)

API_URL="http://zstus.synology.me:8097"
TEST_DIR="./test"

echo "=== test 폴더 직접 사용 테스트 ==="

# JSON 데이터 읽기
CONTENT_DATA=$(cat "$TEST_DIR/text.json")

echo "1. 서버 상태 확인..."
curl -s "$API_URL/" | jq .
echo

echo "2. test 파일을 직접 사용하여 영상 생성..."
echo "⏳ 처리 중..."
echo

curl -X POST "$API_URL/generate-video" \
  -F "content_data=$CONTENT_DATA" \
  -F "music_mood=bright" \
  -F "use_test_files=true" \
  -H "Accept: application/json" | jq .

echo
echo "=== 직접 사용 테스트 완료 ==="
