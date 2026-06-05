# InboxAlert 🚨

**AI-powered email monitoring that sends WhatsApp alerts for important emails**

Never miss a critical email again. InboxAlert watches your Gmail and Outlook inbox 24/7, uses AI to score every incoming email by importance, and instantly sends you a WhatsApp alert when something truly matters.

---

## 🎯 The Problem

- Professionals receive **100+ emails per day**
- Most are newsletters, promotions, or low-priority updates
- Critical emails from clients, managers, or partners get buried
- People either **miss them** or waste time **constantly checking** their inbox

## ✨ The Solution

InboxAlert acts as your **AI executive assistant**:

1. **Monitors** your Gmail/Outlook inbox in real-time
2. **Scores** every email (0-100) using a two-stage AI engine
3. **Alerts** you on WhatsApp only for high-priority emails (score ≥ 80)
4. **Auto-replies** to important emails on your behalf (optional)

---

## 🚀 Features

### Core Features
- ✅ **Real-time email monitoring** via Gmail (Pub/Sub) and Outlook (Graph API) webhooks
- ✅ **Two-stage AI scoring engine** (rule-based + Google Gemini)
- ✅ **WhatsApp alerts** with interactive buttons for quick replies
- ✅ **AI auto-reply** drafting with customizable tone
- ✅ **Multi-account support** (connect multiple Gmail/Outlook accounts)
- ✅ **Email history dashboard** with AI summaries
- ✅ **OAuth 2.0 authentication** (Google + Microsoft)

### Security
- 🔒 **AES-256 encryption** for OAuth tokens at rest
- 🔒 **RS256 JWT** authentication
- 🔒 **Rate limiting** on all API endpoints
- 🔒 **Webhook signature verification**
- 🔒 **No passwords stored** — only OAuth tokens

