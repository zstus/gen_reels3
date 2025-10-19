"""
비디오 생성 라우터
영상 생성 API (동기/비동기)
"""

from fastapi import APIRouter, HTTPException, Form, File, UploadFile
from fastapi.responses import JSONResponse
from utils.logger_config import get_logger
from typing import Optional
import os
import shutil
import uuid
import json

router = APIRouter(tags=["video"])
logger = get_logger('video_router')

# 전역 변수 (main.py에서 설정)
folder_manager = None
job_queue = None
job_logger = None
FOLDER_MANAGER_AVAILABLE = False
JOB_QUEUE_AVAILABLE = False
JOB_LOGGER_AVAILABLE = False
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output_videos"
CURRENT_BGM_PATH = None
VideoGenerator = None
prepare_files_func = None  # main.py의 prepare_files 함수


def set_dependencies(fm, jq, jl, fm_avail, jq_avail, jl_avail,
                     upload_folder, output_folder, current_bgm, video_gen_class, prepare_func):
    """main.py에서 호출하여 의존성 설정"""
    global folder_manager, job_queue, job_logger
    global FOLDER_MANAGER_AVAILABLE, JOB_QUEUE_AVAILABLE, JOB_LOGGER_AVAILABLE
    global UPLOAD_FOLDER, OUTPUT_FOLDER, CURRENT_BGM_PATH, VideoGenerator, prepare_files_func

    folder_manager = fm
    job_queue = jq
    job_logger = jl
    FOLDER_MANAGER_AVAILABLE = fm_avail
    JOB_QUEUE_AVAILABLE = jq_avail
    JOB_LOGGER_AVAILABLE = jl_avail
    UPLOAD_FOLDER = upload_folder
    OUTPUT_FOLDER = output_folder
    CURRENT_BGM_PATH = current_bgm
    VideoGenerator = video_gen_class
    prepare_files_func = prepare_func


