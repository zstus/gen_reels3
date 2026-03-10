#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from PIL import Image

WORKSPACE = Path('/home/xystus/.openclaw/workspace')
TOOLS = WORKSPACE / 'dev' / 'tools'
REPORTS = WORKSPACE / 'reports'


def run_picker() -> dict:
    cmd = [sys.executable, str(TOOLS / 'pann_reels_picker.py')]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f'pann_reels_picker.py failed ({p.returncode})\nstdout:\n{p.stdout}\nstderr:\n{p.stderr}')

    lines = [ln.strip() for ln in p.stdout.splitlines() if ln.strip()]
    if not lines:
        raise RuntimeError('pann_reels_picker.py produced no output')

    # 마지막 JSON 라인을 결과로 사용
    for ln in reversed(lines):
        if ln.startswith('{') and ln.endswith('}'):
            return json.loads(ln)

    raise RuntimeError(f'picker output did not contain JSON\nstdout:\n{p.stdout}')


def slice_comic_8_math(image_path: Path, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    img = Image.open(image_path)
    w, h = img.size
    
    # 4x2 (가로 4칸 x 세로 2줄) 레이아웃
    panel_w = w // 4
    panel_h = h // 2

    out_paths: list[Path] = []
    idx = 1
    for row in range(2):
        for col in range(4):
            left = col * panel_w
            top = row * panel_h
            right = (col + 1) * panel_w if col < 3 else w
            bottom = (row + 1) * panel_h if row < 1 else h
            
            crop = img.crop((left, top, right, bottom))
            out_path = out_dir / f'image_{idx}.png'
            crop.save(out_path, format='PNG')
            out_paths.append(out_path)
            idx += 1
    return out_paths


def slice_comic_8(image_path: Path, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        import cv2
        import numpy as np
    except ImportError:
        print("cv2 또는 numpy 패키지가 없어 수학적 그리드 슬라이싱으로 대체합니다.")
        return slice_comic_8_math(image_path, out_dir)

    img_cv = cv2.imread(str(image_path))
    if img_cv is None:
        return slice_comic_8_math(image_path, out_dir)

    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    
    # 이진화: 검은색 선 주변을 흰색으로 만들어 형태(윤곽선) 탐지
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

    contours, _ = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    h_img, w_img = img_cv.shape[:2]
    # 너무 작거나 큰 윤곽선 제외 (전체 화면의 5% ~ 20% 이내 패널들만 캡처)
    min_area = (h_img * w_img) * 0.05
    max_area = (h_img * w_img) * 0.20

    panels = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if min_area < w * h < max_area:
            panels.append((x, y, w, h))

    # 중복 감지된 패널 영역 제거: 큰 박스부터 처리해서 내부의 작은 박스/겹치는 박스를 필터링
    panels.sort(key=lambda p: p[2] * p[3], reverse=True)
    
    unique_panels = []
    for p in panels:
        x1, y1, w1, h1 = p
        is_duplicate = False
        
        for u in unique_panels:
            x2, y2, w2, h2 = u
            
            # 교집합 영역 계산
            ix1 = max(x1, x2)
            iy1 = max(y1, y2)
            ix2 = min(x1 + w1, x2 + w2)
            iy2 = min(y1 + h1, y2 + h2)            
            
            iw = max(0, ix2 - ix1)
            ih = max(0, iy2 - iy1)
            inter_area = iw * ih
            
            # 현재 박스(p)가 기존 큰 박스(u)와 겹치는 비율이 50% 이상이면 포함되거나 중복된 것으로 간주
            p_area = w1 * h1
            if inter_area / p_area > 0.5:
                is_duplicate = True
                break
                
        if not is_duplicate:
            unique_panels.append(p)

    # 8개의 패널이 정확히 잡히지 않으면 오리지널 수학적 슬라이싱으로 우회
    if len(unique_panels) != 8:
        print(f"정확히 8개의 패널 외곽선을 찾지 못했습니다. (찾은 개수: {len(unique_panels)}). 수학적 그리드 슬라이싱으로 대체합니다.")
        return slice_comic_8_math(image_path, out_dir)

    # 수학적 위치로 정렬 (위에서부터 2줄, 각 줄마다 왼쪽부터 정렬)
    unique_panels.sort(key=lambda p: p[1])
    row1 = sorted(unique_panels[:4], key=lambda p: p[0])
    row2 = sorted(unique_panels[4:], key=lambda p: p[0])
    sorted_panels = row1 + row2

    out_paths: list[Path] = []
    
    # 테두리 먹물 선이 이미지에 포함되지 않게 하기 위한 안쪽 마진(Margin) 픽셀 (test_slicer.py 기준 10픽셀 설정 반영)
    margin = 10
    
    for i, (x, y, w, h) in enumerate(sorted_panels, start=1):
        crop_x = x + margin
        crop_y = y + margin
        crop_w = w - (margin * 2)
        crop_h = h - (margin * 2)
        
        # 만약 너무 슬림해지면 원래 박스 크기로 복원
        if crop_w <= 0 or crop_h <= 0:
            crop_x, crop_y, crop_w, crop_h = x, y, w, h
            
        cropped = img_cv[crop_y:crop_y+crop_h, crop_x:crop_x+crop_w]
        
        out_path = out_dir / f'image_{i}.png'
        cv2.imwrite(str(out_path), cropped)
        out_paths.append(out_path)

    return out_paths


def submit_reels(json_path: Path, image_paths: list[Path]) -> dict:
    base_url = os.getenv('REELS_API_BASE_URL', 'http://zstus.synology.me:8097').rstrip('/')
    submit_path = os.getenv('REELS_SUBMIT_PATH', '/api/v1/generate-reels')
    api_key = os.getenv('REELS_API_KEY', 'test-key-12345')
    user_email = os.getenv('REELS_USER_EMAIL', 'xystus@gmail.com')

    reels = json.loads(json_path.read_text(encoding='utf-8'))

    import re
    cleaned_reels = reels.copy()
    for key, value in cleaned_reels.items():
        if key.startswith('body') and isinstance(value, str):
            # 대사 내의 (장면설명 등) 괄호 안 텍스트와 주변 공백 제거
            cleaned_reels[key] = re.sub(r'\s*\([^)]*\)\s*', ' ', value).strip()

    data = {
        'content_data': json.dumps(cleaned_reels, ensure_ascii=False),
        'user_email': user_email,
    }
    headers = {'X-API-Key': api_key} if api_key else {}

    files = {}
    handles = []
    try:
        for i, p in enumerate(image_paths, start=1):
            f = p.open('rb')
            handles.append(f)
            files[f'image_{i}'] = (p.name, f, 'image/png')

        r = requests.post(f'{base_url}{submit_path}', data=data, files=files, headers=headers, timeout=120)
        payload = r.json() if r.headers.get('content-type', '').startswith('application/json') else {'raw_text': r.text}

        if r.status_code != 200:
            raise RuntimeError(f'submit failed: {r.status_code} {payload}')

        job_id = payload.get('job_id')
        if not job_id:
            raise RuntimeError(f'job_id missing in response: {payload}')

        # 상태 폴링 대기 없이 즉시 시그널 리턴
        return {
            'submit': payload,
            'job_id': job_id,
            'final_status': 'submitted',
            'history': []
        }
    finally:
        for h in handles:
            try:
                h.close()
            except Exception:
                pass


def main() -> int:
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    run_dir = REPORTS / f'pann_reels_batch_{ts}'
    run_dir.mkdir(parents=True, exist_ok=True)

    picker = run_picker()
    json_path = Path(picker['json_path'])
    image_path = Path(picker['image_path'])

    split_dir = run_dir / 'split_images'
    split_paths = slice_comic_8(image_path, split_dir)

    result = submit_reels(json_path, split_paths)

    report = {
        'run_at': datetime.now().isoformat(timespec='seconds'),
        'picker': picker,
        'json_path': str(json_path),
        'source_image_path': str(image_path),
        'split_images': [str(p) for p in split_paths],
        'service_result': result,
    }

    report_path = run_dir / 'batch_report.json'
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

    print(json.dumps({
        'ok': True,
        'report_path': str(report_path),
        'job_id': result.get('job_id'),
        'final_status': result.get('final_status'),
        'picked_title': picker.get('picked_title'),
        'picked_url': picker.get('picked_url'),
    }, ensure_ascii=False))

    return 0 if result.get('final_status') in ('completed', 'submitted') else 1


if __name__ == '__main__':
    raise SystemExit(main())
