import React, { useState, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Grid,
  Card,
  CardContent,
  IconButton,
  Chip,
  Alert,
  CircularProgress,
} from '@mui/material';
import { 
  CloudUpload, 
  Delete, 
  AutoFixHigh, 
  Refresh,
  Image as ImageIcon,
  Download
} from '@mui/icons-material';
import { useDropzone } from 'react-dropzone';
import { ReelsContent, ImageUploadMode } from '../types';

interface TextImagePair {
  textIndex: number;
  textKey: string;
  textContent: string;
  image: File | null;
  isGenerating: boolean;
}

interface TextImagePairManagerProps {
  content: ReelsContent;
  imageUploadMode: ImageUploadMode;
  images: File[];
  onChange: (images: File[], mode: ImageUploadMode) => void;
}

const TextImagePairManager: React.FC<TextImagePairManagerProps> = ({
  content,
  imageUploadMode,
  images,
  onChange,
}) => {
  const [generationStatus, setGenerationStatus] = useState<{ [key: string]: string }>({});
  const [uploadErrors, setUploadErrors] = useState<{ [key: number]: string }>({});

  // 텍스트-이미지 쌍 데이터 생성
  const createTextImagePairs = (): (TextImagePair & { imageIndex: number })[] => {
    const bodyTexts = Object.entries(content)
      .filter(([key, value]) => key.startsWith('body') && value?.trim())
      .map(([key, value], index) => ({ key, value: value.trim(), index }));

    // 위치 정보를 가진 이미지들을 맵으로 생성
    const imageMap = new Map<number, File>();
    images.forEach(img => {
      const storedIndex = (img as any).__imageIndex;
      if (typeof storedIndex === 'number') {
        imageMap.set(storedIndex, img);
      }
    });

    console.log('🗺️ createTextImagePairs - imageMap:', Array.from(imageMap.entries()).map(([idx, file]) => `${idx}:${file.name}`));
    console.log('📝 bodyTexts 길이:', bodyTexts.length, 'imageUploadMode:', imageUploadMode);
    console.log('🔍 받은 images 배열:', images.map(img => `${img.name}(__imageIndex:${(img as any).__imageIndex})`));

    const pairs: (TextImagePair & { imageIndex: number })[] = [];

    if (imageUploadMode === 'per-script') {
      // 텍스트 1개당 이미지 1개
      bodyTexts.forEach(({ key, value, index }) => {
        const foundImage = imageMap.get(index);
        console.log(`📋 per-script: textIndex=${index}, imageIndex=${index}, foundImage=${foundImage?.name || 'null'}`);
        pairs.push({
          textIndex: index,
          textKey: key,
          textContent: value,
          image: foundImage || null,
          imageIndex: index, // 실제 이미지 인덱스 저장
          isGenerating: false,
        });
      });
    } else {
      // 텍스트 2개당 이미지 1개
      for (let i = 0; i < bodyTexts.length; i += 2) {
        const imageIndex = Math.floor(i / 2);
        const text1 = bodyTexts[i];
        const text2 = bodyTexts[i + 1];
        
        if (text1) {
          const foundImage = imageMap.get(imageIndex);
          console.log(`📋 per-two-scripts: textIndex=${i}, imageIndex=${imageIndex}, foundImage=${foundImage?.name || 'null'}`);
          pairs.push({
            textIndex: i,
            textKey: `${text1.key}${text2 ? `+${text2.key}` : ''}`,
            textContent: `${text1.value}${text2 ? ` / ${text2.value}` : ''}`,
            image: foundImage || null,
            imageIndex: imageIndex, // 실제 이미지 인덱스 저장
            isGenerating: false,
          });
        }
      }
    }

    console.log('🎯 최종 pairs 개수:', pairs.length);
    return pairs;
  };

  const textImagePairs = createTextImagePairs();
  
  // 현재 images 배열 상태 로깅
  console.log('📦 현재 images 배열 길이:', images.length);
  console.log('📦 현재 images 배열:', images.length > 0 ? images.map(img => `${img.name}(index:${(img as any).__imageIndex})`) : '빈 배열');
  console.log('🎮 generationStatus:', generationStatus);

  // 개별 이미지 업로드 핸들러
  const handleIndividualImageUpload = useCallback((imageIndex: number, acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;

    const file = acceptedFiles[0];
    
    // 기존 에러 상태 제거
    setUploadErrors(prev => {
      const newErrors = { ...prev };
      delete newErrors[imageIndex];
      return newErrors;
    });
    
    // 파일 유효성 검증
    if (file.size > 10 * 1024 * 1024) {
      setUploadErrors(prev => ({ ...prev, [imageIndex]: '파일 크기가 10MB를 초과합니다' }));
      return;
    }

    const isImage = file.type.startsWith('image/');
    const isVideo = file.type.startsWith('video/');
    
    if (!isImage && !isVideo) {
      setUploadErrors(prev => ({ ...prev, [imageIndex]: '이미지 또는 비디오 파일만 업로드 가능합니다' }));
      return;
    }

    console.log('🔧 handleIndividualImageUpload - imageIndex:', imageIndex, 'fileName:', file.name);

    // 파일에 위치 정보 추가
    (file as any).__imageIndex = imageIndex;
    console.log('🏷️ 파일에 __imageIndex 설정:', imageIndex);

    // 현재 images에서 해당 imageIndex를 가진 파일 제거하고 새 파일 추가
    const newImages = images.filter(img => (img as any).__imageIndex !== imageIndex);
    newImages.push(file);
    
    // imageIndex 순으로 정렬
    newImages.sort((a, b) => {
      const indexA = (a as any).__imageIndex ?? 0;
      const indexB = (b as any).__imageIndex ?? 0;
      return indexA - indexB;
    });
    
    console.log('📊 업데이트된 images 배열:', newImages.map(img => `${img.name}(index:${(img as any).__imageIndex})`));
    
    onChange(newImages, imageUploadMode);
  }, [images, imageUploadMode, content, onChange]);

  // 개별 이미지 자동 생성
  const handleIndividualGenerate = async (imageIndex: number, textContent: string) => {
    console.log('🤖 handleIndividualGenerate 시작 - imageIndex:', imageIndex, 'textContent:', textContent);
    setGenerationStatus(prev => ({ ...prev, [imageIndex]: 'generating' }));

    try {
      // 텍스트를 분리 (2개 텍스트가 합쳐진 경우)
      const texts = textContent.split(' / ');
      
      const response = await fetch('/generate-single-image', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: texts[0], // 첫 번째 텍스트 사용
          additional_context: texts.length > 1 ? texts[1] : null
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '이미지 생성에 실패했습니다');
      }

      const data = await response.json();
      const imageUrl = data.image_url;

      // 생성된 이미지를 다운로드하고 File 객체로 변환
      const imageResponse = await fetch(imageUrl);
      if (!imageResponse.ok) {
        throw new Error('생성된 이미지 다운로드에 실패했습니다');
      }

      const blob = await imageResponse.blob();
      const fileName = `generated_image_pair_${imageIndex}.png`;
      const file = new File([blob], fileName, { type: 'image/png' });

      console.log('📸 이미지 생성 완료 - fileName:', fileName, '호출할 imageIndex:', imageIndex);

      // 이미지 배열 업데이트
      handleIndividualImageUpload(imageIndex, [file]);
      
      setGenerationStatus(prev => ({ ...prev, [imageIndex]: 'success' }));
      setTimeout(() => {
        setGenerationStatus(prev => {
          const newStatus = { ...prev };
          delete newStatus[imageIndex];
          return newStatus;
        });
      }, 3000);

    } catch (error) {
      console.error('개별 이미지 생성 오류:', error);
      setGenerationStatus(prev => ({ ...prev, [imageIndex]: 'error' }));
      setTimeout(() => {
        setGenerationStatus(prev => {
          const newStatus = { ...prev };
          delete newStatus[imageIndex];
          return newStatus;
        });
      }, 5000);
    }
  };

  // 개별 이미지 삭제 (개선됨)
  const handleRemoveImage = (imageIndex: number) => {
    console.log('🗑️ 이미지 삭제 요청 - imageIndex:', imageIndex);
    
    // 지정된 imageIndex를 가진 파일을 제거
    const newImages = images.filter(img => (img as any).__imageIndex !== imageIndex);
    
    // 해당 인덱스의 에러 상태도 함께 제거
    setUploadErrors(prev => {
      const newErrors = { ...prev };
      delete newErrors[imageIndex];
      return newErrors;
    });
    
    // 생성 상태도 함께 제거
    setGenerationStatus(prev => {
      const newStatus = { ...prev };
      delete newStatus[imageIndex];
      return newStatus;
    });
    
    console.log('✅ 이미지 삭제 완료 - imageIndex:', imageIndex);
    console.log('📊 남은 이미지:', newImages.map(img => `${img.name}(index:${(img as any).__imageIndex})`));
    
    onChange(newImages, imageUploadMode);
  };

  // 개별 이미지 다운로드
  const handleDownloadImage = async (imageIndex: number, image: File) => {
    try {
      // 생성된 이미지인지 확인 (filename으로 판단)
      if (image.name.startsWith('generated_')) {
        // 백엔드 다운로드 API를 통해 다운로드
        const link = document.createElement('a');
        link.href = `/download-image/${image.name}`;
        link.download = `reels_image_${imageIndex + 1}.png`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      } else {
        // 업로드된 파일은 직접 다운로드
        const url = URL.createObjectURL(image);
        const link = document.createElement('a');
        link.href = url;
        link.download = `reels_image_${imageIndex + 1}_${image.name}`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
      }
      console.log('💾 이미지 다운로드 완료 - imageIndex:', imageIndex, 'fileName:', image.name);
    } catch (error) {
      console.error('이미지 다운로드 오류:', error);
    }
  };

  // 개별 드래그앤드롭 컴포넌트
  const IndividualDropZone: React.FC<{
    imageIndex: number;
    pair: TextImagePair & { imageIndex: number };
  }> = ({ imageIndex, pair }) => {
    const onDrop = useCallback((acceptedFiles: File[]) => {
      handleIndividualImageUpload(imageIndex, acceptedFiles);
    }, [imageIndex]);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
      onDrop,
      accept: {
        'image/*': ['.jpeg', '.jpg', '.png', '.gif', '.webp', '.bmp'],
        'video/*': ['.mp4', '.mov', '.avi', '.webm']
      },
      maxFiles: 1,
      multiple: false
    });

    const isGenerating = generationStatus[imageIndex] === 'generating';
    const generationError = generationStatus[imageIndex] === 'error';
    const generationSuccess = generationStatus[imageIndex] === 'success';
    const uploadError = uploadErrors[imageIndex];

    return (
      <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        <CardContent sx={{ flex: 1 }}>
          {/* 텍스트 표시 */}
          <Typography variant="h6" gutterBottom sx={{ 
            fontSize: '0.9rem',
            fontWeight: 600,
            color: 'primary.main',
            mb: 2
          }}>
            {pair.textKey.replace('body', '대사 ').replace('+body', ' + 대사 ')}
          </Typography>
          
          <Typography variant="body2" sx={{ 
            mb: 2,
            p: 1.5,
            bgcolor: 'grey.50',
            borderRadius: 1,
            border: '1px solid',
            borderColor: 'grey.200',
            fontSize: '0.8rem',
            lineHeight: 1.4
          }}>
            {pair.textContent}
          </Typography>

          {/* 이미지/비디오 표시 또는 드래그앤드롭 영역 */}
          {pair.image ? (
            <Box sx={{ position: 'relative', mb: 2 }}>
              {pair.image.type.startsWith('video/') ? (
                <video
                  src={URL.createObjectURL(pair.image)}
                  style={{
                    width: '100%',
                    aspectRatio: '1/1',
                    objectFit: 'cover',
                    borderRadius: 8
                  }}
                  muted
                  loop
                  autoPlay
                />
              ) : (
                <Box
                  sx={{
                    width: '100%',
                    aspectRatio: '1/1',
                    backgroundImage: `url(${URL.createObjectURL(pair.image)})`,
                    backgroundSize: 'cover',
                    backgroundPosition: 'center',
                    borderRadius: 1
                  }}
                />
              )}
              
              {/* 이미지 컨트롤 버튼들 */}
              <Box sx={{ 
                position: 'absolute', 
                top: 8, 
                right: 8,
                display: 'flex',
                gap: 0.5
              }}>
                <IconButton
                  size="small"
                  onClick={() => handleDownloadImage(imageIndex, pair.image!)}
                  sx={{
                    bgcolor: 'rgba(255,255,255,0.9)',
                    '&:hover': { bgcolor: 'rgba(255,255,255,1)' }
                  }}
                  title="이미지 다운로드"
                >
                  <Download color="success" fontSize="small" />
                </IconButton>
                <IconButton
                  size="small"
                  onClick={() => handleRemoveImage(imageIndex)}
                  sx={{
                    bgcolor: 'rgba(255,255,255,0.9)',
                    '&:hover': { bgcolor: 'rgba(255,255,255,1)' }
                  }}
                  title="이미지 삭제"
                >
                  <Delete color="error" fontSize="small" />
                </IconButton>
                <IconButton
                  size="small"
                  onClick={() => {
                    console.log('🔄 새로고침 버튼 클릭됨 - imageIndex:', imageIndex, 'textContent:', pair.textContent);
                    handleIndividualGenerate(imageIndex, pair.textContent);
                  }}
                  disabled={isGenerating}
                  sx={{
                    bgcolor: 'rgba(255,255,255,0.9)',
                    '&:hover': { bgcolor: 'rgba(255,255,255,1)' }
                  }}
                  title="이미지 재생성"
                >
                  {isGenerating ? (
                    <CircularProgress size={16} />
                  ) : (
                    <Refresh color="primary" fontSize="small" />
                  )}
                </IconButton>
              </Box>

              <Typography variant="caption" sx={{ 
                position: 'absolute',
                bottom: 4,
                left: 8,
                bgcolor: 'rgba(0,0,0,0.7)',
                color: 'white',
                px: 1,
                py: 0.5,
                borderRadius: 1
              }}>
                {pair.image.name}
              </Typography>
            </Box>
          ) : (
            <Box
              {...getRootProps()}
              sx={{
                border: 2,
                borderColor: isDragActive ? 'primary.main' : 'grey.300',
                borderStyle: 'dashed',
                borderRadius: 1,
                p: 2,
                textAlign: 'center',
                cursor: 'pointer',
                bgcolor: isDragActive ? 'action.hover' : 'background.paper',
                mb: 2,
                aspectRatio: '1/1',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                '&:hover': {
                  borderColor: 'primary.main',
                  bgcolor: 'action.hover'
                }
              }}
            >
              <input {...getInputProps()} />
              <CloudUpload sx={{ fontSize: 32, color: 'grey.400', mb: 1 }} />
              <Typography variant="caption" color="text.secondary">
                {isDragActive ? '파일을 놓으세요' : '미디어 드래그 또는 클릭'}
              </Typography>
            </Box>
          )}

          {/* 상태 메시지 */}
          {isGenerating && (
            <Alert severity="info" sx={{ mt: 1 }}>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <CircularProgress size={16} sx={{ mr: 1 }} />
                이미지 생성 중...
              </Box>
            </Alert>
          )}
          
          {generationSuccess && (
            <Alert severity="success" sx={{ mt: 1 }}>
              이미지 생성 완료!
            </Alert>
          )}
          
          {generationError && (
            <Alert severity="error" sx={{ mt: 1 }}>
              이미지 생성 실패. 다시 시도해주세요.
            </Alert>
          )}
          
          {uploadError && (
            <Alert severity="error" sx={{ mt: 1 }}>
              {uploadError}
            </Alert>
          )}
        </CardContent>

        {/* 하단 액션 버튼 */}
        <Box sx={{ p: 1.5, pt: 0 }}>
          <Button
            fullWidth
            variant="outlined"
            size="small"
            startIcon={<AutoFixHigh />}
            onClick={() => {
              console.log('🖱️ 자동생성 버튼 클릭됨 - imageIndex:', imageIndex, 'textContent:', pair.textContent);
              handleIndividualGenerate(imageIndex, pair.textContent);
            }}
            disabled={isGenerating}
          >
            {isGenerating ? '생성중...' : 'AI 자동생성'}
          </Button>
        </Box>
      </Card>
    );
  };

  return (
    <Box>
      <Typography variant="h6" gutterBottom sx={{ mb: 3 }}>
        텍스트-이미지 매칭 관리
      </Typography>
      
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        각 텍스트에 대응되는 이미지를 개별적으로 관리할 수 있습니다. 
        드래그앤드롭으로 이미지를 업로드하거나 AI로 자동 생성하세요.
      </Typography>

      <Grid container spacing={2}>
        {textImagePairs.map((pair, index) => (
          <Grid item xs={12} sm={6} md={4} key={pair.textKey}>
            <IndividualDropZone imageIndex={pair.imageIndex} pair={pair} />
          </Grid>
        ))}
      </Grid>

      {textImagePairs.length === 0 && (
        <Alert severity="info" sx={{ mt: 2 }}>
          대본을 먼저 작성해주세요.
        </Alert>
      )}
    </Box>
  );
};

export default TextImagePairManager;