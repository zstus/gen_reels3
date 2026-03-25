# 릴스 생성 서비스 — 외부 API 사용 매뉴얼

> 이 문서는 외부 시스템에서 릴스 영상을 자동 생성하기 위한 API 호출 방법을 설명합니다.

---

## 목차

1. [개요](#1-개요)
2. [사전 준비 — API Key 발급](#2-사전-준비--api-key-발급)
3. [엔드포인트 목록](#3-엔드포인트-목록)
4. [API 1 — 릴스 생성 요청](#4-api-1--릴스-생성-요청)
5. [API 2 — 작업 상태 조회](#5-api-2--작업-상태-조회)
6. [전체 흐름 정리](#6-전체-흐름-정리)
7. [content_data 작성 규칙](#7-content_data-작성-규칙)
8. [이미지 파일 규칙](#8-이미지-파일-규칙)
9. [프리셋 설정값 참고](#9-프리셋-설정값-참고)
10. [에러 코드 정리](#10-에러-코드-정리)
11. [언어별 호출 예제](#11-언어별-호출-예제)
12. [자주 묻는 질문](#12-자주-묻는-질문)

---

## 1. 개요

외부 시스템은 두 단계로 릴스 영상을 생성합니다.

```
[1단계] POST /api/v1/generate-reels   → job_id 즉시 반환
[2단계] GET  /job-status/{job_id}      → 상태 폴링 (완료 시 이메일 수신)
```

- **비동기 처리**: 영상 생성은 백그라운드 워커가 수행하므로, API 호출 직후 `job_id`만 반환됩니다.
- **이메일 알림**: 생성이 완료되면 `user_email`로 다운로드 링크가 자동 발송됩니다.
- **인증 방식**: 모든 요청에 `X-API-Key` 헤더가 필요합니다.

---

## 2. 사전 준비 — API Key 발급

서버 관리자에게 API Key를 요청하거나, 서버의 `backend/.env` 파일에서 직접 설정합니다.

```bash
# backend/.env
EXTERNAL_API_KEY=test-key-12345
```

발급된 키는 모든 요청의 `X-API-Key` 헤더에 포함해야 합니다.

---

## 3. 엔드포인트 목록

| 메서드 | 경로 | 인증 | 설명 |
|--------|------|------|------|
| `POST` | `/api/v1/generate-reels` | 필수 | 릴스 생성 요청 |
| `GET`  | `/job-status/{job_id}` | 불필요 | 작업 상태 조회 |

**Base URL 예시**
```
http://zstus.synology.me:8097
```

---

## 4. API 1 — 릴스 생성 요청

### `POST /api/v1/generate-reels`

#### 요청 형식

```
Content-Type: multipart/form-data
X-API-Key: {발급받은 API Key}
```

#### 요청 파라미터

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `content_data` | string (JSON) | **필수** | 대사 데이터 (아래 형식 참고) |
| `user_email` | string | **필수** | 완료 시 이메일 발송 주소 |
| `voice` | string | 선택 | 음성 엔진 선택: `qwen` 또는 `edge` (미지정 시 `qwen`) |
| `image_1` | file | 선택 | 1번 대사에 대응하는 이미지/비디오 |
| `image_2` | file | 선택 | 2번 대사에 대응하는 이미지/비디오 |
| `image_3` ~ `image_50` | file | 선택 | 3~50번 대사 대응 파일 |

> `image_N`은 `body_N` 대사와 1:1 대응합니다 (`image_allocation_mode: 1_per_image`).
> 이미지를 보내지 않으면 해당 대사 구간은 검은 화면으로 처리됩니다.

#### content_data JSON 형식

```json
{
  "title": "영상 제목 (상단 타이틀 영역에 표시)",
  "body1": "첫 번째 대사",
  "body2": "두 번째 대사",
  "body3": "세 번째 대사",
  "body4": "네 번째 대사",
  "body5": "다섯 번째 대사",
  "body6": "여섯 번째 대사",
  "body7": "일곱 번째 대사"
}
```

- `title`은 필수, `body1`~`body50`까지 사용 가능
- 빈 문자열(`""`)인 body는 건너뜀
- 각 body는 TTS로 읽혀 음성이 생성되며, 해당 구간의 이미지와 합성됨

#### 성공 응답 (200 OK)

```json
{
  "status": "success",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "릴스 생성 작업이 접수되었습니다. 완료 시 이메일로 알림됩니다.",
  "email": "user@example.com"
}
```

| 필드 | 설명 |
|------|------|
| `job_id` | 작업 추적에 사용하는 UUID (저장 필수) |
| `email` | 완료 알림을 수신할 이메일 주소 |

#### 에러 응답

| 상태 코드 | 원인 | 응답 예시 |
|-----------|------|-----------|
| `401` | API Key 불일치 또는 누락 | `{"detail": "Unauthorized: 유효하지 않은 API Key입니다."}` |
| `400` | content_data JSON 형식 오류 | `{"detail": "content_data JSON 파싱 오류: ..."}` |
| `500` | 서버 내부 오류 | `{"detail": "릴스 생성 요청 중 오류가 발생했습니다: ..."}` |

---

## 5. API 2 — 작업 상태 조회

### `GET /job-status/{job_id}`

인증 헤더 없이 호출 가능합니다.

#### 요청 예시

```
GET /job-status/550e8400-e29b-41d4-a716-446655440000
```

#### 응답 형식

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "created_at": "2026-03-04T10:30:00.000000",
  "updated_at": "2026-03-04T10:35:42.000000",
  "result": {
    "video_path": "output/job_xxx/reels_abc12345.mp4",
    "completed_at": "2026-03-04T10:35:42.000000"
  },
  "error_message": null
}
```

#### status 값 정의

| status | 의미 | 다음 행동 |
|--------|------|-----------|
| `pending` | 대기 중 (아직 처리 안 됨) | 재시도 대기 |
| `processing` | 워커가 영상 생성 중 | 재시도 대기 |
| `completed` | 생성 완료, 이메일 발송됨 | 이메일 확인 |
| `failed` | 생성 실패 | `error_message` 확인 후 재시도 |

#### 폴링 권장 주기

```
pending/processing 상태: 15~30초 간격으로 재조회
최대 대기 시간: 30분 (영상 길이에 따라 다름)
```

---

## 6. 전체 흐름 정리

```
외부 시스템                              릴스 서버
    │                                       │
    │  POST /api/v1/generate-reels          │
    │  X-API-Key: {key}                     │
    │  content_data: {...}                  │
    │  user_email: user@example.com         │
    │  image_1: (파일)                      │
    │  image_2: (파일)                      │
    │ ─────────────────────────────────────►│
    │                                       │ job_id 생성
    │                                       │ Job 폴더 생성
    │                                       │ 파일 저장
    │                                       │ 큐에 작업 등록
    │◄─────────────────────────────────────┤
    │  { "job_id": "uuid", "status": "success" }
    │                                       │
    │  (15~30초 후 폴링)                    │ [백그라운드 워커]
    │  GET /job-status/{job_id}             │ 영상 생성 중...
    │ ─────────────────────────────────────►│
    │◄─────────────────────────────────────┤
    │  { "status": "processing" }           │
    │                                       │
    │  (완료 후 폴링)                       │
    │  GET /job-status/{job_id}             │
    │ ─────────────────────────────────────►│
    │◄─────────────────────────────────────┤
    │  { "status": "completed" }            │
    │                                       │
    │                    [이메일 수신]       │
    │              user@example.com         │
    │              다운로드 링크 클릭        │
```

---

## 7. content_data 작성 규칙

### 기본 구조

```json
{
  "title": "제목",
  "body1": "대사1",
  "body2": "대사2",
  ...
  "body50": "대사50"
}
```

### 규칙

- **title**: 상단 타이틀 영역(220px)에 표시. 영상 전체에 고정 노출됨.
- **body1~body50**: 순서대로 처리. 빈 문자열이면 해당 대사 생략.
- **이모지 사용 가능**: 자막에는 표시되나, TTS 음성에서는 자동 제거됨.
- **권장 대사 길이**: 한 대사당 15~40자. 너무 길면 화면에 잘릴 수 있음.
- **최대 대사 수**: 50개 (`body1`~`body50`)

### 예시

```json
{
  "title": "오늘의 건강 꿀팁 3가지",
  "body1": "하루 8잔의 물, 마시고 계신가요? 💧",
  "body2": "식후 10분 걷기만 해도 혈당이 안정됩니다.",
  "body3": "잠들기 1시간 전에는 스마트폰을 내려놓으세요.",
  "body4": "이 세 가지만 지켜도 건강이 달라집니다!",
  "body5": "좋아요와 팔로우로 더 많은 정보를 받아보세요 👍"
}
```

---

## 8. 이미지 파일 규칙

### 지원 포맷

| 종류 | 확장자 |
|------|--------|
| 이미지 | `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.bmp` |
| 비디오 | `.mp4`, `.mov`, `.avi`, `.webm` |

### 파일-대사 매핑 규칙

`image_allocation_mode`가 `1_per_image`로 고정되어 있어, 파일 번호와 대사 번호가 1:1 대응합니다.

| 필드명 | 대응 대사 |
|--------|-----------|
| `image_1` | `body1` |
| `image_2` | `body2` |
| `image_3` | `body3` |
| ... | ... |
| `image_50` | `body50` |

> `image_1`을 전송하면 `body1` 구간의 배경으로 사용됩니다.
> 이미지를 보내지 않은 대사 구간은 검은 화면으로 처리됩니다.

### 이미지 가이드라인

- **최대 파일 크기**: 파일 1개당 제한 없음 (서버 디스크 여유 공간 내)
- **권장 해상도**: 1080px 이상 (출력 영상은 504x890 세로형)
- **가로형/세로형 모두 가능**: 자동으로 패닝(Ken Burns) 효과 적용
- **비디오 길이**: 길면 앞부분만 사용, 짧으면 마지막 프레임에서 정지

---

## 9. 프리셋 설정값 참고

외부 API는 아래 값이 고정 적용됩니다. 변경 불가.

| 설정 | 값 | 설명 |
|------|----|------|
| `video_format` | `reels` | 출력 해상도 504x890 (세로형) |
| `text_position` | `bottom-edge` | 자막 위치: 최하단 영역 |
| `text_style` | `outline` | 자막 스타일: 흰 글자 + 검은 외곽선 |
| `title_area_mode` | `keep` | 상단 220px 타이틀 영역 유지 |
| `title_font_size` | `42pt` | 타이틀 폰트 크기 |
| `body_font_size` | `27pt` | 자막 폰트 크기 |
| `title_font` | `BMHANNAPro.ttf` | 타이틀 폰트 |
| `body_font` | `BMYEONSUNG_otf.otf` | 자막 폰트 |
| `image_allocation_mode` | `1_per_image` | 대사 1개당 이미지 1개 |
| `music_mood` | `bright` | BGM 성격: 밝은 계열에서 랜덤 선택 |
| `voice_narration` | `enabled` | TTS 음성 자막 읽기 활성화 |
| `tts_engine` | `qwen` (미지정 시) | TTS 엔진: `voice` 파라미터로 선택 가능 (`qwen` / `edge`) |
| `qwen_speaker` | `Sohee` | TTS 화자 (qwen 선택 시) |
| `qwen_speed` | `fast` | TTS 속도: 빠름 (qwen 선택 시) |
| `qwen_style` | `neutral` | TTS 스타일: 자연스러운 중립 (qwen 선택 시) |
| `edge_speaker` | `female` | Edge TTS 화자: 여성 (edge 선택 시) |
| `edge_speed` | `fast` | Edge TTS 속도: 빠름 (edge 선택 시) |
| `edge_pitch` | `normal` | Edge TTS 톤: 보통 (edge 선택 시) |
| `cross_dissolve` | `disabled` | 장면 전환 효과 없음 |
| `subtitle_duration` | `0.0` | 자막 추가 지속 시간 없음 |

---

## 10. 에러 코드 정리

| HTTP 상태 코드 | 원인 | 해결 방법 |
|---------------|------|-----------|
| `401 Unauthorized` | `X-API-Key` 헤더 없거나 값 불일치 | 올바른 API Key 확인 |
| `400 Bad Request` | `content_data` JSON 파싱 실패 | JSON 문법 오류 확인 |
| `404 Not Found` | 존재하지 않는 `job_id` 조회 | job_id 오타 확인 |
| `500 Internal Server Error` | 서버 내부 오류 (큐 시스템 오류 등) | 서버 관리자에게 문의 |

---

## 11. 언어별 호출 예제

### curl

```bash
curl -X POST "http://zstus.synology.me:8080/api/v1/generate-reels" \
  -H "X-API-Key: your-secret-key-here" \
  -F 'content_data={
    "title": "오늘의 건강 꿀팁",
    "body1": "하루 8잔의 물 마시기 💧",
    "body2": "식후 10분 걷기",
    "body3": "잠들기 전 스마트폰 내려놓기"
  }' \
  -F "user_email=user@example.com" \
  -F "image_1=@/path/to/image1.jpg" \
  -F "image_2=@/path/to/image2.jpg" \
  -F "image_3=@/path/to/image3.jpg"
```

#### 상태 조회 (curl)

```bash
curl "http://zstus.synology.me:8080/job-status/550e8400-e29b-41d4-a716-446655440000"
```

---

### Python (requests)

```python
import requests
import json
import time

BASE_URL = "http://zstus.synology.me:8080"
API_KEY = "your-secret-key-here"

# 1단계: 릴스 생성 요청
content = {
    "title": "오늘의 건강 꿀팁",
    "body1": "하루 8잔의 물 마시기 💧",
    "body2": "식후 10분 걷기",
    "body3": "잠들기 전 스마트폰 내려놓기"
}

files = {
    "image_1": ("image1.jpg", open("/path/to/image1.jpg", "rb"), "image/jpeg"),
    "image_2": ("image2.jpg", open("/path/to/image2.jpg", "rb"), "image/jpeg"),
    "image_3": ("image3.jpg", open("/path/to/image3.jpg", "rb"), "image/jpeg"),
}

data = {
    "content_data": json.dumps(content, ensure_ascii=False),
    "user_email": "user@example.com"
}

response = requests.post(
    f"{BASE_URL}/api/v1/generate-reels",
    headers={"X-API-Key": API_KEY},
    data=data,
    files=files
)
response.raise_for_status()

result = response.json()
job_id = result["job_id"]
print(f"작업 접수 완료: {job_id}")

# 2단계: 상태 폴링
while True:
    status_response = requests.get(f"{BASE_URL}/job-status/{job_id}")
    status_data = status_response.json()
    status = status_data["status"]

    print(f"현재 상태: {status}")

    if status == "completed":
        print("영상 생성 완료! 이메일을 확인하세요.")
        break
    elif status == "failed":
        print(f"생성 실패: {status_data.get('error_message')}")
        break

    time.sleep(20)  # 20초 간격으로 폴링
```

---

### JavaScript / Node.js (fetch + FormData)

```javascript
const FormData = require("form-data");
const fs = require("fs");
const fetch = require("node-fetch");

const BASE_URL = "http://zstus.synology.me:8080";
const API_KEY = "your-secret-key-here";

async function generateReels() {
  const content = {
    title: "오늘의 건강 꿀팁",
    body1: "하루 8잔의 물 마시기 💧",
    body2: "식후 10분 걷기",
    body3: "잠들기 전 스마트폰 내려놓기",
  };

  const form = new FormData();
  form.append("content_data", JSON.stringify(content));
  form.append("user_email", "user@example.com");
  form.append("image_1", fs.createReadStream("/path/to/image1.jpg"));
  form.append("image_2", fs.createReadStream("/path/to/image2.jpg"));
  form.append("image_3", fs.createReadStream("/path/to/image3.jpg"));

  // 1단계: 생성 요청
  const response = await fetch(`${BASE_URL}/api/v1/generate-reels`, {
    method: "POST",
    headers: {
      "X-API-Key": API_KEY,
      ...form.getHeaders(),
    },
    body: form,
  });

  const result = await response.json();
  if (!response.ok) {
    throw new Error(`요청 실패: ${result.detail}`);
  }

  const jobId = result.job_id;
  console.log(`작업 접수 완료: ${jobId}`);

  // 2단계: 상태 폴링
  while (true) {
    await new Promise((r) => setTimeout(r, 20000)); // 20초 대기

    const statusRes = await fetch(`${BASE_URL}/job-status/${jobId}`);
    const statusData = await statusRes.json();

    console.log(`현재 상태: ${statusData.status}`);

    if (statusData.status === "completed") {
      console.log("영상 생성 완료! 이메일을 확인하세요.");
      break;
    } else if (statusData.status === "failed") {
      console.error(`생성 실패: ${statusData.error_message}`);
      break;
    }
  }
}

generateReels().catch(console.error);
```

---

### PHP (cURL)

```php
<?php

$BASE_URL = "http://zstus.synology.me:8080";
$API_KEY  = "your-secret-key-here";

$content = json_encode([
    "title" => "오늘의 건강 꿀팁",
    "body1" => "하루 8잔의 물 마시기 💧",
    "body2" => "식후 10분 걷기",
    "body3" => "잠들기 전 스마트폰 내려놓기",
], JSON_UNESCAPED_UNICODE);

// 1단계: 생성 요청
$postFields = [
    "content_data" => $content,
    "user_email"   => "user@example.com",
    "image_1"      => new CURLFile("/path/to/image1.jpg", "image/jpeg", "image1.jpg"),
    "image_2"      => new CURLFile("/path/to/image2.jpg", "image/jpeg", "image2.jpg"),
    "image_3"      => new CURLFile("/path/to/image3.jpg", "image/jpeg", "image3.jpg"),
];

$ch = curl_init("$BASE_URL/api/v1/generate-reels");
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_POSTFIELDS, $postFields);
curl_setopt($ch, CURLOPT_HTTPHEADER, ["X-API-Key: $API_KEY"]);

$response = json_decode(curl_exec($ch), true);
curl_close($ch);

$jobId = $response["job_id"];
echo "작업 접수 완료: $jobId\n";

// 2단계: 상태 폴링
while (true) {
    sleep(20);

    $ch = curl_init("$BASE_URL/job-status/$jobId");
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    $status = json_decode(curl_exec($ch), true);
    curl_close($ch);

    echo "현재 상태: {$status['status']}\n";

    if ($status["status"] === "completed") {
        echo "영상 생성 완료! 이메일을 확인하세요.\n";
        break;
    } elseif ($status["status"] === "failed") {
        echo "생성 실패: {$status['error_message']}\n";
        break;
    }
}
```

---

## 12. 자주 묻는 질문

**Q. 이미지를 보내지 않아도 되나요?**
A. 네. 이미지 없이 `content_data`와 `user_email`만 보내도 됩니다. 다만 이미지가 없는 대사 구간은 검은 화면으로 처리됩니다.

**Q. body 텍스트 개수와 이미지 개수가 달라도 되나요?**
A. 됩니다. 이미지가 없는 대사 구간은 검은 화면, 대사가 없는 이미지는 무시됩니다.

**Q. 영상 생성에 얼마나 걸리나요?**
A. 대사 수와 서버 상황에 따라 다르지만 보통 3~15분입니다. 30분 이상 `pending`이면 서버 관리자에게 문의하세요.

**Q. 완료 이메일이 오지 않으면 어떻게 하나요?**
A. `GET /job-status/{job_id}`로 상태를 직접 확인하세요. `completed`이면 이메일 스팸함을 확인하거나 서버 관리자에게 문의하세요.

**Q. 같은 job_id로 재요청이 가능한가요?**
A. 불가능합니다. 요청마다 새로운 `job_id`가 서버에서 자동 생성됩니다.

**Q. 비디오 파일(mp4 등)을 이미지 대신 보낼 수 있나요?**
A. 가능합니다. `.mp4`, `.mov`, `.avi`, `.webm` 포맷을 이미지와 혼합해서 사용할 수 있습니다.

**Q. 한 번에 보낼 수 있는 이미지 최대 개수는?**
A. `image_1`부터 `image_50`까지 최대 50개입니다.

**Q. BGM을 직접 지정할 수 있나요?**
A. 외부 API는 프리셋으로 고정되어 있어 `bright` 계열 BGM에서 랜덤 선택됩니다. BGM 변경이 필요하면 서버 관리자에게 문의하세요.
