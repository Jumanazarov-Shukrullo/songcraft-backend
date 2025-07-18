"""Telegram Bot specific endpoints"""

from fastapi import APIRouter, Header, HTTPException, status, Depends
from typing import Optional
import logging

from ...core.config import settings
from ...application.dtos.song_dtos import CreateSongRequest, SongResponse
from ...infrastructure.external_services.ai_service import AIService
from ...infrastructure.repositories.unit_of_work_impl import UnitOfWorkImpl
from ...db.database import SessionLocal  # type: ignore
from ...application.use_cases.create_song import CreateSongUseCase
from ...infrastructure.orm.user_model import UserModel  # type: ignore
from ...infrastructure.orm.song_model import SongModel  # type: ignore
from ...api.dependencies import get_ai_service
from ...core.security import get_password_hash
from ...domain.enums import UserStatus, UserRole

router = APIRouter()

logger = logging.getLogger("bot.routes")


async def verify_bot_key(x_bot_key: Optional[str] = Header(None)):
    # Debug log to trace mismatched keys
    if x_bot_key != settings.BOT_API_KEY:
        logger.warning("Invalid bot key: received %s, expected %s", x_bot_key, settings.BOT_API_KEY)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bot API key")


@router.post("/create-song", response_model=SongResponse, dependencies=[Depends(verify_bot_key)])
async def create_song_for_bot(
    req: CreateSongRequest,
    telegram_id: int = Header(..., alias="X-Telegram-Id"),
):
    """Create a song on behalf of a Telegram user.

    The bot must supply:
    • `X-Bot-Key` header – shared secret (handled by dependency)
    • `X-Telegram-Id` header – unique Telegram user ID (int)
    Body must conform to CreateSongRequest (story / style / etc.).
    The endpoint auto-creates a free order and returns the SongResponse.
    """
    session = SessionLocal()
    # ------------------------------------------------------------------
    # Map Telegram ID → internal user ----------------------------------
    # ------------------------------------------------------------------
    try:
        # Use deterministic email to find / create user
        tg_email = f"tg-{telegram_id}@bot.lyrzy"
        user = session.query(UserModel).filter(UserModel.email == tg_email).first()
        if not user:
            user = UserModel(
                email=tg_email,
                hashed_password=get_password_hash("telegram-bot"),
                first_name="TG",
                last_name=str(telegram_id),
                status=UserStatus.ACTIVE,
                role=UserRole.USER,
                email_verified=True,
            )
            session.add(user)
            session.flush()  # assign primary key

        internal_user_id = user.id
    except Exception:
        session.rollback()
        raise

    # ------------------------------------------------------------------
    # Song creation
    # ------------------------------------------------------------------
    uow = UnitOfWorkImpl(session)
    ai_service = AIService()
    try:
        use_case = CreateSongUseCase(uow, ai_service)
        # Convert UUID to string for the use case
        user_id_str = str(internal_user_id)
        song_resp = await use_case.execute(req, user_id=user_id_str)
        return song_resp
    finally:
        session.close()


# -----------------------------------------------------------------------------
# Stats endpoint for bot admin panel
# -----------------------------------------------------------------------------


@router.get("/stats", dependencies=[Depends(verify_bot_key)])
async def bot_stats():
    """Return basic counts for Telegram admin command (/stats)."""
    session = SessionLocal()
    try:
        user_cnt = session.query(UserModel).count()
        song_cnt = session.query(SongModel).count()
    finally:
        session.close()
    return {"users": user_cnt, "songs": song_cnt}


# -----------------------------------------------------------------------------
# Lyrics generation & improvement for step-wise bot process
# -----------------------------------------------------------------------------


@router.post("/generate-lyrics", dependencies=[Depends(verify_bot_key)])
async def bot_generate_lyrics(
    payload: dict,
    ai_service = Depends(get_ai_service),
):
    """Generate lyrics without creating a song yet."""
    description = payload.get("description") or payload.get("story")
    music_style = payload.get("music_style") or payload.get("style")
    if not description or not music_style:
        raise HTTPException(status_code=400, detail="description and music_style required")
    lyrics = await ai_service.generate_lyrics(description=description, music_style=music_style)
    return {"lyrics": lyrics}


@router.post("/improve-lyrics", dependencies=[Depends(verify_bot_key)])
async def bot_improve_lyrics(
    payload: dict,
    ai_service = Depends(get_ai_service),
):
    """Improve existing lyrics based on feedback."""
    lyrics = payload.get("lyrics")
    feedback = payload.get("feedback")
    if not lyrics or not feedback:
        raise HTTPException(status_code=400, detail="lyrics and feedback required")
    improved = await ai_service.improve_lyrics(lyrics, feedback)
    return {"lyrics": improved} 