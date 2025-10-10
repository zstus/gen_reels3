"""
이미지 생성 라우터
AI 이미지 자동 생성 API (DALL-E)
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from utils.logger_config import get_logger
from models.request_models import SingleImageRequest, ImageGenerateRequest
from typing import Optional, List
import os
import uuid
import asyncio

router = APIRouter(tags=["image"])
logger = get_logger('image_router')

# 전역 변수 (main.py에서 설정)
OPENAI_AVAILABLE = False
OPENAI_API_KEY = None
folder_manager = None
FOLDER_MANAGER_AVAILABLE = False
UPLOAD_FOLDER = "uploads"
OpenAI = None


def set_dependencies(openai_avail, openai_key, fm, fm_avail, upload_folder, openai_class):
    """main.py에서 호출하여 의존성 설정"""
    global OPENAI_AVAILABLE, OPENAI_API_KEY, folder_manager
    global FOLDER_MANAGER_AVAILABLE, UPLOAD_FOLDER, OpenAI
    OPENAI_AVAILABLE = openai_avail
    OPENAI_API_KEY = openai_key
    folder_manager = fm
    FOLDER_MANAGER_AVAILABLE = fm_avail
    UPLOAD_FOLDER = upload_folder
    OpenAI = openai_class


def create_image_generation_prompt(text: str, additional_context: Optional[str] = None) -> str:
    """텍스트 기반 이미지 생성 프롬프트 생성"""

    # 실사풍 기본 프롬프트 구성
    base_prompt = f"""
Create a photorealistic digital painting with soft, natural lighting and seamless blending based on this Korean text: "{text}"

The image should have:
- No visible outlines or hard edges between objects
- Natural shadows and highlights
- Realistic textures and materials
- Soft gradients and smooth color transitions
- Professional photography-like composition
- Warm, ambient lighting
- High detail and depth
- Suitable for vertical video format (9:16 aspect ratio content)
- Safe for all audiences
"""

    # 추가 컨텍스트가 있으면 포함
    if additional_context:
        base_prompt += f"\nAdditional context: \"{additional_context}\""

    base_prompt += """

Style: Digital painting, photorealistic, cinematic lighting, professional photography aesthetic
Quality: High resolution, sharp details, realistic depth of field
Mood: Natural, engaging, appropriate for social media
Avoid: Vector graphics, line art, cartoon style, bold outlines, flat colors, text, letters, words, typography, captions, labels, any written content
"""

    return base_prompt.strip()


def create_safe_image_prompt(text: str, additional_context: Optional[str] = None) -> str:
    """안전 정책 위반을 피하기 위한 안전화된 프롬프트 생성"""

    # 폭력적/위험한 표현들을 안전한 표현으로 대체
    safe_text = text.replace("때리", "터치").replace("때린", "터치").replace("펀치", "움직임")
    safe_text = safe_text.replace("타격", "접촉").replace("공격", "동작").replace("폭발", "반응")
    safe_text = safe_text.replace("충격", "에너지").replace("파괴", "변화").replace("깨", "변형")

    if additional_context:
        safe_additional = additional_context.replace("때리", "터치").replace("때린", "터치").replace("펀치", "움직임")
        safe_additional = safe_additional.replace("타격", "접촉").replace("공격", "동작").replace("폭발", "반응")
    else:
        safe_additional = None

    # 매우 안전한 프롬프트 구성
    base_prompt = f"""
Create a peaceful, educational illustration about marine life and science based on this Korean text: "{safe_text}"

The image should be:
- Educational and informative
- Bright, colorful, and family-friendly
- Featuring marine creatures in their natural habitat
- Scientific and nature-focused
- Suitable for educational content
- Completely safe for all audiences

Focus on:
- Beautiful ocean scenes
- Colorful marine life
- Scientific concepts visualization
- Peaceful underwater environments
"""

    if safe_additional:
        base_prompt += f"\nAdditional educational context: \"{safe_additional}\""

    base_prompt += """

