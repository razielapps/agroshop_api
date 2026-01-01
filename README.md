# AgroShop Backend API

## 🌾 Overview
AgroShop is a comprehensive agricultural marketplace platform that enables buying and selling of farm items, agricultural products, planting materials, food stuffs, land/factory rentals, and equipment. This backend API provides all necessary functionality for the AgroShop mobile/web application.

## ✨ Key Features

### 🔐 User System
- Email/username registration with full name
- JWT-based authentication
- User profiles with verification
- Account deletion with safety checks
- Favorites system

### 💰 Balance & Payment System
- Dual balance system (normal + pending)
- Escrow system for secure trades
- Recharge functionality with payment gateway integration
- Withdrawal system to bank accounts
- Transaction history

### 🛒 Trade System
- Item posting with rich categories
- Variant and option selection (size, color, grade, etc.)
- Secure trade initiation with escrow
- One-to-one chat for buyer-seller communication
- Trade completion and fund release
- Dispute resolution system

### ✅ Verification System
- Document upload for user verification
- Different limits for verified/unverified users
- Admin verification approval panel
- Enhanced trust and security

### 📋 Categories & Listings
- 10+ comprehensive agricultural categories
- Sale/rental/lease options
- Location-based listings
- Image upload support
- Advanced search and filtering

### 👮 Admin Dashboard
- System statistics and analytics
- User management
- Dispute resolution
- Verification approval
- Content moderation

## 🏗️ System Architecture

```
Client (Frontend) → REST API → Django Backend
                             ├── Database (PostgreSQL)
                             ├── File Storage (S3)
                             ├── Cache (Redis)
                             └── Async Tasks (Celery)
```

## 📁 Project Structure

```
agroshop/
├── models.py              # Database models
├── views.py              # API endpoints
├── serializers.py        # Request/response serializers
├── permissions.py        # Custom permissions
├── utils.py              # Utility functions
├── tasks.py              # Celery async tasks
├── admin.py              # Django admin configuration
├── urls.py               # URL routing
├── signals.py            # Django signals
└── apps.py               # App configuration
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- PostgreSQL 12+
- Redis 6+
- Virtualenv

### Installation

1. **Clone the repository**
```bash
git clone repo
cd repo
```

2. **Create and activate virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Run database migrations**
```bash
python manage.py migrate
```

6. **Create superuser**
```bash
python manage.py createsuperuser
```

7. **Run development server**
```bash
python manage.py runserver
```

### Environment Variables
```env
# Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=agroshop
DB_USER=postgres
DB_PASSWORD=yourpassword
DB_HOST=localhost
DB_PORT=5432

# Security
SECRET_KEY=your-secret-key-here
DEBUG=True

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# AWS S3 (optional)
USE_S3=False
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_STORAGE_BUCKET_NAME=your-bucket

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

## 📚 API Documentation

### Authentication
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/register/` | POST | Register new user |
| `/api/auth/login/` | POST | User login |
| `/api/auth/token/refresh/` | POST | Refresh JWT token |

### User Management
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/user/profile/` | GET, PATCH | Get/update user profile |
| `/api/user/balance/` | GET | Get user balance |
| `/api/user/recharge/` | POST | Recharge balance |
| `/api/user/withdraw/` | POST | Withdraw funds |
| `/api/user/verify/` | POST | Submit verification documents |
| `/api/user/dashboard/` | GET | User dashboard |
| `/api/user/account/delete/` | DELETE | Delete user account |

### Categories & Items
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/categories/` | GET | List all categories |
| `/api/items/` | GET, POST | List/create items |
| `/api/items/{id}/` | GET, PUT, PATCH, DELETE | Item CRUD |
| `/api/items/{id}/toggle_favorite/` | POST | Add/remove from favorites |

### Trades
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/trades/` | GET, POST | List/create trades |
| `/api/trades/{id}/` | GET | Get trade details |
| `/api/trades/{id}/mark_complete/` | POST | Mark trade as complete |
| `/api/trades/{id}/open_dispute/` | POST | Open dispute |
| `/api/trades/{id}/messages/` | GET | Get trade messages |
| `/api/trades/{id}/send_message/` | POST | Send message |
| `/api/trades/my_trades/` | GET | Get user's trades |

### Admin Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/admin/dashboard/` | GET | Admin dashboard stats |
| `/api/admin/users/manage/` | POST | Manage users |

## 🔒 Permissions & Limits

### Unverified Users
- Maximum 5 active ads
- Maximum 3 ads per day
- Maximum 3 active trades
- Maximum ₦500,000 per trade
- Maximum ₦1,000,000 daily trade volume

### Verified Users
- Unlimited ads
- Unlimited trades
- No trade amount limits
- 60-day ad expiry (vs 30 days for unverified)

## 💳 Payment Gateway Integration

### Integration Points

1. **Recharge Balance** (`views.py:132-158`)
```python
# Mocked payment gateway - Replace with actual implementation
# Currently simulates successful payment
transaction.status = 'completed'
transaction.save()

# Real implementation would:
# 1. Initialize payment with gateway
# 2. Redirect user to payment page
# 3. Handle webhook callback
# 4. Update transaction status
```

2. **Withdrawal Processing** (`views.py:160-216`)
```python
# Process withdrawal asynchronously
process_withdrawal.delay(transaction.id)

# Real implementation would:
# 1. Call bank transfer API
# 2. Handle callbacks
# 3. Update transaction status
```

### Required Webhook Endpoints
- `/api/webhooks/payment-success/`
- `/api/webhooks/payment-failure/`
- `/api/webhooks/withdrawal-callback/`

