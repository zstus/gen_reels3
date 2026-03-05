import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  Container,
  Stepper,
  Step,
  StepLabel,
  Typography,
  AppBar,
  Toolbar,
  Button,
  Avatar,
  IconButton,
  Menu,
  MenuItem,
} from '@mui/material';
import { AccountCircle, ExitToApp } from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';
import ContentStep from '../components/ContentStep';
import ImageStep, { ImageStepRef } from '../components/ImageStep';
import MusicStep from '../components/MusicStep';
import GenerateStep from '../components/GenerateStep';
import { ProjectData, ReelsContent, MusicMood, ImageUploadMode, MusicFile, TextPosition, TextStyle, TitleAreaMode, CrossDissolve, TTSEngine, QwenSpeaker, QwenSpeed, VideoFormat } from '../types';
import * as apiService from '../services/api';

// UUID 생성 유틸리티 함수
const generateJobId = (): string => {
  return 'job_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now().toString(36);
};

const steps = [
  '릴스 대본 작성',
  '이미지 업로드',
  '음악 선택',
  '영상 생성',
];

const MainApp: React.FC = () => {
  const { user, logout } = useAuth();
  const [activeStep, setActiveStep] = useState(0);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  // ✅ ImageStep의 ref 생성 (영상 생성 시 데이터 수집용)
  const imageStepRef = useRef<ImageStepRef>(null);
  
  // 프로젝트 데이터 상태
  const [projectData, setProjectData] = useState<ProjectData>({
    jobId: generateJobId(), // 초기 Job ID 생성
    content: {
      title: '',
      body1: '',
      body2: '',
      body3: '',
      body4: '',
      body5: '',
      body6: '',
      body7: '',
      body8: '',
    },
    images: [],
    imageUploadMode: 'per-two-scripts',
    textPosition: 'bottom',
    textStyle: 'white_background',
    titleAreaMode: 'keep',
    selectedMusic: null,
    musicMood: 'bright',
    fontSettings: {
      titleFont: 'BMHANNAPro.ttf',
      bodyFont: 'BMYEONSUNG_otf.otf',
      titleFontSize: 42,
      bodyFontSize: 27,
    },
    voiceNarration: 'enabled',
    crossDissolve: 'enabled',
    imagePanningOptions: {}, // 🎨 패닝 옵션 초기화
    // TTS 설정 초기화
    ttsEngine: 'edge',
    qwenSpeaker: 'Sohee',
    qwenSpeed: 'normal',
    qwenStyle: 'neutral',
    edgeSpeaker: 'female',
    edgeSpeed: 'normal',
    edgePitch: 'normal',
    perBodyTTSEnabled: false,
    perBodyTTSSettings: {},
    videoFormat: 'reels',
  });

  // 브라우저 히스토리 연동: 뒤로가기 버튼이 이전 단계로 이동하도록
  useEffect(() => {
    window.history.replaceState({ step: 0 }, '', window.location.pathname);

    const handlePopState = (event: PopStateEvent) => {
      if (event.state && typeof event.state.step === 'number') {
        setActiveStep(event.state.step);
      }
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const handleNext = () => {
    const nextStep = activeStep + 1;
    window.history.pushState({ step: nextStep }, '', window.location.pathname);
    setActiveStep(nextStep);
  };

  const handleBack = () => {
    window.history.back(); // popstate 이벤트 발생 → setActiveStep 자동 처리
  };

  const handleReset = () => {
    window.history.replaceState({ step: 0 }, '', window.location.pathname);
    setActiveStep(0);
    setProjectData({
      jobId: generateJobId(), // 새로운 Job ID 생성
      content: {
        title: '',
        body1: '',
        body2: '',
        body3: '',
        body4: '',
        body5: '',
        body6: '',
        body7: '',
        body8: '',
      },
      images: [],
      imageUploadMode: 'per-two-scripts',
      textPosition: 'bottom',
      textStyle: 'outline',
      titleAreaMode: 'keep',
      selectedMusic: null,
      musicMood: 'bright',
      fontSettings: {
        titleFont: 'BMHANNAPro.ttf',
        bodyFont: 'BMYEONSUNG_otf.otf',
        titleFontSize: 42,
        bodyFontSize: 27,
      },
      voiceNarration: 'enabled',
      crossDissolve: 'enabled',
      imagePanningOptions: {},
      // TTS 설정 초기화
      ttsEngine: 'edge',
      qwenSpeaker: 'Sohee',
      qwenSpeed: 'normal',
      qwenStyle: 'neutral',
      edgeSpeaker: 'female',
      edgeSpeed: 'normal',
      edgePitch: 'normal',
      perBodyTTSEnabled: false,
      perBodyTTSSettings: {},
      videoFormat: 'reels',
    });
  };

  const handleContentChange = (content: ReelsContent) => {
    setProjectData(prev => ({ ...prev, content }));
  };

  const handleImagesChange = (images: File[], mode: ImageUploadMode) => {
    setProjectData(prev => ({
      ...prev,
      images,
      imageUploadMode: mode
    }));
  };

  // 🎨 패닝 옵션 변경 핸들러
  const handlePanningOptionsChange = (options: { [key: number]: boolean }) => {
    setProjectData(prev => ({
      ...prev,
      imagePanningOptions: options
    }));
  };

  // ✅ editedTexts는 ImageStep의 ref를 통해 가져오므로 불필요

  const handleMusicChange = (selectedMusic: MusicFile | null, musicMood: MusicMood) => {
    setProjectData(prev => ({
      ...prev,
      selectedMusic,
      musicMood
    }));
  };

  // ContentStep에서 "다음" 버튼을 누를 때 job 폴더 생성
  const handleContentStepNext = async () => {
    try {
      console.log('🚀 Job 폴더 생성 중:', projectData.jobId);

      // Backend에 job 폴더 생성 요청
      await apiService.createJobFolder(projectData.jobId);

      console.log('✅ Job 폴더 생성 완료:', projectData.jobId);

      // 다음 단계로 이동
      handleNext();
    } catch (error) {
      console.error('❌ Job 폴더 생성 실패:', error);

      // Job ID를 새로 생성하고 재시도 또는 사용자에게 알림
      alert('작업 폴더 생성에 실패했습니다. 다시 시도해주세요.');
    }
  };

  // ImageStep에서 "다음" 버튼을 누를 때 수정된 텍스트를 projectData에 반영
  const handleImageStepNext = () => {
    // ImageStep ref에서 수정된 텍스트 수집
    const { editedTexts } = imageStepRef.current?.getEditedData() || { editedTexts: {} };

    // 원본 content 복사
    const updatedContent = { ...projectData.content };

    // editedTexts를 content에 병합
    Object.keys(editedTexts).forEach(imageIndexStr => {
      const imageIndex = parseInt(imageIndexStr);
      const texts = editedTexts[imageIndex];

      if (texts && texts.length > 0) {
        if (projectData.imageUploadMode === 'per-two-scripts') {
          // per-two-scripts: imageIndex 0 → body1, body2 / imageIndex 1 → body3, body4
          const startIdx = imageIndex * 2 + 1;
          texts.forEach((text, idx) => {
            const bodyKey = `body${startIdx + idx}` as keyof ReelsContent;
            if (text) {
              updatedContent[bodyKey] = text;
            }
          });
        } else if (projectData.imageUploadMode === 'per-script') {
          // per-script: imageIndex 0 → body1 / imageIndex 1 → body2
          const bodyKey = `body${imageIndex + 1}` as keyof ReelsContent;
          if (texts[0]) {
            updatedContent[bodyKey] = texts[0];
          }
        } else if (projectData.imageUploadMode === 'single-for-all') {
          // single-for-all: imageIndex는 항상 0, texts에 모든 대사 포함
          texts.forEach((text, idx) => {
            const bodyKey = `body${idx + 1}` as keyof ReelsContent;
            if (text) {
              updatedContent[bodyKey] = text;
            }
          });
        }
      }
    });

    console.log('✅ 수정된 텍스트 세션에 반영:', updatedContent);

    // projectData 업데이트
    setProjectData(prev => ({ ...prev, content: updatedContent }));

    // 다음 단계로 이동
    handleNext();
  };


  const handleMenuClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = () => {
    handleMenuClose();
    logout();
  };

  const getStepContent = (step: number) => {
    switch (step) {
      case 0:
        return (
          <ContentStep
            content={projectData.content}
            onChange={handleContentChange}
            onNext={handleContentStepNext} // Job 폴더 생성을 포함한 핸들러 사용
          />
        );
      case 1:
        return (
          <ImageStep
            ref={imageStepRef}
            images={projectData.images}
            imageUploadMode={projectData.imageUploadMode}
            content={projectData.content}
            jobId={projectData.jobId}
            imagePanningOptions={projectData.imagePanningOptions || {}}
            onChange={handleImagesChange}
            onPanningOptionsChange={handlePanningOptionsChange}
            onNext={handleImageStepNext}
            onBack={handleBack}
          />
        );
      case 2:
        return (
          <MusicStep
            selectedMusic={projectData.selectedMusic}
            musicMood={projectData.musicMood}
            onChange={handleMusicChange}
            onNext={handleNext}
            onBack={handleBack}
          />
        );
      case 3:
        return (
          <GenerateStep
            projectData={projectData}
            imageStepRef={imageStepRef}
            onBack={handleBack}
            onReset={handleReset}
          />
        );
      default:
        return null;
    }
  };

  return (
    <Box>
      {/* 상단 헤더 */}
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            릴스 영상 생성기
          </Typography>
          
          {user && (
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <Typography variant="body2" sx={{ mr: 1 }}>
                {user.name}
              </Typography>
              <IconButton
                size="large"
                onClick={handleMenuClick}
                color="inherit"
              >
                {user.picture ? (
                  <Avatar src={user.picture} sx={{ width: 32, height: 32 }} />
                ) : (
                  <AccountCircle />
                )}
              </IconButton>
              <Menu
                anchorEl={anchorEl}
                open={Boolean(anchorEl)}
                onClose={handleMenuClose}
              >
                <MenuItem onClick={handleLogout}>
                  <ExitToApp sx={{ mr: 1 }} />
                  로그아웃
                </MenuItem>
              </Menu>
            </Box>
          )}
        </Toolbar>
      </AppBar>

      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        {/* 단계 표시기 */}
        <Box sx={{ mb: 4 }}>
          <Stepper activeStep={activeStep}>
            {steps.map((label) => (
              <Step key={label}>
                <StepLabel>{label}</StepLabel>
              </Step>
            ))}
          </Stepper>
        </Box>

        {/* 메인 콘텐츠 */}
        <Box>
          {getStepContent(activeStep)}
        </Box>
      </Container>
    </Box>
  );
};

export default MainApp;