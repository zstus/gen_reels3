# YouTube 테스트 비디오 목록

YouTube 자막 추출 기능을 테스트할 때 사용할 수 있는 자막이 있는 비디오들입니다.

## 📺 자막이 있는 YouTube 비디오 목록

### 🇰🇷 한국어 자막이 있는 비디오
1. **PSY - Gangnam Style**
   - URL: `https://www.youtube.com/watch?v=9bZkp7q19f0`
   - 자막: 한국어, 영어, 기타 다국어
   - 설명: 세계적으로 유명한 K-POP 비디오

2. **BTS - Dynamite**
   - URL: `https://www.youtube.com/watch?v=gdZLi9oWNZg`
   - 자막: 한국어, 영어
   - 설명: 방탄소년단의 인기 곡

### 🇺🇸 영어 자막이 있는 비디오
1. **Me at the zoo (첫 번째 YouTube 비디오)**
   - URL: `https://www.youtube.com/watch?v=jNQXAC9IVRw`
   - 자막: 영어
   - 설명: YouTube 역사상 첫 번째 업로드된 비디오

2. **TED Talks**
   - URL: `https://www.youtube.com/watch?v=ZSHk0I9XHLE`
   - 자막: 영어, 다국어
   - 설명: 교육적인 내용으로 자막이 잘 되어있음

### 🏢 기업/교육 채널 비디오
1. **Google I/O 발표**
   - URL: `https://www.youtube.com/watch?v=lyRPyRKHO8M`
   - 자막: 영어
   - 설명: 기술 발표 영상

2. **국가기관 공식 채널**
   - 대부분 자막 제공
   - 교육적 내용이 많음

## ❌ 자막이 없는 비디오 유형

### 피해야 할 비디오들
1. **개인 브이로그**: 자막이 없는 경우가 많음
2. **음악 비디오**: 가사가 있어도 자막이 없는 경우
3. **라이브 스트림**: 실시간 영상은 자막이 없음
4. **오래된 비디오**: 2010년 이전 비디오는 자막이 없는 경우가 많음
5. **비공개/제한된 비디오**: 접근 불가

## 🧪 테스트 방법

### 1. 직접 테스트
```bash
# 테스트 스크립트 실행
python3 test_youtube_api.py

# 개별 비디오 테스트
python3 -c "from main import get_youtube_transcript; print(get_youtube_transcript('jNQXAC9IVRw')[:200])"
```

### 2. API 테스트
```bash
curl -X POST "http://localhost:8097/extract-reels-from-url" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=jNQXAC9IVRw"}'
```

### 3. 자막 확인 방법
YouTube 웹사이트에서 비디오를 재생한 후:
1. 설정(톱니바퀴) 버튼 클릭
2. "자막/CC" 옵션 확인
3. 사용 가능한 언어 확인

## 💡 에러 해결

### "자막이 없습니다" 에러 시
1. 다른 비디오로 시도
2. 위 목록의 검증된 비디오 사용
3. YouTube에서 직접 자막 확인

### "비디오를 찾을 수 없습니다" 에러 시
1. URL 형식 확인
2. 비디오가 공개 상태인지 확인
3. 지역 제한이 없는지 확인

### "API 요청 한도 초과" 에러 시
1. 10-30초 대기 후 재시도
2. 다른 비디오로 테스트
3. 서버 재시작