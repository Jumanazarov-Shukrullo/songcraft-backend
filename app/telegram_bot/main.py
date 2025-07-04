"""SongCraft Telegram Bot (aiogram 3.x)
-------------------------------------------------
Async, scalable Telegram bot that lets users create personalized songs via
conversation.  Designed to handle many concurrent users thanks to aiogram's
non-blocking architecture.

Key features
• /start – greeting
• /create – guided flow (ask description ➜ music style)
• Background task triggers existing CreateSongUseCase (free order)
• Admin commands (IDs listed in TELEGRAM_ADMIN_IDS env var):
  – /stats  – quick usage statistics
  – /broadcast <msg> – send announcement to all users (simple demo)

Scaling notes
• aiogram is fully async – heavy IO (LLM / Suno) already async via HTTPX.
• Long-running song generation runs in `asyncio.create_task`, keeping chat
  handlers responsive while work continues.
• The bot stores minimal per-chat FSM state in memory; business data persists
  to DB, so bot restarts are safe.
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections import defaultdict
from typing import Final, List, Dict

from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from aiogram.utils.markdown import hitalic, hbold
from aiogram.enums import ChatAction

import httpx
from ..domain.enums import MusicStyle, EmotionalTone
from dotenv import load_dotenv

# Load environment variables from .env file if present (root directory).
load_dotenv()  # will look for .env in current and parent dirs

# ---------------------------------------------------------------------------
# Configuration ----------------------------------------------------------------
# ---------------------------------------------------------------------------
BOT_TOKEN: Final[str] = os.getenv("TELEGRAM_BOT_TOKEN", "")
if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN env var not set")

ADMIN_IDS: List[int] = [int(uid) for uid in os.getenv("TELEGRAM_ADMIN_IDS", "").split(",") if uid.strip()]

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("songcraft.bot")

# ---------------------------------------------------------------------------
# State Machine ----------------------------------------------------------------
# ---------------------------------------------------------------------------
class SongCreation(StatesGroup):
    waiting_recipient: State = State()
    waiting_occasion: State = State()
    waiting_additional: State = State()
    waiting_style: State = State()
    generating_lyrics: State = State()
    reviewing_lyrics: State = State()
    waiting_feedback: State = State()
    waiting_product: State = State()
    waiting_tone: State = State()
    # Further steps (photos, product, etc.) will be added later

# ---------------------------------------------------------------------------
# Routers ----------------------------------------------------------------------
# ---------------------------------------------------------------------------
user_router = Router()
admin_router = Router()

# Store chat-specific generation tasks so we can track progress
active_jobs: Dict[int, asyncio.Task] = {}

# Simple in-memory broadcast list (persist if you need durability)
known_user_ids: set[int] = set()

# ---------------------------------------------------------------------------
# Helpers ----------------------------------------------------------------------
# ---------------------------------------------------------------------------

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def create_song_for_user(chat_id: int, description: str, style_text: str, bot: Bot, lyrics: str | None = None, tone: str | None = None):
    """Call backend API to create a song and notify user when done."""
    backend_url = os.getenv("BACKEND_API_URL", "http://localhost:8000/api/v1")
    payload = {
        "story": description,
        "style": style_text,
    }
    if lyrics:
        payload["lyrics"] = lyrics
    if tone:
        payload["tone"] = tone
    headers = {
        "X-Bot-Key": os.getenv("BOT_API_KEY", ""),
        "X-Telegram-Id": str(chat_id),
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            resp = await client.post(f"{backend_url}/bot/create-song", json=payload, headers=headers)
            if resp.status_code != 200:
                raise RuntimeError(f"Backend error {resp.status_code}: {resp.text[:200]}")
            data = resp.json()

        msg = (
            f"{hbold('Your song is ready!')}\n"
            f"Title: {hitalic(data.get('title') or 'Untitled')}\n\n"
            f"{hbold('Lyrics')}\n{data.get('lyrics') or '—'}\n\n"
            f"Listen: {data.get('audio_url') or 'Audio still processing…'}"
        )
        await bot.send_message(chat_id, msg)
    except Exception as exc:
        logger.exception("Song generation failed: %s", exc)
        await bot.send_message(chat_id, f"❌ Sorry, something went wrong: {exc}")
    finally:
        active_jobs.pop(chat_id, None)


# ---------------------------------------------------------------------------
# Helper: continuous typing action
# ---------------------------------------------------------------------------


async def _send_typing(bot: Bot, chat_id: int, stop_event: asyncio.Event):
    """Continuously send 'typing' chat action until stop_event is set."""
    try:
        while not stop_event.is_set():
            await bot.send_chat_action(chat_id, ChatAction.TYPING)
            await asyncio.sleep(4)
    except asyncio.CancelledError:
        pass


# ---------------------------------------------------------------------------
# User Command Handlers --------------------------------------------------------
# ---------------------------------------------------------------------------
@user_router.message(Command("start"))
async def cmd_start(message: Message):
    known_user_ids.add(message.from_user.id)
    await message.answer(
        "🎵 <b>Welcome to SongCraft!</b>\n"
        "I can craft personalized songs for you.\n"
        "Send /create to get started.",
        parse_mode="HTML",
    )


@user_router.message(Command("create"))
async def cmd_create(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🎼 Let's craft a song! First, who is this song for? (e.g., my dad, best friend Sarah)"
        "\nYou can cancel anytime with /cancel.")
    await state.set_state(SongCreation.waiting_recipient)


# Step 1: Recipient
@user_router.message(SongCreation.waiting_recipient)
async def recipient_received(message: Message, state: FSMContext):
    recipient = message.text.strip()
    await state.update_data(recipient_description=recipient)
    await message.answer("Great! What's the occasion? (e.g., birthday, anniversary, just because)")
    await state.set_state(SongCreation.waiting_occasion)


# Step 1b: Occasion
@user_router.message(SongCreation.waiting_occasion)
async def occasion_received(message: Message, state: FSMContext):
    occasion = message.text.strip()
    await state.update_data(occasion_description=occasion)
    await message.answer("Any additional details or memories to include? If none, type 'skip'.")
    await state.set_state(SongCreation.waiting_additional)


# Step 1c: Additional details
@user_router.message(SongCreation.waiting_additional)
async def additional_received(message: Message, state: FSMContext):
    text = message.text.strip()
    additional = "" if text.lower() == "skip" else text
    await state.update_data(additional_details=additional)

    # Ask for style
    kb = [[types.KeyboardButton(text=stype.value)] for stype in MusicStyle]
    await message.answer(
        "Choose a music style:",
        reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, one_time_keyboard=True),
    )
    await state.set_state(SongCreation.waiting_style)


@user_router.message(SongCreation.waiting_style)
async def style_received(message: Message, state: FSMContext, bot: Bot):
    user_data = await state.get_data()
    recipient = user_data.get("recipient_description")
    occasion = user_data.get("occasion_description")
    additional = user_data.get("additional_details", "")

    style_text = message.text.strip()
    if style_text not in [s.value for s in MusicStyle]:
        style_text = MusicStyle.POP.value

    # Build story/description string same as frontend
    description = f"Recipient: {recipient}\nOccasion: {occasion}"
    if additional:
        description += f"\nAdditional details: {additional}"

    chat_id = message.chat.id

    await state.update_data(music_style=style_text, full_story=description)

    # Remove keyboard and notify user
    await message.answer("🎤 Generating initial lyrics… please wait.", reply_markup=types.ReplyKeyboardRemove())

    # Call backend generate-lyrics endpoint
    backend_url = os.getenv("BACKEND_API_URL", "http://localhost:8000/api/v1")
    payload = {
        "description": description,
        "music_style": style_text,
    }
    headers = {"X-Bot-Key": os.getenv("BOT_API_KEY", "")}

    async def do_generate():
        stop_event = asyncio.Event()
        typing_task = asyncio.create_task(_send_typing(bot, chat_id, stop_event))
        progress_msg = await bot.send_message(chat_id, "🔧 Analyzing your story and musical style…")

        try:
            async with httpx.AsyncClient(timeout=600.0) as client:
                resp = await client.post(f"{backend_url}/bot/generate-lyrics", json=payload, headers=headers)
                if resp.status_code != 200:
                    raise RuntimeError(f"Backend error {resp.status_code}: {resp.text[:200]}")
                lyrics = resp.json().get("lyrics", "")
                if not lyrics:
                    raise RuntimeError("No lyrics received from backend")

            await state.update_data(lyrics=lyrics)

            stop_event.set()
            await typing_task

            await bot.edit_message_text("🎼 Lyrics generated!", chat_id=chat_id, message_id=progress_msg.message_id)

            # Ask user to pick an emotional tone before further refinement
            tone_kb = [[types.KeyboardButton(text=tone.value)] for tone in EmotionalTone]
            await bot.send_message(
                chat_id,
                f"Here are your lyrics:\n\n{lyrics}\n\nNow choose an emotional tone (optional) to refine the mood:",
                reply_markup=types.ReplyKeyboardMarkup(keyboard=tone_kb, resize_keyboard=True, one_time_keyboard=True),
            )
            await state.set_state(SongCreation.waiting_tone)
        except Exception as exc:
            stop_event.set()
            await typing_task
            await bot.edit_message_text("❌ Failed to generate lyrics.", chat_id=chat_id, message_id=progress_msg.message_id)
            await bot.send_message(chat_id, f"Error: {exc}")
            await state.clear()

    asyncio.create_task(do_generate())


@user_router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Cancelled.", reply_markup=types.ReplyKeyboardRemove())

# Feedback or approval handler
@user_router.message(SongCreation.waiting_tone)
async def tone_received(message: Message, state: FSMContext, bot: Bot):
    tone_input = message.text.strip().lower()
    if tone_input == "skip":
        tone_value = None
    elif tone_input in [t.value for t in EmotionalTone]:
        tone_value = tone_input
    else:
        # Unknown entry – inform and default to emotional
        tone_value = EmotionalTone.EMOTIONAL.value
    await state.update_data(tone=tone_value)

    # Ask for feedback or approval
    await bot.send_message(
        message.chat.id,
        "If you'd like any changes, send feedback now (we'll apply the selected tone). Otherwise type 'approve'.",
        reply_markup=types.ReplyKeyboardRemove(),
    )
    await state.set_state(SongCreation.waiting_feedback)

@user_router.message(SongCreation.waiting_feedback)
async def feedback_received(message: Message, state: FSMContext, bot: Bot):
    text = message.text.strip()
    data = await state.get_data()
    lyrics = data.get("lyrics", "")
    style_text = data.get("music_style", MusicStyle.POP.value)
    chat_id = message.chat.id

    # If user approves lyrics, move to product/package selection
    if text.lower() in {"approve", "approved", "ok", "yes"}:
        kb = [[types.KeyboardButton(text="Audio Only (Free Beta)"), types.KeyboardButton(text="Audio + Video (Free Beta)")]]
        await bot.send_message(chat_id, "Almost done! Choose a package (no charge during beta):", reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, one_time_keyboard=True))
        await state.set_state(SongCreation.waiting_product)
        return

    # Otherwise treat message as feedback to improve lyrics

    # Prepend tone to feedback if user selected one
    selected_tone = data.get("tone")
    feedback_with_tone = text
    if selected_tone:
        feedback_with_tone = f"Please make the lyrics more {selected_tone}. {text}"

    payload = {
        "lyrics": lyrics,
        "feedback": feedback_with_tone,
    }

    try:
        backend_url = os.getenv("BACKEND_API_URL", "http://localhost:8000/api/v1")
        headers = {"X-Bot-Key": os.getenv("BOT_API_KEY", "")}
        async with httpx.AsyncClient(timeout=600.0) as client:
            resp = await client.post(f"{backend_url}/bot/improve-lyrics", json=payload, headers=headers)
            if resp.status_code != 200:
                raise RuntimeError(f"Backend error {resp.status_code}: {resp.text[:200]}")
            new_lyrics = resp.json().get("lyrics", "")
            if not new_lyrics:
                raise RuntimeError("No improved lyrics received")

        await state.update_data(lyrics=new_lyrics)
        await bot.send_message(chat_id, f"✨ Improved lyrics:\n\n{new_lyrics}\n\nSend more feedback or type 'approve'.")
    except Exception as exc:
        await bot.send_message(chat_id, f"❌ Failed to improve lyrics: {exc}")
        await state.clear()

# Package selection handler (placeholder, no payment)
@user_router.message(SongCreation.waiting_product)
async def product_selected(message: Message, state: FSMContext, bot: Bot):
    choice = message.text.lower()
    if "video" in choice:
        product = "audio_video"
    else:
        product = "audio_only"

    await state.update_data(product=product)

    # Retrieve all data for song creation
    data = await state.get_data()
    description = data.get("full_story", "")
    style_text = data.get("music_style", MusicStyle.POP.value)
    lyrics = data.get("lyrics", "")
    tone = data.get("tone")

    # Trigger backend song creation (fire & forget)
    asyncio.create_task(create_song_for_user_with_payload(message.chat.id, description, style_text, lyrics, tone, bot))

    await message.answer("🚀 Great! Your song is being produced now. You'll receive a link once it's ready.", reply_markup=types.ReplyKeyboardRemove())

    await state.clear()

# ---------------------------------------------------------------------------
# Helper wrapper to include tone & lyrics ------------------------------------
# ---------------------------------------------------------------------------

async def create_song_for_user_with_payload(chat_id: int, description: str, style_text: str, lyrics: str, tone: str | None, bot: Bot):
    backend_url = os.getenv("BACKEND_API_URL", "http://localhost:8000/api/v1")
    payload = {
        "story": description,
        "style": style_text,
        "lyrics": lyrics,
    }
    if tone:
        payload["tone"] = tone

    headers = {
        "X-Bot-Key": os.getenv("BOT_API_KEY", ""),
        "X-Telegram-Id": str(chat_id),
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            resp = await client.post(f"{backend_url}/bot/create-song", json=payload, headers=headers)
            if resp.status_code != 200:
                raise RuntimeError(f"Backend error {resp.status_code}: {resp.text[:200]}")
            data = resp.json()

        msg = (
            f"{hbold('Your song is ready!')}\n"
            f"Title: {hitalic(data.get('title') or 'Untitled')}\n\n"
            f"{hbold('Lyrics')}\n{data.get('lyrics') or '—'}\n\n"
            f"Listen: {data.get('audio_url') or 'Audio still processing…'}"
        )
        await bot.send_message(chat_id, msg)
    except Exception as exc:
        logger.exception("Song creation failed: %s", exc)
        await bot.send_message(chat_id, f"❌ Sorry, something went wrong while creating your song: {exc}")

# ---------------------------------------------------------------------------
# Admin Command Handlers ------------------------------------------------------
# ---------------------------------------------------------------------------
@admin_router.message(Command("stats"))
async def cmd_stats(message: Message):
    if not is_admin(message.from_user.id):
        return
    backend_url = os.getenv("BACKEND_API_URL", "http://localhost:8000/api/v1")
    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            resp = await client.get(f"{backend_url}/bot/stats", headers={"X-Bot-Key": os.getenv("BOT_API_KEY", "")})
            if resp.status_code != 200:
                raise RuntimeError(f"Backend error {resp.status_code}: {resp.text[:200]}")
            data = resp.json()
        await message.answer(f" Users: {data.get('users', 0)}\n🎵 Songs: {data.get('songs', 0)}\n🟢 Active jobs: {len(active_jobs)}")
    except Exception as exc:
        logger.exception("Failed to fetch stats: %s", exc)
        await message.answer("❌ Sorry, something went wrong.")


@admin_router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, command: CommandObject, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    text = command.args
    if not text:
        await message.answer("Usage: /broadcast &lt;message&gt;", parse_mode="HTML")
        return
    for uid in known_user_ids:
        try:
            await bot.send_message(uid, f"📢 <b>Announcement</b>\n{text}", parse_mode="HTML")
        except Exception as e:
            logger.warning("Failed to send broadcast to %s: %s", uid, e)
    await message.answer("Broadcast completed.")

# ---------------------------------------------------------------------------
# Entry point -----------------------------------------------------------------
# ---------------------------------------------------------------------------
async def main():
    bot = Bot(BOT_TOKEN, parse_mode="HTML")
    dp = Dispatcher()

    # Mount routers
    dp.include_routers(user_router, admin_router)

    # Start polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped") 