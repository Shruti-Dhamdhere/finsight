from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
FREE_TIER_DAILY_LIMIT = int(os.getenv("FREE_TIER_DAILY_LIMIT", 3))

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verify JWT token from Supabase and return user."""
    token = credentials.credentials
    try:
        user = supabase.auth.get_user(token)
        if not user or not user.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user.user
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def get_user_profile(user_id: str) -> dict:
    """Get user profile including tier and usage."""
    result = supabase.table("profiles").select("*").eq("id", user_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="User profile not found")
    return result.data


def check_usage_limit(user_id: str) -> dict:
    """
    Check if user has exceeded their daily limit.
    Resets count if it's a new day.
    """
    from datetime import date
    profile = get_user_profile(user_id)

    # Reset counter if it's a new day
    today = str(date.today())
    if profile.get("last_reset_date") != today:
        supabase.table("profiles").update({
            "analyses_today": 0,
            "last_reset_date": today
        }).eq("id", user_id).execute()
        profile["analyses_today"] = 0

    # Check limit for free tier
    if profile.get("tier") == "free":
        if profile.get("analyses_today", 0) >= FREE_TIER_DAILY_LIMIT:
            raise HTTPException(
                status_code=429,
                detail={
                    "message": f"Daily limit of {FREE_TIER_DAILY_LIMIT} analyses reached",
                    "tier": "free",
                    "upgrade_required": True
                }
            )

    return profile


def increment_usage(user_id: str):
    """Increment user's daily analysis count."""
    profile = get_user_profile(user_id)
    supabase.table("profiles").update({
        "analyses_today": profile.get("analyses_today", 0) + 1
    }).eq("id", user_id).execute()


def log_analysis(user_id: str, ticker: str, recommendation: str,
                 confidence: float, elapsed: float):
    """Log completed analysis to usage_logs table."""
    supabase.table("usage_logs").insert({
        "user_id": user_id,
        "ticker": ticker,
        "recommendation": recommendation,
        "confidence": confidence,
        "elapsed_seconds": elapsed
    }).execute()