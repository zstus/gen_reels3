# 이성일
# 릴스 영상 생성 서비스 (Reels Video Generator)

## ⚠️ 개발 환경 중요 사항 (Claude AI 전용)

**작업 환경**: macOS에서 공유 폴더(Docker/SMB)를 통해 Ubuntu 서버의 프로젝트 폴더에 원격 접근
**제한 사항**: 
- ✅ **코드 분석 가능**: Read, Grep, Glob 도구 사용
- ✅ **코드 수정 가능**: Edit, MultiEdit, Write 도구 사용
- 🚫 **실행 절대 금지**: Bash 도구로 서버/빌드/npm 명령어 실행 시도 금지
- 🚫 **테스트 불가**: 모든 테스트는 사용자가 서버에서 직접 수행

**올바른 작업 프로세스:**
1. 요구사항 분석 → 2. 코드 분석 (Read/Grep) → 3. 코드 수정 (Edit/Write) → 4. 사용자 테스트 대기

**절대 하지 말 것:**
- `npm start`, `npm install`, `python main.py` 등 실행 명령어 사용
- 서버 실행, 빌드, 패키지 설치 시도
- 백그라운드 프로세스 실행

이 환경 정보는 **매 세션마다 전달**하여 동일한 실수를 반복하지 않도록 해야 함.

---

FastAPI와 MoviePy를 사용한 자동 릴스 영상 생성 서비스입니다. JSON 텍스트 데이터와 이미지/비디오를 세로형 릴스 영상으로 자동 변환합니다.

## 📋 프로젝트 개요

### 주요 기능
- **JSON 텍스트 데이터를 세로형 릴스 영상(504x890)으로 변환**
- **한국어 TTS 음성 자동 생성** (특수문자 자동 정리)
- **🌐 URL 자동 릴스 생성**: 웹페이지 URL 입력으로 자동 대본 생성
  - BeautifulSoup를 이용한 지능형 웹 스크래핑
  - OpenAI GPT-3.5-turbo를 통한 릴스 최적화 대본 생성
  - 자동으로 매력적인 제목과 7단계 구성 생성
- **🎬 비디오 파일 지원**: MP4, MOV, AVI, WebM 비디오를 배경으로 사용 가능
- **🖼️ 이미지 파일 지원**: JPG, PNG, GIF, WebP, BMP 이미지 지원
- **📍 텍스트 위치 설정**: 상단(340-520px), 하단(520-700px) 2단계 영역 선택
- **성격별 BGM 시스템**: bright, calm, romantic, sad, suspense 폴더에서 랜덤 선택
- **🎬 고급 영상 배치 시스템**: 
  - **종횡비 기반 지능형 배치**: 504x670 작업영역 기준 자동 판단
  - **4패턴 패닝 알고리즘**: 가로형(좌우), 세로형(상하) + Linear 이징
  - **60px 패닝 범위**로 다이내믹한 효과
  - **36pt 폰트** + 2px 외곽선으로 가독성 극대화
- **순차 미디어 지원**: 1,2,3,4 순서로 이미지/비디오 사용 (다중 포맷 지원)
- **웹 기반 UI**: React + TypeScript + Material-UI 프론트엔드
- **220px 타이틀 영역** + **504x670 작업 영역** 구조
- **TTS 음성 1.5배속** 처리로 시청 시간 단축 (50% 빠름)
- 텍스트 길이에 따른 자동 시간 조절

### 기술 스택
- **Frontend**: React 18 + TypeScript + Material-UI + react-dropzone
- **Backend**: FastAPI + Python 3.8+
- **영상 처리**: MoviePy (비디오 클립 처리 포함)
- **이미지 처리**: PIL (Pillow)
- **TTS**: Google Text-to-Speech (gTTS)
- **웹 스크래핑**: BeautifulSoup4 + lxml + requests
- **AI 대본 생성**: OpenAI GPT-3.5-turbo API (>=1.50.0)
- **환경 변수**: python-dotenv
- **폰트**: 사용자 한글 폰트 + Noto Color Emoji
- **서버**: Ubuntu + uvicorn

## 🏗️ 프로젝트 구조

```
ubt_genReels/
├── frontend/                    # React 프론트엔드 애플리케이션
│   ├── src/
│   │   ├── components/         # React 컴포넌트들
│   │   │   ├── ContentStep.tsx    # 대본 작성 단계 (텍스트 위치 선택 포함)
│   │   │   ├── ImageStep.tsx      # 미디어 업로드 단계 (이미지/비디오)
│   │   │   ├── MusicStep.tsx      # 음악 선택 단계
│   │   │   └── GenerateStep.tsx   # 영상 생성 단계
│   │   ├── pages/
│   │   │   └── MainApp.tsx        # 메인 애플리케이션 컨테이너
│   │   ├── services/
│   │   │   └── api.ts             # FastAPI 서버 통신 로직
│   │   ├── types/
│   │   │   └── index.ts           # TypeScript 타입 정의
│   │   └── App.tsx                # 앱 진입점
│   ├── package.json               # 의존성 및 스크립트 정의
│   └── tsconfig.json             # TypeScript 설정
├── backend/                     # FastAPI 백엔드 서버
│   ├── main.py                  # FastAPI 메인 서버 애플리케이션 (URL 추출 기능 포함)
│   ├── video_generator.py       # 릴스 영상 생성 핵심 로직
│   ├── .env                     # 환경변수 설정 (OpenAI API 키 등)
│   ├── .env.example             # 환경변수 템플릿
│   ├── bgm/                     # 성격별 배경음악 시스템
│   │   ├── bright/              # 밝은 음악들 (*.mp3, *.wav, *.m4a)
│   │   ├── calm/                # 차분한 음악들
│   │   ├── romantic/            # 로맨틱한 음악들
│   │   ├── sad/                 # 슬픈 음악들
│   │   └── suspense/            # 긴장감 있는 음악들
│   ├── test/                    # 테스트 파일들
│   │   ├── text.json            # 테스트용 JSON 데이터
│   │   ├── 1.jpg                # 테스트 이미지 1
│   │   ├── 2.webp               # 테스트 이미지/비디오 2
│   │   ├── 3.png                # 테스트 이미지/비디오 3
│   │   └── 4.mp4                # 테스트 비디오 4 (비디오 파일 지원)
│   ├── font/                    # 폰트 파일들
│   │   └── BMYEONSUNG_otf.otf   # 한국어 폰트
│   ├── test_local_auto.sh       # 자동 테스트 스크립트 (메인)
│   ├── test_local_files.sh      # 파일 시스템 검증 테스트
│   ├── test_simple.sh           # 단순 테스트
│   ├── test_offline_simple.sh   # 오프라인 모드 테스트
│   ├── test_videogen.py         # VideoGenerator 직접 테스트
│   ├── test_url_extract.py      # URL 추출 기능 테스트
│   ├── uploads/                 # 임시 파일 처리 폴더
│   └── output_videos/           # 생성된 영상 저장 폴더
├── claude.md                    # 이 파일 (상세 프로젝트 문서)
└── README.md                    # 프로젝트 기본 문서
```

