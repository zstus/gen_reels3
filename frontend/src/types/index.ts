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
export type ImageUploadMode = 'per-script' | 'per-two-scripts' | 'single-for-all';

// 텍스트 위치 타입 (3단계 시스템)
export type TextPosition = 'top' | 'bottom' | 'bottom-edge';

// 텍스트 스타일 타입
export type TextStyle = 'outline' | 'background' | 'white_background' | 'black_text_white_outline';

// 자막 읽어주기 타입
export type VoiceNarration = 'enabled' | 'disabled';

// 타이틀 영역 모드 타입
export type TitleAreaMode = 'keep' | 'remove';

// 크로스 디졸브 타입
export type CrossDissolve = 'enabled' | 'disabled';

// 음악 성격 타입
export type MusicMood = 'bright' | 'calm' | 'romantic' | 'sad' | 'suspense' | 'none';

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

// 폰트 파일 타입
export interface FontFile {
  filename: string;
  display_name: string;
  file_path: string;
  size_mb: number;
  extension: string;
}

// 폰트 설정 타입
export interface FontSettings {
  titleFont: string;
  bodyFont: string;
  titleFontSize: number;
  bodyFontSize: number;
}

// 프로젝트 상태 타입
export interface ProjectData {
  jobId: string; // Job ID 추가 - 폴더 격리를 위한 고유 식별자
  content: ReelsContent;
  images: File[]; // 이미지 및 비디오 파일들 (이름은 호환성을 위해 유지)
  imageUploadMode: ImageUploadMode;
  textPosition: TextPosition;
  textStyle: TextStyle;
  titleAreaMode: TitleAreaMode;
  selectedMusic: MusicFile | null;
  musicMood: MusicMood;
  fontSettings: FontSettings;
  voiceNarration: VoiceNarration;
  crossDissolve: CrossDissolve;
  imagePanningOptions?: { [key: number]: boolean }; // 이미지별 패닝 옵션 (선택적)
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
  title_area_mode: TitleAreaMode;
  title_font?: string;
  body_font?: string;
  title_font_size?: number;
  body_font_size?: number;
  voice_narration: VoiceNarration;
  cross_dissolve: CrossDissolve;
  subtitle_duration?: number;
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
  title_area_mode: TitleAreaMode;
  selected_bgm_path?: string;
  use_test_files?: boolean;
  images?: File[];
  title_font?: string;
  body_font?: string;
  title_font_size?: number;
  body_font_size?: number;
  voice_narration: VoiceNarration;
  cross_dissolve: CrossDissolve;
  subtitle_duration?: number;
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
  // 수정된 텍스트 관리 (per-two-scripts 모드용)
  editedTexts?: string[];  // 수정된 개별 텍스트 배열
  originalTexts?: string[]; // 원본 개별 텍스트 배열 (비교용)
}

// Job 폴더 생성 요청 타입
export interface CreateJobFolderRequest {
  job_id: string;
}

// Job 폴더 생성 응답 타입
export interface CreateJobFolderResponse {
  status: 'success' | 'error';
  message: string;
  job_id: string;
  uploads_folder?: string;
  output_folder?: string;
}

// Job 폴더 정리 요청 타입
export interface CleanupJobFolderRequest {
  job_id: string;
  keep_output?: boolean;
}

// Job 폴더 정리 응답 타입
export interface CleanupJobFolderResponse {
  status: 'success' | 'error';
  message: string;
  job_id: string;
  cleaned: boolean;
}

// 북마크 비디오 타입
export interface BookmarkVideo {
  filename: string;
  display_name: string;
  size_mb: number;
  modified_time: number;
  video_url: string;
  thumbnail_url: string | null;
  has_thumbnail: boolean;
  duration: number;
  extension: string;
}

// 북마크 이미지 타입
export interface BookmarkImage {
  filename: string;
  display_name: string;
  size_mb: number;
  modified_time: number;
  image_url: string;
  thumbnail_url: string;
  extension: string;
}

// 북마크 미디어 타입 (비디오와 이미지 통합)
export type BookmarkMedia = BookmarkVideo | BookmarkImage;

// 미디어 타입 구분
export type MediaType = 'video' | 'image';