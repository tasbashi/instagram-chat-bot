"""Instagram Business OAuth flow — Instagram API with Instagram Login.

Flow:
1. Frontend opens auth URL → user authorizes on instagram.com
2. Instagram redirects to our callback with ?code=...
3. We exchange code → short-lived token
4. Fetch user profile via /me
5. Exchange short-lived → long-lived token (60 days)
6. Subscribe app to webhook events
7. Save token + IG user info to database
8. Redirect user back to frontend

Ref: https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/business-login
"""

from __future__ import annotations

import logging
import uuid as uuid_mod

import httpx
from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.config import settings
from app.deps import CurrentUser, DBSession
from app.models.instagram_account import InstagramAccount

logger = logging.getLogger("instagram_link")

router = APIRouter(prefix="/api/instagram", tags=["instagram"])

# ── Endpoints (per official docs) ───────────────────────────────────
IG_OAUTH_URL = "https://www.instagram.com/oauth/authorize"
IG_TOKEN_URL = "https://api.instagram.com/oauth/access_token"          # POST — code → short-lived
IG_LONG_LIVED_URL = "https://graph.instagram.com/access_token"         # GET  — short → long-lived
IG_GRAPH_URL = "https://graph.instagram.com/v25.0"

# All endpoints for Business Login use graph.instagram.com
# IGA tokens are ONLY valid on graph.instagram.com, NOT graph.facebook.com

SCOPES = ",".join([
    "instagram_business_basic",
    "instagram_business_manage_messages",
    "instagram_business_manage_comments",
    "instagram_business_content_publish",
])

# Webhook fields to subscribe to after OAuth
WEBHOOK_FIELDS = ",".join([
    "messages",
    "messaging_postbacks",
    "messaging_handover",
    "messaging_referral",
    "messaging_optins",
    "messaging_seen",
    "message_reactions",
    "comments",
])


@router.get("/auth-url")
async def get_auth_url(current_user: CurrentUser) -> dict:
    """Generate the Instagram OAuth authorization URL."""
    if not settings.instagram_app_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Instagram App ID not configured. Set INSTAGRAM_APP_ID in .env",
        )

    redirect_uri = f"{settings.backend_url}/api/instagram/callback"

    url = (
        f"{IG_OAUTH_URL}"
        f"?client_id={settings.instagram_app_id}"
        f"&redirect_uri={redirect_uri}"
        f"&scope={SCOPES}"
        f"&response_type=code"
        f"&state={current_user.id}"
    )

    return {"auth_url": url}


