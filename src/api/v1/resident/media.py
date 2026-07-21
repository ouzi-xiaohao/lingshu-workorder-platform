import mimetypes

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response

from src.api.dependencies import current_user
from src.models.user import User
from src.service.media_service import MediaService, MediaValidationError


router = APIRouter()


@router.post("", status_code=201)
async def upload_media(file: UploadFile = File(...), user: User = Depends(current_user)):
    try:
        data = await MediaService().upload(file, user.id)
    except MediaValidationError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"code": "OK", "message": "附件上传成功", "data": data}


@router.get("/{object_key:path}")
async def download_media(object_key: str, user: User = Depends(current_user)):
    if user.role == "resident" and not object_key.startswith(f"users/{user.id}/"):
        raise HTTPException(403, "无权访问此附件")
    try:
        data = MediaService().download(object_key)
    except (FileNotFoundError, ValueError):
        raise HTTPException(404, "附件不存在") from None
    content_type = mimetypes.guess_type(object_key)[0] or "application/octet-stream"
    return Response(data, media_type=content_type, headers={"Cache-Control": "private, max-age=3600"})
