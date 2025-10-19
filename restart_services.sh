#!/bin/bash

echo "🔄 릴스 영상 생성 서비스 재시작 시작..."
echo "==========================================\n"

# 1. 기존 프로세스 종료
echo "📴 기존 프로세스 종료 중..."
pkill -f "react-scripts start"
pkill -f "python main.py"
pkill -f "python worker.py"
pkill -f "npm start"

echo "   프로세스 종료 대기 중..."
sleep 3

# 2. 포트 강제 해제 (필요시)
echo "🔧 포트 정리 중..."
sudo fuser -k 3000/tcp 2>/dev/null || true
sudo fuser -k 8080/tcp 2>/dev/null || true

# 3. FastAPI 재시작
echo "🚀 FastAPI 서버 재시작 중..."
cd /zstus/backend
source venv/bin/activate
nohup python main.py > api.log 2>&1 &
echo "   FastAPI 서버 백그라운드에서 시작됨 (포트 8080)"

# 4. 백그라운드 워커 재시작 (이메일 서비스 포함)
echo "🤖 백그라운드 워커 재시작 중..."
cd /zstus/backend
source venv/bin/activate
nohup python worker.py --poll-interval 5 >> api.log 2>&1 &
echo "   백그라운드 워커 시작됨 (5초 폴링 간격, api.log에 통합)"

# 5. React 재시작
echo "⚛️  React 개발 서버 재시작 중..."
cd /zstus/frontend
nohup npm start > react.log 2>&1 &
echo "   React 서버 백그라운드에서 시작됨 (포트 3000)"

# 5. 서비스 시작 대기
echo "⏳ 서비스 시작 대기 중..."
echo "   FastAPI 초기화: 5초 대기..."
sleep 5

echo "   React 빌드 및 시작: 25초 더 대기..."
sleep 25

# 6. 서비스 상태 확인
echo "\n✅ 서비스 상태 확인:"
echo "==========================================\n"

# FastAPI 상태 확인
echo "🔍 FastAPI 서버 상태:"
if curl -s http://localhost:8080 > /dev/null; then
    API_RESPONSE=$(curl -s http://localhost:8080)
    echo "   ✅ FastAPI 정상 실행: $API_RESPONSE"
else
    echo "   ❌ FastAPI 응답 없음 - api.log 확인 필요"
fi

# React 상태 확인
echo "\n🔍 React 서버 상태:"
if curl -s http://localhost:3000 > /dev/null; then
    echo "   ✅ React 정상 실행"
else
    echo "   ❌ React 응답 없음 - react.log 확인 필요"
fi

# 백그라운드 워커 상태 확인
echo "\n🔍 백그라운드 워커 상태:"
if pgrep -f "python worker.py" > /dev/null; then
    WORKER_PID=$(pgrep -f "python worker.py")
    echo "   ✅ 워커 정상 실행 (PID: $WORKER_PID)"
else
    echo "   ❌ 워커 응답 없음 - api.log 확인 필요"
fi

# 7. 실행 중인 프로세스 표시
echo "\n📊 현재 실행 중인 프로세스:"
ps aux | grep -E "(react-scripts|python main.py|python worker.py)" | grep -v grep | head -5

# 8. 포트 상태 표시
echo "\n🌐 포트 사용 상태:"
sudo netstat -tlnp | grep -E ":(3000|8080|80)"

echo "\n==========================================\n"
echo "🎉 서비스 재시작 완료!"
echo "\n📋 접속 정보:"
echo "   - 웹 서비스: http://zstus.synology.me:8097/"
echo "   - FastAPI 직접: http://localhost:8080"
echo "   - React 직접: http://localhost:3000"
echo "\n📄 로그 확인:"
echo "   - 통합 로그 (모든 모듈): tail -f /zstus/backend/api.log"
echo "   - React 로그: tail -f /zstus/frontend/react.log"
echo "\n📧 이메일 서비스:"
echo "   - Gmail SMTP: lazyflicker@gmail.com"
echo "   - 완료 시 자동 이메일 발송 (배치 작업)"
echo "==========================================\n"