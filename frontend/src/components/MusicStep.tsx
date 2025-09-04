import React, { useState, useEffect, useRef } from 'react';
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
  Slider,
  Tabs,
  Tab,
} from '@mui/material';
import {
  PlayArrow,
  Pause,
  VolumeUp,
  MusicNote,
  CheckCircle,
  RadioButtonUnchecked,
} from '@mui/icons-material';
import { MusicFile, MusicMood, MusicFolder } from '../types';
import apiService from '../services/api';

interface MusicStepProps {
  selectedMusic: MusicFile | null;
  musicMood: MusicMood;
  onChange: (selectedMusic: MusicFile | null, musicMood: MusicMood) => void;
  onNext: () => void;
  onBack: () => void;
}

// 음악 성격별 한국어 명칭과 설명
const MOOD_CONFIG = {
  bright: { name: '밝은 음악', description: '활기차고 즐거운 분위기', color: '#ffeb3b' },
  calm: { name: '차분한 음악', description: '평온하고 릴랙스한 분위기', color: '#4caf50' },
  romantic: { name: '로맨틱한 음악', description: '감성적이고 따뜻한 분위기', color: '#e91e63' },
  sad: { name: '슬픈 음악', description: '감정적이고 애절한 분위기', color: '#9c27b0' },
  suspense: { name: '긴장감 있는 음악', description: '스릴 있고 극적인 분위기', color: '#f44336' },
};