@router.post("/generate-video")
async def generate_video(
    # 웹서비스용 URL 입력
    json_url: str = Form(default=""),
    music_mood: str = Form(default="bright"),
    image_urls: str = Form(default="[]"),

    # 기존 호환성 유지
    content_data: str = Form(default=""),
    background_music: Optional[UploadFile] = File(None),

    # 새로운 파라미터
    selected_bgm_path: str = Form(default=""),
    image_allocation_mode: str = Form(default="2_per_image"),
    text_position: str = Form(default="bottom"),
    text_style: str = Form(default="outline"),
    title_area_mode: str = Form(default="keep"),

    # 폰트 설정
    title_font: str = Form(default="BMYEONSUNG_otf.otf"),
    body_font: str = Form(default="BMYEONSUNG_otf.otf"),
    title_font_size: int = Form(default=42),
    body_font_size: int = Form(default=36),

    # 자막 읽어주기 설정
    voice_narration: str = Form(default="enabled"),

    # 크로스 디졸브 설정
    cross_dissolve: str = Form(default="enabled"),

    # 자막 지속 시간 설정
    subtitle_duration: float = Form(default=0.0),

    # 수정된 텍스트 (JSON 문자열)
    edited_texts: str = Form(default="{}"),

    # 이미지별 패닝 옵션 (JSON 문자열, 예: {"0": true, "1": false})
    image_panning_options: str = Form(default="{}"),

    # 이미지 파일 업로드 (최대 50개)
    image_1: Optional[UploadFile] = File(None),
    image_2: Optional[UploadFile] = File(None),
    image_3: Optional[UploadFile] = File(None),
    image_4: Optional[UploadFile] = File(None),
    image_5: Optional[UploadFile] = File(None),
    image_6: Optional[UploadFile] = File(None),
    image_7: Optional[UploadFile] = File(None),
    image_8: Optional[UploadFile] = File(None),
    image_9: Optional[UploadFile] = File(None),
    image_10: Optional[UploadFile] = File(None),
    image_11: Optional[UploadFile] = File(None),
    image_12: Optional[UploadFile] = File(None),
    image_13: Optional[UploadFile] = File(None),
    image_14: Optional[UploadFile] = File(None),
    image_15: Optional[UploadFile] = File(None),
    image_16: Optional[UploadFile] = File(None),
    image_17: Optional[UploadFile] = File(None),
    image_18: Optional[UploadFile] = File(None),
    image_19: Optional[UploadFile] = File(None),
    image_20: Optional[UploadFile] = File(None),
    image_21: Optional[UploadFile] = File(None),
    image_22: Optional[UploadFile] = File(None),
    image_23: Optional[UploadFile] = File(None),
    image_24: Optional[UploadFile] = File(None),
    image_25: Optional[UploadFile] = File(None),
    image_26: Optional[UploadFile] = File(None),
    image_27: Optional[UploadFile] = File(None),
    image_28: Optional[UploadFile] = File(None),
    image_29: Optional[UploadFile] = File(None),
    image_30: Optional[UploadFile] = File(None),
    image_31: Optional[UploadFile] = File(None),
    image_32: Optional[UploadFile] = File(None),
    image_33: Optional[UploadFile] = File(None),
    image_34: Optional[UploadFile] = File(None),
    image_35: Optional[UploadFile] = File(None),
    image_36: Optional[UploadFile] = File(None),
    image_37: Optional[UploadFile] = File(None),
    image_38: Optional[UploadFile] = File(None),
    image_39: Optional[UploadFile] = File(None),
    image_40: Optional[UploadFile] = File(None),
    image_41: Optional[UploadFile] = File(None),
    image_42: Optional[UploadFile] = File(None),
    image_43: Optional[UploadFile] = File(None),
    image_44: Optional[UploadFile] = File(None),
    image_45: Optional[UploadFile] = File(None),
    image_46: Optional[UploadFile] = File(None),
    image_47: Optional[UploadFile] = File(None),
    image_48: Optional[UploadFile] = File(None),
    image_49: Optional[UploadFile] = File(None),
    image_50: Optional[UploadFile] = File(None),

    # 모드 설정
    use_test_files: bool = Form(default=False),

    # Job ID
    job_id: Optional[str] = Form(None)
):
    try:
        logger.info("🚀 웹서비스 API 호출 시작")

        # Job ID에 따라 작업 폴더 설정
        global UPLOAD_FOLDER, OUTPUT_FOLDER, CURRENT_BGM_PATH
        original_upload_folder = UPLOAD_FOLDER
        original_output_folder = OUTPUT_FOLDER

        if job_id and FOLDER_MANAGER_AVAILABLE:
            try:
                job_uploads_folder, job_output_folder = folder_manager.get_job_folders(job_id)
                UPLOAD_FOLDER = job_uploads_folder
                OUTPUT_FOLDER = job_output_folder
                logger.info(f"🗂️ Job 고유 폴더 사용: uploads={UPLOAD_FOLDER}, output={OUTPUT_FOLDER}")
            except Exception as job_error:
                logger.warning(f"⚠️ Job 폴더 사용 실패, 기본 폴더 사용: {job_error}")

        # uploads 폴더 준비
        if job_id and FOLDER_MANAGER_AVAILABLE:
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            logger.info(f"📁 기존 Job 폴더 재사용: {UPLOAD_FOLDER}")
        else:
            if os.path.exists(UPLOAD_FOLDER):
                shutil.rmtree(UPLOAD_FOLDER)
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            logger.info("📁 uploads 폴더 준비 완료")

        # 업로드된 이미지 파일들 수집
        uploaded_images = [
            image_1, image_2, image_3, image_4, image_5, image_6, image_7, image_8, image_9, image_10,
            image_11, image_12, image_13, image_14, image_15, image_16, image_17, image_18, image_19, image_20,
            image_21, image_22, image_23, image_24, image_25, image_26, image_27, image_28, image_29, image_30,
            image_31, image_32, image_33, image_34, image_35, image_36, image_37, image_38, image_39, image_40,
            image_41, image_42, image_43, image_44, image_45, image_46, image_47, image_48, image_49, image_50
        ]
        uploaded_images = [img for img in uploaded_images if img is not None]

        # prepare_files 함수 호출
        await prepare_files_func(
            json_url, music_mood, image_urls,
            content_data, background_music, use_test_files,
            selected_bgm_path, uploaded_images, edited_texts
        )

        # 영상 생성
        video_gen = VideoGenerator()

        # BGM 파일 경로 결정
        if background_music:
            bgm_file = os.path.join(UPLOAD_FOLDER, "back.mp3")
            logger.info(f"🎵 직접 업로드된 음악 사용: {bgm_file}")
        elif CURRENT_BGM_PATH:
            bgm_file = CURRENT_BGM_PATH
            logger.info(f"🎵 선택된 BGM 파일 사용: {bgm_file}")
        else:
            bgm_file = None
            logger.warning("⚠️ BGM 파일이 설정되지 않았습니다")

        # Frontend 모드를 Backend 형식으로 변환
        mode_mapping = {
            "per-script": "1_per_image",
            "per-two-scripts": "2_per_image",
            "single-for-all": "single_for_all"
        }

        if image_allocation_mode in mode_mapping:
            original_mode = image_allocation_mode
            image_allocation_mode = mode_mapping[image_allocation_mode]
            logger.info(f"🎯 미디어 모드 변환: {original_mode} → {image_allocation_mode}")

        # 파라미터 검증
        if image_allocation_mode not in ["2_per_image", "1_per_image", "single_for_all"]:
            image_allocation_mode = "2_per_image"
            logger.warning(f"⚠️ 잘못된 이미지 할당 모드, 기본값 사용: {image_allocation_mode}")

        if text_position not in ["top", "bottom", "bottom-edge"]:
            text_position = "bottom"
            logger.warning(f"⚠️ 잘못된 텍스트 위치, 기본값 사용: {text_position}")

        if text_style not in ["outline", "background"]:
            text_style = "outline"
            logger.warning(f"⚠️ 잘못된 텍스트 스타일, 기본값 사용: {text_style}")

        logger.info(f"🖼️ 이미지 할당 모드: {image_allocation_mode}")
        logger.info(f"📝 텍스트 위치: {text_position}")
        logger.info(f"🎨 텍스트 스타일: {text_style}")
        logger.info(f"🏠 타이틀 영역 모드: {title_area_mode}")
        logger.info(f"🔤 타이틀 폰트: {title_font} ({title_font_size}pt)")
        logger.info(f"📝 본문 폰트: {body_font} ({body_font_size}pt)")
        logger.info(f"🎤 자막 읽어주기: {voice_narration}")
        logger.info(f"🎬 크로스 디졸브: {cross_dissolve}")
        logger.info(f"⏱️ 자막 지속 시간: {subtitle_duration}초")

        # 이미지별 패닝 옵션 파싱
        parsed_panning_options = None
        if image_panning_options and image_panning_options != "{}":
            try:
                panning_dict = json.loads(image_panning_options)
                # 문자열 키를 정수로 변환
                parsed_panning_options = {int(k): v for k, v in panning_dict.items()}
                logger.info(f"🎨 이미지별 패닝 옵션: {parsed_panning_options}")
            except Exception as parse_error:
                logger.warning(f"⚠️ 패닝 옵션 파싱 실패, 기본값 사용: {parse_error}")
                parsed_panning_options = None

        output_path = video_gen.create_video_from_uploads(
            OUTPUT_FOLDER,
            bgm_file,
            image_allocation_mode,
            text_position,
            text_style,
            title_area_mode,
            title_font,
            body_font,
            title_font_size,
            body_font_size,
            "uploads",
            music_mood,
            voice_narration,
            cross_dissolve,
            subtitle_duration,
            parsed_panning_options
        )

        # 영상 생성 성공 시 job 폴더 정리
        if job_id and FOLDER_MANAGER_AVAILABLE:
            try:
                cleaned = folder_manager.cleanup_job_folders(job_id, keep_output=True)
                if cleaned:
                    logger.info(f"✅ Job 폴더 정리 완료: {job_id}")
                else:
                    logger.warning(f"⚠️ Job 폴더 정리 실패: {job_id}")
            except Exception as cleanup_error:
                logger.warning(f"⚠️ Job 폴더 정리 중 오류: {cleanup_error}")

        # 글로벌 변수 복원
        if job_id and FOLDER_MANAGER_AVAILABLE:
            UPLOAD_FOLDER = original_upload_folder
            OUTPUT_FOLDER = original_output_folder

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Video generated successfully",
                "video_path": output_path
            }
        )

    except Exception as e:
        # 에러 시 job 폴더 정리
        if job_id and FOLDER_MANAGER_AVAILABLE:
            try:
                cleaned = folder_manager.cleanup_job_folders(job_id, keep_output=False)
                if cleaned:
                    logger.info(f"🗑️ 에러 발생으로 Job 폴더 전체 정리: {job_id}")
                else:
                    logger.warning(f"⚠️ 에러 시 Job 폴더 정리 실패: {job_id}")
            except Exception as cleanup_error:
                logger.warning(f"⚠️ 에러 시 Job 폴더 정리 중 추가 오류: {cleanup_error}")

        # 글로벌 변수 복원
        if job_id and FOLDER_MANAGER_AVAILABLE:
            UPLOAD_FOLDER = original_upload_folder
            OUTPUT_FOLDER = original_output_folder

        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": str(e)
            }
        )


