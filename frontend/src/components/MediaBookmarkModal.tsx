import React, { useState, useEffect, useCallback, memo } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Grid,
  Card,
  CardMedia,
  CardContent,
  Typography,
  Box,
  CircularProgress,
  Alert,
  IconButton,
  Chip,
  Tabs,
  Tab,
} from '@mui/material';
import {
  Close,
  VideoLibrary,
  Image as ImageIcon,
  CheckCircle,
  PermMedia,
} from '@mui/icons-material';
import { BookmarkVideo, BookmarkImage } from '../types';
import apiService from '../services/api';

interface MediaBookmarkModalProps {
  open: boolean;
  onClose: () => void;
  onSelect: (media: BookmarkVideo | BookmarkImage, mediaType: 'video' | 'image') => void;
}

const MediaBookmarkModal: React.FC<MediaBookmarkModalProps> = ({
  open,
  onClose,
  onSelect,
}) => {
  const [currentTab, setCurrentTab] = useState<'video' | 'image'>('video');
  const [videos, setVideos] = useState<BookmarkVideo[]>([]);
  const [images, setImages] = useState<BookmarkImage[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  const [selectedMedia, setSelectedMedia] = useState<(BookmarkVideo | BookmarkImage) | null>(null);
  const [hoveredFilename, setHoveredFilename] = useState<string | null>(null);

  // 북마크 비디오 목록 로드
  const loadBookmarkVideos = useCallback(async () => {
    setLoading(true);
    setError('');

    try {
      const response = await apiService.getBookmarkVideos();

      if (response.status === 'success') {
        setVideos(response.data);
        console.log(`✅ 북마크 비디오 ${response.data.length}개 로드 완료`);
      } else {
        throw new Error(response.message || '비디오 목록을 불러올 수 없습니다');
      }
    } catch (err: any) {
      console.error('북마크 비디오 로드 실패:', err);
      setError(err.message || '비디오 목록을 불러오는 중 오류가 발생했습니다');
    } finally {
      setLoading(false);
    }
  }, []);

  // 북마크 이미지 목록 로드
  const loadBookmarkImages = useCallback(async () => {
    setLoading(true);
    setError('');

    try {
      const response = await apiService.getBookmarkImages();

      if (response.status === 'success') {
        setImages(response.data);
        console.log(`✅ 북마크 이미지 ${response.data.length}개 로드 완료`);
      } else {
        throw new Error(response.message || '이미지 목록을 불러올 수 없습니다');
      }
    } catch (err: any) {
      console.error('북마크 이미지 로드 실패:', err);
      setError(err.message || '이미지 목록을 불러오는 중 오류가 발생했습니다');
    } finally {
      setLoading(false);
    }
  }, []);

  // 모달이 열릴 때마다 현재 탭의 미디어 목록 로드
  useEffect(() => {
    if (open) {
      if (currentTab === 'video') {
        loadBookmarkVideos();
      } else {
        loadBookmarkImages();
      }
      setSelectedMedia(null);
    }
  }, [open, currentTab, loadBookmarkVideos, loadBookmarkImages]);

  // 탭 변경 핸들러
  const handleTabChange = (event: React.SyntheticEvent, newValue: 'video' | 'image') => {
    setCurrentTab(newValue);
    setSelectedMedia(null);
  };

  // 미디어 선택 핸들러
  const handleMediaClick = (media: BookmarkVideo | BookmarkImage) => {
    setSelectedMedia(media);
  };

  // 선택 확인 핸들러
  const handleConfirmSelection = () => {
    if (selectedMedia) {
      onSelect(selectedMedia, currentTab);
      onClose();
    }
  };

  // 비디오 카드 컴포넌트 (memo로 최적화)
  const VideoCard = memo<{ video: BookmarkVideo; isSelected: boolean }>(({ video, isSelected }) => {
    const [videoError, setVideoError] = useState(false);

    return (
      <Card
        sx={{
          cursor: 'pointer',
          transition: 'all 0.2s ease',
          border: isSelected ? 3 : 1,
          borderColor: isSelected ? 'primary.main' : 'grey.300',
          boxShadow: isSelected ? 4 : 1,
          '&:hover': {
            boxShadow: 4,
            transform: 'translateY(-4px)',
          },
          position: 'relative',
        }}
        onClick={() => handleMediaClick(video)}
        onMouseEnter={() => setHoveredFilename(video.filename)}
        onMouseLeave={() => setHoveredFilename(null)}
      >
        {/* 선택 표시 */}
        {isSelected && (
          <Box
            sx={{
              position: 'absolute',
              top: 8,
              right: 8,
              zIndex: 10,
              bgcolor: 'primary.main',
              borderRadius: '50%',
              p: 0.5,
            }}
          >
            <CheckCircle sx={{ color: 'white', fontSize: 24 }} />
          </Box>
        )}

        {/* 썸네일 또는 비디오 미리보기 */}
        <Box sx={{ position: 'relative', paddingTop: '100%', overflow: 'hidden' }}>
          {video.has_thumbnail && !videoError ? (
            <CardMedia
              component="img"
              image={video.thumbnail_url!}
              alt={video.display_name}
              loading="lazy"
              sx={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: '100%',
                objectFit: 'cover',
              }}
              onError={() => setVideoError(true)}
            />
          ) : (
            <Box
              sx={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                bgcolor: 'grey.200',
              }}
            >
              <VideoLibrary sx={{ fontSize: 48, color: 'grey.500' }} />
            </Box>
          )}

          {/* 호버 시 비디오 재생 */}
          {hoveredFilename === video.filename && (
            <Box
              sx={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: '100%',
                bgcolor: 'rgba(0,0,0,0.8)',
              }}
            >
              <video
                src={video.video_url}
                style={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'cover',
                }}
                autoPlay
                muted
                loop
                playsInline
              />
            </Box>
          )}
        </Box>

        {/* 비디오 정보 */}
        <CardContent sx={{ p: 1.5 }}>
          <Typography
            variant="body2"
            sx={{
              fontWeight: 600,
              mb: 0.5,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {video.display_name}
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Chip
                label={`${video.size_mb} MB`}
                size="small"
                sx={{ fontSize: '0.7rem', height: 20 }}
              />
              <Chip
                label={`${video.duration}초`}
                size="small"
                color="primary"
                sx={{ fontSize: '0.7rem', height: 20 }}
              />
            </Box>
            <Typography variant="caption" color="text.secondary" sx={{ textAlign: 'center' }}>
              {new Date(video.modified_time * 1000).toLocaleDateString('ko-KR', {
                month: 'short',
                day: 'numeric',
              })}
            </Typography>
          </Box>
        </CardContent>
      </Card>
    );
  });

  // 이미지 카드 컴포넌트 (memo로 최적화)
  const ImageCard = memo<{ image: BookmarkImage; isSelected: boolean }>(({ image, isSelected }) => {
    return (
      <Card
        sx={{
          cursor: 'pointer',
          transition: 'all 0.2s ease',
          border: isSelected ? 3 : 1,
          borderColor: isSelected ? 'primary.main' : 'grey.300',
          boxShadow: isSelected ? 4 : 1,
          '&:hover': {
            boxShadow: 4,
            transform: 'translateY(-4px)',
          },
          position: 'relative',
        }}
        onClick={() => handleMediaClick(image)}
      >
        {/* 선택 표시 */}
        {isSelected && (
          <Box
            sx={{
              position: 'absolute',
              top: 8,
              right: 8,
              zIndex: 10,
              bgcolor: 'primary.main',
              borderRadius: '50%',
              p: 0.5,
            }}
          >
            <CheckCircle sx={{ color: 'white', fontSize: 24 }} />
          </Box>
        )}

        {/* 이미지 썸네일 */}
        <Box sx={{ position: 'relative', paddingTop: '100%', overflow: 'hidden' }}>
          <CardMedia
            component="img"
            image={image.thumbnail_url}
            alt={image.display_name}
            loading="lazy"
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              objectFit: 'cover',
            }}
          />
        </Box>

        {/* 이미지 정보 */}
        <CardContent sx={{ p: 1.5 }}>
          <Typography
            variant="body2"
            sx={{
              fontWeight: 600,
              mb: 0.5,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {image.display_name}
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Chip
                label={`${image.size_mb} MB`}
                size="small"
                sx={{ fontSize: '0.7rem', height: 20 }}
              />
              <Chip
                label={image.extension.toUpperCase()}
                size="small"
                color="secondary"
                sx={{ fontSize: '0.7rem', height: 20 }}
              />
            </Box>
            <Typography variant="caption" color="text.secondary" sx={{ textAlign: 'center' }}>
              {new Date(image.modified_time * 1000).toLocaleDateString('ko-KR', {
                month: 'short',
                day: 'numeric',
              })}
            </Typography>
          </Box>
        </CardContent>
      </Card>
    );
  });

  const currentData = currentTab === 'video' ? videos : images;

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: {
          minHeight: '70vh',
          maxHeight: '85vh',
        },
      }}
    >
      <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <PermMedia color="primary" />
          <Typography variant="h6">미디어 불러오기</Typography>
        </Box>
        <IconButton onClick={onClose} size="small">
          <Close />
        </IconButton>
      </DialogTitle>

      {/* 탭 영역 */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', px: 3 }}>
        <Tabs value={currentTab} onChange={handleTabChange}>
          <Tab
            label="비디오"
            value="video"
            icon={<VideoLibrary />}
            iconPosition="start"
          />
          <Tab
            label="이미지"
            value="image"
            icon={<ImageIcon />}
            iconPosition="start"
          />
        </Tabs>
      </Box>

      <DialogContent dividers>
        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 300 }}>
            <CircularProgress />
          </Box>
        )}

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {!loading && !error && currentData.length === 0 && (
          <Alert severity="info">
            저장된 북마크 {currentTab === 'video' ? '동영상' : '이미지'}이 없습니다.
          </Alert>
        )}

        {!loading && !error && currentData.length > 0 && (
          <Box>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              {currentTab === 'video'
                ? '동영상을 선택하면 미리보기를 볼 수 있습니다. 호버하면 동영상이 재생됩니다.'
                : '이미지를 선택하세요.'}
            </Typography>

            <Grid container spacing={2}>
              {currentTab === 'video'
                ? videos.map((video) => (
                    <Grid item xs={12} sm={6} md={4} key={video.filename}>
                      <VideoCard
                        video={video}
                        isSelected={selectedMedia?.filename === video.filename}
                      />
                    </Grid>
                  ))
                : images.map((image) => (
                    <Grid item xs={12} sm={6} md={4} key={image.filename}>
                      <ImageCard
                        image={image}
                        isSelected={selectedMedia?.filename === image.filename}
                      />
                    </Grid>
                  ))
              }
            </Grid>
          </Box>
        )}
      </DialogContent>

      <DialogActions sx={{ px: 3, py: 2 }}>
        <Button onClick={onClose} variant="outlined">
          취소
        </Button>
        <Button
          onClick={handleConfirmSelection}
          variant="contained"
          disabled={!selectedMedia}
          startIcon={<CheckCircle />}
        >
          선택 완료
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default MediaBookmarkModal;
