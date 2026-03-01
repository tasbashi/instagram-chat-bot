# 🤖 Instagram AI Chatbot Platform

> **Multi-tenant AI chatbot platform** that automates Instagram Business DMs with RAG-powered knowledge retrieval, appointment management, and email notifications.

Business owners connect their Instagram accounts, upload PDF knowledge bases, and configure an AI agent that autonomously handles customer conversations — answering product questions, booking appointments, and sending email notifications.

---

## 📐 Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        NGINX (Port 80)                          │
│              Reverse Proxy + Static Frontend Serving             │
├────────────────────────┬─────────────────────────────────────────┤
│    /api/* + /webhook   │              / (Static)                │
│          ↓             │                  ↓                      │
│  ┌──────────────┐      │      ┌─────────────────────┐           │
│  │   FastAPI     │      │      │   React + Vite      │           │
│  │  (Port 8000)  │      │      │   (Tailwind CSS)    │           │
│  │               │      │      │                     │           │
│  │  • Auth API   │      │      │  • Login/Register   │           │
│  │  • Agent CRUD │      │      │  • Agent Management │           │
│  │  • Webhook    │      │      │  • Appointments     │           │
│  │  • Appointments│     │      │  • Chat History     │           │
│  │  • Chat History│     │      │  • Dark/Light Theme │           │
│  │  • Instagram  │      │      └─────────────────────┘           │
│  │    OAuth      │      │                                        │
│  └──────┬───────┘      │                                        │
│         │               │                                        │
│  ┌──────┴───────┐      │                                        │
│  │  Orchestrator │      │                                        │
│  │  (LLM Brain)  │      │                                        │
│  │               │      │                                        │
│  │  tools:       │      │                                        │
│  │  • search_    │      │                                        │
│  │    knowledge  │      │                                        │
│  │  • manage_    │      │                                        │
│  │    appointment│      │                                        │
│  │  • send_email │      │                                        │
│  │  • collect_   │      │                                        │
│  │    compliment │      │                                        │
│  └──────┬───────┘      │                                        │
│         │               │                                        │
│  ┌──────┴───────────────┴──────────────────────────────────┐    │
│  │                    Data Layer                            │    │
│  │                                                          │    │
│  │  ┌─────────────┐    ┌────────────┐    ┌──────────────┐  │    │
│  │  │ PostgreSQL  │    │   Qdrant   │    │ Azure OpenAI │  │    │
│  │  │ (Port 5432) │    │(Port 6333) │    │  Embeddings  │  │    │
│  │  │             │    │            │    │              │  │    │
│  │  │ Users       │    │ Per-agent  │    │ text-embed-  │  │    │
│  │  │ Agents      │    │ vector     │    │ ding-3-small │  │    │
│  │  │ Conversations│   │ collections│    │ (768-dim)    │  │    │
│  │  │ Appointments│    │            │    │              │  │    │
│  │  │ Messages    │    │ Cosine     │    │              │  │    │
│  │  │ Compliments │    │ similarity │    │              │  │    │
│  │  └─────────────┘    └────────────┘    └──────────────┘  │    │
│  └──────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🧰 Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Backend** | FastAPI (Python 3.12) | Async REST API + webhook handler |
| **Frontend** | React 19 + Vite 7 + TypeScript | SPA dashboard |
| **Styling** | Tailwind CSS 4 | Utility-first CSS with dark/light theme |
| **Database** | PostgreSQL 16 + SQLAlchemy 2.0 | Relational data (async via asyncpg) |
| **Vector DB** | Qdrant | Per-agent vector collections for RAG |
| **Embeddings** | Azure OpenAI (text-embedding-3-small) | 768-dim document embeddings |
| **LLM** | Groq (Llama 3.3 70B) / Azure OpenAI (GPT-4o) | Per-agent configurable |
| **Auth** | JWT + bcrypt + email verification | User auth with 6-digit OTP |
| **Email** | aiosmtplib (Gmail SMTP) | Verification codes + event notifications |
| **Migrations** | Alembic | Schema versioning |
| **Proxy** | Nginx | Reverse proxy + SPA routing |
| **Container** | Docker Compose | 4-service orchestration |
| **Tunnel** | ngrok | Webhook dev tunnel |

---

## 📁 Project Structure

```
instagram-chat-bot/
├── backend/
│   ├── app/
│   │   ├── api/                    # FastAPI route modules
│   │   │   ├── auth.py             #   register, verify-email, login, me
│   │   │   ├── agents.py           #   CRUD, LLM config, PDF upload
│   │   │   ├── appointments.py     #   list, create, update, cancel, complete
│   │   │   ├── chat_history.py     #   conversations + messages
│   │   │   └── instagram.py        #   OAuth flow + account linking
│   │   ├── models/                 # SQLAlchemy ORM models
│   │   │   ├── user.py             #   email, password_hash, verification
│   │   │   ├── agent.py            #   name, context, permissions, llm_config
│   │   │   ├── instagram_account.py#   ig_user_id, token, username
│   │   │   ├── appointment.py      #   date, time, status, user_id FK
│   │   │   ├── conversation.py     #   customer, status, result, metadata
│   │   │   ├── message.py          #   sender_type, content, tool_calls
│   │   │   ├── knowledge_document.py#  filename, chunk_count, status
│   │   │   ├── compliment.py       #   content, customer_ig_id
│   │   │   └── email_log.py        #   to, subject, status
│   │   ├── services/               # Business logic
│   │   │   ├── agent_orchestrator.py#  DM → LLM → tools → reply (574 lines)
│   │   │   ├── llm_client.py       #  Provider-agnostic chat completion
│   │   │   ├── llm_providers.py    #  Groq + Azure OpenAI registry
│   │   │   ├── email_service.py    #  SMTP + branded HTML templates
│   │   │   ├── encryption.py       #  Fernet encrypt/decrypt for secrets
│   │   │   ├── instagram_api.py    #  IG Graph API message sending
│   │   │   └── rag/                #  RAG pipeline modules
│   │   │       ├── ingestion.py    #    End-to-end PDF → vectors
│   │   │       ├── pdf_parser.py   #    PyMuPDF text + section extraction
│   │   │       ├── chunker.py      #    Sliding window + sentence boundaries
│   │   │       ├── embedder.py     #    Azure OpenAI embedding client
│   │   │       └── vector_store.py #    Qdrant CRUD operations
│   │   ├── tools/                  # LLM callable tools
│   │   │   ├── base.py             #   BaseTool abstract class
│   │   │   └── executors.py        #   4 tools (632 lines)
│   │   ├── schemas/                # Pydantic request/response models
│   │   ├── config.py               # Pydantic settings from .env
│   │   ├── deps.py                 # FastAPI dependency injection
│   │   ├── security.py             # Webhook signature verification
│   │   ├── handlers.py             # Message/postback/story dispatchers
│   │   └── main.py                 # App entry + lifespan + webhook routes
│   ├── alembic/                    # Database migrations
│   ├── Dockerfile                  # Python 3.12-slim + uvicorn
│   └── requirements.txt            # 77 packages
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── LoginPage.tsx       # Email + password login
│   │   │   ├── RegisterPage.tsx    # Registration form
│   │   │   ├── VerifyEmailPage.tsx # 6-digit OTP verification UI
│   │   │   ├── AgentsPage.tsx      # Agent CRUD + config + PDF upload
│   │   │   ├── AppointmentsPage.tsx# Appointment management dashboard
│   │   │   └── ChatHistoryPage.tsx # Conversation list + message viewer
│   │   ├── context/
│   │   │   ├── AuthContext.tsx     # JWT auth state + API interceptor
│   │   │   └── ThemeContext.tsx    # Dark/light theme toggle
│   │   ├── components/
│   │   │   └── Navbar.tsx          # Navigation bar
│   │   ├── lib/
│   │   │   └── api.ts             # Typed API client (251 lines)
│   │   ├── App.tsx                # Router + auth guards
│   │   ├── main.tsx               # React entry point
│   │   └── index.css              # CSS variables + Tailwind config
│   ├── package.json               # React 19, Vite 7, Tailwind 4
│   └── vite.config.ts
├── nginx/
│   ├── Dockerfile                  # Multi-stage: build frontend + serve
│   └── nginx.conf                  # API proxy + SPA fallback
├── docker-compose.yml              # postgres + qdrant + backend + nginx
├── deploy.sh                       # One-command EC2 deployment
├── .env.production.template        # All environment variables documented
├── STARTUP.md                      # Local development guide
└── docs/                           # Weekly reports
```

**Backend:** 42 Python files · ~5,200 lines  
**Frontend:** 11 source files · ~3,200 lines

---

## ⚙️ Core Features

### 🔐 Authentication System
- **Registration** with email + password (bcrypt hashed)
- **6-digit email verification**: OTP code via SMTP, 5-min expiry, rate limiting
- **JWT tokens**: 24-hour expiry, required for all API access
- **Login gate**: unverified emails blocked (HTTP 403)

### 🤖 AI Agent Orchestrator
- **Single orchestrator per agent** — receives IG DMs, calls LLM, executes tools, sends reply
- **Multi-turn tool calling loop** (max 5 rounds) — the agent can chain multiple tools per conversation turn
- **Per-agent LLM configuration** — choose Groq (Llama 3.3 70B) or Azure OpenAI (GPT-4o)
- **System context prompt** — customizable per agent via the dashboard
- **4 available tools:**

| Tool | Description |
|------|-------------|
| `search_knowledge` | RAG vector search over uploaded PDFs |
| `manage_appointment` | Check availability, create, cancel, list appointments |
| `send_email` | Send email to business owner via SMTP |
| `collect_compliment` | Record positive customer feedback |

### 📚 RAG Pipeline (Retrieval-Augmented Generation)
- **PDF ingestion**: upload → parse (PyMuPDF) → chunk (sliding window, 400 tokens, 50 overlap) → embed (Azure OpenAI) → store (Qdrant)
- **Per-agent vector collections**: each agent has isolated search scope
- **Section-aware parsing**: font-size heuristic detects headings (≥14pt)
- **Sentence boundary chunking**: never breaks mid-sentence

### 📅 Appointment System
- **AI-driven booking** via Instagram DM: the agent collects name, surname, subject, date, time
- **Availability checking**: detects time conflicts, suggests free slots
- **User-scoped data**: `user_id` FK ensures cross-agent isolation
- **Email notifications**: create/cancel/reschedule → branded HTML email to owner
- **Dashboard management**: list, filter, update, cancel, complete

### 📱 Instagram Integration
- **Business Login OAuth**: authorization URL → code exchange → long-lived token
- **Webhook receiver**: message, postback, story mention events
- **Multi-account support**: one user can link multiple IG accounts
- **Agent auto-routing**: webhook `entry.id` matched to correct agent via IGSID resolution
- **Message chunking**: long replies split at natural boundaries (paragraph → line → sentence → word)

### 🎨 Dashboard (React SPA)
- **Agent management**: create, configure LLM, set permissions, upload PDFs
- **Appointment dashboard**: calendar view, filters, status management
- **Chat history**: conversation list with result badges, message viewer
- **Dark/light theme**: CSS variable cascade, localStorage persistence
- **Responsive design**: Tailwind CSS with semantic tokens

---

## 🚀 Quick Start

### Prerequisites

- **Docker** + Docker Compose v2 (for production)
- **Python 3.12+** with `venv` (for local dev)
- **Node.js 18+** with npm (for local dev)
- **PostgreSQL 16** (or use Docker)

### Local Development

```bash
# 1. Clone
git clone <repo-url>
cd instagram-chat-bot

# 2. Start infrastructure
docker run -d --name qdrant -p 6333:6333 -v qdrant_data:/qdrant/storage qdrant/qdrant
sudo service postgresql start  # or use Docker for Postgres too

# 3. Backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in your keys
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 4. Frontend (new terminal)
cd frontend
npm install
npm run dev                   # → http://localhost:5173
```

### Production Deploy (EC2)

```bash
# 1. Copy your secrets
cp .env.production.template backend/.env
# Edit backend/.env with your actual API keys

# 2. One-command deploy
chmod +x deploy.sh
./deploy.sh
```

This will:
- Install Docker if not present
- Build all 4 services (postgres, qdrant, backend, nginx)
- Serve the app on port 80

---

## 🔑 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | ✅ | PostgreSQL async connection string |
| `QDRANT_HOST` | ✅ | Qdrant hostname (default: `localhost`) |
| `JWT_SECRET` | ✅ | JWT signing secret |
| `ENCRYPTION_KEY` | ✅ | Fernet key for encrypting API keys in DB |
| `GROQ_API_KEY` | ⚡ | Groq API key (if using Groq provider) |
| `AZURE_OPENAI_ENDPOINT` | ⚡ | Azure OpenAI endpoint (if using Azure) |
| `AZURE_OPENAI_API_KEY` | ⚡ | Azure OpenAI API key |
| `AZURE_EMBEDDING_ENDPOINT` | ✅ | Azure embedding endpoint (for RAG) |
| `AZURE_EMBEDDING_API_KEY` | ✅ | Azure embedding API key |
| `FACEBOOK_APP_ID` | ✅ | Meta app ID for Instagram OAuth |
| `FACEBOOK_APP_SECRET` | ✅ | Meta app secret |
| `INSTAGRAM_APP_ID` | ✅ | Instagram app ID |
| `INSTAGRAM_APP_SECRET` | ✅ | Instagram app secret |
| `APP_SECRET` | ✅ | Webhook signature verification |
| `SMTP_USER` | ✅ | Gmail address for sending emails |
| `SMTP_PASSWORD` | ✅ | Gmail app password |
| `NGROK_AUTH_TOKEN` | ❌ | For local webhook tunnel (dev only) |

See [`.env.production.template`](.env.production.template) for the complete list with defaults.

---

## 📡 API Reference

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Create account + send verification code |
| POST | `/api/auth/verify-email` | Verify 6-digit code → get JWT |
| POST | `/api/auth/resend-code` | Resend verification code |
| POST | `/api/auth/login` | Login → get JWT |
| GET | `/api/auth/me` | Get current user |

### Agents
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/agents` | List user's agents |
| POST | `/api/agents` | Create agent for IG account |
| PUT | `/api/agents/{id}` | Update name/context |
| PUT | `/api/agents/{id}/permissions` | Update tool permissions |
| PUT | `/api/agents/{id}/llm-config` | Change LLM provider/model |
| PUT | `/api/agents/{id}/toggle` | Activate/deactivate |
| DELETE | `/api/agents/{id}` | Delete agent + data |
| POST | `/api/agents/{id}/documents` | Upload PDF knowledge base |
| GET | `/api/agents/{id}/documents` | List uploaded documents |
| DELETE | `/api/agents/{id}/documents/{doc}` | Delete document + vectors |

### Appointments
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/appointments` | List (filters: agent, status, date) |
| POST | `/api/appointments` | Create appointment |
| PUT | `/api/appointments/{id}` | Update date/time/details |
| PUT | `/api/appointments/{id}/cancel` | Cancel with reason |
| PUT | `/api/appointments/{id}/complete` | Mark completed |

### Chat History
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/chat-history` | List conversations |
| GET | `/api/chat-history/{id}` | Get messages for conversation |
| PUT | `/api/chat-history/{id}/status` | Update status (active/resolved/escalated) |

### Instagram
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/instagram/auth-url` | Get OAuth authorization URL |
| GET | `/api/instagram/callback` | OAuth callback handler |
| GET | `/api/instagram/accounts` | List linked IG accounts |
| DELETE | `/api/instagram/accounts/{id}` | Unlink IG account |

### Webhook
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/webhook` | Meta verification challenge |
| POST | `/webhook` | Incoming DM/event handler |

---

## 🐳 Docker Services

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `postgres` | postgres:16 | 5432 | Relational database |
| `qdrant` | qdrant/qdrant | 6333 | Vector search engine |
| `backend` | python:3.12-slim | 8000 | FastAPI application |
| `nginx` | nginx:alpine | 80 | Reverse proxy + frontend |

---

## 📊 Database Schema

```
users
├── id (UUID PK)
├── email (unique)
├── password_hash
├── full_name
├── is_email_verified
├── verification_code
└── verification_code_expires_at

instagram_accounts
├── id (UUID PK)
├── user_id → users.id
├── ig_user_id
├── ig_username
├── access_token (encrypted)
└── is_active

agents
├── id (UUID PK)
├── instagram_account_id → instagram_accounts.id
├── name
├── system_context (custom prompt)
├── permissions (JSON: read/write/email/appointments)
├── llm_config (JSON: provider, config, temp, max_tokens)
└── is_active

conversations
├── id (UUID PK)
├── agent_id → agents.id
├── customer_ig_id
├── status (active | resolved | escalated)
├── result (appointment_created | compliment | email_sent | ...)
├── message_count
└── metadata (JSON: tags)

messages
├── id (UUID PK)
├── conversation_id → conversations.id
├── sender_type (customer | assistant | system)
├── content
└── tool_calls (JSON)

appointments
├── id (UUID PK)
├── agent_id → agents.id (SET NULL)
├── user_id → users.id (SET NULL)
├── customer_ig_id
├── customer_name / surname
├── appointment_date / time
├── status (confirmed | cancelled | completed | no_show)
├── created_via (chatbot | manual)
└── cancellation_reason

knowledge_documents
├── id (UUID PK)
├── agent_id → agents.id
├── filename
├── chunk_count
└── status (processing | ready | error)

compliments
├── id (UUID PK)
├── agent_id → agents.id
├── customer_ig_id
└── content
```

---

## 🔄 Message Flow

```
Instagram DM → Meta Webhook → POST /webhook
                                    │
                              verify_signature()
                                    │
                              parse entry.id (recipient IG account)
                                    │
                              _resolve_agent() — match webhook IGSID → agent
                                    │
                              handle_incoming_message()
                                    ├── load last 10 messages as context
                                    ├── build system prompt (agent.system_context)
                                    ├── call LLM (Groq/Azure)
                                    │       │
                                    │   tool_calls? ──→ execute tool
                                    │       │              │
                                    │       ←── tool result ←┘
                                    │       │
                                    │   (loop up to 5 rounds)
                                    │       │
                                    ├── final text response
                                    ├── save message to DB
                                    ├── update conversation.result
                                    └── send reply via IG Graph API
                                          │
                                    _split_message() if > 1000 chars
                                          │
                                    POST graph.instagram.com/v25.0/me/messages
```

---

## 📝 License

Private project — all rights reserved.