@router.post("/generate-video-async")
async def generate_video_async(
    user_email: str = Form(...),
    content_data: str = Form(...),
    music_mood: str = Form(default="bright"),
    image_allocation_mode: str = Form(default="2_per_image"),
    text_position: str = Form(default="bottom"),
    text_style: str = Form(default="outline"),
    title_area_mode: str = Form(default="keep"),
    selected_bgm_path: str = Form(default=""),
    use_test_files: bool = Form(default=False),

    # 폰트 설정
    title_font: str = Form(default="BMYEONSUNG_otf.otf"),
    body_font: str = Form(default="BMYEONSUNG_otf.otf"),
    title_font_size: int = Form(default=42),
    body_font_size: int = Form(default=36),

    # 자막 읽어주기 설정
    voice_narration: str = Form(default="enabled"),

    # 크로스 디졸브 설정
    cross_dissolve: str = Form(default="enabled"),

    # 자막 지속 시간 설정
    subtitle_duration: float = Form(default=0.0),

    # Job ID
    job_id: Optional[str] = Form(None),

    # 수정된 텍스트 (JSON 문자열)
    edited_texts: str = Form(default="{}"),

    # 이미지별 패닝 옵션 (JSON 문자열)
    image_panning_options: str = Form(default="{}"),

    # 이미지 파일 업로드 (최대 50개)
    image_1: Optional[UploadFile] = File(None),
    image_2: Optional[UploadFile] = File(None),
    image_3: Optional[UploadFile] = File(None),
    image_4: Optional[UploadFile] = File(None),
    image_5: Optional[UploadFile] = File(None),
    image_6: Optional[UploadFile] = File(None),
    image_7: Optional[UploadFile] = File(None),
    image_8: Optional[UploadFile] = File(None),
    image_9: Optional[UploadFile] = File(None),
    image_10: Optional[UploadFile] = File(None),
    image_11: Optional[UploadFile] = File(None),
    image_12: Optional[UploadFile] = File(None),
    image_13: Optional[UploadFile] = File(None),
    image_14: Optional[UploadFile] = File(None),
    image_15: Optional[UploadFile] = File(None),
    image_16: Optional[UploadFile] = File(None),
    image_17: Optional[UploadFile] = File(None),
    image_18: Optional[UploadFile] = File(None),
    image_19: Optional[UploadFile] = File(None),
    image_20: Optional[UploadFile] = File(None),
    image_21: Optional[UploadFile] = File(None),
    image_22: Optional[UploadFile] = File(None),
    image_23: Optional[UploadFile] = File(None),
    image_24: Optional[UploadFile] = File(None),
    image_25: Optional[UploadFile] = File(None),
    image_26: Optional[UploadFile] = File(None),
    image_27: Optional[UploadFile] = File(None),
    image_28: Optional[UploadFile] = File(None),
    image_29: Optional[UploadFile] = File(None),
    image_30: Optional[UploadFile] = File(None),
    image_31: Optional[UploadFile] = File(None),
    image_32: Optional[UploadFile] = File(None),
    image_33: Optional[UploadFile] = File(None),
    image_34: Optional[UploadFile] = File(None),
    image_35: Optional[UploadFile] = File(None),
    image_36: Optional[UploadFile] = File(None),
    image_37: Optional[UploadFile] = File(None),
    image_38: Optional[UploadFile] = File(None),
    image_39: Optional[UploadFile] = File(None),
    image_40: Optional[UploadFile] = File(None),
    image_41: Optional[UploadFile] = File(None),
    image_42: Optional[UploadFile] = File(None),
    image_43: Optional[UploadFile] = File(None),
    image_44: Optional[UploadFile] = File(None),
    image_45: Optional[UploadFile] = File(None),
    image_46: Optional[UploadFile] = File(None),
    image_47: Optional[UploadFile] = File(None),
    image_48: Optional[UploadFile] = File(None),
    image_49: Optional[UploadFile] = File(None),
    image_50: Optional[UploadFile] = File(None),
):
    """비동기 영상 생성 요청 - 즉시 Job ID 반환"""
    try:
        if not JOB_QUEUE_AVAILABLE:
            raise HTTPException(
                status_code=500,
                detail="배치 작업 시스템이 사용 불가능합니다."
            )

        logger.info(f"🚀 비동기 영상 생성 요청: {user_email}")

        # Job ID 처리
        if job_id:
            logger.info(f"🆔 기존 Job ID 사용: {job_id}")
        else:
            job_id = str(uuid.uuid4())
            logger.info(f"🆔 새 Job ID 생성: {job_id}")

        # Job 폴더 처리
        if FOLDER_MANAGER_AVAILABLE:
            try:
                try:
                    job_uploads_folder, job_output_folder = folder_manager.get_job_folders(job_id)
                    if os.path.exists(job_uploads_folder):
                        uploads_folder_to_use = job_uploads_folder
                        logger.info(f"📁 기존 Job 폴더 사용: {uploads_folder_to_use}")
                    else:
                        job_uploads_folder, job_output_folder = folder_manager.create_job_folders(job_id)
                        uploads_folder_to_use = job_uploads_folder
                        logger.info(f"📁 새 Job 폴더 생성: {uploads_folder_to_use}")
                except Exception:
                    job_uploads_folder, job_output_folder = folder_manager.create_job_folders(job_id)
                    uploads_folder_to_use = job_uploads_folder
                    logger.info(f"📁 Job 폴더 생성 완료: {uploads_folder_to_use}")
            except Exception as job_error:
                logger.warning(f"⚠️ Job 폴더 생성 실패, 기본 폴더 사용: {job_error}")
                uploads_folder_to_use = UPLOAD_FOLDER
                if os.path.exists(uploads_folder_to_use):
                    shutil.rmtree(uploads_folder_to_use)
                os.makedirs(uploads_folder_to_use, exist_ok=True)
        else:
            uploads_folder_to_use = UPLOAD_FOLDER
            if os.path.exists(uploads_folder_to_use):
                shutil.rmtree(uploads_folder_to_use)
            os.makedirs(uploads_folder_to_use, exist_ok=True)
            logger.info(f"📁 기본 폴더 사용: {uploads_folder_to_use}")

        # 업로드된 파일들 저장
        uploaded_files = [
            ("image_1", image_1), ("image_2", image_2), ("image_3", image_3), ("image_4", image_4), ("image_5", image_5),
            ("image_6", image_6), ("image_7", image_7), ("image_8", image_8), ("image_9", image_9), ("image_10", image_10),
            ("image_11", image_11), ("image_12", image_12), ("image_13", image_13), ("image_14", image_14), ("image_15", image_15),
            ("image_16", image_16), ("image_17", image_17), ("image_18", image_18), ("image_19", image_19), ("image_20", image_20),
            ("image_21", image_21), ("image_22", image_22), ("image_23", image_23), ("image_24", image_24), ("image_25", image_25),
            ("image_26", image_26), ("image_27", image_27), ("image_28", image_28), ("image_29", image_29), ("image_30", image_30),
            ("image_31", image_31), ("image_32", image_32), ("image_33", image_33), ("image_34", image_34), ("image_35", image_35),
            ("image_36", image_36), ("image_37", image_37), ("image_38", image_38), ("image_39", image_39), ("image_40", image_40),
            ("image_41", image_41), ("image_42", image_42), ("image_43", image_43), ("image_44", image_44), ("image_45", image_45),
            ("image_46", image_46), ("image_47", image_47), ("image_48", image_48), ("image_49", image_49), ("image_50", image_50)
        ]

        saved_files = []
        for field_name, uploaded_file in uploaded_files:
            if uploaded_file and uploaded_file.filename:
                file_number = field_name.split('_')[1]
                file_extension = uploaded_file.filename.split('.')[-1].lower()
                save_filename = f"{file_number}.{file_extension}"
                save_path = os.path.join(uploads_folder_to_use, save_filename)

                with open(save_path, "wb") as buffer:
                    shutil.copyfileobj(uploaded_file.file, buffer)

                saved_files.append(save_filename)
                logger.info(f"📁 파일 저장: {save_filename}")

        # 작업 파라미터 구성
        video_params = {
            'content_data': content_data,
            'music_mood': music_mood,
            'image_allocation_mode': image_allocation_mode,
            'text_position': text_position,
            'text_style': text_style,
            'title_area_mode': title_area_mode,
            'selected_bgm_path': selected_bgm_path,
            'use_test_files': use_test_files,
            'uploaded_files': saved_files,
            'title_font': title_font,
            'body_font': body_font,
            'title_font_size': title_font_size,
            'body_font_size': body_font_size,
            'voice_narration': voice_narration,
            'cross_dissolve': cross_dissolve,
            'subtitle_duration': subtitle_duration,
            'edited_texts': edited_texts,  # 수정된 텍스트 추가
            'image_panning_options': image_panning_options  # 패닝 옵션 추가
        }

        # 작업을 큐에 추가
        actual_job_id = job_queue.add_job(user_email, video_params, job_id=job_id)

        # Job 로깅 시스템에 로그 생성
        if JOB_LOGGER_AVAILABLE:
            try:
                reels_content_dict = json.loads(content_data)

                job_logger.create_job_log(
                    job_id=job_id,
                    user_email=user_email,
                    reels_content=reels_content_dict,
                    music_mood=music_mood,
                    text_position=text_position,
                    image_allocation_mode=image_allocation_mode,
                    metadata={}
                )

                # 미디어 파일들을 assets 폴더에 저장
                saved_assets_info = []
                for i, filename in enumerate(saved_files, 1):
                    upload_file_path = os.path.join(UPLOAD_FOLDER, filename)
                    if os.path.exists(upload_file_path):
                        file_ext = filename.split('.')[-1].lower()
                        video_extensions = ['mp4', 'mov', 'avi', 'webm']
                        file_type = 'video' if file_ext in video_extensions else 'image'

                        asset_path = job_logger.save_media_file(
                            job_id=job_id,
                            original_file_path=upload_file_path,
                            original_filename=filename,
                            file_type=file_type,
                            sequence_number=i
                        )

                        saved_assets_info.append({
                            'sequence': i,
                            'original_filename': filename,
                            'asset_path': asset_path,
                            'file_type': file_type,
                            'file_size': os.path.getsize(asset_path) if os.path.exists(asset_path) else 0
                        })

                metadata = {
                    'uploaded_files': saved_assets_info,
                    'title_font': title_font,
                    'body_font': body_font,
                    'voice_narration': voice_narration,
                    'title_area_mode': title_area_mode
                }

                job_logger.update_job_metadata(job_id, metadata)
                logger.info(f"✅ Job 로깅 시스템에 기록 완료: {job_id}")
            except Exception as log_error:
                logger.error(f"⚠️ Job 로깅 실패 (작업은 계속 진행): {log_error}")

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "영상 생성 작업이 큐에 추가되었습니다",
                "job_id": actual_job_id
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 비동기 영상 생성 요청 실패: {e}")
        raise HTTPException(status_code=500, detail="영상 생성 요청 중 오류가 발생했습니다.")


