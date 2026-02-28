"""FastAPI application — Instagram Business Chatbot."""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from app.config import settings
from app.db.session import engine, get_db, async_session_factory
from app.handlers import handle_message, handle_postback, handle_story_mention
from app.models.base import Base
from app.security import verify_signature

# Import all models so they're registered with Base.metadata
import app.models  # noqa: F401

# Import API routers
from app.api.auth import router as auth_router
from app.api.agents import router as agents_router
from app.api.appointments import router as appointments_router
from app.api.chat_history import router as chat_history_router
from app.api.instagram import router as instagram_router

# ── Logging ─────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(name)s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("instagram_chatbot")


# ── Lifespan ────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting Instagram Chatbot Server on port %s", settings.port)

    # Create all tables (dev convenience — use Alembic in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Database tables ensured")

    # ── Auto-start ngrok tunnel in dev ──
    tunnel = None
    if settings.ngrok_auth_token:
        try:
            from pyngrok import ngrok, conf

            conf.get_default().auth_token = settings.ngrok_auth_token
            tunnel = ngrok.connect(settings.port, "http")
            public_url = tunnel.public_url

            # Force HTTPS
            if public_url.startswith("http://"):
                public_url = public_url.replace("http://", "https://")

            # Dynamically update the backend URL for OAuth + webhooks
            settings.backend_url = public_url

            logger.info("═" * 60)
            logger.info("  🚇 ngrok tunnel active")
            logger.info("  📡 Public URL:  %s", public_url)
            logger.info("  🪝 Webhook URL: %s/webhook", public_url)
            logger.info("  🔑 Verify Token: %s", settings.verify_token)
            logger.info("  🔗 OAuth Callback: %s/api/instagram/callback", public_url)
            logger.info("═" * 60)
        except Exception:
            logger.warning("⚠️ ngrok failed to start — running without tunnel", exc_info=True)
    else:
        logger.info("ℹ️  No NGROK_AUTH_TOKEN set — skipping tunnel (set it in .env for webhook testing)")

    yield

    # Cleanup
    if tunnel:
        from pyngrok import ngrok
        ngrok.kill()
        logger.info("🚇 ngrok tunnel closed")

    await engine.dispose()
    logger.info("👋 Shutting down")


# ── App ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="Instagram Business Chatbot API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow configured frontend + common dev origins
cors_origins = [
    settings.frontend_url,
    "http://localhost:3000",
    "http://localhost:5173",
]
# Deduplicate
cors_origins = list(set(o for o in cors_origins if o))

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register API routers ────────────────────────────────────────────

app.include_router(auth_router)
app.include_router(agents_router)
app.include_router(appointments_router)
app.include_router(chat_history_router)
app.include_router(instagram_router)


# ── Health ──────────────────────────────────────────────────────────


@app.get("/")
async def health():
    return {"status": "ok", "service": "instagram-chatbot"}


# ── Webhook verification (Meta sends GET) ──────────────────────────


@app.get("/webhook", response_class=PlainTextResponse)
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """Respond to Meta's webhook verification challenge."""
    if hub_mode == "subscribe" and hub_verify_token == settings.verify_token:
        logger.info("✅ Webhook verified successfully")
        return hub_challenge

    logger.warning("❌ Webhook verification failed — mode=%s", hub_mode)
    return PlainTextResponse("Verification failed", status_code=403)


# ── Webhook event receiver (Meta sends POST) ───────────────────────


@app.post("/webhook")
async def receive_webhook(request: Request):
    """Process incoming Instagram webhook events.

    Meta expects a 200 within 20 seconds. We acknowledge fast
    and process inline (tool calls are async-friendly).

    Webhook entry structure:
    {
      "object": "instagram",
      "entry": [{
        "id": "<RECIPIENT_IG_USER_ID>",  ← which IG account received the event
        "messaging": [{ "sender": {"id": "..."}, ... }]
      }]
    }
    """
    body = await verify_signature(request)
    data = json.loads(body)

    logger.info("📨 Webhook payload received")

    obj = data.get("object")
    if obj != "instagram":
        logger.warning("⚠️ Unexpected object type: %s", obj)
        return {"status": "ignored"}

    async with async_session_factory() as db:
        try:
            for entry in data.get("entry", []):
                # entry["id"] = the IG professional account that received this event
                recipient_ig_id = str(entry.get("id", ""))

                for messaging_event in entry.get("messaging", []):
                    sender_id = messaging_event.get("sender", {}).get("id")

                    if not sender_id:
                        continue

                    # Skip if sender is the bot itself (echo)
                    if str(sender_id) == recipient_ig_id:
                        continue

                    # Skip read receipts
                    if "read" in messaging_event:
                        continue

                    # Skip echo messages (sent by the bot itself)
                    message = messaging_event.get("message", {})
                    if message.get("is_echo"):
                        continue

                    # Route by event type — pass recipient_ig_id for correct agent routing
                    if "message" in messaging_event:
                        await handle_message(sender_id, message, db, recipient_ig_id)
                    elif "postback" in messaging_event:
                        await handle_postback(sender_id, messaging_event["postback"], db, recipient_ig_id)
                    elif "story_mention" in messaging_event:
                        await handle_story_mention(sender_id, messaging_event["story_mention"], db)

            await db.commit()
        except Exception:
            await db.rollback()
            logger.exception("Webhook processing error")
            # Still return 200 to prevent Meta from retrying
            return {"status": "error"}

    return {"status": "ok"}

