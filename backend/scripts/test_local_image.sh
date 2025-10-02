#!/bin/bash

# 로컬 이미지 파일을 사용한 테스트 (가장 안정적)
# 이미지를 로컬에서 임시 웹서버로 제공

API_URL="http://zstus.synology.me:8097"
TEST_DIR="./test"

echo "=== 로컬 이미지 파일 테스트 ==="

# 로컬 이미지 파일이 있는지 확인
if [ -f "$TEST_DIR/IMG_8756.jpg" ]; then
    echo "✅ 로컬 이미지 파일 발견: $TEST_DIR/IMG_8756.jpg"
    
    # Python 간단한 웹서버 시작 (백그라운드)
    echo "임시 웹서버 시작 중..."
    cd "$TEST_DIR"
    python3 -m http.server 8888 > /dev/null 2>&1 &
    SERVER_PID=$!
    cd ..
    
    # 서버 시작 대기
    sleep 2
    
    # 로컬 이미지 URL
    LOCAL_IMAGE_URL="http://localhost:8888/IMG_8756.jpg"
    IMAGE_URLS="[\"$LOCAL_IMAGE_URL\", \"https://via.placeholder.com/1920x1080/33FF57/FFFFFF?text=Backup+Image\"]"
    
    echo "로컬 이미지 URL: $LOCAL_IMAGE_URL"
else
    echo "⚠️  로컬 이미지 없음. placeholder 이미지만 사용"
    IMAGE_URLS='["https://via.placeholder.com/1920x1080/FF5733/FFFFFF?text=No+Local+Image"]'
fi

# JSON 데이터
CONTENT_DATA='{
    "title": "로컬 이미지 테스트",
    "body1": "첫 번째 내용 (로컬 이미지)",
    "body2": "두 번째 내용 (로컬 이미지)"
}'

echo
echo "영상 생성 테스트 중..."

curl -X POST "$API_URL/generate-video" \
  -F "content_data=$CONTENT_DATA" \
  -F "background_music=@$TEST_DIR/Gil Kita - A Random Encounter.mp3" \
  -F "image_urls=$IMAGE_URLS" \
  -H "Accept: application/json" | jq .

# 임시 웹서버 종료
if [ ! -z "$SERVER_PID" ]; then
    kill $SERVER_PID 2>/dev/null
    echo "임시 웹서버 종료"
fi

echo
echo "=== 로컬 이미지 테스트 완료 ==="