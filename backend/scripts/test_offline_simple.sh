#!/bin/bash

# 간단한 테스트 파일 모드 테스트

API_URL="http://zstus.synology.me:8097"
TEST_DIR="./test"

echo "=== test 폴더 사용 테스트 ==="

# test 폴더의 text.json 사용
CONTENT_DATA=$(cat "$TEST_DIR/text.json")

echo "1. 서버 상태 확인..."
curl -s "$API_URL/" | jq .
echo

echo "2. test 폴더 파일들로 영상 생성..."
echo "⏳ 처리 중..."
echo

curl -X POST "$API_URL/generate-video" \
  -F "content_data=$CONTENT_DATA" \
  -F "music_mood=bright" \
  -F "use_test_files=true" \
  -H "Accept: application/json" | jq .

echo
echo "=== test 파일 모드 테스트 완료 ==="