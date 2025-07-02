import logging
from sqlalchemy.orm import Session
from .celery_app import celery_app
from .db.database import SessionLocal
from .db.models import Order, Song, OrderStatus
from .services.ai_service import AIService
from .services.email_service import email_service

logger = logging.getLogger(__name__)


def get_db():
    """Get database session for tasks."""
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def generate_song_task(self, order_id: int):
    """Background task to generate song."""
    db = get_db()
    
    try:
        # Get order
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            logger.error(f"Order {order_id} not found")
            return
        
        # Update status
        order.status = OrderStatus.PROCESSING
        db.commit()
        
        # Generate song
        ai_service = AIService()
        song_result = ai_service.generate_music(
            lyrics=order.song.lyrics,
            music_style=order.song.music_style,
            title=f"Song for {order.user.email}"
        )
        
        # Update song record
        song = order.song
        song.audio_url = song_result.get("audio_url")
        song.audio_generated = True
        db.commit()
        
        # If video requested, trigger video generation
        if order.product_type.value == "audio_video":
            generate_video_task.delay(order_id)
        else:
            # Mark order as completed and send email
            order.status = OrderStatus.COMPLETED
            db.commit()
            
            send_completion_email_task.delay(order_id)
        
        logger.info(f"Song generation completed for order {order_id}")
        
    except Exception as exc:
        logger.error(f"Error generating song for order {order_id}: {exc}")
        # Retry the task
        raise self.retry(countdown=60 * (self.request.retries + 1))


@celery_app.task(bind=True, max_retries=3)
def generate_video_task(self, order_id: int):
    """Background task to generate video."""
    db = get_db()
    
    try:
        # Get order
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            logger.error(f"Order {order_id} not found")
            return
        
        # TODO: Implement video generation logic
        # This would involve:
        # 1. Getting uploaded images
        # 2. Syncing with audio beats
        # 3. Creating video with ffmpeg
        # 4. Uploading to storage
        
        # For now, simulate video generation
        song = order.song
        song.video_url = f"https://storage.example.com/videos/{order_id}.mp4"
        song.video_generated = True
        db.commit()
        
        # Mark order as completed
        order.status = OrderStatus.COMPLETED
        db.commit()
        
        # Send completion email
        send_completion_email_task.delay(order_id)
        
        logger.info(f"Video generation completed for order {order_id}")
        
    except Exception as exc:
        logger.error(f"Error generating video for order {order_id}: {exc}")
        raise self.retry(countdown=60 * (self.request.retries + 1))


@celery_app.task(bind=True, max_retries=3)
def send_completion_email_task(self, order_id: int):
    """Background task to send completion email."""
    db = get_db()
    
    try:
        # Get order
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            logger.error(f"Order {order_id} not found")
            return
        
        # Send email
        await email_service.send_song_completion_email(
            email=order.user.email,
            user_name=order.user.email.split('@')[0],  # Use email prefix as name
            song_title=f"Your Personalized Song",
            audio_url=order.song.audio_url,
            video_url=order.song.video_url if order.song.video_generated else None
        )
        
        logger.info(f"Completion email sent for order {order_id}")
        
    except Exception as exc:
        logger.error(f"Error sending completion email for order {order_id}: {exc}")
        raise self.retry(countdown=60)


@celery_app.task
def cleanup_old_files_task():
    """Background task to cleanup old files."""
    # TODO: Implement file cleanup logic
    # This would remove files older than 48 hours
    logger.info("File cleanup task executed")


@celery_app.task
async def send_email_task(to_email: str, subject: str, html_content: str):
    """Generic email sending task."""
    try:
        await email_service.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content
        )
        logger.info(f"Email sent to {to_email}")
    except Exception as exc:
        logger.error(f"Error sending email to {to_email}: {exc}")
        raise 