@router.post("/preview-video")
async def preview_video(
    title: str = Form(...),
    body1: str = Form(...),
    text_position: str = Form(default="bottom"),
    text_style: str = Form(default="outline"),
    title_area_mode: str = Form(default="keep"),
    title_font: str = Form(default="BMYEONSUNG_otf.otf"),
    body_font: str = Form(default="BMYEONSUNG_otf.otf"),
    title_font_size: int = Form(default=42),
    body_font_size: int = Form(default=36),
    image_1: Optional[UploadFile] = File(None),
    image_panning_options: str = Form(default="{}"),
    job_id: Optional[str] = Form(None),
):
    """미리보기 이미지 생성"""
    try:
        logger.info(f"미리보기 요청: {title[:20]}...")

        # VideoGenerator 인스턴스 생성
        video_generator = VideoGenerator()

        # 업로드 폴더 설정 (Job ID에 따라 분기)
        if job_id and FOLDER_MANAGER_AVAILABLE:
            try:
                job_uploads_folder, _ = folder_manager.get_job_folders(job_id)
                uploads_folder = job_uploads_folder
                os.makedirs(uploads_folder, exist_ok=True)
                logger.info(f"🗂️ Job 고유 폴더 사용 (프리뷰): {uploads_folder}")
            except Exception as job_error:
                logger.warning(f"⚠️ Job 폴더 사용 실패, 기본 폴더 사용 (프리뷰): {job_error}")
                uploads_folder = UPLOAD_FOLDER
                os.makedirs(uploads_folder, exist_ok=True)
        else:
            uploads_folder = UPLOAD_FOLDER
            os.makedirs(uploads_folder, exist_ok=True)

        # 이미지/비디오 파일 처리
        preview_image_path = None
        if image_1 and hasattr(image_1, 'filename') and image_1.filename:
            # 업로드된 파일 저장
            import time
            image_filename = f"preview_{int(time.time())}_{image_1.filename}"
            image_save_path = os.path.join(uploads_folder, image_filename)

            with open(image_save_path, "wb") as buffer:
                shutil.copyfileobj(image_1.file, buffer)

            # 비디오 파일인지 확인
            video_extensions = ['.mp4', '.mov', '.avi', '.webm', '.mkv']
            is_video = any(image_1.filename.lower().endswith(ext) for ext in video_extensions)

            if is_video:
                # 비디오 파일에서 첫 번째 프레임 추출
                try:
                    from moviepy.editor import VideoFileClip
                    from PIL import Image as PILImage

                    # 비디오에서 첫 번째 프레임 추출
                    video_clip = VideoFileClip(image_save_path)
                    frame = video_clip.get_frame(0)  # 첫 번째 프레임 (t=0)
                    video_clip.close()

                    # 프레임을 이미지로 저장
                    frame_image = PILImage.fromarray(frame)

                    # 비디오 파일명을 이미지 파일명으로 변경
                    frame_filename = f"preview_{int(time.time())}_frame.png"
                    frame_save_path = os.path.join(uploads_folder, frame_filename)
                    frame_image.save(frame_save_path, "PNG")

                    # 원본 비디오 파일 삭제
                    os.unlink(image_save_path)
                    preview_image_path = frame_save_path

                    logger.info(f"비디오에서 프레임 추출 완료: {frame_filename}")

                except Exception as e:
                    logger.warning(f"비디오 프레임 추출 실패: {e}, 기본 이미지 사용")
                    # 비디오 처리 실패 시 원본 파일 삭제하고 기본 이미지 사용
                    try:
                        os.unlink(image_save_path)
                    except:
                        pass
                    preview_image_path = None
            else:
                # 이미지 파일은 그대로 사용
                preview_image_path = image_save_path
        else:
            # 테스트 이미지 사용
            import glob
            test_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), "test")
            test_images = []
            for ext in ["jpg", "jpeg", "png", "webp", "gif", "bmp"]:
                test_files = glob.glob(os.path.join(test_folder, f"1.{ext}"))
                test_images.extend(test_files)

            if test_images:
                preview_image_path = test_images[0]

        if not preview_image_path or not os.path.exists(preview_image_path):
            raise HTTPException(status_code=400, detail="미리보기용 이미지를 찾을 수 없습니다")

        # PIL로 미리보기 이미지 합성
        from PIL import Image as PILImage

        # 배경 이미지 (504x890)
        final_image = PILImage.new('RGB', (504, 890), color=(0, 0, 0))

        title_image_path = None

        if title_area_mode == "keep":
            # 기존 방식: 타이틀 영역 + 미디어 영역
            # 타이틀 이미지 생성 (504x220)
            title_image_path = video_generator.create_title_image(
                title,
                504,
                220,
                title_font,
                title_font_size
            )

            # 배경 이미지 처리 (670px 영역) - 패닝 옵션 고려
            if os.path.exists(preview_image_path):
                bg_image = PILImage.open(preview_image_path)
                work_area_height = 670  # 890 - 220

                # 패닝 옵션 파싱
                enable_panning = True  # 기본값: 패닝 활성화
                if image_panning_options and image_panning_options != "{}":
                    try:
                        import json
                        panning_dict = json.loads(image_panning_options)
                        # 첫 번째 이미지(index 0)의 패닝 옵션 확인
                        enable_panning = panning_dict.get("0", True)
                        logger.info(f"🎨 미리보기 패닝 옵션: {enable_panning}")
                    except Exception as e:
                        logger.warning(f"⚠️ 패닝 옵션 파싱 실패, 기본값(True) 사용: {e}")

                if enable_panning:
                    # 패닝 ON: 무조건 504x670 리사이즈 (기존 로직)
                    bg_image = bg_image.resize((504, work_area_height), PILImage.Resampling.LANCZOS)
                    final_image.paste(bg_image, (0, 220))
                else:
                    # 패닝 OFF: 가로 504px 맞춤 + 종횡비 유지 + 위쪽 붙임
                    img_width, img_height = bg_image.size
                    new_width = 504
                    new_height = int(img_height * new_width / img_width)

                    # 리사이즈 (종횡비 유지)
                    bg_image = bg_image.resize((new_width, new_height), PILImage.Resampling.LANCZOS)

                    # 타이틀 바로 아래에 붙임 (중앙 배치 아님!)
                    y_pos = 220
                    final_image.paste(bg_image, (0, y_pos))
                    logger.info(f"📐 패닝 OFF 미리보기 (keep): {img_width}x{img_height} → {new_width}x{new_height}, Y=220")

            # 타이틀 이미지 합성 (상단)
            if os.path.exists(title_image_path):
                title_img = PILImage.open(title_image_path)
                final_image.paste(title_img, (0, 0))
        else:
            # remove 모드: 전체 화면 미디어 (890px)
            if os.path.exists(preview_image_path):
                bg_image = PILImage.open(preview_image_path)
                work_area_height = 890  # 전체 높이

                # 패닝 옵션 파싱
                enable_panning = True  # 기본값: 패닝 활성화
                if image_panning_options and image_panning_options != "{}":
                    try:
                        import json
                        panning_dict = json.loads(image_panning_options)
                        enable_panning = panning_dict.get("0", True)
                        logger.info(f"🎨 미리보기 패닝 옵션 (remove): {enable_panning}")
                    except Exception as e:
                        logger.warning(f"⚠️ 패닝 옵션 파싱 실패 (remove): {e}")

                if enable_panning:
                    # 패닝 ON: 504x890 리사이즈 (기존 로직)
                    bg_image = bg_image.resize((504, work_area_height), PILImage.Resampling.LANCZOS)
                    final_image.paste(bg_image, (0, 0))
                else:
                    # 패닝 OFF: 가로 504px 맞춤 + 종횡비 유지 + 위쪽 붙임
                    img_width, img_height = bg_image.size
                    new_width = 504
                    new_height = int(img_height * new_width / img_width)

                    # 리사이즈 (종횡비 유지)
                    bg_image = bg_image.resize((new_width, new_height), PILImage.Resampling.LANCZOS)

                    # 맨 위에 붙임
                    y_pos = 0
                    final_image.paste(bg_image, (0, y_pos))
                    logger.info(f"📐 패닝 OFF 미리보기 (remove): {img_width}x{img_height} → {new_width}x{new_height}, Y=0")

        # 본문 텍스트 이미지 생성 (504x890) - 모든 모드 공통
        body_text_image_path = video_generator.create_text_image(
            body1,
            504,
            890,
            text_position,
            text_style,
            is_title=False,
            title_font=title_font,
            body_font=body_font,
            title_area_mode=title_area_mode,
            title_font_size=title_font_size,
            body_font_size=body_font_size
        )

        # 본문 텍스트 이미지 합성 (오버레이)
        if os.path.exists(body_text_image_path):
            body_img = PILImage.open(body_text_image_path).convert('RGBA')
            final_image.paste(body_img, (0, 0), body_img)

        # 미리보기 이미지 저장
        import time
        preview_filename = f"preview_{int(time.time())}.png"
        preview_save_path = os.path.join(uploads_folder, preview_filename)
        final_image.save(preview_save_path, "PNG")

        # 임시 파일 정리
        for temp_file in [title_image_path, body_text_image_path]:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except:
                    pass

        logger.info(f"미리보기 생성 완료: {preview_filename}")

        # Job ID에 따라 URL 경로 설정
        if job_id and FOLDER_MANAGER_AVAILABLE:
            preview_url = f"/job-uploads/{job_id}/{preview_filename}"
        else:
            preview_url = f"/uploads/{preview_filename}"

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "미리보기 생성 성공",
                "preview_url": preview_url,
                "preview_path": preview_save_path
            }
        )

    except Exception as e:
        logger.error(f"미리보기 생성 오류: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"미리보기 생성 실패: {str(e)}"
            }
        )
