// 사용자 타입
export interface User {
  id: string;
  email: string;
  name: string;
  picture?: string;
}

// 릴스 콘텐츠 타입
export interface ReelsContent {
  title: string;
  body1: string;
  body2?: string;
  body3?: string;
  body4?: string;
  body5?: string;
  body6?: string;
  body7?: string;
  body8?: string;
}

// 이미지 업로드 모드
export type ImageUploadMode = 'per-script' | 'per-two-scripts';

// 텍스트 위치 타입 (2단계 시스템)
export type TextPosition = 'top' | 'bottom';

// 텍스트 스타일 타입
export type TextStyle = 'outline' | 'background';

// 음악 성격 타입
export type MusicMood = 'bright' | 'calm' | 'romantic' | 'sad' | 'suspense';

// 음악 파일 타입
export interface MusicFile {
  filename: string;
  displayName: string;
  mood: MusicMood;
  url: string;
}

// 음악 폴더 타입
export interface MusicFolder {
  mood: MusicMood;
  displayName: string;
  files: MusicFile[];
}

// 프로젝트 상태 타입
export interface ProjectData {
  content: ReelsContent;
  images: File[]; // 이미지 및 비디오 파일들 (이름은 호환성을 위해 유지)
  imageUploadMode: ImageUploadMode;
  textPosition: TextPosition;
  textStyle: TextStyle;
  selectedMusic: MusicFile | null;
  musicMood: MusicMood;
}

// API 응답 타입
export interface ApiResponse<T = any> {
  status: 'success' | 'error';
  message: string;
  data?: T;
  video_path?: string;
}

// 영상 생성 요청 타입
export interface GenerateVideoRequest {
  content_data: string;
  music_mood: MusicMood;
  image_urls?: string;
  background_music?: File;
  use_test_files: boolean;
  selected_bgm_path?: string;
  image_allocation_mode: ImageUploadMode;
  text_position: TextPosition;
  text_style: TextStyle;
}

// 영상 생성 상태 타입
export type GenerationStatus = 'idle' | 'generating' | 'completed' | 'error';

// 배치 작업 상태 타입
export type JobStatus = 'pending' | 'processing' | 'completed' | 'failed';

// 작업 정보 타입
export interface JobInfo {
  job_id: string;
  status: JobStatus;
  created_at: string;
  updated_at: string;
  result?: {
    video_path?: string;
    duration?: string;
    completed_at?: string;
  };
  error_message?: string;
}

// 비동기 영상 생성 요청 타입
export interface AsyncVideoRequest {
  user_email: string;
  content_data: string;
  music_mood: MusicMood;
  image_allocation_mode: ImageUploadMode;
  text_position: TextPosition;
  text_style: TextStyle;
  selected_bgm_path?: string;
  use_test_files?: boolean;
  images?: File[];
}

// 비동기 영상 생성 응답 타입
export interface AsyncVideoResponse {
  status: 'success' | 'error';
  message: string;
  job_id?: string;
  user_email?: string;
  estimated_time?: string;
}

// 단계 타입
export type Step = 'login' | 'content' | 'images' | 'music' | 'generate' | 'download';

// 구글 OAuth 응답 타입
export interface GoogleCredentialResponse {
  credential: string;
  select_by: string;
}

// JWT 페이로드 타입 (구글 토큰)
export interface GoogleJWTPayload {
  iss: string;
  sub: string;
  aud: string;
  exp: number;
  iat: number;
  email: string;
  name: string;
  picture?: string;
  email_verified: boolean;
}

// 커스텀 프롬프트 타입
export interface CustomPrompt {
  imageIndex: number;
  prompt: string;
  enabled: boolean;
}

// 단일 이미지 생성 요청 타입 (커스텀 프롬프트 지원)
export interface SingleImageGenerateRequest {
  text?: string;
  custom_prompt?: string;
  additional_context?: string;
}

// 텍스트-이미지 쌍 타입 (커스텀 프롬프트 지원)
export interface TextImagePair {
  textIndex: number;
  textKey: string;
  textContent: string;
  image: File | null;
  imageIndex: number;
  isGenerating: boolean;
  customPrompt?: string;
  useCustomPrompt?: boolean;
}