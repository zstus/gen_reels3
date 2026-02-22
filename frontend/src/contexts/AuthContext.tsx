import React, { createContext, useContext, useEffect, useState } from 'react';
import { User, GoogleCredentialResponse, GoogleJWTPayload } from '../types';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  login: (credential: string) => void;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// JWT 토큰을 디코딩하는 함수
const decodeJWT = (token: string): GoogleJWTPayload | null => {
  try {
    const payload = token.split('.')[1];
    // Google JWT는 base64url 인코딩 사용 (-→+, _→/, 패딩 생략)
    // atob()은 표준 base64만 지원하므로 변환 필요
    const base64 = payload.replace(/-/g, '+').replace(/_/g, '/');
    const padded = base64.padEnd(base64.length + (4 - base64.length % 4) % 4, '=');
    const decoded = JSON.parse(atob(padded));
    return decoded;
  } catch (error) {
    console.error('JWT 디코딩 실패:', error);
    return null;
  }
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // 컴포넌트 마운트시 저장된 토큰 확인
  useEffect(() => {
    const savedToken = localStorage.getItem('authToken');
    if (savedToken) {
      const payload = decodeJWT(savedToken);
      if (payload && payload.exp * 1000 > Date.now()) {
        setUser({
          id: payload.sub,
          email: payload.email,
          name: payload.name,
          picture: payload.picture,
        });
      } else {
        localStorage.removeItem('authToken');
      }
    }
    setIsLoading(false);
  }, []);

  // Google OAuth 로그인 처리
  const login = (credential: string) => {
    const payload = decodeJWT(credential);
    if (payload) {
      const newUser: User = {
        id: payload.sub,
        email: payload.email,
        name: payload.name,
        picture: payload.picture,
      };
      
      setUser(newUser);
      localStorage.setItem('authToken', credential);
      localStorage.setItem('user', JSON.stringify(newUser));
    }
  };

  // 로그아웃 처리
  const logout = () => {
    setUser(null);
    localStorage.removeItem('authToken');
    localStorage.removeItem('user');
    
    // Google OAuth 로그아웃
    if (window.google) {
      window.google.accounts.id.disableAutoSelect();
    }
  };

  const value: AuthContextType = {
    user,
    isLoading,
    login,
    logout,
    isAuthenticated: !!user,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth는 AuthProvider 내에서 사용되어야 합니다');
  }
  return context;
};

// Google OAuth 초기화
export const initializeGoogleAuth = () => {
  if (window.google) {
    window.google.accounts.id.initialize({
      client_id: process.env.REACT_APP_GOOGLE_CLIENT_ID || '',
      callback: (response: GoogleCredentialResponse) => {
        // 이 부분은 실제 로그인 컴포넌트에서 처리됩니다
        console.log('Google OAuth 응답:', response);
      },
    });
  }
};

// Google OAuth 타입 확장
declare global {
  interface Window {
    google: {
      accounts: {
        id: {
          initialize: (config: any) => void;
          renderButton: (element: HTMLElement, options: any) => void;
          prompt: () => void;
          disableAutoSelect: () => void;
        };
      };
    };
  }
}