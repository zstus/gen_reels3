import React, { useState, useCallback, useMemo, memo, useEffect, useRef, useImperativeHandle, forwardRef } from 'react';
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
  Warning,
  VideoLibrary
} from '@mui/icons-material';
import { useDropzone } from 'react-dropzone';
import { ReelsContent, ImageUploadMode, TextImagePair, CustomPrompt, BookmarkVideo, BookmarkImage } from '../types';
import MediaBookmarkModal from './MediaBookmarkModal';
import apiService from '../services/api';

interface TextImagePairManagerProps {
  content: ReelsContent;
  imageUploadMode: ImageUploadMode;
  images: File[];
  jobId: string;
  imagePanningOptions: { [key: number]: boolean }; // 🎨 패닝 옵션 props 추가
  onChange: (images: File[], mode: ImageUploadMode) => void;
  onPanningOptionsChange: (options: { [key: number]: boolean }) => void; // 🎨 패닝 옵션 변경 핸들러
}

// ✅ ref를 통해 외부에서 접근 가능한 메서드 타입 정의
export interface TextImagePairManagerRef {
  getEditedData: () => {
    editedTexts: { [key: number]: string[] };
    customPrompts: { [key: number]: CustomPrompt };
    imagePanningOptions: { [key: number]: boolean };
  };
}

