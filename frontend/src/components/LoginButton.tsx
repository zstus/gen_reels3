import React, { useEffect, useRef } from 'react';
import { Box, Paper, Typography } from '@mui/material';
import { useAuth } from '../contexts/AuthContext';

const LoginButton: React.FC = () => {
  const { login } = useAuth();
  const googleButtonRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Google OAuth 초기화 및 버튼 렌더링
    const initializeGoogle = () => {
      if (window.google && googleButtonRef.current) {
        window.google.accounts.id.initialize({
          client_id: process.env.REACT_APP_GOOGLE_CLIENT_ID || 'your-google-client-id',
          callback: (response: any) => {
            console.log('Google 로그인 성공:', response);
            login(response.credential);
          },
        });

        window.google.accounts.id.renderButton(
          googleButtonRef.current,
          {
            theme: 'outline',
            size: 'large',
            text: 'signin_with',
            shape: 'rectangular',
            width: 300,
          }
        );

        // 자동 로그인 프롬프트 표시 (선택사항)
        window.google.accounts.id.prompt();
      }
    };

    // Google 스크립트가 로드될 때까지 대기
    if (window.google) {
      initializeGoogle();
    } else {
      const script = document.querySelector('script[src*="gsi/client"]');
      if (script) {
        script.addEventListener('load', initializeGoogle);
      }
    }
  }, [login]);

  return (
    <Box
      display="flex"
      justifyContent="center"
      alignItems="center"
      minHeight="100vh"
      sx={{
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      }}
    >
      <Paper
        elevation={8}
        sx={{
          p: 4,
          maxWidth: 400,
          width: '100%',
          textAlign: 'center',
          borderRadius: 2,
        }}
      >
        <Typography variant="h4" component="h1" gutterBottom color="primary">
          릴스 영상 생성기
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          텍스트를 멋진 릴스 영상으로 자동 변환하세요
        </Typography>
        <Typography variant="h6" component="h2" gutterBottom>
          로그인
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          구글 계정으로 간편하게 시작하세요
        </Typography>
        <Box ref={googleButtonRef} sx={{ display: 'flex', justifyContent: 'center' }} />
        
        <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: 'block' }}>
          * 구글 계정 정보는 로그인 용도로만 사용됩니다
        </Typography>
      </Paper>
    </Box>
  );
};

export default LoginButton;