@router.get("/callback")
async def oauth_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(""),
) -> RedirectResponse:
    """Handle Instagram OAuth callback.

    Steps follow the official Business Login docs exactly:
    1. Exchange code → short-lived token (POST api.instagram.com)
    2. Fetch user profile with /me (GET graph.instagram.com)
    3. Exchange → long-lived token (GET graph.instagram.com)
    4. Subscribe app to webhook events
    5. Upsert to database
    6. Redirect to frontend
    """
    from app.db.session import async_session_factory

    async with async_session_factory() as db:
        redirect_uri = f"{settings.backend_url}/api/instagram/callback"

        async with httpx.AsyncClient(timeout=15) as client:

            # ── Step 1: Exchange code → short-lived token ───────────
            # POST https://api.instagram.com/oauth/access_token
            token_resp = await client.post(IG_TOKEN_URL, data={
                "client_id": settings.instagram_app_id,
                "client_secret": settings.instagram_app_secret,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
                "code": code,
            })

            if token_resp.status_code != 200:
                logger.error("Token exchange failed: %s", token_resp.text)
                return RedirectResponse(
                    f"{settings.frontend_url}/agents?error=token_exchange_failed"
                )

            token_data = token_resp.json()
            logger.info("Token exchange response keys: %s", list(token_data.keys()))

            # Handle both flat and wrapped response formats
            if "data" in token_data and isinstance(token_data["data"], list):
                entry = token_data["data"][0]
                short_token = entry["access_token"]
                ig_user_id = str(entry["user_id"])
            else:
                short_token = token_data["access_token"]
                ig_user_id = str(token_data["user_id"])

            logger.info("Short token acquired for IG user %s", ig_user_id)

            # ── Step 2: Fetch user profile via /me ─────────────────
            # GET https://graph.instagram.com/v25.0/me
            # Per docs: fields=user_id,username
            ig_username = await _fetch_username(client, short_token, ig_user_id)

            # ── Step 3: Exchange → long-lived token (60 days) ──────
            # GET https://graph.instagram.com/access_token
            long_token = await _exchange_long_lived(client, short_token, ig_user_id)

            # ── Step 4: Subscribe app to webhook events ────────────
            await _subscribe_webhooks(client)

            # ── Step 5: Upsert to database ─────────────────────────
            user_id = None
            if state:
                try:
                    user_id = uuid_mod.UUID(state)
                except ValueError:
                    pass

            existing = await db.execute(
                select(InstagramAccount).where(
                    InstagramAccount.ig_user_id == ig_user_id
                )
            )
            account = existing.scalar_one_or_none()

            if account:
                # ── Cross-user protection ──
                # If this IG account belongs to a different user, reject
                if user_id and account.user_id != user_id:
                    logger.warning(
                        "⛔ IG account @%s (ID %s) already linked to user %s — rejecting link for user %s",
                        ig_username, ig_user_id, account.user_id, user_id,
                    )
                    return RedirectResponse(
                        f"{settings.frontend_url}/agents?error=account_owned_by_another_user"
                    )

                # Same user re-linking — refresh token
                account.page_access_token = long_token
                account.ig_username = ig_username
                account.is_active = True
            else:
                account = InstagramAccount(
                    user_id=user_id,
                    ig_user_id=ig_user_id,
                    ig_username=ig_username,
                    page_access_token=long_token,
                    is_active=True,
                )
                db.add(account)

            await db.commit()
            logger.info("✅ IG account saved: @%s (ID: %s)", ig_username, ig_user_id)

        # ── Step 6: Redirect to frontend ───────────────────────────
        return RedirectResponse(
            f"{settings.frontend_url}/agents?linked=true&username={ig_username}"
        )


# ── Helpers ─────────────────────────────────────────────────────────


async def _fetch_username(
    client: httpx.AsyncClient, token: str, ig_user_id: str
) -> str:
    """Try multiple strategies to get the IG username.

    Strategy 1: GET /me with fields=user_id,username (per official docs)
    Strategy 2: GET /{ig_user_id} with fields=username
    Strategy 3: Fall back to ig_user_id as display name
    """
    # Strategy 1: GET /me?fields=user_id,username
    me_resp = await client.get(
        f"{IG_GRAPH_URL}/me",
        params={"fields": "user_id,username", "access_token": token},
    )

    if me_resp.status_code == 200:
        data = me_resp.json()
        # Response may be wrapped: {"data": [{"user_id": ..., "username": ...}]}
        if "data" in data and isinstance(data["data"], list) and data["data"]:
            username = data["data"][0].get("username")
        else:
            username = data.get("username")
        if username:
            logger.info("✅ /me → @%s", username)
            return username

    logger.warning("/me GET failed (%s): %s", me_resp.status_code, me_resp.text)

    # Strategy 2: GET /{ig_user_id}?fields=username
    id_resp = await client.get(
        f"{IG_GRAPH_URL}/{ig_user_id}",
        params={"fields": "username", "access_token": token},
    )

    if id_resp.status_code == 200:
        data = id_resp.json()
        username = data.get("username")
        if username:
            logger.info("✅ /{id} → @%s", username)
            return username

    logger.warning("/{id} GET failed (%s): %s", id_resp.status_code, id_resp.text)

    # Strategy 3: Use the numeric user ID as fallback
    logger.warning("All profile fetches failed, using user ID as username")
    return ig_user_id