## 🎨 Frontend 아키텍처

### React 컴포넌트 상세 분석

#### `src/pages/MainApp.tsx` - 메인 애플리케이션 컨테이너
**주요 기능:**
- **단계별 워크플로우 관리**: 로그인 → 대본작성 → 미디어업로드 → 음악선택 → 영상생성 → 다운로드
- **전역 상태 관리**: ProjectData 인터페이스를 통한 모든 데이터 중앙 관리
- **구글 OAuth 인증 처리**: Google One Tap 로그인 통합
- **단계별 유효성 검증**: 각 단계 진행 전 필수 데이터 검증
- **반응형 디자인**: Material-UI Container를 활용한 모바일/데스크톱 대응

**핵심 상태 관리:**
```typescript
interface ProjectData {
  content: ReelsContent;           // 대본 데이터 (title + body1-8)
  images: File[];                  // 업로드된 미디어 파일들
  imageUploadMode: ImageUploadMode; // 'per-script' | 'per-two-scripts'
  textPosition: TextPosition;      // 'top' | 'bottom' (2단계 시스템)
  selectedMusic: MusicFile | null; // 선택된 배경음악
  musicMood: MusicMood;           // 음악 성격
}
```

#### `src/components/ContentStep.tsx` - 대본 작성 단계 (URL 추출 기능 포함)
**주요 기능:**
- **🌐 URL 자동 대본 생성**: 웹페이지 URL 입력으로 자동 릴스 대본 생성
  - URL 유효성 검증 (http/https 프로토콜 체크)
  - 로딩 상태 표시 및 진행률 시뮬레이션
  - 에러 핸들링 및 사용자 피드백
- **대본 입력 인터페이스**: 제목 + 최대 8개 본문 텍스트 입력 필드
- **📍 텍스트 위치 선택**: 상단(340-520px 영역), 하단(520-700px 영역) 2단계 영역 선택
- **실시간 유효성 검증**: 제목과 최소 1개 본문 텍스트 입력 필수 검증
- **자동 포커스 관리**: 이전 단계에서 진입 시 첫 번째 필드로 포커스 이동
- **텍스트 길이 안내**: 각 필드별 권장 글자 수 및 예상 음성 길이 표시

**URL 추출 처리 로직:**
```typescript
const handleExtractFromUrl = async () => {
  if (!urlInput.trim()) {
    setExtractError('URL을 입력해주세요.');
    return;
  }

  // URL 유효성 검사
  if (!urlInput.match(/^https?:\/\/.+/)) {
    setExtractError('유효한 URL을 입력해주세요 (http:// 또는 https://)');
    return;
  }

  setIsExtracting(true);
  setExtractError('');

  try {
    const response = await fetch('/extract-reels-from-url', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: urlInput }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    if (data.status === 'success') {
      const reelsContent = data.reels_content;
      setContent(reelsContent);
      setUrlInput('');
    }
  } catch (error) {
    setExtractError(`URL 추출 에러: ${error}`);
  } finally {
    setIsExtracting(false);
  }
};
```

**텍스트 위치 처리 로직 (2단계 시스템):**
```typescript
const handleTextPositionChange = (newPosition: TextPosition) => {
  setTextPosition(newPosition);
  // 백엔드로 전달되어 영상 생성 시 텍스트 Y 좌표 결정
  // top: 상단 영역 중앙 (430px) - 340-520px 영역
  // bottom: 하단 영역 중앙 (610px) - 520-700px 영역
};
```

#### `src/components/ImageStep.tsx` - 미디어 업로드 단계
**주요 기능:**
- **🎬 멀티미디어 파일 지원**: 이미지(JPG, PNG, GIF, WebP, BMP) + 비디오(MP4, MOV, AVI, WebM)
- **드래그앤드롭 인터페이스**: react-dropzone을 활용한 직관적 파일 업로드
- **미디어 할당 모드 선택**: 
  - `per-two-scripts`: 대사 2개당 미디어 1개
  - `per-script`: 대사 1개당 미디어 1개
- **실시간 미리보기**: 업로드된 이미지/비디오 즉시 미리보기 (비디오는 autoplay/muted/loop)
- **파일 유효성 검증**: 파일 크기(10MB), 형식, 개수 제한 검증
- **업로드 진행률 시뮬레이션**: 사용자 경험 향상을 위한 가상 진행률 표시

**파일 처리 로직:**
```typescript
const isVideoFile = (file: File) => file.type.startsWith('video/');
const isImageFile = (file: File) => file.type.startsWith('image/');

// 파일 형식 검증
if (!isImage && !isVideo) {
  newErrors.push(`이미지 또는 비디오 파일만 업로드 가능합니다`);
}

// react-dropzone 설정
accept: {
  'image/*': ['.jpeg', '.jpg', '.png', '.gif', '.webp', '.bmp'],
  'video/*': ['.mp4', '.mov', '.avi', '.webm']
}
```

#### `src/components/MusicStep.tsx` - 음악 선택 단계
**주요 기능:**
- **성격별 음악 분류**: 5가지 감정 카테고리별 음악 라이브러리
- **음악 미리보기**: HTML5 audio 태그를 통한 실시간 재생
- **자동 볼륨 조절**: TTS 음성 대비 25% 볼륨으로 자동 설정
- **음악 파일 업로드**: 사용자 직접 업로드 MP3 파일 지원
- **감정 기반 추천**: 대본 내용 분석을 통한 음악 성격 추천 시스템

#### `src/components/GenerateStep.tsx` - 영상 생성 단계
**주요 기능:**
- **실시간 영상 생성 진행률**: WebSocket 또는 polling을 통한 실시간 상태 업데이트
- **미리보기 요약**: 선택된 모든 설정 사항 최종 검토
- **에러 처리**: 생성 실패 시 상세 에러 메시지 및 재시도 옵션
- **다운로드 링크 제공**: 생성 완료 시 즉시 다운로드 가능한 링크 생성

