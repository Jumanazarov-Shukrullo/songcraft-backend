import asyncio
from app.db.database import get_session
from app.infrastructure.repositories.song_repository_impl import SongRepositoryImpl
from app.domain.value_objects.entity_ids import SongId

async def check_song_status():
    async with get_session() as session:
        repo = SongRepositoryImpl(session)
        song = await repo.get_by_id(SongId(19))
        if song:
            print(f'Song ID: {song.id.value}')
            print(f'Title: {song.title}')
            print(f'Audio Status: {song.audio_status.value}')
            print(f'Audio URL: {song.audio_url.url if song.audio_url else None}')
            print(f'Generation Status: {song.generation_status.value}')
            print(f'Updated At: {song.updated_at}')
        else:
            print('Song not found')

if __name__ == "__main__":
    asyncio.run(check_song_status()) 