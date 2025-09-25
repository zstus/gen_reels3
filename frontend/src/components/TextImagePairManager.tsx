import React, { useState, useCallback, useMemo, memo, useEffect, useRef } from 'react';
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
  TextField,
  FormControlLabel,
  Switch,
  Collapse,
} from '@mui/material';
import {
  CloudUpload,
  Delete,
  AutoFixHigh,
  Refresh,
  Image as ImageIcon,
  Download,
  Edit as EditIcon,
  ExpandMore,
  ExpandLess,
  Movie as MovieIcon,
  Warning
} from '@mui/icons-material';
import { useDropzone } from 'react-dropzone';
import { ReelsContent, ImageUploadMode, TextImagePair, CustomPrompt } from '../types';

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
  const [customPrompts, setCustomPrompts] = useState<{ [key: number]: CustomPrompt }>({});
  const [promptsExpanded, setPromptsExpanded] = useState<{ [key: number]: boolean }>({});

  // 최신 images 상태를 추적하기 위한 ref
  const imagesRef = useRef<File[]>(images);

  // images prop이 변경될 때마다 ref 업데이트
  useEffect(() => {
    imagesRef.current = images;
  }, [images]);

  // 커스텀 프롬프트 관리 함수들 (useCallback으로 최적화)
  const updateCustomPrompt = useCallback((imageIndex: number, prompt: string, enabled: boolean) => {
    setCustomPrompts(prev => {
      const currentPrompt = prev[imageIndex];
      // 값이 같으면 업데이트하지 않음 (불필요한 리렌더링 방지)
      if (currentPrompt &&
          currentPrompt.prompt === prompt &&
          currentPrompt.enabled === enabled) {
        return prev;
      }

      return {
        ...prev,
        [imageIndex]: {
          imageIndex,
          prompt,
          enabled
        }
      };
    });
  }, []);

  const togglePromptExpanded = useCallback((imageIndex: number) => {
    setPromptsExpanded(prev => ({
      ...prev,
      [imageIndex]: !prev[imageIndex]
    }));
  }, []);

  // 텍스트-이미지 쌍 데이터 생성 (useMemo로 최적화)
  const textImagePairs = useMemo((): (TextImagePair & { imageIndex: number })[] => {
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
        const customPrompt = customPrompts[index];
        console.log(`📋 per-script: textIndex=${index}, imageIndex=${index}, foundImage=${foundImage?.name || 'null'}`);
        pairs.push({
          textIndex: index,
          textKey: key,
          textContent: value,
          image: foundImage || null,
          imageIndex: index, // 실제 이미지 인덱스 저장
          isGenerating: false,
          customPrompt: customPrompt?.prompt || '',
          useCustomPrompt: customPrompt?.enabled || false,
        });
      });
    } else if (imageUploadMode === 'per-two-scripts') {
      // 텍스트 2개당 이미지 1개
      for (let i = 0; i < bodyTexts.length; i += 2) {
        const imageIndex = Math.floor(i / 2);
        const text1 = bodyTexts[i];
        const text2 = bodyTexts[i + 1];

        if (text1) {
          const foundImage = imageMap.get(imageIndex);
          const customPrompt = customPrompts[imageIndex];
          console.log(`📋 per-two-scripts: textIndex=${i}, imageIndex=${imageIndex}, foundImage=${foundImage?.name || 'null'}`);
          pairs.push({
            textIndex: i,
            textKey: `${text1.key}${text2 ? `+${text2.key}` : ''}`,
            textContent: `${text1.value}${text2 ? ` / ${text2.value}` : ''}`,
            image: foundImage || null,
            imageIndex: imageIndex, // 실제 이미지 인덱스 저장
            isGenerating: false,
            customPrompt: customPrompt?.prompt || '',
            useCustomPrompt: customPrompt?.enabled || false,
          });
        }
      }
    } else if (imageUploadMode === 'single-for-all') {
      // 모든 텍스트에 이미지 1개
      const allTexts = bodyTexts.map(({ key, value }) => key.replace('body', '대사')).join(' + ');
      const allContent = bodyTexts.map(({ value }) => value).join(' / ');
      const foundImage = imageMap.get(0); // 첫 번째 (그리고 유일한) 이미지
      const customPrompt = customPrompts[0];

      console.log(`📋 single-for-all: 모든 대사, imageIndex=0, foundImage=${foundImage?.name || 'null'}`);
      pairs.push({
        textIndex: 0,
        textKey: allTexts,
        textContent: allContent,
        image: foundImage || null,
        imageIndex: 0, // 항상 첫 번째 이미지 인덱스 사용
        isGenerating: false,
        customPrompt: customPrompt?.prompt || '',
        useCustomPrompt: customPrompt?.enabled || false,
      });
    }

    console.log('🎯 최종 pairs 개수:', pairs.length);
    return pairs;
  }, [content, images, imageUploadMode, customPrompts]);
  
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

    // 파일 유효성 검증 (모드에 따라 다른 제한)
    const maxSize = imageUploadMode === 'single-for-all' ? 40 * 1024 * 1024 : 10 * 1024 * 1024;
    const maxSizeText = imageUploadMode === 'single-for-all' ? '40MB' : '10MB';

    if (file.size > maxSize) {
      setUploadErrors(prev => ({ ...prev, [imageIndex]: `파일 크기가 ${maxSizeText}를 초과합니다` }));
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

    // 최신 images 상태를 가져와서 업데이트
    const currentImages = imagesRef.current;
    console.log('🔄 업데이트 전 currentImages (ref):', currentImages.map(img => `${img.name}(index:${(img as any).__imageIndex})`));

    // 현재 images에서 해당 imageIndex를 가진 파일 제거하고 새 파일 추가
    const newImages = currentImages.filter(img => (img as any).__imageIndex !== imageIndex);
    newImages.push(file);

    // imageIndex 순으로 정렬
    newImages.sort((a, b) => {
      const indexA = (a as any).__imageIndex ?? 0;
      const indexB = (b as any).__imageIndex ?? 0;
      return indexA - indexB;
    });

    console.log('📊 업데이트된 images 배열:', newImages.map(img => `${img.name}(index:${(img as any).__imageIndex})`));

    onChange(newImages, imageUploadMode);
  }, [imageUploadMode, onChange]); // images 의존성 제거

  // 개별 이미지 자동 생성
  const handleIndividualGenerate = async (imageIndex: number, textContent: string, customPrompt?: string, useCustomPrompt?: boolean) => {
    console.log('🤖 handleIndividualGenerate 시작 - imageIndex:', imageIndex, 'textContent:', textContent, 'customPrompt:', customPrompt, 'useCustomPrompt:', useCustomPrompt);
    setGenerationStatus(prev => ({ ...prev, [imageIndex]: 'generating' }));

    try {
      // 요청 바디 구성
      let requestBody: any = {};

      if (useCustomPrompt && customPrompt?.trim()) {
        // 커스텀 프롬프트 사용
        requestBody.custom_prompt = customPrompt.trim();
        console.log('📝 커스텀 프롬프트 사용:', customPrompt.trim());
      } else {
        // 기존 텍스트 사용
        const texts = textContent.split(' / ');
        requestBody.text = texts[0]; // 첫 번째 텍스트 사용
        if (texts.length > 1) {
          requestBody.additional_context = texts[1];
        }
        console.log('📝 기본 텍스트 사용:', texts[0]);
      }

      const response = await fetch('/generate-single-image', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
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

    // 최신 images 상태를 가져와서 삭제
    const currentImages = imagesRef.current;
    const newImages = currentImages.filter(img => (img as any).__imageIndex !== imageIndex);
    
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

  // 비디오 미리보기 컴포넌트 (브라우저 직접 재생)
  const VideoPreview: React.FC<{ file: File }> = memo(({ file }) => {
    const [videoUrl, setVideoUrl] = useState<string | null>(null);

    useEffect(() => {
      // 브라우저에서 직접 재생할 수 있도록 URL 생성
      const url = URL.createObjectURL(file);
      setVideoUrl(url);

      return () => {
        if (url) {
          URL.revokeObjectURL(url);
        }
      };
    }, [file]);

    return (
      <Box sx={{ position: 'relative' }}>
        {videoUrl && (
          <video
            src={videoUrl}
            style={{
              width: '100%',
              aspectRatio: '1/1',
              objectFit: 'cover',
              borderRadius: '8px'
            }}
            autoPlay
            muted
            loop
            playsInline
            controls={false}
            onError={(e) => {
              console.error('비디오 재생 오류:', e);
            }}
          />
        )}

        {/* 비디오 아이콘 오버레이 */}
        <Box
          sx={{
            position: 'absolute',
            top: 8,
            left: 8,
            bgcolor: 'rgba(0,0,0,0.7)',
            borderRadius: 1,
            p: 0.5,
            display: 'flex',
            alignItems: 'center'
          }}
        >
          <MovieIcon sx={{ fontSize: 16, color: 'white' }} />
          <Typography variant="caption" color="white" sx={{ ml: 0.5 }}>
            영상
          </Typography>
        </Box>
      </Box>
    );
  });

  // 개별 드래그앤드롭 컴포넌트 (React.memo로 최적화)
  const IndividualDropZone: React.FC<{
    imageIndex: number;
    pair: TextImagePair & { imageIndex: number };
  }> = memo(({ imageIndex, pair }) => {
    const onDrop = useCallback((acceptedFiles: File[]) => {
      handleIndividualImageUpload(imageIndex, acceptedFiles);
    }, [imageIndex]);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
      onDrop,
      accept: {
        'image/*': ['.jpeg', '.jpg', '.png', '.gif', '.webp', '.bmp'],
        'video/*': ['.mp4', '.mov', '.avi', '.webm', '.mkv']
      },
      maxFiles: 1,
      multiple: false
    });

    const isGenerating = generationStatus[imageIndex] === 'generating';
    const generationError = generationStatus[imageIndex] === 'error';
    const generationSuccess = generationStatus[imageIndex] === 'success';
    const uploadError = uploadErrors[imageIndex];
    const isPromptExpanded = promptsExpanded[imageIndex] || false;
    const currentCustomPrompt = customPrompts[imageIndex];

    // ref를 통한 포커스 유지
    const textFieldRef = useRef<HTMLInputElement>(null);

    // 로컬 상태로 입력값 관리 (포커스 유지를 위해)
    const [localPromptValue, setLocalPromptValue] = useState(currentCustomPrompt?.prompt || '');
    const [isInitialized, setIsInitialized] = useState(false);
    const [lastUpdateTime, setLastUpdateTime] = useState(0);

    // 초기화 시에만 외부 상태를 로컬 상태에 동기화
    useEffect(() => {
      if (!isInitialized) {
        setLocalPromptValue(currentCustomPrompt?.prompt || '');
        setIsInitialized(true);
      }
    }, [currentCustomPrompt?.prompt, isInitialized]);

    // 디바운스를 위한 useEffect - 외부 상태 업데이트 방지
    useEffect(() => {
      if (!localPromptValue.trim() && !currentCustomPrompt?.prompt) {
        return; // 빈 값인 경우 업데이트 하지 않음
      }

      const timeoutId = setTimeout(() => {
        const currentExternalValue = customPrompts[imageIndex]?.prompt || '';
        if (localPromptValue !== currentExternalValue) {
          // 클로저를 사용하여 함수 호출 시점의 값을 캡처
          const enabled = customPrompts[imageIndex]?.enabled || false;
          updateCustomPrompt(imageIndex, localPromptValue, enabled);
        }
      }, 1000); // 1초로 늘려서 더 안정적으로

      return () => clearTimeout(timeoutId);
    }, [localPromptValue, imageIndex]);

    // 커스텀 프롬프트 변경 핸들러 (로컬 상태만 업데이트)
    const handleCustomPromptChange = useCallback((prompt: string) => {
      setLocalPromptValue(prompt);
    }, []);

    // 커스텀 프롬프트 활성화/비활성화 핸들러
    const handleCustomPromptToggle = useCallback((enabled: boolean) => {
      updateCustomPrompt(imageIndex, localPromptValue, enabled);
    }, [imageIndex, localPromptValue, updateCustomPrompt]);

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

          {/* 커스텀 프롬프트 섹션 */}
          <Box sx={{ mb: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                AI 생성 옵션
              </Typography>
              <IconButton
                size="small"
                onClick={() => togglePromptExpanded(imageIndex)}
                sx={{ p: 0.5 }}
              >
                {isPromptExpanded ? <ExpandLess fontSize="small" /> : <ExpandMore fontSize="small" />}
              </IconButton>
            </Box>

            <Collapse in={isPromptExpanded}>
              <Box sx={{ bgcolor: 'rgba(25, 118, 210, 0.04)', p: 1.5, borderRadius: 1, border: '1px solid rgba(25, 118, 210, 0.12)' }}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={currentCustomPrompt?.enabled || false}
                      onChange={(e) => handleCustomPromptToggle(e.target.checked)}
                      size="small"
                    />
                  }
                  label={
                    <Typography variant="caption" sx={{ fontWeight: 500 }}>
                      커스텀 프롬프트 사용
                    </Typography>
                  }
                  sx={{ mb: 1, ml: 0 }}
                />

                {currentCustomPrompt?.enabled && (
                  <TextField
                    inputRef={textFieldRef}
                    key={`prompt-input-${imageIndex}-stable`}
                    fullWidth
                    multiline
                    rows={2}
                    size="small"
                    placeholder="이미지 생성을 위한 커스텀 프롬프트를 입력하세요..."
                    value={localPromptValue}
                    onChange={(e) => handleCustomPromptChange(e.target.value)}
                    variant="outlined"
                    sx={{
                      '& .MuiOutlinedInput-root': {
                        fontSize: '0.75rem',
                        bgcolor: 'white'
                      }
                    }}
                    helperText="실제 영상에서는 기존 대사가 사용되며, 이 프롬프트는 이미지 생성에만 사용됩니다."
                    autoComplete="off"
                    spellCheck="false"
                  />
                )}

                {!currentCustomPrompt?.enabled && (
                  <Typography variant="caption" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                    기본 모드: 위의 대사 내용을 기반으로 이미지를 생성합니다.
                  </Typography>
                )}
              </Box>
            </Collapse>
          </Box>

          {/* 이미지/비디오 표시 또는 드래그앤드롭 영역 */}
          {pair.image ? (
            <Box sx={{ position: 'relative', mb: 2 }}>
              {pair.image.type.startsWith('video/') ? (
                <VideoPreview file={pair.image} />
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
                    handleIndividualGenerate(
                      imageIndex,
                      pair.textContent,
                      currentCustomPrompt?.prompt,
                      currentCustomPrompt?.enabled
                    );
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
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5, fontSize: '0.7rem' }}>
                최대 {imageUploadMode === 'single-for-all' ? '40MB' : '10MB'}
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
              handleIndividualGenerate(
                imageIndex,
                pair.textContent,
                currentCustomPrompt?.prompt,
                currentCustomPrompt?.enabled
              );
            }}
            disabled={isGenerating}
            sx={{
              bgcolor: currentCustomPrompt?.enabled ? 'rgba(25, 118, 210, 0.08)' : 'transparent',
              borderColor: currentCustomPrompt?.enabled ? 'primary.main' : 'grey.300',
              color: currentCustomPrompt?.enabled ? 'primary.main' : 'text.primary',
              '&:hover': {
                bgcolor: currentCustomPrompt?.enabled ? 'rgba(25, 118, 210, 0.12)' : 'action.hover',
              }
            }}
          >
            {isGenerating ? '생성중...' : (currentCustomPrompt?.enabled ? '커스텀 프롬프트로 생성' : 'AI 자동생성')}
          </Button>
        </Box>
      </Card>
    );
  });

  return (
    <Box>
      <Typography variant="h6" gutterBottom sx={{ mb: 3 }}>
        텍스트-이미지 매칭 관리
      </Typography>
      
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        각 텍스트에 대응되는 이미지를 개별적으로 관리할 수 있습니다.
        드래그앤드롭으로 이미지를 업로드하거나 AI로 자동 생성하세요.
        <br />
        <Typography component="span" variant="caption" color="text.secondary">
          파일 크기 제한: {imageUploadMode === 'single-for-all' ? '최대 40MB' : '각 파일 최대 10MB'}
        </Typography>
      </Typography>

      <Grid container spacing={2}>
        {textImagePairs.map((pair, index) => (
          <Grid item xs={12} sm={6} md={4} key={`dropzone-${pair.imageIndex}-${pair.textKey}`}>
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