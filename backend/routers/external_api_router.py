"""
외부 API 라우터
외부 시스템에서 직접 릴스를 생성하기 위한 간소화된 API
"""

from fastapi import APIRouter, HTTPException, Form, File, UploadFile, Header
from fastapi.responses import JSONResponse
from utils.logger_config import get_logger
from typing import Optional
import os
import shutil
import uuid

router = APIRouter(prefix="/v1", tags=["external-api"])
logger = get_logger('external_api_router')

# 전역 변수 (main.py에서 설정)
folder_manager = None
job_queue = None
FOLDER_MANAGER_AVAILABLE = False
JOB_QUEUE_AVAILABLE = False
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output_videos"

# 프리셋 설정 (하드코딩)
PRESET = {
    "text_position": "bottom-edge",
    "text_style": "outline",
    "image_allocation_mode": "1_per_image",
    "music_mood": "bright",
    "voice_narration": "enabled",
    "tts_engine": "qwen",
    "qwen_speaker": "Sohee",
    "qwen_speed": "fast",
    "qwen_style": "neutral",
    "cross_dissolve": "disabled",
    "title_area_mode": "keep",
    "title_font_size": 42,
    "body_font_size": 27,
    "title_font": "BMHANNAPro.ttf",
    "body_font": "BMYEONSUNG_otf.otf",
    "video_format": "reels",
    "subtitle_duration": 0.0,
}


def set_dependencies(fm, jq, fm_avail, jq_avail, upload_folder, output_folder):
    """main.py에서 호출하여 의존성 설정"""
    global folder_manager, job_queue
    global FOLDER_MANAGER_AVAILABLE, JOB_QUEUE_AVAILABLE
    global UPLOAD_FOLDER, OUTPUT_FOLDER

    folder_manager = fm
    job_queue = jq
    FOLDER_MANAGER_AVAILABLE = fm_avail
    JOB_QUEUE_AVAILABLE = jq_avail
    UPLOAD_FOLDER = upload_folder
    OUTPUT_FOLDER = output_folder


@router.post("/generate-reels")
async def generate_reels_external(
    content_data: str = Form(...),
    user_email: str = Form(...),

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

    # API Key 인증 헤더
    x_api_key: Optional[str] = Header(None),
):
    """외부 시스템용 릴스 생성 API - 프리셋 옵션 + API Key 인증"""

    # 1. API Key 검증
    expected_api_key = os.getenv("EXTERNAL_API_KEY", "")
    if not expected_api_key:
        logger.error("EXTERNAL_API_KEY 환경변수가 설정되지 않았습니다")
        raise HTTPException(status_code=500, detail="서버 설정 오류: API Key가 구성되지 않았습니다.")

    if not x_api_key or x_api_key != expected_api_key:
        logger.warning(f"인증 실패: 잘못된 API Key (user_email={user_email})")
        raise HTTPException(status_code=401, detail="Unauthorized: 유효하지 않은 API Key입니다.")

    # 2. 작업 시스템 가용성 확인
    if not JOB_QUEUE_AVAILABLE:
        raise HTTPException(status_code=500, detail="배치 작업 시스템이 사용 불가능합니다.")

    logger.info(f"🌐 외부 API 릴스 생성 요청: {user_email}")

    try:
        # 3. Job ID 생성
        job_id = str(uuid.uuid4())
        logger.info(f"🆔 Job ID 생성: {job_id}")

        # 4. Job 폴더 생성
        if FOLDER_MANAGER_AVAILABLE:
            try:
                job_uploads_folder, job_output_folder = folder_manager.create_job_folders(job_id)
                uploads_folder_to_use = job_uploads_folder
                logger.info(f"📁 Job 폴더 생성: {uploads_folder_to_use}")
            except Exception as folder_error:
                logger.warning(f"⚠️ Job 폴더 생성 실패, 기본 폴더 사용: {folder_error}")
                uploads_folder_to_use = UPLOAD_FOLDER
                os.makedirs(uploads_folder_to_use, exist_ok=True)
        else:
            uploads_folder_to_use = UPLOAD_FOLDER
            os.makedirs(uploads_folder_to_use, exist_ok=True)

        # 5. content_data를 text.json으로 저장
        import json
        try:
            content_dict = json.loads(content_data)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"content_data JSON 파싱 오류: {str(e)}")

        json_save_path = os.path.join(uploads_folder_to_use, "text.json")
        with open(json_save_path, 'w', encoding='utf-8') as f:
            json.dump(content_dict, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ content_data 저장: {json_save_path}")

        # 6. 이미지 파일들 저장
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
            ("image_46", image_46), ("image_47", image_47), ("image_48", image_48), ("image_49", image_49), ("image_50", image_50),
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

        logger.info(f"📊 총 {len(saved_files)}개 파일 저장 완료")

        # 7. video_params 구성 (프리셋 값 + 전달받은 content_data 경로)
        logger.info(f"📋 [외부API] PRESET: tts={PRESET['tts_engine']}, pos={PRESET['text_position']}, "
                    f"alloc={PRESET['image_allocation_mode']}, xdissolve={PRESET['cross_dissolve']}")
        video_params = {
            'content_data': content_data,
            'music_mood': PRESET['music_mood'],
            'image_allocation_mode': PRESET['image_allocation_mode'],
            'text_position': PRESET['text_position'],
            'text_style': PRESET['text_style'],
            'title_area_mode': PRESET['title_area_mode'],
            'selected_bgm_path': '',
            'use_test_files': False,
            'uploaded_files': saved_files,
            'title_font': PRESET['title_font'],
            'body_font': PRESET['body_font'],
            'title_font_size': PRESET['title_font_size'],
            'body_font_size': PRESET['body_font_size'],
            'voice_narration': PRESET['voice_narration'],
            'cross_dissolve': PRESET['cross_dissolve'],
            'subtitle_duration': PRESET['subtitle_duration'],
            'edited_texts': '{}',
            'image_panning_options': '{}',
            'tts_engine': PRESET['tts_engine'],
            'qwen_speaker': PRESET['qwen_speaker'],
            'qwen_speed': PRESET['qwen_speed'],
            'qwen_style': PRESET['qwen_style'],
            'per_body_tts_settings': '',
            'edge_speaker': 'female',
            'edge_speed': 'normal',
            'edge_pitch': 'normal',
            'video_format': PRESET['video_format'],
            'source': 'external_api',
        }

        # 8. 작업 큐에 추가
        actual_job_id = job_queue.add_job(user_email, video_params, job_id=job_id)
        logger.info(f"✅ 작업 큐 등록 완료: {actual_job_id}")

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "job_id": actual_job_id,
                "message": "릴스 생성 작업이 접수되었습니다. 완료 시 이메일로 알림됩니다.",
                "email": user_email,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 외부 API 릴스 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=f"릴스 생성 요청 중 오류가 발생했습니다: {str(e)}")
