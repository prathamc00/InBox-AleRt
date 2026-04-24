import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from auth.dependencies import get_current_user
from db.session import get_db
from models.user import User
from core.config import settings
import structlog

log = structlog.get_logger()
router = APIRouter(prefix="/api/billing", tags=["billing"])

stripe.api_key = settings.STRIPE_SECRET_KEY

# Pricing configurations (these would normally map to real Stripe price IDs)
PRICE_IDS = {
    "pro_monthly": "price_pro_monthly_id_here",
    "pro_yearly": "price_pro_yearly_id_here"
}

@router.post("/checkout")
async def create_checkout_session(
    plan: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Creates a Stripe Checkout Session for upgrading."""
    if not stripe.api_key:
        raise HTTPException(status_code=500, detail="Stripe is not configured.")

    price_id = PRICE_IDS.get(plan)
    if not price_id:
        raise HTTPException(status_code=400, detail="Invalid plan selected.")

    # Create or get Stripe Customer
    customer_id = current_user.stripe_customer_id
    if not customer_id:
        customer = stripe.Customer.create(
            email=current_user.email,
            name=current_user.display_name,
            metadata={"user_id": str(current_user.id), "tenant_id": current_user.tenant_id}
        )
        customer_id = customer.id
        current_user.stripe_customer_id = customer_id
        await db.commit()

    try:
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=f"{settings.FRONTEND_URL}/dashboard/billing?success=true",
            cancel_url=f"{settings.FRONTEND_URL}/dashboard/billing?canceled=true",
        )
        return {"url": session.url}
    except Exception as e:
        log.error("Stripe Checkout Error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create checkout session.")


@router.post("/portal")
async def create_customer_portal(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Creates a Stripe Customer Portal link for managing subscriptions."""
    if not current_user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No active subscription found.")

    try:
        session = stripe.billing_portal.Session.create(
            customer=current_user.stripe_customer_id,
            return_url=f"{settings.FRONTEND_URL}/dashboard/billing",
        )
        return {"url": session.url}
    except Exception as e:
        log.error("Stripe Portal Error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to open billing portal.")


@router.post("/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handles Stripe Webhooks (e.g., successful payment, subscription canceled)."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event["type"] == "customer.subscription.created" or event["type"] == "customer.subscription.updated":
        sub = event["data"]["object"]
        customer_id = sub["customer"]
        status = sub["status"]
        
        # Update user tier based on subscription status
        result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
        user = result.scalar_one_or_none()
        
        if user:
            user.stripe_subscription_id = sub["id"]
            user.tier = "pro" if status == "active" else "free"
            await db.commit()
            log.info("Subscription updated", user_id=user.id, status=status)

    elif event["type"] == "customer.subscription.deleted":
        sub = event["data"]["object"]
        customer_id = sub["customer"]
        
        result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
        user = result.scalar_one_or_none()
        
        if user:
            user.tier = "free"
            user.stripe_subscription_id = None
            await db.commit()
            log.info("Subscription canceled", user_id=user.id)

    return Response(status_code=200)