const MusicStep: React.FC<MusicStepProps> = ({
  selectedMusic,
  musicMood,
  onChange,
  onNext,
  onBack,
}) => {
  const [musicFolders, setMusicFolders] = useState<{ [key in MusicMood]: MusicFile[] }>({
    bright: [],
    calm: [],
    romantic: [],
    sad: [],
    suspense: [],
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentlyPlaying, setCurrentlyPlaying] = useState<string | null>(null);
  const [volume, setVolume] = useState(0.5);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  // 컴포넌트 마운트시 BGM 목록 로드
  useEffect(() => {
    loadBgmFiles();
    return () => {
      stopAllMusic();
    };
  }, []);

  // BGM 파일 목록 로드
  const loadBgmFiles = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const bgmList = await apiService.getBgmList();
      const bgmData: { [key in MusicMood]: MusicFile[] } = {
        bright: [],
        calm: [],
        romantic: [],
        sad: [],
        suspense: [],
      };

      // BGM 목록을 성격별로 정리
      bgmList.forEach(folder => {
        bgmData[folder.mood] = folder.files;
      });

      setMusicFolders(bgmData);
    } catch (err: any) {
      setError(err.message || '음악 파일을 불러오는 중 오류가 발생했습니다');
      console.error('BGM 로드 실패:', err);
    } finally {
      setLoading(false);
    }
  };

  const playMusic = (musicFile: MusicFile) => {
    stopAllMusic();
    
    if (audioRef.current) {
      audioRef.current.src = musicFile.url;
      audioRef.current.volume = volume;
      audioRef.current.play();
      setCurrentlyPlaying(musicFile.filename);
      
      // 시간 업데이트 인터벌 시작
      intervalRef.current = setInterval(() => {
        if (audioRef.current) {
          setCurrentTime(audioRef.current.currentTime);
          setDuration(audioRef.current.duration || 0);
        }
      }, 1000);
    }
  };

  const pauseMusic = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      setCurrentlyPlaying(null);
    }
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }
  };

  const stopAllMusic = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    setCurrentlyPlaying(null);
    setCurrentTime(0);
    setDuration(0);
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }
  };

  const selectMusic = (musicFile: MusicFile) => {
    onChange(musicFile, musicFile.mood);
  };

  const handleMoodChange = (_event: React.SyntheticEvent, newMood: MusicMood) => {
    stopAllMusic();
    onChange(selectedMusic?.mood === newMood ? selectedMusic : null, newMood);
  };

  const handleVolumeChange = (_event: Event, newValue: number | number[]) => {
    const volumeValue = newValue as number;
    setVolume(volumeValue);
    if (audioRef.current) {
      audioRef.current.volume = volumeValue;
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const canProceed = selectedMusic !== null;

  return (
    <Box>
      <audio ref={audioRef} onEnded={() => setCurrentlyPlaying(null)} />
      
      <Typography variant="h4" component="h1" gutterBottom>
        음악 선택
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        릴스 영상의 배경음악을 선택하세요. 각 음악을 미리 들어볼 수 있습니다.
      </Typography>

      {loading && (
        <Box display="flex" justifyContent="center" sx={{ my: 4 }}>
          <CircularProgress />
        </Box>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {!loading && !error && (
        <Grid container spacing={3}>
          {/* 왼쪽: 음악 성격 선택 */}
          <Grid item xs={12} md={4}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                음악 성격
              </Typography>
              <Tabs
                orientation="vertical"
                value={musicMood}
                onChange={handleMoodChange}
                sx={{ borderRight: 1, borderColor: 'divider' }}
              >
                {Object.entries(MOOD_CONFIG).map(([mood, config]) => (
                  <Tab
                    key={mood}
                    value={mood}
                    label={
                      <Box sx={{ textAlign: 'left', width: '100%' }}>
                        <Typography variant="body1">{config.name}</Typography>
                        <Typography variant="caption" color="text.secondary">
                          {config.description}
                        </Typography>
                      </Box>
                    }
                    sx={{
                      alignItems: 'flex-start',
                      minHeight: 60,
                      '&.Mui-selected': {
                        bgcolor: `${config.color}20`,
                      }
                    }}
                  />
                ))}
              </Tabs>

              {/* 볼륨 컨트롤 */}
              <Box sx={{ mt: 3 }}>
                <Typography variant="body2" gutterBottom>
                  미리듣기 볼륨
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <VolumeUp sx={{ mr: 1 }} />
                  <Slider
                    value={volume}
                    onChange={handleVolumeChange}
                    step={0.1}
                    min={0}
                    max={1}
                    sx={{ flexGrow: 1 }}
                  />
                </Box>
              </Box>
            </Paper>

            {/* 현재 재생 중인 음악 정보 */}
            {currentlyPlaying && (
              <Paper sx={{ p: 2, mt: 2 }}>
                <Typography variant="subtitle2" gutterBottom>
                  재생 중
                </Typography>
                <Typography variant="body2" color="text.secondary" noWrap>
                  {currentlyPlaying}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {formatTime(currentTime)} / {formatTime(duration)}
                </Typography>
              </Paper>
            )}
          </Grid>

          {/* 오른쪽: 음악 파일 목록 */}
          <Grid item xs={12} md={8}>
            <Paper sx={{ p: 3 }}>
              <Box display="flex" alignItems="center" sx={{ mb: 2 }}>
                <Typography variant="h6" sx={{ flexGrow: 1 }}>
                  {MOOD_CONFIG[musicMood].name} 목록
                </Typography>
                <Chip
                  label={`${musicFolders[musicMood].length}개 곡`}
                  size="small"
                  sx={{ bgcolor: `${MOOD_CONFIG[musicMood].color}20` }}
                />
              </Box>

              {musicFolders[musicMood].length === 0 ? (
                <Box sx={{ textAlign: 'center', py: 4, color: 'text.secondary' }}>
                  <MusicNote sx={{ fontSize: 48, mb: 2 }} />
                  <Typography variant="body2">
                    이 카테고리에는 음악이 없습니다
                  </Typography>
                </Box>
              ) : (
                <Grid container spacing={2}>
                  {musicFolders[musicMood].map((musicFile) => (
                    <Grid item xs={12} sm={6} key={musicFile.filename}>
                      <Card
                        sx={{
                          cursor: 'pointer',
                          border: selectedMusic?.filename === musicFile.filename ? 2 : 1,
                          borderColor: selectedMusic?.filename === musicFile.filename 
                            ? 'primary.main' 
                            : 'divider',
                          '&:hover': {
                            bgcolor: 'action.hover',
                          }
                        }}
                        onClick={() => selectMusic(musicFile)}
                      >
                        <CardContent sx={{ p: 2 }}>
                          <Box display="flex" alignItems="center">
                            <Box sx={{ flexGrow: 1, minWidth: 0 }}>
                              <Typography variant="subtitle2" noWrap>
                                {musicFile.displayName}
                              </Typography>
                              <Typography variant="caption" color="text.secondary" noWrap>
                                {musicFile.filename}
                              </Typography>
                            </Box>
                            
                            <Box display="flex" alignItems="center">
                              {/* 선택 상태 표시 */}
                              <IconButton size="small" sx={{ mr: 1 }}>
                                {selectedMusic?.filename === musicFile.filename ? (
                                  <CheckCircle color="primary" />
                                ) : (
                                  <RadioButtonUnchecked color="action" />
                                )}
                              </IconButton>
                              
                              {/* 재생/일시정지 버튼 */}
                              <IconButton
                                size="small"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  if (currentlyPlaying === musicFile.filename) {
                                    pauseMusic();
                                  } else {
                                    playMusic(musicFile);
                                  }
                                }}
                              >
                                {currentlyPlaying === musicFile.filename ? (
                                  <Pause />
                                ) : (
                                  <PlayArrow />
                                )}
                              </IconButton>
                            </Box>
                          </Box>
                        </CardContent>
                      </Card>
                    </Grid>
                  ))}
                </Grid>
              )}

              {selectedMusic && (
                <Alert severity="success" sx={{ mt: 3 }}>
                  <Typography variant="body2">
                    <strong>{selectedMusic.displayName}</strong>이(가) 선택되었습니다.
                  </Typography>
                </Alert>
              )}
            </Paper>
          </Grid>
        </Grid>
      )}

      {/* 하단 버튼 */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 4 }}>
        <Button
          variant="outlined"
          onClick={() => {
            stopAllMusic();
            onBack();
          }}
          size="large"
        >
          이전: 이미지 업로드
        </Button>
        <Button
          variant="contained"
          onClick={() => {
            stopAllMusic();
            onNext();
          }}
          size="large"
          disabled={!canProceed}
        >
          다음: 영상 생성
        </Button>
      </Box>
    </Box>
  );
};

export default MusicStep;