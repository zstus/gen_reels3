import React, { useState, useCallback, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Grid,
  FormControl,
  FormLabel,
  RadioGroup,
  FormControlLabel,
  Radio,
  Alert,
  Card,
  CardContent,
  IconButton,
  Chip,
  LinearProgress,
} from '@mui/material';
import { CloudUpload, Delete, Image as ImageIcon } from '@mui/icons-material';
import { useDropzone } from 'react-dropzone';
import { ReelsContent, ImageUploadMode } from '../types';

interface ImageStepProps {
  images: File[];
  imageUploadMode: ImageUploadMode;
  content: ReelsContent;
  onChange: (images: File[], mode: ImageUploadMode) => void;
  onNext: () => void;
  onBack: () => void;
}

const ImageStep: React.FC<ImageStepProps> = ({
  images,
  imageUploadMode,
  content,
  onChange,
  onNext,
  onBack,
}) => {
  const [uploadProgress, setUploadProgress] = useState<{ [key: string]: number }>({});
  const [errors, setErrors] = useState<string[]>([]);

  // 필요한 이미지 개수 계산
  const getRequiredImageCount = () => {
    const scriptCount = Object.values(content)
      .slice(1) // title 제외
      .filter(script => script?.trim()).length;
    
    if (imageUploadMode === 'per-script') {
      return scriptCount;
    } else {
      return Math.ceil(scriptCount / 2);
    }
  };

  const requiredImageCount = getRequiredImageCount();

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const validFiles: File[] = [];
    const newErrors: string[] = [];

    acceptedFiles.forEach((file, index) => {
      // 파일 크기 검증 (10MB)
      if (file.size > 10 * 1024 * 1024) {
        newErrors.push(`${file.name}: 파일 크기가 10MB를 초과합니다`);
        return;
      }

      // 파일 형식 검증 (이미지 + 비디오)
      const isImage = file.type.startsWith('image/');
      const isVideo = file.type.startsWith('video/');
      
      if (!isImage && !isVideo) {
        newErrors.push(`${file.name}: 이미지 또는 비디오 파일만 업로드 가능합니다`);
        return;
      }

      validFiles.push(file);

      // 업로드 진행률 시뮬레이션
      setUploadProgress(prev => ({ ...prev, [file.name]: 0 }));
      
      // 가상의 업로드 진행률
      let progress = 0;
      const interval = setInterval(() => {
        progress += 10;
        setUploadProgress(prev => ({ ...prev, [file.name]: progress }));
        
        if (progress >= 100) {
          clearInterval(interval);
          setTimeout(() => {
            setUploadProgress(prev => {
              const newProgress = { ...prev };
              delete newProgress[file.name];
              return newProgress;
            });
          }, 500);
        }
      }, 100);
    });

    if (validFiles.length > 0) {
      const newImages = [...images, ...validFiles].slice(0, requiredImageCount);
      onChange(newImages, imageUploadMode);
    }

    setErrors(newErrors);
  }, [images, imageUploadMode, requiredImageCount, onChange]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.jpeg', '.jpg', '.png', '.gif', '.webp', '.bmp'],
      'video/*': ['.mp4', '.mov', '.avi', '.webm']
    },
    maxFiles: requiredImageCount - images.length,
    disabled: images.length >= requiredImageCount
  });

  const removeImage = (index: number) => {
    const newImages = images.filter((_, i) => i !== index);
    onChange(newImages, imageUploadMode);
  };

  const handleModeChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const newMode = event.target.value as ImageUploadMode;
    const newRequiredCount = newMode === 'per-script' 
      ? Object.values(content).slice(1).filter(script => script?.trim()).length
      : Math.ceil(Object.values(content).slice(1).filter(script => script?.trim()).length / 2);
    
    // 기존 이미지가 새로운 요구사항보다 많으면 자르기
    const newImages = images.slice(0, newRequiredCount);
    onChange(newImages, newMode);
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getMediaPreview = (file: File) => {
    return URL.createObjectURL(file);
  };

  const isVideoFile = (file: File) => {
    return file.type.startsWith('video/');
  };

  const canProceed = images.length === requiredImageCount;

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        미디어 업로드
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        릴스 영상의 배경으로 사용할 이미지 또는 영상을 업로드하세요. (이미지: JPG, PNG, GIF, WebP / 영상: MP4, MOV, AVI, WebM)
      </Typography>

      <Grid container spacing={3}>
        {/* 왼쪽: 업로드 설정 */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              업로드 모드 선택
            </Typography>
            
            <FormControl component="fieldset">
              <RadioGroup
                value={imageUploadMode}
                onChange={handleModeChange}
              >
                <FormControlLabel
                  value="per-two-scripts"
                  control={<Radio />}
                  label={
                    <Box>
                      <Typography variant="body1">
                        대사 2개마다 미디어 1개
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        필요 미디어: {Math.ceil(Object.values(content).slice(1).filter(script => script?.trim()).length / 2)}개
                      </Typography>
                    </Box>
                  }
                />
                <FormControlLabel
                  value="per-script"
                  control={<Radio />}
                  label={
                    <Box>
                      <Typography variant="body1">
                        대사마다 미디어 1개
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        필요 미디어: {Object.values(content).slice(1).filter(script => script?.trim()).length}개
                      </Typography>
                    </Box>
                  }
                />
              </RadioGroup>
            </FormControl>
          </Paper>

          {/* 드래그 앤 드롭 영역 */}
          <Paper sx={{ p: 3 }}>
            <Box
              {...getRootProps()}
              sx={{
                border: 2,
                borderColor: isDragActive ? 'primary.main' : 'grey.300',
                borderStyle: 'dashed',
                borderRadius: 2,
                p: 4,
                textAlign: 'center',
                cursor: images.length >= requiredImageCount ? 'not-allowed' : 'pointer',
                bgcolor: isDragActive ? 'action.hover' : 'background.paper',
                opacity: images.length >= requiredImageCount ? 0.6 : 1,
                transition: 'all 0.2s ease-in-out',
                '&:hover': {
                  borderColor: images.length >= requiredImageCount ? 'grey.300' : 'primary.main',
                  bgcolor: images.length >= requiredImageCount ? 'background.paper' : 'action.hover',
                }
              }}
            >
              <input {...getInputProps()} />
              <CloudUpload sx={{ fontSize: 48, color: 'grey.400', mb: 2 }} />
              <Typography variant="h6" gutterBottom>
                {isDragActive ? '여기에 파일을 놓으세요' : '미디어 파일을 드래그하거나 클릭하여 선택'}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                지원 형식: JPG, PNG, GIF, WebP, BMP, MP4, MOV, AVI, WebM (최대 10MB)
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                업로드 상태: {images.length}/{requiredImageCount}개
              </Typography>
            </Box>

            {/* 업로드 진행률 */}
            {Object.entries(uploadProgress).map(([filename, progress]) => (
              <Box key={filename} sx={{ mt: 2 }}>
                <Typography variant="caption" color="text.secondary">
                  {filename} 업로드 중...
                </Typography>
                <LinearProgress variant="determinate" value={progress} sx={{ mt: 0.5 }} />
              </Box>
            ))}

            {/* 에러 메시지 */}
            {errors.map((error, index) => (
              <Alert severity="error" key={index} sx={{ mt: 2 }}>
                {error}
              </Alert>
            ))}
          </Paper>
        </Grid>

        {/* 오른쪽: 업로드된 미디어 미리보기 */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              업로드된 미디어 ({images.length}/{requiredImageCount})
            </Typography>

            {images.length === 0 ? (
              <Box
                sx={{
                  textAlign: 'center',
                  py: 4,
                  color: 'text.secondary'
                }}
              >
                <ImageIcon sx={{ fontSize: 64, mb: 2 }} />
                <Typography variant="body2">
                  아직 업로드된 미디어가 없습니다
                </Typography>
              </Box>
            ) : (
              <Grid container spacing={2}>
                {images.map((file, index) => (
                  <Grid item xs={6} key={index}>
                    <Card sx={{ position: 'relative' }}>
                      {isVideoFile(file) ? (
                        <video
                          src={getMediaPreview(file)}
                          style={{
                            width: '100%',
                            height: 120,
                            objectFit: 'cover',
                          }}
                          muted
                          loop
                          autoPlay
                        />
                      ) : (
                        <Box
                          sx={{
                            width: '100%',
                            height: 120,
                            backgroundImage: `url(${getMediaPreview(file)})`,
                            backgroundSize: 'cover',
                            backgroundPosition: 'center',
                            position: 'relative'
                          }}
                        />
                      )}
                      <IconButton
                        size="small"
                        onClick={() => removeImage(index)}
                        sx={{
                          position: 'absolute',
                          top: 4,
                          right: 4,
                          bgcolor: 'rgba(255,255,255,0.8)',
                          zIndex: 1,
                          '&:hover': {
                            bgcolor: 'rgba(255,255,255,0.9)'
                          }
                        }}
                      >
                        <Delete color="error" />
                      </IconButton>
                      <Chip
                        label={index + 1}
                        size="small"
                        color="primary"
                        sx={{
                          position: 'absolute',
                          top: 4,
                          left: 4
                        }}
                      />
                      <CardContent sx={{ p: 1 }}>
                        <Typography variant="caption" noWrap>
                          {file.name}
                        </Typography>
                        <Typography variant="caption" color="text.secondary" display="block">
                          {formatFileSize(file.size)}
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            )}

            {!canProceed && images.length > 0 && (
              <Alert severity="info" sx={{ mt: 2 }}>
                {requiredImageCount - images.length}개의 미디어를 더 업로드해주세요
              </Alert>
            )}

            {canProceed && (
              <Alert severity="success" sx={{ mt: 2 }}>
                모든 미디어가 업로드되었습니다! 다음 단계로 진행할 수 있습니다.
              </Alert>
            )}
          </Paper>
        </Grid>
      </Grid>

      {/* 하단 버튼 */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 4 }}>
        <Button
          variant="outlined"
          onClick={onBack}
          size="large"
        >
          이전: 대본 작성
        </Button>
        <Button
          variant="contained"
          onClick={onNext}
          size="large"
          disabled={!canProceed}
        >
          다음: 음악 선택
        </Button>
      </Box>
    </Box>
  );
};

export default ImageStep;