### Supported Payment Methods
- Bank Transfer
- Card Payments
- Mobile Money (to be integrated)
- USSD (to be integrated)

## 🗄️ Database Models

### Core Models
1. **User** - Extended Django User with full name
2. **UserProfile** - Extended user information
3. **UserBalance** - Balance tracking
4. **Category/Subcategory** - Product categorization
5. **Item** - Products for sale/rent
6. **Trade** - Buy-sell transactions
7. **PaymentTransaction** - Payment history
8. **Dispute** - Trade dispute management
9. **UserVerification** - KYC documents

## 🔧 Development

### Running Tests
```bash
python manage.py test
```

### Code Style
```bash
# Install pre-commit
pre-commit install

# Run checks
flake8 .
black .
isort .
```

### Database Migrations
```bash
# Create migration
python manage.py makemigrations

# Apply migration
python manage.py migrate

# Check migration status
python manage.py showmigrations
```

### Async Tasks (Celery)
```bash
# Start Celery worker
celery -A agroshop worker -l info

# Start Celery beat (for scheduled tasks)
celery -A agroshop beat -l info
```

## 🚀 Deployment

### Production Checklist
- [ ] Set `DEBUG=False`
- [ ] Update `ALLOWED_HOSTS`
- [ ] Configure production database
- [ ] Set up SSL certificates
- [ ] Configure S3 for media storage
- [ ] Set up Celery with Redis
- [ ] Configure email service
- [ ] Set up monitoring (Sentry, etc.)
- [ ] Configure backup strategy
- [ ] Enable security headers

### Docker Deployment
```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput

CMD ["gunicorn", "agroshop.wsgi:application", "--bind", "0.0.0.0:8000"]
```

### Deployment Platforms
- **AWS**: Elastic Beanstalk, ECS, EC2
- **Heroku**: Simple deployment
- **DigitalOcean**: Droplets or App Platform
- **Railway**: Easy deployment

## 📊 Performance Optimization

### Implemented
- Database indexing on frequently queried fields
- Query optimization with `select_related` and `prefetch_related`
- API pagination (20 items per page)
- Redis caching for frequently accessed data
- Celery for async tasks

### Recommended
- CDN for static and media files
- Database connection pooling
- API response compression
- Load balancing for high traffic

## 🔐 Security Features

### Implemented
- JWT authentication with refresh tokens
- Password validation and hashing
- CORS configuration
- CSRF protection
- SQL injection prevention (Django ORM)
- XSS protection
- Rate limiting (100/day anonymous, 1000/day users)
- File upload validation

### Recommended for Production
- Web Application Firewall (WAF)
- DDoS protection
- Regular security audits
- Penetration testing
- Security headers (HSTS, CSP)

## 📱 Frontend Integration

### API Client Setup
```javascript
// Example Axios configuration
import axios from 'axios';

const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL,
});

// Add JWT token to requests
api.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle token refresh
api.interceptors.response.use(
  response => response,
  async error => {
    if (error.response.status === 401) {
      // Refresh token logic
    }
    return Promise.reject(error);
  }
);
```

### Required Frontend Features
1. **Authentication flow** (register/login/logout)
2. **Balance management** (recharge/withdraw)
3. **Item listing** (create/edit/delete)
4. **Search and filtering**
5. **Trade management** (initiate/complete/dispute)
6. **Real-time chat** (WebSocket integration recommended)
7. **User profile** (edit/verify)
8. **Notifications system**

## 🐛 Troubleshooting

### Common Issues

1. **Database connection errors**
   - Check PostgreSQL service is running
   - Verify database credentials in `.env`
   - Ensure database exists

2. **Migration errors**
   ```bash
   python manage.py migrate --fake-initial
   python manage.py migrate --run-syncdb
   ```

3. **Static files not loading**
   ```bash
   python manage.py collectstatic
   ```

4. **Celery not processing tasks**
   - Check Redis is running
   - Verify Celery worker is started
   - Check task queue configuration

### Logs
- Application logs: `agroshop.log`
- Server logs: Check web server logs
- Database logs: PostgreSQL logs
- Celery logs: Worker output

## 📄 License
[Specify your license here]

## 👥 Contributing
1. Fork the repository
2. Create a feature branch
3. Commit changes
4. Push to the branch
5. Create a Pull Request

## 📞 Support
For support, please contact:
- Email: support@agroshop.com
- Issues: GitHub Issues page
- Documentation: [Add documentation link]

## 🔮 Roadmap
- [ ] Real-time notifications
- [ ] Advanced analytics dashboard
- [ ] Bulk upload for items
- [ ] Auction system
- [ ] Subscription plans
- [ ] Multi-language support
- [ ] Mobile money integration
- [ ] USSD payment integration
- [ ] Delivery tracking integration
- [ ] Advanced reporting system

---

**AgroShop** - Powering Agricultural Commerce 🚜


# agroshop_api
## This project was bootstrapped using [tap_drf](https://github.com/razielapps/tap_drf) - A production-ready Django REST Framework boilerplate with JWT auth, Swagger docs, Docker support, and more.

**Conscience Ekhomwandolor (AVT Conscience)**  
- Passionate  fullstack developer & cyber security researcher (red team enthusiast) 
- Creator of tap_drf, tap_react, tap_fullstack  
- Personal Blog: [https://medium.com/@avtconscience](https://medium.com/@avtconscience)  
- GitHub: [https://github.com/razielapps](https://github.com/razielapps)  
- Email: [avtxconscience@gmail.com](mailto:avtxconscience@gmail.com)

For questions, support, or collaboration, feel free to reach out.
