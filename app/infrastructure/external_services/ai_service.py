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
        
        # Debug: Print Mureka configuration
        print(f"🔧 Mureka API URL: {self.mureka_api_url}")
        print(f"🔧 Mureka API Key: {self.mureka_api_key[:20]}..." if self.mureka_api_key else "🔧 Mureka API Key: None")

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
            
            # If Mureka returns processing status, try polling for completion
            if mureka_result.get("status") == "processing":
                generation_id = mureka_result.get("generation_id")
                if generation_id:
                    try:
                        return await self._poll_mureka_completion(generation_id)
                    except Exception as e:
                        print(f"⚠️ Polling failed, but generation started successfully: {e}")
                        # Return processing status - user can check later
                        return {
                            "status": "processing",
                            "message": "Music generation started successfully. Please check back in a few minutes.",
                            "generation_id": generation_id
                        }
            
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
                # Use correct Mureka API endpoint and payload format
                url = f"{self.mureka_api_url}/v1/song/generate"
                payload = {
                    "lyrics": lyrics,
                    "model": "auto",
                    "prompt": style  # Use style as prompt description
                }
                
                print(f"🎤 Mureka API request to: {url}")
                print(f"🎤 Mureka API payload: {payload}")
                
                resp = await client.post(url, headers=headers, json=payload)
                print(f"🎤 Mureka API response {resp.status_code}: {resp.text[:200]}")
                
                if resp.status_code != 200:
                    return {"status": "failed", "error": f"mureka-{resp.status_code}"}
                
                data = resp.json()
                print(f"🎤 Mureka API response data: {data}")
                
                # Return the generation ID to poll for completion later
                return {
                    "status": "processing",
                    "generation_id": data.get("id"),
                    "created_at": data.get("created_at"),
                }
        except Exception as e:
            print(f"❌ Mureka request failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def _get_mureka_status(self, generation_id: str) -> dict:
        """Check Mureka generation status using the correct query endpoint"""
        try:
            async with httpx.AsyncClient() as client:
                # Use the correct status endpoint from working implementation
                endpoint = f"{self.mureka_api_url}/v1/song/query/{generation_id}"
                
                print(f"🔍 Checking Mureka status: {endpoint}")
                resp = await client.get(
                    endpoint,
                    headers={"Authorization": f"Bearer {self.mureka_api_key}"},
                    timeout=30.0
                )
                print(f"🔍 Response {resp.status_code}: {resp.text[:200]}")
                
                if resp.status_code == 200:
                    result = resp.json()
                    print(f"✅ Successfully got status: {result}")
                    
                    status = result.get("status", "unknown")
                    
                    # Handle successful completion
                    if status == "succeeded":
                        # Extract URLs from choices array (matching working implementation)
                        audio_urls = []
                        video_urls = []
                        choices = result.get("choices", [])
                        
                        for choice in choices:
                            url = choice.get("url", "")
                            if url:
                                # Assume audio files for now - Mureka typically returns audio
                                audio_urls.append(url)
                        
                        # Extract duration from first choice and convert from ms to seconds
                        duration_seconds = 180  # Default duration
                        if choices and len(choices) > 0:
                            duration_ms = choices[0].get("duration", 180000)  # Default 3 minutes in ms
                            duration_seconds = duration_ms // 1000  # Convert to seconds
                        
                        return {
                            "status": "completed",  # Convert to our internal status
                            "audio_url": audio_urls[0] if audio_urls else None,
                            "video_url": None,  # Mureka typically doesn't return video in song generation
                            "duration": duration_seconds,  # Duration in seconds
                            "all_urls": audio_urls,
                            "choices": choices,
                            **result
                        }
                    else:
                        # Return the status as-is for processing/failed states
                        return result
                        
                elif resp.status_code == 404:
                    return {"status": "error", "error": "Generation not found"}
                else:
                    return {"status": "error", "error": f"Status check failed with code {resp.status_code}"}
                    
        except Exception as e:
            print(f"❌ Error checking Mureka status: {e}")
            return {"status": "error", "error": str(e)}

    async def _poll_mureka_completion(self, generation_id: str) -> dict:
        """Poll Mureka for completion status with MAXIMUM cost-optimization - only 2-3 API calls total"""
        print(f"🔄 Starting MAXIMUM cost-optimized Mureka polling for generation ID: {generation_id}")
        print(f"💰 Strategy: Only 2-3 API calls total per song (vs 60+ original)")
        
        # MAXIMUM COST-OPTIMIZED: Only 2-3 total API calls per song
        start_time = asyncio.get_event_loop().time()
        max_polls = 3  # Maximum 3 API calls total
        poll_intervals = [30, 120, 180]  # 30s, 2min, 3min intervals
        
        for poll_count in range(max_polls):
            # Check once initially, then wait before subsequent polls
            if poll_count > 0:
                wait_time = poll_intervals[min(poll_count-1, len(poll_intervals)-1)]
                print(f"⏳ Waiting {wait_time}s before next poll ({poll_count+1}/{max_polls})")
                await asyncio.sleep(wait_time)
            
            # Get status
            status_result = await self._get_mureka_status(generation_id)
            status = status_result.get("status", "unknown")
            elapsed = int(asyncio.get_event_loop().time() - start_time)
            print(f"⏱️ Poll {poll_count+1}/{max_polls} ({elapsed}s): {status} [Max 3 calls total]")
            
            # Check for terminal states
            if status == "succeeded" or status == "completed":
                print("✅ Mureka generation completed successfully!")
                return {
                    "status": "completed",
                    "audio_url": status_result.get("audio_url"),
                    "video_url": status_result.get("video_url"),
                    "duration": status_result.get("duration", 180),
                    "generation_id": generation_id,
                    "all_urls": status_result.get("all_urls", []),
                    **status_result
                }
            elif status in ["failed", "cancelled", "timeouted"]:
                print(f"❌ Mureka generation failed with status: {status}")
                return {
                    "status": "failed",
                    "error": f"Generation {status}",
                    "generation_id": generation_id,
                    **status_result
                }
            elif status == "error":
                # Temporary error - continue but don't wait as long
                print(f"⚠️ Temporary error: {status_result.get('error', 'Unknown error')}")
                
                # After 3 error polls, give up and return processing status
                if poll_count >= 3:
                    return {
                        "status": "processing",
                        "message": "🎵 Your song is being created! Status checking temporarily unavailable.",
                        "generation_id": generation_id,
                        "provider": "mureka",
                        "estimated_completion_minutes": 3,
                        "user_instructions": "Check your Dashboard in a few minutes to download your completed song!"
                    }
            else:
                # Continue polling for preparing/processing/running/generating states
                print(f"⏳ Status: {status}, will continue polling...")
        
        # Reached max polls - return processing status
        elapsed = int(asyncio.get_event_loop().time() - start_time)
        print(f"⚠️ Reached max polls ({max_polls}) after {elapsed}s - returning processing status [MAXIMUM cost-optimized: 3 calls total]")
        return {
            "status": "processing", 
            "message": "🎵 Song generation is in progress. Please check your Dashboard in 10-15 minutes for the completed song.",
            "generation_id": generation_id,
            "provider": "mureka",
            "estimated_completion_minutes": 10,
            "user_instructions": "Your song will be available for download on the Dashboard when ready!"
        }

    async def get_mureka_status(self, generation_id: str) -> dict:
        """Public method to get Mureka generation status"""
        return await self._get_mureka_status(generation_id)

    async def poll_generation_completion(self, generation_id: str) -> dict:
        """Public method to poll for generation completion (used by background tasks)"""
        try:
            print(f"🔍 Polling completion for generation ID: {generation_id}")
            
            # Use the existing Mureka polling logic
            result = await self._poll_mureka_completion(generation_id)
            
            print(f"📋 Polling result: {result.get('status', 'unknown')}")
            return result
            
        except Exception as e:
            print(f"❌ Error polling generation completion: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "provider": "mureka"
            }

    # ------------------------------------------------------------------
    # Audio/Video Download Helpers
    # ------------------------------------------------------------------
    async def download_audio_file(self, url: str, filename: str = None) -> bytes:
        """Download audio file from URL and return bytes"""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                print(f"✅ Successfully downloaded audio file ({len(response.content)} bytes)")
                return response.content
                
        except Exception as e:
            print(f"❌ Failed to download audio: {e}")
            raise

    async def get_song_download_info(self, generation_id: str) -> dict:
        """Get download URLs for a completed song"""
        try:
            status_result = await self._get_mureka_status(generation_id)
            
            if status_result.get("status") == "completed":
                return {
                    "status": "ready",
                    "audio_url": status_result.get("audio_url"),
                    "all_urls": status_result.get("all_urls", []),
                    "generation_id": generation_id
                }
            else:
                return {
                    "status": status_result.get("status", "unknown"),
                    "message": "Song not ready for download yet",
                    "generation_id": generation_id
                }
                
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "generation_id": generation_id
            }

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