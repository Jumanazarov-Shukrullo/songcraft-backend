#!/usr/bin/env python3
"""
Script to make a user an admin.
Usage: python make_admin.py
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.config import settings

def make_user_admin(email: str):
    """Make a user an admin by email."""
    # Create database connection
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = SessionLocal()
    
    try:
        # First, check if we need to fix the enum values in the database
        try:
            # Try to update with lowercase (Python enum values)
            result = db.execute(
                text("UPDATE users SET role = 'admin' WHERE email = :email"),
                {"email": email}
            )
            
            if result.rowcount == 0:
                print(f"❌ User with email '{email}' not found!")
                return False
            
            db.commit()
            print(f"✅ Successfully made '{email}' an admin!")
            
        except Exception as e:
            # If lowercase fails, the enum might be uppercase, so update the enum
            db.rollback()
            print("Database has uppercase enum, converting to lowercase...")
            
            # First, update the enum to allow lowercase values
            try:
                db.execute(text("ALTER TYPE userrole ADD VALUE 'user'"))
                db.execute(text("ALTER TYPE userrole ADD VALUE 'admin'"))
            except:
                pass  # Values might already exist
            
            # Update all users to use lowercase
            db.execute(text("UPDATE users SET role = 'user' WHERE role = 'USER'"))
            db.execute(text("UPDATE users SET role = 'admin' WHERE role = 'ADMIN'"))
            
            # Now set the specific user as admin
            result = db.execute(
                text("UPDATE users SET role = 'admin' WHERE email = :email"),
                {"email": email}
            )
            
            if result.rowcount == 0:
                print(f"❌ User with email '{email}' not found!")
                return False
            
            db.commit()
            print(f"✅ Successfully made '{email}' an admin with lowercase values!")
        
        # Verify the update
        user_result = db.execute(
            text("SELECT email, role FROM users WHERE email = :email"),
            {"email": email}
        ).fetchone()
        
        if user_result:
            print(f"📋 User: {user_result[0]}, Role: {user_result[1]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    admin_email = "shukrullo.jumanazarov@phystech.edu"
    print(f"🔑 Making {admin_email} an admin...")
    make_user_admin(admin_email) 
"""
Script to make a user an admin.
Usage: python make_admin.py
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.config import settings

def make_user_admin(email: str):
    """Make a user an admin by email."""
    # Create database connection
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = SessionLocal()
    
    try:
        # First, check if we need to fix the enum values in the database
        try:
            # Try to update with lowercase (Python enum values)
            result = db.execute(
                text("UPDATE users SET role = 'admin' WHERE email = :email"),
                {"email": email}
            )
            
            if result.rowcount == 0:
                print(f"❌ User with email '{email}' not found!")
                return False
            
            db.commit()
            print(f"✅ Successfully made '{email}' an admin!")
            
        except Exception as e:
            # If lowercase fails, the enum might be uppercase, so update the enum
            db.rollback()
            print("Database has uppercase enum, converting to lowercase...")
            
            # First, update the enum to allow lowercase values
            try:
                db.execute(text("ALTER TYPE userrole ADD VALUE 'user'"))
                db.execute(text("ALTER TYPE userrole ADD VALUE 'admin'"))
            except:
                pass  # Values might already exist
            
            # Update all users to use lowercase
            db.execute(text("UPDATE users SET role = 'user' WHERE role = 'USER'"))
            db.execute(text("UPDATE users SET role = 'admin' WHERE role = 'ADMIN'"))
            
            # Now set the specific user as admin
            result = db.execute(
                text("UPDATE users SET role = 'admin' WHERE email = :email"),
                {"email": email}
            )
            
            if result.rowcount == 0:
                print(f"❌ User with email '{email}' not found!")
                return False
            
            db.commit()
            print(f"✅ Successfully made '{email}' an admin with lowercase values!")
        
        # Verify the update
        user_result = db.execute(
            text("SELECT email, role FROM users WHERE email = :email"),
            {"email": email}
        ).fetchone()
        
        if user_result:
            print(f"📋 User: {user_result[0]}, Role: {user_result[1]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    admin_email = "shukrullo.jumanazarov@phystech.edu"
    print(f"🔑 Making {admin_email} an admin...")
    make_user_admin(admin_email) 