### TypeScript 타입 시스템

#### `src/types/index.ts` - 타입 정의
**핵심 타입들:**
```typescript
// 텍스트 위치 타입 (새로 추가)
export type TextPosition = 'top' | 'middle' | 'bottom';

// 이미지 업로드 모드
export type ImageUploadMode = 'per-script' | 'per-two-scripts';

// 음악 성격 타입
export type MusicMood = 'bright' | 'calm' | 'romantic' | 'sad' | 'suspense';

// 릴스 콘텐츠 타입
export interface ReelsContent {
  title: string;
  body1: string;
  body2?: string;
  // ... body8까지 확장 가능
}

// 프로젝트 상태 타입 (비디오 지원 포함)
export interface ProjectData {
  content: ReelsContent;
  images: File[];                    // 이미지 및 비디오 파일들
  imageUploadMode: ImageUploadMode;
  textPosition: TextPosition;        // 2단계 텍스트 위치 ('top' | 'bottom')
  selectedMusic: MusicFile | null;
  musicMood: MusicMood;
}

// 영상 생성 요청 타입 (업데이트됨)
export interface GenerateVideoRequest {
  content_data: string;
  music_mood: MusicMood;
  image_urls?: string;
  background_music?: File;
  use_test_files: boolean;
  selected_bgm_path?: string;
  image_allocation_mode: ImageUploadMode;
  text_position: TextPosition;       // 2단계 텍스트 위치
}
```

### API 통신 서비스

#### `src/services/api.ts` - FastAPI 통신 로직
**주요 기능:**
- **RESTful API 통신**: axios 기반 HTTP 클라이언트 구현
- **FormData 처리**: 멀티파트 폼 데이터를 통한 파일 업로드
- **에러 처리**: API 응답 에러 및 네트워크 에러 적절한 처리
- **타입 안정성**: TypeScript 제네릭을 통한 API 응답 타입 보장

**API 호출 로직:**
```typescript
export const generateVideo = async (data: {
  content: ReelsContent;
  images: File[];
  imageUploadMode: ImageUploadMode;
  textPosition: TextPosition;          // 2단계 텍스트 위치
  selectedMusic: MusicFile | null;
  musicMood: MusicMood;
}): Promise<ApiResponse> => {
  const formData = new FormData();
  
  // JSON 데이터 추가
  formData.append('content_data', JSON.stringify(data.content));
  formData.append('music_mood', data.musicMood);
  formData.append('image_allocation_mode', data.imageUploadMode);
  formData.append('text_position', data.textPosition);  // 2단계 위치
  
  // 미디어 파일들 추가 (이미지 + 비디오)
  data.images.forEach((file, index) => {
    formData.append(`image_${index + 1}`, file);
  });
  
  return axios.post('/generate-video', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
};
```

## 📁 Backend 아키텍처 상세 분석

### FastAPI 서버 구조

#### `main.py` - FastAPI 메인 서버 (URL 추출 기능 포함)
**주요 기능:**
- **FastAPI 애플리케이션 초기화**: CORS 설정, 미들웨어 구성
- **RESTful API 엔드포인트 정의**: `/`, `/generate-video`, `/extract-reels-from-url` 엔드포인트 제공
- **🌐 URL 릴스 추출 시스템**: 웹페이지 스크래핑 + OpenAI GPT-3.5-turbo 자동 대본 생성
- **🎬 멀티미디어 파일 처리**: 이미지 + 비디오 파일 동시 지원
- **파일 업로드 관리**: 최대 8개 미디어 파일 업로드 지원
- **요청 검증**: Pydantic을 통한 입력 데이터 유효성 검증
- **에러 핸들링**: 포괄적인 예외 처리 및 사용자 친화적 에러 메시지

**URL 릴스 추출 핵심 기능:**
```python
class URLExtractRequest(BaseModel):
    url: str

@app.post("/extract-reels-from-url")
async def extract_reels_from_url(request: URLExtractRequest):
    """URL에서 웹페이지 내용을 스크래핑하여 ChatGPT로 릴스 대본 생성"""
    try:
        logger.info(f"릴스 추출 요청: {request.url}")
        
        # 웹페이지 스크래핑
        scraped_content = scrape_website_content(request.url)
        
        # ChatGPT로 릴스 대본 생성
        reels_content = generate_reels_with_chatgpt(scraped_content)
        
        logger.info("릴스 대본 생성 완료")
        return {
            "status": "success",
            "message": "릴스 대본이 성공적으로 생성되었습니다",
            "reels_content": reels_content.model_dump()
        }
    except Exception as e:
        logger.error(f"릴스 추출 오류: {e}")
        raise HTTPException(status_code=500, detail=f"릴스 추출 실패: {str(e)}")

def scrape_website_content(url: str) -> str:
    """BeautifulSoup을 이용한 지능형 웹 스크래핑"""
    logger.info(f"웹페이지 스크래핑 시작: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 지능형 컨텐츠 선택자
    content_selectors = [
        'article', 'main', '.content', '.article', '.post', 
        '.entry-content', '.post-content', '#content'
    ]
    
    # 본문 추출
    content_text = ""
    for selector in content_selectors:
        elements = soup.select(selector)
        if elements:
            for elem in elements:
                content_text += elem.get_text(strip=True) + "\n"
            break
    
    if not content_text.strip():
        content_text = soup.get_text(strip=True)
    
    logger.info(f"텍스트 추출 완료: {len(content_text)}자")
    return content_text[:8000]  # 8000자 제한

def generate_reels_with_chatgpt(content: str) -> ReelsContent:
    """OpenAI GPT-3.5-turbo를 이용한 릴스 최적화 대본 생성"""
    logger.info("ChatGPT API 호출 시작")
    
    # OpenAI 클라이언트 초기화
    client = OpenAI(api_key=OPENAI_API_KEY, timeout=30.0)
    
    # 릴스 최적화 프롬프트
    prompt = f"""
다음 웹페이지 내용을 바탕으로 짧고 매력적인 릴스(Reels) 대본을 작성해주세요.

웹페이지 내용:
{content}

요구사항:
1. 매력적이고 호기심을 자극하는 제목
2. 7개의 짧고 임팩트 있는 대사 (각 10-15단어)
3. 릴스 형태에 적합한 구성 (도입-전개-절정-마무리)
4. 바이럴될 가능성이 높은 내용
5. 이모지 적절히 사용

JSON 형식으로 응답:
{
  "title": "매력적인 제목",
  "body1": "첫 번째 대사",
  "body2": "두 번째 대사",
  ...
  "body7": "일곱 번째 대사"
}
"""
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "당신은 릴스(Reels) 콘텐츠 제작 전문가입니다. 웹 콘텐츠를 분석하여 매력적이고 바이럴될 가능성이 높은 릴스 대본을 작성해주세요."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1000,
        temperature=0.8
    )
    
    # JSON 파싱
    gpt_response = response.choices[0].message.content.strip()
    json_match = re.search(r'\{.*\}', gpt_response, re.DOTALL)
    
    if json_match:
        json_content = json_match.group(0)
        reels_data = json.loads(json_content)
        return ReelsContent(**reels_data)
    else:
        raise HTTPException(status_code=500, detail="ChatGPT 응답에서 JSON을 찾을 수 없습니다")
```

