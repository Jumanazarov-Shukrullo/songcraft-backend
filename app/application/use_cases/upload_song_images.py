"""Upload song images use case"""

from typing import List
from io import BytesIO

from ...domain.repositories.unit_of_work import IUnitOfWork
from ...infrastructure.external_services.storage_service import StorageService
from ...domain.value_objects.entity_ids import SongId
from fastapi import UploadFile


class UploadSongImagesUseCase:
    
    def __init__(self, unit_of_work: IUnitOfWork, storage_service: StorageService):
        self.unit_of_work = unit_of_work
        self.storage_service = storage_service
    
    async def execute(
        self,
        song_id: str,  # Changed from int to str for UUID
        images: List[UploadFile],
        user_id,
    ) -> List[str]:
        """Upload images for a song and return their URLs

        Parameters
        ----------
        song_id : str
            UUID string of the song that the images belong to.
        images : List[UploadFile]
            The images uploaded from the client (FastAPI UploadFile objects).
        user_id : int | UserId
            Current user – accepted as either plain int or UserId value object.
        """
        async with self.unit_of_work:
            # Fetch the song and verify ownership
            song = await self.unit_of_work.songs.get_by_id(SongId.from_str(song_id))  # Use from_str for UUID string
            if not song:
                raise ValueError("Song not found")

            # Normalize user id to UUID for comparison
            if hasattr(user_id, "value"):
                user_uuid = user_id.value
            else:
                # Convert string/int to UUID
                from ...domain.value_objects.entity_ids import UserId
                user_uuid = UserId.from_str(str(user_id)).value
            
            if song.user_id.value != user_uuid:
                raise ValueError("Not authorized to modify this song")

            uploaded_urls: List[str] = []

            for file in images:
                # Basic validation – only allow image MIME types
                if not file.content_type or not file.content_type.startswith("image/"):
                    raise ValueError(f"{file.filename} is not a valid image file")

                file_bytes = await file.read()

                # Store images in a structured path per-song, e.g. songs/<song_id>/images/
                file_url = await self.storage_service.upload_file(
                    file_data=file_bytes,
                    filename=file.filename or "image.jpg",
                    content_type=file.content_type,
                    prefix=f"songs/{song_id}/images",
                )
                uploaded_urls.append(file_url)

            # Update song with the number of images
            song.set_image_count(song.image_count + len(uploaded_urls))
            await self.unit_of_work.songs.update(song)
            await self.unit_of_work.commit()

            return uploaded_urls 