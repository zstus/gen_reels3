# YouTube 가로 영상 포맷 지원 - 구현 계획

## 목표
GenerateStep(마지막 화면)에서 영상 포맷을 선택하여, 기존 릴스(세로 504x890) 외에 YouTube 가로 영상(1280x720)도 생성할 수 있도록 한다.

## 핵심 설계 원칙
- **기존 릴스 알고리즘에 영향 최소화**: 하드코딩된 레이아웃 값을 `self` 인스턴스 변수로 추출하고, `set_video_format()` 메서드로 포맷에 따라 값을 설정
- **기존 패턴 재사용**: 이미 `self.video_width`, `self.video_height`가 인스턴스 변수인 것처럼, 나머지 레이아웃 값도 동일 패턴으로 변환
- **함수 시그니처 변경 없음**: `create_video_from_uploads`, `create_video_with_local_images` 등의 파라미터는 변경하지 않음 (TTS와 동일한 `self` 패턴)

---

## 포맷별 레이아웃 프로필

| 항목 | 릴스 (reels) | YouTube (youtube) |
|------|-------------|-------------------|
| 해상도 | 504 x 890 | 1280 x 720 |
| 타이틀 높이 | 220px | 120px |
| 작업 영역 (keep) | 504 x 670 | 1280 x 600 |
| 작업 영역 (remove) | 504 x 890 | 1280 x 720 |
| 텍스트 상단 Y 중앙 | 430px | 340px |
| 텍스트 하단 Y 중앙 | 610px | 520px |
| 텍스트 최하단 여백 | 80px | 60px |
| 패닝 범위 | 60px | 60px |
| 종횡비 기준 (keep) | 0.751 (504/670) | 2.133 (1280/600) |

---

## 수정 파일 목록 (7개)

### 1. `backend/video_generator.py` (핵심)

**`__init__`에 레이아웃 인스턴스 변수 추가:**
```python
# 레이아웃 설정 (릴스 기본값)
self.title_height = 220
self.work_height_keep = 670      # title_area_mode='keep'일 때
self.work_height_remove = 890    # title_area_mode='remove'일 때
self.text_y_top = 430
self.text_y_bottom = 610
self.text_y_bottom_edge_margin = 80
self.panning_range = 60
```

**`set_video_format(format)` 메서드 추가:**
```python
def set_video_format(self, video_format: str):
    """영상 포맷 설정 (reels: 세로 504x890, youtube: 가로 1280x720)"""
    if video_format == 'youtube':
        self.video_width = 1280
        self.video_height = 720
        self.title_height = 120
        self.work_height_keep = 600
        self.work_height_remove = 720
        self.text_y_top = 340
        self.text_y_bottom = 520
        self.text_y_bottom_edge_margin = 60
        self.panning_range = 60
    else:  # reels (기본값)
        self.video_width = 504
        self.video_height = 890
        self.title_height = 220
        self.work_height_keep = 670
        self.work_height_remove = 890
        self.text_y_top = 430
        self.text_y_bottom = 610
        self.text_y_bottom_edge_margin = 80
        self.panning_range = 60
    logger.info(f"🎬 영상 포맷 설정: {video_format} ({self.video_width}x{self.video_height})")
```

**하드코딩 값 → 인스턴스 변수 치환 (전체 목록):**

