import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Grid,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  FormControl,
  FormLabel,
  RadioGroup,
  FormControlLabel,
  Radio,
  Alert,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
  Tooltip,
  CircularProgress,
} from '@mui/material';
import { ExpandMore, Add, Remove, Upload, ContentCopy, Help, Link, AutoAwesome } from '@mui/icons-material';
import { ReelsContent } from '../types';

interface ContentStepProps {
  content: ReelsContent;
  onChange: (content: ReelsContent) => void;
  onNext: () => void;
}

const ContentStep: React.FC<ContentStepProps> = ({ content, onChange, onNext }) => {
  const [scriptCount, setScriptCount] = useState(2); // 기본 2개 대사
  const [errors, setErrors] = useState<{ [key: string]: string }>({});
  const [jsonInput, setJsonInput] = useState('');
  const [jsonError, setJsonError] = useState('');
  const [showOverwriteDialog, setShowOverwriteDialog] = useState(false);
  const [parsedContent, setParsedContent] = useState<ReelsContent | null>(null);
  const [showJsonHelp, setShowJsonHelp] = useState(false);
  const [urlInput, setUrlInput] = useState('');
  const [isExtracting, setIsExtracting] = useState(false);
  const [extractError, setExtractError] = useState('');

  // 현재 작성된 대사 개수 계산
  const getFilledScriptCount = () => {
    let count = 0;
    for (let i = 1; i <= 50; i++) {
      const bodyKey = `body${i}` as keyof ReelsContent;
      if (content[bodyKey]?.trim()) {
        count++;
      }
    }
    return count;
  };

  const addScript = () => {
    if (scriptCount < 50) {
      setScriptCount(scriptCount + 1);
    }
  };

  const removeScript = () => {
    if (scriptCount > 1) {
      setScriptCount(scriptCount - 1);
      // 제거된 대사 내용 초기화
      const bodyKey = `body${scriptCount}` as keyof ReelsContent;
      onChange({ ...content, [bodyKey]: '' });
    }
  };

  const handleChange = (field: keyof ReelsContent, value: string) => {
    onChange({ ...content, [field]: value });
    
    // 에러 상태 초기화
    if (errors[field]) {
      setErrors({ ...errors, [field]: '' });
    }
  };

  const validateContent = () => {
    const newErrors: { [key: string]: string } = {};

    // 제목 검증
    if (!content.title.trim()) {
      newErrors.title = '제목을 입력해주세요';
    } else if (content.title.length > 50) {
      newErrors.title = '제목은 50자 이내로 입력해주세요';
    }

    // 최소 1개 대사 검증
    const filledScripts = getFilledScriptCount();
    if (filledScripts === 0) {
      newErrors.body1 = '최소 1개 이상의 대사를 입력해주세요';
    }

    // 각 대사 길이 검증
    for (let i = 1; i <= scriptCount; i++) {
      const bodyKey = `body${i}` as keyof ReelsContent;
      const bodyValue = content[bodyKey]?.trim() || '';
      
      if (bodyValue && bodyValue.length > 200) {
        newErrors[bodyKey] = `대사 ${i}은 200자 이내로 입력해주세요`;
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleNext = () => {
    if (validateContent()) {
      onNext();
    }
  };

  const getCharacterCount = (text: string) => {
    return text ? text.length : 0;
  };

  const getEstimatedDuration = () => {
    let totalChars = 0;
    for (let i = 1; i <= 50; i++) {
      const bodyKey = `body${i}` as keyof ReelsContent;
      totalChars += getCharacterCount(content[bodyKey] || '');
    }
    // 한국어 기준: 분당 300자, 1.5배속 적용 (분당 450자)
    const duration = Math.max(5, Math.ceil((totalChars / 450) * 60));
    return duration;
  };

  // JSON 파싱 함수
  const parseJsonContent = (jsonString: string): ReelsContent | null => {
    try {
      // 스마트 따옴표 → 일반 따옴표 정규화 (맥 등에서 자동 변환되는 문제 대응)
      const normalized = jsonString
        .replace(/\u201c/g, '"')   // " → "
        .replace(/\u201d/g, '"')   // " → "
        .replace(/\u2018/g, "'")   // ' → '
        .replace(/\u2019/g, "'");  // ' → '
      const parsed = JSON.parse(normalized);
      
      // 필수 필드 검증
      if (!parsed.title) {
        setJsonError('title 필드가 필요합니다.');
        return null;
      }

      // ReelsContent 형태로 변환
      const newContent: any = {
        title: parsed.title.substring(0, 50), // 길이 제한
        body1: '',
      };

      // body 필드들 추가 (최대 50개)
      let bodyCount = 0;
      for (let i = 1; i <= 50; i++) {
        const bodyKey = `body${i}`;
        if (parsed[bodyKey]) {
          const bodyText = parsed[bodyKey].substring(0, 200); // 길이 제한
          newContent[bodyKey] = bodyText;
          bodyCount = i;
        } else if (i > 1) {
          // body2 이후는 선택사항으로 빈 문자열 초기화하지 않음
          newContent[bodyKey] = '';
        }
      }

      setJsonError('');
      return newContent;
    } catch (error) {
      setJsonError('올바른 JSON 형식이 아닙니다.');
      return null;
    }
  };

  // JSON에서 콘텐츠 불러오기
  const handleJsonImport = () => {
    if (!jsonInput.trim()) {
      setJsonError('JSON 내용을 입력해주세요.');
      return;
    }

    const parsed = parseJsonContent(jsonInput);
    if (parsed) {
      setParsedContent(parsed);
      
      // 기존 내용이 있는지 확인
      const hasExistingContent = content.title.trim() || getFilledScriptCount() > 0;
      
      if (hasExistingContent) {
        setShowOverwriteDialog(true);
      } else {
        applyParsedContent(parsed);
      }
    }
  };

  // 파싱된 콘텐츠 적용
  const applyParsedContent = (newContent: ReelsContent) => {
    onChange(newContent);
    
    // script count 자동 조정
    let maxBodyIndex = 0;
    for (let i = 1; i <= 50; i++) {
      const bodyKey = `body${i}` as keyof ReelsContent;
      if (newContent[bodyKey]?.trim()) {
        maxBodyIndex = i;
      }
    }
    setScriptCount(Math.max(2, maxBodyIndex)); // 최소 2개
    
    setJsonInput('');
    setShowOverwriteDialog(false);
    setParsedContent(null);
  };

  // 덮어쓰기 확인
  const handleOverwriteConfirm = () => {
    if (parsedContent) {
      applyParsedContent(parsedContent);
    }
  };

  // 예제 JSON 불러오기
  const loadExampleJson = () => {
    const exampleJson = {
      "title": "결혼 5개월 전",
      "body1": "펜션에서 컵라면 먹으려다, 커피포트 물이 튀어 발등 화상!",
      "body2": "너무 아파서 주저앉았는데… 예비신랑? 그냥 '헐' 한마디 하고 소파 가서 유튜브",
      "body3": "심지어 '괜찮아?' 이 한마디도 없음. 동태눈으로 빤히 쳐다본 게 다임",
      "body4": "이전에도 공감 제로, 내 얘기하면 무반응, 웃겨도 정색… 이번엔 진짜 터짐.",
      "body5": "따지니까 '내가 괜찮냐고 물으면 낫냐? 여자들은 너무 기대가 크다' 이딴 소리",
      "body6": "결혼 약속하니까 이제 보인다. 이기적이고 공감 없는 남자라는 거.",
      "body7": "백년해로? 아니, 예식장 취소부터 검색 중ㅋㅋ 내가 너무한 걸까?"
    };
    setJsonInput(JSON.stringify(exampleJson, null, 2));
  };

  // URL에서 릴스 대본 추출
  const handleExtractFromUrl = async () => {
    if (!urlInput.trim()) {
      setExtractError('URL을 입력해주세요.');
      return;
    }

    // URL 형식 검증
    try {
      new URL(urlInput);
    } catch {
      setExtractError('올바른 URL 형식이 아닙니다.');
      return;
    }

    setIsExtracting(true);
    setExtractError('');

    try {
      const response = await fetch('/extract-reels-from-url', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url: urlInput }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      if (data.status === 'success') {
        // JSON 입력 영역에 결과 설정
        setJsonInput(JSON.stringify(data.reels_content, null, 2));
        setExtractError('');
        
        // 성공 메시지 표시 (선택사항)
        setTimeout(() => {
          setUrlInput(''); // URL 입력 초기화
        }, 1000);
      } else {
        throw new Error(data.message || '릴스 대본 추출에 실패했습니다.');
      }
    } catch (error) {
      console.error('URL 추출 에러:', error);
      setExtractError(error instanceof Error ? error.message : '알 수 없는 오류가 발생했습니다.');
    } finally {
      setIsExtracting(false);
    }
  };

  // URL 입력 변경 처리
  const handleUrlChange = (value: string) => {
    setUrlInput(value);
    if (extractError) {
      setExtractError('');
    }
  };

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        릴스 대본 작성
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        릴스 영상에 사용할 제목과 대사를 입력하세요. URL에서 자동으로 대본을 생성하거나 직접 입력할 수 있습니다.
      </Typography>

      {/* URL에서 릴스 대본 추출 영역 */}
      <Paper sx={{ p: 3, mb: 3, bgcolor: 'primary.50', border: '1px solid', borderColor: 'primary.200' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
          <AutoAwesome color="primary" />
          <Typography variant="h6" color="primary">
            AI로 릴스 대본 자동 생성
          </Typography>
        </Box>
        
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          웹사이트 URL을 입력하면 AI가 해당 페이지의 내용을 분석하여 릴스용 대본을 자동으로 생성해드립니다.
        </Typography>

        <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
          <TextField
            label="웹사이트 URL"
            value={urlInput}
            onChange={(e) => handleUrlChange(e.target.value)}
            placeholder="https://example.com/article"
            fullWidth
            error={!!extractError}
            helperText={extractError}
            disabled={isExtracting}
            InputProps={{
              startAdornment: <Link sx={{ mr: 1, color: 'text.secondary' }} />,
            }}
          />
          <Button
            variant="contained"
            onClick={handleExtractFromUrl}
            disabled={isExtracting || !urlInput.trim()}
            sx={{ minWidth: 140 }}
            startIcon={isExtracting ? <CircularProgress size={16} /> : <AutoAwesome />}
          >
            {isExtracting ? '추출 중...' : '릴스 JSON 추출'}
          </Button>
        </Box>

        {isExtracting && (
          <Alert severity="info" sx={{ mb: 2 }}>
            <Typography variant="body2">
              AI가 페이지 내용을 분석하고 릴스용 대본을 생성하고 있습니다... 잠시만 기다려주세요.
            </Typography>
          </Alert>
        )}
      </Paper>

      <Grid container spacing={3}>
        {/* 왼쪽: 입력 폼 */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3 }}>
            {/* 제목 입력 */}
            <TextField
              label={
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  영상 제목?
                  <Tooltip
                    title={
                      <Box sx={{ p: 1 }}>
                        <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 1 }}>
                          🎨 색상 태그 사용법
                        </Typography>
                        <Typography variant="body2" sx={{ mb: 1 }}>
                          형식: <code style={{ backgroundColor: '#555', padding: '2px 4px', borderRadius: '3px' }}>[색상:단어]</code>
                        </Typography>
                        <Typography variant="body2" sx={{ mb: 1 }}>
                          예시: <code style={{ backgroundColor: '#555', padding: '2px 4px', borderRadius: '3px' }}>나는 [yellow:학교]를</code>
                        </Typography>
                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 1 }}>
                          <Box component="span" sx={{ fontSize: '11px', bgcolor: '#FDCA03', color: '#000', px: 0.5, py: 0.25, borderRadius: '3px', fontWeight: 'bold' }}>yellow</Box>
                          <Box component="span" sx={{ fontSize: '11px', bgcolor: '#0090FF', color: '#fff', px: 0.5, py: 0.25, borderRadius: '3px', fontWeight: 'bold' }}>blue</Box>
                          <Box component="span" sx={{ fontSize: '11px', bgcolor: '#FE0102', color: '#fff', px: 0.5, py: 0.25, borderRadius: '3px', fontWeight: 'bold' }}>red</Box>
                          <Box component="span" sx={{ fontSize: '11px', bgcolor: '#02D330', color: '#fff', px: 0.5, py: 0.25, borderRadius: '3px', fontWeight: 'bold' }}>green</Box>
                          <Box component="span" sx={{ fontSize: '11px', bgcolor: '#FF822B', color: '#fff', px: 0.5, py: 0.25, borderRadius: '3px', fontWeight: 'bold' }}>orange</Box>
                          <Box component="span" sx={{ fontSize: '11px', bgcolor: '#6FDAA5', color: '#000', px: 0.5, py: 0.25, borderRadius: '3px', fontWeight: 'bold' }}>mint</Box>
                          <Box component="span" sx={{ fontSize: '11px', bgcolor: '#02FDFE', color: '#000', px: 0.5, py: 0.25, borderRadius: '3px', fontWeight: 'bold' }}>sky</Box>
                        </Box>
                      </Box>
                    }
                    arrow
                    placement="right"
                  >
                    <Help fontSize="small" sx={{ color: 'action.active', cursor: 'help' }} />
                  </Tooltip>
                </Box>
              }
              placeholder="숏폼 상단 타이틀"
              value={content.title}
              onChange={(e) => handleChange('title', e.target.value)}
              fullWidth
              error={!!errors.title}
              helperText={errors.title || `${getCharacterCount(content.title)}/50자`}
              sx={{ mb: 3 }}
              inputProps={{ maxLength: 50 }}
              InputLabelProps={{ shrink: true }}
            />

            {/* JSON 일괄 입력 영역 */}
            <Accordion sx={{ mb: 3 }}>
              <AccordionSummary expandIcon={<ExpandMore />}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Upload color="primary" />
                  <Typography variant="h6">JSON으로 일괄 입력</Typography>
                  <Tooltip title="JSON 형식 도움말">
                    <IconButton size="small" onClick={() => setShowJsonHelp(true)}>
                      <Help fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <Box>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    JSON 형태로 제목과 대사를 한 번에 입력할 수 있습니다.
                  </Typography>
                  
                  <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
                    <Button
                      variant="outlined"
                      size="small"
                      onClick={loadExampleJson}
                      startIcon={<ContentCopy />}
                    >
                      예제 불러오기
                    </Button>
                  </Box>

                  <TextField
                    label="JSON 데이터"
                    value={jsonInput}
                    onChange={(e) => setJsonInput(e.target.value)}
                    multiline
                    rows={8}
                    fullWidth
                    placeholder='{\n  "title": "영상 제목",\n  "body1": "첫 번째 대사",\n  "body2": "두 번째 대사"\n}'
                    error={!!jsonError}
                    helperText={jsonError}
                    sx={{ mb: 2 }}
                  />

                  <Button
                    variant="contained"
                    onClick={handleJsonImport}
                    startIcon={<Upload />}
                    disabled={!jsonInput.trim()}
                  >
                    JSON에서 불러오기
                  </Button>
                </Box>
              </AccordionDetails>
            </Accordion>

            {/* 대사 입력 섹션 */}
            <Box sx={{ mb: 3 }}>
              <Box display="flex" alignItems="center" justifyContent="space-between" sx={{ mb: 2 }}>
                <Typography variant="h6">대사 입력</Typography>
                <Box>
                  <Button
                    size="small"
                    onClick={removeScript}
                    disabled={scriptCount <= 1}
                    startIcon={<Remove />}
                    sx={{ mr: 1 }}
                  >
                    제거
                  </Button>
                  <Button
                    size="small"
                    onClick={addScript}
                    disabled={scriptCount >= 50}
                    startIcon={<Add />}
                    variant="outlined"
                  >
                    추가
                  </Button>
                </Box>
              </Box>

              {/* 대사 입력 필드들 */}
              {Array.from({ length: scriptCount }, (_, i) => i + 1).map((num) => {
                const bodyKey = `body${num}` as keyof ReelsContent;
                const value = content[bodyKey] || '';
                
                return (
                  <TextField
                    key={bodyKey}
                    label={`대사 ${num}`}
                    value={value}
                    onChange={(e) => handleChange(bodyKey, e.target.value)}
                    fullWidth
                    multiline
                    rows={3}
                    error={!!errors[bodyKey]}
                    helperText={errors[bodyKey] || `${getCharacterCount(value)}/200자`}
                    sx={{ mb: 2 }}
                    inputProps={{ maxLength: 200 }}
                    placeholder="대사 내용을 입력하세요"
                  />
                );
              })}
            </Box>

            <Button
              variant="contained"
              size="large"
              onClick={handleNext}
              disabled={!content.title.trim() || getFilledScriptCount() === 0}
              sx={{ mt: 2 }}
            >
              다음: 이미지 업로드
            </Button>
          </Paper>
        </Grid>

        {/* 오른쪽: 정보 패널 */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, mb: 2 }}>
            <Typography variant="h6" gutterBottom>
              작성 현황
            </Typography>
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" color="text.secondary">
                작성된 대사: <strong>{getFilledScriptCount()}/{scriptCount}개</strong>
              </Typography>
              <Typography variant="body2" color="text.secondary">
                예상 영상 길이: <strong>약 {getEstimatedDuration()}초</strong>
              </Typography>
            </Box>
            
            {/* 작성 상태 칩 */}
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
              <Chip
                label={`제목 ${content.title.trim() ? '완료' : '미완료'}`}
                color={content.title.trim() ? 'success' : 'default'}
                size="small"
              />
              {Array.from({ length: scriptCount }, (_, i) => i + 1).map((num) => {
                const bodyKey = `body${num}` as keyof ReelsContent;
                const filled = !!(content[bodyKey]?.trim());
                return (
                  <Chip
                    key={bodyKey}
                    label={`대사${num} ${filled ? '완료' : '미완료'}`}
                    color={filled ? 'success' : 'default'}
                    size="small"
                  />
                );
              })}
            </Box>
          </Paper>

          {/* 도움말 */}
          <Accordion>
            <AccordionSummary expandIcon={<ExpandMore />}>
              <Typography variant="subtitle2">작성 가이드</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Typography variant="body2" component="div">
                <strong>제목 작성 팁:</strong>
                <ul>
                  <li>간결하고 흥미로운 제목 작성</li>
                  <li>50자 이내 권장</li>
                </ul>
                <strong>대사 작성 팁:</strong>
                <ul>
                  <li>각 대사는 하나의 화면으로 표시됩니다</li>
                  <li>200자 이내 권장</li>
                  <li>읽기 쉬운 길이로 나누어 작성</li>
                </ul>

                <Divider sx={{ my: 2 }} />

                <Box sx={{ mt: 2, p: 2, bgcolor: 'primary.50', borderRadius: 1, border: '1px solid', borderColor: 'primary.200' }}>
                  <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 1, color: 'primary.main' }}>
                    🎬 영상 생성 프로세스가 궁금하신가요?
                  </Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
                    대본 작성부터 최종 영상 완성까지의 전체 과정을 시각적으로 확인하세요
                  </Typography>
                  <Button
                    variant="outlined"
                    size="small"
                    fullWidth
                    onClick={() => window.open('/reels-generation-flowchart.html', '_blank')}
                    startIcon={<Help />}
                    sx={{
                      textTransform: 'none',
                      borderColor: 'primary.main',
                      color: 'primary.main',
                      '&:hover': {
                        borderColor: 'primary.dark',
                        bgcolor: 'primary.100'
                      }
                    }}
                  >
                    인터랙티브 플로우차트 보기
                  </Button>
                </Box>
              </Typography>
            </AccordionDetails>
          </Accordion>

          {/* 예상 결과 미리보기 */}
          {(content.title.trim() || getFilledScriptCount() > 0) && (
            <Paper sx={{ p: 2, mt: 2, bgcolor: 'action.hover' }}>
              <Typography variant="subtitle2" gutterBottom>
                미리보기
              </Typography>
              <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 1 }}>
                {content.title || '[제목]'}
              </Typography>
              {Array.from({ length: scriptCount }, (_, i) => i + 1).map((num) => {
                const bodyKey = `body${num}` as keyof ReelsContent;
                const value = content[bodyKey]?.trim();
                if (value) {
                  return (
                    <Typography key={bodyKey} variant="body2" sx={{ mb: 0.5 }}>
                      {num}. {value}
                    </Typography>
                  );
                }
                return null;
              })}
            </Paper>
          )}
        </Grid>
      </Grid>

      {/* 덮어쓰기 확인 다이얼로그 */}
      <Dialog open={showOverwriteDialog} onClose={() => setShowOverwriteDialog(false)}>
        <DialogTitle>기존 내용을 덮어쓰시겠습니까?</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary">
            현재 작성된 내용이 있습니다. JSON 데이터로 덮어쓰면 기존 내용이 모두 사라집니다.
          </Typography>
          {parsedContent && (
            <Box sx={{ mt: 2, p: 2, bgcolor: 'grey.100', borderRadius: 1 }}>
              <Typography variant="subtitle2" sx={{ mb: 1 }}>미리보기:</Typography>
              <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 1 }}>
                제목: {parsedContent.title}
              </Typography>
              {Object.entries(parsedContent).map(([key, value]) => {
                if (key !== 'title' && value?.trim()) {
                  const num = key.replace('body', '');
                  return (
                    <Typography key={key} variant="caption" display="block">
                      대사 {num}: {value.substring(0, 50)}{value.length > 50 ? '...' : ''}
                    </Typography>
                  );
                }
                return null;
              })}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowOverwriteDialog(false)}>취소</Button>
          <Button onClick={handleOverwriteConfirm} variant="contained" color="warning">
            덮어쓰기
          </Button>
        </DialogActions>
      </Dialog>

      {/* JSON 도움말 다이얼로그 */}
      <Dialog open={showJsonHelp} onClose={() => setShowJsonHelp(false)} maxWidth="md" fullWidth>
        <DialogTitle>JSON 형식 가이드</DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ mb: 2 }}>
            다음과 같은 JSON 형식으로 데이터를 입력하세요:
          </Typography>
          
          <Box sx={{ bgcolor: 'grey.100', p: 2, borderRadius: 1, mb: 2 }}>
            <Typography component="pre" variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.875rem' }}>
{`{
  "title": "영상 제목 (필수, 50자 이내)",
  "body1": "첫 번째 대사 (200자 이내)",
  "body2": "두 번째 대사 (200자 이내)",
  "body3": "세 번째 대사 (선택사항)",
  ...
  "body50": "마지막 대사 (최대 50개)"
}`}
            </Typography>
          </Box>

          <Typography variant="body2" sx={{ mb: 2 }}>
            <strong>주의사항:</strong>
          </Typography>
          <Box component="ul" sx={{ pl: 2, m: 0 }}>
            <Typography component="li" variant="body2">title 필드는 필수입니다</Typography>
            <Typography component="li" variant="body2">제목은 50자, 각 대사는 200자까지 입력 가능합니다</Typography>
            <Typography component="li" variant="body2">body1부터 body50까지 순서대로 입력하세요 (최대 50개)</Typography>
            <Typography component="li" variant="body2">빈 body 필드가 있어도 괜찮습니다</Typography>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowJsonHelp(false)} variant="contained">
            확인
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ContentStep;