Style: Educational illustration, nature documentary style
Quality: High resolution, sharp details
Mood: Peaceful, educational, wonder and discovery
No violence, conflict, or aggressive themes
"""

    return base_prompt.strip()


async def generate_images_with_dalle(texts: List[str], job_id: Optional[str] = None) -> List[str]:
    """DALL-E를 사용하여 이미지 생성하고 로컬에 저장 (병렬 처리)"""
    import requests

    # aiohttp 사용 가능 여부 확인
    try:
        import aiohttp
        AIOHTTP_AVAILABLE = True
    except Exception:
        AIOHTTP_AVAILABLE = False

    if not AIOHTTP_AVAILABLE:
        logger.warning("aiohttp가 설치되지 않아 순차 처리로 대체합니다.")
        return await generate_images_with_dalle_sequential(texts, job_id)

    try:
        if not OPENAI_API_KEY:
            raise ValueError("OpenAI API 키가 설정되지 않았습니다.")

        logger.info(f"🚀 병렬 DALL-E 이미지 생성 시작: {len(texts)}개")

        # OpenAI 클라이언트 초기화
        client = OpenAI(api_key=OPENAI_API_KEY, timeout=60.0)

        # uploads 디렉토리 설정
        if job_id and FOLDER_MANAGER_AVAILABLE:
            try:
                job_uploads_folder, _ = folder_manager.get_job_folders(job_id)
                uploads_dir = job_uploads_folder
                os.makedirs(uploads_dir, exist_ok=True)
                logger.info(f"🗂️ Job 고유 폴더 사용: {uploads_dir}")
            except Exception as job_error:
                logger.warning(f"⚠️ Job 폴더 사용 실패, 기본 폴더 사용: {job_error}")
                uploads_dir = UPLOAD_FOLDER
                os.makedirs(uploads_dir, exist_ok=True)
        else:
            uploads_dir = UPLOAD_FOLDER
            os.makedirs(uploads_dir, exist_ok=True)

        async def generate_single_image(i: int, text: str) -> str:
            """단일 이미지 생성 함수"""
            try:
                logger.info(f"📸 이미지 {i+1}/{len(texts)} 생성 시작: {text[:30]}...")

                prompt = create_image_generation_prompt(text)
                logger.info(f"🎯 이미지 {i+1} 프롬프트 생성 완료")

                # DALL-E API 호출
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: client.images.generate(
                        model="dall-e-3",
                        prompt=prompt,
                        size="1024x1024",
                        quality="standard",
                        n=1,
                    ),
                )

                # 이미지 URL 추출
                image_url = response.data[0].url
                logger.info(f"✅ 이미지 {i+1} 생성 완료, 다운로드 중...")

                # 비동기 이미지 다운로드
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                    async with session.get(image_url) as img_response:
                        if img_response.status == 200:
                            filename = f"generated_{uuid.uuid4().hex[:8]}_{i+1}.png"
                            file_path = os.path.join(uploads_dir, filename)
                            with open(file_path, "wb") as f:
                                f.write(await img_response.read())

                            # Job ID에 따라 URL 경로 설정
                            if job_id and FOLDER_MANAGER_AVAILABLE:
                                image_url_path = f"/job-uploads/{job_id}/{filename}"
                            else:
                                image_url_path = f"/get-image/{filename}"

                            logger.info(f"💾 이미지 {i+1} 저장 완료: {filename}")
                            return image_url_path
                        else:
                            logger.error(f"❌ 이미지 {i+1} 다운로드 실패: HTTP {img_response.status}")
                            return ""

            except Exception as e:
                logger.error(f"💥 이미지 {i+1} 처리 실패: {e}")

                # 콘텐츠 필터링 에러인 경우 재시도
                if "content_policy_violation" in str(e).lower():
                    logger.info(f"🔄 이미지 {i+1} 콘텐츠 필터링으로 인한 재시도 중...")
                    try:
                        retry_prompt = create_safe_image_prompt(text)
                        loop = asyncio.get_event_loop()
                        retry_response = await loop.run_in_executor(
                            None,
                            lambda: client.images.generate(
                                model="dall-e-3",
                                prompt=retry_prompt,
                                size="1024x1024",
                                quality="standard",
                                n=1,
                            ),
                        )

                        retry_image_url = retry_response.data[0].url
                        logger.info(f"🔄 이미지 {i+1} 재시도 성공, 다운로드 중...")

                        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                            async with session.get(retry_image_url) as retry_img_response:
                                if retry_img_response.status == 200:
                                    retry_filename = f"generated_{uuid.uuid4().hex[:8]}_{i+1}_retry.png"
                                    retry_file_path = os.path.join(uploads_dir, retry_filename)
                                    with open(retry_file_path, "wb") as f:
                                        f.write(await retry_img_response.read())

                                    # Job ID에 따라 URL 경로 설정 (재시도도 동일하게)
                                    if job_id and FOLDER_MANAGER_AVAILABLE:
                                        retry_image_url_path = f"/job-uploads/{job_id}/{retry_filename}"
                                    else:
                                        retry_image_url_path = f"/get-image/{retry_filename}"

                                    logger.info(f"💾 이미지 {i+1} 재시도 저장 완료: {retry_filename}")
                                    return retry_image_url_path
                                else:
                                    logger.error(f"❌ 이미지 {i+1} 재시도 다운로드 실패: HTTP {retry_img_response.status}")
                                    return ""
                    except Exception as retry_e:
                        logger.error(f"💥 이미지 {i+1} 재시도 실패: {retry_e}")
                        return ""
                else:
                    return ""

        # 병렬 처리로 모든 이미지 동시 생성
        logger.info(f"⚡ {len(texts)}개 이미지를 병렬로 처리 시작...")
        tasks = [generate_single_image(i, text) for i, text in enumerate(texts)]
        generated_image_paths = await asyncio.gather(*tasks)

        success_count = sum(1 for path in generated_image_paths if path)
        logger.info(f"🎉 병렬 DALL-E 이미지 생성 완료: {success_count}/{len(texts)}개 성공")

        return generated_image_paths

    except Exception as e:
        logger.error(f"DALL-E API 오류: {e}")
        raise ValueError(f"이미지 생성에 실패했습니다: {str(e)}")


async def generate_images_with_dalle_sequential(texts: List[str], job_id: Optional[str] = None) -> List[str]:
    """DALL-E를 사용하여 이미지 생성하고 로컬에 저장 (순차 처리 fallback)"""
    import requests

    try:
        if not OPENAI_API_KEY:
            raise ValueError("OpenAI API 키가 설정되지 않았습니다.")

        logger.info(f"🔄 순차 DALL-E 이미지 생성 시작: {len(texts)}개")

        # OpenAI 클라이언트 초기화
        client = OpenAI(api_key=OPENAI_API_KEY, timeout=60.0)

        # uploads 디렉토리 설정
        if job_id and FOLDER_MANAGER_AVAILABLE:
            try:
                job_uploads_folder, _ = folder_manager.get_job_folders(job_id)
                uploads_dir = job_uploads_folder
                os.makedirs(uploads_dir, exist_ok=True)
                logger.info(f"🗂️ Job 고유 폴더 사용: {uploads_dir}")
            except Exception as job_error:
                logger.warning(f"⚠️ Job 폴더 사용 실패, 기본 폴더 사용: {job_error}")
                uploads_dir = UPLOAD_FOLDER
                os.makedirs(uploads_dir, exist_ok=True)
        else:
            uploads_dir = UPLOAD_FOLDER
            os.makedirs(uploads_dir, exist_ok=True)

        generated_image_paths: List[str] = []

        for i, text in enumerate(texts):
            try:
                logger.info(f"📸 이미지 {i+1}/{len(texts)} 생성 시작: {text[:30]}...")

                prompt = create_image_generation_prompt(text)
                logger.info(f"🎯 이미지 {i+1} 프롬프트 생성 완료")

                # DALL-E API 호출
                response = client.images.generate(
                    model="dall-e-3",
                    prompt=prompt,
                    size="1024x1024",
                    quality="standard",
                    n=1,
                )

                image_url = response.data[0].url
                logger.info(f"✅ 이미지 {i+1} 생성 완료, 다운로드 중...")

                # 이미지 다운로드
                img_response = requests.get(image_url, timeout=30)
                img_response.raise_for_status()

                filename = f"generated_{uuid.uuid4().hex[:8]}_{i+1}.png"
                file_path = os.path.join(uploads_dir, filename)

                with open(file_path, "wb") as f:
                    f.write(img_response.content)

                # Job ID에 따라 URL 경로 설정
                if job_id and FOLDER_MANAGER_AVAILABLE:
                    image_url_path = f"/job-uploads/{job_id}/{filename}"
                else:
                    image_url_path = f"/get-image/{filename}"

                logger.info(f"💾 이미지 {i+1} 저장 완료: {filename}")
                generated_image_paths.append(image_url_path)

            except Exception as e:
                logger.error(f"💥 이미지 {i+1} 처리 실패: {e}")

                # 콘텐츠 필터링 에러인 경우 재시도
                if "content_policy_violation" in str(e).lower():
                    logger.info(f"🔄 이미지 {i+1} 콘텐츠 필터링으로 인한 재시도 중...")
                    try:
                        retry_prompt = create_safe_image_prompt(text)
                        retry_response = client.images.generate(
                            model="dall-e-3",
                            prompt=retry_prompt,
                            size="1024x1024",
                            quality="standard",
                            n=1,
                        )

                        retry_image_url = retry_response.data[0].url
                        logger.info(f"🔄 이미지 {i+1} 재시도 성공, 다운로드 중...")

                        retry_img_response = requests.get(retry_image_url, timeout=30)
                        retry_img_response.raise_for_status()

                        retry_filename = f"generated_{uuid.uuid4().hex[:8]}_{i+1}_retry.png"
                        retry_file_path = os.path.join(uploads_dir, retry_filename)

                        with open(retry_file_path, "wb") as f:
                            f.write(retry_img_response.content)

                        # Job ID에 따라 URL 경로 설정 (재시도도 동일하게)
                        if job_id and FOLDER_MANAGER_AVAILABLE:
                            retry_image_url_path = f"/job-uploads/{job_id}/{retry_filename}"
                        else:
                            retry_image_url_path = f"/get-image/{retry_filename}"

                        logger.info(f"💾 이미지 {i+1} 재시도 저장 완료: {retry_filename}")
                        generated_image_paths.append(retry_image_url_path)

                    except Exception as retry_e:
                        logger.error(f"💥 이미지 {i+1} 재시도 실패: {retry_e}")
                        generated_image_paths.append("")
                else:
                    generated_image_paths.append("")

        success_count = sum(1 for path in generated_image_paths if path)
        logger.info(f"✅ 순차 DALL-E 이미지 생성 완료: {success_count}/{len(texts)}개 성공")

        return generated_image_paths

    except Exception as e:
        logger.error(f"DALL-E API 오류: {e}")
        raise ValueError(f"이미지 생성에 실패했습니다: {str(e)}")


@router.post("/generate-single-image")
async def generate_single_image(request: SingleImageRequest):
    """개별 텍스트에 대한 이미지 자동 생성 (커스텀 프롬프트 지원)"""
    try:
        logger.info(f"🔥 개별 이미지 생성 요청 시작")
        logger.info(f"📝 요청 텍스트: {request.text}")
        logger.info(f"🎨 커스텀 프롬프트: {request.custom_prompt}")
        logger.info(f"📝 추가 컨텍스트: {request.additional_context}")

        # 입력 유효성 검증
        if not request.text and not request.custom_prompt:
            logger.error("❌ 텍스트 또는 커스텀 프롬프트 중 하나는 필수입니다")
            raise HTTPException(status_code=400, detail="텍스트 또는 커스텀 프롬프트 중 하나는 필수입니다")

        if not OPENAI_AVAILABLE:
            logger.error("❌ OpenAI 라이브러리가 설치되지 않음")
            raise HTTPException(status_code=500, detail="OpenAI 라이브러리가 설치되지 않았습니다")

        if not OPENAI_API_KEY:
            logger.error("❌ OpenAI API 키가 설정되지 않음")
            raise HTTPException(status_code=500, detail="OpenAI API 키가 설정되지 않았습니다")

        logger.info("🔑 OpenAI API 키 확인 완료")

        # 이미지 생성용 프롬프트 선택
        if request.custom_prompt and request.custom_prompt.strip():
            # 커스텀 프롬프트 사용
            image_prompt = request.custom_prompt.strip()
            logger.info(f"🎨 커스텀 프롬프트 사용: {image_prompt[:200]}...")
        else:
            # 기존 텍스트 기반 프롬프트 생성
            image_prompt = create_image_generation_prompt(request.text, request.additional_context)
            logger.info(f"🎯 기본 텍스트 기반 프롬프트: {image_prompt[:200]}...")

        # OpenAI DALL-E를 통한 이미지 생성
        client = OpenAI(api_key=OPENAI_API_KEY, timeout=30.0)
        logger.info("🤖 DALL-E API 호출 시작...")

        try:
            response = client.images.generate(
                model="dall-e-3",
                prompt=image_prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )
            logger.info("✅ DALL-E API 호출 성공")
        except Exception as dalle_error:
            logger.error(f"💥 DALL-E API 호출 실패: {dalle_error}")
            # 프롬프트 안전화 시도
            if "safety system" in str(dalle_error) or "content_policy_violation" in str(dalle_error):
                logger.info("🛡️ 안전 정책 위반 감지 - 프롬프트 안전화 시도")

                if request.custom_prompt and request.custom_prompt.strip():
                    # 커스텀 프롬프트의 경우 기본 안전한 프롬프트로 대체
                    safe_prompt = "A peaceful and beautiful landscape with soft colors, professional photography style"
                    logger.info(f"🔒 커스텀 프롬프트 안전화: {safe_prompt}")
                else:
                    # 기존 텍스트 기반 안전화
                    safe_prompt = create_safe_image_prompt(request.text, request.additional_context)
                    logger.info(f"🔒 텍스트 기반 안전화: {safe_prompt[:200]}...")

                response = client.images.generate(
                    model="dall-e-3",
                    prompt=safe_prompt,
                    size="1024x1024",
                    quality="standard",
                    n=1,
                )
                logger.info("✅ 안전화된 프롬프트로 성공")
            else:
                raise dalle_error

        image_url = response.data[0].url
        logger.info(f"🌐 이미지 URL 수신: {image_url}")

        # 생성된 이미지 다운로드 및 저장
        import requests
        from datetime import datetime

        logger.info("📥 이미지 다운로드 시작...")
        image_response = requests.get(image_url, timeout=30)
        image_response.raise_for_status()
        logger.info(f"📥 이미지 다운로드 완료 ({len(image_response.content)} bytes)")

        # Job 폴더 또는 기본 uploads 폴더에 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"generated_single_{timestamp}_{uuid.uuid4().hex[:8]}.png"

        if request.job_id and FOLDER_MANAGER_AVAILABLE:
            # Job 고유 폴더에 저장
            try:
                job_uploads_folder, _ = folder_manager.get_job_folders(request.job_id)
                os.makedirs(job_uploads_folder, exist_ok=True)
                local_path = os.path.join(job_uploads_folder, filename)

                with open(local_path, 'wb') as f:
                    f.write(image_response.content)

                logger.info(f"💾 개별 이미지 job 폴더 저장 완료: {filename}")
                logger.info(f"📂 Job 경로: {local_path}")

                # job_id가 있는 경우 job별 URL 반환
                return {
                    "status": "success",
                    "message": "이미지가 성공적으로 생성되었습니다",
                    "image_url": f"/job-uploads/{request.job_id}/{filename}",
                    "local_path": local_path,
                    "job_id": request.job_id
                }

            except Exception as job_error:
                logger.warning(f"⚠️ Job 폴더 저장 실패, 기본 폴더 사용: {job_error}")

        # 기본 uploads 폴더에 저장
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        local_path = os.path.join(UPLOAD_FOLDER, filename)

        with open(local_path, 'wb') as f:
            f.write(image_response.content)

        logger.info(f"💾 개별 이미지 기본 폴더 저장 완료: {filename}")
        logger.info(f"📂 로컬 경로: {local_path}")

        return {
            "status": "success",
            "message": "이미지가 성공적으로 생성되었습니다",
            "image_url": f"/uploads/{filename}",
            "local_path": local_path
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 개별 이미지 생성 치명적 오류: {e}")
        logger.error(f"🔍 오류 타입: {type(e).__name__}")
        raise HTTPException(status_code=500, detail=f"이미지 생성 실패: {str(e)}")


@router.post("/generate-images")
async def generate_images(request: ImageGenerateRequest):
    """텍스트 기반 이미지 자동 생성"""
    try:
        logger.info(f"이미지 생성 요청: {len(request.texts)}개 텍스트")

        # 텍스트 검증
        if not request.texts or len(request.texts) == 0:
            raise HTTPException(status_code=400, detail="생성할 텍스트가 필요합니다.")

        # 모드에 따른 텍스트 처리
        if request.mode == "per_two_scripts":
            # 2개씩 묶어서 처리
            processed_texts = []
            for i in range(0, len(request.texts), 2):
                combined_text = request.texts[i]
                if i + 1 < len(request.texts):
                    combined_text += f" {request.texts[i + 1]}"
                processed_texts.append(combined_text)
        else:
            # 각각 개별 처리
            processed_texts = request.texts

        # DALL-E로 이미지 생성
        try:
            image_urls = await generate_images_with_dalle(processed_texts, request.job_id)
        except ValueError as e:
            raise HTTPException(status_code=500, detail=str(e))

        return JSONResponse(
            content={
                "status": "success",
                "message": f"{len([url for url in image_urls if url])}개 이미지가 생성되었습니다.",
                "image_urls": image_urls
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"이미지 생성 중 예외 발생: {e}")
        raise HTTPException(status_code=500, detail="이미지 생성 중 오류가 발생했습니다.")


@router.get("/get-image/{filename}")
async def get_image(filename: str):
    """생성된 이미지 파일 서빙"""
    try:
        file_path = os.path.join(UPLOAD_FOLDER, filename)

        # 파일 존재 여부 확인
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="이미지 파일을 찾을 수 없습니다.")

        # 보안을 위해 파일명 검증
        if not filename.startswith("generated_") or not filename.endswith(".png"):
            raise HTTPException(status_code=403, detail="접근이 허용되지 않은 파일입니다.")

        return FileResponse(
            path=file_path,
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=3600"}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"이미지 파일 서빙 오류: {e}")
        raise HTTPException(status_code=500, detail="이미지 파일을 읽을 수 없습니다.")


@router.get("/download-image/{filename}")
async def download_image(filename: str):
    """생성된 이미지 파일 다운로드"""
    try:
        file_path = os.path.join(UPLOAD_FOLDER, filename)

        # 파일 존재 여부 확인
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="이미지 파일을 찾을 수 없습니다.")

        # 보안을 위해 파일명 검증
        if not filename.startswith("generated_") or not filename.endswith(".png"):
            raise HTTPException(status_code=403, detail="접근이 허용되지 않은 파일입니다.")

        # 더 친화적인 파일명 생성
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        download_filename = f"reels_image_{timestamp}.png"

        return FileResponse(
            path=file_path,
            media_type="image/png",
            filename=download_filename,
            headers={
                "Content-Disposition": f"attachment; filename={download_filename}",
                "Cache-Control": "no-cache"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"이미지 다운로드 오류: {e}")
        raise HTTPException(status_code=500, detail="이미지 다운로드 중 오류가 발생했습니다.")