| 위치 (라인 근처) | 변경 전 | 변경 후 |
|-----------------|---------|---------|
| create_text_image ~768 | `title_height = 220` | `title_height = self.title_height` |
| create_text_image ~772 | `zone_center_y = 430` | `zone_center_y = self.text_y_top` |
| create_text_image ~778 | `start_y = 890 - 80 - total_height` | `start_y = self.video_height - self.text_y_bottom_edge_margin - total_height` |
| create_text_image ~781 | `zone_center_y = 610` | `zone_center_y = self.text_y_bottom` |
| create_background_clip ~1086 | `work_height = 670` | `work_height = self.work_height_keep` |
| create_background_clip ~1087 | `y_offset = 220` | `y_offset = self.title_height` |
| create_background_clip ~1089 | `work_height = 890` | `work_height = self.work_height_remove` |
| create_background_clip ~1157,1180 | `min(60, ...)` | `min(self.panning_range, ...)` |
| create_background_clip ~1278 | `y_offset = 220` | `y_offset = self.title_height` |
| create_background_clip ~1279 | `work_height = 670` | `work_height = self.work_height_keep` |
| create_background_clip ~1282 | `work_height = 890` | `work_height = self.work_height_remove` |
| fallback ~1239,1243 | `set_position((0, 220))` | `set_position((0, self.title_height))` |
| fallback ~1674 | `ColorClip(size=(504, 670), ...)` | `ColorClip(size=(self.video_width, self.work_height_keep), ...)` |
| fallback ~1675 | `set_position((0, 220))` | `set_position((0, self.title_height))` |
| create_video_background_clip ~1439 | `work_height = 670` | `work_height = self.work_height_keep` |
| create_video_background_clip ~1558 | `min(60, ...)` | `min(self.panning_range, ...)` |
| create_video_background_clip ~1585 | `set_position((x_offset, 220))` | `set_position((x_offset, self.title_height))` |
| create_video_background_clip ~1632 | `min(60, ...)` | `min(self.panning_range, ...)` |
| create_video_background_clip ~1641 | `y_offset = 220 - (...)` | `y_offset = self.title_height - (...)` |
| create_video_background_clip ~1651 | `y_offset = 220 - (...)` | `y_offset = self.title_height - (...)` |
| create_video_background_clip ~1658 | `y_offset = 220 - (...)` | `y_offset = self.title_height - (...)` |
| CompositeVideoClip ~2270 | `ColorClip(size=(self.video_width, 220), ...)` | `ColorClip(size=(self.video_width, self.title_height), ...)` |
| CompositeVideoClip ~2346 | `ColorClip(size=(self.video_width, 220), ...)` | `ColorClip(size=(self.video_width, self.title_height), ...)` |
| CompositeVideoClip ~2440 | `ColorClip(size=(self.video_width, 220), ...)` | `ColorClip(size=(self.video_width, self.title_height), ...)` |
| CompositeVideoClip ~2705 | `ColorClip(size=(self.video_width, 220), ...)` | `ColorClip(size=(self.video_width, self.title_height), ...)` |
| CompositeVideoClip ~2749 | `ColorClip(size=(self.video_width, 220), ...)` | `ColorClip(size=(self.video_width, self.title_height), ...)` |
| CompositeVideoClip ~2804 | `ColorClip(size=(self.video_width, 220), ...)` | `ColorClip(size=(self.video_width, self.title_height), ...)` |
| fullscreen ~3275,3297 | `min(60, available_margin)` | `min(self.panning_range, available_margin)` |

### 2. `frontend/src/types/index.ts`
- `VideoFormat` 타입 추가: `export type VideoFormat = 'reels' | 'youtube';`
- `ProjectData`에 `videoFormat: VideoFormat` 필드 추가

### 3. `frontend/src/pages/MainApp.tsx`
- `projectData` 초기 상태에 `videoFormat: 'reels'` 추가
- `handleReset`에도 동일하게 `videoFormat: 'reels'` 추가

### 4. `frontend/src/components/GenerateStep.tsx`
- ToggleButtonGroup 으로 영상 포맷 선택 UI 추가 (릴스 504x890 / YouTube 1280x720)
- 선택된 포맷에 따른 해상도/비율 설명 텍스트 표시
- `startAsyncGeneration`, `startSyncGeneration` 양쪽에 `videoFormat` 전달

### 5. `frontend/src/services/api.ts`
- `generateVideo`, `generateVideoAsync` 파라미터에 `videoFormat?: string` 추가
- FormData에 `video_format` append

### 6. `backend/routers/video_router.py`
- 동기/비동기 엔드포인트 모두에 `video_format: str = Form(default="reels")` 추가
- 동기 엔드포인트: `video_gen.set_video_format(video_format)` 호출
- 비동기 엔드포인트: `video_params`에 `"video_format": video_format` 저장

### 7. `backend/worker.py`
- `video_params`에서 `video_format` 추출 (기본값 `"reels"`)
- `self.video_generator.set_video_format(video_format)` 호출

---

## 작업 순서

1. **Backend video_generator.py**: `__init__` 인스턴스 변수 추가 + `set_video_format()` 메서드 + 하드코딩 값 치환
2. **Frontend types/index.ts**: `VideoFormat` 타입 + `ProjectData` 필드
3. **Frontend MainApp.tsx**: 초기 상태 + 리셋에 `videoFormat` 추가
4. **Frontend GenerateStep.tsx**: 포맷 선택 UI + API 호출 전달
5. **Frontend api.ts**: `video_format` 파라미터 추가
6. **Backend video_router.py**: Form 파라미터 + `set_video_format()` 호출
7. **Backend worker.py**: `video_format` 파싱 + `set_video_format()` 호출

## 영향 범위 분석

- **기존 릴스 생성**: `set_video_format`을 호출하지 않거나 `'reels'`로 호출하면 `__init__` 기본값과 동일 → **변경 없음**
- **함수 시그니처**: `create_video_from_uploads`, `create_video_with_local_images` 등 기존 함수 시그니처 **변경 없음**
- **기존 패턴 일관성**: `self` 인스턴스 변수 패턴 (TTS, video_width/height와 동일)
- **하드코딩 → self 변수 치환**: 값 자체는 동일하므로 릴스 포맷일 때 기존과 100% 동일한 결과

## 검증 방법

1. 릴스 포맷 선택 → 기존과 동일한 504x890 영상 생성 확인
2. YouTube 포맷 선택 → 1280x720 가로 영상 생성 확인
3. 타이틀 영역, 텍스트 위치, 패닝 효과가 포맷에 맞게 조정되는지 확인
4. 비동기(워커) 생성에서도 포맷이 정확히 전달되는지 확인
