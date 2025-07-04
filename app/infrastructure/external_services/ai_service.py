"""AI service using DeepSeek for lyrics + Suno for audio/video"""

import httpx
import asyncio
import subprocess
import tempfile
import os
from typing import Optional, List

from ...core.config import settings


class AIService:
    """Central external-AI helper.

    • DeepSeek: lyrics + lyric improvement
    • Suno: music (audio) generation
    • ffmpeg helpers: video generation / beat-sync
    """

    # ------------------------------------------------------------------
    # INIT / DEEPSEEK CLIENT ------------------------------------------------
    # ------------------------------------------------------------------
    def __init__(self) -> None:
        # Configure provider (OpenRouter preferred if API key present)
        self.http_client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0, read=50.0))

        if settings.OPENROUTER_API_KEY:
            # Use OpenRouter gateway – still OpenAI-compatible schema
            self.deepseek_api_key = settings.OPENROUTER_API_KEY
            self.deepseek_base = "https://openrouter.ai/api/v1"
            self.model_id = "deepseek/deepseek-chat"  # default DeepSeek model via OpenRouter
            print("🚀 AI provider set to OpenRouter")
        else:
            # Fallback to DeepSeek direct
            self.deepseek_api_key = settings.DEEPSEEK_API_KEY
            self.deepseek_base = "https://api.deepseek.com/v1"
            self.model_id = "deepseek-chat"
            print("🚀 AI provider set to DeepSeek")

        # Suno (music) API keys
        self.suno_api_key = settings.SUNO_API_KEY
        self.suno_api_url = settings.SUNO_API_URL
        # Mureka
        self.mureka_api_key = settings.MUREKA_API_KEY
        self.mureka_api_url = settings.MUREKA_API_URL

    # ------------------------------------------------------------------
    # LYRICS (DEE P S E E K) -------------------------------------------
    # ------------------------------------------------------------------
    async def _deepseek_chat(self, messages: List[dict], max_tokens: int = 800, temperature: float = 0.8) -> str:
        """Low-level DeepSeek chat completion wrapper."""
        payload = {
            "model": self.model_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {self.deepseek_api_key}",
            "Content-Type": "application/json",
        }
        resp = await self.http_client.post(f"{self.deepseek_base}/chat/completions", json=payload, headers=headers)
        if resp.status_code != 200:
            raise RuntimeError(f"DeepSeek error {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()

    async def generate_lyrics(self, description: str, music_style: str) -> str:
        """Generate fresh lyrics with DeepSeek."""
        print("🎤 Generating lyrics via DeepSeek…")
        prompt = (
            "Create personalized song lyrics based on the following information.\n"
            f"Description: {description}\n"
            f"Music style: {music_style}\n\n"
            "Write 2-3 verses and a chorus. Return ONLY the lyrics."  # no markdown / headers
        )
        return await self._deepseek_chat([
            {"role": "system", "content": "You are a talented songwriter."},
            {"role": "user", "content": prompt},
        ])

    async def improve_lyrics(self, original_lyrics: str, feedback: str) -> str:
        """Refine existing lyrics with DeepSeek based on user feedback."""
        print("📝 Improving lyrics via DeepSeek…")
        prompt = (
            "Improve these song lyrics based on the feedback. Return only the new lyrics.\n\n"
            "Original lyrics:\n" + original_lyrics + "\n\n"
            "Feedback: " + feedback + "\n"
        )
        return await self._deepseek_chat([
            {"role": "system", "content": "You are a talented songwriter."},
            {"role": "user", "content": prompt},
        ], temperature=0.7)

    # ------------------------------------------------------------------
    # TITLE GENERATION --------------------------------------------------
    # ------------------------------------------------------------------
    async def generate_title(self, lyrics: str) -> str:
        """Generate a concise (max 2-word) title for the song based on lyrics."""
        print("🏷️ Generating song title via LLM…")
        prompt = (
            "Suggest a short, catchy song title of at most two words based on the lyrics below.\n"
            "Return ONLY the title, no quotes or punctuation.\n\n"
            + lyrics
        )
        raw = await self._deepseek_chat([
            {"role": "system", "content": "You are a creative assistant."},
            {"role": "user", "content": prompt},
        ], temperature=0.7)
        # Ensure max two words
        words = raw.strip().split()
        return " ".join(words[:2])

    # ------------------------------------------------------------------
    # MUSIC / VIDEO (SUNO + FFMPEG) -------------------------------------
    # ------------------------------------------------------------------
    async def generate_music(self, lyrics: str, style: str) -> Optional[str]:
        """Kick off Suno music generation – returns generation_id or None."""
        print("🎵 Generating music via Suno API…")
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                resp = await client.post(
                    f"{self.suno_api_url}/v1/generate",
                    headers={
                        "Authorization": f"Bearer {self.suno_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "lyrics": lyrics,
                        "style": style,
                        "duration": 180,
                        "instrumental": False,
                        "quality": "high",
                    },
                )
                if resp.status_code == 200:
                    return resp.json().get("generation_id")
                print(f"❌ Suno error {resp.status_code}: {resp.text[:200]}")
                return None
        except Exception as e:
            print(f"❌ Suno request failed: {e}")
            return None

    async def get_music_status(self, generation_id: str) -> dict:
        """Check music generation status"""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.suno_api_url}/v1/generate/{generation_id}",
                    headers={"Authorization": f"Bearer {self.suno_api_key}"},
                )
                return resp.json() if resp.status_code == 200 else {"status": "error", "error": resp.text}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def generate_audio(self, lyrics: str, music_style: str) -> dict:
        """Generate complete audio file from lyrics"""
        # Try Suno first; if unavailable (e.g., 503) fall back to Mureka
        gen_id = await self.generate_music(lyrics, music_style)
        if not gen_id and self.mureka_api_key:
            print("🔄 Falling back to Mureka AI for music generation…")
            mureka_result = await self._generate_audio_mureka(lyrics, music_style)
            print(f"🪄 Mureka result: {mureka_result}")
            return mureka_result
        if not gen_id:
            print("❌ Unable to start audio generation with any provider")
            return {"status": "failed", "error": "unable to start generation"}
        # Poll until done / fail or timeout (max 10 mins)
        for i in range(30):
            await asyncio.sleep(20)
            status = await self.get_music_status(gen_id)
            print(f"⏱️ Suno poll {i+1}: {status}")
            if status.get("status") == "completed":
                return {"status": "completed", **status}
            if status.get("status") == "failed":
                return status
        return {"status": "timeout", "error": "music generation timed out"}

    # ------------------------------------------------------------------
    # MUREKA FALLBACK ---------------------------------------------------
    # ------------------------------------------------------------------
    async def _generate_audio_mureka(self, lyrics: str, style: str) -> dict:
        headers = {
            "Authorization": f"Bearer {self.mureka_api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                url1 = f"{self.mureka_api_url}/v1/generate"
                url2 = f"{self.mureka_api_url}/generate"
                resp = await client.post(url1, headers=headers, json={"lyrics": lyrics, "style": style})
                if resp.status_code == 404:
                    resp = await client.post(url2, headers=headers, json={"lyrics": lyrics, "style": style})
                print(f"🎤 Mureka API response {resp.status_code}: {resp.text[:200]}")
                if resp.status_code != 200:
                    return {"status": "failed", "error": f"mureka-{resp.status_code}"}
                data = resp.json()
                return {
                    "status": "completed",
                    "audio_url": data.get("audio_url"),
                    "duration": data.get("duration", 180),
                }
        except Exception as e:
            print(f"❌ Mureka request failed: {e}")
            return {"status": "failed", "error": str(e)}

    # ------------------------------------------------------------------
    # Existing video helpers (generate_video / sync_video_to_beats)
    # ------------------------------------------------------------------
    async def generate_video(self, audio_url: str, image_urls: List[str]) -> str:
        """Trivial wrapper – defers to sync_video_to_beats for now."""
        return await self.sync_video_to_beats(audio_url, image_urls)

    async def sync_video_to_beats(self, audio_url: str, image_urls: List[str]) -> str:
        """Placeholder: Keep existing ffmpeg logic if needed (not implemented here)."""
        # For brevity, return audio-only URL as placeholder
        return audio_url  # Implement full logic if required 