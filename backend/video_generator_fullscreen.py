# 전체 화면용 메서드들 (video_generator.py에 추가할 메서드들)

import tempfile
import random
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont
import os

def create_fullscreen_background_clip(self, image_path, duration):
    """전체 화면(504x890)용 이미지 배경 클립 생성"""
    print(f"🖼️ 전체 화면 이미지 클립 생성: {os.path.basename(image_path)}")

    try:
        # 이미지 로드 및 크기 확인
        img = Image.open(image_path)
        orig_width, orig_height = img.size
        print(f"📐 원본 이미지: {orig_width}x{orig_height}")

        # 작업 영역: 전체 화면 504x890
        work_width = self.video_width
        work_height = self.video_height
        work_aspect_ratio = work_width / work_height
        image_aspect_ratio = orig_width / orig_height

        print(f"🎯 목표: 전체 화면 {work_width}x{work_height}")

        # 종횡비 기반 지능형 배치
        if image_aspect_ratio > work_aspect_ratio:
            # 가로형: 높이 맞춤 후 좌우 패닝
            resized_height = work_height
            resized_width = int(orig_width * resized_height / orig_height)
            print(f"🔳 가로형 이미지: 높이 기준 리사이즈 {resized_width}x{resized_height}")

            # 좌우 패닝 범위
            pan_range = min(60, (resized_width - work_width) // 2)
        else:
            # 세로형: 폭 맞춤 후 상하 패닝
            resized_width = work_width
            resized_height = int(orig_height * resized_width / orig_width)
            print(f"🔳 세로형 이미지: 폭 기준 리사이즈 {resized_width}x{resized_height}")

            # 상하 패닝 범위
            pan_range = min(60, (resized_height - work_height) // 2)

        # MoviePy 이미지 클립 생성
        clip = ImageClip(image_path).set_duration(duration)
        clip = clip.resize((resized_width, resized_height))

        # 패닝 애니메이션 (4패턴 랜덤)
        patterns = [1, 2, 3, 4]
        pattern = random.choice(patterns)

        if image_aspect_ratio > work_aspect_ratio:
            # 가로형 패닝 (좌우)
            if pattern in [1, 3]:
                # 좌 → 우
                print(f"🎬 패턴 {pattern}: 좌 → 우 패닝 (duration: {duration:.1f}s)")
                start_x = -pan_range
                end_x = pan_range
            else:
                # 우 → 좌
                print(f"🎬 패턴 {pattern}: 우 → 좌 패닝 (duration: {duration:.1f}s)")
                start_x = pan_range
                end_x = -pan_range

            start_y = (work_height - resized_height) // 2
            end_y = start_y
        else:
            # 세로형 패닝 (상하)
            if pattern in [1, 3]:
                # 상 → 하
                print(f"🎬 패턴 {pattern}: 상 → 하 패닝 (duration: {duration:.1f}s)")
                start_y = -pan_range
                end_y = pan_range
            else:
                # 하 → 상
                print(f"🎬 패턴 {pattern}: 하 → 상 패닝 (duration: {duration:.1f}s)")
                start_y = pan_range
                end_y = -pan_range

            start_x = (work_width - resized_width) // 2
            end_x = start_x

        # Linear 이징으로 패닝 적용
        def pos_func(t):
            progress = t / duration if duration > 0 else 0
            x = start_x + (end_x - start_x) * progress
            y = start_y + (end_y - start_y) * progress
            return (x, y)

        clip = clip.set_position(pos_func)

        print(f"🎯 Linear 이징 적용: 일정한 속도로 명확한 움직임")
        print(f"📏 패닝 범위: {pan_range}px 이동 (2배 확대)")
        print(f"✅ 전체 화면 이미지 클립 생성 완료!")

        return clip

    except Exception as e:
        print(f"❌ 전체 화면 이미지 클립 생성 실패: {e}")
        # 폴백: 검은 배경
        return ColorClip(size=(self.video_width, self.video_height),
                       color=(0,0,0), duration=duration)

def create_fullscreen_video_clip(self, video_path, duration):
    """전체 화면(504x890)용 비디오 배경 클립 생성"""
    print(f"🎬 전체 화면 비디오 클립 생성: {os.path.basename(video_path)}")

    try:
        # 비디오 클립 로드
        video_clip = VideoFileClip(video_path)
        orig_width, orig_height = video_clip.size
        print(f"📐 원본 비디오: {orig_width}x{orig_height}")

        # 전체 화면에 맞춰 리사이즈 (종횡비 유지하면서 화면 꽉 채움)
        work_width = self.video_width
        work_height = self.video_height
        work_aspect_ratio = work_width / work_height
        video_aspect_ratio = orig_width / orig_height

        print(f"🎯 목표: 전체 화면 {work_width}x{work_height}")

        # 화면비에 따른 크롭 및 리사이즈
        if video_aspect_ratio > work_aspect_ratio:
            # 가로형 비디오: 높이 맞춤 후 양옆 크롭
            new_height = work_height
            new_width = int(orig_width * new_height / orig_height)
            print(f"📐 가로형 비디오: 높이 기준 리사이즈 {new_width}x{new_height}")
            video_clip = video_clip.resize(height=new_height)

            # 중앙 크롭
            crop_x = (new_width - work_width) // 2
            video_clip = video_clip.crop(x1=crop_x, x2=crop_x + work_width)
        else:
            # 세로형 비디오: 폭 맞춤 후 상하 크롭
            new_width = work_width
            new_height = int(orig_height * new_width / orig_width)
            print(f"📐 세로형 비디오: 폭 기준 리사이즈 {new_width}x{new_height}")
            video_clip = video_clip.resize(width=new_width)

            # 중앙 크롭
            crop_y = (new_height - work_height) // 2
            video_clip = video_clip.crop(y1=crop_y, y2=crop_y + work_height)

        # 길이 조정
        if video_clip.duration > duration:
            video_clip = video_clip.subclip(0, duration)
            print(f"⏂ 비디오 길이 조정: {duration:.1f}초로 잘라냄")
        elif video_clip.duration < duration:
            # 마지막 프레임으로 연장
            last_frame = video_clip.to_ImageClip(t=video_clip.duration-0.1)
            extension_clip = last_frame.set_duration(duration - video_clip.duration)
            video_clip = CompositeVideoClip([video_clip, extension_clip.set_start(video_clip.duration)])
            print(f"⏸ 마지막 프레임으로 연장: {duration:.1f}초")

        # 위치 설정 (화면 가득)
        video_clip = video_clip.set_position((0, 0))

        print(f"✅ 전체 화면 비디오 클립 생성 완료!")

        return video_clip

    except Exception as e:
        print(f"❌ 전체 화면 비디오 클립 생성 실패: {e}")
        # 폴백: 검은 배경
        return ColorClip(size=(self.video_width, self.video_height),
                       color=(0,0,0), duration=duration)

def create_overlay_text_image(self, text, width, height, text_style="outline", font_path="BMYEONSUNG_otf.otf"):
    """오버레이용 텍스트 이미지 생성 (전체 화면 중앙에 배치)"""
    print(f"✏️ 오버레이 텍스트 이미지 생성: '{text[:20]}...' (스타일: {text_style})")

    try:
        # 폰트 설정
        font_size = 48  # 전체 화면용으로 크게
        full_font_path = os.path.join(self.font_folder, font_path)

        if not os.path.exists(full_font_path):
            print(f"⚠️ 폰트 파일 없음: {full_font_path}, 기본 폰트 사용")
            font = ImageFont.load_default()
        else:
            font = ImageFont.truetype(full_font_path, font_size)

        # 텍스트 크기 측정
        temp_img = Image.new('RGBA', (1, 1), (0, 0, 0, 0))
        temp_draw = ImageDraw.Draw(temp_img)
        bbox = temp_draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # 이미지 생성 (투명 배경)
        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # 텍스트 위치 (화면 중앙)
        x = (width - text_width) // 2
        y = (height - text_height) // 2

        if text_style == "outline":
            # 외곽선 스타일
            outline_positions = [
                (-2, -2), (-2, -1), (-2, 0), (-2, 1), (-2, 2),
                (-1, -2), (-1, -1), (-1, 0), (-1, 1), (-1, 2),
                (0, -2), (0, -1),           (0, 1), (0, 2),
                (1, -2), (1, -1), (1, 0), (1, 1), (1, 2),
                (2, -2), (2, -1), (2, 0), (2, 1), (2, 2)
            ]

            # 검은색 외곽선
            for dx, dy in outline_positions:
                draw.text((x + dx, y + dy), text, font=font, fill=(0, 0, 0, 255))

            # 흰색 텍스트
            draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))
        else:
            # 반투명 배경 스타일
            padding = 20
            bg_x1 = x - padding
            bg_y1 = y - padding
            bg_x2 = x + text_width + padding
            bg_y2 = y + text_height + padding

            # 반투명 검은 배경
            draw.rectangle([bg_x1, bg_y1, bg_x2, bg_y2], fill=(0, 0, 0, 180))

            # 흰색 텍스트
            draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))

        # 이미지 저장
        temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        img.save(temp_file.name, 'PNG')
        temp_file.close()

        print(f"✅ 오버레이 텍스트 이미지 생성 완료: {width}x{height}")

        return temp_file.name

    except Exception as e:
        print(f"❌ 오버레이 텍스트 이미지 생성 실패: {e}")
        # 폴백: 빈 투명 이미지
        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        img.save(temp_file.name, 'PNG')
        temp_file.close()
        return temp_file.name