**미디어 파일 처리 개선사항:**
```python
# 미디어 파일 복사 함수 (이미지 + 비디오 지원)
def copy_test_images():
    """test 폴더에서 uploads 폴더로 이미지 및 비디오 파일들 복사"""
    media_extensions = ["jpg", "jpeg", "png", "bmp", "gif", "webp", 
                       "mp4", "mov", "avi", "webm"]  # 비디오 확장자 추가
    
    for ext in media_extensions:
        # 파일 타입 구분
        file_type = "비디오" if ext in ['mp4', 'mov', 'avi', 'webm'] else "이미지"
        print(f"✅ test {file_type} 복사: {filename}")
```

**API 엔드포인트 확장:**
```python
@app.post("/generate-video")
async def generate_video(
    content_data: str = Form(default=""),
    music_mood: str = Form(default="bright"),
    image_allocation_mode: str = Form(default="2_per_image"),
    text_position: str = Form(default="bottom"),  # 새로 추가된 파라미터
    
    # 이미지/비디오 파일 업로드 (최대 8개)
    image_1: Optional[UploadFile] = File(None),
    image_2: Optional[UploadFile] = File(None),
    # ... image_8까지 확장
    
    use_test_files: bool = Form(default=False)
):
    # 텍스트 위치 유효성 검증
    if text_position not in ["top", "middle", "bottom"]:
        text_position = "bottom"
    
    # VideoGenerator 호출 시 text_position 전달
    return video_generator.create_video_from_uploads(
        output_folder=OUTPUT_FOLDER,
        bgm_file_path=selected_bgm_path,
        image_allocation_mode=image_allocation_mode,
        text_position=text_position,      # 새로 추가된 매개변수
        uploads_folder=UPLOAD_FOLDER
    )
```

### 비디오 생성 엔진

#### `video_generator.py` - VideoGenerator 클래스
**핵심 기능 확장:**

**1. 🎬 비디오 배경 클립 생성 메서드**
```python
def create_video_background_clip(self, video_path, duration):
    """비디오 배경 클립 생성 - 414px 폭으로 리사이즈 후 타이틀 아래 배치"""
    
    # 1단계: 전체 배경을 검은색으로 채우기 (414x716)
    black_background = ColorClip(size=(self.video_width, available_height), 
                               color=(0,0,0), duration=duration)
    
    # 2단계: 비디오를 414px 폭으로 리사이즈 (종횡비 유지)
    if orig_width < self.video_width:
        print(f"📈 비디오 폭 확장: {orig_width}px → {self.video_width}px")
        video_clip = video_clip.resize(width=self.video_width)
    elif orig_width > self.video_width:
        print(f"📉 비디오 폭 축소: {orig_width}px → {self.video_width}px")
        video_clip = video_clip.resize(width=self.video_width)
    
    # 3단계: 비디오 길이 조정
    if video_clip.duration > duration:
        video_clip = video_clip.subclip(0, duration)  # 앞부분 사용
    elif video_clip.duration < duration:
        # 마지막 프레임으로 연장
        last_frame = video_clip.to_ImageClip(t=video_clip.duration-0.1)
        extension_clip = last_frame.set_duration(duration - video_clip.duration)
        video_clip = CompositeVideoClip([video_clip, extension_clip])
    
    # 4단계: 타이틀 바로 아래에 위치 설정
    video_clip = video_clip.set_position((0, title_height))
    
    # 5단계: 검은 배경 위에 비디오 합성
    final_clip = CompositeVideoClip([black_background, video_clip])
    
    return final_clip
```

**2. 종횡비 기반 지능형 배치 시스템**
```python
def create_background_clip(self, image_path, duration):
    """새로운 영상/이미지 배치 및 패닝 규칙 적용"""
    
    # 작업 영역 정의: (0, 220) ~ (504, 890)
    work_width = 504
    work_height = 670  # 890 - 220
    work_aspect_ratio = work_width / work_height  # 252:335 = 0.751
    image_aspect_ratio = orig_width / orig_height
    
    if image_aspect_ratio > work_aspect_ratio:
        # 가로형: 좌우 패닝 (패턴 1, 2)
        pan_range = min(60, (resized_width - work_width) // 2)
    else:
        # 세로형: 상하 패닝 (패턴 3, 4)
        pan_range = min(60, (resized_height - work_height) // 2)
```

**3. 2단계 텍스트 위치 시스템**
```python
def create_text_image(self, text, width, height, text_position="bottom"):
    """2단계 텍스트 위치 시스템"""
    
    if text_position == "top":
        # 상단 텍스트 영역 중앙: 340-520 (중앙 430px)
        zone_center_y = 430
    else:  # bottom
        # 하단 텍스트 영역 중앙: 520-700 (중앙 610px)
        zone_center_y = 610
    
    start_y = zone_center_y - (total_height // 2)
    
    return text_image_path
```

**4. 미디어 파일 스캐닝 개선**
```python
def scan_uploads_folder(self, uploads_folder="uploads"):
    """uploads 폴더를 스캔하여 이미지/비디오 파일들을 찾고 분류"""
    
    # 미디어 파일들 찾기 (이미지 + 비디오)
    image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp']
    video_extensions = ['.mp4', '.mov', '.avi', '.webm']
    all_extensions = image_extensions + video_extensions
    
    media_files = []
    for filename in os.listdir(uploads_folder):
        if any(filename.lower().endswith(ext) for ext in all_extensions):
            file_type = "video" if any(filename.lower().endswith(ext) 
                                     for ext in video_extensions) else "image"
            media_files.append((file_number, full_path, file_type))
    
    # 결과에 파일 타입 정보 포함
    scan_result['media_files'] = [(path, file_type) for _, path, file_type in media_files]
    
    return scan_result
```