async def _exchange_long_lived(
    client: httpx.AsyncClient, short_token: str, ig_user_id: str
) -> str:
    """Exchange short-lived → long-lived token.

    Per docs: GET https://graph.instagram.com/access_token
      ?grant_type=ig_exchange_token
      &client_secret={app_secret}
      &access_token={short_token}
    """
    ll_resp = await client.get(IG_LONG_LIVED_URL, params={
        "grant_type": "ig_exchange_token",
        "client_secret": settings.instagram_app_secret,
        "access_token": short_token,
    })

    if ll_resp.status_code == 200:
        long_token = ll_resp.json()["access_token"]
        expires_in = ll_resp.json().get("expires_in", "?")
        logger.info("✅ Long-lived token acquired (expires_in: %s)", expires_in)
        return long_token

    logger.warning("Long-lived exchange failed (%s): %s", ll_resp.status_code, ll_resp.text)
    logger.info("Using short-lived token (valid ~1 hour)")
    return short_token


async def _subscribe_webhooks(client: httpx.AsyncClient) -> None:
    """Subscribe the app to Instagram webhook events.

    POST https://graph.instagram.com/v25.0/{app_id}/subscriptions
    Uses App Access Token: {app_id}|{app_secret}

    This ensures webhooks are delivered for all connected accounts.
    """
    app_id = settings.facebook_app_id or settings.instagram_app_id
    app_secret = settings.facebook_app_secret or settings.instagram_app_secret

    if not app_id or not app_secret:
        logger.warning("⚠️ Missing app credentials — skipping webhook subscription")
        return

    if not settings.backend_url or "localhost" in settings.backend_url:
        logger.warning("⚠️ Backend URL is localhost — skipping webhook subscription")
        return

    app_access_token = f"{app_id}|{app_secret}"
    callback_url = f"{settings.backend_url}/webhook"

    resp = await client.post(
        f"https://graph.facebook.com/v25.0/{app_id}/subscriptions",
        data={
            "object": "instagram",
            "callback_url": callback_url,
            "fields": WEBHOOK_FIELDS,
            "verify_token": settings.verify_token,
            "access_token": app_access_token,
        },
    )

    if resp.status_code == 200:
        logger.info("✅ Webhook subscription active → %s", callback_url)
    else:
        logger.warning(
            "⚠️ Webhook subscription failed (%s): %s — configure manually in Meta Console",
            resp.status_code, resp.text,
        )


# ── Account listing ─────────────────────────────────────────────────


@router.get("/accounts")
async def list_accounts(db: DBSession, current_user: CurrentUser) -> list[dict]:
    """List all Instagram accounts linked to the current user."""
    result = await db.execute(
        select(InstagramAccount).where(
            InstagramAccount.user_id == current_user.id
        )
    )
    accounts = result.scalars().all()
    return [
        {
            "id": str(a.id),
            "ig_user_id": a.ig_user_id,
            "ig_username": a.ig_username,
            "is_active": a.is_active,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in accounts
    ]


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: uuid_mod.UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> None:
    """Unlink and delete an Instagram account.

    This will cascade-delete:
    - The agent linked to this account
    - All conversations, messages, appointments, and knowledge docs for that agent

    Optionally revokes the access token with Instagram.
    """
    result = await db.execute(
        select(InstagramAccount).where(
            InstagramAccount.id == account_id,
            InstagramAccount.user_id == current_user.id,
        )
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instagram account not found or not owned by you",
        )

    username = account.ig_username

    # Attempt to revoke the token with Instagram (best-effort)
    if account.page_access_token:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                revoke_resp = await client.delete(
                    f"{IG_GRAPH_URL}/me/permissions",
                    params={"access_token": account.page_access_token},
                )
                if revoke_resp.status_code == 200:
                    logger.info("Revoked IG permissions for @%s", username)
                else:
                    logger.warning("Token revocation failed: %s", revoke_resp.text)
        except Exception:
            logger.warning("Token revocation request failed (non-blocking)")

    # Delete the account (cascades to agent → conversations → messages etc.)
    await db.delete(account)
    await db.flush()

    logger.info("🗑️ Deleted IG account @%s (ID: %s)", username, account_id)

