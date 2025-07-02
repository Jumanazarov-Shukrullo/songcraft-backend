"""Email service for sending notifications and song delivery"""

import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional, Dict
import httpx
import tempfile
import os

from ...core.config import settings


class EmailService:
    
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.smtp_use_tls = settings.SMTP_USE_TLS
        self.from_email = settings.FROM_EMAIL
        self.from_name = settings.FROM_NAME
        self.frontend_url = settings.FRONTEND_URL
    
    async def send_email(self, 
                        to_email: str, 
                        subject: str, 
                        html_content: str, 
                        text_content: str = None,
                        attachments: List[Dict] = None) -> bool:
        """Send email with HTML content and optional attachments"""
        try:
            print(f"📧 Sending email to {to_email}: {subject}")
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            
            # Add text and HTML parts
            if text_content:
                text_part = MIMEText(text_content, 'plain')
                msg.attach(text_part)
            
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Add attachments if provided
            if attachments:
                for attachment in attachments:
                    await self._add_attachment(msg, attachment)
            
            # Send email
            await self._send_smtp_email(msg)
            
            print(f"✅ Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            print(f"❌ Error sending email to {to_email}: {e}")
            return False
    
    async def _send_smtp_email(self, msg: MIMEMultipart):
        """Send email via SMTP"""
        def send_sync():
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_use_tls:
                    server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, send_sync)
    
    async def _add_attachment(self, msg: MIMEMultipart, attachment: Dict):
        """Add attachment to email message"""
        try:
            url = attachment.get('url')
            filename = attachment.get('filename', 'attachment')
            
            if url:
                # Download file from URL
                async with httpx.AsyncClient() as client:
                    response = await client.get(url)
                    file_data = response.content
            else:
                file_data = attachment.get('data')
            
            if file_data:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(file_data)
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {filename}'
                )
                msg.attach(part)
                
        except Exception as e:
            print(f"⚠️ Failed to add attachment {attachment.get('filename', 'unknown')}: {e}")
    
    async def send_verification_email(self, to_email: str, verification_token: str) -> bool:
        """Send email verification email"""
        verification_url = f"{self.frontend_url}/verify-email?token={verification_token}"
        
        subject = f"Verify your {self.from_name} account"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎵 Welcome to {self.from_name}!</h1>
                    <p>Personalized Song Generation Platform</p>
                </div>
                <div class="content">
                    <h2>Verify Your Email Address</h2>
                    <p>Thank you for signing up! Please click the button below to verify your email address and start creating amazing personalized songs.</p>
                    
                    <a href="{verification_url}" class="button">Verify Email Address</a>
                    
                    <p>Or copy and paste this link into your browser:</p>
                    <p><a href="{verification_url}">{verification_url}</a></p>
                    
                    <p>This verification link will expire in 24 hours.</p>
                </div>
                <div class="footer">
                    <p>If you didn't sign up for {self.from_name}, you can safely ignore this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Welcome to {self.from_name}!
        
        Please verify your email address by clicking this link:
        {verification_url}
        
        This verification link will expire in 24 hours.
        
        If you didn't sign up for {self.from_name}, you can safely ignore this email.
        """
        
        return await self.send_email(to_email, subject, html_content, text_content)
    
    async def send_song_completed_email(self, 
                                      to_email: str, 
                                      song_title: str,
                                      audio_url: Optional[str] = None,
                                      video_url: Optional[str] = None,
                                      lyrics: str = "",
                                      order_id: str = "") -> bool:
        """Send email when song generation is completed"""
        
        subject = f"🎵 Your song '{song_title}' is ready!"
        
        # Prepare download links
        download_section = ""
        if audio_url:
            download_section += f'<p><a href="{audio_url}" class="button">🎧 Download Audio</a></p>'
        if video_url:
            download_section += f'<p><a href="{video_url}" class="button">🎬 Download Video</a></p>'
        
        # Truncate lyrics for email
        lyrics_preview = lyrics[:500] + "..." if len(lyrics) > 500 else lyrics
        
        dashboard_url = f"{self.frontend_url}/dashboard"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 10px 5px; }}
                .lyrics {{ background: white; padding: 20px; border-left: 4px solid #667eea; margin: 20px 0; font-style: italic; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
                .success {{ background: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Your Song is Ready!</h1>
                    <h2>"{song_title}"</h2>
                </div>
                <div class="content">
                    <div class="success">
                        <strong>✅ Generation Complete!</strong> Your personalized song has been successfully created.
                    </div>
                    
                    <h3>Download Your Song</h3>
                    {download_section}
                    
                    <h3>Song Lyrics</h3>
                    <div class="lyrics">
                        {lyrics_preview.replace(chr(10), '<br>')}
                    </div>
                    
                    <h3>Access Your Dashboard</h3>
                    <p>View all your songs and orders in your personal dashboard:</p>
                    <p><a href="{dashboard_url}" class="button">🎵 Open Dashboard</a></p>
                    
                    <p><strong>Order ID:</strong> {order_id}</p>
                </div>
                <div class="footer">
                    <p>Thank you for using {self.from_name}! 🎵</p>
                    <p>Need help? Reply to this email or contact our support team.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        🎉 Your Song is Ready!
        
        Song Title: "{song_title}"
        
        Your personalized song has been successfully created!
        
        Download Links:
        {f'Audio: {audio_url}' if audio_url else ''}
        {f'Video: {video_url}' if video_url else ''}
        
        Lyrics:
        {lyrics_preview}
        
        Dashboard: {dashboard_url}
        Order ID: {order_id}
        
        Thank you for using {self.from_name}!
        """
        
        return await self.send_email(to_email, subject, html_content, text_content)
    
    async def send_payment_confirmation_email(self, 
                                            to_email: str, 
                                            order_number: str,
                                            product_type: str,
                                            amount: float,
                                            currency: str = "USD") -> bool:
        """Send payment confirmation email"""
        
        subject = f"Payment Confirmed - Order #{order_number}"
        
        product_name = "Audio Song" if product_type == "audio" else "Video Song"
        dashboard_url = f"{self.frontend_url}/dashboard"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; background: #28a745; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .order-details {{ background: white; padding: 20px; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>💳 Payment Confirmed!</h1>
                    <p>Thank you for your purchase</p>
                </div>
                <div class="content">
                    <h2>Your order is being processed</h2>
                    
                    <div class="order-details">
                        <h3>Order Details</h3>
                        <p><strong>Order Number:</strong> #{order_number}</p>
                        <p><strong>Product:</strong> {product_name}</p>
                        <p><strong>Amount:</strong> ${amount:.2f} {currency}</p>
                        <p><strong>Status:</strong> ✅ Paid</p>
                    </div>
                    
                    <h3>What's Next?</h3>
                    <p>🎵 Our AI is now generating your personalized song</p>
                    <p>⏱️ This typically takes 5-15 minutes</p>
                    <p>📧 You'll receive another email when it's ready</p>
                    
                    <p><a href="{dashboard_url}" class="button">Track Progress</a></p>
                </div>
                <div class="footer">
                    <p>Questions? Reply to this email or contact support.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Payment Confirmed!
        
        Thank you for your purchase. Your order is being processed.
        
        Order Details:
        - Order Number: #{order_number}
        - Product: {product_name}
        - Amount: ${amount:.2f} {currency}
        - Status: Paid
        
        What's Next?
        - Our AI is now generating your personalized song
        - This typically takes 5-15 minutes
        - You'll receive another email when it's ready
        
        Track progress: {dashboard_url}
        """
        
        return await self.send_email(to_email, subject, html_content, text_content)
    
    async def send_password_reset_email(self, to_email: str, reset_token: str) -> bool:
        """Send password reset email"""
        reset_url = f"{self.frontend_url}/reset-password?token={reset_token}"
        
        subject = "Reset your password"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #dc3545 0%, #fd7e14 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; background: #dc3545; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
                .warning {{ background: #fff3cd; border: 1px solid #ffeaa7; color: #856404; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔒 Password Reset</h1>
                    <p>Reset your {self.from_name} password</p>
                </div>
                <div class="content">
                    <h2>Reset Your Password</h2>
                    <p>We received a request to reset your password. Click the button below to create a new password:</p>
                    
                    <a href="{reset_url}" class="button">Reset Password</a>
                    
                    <p>Or copy and paste this link into your browser:</p>
                    <p><a href="{reset_url}">{reset_url}</a></p>
                    
                    <div class="warning">
                        <strong>⚠️ Security Notice:</strong>
                        <ul>
                            <li>This link will expire in 1 hour</li>
                            <li>If you didn't request this reset, ignore this email</li>
                            <li>Your password hasn't been changed yet</li>
                        </ul>
                    </div>
                </div>
                <div class="footer">
                    <p>If you didn't request a password reset, you can safely ignore this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Password Reset Request
        
        We received a request to reset your {self.from_name} password.
        
        Click this link to reset your password:
        {reset_url}
        
        This link will expire in 1 hour.
        
        If you didn't request this reset, you can safely ignore this email.
        """
        
        return await self.send_email(to_email, subject, html_content, text_content) 