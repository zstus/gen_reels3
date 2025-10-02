"""
미디어 자산 관리 시스템 - SQLite 기반
"""
import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from utils.logger_config import get_logger

try:
    from moviepy.editor import VideoFileClip
    from PIL import Image
    MOVIEPY_AVAILABLE = True
except ImportError as e:
    print(f"MoviePy import 오류 (media_asset_manager): {e}")
    VideoFileClip = None
    MOVIEPY_AVAILABLE = False

# 로깅 설정
logger = get_logger('media_asset_manager')

class MediaAssetManager:
    def __init__(self, db_path: str = "log/job_logs.db"):
        self.db_path = db_path
        self.assets_videos_dir = "assets/videos"

        # 디렉토리 생성
        os.makedirs(self.assets_videos_dir, exist_ok=True)

    def extract_video_metadata(self, video_path: str) -> Dict[str, Any]:
        """비디오 파일에서 메타데이터 추출"""
        metadata = {
            'duration': None,
            'width': None,
            'height': None
        }

        if not MOVIEPY_AVAILABLE:
            logger.warning("MoviePy가 사용 불가능하여 메타데이터 추출을 건너뜁니다")
            return metadata

        try:
            with VideoFileClip(video_path) as clip:
                metadata['duration'] = clip.duration
                metadata['width'] = clip.w
                metadata['height'] = clip.h
                logger.info(f"메타데이터 추출 완료: {video_path} ({clip.w}x{clip.h}, {clip.duration:.1f}s)")
        except Exception as e:
            logger.warning(f"메타데이터 추출 실패 ({video_path}): {e}")

        return metadata

    def generate_thumbnail(self, video_path: str, thumbnail_path: str) -> bool:
        """비디오 파일에서 썸네일 이미지 생성"""
        if not MOVIEPY_AVAILABLE:
            logger.warning("MoviePy가 사용 불가능하여 썸네일 생성을 건너뜁니다")
            return False

        try:
            with VideoFileClip(video_path) as clip:
                # 동영상 길이의 10% 지점에서 썸네일 추출 (최소 1초)
                thumbnail_time = min(max(1.0, clip.duration * 0.1), clip.duration - 0.1)

                # 프레임 추출
                frame = clip.get_frame(thumbnail_time)

                # PIL Image로 변환
                image = Image.fromarray(frame)

                # 썸네일 크기로 리사이즈 (가로 240px, 세로 비례 조정)
                image.thumbnail((240, 240), Image.Resampling.LANCZOS)

                # JPG로 저장
                image.save(thumbnail_path, 'JPEG', quality=85)

                logger.info(f"썸네일 생성 완료: {thumbnail_path}")
                return True

        except Exception as e:
            logger.warning(f"썸네일 생성 실패 ({video_path}): {e}")
            return False

    def add_media_asset(self,
                       file_path: str,
                       original_filename: str,
                       title: str = None,
                       tags: List[str] = None,
                       job_id: str = None) -> Optional[int]:
        """새로운 미디어 자산 추가"""
        try:
            if not os.path.exists(file_path):
                logger.error(f"파일이 존재하지 않습니다: {file_path}")
                return None

            # 파일 정보 추출
            file_size = os.path.getsize(file_path)
            file_ext = os.path.splitext(original_filename)[1].lower()

            # 파일 타입 결정
            video_extensions = ['.mp4', '.mov', '.avi', '.webm', '.mkv']
            image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']

            if file_ext in video_extensions:
                file_type = "video"
            elif file_ext in image_extensions:
                file_type = "image"
            else:
                logger.warning(f"지원하지 않는 파일 형식: {file_ext}")
                return None

            # 메타데이터 추출 (비디오인 경우)
            metadata = {}
            if file_type == "video":
                metadata = self.extract_video_metadata(file_path)

            # 썸네일 생성 (비디오인 경우)
            thumbnail_path = None
            if file_type == "video":
                # 썸네일 파일명 생성
                filename_without_ext = os.path.splitext(os.path.basename(file_path))[0]
                thumbnail_filename = f"{filename_without_ext}.jpg"
                thumbnail_path = os.path.join(self.assets_videos_dir, thumbnail_filename)

                # 썸네일 생성 시도
                if self.generate_thumbnail(file_path, thumbnail_path):
                    # 상대 경로로 저장
                    thumbnail_path = os.path.relpath(thumbnail_path)
                else:
                    thumbnail_path = None

            # 데이터베이스에 저장
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                now = datetime.now()
                cursor.execute('''
                    INSERT INTO media_assets (
                        file_path, original_filename, file_type, file_size,
                        duration, width, height, thumbnail_path, title, tags,
                        is_favorite, created_at, updated_at, job_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    file_path,
                    original_filename,
                    file_type,
                    file_size,
                    metadata.get('duration'),
                    metadata.get('width'),
                    metadata.get('height'),
                    thumbnail_path,
                    title or original_filename,
                    json.dumps(tags or [], ensure_ascii=False),
                    False,  # is_favorite
                    now,
                    now,
                    job_id
                ))

                asset_id = cursor.lastrowid
                conn.commit()

                logger.info(f"미디어 자산 추가 완료: {original_filename} (ID: {asset_id})")
                return asset_id

        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                logger.warning(f"이미 존재하는 파일입니다: {file_path}")
                return self.get_asset_by_path(file_path)
            else:
                logger.error(f"데이터베이스 무결성 오류: {e}")
                return None
        except Exception as e:
            logger.error(f"미디어 자산 추가 실패: {e}")
            return None

    def get_asset_by_path(self, file_path: str) -> Optional[int]:
        """파일 경로로 자산 ID 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id FROM media_assets WHERE file_path = ?', (file_path,))
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            logger.error(f"자산 ID 조회 실패: {e}")
            return None

    def get_recent_videos(self,
                         page: int = 1,
                         limit: int = 10,
                         tags: List[str] = None) -> Dict[str, Any]:
        """최근 비디오 목록 조회 (페이지네이션 및 태그 필터링 지원)"""
        try:
            offset = (page - 1) * limit

            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # 기본 쿼리
                base_query = '''
                    FROM media_assets
                    WHERE file_type = 'video'
                '''
                params = []

                # 태그 필터링 추가
                if tags and len(tags) > 0:
                    tag_conditions = []
                    for tag in tags:
                        tag_conditions.append("tags LIKE ?")
                        params.append(f'%"{tag}"%')
                    base_query += f" AND ({' OR '.join(tag_conditions)})"

                # 정렬 (즐겨찾기 우선, 그 다음 생성일 역순)
                order_by = " ORDER BY is_favorite DESC, created_at DESC"

                # 전체 개수 조회
                count_query = f"SELECT COUNT(*) {base_query}"
                cursor.execute(count_query, params)
                total_count = cursor.fetchone()[0]

                # 데이터 조회
                data_query = f'''
                    SELECT id, file_path, original_filename, file_type, file_size,
                           duration, width, height, thumbnail_path, title, tags,
                           is_favorite, created_at, updated_at, job_id
                    {base_query}
                    {order_by}
                    LIMIT ? OFFSET ?
                '''
                cursor.execute(data_query, params + [limit, offset])

                videos = []
                for row in cursor.fetchall():
                    video_data = dict(row)
                    # tags JSON 파싱
                    video_data['tags'] = json.loads(video_data['tags'])
                    # 썸네일 URL 생성
                    if video_data['thumbnail_path']:
                        video_data['thumbnail_url'] = f"/assets/videos/{os.path.basename(video_data['thumbnail_path'])}"
                    else:
                        video_data['thumbnail_url'] = None
                    videos.append(video_data)

                return {
                    'videos': videos,
                    'total_count': total_count,
                    'page': page,
                    'limit': limit,
                    'total_pages': (total_count + limit - 1) // limit,
                    'has_more': offset + len(videos) < total_count
                }

        except Exception as e:
            logger.error(f"최근 비디오 조회 실패: {e}")
            return {
                'videos': [],
                'total_count': 0,
                'page': page,
                'limit': limit,
                'total_pages': 0,
                'has_more': False,
                'error': str(e)
            }

    def update_asset_tags(self, asset_id: int, tags: List[str]) -> bool:
        """자산의 태그 업데이트"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE media_assets
                    SET tags = ?, updated_at = ?
                    WHERE id = ?
                ''', (json.dumps(tags, ensure_ascii=False), datetime.now(), asset_id))

                conn.commit()
                logger.info(f"자산 태그 업데이트 완료: ID {asset_id}")
                return cursor.rowcount > 0

        except Exception as e:
            logger.error(f"자산 태그 업데이트 실패: {e}")
            return False

    def set_favorite(self, asset_id: int, is_favorite: bool) -> bool:
        """즐겨찾기 상태 설정"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE media_assets
                    SET is_favorite = ?, updated_at = ?
                    WHERE id = ?
                ''', (is_favorite, datetime.now(), asset_id))

                conn.commit()
                logger.info(f"즐겨찾기 상태 변경: ID {asset_id} -> {is_favorite}")
                return cursor.rowcount > 0

        except Exception as e:
            logger.error(f"즐겨찾기 상태 변경 실패: {e}")
            return False

    def get_all_tags(self) -> List[str]:
        """모든 태그 목록 조회 (자동완성용)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT DISTINCT tags FROM media_assets WHERE tags != "[]"')

                all_tags = set()
                for row in cursor.fetchall():
                    tags = json.loads(row[0])
                    all_tags.update(tags)

                return sorted(list(all_tags))

        except Exception as e:
            logger.error(f"태그 목록 조회 실패: {e}")
            return []

    def scan_and_import_existing_videos(self) -> Dict[str, Any]:
        """기존 비디오 파일들을 스캔하여 데이터베이스에 추가"""
        try:
            video_extensions = ['.mp4', '.mov', '.avi', '.webm', '.mkv']
            imported_count = 0
            skipped_count = 0
            error_count = 0

            logger.info(f"비디오 폴더 스캔 시작: {self.assets_videos_dir}")

            if not os.path.exists(self.assets_videos_dir):
                logger.warning(f"비디오 폴더가 존재하지 않습니다: {self.assets_videos_dir}")
                return {
                    'imported': 0,
                    'skipped': 0,
                    'errors': 0,
                    'message': '비디오 폴더가 존재하지 않습니다'
                }

            for filename in os.listdir(self.assets_videos_dir):
                file_path = os.path.join(self.assets_videos_dir, filename)

                # 디렉토리 건너뛰기
                if os.path.isdir(file_path):
                    continue

                # 썸네일 파일 건너뛰기 (.jpg)
                if filename.lower().endswith('.jpg'):
                    continue

                # 비디오 파일인지 확인
                file_ext = os.path.splitext(filename)[1].lower()
                if file_ext not in video_extensions:
                    continue

                try:
                    # 이미 존재하는지 확인
                    if self.get_asset_by_path(file_path):
                        skipped_count += 1
                        logger.info(f"이미 존재하는 파일 건너뛰기: {filename}")
                        continue

                    # 데이터베이스에 추가
                    asset_id = self.add_media_asset(
                        file_path=file_path,
                        original_filename=filename,
                        title=os.path.splitext(filename)[0]
                    )

                    if asset_id:
                        imported_count += 1
                        logger.info(f"파일 가져오기 완료: {filename}")
                    else:
                        error_count += 1
                        logger.error(f"파일 가져오기 실패: {filename}")

                except Exception as e:
                    error_count += 1
                    logger.error(f"파일 처리 중 오류 ({filename}): {e}")

            result = {
                'imported': imported_count,
                'skipped': skipped_count,
                'errors': error_count,
                'message': f"스캔 완료: {imported_count}개 가져옴, {skipped_count}개 건너뜀, {error_count}개 오류"
            }

            logger.info(result['message'])
            return result

        except Exception as e:
            logger.error(f"비디오 스캔 및 가져오기 실패: {e}")
            return {
                'imported': 0,
                'skipped': 0,
                'errors': 1,
                'message': f"스캔 실패: {str(e)}"
            }

# 전역 인스턴스
media_asset_manager = MediaAssetManager()