"""Database base for DDD architecture"""

from sqlalchemy.ext.declarative import declarative_base

# Keep Base for ORM models
Base = declarative_base()

# NOTE: All model classes are now in infrastructure/orm/ directory
# This follows DDD architecture where infrastructure details are separated
# from domain logic.

# No imports of ORM models here to avoid circular dependencies
