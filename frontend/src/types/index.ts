// 사용자 타입
export interface User {
  id: string;
  email: string;
  name: string;
  picture?: string;
}

// 릴스 콘텐츠 타입 (최대 50개 대사 지원)
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
  body9?: string;
  body10?: string;
  body11?: string;
  body12?: string;
  body13?: string;
  body14?: string;
  body15?: string;
  body16?: string;
  body17?: string;
  body18?: string;
  body19?: string;
  body20?: string;
  body21?: string;
  body22?: string;
  body23?: string;
  body24?: string;
  body25?: string;
  body26?: string;
  body27?: string;
  body28?: string;
  body29?: string;
  body30?: string;
  body31?: string;
  body32?: string;
  body33?: string;
  body34?: string;
  body35?: string;
  body36?: string;
  body37?: string;
  body38?: string;
  body39?: string;
  body40?: string;
  body41?: string;
  body42?: string;
  body43?: string;
  body44?: string;
  body45?: string;
  body46?: string;
  body47?: string;
  body48?: string;
  body49?: string;
  body50?: string;
}

// 이미지 업로드 모드
export type ImageUploadMode = 'per-script' | 'per-two-scripts' | 'single-for-all';

// 텍스트 위치 타입 (3단계 시스템)
export type TextPosition = 'top' | 'bottom' | 'bottom-edge';

// 텍스트 스타일 타입
export type TextStyle = 'outline' | 'background' | 'white_background' | 'black_text_white_outline';

// 자막 읽어주기 타입
export type VoiceNarration = 'enabled' | 'disabled';

// TTS 엔진 타입
export type TTSEngine = 'google' | 'qwen';

// Qwen TTS 화자 타입
export type QwenSpeaker = 'Sohee' | 'Vivian' | 'Serena' | 'Uncle_Fu' | 'Dylan' | 'Eric' | 'Ryan' | 'Aiden' | 'Ono_Anna';

// Qwen TTS 속도 타입
export type QwenSpeed = 'very_slow' | 'slow' | 'normal' | 'fast' | 'very_fast';

// Qwen TTS 스타일 타입
export type QwenStyle = 'neutral' | 'cheerful_witty' | 'cynical_calm';

// Qwen 화자 정보
export interface QwenSpeakerInfo {
  id: QwenSpeaker;
  language: string;
  description: string;
}

// Qwen 화자 목록
export const QWEN_SPEAKERS: QwenSpeakerInfo[] = [
  { id: 'Sohee', language: 'Korean', description: '한국어 여성 (기본)' },
  { id: 'Vivian', language: 'Chinese', description: '중국어 여성' },
  { id: 'Serena', language: 'Chinese', description: '중국어 여성' },
  { id: 'Uncle_Fu', language: 'Chinese', description: '중국어 남성' },
  { id: 'Dylan', language: 'Chinese', description: '중국어 남성' },
  { id: 'Eric', language: 'Chinese', description: '중국어 남성' },
  { id: 'Ryan', language: 'English', description: '영어 남성' },
  { id: 'Aiden', language: 'English', description: '영어 남성' },
  { id: 'Ono_Anna', language: 'Japanese', description: '일본어 여성' },
];

// Qwen 속도 프리셋
export const QWEN_SPEED_PRESETS: { id: QwenSpeed; label: string; description: string }[] = [
  { id: 'very_slow', label: '매우 느림', description: '천천히 명확하게 발음' },
  { id: 'slow', label: '느림', description: '느린 속도로 발음' },
  { id: 'normal', label: '보통', description: '일반적인 속도 (기본값)' },
  { id: 'fast', label: '빠름', description: '빠른 속도로 발음' },
  { id: 'very_fast', label: '매우 빠름', description: '매우 빠르고 활기차게 발음' },
];

// Qwen 스타일 프리셋
export const QWEN_STYLE_PRESETS: { id: QwenStyle; label: string; description: string }[] = [
  { id: 'neutral', label: '기본', description: '자연스러운 말투' },
  { id: 'cheerful_witty', label: '쾌활/익살', description: '쾌활하게 익살스러운 목소리로' },
  { id: 'cynical_calm', label: '덤덤/시니컬', description: '덤덤한 말투로 시니컬하게' },
];

// 대사별 TTS 설정 타입
export interface PerBodyTTSSetting {
  speaker: QwenSpeaker;
  style: QwenStyle;
}

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
  // TTS 설정
  ttsEngine: TTSEngine;
  qwenSpeaker: QwenSpeaker;
  qwenSpeed: QwenSpeed;
  qwenStyle: QwenStyle;
  // 대사별 TTS 설정
  perBodyTTSEnabled: boolean;
  perBodyTTSSettings: { [bodyKey: string]: PerBodyTTSSetting };
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
  // TTS 설정
  tts_engine?: TTSEngine;
  qwen_speaker?: QwenSpeaker;
  qwen_speed?: QwenSpeed;
  qwen_style?: QwenStyle;
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
  // TTS 설정
  tts_engine?: TTSEngine;
  qwen_speaker?: QwenSpeaker;
  qwen_speed?: QwenSpeed;
  qwen_style?: QwenStyle;
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