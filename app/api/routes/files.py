"""File routes with individual use case imports"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from typing import List

from ...application.use_cases.upload_song_images import UploadSongImagesUseCase
from ...api.dependencies import get_current_user, get_unit_of_work, get_storage_service
from ...domain.entities.user import User


router = APIRouter(tags=["files"])


@router.post("/upload/images")
async def upload_images(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    storage_service = Depends(get_storage_service)
):
    """Upload multiple images (general purpose)"""
    try:
        if len(files) > 30:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 30 files allowed"
            )
        
        uploaded_urls = []
        
        for file in files:
            # Validate file type
            if not file.content_type or not file.content_type.startswith('image/'):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File {file.filename} is not an image"
                )
            
            # Read file content
            file_content = await file.read()
            
            # Upload to storage
            file_url = await storage_service.upload_file(
                file_data=file_content,
                filename=file.filename or "unnamed.jpg",
                content_type=file.content_type
            )
            
            uploaded_urls.append({
                "filename": file.filename,
                "url": file_url
            })
        
        return {
            "uploaded_files": uploaded_urls,
            "count": len(uploaded_urls)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload files: {str(e)}"
        )


@router.post("/songs/{song_id}/images")
async def upload_song_images(
    song_id: str,  # Changed from int to str for UUID
    images: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    unit_of_work = Depends(get_unit_of_work),
    storage_service = Depends(get_storage_service)
):
    """Upload images for a song"""
    use_case = UploadSongImagesUseCase(unit_of_work, storage_service)
    return await use_case.execute(song_id, images, current_user.id)


@router.get("/health")
async def files_health():
    """Files health check"""
    return {"status": "ok", "service": "files"}
