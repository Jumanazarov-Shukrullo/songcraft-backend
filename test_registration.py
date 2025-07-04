"""Test registration functionality to debug 500 error"""

import asyncio
from app.application.use_cases.register_user import RegisterUserUseCase
from app.application.dtos.user_dtos import CreateUserDto
from app.infrastructure.repositories.unit_of_work_impl import UnitOfWorkImpl
from app.infrastructure.external_services.email_service import EmailService
from app.db.database import get_db

async def test_registration():
    """Test registration to find the source of 500 error"""
    
    # Get database session
    db = next(get_db())
    
    # Create dependencies
    unit_of_work = UnitOfWorkImpl(db)
    email_service = EmailService()
    
    # Create test user data
    user_data = CreateUserDto(
        email="test@example.com",
        password="testpassword123",
        first_name="Test",
        last_name="User"
    )
    
    # Create and execute use case
    use_case = RegisterUserUseCase(unit_of_work, email_service)
    
    try:
        result = await use_case.execute(user_data)
        print("Registration successful!")
        print(f"User ID: {result.user.id}")
        print(f"Email: {result.user.email}")
        return result
        
    except Exception as e:
        print(f"Registration failed with error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    asyncio.run(test_registration())