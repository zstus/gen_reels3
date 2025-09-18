import React, { useState } from 'react';
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
import ImageStep from '../components/ImageStep';
import MusicStep from '../components/MusicStep';
import GenerateStep from '../components/GenerateStep';
import { ProjectData, ReelsContent, MusicMood, ImageUploadMode, MusicFile, TextPosition, TextStyle } from '../types';

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
  
  // 프로젝트 데이터 상태
  const [projectData, setProjectData] = useState<ProjectData>({
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
    selectedMusic: null,
    musicMood: 'bright',
    fontSettings: {
      titleFont: 'BMYEONSUNG_otf.otf',
      bodyFont: 'BMYEONSUNG_otf.otf',
    },
  });

  const handleNext = () => {
    setActiveStep((prevActiveStep) => prevActiveStep + 1);
  };

  const handleBack = () => {
    setActiveStep((prevActiveStep) => prevActiveStep - 1);
  };

  const handleReset = () => {
    setActiveStep(0);
    setProjectData({
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
      selectedMusic: null,
      musicMood: 'bright',
      fontSettings: {
        titleFont: 'BMYEONSUNG_otf.otf',
        bodyFont: 'BMYEONSUNG_otf.otf',
      },
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

  const handleMusicChange = (selectedMusic: MusicFile | null, musicMood: MusicMood) => {
    setProjectData(prev => ({ 
      ...prev, 
      selectedMusic,
      musicMood 
    }));
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
            onNext={handleNext}
          />
        );
      case 1:
        return (
          <ImageStep
            images={projectData.images}
            imageUploadMode={projectData.imageUploadMode}
            content={projectData.content}
            onChange={handleImagesChange}
            onNext={handleNext}
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