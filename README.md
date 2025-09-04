# 릴스 영상 생성 서비스 (Reels Video Generator)

FastAPI와 React를 사용한 전체 스택 릴스 영상 생성 서비스입니다. JSON 텍스트 데이터를 세로형 릴스 영상으로 자동 변환하고, 웹 인터페이스를 통해 쉽게 사용할 수 있습니다.

## 📋 프로젝트 개요

### 주요 기능
- **웹 인터페이스**: React 기반 사용자 친화적 웹 UI
- **Google OAuth**: 구글 계정 로그인 시스템
- **대본 작성**: 제목 + 최대 8개 대사 입력 (이모지 지원)
- **이미지 업로드**: 드래그 앤 드롭으로 쉬운 이미지 업로드
- **음악 선택**: BGM 폴더에서 음악 선택 및 미리듣기
- **영상 생성**: 414x896 세로형 릴스 영상 자동 생성
- **영상 다운로드**: 브라우저에서 직접 다운로드

### 기술 스택
- **Frontend**: React + TypeScript + Material-UI
- **Backend**: FastAPI + Python 3.8+
- **영상 처리**: MoviePy
- **이미지 처리**: PIL (Pillow)
- **TTS**: Google Text-to-Speech (gTTS)
- **인프라**: Nginx (리버스 프록시)
- **서버**: Ubuntu + uvicorn

## 🏗️ 프로젝트 구조

```
ubt_genReels/
├── frontend/                     # React 프론트엔드
│   ├── public/
│   │   └── index.html            # 메인 HTML (Google OAuth 포함)
│   ├── src/
│   │   ├── components/           # React 컴포넌트
│   │   │   ├── LoginButton.tsx   # Google OAuth 로그인
│   │   │   ├── ContentStep.tsx   # 대본 작성 단계
│   │   │   ├── ImageStep.tsx     # 이미지 업로드 단계
│   │   │   ├── MusicStep.tsx     # 음악 선택 단계
│   │   │   └── GenerateStep.tsx  # 영상 생성 및 다운로드
│   │   ├── pages/
│   │   │   └── MainApp.tsx       # 메인 애플리케이션
│   │   ├── contexts/
│   │   │   └── AuthContext.tsx   # 인증 상태 관리
│   │   ├── services/
│   │   │   └── api.ts            # API 통신
│   │   ├── types/
│   │   │   └── index.ts          # TypeScript 타입 정의
│   │   ├── App.tsx               # 앱 루트 컴포넌트
│   │   └── index.tsx             # React 진입점
│   ├── package.json              # NPM 의존성 및 스크립트
│   └── .env                      # 환경 변수 (Google OAuth)
├── backend/                      # FastAPI 백엔드 서버
│   ├── main.py                   # FastAPI 메인 서버 애플리케이션
│   ├── video_generator.py        # 릴스 영상 생성 핵심 로직
│   ├── bgm/                      # 성격별 배경음악 시스템
│   │   ├── bright/               # 밝은 음악들
│   │   ├── calm/                 # 차분한 음악들
│   │   ├── romantic/             # 로맨틱한 음악들
│   │   ├── sad/                  # 슬픈 음악들
│   │   └── suspense/             # 긴장감 있는 음악들
│   ├── test/                     # 테스트 파일들
│   ├── uploads/                  # 임시 파일 처리 폴더
│   └── output_videos/            # 생성된 영상 저장 폴더
├── server.txt                    # 서버 설정 가이드
└── README.md                     # 이 파일 (프로젝트 문서)
```

## API 사용법

### 엔드포인트: POST /generate-video

**요청 파라미터:**
- `content_data` (form-data): JSON 형태의 텍스트 데이터
- `background_music` (file): MP3 배경음악 파일
- `image_url` (form-data): 배경 이미지 URL

**JSON 데이터 형식:**
```json
{
  "title": "영상 제목",
  "body1": "첫 번째 내용",
  "body2": "두 번째 내용",
  "body3": "세 번째 내용",
  ...
}
```

**응답 형식:**
```json
{
  "status": "success",
  "message": "Video generated successfully",
  "video_path": "output_videos/reels_abc12345.mp4"
}
```

## 설치 및 실행

1. **서버 설치**: `exec.txt` 파일의 매뉴얼을 따라 Ubuntu 서버에서 실행

2. **로컬 테스트**: `backend/test_client.py`를 사용하여 API 테스트

## 예시 사용

```bash
# 서버 실행
cd /zstus/backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000

# curl을 이용한 테스트
curl -X POST "http://localhost:8000/generate-video" \
-F "content_data='{\"title\": \"테스트\", \"body1\": \"내용1\"}'" \
-F "background_music=@music.mp3" \
-F "image_url=https://example.com/image.jpg"
```

## 주요 특징

- **Ken Burns 효과**: 배경 이미지가 확대/축소/이동하면서 영상처럼 보임
- **텍스트 오버레이**: 검은 외곽선이 있는 흰색 텍스트로 가독성 향상
- **자동 줄바꿈**: 긴 텍스트를 자동으로 여러 줄로 분할
- **음악 동기화**: 배경음악을 영상 길이에 맞게 조정

## 필요 조건

- Ubuntu 18.04 이상
- Python 3.8 이상
- FFmpeg
- 충분한 디스크 공간 (영상 파일 저장용)

## 문제 해결

자세한 문제 해결 방법은 `exec.txt` 파일의 "문제 해결" 섹션을 참고하세요.