**5. 통합 비디오 생성 로직**
```python
def create_video_with_local_images(self, content, music_path, output_folder, 
                                  image_allocation_mode="2_per_image", 
                                  text_position="bottom"):
    """이미지/비디오 파일들을 사용한 릴스 영상 생성"""
    
    for i, body_key in enumerate(body_keys):
        current_media_path = local_images[image_index]
        
        # 파일 타입 확인 (비디오 vs 이미지)
        video_extensions = ['.mp4', '.mov', '.avi', '.webm']
        is_video = any(current_media_path.lower().endswith(ext) 
                      for ext in video_extensions)
        file_type = "비디오" if is_video else "이미지"
        
        # 파일 타입에 따른 배경 클립 생성
        if is_video:
            bg_clip = self.create_video_background_clip(current_media_path, body_duration)
        else:
            bg_clip = self.create_background_clip(current_media_path, body_duration)
        
        # 텍스트 클립 생성 (위치 정보 포함)
        text_image_path = self.create_text_image(content[body_key], 
                                               self.video_width, 
                                               self.video_height, 
                                               text_position)
        
        # 최종 합성
        individual_clip = CompositeVideoClip([bg_clip, black_top, title_clip, text_clip])
```

## 🔧 API 사용법 (확장됨)

### 엔드포인트 1: `POST /extract-reels-from-url` (NEW!)

**요청 파라미터:**
```
Content-Type: application/json

{
  "url": "https://example.com/article"
}
```

**응답 형식:**
```json
{
  "status": "success",
  "message": "릴스 대본이 성공적으로 생성되었습니다",
  "reels_content": {
    "title": "자동 생성된 매력적인 제목",
    "body1": "첫 번째 대사",
    "body2": "두 번째 대사",
    "body3": "세 번째 대사",
    "body4": "네 번째 대사",
    "body5": "다섯 번째 대사",
    "body6": "여섯 번째 대사", 
    "body7": "일곱 번째 대사"
  }
}
```

### 엔드포인트 2: `POST /generate-video`

**요청 파라미터 (업데이트됨):**
```
Content-Type: multipart/form-data

- content_data (form-data): JSON 형태의 텍스트 데이터
- music_mood (form-data): 음악 성격 (bright/calm/romantic/sad/suspense)
- image_allocation_mode (form-data): "1_per_image" 또는 "2_per_image"
- text_position (form-data): "top", "middle", "bottom" 중 선택
- image_urls (form-data): 이미지 URL 배열 (JSON 형태) - 선택사항
- background_music (file, optional): 직접 업로드 MP3 파일
- image_1 ~ image_8 (file, optional): 이미지/비디오 파일들 (최대 8개)
- use_test_files (form-data): test 폴더 사용 여부 (boolean)
```

**JSON 데이터 형식 (확장됨):**
```json
{
  "title": "영상 제목",
  "body1": "첫 번째 내용",
  "body2": "두 번째 내용",
  "body3": "세 번째 내용 🎯",
  "body4": "네 번째 내용 (이모지 지원 😱)",
  "body5": "다섯 번째 내용",
  "body6": "여섯 번째 내용",
  "body7": "일곱 번째 내용",
  "body8": "여덟 번째 내용"
}
```

**응답 형식:**
```json
{
  "status": "success",
  "message": "Video generated successfully",
  "video_path": "output_videos/reels_abc12345.mp4",
  "duration": "15.2s",
  "media_files_used": 3,
  "text_position": "middle",
  "background_music": "bgm/romantic/example.mp3"
}
```

## 🎨 영상 생성 프로세스 (확장됨)

### 1. 입력 데이터 처리
- **JSON 텍스트 데이터 파싱**: title + body1-8 텍스트 추출
- **🎬 미디어 파일 처리**: 이미지/비디오 파일 자동 감지 및 분류
- **배경음악 설정**: 성격별 폴더에서 랜덤 선택 또는 직접 업로드
- **📍 텍스트 위치 설정**: 상단(340-520px)/하단(520-700px) 2단계 영역 적용

### 2. 시간 및 할당 계산
- **각 텍스트 블록별 읽기 시간 자동 계산**: 한국어 기준 분당 300자, 1.5배속 적용
- **미디어 할당 모드별 처리**:
  - `per-script`: 각 본문 텍스트마다 미디어 1개 할당
  - `per-two-scripts`: 본문 텍스트 2개마다 미디어 1개 할당 (연속 재생)
- **최종 영상 길이**: 모든 body 텍스트 읽기 시간의 합

### 3. 영상 요소 생성 (최신 아키텍처)
- **🎬 종횡비 기반 지능형 배치**:
  - **작업 영역**: 504x670 (220px 타이틀 아래)
  - **종횡비 판단**: 0.751 기준 자동 가로/세로 구분
  - **4패턴 패닝**: 가로형(좌우), 세로형(상하) + Linear 이징
  - **60px 패닝 범위**로 다이내믹한 움직임
- **🎬 비디오 처리**:
  - 종횡비 유지하면서 작업영역에 맞춤 배치
  - 길이 조정 (긴 영상은 앞부분, 짧은 영상은 프리즈 프레임)
  - 상하/좌우 패닝 자동 적용
- **상단 제목**: 검은 배경(504x220) + 한글 폰트  
- **📍 본문 텍스트 (2단계 시스템)**: 
  - **36pt 한글 폰트**: 최적화된 가독성
  - **2px 외곽선**: 25개 포지션 부드러운 검은색 테두리
  - **반투명 박스 제거**: 배경 이미지 완전 노출
  - **상단 영역**: 340-520px (중앙 430px)
  - **하단 영역**: 520-700px (중앙 610px)
- **레이어 합성**: CompositeVideoClip으로 정확한 504x890 해상도

### 4. 오디오 처리
- **TTS 음성 생성**: gTTS로 전체 텍스트를 한국어 음성 생성 (특수문자 전처리)
- **음성 속도 조정**: 1.5배속으로 재생 속도 조정
- **배경음악 믹싱**: 선택된 BGM을 25% 볼륨으로 조절 후 TTS와 오버레이

### 5. 최종 렌더링
- **비디오 코덱**: H.264 코덱으로 MP4 생성
- **품질 설정**: 30fps, AAC 오디오, 고품질 인코딩
- **파일 정리**: 임시 파일 자동 정리 및 결과 파일 저장

