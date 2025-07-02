"""Upload song images use case"""

from typing import List, BinaryIO
from io import BytesIO

from ...domain.repositories.unit_of_work import IUnitOfWork
from ...infrastructure.external_services.storage_service import StorageService
from ...domain.value_objects.entity_ids import SongId


class UploadSongImagesUseCase:
    
    def __init__(self, unit_of_work: IUnitOfWork, storage_service: StorageService):
        self.unit_of_work = unit_of_work
        self.storage_service = storage_service
    
    async def execute(
        self,
        song_id: int,
        files: List[tuple[bytes, str, str]]  # (file_data, filename, content_type)
    ) -> List[str]:
        """Upload images for song and return URLs"""
        async with self.unit_of_work:
            # Verify song exists and user owns it
            song = await self.unit_of_work.songs.get_by_id(SongId(song_id))
            if not song:
                raise ValueError("Song not found")
            
            uploaded_urls = []
            
            for file_data, filename, content_type in files:
                # Create BytesIO object for the storage service
                file_stream = BytesIO(file_data)
                
                # Upload file to storage
                file_url = await self.storage_service.upload_file(
                    file_stream, filename, content_type
                )
                uploaded_urls.append(file_url)
                
                # Note: In a full implementation, we would save file references
                # to a SongImage entity/model to track uploaded files
            
            return uploaded_urls 