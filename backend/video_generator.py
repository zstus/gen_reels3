import os
import requests
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import *
import uuid
import tempfile
from gtts import gTTS
import re
import base64
import json
import random
import math

class VideoGenerator:
    def __init__(self):
        self.video_width = 414
        self.video_height = 896  # 스마트폰 해상도 (414x896)
        self.fps = 30
        self.font_path = os.path.join(os.path.dirname(__file__), "font", "BMYEONSUNG_otf.otf")
        
        # Naver Clova Voice 설정 (환경변수에서 가져오기)
        self.naver_client_id = os.getenv('NAVER_CLIENT_ID')
        self.naver_client_secret = os.getenv('NAVER_CLIENT_SECRET')
        
        # Microsoft Azure Speech 설정
        self.azure_speech_key = os.getenv('AZURE_SPEECH_KEY')
        self.azure_speech_region = os.getenv('AZURE_SPEECH_REGION', 'koreacentral')
        
    def get_emoji_font(self):
        """이모지 지원 폰트 경로 반환"""
        emoji_fonts = [
            "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
            "/System/Library/Fonts/Apple Color Emoji.ttc",
            "/Windows/Fonts/seguiemj.ttf",
            "/usr/share/fonts/truetype/noto/NotoEmoji-Regular.ttf"
        ]
        
        for font_path in emoji_fonts:
            if os.path.exists(font_path):
                return font_path
        return None
    
    def has_emoji(self, text):
        """텍스트에 이모지가 포함되어 있는지 확인"""
        emoji_pattern = re.compile(
            "[\U0001F600-\U0001F64F"  # 감정 표현
            "\U0001F300-\U0001F5FF"  # 기호 및 그림문자
            "\U0001F680-\U0001F6FF"  # 교통 및 지도 기호
            "\U0001F1E0-\U0001F1FF"  # 국기
            "\U00002600-\U000026FF"  # 기타 기호
            "\U00002700-\U000027BF"  # 장식 기호
            "\U0001F900-\U0001F9FF"  # 추가 그림문자
            "\U0001FA70-\U0001FAFF"  # 확장된 그림문자-A
            "]+", re.UNICODE)
        return emoji_pattern.search(text) is not None
    
    def split_text_and_emoji(self, text):
        """텍스트와 이모지를 분리"""
        emoji_pattern = re.compile(
            "[\U0001F600-\U0001F64F"
            "\U0001F300-\U0001F5FF"
            "\U0001F680-\U0001F6FF"
            "\U0001F1E0-\U0001F1FF"
            "\U00002600-\U000026FF"
            "\U00002700-\U000027BF"
            "\U0001F900-\U0001F9FF"
            "\U0001FA70-\U0001FAFF"
            "]", re.UNICODE)
        
        parts = []
        last_end = 0
        
        for match in emoji_pattern.finditer(text):
            if match.start() > last_end:
                parts.append(('text', text[last_end:match.start()]))
            parts.append(('emoji', match.group()))
            last_end = match.end()
        
        if last_end < len(text):
            parts.append(('text', text[last_end:]))
        
        return parts
    
    def draw_text_with_emoji(self, draw, text, x, y, text_font, emoji_font, color):
        """텍스트와 이모지를 함께 렌더링"""
        parts = self.split_text_and_emoji(text)
        current_x = x
        
        for part_type, content in parts:
            if part_type == 'text' and content.strip():
                draw.text((current_x, y), content, font=text_font, fill=color)
                bbox = draw.textbbox((0, 0), content, font=text_font)
                current_x += bbox[2] - bbox[0]
            elif part_type == 'emoji':
                # 이모지 폰트가 있으면 사용, 없으면 기본 폰트로 시도
                if emoji_font:
                    try:
                        draw.text((current_x, y + 2), content, font=emoji_font, fill=color)
                        bbox = draw.textbbox((0, 0), content, font=emoji_font)
                    except:
                        # 이모지 폰트 실패시 기본 폰트로 시도
                        draw.text((current_x, y), content, font=text_font, fill=color)
                        bbox = draw.textbbox((0, 0), content, font=text_font)
                else:
                    # 이모지 폰트가 없으면 기본 폰트로 시도
                    draw.text((current_x, y), content, font=text_font, fill=color)
                    bbox = draw.textbbox((0, 0), content, font=text_font)
                
                current_x += bbox[2] - bbox[0]
        
    def create_fallback_image(self, width=1920, height=1080, color_index=0):
        """인터넷 연결 없이 기본 이미지 생성"""
        try:
            # 다양한 색상 팔레트
            colors = [
                (255, 87, 51),   # 주황색
                (51, 255, 87),   # 초록색  
                (51, 87, 255),   # 파란색
                (255, 51, 245),  # 자주색
                (255, 195, 0),   # 노란색
                (0, 195, 255),   # 하늘색
            ]
            
            color = colors[color_index % len(colors)]
            
            # 이미지 생성
            img = Image.new('RGB', (width, height), color=color)
            draw = ImageDraw.Draw(img)
            
            # 텍스트 추가
            try:
                font = ImageFont.truetype(self.font_path, 60)
            except:
                font = ImageFont.load_default()
            
            text = f"배경 이미지 {color_index + 1}"
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (width - text_width) // 2
            y = (height - text_height) // 2
            
            # 텍스트 그림자
            draw.text((x + 2, y + 2), text, font=font, fill=(0, 0, 0))
            # 흰색 텍스트
            draw.text((x, y), text, font=font, fill=(255, 255, 255))
            
            # 임시 파일로 저장
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            img.save(temp_file.name, "JPEG", quality=85)
            temp_file.close()
            
            print(f"기본 이미지 생성 완료: {temp_file.name}")
            return temp_file.name
            
        except Exception as e:
            print(f"기본 이미지 생성 실패: {e}")
            return None

    def download_image(self, image_url):
        """이미지 URL에서 이미지 다운로드 (fallback 포함)"""
        try:
            print(f"이미지 다운로드 시도: {image_url}")
            
            # 타임아웃과 헤더 추가
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(image_url, headers=headers, timeout=10)  # 타임아웃 단축
            
            print(f"응답 상태: {response.status_code}")
            response.raise_for_status()
            
            # 이미지 콘텐츠 유효성 검사
            if len(response.content) < 1000:
                raise Exception(f"이미지 파일이 너무 작습니다: {len(response.content)} bytes")
            
            # 임시 파일로 저장
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            temp_file.write(response.content)
            temp_file.close()
            
            print(f"이미지 다운로드 완료: {temp_file.name} ({len(response.content)} bytes)")
            return temp_file.name
            
        except Exception as e:
            print(f"이미지 다운로드 실패 ({str(e)}), 기본 이미지로 대체")
            # URL에서 색상 인덱스 추출 시도
            color_index = 0
            try:
                if "Image+1" in image_url or "random=1" in image_url:
                    color_index = 0
                elif "Image+2" in image_url or "random=2" in image_url:
                    color_index = 1
                elif "Image+3" in image_url or "random=3" in image_url:
                    color_index = 2
                elif "Image+4" in image_url or "random=4" in image_url:
                    color_index = 3
            except:
                pass
                
            fallback_image = self.create_fallback_image(1920, 1080, color_index)
            if fallback_image:
                return fallback_image
            else:
                raise Exception(f"이미지 다운로드 및 기본 이미지 생성 모두 실패: {str(e)}")
    
    def create_title_image(self, title, width, height):
        """제목 이미지 생성"""
        # 검은 배경 이미지 생성
        img = Image.new('RGB', (width, height), color='black')
        draw = ImageDraw.Draw(img)
        
        # 한글 폰트 설정 (2배 크기로)
        try:
            font = ImageFont.truetype(self.font_path, 48)  # 24 → 48로 2배 크기
        except Exception as e:
            print(f"폰트 로드 실패: {e}")
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
            except:
                font = ImageFont.load_default()
        
        # 텍스트를 여러 줄로 나누기 (긴 제목 처리)
        words = title.split(' ')
        lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + " " + word if current_line else word
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] < width - 40:  # 좌우 여백 20씩
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        # 이모지 폰트 준비 (제목 폰트 크기에 맞춤)
        emoji_font_path = self.get_emoji_font()
        emoji_font = None
        if emoji_font_path:
            try:
                emoji_font = ImageFont.truetype(emoji_font_path, 44)  # 22 → 44로 2배 증가
            except:
                emoji_font = None
        
        # 텍스트 중앙 정렬 (폰트 크기에 맞춘 줄간격)
        line_height = 45  # 48px 폰트에 맞춘 적정 줄간격
        total_height = len(lines) * line_height
        start_y = (height - total_height) // 2
        
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x = (width - text_width) // 2
            y = start_y + i * line_height
            
            # 일단 기본 폰트로 텍스트 렌더링 (이모지 포함)
            try:
                draw.text((x, y), line, font=font, fill='white')
            except Exception as e:
                print(f"텍스트 렌더링 오류: {e}")
                # 폴백으로 기본 폰트 사용
                default_font = ImageFont.load_default()
                draw.text((x, y), line, font=default_font, fill='white')
        
        # 임시 파일로 저장
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        img.save(temp_file.name, "PNG")
        temp_file.close()
        
        return temp_file.name
    
    def create_simple_group_clip(self, image_path, group_segments, total_duration, title_image_path=None, text_position="bottom"):
        """간단한 그룹 클립 생성 (uploads 폴더용)"""
        print(f"    🔧 간단한 그룹 클립 생성: {total_duration:.1f}초")
        
        # 1. 연속 배경 이미지 (전체 그룹 시간동안)
        bg_clip = self.create_continuous_background_clip(image_path, total_duration)
        
        # 2. 상단 검은 영역 (전체 시간)
        black_top = ColorClip(size=(self.video_width, 180), color=(0,0,0))
        black_top = black_top.set_duration(total_duration).set_position((0, 0))
        
        # 3. 제목 클립 설정
        if title_image_path and os.path.exists(title_image_path):
            title_clip = ImageClip(title_image_path).set_duration(total_duration).set_position((0, 0))
        else:
            title_clip = None
        
        # 4. 각 텍스트를 시간별로 배치
        text_clips = []
        current_time = 0.0
        
        for body_key, body_text, tts_path, clip_duration in group_segments:
            text_image_path = self.create_text_image(body_text, self.video_width, self.video_height - 180, text_position, text_style)
            text_clip = ImageClip(text_image_path).set_start(current_time).set_duration(clip_duration).set_position((0, 180))
            text_clips.append(text_clip)
            current_time += clip_duration
        
        # 5. 합성
        composition_clips = [bg_clip, black_top]
        if title_clip:
            composition_clips.append(title_clip)
        composition_clips.extend(text_clips)
        
        group_final = CompositeVideoClip(composition_clips, size=(self.video_width, self.video_height))
        
        return group_final

    def create_truly_continuous_group_clip(self, image_path, group_segments, total_duration, title_image_path, text_position="bottom"):
        """그룹 내에서 정말 끊기지 않는 연속 클립 생성"""
        print(f"    🔧 연속 그룹 클립 생성: {total_duration:.1f}초")
        
        # 1. 연속 배경 이미지 (전체 그룹 시간동안 - 끊기지 않음!)
        bg_clip = self.create_continuous_background_clip(image_path, total_duration)
        
        # 2. 상단 검은 영역 (전체 시간)
        black_top = ColorClip(size=(self.video_width, 180), color=(0,0,0))
        black_top = black_top.set_duration(total_duration).set_position((0, 0))
        
        # 3. 제목 (전체 시간)
        title_clip = ImageClip(title_image_path).set_duration(total_duration).set_position((0, 0))
        
        # 4. 간단한 방법: 각 텍스트를 시간별로 배치
        text_clips = []
        current_time = 0.0
        
        for body_key, body_text, tts_path, clip_duration in group_segments:
            text_image_path = self.create_text_image(body_text, self.video_width, self.video_height - 180, text_position, text_style)
            text_clip = ImageClip(text_image_path).set_start(current_time).set_duration(clip_duration).set_position((0, 180))
            text_clips.append(text_clip)
            current_time += clip_duration
        
        # 5. 합성 (배경은 연속, 텍스트만 시간별로)
        group_final = CompositeVideoClip([
            bg_clip,     # 연속 배경
            black_top,   # 상단
            title_clip,  # 제목
        ] + text_clips, size=(self.video_width, self.video_height))
        
        return group_final
    
    def create_text_image(self, text, width, height, text_position="bottom", text_style="outline"):
        """텍스트 이미지 생성 (배경 박스 포함)"""
        # 투명 배경 이미지 생성
        img = Image.new('RGBA', (width, height), color=(0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # 한글 폰트 설정 (바디 텍스트용, 36pt로 조정)
        try:
            font = ImageFont.truetype(self.font_path, 36)  # 36pt로 설정
        except Exception as e:
            print(f"폰트 로드 실패: {e}")
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
            except:
                font = ImageFont.load_default()
        
        # 텍스트를 여러 줄로 나누기
        words = text.split(' ')
        lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + " " + word if current_line else word
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] < width - 60:  # 여백 고려 (좌우 30씩)
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        # 전체 텍스트 박스 크기 계산 (폰트 크기에 맞춘 줄간격)
        line_height = 40  # 36pt 폰트에 맞춘 적정 줄간격
        total_height = len(lines) * line_height
        padding = 20  # 패딩 조정
        
        # 텍스트 위치 계산 (body 자막 영역 4등분 방식)
        # 전체 높이: 896px, 타이틀 영역: 180px, body 자막 영역: 716px
        # body 영역을 4등분: 179px씩 4개 영역, 위에서 3개만 사용
        
        title_height = 180  # 타이틀 영역 높이 (고정)
        body_area_height = height - title_height  # 716px (body 자막 사용 가능 영역)
        zone_height = body_area_height // 4  # 179px (각 영역 높이)
        
        if text_position == "top":
            # 상: 1번째 영역의 가운데 (180 + 179/2 = 180 + 89.5 ≈ 269px)
            zone_center_y = title_height + (zone_height // 2)
            start_y = zone_center_y - (total_height // 2)
        elif text_position == "middle":
            # 중: 2번째 영역의 가운데 (180 + 179 + 179/2 = 180 + 268.5 ≈ 448px)
            zone_center_y = title_height + zone_height + (zone_height // 2)
            start_y = zone_center_y - (total_height // 2)
        else:  # bottom (기본값)
            # 하: 3번째 영역의 가운데 (180 + 179*2 + 179/2 = 180 + 447.5 ≈ 627px)
            zone_center_y = title_height + (zone_height * 2) + (zone_height // 2)
            start_y = zone_center_y - (total_height // 2)
        
        # 최소값 보장 (타이틀 영역 침범 방지)
        start_y = max(start_y, title_height + padding)
        
        # 이모지 폰트 준비 (본문 폰트 크기에 맞춤)
        emoji_font_path = self.get_emoji_font()
        emoji_font = None
        if emoji_font_path:
            try:
                emoji_font = ImageFont.truetype(emoji_font_path, 32)  # 36pt 본문에 맞춘 이모지 크기
            except:
                emoji_font = None
        
        # text_style에 따른 텍스트 렌더링
        if text_style == "background":
            # 반투명 배경 스타일
            self._render_text_with_background(draw, lines, font, emoji_font, width, start_y, line_height)
        else:
            # 외곽선 스타일 (기본값)
            self._render_text_with_outline(draw, lines, font, emoji_font, width, start_y, line_height)
        
        # 임시 파일로 저장
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        img.save(temp_file.name, "PNG")
        temp_file.close()
        
        return temp_file.name
    
    def _render_text_with_outline(self, draw, lines, font, emoji_font, width, start_y, line_height):
        """외곽선 스타일로 텍스트 렌더링 (기존 방식)"""
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x = (width - text_width) // 2
            y = start_y + i * line_height
            
            # 텍스트 렌더링 (부드러운 외곽선 효과)
            try:
                # 더 부드러운 외곽선 (2px 두께)
                outline_positions = [
                    (-2, -2), (-2, -1), (-2, 0), (-2, 1), (-2, 2),
                    (-1, -2), (-1, -1), (-1, 0), (-1, 1), (-1, 2),
                    (0, -2), (0, -1),           (0, 1), (0, 2),
                    (1, -2), (1, -1), (1, 0), (1, 1), (1, 2),
                    (2, -2), (2, -1), (2, 0), (2, 1), (2, 2)
                ]
                
                # 검은색 외곽선 그리기
                for dx, dy in outline_positions:
                    draw.text((x + dx, y + dy), line, font=font, fill='black')
                
                # 흰색 텍스트 (중앙)
                draw.text((x, y), line, font=font, fill='white')
                
            except Exception as e:
                print(f"본문 텍스트 렌더링 오류: {e}")
                # 폴백: 기본 외곽선
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        if dx != 0 or dy != 0:
                            draw.text((x + dx, y + dy), line, font=font, fill='black')
                draw.text((x, y), line, font=font, fill='white')
    
    def _render_text_with_background(self, draw, lines, font, emoji_font, width, start_y, line_height):
        """반투명 배경 스타일로 텍스트 렌더링"""
        # 전체 텍스트 영역 크기 계산
        max_text_width = 0
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            if text_width > max_text_width:
                max_text_width = text_width
        
        # 배경 박스 크기와 위치 계산
        padding_x = 20  # 좌우 패딩
        padding_y = 10  # 상하 패딩
        background_width = max_text_width + padding_x * 2
        background_height = len(lines) * line_height + padding_y * 2
        
        background_x = (width - background_width) // 2
        background_y = start_y - padding_y
        
        # 반투명 검은 배경 직접 그리기
        draw.rectangle(
            [background_x, background_y, background_x + background_width, background_y + background_height],
            fill=(0, 0, 0, 178)  # 검은색 70% 투명도
        )
        
        # 텍스트 렌더링 (배경 위에 흰색 텍스트)
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x = (width - text_width) // 2
            y = start_y + i * line_height
            
            # 흰색 텍스트 (배경이 있으므로 외곽선 불필요)
            draw.text((x, y), line, font=font, fill='white')
    
    def crop_to_square(self, image_path):
        """이미지를 중앙 기준 정사각형으로 크롭하여 716x716으로 리사이즈"""
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                print(f"🔳 이미지 로드: {image_path} ({width}x{height})")
                
                # 이미 716x716인 경우 그대로 반환
                if width == 716 and height == 716:
                    print(f"🔳 이미 716x716: 변환 불필요")
                    return image_path
                
                # 짧은 변을 기준으로 정사각형 크기 결정
                crop_size = min(width, height)
                
                # 중앙 기준 크롭 좌표 계산
                left = (width - crop_size) // 2
                top = (height - crop_size) // 2
                right = left + crop_size
                bottom = top + crop_size
                
                # 크롭 실행 (정사각형이 아닌 경우만)
                if width != height:
                    cropped_img = img.crop((left, top, right, bottom))
                    print(f"🔳 크롭 실행: {width}x{height} → {crop_size}x{crop_size}")
                else:
                    cropped_img = img.copy()
                    print(f"🔳 정사각형 이미지: 크롭 생략")
                
                # 항상 716x716으로 리사이즈 (PIL 버전 호환성 고려)
                try:
                    # Pillow 10.0.0+ 버전
                    resized_img = cropped_img.resize((716, 716), Image.Resampling.LANCZOS)
                except AttributeError:
                    # 이전 버전 호환성
                    resized_img = cropped_img.resize((716, 716), Image.LANCZOS)
                
                # RGBA 모드인 경우 RGB로 변환 (JPEG 저장 위해)
                if resized_img.mode in ('RGBA', 'LA', 'P'):
                    # 흰색 배경으로 변환
                    background = Image.new('RGB', resized_img.size, (255, 255, 255))
                    if resized_img.mode == 'P':
                        resized_img = resized_img.convert('RGBA')
                    background.paste(resized_img, mask=resized_img.split()[-1] if resized_img.mode in ('RGBA', 'LA') else None)
                    resized_img = background
                    print(f"🔳 RGBA → RGB 변환 완료")
                
                # 임시 파일로 저장
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
                resized_img.save(temp_file.name, 'JPEG', quality=95)
                
                print(f"🔳 최종 리사이즈: → 716x716")
                print(f"🔳 임시 파일 생성: {temp_file.name}")
                
                return temp_file.name
                
        except Exception as e:
            print(f"❌ 이미지 변환 에러: {image_path}")
            print(f"❌ 에러 내용: {str(e)}")
            # 에러 발생시 원본 파일 그대로 반환
            return image_path

    def easing_function(self, p):
        """더욱 부드러운 이징 함수 (cubic ease-in-out)"""
        if p < 0.5:
            return 4 * p * p * p
        else:
            return 1 - pow(-2 * p + 2, 3) / 2
    
    def linear_easing_function(self, p):
        """일정한 속도의 선형 이징 함수 (패닝 전용)"""
        return p

    def create_background_clip(self, image_path, duration):
        """3가지 Ken Burns 효과 중 랜덤 선택 - 정사각형 크롭 + 패턴 적용"""
        print(f"🎬 배경 클립 생성 시작: {image_path} (duration: {duration:.1f}s)")
        
        # 이미지를 정사각형으로 크롭 후 716x716으로 리사이즈
        square_image_path = self.crop_to_square(image_path)
        
        try:
            # 배경 클립 생성
            bg_clip = ImageClip(square_image_path).set_duration(duration)
            
            # 타이틀 아래 영역 계산 (타이틀 높이 180px)
            title_height = 180
            
            # 2가지 패닝 패턴 중 랜덤 선택 (확대 패턴 제거)
            pattern = random.randint(1, 2)
            
            # 모든 클립에 패닝 적용 (3초 미만 포함)
            if pattern == 1:
                # 패턴 1: 좌 → 우 패닝 (Linear 이징 + 60px 이동 범위)
                def left_to_right(t):
                    progress = self.linear_easing_function(t / duration)  # 일정한 속도
                    # 302px 여유공간에서 60px 이동 (더 명확한 패닝 효과)
                    x_offset = -(151 - 60 * progress)  # 왼쪽에서 오른쪽으로 60px 이동
                    return (x_offset, title_height)
                
                bg_clip = bg_clip.set_position(left_to_right)
                print(f"🎬 패턴 1: 좌 → 우 패닝 (duration: {duration:.1f}s)")
                
            else:
                # 패턴 2: 우 → 좌 패닝 (Linear 이징 + 60px 이동 범위)
                def right_to_left(t):
                    progress = self.linear_easing_function(t / duration)  # 일정한 속도
                    # 302px 여유공간에서 60px 이동 (더 명확한 패닝 효과)
                    x_offset = -(151 - 60 * (1 - progress))  # 오른쪽에서 왼쪽으로 60px 이동
                    return (x_offset, title_height)
                
                bg_clip = bg_clip.set_position(right_to_left)
                print(f"🎬 패턴 2: 우 → 좌 패닝 (duration: {duration:.1f}s)")
            
            return bg_clip
                
        except Exception as e:
            print(f"❌ 배경 클립 생성 에러: {str(e)}")
            # 에러 발생시 기본 클립 반환
            fallback_clip = ImageClip(image_path).set_duration(duration)
            fallback_clip = fallback_clip.resize(height=716).set_position((0, 180))
            return fallback_clip
            
        finally:
            # 임시 파일 정리
            if square_image_path != image_path and os.path.exists(square_image_path):
                try:
                    os.unlink(square_image_path)
                    print(f"🗑️ 임시 파일 정리: {square_image_path}")
                except:
                    pass


    
    def create_continuous_background_clip(self, image_path, total_duration, start_offset=0.0):
        """2개 body 동안 연속적으로 움직이는 배경 클립 생성 - 3가지 패턴 중 랜덤 선택"""
        print(f"🎬 연속 배경 클립 생성: {image_path} (duration: {total_duration:.1f}s, offset: {start_offset:.1f}s)")
        
        # 이미지를 정사각형으로 크롭 후 716x716으로 리사이즈
        square_image_path = self.crop_to_square(image_path)
        
        try:
            # 배경 클립 생성
            bg_clip = ImageClip(square_image_path).set_duration(total_duration)
            
            # 타이틀 아래 영역 계산
            title_height = 180
            
            # 2가지 패닝 패턴 중 랜덤 선택 (확대 패턴 제거)
            pattern = random.randint(1, 2)
            
            # 모든 연속 클립에 패닝 적용 (3초 미만 포함)
            if pattern == 1:
                # 패턴 1: 연속 좌 → 우 패닝 (Linear 이징 + 60px 이동)
                def continuous_left_to_right(t):
                    # 전체 지속 시간에 대한 진행도
                    progress = self.linear_easing_function(t / total_duration)  # 일정한 속도
                    # 60px 이동 범위로 확대
                    x_offset = -(151 - 60 * progress)
                    return (x_offset, title_height)
                
                bg_clip = bg_clip.set_position(continuous_left_to_right)
                print(f"🎬 연속 패턴 1: 좌 → 우 패닝 (duration: {total_duration:.1f}s)")
                
            else:
                # 패턴 2: 연속 우 → 좌 패닝 (Linear 이징 + 60px 이동)
                def continuous_right_to_left(t):
                    # 전체 지속 시간에 대한 진행도
                    progress = self.linear_easing_function(t / total_duration)  # 일정한 속도
                    # 60px 이동 범위로 확대 (반대 방향)
                    x_offset = -(151 - 60 * (1 - progress))
                    return (x_offset, title_height)
                
                bg_clip = bg_clip.set_position(continuous_right_to_left)
                print(f"🎬 연속 패턴 2: 우 → 좌 패닝 (duration: {total_duration:.1f}s)")
            
            return bg_clip
                
        except Exception as e:
            print(f"❌ 연속 배경 클립 에러: {str(e)}")
            # 에러 발생시 기본 클립 반환
            fallback_clip = ImageClip(image_path).set_duration(total_duration)
            fallback_clip = fallback_clip.resize(height=716).set_position((0, 180))
            return fallback_clip
            
        finally:
            # 임시 파일 정리
            if square_image_path != image_path and os.path.exists(square_image_path):
                try:
                    os.unlink(square_image_path)
                    print(f"🗑️ 연속 임시 파일 정리: {square_image_path}")
                except:
                    pass

    
    def create_video_background_clip(self, video_path, duration):
        """비디오 배경 클립 생성 - 414px 폭으로 리사이즈 후 타이틀 아래 중앙정렬"""
        from moviepy.editor import VideoFileClip, ColorClip, CompositeVideoClip
        
        try:
            print(f"🎬 비디오 배경 클립 생성 시작: {video_path}")
            
            # 비디오 파일 로드
            video_clip = VideoFileClip(video_path)
            
            # 타이틀 아래 영역 계산 (타이틀 높이 180px)
            title_height = 180
            available_height = self.video_height - title_height  # 896 - 180 = 716px
            
            # 비디오 원본 크기
            orig_width = video_clip.w
            orig_height = video_clip.h
            
            print(f"📐 비디오 원본: {orig_width}x{orig_height}")
            print(f"🎯 목표: 폭 414px로 리사이즈 후 타이틀 아래 중앙정렬")
            
            # 1단계: 전체 배경을 검은색으로 채우기
            black_background = ColorClip(size=(self.video_width, available_height), 
                                       color=(0,0,0), duration=duration)
            black_background = black_background.set_position((0, title_height))
            
            # 2단계: 비디오를 414px 폭으로 리사이즈 (종횡비 유지)
            if orig_width < self.video_width:
                print(f"📈 비디오 폭 확장 필요: {orig_width}px → {self.video_width}px")
                # 작은 비디오는 414px로 확장 (종횡비 유지)
                video_clip = video_clip.resize(width=self.video_width)
            elif orig_width > self.video_width:
                print(f"📉 비디오 폭 축소 필요: {orig_width}px → {self.video_width}px")
                # 큰 비디오는 414px로 축소 (종횡비 유지)
                video_clip = video_clip.resize(width=self.video_width)
            else:
                print(f"✅ 비디오 폭 이미 적정: {orig_width}px = {self.video_width}px")
            
            resized_height = video_clip.h
            print(f"🔧 리사이즈 완료: {self.video_width}x{resized_height}")
            
            # 3단계: 비디오 길이 조정
            if video_clip.duration > duration:
                video_clip = video_clip.subclip(0, duration)
                print(f"⏂ 비디오 길이 조정: {duration}초로 잘라냄")
            elif video_clip.duration < duration:
                last_frame_time = max(video_clip.duration - 0.1, 0)
                last_frame = video_clip.to_ImageClip(t=last_frame_time)
                extension_duration = duration - video_clip.duration
                extension_clip = last_frame.set_duration(extension_duration)
                video_clip = CompositeVideoClip([video_clip, extension_clip.set_start(video_clip.duration)])
                print(f"⏩ 비디오 길이 연장: {duration}초까지 마지막 프레임으로 채움")
            
            # 4단계: 타이틀 바로 아래에 중앙정렬로 위치 설정
            x_center = 0  # 가로는 이미 414px로 맞춤
            y_position = title_height  # 타이틀 바로 아래
            
            video_clip = video_clip.set_position((x_center, y_position))
            
            # 5단계: 검은 배경 위에 비디오 합성
            final_clip = CompositeVideoClip([black_background, video_clip])
            
            print(f"✅ 완성: 검은배경({self.video_width}x{available_height}) + 비디오({self.video_width}x{resized_height})")
            print(f"🎉 비디오 배경 클립 생성 완료!")
            
            return final_clip
            
        except Exception as e:
            print(f"❌ 비디오 배경 클립 생성 실패: {e}")
            import traceback
            traceback.print_exc()
            
            # 실패 시 검은 화면으로 대체
            title_height = 180
            available_height = self.video_height - title_height
            fallback_clip = ColorClip(size=(self.video_width, available_height), 
                                    color=(0,0,0), duration=duration)
            fallback_clip = fallback_clip.set_position((0, title_height))
            print(f"🔄 검은 화면으로 대체: {self.video_width}x{available_height}")
            return fallback_clip
    
    def create_tts_with_naver(self, text):
        """네이버 Clova Voice TTS 생성"""
        if not self.naver_client_id or not self.naver_client_secret:
            return None
            
        try:
            print(f"네이버 TTS 생성 중: {text[:50]}...")
            
            # Naver Clova Voice API 호출
            url = "https://naveropenapi.apigw.ntruss.com/tts-premium/v1/tts"
            headers = {
                "X-NCP-APIGW-API-KEY-ID": self.naver_client_id,
                "X-NCP-APIGW-API-KEY": self.naver_client_secret,
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            data = {
                "speaker": "nara",  # 여성 음성 (clara, matt, shinji, nara 등 선택 가능)
                "volume": "0",      # 볼륨 (-5~5)
                "speed": "0",       # 속도 (-5~5)
                "pitch": "0",       # 음높이 (-5~5)
                "format": "mp3",    # 출력 포맷
                "text": text
            }
            
            response = requests.post(url, headers=headers, data=data)
            
            if response.status_code == 200:
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                temp_file.write(response.content)
                temp_file.close()
                print(f"네이버 TTS 생성 완료: {temp_file.name}")
                return temp_file.name
            else:
                print(f"네이버 TTS API 오류: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"네이버 TTS 생성 실패: {e}")
            return None
    
    def create_tts_with_azure(self, text):
        """Microsoft Azure Cognitive Services TTS 생성"""
        if not self.azure_speech_key:
            return None
            
        try:
            print(f"Azure TTS 생성 중: {text[:50]}...")
            
            # Azure Cognitive Services Speech API 호출
            url = f"https://{self.azure_speech_region}.tts.speech.microsoft.com/cognitiveservices/v1"
            headers = {
                "Ocp-Apim-Subscription-Key": self.azure_speech_key,
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3"
            }
            
            # SSML 형식으로 요청 생성 (한국어 여성 음성)
            ssml = f"""<speak version='1.0' xml:lang='ko-KR'>
                <voice xml:lang='ko-KR' xml:gender='Female' name='ko-KR-SunHiNeural'>
                    <prosody rate='medium' pitch='medium'>
                        {text}
                    </prosody>
                </voice>
            </speak>"""
            
            response = requests.post(url, headers=headers, data=ssml.encode('utf-8'))
            
            if response.status_code == 200:
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                temp_file.write(response.content)
                temp_file.close()
                print(f"Azure TTS 생성 완료: {temp_file.name}")
                return temp_file.name
            else:
                print(f"Azure TTS API 오류: {response.status_code}, {response.text}")
                return None
                
        except Exception as e:
            print(f"Azure TTS 생성 실패: {e}")
            return None
    
    def create_tts_audio(self, text, lang='ko'):
        """Google TTS로 최적화된 한국어 음성 생성 - 30% 빠른 속도 적용"""
        try:
            print(f"Google TTS 생성 중: {text[:50]}...")
            
            # 한국어 텍스트 전처리 (더 자연스럽게)
            processed_text = self.preprocess_korean_text(text)
            
            # 최적화된 한국어 Google TTS 설정
            tts = gTTS(
                text=processed_text, 
                lang='ko',  # 명시적으로 한국어 설정
                slow=False,
                tld='com'   # 구글 도메인 최적화
            )
            
            # 임시 파일에 저장 (원본 속도)
            original_temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            tts.save(original_temp_file.name)
            original_temp_file.close()
            print(f"Google TTS 원본 생성 완료: {original_temp_file.name}")
            
            # 40% 빠르게 속도 조정
            speed_adjusted_file = self.speed_up_audio(original_temp_file.name, speed_factor=1.4)
            
            # 속도 조정이 실패하면 원본 파일 사용, 성공하면 원본 파일만 정리
            if speed_adjusted_file != original_temp_file.name and os.path.exists(speed_adjusted_file):
                # 속도 조정 성공: 새로운 파일이 생성됨, 원본 파일만 정리
                if os.path.exists(original_temp_file.name):
                    os.unlink(original_temp_file.name)
                    print(f"🗑️ 원본 TTS 파일 정리: {original_temp_file.name}")
                print(f"Google TTS 생성 완료 (40% 고속화): {speed_adjusted_file}")
            else:
                # 속도 조정 실패: 원본 파일 그대로 사용 (삭제하지 않음)
                print(f"Google TTS 생성 완료 (원본 속도): {speed_adjusted_file}")
            
            return speed_adjusted_file
            
        except Exception as e:
            print(f"TTS 생성 실패: {e}")
            return None
    
    def speed_up_audio(self, audio_path, speed_factor=1.4):
        """고급 오디오 속도 조정 (다중 알고리즘 지원)"""
        try:
            print(f"🎵 고급 오디오 속도 조정 시작: {speed_factor}x 속도")
            
            # 방법 1: FFmpeg 직접 사용 (가장 안정적)
            try:
                return self._speed_up_with_ffmpeg(audio_path, speed_factor)
            except Exception as e:
                print(f"⚠️ FFmpeg 방법 실패: {e}")
            
            # 방법 2: MoviePy 다중 방식
            try:
                return self._speed_up_with_moviepy(audio_path, speed_factor)
            except Exception as e:
                print(f"⚠️ MoviePy 방법 실패: {e}")
            
            # 방법 3: Pydub 사용
            try:
                return self._speed_up_with_pydub(audio_path, speed_factor)
            except Exception as e:
                print(f"⚠️ Pydub 방법 실패: {e}")
            
            # 방법 4: 샘플링 기반 간단한 속도 조정
            try:
                return self._speed_up_with_sampling(audio_path, speed_factor)
            except Exception as e:
                print(f"⚠️ 샘플링 방법 실패: {e}")
            
            print(f"❌ 모든 속도 조정 방법 실패, 원본 파일 사용: {audio_path}")
            return audio_path
            
        except Exception as e:
            print(f"❌ 오디오 속도 조정 전체 실패: {e}")
            return audio_path

    def _speed_up_with_ffmpeg(self, audio_path, speed_factor):
        """방법 1: FFmpeg를 직접 사용한 고품질 속도 조정"""
        print(f"🔧 FFmpeg 방식 속도 조정 시도...")
        
        import subprocess
        import shutil
        
        # FFmpeg 설치 확인
        if not shutil.which('ffmpeg'):
            raise Exception("FFmpeg가 설치되지 않았습니다")
        
        # 출력 파일 생성
        speed_adjusted_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        speed_adjusted_file.close()
        
        # FFmpeg 명령어로 속도 조정 (atempo 필터 사용)
        # atempo는 피치 변경 없이 속도만 조정 (최대 2.0배까지)
        if speed_factor <= 2.0:
            atempo_filter = f"atempo={speed_factor}"
        else:
            # 2.0배 초과시 여러 단계로 나눔
            atempo_filter = "atempo=2.0,atempo=" + str(speed_factor / 2.0)
        
        cmd = [
            'ffmpeg', '-y',  # 덮어쓰기 허용
            '-i', audio_path,
            '-filter:a', atempo_filter,
            '-loglevel', 'error',  # 에러만 출력
            speed_adjusted_file.name
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ FFmpeg 속도 조정 성공: {speed_factor}x")
            return speed_adjusted_file.name
        else:
            raise Exception(f"FFmpeg 실행 실패: {result.stderr}")
    
    def _speed_up_with_moviepy(self, audio_path, speed_factor):
        """방법 2: MoviePy 다중 방식 시도"""
        print(f"🎬 MoviePy 방식 속도 조정 시도...")
        
        from moviepy.editor import AudioFileClip
        
        audio_clip = AudioFileClip(audio_path)
        original_duration = audio_clip.duration
        
        # 시도 1: speedx import
        try:
            from moviepy.audio.fx import speedx
            speed_adjusted_clip = audio_clip.fx(speedx.speedx, speed_factor)
        except ImportError:
            try:
                from moviepy.audio.fx.speedx import speedx
                speed_adjusted_clip = audio_clip.fx(speedx, speed_factor)
            except ImportError:
                # 시도 2: 직접 시간 매핑
                print("📐 직접 시간 매핑으로 속도 조정...")
                def speed_function(get_frame, t):
                    return get_frame(t * speed_factor)
                
                speed_adjusted_clip = audio_clip.fl(speed_function, apply_to=['mask'])
                speed_adjusted_clip = speed_adjusted_clip.set_duration(audio_clip.duration / speed_factor)
        
        new_duration = speed_adjusted_clip.duration
        
        # 파일 저장
        speed_adjusted_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        speed_adjusted_clip.write_audiofile(
            speed_adjusted_file.name, 
            verbose=False, 
            logger=None,
            temp_audiofile=None  # 임시 파일 경로 문제 방지
        )
        speed_adjusted_file.close()
        
        # 리소스 해제
        audio_clip.close()
        speed_adjusted_clip.close()
        
        print(f"✅ MoviePy 속도 조정 완료: {original_duration:.1f}초 → {new_duration:.1f}초")
        return speed_adjusted_file.name
    
    def _speed_up_with_pydub(self, audio_path, speed_factor):
        """방법 3: Pydub를 사용한 속도 조정"""
        print(f"🎵 Pydub 방식 속도 조정 시도...")
        
        try:
            from pydub import AudioSegment
            from pydub.playback import play
        except ImportError:
            raise Exception("pydub 라이브러리가 설치되지 않았습니다")
        
        # 오디오 로드
        audio = AudioSegment.from_mp3(audio_path)
        
        # 속도 조정 (재생 속도 변경)
        # frame_rate를 증가시켜 속도를 빠르게 함
        new_sample_rate = int(audio.frame_rate * speed_factor)
        speed_adjusted_audio = audio._spawn(audio.raw_data, overrides={"frame_rate": new_sample_rate})
        speed_adjusted_audio = speed_adjusted_audio.set_frame_rate(audio.frame_rate)
        
        # 파일 저장
        speed_adjusted_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        speed_adjusted_audio.export(speed_adjusted_file.name, format="mp3")
        speed_adjusted_file.close()
        
        print(f"✅ Pydub 속도 조정 완료: {len(audio)}ms → {len(speed_adjusted_audio)}ms")
        return speed_adjusted_file.name
    
    def _speed_up_with_sampling(self, audio_path, speed_factor):
        """방법 4: 간단한 샘플링 기반 속도 조정"""
        print(f"📊 샘플링 방식 속도 조정 시도...")
        
        try:
            import numpy as np
            import wave
        except ImportError:
            raise Exception("numpy 라이브러리가 필요합니다")
        
        # WAV로 먼저 변환 (필요한 경우)
        from moviepy.editor import AudioFileClip
        temp_wav = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        temp_wav.close()
        
        audio_clip = AudioFileClip(audio_path)
        audio_clip.write_audiofile(temp_wav.name, verbose=False, logger=None)
        audio_clip.close()
        
        # WAV 파일 읽기
        with wave.open(temp_wav.name, 'rb') as wav_file:
            frames = wav_file.readframes(-1)
            sound_info = wav_file.getparams()
            audio_data = np.frombuffer(frames, dtype=np.int16)
        
        # 샘플링으로 속도 조정 (간단한 방법)
        step = int(1 / speed_factor * len(audio_data))
        if step > 0:
            speed_adjusted_data = audio_data[::int(1/speed_factor)]
        else:
            speed_adjusted_data = audio_data
        
        # 새로운 WAV 파일 생성
        speed_adjusted_wav = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        with wave.open(speed_adjusted_wav.name, 'wb') as new_wav:
            new_wav.setparams(sound_info)
            new_wav.writeframes(speed_adjusted_data.tobytes())
        speed_adjusted_wav.close()
        
        # MP3로 변환
        speed_adjusted_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        converted_clip = AudioFileClip(speed_adjusted_wav.name)
        converted_clip.write_audiofile(speed_adjusted_file.name, verbose=False, logger=None)
        converted_clip.close()
        speed_adjusted_file.close()
        
        # 임시 파일 정리
        os.unlink(temp_wav.name)
        os.unlink(speed_adjusted_wav.name)
        
        print(f"✅ 샘플링 속도 조정 완료")
        return speed_adjusted_file.name
    
    def preprocess_korean_text(self, text):
        """한국어 TTS 품질 향상을 위한 텍스트 전처리 (간단 버전)"""
        try:
            import re
            processed = text.strip()
            
            # 1. 이모지만 제거 (한글 텍스트는 보존)
            emoji_pattern = re.compile("["
                u"\U0001F600-\U0001F64F"  # emoticons
                u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                u"\U0001F680-\U0001F6FF"  # transport & map symbols
                u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                "]+", flags=re.UNICODE)
            processed = emoji_pattern.sub(' ', processed)
            
            # 2. 물음표, 느낌표, 물결표시를 마침표로 변환
            processed = re.sub(r'[?!~]+', '.', processed)
            
            # 3. 공백 정리
            processed = re.sub(r'\s+', ' ', processed).strip()
            if processed and not processed.endswith('.'):
                processed += '.'
            
            print(f"TTS 전처리 전: {text}")
            print(f"TTS 전처리 후: {processed}")
            
            return processed
            
        except Exception as e:
            print(f"텍스트 전처리 실패: {e}")
            return text  # 실패시 원본 반환
    
    def get_audio_duration(self, audio_path):
        """오디오 파일의 실제 재생 시간 반환"""
        try:
            audio = AudioFileClip(audio_path)
            duration = audio.duration
            audio.close()
            return duration
        except Exception as e:
            print(f"오디오 길이 확인 실패: {e}")
            return 3.0  # 기본값
    
    def get_local_images(self, test_folder="./test"):
        """test 폴더에서 이미지 파일들을 이름순으로 가져오기"""
        import glob
        
        # 이미지 확장자 패턴 (webp 추가)
        image_patterns = ["*.jpg", "*.jpeg", "*.png", "*.bmp", "*.gif", "*.webp"]
        image_files = []
        
        for pattern in image_patterns:
            files = glob.glob(os.path.join(test_folder, pattern))
            files.extend(glob.glob(os.path.join(test_folder, pattern.upper())))
            image_files.extend(files)
        
        # 숫자 순서대로 정렬 (1.png, 2.png, 3.png, 4.png)
        import re
        def natural_sort_key(path):
            filename = os.path.basename(path).lower()
            # 숫자 부분 추출
            numbers = re.findall(r'\d+', filename)
            if numbers:
                return int(numbers[0])  # 첫 번째 숫자로 정렬
            else:
                return float('inf')  # 숫자가 없으면 맨 뒤로
        
        image_files.sort(key=natural_sort_key)
        
        print(f"로컬 이미지 파일 발견: {len(image_files)}개 (숫자 순서대로)")
        for i, file in enumerate(image_files):
            print(f"  {i+1}. {os.path.basename(file)}")
        
        if len(image_files) == 0:
            print("❌ test 폴더에 이미지 파일이 없습니다")
        else:
            print(f"✅ 이미지 사용 순서: {' → '.join([os.path.basename(f) for f in image_files])}")
        
        return image_files
    
    def create_video_with_local_images(self, content, music_path, output_folder, image_allocation_mode="2_per_image", text_position="bottom", text_style="outline"):
        """로컬 이미지 파일들을 사용한 릴스 영상 생성"""
        try:
            # 로컬 이미지 파일들 가져오기
            local_images = self.get_local_images()
            
            if not local_images:
                raise Exception("test 폴더에 이미지 파일이 없습니다")
            
            print(f"로컬 이미지 {len(local_images)}개를 사용하여 영상 생성")
            
            # 제목 이미지 생성 (414x180, 더 넓은 영역)
            title_image_path = self.create_title_image(
                content['title'], 
                self.video_width, 
                180
            )
            
            # 각 body별로 개별 TTS 생성 (빈 값 제외)
            body_keys = [key for key in content.keys() if key.startswith('body') and content[key].strip()]
            tts_files = []
            
            for body_key in body_keys:
                print(f"{body_key} TTS 생성 중...")
                body_tts = self.create_tts_audio(content[body_key])
                if body_tts:
                    body_duration = self.get_audio_duration(body_tts)
                    tts_files.append((body_key, body_tts, body_duration))
                    print(f"{body_key} TTS 완료: {body_duration:.1f}초")
            
            # 이미지 할당 모드에 따른 처리 분기
            print(f"🎬 이미지 할당 모드: {image_allocation_mode}")
            
            group_clips = []
            audio_segments = []
            
            if image_allocation_mode == "1_per_image":
                # Mode 2: body 1개당 이미지 1개 (1:1 매칭)
                print("🖼️ 1:1 매칭 모드: body별로 각각 다른 이미지 사용")
                
                for i, body_key in enumerate(body_keys):
                    # body별로 개별 이미지 할당 (이미지가 부족하면 마지막 이미지 사용)
                    image_index = min(i, len(local_images) - 1)
                    current_image_path = local_images[image_index]
                    
                    # 해당 body의 TTS 정보 찾기
                    body_tts_info = None
                    body_duration = 3.0
                    for tts_key, tts_path, tts_duration in tts_files:
                        if tts_key == body_key:
                            body_tts_info = (body_key, content[body_key], tts_path, tts_duration)
                            body_duration = tts_duration
                            break
                    else:
                        body_tts_info = (body_key, content[body_key], None, 3.0)
                    
                    # 파일 타입 확인 (비디오 vs 이미지)
                    video_extensions = ['.mp4', '.mov', '.avi', '.webm']
                    is_video = any(current_image_path.lower().endswith(ext) for ext in video_extensions)
                    file_type = "비디오" if is_video else "이미지"
                    
                    print(f"📸 {body_key}: {file_type} {image_index + 1}/{len(local_images)} → '{os.path.basename(current_image_path)}' ({body_duration:.1f}초)")
                    
                    # 파일 타입에 따른 배경 클립 생성
                    if is_video:
                        bg_clip = self.create_video_background_clip(current_image_path, body_duration)
                    else:
                        bg_clip = self.create_background_clip(current_image_path, body_duration)
                    black_top = ColorClip(size=(self.video_width, 180), color=(0,0,0)).set_duration(body_duration).set_position((0, 0))
                    title_clip = ImageClip(title_image_path).set_duration(body_duration).set_position((0, 0))
                    
                    # 텍스트 클립
                    text_image_path = self.create_text_image(content[body_key], self.video_width, self.video_height - 180, text_position, text_style)
                    text_clip = ImageClip(text_image_path).set_duration(body_duration).set_position((0, 180))
                    
                    # 개별 클립 합성
                    individual_clip = CompositeVideoClip([bg_clip, black_top, title_clip, text_clip], size=(self.video_width, self.video_height))
                    group_clips.append(individual_clip)
                    print(f"    ✅ {body_key} 완료: 개별 이미지 적용")
                    
                    # 오디오 추가
                    if body_tts_info[2]:  # tts_path가 있으면
                        audio_segments.append(AudioFileClip(body_tts_info[2]))
                        
            else:  # image_allocation_mode == "2_per_image"
                # Mode 1: body 2개당 이미지 1개 (그룹 방식)
                print("🖼️ 2:1 매칭 모드: body 2개당 이미지 1개 사용")
                
                for group_idx in range(0, len(body_keys), 2):
                    group_bodies = body_keys[group_idx:group_idx + 2]
                    # 그룹 순서대로 이미지 사용 (body1,2 → image0, body3,4 → image1)
                    image_index = min(group_idx // 2, len(local_images) - 1)
                    current_image_path = local_images[image_index]
                    print(f"그룹 {group_idx//2 + 1}: 이미지 인덱스 {image_index}, 파일: {os.path.basename(current_image_path)}")
                    
                    # 그룹 TTS 정보 수집
                    group_tts_info = []
                    group_total_duration = 0.0
                    
                    for body_key in group_bodies:
                        for tts_key, tts_path, tts_duration in tts_files:
                            if tts_key == body_key:
                                group_tts_info.append((body_key, content[body_key], tts_path, tts_duration))
                                group_total_duration += tts_duration
                                break
                        else:
                            group_tts_info.append((body_key, content[body_key], None, 3.0))
                            group_total_duration += 3.0
                    
                    # 파일 타입 확인 (비디오 vs 이미지)
                    video_extensions = ['.mp4', '.mov', '.avi', '.webm']
                    is_video = any(current_image_path.lower().endswith(ext) for ext in video_extensions)
                    file_type = "비디오" if is_video else "이미지"
                    
                    print(f"📸 그룹 {group_idx//2 + 1}: {[info[0] for info in group_tts_info]} → '{os.path.basename(current_image_path)}' ({file_type}, {group_total_duration:.1f}초)")
                    
                    # 파일 타입에 따른 배경 클립 생성
                    if is_video:
                        bg_clip = self.create_video_background_clip(current_image_path, group_total_duration)
                    else:
                        bg_clip = self.create_continuous_background_clip(current_image_path, group_total_duration, 0.0)
                    black_top = ColorClip(size=(self.video_width, 180), color=(0,0,0)).set_duration(group_total_duration)
                    title_clip = ImageClip(title_image_path).set_duration(group_total_duration).set_position((0, 0))
                    
                    # 텍스트 클립들
                    text_clips = []
                    current_time = 0.0
                    for body_key, body_text, tts_path, duration in group_tts_info:
                        text_image_path = self.create_text_image(body_text, self.video_width, self.video_height - 180, text_position, text_style)
                        text_clip = ImageClip(text_image_path).set_start(current_time).set_duration(duration).set_position((0, 180))
                        text_clips.append(text_clip)
                        print(f"      {body_key}: {current_time:.1f}~{current_time + duration:.1f}초")
                        current_time += duration
                    
                    # 그룹 전체 합성 (CompositeVideoClip 하나로)
                    group_clip = CompositeVideoClip([bg_clip, black_top, title_clip] + text_clips, size=(self.video_width, self.video_height))
                    group_clips.append(group_clip)
                    print(f"    ✅ 그룹 {group_idx//2 + 1} 완료: 배경 연속 보장")
                    
                    # 오디오 추가
                    for _, _, tts_path, _ in group_tts_info:
                        if tts_path:
                            audio_segments.append(AudioFileClip(tts_path))
            
            # 그룹들 연결
            final_video = concatenate_videoclips(group_clips, method="compose")
            
            # 8. TTS 오디오들 연결
            if audio_segments:
                final_audio = concatenate_audioclips(audio_segments)
                
                # 9. 배경음악 추가
                if music_path and os.path.exists(music_path):
                    background_music = AudioFileClip(music_path)
                    background_music = background_music.volumex(0.25)  # 볼륨 25%
                    
                    # 배경음악이 영상보다 짧으면 반복, 길면 자르기
                    if background_music.duration < final_audio.duration:
                        background_music = background_music.loop(duration=final_audio.duration)
                    else:
                        background_music = background_music.subclip(0, final_audio.duration)
                    
                    # TTS와 배경음악 합성
                    final_audio = CompositeAudioClip([final_audio, background_music])
                
                final_video = final_video.set_audio(final_audio)
                print("TTS 오디오와 배경음악 합성 완료")
            
            # 10. 최종 영상 저장
            video_id = str(uuid.uuid4())[:8]
            output_filename = f"reels_{video_id}.mp4"
            output_path = os.path.join(output_folder, output_filename)
            
            print(f"최종 영상 렌더링 시작: {output_path}")
            final_video.write_videofile(
                output_path,
                fps=self.fps,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True
            )
            
            print(f"영상 생성 완료: {output_path}")
            return output_path
            
        except Exception as e:
            raise Exception(f"로컬 이미지 영상 생성 실패: {str(e)}")
    
    def create_video(self, content, image_urls, music_path, output_folder, image_allocation_mode="2_per_image", text_position="bottom", text_style="outline"):
        """릴스 영상 생성 (414x896 해상도, 여러 이미지 지원)"""
        try:
            # 여러 이미지 다운로드
            image_paths = []
            for i, image_url in enumerate(image_urls):
                print(f"이미지 {i+1}/{len(image_urls)} 다운로드 중: {image_url}")
                image_path = self.download_image(image_url)
                image_paths.append(image_path)
            
            # 제목 이미지 생성 (414x180, 더 넓은 영역)
            title_image_path = self.create_title_image(
                content['title'], 
                self.video_width, 
                180
            )
            
            # 각 body별로 개별 TTS 생성 (빈 값 제외)
            body_keys = [key for key in content.keys() if key.startswith('body') and content[key].strip()]
            tts_files = []
            
            # 제목 TTS 생성
            print("제목 TTS 생성 중...")
            title_tts = self.create_tts_audio(content['title'])
            if title_tts:
                title_duration = self.get_audio_duration(title_tts)
                tts_files.append(('title', title_tts, title_duration))
                print(f"제목 TTS 완료: {title_duration:.1f}초")
            
            # 각 body TTS 생성
            for body_key in body_keys:
                print(f"{body_key} TTS 생성 중...")
                body_tts = self.create_tts_audio(content[body_key])
                if body_tts:
                    body_duration = self.get_audio_duration(body_tts)
                    tts_files.append((body_key, body_tts, body_duration))
                    print(f"{body_key} TTS 완료: {body_duration:.1f}초")
            
            # 이미지 할당 모드에 따른 처리 분기
            print(f"🎬 이미지 할당 모드: {image_allocation_mode}")
            body_clips = []
            audio_segments = []  # TTS 오디오 세그먼트들
            
            if image_allocation_mode == "1_per_image":
                # Mode 2: body 1개당 이미지 1개 (1:1 매칭)
                print("🖼️ 1:1 매칭 모드: body별로 각각 다른 이미지 사용")
                
                for i, body_key in enumerate(body_keys):
                    # 해당 body의 TTS 정보 찾기
                    body_tts_info = None
                    for tts_key, tts_path, tts_duration in tts_files:
                        if tts_key == body_key:
                            body_tts_info = (tts_path, tts_duration)
                            break
                    
                    if not body_tts_info:
                        print(f"{body_key}의 TTS를 찾을 수 없습니다. 기본 시간 사용.")
                        clip_duration = 3.0
                        tts_path = None
                    else:
                        tts_path, clip_duration = body_tts_info
                    
                    # body별로 개별 이미지 할당 (이미지가 부족하면 마지막 이미지 사용)
                    image_index = min(i, len(image_paths) - 1)  # body1 → image0, body2 → image1, body3 → image2
                    current_image_path = image_paths[image_index]
                    
                    print(f"{body_key} 클립 생성: {clip_duration:.1f}초, 이미지: {image_index + 1}/{len(image_paths)} (1:1 매칭)")
                    
                    # 개별 body 클립 생성
                    bg_clip = self.create_background_clip(current_image_path, clip_duration)
                    black_top = ColorClip(size=(self.video_width, 180), color=(0,0,0)).set_duration(clip_duration).set_position((0, 0))
                    title_clip = ImageClip(title_image_path).set_duration(clip_duration).set_position((0, 0))
                    
                    text_image_path = self.create_text_image(content[body_key], self.video_width, self.video_height - 180, text_position, text_style)
                    text_clip = ImageClip(text_image_path).set_duration(clip_duration).set_position((0, 180))
                    
                    # 개별 클립 합성
                    combined_clip = CompositeVideoClip([bg_clip, black_top, title_clip, text_clip], size=(self.video_width, self.video_height))
                    body_clips.append(combined_clip)
                    
                    # 오디오 세그먼트 추가
                    if tts_path and os.path.exists(tts_path):
                        body_audio = AudioFileClip(tts_path)
                        audio_segments.append(body_audio)
                        print(f"{body_key} 오디오 세그먼트 추가")
                        
            else:  # image_allocation_mode == "2_per_image"
                # Mode 1: body 2개당 이미지 1개 (그룹 방식)
                print("🖼️ 2:1 매칭 모드: body 2개당 이미지 1개 사용")
                
                for i, body_key in enumerate(body_keys):
                    # 해당 body의 TTS 정보 찾기
                    body_tts_info = None
                    for tts_key, tts_path, tts_duration in tts_files:
                        if tts_key == body_key:
                            body_tts_info = (tts_path, tts_duration)
                            break
                    
                    if not body_tts_info:
                        print(f"{body_key}의 TTS를 찾을 수 없습니다. 기본 시간 사용.")
                        clip_duration = 3.0
                        tts_path = None
                    else:
                        tts_path, clip_duration = body_tts_info
                    
                    # body 2개당 이미지 1개 할당 (body1,2 → image0, body3,4 → image1)
                    image_index = min(i // 2, len(image_paths) - 1)
                    current_image_path = image_paths[image_index]
                    
                    print(f"{body_key} 클립 생성: {clip_duration:.1f}초, 이미지: {image_index + 1}/{len(image_paths)} (2:1 매칭)")
                    
                    # 기존 방식대로 클립 생성
                    bg_clip = self.create_background_clip(current_image_path, clip_duration)
                    black_top = ColorClip(size=(self.video_width, 180), color=(0,0,0)).set_duration(clip_duration).set_position((0, 0))
                    title_clip = ImageClip(title_image_path).set_duration(clip_duration).set_position((0, 0))
                    
                    text_image_path = self.create_text_image(content[body_key], self.video_width, self.video_height - 180, text_position, text_style)
                    text_clip = ImageClip(text_image_path).set_duration(clip_duration).set_position((0, 180))
                    
                    # 클립 합성
                    combined_clip = CompositeVideoClip([bg_clip, black_top, title_clip, text_clip], size=(self.video_width, self.video_height))
                    body_clips.append(combined_clip)
                    
                    # 오디오 세그먼트 추가
                    if tts_path and os.path.exists(tts_path):
                        body_audio = AudioFileClip(tts_path)
                        audio_segments.append(body_audio)
                        print(f"{body_key} 오디오 세그먼트 추가")
            
            # 전체 영상 합치기
            final_video = concatenate_videoclips(body_clips)
            print(f"최종 비디오 길이: {final_video.duration:.1f}초")
            
            # TTS 오디오 세그먼트들을 순서대로 연결
            if audio_segments:
                print(f"TTS 오디오 세그먼트 개수: {len(audio_segments)}")
                combined_tts = concatenate_audioclips(audio_segments)
                print(f"결합된 TTS 길이: {combined_tts.duration:.1f}초")
                
                # 배경음악 추가
                audio_tracks = [combined_tts]
                
                if os.path.exists(music_path):
                    print("배경음악 추가 중...")
                    # 배경음악 (볼륨을 20%로 낮춤 - TTS가 더 잘 들리도록)
                    bg_music = AudioFileClip(music_path).volumex(0.2)
                    if bg_music.duration < combined_tts.duration:
                        bg_music = bg_music.loop(duration=combined_tts.duration)
                    else:
                        bg_music = bg_music.subclip(0, combined_tts.duration)
                    audio_tracks.append(bg_music)
                
                # 오디오 합성
                if len(audio_tracks) > 1:
                    print("TTS + 배경음악 합성 중...")
                    final_audio = CompositeAudioClip(audio_tracks)
                else:
                    print("TTS만 사용")
                    final_audio = audio_tracks[0]
                
                final_video = final_video.set_audio(final_audio)
                print("최종 비디오에 오디오 추가 완료")
                
            else:
                print("TTS 오디오가 없어서 배경음악만 사용")
                if os.path.exists(music_path):
                    bg_music = AudioFileClip(music_path)
                    if bg_music.duration > final_video.duration:
                        bg_music = bg_music.subclip(0, final_video.duration)
                    final_video = final_video.set_audio(bg_music)
            
            # 출력 파일 경로 생성
            output_filename = f"reels_{uuid.uuid4().hex[:8]}.mp4"
            output_path = os.path.join(output_folder, output_filename)
            
            # 영상 렌더링 (이미 414x896으로 구성됨)
            final_video.write_videofile(
                output_path,
                fps=self.fps,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True
            )
            
            # 임시 파일 정리
            if os.path.exists(image_path):
                os.unlink(image_path)
            if os.path.exists(title_image_path):
                os.unlink(title_image_path)
            
            # 모든 TTS 파일 정리
            for tts_key, tts_path, tts_duration in tts_files:
                if os.path.exists(tts_path):
                    os.unlink(tts_path)
                    print(f"{tts_key} TTS 파일 정리: {tts_path}")
            
            return output_path
            
        except Exception as e:
            raise Exception(f"Video generation failed: {str(e)}")
    
    def scan_uploads_folder(self, uploads_folder="uploads"):
        """uploads 폴더를 스캔하여 파일들을 찾고 분류"""
        scan_result = {
            'json_file': None,
            'image_files': [],  # 호환성 유지
            'media_files': []   # 새로운 미디어 파일 리스트
        }
        
        if not os.path.exists(uploads_folder):
            print(f"❌ {uploads_folder} 폴더가 존재하지 않습니다")
            return scan_result
        
        # JSON 파일 찾기 (text.json)
        json_path = os.path.join(uploads_folder, "text.json")
        if os.path.exists(json_path):
            scan_result['json_file'] = json_path
            print(f"✅ JSON 파일 발견: {json_path}")
        
        # 음악 파일은 더 이상 uploads에서 찾지 않음 (bgm 폴더 직접 사용)
        
        # 미디어 파일들 찾기 (이미지 + 비디오)
        image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp']
        video_extensions = ['.mp4', '.mov', '.avi', '.webm']
        all_extensions = image_extensions + video_extensions
        
        # 숫자로 시작하는 미디어 파일들을 찾아서 정렬
        media_files = []
        image_files = []  # 호환성을 위한 기존 이미지 파일 리스트
        
        for filename in os.listdir(uploads_folder):
            if any(filename.lower().endswith(ext) for ext in all_extensions):
                # 파일명이 숫자로 시작하는지 확인
                name_without_ext = os.path.splitext(filename)[0]
                if name_without_ext.isdigit():
                    file_number = int(name_without_ext)
                    full_path = os.path.join(uploads_folder, filename)
                    
                    # 파일 타입 결정
                    is_video = any(filename.lower().endswith(ext) for ext in video_extensions)
                    file_type = "video" if is_video else "image"
                    
                    media_files.append((file_number, full_path, file_type))
                    
                    # 호환성을 위해 기존 image_files에도 추가
                    image_files.append((file_number, full_path))
        
        # 숫자 순서대로 정렬
        media_files.sort(key=lambda x: x[0])
        image_files.sort(key=lambda x: x[0])
        
        # 결과 저장
        scan_result['media_files'] = [(path, file_type) for _, path, file_type in media_files]
        scan_result['image_files'] = [path for _, path in image_files]  # 호환성 유지
        
        print(f"📊 미디어 파일 {len(scan_result['media_files'])}개 발견:")
        for i, (media_path, file_type) in enumerate(scan_result['media_files'], 1):
            print(f"   {i}. {os.path.basename(media_path)} ({file_type})")
        
        return scan_result
    
    def create_video_from_uploads(self, output_folder, bgm_file_path=None, image_allocation_mode="2_per_image", text_position="bottom", text_style="outline", uploads_folder="uploads"):
        """uploads 폴더의 파일들을 사용하여 영상 생성 (기존 메서드 재사용)"""
        try:
            print("🚀 uploads 폴더 기반 영상 생성 시작")
            
            # uploads 폴더 스캔
            scan_result = self.scan_uploads_folder(uploads_folder)
            
            # 필수 파일 검증
            if not scan_result['json_file']:
                raise Exception("text.json 파일이 없습니다")
            
            if not scan_result['image_files']:
                raise Exception("이미지 파일이 없습니다")
            
            # JSON 내용 로드
            with open(scan_result['json_file'], 'r', encoding='utf-8') as f:
                content = json.load(f)
            print(f"✅ JSON 내용 로드: {scan_result['json_file']}")
            
            # 음악 파일 설정 (bgm_file_path 직접 사용)
            music_path = bgm_file_path or ""
            if music_path and os.path.exists(music_path):
                print(f"✅ 음악 파일 사용: {music_path}")
            else:
                print("⚠️  음악 파일 없음 - 음성만 사용")
                music_path = ""
            
            # 기존 create_video_with_local_images 방식 재사용
            # 스캔된 이미지 파일들로 로컬 이미지 리스트 대체
            self._temp_local_images = scan_result['image_files']
            
            # 기존 메서드 호출 (이미지 할당 모드, 텍스트 위치, 텍스트 스타일 전달)
            return self.create_video_with_local_images(content, music_path, output_folder, image_allocation_mode, text_position, text_style)
            
        except Exception as e:
            raise Exception(f"uploads 폴더 기반 영상 생성 실패: {str(e)}")
    
    def get_local_images(self, test_folder="./test"):
        """test 폴더에서 이미지 파일들을 이름순으로 가져오기"""
        # uploads 폴더 사용 시 임시 이미지 리스트가 있으면 그것을 사용
        if hasattr(self, '_temp_local_images') and self._temp_local_images:
            images = self._temp_local_images
            self._temp_local_images = None  # 사용 후 정리
            print(f"업로드 이미지 파일 발견: {len(images)}개 (순서대로)")
            for i, file in enumerate(images):
                print(f"  {i+1}. {os.path.basename(file)}")
            return images
        
        # 기존 test 폴더 로직
        import glob
        
        # 이미지 확장자 패턴 (webp 추가)
        image_patterns = ["*.jpg", "*.jpeg", "*.png", "*.bmp", "*.gif", "*.webp"]
        image_files = []
        
        for pattern in image_patterns:
            files = glob.glob(os.path.join(test_folder, pattern))
            files.extend(glob.glob(os.path.join(test_folder, pattern.upper())))
            image_files.extend(files)
        
        # 숫자 순서대로 정렬 (1.png, 2.png, 3.png, 4.png)
        import re
        def natural_sort_key(path):
            filename = os.path.basename(path).lower()
            # 숫자 부분 추출
            numbers = re.findall(r'\d+', filename)
            if numbers:
                return int(numbers[0])  # 첫 번째 숫자로 정렬
            else:
                return float('inf')  # 숫자가 없으면 맨 뒤로
        
        image_files.sort(key=natural_sort_key)
        
        print(f"로컬 이미지 파일 발견: {len(image_files)}개 (숫자 순서대로)")
        for i, file in enumerate(image_files):
            print(f"  {i+1}. {os.path.basename(file)}")
        
        if len(image_files) == 0:
            print("❌ test 폴더에 이미지 파일이 없습니다")
        else:
            print(f"✅ 이미지 사용 순서: {' → '.join([os.path.basename(f) for f in image_files])}")
        
        return image_files