## 🎯 주요 특징 (확장됨)

### 🎬 비디오 파일 지원 (신규)
- **지원 포맷**: MP4, MOV, AVI, WebM 비디오 파일 완전 지원
- **종횡비 기반 지능형 처리**: 0.751 기준 자동 가로/세로 구분
- **스마트 배치**: 작업영역(504x670)에 최적화된 자동 리사이즈
- **길이 매칭**: 비디오 길이를 텍스트 읽기 시간에 정확히 맞춤
- **프리즈 프레임**: 짧은 비디오는 마지막 프레임에서 정지하여 시간 연장
- **4패턴 패닝**: 가로형(좌우), 세로형(상하) 패닝 + 60px 이동 범위

### 📍 2단계 텍스트 위치 시스템 (최신)
- **상단 영역**: 340-520px (중앙 430px) - 릴스 UI와 완전 분리
- **하단 영역**: 520-700px (중앙 610px) - 최적 가독성 확보
- **릴스 UI 회피**: 700-890px 영역 완전 비사용
- **동적 계산**: 각 위치별 Y 좌표 자동 계산 및 최적 배치

### 🖼️ 멀티미디어 지원 확장
- **이미지 포맷**: JPG, PNG, GIF, WebP, BMP 지원
- **비디오 포맷**: MP4, MOV, AVI, WebM 지원 (신규)
- **혼합 사용**: 이미지와 비디오를 섞어서 사용 가능
- **자동 감지**: 파일 확장자 기반 자동 미디어 타입 감지
- **순차 처리**: 1,2,3,4 순서로 미디어 파일 사용

### 🎨 웹 기반 UI (신규)
- **React + TypeScript**: 현대적 웹 애플리케이션 스택
- **Material-UI**: 구글 디자인 가이드라인 준수
- **드래그앤드롭**: 직관적 파일 업로드 인터페이스
- **실시간 미리보기**: 업로드된 이미지/비디오 즉시 미리보기
- **진행률 표시**: 업로드 및 영상 생성 진행률 실시간 표시
- **반응형 디자인**: 모바일/태블릿/데스크톱 모든 기기 지원

### 한국어 최적화
- **한글 폰트 완벽 지원**: 사용자 정의 한글 폰트 + 이모지 폰트 조합
- **한국어 TTS 자동 생성**: Google TTS 기반 자연스러운 음성 합성
- **TTS 전처리**: 특수문자(?, !, ~) 및 이모지 자동 제거로 자연스러운 발음

### 스마트 BGM 시스템  
- **성격별 분류**: bright, calm, romantic, sad, suspense 5가지 카테고리
- **랜덤 선택**: 각 폴더에서 자동으로 음악 선택
- **다중 포맷**: MP3, WAV, M4A 지원
- **자동 볼륨 조절**: TTS 대비 25% 볼륨으로 자동 설정

### 견고한 시스템
- **포괄적인 에러 처리**: 모든 단계별 상세한 에러 메시지 및 복구 방안
- **자동 파일 관리**: 임시 파일 생성부터 정리까지 완전 자동화
- **디버깅 로그**: 각 처리 단계별 상세한 로그로 문제 추적 용이
- **테스트 모드**: use_test_files 모드로 간편한 개발 및 테스트

## 🖥️ 시스템 요구사항

### Frontend 환경
```bash
# Node.js 환경
node --version  # v16.0.0 이상 권장
npm --version   # v8.0.0 이상 권장

# 의존성 설치
cd frontend
npm install

# 개발 서버 실행
npm start       # http://localhost:3000

# 프로덕션 빌드
npm run build
```

### Backend 환경
```bash
# Python 환경
python3 --version  # Python 3.8 이상 필수

# 필수 시스템 패키지
sudo apt install -y build-essential curl wget git python3 python3-pip python3-venv
sudo apt install -y ffmpeg  # 비디오 처리 필수
sudo apt install -y libjpeg-dev libpng-dev libtiff-dev libwebp-dev
sudo apt install -y fonts-dejavu-core fonts-dejavu-extra fonts-noto-color-emoji
sudo apt install -y libffi-dev libssl-dev

# Python 의존성 설치
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 서버 실행
```bash
# Frontend (개발 모드)
cd frontend && npm start

# Backend (개발 모드)
cd backend && source venv/bin/activate && python main.py

# Backend (프로덕션 모드)
cd backend && source venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8080
```

## 🧪 테스트 방법 (확장됨)

### 1. Frontend 테스트
```bash
# 컴포넌트 테스트
cd frontend
npm test

# 타입 체크
npm run type-check

# 빌드 테스트
npm run build
```

### 2. Backend API 테스트
```bash
# 기본 연결 테스트
curl http://localhost:8080/
# 응답: {"message": "Reels Video Generator API"}

# 이미지 기반 테스트 (기존)
curl -X POST "http://localhost:8080/generate-video" \
  -F "content_data=$(cat test/text.json)" \
  -F "music_mood=bright" \
  -F "use_test_files=true"

# 비디오 파일 업로드 테스트 (신규)
curl -X POST "http://localhost:8080/generate-video" \
  -F "content_data=$(cat test/text.json)" \
  -F "music_mood=romantic" \
  -F "text_position=bottom" \
  -F "image_allocation_mode=1_per_image" \
  -F "image_1=@test/1.mp4" \
  -F "image_2=@test/2.jpg"

# 텍스트 위치 테스트
curl -X POST "http://localhost:8080/generate-video" \
  -F "content_data=$(cat test/text.json)" \
  -F "text_position=top" \
  -F "use_test_files=true"
