import stripe
import os
from fastapi import HTTPException, Request
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def create_checkout_session(user_id: str, user_email: str) -> str:
    """
    Create a Stripe checkout session for FinSight Alpha subscription.
    Returns the checkout URL to redirect the user to.
    """
    try:
        # Create or retrieve Stripe customer
        profile = supabase.table("profiles").select(
            "stripe_customer_id"
        ).eq("id", user_id).single().execute()

        customer_id = profile.data.get("stripe_customer_id")

        if not customer_id:
            customer = stripe.Customer.create(
                email=user_email,
                metadata={"supabase_user_id": user_id}
            )
            customer_id = customer.id
            supabase.table("profiles").update({
                "stripe_customer_id": customer_id
            }).eq("id", user_id).execute()

        # Create checkout session
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
            mode="subscription",
            success_url="http://localhost:3000?upgraded=true",
            cancel_url="http://localhost:3000?cancelled=true",
            metadata={"supabase_user_id": user_id}
        )

        return session.url

    except stripe.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


def create_portal_session(user_id: str) -> str:
    """
    Create a Stripe customer portal session so users can
    manage or cancel their subscription.
    """
    try:
        profile = supabase.table("profiles").select(
            "stripe_customer_id"
        ).eq("id", user_id).single().execute()

        customer_id = profile.data.get("stripe_customer_id")
        if not customer_id:
            raise HTTPException(status_code=400, detail="No subscription found")

        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url="http://localhost:3000"
        )
        return session.url

    except stripe.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


async def handle_webhook(request: Request):
    """
    Handle Stripe webhook events.
    Upgrades/downgrades user tier based on subscription status.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle subscription events
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session["metadata"].get("supabase_user_id")
        subscription_id = session.get("subscription")

        if user_id:
            supabase.table("profiles").update({
                "tier": "alpha",
                "stripe_subscription_id": subscription_id
            }).eq("id", user_id).execute()

    elif event["type"] in ["customer.subscription.deleted",
                           "customer.subscription.paused"]:
        subscription = event["data"]["object"]
        # Find user by subscription ID and downgrade
        result = supabase.table("profiles").select("id").eq(
            "stripe_subscription_id", subscription["id"]
        ).execute()

        if result.data:
            supabase.table("profiles").update({
                "tier": "free",
                "stripe_subscription_id": None
            }).eq("stripe_subscription_id", subscription["id"]).execute()

    return {"status": "ok"}