### Scalability
- ⚡ **Async processing** with Celery + Redis
- ⚡ **Multi-tenant architecture**
- ⚡ **Docker containerized**
- ⚡ **Horizontal scaling ready**

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Email Providers                          │
│              Gmail (Pub/Sub) | Outlook (Graph)              │
└────────────────────┬────────────────────────────────────────┘
                     │ Webhook
                     ↓
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend                           │
│  • Receives webhooks                                        │
│  • Validates signatures                                     │
│  • Queues tasks in Redis                                    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│                  Celery Worker                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Two-Stage AI Engine                          │  │
│  │                                                       │  │
│  │  Stage 1: Rule Engine (instant, free)               │  │
│  │  • Keyword detection ("urgent", "deadline")         │  │
│  │  • Spam filtering ("newsletter", "promo")           │  │
│  │  • Score modifiers (+30 or -50)                     │  │
│  │                                                       │  │
│  │  Stage 2: Gemini AI (Google's latest model)        │  │
│  │  • Reads sender, subject, body                      │  │
│  │  • Returns score (0-100) + 3-line summary          │  │
│  │  • Cost: ~$0.0001 per email                         │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
              Score >= 80?
                     │
                     ↓ YES
┌─────────────────────────────────────────────────────────────┐
│              WhatsApp  (Meta)                       │
│  🚨 Important Email Alert (Score: 94)                       │
│                                                             │
│  👤 From: client@company.com                                │
│  📌 Subject: Contract needs signature today                 │
│                                                             │
│  📝 AI Summary:                                             │
│  Your client needs the NDA signed before the 5 PM          │
│  board meeting. They've sent it twice already.             │
│                                                             │
│  [Thanks, received]  [Will review today]  [Snooze]         │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Next.js 15 + TypeScript | Modern React framework with SSR |
| **Backend** | FastAPI (Python 3.11+) | High-performance async API |
| **Database** | PostgreSQL 15 | Relational data storage |
| **Cache/Queue** | Redis 7 | Task queue + caching |
| **Task Queue** | Celery | Async email processing |
| **AI Engine** | Google Gemini 2.5 Flash | Email scoring + auto-reply |
| **Email (Gmail)** | Google Cloud Pub/Sub | Real-time push notifications |
| **Email (Outlook)** | Microsoft Graph API | Real-time push notifications |
| **WhatsApp** | Meta Business API | Alert delivery |
| **Auth** | OAuth 2.0 (Google + Microsoft) | Secure authentication |
| **Deployment** | Docker + Docker Compose | Containerization |

---

## 📦 Installation

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Google Cloud account (for Gmail + Gemini)
- Microsoft Azure account (for Outlook)
- Meta Business account (for WhatsApp)

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/inboxalert.git
cd inboxalert
```

### 2. Start infrastructure services

```bash
docker-compose up -d
```

This starts PostgreSQL and Redis.

### 3. Backend setup

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
# See SETUP.md for detailed configuration

# Run database migrations
alembic upgrade head

# Start backend server
uvicorn main:app --reload --port 8000
```

### 4. Start Celery worker (separate terminal)

```bash
cd backend
celery -A tasks.celery_app worker --loglevel=info --pool=solo
```

### 5. Frontend setup (separate terminal)

```bash
cd frontend

# Install dependencies
npm install

# Copy environment template
cp .env.local.example .env.local

# Edit .env.local with your backend URL

# Start development server
npm run dev
```

### 6. Expose with Cloudflare Tunnel (for webhooks)

```bash
cloudflared tunnel --url http://localhost:8000
```

Copy the generated URL and configure it in:
- Google Cloud Console (OAuth redirect + Pub/Sub webhook)
- Microsoft Azure (OAuth redirect + Graph webhook)
- Your `.env` file

---

## ⚙️ Configuration

### Required Environment Variables

Create `backend/.env`:

```env
# App
APP_NAME=InboxAlert
DEBUG=true
FRONTEND_URL=http://localhost:3000

# Database
DATABASE_URL=postgresql+asyncpg://inboxalert:inboxalert_dev_secret@localhost:5432/inboxalert

# Redis
REDIS_URL=redis://:inboxalert_redis_dev@localhost:6379/0

# JWT Keys (generate with: ssh-keygen -t rsa -b 2048 -m PEM)
JWT_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
JWT_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"

# Encryption (generate with: openssl rand -hex 32)
TOKEN_ENCRYPTION_KEY=your_64_char_hex_string

# Google OAuth
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
GOOGLE_CLOUD_PROJECT=your_project_id

# Microsoft OAuth
MICROSOFT_CLIENT_ID=your_client_id
MICROSOFT_CLIENT_SECRET=your_client_secret
MICROSOFT_TENANT_ID=common
MICROSOFT_REDIRECT_URI=http://localhost:8000/auth/microsoft/callback

# AI
GEMINI_API_KEY=your_gemini_api_key

# WhatsApp (Meta Business API)
WHATSAPP_ACCESS_TOKEN=your_access_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_BUSINESS_ACCOUNT_ID=your_business_account_id
WHATSAPP_WEBHOOK_VERIFY_TOKEN=your_random_secret

# Webhook Security
OUTLOOK_WEBHOOK_CLIENT_STATE=your_random_secret

# Stripe (optional)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

See `SETUP.md` for detailed setup instructions.

---

## 🧪 Testing

### Send a test email

Send this to your connected Gmail/Outlook account:

**Subject:** `Urgent: Contract needs your signature today`

**Body:**
```
Hi,

I hope this finds you well. I'm following up on the NDA we discussed 
last week. Our legal team needs your signature before the board meeting 
at 5 PM today — this is blocking the project launch.

Please review and sign at your earliest convenience. This is a priority.

Best regards,
John Smith
```

You should receive a WhatsApp alert within seconds.

### Run backend tests

```bash
cd backend
pytest
```

### Check logs

- **Backend:** Check the terminal running `uvicorn`
- **Celery:** Check the terminal running `celery worker`
- **Database:** `docker logs inbox-alert-postgres-1`

---

## 📊 How the AI Scoring Works

### Stage 1: Rule Engine (Instant, Free)

```python
# Boost score for urgent keywords
if "urgent" or "deadline" in subject:
    score += 30

# Penalize newsletters/promos
if "newsletter" or "unsubscribe" in body:
    score -= 50
    skip_ai = True  # Save API cost
```

### Stage 2: Gemini AI (If not skipped)

```
Prompt to Gemini:
"You are an executive assistant. Score this email 0-100 for importance:

Sender: client@company.com
Subject: Contract needs signature today
Body: [email body]

Return JSON: {"score": 95, "summary": "Client needs NDA signed before 5 PM board meeting"}"
```

### Final Score Calculation

```
final_score = rule_score + ai_score
final_score = clamp(final_score, 0, 100)

if final_score >= 80:
    send_whatsapp_alert()
```

---

## 🔐 Security Best Practices

- ✅ OAuth tokens encrypted with AES-256-GCM before storage
- ✅ JWT tokens use RS256 (asymmetric keys)
- ✅ All API endpoints rate-limited (SlowAPI)
- ✅ Webhook signatures verified (HMAC)
- ✅ CORS configured for frontend only
- ✅ Security headers (CSP, X-Frame-Options, etc.)
- ✅ SQL injection protection (SQLAlchemy ORM)
- ✅ No sensitive data in logs

---

## 📈 Scalability

### Current Architecture
- Single server handles ~1000 emails/hour
- Celery workers can be scaled horizontally
- Redis handles task queue + caching
- PostgreSQL with connection pooling

### Production Recommendations
- Deploy backend on Google Cloud Run / AWS ECS
- Use managed PostgreSQL (Cloud SQL / RDS)
- Use managed Redis (Cloud Memorystore / ElastiCache)
- Scale Celery workers based on queue depth
- Add CDN for frontend (Vercel / Cloudflare)

---

## 💰 Cost Breakdown (per 1000 emails/day)

| Service | Cost | Notes |
|---------|------|-------|
| **Gemini AI** | ~$3/month | $0.0001 per email (rule engine skips ~40%) |
| **WhatsApp (Meta)** | ~$1.50/month | $0.005-0.03 per conversation |
| **Google Cloud** | ~$10/month | Pub/Sub + Cloud Run (small instance) |
| **Database** | ~$7/month | Cloud SQL (db-f1-micro) |
| **Redis** | ~$5/month | Cloud Memorystore (1GB) |
| **Total** | **~$26.50/month** | For 1000 emails/day, ~200 alerts/month |

---

## 🗺️ Roadmap

- [ ] Slack integration (alternative to WhatsApp)
- [ ] Custom scoring rules (user-defined keywords)
- [ ] Email templates for auto-replies
- [ ] Mobile app (React Native)
- [ ] Team collaboration features
- [ ] Analytics dashboard (email patterns, response times)
- [ ] Calendar integration (meeting detection)
- [ ] Multi-language support

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Next.js](https://nextjs.org/) - React framework
- [Google Gemini](https://ai.google.dev/) - AI scoring engine
- [Celery](https://docs.celeryq.dev/) - Distributed task queue

---

## 📞 Support

- **Documentation:** See `docs/` folder
- **Issues:** [GitHub Issues](https://github.com/yourusername/inboxalert/issues)
- **Email:** support@inboxalert.com

---

## 🎯 Use Cases

### For Founders
"Never miss an investor email or customer complaint while focusing on building."

### For Sales Teams
"Get instant alerts when high-value leads reply — respond faster than competitors."

### For Executives
"Let AI filter your 200+ daily emails and only alert you for what truly matters."

### For Support Teams
"Auto-reply to common questions, escalate urgent issues via WhatsApp."

---

**Built with ❤️ by Pratham**

⭐ Star this repo if you find it useful!
