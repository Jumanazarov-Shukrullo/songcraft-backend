#!/bin/bash

echo "🧹 Cleaning up old files that conflict with DDD architecture..."

# Remove old route files that import deleted services
echo "Removing old route files..."
rm -f backend/app/api/routes/users.py
rm -f backend/app/api/routes/songs.py
rm -f backend/app/api/routes/files.py
rm -f backend/app/api/routes/payments.py
rm -f backend/app/api/routes/admin.py

# Remove old service files (already deleted but check)
echo "Removing any remaining service files..."
rm -rf backend/app/services/

# Remove old schema files if they exist
echo "Removing old schemas..."
rm -f backend/app/api/schemas.py

# Remove old model files that conflict with DDD
echo "Removing conflicting model files..."
# Keep db/models.py for now but we'll migrate it

# Remove v2 files since we'll use v1 names
echo "Removing v2 files..."
rm -f backend/app/api/routes/*_v2.py

# Remove old migration files that might conflict
echo "Removing old migration versions..."
rm -f backend/alembic/versions/41dfaba905e6_add_admin_role.py
rm -f backend/alembic/versions/dedbc5e7bb5f_initial_migration_create_all_tables.py

# Remove temporary files
echo "Removing temporary files..."
rm -f backend/app/*.pyc
rm -rf backend/app/__pycache__/
rm -rf backend/app/*/__pycache__/
rm -rf backend/app/*/*/__pycache__/
rm -rf backend/app/*/*/*/__pycache__/

echo "✅ Cleanup completed!"
echo "📝 Next steps:"
echo "  1. Fix router.py imports"
echo "  2. Create proper route files"
echo "  3. Test the application" 