#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import os
import random
import re
import smtplib
import urllib.request
import urllib.error
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
from html import unescape
from pathlib import Path
from typing import List


import sqlite3

WORKSPACE = Path('/home/xystus/.openclaw/workspace')
REPORTS = WORKSPACE / 'reports'
GMAIL_ENV = Path('/home/xystus/.config/openclaw/gmail.env')
WORKSPACE_ENV = WORKSPACE / '.env'
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36'
BASE = 'https://pann.nate.com'
DEFAULT_TO = 'xystus@gmail.com'

def init_db() -> sqlite3.Connection:
    db_path = WORKSPACE / 'data.db'
    conn = sqlite3.connect(db_path)
    # Create the table using the batch script name as requested by the user
    conn.execute('''
        CREATE TABLE IF NOT EXISTS pann_reels_to_service_batch (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    return conn

@dataclass
class Post:
    section: str
    title: str
    url: str
    comments: int
    body: str

def load_env(path: Path):
    if not path.exists():
        return
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        m1 = re.match(r"^([A-Z0-9_]+)='(.*)'$", line)
        m2 = re.match(r'^([A-Z0-9_]+)="(.*)"$', line)
        m3 = re.match(r'^([A-Z0-9_]+)=(.*)$', line)
        m = m1 or m2 or m3
        if m:
            os.environ[m.group(1)] = m.group(2).strip()

def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        cs = r.headers.get_content_charset() or 'utf-8'
        return r.read().decode(cs, errors='ignore')

def clean_text(raw: str) -> str:
    txt = unescape(re.sub(r'<br\s*/?>', '\n', raw, flags=re.I))
    txt = re.sub(r'<[^>]+>', '', txt)
    txt = re.sub(r'\r', '', txt)
    txt = re.sub(r'\n{3,}', '\n\n', txt)
    return txt.strip()

def parse_today_links(home: str) -> list[tuple[str, str, int]]:
    out = []
    m = re.search(r'<div class="today-talk ellipsis">([\s\S]*?)</ul>', home)
    if not m:
        return out
    sec = m.group(1)
    pat = re.compile(r'<a href="(/talk/\d+)"[^>]*title="([^"]*)"[^>]*>.*?</a>\s*<span class="reple-num">\((\d+)\)', re.S)
    seen = set()
    for href, title, cnt in pat.findall(sec):
        url = BASE + href
        if url in seen:
            continue
        seen.add(url)
        out.append((unescape(title).strip(), url, int(cnt)))
    return out

def parse_besttalk_links(home: str) -> list[tuple[str, str, int]]:
    out = []
    m = re.search(r'<div class="best-talk ellipsis">([\s\S]*?)</div>\s*</div>\s*<!-- //베스트 톡톡 -->', home)
    sec = m.group(1) if m else ''
    if not sec:
        m2 = re.search(r'<div class="best-talk ellipsis">([\s\S]*?)<div class="navi-paging">', home)
        sec = m2.group(1) if m2 else ''
    if not sec:
        return out

    pat = re.compile(r'<a href="(https://pann\.nate\.com/talk/\d+|/talk/\d+)"[^>]*>([^<]+)</a>\s*<span class="reple-num">\((\d+)\)', re.S)
    seen = set()
    for href, title, cnt in pat.findall(sec):
        url = href if href.startswith('http') else BASE + href
        if url in seen:
            continue
        seen.add(url)
        out.append((unescape(title).strip(), url, int(cnt)))
    return out

def fetch_post_content(url: str) -> tuple[str, bool]:
    try:
        html = fetch(url)
    except Exception:
        return '', False

    m = re.search(r'<div id="contentArea">([\s\S]*?)</div>', html)
    if not m:
        return '', False

    raw = m.group(1)

    raw = re.sub(r'<script[\s\S]*?</script>', '', raw, flags=re.I)
    raw = re.sub(r'<style[\s\S]*?</style>', '', raw, flags=re.I)

    has_media = bool(re.search(r'<(img|video|iframe|object|embed|source)\b', raw, flags=re.I))

    body = clean_text(raw)
    return body, has_media

def collect_posts() -> List[Post]:
    home = fetch(BASE + '/')
    links = []
    for t, u, c in parse_today_links(home):
        links.append(('오늘의 톡', t, u, c))
    for t, u, c in parse_besttalk_links(home):
        links.append(('베스트 톡톡', t, u, c))

    uniq = {}
    for sec, t, u, c in links:
        uniq[u] = (sec, t, c)

    # DB에서 이미 처리된 URL 목록 가져오기
    conn = init_db()
    cursor = conn.cursor()
    cursor.execute('SELECT url FROM pann_reels_to_service_batch')
    generated_urls = set(row[0] for row in cursor.fetchall())
    conn.close()

    posts: List[Post] = []
    for u, (sec, t, c) in uniq.items():
        # 이미 릴스로 생성한 이력이 있는 글은 제외
        if u in generated_urls:
            continue
            
        body, has_media = fetch_post_content(u)
        body_len = len(re.sub(r'\s+', '', body))

        if body_len > 200 and not has_media:
            posts.append(Post(section=sec, title=t, url=u, comments=c, body=body))
    return posts


def pick_and_generate_reels_via_gpt(posts: List[Post]) -> tuple[Post, dict, str]:
    api_key = os.getenv('OPENAI_API_KEY', '').strip()
    if not api_key:
        raise RuntimeError('OPENAI_API_KEY가 없어 ChatGPT 대본 생성을 할 수 없습니다.')

    posts_text = []
    for i, p in enumerate(posts):
        body = p.body[:1000] + ('...' if len(p.body) > 1000 else '')
        posts_text.append(f"[Post {i}]\nTitle: {p.title}\nBody: {body}")

    content = "\n\n".join(posts_text)

    sys_prompt = """너는 100만 조회수를 지속적으로 만들어내는 상위 1% 숏폼(릴스/쇼츠) 전문 기획자이자 작가야. 아래에 제공된 [원본 포스트]의 핵심 내용을 기반으로 시청 지속 시간(Retention)과 공유/저장(Engagement)을 극대화할 수 있는 바이럴 릴스 대본을 아래 json형태로 구성해줘.

[원본포스트]의 내용을 대변할 제목을 먼저 생성해. 제목은 사람들의 관심을 확 끌 수 있게 15자 이내로 해주고, 제목에서 강조하고 싶은 부분을 '[orange:'강조하고싶은 대사']' 이렇게 표시해줘. (예: 나는 정말 [orange:감옥]에 가고싶지 않음) 대사에는 강조를 사용하지 말 것.

그리고, [원본 포스트]의 내용을 충분히 담고 있는 8개의 대사를 구성할 차례야. 먼저 쇼츠 기획의 달인인 당신의 감각을 활용하여 [원본포스트]의 내용에 적합한 릴스 전개방안을 설계해. 이야기의 흐름, 기승전결, 스토리가 중요해. 그리고, 감칠맛 나는 여러 릴스 대사 테크닉을 사용해서 각 대사를 구성해주시고, 그 대사에 부합하는 주인공의 표정이나 필요한 장면 설정을 괄호를 사용한 지문으로 추가해줘. 이때 원문에 있는 글들을 너무 축약하지 말고 충분히 반영해줘.
8번째 대사는 참여를 유도하는 질문, 단정 등으로 댓글/저장 유도를 해줘.

[출력 형식: JSON 구조]
{
  "selected_index": 선택한 Post의 번호 (예: 2),
  "title": "클릭을 유발하는 강력한 제목 (15자 이내)",
  "body1": "첫 3초 후킹 대사 (장면설명 포함)",
  "body2": "대사 (장면설명 포함)",
  "body3": "대사 (장면설명 포함)",
  "body4": "대사 (장면설명 포함)",
  "body5": "대사 (장면설명 포함)",
  "body6": "대사 (장면설명 포함)",
  "body7": "대사 (장면설명 포함)",
  "body8": "결론 요약 및 행동 유도(저장/공유/댓글) 대사 (장면설명 포함)"
}"""

    payload = {
        'model': 'gpt-4o',
        'messages': [
            {'role': 'system', 'content': sys_prompt},
            {'role': 'user', 'content': content}
        ],
        'response_format': {'type': 'json_object'},
        'temperature': 0.7
    }

    last_err = None
    for _ in range(3):
        req = urllib.request.Request(
            'https://api.openai.com/v1/chat/completions',
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}',
            },
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                data = json.loads(r.read().decode('utf-8'))
                res_content = data['choices'][0]['message']['content']
                res_json = json.loads(res_content)

                idx = res_json.get('selected_index', 0)
                if not isinstance(idx, int) or not (0 <= idx < len(posts)):
                    idx = 0

                picked_post = posts[idx]
                reels = {'title': res_json.get('title', picked_post.title)}
                for i in range(1, 9):
                    reels[f'body{i}'] = res_json.get(f'body{i}', '')

                gpt_prompt = f"[System Prompt]\n{sys_prompt}\n\n[User Prompt]\n{content}"
                return picked_post, reels, gpt_prompt

        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='replace')
            last_err = RuntimeError(f'ChatGPT 대본 생성 실패 (HTTP {e.code}): {body}')
            if e.code in (429, 500, 502, 503, 504):
                continue
            raise last_err from e

        except Exception as e:
            last_err = e

    raise RuntimeError(f'ChatGPT 대본 생성 실패: {last_err}')


def make_comic_image(out_path: Path, reels: dict) -> str:
    """Generate a single-page 8-cut comic with strong consistency constraints."""
    api_key = os.getenv('OPENAI_API_KEY', '').strip()
    if not api_key:
        raise RuntimeError('OPENAI_API_KEY가 없어 8컷 만화 이미지를 생성할 수 없습니다.')

    title = reels.get('title', '')

    scene_lines = []
    for i in range(1, 9):
        t = reels.get(f'body{i}', '').strip()
        scene_lines.append(f'{i}) {t}')

    prompt = f"""너는 백만부씩 팔리는 일본 만화작가야. 먼저 [장면내용]을 보고, 스토리를 구상해줘.
    그리고, 최신 유행하는 일본만화 스타일로 [장면내용] 대사별 컷을 그려줘.
컷은 직사각형의 동일한 크기로 여덟개를 그려주면 돼. 컷 바깥의 여백이 없도록 해줘. 각 컷은 장면번호의 지문 내용을 담고 있어야 해. 
안에 대사, 캡션, 글자, 문자는 절대 넣지 말아줘. 캐릭터의 일관성을 유지하며 다이나믹한 표정의 캐릭터를 담아줘. 

컷 순서:
[1][2][3][4]
[5][6][7][8]

[장면내용]

{chr(10).join(scene_lines)}
"""

    payload = {
        'model': 'gpt-image-1.5',
        'prompt': prompt,
        'size': '1536x1024',
        'quality': 'medium',
        'output_format': 'png',
        'n': 1
    }

    last_err = None
    for _ in range(4):
        req = urllib.request.Request(
            'https://api.openai.com/v1/images/generations',
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}',
            },
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                data = json.loads(r.read().decode('utf-8'))

            b64 = data['data'][0]['b64_json']
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(base64.b64decode(b64))
            return prompt

        except urllib.error.HTTPError as e:
            err_body = e.read().decode('utf-8', errors='replace')
            last_err = RuntimeError(f'OpenAI 이미지 생성 실패 (HTTP {e.code}): {err_body}')

            if e.code in (429, 500, 502, 503, 504):
                continue
            raise last_err from e

        except Exception as e:
            last_err = e

    raise RuntimeError(f'OpenAI 이미지 생성 실패: {last_err}')


def send_email(to_addr: str, subject: str, body: str, image_path: Path):
    user = os.getenv('GMAIL_USER')
    pw = os.getenv('GMAIL_APP_PASSWORD')
    if not user or not pw:
        raise RuntimeError('Missing GMAIL_USER or GMAIL_APP_PASSWORD')

    msg = EmailMessage()
    msg['From'] = user
    msg['To'] = to_addr
    msg['Subject'] = subject
    msg.set_content(body)

    with open(image_path, 'rb') as f:
        msg.add_attachment(f.read(), maintype='image', subtype='png', filename=image_path.name)

    with smtplib.SMTP('smtp.gmail.com', 587, timeout=30) as s:
        s.starttls()
        s.login(user, pw)
        s.send_message(msg)


def main():
    load_env(WORKSPACE_ENV)
    load_env(GMAIL_ENV)

    REPORTS.mkdir(parents=True, exist_ok=True)

    posts = collect_posts()
    if not posts:
        print('No post over 200 chars found.')
        return 0

    picked, reels, gpt_prompt = pick_and_generate_reels_via_gpt(posts)

    # 릴스 생성 완료 후 DB에 기록
    conn = init_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT INTO pann_reels_to_service_batch (url, title) VALUES (?, ?)',
            (picked.url, picked.title)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        # 이미 존재하는 경우 무시 (혹시 모를 동시 실행 방지)
        pass
    finally:
        conn.close()

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    json_path = REPORTS / f'pann_reels_{ts}.json'
    img_path = REPORTS / f'pann_reels_{ts}.png'

    json_path.write_text(json.dumps(reels, ensure_ascii=False, indent=2), encoding='utf-8')
    image_prompt = make_comic_image(img_path, reels)

    body = (
        f"선정 포스트: {picked.title}\n"
        f"섹션: {picked.section}\n"
        f"URL: {picked.url}\n\n"
        f"릴스 대본 JSON:\n{json.dumps(reels, ensure_ascii=False, indent=2)}\n\n"
        f"=========================================\n"
        f"GPT 대본 생성 프롬프트 원문:\n"
        f"{gpt_prompt}\n\n"
        f"=========================================\n"
        f"이미지 생성 프롬프트 원문:\n"
        f"{image_prompt}\n"
    )

    send_email(DEFAULT_TO, f"[Daily Pann Reels] {datetime.now().strftime('%Y-%m-%d')}", body, img_path)

    print(json.dumps({
        'picked_title': picked.title,
        'picked_url': picked.url,
        'json_path': str(json_path),
        'image_path': str(img_path),
        'sent_to': DEFAULT_TO,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())