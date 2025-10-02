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
} from '@mui/material';
import {
  Close,
  VideoLibrary,
  CheckCircle,
} from '@mui/icons-material';
import { BookmarkVideo } from '../types';
import apiService from '../services/api';

interface VideoBookmarkModalProps {
  open: boolean;
  onClose: () => void;
  onSelect: (video: BookmarkVideo) => void;
}

const VideoBookmarkModal: React.FC<VideoBookmarkModalProps> = ({
  open,
  onClose,
  onSelect,
}) => {
  const [videos, setVideos] = useState<BookmarkVideo[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  const [selectedVideo, setSelectedVideo] = useState<BookmarkVideo | null>(null);
  const [hoveredVideo, setHoveredVideo] = useState<string | null>(null);

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

  // 모달이 열릴 때마다 비디오 목록 로드
  useEffect(() => {
    if (open) {
      loadBookmarkVideos();
      setSelectedVideo(null);
    }
  }, [open, loadBookmarkVideos]);

  // 비디오 선택 핸들러
  const handleVideoClick = (video: BookmarkVideo) => {
    setSelectedVideo(video);
  };

  // 선택 확인 핸들러
  const handleConfirmSelection = () => {
    if (selectedVideo) {
      onSelect(selectedVideo);
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
        onClick={() => handleVideoClick(video)}
        onMouseEnter={() => setHoveredVideo(video.filename)}
        onMouseLeave={() => setHoveredVideo(null)}
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
          {hoveredVideo === video.filename && (
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
          <VideoLibrary color="primary" />
          <Typography variant="h6">북마크 동영상 불러오기</Typography>
        </Box>
        <IconButton onClick={onClose} size="small">
          <Close />
        </IconButton>
      </DialogTitle>

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

        {!loading && !error && videos.length === 0 && (
          <Alert severity="info">
            저장된 북마크 동영상이 없습니다.
          </Alert>
        )}

        {!loading && !error && videos.length > 0 && (
          <Box>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              동영상을 선택하면 미리보기를 볼 수 있습니다. 호버하면 동영상이 재생됩니다.
            </Typography>

            <Grid container spacing={2}>
              {videos.map((video) => (
                <Grid item xs={12} sm={6} md={4} key={video.filename}>
                  <VideoCard
                    video={video}
                    isSelected={selectedVideo?.filename === video.filename}
                  />
                </Grid>
              ))}
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
          disabled={!selectedVideo}
          startIcon={<CheckCircle />}
        >
          선택 완료
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default VideoBookmarkModal;