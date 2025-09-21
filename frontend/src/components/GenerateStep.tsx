import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Grid,
  Alert,
  LinearProgress,
  Card,
  CardContent,
  Divider,
  Chip,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControlLabel,
  Switch,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  RadioGroup,
  Radio,
  FormLabel,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Skeleton,
} from '@mui/material';
import {
  PlayArrow,
  Download,
  Refresh,
  CheckCircle,
  Error as ErrorIcon,
  VideoCall,
  MusicNote,
  Image as ImageIcon,
  TextFields,
  Email,
  Schedule,
  Send,
  ExpandMore,
  Visibility,
  FontDownload,
  Style,
  FormatColorText,
} from '@mui/icons-material';
import { ProjectData, GenerationStatus, AsyncVideoResponse, FontFile, TextPosition, TextStyle, VoiceNarration, TitleAreaMode } from '../types';
import apiService from '../services/api';

interface GenerateStepProps {
  projectData: ProjectData;
  onBack: () => void;
  onReset: () => void;
}

const GenerateStep: React.FC<GenerateStepProps> = ({
  projectData,
  onBack,
  onReset,
}) => {
  // 사용자 정보 가져오기 (임시로 localStorage에서 직접 가져오기)
  const getUserFromStorage = () => {
    try {
      const savedUser = localStorage.getItem('user');
      return savedUser ? JSON.parse(savedUser) : null;
    } catch {
      return null;
    }
  };

  const user = getUserFromStorage();

  // 기존 상태 변수들
  const [generationStatus, setGenerationStatus] = useState<GenerationStatus>('idle');
  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState('');
  const [videoPath, setVideoPath] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);

  // 배치 작업 관련 상태 변수들
  const [userEmail, setUserEmail] = useState<string>(user?.email || '');
  const [enableAsyncMode, setEnableAsyncMode] = useState<boolean>(true);
  const [jobId, setJobId] = useState<string | null>(null);
  const [asyncResponse, setAsyncResponse] = useState<AsyncVideoResponse | null>(null);
  const [estimatedTime, setEstimatedTime] = useState<string>('약 3-10분');

  // 폰트 및 스타일 관련 상태 변수들
  const [availableFonts, setAvailableFonts] = useState<FontFile[]>([]);
  const [loadingFonts, setLoadingFonts] = useState(true);
  const [titleFont, setTitleFont] = useState<string>('BMYEONSUNG_otf.otf');
  const [bodyFont, setBodyFont] = useState<string>('BMYEONSUNG_otf.otf');
  const [textPosition, setTextPosition] = useState<TextPosition>('bottom');
  const [textStyle, setTextStyle] = useState<TextStyle>('outline');
  const [titleAreaMode, setTitleAreaMode] = useState<TitleAreaMode>('keep');
  const [voiceNarration, setVoiceNarration] = useState<VoiceNarration>('enabled');

  // 미리보기 관련 상태
  const [previewImage, setPreviewImage] = useState<string | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);

  // 예상 생성 시간 계산
  const calculateEstimatedTime = () => {
    const scriptCount = Object.values(projectData.content)
      .slice(1) // title 제외
      .filter(script => script?.trim()).length;
    
    // 기본 30초 + 대사당 10초 + 이미지당 5초
    const baseTime = 30;
    const scriptTime = scriptCount * 10;
    const imageTime = projectData.images.length * 5;
    
    return Math.max(60, baseTime + scriptTime + imageTime);
  };

  // 폰트 목록 가져오기
  useEffect(() => {
    const fetchFonts = async () => {
      try {
        setLoadingFonts(true);
        const response = await fetch('/font-list');
        const data = await response.json();

        if (data.status === 'success') {
          setAvailableFonts(data.data);
        } else {
          console.error('폰트 목록 가져오기 실패:', data.message);
        }
      } catch (error) {
        console.error('폰트 목록 가져오기 오류:', error);
      } finally {
        setLoadingFonts(false);
      }
    };

    fetchFonts();
  }, []);

  // 미리보기 생성
  const generatePreview = async () => {
    if (!projectData.content.title || !projectData.content.body1) {
      alert('미리보기를 위해서는 제목과 첫 번째 대사가 필요합니다.');
      return;
    }

    setLoadingPreview(true);
    try {
      const response = await apiService.generatePreview({
        title: projectData.content.title,
        body1: projectData.content.body1,
        textPosition: textPosition,
        textStyle: textStyle,
        titleAreaMode: titleAreaMode,
        titleFont: titleFont,
        bodyFont: bodyFont,
        image: projectData.images[0] || undefined,
      });

      if (response.status === 'success') {
        setPreviewImage(response.preview_url);
        console.log('미리보기 생성 성공:', response.message);
      } else {
        throw new Error(response.message || '미리보기 생성 실패');
      }

    } catch (error) {
      console.error('미리보기 생성 오류:', error);
      alert('미리보기 생성 중 오류가 발생했습니다.');
      setPreviewImage(null);
    } finally {
      setLoadingPreview(false);
    }
  };

  // 자동 미리보기 생성은 제거하고, 수동으로만 미리보기 생성하도록 변경
  // useEffect로 인한 무한 루프 방지

  // 배치 영상 생성 시작 (비동기)
  const startAsyncGeneration = async () => {
    // 이메일 주소 검증
    if (!userEmail.trim()) {
      setError('이메일 주소를 입력해주세요.');
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(userEmail)) {
      setError('유효한 이메일 주소를 입력해주세요.');
      return;
    }

    setGenerationStatus('generating');
    setProgress(30);
    setError(null);
    setVideoPath(null);
    setJobId(null);
    setAsyncResponse(null);

    try {
      setStatusMessage('배치 작업 요청 중...');

      // 배치 작업 API 호출
      const contentData = JSON.stringify(projectData.content);
      const response = await apiService.generateVideoAsync({
        userEmail: userEmail,
        content: contentData,
        images: projectData.images,
        imageUploadMode: projectData.imageUploadMode,
        textPosition: textPosition,
        textStyle: textStyle,
        titleAreaMode: titleAreaMode,
        musicFile: projectData.selectedMusic || undefined,
        musicMood: projectData.musicMood,
        titleFont: titleFont,
        bodyFont: bodyFont,
        voiceNarration: voiceNarration,
      });

      if (response.status === 'success') {
        setProgress(50);
        setStatusMessage('작업이 큐에 추가되었습니다. 완료되면 이메일로 알려드립니다.');
        setJobId(response.job_id || null);
        setAsyncResponse(response);
        setEstimatedTime(response.estimated_time || '약 3-10분');
        setGenerationStatus('completed');
      } else {
        throw new Error(response.message || '작업 요청에 실패했습니다');
      }
    } catch (err: any) {
      console.error('배치 작업 요청 실패:', err);
      setError(err.message || '작업 요청 중 오류가 발생했습니다');
      setGenerationStatus('error');
      setProgress(0);
      setStatusMessage('');
    }
  };

  // 기존 동기식 영상 생성 (레거시)
  const startSyncGeneration = async () => {
    setGenerationStatus('generating');
    setProgress(0);
    setError(null);
    setVideoPath(null);

    try {
      // 진행률 시뮬레이션
      const progressSteps = [
        { progress: 10, message: '텍스트 분석 중...' },
        { progress: 20, message: 'TTS 음성 생성 중...' },
        { progress: 40, message: '이미지 처리 중...' },
        { progress: 60, message: '배경음악 준비 중...' },
        { progress: 80, message: '영상 합성 중...' },
        { progress: 95, message: '최종 렌더링 중...' },
      ];

      // 단계별 진행률 업데이트
      for (const step of progressSteps) {
        await new Promise(resolve => setTimeout(resolve, 2000));
        setProgress(step.progress);
        setStatusMessage(step.message);
      }

      // API 호출
      const contentData = JSON.stringify(projectData.content);
      const response = await apiService.generateVideo({
        content: contentData,
        images: projectData.images,
        imageUploadMode: projectData.imageUploadMode,
        textPosition: textPosition,
        textStyle: textStyle,
        titleAreaMode: titleAreaMode,
        musicFile: projectData.selectedMusic || undefined,
        musicMood: projectData.musicMood,
        titleFont: titleFont,
        bodyFont: bodyFont,
        voiceNarration: voiceNarration,
      });

      if (response.status === 'success') {
        setProgress(100);
        setStatusMessage('영상 생성 완료!');
        setVideoPath(response.video_path || null);
        setGenerationStatus('completed');
      } else {
        throw new Error(response.message || '영상 생성에 실패했습니다');
      }
    } catch (err: any) {
      console.error('영상 생성 실패:', err);
      setError(err.message || '영상 생성 중 오류가 발생했습니다');
      setGenerationStatus('error');
      setProgress(0);
      setStatusMessage('');
    }
  };

  // 영상 생성 시작 (모드에 따라 분기)
  const startGeneration = () => {
    if (enableAsyncMode) {
      startAsyncGeneration();
    } else {
      startSyncGeneration();
    }
  };

  // 영상 다운로드
  const downloadVideo = () => {
    if (videoPath) {
      const downloadUrl = apiService.getVideoDownloadUrl(videoPath);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = `reels_${new Date().toISOString().slice(0, 10)}.mp4`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  // 새 프로젝트 시작 확인
  const handleNewProject = () => {
    setShowConfirmDialog(true);
  };

  const confirmNewProject = () => {
    setShowConfirmDialog(false);
    onReset();
  };

  // 프로젝트 요약 정보
  const getProjectSummary = () => {
    const scriptCount = Object.values(projectData.content)
      .slice(1)
      .filter(script => script?.trim()).length;
    
    let totalChars = 0;
    Object.values(projectData.content).slice(1).forEach(script => {
      if (script?.trim()) {
        totalChars += script.length;
      }
    });

    const estimatedDuration = Math.max(5, Math.ceil((totalChars / 450) * 60));

    return {
      scriptCount,
      totalChars,
      estimatedDuration,
      imageCount: projectData.images.length,
      imageMode: projectData.imageUploadMode === 'per-script'
        ? '대사마다 이미지'
        : projectData.imageUploadMode === 'per-two-scripts'
          ? '2대사마다 이미지'
          : '모든 대사에 미디어 1개',
      titleAreaMode: titleAreaMode === 'keep' ? '확보 (타이틀 + 미디어 영역)' : '제거 (전체 미디어)',
      textPosition: titleAreaMode === 'keep' ? (textPosition === 'top' ? '상단 (340-520px 영역)' : '하단 (520-700px 영역)') : '미디어 위 오버레이',
      textStyle: projectData.textStyle === 'outline' ? '외곽선 (배경 투명)' : '반투명 검은 배경',
      musicName: projectData.selectedMusic?.displayName || '기본 음악',
      musicMood: projectData.musicMood,
    };
  };

  const summary = getProjectSummary();

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        영상 생성
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        모든 준비가 완료되었습니다. 영상을 생성하고 다운로드하세요.
      </Typography>

      <Grid container spacing={3}>
        {/* 왼쪽: 프로젝트 요약 */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              프로젝트 요약
            </Typography>

            {/* 콘텐츠 정보 */}
            <Card sx={{ mb: 2 }}>
              <CardContent>
                <Box display="flex" alignItems="center" sx={{ mb: 1 }}>
                  <TextFields color="primary" sx={{ mr: 1 }} />
                  <Typography variant="subtitle2">콘텐츠</Typography>
                </Box>
                <Typography variant="body2" color="text.secondary">
                  제목: {projectData.content.title}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  대사: {summary.scriptCount}개 ({summary.totalChars}자)
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  예상 길이: 약 {summary.estimatedDuration}초
                </Typography>
              </CardContent>
            </Card>

            {/* 이미지 및 텍스트 정보 */}
            <Card sx={{ mb: 2 }}>
              <CardContent>
                <Box display="flex" alignItems="center" sx={{ mb: 1 }}>
                  <ImageIcon color="primary" sx={{ mr: 1 }} />
                  <Typography variant="subtitle2">미디어 & 텍스트 설정</Typography>
                </Box>
                <Typography variant="body2" color="text.secondary">
                  업로드된 미디어: {summary.imageCount}개
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  모드: {summary.imageMode}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  타이틀 영역: {summary.titleAreaMode}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  텍스트 위치: {summary.textPosition}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  자막 스타일: {summary.textStyle}
                </Typography>
              </CardContent>
            </Card>

            {/* 음악 정보 */}
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" sx={{ mb: 1 }}>
                  <MusicNote color="primary" sx={{ mr: 1 }} />
                  <Typography variant="subtitle2">배경음악</Typography>
                </Box>
                <Typography variant="body2" color="text.secondary">
                  선택된 음악: {summary.musicName}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  성격: {summary.musicMood}
                </Typography>
              </CardContent>
            </Card>
          </Paper>
        </Grid>

        {/* 오른쪽: 폰트/스타일 설정 & 이메일 설정 & 생성 상태 */}
        <Grid item xs={12} md={6}>
          {/* 폰트 및 스타일 설정 */}
          <Paper sx={{ p: 3, mb: 2 }}>
            <Typography variant="h6" gutterBottom>
              <FontDownload sx={{ mr: 1, verticalAlign: 'middle' }} />
              폰트 및 스타일 설정
            </Typography>

            {/* 폰트 설정 */}
            <Accordion sx={{ mb: 2 }}>
              <AccordionSummary expandIcon={<ExpandMore />}>
                <Typography variant="subtitle2">
                  <Style sx={{ mr: 1, verticalAlign: 'middle' }} />
                  폰트 선택
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6}>
                    <FormControl fullWidth size="small">
                      <InputLabel>타이틀 폰트</InputLabel>
                      <Select
                        value={titleFont}
                        label="타이틀 폰트"
                        onChange={(e) => setTitleFont(e.target.value)}
                        disabled={loadingFonts}
                      >
                        {loadingFonts ? (
                          <MenuItem disabled>
                            <CircularProgress size={16} sx={{ mr: 1 }} />
                            로딩 중...
                          </MenuItem>
                        ) : (
                          availableFonts.map((font) => (
                            <MenuItem key={font.filename} value={font.filename}>
                              {font.display_name} ({font.size_mb}MB)
                            </MenuItem>
                          ))
                        )}
                      </Select>
                    </FormControl>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <FormControl fullWidth size="small">
                      <InputLabel>본문 폰트</InputLabel>
                      <Select
                        value={bodyFont}
                        label="본문 폰트"
                        onChange={(e) => setBodyFont(e.target.value)}
                        disabled={loadingFonts}
                      >
                        {loadingFonts ? (
                          <MenuItem disabled>
                            <CircularProgress size={16} sx={{ mr: 1 }} />
                            로딩 중...
                          </MenuItem>
                        ) : (
                          availableFonts.map((font) => (
                            <MenuItem key={font.filename} value={font.filename}>
                              {font.display_name} ({font.size_mb}MB)
                            </MenuItem>
                          ))
                        )}
                      </Select>
                    </FormControl>
                  </Grid>
                </Grid>
              </AccordionDetails>
            </Accordion>

            {/* 텍스트 위치 및 스타일 설정 */}
            <Accordion sx={{ mb: 2 }}>
              <AccordionSummary expandIcon={<ExpandMore />}>
                <Typography variant="subtitle2">
                  <FormatColorText sx={{ mr: 1, verticalAlign: 'middle' }} />
                  텍스트 위치 및 스타일
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Box sx={{ mb: 2 }}>
                  <FormControl component="fieldset">
                    <FormLabel component="legend">타이틀 영역</FormLabel>
                    <RadioGroup
                      row
                      value={titleAreaMode}
                      onChange={(e) => setTitleAreaMode(e.target.value as TitleAreaMode)}
                    >
                      <FormControlLabel
                        value="keep"
                        control={<Radio size="small" />}
                        label="확보"
                      />
                      <FormControlLabel
                        value="remove"
                        control={<Radio size="small" />}
                        label="제거"
                      />
                    </RadioGroup>
                  </FormControl>
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                    - 확보: 타이틀 영역(220px)과 미디어 영역(670px)으로 구분<br/>
                    - 제거: 타이틀 제거하고 전체 화면(890px)을 미디어로 채움
                  </Typography>
                </Box>

                <Box sx={{ mb: 2 }}>
                  <FormControl component="fieldset">
                    <FormLabel component="legend">텍스트 위치</FormLabel>
                    <RadioGroup
                      row
                      value={textPosition}
                      onChange={(e) => setTextPosition(e.target.value as TextPosition)}
                    >
                      <FormControlLabel
                        value="top"
                        control={<Radio size="small" />}
                        label="상단"
                      />
                      <FormControlLabel
                        value="bottom"
                        control={<Radio size="small" />}
                        label="하단"
                      />
                    </RadioGroup>
                    <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                      {titleAreaMode === 'keep'
                        ? "타이틀 영역 아래 미디어 영역에서의 텍스트 위치"
                        : "전체 화면에서의 텍스트 위치 (기존 위치 유지)"
                      }
                    </Typography>
                  </FormControl>
                </Box>

                <Box>
                  <FormControl component="fieldset">
                    <FormLabel component="legend">텍스트 스타일</FormLabel>
                    <RadioGroup
                      row
                      value={textStyle}
                      onChange={(e) => setTextStyle(e.target.value as TextStyle)}
                    >
                      <FormControlLabel
                        value="outline"
                        control={<Radio size="small" />}
                        label="외곽선"
                      />
                      <FormControlLabel
                        value="background"
                        control={<Radio size="small" />}
                        label="반투명 배경"
                      />
                    </RadioGroup>
                  </FormControl>
                </Box>

                <Box>
                  <FormControl component="fieldset">
                    <FormLabel component="legend">자막 읽어주기</FormLabel>
                    <RadioGroup
                      row
                      value={voiceNarration}
                      onChange={(e) => setVoiceNarration(e.target.value as VoiceNarration)}
                    >
                      <FormControlLabel
                        value="enabled"
                        control={<Radio size="small" />}
                        label="추가"
                      />
                      <FormControlLabel
                        value="disabled"
                        control={<Radio size="small" />}
                        label="제거"
                      />
                    </RadioGroup>
                  </FormControl>
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                    - 추가: 자막 음성이 포함된 영상 생성<br/>
                    - 제거: 자막 표시는 유지하되 음성은 무음으로 처리 (배경음악이나 원본 비디오 소리만 재생)
                  </Typography>
                </Box>
              </AccordionDetails>
            </Accordion>

            {/* 미리보기 */}
            <Box sx={{ textAlign: 'center' }}>
              <Button
                variant="outlined"
                size="small"
                startIcon={loadingPreview ? <CircularProgress size={16} /> : <Visibility />}
                onClick={generatePreview}
                disabled={loadingPreview || !projectData.content.title || !projectData.content.body1 || projectData.images.length === 0}
                sx={{ mb: 2 }}
              >
                {loadingPreview ? '생성 중...' : '미리보기 생성'}
              </Button>

              {previewImage && (
                <Box sx={{
                  mt: 2,
                  border: '1px solid',
                  borderColor: 'divider',
                  borderRadius: 1,
                  overflow: 'hidden',
                  maxWidth: 200,
                  mx: 'auto'
                }}>
                  <img
                    src={previewImage}
                    alt="미리보기"
                    style={{
                      width: '100%',
                      height: 'auto',
                      display: 'block'
                    }}
                  />
                  <Typography variant="caption" color="text.secondary" sx={{ p: 1, display: 'block' }}>
                    미리보기 (타이틀 + 첫 번째 대사)
                  </Typography>
                </Box>
              )}
            </Box>
          </Paper>

          {/* 이메일 알림 설정 */}
          <Paper sx={{ p: 3, mb: 2 }}>
            <Typography variant="h6" gutterBottom>
              <Email sx={{ mr: 1, verticalAlign: 'middle' }} />
              이메일 알림 설정
            </Typography>

            <Box sx={{ mb: 2 }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={enableAsyncMode}
                    onChange={(e) => setEnableAsyncMode(e.target.checked)}
                    color="primary"
                  />
                }
                label="배치 작업 모드 (이메일 알림)"
              />
            </Box>

            {enableAsyncMode && (
              <Box sx={{ mb: 2 }}>
                <TextField
                  fullWidth
                  label="알림받을 이메일 주소"
                  type="email"
                  value={userEmail}
                  onChange={(e) => setUserEmail(e.target.value)}
                  placeholder={user?.email || 'your.email@example.com'}
                  helperText="영상 생성 완료 시 다운로드 링크가 발송됩니다"
                  variant="outlined"
                  InputProps={{
                    startAdornment: <Email sx={{ mr: 1, color: 'action.active' }} />
                  }}
                />
              </Box>
            )}

            <Alert
              severity={enableAsyncMode ? "info" : "warning"}
              sx={{ mb: 2 }}
            >
              {enableAsyncMode ? (
                <>
                  <strong>배치 작업 모드:</strong><br/>
                  • 영상 생성 요청 후 즉시 대응 가능<br/>
                  • 완료되면 이메일로 다운로드 링크 전송<br/>
                  • 예상 시간: {estimatedTime}
                </>
              ) : (
                <>
                  <strong>즉시 생성 모드:</strong><br/>
                  • 생성 완료까지 브라우저 유지 필요<br/>
                  • 최대 6분 소요, 네트워크 불안 시 실패 가능
                </>
              )}
            </Alert>
          </Paper>

          {/* 생성 상태 */}
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              <Schedule sx={{ mr: 1, verticalAlign: 'middle' }} />
              생성 상태
            </Typography>

            {generationStatus === 'idle' && (
              <Box sx={{ textAlign: 'center', py: 4 }}>
                <VideoCall sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                <Typography variant="body1" sx={{ mb: 3 }}>
                  영상 생성을 시작할 준비가 되었습니다
                </Typography>
                <Alert severity="info" sx={{ mb: 3 }}>
                  예상 생성 시간: 약 {Math.ceil(estimatedTime / 60)}분
                </Alert>
                <Button
                  variant="contained"
                  size="large"
                  startIcon={<PlayArrow />}
                  onClick={startGeneration}
                >
                  영상 생성 시작
                </Button>
              </Box>
            )}

            {generationStatus === 'generating' && (
              <Box sx={{ textAlign: 'center', py: 4 }}>
                <CircularProgress size={64} sx={{ mb: 2 }} />
                <Typography variant="h6" gutterBottom>
                  영상 생성 중...
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                  {statusMessage}
                </Typography>
                <LinearProgress 
                  variant="determinate" 
                  value={progress} 
                  sx={{ mb: 2, height: 8, borderRadius: 4 }}
                />
                <Typography variant="body2" color="text.secondary">
                  {progress}% 완료 (예상 시간: {Math.ceil((100 - progress) / 100 * estimatedTime / 60)}분 남음)
                </Typography>
                <Alert severity="warning" sx={{ mt: 2 }}>
                  생성 중에는 페이지를 닫지 마세요
                </Alert>
              </Box>
            )}

            {generationStatus === 'completed' && (
              <Box sx={{ textAlign: 'center', py: 4 }}>
                {enableAsyncMode ? (
                  <>
                    <Send sx={{ fontSize: 64, color: 'success.main', mb: 2 }} />
                    <Typography variant="h6" gutterBottom>
                      작업 요청 완료!
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                      배치 작업이 시작되었습니다
                    </Typography>
                    <Alert severity="success" sx={{ mb: 2 }}>
                      {statusMessage}
                    </Alert>

                    {asyncResponse && (
                      <Card sx={{ mb: 3, textAlign: 'left' }}>
                        <CardContent>
                          <Typography variant="subtitle2" gutterBottom>
                            📧 작업 정보
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            • 작업 ID: {jobId}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            • 이메일: {asyncResponse.user_email}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            • 예상 시간: {asyncResponse.estimated_time}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            • 상태: 작업 큐에서 대기 중
                          </Typography>
                        </CardContent>
                      </Card>
                    )}

                    <Alert severity="info" sx={{ mb: 3, textAlign: 'left' }}>
                      <strong>다음 단계:</strong><br/>
                      1. 작업이 백그라운드에서 진행됩니다<br/>
                      2. 완료되면 입력하신 이메일로 다운로드 링크를 보내드립니다<br/>
                      3. 이메일의 링크를 클릭하여 영상을 다운로드하세요<br/>
                      4. 다운로드 링크는 48시간 후 만료됩니다
                    </Alert>
                  </>
                ) : (
                  <>
                    <CheckCircle sx={{ fontSize: 64, color: 'success.main', mb: 2 }} />
                    <Typography variant="h6" gutterBottom>
                      영상 생성 완료!
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                      릴스 영상이 성공적으로 생성되었습니다
                    </Typography>
                    <Alert severity="success" sx={{ mb: 3 }}>
                      {statusMessage}
                    </Alert>
                    <Button
                      variant="contained"
                      size="large"
                      startIcon={<Download />}
                      onClick={downloadVideo}
                      sx={{ mr: 2 }}
                    >
                      영상 다운로드
                    </Button>
                  </>
                )}

                <Button
                  variant="outlined"
                  size="large"
                  startIcon={<Refresh />}
                  onClick={handleNewProject}
                >
                  새 프로젝트
                </Button>
              </Box>
            )}

            {generationStatus === 'error' && (
              <Box sx={{ textAlign: 'center', py: 4 }}>
                <ErrorIcon sx={{ fontSize: 64, color: 'error.main', mb: 2 }} />
                <Typography variant="h6" gutterBottom>
                  생성 실패
                </Typography>
                <Alert severity="error" sx={{ mb: 3 }}>
                  {error}
                </Alert>
                <Button
                  variant="contained"
                  color="error"
                  size="large"
                  startIcon={<Refresh />}
                  onClick={startGeneration}
                  sx={{ mr: 2 }}
                >
                  다시 시도
                </Button>
                <Button
                  variant="outlined"
                  size="large"
                  onClick={onBack}
                >
                  설정 수정
                </Button>
              </Box>
            )}
          </Paper>
        </Grid>
      </Grid>

      {/* 하단 버튼 */}
      {generationStatus === 'idle' && (
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 4 }}>
          <Button
            variant="outlined"
            onClick={onBack}
            size="large"
          >
            이전: 음악 선택
          </Button>
        </Box>
      )}

      {/* 새 프로젝트 확인 다이얼로그 */}
      <Dialog open={showConfirmDialog} onClose={() => setShowConfirmDialog(false)}>
        <DialogTitle>새 프로젝트 시작</DialogTitle>
        <DialogContent>
          <Typography variant="body1">
            새 프로젝트를 시작하면 현재 작업 내용이 모두 초기화됩니다. 
            계속하시겠습니까?
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowConfirmDialog(false)}>취소</Button>
          <Button onClick={confirmNewProject} variant="contained" color="primary">
            확인
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default GenerateStep;