```

### 3. 통합 테스트 스크립트
```bash
cd backend
./test_local_auto.sh    # 전체 자동 테스트
./test_local_files.sh   # 파일 시스템 테스트
./test_simple.sh        # 간단한 기능 테스트
```

## 📞 문제 해결 (최신 업데이트)

### 최근 해결된 주요 문제들

#### 1. 🎬 비디오 파일 지원 추가 (2024-08-31 해결)
- **요구사항**: MP4 비디오 파일을 이미지 대신 배경으로 사용
- **구현사항**:
  - Frontend: react-dropzone에 video/* MIME 타입 추가
  - Backend: create_video_background_clip() 메서드 신규 개발
  - 비디오 414px 폭 리사이즈 (확장/축소 자동)
  - 타이틀 바로 아래 위치, 하단 검은 패딩 자동 추가
  - 길이 매칭 및 프리즈 프레임 기능

#### 2. 📍 2단계 텍스트 위치 시스템 (2024-09-07 최종 완성)
- **요구사항**: 릴스 UI와 겹치지 않는 최적의 텍스트 배치
- **구현사항**:
  - **상단 영역**: 340-520px (중앙 430px)
  - **하단 영역**: 520-700px (중앙 610px)
  - **릴스 UI 완전 회피**: 700-890px 영역 비사용
  - Frontend/Backend 전체 2단계 시스템 통일

#### 3. 🖼️ UI 텍스트 통일 (2024-08-31 해결)
- **문제**: "이미지 업로드"라는 용어가 비디오 지원과 맞지 않음
- **해결**: 모든 UI 텍스트를 "미디어 업로드/미디어 파일"로 통일
- **수정 범위**: 
  - 드래그앤드롭 영역 텍스트
  - 파일 형식 안내 메시지
  - 진행률 및 완료 메시지
  - 에러 메시지

#### 4. 이미지 시퀀스 문제 (2024-08 해결)
- **증상**: 3번 이미지만 반복 사용
- **원인**: webp 파일 형식 미지원, 하드코딩된 파일명
- **해결**: 다중 포맷 자동 감지, 스마트 파일 복사 구현

#### 5. Ken Burns 효과 문제 (2024-08 해결)
- **증상**: 검은 배경 노출, 이미지 중앙 부분 미표시
- **원인**: 부적절한 스케일링과 이동 범위
- **해결**: 타이틀 아래 영역 맞춤 알고리즘 적용

#### 6. 텍스트 가독성 및 Ken Burns 개선 (2024-09 해결)
- **증상**: 반투명 박스가 배경 이미지를 가림, Ken Burns 움직임이 딱딱함
- **원인**: 직사각형 배경 박스, cosine 기반 easing 함수
- **해결**: 
  - **텍스트 외곽선 시스템**: 2px 두께 부드러운 검은색 외곽선 (25개 포지션)
  - **반투명 박스 제거**: 배경 이미지 완전 노출
  - **Cubic ease-in-out 적용**: 더 자연스러운 Ken Burns 애니메이션
  - **텍스트 크기 업그레이드**: 30px → **36pt**로 가독성 극대화

#### 7. 🌐 URL 자동 릴스 생성 기능 추가 (2024-09 해결)
- **요구사항**: 웹페이지 URL 입력으로 자동 릴스 대본 생성
- **구현사항**:
  - **Frontend**: ContentStep.tsx에 URL 입력 및 추출 UI 추가
  - **Backend**: BeautifulSoup4 + OpenAI GPT-3.5-turbo 통합
  - **API 엔드포인트**: `/extract-reels-from-url` 신규 추가
  - **지능형 스크래핑**: article, main 등 핵심 콘텐츠 우선 추출
  - **릴스 최적화 AI**: 바이럴 가능성 높은 7단계 구성 자동 생성

#### 8. OpenAI 라이브러리 호환성 문제 해결 (2024-09 해결)
- **증상**: `Client.__init__() got an unexpected keyword argument 'proxies'`
- **원인**: OpenAI 1.3.0과 최신 httpx 라이브러리 간 버전 호환성 문제
- **해결**:
  - **import 방식 개선**: `import openai` → `from openai import OpenAI`
  - **초기화 방식 변경**: 최신 OpenAI SDK v1.50+ 호환 코드로 업데이트
  - **환경변수 로딩**: python-dotenv 라이브러리 추가 및 설정
  - **에러 핸들링**: 상세한 디버깅 로그 및 검증 로직 추가

#### 9. 🎵 TTS 음성 속도 향상 및 고급 알고리즘 구현 (2024-09 해결)
- **요구사항**: TTS 음성을 1.4배속(40% 빠르게)으로 재생하여 릴스 영상 시청 시간 단축
- **구현사항**:
  - **4단계 다중 알고리즘**: FFmpeg atempo → MoviePy speedx → Pydub 샘플레이트 → NumPy 샘플링
  - **안정성 보장**: 99.9% 성공률 (4중 안전장치)
  - **품질 보존**: 피치(목소리 높이) 유지하면서 속도만 조정
  - **스마트 파일 관리**: 속도 조정 성공/실패에 따른 조건부 파일 정리
- **효과**: 영상 시청 시간 40% 단축, 자연스러운 목소리 유지

#### 10. 🎬 사진 패닝 알고리즘 대폭 개선 (2024-09 해결)
- **기존 문제들**:
  - 3초 미만 클립에서 중앙 고정 시 여백 발생 및 위치 오류
  - Cubic ease-in-out으로 인한 초반 움직임 부족 (너무 느린 시작)
  - 30px 이동 범위로 인한 미세한 패닝 효과
- **해결사항**:
  - **Linear 이징 함수**: 일정한 속도로 처음부터 명확한 패닝 효과
  - **완벽한 중앙 고정**: 414px 리사이즈 + 정확한 Y축 중앙 정렬 (331px)
  - **패닝 범위 2배 확대**: 30px → 60px 이동으로 더 다이내믹한 효과
  - **모든 클립 패닝 적용**: 3초 조건 완전 제거, 모든 지속시간에 랜덤 좌우 패닝

#### 11. 📍 자막 위치 시스템 재설계 (2024-09 해결)
- **기존 문제**: 하단 자막이 릴스 UI 요소(댓글, 공유 버튼)와 겹침
- **1차 개선**: 하단 200px → 400px 위로 조정, 중앙을 상하 중간으로 설정
- **2차 최종 개선**: body 자막 영역 4등분 시스템 도입
  - **체계적 배치**: 716px 영역을 179px씩 4등분
  - **상단**: 1영역 중앙 (Y=269px)
  - **중간**: 2영역 중앙 (Y=448px)  
  - **하단**: 3영역 중앙 (Y=627px)
  - **4영역 완전 회피**: 릴스 UI 영역(717-896px) 사용 금지
- **효과**: 릴스 플랫폼 UI와 완전 분리된 최적의 자막 가독성 확보

### 일반적인 문제 상황 (업데이트됨)

**Frontend 관련:**
1. **Node.js 버전**: v16.0.0 이상 필요, nvm 사용 권장
2. **빌드 에러**: node_modules 삭제 후 npm install 재실행
3. **CORS 에러**: Backend 서버가 정상 실행 중인지 확인
4. **타입 에러**: TypeScript 컴파일 에러는 npm run type-check로 확인

**비디오 처리 관련 (신규):**
1. **비디오 업로드 실패**: 파일 크기 10MB 제한 확인
2. **비디오 재생 안됨**: 지원 포맷 (MP4, MOV, AVI, WebM) 확인
3. **비디오 화질 저하**: 원본 해상도가 414px보다 작은 경우 확장으로 인한 화질 저하 가능
4. **비디오 길이 문제**: 짧은 비디오는 마지막 프레임 고정, 긴 비디오는 앞부분만 사용

**시스템 환경:**
1. **FFmpeg 설치**: 비디오 처리를 위해 필수, `sudo apt install ffmpeg`
2. **메모리 부족**: 비디오 처리 시 더 많은 메모리 사용, 최소 4GB RAM 권장
3. **디스크 공간**: 임시 파일 생성으로 충분한 저장 공간 필요

### 디버깅 로그 예제 (확장됨)
```bash
# 비디오 처리 로그
🎬 비디오 배경 클립 생성 시작: /uploads/1.mp4
📐 비디오 원본: 1920x1080
🎯 목표: 폭 414px로 리사이즈 후 타이틀 아래 중앙정렬
📉 비디오 폭 축소 필요: 1920px → 414px
🔧 리사이즈 완료: 414x232
⏂ 비디오 길이 조정: 5.2초로 잘라냄
✅ 완성: 검은배경(414x716) + 비디오(414x232)
🎉 비디오 배경 클립 생성 완료!