const TextImagePairManager = forwardRef<TextImagePairManagerRef, TextImagePairManagerProps>(({
  content,
  imageUploadMode,
  images,
  jobId,
  imagePanningOptions, // 🎨 props에서 받기
  onChange,
  onPanningOptionsChange, // 🎨 props에서 받기
}, ref) => {
  const [generationStatus, setGenerationStatus] = useState<{ [key: string]: string }>({});
  const [generationType, setGenerationType] = useState<{ [key: number]: 'ai' | 'bookmark' }>({});
  const [uploadErrors, setUploadErrors] = useState<{ [key: number]: string }>({});
  const [customPrompts, setCustomPrompts] = useState<{ [key: number]: CustomPrompt }>({});
  const [promptsExpanded, setPromptsExpanded] = useState<{ [key: number]: boolean }>({});
  const [bookmarkModalOpen, setBookmarkModalOpen] = useState<boolean>(false);
  const [currentBookmarkIndex, setCurrentBookmarkIndex] = useState<number | null>(null);

  // 🎨 이미지 개수가 변경될 때마다 패닝 옵션 초기화 (기본값: true)
  useEffect(() => {
    const imageCount = images.length;
    if (imageCount === 0) return; // 이미지가 없으면 초기화 안 함

    const newOptions: { [key: number]: boolean } = {};
    let hasChanges = false;

    for (let i = 0; i < imageCount; i++) {
      // 기존 값이 있으면 유지, 없으면 true로 초기화
      if (imagePanningOptions[i] !== undefined) {
        newOptions[i] = imagePanningOptions[i];
      } else {
        newOptions[i] = true; // 기본값: 패닝 활성화
        hasChanges = true;
      }
    }

    // 변경사항이 있을 때만 업데이트
    if (hasChanges) {
      console.log(`🎨 패닝 옵션 초기화: ${imageCount}개 이미지에 대해 기본값 설정`, newOptions);
      onPanningOptionsChange(newOptions);
    }
  }, [images.length, images]);

  // ✅ Uncontrolled TextField를 위한 ref 저장소
  const textFieldRefs = useRef<{ [key: string]: HTMLInputElement }>({});
  const customPromptRefs = useRef<{ [key: number]: HTMLInputElement }>({});

  // ✅ TextField의 현재 값 캐시 (재렌더링 시 값 복원용)
  const textFieldValuesCache = useRef<{ [key: string]: string }>({});
  const customPromptValuesCache = useRef<{ [key: number]: string }>({});

  // 최신 images 상태를 추적하기 위한 ref
  const imagesRef = useRef<File[]>(images);

  // images prop이 변경될 때마다 ref 업데이트
  useEffect(() => {
    imagesRef.current = images;
  }, [images]);

  // ✅ ref를 통해 외부에서 데이터를 가져갈 수 있도록 메서드 제공
  useImperativeHandle(ref, () => ({
    getEditedData: () => {
      // ✅ TextField ref에서 현재 값 읽기
      const editedTexts: { [key: number]: string[] } = {};

      Object.keys(textFieldRefs.current).forEach(key => {
        // ✅ imageIndex-textIdx 형태만 처리 (예: "0-0", "1-1")
        // stableRefKey 형태(예: "body1-0")는 건너뜀
        const parts = key.split('-');
        if (parts.length !== 2) return; // body1+body2 같은 경우 건너뜀

        const imageIndex = parseInt(parts[0]);
        const textIdx = parseInt(parts[1]);

        // 숫자로 파싱 가능한 경우만 처리
        if (isNaN(imageIndex) || isNaN(textIdx)) return;

        const value = textFieldRefs.current[key]?.value || '';

        if (!editedTexts[imageIndex]) {
          editedTexts[imageIndex] = [];
        }
        editedTexts[imageIndex][textIdx] = value;
      });

      // ✅ customPrompt ref에서 현재 값 읽기
      const customPromptsData: { [key: number]: CustomPrompt } = {};

      Object.keys(customPromptRefs.current).forEach(indexStr => {
        const imageIndex = parseInt(indexStr);
        const promptValue = customPromptRefs.current[imageIndex]?.value || '';
        const enabled = customPrompts[imageIndex]?.enabled || false;

        if (promptValue || enabled) {
          customPromptsData[imageIndex] = {
            imageIndex,
            prompt: promptValue,
            enabled
          };
        }
      });

      return {
        editedTexts,
        customPrompts: customPromptsData,
        imagePanningOptions: imagePanningOptions
      };
    }
  }), [customPrompts, imagePanningOptions]); // customPrompts와 imagePanningOptions 의존

  // ✅ 커스텀 프롬프트 토글 (enabled 상태만 관리)
  const toggleCustomPrompt = (imageIndex: number, enabled: boolean) => {
    setCustomPrompts(prev => ({
      ...prev,
      [imageIndex]: {
        imageIndex,
        prompt: prev[imageIndex]?.prompt || '',
        enabled
      }
    }));
  };

  const togglePromptExpanded = (imageIndex: number) => {
    setPromptsExpanded(prev => ({
      ...prev,
      [imageIndex]: !prev[imageIndex]
    }));
  };

  // 🎨 패닝 옵션 토글 함수
  const togglePanningOption = (imageIndex: number, enabled: boolean) => {
    const newOptions = {
      ...imagePanningOptions,
      [imageIndex]: enabled
    };
    console.log(`🎨 패닝 옵션 변경 - imageIndex: ${imageIndex}, enabled: ${enabled}`);
    console.log(`🎨 전체 패닝 옵션 상태:`, newOptions);
    onPanningOptionsChange(newOptions); // 🎨 props 핸들러 호출
  };

  // 텍스트-이미지 쌍 데이터 생성 (useMemo로 최적화)
  // ✅ editedTexts 의존성 제거 - TextField 입력 시 재계산 방지
  const textImagePairs = useMemo((): (TextImagePair & { imageIndex: number })[] => {
    const bodyTexts = Object.entries(content)
      .filter(([key, value]) => key.startsWith('body') && value?.trim())
      .map(([key, value]) => {
        // body 번호를 key에서 추출 (예: "body1" -> 0, "body10" -> 9)
        const bodyNumber = parseInt(key.replace('body', '')) - 1; // 0-based index
        return { key, value: value.trim(), index: bodyNumber };
      });

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

        // 원본 텍스트 배열 (per-script는 1개)
        const originalTexts = [value];

        console.log(`📋 per-script: textIndex=${index}, imageIndex=${index}, foundImage=${foundImage?.name || 'null'}`);
        pairs.push({
          textIndex: index,
          textKey: key,
          textContent: value,
          image: foundImage || null,
          imageIndex: index,
          isGenerating: false,
          customPrompt: customPrompt?.prompt || '',
          useCustomPrompt: customPrompt?.enabled || false,
          originalTexts: originalTexts,
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

          // 원본 텍스트 배열
          const originalTexts = [text1.value, text2?.value].filter(Boolean) as string[];

          console.log(`📋 per-two-scripts: textIndex=${i}, imageIndex=${imageIndex}, foundImage=${foundImage?.name || 'null'}`);
          pairs.push({
            textIndex: i,
            textKey: `${text1.key}${text2 ? `+${text2.key}` : ''}`,
            textContent: `${text1.value}${text2 ? ` / ${text2.value}` : ''}`,
            image: foundImage || null,
            imageIndex: imageIndex,
            isGenerating: false,
            customPrompt: customPrompt?.prompt || '',
            useCustomPrompt: customPrompt?.enabled || false,
            originalTexts: originalTexts,
          });
        }
      }
    } else if (imageUploadMode === 'single-for-all') {
      // 모든 텍스트에 이미지 1개
      const allTexts = bodyTexts.map(({ key, value }) => key.replace('body', '대사')).join(' + ');
      const allContent = bodyTexts.map(({ value }) => value).join(' / ');
      const foundImage = imageMap.get(0);
      const customPrompt = customPrompts[0];

      // 원본 텍스트 배열 (모든 대사)
      const originalTexts = bodyTexts.map(({ value }) => value);

      console.log(`📋 single-for-all: 모든 대사, imageIndex=0, foundImage=${foundImage?.name || 'null'}`);
      pairs.push({
        textIndex: 0,
        textKey: allTexts,
        textContent: allContent,
        image: foundImage || null,
        imageIndex: 0,
        isGenerating: false,
        customPrompt: customPrompt?.prompt || '',
        useCustomPrompt: customPrompt?.enabled || false,
        originalTexts: originalTexts,
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
    const maxSize = imageUploadMode === 'single-for-all' ? 80 * 1024 * 1024 : 40 * 1024 * 1024;
    const maxSizeText = imageUploadMode === 'single-for-all' ? '80MB' : '40MB';

    if (file.size > maxSize) {
      setUploadErrors(prev => ({ ...prev, [imageIndex]: `파일 크기가 ${maxSizeText}를 초과합니다` }));
      return;
    }

    // 파일 형식 검증 (MIME 타입 + 확장자)
    const fileName = file.name.toLowerCase();
    const isImageByType = file.type.startsWith('image/');
    const isVideoByType = file.type.startsWith('video/');

    // HEIC/HEIF는 브라우저에서 MIME 타입이 없을 수 있으므로 확장자로 검증
    const imageExtensions = ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.heic', '.heif'];
    const videoExtensions = ['.mp4', '.mov', '.avi', '.webm', '.mkv', '.gif'];

    const isImageByExt = imageExtensions.some(ext => fileName.endsWith(ext));
    const isVideoByExt = videoExtensions.some(ext => fileName.endsWith(ext));

    const isImage = isImageByType || isImageByExt;
    const isVideo = isVideoByType || isVideoByExt;

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
  const handleIndividualGenerate = async (imageIndex: number, pair: TextImagePair & { imageIndex: number }, customPrompt?: string, useCustomPrompt?: boolean) => {
    console.log('🤖 handleIndividualGenerate 시작 - imageIndex:', imageIndex, 'pair:', pair, 'customPrompt:', customPrompt, 'useCustomPrompt:', useCustomPrompt);
    setGenerationStatus(prev => ({ ...prev, [imageIndex]: 'generating' }));
    setGenerationType(prev => ({ ...prev, [imageIndex]: 'ai' }));

    try {
      // 요청 바디 구성
      let requestBody: any = {
        job_id: jobId  // Job ID 추가
      };

      // 🎯 우선순위 1: 커스텀 프롬프트
      if (useCustomPrompt && customPrompt?.trim()) {
        requestBody.custom_prompt = customPrompt.trim();
        console.log('📝 [우선순위 1] 커스텀 프롬프트 사용:', customPrompt.trim());
      }
      // 🎯 우선순위 2: 수정된 텍스트 (TextField ref에서 읽기)
      else {
        // ✅ TextField ref에서 현재 입력된 값 읽기
        const editedText0 = textFieldRefs.current[`${imageIndex}-0`]?.value || '';
        const editedText1 = textFieldRefs.current[`${imageIndex}-1`]?.value || '';

        // originalTexts 가져오기
        const originalTexts = pair.originalTexts || [];

        // 수정된 텍스트가 있는지 확인
        const hasEditedText0 = editedText0 && editedText0 !== originalTexts[0];
        const hasEditedText1 = editedText1 && editedText1 !== originalTexts[1];

        if (hasEditedText0 || hasEditedText1) {
          // 수정된 텍스트 사용
          requestBody.text = editedText0 || originalTexts[0];
          if (editedText1 || originalTexts[1]) {
            requestBody.additional_context = editedText1 || originalTexts[1];
          }
          console.log('📝 [우선순위 2] 수정된 텍스트 사용 (ref에서 읽음):', requestBody.text);
        } else {
          // 원본 텍스트 사용
          const texts = pair.textContent.split(' / ');
          requestBody.text = texts[0];
          if (texts.length > 1) {
            requestBody.additional_context = texts[1];
          }
          console.log('📝 [우선순위 3] 원본 텍스트 사용:', texts[0]);
        }
      }

      console.log('🚀 요청 바디 (Job ID 포함):', requestBody);

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

  // 북마크 모달 열기
  const handleOpenBookmarkModal = (imageIndex: number) => {
    console.log('🎬 북마크 모달 열기 - imageIndex:', imageIndex);
    setCurrentBookmarkIndex(imageIndex);
    setBookmarkModalOpen(true);
  };

  // 북마크 모달 닫기
  const handleCloseBookmarkModal = () => {
    setBookmarkModalOpen(false);
    setCurrentBookmarkIndex(null);
  };

  // 북마크 미디어(비디오/이미지) 선택 핸들러
  const handleSelectBookmarkMedia = async (media: BookmarkVideo | BookmarkImage, mediaType: 'video' | 'image') => {
    if (currentBookmarkIndex === null) return;

    console.log(`✅ 북마크 ${mediaType === 'video' ? '비디오' : '이미지'} 선택:`, media.filename, 'imageIndex:', currentBookmarkIndex);

    try {
      // 생성 상태 업데이트
      setGenerationStatus(prev => ({ ...prev, [currentBookmarkIndex]: 'generating' }));
      setGenerationType(prev => ({ ...prev, [currentBookmarkIndex]: 'bookmark' }));

      // 백엔드 API 호출: 북마크 미디어를 Job 폴더로 복사
      const response = mediaType === 'video'
        ? await apiService.copyBookmarkVideo(jobId, media.filename, currentBookmarkIndex)
        : await apiService.copyBookmarkImage(jobId, media.filename, currentBookmarkIndex);

      if (response.status === 'success') {
        // 복사된 파일을 File 객체로 변환하여 이미지 배열에 추가
        const fileUrl = response.data.file_url;
        const filename = response.data.filename;

        // 파일을 Fetch로 가져와서 File 객체 생성
        const fileResponse = await fetch(fileUrl);
        if (!fileResponse.ok) {
          throw new Error(`${mediaType === 'video' ? '비디오' : '이미지'} 파일 다운로드에 실패했습니다`);
        }

        const blob = await fileResponse.blob();

        // 파일 타입 결정
        const ext = filename.split('.').pop()?.toLowerCase();
        let mimeType = 'application/octet-stream';

        if (mediaType === 'video') {
          if (ext === 'mp4') mimeType = 'video/mp4';
          else if (ext === 'mov') mimeType = 'video/quicktime';
          else if (ext === 'avi') mimeType = 'video/x-msvideo';
          else if (ext === 'webm') mimeType = 'video/webm';
        } else {
          if (ext === 'jpg' || ext === 'jpeg') mimeType = 'image/jpeg';
          else if (ext === 'png') mimeType = 'image/png';
          else if (ext === 'webp') mimeType = 'image/webp';
          else if (ext === 'gif') mimeType = 'image/gif';
        }

        const file = new File([blob], filename, { type: mimeType });

        console.log(`📸 북마크 ${mediaType === 'video' ? '비디오' : '이미지'} 파일 생성 완료 - fileName:`, filename, 'imageIndex:', currentBookmarkIndex);

        // 이미지 배열 업데이트
        handleIndividualImageUpload(currentBookmarkIndex, [file]);

        setGenerationStatus(prev => ({ ...prev, [currentBookmarkIndex]: 'success' }));
        setTimeout(() => {
          setGenerationStatus(prev => {
            const newStatus = { ...prev };
            delete newStatus[currentBookmarkIndex];
            return newStatus;
          });
        }, 3000);

        console.log(`✅ 북마크 ${mediaType === 'video' ? '비디오' : '이미지'} 복사 및 업로드 완료`);
      }
    } catch (error: any) {
      console.error(`❌ 북마크 ${mediaType === 'video' ? '비디오' : '이미지'} 선택 오류:`, error);
      setGenerationStatus(prev => ({ ...prev, [currentBookmarkIndex]: 'error' }));
      setUploadErrors(prev => ({ ...prev, [currentBookmarkIndex]: error.message || `북마크 ${mediaType === 'video' ? '비디오' : '이미지'} 불러오기 실패` }));

      setTimeout(() => {
        setGenerationStatus(prev => {
          const newStatus = { ...prev };
          delete newStatus[currentBookmarkIndex];
          return newStatus;
        });
      }, 5000);
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
        'image/*': ['.jpeg', '.jpg', '.png', '.webp', '.bmp', '.heic', '.heif'],
        'video/*': ['.mp4', '.mov', '.avi', '.webm', '.mkv', '.gif']
      },
      maxFiles: 1,
      multiple: false
    });

    const isGenerating = generationStatus[imageIndex] === 'generating';
    const generationError = generationStatus[imageIndex] === 'error';
    const generationSuccess = generationStatus[imageIndex] === 'success';
    const currentGenerationType = generationType[imageIndex];
    const uploadError = uploadErrors[imageIndex];
    const isPromptExpanded = promptsExpanded[imageIndex] || false;
    const currentCustomPrompt = customPrompts[imageIndex];

    // 🎨 패닝 옵션 상태 (기본값: true)
    const currentPanningOption = imagePanningOptions[imageIndex] !== undefined
      ? imagePanningOptions[imageIndex]
      : true;

    // ✅ 심플한 커스텀 프롬프트 핸들러 (복잡한 로컬 상태/디바운스 제거)

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

          {/* 모든 모드: 개별 텍스트박스 */}
          {pair.originalTexts ? (
            <Box sx={{ mb: 2 }}>
              {pair.originalTexts.map((originalText, idx) => {
                // ✅ 안정적인 고유 키: textKey 사용 (imageIndex는 순서 변경 시 바뀜)
                const stableRefKey = `${pair.textKey}-${idx}`;
                const stableKey = `text-${pair.textKey}-${idx}`;

                // ✅ 캐시된 값이 있으면 사용, 없으면 원본 사용
                const initialValue = textFieldValuesCache.current[stableRefKey] || originalText;

                return (
                  <TextField
                    key={stableKey}
                    fullWidth
                    multiline
                    minRows={2}
                    maxRows={8}
                    defaultValue={initialValue}
                    inputRef={(el) => {
                      if (el) {
                        textFieldRefs.current[stableRefKey] = el;
                        // ✅ imageIndex 기반 ref도 유지 (AI 생성 시 사용)
                        textFieldRefs.current[`${imageIndex}-${idx}`] = el;
                      }
                    }}
                    onChange={(e) => {
                      // ✅ 값이 변경될 때마다 캐시에 저장
                      textFieldValuesCache.current[stableRefKey] = e.target.value;
                    }}
                    label={imageUploadMode === 'per-two-scripts' ? `대사 ${pair.textIndex + idx + 1}` :
                           imageUploadMode === 'per-script' ? `대사 ${pair.textIndex + 1}` :
                           `대사 ${idx + 1}`}
                    variant="outlined"
                    size="small"
                    sx={{ mb: 1 }}
                    helperText={idx === 0 ? "수정된 텍스트는 영상 생성 시 사용됩니다" : ""}
                  />
                );
              })}
            </Box>
          ) : (
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
          )}

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
                      onChange={(e) => {
                        toggleCustomPrompt(imageIndex, e.target.checked);
                      }}
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

                <TextField
                  key={`prompt-${imageIndex}`}
                  fullWidth
                  multiline
                  rows={2}
                  size="small"
                  placeholder="이미지 생성을 위한 커스텀 프롬프트를 입력하세요..."
                  defaultValue={customPromptValuesCache.current[imageIndex] || currentCustomPrompt?.prompt || ''}
                  inputRef={(el) => {
                    if (el) customPromptRefs.current[imageIndex] = el;
                  }}
                  onChange={(e) => {
                    // ✅ 값이 변경될 때마다 캐시에 저장
                    customPromptValuesCache.current[imageIndex] = e.target.value;
                  }}
                  variant="outlined"
                  sx={{
                    display: currentCustomPrompt?.enabled ? 'block' : 'none',
                    '& .MuiOutlinedInput-root': {
                      fontSize: '0.75rem',
                      bgcolor: 'white'
                    }
                  }}
                  helperText="실제 영상에서는 기존 대사가 사용되며, 이 프롬프트는 이미지 생성에만 사용됩니다."
                  autoComplete="off"
                  spellCheck="false"
                />

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
              {(() => {
                // 파일 타입 확인 (MIME 타입 + 확장자)
                const fileName = pair.image.name.toLowerCase();
                const videoExtensions = ['.mp4', '.mov', '.avi', '.webm', '.mkv'];
                const gifExtensions = ['.gif'];
                const isVideo = pair.image.type.startsWith('video/') || videoExtensions.some(ext => fileName.endsWith(ext));
                const isGif = pair.image.type === 'image/gif' || gifExtensions.some(ext => fileName.endsWith(ext));

                // HEIC 파일 확인
                const heicExtensions = ['.heic', '.heif'];
                const isHEIC = heicExtensions.some(ext => fileName.endsWith(ext));

                if (isGif) {
                  // GIF는 img 태그로 애니메이션 재생
                  return (
                    <Box sx={{ position: 'relative' }}>
                      <img
                        src={URL.createObjectURL(pair.image)}
                        alt="GIF preview"
                        style={{
                          width: '100%',
                          aspectRatio: '1/1',
                          objectFit: 'cover',
                          borderRadius: '8px'
                        }}
                      />
                      {/* GIF 아이콘 오버레이 */}
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
                          GIF
                        </Typography>
                      </Box>
                    </Box>
                  );
                } else if (isVideo) {
                  return <VideoPreview file={pair.image} />;
                } else if (isHEIC) {
                  // HEIC 파일은 브라우저에서 미리보기 불가 → 파일명 표시
                  return (
                    <Box
                      sx={{
                        width: '100%',
                        aspectRatio: '1/1',
                        backgroundColor: '#f5f5f5',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexDirection: 'column',
                        borderRadius: 1,
                        border: '2px dashed #ccc'
                      }}
                    >
                      <Typography variant="h6" color="text.secondary">📷</Typography>
                      <Typography variant="caption" color="text.secondary" sx={{ mt: 1, px: 2, textAlign: 'center' }}>
                        {pair.image.name}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        (HEIC 파일 - 미리보기 불가)
                      </Typography>
                    </Box>
                  );
                } else {
                  // 일반 이미지
                  return (
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
                  );
                }
              })()}
              
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
                    // ✅ ref에서 현재 프롬프트 값 읽기
                    const currentPromptValue = customPromptRefs.current[imageIndex]?.value || '';
                    const isEnabled = currentCustomPrompt?.enabled || false;

                    console.log('🔄 새로고침 버튼 클릭됨 - imageIndex:', imageIndex, 'pair:', pair);
                    console.log('📝 커스텀 프롬프트 값 (ref에서 읽음):', currentPromptValue);

                    handleIndividualGenerate(
                      imageIndex,
                      pair,
                      currentPromptValue,
                      isEnabled
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

              {/* 🎨 패닝 옵션 섹션 (이미지가 있을 때만 표시, 비디오 제외) */}
              {!pair.image.type.startsWith('video/') && (
                <Box sx={{
                  mt: 2,
                  p: 1.5,
                  bgcolor: 'rgba(76, 175, 80, 0.04)',
                  borderRadius: 1,
                  border: '1px solid rgba(76, 175, 80, 0.2)'
                }}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={currentPanningOption}
                        onChange={(e) => togglePanningOption(imageIndex, e.target.checked)}
                        size="small"
                        color="success"
                      />
                    }
                    label={
                      <Box>
                        <Typography variant="caption" sx={{ fontWeight: 600, display: 'block' }}>
                          🎬 패닝 효과
                        </Typography>
                        <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                          {currentPanningOption
                            ? '이미지가 좌우/상하로 부드럽게 움직입니다'
                            : '이미지가 고정되어 움직이지 않습니다'}
                        </Typography>
                      </Box>
                    }
                    sx={{ ml: 0, width: '100%' }}
                  />
                </Box>
              )}
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
              <Box sx={{ display: 'flex', justifyContent: 'center', width: '100%' }}>
                <CloudUpload sx={{ fontSize: 32, color: 'grey.400', mb: 1 }} />
              </Box>
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
                {currentGenerationType === 'bookmark' ? '미디어 불러오는 중...' : '이미지 생성 중...'}
              </Box>
            </Alert>
          )}

          {generationSuccess && (
            <Alert severity="success" sx={{ mt: 1 }}>
              {currentGenerationType === 'bookmark' ? '미디어 불러오기 완료!' : '이미지 생성 완료!'}
            </Alert>
          )}

          {generationError && (
            <Alert severity="error" sx={{ mt: 1 }}>
              {currentGenerationType === 'bookmark' ? '미디어 불러오기 실패. 다시 시도해주세요.' : '이미지 생성 실패. 다시 시도해주세요.'}
            </Alert>
          )}
          
          {uploadError && (
            <Alert severity="error" sx={{ mt: 1 }}>
              {uploadError}
            </Alert>
          )}
        </CardContent>

        {/* 하단 액션 버튼 */}
        <Box sx={{ p: 1.5, pt: 0, display: 'flex', flexDirection: 'column', gap: 1 }}>
          <Button
            fullWidth
            variant="outlined"
            size="small"
            startIcon={<AutoFixHigh />}
            onClick={() => {
              // ✅ ref에서 현재 프롬프트 값 읽기
              const currentPromptValue = customPromptRefs.current[imageIndex]?.value || '';
              const isEnabled = currentCustomPrompt?.enabled || false;

              console.log('🖱️ 자동생성 버튼 클릭됨 - imageIndex:', imageIndex, 'pair:', pair);
              console.log('📝 커스텀 프롬프트 값 (ref에서 읽음):', currentPromptValue);
              console.log('✅ 커스텀 프롬프트 enabled:', isEnabled);

              handleIndividualGenerate(
                imageIndex,
                pair,
                currentPromptValue,
                isEnabled
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

          <Button
            fullWidth
            variant="outlined"
            size="small"
            startIcon={<VideoLibrary />}
            onClick={() => handleOpenBookmarkModal(imageIndex)}
            disabled={isGenerating}
            sx={{
              borderColor: 'secondary.main',
              color: 'secondary.main',
              '&:hover': {
                bgcolor: 'rgba(156, 39, 176, 0.08)',
                borderColor: 'secondary.main',
              }
            }}
          >
            미디어 불러오기
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

      {/* 북마크 미디어 선택 모달 */}
      <MediaBookmarkModal
        open={bookmarkModalOpen}
        onClose={handleCloseBookmarkModal}
        onSelect={handleSelectBookmarkMedia}
      />
    </Box>
  );
});

// Display name for debugging
TextImagePairManager.displayName = 'TextImagePairManager';

export default TextImagePairManager;