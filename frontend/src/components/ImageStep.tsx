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
  CircularProgress,
  Divider,
} from '@mui/material';
import { CloudUpload, Delete, Image as ImageIcon, AutoFixHigh } from '@mui/icons-material';
import { useDropzone } from 'react-dropzone';
import { ReelsContent, ImageUploadMode } from '../types';
import TextImagePairManager from './TextImagePairManager';

interface ImageStepProps {
  images: File[];
  imageUploadMode: ImageUploadMode;
  content: ReelsContent;
  jobId: string; // Job ID 추가
  onChange: (images: File[], mode: ImageUploadMode) => void;
  onNext: () => void;
  onBack: () => void;
}

const ImageStep: React.FC<ImageStepProps> = ({
  images,
  imageUploadMode,
  content,
  jobId, // Job ID 추가
  onChange,
  onNext,
  onBack,
}) => {
  const [uploadProgress, setUploadProgress] = useState<{ [key: string]: number }>({});
  const [errors, setErrors] = useState<string[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationProgress, setGenerationProgress] = useState('');

  // 필요한 이미지 개수 계산
  const getRequiredImageCount = () => {
    const scriptCount = Object.values(content)
      .slice(1) // title 제외
      .filter(script => script?.trim()).length;

    if (imageUploadMode === 'per-script') {
      return scriptCount;
    } else if (imageUploadMode === 'per-two-scripts') {
      return Math.ceil(scriptCount / 2);
    } else { // single-for-all
      return 1;
    }
  };

  const requiredImageCount = getRequiredImageCount();

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const validFiles: File[] = [];
    const newErrors: string[] = [];

    acceptedFiles.forEach((file, index) => {
      // 파일 크기 검증 (모드에 따라 다른 제한)
      const maxSize = imageUploadMode === 'single-for-all' ? 80 * 1024 * 1024 : 40 * 1024 * 1024;
      const maxSizeText = imageUploadMode === 'single-for-all' ? '80MB' : '40MB';

      if (file.size > maxSize) {
        newErrors.push(`${file.name}: 파일 크기가 ${maxSizeText}를 초과합니다`);
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
      // 스마트 이미지 할당: 빈 슬롯부터 채우기
      const updatedImages = [...images];
      
      // 각 valid 파일에 대해 첫 번째로 비어있는 슬롯에 __imageIndex 설정하여 추가
      let validFileIndex = 0;
      for (let i = 0; i < requiredImageCount && validFileIndex < validFiles.length; i++) {
        // 해당 인덱스에 이미지가 없으면 새 파일 할당
        const hasImageAtIndex = images.some(img => (img as any).__imageIndex === i);
        if (!hasImageAtIndex) {
          const file = validFiles[validFileIndex];
          (file as any).__imageIndex = i;
          updatedImages.push(file);
          validFileIndex++;
        }
      }
      
      // 위치 정보 기준으로 정렬
      updatedImages.sort((a, b) => {
        const indexA = (a as any).__imageIndex ?? 0;
        const indexB = (b as any).__imageIndex ?? 0;
        return indexA - indexB;
      });
      
      onChange(updatedImages, imageUploadMode);
    }

    setErrors(newErrors);
  }, [images, imageUploadMode, requiredImageCount, onChange]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.jpeg', '.jpg', '.png', '.gif', '.webp', '.bmp'],
      'video/*': ['.mp4', '.mov', '.avi', '.webm', '.mkv']
    },
    // 무제한 파일 업로드 허용 (빈 슬롯에 자동 할당)
    maxFiles: undefined,
    disabled: false
  });

  const removeImage = (imageIndex: number) => {
    // 특정 __imageIndex를 가진 파일만 제거
    const newImages = images.filter(img => (img as any).__imageIndex !== imageIndex);
    onChange(newImages, imageUploadMode);
  };

  const handleModeChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const newMode = event.target.value as ImageUploadMode;
    const scriptCount = Object.values(content).slice(1).filter(script => script?.trim()).length;

    let newRequiredCount;
    if (newMode === 'per-script') {
      newRequiredCount = scriptCount;
    } else if (newMode === 'per-two-scripts') {
      newRequiredCount = Math.ceil(scriptCount / 2);
    } else { // single-for-all
      newRequiredCount = 1;
    }

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

  // 위치 정보가 있는 실제 이미지 개수 계산
  const getActualImageCount = () => {
    return images.filter(img => typeof (img as any).__imageIndex === 'number').length;
  };

  const canProceed = getActualImageCount() === requiredImageCount;

  // 자동 이미지 생성 함수
  const handleAutoGenerate = async (mode: 'per_script' | 'per_two_scripts' | 'single_for_all') => {
    setIsGenerating(true);
    setErrors([]);
    
    try {
      // content에서 body 텍스트들 추출
      const bodyTexts = Object.entries(content)
        .filter(([key, value]) => key.startsWith('body') && value?.trim())
        .map(([key, value]) => value.trim());
      
      if (bodyTexts.length === 0) {
        setErrors(['대본 내용이 없습니다. 먼저 대본을 작성해주세요.']);
        setIsGenerating(false);
        return;
      }

      setGenerationProgress('이미지 생성 중...');
      
      const response = await fetch('/generate-images', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          texts: bodyTexts,
          mode: mode,
          job_id: jobId  // Job ID 추가
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || ' 이미지 생성에 실패했습니다');
      }

      const data = await response.json();
      const imageUrls = data.image_urls;

      setGenerationProgress('이미지 다운로드 중...');
      
      // 백엔드에서 저장된 이미지를 다운로드하고 File 객체로 변환
      const imageFiles = await Promise.all(
        imageUrls.filter((url: string) => url.trim() !== '').map(async (url: string, index: number) => {
          // 백엔드와 같은 서버를 사용하므로 상대 경로로 접근
          const fullUrl = url.startsWith('http') ? url : url;
          const imageResponse = await fetch(fullUrl);
          if (!imageResponse.ok) {
            throw new Error(`이미지 다운로드 실패: ${index + 1}`);
          }
          
          const blob = await imageResponse.blob();
          const fileName = `generated_image_${index + 1}.png`;
          const file = new File([blob], fileName, { type: 'image/png' });
          
          // 🔧 중요: TextImagePairManager에서 매칭을 위한 __imageIndex 설정
          (file as any).__imageIndex = index;
          
          return file;
        })
      );

      // 🔧 기존 이미지와 새로 생성된 이미지를 스마트하게 병합
      // 빈 슬롯부터 채우고, imageIndex 순으로 정렬
      const updatedImages = [...images];
      
      imageFiles.forEach((file) => {
        const targetIndex = (file as any).__imageIndex;
        // 해당 인덱스에 기존 이미지가 있으면 교체, 없으면 추가
        const existingIndex = updatedImages.findIndex(img => (img as any).__imageIndex === targetIndex);
        if (existingIndex >= 0) {
          updatedImages[existingIndex] = file;
        } else {
          updatedImages.push(file);
        }
      });
      
      // imageIndex 순으로 정렬
      updatedImages.sort((a, b) => {
        const indexA = (a as any).__imageIndex ?? 0;
        const indexB = (b as any).__imageIndex ?? 0;
        return indexA - indexB;
      });
      
      // 필요한 개수만큼만 유지
      const finalImages = updatedImages.slice(0, requiredImageCount);
      onChange(finalImages, imageUploadMode);
      
      const successCount = imageFiles.length;
      const totalRequested = imageUrls.length;
      
      if (successCount === totalRequested) {
        setGenerationProgress('이미지 생성 완료!');
      } else {
        setGenerationProgress(`이미지 생성 완료! (${successCount}/${totalRequested}개 성공)`);
      }
      
      setTimeout(() => setGenerationProgress(''), 3000);
      
    } catch (error) {
      console.error('이미지 생성 중 오류:', error);
      setErrors([error instanceof Error ? error.message : '이미지 생성 중 오류가 발생했습니다']);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        미디어 업로드
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        릴스 영상의 배경으로 사용할 이미지 또는 영상을 업로드하세요. (이미지: JPG, PNG, GIF, WebP / 영상: MP4, MOV, AVI, WebM, MKV)
      </Typography>

      {/* 업로드 모드 선택 */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          업로드 모드 선택
        </Typography>
        
        <FormControl component="fieldset">
          <RadioGroup
            value={imageUploadMode}
            onChange={handleModeChange}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
              <FormControlLabel
                value="per-two-scripts"
                control={<Radio />}
                label={
                  <Box>
                    <Typography variant="body1">
                      대사 2개마다 미디어 1개
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      필요 미디어: {Math.ceil(Object.values(content).slice(1).filter(script => script?.trim()).length / 2)}개 (각 최대 10MB)
                    </Typography>
                  </Box>
                }
              />
              <Button
                variant="outlined"
                size="small"
                startIcon={<AutoFixHigh />}
                onClick={() => handleAutoGenerate('per_two_scripts')}
                disabled={isGenerating || Object.values(content).slice(1).filter(script => script?.trim()).length === 0}
                sx={{ ml: 2, minWidth: 100 }}
              >
                자동생성
              </Button>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
              <FormControlLabel
                value="per-script"
                control={<Radio />}
                label={
                  <Box>
                    <Typography variant="body1">
                      대사마다 미디어 1개
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      필요 미디어: {Object.values(content).slice(1).filter(script => script?.trim()).length}개 (각 최대 10MB)
                    </Typography>
                  </Box>
                }
              />
              <Button
                variant="outlined"
                size="small"
                startIcon={<AutoFixHigh />}
                onClick={() => handleAutoGenerate('per_script')}
                disabled={isGenerating || Object.values(content).slice(1).filter(script => script?.trim()).length === 0}
                sx={{ ml: 2, minWidth: 100 }}
              >
                자동생성
              </Button>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
              <FormControlLabel
                value="single-for-all"
                control={<Radio />}
                label={
                  <Box>
                    <Typography variant="body1">
                      모든 대사에 미디어 1개
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      필요 미디어: 1개 (모든 대사에 동일한 미디어 사용, 최대 40MB)
                    </Typography>
                  </Box>
                }
              />
              <Button
                variant="outlined"
                size="small"
                startIcon={<AutoFixHigh />}
                onClick={() => handleAutoGenerate('single_for_all')}
                disabled={isGenerating || Object.values(content).slice(1).filter(script => script?.trim()).length === 0}
                sx={{ ml: 2, minWidth: 100 }}
              >
                자동생성
              </Button>
            </Box>
          </RadioGroup>
        </FormControl>
        
        {/* 생성 진행 상황 표시 */}
        {isGenerating && (
          <Box sx={{ mt: 2, display: 'flex', alignItems: 'center' }}>
            <CircularProgress size={20} sx={{ mr: 1 }} />
            <Typography variant="body2" color="primary">
              {generationProgress}
            </Typography>
          </Box>
        )}
        
        {generationProgress && !isGenerating && (
          <Alert severity="success" sx={{ mt: 2 }}>
            {generationProgress}
          </Alert>
        )}
      </Paper>

      {/* 미디어 파일 멀티 드래그 영역 */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          미디어 파일 멀티 드래그 영역
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          여러 미디어 파일을 한 번에 드래그하여 업로드하세요. 빈 슬롯부터 자동으로 채워집니다.
        </Typography>
        
        <Box
          {...getRootProps()}
          sx={{
            border: 2,
            borderColor: isDragActive ? 'primary.main' : 'grey.300',
            borderStyle: 'dashed',
            borderRadius: 2,
            p: 4,
            textAlign: 'center',
            cursor: 'pointer',
            bgcolor: isDragActive ? 'action.hover' : 'background.paper',
            transition: 'all 0.2s ease-in-out',
            '&:hover': {
              borderColor: 'primary.main',
              bgcolor: 'action.hover',
            }
          }}
        >
          <input {...getInputProps()} />
          <CloudUpload sx={{ fontSize: 48, color: 'grey.400', mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            {isDragActive ? '여기에 파일을 놓으세요' : '미디어 파일을 드래그하거나 클릭하여 선택'}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            지원 형식: JPG, PNG, GIF, WebP, BMP, MP4, MOV, AVI, WebM, MKV (최대 {imageUploadMode === 'single-for-all' ? '40MB' : '10MB'})
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            현재 상태: {getActualImageCount()}/{requiredImageCount}개
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
        
        {/* 진행률 표시 */}
        {canProceed && (
          <Alert severity="success" sx={{ mt: 2 }}>
            모든 미디어가 업로드되었습니다! 다음 단계로 진행할 수 있습니다.
          </Alert>
        )}
      </Paper>

      {/* 텍스트-이미지 매칭 관리 영역 */}
      <Box sx={{ mt: 4 }}>
        <Divider sx={{ mb: 3 }} />
        <TextImagePairManager
          content={content}
          imageUploadMode={imageUploadMode}
          images={images}
          jobId={jobId} // Job ID 전달
          onChange={onChange}
        />
      </Box>

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