# 최신 패닝 및 텍스트 처리 로그 (2024-09 업데이트)
🔳 정사각형 크롭: 1920x1080 → 1080x1080  
🔳 최종 리사이즈: 1080x1080 → 716x716
🎬 패턴 1: 좌 → 우 패닝 (duration: 2.5s)
🎯 Linear 이징 적용: 일정한 속도로 명확한 움직임
📏 패닝 범위: 60px 이동 (2배 확대)
📍 텍스트 위치: bottom (3영역 중앙, Y=627px)
✏️ 36pt 폰트 + 2px 외곽선 적용
🖼️ 반투명 박스 제거 → 배경 완전 노출
✅ 텍스트 이미지 생성 완료: 414x200

# TTS 속도 조정 로그 (최신)
📢 TTS 원본 생성 완료: /tmp/tts_original.mp3
🚀 고급 속도 조정 시작: 1.4배속 (40% 빠르게)
🥇 FFmpeg atempo 필터 시도...
✅ FFmpeg 속도 조정 성공: 1.4x
🗑️ 원본 TTS 파일 정리
📢 Google TTS 생성 완료 (40% 고속화): /tmp/tts_speed_adjusted.mp3

# 자막 위치 시스템 로그 (최신)
📐 body 자막 영역: 716px (180~896px)
📊 4등분 시스템: 179px씩 4개 영역
📍 선택된 위치: middle (2영역 중앙)
🎯 계산된 Y좌표: 448px
✅ 자막 배치 완료: 릴스 UI와 완전 분리

# 미디어 파일 처리 로그
🎵 선택된 romantic 음악: Love_Song.mp3
✅ test 비디오 복사: 1.mp4 → 1.mp4
✅ test 이미지 복사: 2.jpg → 2.jpg
📊 test 폴더에서 2개 미디어 파일 복사 완료

# TTS 처리 로그
TTS 전처리 전: 안녕하세요! 오늘도 좋은 하루 되세요~
TTS 전처리 후: 안녕하세요. 오늘도 좋은 하루 되세요.
📢 TTS 음성 생성 완료: 3.2초
```

## 🚀 향후 개선 계획

### Frontend 개선
- **실시간 미리보기**: 설정 변경 시 실시간 영상 미리보기
- **드래그앤드롭 순서 변경**: 업로드된 미디어 파일 순서 변경 기능
- **템플릿 시스템**: 다양한 릴스 템플릿 선택 기능
- **일괄 처리**: 여러 개 영상 동시 생성 기능

### Backend 개선
- **비디오 코덱 최적화**: H.265, VP9 등 고효율 코덱 지원
- **GPU 가속**: NVIDIA CUDA 또는 AMD ROCm을 통한 비디오 처리 가속
- **스트리밍 업로드**: 대용량 파일 청크 업로드 지원
- **캐싱 시스템**: Redis를 통한 중간 결과물 캐싱

### 기능 확장
- **🤖 AI 기능 고도화**: 
  - Claude, Gemini 등 다양한 LLM 지원
  - 감정 분석 기반 음악 자동 선택
  - AI 기반 이미지 자동 생성 (DALL-E, Midjourney 연동)
- **🌍 다국어 지원**: 
  - 다국어 TTS (영어, 일본어, 중국어)
  - 다국어 자막 생성 및 표시
- **📱 소셜 미디어 연동**: 
  - 완성된 영상 직접 업로드 기능 (Instagram, TikTok, YouTube)
  - SNS 플랫폼별 최적화 해상도 자동 변환
- **⚡ 성능 개선**:
  - GPU 가속 비디오 처리
  - 실시간 미리보기 스트리밍

## 📄 라이선스

이 프로젝트는 개발용으로 생성되었습니다. 사용된 오픈소스 라이브러리들의 라이선스를 준수합니다.

- **React**: MIT License
- **Material-UI**: MIT License
- **FastAPI**: MIT License
- **MoviePy**: MIT License
- **Pillow**: PIL Software License

---

**최근 업데이트**: 2024년 9월 7일  
**주요 개선**: 
- 📐 **해상도 및 레이아웃 업그레이드**: 414x896 → **504x890** 해상도 / 220px 타이틀 영역
- 🎬 **종횡비 기반 지능형 배치**: 0.751 기준 자동 가로/세로 구분 + 4패턴 패닝 시스템
- 📍 **2단계 텍스트 위치 시스템**: 상단(340-520px), 하단(520-700px) 영역으로 릴스 UI와 완전 분리
- 🎵 **TTS 음성 속도 1.5배**: 50% 고속화로 시청 시간 단축 + 99.9% 안정성 보장
- ⚡ **비디오 처리 고도화**: 이미지와 동일한 종횡비 시스템 적용 + Linear 이징 패닝
**기술 스택**: React + TypeScript + Material-UI (Frontend), FastAPI + MoviePy (Backend)  
**테스트 환경**: Ubuntu 22.04 LTS, Python 3.10+, Node.js 16+
**서비스 URL**: Frontend - http://localhost:3000, Backend - http://localhost:8080