#!/bin/bash

# 릴스 영상 생성 API 테스트 스크립트 (test 폴더 파일 사용)
# 새로운 웹서비스 API 구조로 업데이트
# 서버 URL: zstus.synology.me:8097

API_URL="http://zstus.synology.me:8097"
TEST_DIR="./test"

echo "=== 릴스 영상 생성 API 테스트 (test 폴더 사용) ==="
echo "서버 URL: $API_URL"
echo

# 1. 서버 상태 확인
echo "1. 서버 상태 확인..."
curl -s "$API_URL/" | jq .
echo

# 2. 테스트 파일 확인 (새로운 구조)
echo "2. 테스트 파일 확인 (uploads 호환 구조)..."

# text.json 확인
if [ ! -f "$TEST_DIR/text.json" ]; then
    echo "❌ text.json 파일이 없습니다."
    exit 1
fi
echo "✅ text.json 발견"

# bgm 폴더 확인 (음악 파일은 bgm 폴더에서 랜덤 선택)
if [ ! -d "./bgm/bright" ]; then
    echo "❌ bgm/bright 폴더가 없습니다."
    exit 1
fi
echo "✅ bgm 폴더 시스템 사용 (음악은 성격별 랜덤 선택)"

# 번호 순서 이미지 파일들 확인 (1.png, 2.png, 3.png, 4.png 등)
echo "✅ 이미지 파일 목록:"
FOUND_IMAGES=0
for i in {1..10}; do
    for ext in png jpg jpeg gif webp bmp; do
        if [ -f "$TEST_DIR/$i.$ext" ]; then
            echo "   $i.$ext 발견"
            FOUND_IMAGES=$((FOUND_IMAGES + 1))
            break
        fi
    done
done

if [ $FOUND_IMAGES -eq 0 ]; then
    echo "❌ 번호 순서 이미지 파일이 없습니다 (1.png, 2.jpg 등)."
    exit 1
fi

echo "📊 총 $FOUND_IMAGES 개의 이미지 파일 발견"
echo

# 3. JSON 데이터 미리보기
echo "3. JSON 데이터 미리보기..."
echo "$(cat "$TEST_DIR/text.json" | jq .)"
echo

# 4. 새로운 웹서비스 API 호출 (test 폴더 모드)
echo "4. 웹서비스 API 호출 중 (test 폴더 모드)..."
echo "⏳ test 폴더의 파일들을 uploads 폴더로 복사하여 영상 생성..."
echo "⏳ 영상 생성에는 시간이 걸립니다. 잠시만 기다려주세요..."
echo

curl -X POST "$API_URL/generate-video" \
  -F "use_test_files=true" \
  -H "Accept: application/json" | jq .

echo
echo "=== 테스트 완료 ==="
echo "📝 참고: use_test_files=true 모드는 test 폴더의 파일들을 자동으로 uploads 폴더로 복사하여 사용합니다."