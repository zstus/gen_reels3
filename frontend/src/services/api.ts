import axios from 'axios';
import { ApiResponse, GenerateVideoRequest, MusicFolder, MusicFile, MusicMood, ImageUploadMode, TextPosition, TextStyle } from '../types';

// API 베이스 URL 설정
const API_BASE_URL = '/api';

// Axios 인스턴스 생성
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5분 (영상 생성 시간 고려)
  headers: {
    'Content-Type': 'application/json',
  },
});

// 요청 인터셉터 - 인증 토큰 추가
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 응답 인터셉터 - 에러 처리
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error);
    if (error.response?.status === 401) {
      // 인증 오류시 로그아웃 처리
      localStorage.removeItem('authToken');
      window.location.href = '/';
    }
    return Promise.reject(error);
  }
);

export const apiService = {
  // 서버 상태 확인
  async checkHealth(): Promise<ApiResponse> {
    const response = await apiClient.get('/');
    return response.data;
  },

  // BGM 목록 조회
  async getBgmList(): Promise<MusicFolder[]> {
    try {
      const response = await apiClient.get('/bgm-list');
      if (response.data.status === 'success') {
        const bgmData = response.data.data;
        return Object.values(bgmData) as MusicFolder[];
      } else {
        throw new Error(response.data.message || 'BGM 목록 조회 실패');
      }
    } catch (error) {
      console.error('BGM 목록 조회 실패:', error);
      throw error;
    }
  },

  // 특정 성격의 BGM 파일 목록 조회
  async getBgmFiles(mood: MusicMood): Promise<MusicFile[]> {
    try {
      const response = await apiClient.get(`/bgm/${mood}`);
      if (response.data.status === 'success') {
        return response.data.data;
      } else {
        throw new Error(response.data.message || 'BGM 파일 목록 조회 실패');
      }
    } catch (error) {
      console.error(`BGM 파일 목록 조회 실패 (${mood}):`, error);
      throw error;
    }
  },

  // 영상 생성
  async generateVideo(data: {
    content: string;
    images: File[];
    imageUploadMode: ImageUploadMode;
    textPosition: TextPosition;
    textStyle: TextStyle;
    musicFile?: MusicFile;
    musicMood: MusicMood;
    useTestFiles?: boolean;
  }): Promise<ApiResponse> {
    const formData = new FormData();
    
    // JSON 데이터 추가
    formData.append('content_data', data.content);
    formData.append('music_mood', data.musicMood);
    formData.append('use_test_files', String(data.useTestFiles || false));
    
    // 이미지 할당 모드 추가 (백엔드 형식에 맞게 변환)
    const backendImageMode = data.imageUploadMode === 'per-script' ? '1_per_image' : '2_per_image';
    formData.append('image_allocation_mode', backendImageMode);

    // 텍스트 위치 추가
    formData.append('text_position', data.textPosition);

    // 텍스트 스타일 추가
    formData.append('text_style', data.textStyle);

    // 선택된 음악 파일 경로 추가
    if (data.musicFile) {
      formData.append('selected_bgm_path', data.musicFile.filename);
    }

    // 이미지 파일들 추가
    if (data.images.length > 0 && !data.useTestFiles) {
      // 이미지 파일을 FormData로 직접 첨부
      data.images.forEach((image, index) => {
        formData.append(`image_${index + 1}`, image, `${index + 1}.${image.name.split('.').pop()}`);
      });
      // image_urls는 빈 배열로 전송 (파일 업로드 방식 사용)
      formData.append('image_urls', '[]');
    } else {
      formData.append('image_urls', '[]');
    }

    try {
      const response = await apiClient.post('/generate-video', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      return response.data;
    } catch (error) {
      console.error('영상 생성 실패:', error);
      throw error;
    }
  },

  // 영상 파일 다운로드 URL 생성
  getVideoDownloadUrl(videoPath: string): string {
    // video_path에서 파일명 추출
    const filename = videoPath.split('/').pop();
    return `/videos/${filename}`;
  },

  // BGM 파일 URL 생성 (미리듣기용)
  getBgmUrl(mood: MusicMood, filename: string): string {
    return `/bgm/${mood}/${encodeURIComponent(filename)}`;
  }
};

export default apiService;