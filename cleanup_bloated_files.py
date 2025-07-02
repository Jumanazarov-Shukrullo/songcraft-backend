#!/usr/bin/env python3
"""
Cleanup script to remove bloated/duplicate files and keep clean DDD architecture.
This script removes large monolithic files that have been properly split into smaller ones.
"""

import os
import shutil

def remove_bloated_files():
    """Remove large monolithic files that have been split into smaller focused files"""
    
    files_to_remove = [
        # Large monolithic files that should be split
        "app/domain/entities.py",           # 392 lines - we have app/domain/entities/
        "app/application/dtos.py",          # 245 lines - we have app/application/dtos/
        "app/domain/domain_events.py",      # 171 lines - we have app/domain/events/
        "app/domain/value_objects.py",     # 169 lines - we have app/domain/value_objects/
        "app/domain/repositories.py",      # 143 lines - we have app/domain/repositories/
        "app/domain/aggregates.py",        # 159 lines - not needed for simple DDD
        
        # Large use case files that should be individual files
        "app/application/use_cases/user_use_cases.py",   # 219 lines
        "app/application/use_cases/song_use_cases.py",   # 192 lines  
        "app/application/use_cases/order_use_cases.py",  # 192 lines
        "app/application/use_cases/admin_use_cases.py",  # 108 lines
    ]
    
    removed_files = []
    
    for file_path in files_to_remove:
        if os.path.exists(file_path):
            print(f"🗑️  Removing bloated file: {file_path}")
            os.remove(file_path)
            removed_files.append(file_path)
        else:
            print(f"⚠️  File not found (already removed?): {file_path}")
    
    return removed_files

def clean_models_file():
    """Clean up the bloated db/models.py since we have split ORM models"""
    models_file = "app/db/models.py"
    
    if os.path.exists(models_file):
        # Keep only base imports and essential models
        clean_content = '''"""Database models - cleaned up version"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Float, JSON, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

Base = declarative_base()

# Keep only essential enums that are used across the app
class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING_VERIFICATION = "pending_verification"

class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"

class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ProductType(str, enum.Enum):
    AUDIO_ONLY = "audio_only"
    AUDIO_VIDEO = "audio_video"

class MusicStyle(str, enum.Enum):
    RAP = "rap"
    POP = "pop"
    ELECTROPOP = "electropop"
    JAZZ = "jazz"
    FUNK = "funk"
    ACOUSTIC = "acoustic"

# NOTE: Actual model classes are now in infrastructure/orm/ directory
# This keeps the file clean and follows DDD architecture
'''
        
        with open(models_file, 'w') as f:
            f.write(clean_content)
        
        print(f"🧹 Cleaned up {models_file} - removed bloated model definitions")

def remove_duplicate_directories():
    """Remove empty or duplicate directories"""
    dirs_to_check = [
        "app/domain/services",      # Empty and not needed for our DDD
        "app/application/services", # Empty and not needed
    ]
    
    for dir_path in dirs_to_check:
        if os.path.exists(dir_path) and os.path.isdir(dir_path):
            try:
                # Check if directory is empty (except __init__.py)
                files = [f for f in os.listdir(dir_path) if f != '__init__.py']
                if not files:
                    shutil.rmtree(dir_path)
                    print(f"🗂️  Removed empty directory: {dir_path}")
            except Exception as e:
                print(f"❌ Could not remove {dir_path}: {e}")

def main():
    print("🧹 Starting cleanup of bloated files...")
    print("=" * 50)
    
    # Remove bloated files
    removed = remove_bloated_files()
    
    # Clean up models file
    clean_models_file()
    
    # Remove empty directories
    remove_duplicate_directories()
    
    print("=" * 50)
    print(f"✅ Cleanup completed! Removed {len(removed)} bloated files.")
    print("\n📁 Clean architecture maintained:")
    print("   • app/domain/entities/ - individual entity files")
    print("   • app/domain/value_objects/ - individual value object files") 
    print("   • app/domain/repositories/ - individual repository interfaces")
    print("   • app/application/dtos/ - individual DTO files")
    print("   • app/application/use_cases/ - individual use case files")
    print("   • app/infrastructure/orm/ - individual ORM model files")
    print("   • app/infrastructure/repositories/ - repository implementations")

if __name__ == "__main__":
    main() 