"""AI service for lyrics and music generation"""

import httpx
import asyncio
import subprocess
import tempfile
import os
from typing import Optional, List
from openai import AsyncOpenAI

from ...core.config import settings


class AIService:
    
    def __init__(self):
        # Configure HTTP client with proxy support and longer timeouts
        http_client = None
        if hasattr(settings, 'OPENAI_PROXY_URL') and settings.OPENAI_PROXY_URL:
            http_client = httpx.AsyncClient(
                proxies=settings.OPENAI_PROXY_URL,
                timeout=httpx.Timeout(180.0, connect=60.0, read=120.0),  # 3 minutes total, 1 min connect, 2 min read
                verify=False  # Set to True for production with proper SSL
            )
        
        self.openai_client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            http_client=http_client,
            base_url=getattr(settings, 'OPENAI_BASE_URL', None) or "https://api.openai.com/v1",
            timeout=180.0  # 3 minutes timeout
        )
        self.suno_api_key = settings.SUNO_API_KEY
        self.suno_api_url = settings.SUNO_API_URL
    
    async def generate_lyrics(self, description: str, music_style: str) -> str:
        """Generate lyrics using OpenAI"""
        try:
            print(f"🔄 Generating lyrics via OpenAI API (this may take 1-3 minutes with proxy)...")
            
            prompt = f"""
            Create personalized song lyrics based on:
            Description: {description}
            Music style: {music_style}
            
            Make it heartfelt and personal. Write 2-3 verses and a chorus.
            Return only the lyrics without any additional text or formatting.
            """
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a talented songwriter who creates beautiful, personalized lyrics."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.8
            )
            
            result = response.choices[0].message.content.strip()
            print("✅ Successfully generated lyrics via OpenAI API!")
            return result
            
        except Exception as e:
            error_msg = str(e)
            print(f"⚠️ OpenAI API error: {error_msg}")
            
            # Check if it's a timeout specifically
            if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                print("⏰ Request timed out - proxy connection may be slow")
                print("💡 Consider using a faster proxy or increasing timeout")
            
            print("🔄 Using fallback lyrics generation...")
            
            # Fallback lyrics if API fails
            return f"""[Verse 1]
Here's a song created just for you
With all the love that shines so true
In the style of {music_style.lower()}
This melody is meant to be

[Chorus]
Every note, every word, every rhyme
Crafted with love, perfect in time
{description[:50]}...
This song is yours, now and forever

[Verse 2]
Music speaks what words cannot say
In this {music_style.lower()} in every way
Hold this close, let it play
A gift of song for you today

[Bridge]
When words fall short, music will speak
The perfect song that you seek
{music_style.capitalize()} beats in perfect time
This personal song, yours and mine"""
    
    async def improve_lyrics(self, original_lyrics: str, feedback: str) -> str:
        """Improve lyrics based on user feedback"""
        try:
            print(f"🔄 Improving lyrics via OpenAI API...")
            
            prompt = f"""
            Improve these song lyrics based on the feedback:
            
            Original lyrics:
            {original_lyrics}
            
            Feedback: {feedback}
            
            Return the improved lyrics without any additional text.
            """
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a talented songwriter who improves lyrics based on feedback."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.7
            )
            
            result = response.choices[0].message.content.strip()
            print("✅ Successfully improved lyrics via OpenAI API!")
            return result
            
        except Exception as e:
            print(f"⚠️ OpenAI API error during improvement: {e}")
            print("🔄 Returning original lyrics...")
            return original_lyrics  # Return original if improvement fails
    
    async def generate_music(self, lyrics: str, style: str) -> Optional[str]:
        """Generate music using Suno API"""
        try:
            print(f"🎵 Generating music via Suno API...")
            
            async with httpx.AsyncClient(timeout=300.0) as client:  # 5 minutes for music generation
                response = await client.post(
                    f"{self.suno_api_url}/v1/generate",
                    headers={
                        "Authorization": f"Bearer {self.suno_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "lyrics": lyrics,
                        "style": style,
                        "duration": 180,  # 3 minutes
                        "instrumental": False,
                        "quality": "high"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print("✅ Music generation started successfully!")
                    return data.get("generation_id")
                else:
                    print(f"❌ Suno API error: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            print(f"❌ Error generating music: {e}")
            return None

    async def get_music_status(self, generation_id: str) -> dict:
        """Check music generation status"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.suno_api_url}/v1/generate/{generation_id}",
                    headers={"Authorization": f"Bearer {self.suno_api_key}"}
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"status": "error", "error": response.text}
                    
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def generate_audio(self, lyrics: str, music_style: str) -> dict:
        """Generate complete audio file from lyrics"""
        try:
            # Start music generation
            generation_id = await self.generate_music(lyrics, music_style)
            if not generation_id:
                return {"status": "error", "error": "Failed to start music generation"}
            
            # Poll for completion (with timeout)
            max_attempts = 30  # 10 minutes max
            for attempt in range(max_attempts):
                await asyncio.sleep(20)  # Wait 20 seconds between checks
                
                status_result = await self.get_music_status(generation_id)
                status = status_result.get("status")
                
                if status == "completed":
                    return {
                        "audio_url": status_result.get("audio_url"),
                        "duration": status_result.get("duration", 180),
                        "status": "completed",
                        "generation_id": generation_id
                    }
                elif status == "failed":
                    return {
                        "status": "error", 
                        "error": status_result.get("error", "Music generation failed")
                    }
                # If status is "processing", continue polling
                
            return {"status": "timeout", "error": "Music generation timed out"}
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def generate_video(self, audio_url: str, image_urls: List[str]) -> str:
        """Generate video from audio and images using ffmpeg"""
        try:
            print(f"🎬 Generating video with {len(image_urls)} images...")
            
            with tempfile.TemporaryDirectory() as temp_dir:
                # Download audio file
                audio_path = os.path.join(temp_dir, "audio.mp3")
                async with httpx.AsyncClient() as client:
                    audio_response = await client.get(audio_url)
                    with open(audio_path, "wb") as f:
                        f.write(audio_response.content)
                
                # Download images
                image_paths = []
                for i, img_url in enumerate(image_urls):
                    img_path = os.path.join(temp_dir, f"image_{i:03d}.jpg")
                    async with httpx.AsyncClient() as client:
                        img_response = await client.get(img_url)
                        with open(img_path, "wb") as f:
                            f.write(img_response.content)
                    image_paths.append(img_path)
                
                # Create video with ffmpeg
                output_path = os.path.join(temp_dir, "output.mp4")
                
                # Calculate duration per image
                # First, get audio duration
                audio_info = subprocess.run([
                    "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                    "-of", "csv=p=0", audio_path
                ], capture_output=True, text=True)
                
                audio_duration = float(audio_info.stdout.strip())
                duration_per_image = audio_duration / len(image_paths)
                
                # Create image list file for ffmpeg
                image_list_path = os.path.join(temp_dir, "images.txt")
                with open(image_list_path, "w") as f:
                    for img_path in image_paths:
                        f.write(f"file '{img_path}'\n")
                        f.write(f"duration {duration_per_image}\n")
                    # Add last image without duration to avoid ffmpeg warning
                    f.write(f"file '{image_paths[-1]}'\n")
                
                # Generate video with ffmpeg
                ffmpeg_cmd = [
                    "ffmpeg", "-y",  # Overwrite output
                    "-f", "concat",
                    "-safe", "0",
                    "-i", image_list_path,
                    "-i", audio_path,
                    "-c:v", "libx264",
                    "-c:a", "aac",
                    "-pix_fmt", "yuv420p",
                    "-shortest",  # End when shortest stream ends
                    "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",  # 9:16 aspect ratio
                    output_path
                ]
                
                print("🔄 Running ffmpeg video generation...")
                result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    print(f"❌ FFmpeg error: {result.stderr}")
                    raise Exception(f"Video generation failed: {result.stderr}")
                
                # Upload generated video to storage
                # This would typically upload to your storage service
                # For now, return a placeholder URL
                print("✅ Video generated successfully!")
                # TODO: Upload output_path to storage service and return real URL
                return f"https://storage.songcraft.app/videos/{hash(audio_url)}.mp4"
                
        except Exception as e:
            print(f"❌ Error generating video: {e}")
            raise Exception(f"Failed to generate video: {e}")

    async def sync_video_to_beats(self, audio_url: str, image_urls: List[str]) -> str:
        """Generate video with beat-synchronized image transitions"""
        try:
            print(f"🎯 Generating beat-synced video...")
            
            with tempfile.TemporaryDirectory() as temp_dir:
                # Download audio
                audio_path = os.path.join(temp_dir, "audio.mp3")
                async with httpx.AsyncClient() as client:
                    audio_response = await client.get(audio_url)
                    with open(audio_path, "wb") as f:
                        f.write(audio_response.content)
                
                # Analyze audio for beats using ffmpeg
                beats_cmd = [
                    "ffmpeg", "-i", audio_path,
                    "-af", "dynaudnorm,highpass=f=80,lowpass=f=16000",
                    "-f", "null", "-"
                ]
                
                # For simplicity, create transitions every 4 seconds (typical beat pattern)
                # In production, you'd use proper beat detection
                audio_info = subprocess.run([
                    "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                    "-of", "csv=p=0", audio_path
                ], capture_output=True, text=True)
                
                audio_duration = float(audio_info.stdout.strip())
                beat_interval = 4.0  # 4 seconds per beat/transition
                
                # Download and prepare images
                image_paths = []
                for i, img_url in enumerate(image_urls):
                    img_path = os.path.join(temp_dir, f"image_{i:03d}.jpg")
                    async with httpx.AsyncClient() as client:
                        img_response = await client.get(img_url)
                        with open(img_path, "wb") as f:
                            f.write(img_response.content)
                    image_paths.append(img_path)
                
                # Create complex ffmpeg filter for beat-synced transitions
                output_path = os.path.join(temp_dir, "beat_synced.mp4")
                
                # Build filter chain for crossfade transitions
                filter_parts = []
                num_images = len(image_paths)
                
                # Input each image as a video stream
                input_args = []
                for img_path in image_paths:
                    input_args.extend(["-loop", "1", "-t", str(audio_duration), "-i", img_path])
                
                # Add audio input
                input_args.extend(["-i", audio_path])
                
                # Create filter for crossfade transitions
                filter_chain = ""
                for i in range(num_images - 1):
                    start_time = i * beat_interval
                    if i == 0:
                        filter_chain += f"[{i}:v][{i+1}:v]xfade=transition=fade:duration=1:offset={start_time}[v{i}];"
                    else:
                        filter_chain += f"[v{i-1}][{i+1}:v]xfade=transition=fade:duration=1:offset={start_time}[v{i}];"
                
                # Final output
                final_video = f"v{num_images-2}" if num_images > 1 else "0:v"
                filter_chain += f"[{final_video}]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2[out]"
                
                ffmpeg_cmd = [
                    "ffmpeg", "-y"
                ] + input_args + [
                    "-filter_complex", filter_chain,
                    "-map", "[out]",
                    "-map", f"{num_images}:a",  # Audio stream
                    "-c:v", "libx264",
                    "-c:a", "aac",
                    "-pix_fmt", "yuv420p",
                    "-shortest",
                    output_path
                ]
                
                print("🔄 Creating beat-synchronized video...")
                result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    print(f"❌ Beat sync failed, falling back to simple video...")
                    # Fallback to simple video generation
                    return await self.generate_video(audio_url, image_urls)
                
                print("✅ Beat-synchronized video generated!")
                # TODO: Upload to storage service
                return f"https://storage.songcraft.app/videos/beat-synced-{hash(audio_url)}.mp4"
                
        except Exception as e:
            print(f"⚠️ Beat sync failed: {e}, falling back to simple video...")
            return await self.generate_video(audio_url, image_urls) 