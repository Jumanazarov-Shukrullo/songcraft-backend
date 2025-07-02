# SongCraft Backend - Production-Ready DDD Architecture

🎵 **AI-powered personalized song generation platform** built with clean Domain-Driven Design (DDD) architecture.

## 🏗️ Architecture Overview

This backend follows **Domain-Driven Design (DDD)** principles with clean separation of concerns:

```
app/
├── domain/                    # Business Logic (Core)
│   ├── entities/             # Business entities (User, Order, Song)
│   ├── value_objects/        # Immutable values (Email, Money, EntityIds)
│   ├── repositories/         # Repository interfaces
│   ├── events/              # Domain events
│   └── enums.py             # Business enums
├── application/              # Application Logic
│   ├── use_cases/           # Individual business use cases
│   ├── dtos/                # Data transfer objects
│   └── services/            # Application services
├── infrastructure/           # Technical Implementation
│   ├── orm/                 # Database models (SQLAlchemy)
│   ├── repositories/        # Repository implementations
│   └── external_services/   # External integrations
├── api/                     # Web Layer
│   ├── routes/              # FastAPI route handlers
│   ├── dependencies.py     # Dependency injection
│   └── router.py           # Main API router
├── core/                    # Configuration & Security
│   ├── config.py           # Settings
│   └── security.py         # JWT, password hashing
└── db/                      # Database Setup
    ├── database.py         # Connection
    └── models.py           # Core enums (cleaned)
```

## 🔧 Key Features

### **Easily Replaceable Services** 
- **Email**: SMTP → Mailgun/SendGrid/Resend
- **Payment**: Lemon Squeezy → Stripe → any provider
- **Storage**: MinIO → AWS S3 → any cloud storage
- **AI**: OpenAI + Suno → any AI providers

### **Production-Ready**
- ✅ **Async/await** everywhere
- ✅ **Proper error handling** with meaningful messages
- ✅ **Background tasks** for heavy operations
- ✅ **Repository pattern** with real database operations
- ✅ **Dependency injection** for easy testing
- ✅ **Single-responsibility** classes and files

### **Scalable DDD Architecture**
- ✅ **Domain entities** with business logic
- ✅ **Value objects** for type safety
- ✅ **Use cases** for individual business operations
- ✅ **Unit of Work** for transaction management
- ✅ **Clean separation** of concerns

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- PostgreSQL
- Redis (optional)
- MinIO (for file storage)

### Installation

```bash
# Clone and setup
cd backend
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

# Clean up bloated files (run once)
python cleanup_bloated_files.py

# Setup database
alembic upgrade head

# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Environment Variables

Create `.env` file:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost/songcraft

# Security
SECRET_KEY=your-super-secret-key-here
DEBUG=True

# AI Services
OPENAI_API_KEY=sk-...
SUNO_API_KEY=your-suno-key

# Payment (Lemon Squeezy)
LEMONSQUEEZY_API_KEY=your-lemon-squeezy-key
LEMONSQUEEZY_STORE_ID=your-store-id
LEMONSQUEEZY_WEBHOOK_SECRET=your-webhook-secret
LEMONSQUEEZY_PRODUCT_ID_AUDIO=product-id-audio
LEMONSQUEEZY_PRODUCT_ID_VIDEO=product-id-video

# Storage (MinIO)
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=songcraft

# Email (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=your-email@gmail.com

# Frontend
FRONTEND_URL=http://localhost:3000
```

## 📁 File Organization

### **Individual Use Cases** (Single Responsibility)
```
application/use_cases/
├── register_user.py          # User registration
├── login_user.py             # User authentication  
├── get_user_profile.py       # Get user data
├── update_user_profile.py    # Update user data
├── create_song.py            # Create new song
├── upload_song_images.py     # Upload song images
├── process_payment_webhook.py # Handle payments
└── ...
```

### **Individual Entities** (Business Logic)
```
domain/entities/
├── user.py                   # User business logic
├── order.py                  # Order business logic
└── song.py                   # Song business logic
```

### **Individual Value Objects** (Type Safety)
```
domain/value_objects/
├── email.py                  # Email validation
├── money.py                  # Money handling
├── entity_ids.py             # Strongly-typed IDs
└── song_content.py           # Song content types
```

### **Individual ORM Models** (Database)
```
infrastructure/orm/
├── user_model.py             # User database model
├── order_model.py            # Order database model
└── song_model.py             # Song database model
```

## 🔄 API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register user
- `POST /api/v1/auth/login` - Login user
- `GET /api/v1/auth/verify-email/{token}` - Verify email

### Orders & Payments
- `POST /api/v1/orders` - Create order → get payment URL
- `GET /api/v1/orders` - List user orders
- `POST /api/v1/orders/webhooks/payment` - Payment webhook

### Songs & AI
- `POST /api/v1/songs` - Create song (starts AI generation)
- `GET /api/v1/songs` - List user songs
- `POST /api/v1/songs/{id}/generate-lyrics` - Generate lyrics
- `POST /api/v1/songs/{id}/generate-audio` - Generate audio

### File Management
- `POST /api/v1/files/songs/{id}/images` - Upload song images

### Admin
- `GET /api/v1/admin/dashboard/stats` - Dashboard stats
- `GET /api/v1/admin/users` - List all users
- `GET /api/v1/admin/system/health` - System health

## 🧪 Testing

```bash
# Run tests
pytest

# Test specific module
pytest tests/test_use_cases/

# Coverage report
pytest --cov=app tests/
```

## 🔄 Service Replacement Examples

### Replace Email Service
```python
# infrastructure/external_services/email_service.py
class EmailService:
    def __init__(self):
        # Change from SMTP to Mailgun
        self.client = MailgunClient(api_key=settings.MAILGUN_API_KEY)
        # self.client = SMTPClient(...)  # Old implementation
```

### Replace Payment Service  
```python
# infrastructure/external_services/payment_service.py
class PaymentService:
    def __init__(self):
        # Change from Lemon Squeezy to Stripe
        self.client = StripeClient(api_key=settings.STRIPE_API_KEY)
        # self.client = LemonSqueezyClient(...)  # Old implementation
```

## 📊 Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## 🐳 Docker Deployment

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f backend
```

## 🎯 Business Flow

1. **User Registration** → Email verification → Login
2. **Create Order** → Payment processing → Order confirmation
3. **Song Creation** → AI lyrics generation → AI audio generation → Delivery
4. **File Upload** → Image processing → Storage → Video generation

## 🔒 Security Features

- ✅ **JWT authentication** with refresh tokens
- ✅ **Password hashing** with bcrypt
- ✅ **Input validation** with Pydantic
- ✅ **CORS configuration** for frontend
- ✅ **Rate limiting** ready
- ✅ **Webhook signature verification**

## 📈 Scalability

- ✅ **Async operations** for high concurrency
- ✅ **Background tasks** for heavy AI processing
- ✅ **Repository pattern** for easy database switching
- ✅ **Clean architecture** for adding new features
- ✅ **Service interfaces** for easy integration changes

---

**Built with**: FastAPI, SQLAlchemy, PostgreSQL, Redis, MinIO, OpenAI, Suno AI 