"""
Gmail SMTP 이메일 발송 서비스
무료 Gmail 계정을 사용한 이메일 발송 시스템
"""

import smtplib
import os
import jwt
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jinja2 import Template
from dotenv import load_dotenv
from utils.logger_config import get_logger

# 환경변수 로드
load_dotenv()

# 로깅 설정
logger = get_logger('email_service')

class EmailService:
    def __init__(self):
        # Gmail SMTP 설정
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587

        # 환경변수에서 Gmail 설정 로드
        self.gmail_email = os.getenv("GMAIL_EMAIL", "")
        self.gmail_password = os.getenv("GMAIL_APP_PASSWORD", "")
        self.from_name = os.getenv("EMAIL_FROM_NAME", "릴스 영상 생성 서비스")

        # JWT 시크릿 키 (다운로드 링크 보안용)
        self.jwt_secret = os.getenv("JWT_SECRET_KEY", "default-secret-key-change-me")

        # 기본 설정 검증
        self._validate_config()

    def _validate_config(self):
        """이메일 설정 검증"""
        if not self.gmail_email:
            logger.error("GMAIL_EMAIL 환경변수가 설정되지 않았습니다.")
            return False

        if not self.gmail_password:
            logger.error("GMAIL_APP_PASSWORD 환경변수가 설정되지 않았습니다.")
            return False

        logger.info(f"✅ Gmail 설정 완료: {self.gmail_email}")
        return True

    def generate_download_token(self, video_path: str, user_email: str, expire_hours: int = 48) -> str:
        """다운로드 링크용 JWT 토큰 생성"""
        payload = {
            'video_path': video_path,
            'user_email': user_email,
            'exp': datetime.utcnow() + timedelta(hours=expire_hours),
            'iat': datetime.utcnow()
        }

        token = jwt.encode(payload, self.jwt_secret, algorithm='HS256')
        logger.info(f"🔐 다운로드 토큰 생성: {user_email} (만료: {expire_hours}시간)")
        return token

    def verify_download_token(self, token: str) -> Optional[Dict[str, Any]]:
        """다운로드 토큰 검증"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("⚠️ 만료된 다운로드 토큰")
            return None
        except jwt.InvalidTokenError:
            logger.warning("⚠️ 유효하지 않은 다운로드 토큰")
            return None

    def get_email_template(self) -> str:
        """이메일 HTML 템플릿 반환"""
        template = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>릴스 영상 생성 완료</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f4f4f4;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px 20px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 28px;
            font-weight: bold;
        }
        .header p {
            margin: 10px 0 0 0;
            opacity: 0.9;
        }
        .content {
            padding: 30px 20px;
        }
        .video-info {
            background: #f8f9ff;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            border-left: 4px solid #667eea;
        }
        .download-btn {
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 30px;
            text-decoration: none;
            border-radius: 50px;
            font-weight: bold;
            text-align: center;
            margin: 20px 0;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
            transition: transform 0.2s;
        }
        .download-btn:hover {
            transform: translateY(-2px);
        }
        .footer {
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
            font-size: 14px;
            border-top: 1px solid #e9ecef;
        }
        .warning {
            background: #fff3cd;
            color: #856404;
            padding: 15px;
            border-radius: 5px;
            border: 1px solid #ffeaa7;
            margin: 15px 0;
        }
        .emoji {
            font-size: 24px;
            margin-right: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1><span class="emoji">🎬</span>릴스 영상 생성 완료!</h1>
            <p>요청하신 영상이 성공적으로 생성되었습니다</p>
        </div>

        <div class="content">
            <p><strong>{{ user_email }}</strong>님, 안녕하세요!</p>

            <p>요청해주신 릴스 영상이 성공적으로 생성되었습니다. 아래 버튼을 클릭하여 다운로드해주세요.</p>

            <div class="video-info">
                <h3><span class="emoji">📋</span>영상 정보</h3>
                <p><strong>제목:</strong> {{ video_title }}</p>
                <p><strong>생성 완료 시간:</strong> {{ completed_at }}</p>
                <p><strong>예상 파일 크기:</strong> 약 5-15MB</p>
                <p><strong>영상 길이:</strong> {{ duration }}</p>
            </div>

            <div style="text-align: center;">
                <a href="{{ download_link }}" class="download-btn">
                    <span class="emoji">⬇️</span>영상 다운로드
                </a>
            </div>

            <div class="warning">
                <strong><span class="emoji">⚠️</span>중요 안내</strong>
                <ul style="margin: 10px 0; padding-left: 20px;">
                    <li>다운로드 링크는 <strong>48시간 후</strong> 만료됩니다</li>
                    <li>보안을 위해 이 링크를 다른 사람과 공유하지 마세요</li>
                    <li>영상은 MP4 형식으로 제공되며, 대부분의 기기에서 재생 가능합니다</li>
                </ul>
            </div>

            <p>문의사항이 있으시면 언제든지 연락주세요.</p>
            <p>감사합니다! <span class="emoji">😊</span></p>
        </div>

        <div class="footer">
            <p>© 2024 릴스 영상 생성 서비스. All rights reserved.</p>
            <p style="margin-top: 10px; font-size: 12px;">
                이 메일은 자동 발송되었습니다. 회신하지 마세요.
            </p>
        </div>
    </div>
</body>
</html>
        """
        return template

    def send_completion_email(self,
                             user_email: str,
                             video_path: str,
                             video_title: str = "릴스 영상",
                             duration: str = "약 10-30초") -> bool:
        """영상 생성 완료 이메일 발송"""
        try:
            # 다운로드 토큰 생성
            download_token = self.generate_download_token(video_path, user_email)

            # 다운로드 링크 생성 (기존 /download-video 엔드포인트 사용)
            base_url = os.getenv("BASE_URL", "http://localhost:8097")
            download_link = f"{base_url}/api/download-video?token={download_token}"

            # 이메일 템플릿 렌더링
            template = Template(self.get_email_template())
            html_content = template.render(
                user_email=user_email,
                video_title=video_title,
                completed_at=datetime.now().strftime("%Y년 %m월 %d일 %H시 %M분"),
                duration=duration,
                download_link=download_link
            )

            # 이메일 메시지 생성
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.from_name} <{self.gmail_email}>"
            msg['To'] = user_email
            msg['Subject'] = f"🎬 릴스 영상 생성 완료 - {video_title}"

            # HTML 내용 추가
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)

            # 텍스트 버전도 추가 (HTML 미지원 클라이언트용)
            text_content = f"""
릴스 영상 생성 완료!

{user_email}님, 안녕하세요!

요청해주신 릴스 영상 '{video_title}'이 성공적으로 생성되었습니다.

다운로드 링크: {download_link}

⚠️ 중요 안내:
- 다운로드 링크는 48시간 후 만료됩니다
- 보안을 위해 이 링크를 다른 사람과 공유하지 마세요

감사합니다!
릴스 영상 생성 서비스
            """
            text_part = MIMEText(text_content, 'plain')
            msg.attach(text_part)

            # SMTP 서버 연결 및 메일 발송
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.gmail_email, self.gmail_password)
                server.send_message(msg)

            logger.info(f"✅ 완료 이메일 발송 성공: {user_email}")
            return True

        except Exception as e:
            logger.error(f"❌ 이메일 발송 실패: {e}")
            return False

    def send_error_email(self, user_email: str, job_id: str, error_message: str) -> bool:
        """영상 생성 실패 이메일 발송"""
        try:
            subject = "⚠️ 릴스 영상 생성 실패 안내"

            html_content = f"""
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <h2 style="color: #e74c3c;">⚠️ 릴스 영상 생성 실패</h2>

    <p><strong>{user_email}</strong>님, 안녕하세요.</p>

    <p>죄송합니다. 요청해주신 릴스 영상 생성 중 문제가 발생했습니다.</p>

    <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0;">
        <strong>작업 ID:</strong> {job_id}<br>
        <strong>오류 내용:</strong> {error_message}
    </div>

    <p>이 문제가 지속되면 관리자에게 문의해주세요.</p>

    <p>불편을 드려 죄송합니다.</p>
    <p>감사합니다.</p>
</div>
            """

            msg = MIMEMultipart()
            msg['From'] = f"{self.from_name} <{self.gmail_email}>"
            msg['To'] = user_email
            msg['Subject'] = subject
            msg.attach(MIMEText(html_content, 'html'))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.gmail_email, self.gmail_password)
                server.send_message(msg)

            logger.info(f"✅ 실패 이메일 발송 성공: {user_email}")
            return True

        except Exception as e:
            logger.error(f"❌ 실패 이메일 발송 실패: {e}")
            return False

# 전역 인스턴스
email_service = EmailService()

# 사용 예제
if __name__ == "__main__":
    # 테스트용 이메일 발송
    success = email_service.send_completion_email(
        user_email="test@example.com",
        video_path="output_videos/test_video.mp4",
        video_title="테스트 릴스 영상",
        duration="15초"
    )

    if success:
        print("✅ 테스트 이메일 발송 완료")
    else:
        print("❌ 테스트 이메일 발송 실패")